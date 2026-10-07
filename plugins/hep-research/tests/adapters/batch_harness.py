"""Shared harness for the batch-scheduler adapter tests: fake schedulers on PATH, fault files, the call log."""
import json
import os
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "batch-schedulers"
SHIMS = Path(__file__).resolve().parent / "batch_shims"
sys.path.insert(0, str(ADAPTER))
import batch_campaign  # noqa: E402

WORKER = """
import json, sys
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
start, stop = int(a["--start"]), int(a["--stop"])
print("synthetic worker", a["--id"], "value", a.get("--print", ""))
json.dump({"n": stop - start, "sum": sum(range(start, stop)), "seed_sum": int(a["--seed"])}, open(a["--out"], "w"))
"""


class Harness:
    """One temporary project: config, campaign, fake-scheduler store, fault file and call log."""

    def __init__(self, backend: str, items=10, chunk=1, extra=None, worker_print=""):
        self.tmp = tempfile.TemporaryDirectory(prefix="hepbatch")
        self.dir = Path(self.tmp.name).resolve()  # macOS: /var/folders is a symlink to /private/var/folders
        self.log = self.dir / "shim-calls.jsonl"
        self.faults = self.dir / "faults.json"
        self.faults.write_text("{}")
        self.env = dict(os.environ, PATH=f"{SHIMS}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
                        HEP_BATCH_SHIM_STATE=str(self.dir / "shim-store"), HEP_BATCH_SHIM_LOG=str(self.log),
                        HEP_BATCH_SHIM_FAULTS=str(self.faults))
        (self.dir / "worker.py").write_text(WORKER)
        self.cmd = (f"{shlex.quote(sys.executable)} {self.dir / 'worker.py'} --start {{start}} --stop {{stop}} --seed {{seed}} "
                    f"--out {{out}} --id {{id}}" + (f" --print {worker_print}" if worker_print else ""))
        cfg = {"backend": backend, "campaign_dir": "campaign", "resources": {"cpus": 1, "memory_mb": 1000}}
        if backend == "slurm":
            cfg["resources"]["time_limit"] = "00:10:00"
            cfg["slurm"] = {"partition": "synthetic-partition"}
        else:
            cfg["htcondor"] = {"universe": "vanilla", "file_transfer": "shared-filesystem"}
        for k, v in (extra or {}).items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        self.cfg = cfg
        self.write_config()
        self.items, self.chunk = items, chunk

    def write_config(self):
        self.config = self.dir / "batch-config.json"
        self.config.write_text(json.dumps(self.cfg))

    @property
    def cdir(self) -> Path:
        return self.dir / "campaign"

    def set_faults(self, faults: dict):
        self.faults.write_text(json.dumps(faults))

    def calls(self) -> list:
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def cli(self, *args, sleep=None):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = batch_campaign.main([args[0], "--config", str(self.config), *args[1:]], env=self.env, sleep=sleep)
        return code, json.loads(buf.getvalue())

    def plan(self, seed=11):
        return self.cli("plan", "--job", "synthetic-batch", "--items", str(self.items), "--chunk-size", str(self.chunk),
                        "--seed", str(seed), "--cmd", self.cmd)

    def state(self) -> dict:
        return json.loads((self.cdir / "state.json").read_text())

    def single_run(self) -> dict:
        m = json.loads((self.cdir / "manifest.json").read_text())
        n = m["n_items"]
        return {"n": n, "sum": sum(range(n)), "seed_sum": sum(c["seed"] for c in m["chunks"])}

    def cleanup(self):
        self.tmp.cleanup()

"""Shared helpers for the core/partition tests: a tiny worker command and a scripted executor."""
import json
import shlex
import subprocess
import sys
from pathlib import Path

from core.partition import campaign as cp
from core.partition import engine
from core.partition.executors import Executor, _blank

WORKER = """
import json, sys
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
start, stop = int(a["--start"]), int(a["--stop"])
print("worker", a["--id"], "seed", a["--seed"])
json.dump({"n": stop - start, "sum": sum(range(start, stop)), "seed_echo": int(a["--seed"])}, open(a["--out"], "w"))
"""


def make_campaign(root: Path, n_items=10, chunk=4, seed=7):
    root.mkdir(parents=True, exist_ok=True)
    (root / "worker.py").write_text(WORKER)
    q = shlex.quote
    cmd = f"{q(sys.executable)} {q(str(root / 'worker.py'))} --start {{start}} --stop {{stop}} --seed {{seed}} --out {{out}} --id {{id}}"
    manifest = engine.make_manifest("synthetic-test", n_items, chunk, seed)
    return cp.init(root / "campaign dir", manifest, cmd), manifest, cmd


def single_run(manifest, cmd_root: Path):
    """Reference: every chunk computed once in-process with the same formula as WORKER."""
    out = None
    for c in manifest["chunks"]:
        r = {"n": c["stop"] - c["start"], "sum": sum(range(c["start"], c["stop"])), "seed_echo": c["seed"]}
        out = r if out is None else engine._sum(out, r)
    return out


def run_runner(cdir: Path, cid: str, aid: str) -> int:
    return subprocess.run([sys.executable, str(cdir / "runner.py"), "--spec", str(cdir / "spec.json"), "--out-dir",
                           str(cdir / "outputs" / cid), "--chunk", cid, "--attempt", aid], capture_output=True, timeout=600).returncode


class ScriptedExecutor(Executor):
    """Each chunk gets a list of observations, one per poll; 'done' observations run the real runner first.

    script = {chunk_id: [obs, obs, ...]}; the last observation repeats. obs is a dict accepted by _blank(), plus
    "write": False to report success without writing output, "twice": True to run the chunk twice.
    """

    name = "scripted"

    def __init__(self, script):
        super().__init__()
        self.script, self.polls, self.calls, self.by_tag = script, {}, [], {}

    def prepare(self, ctx):
        return {"backend": self.name, "submission_id": ctx["submission_id"], "files": {"plan.json": json.dumps(ctx["rows"])},
                "submit_argv": ["scripted-submit"], "rows": ctx["rows"], "cdir": str(ctx["campaign_dir"]), "tag": ctx.get("tag")}

    def submit(self, plan):
        self.calls.append(("submit", [r["chunk_id"] for r in plan["rows"]]))
        self.cdir = Path(plan["cdir"])
        jobs = [{"attempt_id": r["attempt_id"], "job_id": f"j-{r['attempt_id']}"} for r in plan["rows"]]
        self.by_tag.setdefault(plan.get("tag"), []).extend({"job_id": j["job_id"]} for j in jobs)
        return jobs

    def find(self, tag, since=None):
        return list(self.by_tag.get(tag, []))

    def poll(self, records):
        self.calls.append(("poll", len(records)))
        out = {}
        for rec in records:
            seq = self.script.get(rec["chunk_id"], [{"state": "done"}])
            k = self.polls.get(rec["attempt_id"], 0)
            self.polls[rec["attempt_id"]] = k + 1
            o = dict(seq[min(k, len(seq) - 1)])
            if isinstance(o.get("per_attempt"), dict):  # different behavior per attempt number
                o = dict(o["per_attempt"].get(rec["attempt_id"], o["per_attempt"]["default"]))
            if o.get("state") == "done" and o.pop("write", True):
                run_runner(self.cdir, rec["chunk_id"], rec["attempt_id"])
                if o.pop("twice", False):
                    run_runner(self.cdir, rec["chunk_id"], rec["attempt_id"])
            o.pop("write", None)
            o.pop("twice", None)
            out[rec["attempt_id"]] = _blank(**o)
        return out

    def cancel(self, records):
        self.calls.append(("cancel", [r["job_id"] for r in records]))
        return [["scripted-cancel", r["job_id"]] for r in records]

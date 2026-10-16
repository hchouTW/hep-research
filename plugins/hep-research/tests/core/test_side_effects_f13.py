"""F-13: side effects are opt-in or bounded.
- core/partition/runner.py gives a local worker a default timeout (DEFAULT_LOCAL_WORKER_TIMEOUT_S) when the campaign
  sets none; the local executor runs the runner with --local-worker; a batch node keeps the scheduler's wall time.
- check_diagram_sources.py --no-mermaid starts no Mermaid CLI (and so no headless browser).
- the CERN EOS storage note says to ask before writing to EOS.
Before the fix a local worker had no time limit, the Mermaid CLI always ran when installed, and the note had no rule."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import engine, runner
from core.partition.executors import LocalExecutor

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "core" / "partition" / "runner.py"
DIAGRAMS = ROOT / "skills" / "hep-communication" / "scripts" / "check_diagram_sources.py"


class LocalWorkerTimeout(unittest.TestCase):
    def spec(self, d: Path, cmd: str, **extra) -> Path:
        p = d / "spec.json"
        p.write_text(json.dumps({"manifest": engine.make_manifest("f13", 2, 2, 5), "cmd": cmd, **extra}))
        return p

    def run_runner(self, d, spec, *extra):
        res = subprocess.run([sys.executable, str(RUNNER), "--spec", str(spec), "--out-dir", str(d / "out"), "--chunk",
                              "c0000", "--attempt", "c0000-a01", *extra], capture_output=True, text=True, timeout=120)
        metas = sorted((d / "out").glob("*.meta.json"))
        return res.returncode, json.loads(metas[-1].read_text())

    def test_local_runner_has_a_default_timeout(self):
        self.assertGreater(runner.DEFAULT_LOCAL_WORKER_TIMEOUT_S, 0)
        ok = f"{sys.executable} -c \"import json,sys; json.dump(dict(), open(sys.argv[1], 'w'))\" {{out}}"
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            code, meta = self.run_runner(d, self.spec(d, ok), "--local-worker")
            self.assertEqual(code, 0, meta)
            self.assertEqual((meta["worker_timeout_s"], meta["worker_timeout_source"]),
                             (runner.DEFAULT_LOCAL_WORKER_TIMEOUT_S, "default for a local worker"))
        with tempfile.TemporaryDirectory() as td:     # a batch node: no default, the scheduler's wall time applies
            d = Path(td)
            code, meta = self.run_runner(d, self.spec(d, ok))
            self.assertEqual((meta["worker_timeout_s"], meta["worker_timeout_source"]), (None, "none (batch node)"))

    def test_spec_timeout_wins_and_stops_a_slow_worker(self):
        slow = f"{sys.executable} -c \"import time; time.sleep(30)\" {{out}}"
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            code, meta = self.run_runner(d, self.spec(d, slow, worker_timeout_s=1), "--local-worker")
            self.assertEqual(code, 124)
            self.assertEqual((meta["worker_timeout_s"], meta["worker_timeout_source"]), (1, "spec"))
            self.assertIn("worker_timeout_s", meta["runner_error"])

    def test_local_executor_passes_local(self):
        ctx = {"runner": "runner.py", "spec": "spec.json", "outputs_dir": "out", "submission_id": "s1",
               "submission_dir": "sub", "rows": [{"chunk_id": "c0000", "attempt_id": "c0000-a01", "index": 0}]}
        self.assertIn("--local-worker", LocalExecutor().prepare(ctx)["argv"][0])


class NoMermaid(unittest.TestCase):
    def test_no_mermaid_starts_no_mermaid_cli(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            marker = d / "mmdc-was-run"
            fake = d / "bin" / "mmdc"
            fake.parent.mkdir()
            fake.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            md = d / "doc.md"
            md.write_text("```mermaid\nflowchart LR\n  A --> B\n```\n")
            env = dict(os.environ, PATH=f"{fake.parent}{os.pathsep}{os.environ.get('PATH', '')}")
            res = subprocess.run([sys.executable, "-I", str(DIAGRAMS), str(md), "--format", "json", "--no-mermaid"],
                                 capture_output=True, text=True, timeout=300, env=env)
            self.assertFalse(marker.exists(), "the Mermaid CLI was started despite --no-mermaid")
            rep = json.loads(res.stdout)
            self.assertIn("--no-mermaid", json.dumps(rep["renderers"]["mmdc"]))
            subprocess.run([sys.executable, "-I", str(DIAGRAMS), str(md), "--format", "json"], capture_output=True,
                           text=True, timeout=300, env=env)
            self.assertTrue(marker.exists(), "control: without the flag the fake Mermaid CLI runs")

    def test_network_use_is_documented(self):
        doc = DIAGRAMS.read_text(encoding="utf-8").split('"""')[1]
        self.assertIn("--no-mermaid", doc)
        self.assertIn("network", doc)


class EosWriteRule(unittest.TestCase):
    def test_note_says_to_ask_before_writing(self):
        note = " ".join((ROOT / "skills/hep-computing/references/storage-cern-eos.md").read_text().split())
        self.assertRegex(note, r"[Aa]sk the user before (any )?(command that )?writes?")


if __name__ == "__main__":
    unittest.main()

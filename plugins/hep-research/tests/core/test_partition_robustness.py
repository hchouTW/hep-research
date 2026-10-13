"""Robustness regressions from the hep-computing remediation (CMP-01, CMP-02) of core/partition/engine.py.

CMP-01: run(), reset() and merge() took no lock: two processes on one state folder raced for state.json and lost
        attempt counts. Now the second gets PartitionError("partition.locked") (CLI: exit 2, JSON error).
CMP-02: _write_atomic had no fsync and left .tmp-* files on failure; a worker result that is not JSON-serializable
        escaped run() as a TypeError, lost the attempt and left a partial .tmp-*.json that merge reported unreadable.
Each test fails on c1d375c. All inputs SYNTHETIC.
"""
import json
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.partition import engine  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "local_partition.py"

SLOW_WORKER = """
import json, sys, time
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
time.sleep(float(a["--sleep"]))
json.dump({"n": int(a["--stop"]) - int(a["--start"])}, open(a["--out"], "w"))
"""


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.state = self.d / "state"
        self.man = engine.make_manifest("rob", 4, 1, 3)


class LockTests(_Base):
    """CMP-01."""

    def hold_lock(self, release: threading.Event, held: threading.Event):
        with engine.dir_lock(self.state, "holder"):
            held.set()
            release.wait(30)

    def test_run_reset_merge_refuse_while_another_thread_holds_the_lock(self):
        release, held = threading.Event(), threading.Event()
        t = threading.Thread(target=self.hold_lock, args=(release, held))
        t.start()
        self.addCleanup(t.join)
        self.addCleanup(release.set)
        self.assertTrue(held.wait(10))
        for call in (lambda: engine.run(self.man, self.state, lambda ch: {"n": 1}),
                     lambda: engine.reset(self.state, [], "x"),
                     lambda: engine.merge(self.man, self.state)):
            with self.assertRaises(engine.PartitionError) as err:
                call()
            self.assertEqual(err.exception.code, "partition.locked")
            self.assertIn("holder", str(err.exception))
        # status only reads: no lock, no error
        self.assertFalse(engine.status(self.man, self.state)["complete"])
        release.set()
        t.join()
        self.assertTrue(engine.run(self.man, self.state, lambda ch: {"n": 1})["complete"])  # free again

    def test_the_lock_is_reentrant_in_one_thread(self):
        with engine.dir_lock(self.state, "outer"):
            engine.run(self.man, self.state, lambda ch: {"n": 1})
            self.assertEqual(engine.merge(self.man, self.state)["merged"], {"n": 4})
            self.assertIn("outer", (self.state / ".lock").read_text())

    def test_two_concurrent_cli_runs_one_refused(self):
        (self.d / "w.py").write_text(SLOW_WORKER)
        man = self.d / "m.json"
        man.write_text(json.dumps(self.man))
        q = shlex.quote
        cmd = f"{q(sys.executable)} {q(str(self.d / 'w.py'))} --start {{start}} --stop {{stop}} --out {{out}} --sleep 0.5"
        argv = [sys.executable, str(SCRIPT), "run", "--manifest", str(man), "--state", str(self.state), "--cmd", cmd]
        first = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 30
        while time.time() < deadline and not ((self.state / ".lock").exists() and (self.state / ".lock").read_text()):
            time.sleep(0.05)
        second = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        out1, err1 = first.communicate(timeout=120)
        self.assertEqual(first.returncode, 0, err1)
        self.assertEqual(second.returncode, 2, second.stderr)
        self.assertNotIn("Traceback", second.stderr)
        doc = json.loads(second.stdout)
        self.assertEqual(doc["code"], "partition.locked")
        state = json.loads((self.state / "state.json").read_text())
        self.assertEqual({c: s["attempts"] for c, s in state["chunks"].items()}, {c["id"]: 1 for c in self.man["chunks"]})


if __name__ == "__main__":
    unittest.main()

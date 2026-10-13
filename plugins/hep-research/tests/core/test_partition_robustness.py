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


class AtomicWriteTests(_Base):
    """CMP-02 and Q5."""

    def tmp_files(self):
        return sorted(str(f.relative_to(self.d)) for f in self.d.rglob(".tmp-*"))

    def test_unserializable_result_is_a_failed_attempt_and_the_run_goes_on(self):
        def worker(ch):
            return {1, 2} if ch["id"] == "c0001" else {"n": 1}
        res = engine.run(self.man, self.state, worker, {"max_attempts": 3})
        st = json.loads((self.state / "state.json").read_text())["chunks"]
        self.assertEqual(st["c0001"]["signatures"], ["unserializable-result", "unserializable-result"])
        self.assertEqual(st["c0001"]["attempts"], 2)  # two identical signatures stop the chunk
        self.assertEqual(st["c0001"]["status"], "stopped-repeated-failure")
        self.assertEqual([c for c, s in st.items() if s["status"] == "done"], ["c0000", "c0002", "c0003"])
        self.assertEqual(res["not_done"], ["c0001"])
        self.assertEqual(self.tmp_files(), [])
        m = engine.merge(self.man, self.state)
        self.assertNotIn("merge.unreadable", [p["code"] for p in m["problems"]])

    def test_failed_write_removes_its_temporary_file(self):
        target = self.d / "out" / "x.json"
        with self.assertRaises(TypeError):
            engine._write_atomic(target, {"a": object()})
        self.assertFalse(target.exists())
        self.assertEqual(self.tmp_files(), [])
        orig = engine.os.replace

        def boom(a, b):
            raise OSError("synthetic rename failure")
        engine.os.replace = boom
        try:
            with self.assertRaises(OSError):
                engine._write_atomic(target, {"a": 1})
        finally:
            engine.os.replace = orig
        self.assertEqual(self.tmp_files(), [])

    def test_write_is_fsynced(self):
        calls = []
        orig = engine.os.fsync
        engine.os.fsync = lambda fd: calls.append(fd) or orig(fd)
        try:
            engine._write_atomic(self.d / "y.json", {"a": 1})
        finally:
            engine.os.fsync = orig
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads((self.d / "y.json").read_text()), {"a": 1})

    def test_merge_ignores_leftover_temporary_files(self):
        engine.run(self.man, self.state, lambda ch: {"n": 1})
        (self.state / "chunks" / ".tmp-abc.json").write_text('{"partial": ')
        m = engine.merge(self.man, self.state)
        self.assertEqual(m["status"], "complete")
        self.assertEqual(m["problems"], [])

    def test_attempts_exhausted_on_the_call_that_used_the_last_attempt(self):
        n = {"k": 0}

        def worker(ch):
            n["k"] += 1
            raise (RuntimeError, OSError)[n["k"] % 2](f"boom {ch['id']}")
        engine.run(self.man, self.state, worker, {"max_attempts": 2})
        st = json.loads((self.state / "state.json").read_text())["chunks"]
        self.assertEqual({s["status"] for s in st.values()}, {"attempts-exhausted"})
        self.assertEqual({s["attempts"] for s in st.values()}, {2})


if __name__ == "__main__":
    unittest.main()

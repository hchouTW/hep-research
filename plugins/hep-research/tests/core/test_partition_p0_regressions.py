"""P0 regressions from the hep-computing audit (2026-10-13) of core/partition/engine.py.

F01: max_attempts bounded the attempts of one run() call, not of the chunk: rerunning bought new attempts
     (max_attempts=3 gave 3, 6, 9, 12 attempts over four calls), and the 'two identical failures stop' rule compared
     raw error texts, so a varying temporary path or timestamp in the message never stopped the chunk.
F02: merge() took chunk files in filename order and kept the first file claiming a chunk: a stray 'b_c0000.json' with a
     different result replaced the real 'c0000.json' and the merge still reported 'complete'. Non-object or
     incomplete chunk files crashed the merge with a traceback.
Each test fails on the audited code and states the behavior that is now required. All inputs SYNTHETIC.
"""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.partition import engine  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "local_partition.py"


class _Counter:
    """A worker that always fails, with a message that differs on every call (attempt number, temp path)."""

    def __init__(self, exc_type=RuntimeError):
        self.calls = 0
        self.exc_type = exc_type

    def __call__(self, ch):
        self.calls += 1
        raise self.exc_type(f"attempt {self.calls}: cannot open /tmp/tmpab{self.calls:04d}xy/out.json at 12:00:{self.calls:02d}")


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.state = self.d / "state"
        self.man = engine.make_manifest("p0", 4, 2, 7)


class RetryBoundAcrossRunsTests(_Base):
    """F01."""

    def test_max_attempts_is_a_total_over_runs(self):
        calls = {"n": 0}

        def worker(ch):
            if ch["id"] == "c0000":
                return {"n": 2}
            calls["n"] += 1
            # a different exception type each time: the repeated-failure stop never triggers, only the cap can stop it
            raise (RuntimeError, OSError, ValueError, KeyError, TypeError)[calls["n"] % 5]("boom")

        cfg = {"max_attempts": 3}
        for _ in range(4):
            res = engine.run(self.man, self.state, worker, cfg)
        self.assertEqual(calls["n"], 3, "four run() calls must not exceed max_attempts=3 attempts in total")
        row = res["chunks"]["c0001"]
        self.assertEqual(row["attempts"], 3)
        self.assertEqual(row["status"], "attempts-exhausted")
        self.assertEqual(res["invocations"], [], "the fourth call has nothing left to try")
        self.assertFalse(res["complete"])

    def test_default_is_one_attempt_in_total(self):
        w = _Counter()
        engine.run(self.man, self.state, w)
        engine.run(self.man, self.state, w)
        self.assertEqual(w.calls, 2, "one attempt per chunk in total (two chunks), not one per call")

    def test_varying_message_still_stops_after_two_identical_failures(self):
        w = _Counter()
        res = engine.run(self.man, self.state, w, {"max_attempts": 10})
        for cid in ("c0000", "c0001"):
            self.assertEqual(res["chunks"][cid]["status"], "stopped-repeated-failure")
            self.assertEqual(res["chunks"][cid]["attempts"], 2)
        self.assertEqual(w.calls, 4)

    def test_explicit_signature_is_used(self):
        class Fail(RuntimeError):
            signature = "exit=3"

        n = {"i": 0}

        def worker(ch):
            n["i"] += 1
            raise Fail(f"different text {n['i']} {'x' * n['i']}")

        res = engine.run(engine.make_manifest("s", 1, 1, 1), self.state, worker, {"max_attempts": 9})
        self.assertEqual(res["chunks"]["c0000"]["status"], "stopped-repeated-failure")
        self.assertEqual(n["i"], 2)

    def test_reset_restores_the_budget_and_keeps_history(self):
        w = _Counter()
        engine.run(self.man, self.state, w, {"max_attempts": 1})
        engine.reset(self.state, ["c0000"], "fixed input path")
        res = engine.run(self.man, self.state, lambda ch: {"n": 2}, {"max_attempts": 1})
        self.assertEqual(res["chunks"]["c0000"]["status"], "done")
        self.assertEqual(res["chunks"]["c0001"]["status"], "attempts-exhausted")
        state = json.loads((self.state / "state.json").read_text())
        self.assertEqual(state["chunks"]["c0000"]["attempts"], 2, "the lifetime count is kept")
        self.assertEqual(state["resets"][0]["reason"], "fixed input path")

    def test_state_from_before_the_fix_counts_all_attempts(self):
        self.state.mkdir()
        legacy = {"manifest_hash": self.man["manifest_hash"], "chunks": {
            "c0000": {"attempts": 3, "errors": ["RuntimeError: a", "OSError: b", "ValueError: c"], "status": "failed"}}}
        (self.state / "state.json").write_text(json.dumps(legacy))
        w = _Counter()
        res = engine.run(self.man, self.state, w, {"max_attempts": 3})
        self.assertEqual(res["chunks"]["c0000"]["status"], "attempts-exhausted")
        self.assertNotIn("c0000", res["invocations"])

    def test_max_attempts_must_be_a_positive_integer(self):
        for bad in (0, -1, 2.7, True, "3", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                engine.run(self.man, self.state, lambda ch: {"n": 1}, {"max_attempts": bad})

    def test_signature_masks_paths_numbers_and_hex(self):
        a = engine.failure_signature(OSError("open /scratch/job_123/tmpk3j/out.json failed at 2026-10-13T08:00:01 id deadbeef01"))
        b = engine.failure_signature(OSError("open /scratch/job_999/tmpzz/out.json failed at 2026-10-14T09:11:59 id 0123abcd99"))
        self.assertEqual(a, b)
        self.assertNotEqual(engine.failure_signature(OSError("x")), engine.failure_signature(ValueError("x")))


class CliWorkerSignatureTests(_Base):
    """F01 through the CLI: a command that exits 0 without writing {out} used to fail with the random temp path in the
    message, so the repeated-failure rule never fired."""

    def test_missing_output_stops_after_two(self):
        man = self.d / "manifest.json"
        man.write_text(json.dumps(engine.make_manifest("cli", 2, 1, 1)))
        cfg = self.d / "cfg.json"
        cfg.write_text(json.dumps({"max_attempts": 5}))
        cmd = f"{shlex.quote(sys.executable)} -c pass --out {{out}}"
        p = subprocess.run([sys.executable, str(SCRIPT), "run", "--manifest", str(man), "--state", str(self.state),
                            "--cmd", cmd, "--config", str(cfg)], capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 1, p.stderr)
        out = json.loads(p.stdout)
        for cid in ("c0000", "c0001"):
            self.assertEqual(out["chunks"][cid]["status"], "stopped-repeated-failure")
            self.assertEqual(out["chunks"][cid]["attempts"], 2)


class MergeDuplicateTests(_Base):
    """F02."""

    def setUp(self):
        super().setUp()
        engine.run(self.man, self.state, lambda ch: {"n": ch["stop"] - ch["start"]})
        self.cdir = self.state / "chunks"

    def _stray(self, name, **changes):
        doc = json.loads((self.cdir / "c0000.json").read_text())
        doc.update(changes)
        (self.cdir / name).write_text(json.dumps(doc))

    def codes(self, res):
        return [p["code"] for p in res["problems"]]

    def test_conflicting_stray_never_replaces_the_chunk(self):
        self._stray("b_c0000.json", result={"n": 999})  # sorts before c0000.json
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "incomplete")
        self.assertIsNone(res["merged"])
        self.assertIn("merge.conflicting_duplicate", self.codes(res))

    def test_identical_stray_is_reported_not_counted(self):
        self._stray("b_c0000.json")
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "complete")
        self.assertEqual(res["merged"], {"n": 4})
        self.assertIn("merge.duplicate_chunk", self.codes(res))

    def test_stray_cannot_stand_in_for_a_missing_chunk(self):
        self._stray("copy.json")
        (self.cdir / "c0000.json").unlink()
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "incomplete")
        self.assertIn("merge.missing_chunks", self.codes(res))

    def test_wrong_chunk_id_in_canonical_file(self):
        doc = json.loads((self.cdir / "c0001.json").read_text())
        (self.cdir / "c0000.json").write_text(json.dumps(dict(doc, start=0, stop=2)))
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "incomplete")
        self.assertIn("merge.id_mismatch", self.codes(res))

    def test_seed_mismatch(self):
        doc = json.loads((self.cdir / "c0000.json").read_text())
        (self.cdir / "c0000.json").write_text(json.dumps(dict(doc, seed=doc["seed"] + 1)))
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "incomplete")
        self.assertIn("merge.seed_mismatch", self.codes(res))

    def test_malformed_files_are_reported_not_crashing(self):
        (self.cdir / "list.json").write_text("[1, 2]")
        (self.cdir / "partial.json").write_text(json.dumps({"chunk_id": "c0000"}))
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "complete")
        self.assertEqual(self.codes(res).count("merge.unreadable"), 2)
        (self.cdir / "c0001.json").write_text("[]")
        res = engine.merge(self.man, self.state)
        self.assertEqual(res["status"], "incomplete")
        self.assertIn("merge.missing_chunks", self.codes(res))


if __name__ == "__main__":
    unittest.main()

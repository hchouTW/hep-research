"""B02: remote chunk protocol: worker-side runner, collection, duplicate safety, quarantine."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import campaign as cp
from tests.core.partition_helpers import ScriptedExecutor, make_campaign, run_runner, single_run


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cdir, self.manifest, _ = make_campaign(Path(self.tmp.name))

    def runner(self, *a):
        return subprocess.run([sys.executable, str(self.cdir / "runner.py"), "--spec", str(self.cdir / "spec.json"), *a],
                              capture_output=True, text=True, timeout=600)

    def test_seed_comes_from_the_manifest_via_the_map(self):
        m = self.cdir / "map.json"
        m.write_text(json.dumps([{"index": 0, "chunk_id": "c0002", "attempt_id": "c0002-a01"}]))
        out = self.cdir / "outputs" / "c0002"
        p = self.runner("--out-dir", str(out), "--map", str(m), "--index", "0")
        self.assertEqual(p.returncode, 0, p.stderr)
        doc = json.loads((out / "c0002-a01.json").read_text())
        chunk = self.manifest["chunks"][2]
        self.assertEqual((doc["seed"], doc["result"]["seed_echo"], doc["start"]), (chunk["seed"], chunk["seed"], chunk["start"]))
        meta = json.loads((out / "c0002-a01.meta.json").read_text())
        for k in ("chunk_id", "manifest_hash", "attempt_id", "host", "start_time", "end_time", "exit_code", "python"):
            self.assertIn(k, meta)
        self.assertEqual(meta["exit_code"], 0)

    def test_second_execution_never_overwrites(self):
        out = self.cdir / "outputs" / "c0000"
        for _ in range(2):
            self.assertEqual(run_runner(self.cdir, "c0000", "c0000-a01"), 0)
        names = sorted(p.name for p in out.iterdir())
        self.assertEqual(names, ["c0000-a01.json", "c0000-a01.meta.json", "c0000-a01.rerun-1.json", "c0000-a01.rerun-1.meta.json"])

    def test_bad_arguments_and_unknown_chunk(self):
        self.assertEqual(self.runner("--out-dir", str(self.cdir), "--chunk", "c9999", "--attempt", "x").returncode, 2)
        self.assertEqual(self.runner("--out-dir", str(self.cdir)).returncode, 2)

    def test_failed_command_leaves_only_meta(self):
        spec = json.loads((self.cdir / "spec.json").read_text())
        spec["cmd"] = f"{sys.executable} -c \"import sys; sys.exit(3)\""
        (self.cdir / "spec.json").write_text(json.dumps(spec))
        out = self.cdir / "outputs" / "c0001"
        self.assertEqual(run_runner(self.cdir, "c0001", "c0001-a01"), 3)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["c0001-a01.meta.json"])
        self.assertEqual(json.loads((out / "c0001-a01.meta.json").read_text())["exit_code"], 3)

    def test_missing_result_is_a_runner_error(self):
        spec = json.loads((self.cdir / "spec.json").read_text())
        spec["cmd"] = f"{sys.executable} -c pass"
        (self.cdir / "spec.json").write_text(json.dumps(spec))
        self.assertEqual(run_runner(self.cdir, "c0001", "c0001-a01"), 70)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cdir, self.manifest, _ = make_campaign(Path(self.tmp.name))

    def test_double_run_is_one_duplicate_and_merge_equals_single_run(self):
        ex = ScriptedExecutor({"c0001": [{"state": "done", "twice": True}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        rep = cp.poll(self.cdir, ex)
        self.assertTrue(rep["complete"])
        self.assertEqual(rep["duplicates"], 1)
        _, state = cp.load(self.cdir)
        self.assertEqual(state["duplicates"][0]["file"], "outputs/c0001/c0001-a01.rerun-1.json")
        self.assertTrue(state["duplicates"][0]["identical_result"])
        self.assertEqual(state["duplicates"][0]["kept"], "c0001-a01")
        merged = cp.merge(self.cdir)
        self.assertEqual(merged["status"], "complete")
        self.assertEqual(merged["merged"], single_run(self.manifest, None))

    def test_late_original_after_resubmission_is_a_duplicate(self):
        ex = ScriptedExecutor({"c0000": [{"state": "preempted-or-evicted"}], "c0001": [{"state": "done"}], "c0002": [{"state": "done"}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        cp.poll(self.cdir, ex)
        ex.script["c0000"] = [{"state": "done"}]
        cp.resubmit(self.cdir, ex, {"max_attempts": 3}, approved=True)
        cp.poll(self.cdir, ex)
        run_runner(self.cdir, "c0000", "c0000-a01")  # the preempted original turns up later
        col = cp.collect(self.cdir)
        self.assertEqual([d["file"] for d in col["duplicates"]], ["outputs/c0000/c0000-a01.json"])
        self.assertEqual(json.loads((self.cdir / "chunks" / "c0000.json").read_text())["attempt_id"], "c0000-a02")
        self.assertEqual(cp.merge(self.cdir)["merged"], single_run(self.manifest, None))

    def test_foreign_output_is_quarantined_and_merge_stays_incomplete(self):
        ex = ScriptedExecutor({"c0002": [{"state": "done", "write": False}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        out = self.cdir / "outputs" / "c0002" / "c0002-a01.json"
        out.write_text(json.dumps({"chunk_id": "c0002", "manifest_hash": "f" * 64, "attempt_id": "c0002-a01", "start": 8,
                                   "stop": 10, "seed": self.manifest["chunks"][2]["seed"], "result": {"n": 2}}))
        rep = cp.poll(self.cdir, ex)
        self.assertEqual(rep["chunks"]["c0002"]["status"], "lost")
        self.assertTrue((self.cdir / "quarantine" / "c0002" / "c0002-a01.json").exists())
        _, state = cp.load(self.cdir)
        self.assertIn("another manifest", state["quarantine"][0]["reason"])
        self.assertEqual(cp.merge(self.cdir)["status"], "incomplete")
        ex.script["c0002"] = [{"state": "done"}]
        cp.resubmit(self.cdir, ex, {"max_attempts": 2}, approved=True)
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])
        self.assertEqual(cp.merge(self.cdir)["status"], "complete")

    def test_partial_files_are_never_collected(self):
        ex = ScriptedExecutor({"c0000": [{"state": "running"}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        d = self.cdir / "outputs" / "c0000"
        (d / ".tmp-abc.json").write_text('{"chunk_id": "c0000"')   # a write that never got renamed
        (d / "c0000-a01.json").write_text('{"chunk_id": "c0000", "manif')  # truncated in place
        rep = cp.poll(self.cdir, ex)
        self.assertEqual(rep["chunks"]["c0000"]["status"], "running")
        self.assertFalse((self.cdir / "chunks" / "c0000.json").exists())
        _, state = cp.load(self.cdir)
        self.assertEqual([q["file"] for q in state["quarantine"]], ["outputs/c0000/c0000-a01.json"])
        self.assertTrue(state["quarantine"][0]["reason"].startswith("unreadable"))
        self.assertTrue((d / ".tmp-abc.json").exists())

    def test_non_finite_and_unsubmitted_attempts_are_quarantined(self):
        ex = ScriptedExecutor({"c0000": [{"state": "running"}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        d = self.cdir / "outputs" / "c0000"
        c = self.manifest["chunks"][0]
        base = {"chunk_id": "c0000", "manifest_hash": self.manifest["manifest_hash"], "start": c["start"], "stop": c["stop"], "seed": c["seed"]}
        (d / "c0000-a01.json").write_text(json.dumps(dict(base, attempt_id="c0000-a01", result={"x": float("nan")})))
        (d / "c0000-a07.json").write_text(json.dumps(dict(base, attempt_id="c0000-a07", result={"x": 1})))
        cp.collect(self.cdir)
        _, state = cp.load(self.cdir)
        reasons = sorted(q["reason"] for q in state["quarantine"])
        self.assertIn("non-finite", reasons[1])
        self.assertIn("never submitted", reasons[0])
        self.assertFalse((self.cdir / "chunks" / "c0000.json").exists())

    def test_collected_output_is_write_once(self):
        ex = ScriptedExecutor({})
        cp.submit(self.cdir, ex, {}, approved=True)
        cp.poll(self.cdir, ex)
        before = (self.cdir / "chunks" / "c0000.json").read_bytes()
        run_runner(self.cdir, "c0000", "c0000-a01")
        cp.collect(self.cdir)
        self.assertEqual(before, (self.cdir / "chunks" / "c0000.json").read_bytes())


if __name__ == "__main__":
    unittest.main()

"""B01: core/partition engine and executor interface (the local executor runs through the batch protocol)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import campaign as cp
from core.partition import engine
from core.partition.executors import Executor, LocalExecutor
from tests.core.partition_helpers import make_campaign, single_run

ROOT = Path(__file__).resolve().parents[2]


class EngineMoveTests(unittest.TestCase):
    def test_cli_module_reexports_the_core_engine(self):
        sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
        import local_partition as lp
        for name in ("make_manifest", "run", "status", "reset", "merge"):
            self.assertIs(getattr(lp, name), getattr(engine, name))

    def test_owner_lists_both_consumers(self):
        owners = json.loads((ROOT / "core" / "OWNERS.json").read_text())["modules"]["partition"]
        self.assertEqual(owners["steward"], "hep-computing")
        self.assertEqual(len(owners["consumers"]), 2)


class LocalExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cdir, self.manifest, self.cmd = make_campaign(Path(self.tmp.name))

    def test_interface_methods_exist(self):
        for m in ("prepare", "submit", "poll", "cancel", "version"):
            self.assertTrue(callable(getattr(Executor, m)))

    def test_prepare_is_pure(self):
        before = sorted(p.relative_to(self.cdir) for p in self.cdir.rglob("*"))
        ctx = {"campaign_dir": self.cdir, "submission_id": "s001", "submission_dir": self.cdir / "submissions" / "s001",
               "rows": [{"index": 0, "chunk_id": "c0000", "attempt_id": "c0000-a01"}], "config": {},
               "spec": self.cdir / "spec.json", "runner": self.cdir / "runner.py", "outputs_dir": self.cdir / "outputs"}
        plan = LocalExecutor().prepare(ctx)
        self.assertIn("commands.json", plan["files"])
        self.assertEqual(before, sorted(p.relative_to(self.cdir) for p in self.cdir.rglob("*")))

    def test_dry_run_starts_nothing(self):
        rep = cp.submit(self.cdir, LocalExecutor(), {})
        self.assertTrue(rep["dry_run"])
        self.assertEqual(list((self.cdir / "outputs").iterdir()), [])
        _, state = cp.load(self.cdir)
        self.assertEqual(state["submissions"], [])

    def test_local_campaign_merges_like_a_single_run(self):
        ex = LocalExecutor()
        cp.submit(self.cdir, ex, {}, approved=True)
        rep = cp.poll(self.cdir, ex)
        self.assertTrue(rep["complete"], rep)
        merged = cp.merge(self.cdir)
        self.assertEqual(merged["status"], "complete")
        self.assertEqual(merged["merged"], single_run(self.manifest, None))
        _, state = cp.load(self.cdir)
        rec = state["chunks"]["c0001"]["attempt_records"][0]
        for k in ("attempt_id", "backend", "job_id", "submit_time", "final_state"):
            self.assertIn(k, rec)
        self.assertEqual(rec["final_state"], "done")

    def test_submit_twice_does_not_rerun_chunks(self):
        ex = LocalExecutor()
        cp.submit(self.cdir, ex, {}, approved=True)
        self.assertEqual(cp.submit(self.cdir, ex, {}, approved=True)["submitted"], [])
        with self.assertRaises(cp.CampaignError):
            cp.submit(self.cdir, ex, {}, chunk_ids=["c0000"], approved=True)

    def test_state_without_attempt_records_still_reads(self):
        state = json.loads((self.cdir / "state.json").read_text())
        state["chunks"] = {"c0000": {"attempts": 1, "errors": [], "status": "failed"}}  # pre-B01 row shape
        (self.cdir / "state.json").write_text(json.dumps(state))
        rep = cp.report(self.cdir)
        self.assertEqual(rep["chunks"]["c0000"]["status"], "planned")
        self.assertFalse(rep["complete"])

    def test_other_manifest_refused(self):
        with self.assertRaises(cp.CampaignError):
            cp.init(self.cdir, engine.make_manifest("other", 10, 4, 8), self.cmd)


if __name__ == "__main__":
    unittest.main()

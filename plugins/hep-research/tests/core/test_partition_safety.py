"""Campaign safety (T15): an intent record written before the scheduler call, recovery after an interrupted submit,
a lock against concurrent invocations, no silent string merges, and no non-finite merged results. Uses the scripted
fake scheduler from partition_helpers; nothing reaches a real scheduler."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from core.partition import campaign as cp
from core.partition import engine
from tests.core.partition_helpers import ScriptedExecutor, make_campaign, single_run

CONFIG = {"max_attempts": 2, "resources": {"time": "00:10:00"}}


class Interrupted(BaseException):
    """Stands in for a kill or Ctrl-C after the scheduler accepted the jobs but before the campaign saved them."""


class InterruptingExecutor(ScriptedExecutor):
    def submit(self, plan):
        self.accepted = super().submit(plan)  # the scheduler now has the jobs
        raise Interrupted()


class RefusingExecutor(ScriptedExecutor):
    def submit(self, plan):
        raise RuntimeError("sbatch: error: invalid partition")


class SlowExecutor(ScriptedExecutor):
    def submit(self, plan):
        time.sleep(0.5)
        return super().submit(plan)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cdir, self.manifest, _ = make_campaign(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return json.loads((self.cdir / "state.json").read_text())

    def test_an_interrupted_submit_leaves_a_recoverable_intent_record(self):
        ex = InterruptingExecutor({})
        with self.assertRaises(Interrupted):
            cp.submit(self.cdir, ex, CONFIG, approved=True)
        state = self.state()
        sub = state["submissions"][-1]
        self.assertEqual(sub["status"], "intent")
        recs = [r for row in state["chunks"].values() for r in row["attempt_records"]]
        self.assertEqual({r["state"] for r in recs}, {"submitting"})
        self.assertTrue(all(r["job_id"] is None for r in recs))
        # nothing is submitted twice, and a watch stops for a person
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(self.cdir, ScriptedExecutor({}), CONFIG, approved=True)
        self.assertEqual(err.exception.code, "submit.unconfirmed")
        self.assertEqual(cp.report(self.cdir)["chunks"]["c0000"]["status"], "submitting")
        self.assertEqual(ex.calls, [("submit", [c["id"] for c in self.manifest["chunks"]])])
        # the person finds the jobs at the scheduler and confirms them; the campaign then completes normally
        with self.assertRaises(cp.CampaignError):
            cp.confirm_submission(self.cdir, sub["id"], {"c0000-a01": "x"})  # every attempt needs its job
        cp.confirm_submission(self.cdir, sub["id"], {j["attempt_id"]: j["job_id"] for j in ex.accepted})
        rep = cp.poll(self.cdir, ex)
        self.assertTrue(rep["complete"], rep["not_done"])
        merged = cp.merge(self.cdir)
        self.assertEqual(merged["merged"], single_run(self.manifest, None))

    def test_an_abandoned_submission_needs_a_reset_to_run_again(self):
        with self.assertRaises(Interrupted):
            cp.submit(self.cdir, InterruptingExecutor({}), CONFIG, approved=True)
        sid = self.state()["submissions"][-1]["id"]
        with self.assertRaises(cp.CampaignError):
            cp.abandon_submission(self.cdir, sid, " ")
        cp.abandon_submission(self.cdir, sid, "no jobs from this submission at the scheduler")
        statuses = {c["status"] for c in cp.report(self.cdir)["chunks"].values()}
        self.assertEqual(statuses, {"not-submitted"})
        ids = [c["id"] for c in self.manifest["chunks"]]
        cp.reset(self.cdir, ids, "abandoned after an interrupted submit")
        ex = ScriptedExecutor({})
        rep = cp.resubmit(self.cdir, ex, CONFIG, approved=True)
        self.assertEqual(sorted(rep["resubmitted"]), ids)
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])

    def test_a_refused_submission_is_recorded_as_not_submitted(self):
        with self.assertRaises(RuntimeError):
            cp.submit(self.cdir, RefusingExecutor({}), CONFIG, approved=True)
        state = self.state()
        self.assertEqual(state["submissions"][-1]["status"], "not-submitted")
        self.assertIn("invalid partition", state["submissions"][-1]["reason"])
        self.assertEqual({c["status"] for c in cp.report(self.cdir)["chunks"].values()}, {"not-submitted"})

    def test_concurrent_submits_cannot_both_run(self):
        results, errors = [], []

        def go():
            try:
                results.append(cp.submit(self.cdir, SlowExecutor({}), CONFIG, approved=True))
            except cp.CampaignError as exc:
                errors.append(exc.code)

        threads = [threading.Thread(target=go) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 1)
        self.assertEqual(errors, ["campaign.locked"])
        self.assertEqual([s["id"] for s in self.state()["submissions"]], ["s001"])

    def test_the_lock_is_released_and_reentrant(self):
        with cp.campaign_lock(self.cdir, "outer"):
            with cp.campaign_lock(self.cdir, "inner"):  # the same thread may nest (resubmit calls submit)
                pass
            self.assertIn("outer", (self.cdir / ".lock").read_text())
        cp.submit(self.cdir, ScriptedExecutor({}), CONFIG, approved=True)  # free again


class MergeGuardTests(unittest.TestCase):
    def run_chunks(self, td, results):
        manifest = engine.make_manifest("guard", len(results), 1, 1)
        it = iter(results)
        engine.run(manifest, td, lambda ch: next(it))
        return engine.merge(manifest, td)

    def test_strings_are_not_concatenated(self):
        with tempfile.TemporaryDirectory() as td:
            out = self.run_chunks(td, [{"label": "a", "n": 1}, {"label": "b", "n": 2}])
        self.assertEqual(out["status"], "incomplete")
        self.assertIsNone(out["merged"])
        self.assertIn("merge.combine_failed", {p["code"] for p in out["problems"]})
        with tempfile.TemporaryDirectory() as td:  # a combine function may handle them
            manifest = engine.make_manifest("guard", 2, 1, 1)
            engine.run(manifest, td, lambda ch: {"label": ch["id"]})
            out = engine.merge(manifest, td, combine=lambda rs: "+".join(r["label"] for r in rs))
        self.assertEqual(out["merged"], "c0000+c0001")

    def test_non_finite_results_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out = self.run_chunks(td, [{"x": 1.0}, {"x": float("nan")}, {"x": 2.0}])
        self.assertEqual(out["status"], "incomplete")
        self.assertIsNone(out["merged"])
        self.assertTrue(any(p["code"] == "merge.non_finite" and "result.x" in p["message"] for p in out["problems"]))
        with tempfile.TemporaryDirectory() as td:
            out = self.run_chunks(td, [{"x": 1e308}, {"x": 1e308}])  # finite parts, an infinite sum
        self.assertIn("merged.x is not finite after combining", " ".join(p.get("message", "") for p in out["problems"]))


if __name__ == "__main__":
    unittest.main()

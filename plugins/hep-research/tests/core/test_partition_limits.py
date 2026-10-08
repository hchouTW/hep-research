"""T3.4: global attempt identity, campaign limits (unknown and orphan-risk jobs count as used), reset caps (X08), and
cancellation that records exits, targets orphans through the submission tag and confirms termination only by a poll
(X09). Scripted fake scheduler only; nothing reaches a real scheduler."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from core.partition import campaign as cp
from core.partition import limits as lim
from core.partition.executors import LocalExecutor
from core.partition.states import decide
from tests.core.partition_helpers import ScriptedExecutor, make_campaign

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "adapters" / "batch-schedulers"))
import batch_config as bc  # noqa: E402

TL = {"cpus": 2, "time_limit": "01:00:00"}


class Interrupted(BaseException):
    pass


class InterruptingExecutor(ScriptedExecutor):
    def submit(self, plan):
        self.accepted = super().submit(plan)
        raise Interrupted()


class ExitReportingExecutor(ScriptedExecutor):
    """cancel() reports exits like the Slurm and HTCondor backends: a dict per job, in order."""

    def __init__(self, script, exits=None):
        super().__init__(script)
        self.exits = exits or {}

    def cancel(self, records):
        self.calls.append(("cancel", [r["job_id"] for r in records]))
        return [{"argv": ["scancel", r["job_id"]], "exit": self.exits.get(r["job_id"], 0)} for r in records]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cdir, self.manifest, _ = make_campaign(Path(self.tmp.name))
        self.ids = [c["id"] for c in self.manifest["chunks"]]

    def tearDown(self):
        self.tmp.cleanup()

    def state(self):
        return json.loads((self.cdir / "state.json").read_text())

    def refused(self, code, fn, *a, **kw):
        before = (self.cdir / "state.json").read_text()
        with self.assertRaises(cp.CampaignError) as err:
            fn(*a, **kw)
        self.assertEqual(err.exception.code, code)
        self.assertEqual((self.cdir / "state.json").read_text(), before, "a refusal writes nothing")
        return err.exception


class IdentityTests(Base):
    def test_attempts_carry_the_global_identity(self):
        cp.submit(self.cdir, ScriptedExecutor({}), {}, approved=True)
        st = self.state()
        for row in st["chunks"].values():
            for rec in row["attempt_records"]:
                self.assertEqual(rec["global_attempt_id"], f"{st['campaign_uid']}:{rec['attempt_id']}")

    def test_campaign_uids_differ(self):
        other, _, _ = make_campaign(Path(self.tmp.name) / "other")
        self.assertNotEqual(cp.load(self.cdir)[1]["campaign_uid"], cp.load(other)[1]["campaign_uid"])


class LimitTests(Base):
    def test_bad_limits_are_refused(self):
        for bad in ({"max_jobs": 3}, {"max_total_jobs": 0}, {"max_core_hours": -1}, {"max_resets_per_chunk": True}, [1]):
            self.refused("limits.bad_config", cp.submit, self.cdir, ScriptedExecutor({}), {"limits": bad})

    def test_total_jobs_limit_stops_a_submission_before_anything_is_written(self):
        cfg = {"limits": {"max_total_jobs": 2}}
        err = self.refused("limits.exceeded", cp.submit, self.cdir, ScriptedExecutor({}), cfg, approved=True)
        self.assertIn("max_total_jobs: 0 used + 3 new > 2", str(err))
        self.refused("limits.exceeded", cp.submit, self.cdir, ScriptedExecutor({}), cfg)  # the dry run too
        rep = cp.submit(self.cdir, ScriptedExecutor({}), cfg, pilot=True, approved=True)
        self.assertEqual(rep["limits"]["usage_before"]["total_jobs"], 0)

    def test_submissions_limit(self):
        cfg = {"limits": {"max_submissions": 1}}
        cp.submit(self.cdir, ScriptedExecutor({}), cfg, pilot=True, approved=True)
        self.refused("limits.exceeded", cp.submit, self.cdir, ScriptedExecutor({}), cfg, approved=True)

    def test_refused_client_is_not_counted_but_abandoned_jobs_are(self):
        with self.assertRaises(Interrupted):
            cp.submit(self.cdir, InterruptingExecutor({}), {"resources": TL}, approved=True)
        sid = self.state()["submissions"][-1]["id"]
        cp.abandon_submission(self.cdir, sid, "no jobs found at the scheduler")
        use = lim.usage(self.state())
        self.assertEqual((use["submissions"], use["total_jobs"], use["orphan_risk_jobs"]), (1, 3, 3))
        self.assertEqual(use["concurrent_jobs"], 3)  # abandoned jobs may still run: queue time has no bound
        self.assertEqual(use["core_hours"], 3 * 2 * 1.0)  # worst case: cpus x walltime per orphan-risk job
        risks = self.state()["resource_risk"]
        self.assertEqual(sorted(r["kind"] for r in risks), ["abandoned"] * 3)
        self.assertTrue(all(r["global_attempt_id"].endswith(r["attempt_id"]) for r in risks))
        cp.reset(self.cdir, self.ids, "abandoned after an interrupted submit")
        cfg = {"max_attempts": 2, "resources": TL, "limits": {"max_concurrent_jobs": 4}}
        with self.assertRaises(cp.CampaignError) as err:  # resubmission is a submission: the same limits apply
            cp.resubmit(self.cdir, ScriptedExecutor({}), cfg, approved=True)
        self.assertIn("max_concurrent_jobs: 3 used + 3 new > 4", str(err.exception))

    def test_unknown_jobs_count_as_running_without_a_walltime(self):
        ex = ScriptedExecutor({"c0000": [{"state": "unknown"}]})
        cp.submit(self.cdir, ex, {}, ["c0000"], approved=True)
        cp.poll(self.cdir, ex)
        use = lim.usage(self.state())
        self.assertEqual((use["concurrent_jobs"], use["orphan_risk_jobs"], use["core_hours"]), (1, 1, None))
        self.assertEqual([r["kind"] for r in self.state()["resource_risk"]], ["unknown"])
        self.refused("limits.exceeded", cp.submit, self.cdir, ex, {"limits": {"max_concurrent_jobs": 1}}, ["c0001"])

    def test_core_hours_need_a_walltime_bound(self):
        err = self.refused("limits.exceeded", cp.submit, self.cdir, ScriptedExecutor({}), {"limits": {"max_core_hours": 100}})
        self.assertIn("unbounded", str(err))
        cfg = {"resources": TL, "limits": {"max_core_hours": 5}}  # 3 jobs x 2 cpus x 1 h = 6 > 5
        self.refused("limits.exceeded", cp.submit, self.cdir, ScriptedExecutor({}), cfg)
        ex = ScriptedExecutor({"c0000": [{"state": "done", "elapsed_s": 900}]})
        cp.submit(self.cdir, ex, cfg, pilot=True, approved=True)
        cp.poll(self.cdir, ex)
        self.assertAlmostEqual(lim.usage(self.state())["core_hours"], 0.5)  # observed: 2 cpus x 15 min
        self.assertEqual(len(cp.submit(self.cdir, ex, cfg, approved=True)["chunks"]), 2)  # 0.5 + 4 <= 5

    def test_batch_config_validates_limits(self):
        base = {"backend": "slurm", "campaign_dir": "c", "resources": {"time_limit": "00:10:00"}, "slurm": {"partition": "p"}}
        self.assertEqual(bc.validate(dict(base, limits={"max_total_jobs": 10, "max_core_hours": 2.5, "max_resets_per_chunk": 0})), [])
        errs = bc.validate(dict(base, limits={"max_total_jobs": 0, "max_cpus": 1}))
        self.assertEqual(sorted(e["code"] for e in errs), ["config.bad_value", "config.unknown_key"])


class ClearOrphanTests(Base):
    def abandoned(self):
        ex = InterruptingExecutor({})
        with self.assertRaises(Interrupted):
            cp.submit(self.cdir, ex, {"resources": TL}, ["c0000"], approved=True)
        sid = self.state()["submissions"][-1]["id"]
        cp.abandon_submission(self.cdir, sid, "no confirmation")
        return ex, sid

    def test_queued_past_walltime_still_counts_until_cleared_with_evidence(self):
        ex, sid = self.abandoned()
        self.assertEqual(lim.usage(self.state())["concurrent_jobs"], 1)
        ex.by_tag[self.state()["submissions"][-1]["tag"]] = [{"job_id": "j-c0000-a01", "state": "queued"}]
        self.refused("clear.jobs_active", cp.clear_orphan_risk, self.cdir, ex, sid, "checked the queue")
        self.refused("clear.reason_missing", cp.clear_orphan_risk, self.cdir, ex, sid, " ")
        ex.by_tag[self.state()["submissions"][-1]["tag"]] = [{"job_id": "j-c0000-a01", "state": "cancelled"}]
        rep = cp.clear_orphan_risk(self.cdir, ex, sid, "sacct shows the job cancelled")
        self.assertEqual(rep["cleared"], ["c0000-a01"])
        use = lim.usage(self.state())
        self.assertEqual((use["concurrent_jobs"], use["total_jobs"], use["orphan_risk_jobs"]), (0, 1, 1))
        self.assertEqual([r["kind"] for r in self.state()["resource_risk"]], ["abandoned", "orphan-cleared"])
        self.refused("clear.nothing", cp.clear_orphan_risk, self.cdir, ex, sid, "again")

    def test_an_executor_without_tag_lookup_gives_no_evidence(self):
        _, sid = self.abandoned()
        self.refused("clear.no_evidence", cp.clear_orphan_risk, self.cdir, LocalExecutor(), sid, "nothing listed")


class RestartTests(Base):
    def test_scheduler_restarts_do_not_make_core_hours_unbounded(self):
        cfg = {"resources": TL, "limits": {"max_core_hours": 10}}
        ex = ScriptedExecutor({"c0000": [{"state": "done", "restarts": 1, "elapsed_s": 1800}]})
        cp.submit(self.cdir, ex, cfg, pilot=True, approved=True)
        cp.poll(self.cdir, ex)
        use = lim.usage(self.state())
        self.assertEqual((use["total_jobs"], use["core_hours"]), (1, 1.0))  # the restart is inside the job's elapsed time
        self.assertEqual(len(cp.submit(self.cdir, ex, cfg, approved=True)["chunks"]), 2)


class ResetCapTests(Base):
    def test_resets_are_capped_x08(self):
        # R5.3 X08: five resubmissions with max_attempts=1 through resets. With a cap, the second reset is refused.
        cfg = {"max_attempts": 1, "limits": {"max_resets_per_chunk": 1}}
        ex = ScriptedExecutor({"c0000": [{"state": "failed", "exit_code": 1}]})
        cp.submit(self.cdir, ex, cfg, ["c0000"], approved=True)
        cp.poll(self.cdir, ex)
        cp.reset(self.cdir, ["c0000"], "fixed the input path", cfg)
        self.assertEqual(cp.resubmit(self.cdir, ex, cfg, approved=True)["resubmitted"], ["c0000"])
        cp.poll(self.cdir, ex)
        self.refused("limits.exceeded", cp.reset, self.cdir, ["c0000"], "try again", cfg)
        self.refused("reset.duplicate_chunk", cp.reset, self.cdir, ["c0001", "c0001"], "twice")
        # a reset recorded without the configuration (or before a lower cap) is still caught by decide()
        cp.reset(self.cdir, ["c0000"], "reset without the config")
        rep = cp.resubmit(self.cdir, ex, cfg, approved=True)
        self.assertEqual(rep["resubmitted"], [])
        self.assertEqual(rep["blocked"]["c0000"]["decision"], "resets-exhausted")

    def test_decide_cap(self):
        chunk = {"attempt_records": [{"attempt_id": "a", "final_state": "failed"}], "reset_reason": "fixed", "errors": []}
        self.assertEqual(decide(chunk, None, None)["decision"], "resubmit")
        self.assertEqual(decide(chunk, None, None, resets_used=1, max_resets=1)["decision"], "resubmit")
        self.assertEqual(decide(chunk, None, None, resets_used=2, max_resets=1)["decision"], "resets-exhausted")
        self.assertEqual(decide(chunk, None, None, resets_used=1, max_resets=0)["decision"], "resets-exhausted")


class CancelTests(Base):
    def test_request_is_not_termination(self):
        ex = ExitReportingExecutor({"c0000": [{"state": "running"}], "c0001": [{"state": "running"}]}, exits={"j-c0001-a01": 1})
        cp.submit(self.cdir, ex, {}, ["c0000", "c0001"], approved=True)
        cp.poll(self.cdir, ex)
        rep = cp.cancel(self.cdir, ex, approved=True)
        self.assertEqual({j["job_id"]: j["status"] for j in rep["jobs"]}, {"j-c0000-a01": "requested", "j-c0001-a01": "request-failed"})
        st = self.state()
        rec = st["chunks"]["c0000"]["attempt_records"][-1]
        self.assertEqual(rec["cancel_requests"][0]["exit"], 0)
        self.assertNotIn("termination_observed", rec)
        self.assertIsNone(rec["final_state"])  # still running as far as anyone has observed
        ex.script["c0000"] = [{"state": "cancelled", "native_state": "CANCELLED by 1000"}]
        cp.poll(self.cdir, ex)
        rec = self.state()["chunks"]["c0000"]["attempt_records"][-1]
        self.assertEqual(rec["termination_observed"]["final_state"], "cancelled")
        self.assertNotIn("termination_observed", self.state()["chunks"]["c0001"]["attempt_records"][-1])
        ex.script["c0001"] = [{"state": "done"}]  # the job whose cancel failed ends on its own: not a cancellation
        cp.poll(self.cdir, ex)
        rec = self.state()["chunks"]["c0001"]["attempt_records"][-1]
        self.assertEqual(rec["cancel_requests"][0]["status"], "request-failed")
        self.assertNotIn("termination_observed", rec)

    def test_orphans_found_through_the_tag(self):
        ex = InterruptingExecutor({})
        with self.assertRaises(Interrupted):
            cp.submit(self.cdir, ex, {}, ["c0000"], approved=True)
        dry = cp.cancel(self.cdir, ex)
        self.assertEqual(dry["would_cancel"], [])
        self.assertEqual(dry["would_cancel_orphans"], ["j-c0000-a01"])  # intent: no job ID recorded, found by tag
        rep = cp.cancel(self.cdir, ex, approved=True)
        self.assertEqual(rep["requested"], ["j-c0000-a01"])
        risks = self.state()["resource_risk"]
        self.assertEqual([(r["kind"], r["job_id"]) for r in risks], [("orphan-cancel-unconfirmed", "j-c0000-a01")])
        sid = self.state()["submissions"][-1]["id"]
        cp.abandon_submission(self.cdir, sid, "cancelled the job found under the tag")
        self.assertEqual(cp.cancel(self.cdir, ex)["would_cancel_orphans"], ["j-c0000-a01"])  # abandoned is still targeted
        self.assertEqual(cp.cancel(self.cdir, ex, ["c0001"])["would_cancel_orphans"], [])  # other chunks: not touched


if __name__ == "__main__":
    unittest.main()

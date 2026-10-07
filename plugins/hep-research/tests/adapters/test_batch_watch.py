"""B06: the watch loop stops at its limits, early on problems, and never acts beyond collection."""
import unittest

from tests.adapters.batch_harness import Harness


class WatchTests(unittest.TestCase):
    def make(self, backend="slurm", monitor=None, faults=None):
        h = Harness(backend, items=3, chunk=1, extra={"monitor": monitor} if monitor else None)
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults(faults or {})
        h.cli("submit", "--submit")
        self.sleeps = []
        return h

    def watch(self, h):
        return h.cli("watch", sleep=self.sleeps.append)

    def polls(self, h, tool):
        return sum(1 for c in h.calls() if c["tool"] == tool)

    def test_stuck_chunk_stops_after_exactly_max_polls(self):
        h = self.make(monitor={"poll_interval_s": 60, "max_polls": 4}, faults={"c0001": [{"kind": "stuck"}]})
        code, rep = self.watch(h)
        self.assertEqual(code, 1)
        self.assertEqual((rep["stop_reason"], rep["polls"], rep["status"]), ("max-polls", 4, "incomplete"))
        self.assertEqual(rep["not_done"], ["c0001"])
        self.assertEqual(rep["chunks"]["c0001"]["status"], "queued")
        self.assertEqual(self.sleeps, [60, 60, 60])
        self.assertEqual(self.polls(h, "sacct"), 4)
        self.assertEqual(sum(1 for c in h.calls() if c["tool"] == "sbatch"), 1, "watch never resubmits")

    def test_watch_without_limits_refuses_before_polling(self):
        for monitor in (None, {"poll_interval_s": 60}, {"max_polls": 3}):
            with self.subTest(monitor=monitor):
                h = self.make(monitor=monitor)
                code, rep = self.watch(h)
                self.assertEqual((code, rep["code"]), (2, "watch.limits_missing"))
                self.assertEqual(self.polls(h, "sacct"), 0)
                self.assertEqual(h.state()["polls"], 0)

    def test_short_interval_is_refused_by_the_config(self):
        h = self.make(monitor={"poll_interval_s": 59, "max_polls": 3})
        code, rep = self.watch(h)
        self.assertEqual(code, 2)
        self.assertEqual(rep["errors"][0]["key"], "monitor.poll_interval_s")

    def test_repeated_malformed_output_stops_with_the_parse_error(self):
        h = self.make(monitor={"poll_interval_s": 60, "max_polls": 10}, faults={"_global": {"sacct": "malformed"}})
        code, rep = self.watch(h)
        self.assertEqual((code, rep["stop_reason"], rep["polls"]), (1, "repeated-poll-error", 2))
        self.assertEqual(rep["poll_errors"][0]["poll_error"], "slurm.sacct.unparsable")
        self.assertIn("this is not sacct output", rep["poll_errors"][1]["text"])

    def test_held_job_stops_early_for_a_person(self):
        h = self.make("htcondor", monitor={"poll_interval_s": 120, "deadline_s": 3600},
                      faults={"c0002": [{"kind": "hold", "reason": "synthetic hold", "code": 26}], "c0000": [{"kind": "stuck"}]})
        code, rep = self.watch(h)
        self.assertEqual((rep["stop_reason"], rep["polls"]), ("needs-person", 1))
        self.assertEqual(rep["log"][0]["needs_person"], {"c0002": "held"})
        self.assertEqual(rep["log"][0]["not_done"]["c0002"]["hold_reason"], "synthetic hold")

    def test_deadline_stops_the_loop(self):
        h = Harness("slurm", items=2, chunk=1, extra={"monitor": {"poll_interval_s": 60, "deadline_s": 150}})
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults({"c0000": [{"kind": "stuck"}]})
        h.cli("submit", "--submit")
        import sys
        sys.path.insert(0, str(h.config.parent))
        from core.partition import campaign as cp
        import batch_campaign
        clock = iter(range(0, 10_000, 60))
        cfg = h.cfg
        rep = cp.watch(h.cdir, batch_campaign.executor_for(cfg, h.env), cfg, sleep=lambda s: None, clock=lambda: next(clock))
        self.assertEqual((rep["stop_reason"], rep["polls"]), ("deadline", 2))

    def test_complete_campaign_stops_at_once(self):
        h = self.make(monitor={"poll_interval_s": 60, "max_polls": 5})
        code, rep = self.watch(h)
        self.assertEqual((code, rep["stop_reason"], rep["polls"]), (0, "complete", 1))
        self.assertEqual(self.sleeps, [])


if __name__ == "__main__":
    unittest.main()

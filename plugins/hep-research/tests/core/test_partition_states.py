"""B03: normalized states, retry classes, failure signatures and bounded, explicit resubmission."""
import tempfile
import unittest
from pathlib import Path

from core.partition import campaign as cp
from core.partition import states
from tests.core.partition_helpers import ScriptedExecutor, make_campaign

EXPECTED = {  # final state -> decision with max_attempts=3, attempts left, resources unchanged
    "preempted-or-evicted": "resubmit", "node-failure": "resubmit", "lost": "resubmit",
    "timeout": "needs-resource-change", "out-of-memory": "needs-resource-change",
    "failed": "needs-reset", "held": "needs-reset", "cancelled": "needs-reset", "unknown": "needs-reset",
    "not-submitted": "needs-reset", "abandoned": "needs-reset",
}


def chunk(final, n=1, errors=(), reset=None, rh="h0"):
    recs = [{"attempt_id": f"c-a{i:02d}", "final_state": final, "resources_hash": rh} for i in range(1, n + 1)]
    return {"attempt_records": recs, "errors": list(errors), "attempts_since_reset": n, "reset_reason": reset}


class ChunkStatusTests(unittest.TestCase):
    def test_chunk_status_reads_outputs_records_and_repeats(self):
        with tempfile.TemporaryDirectory() as td:
            cdir = Path(td)
            (cdir / "chunks").mkdir()
            state = {"chunks": {}}
            self.assertEqual(cp.chunk_status(cdir, state, "c0000"), "planned")
            state["chunks"]["c0000"] = {"attempt_records": [{"attempt_id": "a1", "final_state": None, "state": "running"}]}
            self.assertEqual(cp.chunk_status(cdir, state, "c0000"), "running")
            state["chunks"]["c0000"] = chunk("timeout", 2, errors=["TimeoutError: x", "TimeoutError: x"])
            self.assertEqual(cp.chunk_status(cdir, state, "c0000"), "stopped-repeated-failure")
            state["chunks"]["c0000"]["reset_reason"] = "raised the time limit"
            self.assertEqual(cp.chunk_status(cdir, state, "c0000"), "timeout")
            (cdir / "chunks" / "c0000.json").write_text("{}")
            self.assertEqual(cp.chunk_status(cdir, state, "c0000"), "done")  # an output wins over any record


class DecisionTableTests(unittest.TestCase):
    def test_every_normalized_state_has_a_decision(self):
        for st in states.NORMALIZED_STATES:
            with self.subTest(state=st):
                if st in ("planned", "queued", "running", "submitting"):
                    self.assertEqual(states.decide({"attempt_records": [{"attempt_id": "a", "final_state": None, "state": st}]}, 3, "h0")["decision"], "wait")
                elif st == "done":
                    self.assertNotIn(st, states.RETRY_CLASS)  # a done chunk is never decided on
                else:
                    self.assertEqual(states.decide(chunk(st), 3, "h0")["decision"], EXPECTED[st])

    def test_resource_change_unlocks_timeout_and_oom(self):
        for st in ("timeout", "out-of-memory"):
            self.assertEqual(states.decide(chunk(st), 3, "h1")["decision"], "resubmit")

    def test_limits(self):
        self.assertEqual(states.decide(chunk("node-failure"), None, "h0")["decision"], "no-retries-configured")
        self.assertEqual(states.decide(chunk("node-failure", n=3), 3, "h0")["decision"], "attempts-exhausted")
        self.assertEqual(states.decide(chunk("failed", reset="fixed path"), None, "h0")["decision"], "resubmit")
        sig = "failed|exit=3|signal=None|hold=None"
        self.assertEqual(states.decide(chunk("failed", n=2, errors=[sig, sig]), 5, "h0")["decision"], "stopped-repeated-failure")

    def test_unknown_native_state_normalizes_to_unknown(self):
        self.assertEqual(states.normalize("SOMETHING_NEW"), "unknown")
        self.assertEqual(states.normalize(None), "unknown")

    def test_signature_ignores_host_and_time(self):
        a = {"final_state": "failed", "exit_code": 3, "signal": None, "hold_code": None, "host": "node1", "submit_time": "t1"}
        b = dict(a, host="node2", submit_time="t2", job_id="99")
        self.assertEqual(states.signature(a), states.signature(b))
        self.assertNotEqual(states.signature(a), states.signature(dict(a, exit_code=4)))


class CampaignRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cdir, self.manifest, _ = make_campaign(Path(self.tmp.name))

    def test_same_failure_on_two_hosts_stops(self):
        ex = ScriptedExecutor({"c0001": [{"per_attempt": {"c0001-a01": {"state": "failed", "exit_code": 3, "host": "node-a"},
                                                          "default": {"state": "failed", "exit_code": 3, "host": "node-b"}}}]})
        cfg = {"max_attempts": 5}
        cp.submit(self.cdir, ex, cfg, approved=True)
        cp.poll(self.cdir, ex)
        cp.reset(self.cdir, ["c0001"], "retry on another node")  # failed needs a reset; the history is kept in resets
        cp.resubmit(self.cdir, ex, cfg, approved=True)
        cp.poll(self.cdir, ex)
        _, state = cp.load(self.cdir)
        hosts = [r["host"] for r in state["chunks"]["c0001"]["attempt_records"]]
        self.assertEqual(hosts, ["node-a", "node-b"])
        rep = cp.report(self.cdir)
        self.assertEqual(rep["chunks"]["c0001"]["status"], "stopped-repeated-failure")
        again = cp.resubmit(self.cdir, ex, cfg, approved=True)
        self.assertEqual(again["resubmitted"], [])
        self.assertEqual(again["blocked"]["c0001"]["decision"], "stopped-repeated-failure")
        self.assertEqual(len(state["resets"]), 1)

    def test_two_identical_retryable_failures_stop(self):
        ex = ScriptedExecutor({"c0001": [{"state": "node-failure", "exit_code": 0, "host": "n1"}]})
        cfg = {"max_attempts": 5}
        cp.submit(self.cdir, ex, cfg, approved=True)
        cp.poll(self.cdir, ex)
        ex.script["c0001"] = [{"state": "node-failure", "exit_code": 0, "host": "n2"}]
        self.assertEqual(cp.resubmit(self.cdir, ex, cfg, approved=True)["resubmitted"], ["c0001"])
        rep = cp.poll(self.cdir, ex)
        self.assertEqual(rep["chunks"]["c0001"]["status"], "stopped-repeated-failure")
        again = cp.resubmit(self.cdir, ex, cfg, approved=True)
        self.assertEqual(again["resubmitted"], [])
        self.assertEqual(again["blocked"]["c0001"]["decision"], "stopped-repeated-failure")

    def test_no_max_attempts_means_zero_resubmissions(self):
        ex = ScriptedExecutor({"c0000": [{"state": "preempted-or-evicted"}], "c0002": [{"state": "failed", "exit_code": 1}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        cp.poll(self.cdir, ex)
        n_submit = sum(1 for c in ex.calls if c[0] == "submit")
        rep = cp.resubmit(self.cdir, ex, {}, approved=True)
        self.assertEqual(rep["resubmitted"], [])
        self.assertEqual(sorted(rep["blocked"]), ["c0000", "c0002"])
        self.assertEqual(rep["blocked"]["c0000"]["decision"], "no-retries-configured")
        self.assertEqual(sum(1 for c in ex.calls if c[0] == "submit"), n_submit)

    def test_out_of_memory_needs_changed_resources_and_records_the_change(self):
        cfg = {"max_attempts": 3, "resources": {"memory_mb": 1000}}
        ex = ScriptedExecutor({"c0001": [{"state": "out-of-memory"}]})
        cp.submit(self.cdir, ex, cfg, approved=True)
        cp.poll(self.cdir, ex)
        self.assertEqual(cp.resubmit(self.cdir, ex, cfg, approved=True)["blocked"]["c0001"]["decision"], "needs-resource-change")
        ex.script["c0001"] = [{"state": "done"}]
        cfg2 = {"max_attempts": 3, "resources": {"memory_mb": 2000}}
        self.assertEqual(cp.resubmit(self.cdir, ex, cfg2, approved=True)["resubmitted"], ["c0001"])
        _, state = cp.load(self.cdir)
        change = state["chunks"]["c0001"]["attempt_records"][-1]["resource_change"]
        self.assertEqual(change, {"after": "out-of-memory", "from": {"memory_mb": 1000}, "to": {"memory_mb": 2000}})
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])

    def test_resubmit_is_a_dry_run_unless_approved(self):
        ex = ScriptedExecutor({"c0000": [{"state": "lost"}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        cp.poll(self.cdir, ex)
        rep = cp.resubmit(self.cdir, ex, {"max_attempts": 2})
        self.assertTrue(rep["submission"]["dry_run"])
        self.assertEqual(rep["resubmitted"], [])
        self.assertEqual(sum(1 for c in ex.calls if c[0] == "submit"), 1)

    def test_scheduler_restarts_count_as_attempts(self):
        ex = ScriptedExecutor({"c0000": [{"state": "done", "restarts": 1}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        rep = cp.poll(self.cdir, ex)
        self.assertEqual(rep["chunks"]["c0000"]["status"], "done")
        self.assertEqual(rep["chunks"]["c0000"]["attempts"], 2)
        _, state = cp.load(self.cdir)
        self.assertEqual([r["origin"] for r in state["chunks"]["c0000"]["attempt_records"]], ["scheduler-restart", "submit"])

    def test_success_without_output_is_lost(self):
        ex = ScriptedExecutor({"c0000": [{"state": "done", "write": False}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        self.assertEqual(cp.poll(self.cdir, ex)["chunks"]["c0000"]["status"], "lost")

    def test_cancel_needs_approval(self):
        ex = ScriptedExecutor({"c0000": [{"state": "queued"}]})
        cp.submit(self.cdir, ex, {}, approved=True)
        cp.poll(self.cdir, ex)
        self.assertTrue(cp.cancel(self.cdir, ex, ["c0000"])["dry_run"])
        self.assertFalse(any(c[0] == "cancel" for c in ex.calls))
        self.assertEqual(cp.cancel(self.cdir, ex, ["c0000"], approved=True)["requested"], ["j-c0000-a01"])


if __name__ == "__main__":
    unittest.main()

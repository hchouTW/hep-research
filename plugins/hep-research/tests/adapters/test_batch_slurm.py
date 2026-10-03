"""B04/B08: Slurm backend against the fake scheduler (tests/adapters/batch_shims); real Slurm only with HEP_SLURM_TEST=1."""
import json
import os
import shutil
import unittest
from pathlib import Path

from tests.adapters.batch_harness import ADAPTER, Harness

GOLDEN = Path(__file__).resolve().parent / "golden" / "slurm-array-10x3.sbatch"
import slurm_backend as sb  # noqa: E402  (batch_harness put the adapter on sys.path)

SCENARIOS = [  # (fault, normalized state, native state)
    ({}, "done", "COMPLETED"),
    ({"kind": "exit", "code": 3}, "failed", "FAILED"),
    ({"kind": "timeout"}, "timeout", "TIMEOUT"),
    ({"kind": "oom"}, "out-of-memory", "OUT_OF_MEMORY"),
    ({"kind": "preempt"}, "preempted-or-evicted", "PREEMPTED"),
    ({"kind": "node-failure"}, "node-failure", "NODE_FAIL"),
    ({"kind": "cancelled"}, "cancelled", "CANCELLED by 0"),
    ({"kind": "native", "state": "REQUEUE_HOLD"}, "held", "REQUEUE_HOLD"),
    ({"kind": "native", "state": "RUNNING"}, "running", "RUNNING"),
    ({"kind": "stuck"}, "queued", "PENDING"),
    ({"kind": "vanish"}, "lost", "not in queue, no runner record"),
    ({"kind": "native", "state": "SUSPENDED"}, "unknown", "SUSPENDED"),
]


class SlurmShimTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness("slurm", items=4, chunk=2)
        self.addCleanup(self.h.cleanup)

    def test_each_native_state_maps(self):
        for fault, normalized, native in SCENARIOS:
            with self.subTest(native=native):
                h = Harness("slurm", items=2, chunk=1)
                self.addCleanup(h.cleanup)
                h.plan()
                h.set_faults({"c0000": [fault]})
                self.assertEqual(h.cli("submit", "--submit")[0], 0)
                code, rep = h.cli("status")
                c = rep["chunks"]["c0000"]
                self.assertEqual(c["status"], normalized)
                self.assertEqual(c["native_state"], native)
                self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
                self.assertEqual(code, 0 if normalized == "done" else 1)
        self.assertEqual(sb.mapped("SOMETHING_NEW"), "unknown")
        # states from the squeue/sacct 26.05 state code tables that the fault shims do not produce
        for native, normalized in (("RESV_DEL_HOLD", "held"), ("SIGNALING", "running"), ("SUSPENDED", "unknown"),
                                   ("STOPPED", "unknown"), ("DEADLINE", "failed"), ("REVOKED", "cancelled"),
                                   ("CANCELLED+", "cancelled")):
            self.assertEqual(sb.mapped(native), normalized, native)

    def test_exit_code_and_signal_are_parsed(self):
        self.assertEqual(sb.parse_exit("0:125"), (0, 125))
        self.assertEqual(sb.parse_exit("3:0"), (3, None))
        with self.assertRaises(ValueError):
            sb.parse_exit("3")
        self.assertEqual(sb.parse_elapsed("1-02:03:04"), 93784.0)
        self.assertEqual(sb.parse_elapsed("03:04"), 184.0)
        self.assertAlmostEqual(sb.parse_rss_mb("20480K"), 20.0)
        self.assertEqual(sb.expand_range("0-3,7%2"), [0, 1, 2, 3, 7])

    def test_golden_array_script_and_dry_run(self):
        h = Harness("slurm", items=10, chunk=1, extra={"throttle": 3, "slurm": {"account": "synthetic-account", "qos": "synthetic-qos"}})
        self.addCleanup(h.cleanup)
        h.plan()
        code, rep = h.cli("submit")
        self.assertEqual(code, 0)
        self.assertTrue(rep["dry_run"])
        self.assertEqual(h.calls(), [], "a dry run must not call the scheduler")
        script = (h.cdir / "dry-run" / "s001" / "job.sbatch").read_text().replace(str(h.cdir), "<CAMPAIGN>")
        if os.environ.get("HEP_UPDATE_GOLDEN"):
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(script)
        self.assertEqual(script, GOLDEN.read_text())
        self.assertIn("#SBATCH --array=0-9%3", script)
        self.assertIn("#SBATCH --no-requeue", script)
        code, rep = h.cli("submit", "--submit")
        self.assertEqual([c["tool"] for c in h.calls()], ["sbatch"])
        self.assertEqual(len(h.state()["submissions"]), 1)
        self.assertEqual(rep["jobs"][9]["job_id"], "1000_9")

    def test_missing_site_keys_refuse_without_a_call(self):
        h = Harness("slurm")
        self.addCleanup(h.cleanup)
        del h.cfg["slurm"]["partition"], h.cfg["resources"]["time_limit"]
        h.write_config()
        code, rep = h.cli("submit", "--submit")
        self.assertEqual(code, 2)
        self.assertEqual(sorted(e["key"] for e in rep["errors"]), ["resources.time_limit", "slurm.partition"])
        self.assertEqual(h.calls(), [])

    def test_campaign_completes_and_merges_like_a_single_run(self):
        self.h.plan()
        self.h.set_faults({"c0001": [{"kind": "requeue-duplicate", "node": "n7"}]})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["duplicates"], 1)  # the site-forced requeue ran the task twice
        self.assertEqual(rep["chunks"]["c0001"]["attempts"], 2)
        code, merged = self.h.cli("merge")
        self.assertEqual(code, 0)
        self.assertEqual(merged["merged"], self.h.single_run())
        recs = self.h.state()["chunks"]["c0000"]["attempt_records"]
        self.assertEqual(recs[0]["evidence"], "accounting (sacct)")
        self.assertAlmostEqual(recs[0]["max_rss_mb"], 20.0)
        self.assertEqual(recs[0]["elapsed_s"], 1.0)

    def test_accounting_unavailable_falls_back_to_queue_and_runner_records(self):
        self.h.plan()
        self.h.set_faults({"c0000": [{"kind": "stuck"}], "c0001": [{"kind": "exit", "code": 4}], "_global": {"sacct": "unavailable"}})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(code, 1)
        self.assertEqual(rep["chunks"]["c0000"]["status"], "queued")
        self.assertEqual(rep["chunks"]["c0001"]["status"], "lost")  # failed before the runner ran: no record anywhere
        recs = self.h.state()["chunks"]["c0000"]["attempt_records"]
        self.assertTrue(recs[-1]["evidence"].startswith("queue+outputs"))

    def test_malformed_accounting_is_a_poll_error(self):
        self.h.plan()
        self.h.set_faults({"_global": {"sacct": "malformed"}})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(code, 1)
        self.assertEqual(rep["code"], "slurm.sacct.unparsable")

    def test_cancel_needs_approval(self):
        self.h.plan()
        self.h.set_faults({"c0000": [{"kind": "stuck"}]})
        self.h.cli("submit", "--submit")
        self.h.cli("status")
        n = len(self.h.calls())
        code, rep = self.h.cli("cancel")
        self.assertTrue(rep["dry_run"])
        self.assertEqual(len(self.h.calls()), n)
        code, rep = self.h.cli("cancel", "--approve-cancel")
        self.assertEqual(rep["cancelled"], ["1000_0"])
        self.assertEqual(self.h.cli("status")[1]["chunks"]["c0000"]["status"], "cancelled")

    def test_pilot_submits_one_chunk_and_reports_its_size(self):
        self.h.plan()
        code, rep = self.h.cli("submit", "--submit", "--pilot")
        self.assertEqual(rep["chunks"], ["c0000"])
        code, rep = self.h.cli("status")
        self.assertEqual(rep["chunks"]["c0000"]["elapsed_s"], 1.0)
        self.assertAlmostEqual(rep["chunks"]["c0000"]["max_rss_mb"], 20.0)
        self.assertEqual(rep["chunks"]["c0001"]["status"], "planned")


@unittest.skipUnless(os.environ.get("HEP_SLURM_TEST") == "1" and shutil.which("sbatch"), "real Slurm not available (HEP_SLURM_TEST=1 and sbatch on PATH)")
class RealSlurmTests(unittest.TestCase):
    def test_example_campaign_on_real_slurm(self):
        raise unittest.SkipTest("no approved Slurm installation in the declared environment (TASK Q1)")


if __name__ == "__main__":
    unittest.main()

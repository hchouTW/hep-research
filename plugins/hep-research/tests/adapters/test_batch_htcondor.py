"""B05/B08: HTCondor backend against the fake scheduler; real HTCondor only with HEP_HTCONDOR_TEST=1."""
import json
import os
import shutil
import unittest
from pathlib import Path

from tests.adapters.batch_harness import Harness

GOLDEN = Path(__file__).resolve().parent / "golden" / "htcondor-chunks-transfer.sub"
import htcondor_backend as hb  # noqa: E402
from core.partition.executors import PollError  # noqa: E402

SCENARIOS = [  # (fault, normalized state, native state)
    ({}, "done", "event 005"),
    ({"kind": "exit", "code": 3}, "failed", "event 005"),
    ({"kind": "signal", "signal": 9}, "failed", "event 005"),
    ({"kind": "hold", "reason": "Error from slot1@shim: job exceeded its memory request", "code": 34, "subcode": 0}, "held", "event 012"),
    ({"kind": "remove"}, "cancelled", "event 009"),
    ({"kind": "stuck"}, "queued", "event 000"),
    ({"kind": "vanish"}, "lost", "event 000"),  # submitted, then gone from queue and history
]


class HTCondorShimTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness("htcondor", items=4, chunk=2)
        self.addCleanup(self.h.cleanup)

    def test_each_event_maps(self):
        for fault, normalized, native in SCENARIOS:
            with self.subTest(fault=fault.get("kind", "none")):
                h = Harness("htcondor", items=2, chunk=1)
                self.addCleanup(h.cleanup)
                h.plan()
                h.set_faults({"c0000": [fault]})
                self.assertEqual(h.cli("submit", "--submit")[0], 0)
                code, rep = h.cli("status")
                c = rep["chunks"]["c0000"]
                self.assertEqual(c["status"], normalized)
                self.assertEqual(c["native_state"], native)
                self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
                if fault.get("kind") == "signal":
                    self.assertEqual(c["signal"], 9)
                if fault.get("kind") == "hold":
                    self.assertEqual((c["hold_code"], c["hold_reason"]), ("34.0", fault["reason"]))

    def test_running_suspended_and_job_status_codes(self):
        log = ("000 (100.000.000) 2026-10-03 10:00:00 Job submitted from host: <h>\n...\n"
               "001 (100.000.000) 2026-10-03 10:00:05 Job executing on host: <slot@n1>\n...\n"
               "000 (100.001.000) 2026-10-03 10:00:00 Job submitted from host: <h>\n...\n"
               "001 (100.001.000) 2026-10-03 10:00:05 Job executing on host: <slot@n1>\n...\n"
               "010 (100.001.000) 2026-10-03 10:00:09 Job was suspended.\n...\n")
        p = hb.parse_event_log(log)
        self.assertEqual((p[(100, 0)]["state"], p[(100, 1)]["state"]), ("running", "unknown"))
        for status, expected in ((1, "queued"), (2, "running"), (3, "cancelled"), (5, "held"), (6, "running"), (7, "unknown")):
            self.assertEqual(hb.HTCondorExecutor._from_ad({"JobStatus": status}, "t")["state"], expected)
        self.assertEqual(hb.HTCondorExecutor._from_ad({"JobStatus": 4, "ExitCode": 0}, "t")["state"], "done")
        self.assertEqual(hb.HTCondorExecutor._from_ad({"JobStatus": 4, "ExitBySignal": True, "ExitSignal": 11}, "t")["signal"], 11)
        with self.assertRaises(PollError):
            hb.parse_event_log("garbage\n...\n")

    def test_eviction_then_completion_is_one_done_chunk_with_two_attempts(self):
        self.h.plan()
        self.h.set_faults({"c0001": [{"kind": "evict-after-output"}]})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
        self.assertEqual(rep["chunks"]["c0001"]["attempts"], 2)
        self.assertEqual(rep["duplicates"], 1)
        recs = self.h.state()["chunks"]["c0001"]["attempt_records"]
        self.assertEqual([r["origin"] for r in recs], ["scheduler-restart", "submit"])
        self.assertEqual(self.h.cli("merge")[1]["merged"], self.h.single_run())

    def test_held_job_blocks_the_merge_and_is_never_released(self):
        self.h.plan()
        self.h.set_faults({"c0000": [{"kind": "hold", "reason": "Transfer input files failure (synthetic)", "code": 13, "subcode": 2}]})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(rep["chunks"]["c0000"]["status"], "held")
        self.assertEqual(rep["chunks"]["c0000"]["hold_reason"], "Transfer input files failure (synthetic)")
        code, merged = self.h.cli("merge")
        self.assertEqual((code, merged["status"]), (1, "incomplete"))
        self.assertFalse(any(c["tool"] in ("condor_release", "condor_rm") for c in self.h.calls()))
        self.h.cfg["max_attempts"] = 3
        self.h.write_config()
        code, rs = self.h.cli("resubmit", "--submit")
        self.assertEqual(rs["blocked"]["c0000"]["decision"], "needs-reset")

    def test_file_transfer_mode_remaps_outputs_and_matches_golden(self):
        h = Harness("htcondor", items=4, chunk=2, extra={"throttle": 2, "htcondor": {"file_transfer": "transfer", "requirements": "(OpSysAndVer == \"SyntheticOS\")"},
                                                         "resources": {"disk_mb": 500, "gpus": 0}})
        self.addCleanup(h.cleanup)
        h.plan()
        self.assertTrue(h.cli("submit")[1]["dry_run"])
        self.assertEqual(h.calls(), [])
        sub = (h.cdir / "dry-run" / "s001" / "job.sub").read_text().replace(str(h.cdir), "<CAMPAIGN>")
        if os.environ.get("HEP_UPDATE_GOLDEN"):
            GOLDEN.write_text(sub)
        self.assertEqual(sub, GOLDEN.read_text())
        h.set_faults({"c0000": [{"kind": "evict-after-output"}]})
        h.cli("submit", "--submit")
        code, rep = h.cli("status")
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["duplicates"], 0)  # output is transferred only on exit, so the evicted run left none
        self.assertEqual(rep["chunks"]["c0000"]["attempts"], 2)
        self.assertTrue((h.cdir / "outputs" / "c0000" / "c0000-a01.json").exists())
        self.assertEqual(h.cli("merge")[1]["merged"], h.single_run())

    def test_dry_run_job_file_reads_its_own_item_list(self):
        """The item list is named relative to the submit file's folder (condor_submit runs there), so the dry-run copy
        can be checked with `condor_submit -dry-run - job.sub` inside dry-run/<id>/ (FULLTEST-E3 L08)."""
        h = Harness("htcondor", items=4, chunk=2)
        self.addCleanup(h.cleanup)
        h.plan()
        self.assertTrue(h.cli("submit")[1]["dry_run"])
        preview = h.cdir / "dry-run" / "s001"
        queue = [l for l in (preview / "job.sub").read_text().splitlines() if l.startswith("queue ")]
        self.assertEqual(len(queue), 1)
        items = queue[0].split(" from ")[1].strip()
        self.assertFalse(Path(items).is_absolute(), queue[0])
        self.assertTrue((preview / items).is_file())

    def test_missing_transfer_choice_refuses(self):
        h = Harness("htcondor")
        self.addCleanup(h.cleanup)
        del h.cfg["htcondor"]["file_transfer"]
        h.write_config()
        code, rep = h.cli("submit", "--submit")
        self.assertEqual(code, 2)
        self.assertEqual([e["key"] for e in rep["errors"]], ["htcondor.file_transfer"])
        self.assertEqual(h.calls(), [])

    def test_missing_event_log_falls_back_to_queue_and_history(self):
        self.h.plan()
        self.h.set_faults({"c0000": [{"kind": "stuck"}], "_global": {"eventlog": "missing"}})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(rep["chunks"]["c0000"]["status"], "queued")
        self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
        recs = self.h.state()["chunks"]
        self.assertEqual(recs["c0000"]["attempt_records"][0]["evidence"], "condor_q")
        self.assertEqual(recs["c0001"]["attempt_records"][0]["evidence"], "condor_history")

    def test_malformed_outputs_are_poll_errors(self):
        for mode, code in (({"eventlog": "malformed"}, "htcondor.eventlog.unparsable"),):
            h = Harness("htcondor", items=2, chunk=1)
            self.addCleanup(h.cleanup)
            h.plan()
            h.set_faults({"_global": mode})
            h.cli("submit", "--submit")
            self.assertEqual(h.cli("status"), (1, {"error": h.cli("status")[1]["error"], "code": code}))
        h = Harness("htcondor", items=2, chunk=1)
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults({"c0000": [{"kind": "stuck"}], "_global": {"condor_q": "malformed"}})
        h.cli("submit", "--submit")
        self.assertEqual(h.cli("status")[1]["code"], "htcondor.condor_q.unparsable")

    def test_whitespace_in_paths_is_refused(self):
        h = Harness("htcondor", items=2, chunk=1, extra={"campaign_dir": "campaign dir"})
        self.addCleanup(h.cleanup)
        h.plan()
        code, rep = h.cli("submit")
        self.assertEqual((code, rep["code"]), (2, "htcondor.path_whitespace"))


@unittest.skipUnless(os.environ.get("HEP_HTCONDOR_TEST") == "1" and shutil.which("condor_submit"), "real HTCondor not available (HEP_HTCONDOR_TEST=1 and condor_submit on PATH)")
class RealHTCondorTests(unittest.TestCase):
    def test_example_campaign_on_a_personal_pool(self):
        raise unittest.SkipTest("no approved HTCondor installation in the declared environment (TASK Q1)")


if __name__ == "__main__":
    unittest.main()

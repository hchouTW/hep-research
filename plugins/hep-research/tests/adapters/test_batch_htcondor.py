"""B05/B08: HTCondor backend against the fake scheduler; real HTCondor only with HEP_HTCONDOR_TEST=1."""
import json
import os
import re
import shutil
import unittest
from pathlib import Path

from tests.adapters.batch_harness import Harness

GOLDEN = Path(__file__).resolve().parent / "golden" / "htcondor-chunks-transfer.sub"
GOLDEN_SITE = Path(__file__).resolve().parent / "golden" / "htcondor-chunks-site-attributes.sub"
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

    def test_cluster_level_events_with_a_negative_proc_are_skipped(self):
        """T03 H4 (HTCondor 24.12.16, CERN, 2026-10-10): the log opens with '035 (15004600.-01.000) ... Cluster
        submitted'; a cluster-level event names no process and must not make the log unparsable."""
        log = ("035 (15004600.-01.000) 10/10 01:32:16 Cluster submitted from host: <137.138.156.150:9618?alias=bigbird13.cern.ch>\n...\n"
               "000 (15004600.000.000) 10/10 01:32:16 Job submitted from host: <137.138.156.150:9618?alias=bigbird13.cern.ch>\n...\n"
               "022 (15004600.000.000) 10/10 01:33:02 Job disconnected, attempting to reconnect\n"
               "    Socket between submit and execute hosts closed unexpectedly\n...\n"
               "024 (15004600.000.000) 10/10 01:33:02 Job reconnection failed\n    Job not found at execution machine\n...\n"
               "004 (15004600.000.000) 10/10 01:33:02 Job was evicted. Code 1008 Subcode 0\n\t(0) CPU times\n\tReason: Job not found at execution machine\n...\n")
        p = hb.parse_event_log(log)
        self.assertEqual(list(p), [(15004600, 0)])
        self.assertEqual((p[(15004600, 0)]["state"], p[(15004600, 0)]["starts"]), ("queued", 0))

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
        sub = re.sub(r"hepr-[0-9a-f]{16}-", "hepr-<UID>-",
                     (h.cdir / "dry-run" / "s001" / "job.sub").read_text().replace(str(h.cdir), "<CAMPAIGN>"))
        self.assertIn("getenv = false", sub)  # the submitter's environment never reaches the job (X06)
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

    def test_history_queries_stop_after_the_records_they_need(self):
        """T03 H4 (CERN bigbird13, 2026-10-10): condor_history scans the schedd's whole history file, newest first,
        and took over 120 s for one cluster; -match N (the number of jobs asked about) returns as soon as they are found."""
        self.h.plan()
        self.h.set_faults({"c0000": [{"kind": "stuck"}], "_global": {"eventlog": "missing"}})
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
        hist = [c["argv"] for c in self.h.calls() if c["tool"] == "condor_history"]
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0][hist[0].index("-match") + 1], "1", hist[0])  # one job was missing from the queue

    def test_lagging_event_log_is_read_again_before_the_history_fallback(self):
        """T03 H4 (CERN pool, 2026-10-10): right after a job finished, the AFS copy of the event log still showed it
        queued while condor_q no longer listed it, so poll went to condor_history, whose records appear minutes later
        and whose scan then exceeded the timeout. When the queue says gone, the log is read once more before the
        history is asked; a terminal event that arrived meanwhile settles the job without any history call."""
        self.h.plan()
        self.h.set_faults({"_global": {"eventlog": "lagged"}})  # terminal events reach the log only after the next condor_q
        self.h.cli("submit", "--submit")
        code, rep = self.h.cli("status")
        self.assertEqual(code, 0, rep)
        self.assertEqual({c: v["status"] for c, v in rep["chunks"].items()}, {"c0000": "done", "c0001": "done"})
        tools = [c["tool"] for c in self.h.calls()]
        self.assertIn("condor_q", tools)
        self.assertNotIn("condor_history", tools, "the re-read log settled the jobs; no history scan was needed")
        recs = self.h.state()["chunks"]["c0000"]["attempt_records"]
        self.assertEqual(recs[0]["evidence"], "job event log")

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

    def test_site_attributes_render_as_plus_lines_and_match_golden(self):
        """T03 H3: CERN's JobFlavour / MaxRuntime / WantOS are +Name = value lines from the configuration, after the
        resource lines; a walltime is accepted for HTCondor so limits.max_core_hours can count."""
        h = Harness("htcondor", items=2, chunk=1, extra={
            "resources": {"time_limit": "00:20:00"}, "limits": {"max_core_hours": 1},
            "htcondor": {"site_attributes": {"JobFlavour": "espresso", "MaxRuntime": 1200, "WantOS": "el9", "WantIOProxy": True}}})
        self.addCleanup(h.cleanup)
        h.plan()
        self.assertTrue(h.cli("submit")[1]["dry_run"])
        text = (h.cdir / "dry-run" / "s001" / "job.sub").read_text()
        lines = [l for l in text.splitlines() if l.startswith("+") and "HepResearchTag" not in l]
        self.assertEqual(lines, ['+JobFlavour = "espresso"', "+MaxRuntime = 1200", '+WantOS = "el9"', "+WantIOProxy = true"])
        self.assertLess(text.index("request_memory"), text.index("+JobFlavour"))
        sub = re.sub(r"hepr-[0-9a-f]{16}-", "hepr-<UID>-", text.replace(str(h.cdir), "<CAMPAIGN>"))
        if os.environ.get("HEP_UPDATE_GOLDEN"):
            GOLDEN_SITE.write_text(sub)
        self.assertEqual(sub, GOLDEN_SITE.read_text())
        self.assertEqual(h.cli("submit", "--submit")[0], 0)
        code, rep = h.cli("status")
        self.assertEqual((code, rep["chunks"]["c0000"]["status"]), (0, "done"))

    def test_schedd_name_binds_every_scheduler_call_of_the_campaign(self):
        """T03 H3: a configured schedd is passed as -name to condor_submit, condor_q, condor_history and condor_rm,
        recorded with the submission, and the recorded one wins over a later configuration change."""
        h = Harness("htcondor", items=2, chunk=1, extra={"htcondor": {"schedd": "shim-schedd.example"}})
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults({"c0000": [{"kind": "stuck"}]})
        self.assertEqual(h.cli("submit", "--submit")[0], 0)
        self.assertEqual((h.cdir / "submissions" / "s001" / "schedd.txt").read_text().strip(), "shim-schedd.example")
        h.cfg["htcondor"]["schedd"] = "other-schedd.example"  # a later myschedd bump must not move the campaign
        h.write_config()
        code, rep = h.cli("status")
        self.assertEqual(rep["chunks"]["c0000"]["status"], "queued")
        code, rep = h.cli("cancel", "--approve-cancel")
        self.assertEqual(code, 0, rep)
        tools = {c["tool"] for c in h.calls()}
        self.assertEqual(tools, {"condor_version", "condor_submit", "condor_q", "condor_history", "condor_rm"} & tools | {"condor_submit", "condor_q", "condor_rm"})
        for c in h.calls():
            if c["tool"] in ("condor_submit", "condor_q", "condor_history", "condor_rm"):
                self.assertEqual(c["argv"][:2], ["-name", "shim-schedd.example"], c)

    def test_schedd_caller_takes_the_name_from_the_callers_environment(self):
        h = Harness("htcondor", items=2, chunk=1, extra={"htcondor": {"schedd": "caller"}})
        self.addCleanup(h.cleanup)
        h.env.pop("_condor_SCHEDD_HOST", None)  # the developer's own shell may export it (lxplus does)
        h.plan()
        code, rep = h.cli("submit", "--submit")
        self.assertEqual((code, rep["code"]), (2, "htcondor.schedd.unresolved"))
        self.assertEqual(h.calls(), [])
        h.env["_condor_SCHEDD_HOST"] = "caller-schedd.example"
        self.assertEqual(h.cli("submit", "--submit")[0], 0)
        self.assertEqual((h.cdir / "submissions" / "s001" / "schedd.txt").read_text().strip(), "caller-schedd.example")
        self.assertEqual([c["argv"][:2] for c in h.calls() if c["tool"] == "condor_submit"], [["-name", "caller-schedd.example"]])

    def test_no_schedd_configured_keeps_the_site_mapping(self):
        self.h.plan()
        self.h.cli("submit", "--submit")
        self.assertFalse((self.h.cdir / "submissions" / "s001" / "schedd.txt").exists())
        self.assertFalse(any("-name" in c["argv"] for c in self.h.calls()))

    def test_credential_or_queue_refusal_at_submit_is_not_submitted(self):
        """T03 H2 observed: 'The credmon did not process credentials within the timeout period ... BAILING OUT.' and
        'ERROR: Failed to commit job submission into the queue.' both end condor_submit before a cluster exists."""
        for mode, code in (("credmon-timeout", "htcondor.submit.credential"), ("rejected", "htcondor.submit.rejected")):
            with self.subTest(mode=mode):
                h = Harness("htcondor", items=2, chunk=1)
                self.addCleanup(h.cleanup)
                h.plan()
                h.set_faults({"_global": {"condor_submit": mode}})
                rc, rep = h.cli("submit", "--submit")
                self.assertEqual((rc, rep["code"]), (1, code), rep)
                sub = h.state()["submissions"][0]
                self.assertEqual(sub["status"], "not-submitted")
                self.assertEqual([r["state"] for r in h.state()["chunks"]["c0000"]["attempt_records"]], ["not-submitted"])
                h.set_faults({})
                # not 'unconfirmed': the documented retry path (needs-reset -> reset with a reason -> resubmit) is open
                self.assertEqual(h.cli("resubmit")[1]["blocked"]["c0000"]["decision"], "needs-reset")
                self.assertEqual(h.cli("reset", "--chunks", "c0000", "c0001", "--reason", "credential step failed; retrying")[0], 0)
                self.assertEqual(h.cli("resubmit", "--submit")[0], 0)
                self.assertEqual(h.cli("status")[1]["chunks"]["c0000"]["status"], "done")

    def test_whitespace_in_paths_is_refused(self):
        h = Harness("htcondor", items=2, chunk=1, extra={"campaign_dir": "campaign dir"})
        self.addCleanup(h.cleanup)
        h.plan()
        code, rep = h.cli("submit")
        self.assertEqual((code, rep["code"]), (2, "htcondor.path_whitespace"))


@unittest.skipUnless(os.environ.get("HEP_HTCONDOR_TEST") == "1" and shutil.which("condor_submit"), "real HTCondor not available (HEP_HTCONDOR_TEST=1 and condor_submit on PATH)")
class RealHTCondorTests(unittest.TestCase):
    """A real pool, never a fake: HEP_HTCONDOR_TEST=1, condor_submit on PATH, and HEP_HTCONDOR_CONFIG naming a batch
    configuration the user reviewed (site facts never live in the plugin; its campaign_dir must be on a file system the
    jobs can write, and the test makes a fresh campaign folder beside it). Setting the variables is the approval to
    submit two short synthetic jobs. First run: lxplus, HTCondor 24.12.16, 2026-10-10 (T03 H4)."""

    DEADLINE_S = 1200

    def test_two_synthetic_chunks_merge_like_a_single_run(self):
        cfg_path = os.environ.get("HEP_HTCONDOR_CONFIG")
        if not cfg_path:
            self.skipTest("HEP_HTCONDOR_CONFIG not set: no reviewed site configuration to submit with")
        import contextlib
        import io
        import time
        import batch_campaign
        base = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        stamp = time.strftime("%Y%m%dT%H%M%S")
        root = Path(base["campaign_dir"]).resolve().parent / f"realtest-{stamp}"
        (root / "worker").mkdir(parents=True)
        worker = root / "worker" / "toy.py"
        worker.write_text("#!/usr/bin/env python3\nimport json, sys\na = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
                          "start, stop = int(a['--start']), int(a['--stop'])\n"
                          "json.dump({'n': stop - start, 'sum': sum(range(start, stop)), 'seed_sum': int(a['--seed'])}, open(a['--out'], 'w'))\n")
        cfg = dict(base, campaign_dir=str(root / "campaign"))
        config = root / "batch-config.json"
        config.write_text(json.dumps(cfg))
        python = cfg.get("worker_python") or sys.executable

        def cli(*args):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = batch_campaign.main([args[0], "--config", str(config), *args[1:]], env=dict(os.environ))
            return code, json.loads(buf.getvalue())

        self.assertEqual(cli("check-config")[0], 0)
        self.assertEqual(cli("plan", "--job", "real-htcondor-test", "--items", "200", "--chunk-size", "100", "--seed", "7",
                             "--cmd", f"{python} {worker} --start {{start}} --stop {{stop}} --seed {{seed}} --out {{out}}")[0], 0)
        code, dry = cli("submit")
        self.assertTrue(dry["dry_run"])
        code, sub = cli("submit", "--submit", "--plan-digest", dry["plan_digest"])
        self.assertEqual(code, 0, sub)
        self.assertEqual(len(sub["jobs"]), 2)
        t0 = time.time()
        while True:
            code, rep = cli("status")
            states = {c: v["status"] for c, v in rep.get("chunks", {}).items()} if "chunks" in rep else {}
            if states and all(s == "done" for s in states.values()):
                break
            if any(s in ("failed", "held", "lost", "cancelled", "unknown") for s in states.values()):
                self.fail(f"chunk not done: {rep}")
            if time.time() - t0 > self.DEADLINE_S:
                self.fail(f"not done within {self.DEADLINE_S} s: {rep}")
            time.sleep(30)
        code, merged = cli("merge")
        self.assertEqual((code, merged["status"]), (0, "complete"), merged)
        self.assertEqual(merged["merged"]["n"], 200)
        self.assertEqual(merged["merged"]["sum"], sum(range(200)))
        code, rep = cli("report", "--out", str(root / "report.json"), "--label", "synthetic")
        self.assertEqual(code, 0, rep)


if __name__ == "__main__":
    unittest.main()

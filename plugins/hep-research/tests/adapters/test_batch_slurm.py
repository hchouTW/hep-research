"""B04/B08: Slurm backend against the fake scheduler (tests/adapters/batch_shims); real Slurm only with HEP_SLURM_TEST=1."""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from core.partition import limits as lim
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
        script = re.sub(r"hepr-[0-9a-f]{16}-", "hepr-<UID>-",
                        (h.cdir / "dry-run" / "s001" / "job.sbatch").read_text().replace(str(h.cdir), "<CAMPAIGN>"))
        if os.environ.get("HEP_UPDATE_GOLDEN"):
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(script)
        self.assertEqual(script, GOLDEN.read_text())
        self.assertIn("#SBATCH --array=0-9%3", script)
        self.assertIn("#SBATCH --no-requeue", script)
        self.assertIn("#SBATCH --export=NONE", script)  # the submitter's environment never reaches the job (X06)
        self.assertIn("#SBATCH --job-name=hepr-<UID>-s001", script)
        code, rep = h.cli("submit", "--submit")
        self.assertEqual([c["tool"] for c in h.calls()], ["scontrol", "sbatch"])  # MaxArraySize preflight (CMP-22)
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

    def test_allocated_cpus_are_recorded_and_counted(self):
        """GPU-CAMPAIGN-RUN: 1 CPU requested, 2 allocated (a whole core on a hyper-threaded node); sacct AllocCPUS."""
        self.h.plan()
        self.h.set_faults({"c0000": [{"alloc_cpus": 2}]})
        self.h.cli("submit", "--submit")
        self.h.cli("status")
        state = self.h.state()
        self.assertEqual(state["chunks"]["c0000"]["attempt_records"][0]["alloc_cpus"], 2)
        self.assertEqual(state["chunks"]["c0001"]["attempt_records"][0]["alloc_cpus"], 1)
        self.assertEqual(lim.usage(state)["alloc_cpu_factor"], 2.0)

    def test_allocated_gpus_are_recorded(self):
        self.h.plan()
        self.h.set_faults({"c0000": [{"alloc_gpus": 1}]})
        self.h.cli("submit", "--submit")
        self.h.cli("status")
        recs = {c: r["attempt_records"][0] for c, r in self.h.state()["chunks"].items()}
        self.assertEqual((recs["c0000"]["alloc_gpus"], recs["c0001"]["alloc_gpus"]), (1, 0))

    def _poll_real(self, out, job_id):
        ex = sb.SlurmExecutor({"resources": {"cpus": 1}})
        ex.run_poll = lambda argv, cwd=None: subprocess.CompletedProcess(argv, 0, out, "")
        return ex.poll([{"attempt_id": "a1", "job_id": job_id}])["a1"]

    def test_poll_parses_real_sacct_alloc_cpus_and_gpus(self):
        """sacct output recorded on NSTCCore (Slurm 24.05.1, 2026-10-11): a 1-CPU 1-GPU V100 job allocated 2 CPUs and
        1 GPU (AllocTRES gres/gpu=1); a CPU job's AllocTRES has no gres/gpu."""
        obs = self._poll_real("7050788_0|COMPLETED|0:0|00:00:04||hp-teslav06|2|billing=2,cpu=2,gres/gpu=1,mem=8000M,node=1\n"
                              "7050788_0.batch|COMPLETED|0:0|00:00:04|68K|hp-teslav06|2|cpu=2,gres/gpu=1,mem=8000M,node=1\n",
                              "7050788_0")
        self.assertEqual((obs["state"], obs["alloc_cpus"], obs["alloc_gpus"], obs["elapsed_s"], obs["host"]),
                         ("done", 2, 1, 4.0, "hp-teslav06"))
        obs = self._poll_real("7050429_0|COMPLETED|0:0|00:00:05||hpa-wn07|1|billing=1,cpu=1,mem=200M,node=1\n"
                              "7050429_0.batch|COMPLETED|0:0|00:00:05|18760K|hpa-wn07|1|cpu=1,mem=200M,node=1\n",
                              "7050429_0")
        self.assertEqual((obs["alloc_cpus"], obs["alloc_gpus"]), (1, 0))

    def test_alloc_tres_pending_and_typed_gpus(self):
        obs = self._poll_real("7_0|PENDING|0:0|00:00:00||None assigned|0|\n", "7_0")
        self.assertEqual((obs["state"], obs["alloc_gpus"]), ("queued", None))  # nothing allocated yet: unknown
        obs = self._poll_real("7_0|RUNNING|0:0|00:00:09||n1|4|billing=4,cpu=4,gres/gpu:v100=2,gres/gpu=2,node=1\n", "7_0")
        self.assertEqual(obs["alloc_gpus"], 2)  # the typed entry repeats the count; it is not added

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
        self.assertEqual(rep["requested"], ["1000_0"])
        self.assertEqual([c["exit"] for c in rep["commands"]], [0])
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
    """A real cluster, never a fake: HEP_SLURM_TEST=1, sbatch on PATH, and HEP_SLURM_CONFIG naming a batch configuration
    the user reviewed (site facts never live in the plugin; its campaign_dir must be on a file system the jobs can write,
    and the test makes a fresh campaign folder beside it). Setting the variables is the approval to submit two short
    synthetic jobs. First run: NSTCCore, Slurm 24.05.1, 2026-10-10."""

    DEADLINE_S = 1200

    def test_two_synthetic_chunks_merge_like_a_single_run(self):
        cfg_path = os.environ.get("HEP_SLURM_CONFIG")
        if not cfg_path:
            self.skipTest("HEP_SLURM_CONFIG not set: no reviewed site configuration to submit with")
        import contextlib
        import io
        import sys
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
        self.assertEqual(cli("plan", "--job", "real-slurm-test", "--items", "200", "--chunk-size", "100", "--seed", "7",
                             "--cmd", f"{python} {worker} --start {{start}} --stop {{stop}} --seed {{seed}} --out {{out}}")[0], 0)
        code, dry = cli("submit")
        self.assertTrue(dry["dry_run"])
        code, sub = cli("submit", "--submit", "--plan-digest", dry["plan_digest"])
        self.assertEqual(code, 0, sub)
        self.assertEqual(len(sub["jobs"]), 2)
        self.assertTrue(all(re.fullmatch(r"\d+_[01]", j["job_id"]) for j in sub["jobs"]), sub["jobs"])
        t0 = time.time()
        while True:
            code, rep = cli("status")
            states = {c: v["status"] for c, v in rep.get("chunks", {}).items()} if "chunks" in rep else {}
            if states and all(s == "done" for s in states.values()):
                break
            if any(s in ("failed", "held", "lost", "cancelled", "unknown", "timeout", "out-of-memory") for s in states.values()):
                self.fail(f"chunk not done: {rep}")
            if time.time() - t0 > self.DEADLINE_S:
                self.fail(f"not done within {self.DEADLINE_S} s (jobs {[j['job_id'] for j in sub['jobs']]} may still be queued): {rep}")
            time.sleep(30)
        self.assertEqual({v["native_state"] for v in rep["chunks"].values()}, {"COMPLETED"})
        code, merged = cli("merge")
        self.assertEqual((code, merged["status"]), (0, "complete"), merged)
        self.assertEqual(merged["merged"]["n"], 200)
        self.assertEqual(merged["merged"]["sum"], sum(range(200)))
        code, rep = cli("report", "--out", str(root / "report.json"), "--label", "synthetic")
        self.assertEqual(code, 0, rep)


if __name__ == "__main__":
    unittest.main()


class InterruptedSubmitCliTests(unittest.TestCase):
    """confirm and abandon on the command line (T15): an interrupted submit is recovered by a person, never guessed."""

    def setUp(self):
        self.h = Harness("slurm", items=2, chunk=1)
        self.h.plan()

    def tearDown(self):
        self.h.cleanup()

    def interrupt(self):
        import core.partition.campaign as cp
        from tests.core.partition_helpers import ScriptedExecutor

        class Stop(BaseException):
            pass

        class Interrupting(ScriptedExecutor):
            def submit(self, plan):
                raise Stop()
        with self.assertRaises(Stop):
            cp.submit(self.h.cdir, Interrupting({}), self.h.cfg, approved=True)
        return self.h.state()["submissions"][-1]["id"]

    def test_confirm_and_abandon(self):
        code, rep = self.h.cli("confirm", "--submission", "s001", "--jobs", "c0000-a01=1")
        self.assertEqual((code, rep["code"]), (2, "confirm.not_unconfirmed"))
        sid = self.interrupt()
        code, rep = self.h.cli("submit", "--submit")
        self.assertEqual((code, rep["code"]), (2, "submit.unconfirmed"))
        self.assertEqual(self.h.cli("confirm", "--submission", sid, "--jobs", "nonsense")[0], 2)
        code, rep = self.h.cli("reconcile", "--submission", sid)
        self.assertEqual((code, rep["candidates"]), (0, []))  # the scheduler has no job under the tag
        code, rep = self.h.cli("confirm", "--submission", sid, "--jobs", "c0000-a01=1000_0")
        self.assertEqual((code, rep["code"]), (2, "confirm.unknown_jobs"))  # a fabricated job ID is refused (X07)
        code, rep = self.h.cli("abandon", "--submission", sid, "--reason", "squeue lists no job of this submission")
        self.assertEqual(code, 0, rep)
        self.assertEqual(self.h.state()["submissions"][-1]["status"], "abandoned")

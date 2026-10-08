"""AGENTIC-R5 WP3' (T3.1, T3.2, T3.6): scheduler timeouts and ambiguous submissions, reconciliation tags, and the
execution-layer gaps X01, X03, X04, X06, X11, X13, X15, X16. Synthetic campaigns and fake tools only."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.adapters.batch_harness import ADAPTER  # noqa: F401  (puts the adapter on sys.path)
from tests.core.partition_helpers import ScriptedExecutor, make_campaign

import batch_config  # noqa: E402
from core.partition import campaign as cp  # noqa: E402
from core.partition.executors import PollError, SubmitAmbiguous, SubmitRefused, allowed_env  # noqa: E402
from slurm_backend import SlurmExecutor  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = {"backend": "slurm", "campaign_dir": "c", "resources": {"time_limit": "00:10:00"}, "slurm": {"partition": "p1"}}


def codes(cfg):
    return {(e["code"], e["key"]) for e in batch_config.validate(cfg)}


def fake_tool(d: Path, name: str, body: str) -> None:
    p = d / name
    p.write_text(f"#!/bin/sh\n{body}\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


class ConfigInjectionX01X13(unittest.TestCase):
    def test_newlines_braces_and_names_are_refused(self):
        for key, value in (("job_name", "x\nexec evil"), ("job_name", "two words"), ("job_name", "{{runner}}")):
            with self.subTest(value=value):
                self.assertIn(("config.bad_value", key), codes(dict(BASE, **{key: value})))
        for k, v in (("partition", "p1\n#SBATCH --uid=0"), ("account", "a b"), ("constraint", "x\ny")):
            with self.subTest(slurm=k):
                self.assertIn(("config.bad_value", f"slurm.{k}"), codes(dict(BASE, slurm={"partition": "p1", k: v})))
        h = {"backend": "htcondor", "campaign_dir": "c", "resources": {},
             "htcondor": {"universe": "vanilla", "file_transfer": "transfer", "requirements": "x\nexecutable = /bin/sh"}}
        self.assertIn(("config.bad_value", "htcondor.requirements"), codes(h))

    def test_paths_must_be_absolute(self):
        self.assertIn(("config.bad_value", "worker_python"), codes(dict(BASE, worker_python="python3")))
        self.assertEqual(codes(dict(BASE, worker_python="/usr/bin/python3")), set())
        h = {"backend": "htcondor", "campaign_dir": "c", "resources": {},
             "htcondor": {"universe": "vanilla", "file_transfer": "transfer", "transfer_input_files": ["../secrets.json"]}}
        self.assertIn(("config.bad_value", "htcondor.transfer_input_files[0]"), codes(h))

    def test_credentials_cannot_be_passed_through(self):
        self.assertIn(("config.bad_value", "env_passthrough"), codes(dict(BASE, env_passthrough=["GITHUB_TOKEN"])))
        self.assertEqual(codes(dict(BASE, env_passthrough=["MY_SITE_SETTING"], scheduler_timeout_s=30)), set())


class EnvironmentX06(unittest.TestCase):
    def test_scheduler_clients_get_the_allow_list_only(self):
        env = {"PATH": "/bin", "HOME": "/h", "HEP_SYNTHETIC_CANARY": "sentinel-123", "SSH_AUTH_SOCK": "/tmp/agent"}
        ex = SlurmExecutor(dict(BASE, env_passthrough=["HOME"]), env)
        self.assertEqual(ex.env, {"PATH": "/bin", "HOME": "/h"})
        self.assertNotIn("SSH_AUTH_SOCK", allowed_env(env))


class SubmissionOutcomesT31(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.bin = self.d / "bin"
        self.bin.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def executor(self, timeout=2):
        return SlurmExecutor(dict(BASE, scheduler_timeout_s=timeout), {"PATH": str(self.bin)})

    def plan(self):
        return {"submit_argv": ["sbatch", "--parsable", "job.sbatch"], "submission_dir": str(self.d), "rows": []}

    def test_missing_client_is_refused(self):
        with self.assertRaises(SubmitRefused):
            self.executor().submit(self.plan())

    def test_timeout_exit_zero_without_id_and_failure_are_ambiguous(self):
        for body, sig in (("/bin/sleep 5", "slurm.submit.timeout"), ("exit 0", "slurm.sbatch.failed"),
                          ("echo 'sbatch: error: Socket timed out' >&2; exit 1", "slurm.sbatch.failed")):
            with self.subTest(body=body):
                fake_tool(self.bin, "sbatch", body)
                with self.assertRaises(SubmitAmbiguous) as err:
                    self.executor(timeout=1).submit(self.plan())
                self.assertEqual(err.exception.signature, sig)

    def test_hung_poll_is_a_poll_error_not_a_held_lock(self):
        fake_tool(self.bin, "sacct", "/bin/sleep 5")
        with self.assertRaises(PollError) as err:
            self.executor(timeout=1).poll([{"job_id": "1_0", "attempt_id": "c-a01"}])
        self.assertEqual(err.exception.signature, "slurm.timeout")

    def test_lost_response_is_never_recorded_as_not_submitted(self):
        cdir, _, _ = make_campaign(self.d / "camp")

        class Lost(ScriptedExecutor):
            def submit(self, plan):
                super().submit(plan)
                raise SubmitAmbiguous("scripted.timeout", "no answer")
        with self.assertRaises(SubmitAmbiguous):
            cp.submit(cdir, Lost({}), {"max_attempts": 1}, approved=True)
        state = json.loads((cdir / "state.json").read_text())
        self.assertEqual(state["submissions"][-1]["status"], "intent")
        self.assertTrue(state["submissions"][-1]["tag"].startswith("hepr-" + state["campaign_uid"]))


class CollectionAndMergeX03X04X11X15(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.cdir, self.manifest, _ = make_campaign(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def test_symlinked_output_dir_is_not_followed(self):
        elsewhere = self.d / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "precious.json").write_text("{}")
        os.symlink(elsewhere, self.cdir / "outputs" / "c0000")
        col = cp.collect(self.cdir)
        self.assertTrue((elsewhere / "precious.json").exists(), "a target outside the campaign was moved")
        self.assertEqual([q["file"] for q in col["quarantined"]], ["outputs/c0000"])

    def test_forged_or_changed_chunk_files_fail_the_merge(self):
        ex = ScriptedExecutor({})
        cp.submit(self.cdir, ex, {}, approved=True)
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])
        self.assertEqual(cp.merge(self.cdir)["status"], "complete")
        f = self.cdir / "chunks" / "c0000.json"
        doc = json.loads(f.read_text())
        doc["result"]["sum"] += 1
        f.write_text(json.dumps(doc, sort_keys=True))
        rep = cp.merge(self.cdir)
        self.assertEqual(rep["status"], "refused")
        self.assertEqual([p["code"] for p in rep["problems"]], ["merge.chunk_changed"])
        (self.cdir / "chunks" / "c9999.json").write_text("{}")
        self.assertIn("merge.uncollected_chunk", {p["code"] for p in cp.merge(self.cdir)["problems"]})

    def test_orphan_output_is_recorded(self):
        class Lost(ScriptedExecutor):
            def submit(self, plan):
                super().submit(plan)  # the jobs run
                raise SubmitAmbiguous("scripted.timeout", "no answer")
        ex = Lost({})
        with self.assertRaises(SubmitAmbiguous):
            cp.submit(self.cdir, ex, {}, approved=True)
        sid = json.loads((self.cdir / "state.json").read_text())["submissions"][-1]["id"]
        cp.abandon_submission(self.cdir, sid, "squeue showed nothing at the time")
        ex.poll([{"chunk_id": c["id"], "attempt_id": f"{c['id']}-a01"} for c in self.manifest["chunks"]])  # the jobs ran
        cp.collect(self.cdir)
        state = json.loads((self.cdir / "state.json").read_text())
        flagged = [r for row in state["chunks"].values() for r in row["attempt_records"] if r.get("orphan_output_collected")]
        self.assertEqual(len(flagged), len(self.manifest["chunks"]))
        rep = cp.merge(self.cdir)
        self.assertEqual(rep["status"], "complete")
        self.assertIn("merge.orphan_output", {w["code"] for w in rep["provenance_warnings"]})

    def test_plan_digest_binds_the_reviewed_dry_run(self):
        ex = ScriptedExecutor({})
        dry = cp.submit(self.cdir, ex, {}, approved=False)
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(self.cdir, ex, {}, approved=True, expected_plan_digest="0" * 64)
        self.assertEqual(err.exception.code, "submit.plan_changed")
        self.assertFalse(cp.submit(self.cdir, ex, {}, approved=True, expected_plan_digest=dry["plan_digest"])["dry_run"])


class WorkerTimeoutT31(unittest.TestCase):
    def test_runner_stops_a_hung_worker_and_records_it(self):
        from core.partition import engine
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            m = engine.make_manifest("synthetic-test", 1, 1, 1)
            cmd = f"{sys.executable} -c 'import time; time.sleep(5)' {{out}}"
            cdir = cp.init(d / "c", m, cmd, worker_timeout_s=1)
            p = subprocess.run([sys.executable, str(cdir / "runner.py"), "--spec", str(cdir / "spec.json"), "--chunk", "c0000",
                                "--attempt", "c0000-a01", "--out-dir", str(d / "out")], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 124)
            meta = json.loads((d / "out" / "c0000-a01.meta.json").read_text())
            self.assertIn("worker_timeout_s", meta["runner_error"])


class LocalRulesX16(unittest.TestCase):
    def test_local_partition_timeout_and_environment(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "w.py").write_text("import json, os, sys, time\na = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
                                    "time.sleep(float(os.environ.get('SLEEP_S', '0')))\n"
                                    "json.dump({'n': 1, 'leak': int('HEP_SYNTHETIC_CANARY' in os.environ)}, open(a['--out'], 'w'))\n")
            script = ROOT / "skills" / "hep-computing" / "scripts" / "local_partition.py"
            run = lambda *a, env=None: subprocess.run([sys.executable, str(script), *a], capture_output=True, text=True,
                                                      timeout=120, env=env)
            self.assertEqual(run("plan", "--job", "t", "--items", "2", "--chunk-size", "1", "--seed", "1",
                                 "--out", str(d / "m.json")).returncode, 0)
            cmd = f"{sys.executable} {d / 'w.py'} --out {{out}} --id {{id}}"
            env = dict(os.environ, HEP_SYNTHETIC_CANARY="sentinel", SLEEP_S="0")
            p = run("run", "--manifest", str(d / "m.json"), "--state", str(d / "s1"), "--cmd", cmd, env=env)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            merged = run("merge", "--manifest", str(d / "m.json"), "--state", str(d / "s1"))
            self.assertEqual(json.loads(merged.stdout)["merged"]["leak"], 0)  # the token never reached the worker
            env["SLEEP_S"] = "5"
            p = run("run", "--manifest", str(d / "m.json"), "--state", str(d / "s2"), "--cmd", cmd, "--timeout", "1",
                    "--env-passthrough", "SLEEP_S", env=env)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("timeout", p.stdout)


if __name__ == "__main__":
    unittest.main()

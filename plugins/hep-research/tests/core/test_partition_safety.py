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
from core.partition.executors import SubmitAmbiguous, SubmitRefused
from tests.core.partition_helpers import ScriptedExecutor, make_campaign, single_run

CONFIG = {"max_attempts": 2, "resources": {"time": "00:10:00"}}


class Interrupted(BaseException):
    """Stands in for a kill or Ctrl-C after the scheduler accepted the jobs but before the campaign saved them."""


class InterruptingExecutor(ScriptedExecutor):
    def submit(self, plan):
        self.accepted = super().submit(plan)  # the scheduler now has the jobs
        raise Interrupted()


class RefusingExecutor(ScriptedExecutor):
    def submit(self, plan):  # the client could not start: certainly nothing was submitted
        raise SubmitRefused("scripted.submit.not_started", "sbatch: No such file or directory")


class AmbiguousExecutor(ScriptedExecutor):
    def submit(self, plan):  # the scheduler queued the jobs, then the client failed (or timed out)
        self.accepted = super().submit(plan)
        raise SubmitAmbiguous("scripted.submit.failed", "exit 1: sbatch: error: Socket timed out")


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
            cp.confirm_submission(self.cdir, sub["id"], {"c0000-a01": "x"}, ex)  # every attempt needs its job
        rec = cp.reconcile(self.cdir, ex, sub["id"])
        self.assertEqual(sorted(c["job_id"] for c in rec["candidates"]), sorted(j["job_id"] for j in ex.accepted))
        fabricated = {j["attempt_id"]: "99999" for j in ex.accepted}
        with self.assertRaises(cp.CampaignError) as err:  # IDs the scheduler does not list under the tag (X07)
            cp.confirm_submission(self.cdir, sub["id"], fabricated, ex)
        self.assertEqual(err.exception.code, "confirm.unknown_jobs")
        with self.assertRaises(cp.CampaignError):  # no executor: no candidates to check against
            cp.confirm_submission(self.cdir, sub["id"], {j["attempt_id"]: j["job_id"] for j in ex.accepted})
        cp.confirm_submission(self.cdir, sub["id"], {j["attempt_id"]: j["job_id"] for j in ex.accepted}, ex)
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
        self.assertEqual(statuses, {"abandoned"})  # not proof that the scheduler never accepted them
        ids = [c["id"] for c in self.manifest["chunks"]]
        cp.reset(self.cdir, ids, "abandoned after an interrupted submit")
        ex = ScriptedExecutor({})
        rep = cp.resubmit(self.cdir, ex, CONFIG, approved=True)
        self.assertEqual(sorted(rep["resubmitted"]), ids)
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])

    def test_a_refused_submission_is_recorded_as_not_submitted(self):
        with self.assertRaises(SubmitRefused):
            cp.submit(self.cdir, RefusingExecutor({}), CONFIG, approved=True)
        state = self.state()
        self.assertEqual(state["submissions"][-1]["status"], "not-submitted")
        self.assertIn("No such file", state["submissions"][-1]["reason"])
        self.assertEqual({c["status"] for c in cp.report(self.cdir)["chunks"].values()}, {"not-submitted"})

    def test_an_ambiguous_submission_stays_unconfirmed(self):
        # a lost response is never recorded as not submitted (N08, U09): it waits for a person to reconcile it
        ex = AmbiguousExecutor({})
        with self.assertRaises(SubmitAmbiguous):
            cp.submit(self.cdir, ex, CONFIG, approved=True)
        sub = self.state()["submissions"][-1]
        self.assertEqual(sub["status"], "intent")
        self.assertIn("Socket timed out", sub["ambiguous"])
        with self.assertRaises(cp.CampaignError) as err:
            cp.submit(self.cdir, ScriptedExecutor({}), CONFIG, approved=True)
        self.assertEqual(err.exception.code, "submit.unconfirmed")
        cp.confirm_submission(self.cdir, sub["id"], {j["attempt_id"]: j["job_id"] for j in ex.accepted}, ex)
        self.assertTrue(cp.poll(self.cdir, ex)["complete"])
        self.assertEqual(sum(1 for c in ex.calls if c[0] == "submit"), 1)

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


GATED_SUBMIT = """
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from core.partition import campaign as cp
from tests.core.partition_helpers import ScriptedExecutor
cdir, inside, go = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])

class Gated(ScriptedExecutor):
    def submit(self, plan):  # inside the locked submit: tell the test, then wait for its go file
        inside.write_text("in")
        deadline = time.time() + 120
        while not go.exists() and time.time() < deadline:
            time.sleep(0.01)
        return super().submit(plan)

ex = Gated({}) if inside.name != "-" else ScriptedExecutor({})
try:
    out = cp.submit(cdir, ex, {"max_attempts": 2, "resources": {"time": "00:10:00"}}, approved=True)
    print(json.dumps({"ok": True, "chunks": out.get("chunks", out.get("submitted")), "id": out.get("submission_id")}))
except cp.CampaignError as exc:
    print(json.dumps({"ok": False, "code": exc.code}))
"""


class IndependentClosureTests(unittest.TestCase):
    """sci-fix ROBUST-CAMPAIGN, axis C. Analytic oracle: the merged result of a whole campaign (scripted scheduler,
    the real runner per chunk) against closed forms computed here, not by engine merging: n = N, sum of 0..N-1 =
    N(N-1)/2, and the sum of the manifest's per-chunk seeds. The helper reference single_run() adds chunks with
    engine._sum, the function under test; these do not. Also a real two-process lock test: a second process's submit
    while the first is inside its locked submit is refused (campaign.locked), forced by files, not by timing."""

    def closed_form(self, manifest):
        n = manifest["n_items"]
        return {"n": n, "sum": n * (n - 1) // 2, "seed_sum": sum(c["seed"] for c in manifest["chunks"])}

    def test_merged_campaign_equals_the_closed_form(self):
        for n_items, chunk, seed in ((10, 4, 7), (1, 1, 1), (23, 23, 5), (37, 5, 3)):
            with self.subTest(n=n_items, chunk=chunk), tempfile.TemporaryDirectory() as td:
                cdir, manifest, _ = make_campaign(Path(td), n_items, chunk, seed)
                self.assertEqual(len({c["seed"] for c in manifest["chunks"]}), len(manifest["chunks"]))
                ex = ScriptedExecutor({})
                cp.submit(cdir, ex, CONFIG, approved=True)
                self.assertTrue(cp.poll(cdir, ex)["complete"])
                self.assertEqual(cp.merge(cdir)["merged"], self.closed_form(manifest))

    def test_interrupted_then_confirmed_campaign_equals_the_closed_form(self):
        """The fix's scenario (an interrupt after the scheduler accepted the jobs): after confirming them the merged
        result is the closed form, and the scheduler saw one submission (the pre-fix second submit sent the chunks
        again)."""
        with tempfile.TemporaryDirectory() as td:
            cdir, manifest, _ = make_campaign(Path(td), 19, 4, 9)
            ex = InterruptingExecutor({})
            with self.assertRaises(Interrupted):
                cp.submit(cdir, ex, CONFIG, approved=True)
            sub = json.loads((cdir / "state.json").read_text())["submissions"][-1]
            cp.confirm_submission(cdir, sub["id"], {j["attempt_id"]: j["job_id"] for j in ex.accepted}, ex)
            self.assertTrue(cp.poll(cdir, ex)["complete"])
            self.assertEqual(cp.merge(cdir)["merged"], self.closed_form(manifest))
            self.assertEqual(sum(1 for c in ex.calls if c[0] == "submit"), 1)

    def test_a_second_process_is_refused_while_the_first_is_inside_submit(self):
        import subprocess
        import sys

        plugin = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            cdir, manifest, _ = make_campaign(Path(td) / "c")
            script, inside, go = Path(td) / "gated.py", Path(td) / "inside", Path(td) / "go"
            script.write_text(GATED_SUBMIT)
            first = subprocess.Popen([sys.executable, str(script), str(plugin), str(cdir), str(inside), str(go)],
                                     cwd=plugin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.time() + 120
                while not inside.exists() and first.poll() is None and time.time() < deadline:
                    time.sleep(0.01)
                self.assertTrue(inside.exists(), first.stderr.read() if first.poll() is not None else "timeout")
                second = subprocess.run([sys.executable, str(script), str(plugin), str(cdir), str(Path(td) / "-"),
                                         str(go)], cwd=plugin, capture_output=True, text=True, timeout=300)
                self.assertEqual(json.loads(second.stdout), {"ok": False, "code": "campaign.locked"}, second.stderr)
            finally:
                go.write_text("go")
                out, err = first.communicate(timeout=300)
            done = json.loads(out)
            self.assertTrue(done["ok"], err)
            self.assertEqual((done["id"], sorted(done["chunks"])), ("s001", [c["id"] for c in manifest["chunks"]]))
            state = json.loads((cdir / "state.json").read_text())
            self.assertEqual([s["id"] for s in state["submissions"]], ["s001"])
            self.assertEqual({c: len(row["attempt_records"]) for c, row in state["chunks"].items()},
                             {c["id"]: 1 for c in manifest["chunks"]})
            after = subprocess.run([sys.executable, str(script), str(plugin), str(cdir), str(Path(td) / "-"), str(go)],
                                   cwd=plugin, capture_output=True, text=True, timeout=300)
            # the lock was released: a third submit runs (nothing left to submit)
            self.assertEqual(json.loads(after.stdout), {"ok": True, "chunks": [], "id": None}, after.stderr)


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

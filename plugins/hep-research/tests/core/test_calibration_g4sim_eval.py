"""The g4sim evaluator adapters/geant4/assets/g4sim_calib_eval.py (Part B sections 6.1, 6.6, 7.1, 11.4, 15.2,
15.3.19; phase 3, WP-B) on synthetic g4sim products, with g4sim's Python layers and no Geant4: registration with the
engine, node-0 reweighting with source-density/1 and the external-source rejection (section 17, S3/S4), the Birks
deterministic rerun from edep_by_dedx_class with its bound (D75), re-digitization through digitize.py on the
g4sim-digi-job/1 path with a job that passes calib_design's job check, common random numbers (section 15.2), independent
batches, and resimulation requests through ask/tell. Items that need a Geant4 run read the products of campaign p3-g4
under $SIMCAL_G4_PRODUCTS (calibration_phase3_g4.calo_evidence) and are skipped, saying so, when it is unset."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_fixtures as F  # noqa: E402
import calibration_g4sim_eval_fixtures as G  # noqa: E402
import calibration_phase3_g4 as P3  # noqa: E402
import g4sim_calib_eval as E  # noqa: E402
import g4sim_simulate as simulate  # noqa: E402

from core.calibration import contract as C  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import evaluator  # noqa: E402

EVAL = ROOT / "adapters" / "geant4" / "assets" / "g4sim_calib_eval.py"
N = 300


def make(batches=None, **kw):
    batches = batches or {"nominal": G.batch(101, 0, N, use="fit"), "ref": G.batch(102, 0, N, use="reference")}
    return evaluator.make(G.plan(batches, **kw))


class Registration(unittest.TestCase):
    def test_registered_by_the_adapter_only(self):
        self.assertIsInstance(make(), E.G4simEvaluator)
        code = (f"import sys; sys.path.insert(0, {str(ROOT)!r})\nfrom core.calibration import evaluator\ntry:\n"
                " evaluator.make({'evaluator': {'kind': 'g4sim'}})\nexcept evaluator.EvaluatorUnavailable:\n"
                " print('unavailable')")
        out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), "unavailable")              # core alone does not know g4sim

    def test_method_from_the_binding(self):
        e = make()
        self.assertEqual(e.methods, {"light_yield": "re-digitization", "gain": "re-digitization", "birks": "rerun",
                                     "beam_mean": "analytic-reweighting", "wrapping": "resimulation"})
        with self.assertRaises(DG.CheckError) as caught:                  # a plan method the binding does not allow
            make(methods={"wrapping": "re-digitization"})
        self.assertEqual(caught.exception.code, "evaluator.method")
        self.assertIsInstance(make(methods={"wrapping": "surrogate-model", "birks": "rerun"}), E.G4simEvaluator)

    def test_batches_must_be_independent(self):
        with self.assertRaises(DG.CheckError) as caught:                  # two uses on one seed and interval
            make({"nominal": G.batch(101, 0, 50, use="fit"), "val": G.batch(101, 25, 50, use="validation")})
        self.assertEqual(caught.exception.code, "evaluator.batches")
        self.assertIsInstance(make({"nominal": G.batch(101, 0, 50, use="fit"),
                                    "val": G.batch(101, 50, 50, use="validation")}), E.G4simEvaluator)


class NodeZero(unittest.TestCase):
    """Node-0 analytic reweighting and the external source (section 17 preconditions, S3/S4; section 15.3.19)."""

    def test_reweighting_with_source_density(self):
        e = make()
        r0, r = e.evaluate({}), e.evaluate({"beam_mean": 520.0})
        self.assertEqual(r["methods"], {"beam_mean": "analytic-reweighting"})
        self.assertNotIn("source", r0["node_diag"])
        k = r["names"].index("e_mean")
        sd = float(np.sqrt(r["V_MC"][k, k]))
        self.assertLess(abs(r["pred"][k] - 520.0), 4 * sd)               # the reweighted beam mean is the target's
        self.assertGreater(abs(r["pred"][k] - r0["pred"][k]), 4 * sd)
        self.assertLess(r["node_diag"]["source"]["n_eff"], N)
        self.assertEqual(r["missing_support_runs"], [])
        same = e.evaluate({"beam_mean": 500.0})                          # at the generation point every weight is 1
        np.testing.assert_allclose(same["pred"], r0["pred"])

    def test_external_source_is_rejected(self):
        d = G.documents()
        ext = {"density": "external", "path": "events.txt", "sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as folder:                        # g4sim reads the external source (S4) ...
            import hashlib
            (Path(folder) / "events.txt").write_text("0 11 500 0 0 0 0 0 1\n")
            ext["sha256"] = hashlib.sha256((Path(folder) / "events.txt").read_bytes()).hexdigest()
            self.assertEqual(simulate.resolved_external(ext, Path(folder))["density"], "external")
        c = F.contract()
        c["simulator"], c["source"] = "g4sim", ext                       # ... and the contract checker rejects it
        self.assertIn("source.external", {f["code"] for f in C.check(c)["findings"]})
        c["source"] = d["request"]["source"]                             # positive control: the analytic request
        self.assertFalse({"source.external", "source.density"} & {f["code"] for f in C.check(c)["findings"]})
        p = G.plan({"nominal": G.batch(101, 0, 20)})
        p["evaluator"]["documents"]["request"]["source"] = ext
        with self.assertRaises(DG.CheckError) as caught:                 # and the evaluator cannot reweight it
            evaluator.make(p)
        self.assertEqual(caught.exception.code, "evaluator.source_density")


class Birks(unittest.TestCase):
    """The deterministic rerun from edep_by_dedx_class (D75), section 15.2 synthetic ZDC item 2."""

    def test_rerun_is_deterministic_without_weights(self):
        e = make()
        r = e.evaluate({"birks": 0.15})
        self.assertEqual(r["methods"], {"birks": "rerun"})
        np.testing.assert_allclose(r["n_eff"], N)                       # no event weights: G4 does not apply
        tab = E.batch_tables(e.batches["nominal"], e.scorers)
        want = np.mean([sum(simulate.reweighted(rows, 0.15) for (ev, v), rows in tab["dedx"].items() if ev == i)
                        for i in range(N)])
        self.assertAlmostEqual(r["pred"][r["names"].index("vis_mean")], want, places=12)
        bound = np.mean([sum(simulate.reweighting_bound(rows, 0.15) for (ev, v), rows in tab["dedx"].items()
                             if ev == i) for i in range(N)])
        self.assertAlmostEqual(r["birks_bound_MeV"]["vis_mean"], bound, places=12)
        self.assertIn("kB-split-nominal", r["flags"])                    # downstream scintillation: P0 at the extremes
        self.assertEqual(e.evaluate({"birks": 0.1})["flags"], [])

    def test_birks_scales_the_scintillation_bins(self):
        e = make()
        lo, hi = e.evaluate({"birks": 0.05}), e.evaluate({"birks": 0.2})
        k = lo["names"].index("pe_mean")
        self.assertGreater(lo["pred"][k], hi["pred"][k])                 # more quenching, fewer photoelectrons

    def test_rerun_agrees_with_resimulation_at_the_new_birks(self):
        """Resimulation with the new k_B written into the detector-spec (the g4sim_runs 'kB-low', 'kB-centre', 'kB-high'
        of campaign p3-g4, $SIMCAL_G4_PRODUCTS): the evaluator's rerun at that k_B agrees with the run's edep_visible,
        per (event, volume) and in vis_mean, within the D75 bound; both fall as k_B grows."""
        rows = P3.calo_evidence("zdc-birks-rerun")["rows"]
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertEqual(r["within"], r["pairs"], r)
            self.assertTrue(r["mean_within"], r)
            self.assertLessEqual(abs(r["mean_rerun"] - r["mean_run"]), r["mean_bound"], r)
        by_kb = sorted(rows, key=lambda r: r["birks"])
        for key in ("mean_rerun", "mean_run"):
            self.assertTrue(all(a[key] > b[key] for a, b in zip(by_kb, by_kb[1:])), key)


class Redigitization(unittest.TestCase):
    """Re-digitization of response parameters on the g4sim-digi-job/1 path (section 11.4 Table 2)."""

    def test_job_is_built_from_and_passes_the_documents_check(self):
        e = make()
        docs = DG.apply_theta(e.documents, e.plan, {"light_yield": 230.0})
        job = DG.job_from_documents(docs["pipeline"], docs["maps"]["light"], "zdc", [0, 1], 101)
        self.assertEqual(job["stage"]["light_yield_per_MeV"], 230.0)
        self.assertEqual((job["run_seed"], job["replica"]), (101, 0))     # run_seed = logical_run_seed, replica 0
        plan = {"evaluations": [{"run_id": "fit", "use": "fit", "logical_run_seed": 101, "first_event": 0,
                                 "events": N}], "node_binding": e.plan["node_binding"],
                "digi_jobs": [{"job": job, "evaluation": "fit", "readout": "zdc", "map": "light",
                               "theta": {"light_yield": 230.0}}]}
        self.assertEqual(DG.digi_job_findings(plan, e.documents), [])
        r = e.evaluate({"light_yield": 230.0})
        self.assertEqual(r["seeds"], {"logical_run_seed": 101, "first_event": 0, "events": N})

    def test_response_parameters_move_the_prediction(self):
        e = make()
        r0, r1 = e.evaluate({}), e.evaluate({"light_yield": 240.0})
        k = r0["names"].index("pe_mean")
        self.assertGreater(r1["pred"][k], r0["pred"][k])
        self.assertEqual(r0["pred"][r0["names"].index("vis_mean")], r1["pred"][r1["names"].index("vis_mean")])

    def test_common_random_numbers(self):
        """Section 15.2 g4sim (common random numbers): the same Geant4 events and Philox key at two theta give a
        difference with a smaller MC variance than two independent sets of events."""
        batches = {f"b{i}": G.batch(200 + i, 0, 120, use="toy-replica", set=i) for i in range(16)}
        e = make(batches)
        a = [e.evaluate({"light_yield": 200.0}, seeds={"batch": f"b{i}"}) for i in range(16)]
        b = [e.evaluate({"light_yield": 215.0}, seeds={"batch": f"b{i}"}) for i in range(16)]
        k = a[0]["names"].index("pe_mean")
        crn = np.array([b[i]["pred"][k] - a[i]["pred"][k] for i in range(16)])
        ind = np.array([b[(i + 1) % 16]["pred"][k] - a[i]["pred"][k] for i in range(16)])
        self.assertLess(crn.var(ddof=1), 0.25 * ind.var(ddof=1))
        np.testing.assert_allclose(e.evaluate({"light_yield": 200.0}, seeds={"batch": "b3"})["pred"], a[3]["pred"])

    def test_p0_against_full_simulation(self):
        """P0 of the light yield by re-digitization against a full g4sim_run plus response at theta (the light-yield
        extremes 'LY-low', 'LY-high' of campaign p3-g4, $SIMCAL_G4_PRODUCTS): the rows at the full runs come from
        transport, and P0 passes there and overall."""
        r = P3.calo_evidence("zdc-p0-response")["result"]
        self.assertEqual(r["status"], "passed", r["points"])
        full = [row for row in r["points"] if row["rerun_from"] == ["transport"]]
        self.assertEqual(sorted(row["point"]["light_yield"] for row in full), [180.0, 220.0])
        for row in full:
            self.assertIn("spot_check", row)
            self.assertEqual((row["failing"], row["missing_support_runs"]), ([], []), row)
            self.assertLess(row["max_ratio"], 1.0, row)


class AskTell(unittest.TestCase):
    """Resimulation requests (section 6.4, 7.1): run cards per design point, the state file, merged parts."""

    def test_requests_and_products(self):
        e = make()
        with self.assertRaises(E.ResimulationRequired):
            e.evaluate({"wrapping": 0.7})
        with tempfile.TemporaryDirectory() as folder:
            state = str(Path(folder) / "state.json")
            reqs = e.ask([{"wrapping": 0.6}, {"wrapping": 0.7}], state, series="s", study="zdc", events=40)
            self.assertEqual(len({(r["logical_run_seed"], r["first_event"], r["events"]) for r in reqs}), 1)
            self.assertEqual([r["detector"]["params"]["wrapping_mm"] for r in reqs], ["0.6", "0.7"])
            self.assertEqual(reqs[0]["run"]["run"]["logical_run_seed"], reqs[0]["logical_run_seed"])
            self.assertNotEqual(reqs[0]["detector_sha256"], reqs[1]["detector_sha256"])
            self.assertEqual(reqs[0]["run_sha256"], reqs[1]["run_sha256"])          # one card: only theta moves
            s = reqs[1]["logical_run_seed"]
            parts = [G.batch(s, 0, 25), G.batch(s, 25, 15)]
            with self.assertRaises(DG.CheckError):                                   # not the asked interval
                E.G4simEvaluator.tell(state, "1", "run-x", parts[:1])
            with self.assertRaises(DG.CheckError):                                   # parts that overlap
                E.G4simEvaluator.tell(state, "1", "run-x", [G.batch(s, 0, 25), G.batch(s, 20, 20)])
            rec = E.G4simEvaluator.tell(state, "1", "run-1", parts)
            self.assertEqual((rec["status"], rec["run_id"]), ("told", "run-1"))
            p = G.plan({"nominal": G.batch(101, 0, N)})
            p["evaluator"]["state"] = state
            r = evaluator.make(p).evaluate({"wrapping": 0.7})
            self.assertEqual((r["batch"], r["seeds"]["events"]), ("point:1", 40))
            with self.assertRaises(E.ResimulationRequired):
                evaluator.make(p).evaluate({"wrapping": 0.6})                        # asked, not told

    def test_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            d = Path(folder)
            plan = G.plan({"nominal": G.batch(101, 0, 50)})
            (d / "plan.json").write_text(json.dumps(plan))
            (d / "theta.json").write_text(json.dumps({"light_yield": 210.0}))
            out = subprocess.run([sys.executable, "-I", str(EVAL), "evaluate", "--plan", d / "plan.json", "--theta",
                                  d / "theta.json"], capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout)["methods"], {"light_yield": "re-digitization"})
            (d / "theta.json").write_text(json.dumps({"wrapping": 0.9}))
            out = subprocess.run([sys.executable, "-I", str(EVAL), "evaluate", "--plan", d / "plan.json", "--theta",
                                  d / "theta.json"], capture_output=True, text=True, timeout=120)
            self.assertEqual((out.returncode, json.loads(out.stdout)["status"]), (3, "incomplete"))
            bad = copy.deepcopy(plan)
            bad["evaluator"]["kind"] = "toy-detector"
            (d / "bad.json").write_text(json.dumps(bad))
            out = subprocess.run([sys.executable, "-I", str(EVAL), "evaluate", "--plan", d / "bad.json", "--theta",
                                  d / "theta.json"], capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()

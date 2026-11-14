"""The learned density ratio and G4-L (Part B sections 6.2, 8.2, phase 5; A25 on section 19-9): the classifier path
(cross-fitting, Platt calibration, prior-ratio correction), V_learn and V_learn^bias, learned_closure on the toy
evaluator, the post-hoc fixture (core/calibration/data/toy_posthoc.json), G4-L and P0 on the learned path. Each
negative test has a positive control on the same fixture. Section 15.3.1 G4-L: "no cross-fitting"; section 15.3.16:
a learned plan makes P0 and G4-L apply (the full-resimulation case is
test_calibration_design.Applicability.test_full_resimulation_only, rerun, not duplicated). Synthetic."""
from __future__ import annotations

import copy
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import chain, design, kernel_check, learned, linear, reweight, toy  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")
N = 10_000


def fixture(n=N, **over):
    c, p = toy.posthoc_fixture()
    c, p = copy.deepcopy(c), copy.deepcopy(p)
    p["evaluator"]["spec"]["runs"][0]["n"] = n
    p["evaluator"]["learned"].update(over)
    return c, p


def g4l(c, p, points=None):
    ev = E.make(p, c)
    d = linear.design(ev, c, p)
    pts = points or kernel_check.default_points(ev, c, p)
    return ev, d, pts, reweight.g4l_run(ev, c, d, pts)


class Fixture(unittest.TestCase):
    def test_post_hoc_node_makes_the_learned_ratio_the_candidate(self):
        """The toy detector of section 15.1 has no post-hoc node; this fixture's correction node is a samplable black
        box with stored inputs and outputs and post_hoc_correction, so the learned density ratio is a candidate."""
        c, p = toy.posthoc_fixture()
        ms = [m["method"] for m in chain.candidate_methods(c, p)["parameters"]["strength"]]
        self.assertIn("learned-density-ratio", ms)
        self.assertNotIn("analytic-reweighting", ms)
        c2 = copy.deepcopy(c)
        for nd in c2["stage_graph"]["nodes"]:
            nd["post_hoc_correction"] = False
        self.assertNotIn("learned-density-ratio",
                         [m["method"] for m in chain.candidate_methods(c2, p)["parameters"]["strength"]])

    def test_15_3_16_learned_plan_makes_p0_and_g4l_apply(self):
        a = design.applicability({"strength": "learned-density-ratio"})["gates"]
        self.assertEqual((a["P0"], a["G4-L"], a["G4"], a["P6"]),
                         ("applicable", "applicable", "not-applicable", "not-applicable"))
        a = design.applicability({"strength": "resimulation"})["gates"]          # control
        self.assertEqual((a["P0"], a["G4-L"]), ("not-applicable", "not-applicable"))


class Classifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.p = fixture()
        cls.ev = E.make(cls.p, cls.c)
        cls.tr = cls.ev.learned_ratio()

    def features(self):
        e = self.ev.nominal["runs"]["run"]["events"]
        return e["x"]["x"], e["correction"]["y"]

    def test_ratio_matches_the_true_kernel_ratio(self):
        x, y = self.features()
        kern = self.ev.model.runs["run"].kernels["correction"]
        for c1 in (0.0, 0.2):
            lr = self.tr.log_weights(np.stack([x, y], 1), {"strength": c1})
            tl = kern.true_log_ratio(x, y, c1, 0.1)
            self.assertLess(np.std(lr - tl), 0.3 * np.std(tl), c1)

    def test_ratio_is_one_at_the_generation_point(self):
        x, y = self.features()
        self.assertTrue(np.all(self.tr.log_weights(np.stack([x, y], 1), {"strength": 0.1}) == 0.0))
        r = self.ev.evaluate({"strength": 0.1})
        self.assertEqual(float(r["n_eff"][0]), float(N))

    def test_record_shows_cross_fitting_calibration_and_prior_ratio(self):
        rec = self.ev.learned_record()
        self.assertTrue(rec["cross_fitted"])
        self.assertEqual((rec["folds"], rec["calibration"], rec["prior_ratio_corrected"]), (5, "platt", True))
        self.assertTrue(all(rec["train_apply_disjoint"]) and rec["converged"])
        self.assertEqual(reweight.g4l_structural(rec, self.c), [])

    def test_ratio_outside_its_support_is_refused(self):
        """A ratio queried outside its training box is refused, never extrapolated (negative); inside it evaluates
        (control)."""
        with self.assertRaises(learned.OutsideSupport) as cm:
            self.ev.evaluate({"strength": 0.3})
        self.assertEqual(cm.exception.code, "learned.outside_support")
        self.assertTrue(np.isfinite(self.ev.evaluate({"strength": 0.2})["pred"]).all())
        r = reweight.g4l_run(self.ev, self.c, linear.design(self.ev, self.c, self.p),
                             [{"strength": 0.05}, {"strength": 0.15}, {"strength": 0.3}])
        self.assertEqual((r["status"], r["finding"]), ("rejected", "learned.outside_support"))

    def test_v_learn_parts(self):
        v = self.ev.v_learn({"strength": 0.2})
        self.assertEqual(v["repeats"], 5)
        np.testing.assert_allclose(v["V_learn"], v["V_learn_train"] + v["V_learn_bias"])
        np.testing.assert_allclose(v["V_learn_bias"], np.outer(v["bias"], v["bias"]))
        self.assertGreaterEqual(np.linalg.eigvalsh(v["V_learn_train"]).min(), -1e-15)
        cl = [self.ev.learned_closure(k, {"strength": 0.2}) for k in range(5)]
        np.testing.assert_allclose(v["bias"], np.mean([c["learned"]["pred"] for c in cl], 0) - cl[0]["direct"]["pred"])
        self.assertTrue(np.all(np.diag(v["V_learn_train"]) > 0))      # repeated trainings differ (new training MC)
        with self.assertRaises(learned.LearnedError):
            learned.v_learn([v["bias"]], v["bias"])

    def test_learned_closure_is_held_out(self):
        cl = self.ev.learned_closure(2, {"strength": 0.15})
        self.assertEqual((cl["fold"], cl["train_folds"], cl["sample"]), (2, [0, 1, 3, 4], "closure"))
        self.assertEqual(cl["direct"]["missing_support_runs"], [])


class G4L(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.p = fixture()
        cls.ev, cls.d, cls.pts, cls.good = g4l(cls.c, cls.p)

    def test_correct_ratio_passes(self):
        """Positive control of every G4-L negative below: the cross-fitted, calibrated ratio passes."""
        r = self.good
        self.assertEqual(r["status"], "passed", r["findings"])
        self.assertEqual((r["M"], len(r["points"])), (3, 3))
        self.assertIn("provisional-thresholds", r["flags"])

    def test_15_3_1_no_cross_fitting(self):
        """Section 15.3.1 G4-L: no cross-fitting (the weights applied to the events the classifier was trained on):
        refused structurally from the record's index sets (reading L5)."""
        c, p = fixture(folds=1)
        r = g4l(c, p, self.pts)[3]
        self.assertEqual(r["status"], "rejected")
        self.assertIn("g4l.no_cross_fitting", {f["code"] for f in r["findings"]})
        self.assertFalse(r["record"]["cross_fitted"])

    def test_uncalibrated_classifier(self):
        """A classifier trained with label smoothing and not calibrated: refused (structural) and its closure fails
        (statistical, the shrunk ratio under-corrects); with Platt calibration the same classifier passes."""
        c, p = fixture(calibration="none", label_smoothing=0.5)
        r = g4l(c, p, self.pts)[3]
        codes = {f["code"] for f in r["findings"]}
        self.assertEqual(r["status"], "rejected")
        self.assertTrue({"g4l.uncalibrated", "g4l.closure"} <= codes, codes)
        c, p = fixture(label_smoothing=0.5)
        self.assertEqual(g4l(c, p, self.pts)[3]["status"], "passed")

    def test_alpha_declared_in_the_contract(self):
        """Section 8.1: G4-L's alpha and multiple-comparison method are in the contract (Inferred); absent or looser
        than 0.01 is rejected, the fixture's declaration passes (control)."""
        rec = self.ev.learned_record()
        c = copy.deepcopy(self.c)
        del c["acceptance"]["gates"]
        self.assertEqual([f["code"] for f in reweight.g4l_structural(rec, c)], ["g4l.alpha_undeclared"])
        c["acceptance"]["gates"] = {"G4-L": {"alpha": 0.05, "multiple_comparison": "bonferroni"}}
        self.assertEqual([f["code"] for f in reweight.g4l_structural(rec, c)], ["g4l.alpha"])
        self.assertEqual(reweight.g4l_structural(rec, self.c), [])

    def test_prior_ratio_and_calibration_required_in_the_record(self):
        rec = self.ev.learned_record()
        for k, v, code in (("prior_ratio_corrected", False, "g4l.prior_ratio"), ("calibration", "none",
                                                                                "g4l.uncalibrated")):
            self.assertEqual([f["code"] for f in reweight.g4l_structural({**rec, k: v})], [code])

    def test_too_few_points(self):
        r = reweight.g4l_run(self.ev, self.c, self.d, self.pts[:2])
        self.assertIn("g4l.too_few_points", {f["code"] for f in r["findings"]})


class P0OnTheLearnedPath(unittest.TestCase):
    def test_p0_passes_with_the_correct_ratio_and_fails_uncalibrated(self):
        """P0 applies to the learned density ratio (section 8.1): the cross-fitted, calibrated ratio passes against
        resample + evaluate_from; the uncalibrated one fails (negative)."""
        for over, want in (({}, "passed"), ({"calibration": "none", "label_smoothing": 0.5}, "failed")):
            c, p = fixture(**over)
            ev = E.make(p, c)
            d = linear.design(ev, c, p)
            r = kernel_check.p0(ev, c, p, d, kernel_check.default_points(ev, c, p), seed=5)
            self.assertEqual(r["status"], want, over)


class SBIBoundary(unittest.TestCase):
    """A25 (section 19-9): a learned ratio is the density ratio of one post-hoc node, used only to reweight stored
    MC events; learning the likelihood or posterior of theta from observables is refused."""

    def refused(self, code, **over):
        c, p = fixture(**over)
        with self.assertRaises(learned.LearnedError) as cm:
            E.make(p, c)
        self.assertEqual(cm.exception.code, code)

    def test_sbi_targets_are_refused(self):
        self.refused("learned.sbi_refused", target="posterior")
        self.refused("learned.sbi_refused", target="likelihood")
        self.refused("learned.sbi_refused", use="fit-theta")
        self.refused("learned.sbi_refused", features={"inputs": ["x"], "outputs": ["y"], "observables": ["y_mean"]})
        self.refused("learned.sbi_refused", features={"inputs": ["y_mean"], "outputs": ["y"]})
        c, p = fixture()                                                     # control
        self.assertEqual(learned.check_spec(p["evaluator"]["learned"], {"strength": ["correction"]},
                                            ({"x"}, {"y"}), c, p["methods"]), [])

    def test_one_post_hoc_node_only(self):
        self.refused("learned.one_node", node=["correction", "x"])
        c, p = fixture()
        c["stage_graph"]["nodes"][1]["post_hoc_correction"] = False
        ev = E.make(p, c)
        r = reweight.g4l_run(ev, c, {"names": ["y_mean", "y_width"]}, [{}])
        self.assertEqual((r["status"], r["finding"]), ("rejected", "learned.not_post_hoc"))

    def test_learned_method_without_a_spec(self):
        c, p = fixture()
        del p["evaluator"]["learned"]
        with self.assertRaises(ValueError):
            E.make(p, c)


class S1Driver(unittest.TestCase):
    """The S1 driver (tests/core/calibration_phase5_g4l.py): the task table, the local smoke and the decision rule,
    where a failing configuration is reported failed (negative) next to a passing control."""

    def test_task_table_and_rule(self):
        import calibration_phase5_g4l as X
        reps = [r for t in X.TASKS for r in range(t["r0"], t["r0"] + t["reps"])]
        self.assertEqual(reps, list(range(X.REPS)))
        self.assertEqual((X.MAX_FALSE_ALARMS, X.EVENTS), (16, 40_000))
        self.assertEqual(len({X._seed(r, j) for r in range(50) for j in range(4)}), 200)

    def test_judge(self):
        import calibration_phase5_g4l as X

        def rows(n_fail, extra=()):
            return [{"r": r, "status": "failed" if r < n_fail else "passed"} for r in range(1000)] + list(extra)
        self.assertTrue(X.judge(rows(16))["passed"])                                  # control
        self.assertFalse(X.judge(rows(17))["passed"])                                 # negative
        bad = rows(0)
        bad[3] = {"r": 3, "status": "error"}
        j = X.judge(bad)
        self.assertEqual((j["complete"], j["passed"], j["not_judged"]), (False, False, [3]))
        self.assertFalse(X.judge(rows(0)[:999])["passed"])                            # a missing repetition

    def test_local_smoke(self):
        import contextlib
        import io as _io
        import json
        import tempfile

        import calibration_phase5_g4l as X
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "local.json"
            with contextlib.redirect_stdout(_io.StringIO()):
                self.assertEqual(X.main(["--local", "--out", str(out)]), 0)
            rep = json.loads(out.read_text())
        self.assertEqual((rep["label"], rep["result"]["repetitions"]), ("smoke", 2))
        self.assertEqual(rep["result"]["not_judged"], [])
        self.assertIn("provisional-thresholds", rep["flags"])


class DefaultOff(unittest.TestCase):
    def test_plans_without_a_learned_ratio_are_untouched(self):
        c, p = H.gaussian_chain(n=2000)
        ev = E.make(p)
        r = ev.evaluate({"mu": 0.3})
        self.assertIsNone(r["V_learn"])
        self.assertEqual(ev._learned, {})
        with self.assertRaises(NotImplementedError):
            ev.learned_closure(0)


if __name__ == "__main__":
    unittest.main()

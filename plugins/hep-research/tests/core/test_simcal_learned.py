"""The learned density ratio and G4-L (Part B sections 6.2, 8.2, phase 5; A25 on section 19-9): the classifier path
(cross-fitting, Platt calibration, prior-ratio correction), V_learn and V_learn^bias, learned_closure on the toy
evaluator, the post-hoc fixture (core/simcal/data/toy_posthoc.json), G4-L and P0 on the learned path. Each
negative test has a positive control on the same fixture. Section 15.3.1 G4-L: "no cross-fitting"; section 15.3.16:
a learned plan makes P0 and G4-L apply (the full-resimulation case is
test_simcal_design.Applicability.test_full_resimulation_only, rerun, not duplicated). Synthetic."""
from __future__ import annotations

import copy
import math
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import simcal_phase1 as H  # noqa: E402
from core.simcal import chain, design, kernel_check, learned, linear, reweight, toy  # noqa: E402
from core.simcal import evaluator as E  # noqa: E402

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

    @staticmethod
    def clip_violations(tr, F, theta, bounds) -> list:
        """The check of the log-ratio clip (A31): per fold k, no evaluated log ratio outside bounds[k], the fold's
        training range [lr_lo, lr_hi]. Returns the folds that violate it."""
        return [k for k, (lo, hi) in enumerate(bounds)
                if np.any((tr.log_weights(F, theta, fold=k) < lo - 1e-12) | (tr.log_weights(F, theta, fold=k) > hi + 1e-12))]

    def test_log_ratio_clip(self):
        """Positive: log ratios inside the fold's training range are unchanged (equal to the unclipped evaluation),
        and an out-of-range point's log ratio sits at the bound. Negative: the same fold models without the recorded
        range (the code before A31) give that point a log ratio beyond the bound, and the check catches it."""
        import copy as _copy
        x, y = self.features()
        F = np.stack([x, y], 1)
        th = {"strength": 0.2}
        fm = self.tr.folds[0]
        self.assertLess(fm.lr_lo, fm.lr_hi)
        raw = _copy.deepcopy(self.tr)
        for f in raw.folds:
            f.lr_lo = f.lr_hi = None
        a, b = self.tr.log_weights(F, th, fold=0), raw.log_weights(F, th, fold=0)
        inside = (b > fm.lr_lo) & (b < fm.lr_hi)
        self.assertGreater(inside.mean(), 0.99)
        np.testing.assert_array_equal(a[inside], b[inside])
        far = np.array([[x.max() + 4.0, y.min() - 8.0], [x.min() - 4.0, y.max() + 8.0]])
        cl, un = self.tr.log_weights(far, th, fold=0), raw.log_weights(far, th, fold=0)
        out = (un < fm.lr_lo) | (un > fm.lr_hi)
        self.assertTrue(out.any(), un)                                      # the old code's value exceeds the bound
        np.testing.assert_allclose(cl[out], np.clip(un[out], fm.lr_lo, fm.lr_hi))
        bounds = [(f.lr_lo, f.lr_hi) for f in self.tr.folds]
        self.assertEqual(self.clip_violations(self.tr, far, th, bounds), [])               # positive
        self.assertIn(0, self.clip_violations(raw, far, th, bounds))                       # negative: caught

    def test_v_learn_parts(self):
        """V_learn = V_train + V_bias; b = the fold-averaged closure difference at theta minus the same at theta_0
        (A29: was the difference at theta alone, so V_bias = b b^T exactly); V_bias = b b^T - the covariance of b's
        MC noise, clipped to positive semi-definite."""
        v = self.ev.v_learn({"strength": 0.2})
        self.assertEqual(v["repeats"], 5)
        np.testing.assert_allclose(v["V_learn"], v["V_learn_train"] + v["V_learn_bias"])
        lam, U = np.linalg.eigh(np.outer(v["bias"], v["bias"]) - v["V_learn_bias_noise"])
        np.testing.assert_allclose(v["V_learn_bias"], (U * np.clip(lam, 0, None)) @ U.T, atol=1e-18)
        self.assertGreaterEqual(np.linalg.eigvalsh(v["V_learn_bias"]).min(), -1e-15)
        self.assertGreaterEqual(np.linalg.eigvalsh(v["V_learn_train"]).min(), -1e-15)
        cl = [self.ev.learned_closure(k, {"strength": 0.2}) for k in range(5)]
        raw = np.mean([c["learned"]["pred"] for c in cl], 0) - cl[0]["direct"]["pred"]
        np.testing.assert_allclose(v["bias_raw"], raw)
        c0 = self.ev.learned_closure(0, {"strength": 0.1})
        np.testing.assert_allclose(v["bias"], raw - (c0["learned"]["pred"] - c0["direct"]["pred"]))
        self.assertTrue(np.all(np.diag(v["V_learn_train"]) > 0))      # repeated trainings differ (new training MC)
        with self.assertRaises(learned.LearnedError):
            learned.v_learn([v["bias"]], v["bias"])

    def test_v_learn_bias_vanishes_at_the_generation_point(self):
        """At theta_0 the ratio is 1 by construction, so V_learn^bias is 0 there (positive, A29); the uncorrected
        closure difference (the construction before A29) is the closure comparison's own MC noise, not 0 (negative)."""
        v = self.ev.v_learn({"strength": 0.1})
        self.assertLess(float(np.abs(v["bias"]).max()), 1e-14)
        self.assertLess(float(np.abs(v["V_learn_bias"]).max()), 1e-25)
        self.assertGreater(float(np.abs(v["bias_raw"]).max()), 1e-4)

    def test_v_learn_bias_noise_subtraction(self):
        """learned.v_learn with bias_noise: over draws b ~ N(delta, N) with delta delta^T ~ N, the mean V_bias keeps
        less than 0.7 tr N above delta delta^T (positive; the clipping keeps about 0.6 here), while b b^T (the
        construction before A29) adds all of N (negative)."""
        rng = np.random.default_rng(5)
        delta, N = np.array([0.02, -0.01]), np.array([[4e-4, 1e-4], [1e-4, 2e-4]])
        P = rng.normal(size=(3, 2))
        Lc = np.linalg.cholesky(N)
        corrected, uncorrected = [], []
        for _ in range(4000):
            b = delta + Lc @ rng.standard_normal(2)
            corrected.append(learned.v_learn(P, b, N)["V_learn_bias"])
            uncorrected.append(learned.v_learn(P, b)["V_learn_bias"])
        t0 = float(delta @ delta)
        self.assertLess(abs(np.trace(np.mean(corrected, 0)) - t0), 0.7 * np.trace(N))
        self.assertGreater(np.trace(np.mean(uncorrected, 0)) - t0, 0.9 * np.trace(N))

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


    def test_15_3_1_no_cross_fitting_is_caught_by_the_record_not_the_closure(self):
        """A33 (review F4): G4-L's statistical part is the held-out closure of section 7.1 (learned_closure: the
        difference on the held-out sample), whose events no classifier saw whatever F, so it cannot see a ratio
        applied to its own training events: with F = 1 every closure point passes the bound (shown, the statistical
        part is blind) and only the record check rejects. The record check reads the index sets: a record that
        declares cross_fitted but whose train/apply sets overlap, or that lacks them, is refused (negative); the real
        cross-fitted record passes (control)."""
        c, p = fixture(folds=1)
        r = g4l(c, p, self.pts)[3]
        self.assertEqual([f["code"] for f in r["findings"]], ["g4l.no_cross_fitting"])
        self.assertTrue(all(not row["failing"] for row in r["points"]), r["points"])     # blind statistically
        rec = self.ev.learned_record()
        self.assertEqual(reweight.g4l_structural(rec), [])                                 # control
        for bad in ({**rec, "train_apply_disjoint": [True] * 4 + [False]},               # declared, sets overlap
                    {k: v for k, v in rec.items() if k != "train_apply_disjoint"},        # no index sets
                    {**rec, "train_apply_disjoint": [True] * 3}):                          # not one per fold
            self.assertEqual([f["code"] for f in reweight.g4l_structural(bad)], ["g4l.no_cross_fitting"])


class PriorRatio(unittest.TestCase):
    """Section 6.2 prior-ratio correction with unequal class sizes (A33, review F5: with the default design n_1 = n_0
    and the correction is 0). class1_fraction 0.25 keeps a quarter of the class-1 calibration rows: log r =
    logit' - log(n_1/n_0) must match the true kernel log ratio in level (mean difference) and the weights must keep
    E_0[r] = 1. Positive: the correct correction (and the balanced default). Negatives: a sign error injected into the
    training (log(n_0/n_1)) and no correction both shift log r by a constant, and both are caught."""

    TOL = 0.05

    def level(self, patch=False, **over):
        from unittest import mock
        c, p = fixture(**over)
        ev = E.make(p, c)
        if patch:
            class SignError:
                @staticmethod
                def log(v):
                    return -math.log(v)
            with mock.patch.object(learned, "math", SignError):
                tr = ev.learned_ratio()
        else:
            tr = ev.learned_ratio()
        e = ev.nominal["runs"]["run"]["events"]
        x, y = e["x"]["x"], e["correction"]["y"]
        kern = ev.model.runs["run"].kernels["correction"]
        out = []
        for c1 in (0.0, 0.2):
            lr = tr.log_weights(np.stack([x, y], 1), {"strength": c1})
            out.append((abs(float(np.mean(lr - kern.true_log_ratio(x, y, c1, 0.1)))),
                        abs(float(np.mean(np.exp(lr))) - 1.0)))
        return tr, out

    def ok(self, out):
        return all(a < self.TOL and b < self.TOL for a, b in out)

    def test_unequal_classes(self):
        tr, out = self.level(class1_fraction=0.25)
        self.assertTrue(all(abs(f.log_prior - math.log(0.25)) < 0.01 for f in tr.folds))   # the classes differ
        self.assertTrue(self.ok(out), out)                                                   # positive
        self.assertTrue(self.ok(self.level()[1]))                                            # balanced control
        _, sign = self.level(patch=True, class1_fraction=0.25)
        self.assertFalse(self.ok(sign), sign)                                                # sign error: caught
        _, none = self.level(class1_fraction=0.25, prior_ratio=False)
        self.assertFalse(self.ok(none), none)                                                # no correction: caught

    def test_fraction_is_checked(self):
        for v, code in ((0.0, "learned.spec"), (1.5, "learned.spec")):
            self.assertIn(code, {f["code"] for f in learned.check_spec({**fixture()[1]["evaluator"]["learned"],
                                                                         "class1_fraction": v})})
        self.assertTrue(learned.check_spec({**fixture()[1]["evaluator"]["learned"], "class1_fraction": 0.5,
                                            "calibration": "none"}))                         # needs Platt
        self.assertEqual(learned.check_spec({**fixture()[1]["evaluator"]["learned"], "class1_fraction": 0.5}), [])


class DesignWithVLearn(unittest.TestCase):
    """Sections 7.1, 2.1, 8.1 (A33, review F8): on the learned path `evaluate` returns V_learn (lazily: v_learn at the
    evaluation's point), and linear.design puts it in V at theta_ref, so sigma_tot^design is the Asimov Sigma_theta
    with V_G = V_data + V_MC + V_learn (positive). Negative: the design with V_learn hidden (the construction before
    A33) has a smaller sigma_tot^design; a plan without a learned ratio gets V_learn None (control)."""

    LIGHT = {"folds": 2, "repeats": 3, "training_points": 4, "degree": 2}
    REF = {"strength": 0.15}         # the prior centre 0.1 is the generation point, where V_learn = 0 by construction

    @classmethod
    def setUpClass(cls):
        cls.c, cls.p = fixture(n=4000, **cls.LIGHT)
        cls.ev = E.make(cls.p, cls.c)

    def test_evaluate_carries_v_learn(self):
        r = self.ev.evaluate({"strength": 0.15})
        self.assertIsNotNone(r["V_learn"])
        np.testing.assert_array_equal(linear.v_learn_of(r), self.ev.v_learn({"strength": 0.15})["V_learn"])
        self.assertIsNone(E.make(H.gaussian_chain(n=2000)[1]).evaluate({"mu": 0.3})["V_learn"])     # control

    def test_sigma_tot_design_includes_v_learn(self):
        d = linear.design(self.ev, self.c, self.p, theta_ref=self.REF)
        g = linear.to_link_delta(d["mu"], d["links"])
        v = self.ev.v_learn(d["theta_ref"], d["names"])["V_learn"]
        np.testing.assert_allclose(d["V_learn"], v * np.outer(g, g), rtol=1e-12)
        op = linear.operator(d["J"], d["V_data"], d["V_MC"], V_learn=d["V_learn"])
        np.testing.assert_allclose(d["sigma_tot"], op["sigma_tot"], rtol=1e-10)
        ev = self.ev

        class Hidden:                                  # the construction before A33: V_learn not returned
            def __getattr__(self, k):
                return getattr(ev, k)

            def evaluate(self, theta, **kw):
                return dict(ev.evaluate(theta, **kw), V_learn=None)
        d0 = linear.design(Hidden(), self.c, self.p, theta_ref=self.REF)
        self.assertNotIn("V_learn", d0)
        self.assertTrue(np.all(d0["sigma_tot"] < d["sigma_tot"]), (d0["sigma_tot"], d["sigma_tot"]))
        dc = linear.design(self.ev, self.c, self.p)          # at the prior centre (= theta_0): V_learn = 0
        self.assertLess(float(np.abs(dc["V_learn"]).max()), 1e-25)


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
    """The S1 driver (tests/core/simcal_phase5_g4l.py): the task table, the local smoke and the decision rule,
    where a failing configuration is reported failed (negative) next to a passing control."""

    def test_task_table_and_rule(self):
        import simcal_phase5_g4l as X
        reps = [r for t in X.TASKS for r in range(t["r0"], t["r0"] + t["reps"])]
        self.assertEqual(reps, list(range(X.REPS)))
        self.assertEqual((X.MAX_FALSE_ALARMS, X.EVENTS), (16, 40_000))
        self.assertEqual(len({X._seed(r, j) for r in range(50) for j in range(4)}), 200)

    def test_judge(self):
        import simcal_phase5_g4l as X

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

        import simcal_phase5_g4l as X
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "local.json"
            with contextlib.redirect_stdout(_io.StringIO()):
                self.assertEqual(X.main(["--local", "--out", str(out)]), 0)
            rep = json.loads(out.read_text())
        self.assertEqual((rep["label"], rep["result"]["repetitions"]), ("smoke", 2))
        self.assertEqual(rep["result"]["not_judged"], [])
        self.assertIn("provisional-thresholds", rep["flags"])


class TaskEnvironment(unittest.TestCase):
    """A33 (review F10): a merged study file records the tasks' Python, NumPy and file hashes (task_environment),
    besides the merging process's provenance; agreeing tasks give one set (positive), a task with another NumPy
    is reported as disagreeing (negative). Reported only: no study rule changes."""

    def merged(self, numpys):
        import json
        import tempfile

        import simcal_phase5_g4l as X
        tasks = [{"r0": i, "reps": 1} for i in range(len(numpys))]
        with tempfile.TemporaryDirectory() as d:
            for i, v in enumerate(numpys):
                prov = {"commit": "c" * 40, "dirty": False, "python": "3.13.18", "numpy": v, "sha256": {"f": "a"}}
                (Path(d) / f"task_{i:04d}.json").write_text(json.dumps(
                    {"task": i, "rows": [{"r": i, "status": "passed"}], "seconds": 1.0, "provenance": prov}))
            return X.merge(Path(d), Path(d) / "merged.json", tasks, reps=len(numpys))

    def test_task_environment(self):
        rep = self.merged(["2.4.6", "2.4.6"])
        te = rep["task_environment"]
        self.assertEqual((te["python"], te["numpy"], te["agree"], te["sha256"], te["n_tasks"]),
                         (["3.13.18"], ["2.4.6"], True, {"f": "a"}, 2))
        self.assertEqual(rep["provenance"]["numpy"], np.__version__)            # the merger's, kept apart
        te = self.merged(["2.4.6", "2.2.2"])["task_environment"]
        self.assertEqual((te["numpy"], te["agree"], te["sha256"]), (["2.2.2", "2.4.6"], False, None))


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

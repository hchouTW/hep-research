"""The phase-2 items of calib_design (Part B sections 2.1, 6.6, 8.2 note 3, 9.3, 9.4; phase 2, WP4)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import design_noise as DN  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402


class BJ(unittest.TestCase):
    def test_formula_matches_simulation(self):
        """MC noise of the nominal varying with theta (e = e0 (1 + g theta)): the bias of the fit with V fixed equals
        b_J within its simulation error (section 8.2 note 3, en/compute-19-13.md)."""
        rng = np.random.default_rng(0)
        cfg = T.linear_config(n=20, d=2, mc_ratio=0.3)
        g = rng.normal(size=(20, 2)) * 0.6
        cfg.e_scale = g
        truth = np.array([0.5, -0.3])
        B = []
        for s in range(1500):
            p = T.make(cfg, truth, data_seed=10 + s, mc_seed=50_000 + s)
            B.append(F.iterate(p, T.initial_beta(p), lndet=False).beta[:2] - truth)
        B = np.array(B)
        W = np.linalg.inv(cfg.V_data + cfg.V_MC)
        Ks = [np.diag(g[:, l]) @ cfg.V_MC @ np.diag(1 + g @ truth) for l in range(2)]
        pred = DN.b_J(cfg.J, W, Ks)
        se = B.std(0) / np.sqrt(len(B))
        self.assertTrue(np.all(np.abs(B.mean(0) - pred) < 3.5 * se + 0.005))

    def test_p5_item(self):
        rng = np.random.default_rng(1)
        J = rng.normal(size=(20, 2))
        W = np.eye(20)
        zero = {"J": J, "W": W, "K": [np.zeros((20, 20))] * 2, "sigma_tot": [0.2, 0.2]}
        self.assertTrue(DN.p5_b_J([zero])["passed"])            # K_l = 0: the item passes
        K = [np.eye(20) * 0.02, np.eye(20) * -0.03]
        big = {"J": J, "W": W, "K": K, "sigma_tot": np.sqrt(np.diag(np.linalg.inv(J.T @ J)))}
        r = DN.p5_b_J([big])
        self.assertFalse(r["passed"])
        self.assertEqual(r["finding"], "p5.b_J")
        self.assertGreater(r["increase_mc_factor"], 1.0)


class SigmaBoot(unittest.TestCase):
    def setUp(self):
        cfg = T.linear_config(n=30, d=3)
        cfg.bootstrap_B = 1500
        self.p = T.make(cfg, [0.5, -0.3, 1.0], 3, 4)
        self.Sd = np.linalg.inv(cfg.J.T @ np.linalg.inv(cfg.V_data) @ cfg.J)

    def test_estimate_size_and_w(self):
        """Sigma_boot ~ (p - d) / B Sigma_data; nu_b = 50; w = 0.891 with all 60 converged (eps-hat+ = 1/61)."""
        sb = DN.sigma_boot(self.p, self.p.truth, 7)
        self.assertEqual((sb["status"], sb["nu_b"]), ("ok", 50))
        self.assertAlmostEqual(sb["w"], 0.891, places=3)
        ratio = np.trace(sb["Sigma_boot"][:3, :3]) / np.trace(self.Sd)
        self.assertAlmostEqual(ratio, 27 / 1500, delta=0.3 * 27 / 1500)
        self.assertTrue(DN.p5_sigma_boot(sb["Sigma_boot"][:3, :3], sb["w"], self.Sd)["passed"])

    def test_asimov_and_size_rules(self):
        with self.assertRaises(DN.DesignError):
            DN.sigma_boot(self.p, self.p.truth, 7, source="asimov")
        with self.assertRaises(DN.DesignError):
            DN.sigma_boot(self.p, self.p.truth, 7, N_t=5)

    def test_p5_negative_control(self):
        """Sigma_boot = 0.095 Sigma_data with w = 0.891 satisfies Sigma_boot <= f Sigma_data but must fail
        (section 15.3.9)."""
        r = DN.p5_sigma_boot(0.095 * self.Sd, 0.891, self.Sd)
        self.assertFalse(r["passed"])
        self.assertEqual(r["finding"], "p5.sigma_boot")


class P7(unittest.TestCase):
    def test_modes_and_paths(self):
        self.assertEqual(DN.p7("none", 3, {}, "analytic")["status"], "not-applicable")
        self.assertEqual(DN.p7("holdout", 0, {}, "analytic")["status"], "no-testable-direction")
        rng = np.random.default_rng(2)
        ok = DN.p7("holdout", 5, {"a": 30 + rng.normal(size=50)}, "analytic")
        self.assertEqual(ok["status"], "passed")
        low = DN.p7("holdout", 5, {"a": 6 + rng.normal(size=50)}, "analytic")
        self.assertEqual(low["finding"], "p7.insufficient_power")
        inc = DN.p7("holdout", 5, {"a": None}, "analytic")
        self.assertEqual(inc["status"], "incomplete")

    def test_toy_path(self):
        good = DN.p7("cross-validation", 5, {}, "toy", toy_results={"a": {"rejections": 960, "n": 1000, "X": 0}})
        self.assertEqual(good["status"], "passed")
        bad = DN.p7("cross-validation", 5, {}, "toy", toy_results={"a": {"rejections": 700, "n": 1000, "X": 0}})
        self.assertEqual(bad["status"], "failed")
        rt = DN.p7("cross-validation", 5, {}, "toy", toy_results={"a": {"status": "incomplete",
                                                                       "finding": "validate.ratio_test"}})
        self.assertEqual((rt["status"], rt["finding"]), ("incomplete", "p7.ratio_test"))

    def test_parameter_shift_alternative(self):
        """nu_k = 2 declared as an alternative hypothesis is rejected (section 15.3.1 P7)."""
        self.assertTrue(DN.alternative_is_parameter_shift({"form": "parameter-shift", "shift": {"nu_0": 2}}))
        self.assertFalse(DN.alternative_is_parameter_shift({"form": "discrete-model", "model": "FTFP"}))


class Folds(unittest.TestCase):
    def test_rules(self):
        contract = {"observables": [{"name": "t", "derived_from": ["p1", "p2"]}, {"name": "p1"}, {"name": "p2"}],
                    "validation": {"N_dc": [{"n": {"a": 1, "b": -1}}]}}
        self.assertEqual(DN.fold_split_check(contract, {"t": 0, "p1": 0, "p2": 0, "a": 1, "b": 1}), [])
        codes = {f["code"] for f in DN.fold_split_check(contract, {"t": 0, "p1": 1, "p2": 0, "a": 1, "b": 0})}
        self.assertEqual(codes, {"design.fold_splits_derived", "design.fold_splits_N_dc"})
        shape = DN.fold_split_check({"observables": []}, {"s[0]": 0, "s[1]": 1})
        self.assertEqual(shape[0]["code"], "design.fold_splits_shape")

    def test_fold_p3(self):
        """The only rows constraining a parameter form a fold by themselves: that training fold fails P3, the split is
        rejected (section 15.3.8)."""
        cfg = T.linear_config(n=16, d=2)
        cfg.J[4:, 1] = 0.0                                  # only rows 0..3 constrain t1
        cfg.J[:4, 1] = [2.0, -2.0, 2.5, -1.5]
        p = T.make(cfg, [0.5, -0.3], 3, 4)
        bad = DN.fold_p3(p, [np.arange(0, 4), np.arange(4, 10), np.arange(10, 16)], p.truth)
        self.assertEqual(bad[0]["code"], "design.fold_p3")
        ok = DN.fold_p3(p, [np.array([0, 4, 5, 6, 7]), np.array([1, 8, 9, 10, 11]),
                           np.array([2, 3, 12, 13, 14, 15])], p.truth)
        self.assertEqual(ok, [])


class Practices(unittest.TestCase):
    def test_rejected_plans(self):
        codes = lambda plan: {f["code"] for f in DN.practice_findings(plan)}  # noqa: E731
        self.assertEqual(codes({"toys": {"construction": "nominal-truth-single-replica"}}),
                         {"design.toy_single_replica"})
        self.assertEqual(codes({"toys": {"construction": "philox-only"}}), {"design.toy_philox_only"})
        self.assertEqual(codes({"toys": {"construction": "parametric-gaussian"}}), {"design.toy_parametric_mc"})
        self.assertEqual(codes({"bootstrap": {"reuse_by_reweighting": True}}), {"design.bootstrap_reweighted"})
        self.assertEqual(codes({"g8": {"run": True, "fit_mc": "shared"}}), {"design.g8_shared_mc"})
        self.assertEqual(codes({"toys": {"construction": "full"}}), set())

    def test_seed_independence(self):
        self.assertEqual(DN.seed_independence({"toys": [(1, 0), (1, 1)], "g8": [(2, 0)]}), [])
        rep = DN.seed_independence({"toys": [(1, 0), (1, 1)], "chat": [(1, 1)]})
        self.assertEqual(rep[0]["code"], "design.seed_overlap")


if __name__ == "__main__":
    unittest.main()

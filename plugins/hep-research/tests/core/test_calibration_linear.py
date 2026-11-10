"""The design-stage fit operator A for Gaussian blocks (Part B sections 6.7, 8.1, 9.2; phase 1)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration import linear  # noqa: E402

rng = np.random.default_rng(1)


class Operator(unittest.TestCase):
    def setUp(self):
        self.J = rng.normal(size=(8, 2))
        self.data_cov = np.diag(rng.uniform(0.5, 2.0, 8))
        self.mc_cov = 0.1 * np.diag(rng.uniform(0.5, 2.0, 8))
        self.U = rng.normal(size=(8, 2)) * 0.3

    def test_equals_gls_with_constraint_rows(self):
        """Sigma_beta with N(0,1) nuisance columns equals the GLS covariance of the augmented system (data rows plus
        one pseudo-measurement 0 +- 1 per nuisance)."""
        op = linear.operator(self.J, self.data_cov, self.mc_cov, self.U)
        X = np.concatenate([self.J, self.U], 1)
        Xa = np.concatenate([X, np.concatenate([np.zeros((2, 2)), np.eye(2)], 1)])
        Va = np.zeros((10, 10))
        Va[:8, :8] = self.data_cov + self.mc_cov
        Va[8:, 8:] = np.eye(2)
        S = np.linalg.inv(Xa.T @ np.linalg.inv(Va) @ Xa)
        np.testing.assert_allclose(op["Sigma_beta"], S, rtol=1e-10)

    def test_sigma_mc_and_nuisance_contribution(self):
        op = linear.operator(self.J, self.data_cov, self.mc_cov, self.U)
        np.testing.assert_allclose(op["Sigma_MC"], op["A_theta"] @ self.mc_cov @ op["A_theta"].T)
        bare = linear.operator(self.J, self.data_cov, self.mc_cov)
        self.assertTrue(np.all(op["sigma_tot"] > bare["sigma_tot"]))       # nu enters sigma_tot^design (section 17)

    def test_projected_inverse(self):
        V = np.diag([1.0, 2.0, 4.0])
        W = linear.projected_inverse(V, [np.array([1.0, 0.0, 0.0])])
        np.testing.assert_allclose(W, np.diag([0.0, 0.5, 0.25]), atol=1e-12)
        np.testing.assert_allclose(linear.projected_inverse(V, []), np.linalg.inv(V))

    def test_matrix_condition(self):
        S = np.array([[2.0, 0.3], [0.3, 1.0]])
        self.assertAlmostEqual(linear.matrix_condition(0.07 * S, S), 0.07)
        self.assertEqual(linear.matrix_condition(np.eye(2), np.diag([1.0, 0.0])), float("inf"))

    def test_singular_information(self):
        with self.assertRaises(linear.DesignError) as cm:
            linear.operator(np.ones((4, 2)), np.eye(4), 0.1 * np.eye(4))
        self.assertEqual(cm.exception.code, "linear.singular")

    def test_vmodel_and_systematic_columns(self):
        c = {"model_discrepancy": {"components": [{"kind": "squared-exponential", "observables": ["a", "b"],
                                                   "f": 0.1, "length": 1.0, "control": {"a": 0.0, "b": 1.0}}]}}
        U = linear.vmodel_columns(c, ["a", "b", "c"])
        R = U @ U.T
        self.assertAlmostEqual(R[0, 0], 0.01)
        self.assertAlmostEqual(R[0, 1], 0.01 * np.exp(-0.5))
        self.assertAlmostEqual(R[2, 2], 0.0)
        S = linear.systematic_columns([{"relative": {"a": 0.01, "c": 0.02}}], ["a", "b", "c"],
                                      np.array([2.0, 1.0, 3.0]), ["log", "log", "identity"])
        np.testing.assert_allclose(S[:, 0], [0.01, 0.0, 0.06])

    def test_phase2_content_refused(self):
        for change in ({"block": "poisson"}, {"link": "logit"}):
            c = {"observables": [{"name": "a", "role": "calibration", "block": "gaussian", "link": "log", **change}]}
            with self.assertRaises(linear.DesignError) as cm:
                linear.calibration_observables(c)
            self.assertEqual(cm.exception.code, "linear.incomplete")


class ToyDesign(unittest.TestCase):
    def test_lambda_is_the_exposure_ratio_with_unit_weights(self):
        """At theta_ref = the generation point all weights are 1, so Sigma_MC = (N_data / N_MC) Sigma_data."""
        fx = H.toy_design()
        plan = dict(fx["plan"], evaluator={"kind": "toy-detector", "events": 10_000})
        ev = E.make(plan)
        d = linear.design(ev, fx["contract"], plan, systematics=fx["release"]["content"]["systematic"])
        self.assertAlmostEqual(d["lambda_max"], 2000 / 10_000, places=6)
        self.assertEqual((d["n_nu"], d["n_eta"], d["n_phi"]), (4, 1, 1))
        self.assertTrue(np.all(np.isfinite(d["sigma_tot"])) and np.all(d["sigma_tot"] > 0))


if __name__ == "__main__":
    unittest.main()

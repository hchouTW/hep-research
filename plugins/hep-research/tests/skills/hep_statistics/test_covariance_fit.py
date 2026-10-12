"""hep-statistics audit T18 (covariance fits) and T19 (multiplicative uncertainties): skills/hep-statistics/scripts/
covariance_fit.py. SYNTHETIC. Criteria fixed before the runs: a mean chi2 within 4 standard errors of its dof over
toys; a bias test at 4 standard errors; oracle values to 1e-6 (closed forms) or 1e-5 (independent minimization)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import covariance_fit as cf  # noqa: E402

X = np.arange(8.0)
P = np.exp(-0.3 * X)
P /= P.sum()
N = 5000
C_NORM = (np.diag(P) - np.outer(P, P)) / N          # covariance of a normalized spectrum: singular along (1, ..., 1)
ONES = [[1.0] * 8]


class T18ConstrainedSpectrum(unittest.TestCase):
    def test_unconstrained_fit_is_refused_not_regularized(self):
        y = np.random.default_rng(1).multinomial(N, P) / N
        with self.assertRaisesRegex(cf.CovFitError, "singular beyond the 0 declared"):
            cf.fit(y, C_NORM, "exponential-normalized", x=X, start=[0.2])
        with self.assertRaisesRegex(cf.CovFitError, "not a null direction"):
            cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=[[1.0] * 7 + [2.0]], start=[0.2])

    def test_dof_and_chi2_in_the_constrained_subspace(self):
        rng = np.random.default_rng(2)
        chi2, pulls = [], []
        for _ in range(400):
            y = rng.multinomial(N, P) / N
            r = cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=ONES, start=[0.2])
            self.assertEqual((r["dof"], r["covariance"]["rank_in_subspace"]), (6, 7))
            chi2.append(r["chi2"])
            pulls.append((r["theta"][0] - 0.3) / r["theta_errors"][0])
        self.assertLess(abs(np.mean(chi2) - 6), 4 * math.sqrt(2 * 6 / 400))
        self.assertLess(abs(np.std(pulls) - 1), 4 / math.sqrt(2 * 400))

    def test_diagonal_approximation_is_a_detectable_error(self):
        rng = np.random.default_rng(3)
        rho = 0.8 ** np.abs(np.subtract.outer(X, X))
        cov = 0.04 * rho
        chol = np.linalg.cholesky(cov)
        full, diag = [], []
        for _ in range(400):
            y = 1.0 + 0.05 * X + chol @ rng.standard_normal(8)
            full.append(cf.fit(y, cov, "line", x=X, start=[1.0, 0.0])["chi2"])
            diag.append(cf.fit(y, np.diag(np.diag(cov)), "line", x=X, start=[1.0, 0.0])["chi2"])
        se = 4 * math.sqrt(2 * 6 / 400)
        self.assertLess(abs(np.mean(full) - 6), se)
        self.assertGreater(abs(np.mean(diag) - 6), se)

    def test_near_singular_is_fitted_and_flagged(self):
        ev = np.array([1.0, 0.5, 0.2, 1e-11])
        q = np.linalg.qr(np.random.default_rng(4).standard_normal((4, 4)))[0]
        cov = q @ np.diag(ev) @ q.T
        r = cf.fit(np.array([1.0, 1.1, 0.9, 1.05]), cov, "constant")
        self.assertTrue(r["covariance"]["near_singular"])
        self.assertGreater(r["covariance"]["condition_number"], 1e10)

    def test_units_do_not_change_the_inference(self):
        y = np.random.default_rng(5).multinomial(N, P) / N
        a = cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=ONES, start=[0.2])
        rho = 0.5 ** np.abs(np.subtract.outer(X, X))
        yl = 2.0 + 0.1 * X + np.random.default_rng(6).standard_normal(8) * 0.1
        b1 = cf.fit(yl, 0.01 * rho, "line", x=X, start=[1.0, 0.0])
        b2 = cf.fit(1000 * yl, 1e4 * rho, "line", x=X, start=[1000.0, 0.0])
        self.assertAlmostEqual(b1["chi2"], b2["chi2"], delta=1e-6 * b1["chi2"])
        self.assertAlmostEqual(1000 * b1["theta"][1], b2["theta"][1], delta=1e-5 * abs(b2["theta"][1]))
        self.assertEqual(a["dof"], 6)

    def test_parameter_dependent_covariance_matches_the_exact_gaussian_mle(self):
        rel = 0.01 * np.eye(5)                     # 10% independent errors that scale with the model
        add = 1e-4 * np.eye(5)
        rng = np.random.default_rng(7)
        y = 10.0 * (1 + 0.1 * rng.standard_normal(5))
        r = cf.fit(y, add, "constant", multiplicative={"relative_cov": rel.tolist(), "mode": "model"}, start=[9.0])

        def m2ll(t):
            c = add + rel * t[0] ** 2
            d = y - t[0]
            return float(d @ np.linalg.solve(c, d) + np.linalg.slogdet(c)[1])
        ref = optimize.minimize(m2ll, [9.0], method="Nelder-Mead", options={"xatol": 1e-10, "fatol": 1e-12}).x[0]
        self.assertAlmostEqual(r["theta"][0], ref, delta=1e-5)
        self.assertTrue(r["logdet"])


class T19Multiplicative(unittest.TestCase):
    Y = [1.5, 1.0]
    STAT = np.diag([0.15 ** 2, 0.10 ** 2])
    REL = np.full((2, 2), 0.04)                    # 20% common normalization

    def run_mode(self, mode, y=None):
        return cf.fit(y if y is not None else self.Y, self.STAT, "constant",
                      multiplicative={"relative_cov": self.REL.tolist(), "mode": mode}, start=[1.2])

    def test_peelle_oracles(self):
        c = self.STAT + 0.04 * np.outer(self.Y, self.Y)        # GLS with the covariance scaled by the data
        w = np.linalg.solve(c, np.ones(2))
        r = self.run_mode("data")
        self.assertAlmostEqual(r["theta"][0], w @ self.Y / w.sum(), delta=1e-6)   # 0.882: below both measurements
        self.assertAlmostEqual(r["theta_errors"][0], 1 / math.sqrt(w.sum()), delta=1e-5)
        wm = np.array([1 / 0.15 ** 2, 1 / 0.10 ** 2])
        mean = wm @ self.Y / wm.sum()
        r = self.run_mode("nuisance")
        self.assertAlmostEqual(r["theta"][0], mean, delta=1e-6)                     # 1.154
        self.assertAlmostEqual(r["theta_errors"][0], math.sqrt(1 / wm.sum() + 0.04 * mean ** 2), delta=1e-4)

    def test_data_scaled_covariance_is_biased_and_the_nuisance_form_is_not(self):
        rng = np.random.default_rng(8)
        est = {m: [] for m in ("data", "model", "nuisance")}
        for _ in range(1000):
            norm = 1 + 0.2 * rng.standard_normal()
            y = norm * (1.0 + np.array([0.15, 0.10]) * rng.standard_normal(2))
            for m in est:
                est[m].append(self.run_mode(m, y)["theta"][0])
        for m, v in est.items():
            v = np.array(v)
            setattr(self, f"bias_{m}", (v.mean() - 1.0, v.std() / math.sqrt(len(v))))
        b, se = self.bias_data
        self.assertLess(b, -4 * se)                                # biased low (Peelle)
        b2, se2 = self.bias_nuisance
        self.assertLess(abs(b2), 4 * se2)                          # the normalization as a nuisance: unbiased
        # recorded, not required: the Gaussian likelihood with C(theta) and ln det is also biased low here
        # (-0.039 +- 0.007 at seed 8): a common normalization is not an additive Gaussian error
        b3, se3 = self.bias_model
        self.assertLess(b3, 0.0)

    def test_mode_is_required(self):
        with self.assertRaises(cf.CovFitError):
            cf.fit(self.Y, self.STAT, "constant", multiplicative={"relative_cov": self.REL.tolist()})


if __name__ == "__main__":
    unittest.main()

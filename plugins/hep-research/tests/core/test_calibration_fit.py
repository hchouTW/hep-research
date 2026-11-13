"""The inference engine of Part B section 7 and the fit gates G1, G2, G3, G6, G7 (phase 2, WP2)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import fit as F  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402

TRUTH = [0.5, -0.3, 1.0]


class RatioTest(unittest.TestCase):
    def test_k_star_examples_of_section_7_3(self):
        self.assertEqual([F.k_star(n) for n in (5, 10, 60, 500, 1000)], [3, 3, 5, 14, 22])
        self.assertEqual(F.k_star(198), 9)          # G8 standard, d = 3
        self.assertEqual(F.k_star(1036), 23)        # G8 full, d = 3
        self.assertEqual([F.k_star(n, False) for n in (5, 198)], [2, 8])

    def test_w_examples(self):
        got = [round(F.w_factor(e), 3) for e in (0.005, 0.01, 1 / 61, 2 / 62)]
        self.assertEqual(got, [0.956, 0.925, 0.891, 0.822])
        self.assertEqual(F.w_factor(0.0), 1.0)
        self.assertAlmostEqual(F.w_factor(F.eps_hat(0, 60, plus=True)), 0.891, places=3)
        self.assertAlmostEqual(F.w_factor(F.eps_hat(0, 120, plus=True)), 0.935, places=3)

    def test_eps_max_cv(self):
        self.assertAlmostEqual(F.eps_max_cv(2), 0.0199, places=4)
        self.assertEqual(F.eps_max_cv(3), 0.02)
        self.assertEqual(F.eps_max_cv(20), 0.02)

    def test_estimation_ensemble_replaces_and_stops_at_k_star(self):
        """Replacement until n_req converged; the ensemble fails when X reaches k* (Sigma_boot: n = 60, k* = 5)."""
        bad = {3, 7}
        r = F.run_estimation_ensemble(lambda s: (s not in bad, s, {}), 60, range(1000))
        self.assertFalse(r.ratio_failed)
        self.assertEqual((len(r.values), r.X, r.k_star), (60, 2, 5))
        r = F.run_estimation_ensemble(lambda s: (s % 2 == 0, s, {}), 60, range(1000))
        self.assertTrue(r.ratio_failed)
        self.assertEqual(r.X, 5)

    def test_redo_continues_the_ensemble(self):
        """A redo sums X over attempts and uses the converged members of the earlier attempts in k* (section 7.3)."""
        r = F.run_estimation_ensemble(lambda s: (True, s, {}), 60, range(100), carried_X=4, carried_converged=60)
        self.assertEqual(r.k_star, F.k_star(120))
        self.assertEqual(r.X, 4)

    def test_testing_ensemble_counting(self):
        """Reference toys: non-converged toys count as statistic >= observed (D49); full G6/G2 toys count them as
        T_toy < T_obs (D46, A8)."""
        self.assertAlmostEqual(F.testing_pvalue(5.0, [1, 2, 6, 7], 2), (2 + 2 + 1) / 7)
        self.assertAlmostEqual(F.fullfit_gof_pvalue(5.0, [1, 2, 6, 7], 2), (2 + 1) / 7)
        with self.assertRaises(F.FitError):                         # never fewer toys than n silently (F8)
            F.run_testing_ensemble(lambda s: (True, s, {}), 100, range(50))
        r = F.run_testing_ensemble(lambda s: (s % 10 != 0, s, {}), 100, range(100))
        self.assertEqual(r.X, 10)
        self.assertTrue(r.ratio_failed)


class Iteration(unittest.TestCase):
    def test_equals_gls_on_the_linear_gaussian(self):
        cfg = T.linear_config(n=20, d=3)
        p = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p))
        W = np.linalg.inv(cfg.V_data)
        th = np.linalg.solve(cfg.J.T @ W @ cfg.J, cfg.J.T @ W @ (p.observed.y_gauss - cfg.m0))
        # within the declared minimizer tolerance (EDM < 0.002 tol, tol = 0.01: |delta| ~ 0.01 sigma, D79)
        np.testing.assert_allclose(f.beta[:3], th, atol=0.02 * f.sigma_tot.min())
        np.testing.assert_allclose(f.sigma_tot, np.sqrt(np.diag(np.linalg.inv(cfg.J.T @ W @ cfg.J))), rtol=1e-6)

    def test_minimize_uses_the_problems_analytic_jacobian(self):
        """A problem with H(tp) has its analytic Jacobian used by minimize (it was never used: a bound method is a new
        object on each access, so `hfun is problem.h` was always False); control: the same problem without H falls
        back to finite differences and reaches the same minimum."""
        cfg = T.linear_config(n=20, d=3)
        base = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)

        class WithH:
            def __init__(self, p):
                self.p, self.calls = p, 0

            def __getattr__(self, name):
                return getattr(self.p, name)

            def H(self, tp):
                self.calls += 1
                return np.asarray(cfg.J, float)
        p = WithH(base)
        ref = base.reference(np.asarray(TRUTH, float), None)
        m = F.minimize(p, ref, T.initial_beta(base))
        self.assertGreater(p.calls, 0)
        m0 = F.minimize(base, ref, T.initial_beta(base))
        np.testing.assert_allclose(m.beta[:3], m0.beta[:3], atol=1e-3)

    def test_lndet_diagnostic_matches_direct_minimization(self):
        cfg = T.linear_config(n=20, d=3, count_c=0.5)
        p = T.make(cfg, [2.0, -2.0, 2.0], data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p, [-2.5, 2.5, -2.5]), lndet=False)

        def full(th):
            r = p.reference(th, None)
            return L.Likelihood(p.layout, p.observed, r).deviance(np.r_[th], p.h(th)) + r.ln_det
        o = optimize.minimize(full, f.beta[:3], method="Nelder-Mead",
                              options=dict(xatol=1e-9, fatol=1e-11, maxiter=40000))
        shift, _ = F.lndet_diagnostic(p, f)
        self.assertAlmostEqual(shift, float(np.max(np.abs(o.x - f.beta[:3]) / f.sigma_tot)), delta=0.01)

    def test_g1_iteration_limit(self):
        """G1: limiting the number of iterations makes the fit not converged (section 15.3.1)."""
        cfg = T.linear_config(n=20, d=3, count_c=0.2, sd=1.0)
        p = T.make(cfg, [2.0, -2.0, 2.0], data_seed=3, mc_seed=4)
        b0 = T.initial_beta(p, [-2.5, 2.5, -2.5])
        ok = F.iterate(p, b0)
        self.assertTrue(ok.converged)
        self.assertEqual(ok.iterations, 3)
        bad = F.iterate(p, b0, limit=2)
        self.assertFalse(bad.converged)
        self.assertEqual(F.g1(bad, p)["finding"], "g1.not_converged")
        self.assertEqual(F.g1(ok, p)["status"], "passed")

    def test_lndet_failure_is_nonconvergence(self):
        cfg = T.linear_config(n=20, d=3, count_c=0.5)
        p = T.make(cfg, [2.0, -2.0, 2.0], data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p, [-2.5, 2.5, -2.5]))
        self.assertFalse(f.converged)
        self.assertIn("ln det", f.reason)


class Basins(unittest.TestCase):
    def test_exactly_degenerate_basins_are_kept_and_tied(self):
        """Bimodal model: both mirror basins reported, not merged; `multimodal` and `tie`; theta-hat the first in
        lexicographic order; G1 decided per basin (sections 7.4, 15.2)."""
        cfg = T.linear_config(n=20, d=2, prior=[(-1, 3), (-3, 3)])
        cfg.bimodal = True
        p = T.make(cfg, [1.8, 0.3], data_seed=5, mc_seed=6)
        fe = F.find_extremum(p, 7, T.initial_beta(p, [1.0, 0.0]))
        self.assertIn("multimodal", fe.flags)
        self.assertIn("tie", fe.flags)
        self.assertEqual(len(fe.basins), 2)
        self.assertAlmostEqual(fe.basins[0]["theta"][0] + fe.basins[1]["theta"][0], 2.0, places=3)
        self.assertLess(fe.beta[0], 1.0)
        self.assertEqual(F.g1(fe, p)["status"], "passed")

    def test_reseeding_keeps_the_classification(self):
        cfg = T.linear_config(n=20, d=2, prior=[(-1, 3), (-3, 3)])
        cfg.bimodal = True
        p = T.make(cfg, [1.8, 0.3], data_seed=5, mc_seed=6)
        cls = {tuple(sorted(round(b["theta"][0], 2) for b in F.find_extremum(p, s, T.initial_beta(p)).basins))
               for s in range(5)}
        self.assertEqual(len(cls), 1)

    def test_stationary_point_beyond_prior_width_is_not_a_basin(self):
        """sigma_tot,i > sigma_prior,i: not admitted, recorded, no basin (section 7.4)."""
        cfg = T.linear_config(n=20, d=3)
        cfg.J[:, 2] *= 1e-3
        p = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)
        fe = F.find_extremum(p, 7, T.initial_beta(p))
        self.assertIn("no-admitted-endpoint", fe.flags)
        self.assertTrue(fe.nonidentified)
        self.assertTrue(all(max(e["sigma_ratio"]) > 1.0 for e in fe.nonidentified))

    def test_unimodal_single_basin(self):
        cfg = T.linear_config(n=20, d=3)
        p = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)
        fe = F.find_extremum(p, 7, T.initial_beta(p))
        self.assertEqual(len(fe.basins), 1)
        self.assertNotIn("multimodal", fe.flags)
        self.assertEqual(F.n_starts(3), 16)
        self.assertEqual(F.n_starts(10), 20)


class G7(unittest.TestCase):
    @staticmethod
    def rate(factor, reps, K=10, seed=1000):
        cfg = T.linear_config(n=20, d=3, mc_ratio=0.1)
        det = 0
        for r in range(reps):
            p0 = T.make(cfg, TRUTH, data_seed=seed + r, mc_seed=1)
            f0 = F.iterate(p0, T.initial_beta(p0), lndet=False)
            th = []
            for k in range(K):
                p = T.LinearProblem(cfg, mc_seed=10_000 * r + k + 7, observed=p0.observed)
                th.append(F.iterate(p, T.initial_beta(p), lndet=False).beta[:3])
            det += F.g7(np.array(th), F.sigma_mc(p0, f0, cfg.V_MC / factor))["status"] == "failed"
        return det / reps

    def test_underestimated_v_mc_detected(self):
        """V_MC underestimated by a factor of 3, K = 10, d = 3: detection rate >= 0.9 (section 15.3.1)."""
        self.assertGreaterEqual(self.rate(3.0, 40), 0.9)

    def test_correct_v_mc_rarely_fails(self):
        self.assertLessEqual(self.rate(1.0, 40, seed=5000), 0.1)

    def test_rank_one_uses_k_minus_one_and_null_spread_fails(self):
        """Rank-one Sigma_MC: K - 1 degrees of freedom; a spread inside the null space fails (section 15.3a)."""
        e = np.array([1.0, 2.0, 0.0])
        S = np.outer(e, e) * 0.01
        rng = np.random.default_rng(3)
        X = np.outer(rng.normal(size=10) * 0.1, e)
        r = F.g7(X, S)
        self.assertEqual((r["rank"], r["df"]), (1, 9))
        X2 = X + np.outer(rng.normal(size=10), [0.0, 0.0, 1e-3])
        self.assertEqual(F.g7(X2, S, sigma_tot_ref=np.ones(3))["finding"], "g7.null_space_spread")
        self.assertEqual(F.g7(np.zeros((10, 3)), np.zeros((3, 3)))["rank"], 0)


class G6(unittest.TestCase):
    def setUp(self):
        self.cfg = T.linear_config(n=20, d=3, mc_ratio=0.1)

    def test_correct_model_passes(self):
        p = T.make(self.cfg, TRUTH, data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p))
        r = F.g6(p, f, F.null_toys(p, f, 500, 99))
        self.assertEqual(r["status"], "passed")
        self.assertTrue(r["linearity_ok"])

    def test_missing_effect_fails(self):
        """The simulation lacks one effect (section 15.3.1)."""
        p = T.make(self.cfg, TRUTH, data_seed=3, mc_seed=4)
        p.observed.y_gauss = p.observed.y_gauss + np.r_[np.zeros(10), np.full(10, 1.5)]
        f = F.iterate(p, T.initial_beta(p))
        r = F.g6(p, f, F.null_toys(p, f, 500, 99))
        self.assertEqual(r["finding"], "g6.p_value")

    def test_cross_term_nonlinearity_requires_full_toys(self):
        q = np.zeros((20, 3, 3))
        q[:, 0, 1] = np.random.default_rng(2).normal(size=20) * 3.0
        cfg = T.linear_config(n=20, d=3, quad=q)
        p = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p))
        r = F.g6(p, f, F.null_toys(p, f, 200, 99))
        self.assertEqual(r["finding"], "g6.linearity_check_failed")
        self.assertGreater(r["linearity_fraction"], 0.05)

    def test_lndet_diagnostic_rejects_points_it_cannot_evaluate(self):
        """A trial point of the ln det diagnostic where the reference quantities cannot be computed is rejected like a
        worse point (found 2026-11-11: a non-identifiable toy-detector fit stepped where a width was not finite)."""
        p = T.make(self.cfg, TRUTH, data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p))
        base = p.reference

        def fragile(tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
            if abs(tp[0] - f.beta[0]) > 1e-12:              # every point off the fit point fails
                raise ValueError("array must not contain infs or NaNs")
            return base(tp, beta, frozen, bootstrap_frozen, bootstrap_seed)
        v = F.view(p, reference=lambda tp, b, frozen, bf: fragile(tp, b, frozen, bf))
        v.V_depends_on_theta = True                       # run the diagnostic (the linear toy's V is constant)
        shift, _ = F.lndet_diagnostic(v, f)
        self.assertTrue(np.isfinite(shift))

    def test_full_toys_after_the_linearity_check(self):
        """G6 with full toys (D46): the correct quadratic model passes where the linear toys could not decide; the
        missing effect still fails."""
        q = np.zeros((20, 3, 3))
        q[:, 0, 1] = np.random.default_rng(2).normal(size=20) * 3.0
        cfg = T.linear_config(n=20, d=3, quad=q)
        p = T.make(cfg, TRUTH, data_seed=3, mc_seed=4)
        f = F.iterate(p, T.initial_beta(p))
        r = F.g6_full(p, f, 200, 98)
        self.assertEqual((r["status"], r["construction"]), ("passed", "full-toys"))
        p.observed.y_gauss = p.observed.y_gauss + np.r_[np.zeros(10), np.full(10, 1.5)]
        f = F.iterate(p, T.initial_beta(p))
        self.assertEqual(F.g6_full(p, f, 200, 98)["finding"], "g6.p_value")


class G2G3(unittest.TestCase):
    def setUp(self):
        self.cfg = T.linear_config(n=20, d=2, bounds=[(0.0, 10.0), (-10, 10)], prior=[(0, 3), (-3, 3)])

    def test_truth_beyond_boundary_fails(self):
        p = T.make(self.cfg, [-1.0, 0.3], data_seed=11, mc_seed=12)
        f = F.iterate(p, T.initial_beta(p, [1.0, 0.0]))
        r = F.g2(p, f, F.null_toys(p, f, 500, 5))
        self.assertEqual(r["finding"], "g2.boundary_significant")

    def test_truth_on_boundary_passes_with_flag(self):
        p = T.make(self.cfg, [0.0, 0.3], data_seed=11, mc_seed=12)
        f = F.iterate(p, T.initial_beta(p, [1.0, 0.0]))
        r = F.g2(p, f, F.null_toys(p, f, 500, 5))
        self.assertEqual(r["status"], "passed")
        self.assertIn("boundary-solution", r["flags"])

    def test_two_parameters_on_the_boundary_use_chibar(self):
        cfg = T.linear_config(n=20, d=2, bounds=[(0.0, 10.0), (0.0, 10.0)], prior=[(0, 3), (0, 3)])
        p = T.make(cfg, [0.0, 0.0], data_seed=21, mc_seed=12)
        f = F.iterate(p, T.initial_beta(p, [1.0, 1.0]))
        r = F.g2(p, f, F.null_toys(p, f, 400, 5))
        if r["active"]:
            self.assertEqual(len(r["weights"]), len(r["active"]) + 1)
        self.assertAlmostEqual(F.chibar_pvalue(3.0, [0.25, 0.5, 0.25]), 0.5 * 0.0833 + 0.25 * 0.2231, places=3)

    def test_g3_isolation_mode(self):
        """G3 (single-gate isolation mode): the 68% region outside the feasible region fails (section 15.3.1)."""
        lim = {"feasible": {"t0": [0.0, 1.0]}, "support": {"t0": [-1.0, 2.0]}}
        self.assertEqual(F.g3({"t0": [0.2, 0.8]}, lim)["status"], "passed")
        self.assertEqual(F.g3({"t0": [0.7, 1.3]}, lim)["finding"], "g3.outside_limits")
        self.assertEqual(F.g3({"t0": None}, lim)["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()

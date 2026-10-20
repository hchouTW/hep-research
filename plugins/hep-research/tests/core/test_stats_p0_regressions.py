"""P0 regressions from the hep-statistics audit (audit commit b5c3a55; checks T01-T05).

F01: the shape likelihood accepted a negative Poisson mean when the bin had no events (expected = [-1], NLL = 2).
F02: zero toy exceedances were reported as a definite p = 0 with binomial error 0.
F03: the Newton minimizer returned no convergence status (max_iter = 0 returned the start point as if fitted).
Each test fails on the audited code and states the behavior that is now required. All inputs SYNTHETIC.
"""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scipy import stats as sps  # noqa: E402  (oracle; scipy is in the pinned CI set, a missing scipy is an error)

from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import tail_estimation as te  # noqa: E402
from core.stats.fit_diagnostics import newton_fit  # noqa: E402

F01_DOC = {"bins": [{"n": 0, "b": 1.0, "s": 1.0}],
           "nuisances": [{"kind": "background_shape", "up": [2.0], "down": [0.0]}]}


def shape_model(doc):
    return ll._ShapeModel(*ll._load_shape(doc))


class T01LikelihoodDomain(unittest.TestCase):
    def test_negative_mean_with_zero_count_is_invalid(self):
        m = shape_model(F01_DOC)
        self.assertEqual(m.expected(0.0, [-2.0]), [-1.0])          # the model value itself is unchanged
        self.assertFalse(math.isfinite(m.nll(0.0, [-2.0], [0], m.aux_obs())))

    def test_zero_mean_zero_count_is_valid_and_positive_count_is_not(self):
        doc = {"bins": [{"n": 0, "b": 0.0, "s": 1.0}]}
        m = shape_model(doc)
        self.assertEqual(m.nll(0.0, [], [0], m.aux_obs()), 0.0)
        self.assertFalse(math.isfinite(m.nll(0.0, [], [1], m.aux_obs())))

    def test_nan_and_inf_are_rejected(self):
        m = shape_model(F01_DOC)
        for th in (float("nan"), float("inf")):
            self.assertFalse(math.isfinite(m.nll(0.0, [th], [0], m.aux_obs())), th)
        self.assertFalse(math.isfinite(m.nll(float("nan"), [0.0], [0], m.aux_obs())))

    def test_single_bin_log_likelihood_rejects_negative_mean(self):
        self.assertEqual(ll._lnl(0, 0.0), 0.0)
        self.assertLessEqual(ll._lnl(0, -1.0), ll.NEG)
        self.assertLessEqual(ll._lnl(1, 0.0), ll.NEG)

    def test_lnl_against_scipy_and_sympy_poisson(self):
        """F01, oracles from third-party implementations of the Poisson distribution (ledger review, 2026-10-20):
        ln L + ln n! equals scipy.stats.poisson.logpmf (independent implementation) and the log of sympy.stats'
        Poisson density (symbolic), for n = 0 to 30 and means from 1e-6 to 200; at mu = 0 scipy gives log 1 = 0 for
        n = 0 and -inf otherwise, and a negative mean is outside both libraries' Poisson (scipy nan, sympy refuses
        it), where ln L is NEG."""
        import sympy
        from sympy import stats as sst

        rate = sympy.Symbol("mu", positive=True)
        density = sst.density(sst.Poisson("N", rate))
        for n in range(31):
            for mu in (1e-6, 0.3, 1.0, 4.5, 30.0, 200.0):
                with self.subTest(n=n, mu=mu):
                    ref = float(sps.poisson.logpmf(n, mu)) + math.lgamma(n + 1)
                    sym = float(sympy.log(density(n).subs(rate, mu)).evalf(30)) + math.lgamma(n + 1)
                    tol = 1e-12 * max(1.0, abs(ref))
                    self.assertAlmostEqual(ll._lnl(n, mu), ref, delta=tol)
                    self.assertAlmostEqual(ll._lnl(n, mu), sym, delta=tol)
            self.assertEqual(ll._lnl(n, 0.0), 0.0 if sps.poisson.logpmf(n, 0.0) == 0.0 else ll._lnl(n, 0.0))
            if n:
                self.assertEqual(sps.poisson.logpmf(n, 0.0), -math.inf)
                self.assertLessEqual(ll._lnl(n, 0.0), ll.NEG)
            self.assertTrue(math.isnan(sps.poisson.logpmf(n, -1.0)))
            self.assertLessEqual(ll._lnl(n, -1.0), ll.NEG)
        with self.assertRaises(ValueError):
            sst.Poisson("M", -1)

    def test_profiled_background_stays_in_the_domain(self):
        # a negative signal (two-POI fits allow it) must not profile the background below -s
        for n in (0, 3):
            b = ll._b_hat(n, -2.0, 1.0, 0.5)
            self.assertGreaterEqual(b - 2.0, 0.0, n)

    def test_fit_never_settles_on_a_negative_mean(self):
        m = shape_model(F01_DOC)
        th, val = m.cond(0.0, [0], m.aux_obs())
        self.assertTrue(math.isfinite(val))
        self.assertGreaterEqual(min(m.expected(0.0, th)), 0.0)


class T02T03ToyTails(unittest.TestCase):
    def test_zero_exceedances_give_a_bound_not_a_zero(self):
        r = ll.profile_significance(20, 1.0, 0.0, 100, 1)
        self.assertIsNone(r["p_value_toys"])
        self.assertIsNone(r["binomial_error_on_p_toys"])
        tail = r["toy_tail"]
        self.assertEqual((tail["k"], tail["n"]), (0, 100))
        self.assertAlmostEqual(tail["upper_bound"]["value"], 1.0 - 0.05 ** (1 / 100), places=12)
        self.assertAlmostEqual(tail["upper_bound"]["value"], 0.029513, places=6)
        self.assertEqual(tail["upper_bound"]["cl"], 0.95)
        self.assertFalse(tail["resolved"])
        self.assertLess(r["log_p_value_exact_poisson"], math.log(tail["upper_bound"]["value"]))

    def test_clopper_pearson_against_scipy(self):
        for n in (1, 7, 100, 20000):
            for k in sorted({0, 1, n // 3, n - 1, n}):
                lo, hi = te.clopper_pearson(k, n, 0.6827)
                a = (1 - 0.6827) / 2
                ref_lo = 0.0 if k == 0 else sps.beta.ppf(a, k, n - k + 1)
                ref_hi = 1.0 if k == n else sps.beta.ppf(1 - a, k + 1, n - k)
                self.assertAlmostEqual(lo, ref_lo, delta=1e-10 * max(ref_lo, 1e-300) + 1e-14, msg=(k, n))
                self.assertAlmostEqual(hi, ref_hi, delta=1e-10 * max(ref_hi, 1e-300) + 1e-14, msg=(k, n))
                up = te.one_sided_upper(k, n, 0.95)
                ref_up = 1.0 if k == n else sps.beta.ppf(0.95, k + 1, n - k)
                self.assertAlmostEqual(up, ref_up, delta=1e-10 * ref_up + 1e-14, msg=(k, n))
                # the defining tail equations, from scipy.stats.binom (not the beta identity): P(X >= k | lo) = a
                # and P(X <= k | hi) = a (ledger review, 2026-10-20)
                if k > 0:
                    self.assertAlmostEqual(sps.binom.sf(k - 1, n, lo) / a, 1.0, delta=1e-8, msg=(k, n))
                if k < n:
                    self.assertAlmostEqual(sps.binom.cdf(k, n, hi) / a, 1.0, delta=1e-8, msg=(k, n))

    def test_zero_exceedance_bound_solves_the_binomial_equation_symbolically(self):
        """F02, symbolic oracle (sympy.stats.Binomial, ledger review 2026-10-20): the 95% upper bound for zero
        exceedances in N toys is the p with P(K = 0 | N, p) = 0.05, sympy's own Binomial probability solved on
        (0, 1) by bracketing at 30 digits (mpmath illinois); the code's 1 - 0.05^(1/N) must equal it. Tolerance
        1e-12: the code's closed form loses about 1e-14 to cancellation at N = 1000."""
        import mpmath
        import sympy
        from sympy import stats as sst

        p = sympy.Symbol("p", positive=True)
        for n in (1, 7, 100, 1000):
            with self.subTest(n=n):
                equation = sympy.lambdify(p, sst.P(sympy.Eq(sst.Binomial("K", n, p), 0)) - sympy.Rational(1, 20),
                                          "mpmath")
                with mpmath.workdps(30):
                    root = float(mpmath.findroot(equation, (mpmath.mpf("1e-15"), 1 - mpmath.mpf("1e-15")),
                                                 solver="illinois", tol=1e-25, maxsteps=500))
                bound = te.toy_tail(0, n)["upper_bound"]["value"]
                self.assertAlmostEqual(bound / root, 1.0, delta=1e-12)

    def test_tail_record_cases(self):
        n = 50
        self.assertIsNone(te.toy_tail(0, n)["estimate"])
        self.assertIn("upper_bound", te.toy_tail(0, n))
        full = te.toy_tail(n, n)
        self.assertEqual(full["estimate"], 1.0)
        self.assertAlmostEqual(full["lower_bound"]["value"], 0.05 ** (1 / n), places=12)
        self.assertIsNone(full["binomial_error"])
        mid = te.toy_tail(1, n)
        self.assertEqual(mid["estimate"], 1 / n)
        self.assertTrue(mid["resolved"])
        lo, hi = mid["interval"]
        self.assertLess(lo, 1 / n)
        self.assertLess(1 / n, hi)
        self.assertEqual(te.toy_tail(n - 1, n)["estimate"], (n - 1) / n)

    def test_extreme_beta_quantiles_keep_relative_precision(self):
        # review finding: sqrt(lo * hi) underflowed below 1e-308 and stopped the search early (5e-199 for 2e-201)
        for q in (1e-100, 1e-200, 1e-300):
            ref = sps.beta.ppf(q, 1, 5)
            self.assertAlmostEqual(te.beta_ppf(q, 1, 5) / ref, 1.0, delta=1e-9)

    def test_zero_toys_rejected(self):
        for bad in (0, -1, 2.5, True):
            with self.assertRaises(te.TailError):
                te.toy_tail(0, bad)
        with self.assertRaises(te.TailError):
            te.toy_tail(5, 4)

    def test_extreme_exact_tail_in_log_space(self):
        # P(N >= 200 | 1) is about 1e-375, below the smallest double (scipy's logsf returns -inf here); the oracle is
        # the log-sum of scipy's log pmf over the tail
        from scipy.special import logsumexp
        import numpy as np
        lp = te.log_poisson_tail(200, 1.0)
        ref = float(logsumexp(sps.poisson.logpmf(np.arange(200, 2000), 1.0)))
        self.assertAlmostEqual(lp, ref, delta=1e-9 * abs(ref))
        self.assertTrue(math.isfinite(te.z_from_log_tail(lp)))
        self.assertGreater(te.z_from_log_tail(lp), 40.0)


class T04FitStatus(unittest.TestCase):
    def test_max_iter_zero_is_not_converged(self):
        r = newton_fit(lambda x: (x[0] - 3.0) ** 2, [0.0], max_iter=0)
        self.assertEqual(r.status, "failed")
        self.assertIn("max_iterations", r.reasons)
        self.assertEqual(r.x, [0.0])

    def test_quadratic_converges(self):
        r = newton_fit(lambda p: (p[0] - 1.0) ** 2 + 3 * (p[1] + 2.0) ** 2 + 0.5 * p[0] * p[1], [0.0, 0.0])
        self.assertEqual(r.status, "converged", r.reasons)
        self.assertLess(r.edm, 1e-5)

    def test_flat_direction_fails(self):
        r = newton_fit(lambda p: (p[0] + p[1] - 1.0) ** 2, [0.0, 0.0])
        self.assertEqual(r.status, "failed")
        self.assertIn("hessian_not_positive_definite", r.reasons)

    def test_stalled_at_an_invalid_domain_edge_fails(self):
        r = newton_fit(lambda x: (x[0] - 3.0) ** 2 if x[0] <= 1.0 else math.inf, [0.0])
        self.assertEqual(r.status, "failed")
        self.assertTrue({"line_search_stalled", "invalid_domain_nearby", "gradient_not_small"} & set(r.reasons), r.reasons)

    def test_invalid_start_fails(self):
        r = newton_fit(lambda x: math.inf, [0.0])
        self.assertEqual(r.status, "failed")
        self.assertIn("invalid_domain", r.reasons)

    def test_shape_limit_reports_failed_status_and_cli_exit(self):
        import io
        import contextlib
        import json
        import tempfile
        doc = {"bins": [{"n": 4, "b": 3.0, "s": 1.0}, {"n": 2, "b": 1.5, "s": 0.8}],
               "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.1}]}
        ok = ll.shape_limit(doc, 0.95, 0, 1)
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["fit_diagnostics"]["observed"]["failed"], 0)
        orig = ll.newton_fit
        try:
            ll.newton_fit = lambda f, x0, fixed_first=False, max_iter=60: orig(f, x0, fixed_first, 0)
            bad = ll.shape_limit(doc, 0.95, 0, 1)
            self.assertEqual(bad["status"], "failed")
            self.assertGreater(bad["fit_diagnostics"]["observed"]["failed"], 0)
            self.assertIn("max_iterations", bad["fit_diagnostics"]["observed"]["reasons"])
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "m.json"
                p.write_text(json.dumps(doc))
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = ll.main(["shape-limit", "--input", str(p), "--seed", "1"])
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(buf.getvalue())["status"], "failed")
        finally:
            ll.newton_fit = orig


class T04AnalyticOracle(unittest.TestCase):
    """Sci-fix F03, axis C: newton_fit and its verdict against a model with a closed-form minimum and Hessian. Two
    Poisson bins and a Gaussian constraint: n1 ~ Pois(mu s + theta b), n2 ~ Pois(theta c), theta ~ N(1, sigma). Bin 1
    is saturated at the minimum (mu s + theta b = n1), so theta solves c - n2/theta + (theta - 1)/sigma^2 = 0, a
    quadratic, and mu = (n1 - theta b)/s; the Hessian is n1/lambda1^2 (s, b)(s, b)^T + diag(0, n2/theta^2 + 1/sigma^2).
    The EDM g^T H^-1 g / 2 is computed here from the analytic gradient and Hessian at the point the fit returns."""

    N1, N2, S, B, C, SIGMA = 12, 40, 2.0, 3.0, 10.0, 0.1

    def nll(self, p):
        mu, theta = p
        l1, l2 = mu * self.S + theta * self.B, theta * self.C
        if l1 <= 0 or l2 <= 0:
            return math.inf
        return l1 - self.N1 * math.log(l1) + l2 - self.N2 * math.log(l2) + 0.5 * ((theta - 1) / self.SIGMA) ** 2

    def minimum(self):
        k = self.C * self.SIGMA ** 2 - 1
        theta = (-k + math.sqrt(k * k + 4 * self.N2 * self.SIGMA ** 2)) / 2
        return [(self.N1 - theta * self.B) / self.S, theta]

    def analytic_edm(self, p):
        import numpy as np
        mu, theta = p
        l1, v = mu * self.S + theta * self.B, np.array([self.S, self.B])
        g = v * (1 - self.N1 / l1) + np.array([0.0, self.C - self.N2 / theta + (theta - 1) / self.SIGMA ** 2])
        h = self.N1 / l1 ** 2 * np.outer(v, v) + np.diag([0.0, self.N2 / theta ** 2 + 1 / self.SIGMA ** 2])
        return 0.5 * float(g @ np.linalg.solve(h, g)), np.linalg.inv(h)

    def test_minimum_and_value_match_the_closed_form(self):
        """Tolerances from the verdict itself: EDM <= 1e-5 bounds (x - x*)^T H (x - x*) by 2e-5, so each coordinate is
        within sqrt(2e-5 (H^-1)_ii) and the value within 1e-5 above the minimum (observed 8e-9 and 1e-14)."""
        best = self.minimum()
        _, cov = self.analytic_edm(best)
        for start in ([1.0, 1.0], [5.0, 0.8], [0.5, 1.3]):
            r = newton_fit(self.nll, start)
            self.assertEqual(r.status, "converged", r.reasons)
            for i in range(2):
                self.assertLess(abs(r.x[i] - best[i]), math.sqrt(2e-5 * cov[i][i]), (start, i, r.x))
            self.assertLessEqual(r.fval - self.nll(best), 1e-5 + 1e-12)
            self.assertGreaterEqual(r.fval - self.nll(best), -1e-12)

    def test_converged_fits_match_a_third_party_minimum(self):
        """Independent implementation (ledger review, 2026-10-20): the same model's negative log likelihood built from
        scipy.stats.poisson.logpmf and scipy.stats.norm.logpdf (constants differ, the minimum does not) and
        minimized by scipy.optimize.minimize (Nelder-Mead, xatol 1e-12); every converged newton_fit lands at that
        minimum within sqrt(2e-5 (H^-1)_ii), the bound its EDM <= 1e-5 verdict implies, and its value is within
        1e-5 of the third-party minimum value."""
        from scipy import optimize

        def nll(x):
            mu, theta = x
            l1, l2 = mu * self.S + theta * self.B, theta * self.C
            if l1 <= 0 or l2 <= 0:
                return math.inf
            return -float(sps.poisson.logpmf(self.N1, l1) + sps.poisson.logpmf(self.N2, l2)
                          + sps.norm.logpdf(theta, 1.0, self.SIGMA))

        ref = optimize.minimize(nll, [1.0, 1.0], method="Nelder-Mead",
                                options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 20000})
        self.assertTrue(ref.success, ref.message)
        _, cov = self.analytic_edm(ref.x)
        for start in ([1.0, 1.0], [5.0, 0.8], [0.5, 1.3]):
            r = newton_fit(self.nll, start)
            self.assertEqual(r.status, "converged", r.reasons)
            for i in range(2):
                self.assertLess(abs(r.x[i] - ref.x[i]), math.sqrt(2e-5 * cov[i][i]), (start, i, r.x, ref.x))
            self.assertLessEqual(nll(r.x) - ref.fun, 1e-5 + 1e-12)

    def test_edm_and_verdict_agree_with_the_analytic_edm(self):
        """The reported EDM equals the analytic one to 1e-5 relative + 1e-11 (central differences with h = 1e-4:
        truncation about h^2, roundoff about eps |f| / h in the gradient; observed 3e-7 relative where the EDM is above
        1e-6), and the verdict is 'converged' exactly when the analytic EDM is at most 1e-5, at every stop of fits cut
        after 0 to 5 iterations. Negative control: the pre-fix minimizer returned no verdict, so every stop was taken as
        fitted; the analytic EDM shows most of them are not minima."""
        not_minima = 0
        for start in ([1.0, 1.0], [5.0, 0.8], [0.5, 1.3], [3.0, 1.05]):
            for iterations in range(6):
                with self.subTest(start=start, iterations=iterations):
                    r = newton_fit(self.nll, start, max_iter=iterations)
                    edm, _ = self.analytic_edm(r.x)
                    self.assertAlmostEqual(r.edm, edm, delta=1e-5 * edm + 1e-11)
                    self.assertFalse(0.5e-5 < edm < 2e-5, "too close to the threshold to judge")
                    self.assertEqual(r.status == "converged", edm <= 1e-5, (r.status, r.reasons, edm))
                    not_minima += edm > 1e-5
        self.assertGreater(not_minima, 10)


class T05GlobalVersusConditional(unittest.TestCase):
    DOC = {"bins": [{"n": 9, "b": 3.0, "s": 2.0}, {"n": 5, "b": 2.0, "s": 1.0}],
           "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.2}]}

    def test_degraded_global_fit_is_refitted(self):
        m = shape_model(self.DOC)
        aux = m.aux_obs()
        good = m.glob(m.n, aux)
        bad_th = [2.5]
        degraded = (0.2, bad_th, m.nll(0.2, bad_th, m.n, aux))
        self.assertGreater(degraded[2], m.cond(1.0, m.n, aux)[1])     # global above conditional: the defect
        q_good = m.q(1.0, m.n, aux, good)
        q_degraded = m.q(1.0, m.n, aux, degraded)
        self.assertAlmostEqual(q_degraded, q_good, delta=1e-4)
        self.assertGreaterEqual(m.log.events.get("global_refit", 0), 1)
        self.assertEqual(m.log.summary()["observed"]["failed"], 0)

    def test_unrepairable_violation_is_a_failure(self):
        m = shape_model(self.DOC)
        aux = m.aux_obs()
        m.glob = lambda ns, aux_, start=None: (0.2, [2.5], m.nll(0.2, [2.5], ns, aux_))  # a broken global fitter
        m._glob_from = lambda ns, aux_, x0: m.glob(ns, aux_)
        m.q(1.0, m.n, aux, m.glob(m.n, aux))
        s = m.log.summary()["observed"]
        self.assertGreater(s["failed"], 0)
        self.assertIn("global_above_conditional", s["reasons"])

    def test_boundary_optimum_is_accepted_by_kkt(self):
        doc = {"bins": [{"n": 0, "b": 3.0, "s": 2.0}, {"n": 1, "b": 2.0, "s": 1.0}],
               "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.2}]}
        m = shape_model(doc)
        mu, th, val = m.glob(m.n, m.aux_obs())
        self.assertEqual(mu, 0.0)
        s = m.log.summary()["observed"]
        self.assertEqual(s["failed"], 0, s)
        self.assertGreaterEqual(m.log.events.get("boundary_kkt_ok", 0), 1)


class ReviewFindings(unittest.TestCase):
    """Paths an independent review found untested: a KKT violation at the boundary, the incomplete status (only toy
    fits failed, exit 3), and the asymptotic gate at q0 = 0 and with failed toys."""

    DOC = {"bins": [{"n": 9, "b": 3.0, "s": 2.0}, {"n": 5, "b": 2.0, "s": 1.0}],
           "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.2}]}

    def test_boundary_kkt_violation_is_a_failure(self):
        # a degraded global optimizer claims mu-hat < 0 on data with a clear excess: the boundary fit at mu = 0 fails KKT
        from core.stats.fit_diagnostics import FitResult
        m = shape_model(self.DOC)
        orig = ll.newton_fit

        def degraded(f, x0, fixed_first=False, max_iter=60):
            r = orig(f, x0, fixed_first, max_iter)
            if len(x0) == m.k + 1:
                return FitResult([-1.0] + r.x[1:], r.fval, r.status, r.reasons, r.iterations, r.edm, r.stop)
            return r
        ll.newton_fit = degraded
        try:
            mu, _, _ = m.glob(m.n, m.aux_obs())
        finally:
            ll.newton_fit = orig
        self.assertEqual(mu, 0.0)
        self.assertIn("boundary_kkt_violated", m.log.summary()["observed"]["reasons"])

    def test_only_toy_failures_give_incomplete_and_exit_3(self):
        import contextlib
        import io
        import tempfile
        orig = ll.newton_fit
        calls = {"n": 0}

        def counting(f, x0, fixed_first=False, max_iter=60):
            calls["n"] += 1
            return orig(f, x0, fixed_first, max_iter)
        ll.newton_fit = counting
        try:
            ll.shape_limit(self.DOC, 0.95, 0, 1)
        finally:
            ll.newton_fit = orig
        observed_calls = calls["n"]

        def fail_after_observed(f, x0, fixed_first=False, max_iter=60):
            calls["n"] += 1
            return orig(f, x0, fixed_first, 0 if calls["n"] > observed_calls + 2 else max_iter)
        calls["n"] = 0
        ll.newton_fit = fail_after_observed
        try:
            r = ll.shape_limit(self.DOC, 0.95, 100, 1)
            self.assertEqual(r["status"], "incomplete")
            self.assertGreater(r["fit_diagnostics"]["toys_with_a_failed_fit"], 0)
            self.assertEqual(r["fit_diagnostics"]["observed"]["failed"], 0)
            self.assertIn("toy_p_value_range_with_failures", r)
            self.assertEqual(r["asymptotic_calibration"]["verdict"], "unresolved")
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "m.json"
                p.write_text(__import__("json").dumps(self.DOC))
                calls["n"] = 0
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(ll.main(["shape-limit", "--input", str(p), "--toys", "100", "--seed", "1"]), 3)
        finally:
            ll.newton_fit = orig

    def test_gate_at_q0_zero_is_not_applicable(self):
        for n in (1, 3):
            r = ll.profile_significance(n, 3.0, 0.0, 2000, 1)
            self.assertEqual(r["q0_observed"], 0.0)
            self.assertEqual(r["asymptotic_calibration"]["verdict"], "not-applicable")


class ConstraintNaming(unittest.TestCase):
    """Audit wording fix: a frequentist normalization nuisance names its constraint term ("constraint"); "prior" stays
    a legacy alias with the same meaning, and the two may not disagree."""

    def test_alias_and_conflict(self):
        base = {"bins": [{"n": 5, "b": 3.0, "s": 1.0}, {"n": 2, "b": 1.0, "s": 0.5}]}
        a = ll.shape_limit(dict(base, nuisances=[{"name": "n", "kind": "background_norm", "sigma": 0.3, "constraint": "gamma"}]), 0.95, 0, 1)
        b = ll.shape_limit(dict(base, nuisances=[{"name": "n", "kind": "background_norm", "sigma": 0.3, "prior": "gamma"}]), 0.95, 0, 1)
        self.assertEqual(a["asymptotic_observed_upper_limit"], b["asymptotic_observed_upper_limit"])
        self.assertEqual(a["constraints"], {"n": "gamma"})
        with self.assertRaises(ll.LikelihoodError):
            ll.shape_limit(dict(base, nuisances=[{"name": "n", "kind": "background_norm", "sigma": 0.3, "constraint": "gamma",
                                                  "prior": "lognormal"}]), 0.95, 0, 1)


if __name__ == "__main__":
    unittest.main()

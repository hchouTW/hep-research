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


if __name__ == "__main__":
    unittest.main()

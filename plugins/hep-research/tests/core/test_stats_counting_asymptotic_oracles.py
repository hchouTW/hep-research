"""Independent oracles for exact counting limits and asymptotic test statistics (hep-statistics audit T09, T10).

T09: the classical and CLs limits at n = 0, b = 0 equal -ln(0.05) = 2.995732; over an (n, b) grid they equal SciPy
roots of the defining equations; the Feldman-Cousins interval is checked against an independently written ordering
(likelihood-ratio ranking with SciPy Poisson probabilities), not against the same number.
T10: q0, q-tilde_mu and the Asimov statistics of the single-bin and multi-bin likelihoods equal the closed forms of
Cowan, Cranmer, Gross and Vitells (2011), including the piecewise boundary case; the profiled background equals a
numerical maximization; the calibration gate passes the half-chi2 approximation at large counts and declares it
inapplicable at low counts, where the toys are the result. All inputs SYNTHETIC.
"""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize
from scipy import stats as sps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import poisson_diagnostics as pd  # noqa: E402

ALPHA = 0.05


def classical_oracle(n, b, cl):
    a = 1 - cl
    return optimize.brentq(lambda mu: sps.poisson.cdf(n, mu) - a, 1e-12, 500.0, xtol=1e-12) - b


def cls_oracle(n, b, cl):
    a, clb = 1 - cl, sps.poisson.cdf(n, b)
    return optimize.brentq(lambda s: sps.poisson.cdf(n, s + b) / clb - a, 0.0, 500.0, xtol=1e-12)


def fc_oracle(n_obs, b, cl, step=0.005, s_max=None):
    """Plain Feldman-Cousins construction written independently: for each s on the grid, rank n by
    R = P(n | s + b) / P(n | max(0, n - b) + b) and accept in decreasing R until the probability reaches cl."""
    s_max = s_max or (n_obs + 3.0 * math.sqrt(n_obs + 1) + 8.0)
    ns = np.arange(0, int(s_max + b + 12 * math.sqrt(s_max + b + 1) + 30))
    best = sps.poisson.pmf(ns, np.maximum(ns - b, 0.0) + b)
    accepted = []
    for s in np.arange(0.0, s_max + step / 2, step):
        p = sps.poisson.pmf(ns, s + b)
        order = np.argsort(-(p / best), kind="stable")
        k = int(np.searchsorted(np.cumsum(p[order]), cl - 1e-12)) + 1
        if n_obs in set(order[:k].tolist()):
            accepted.append(s)
    return min(accepted), max(accepted)


class T09ExactCounting(unittest.TestCase):
    def test_zero_count_zero_background(self):
        ref = -math.log(ALPHA)
        self.assertAlmostEqual(ref, 2.995732, places=6)
        self.assertAlmostEqual(pd.upper_limit(0, 0.0, 0.95)["upper_limit_on_signal"], ref, places=8)
        self.assertAlmostEqual(pd.cls_limit(0, 0.0, 0.95)["observed_upper_limit"], ref, places=6)
        # Feldman-Cousins at n = 0, b = 0 is a different construction: its 95% upper end is 3.09 (FC 1998, Table VI)
        fc = pd.fc_interval(0, 0.0, 0.95)
        self.assertAlmostEqual(fc["upper"], 3.09, delta=0.01)
        self.assertGreater(fc["upper"], ref)

    def test_classical_and_cls_grid_against_scipy_roots(self):
        for cl in (0.90, 0.95):
            for n in range(0, 9):
                for b in (0.0, 0.5, 1.5, 3.0, 6.0):
                    with self.subTest(cl=cl, n=n, b=b):
                        ref = classical_oracle(n, b, cl)
                        got = pd.upper_limit(n, b, cl)["upper_limit_on_signal"]
                        if ref <= 0:
                            self.assertIsNone(got)              # an empty classical limit is refused, not reported
                        else:
                            self.assertAlmostEqual(got, ref, delta=1e-7 * max(1.0, ref))
                        self.assertAlmostEqual(pd.cls_limit(n, b, cl)["observed_upper_limit"], cls_oracle(n, b, cl), delta=1e-6)

    def test_feldman_cousins_against_an_independent_ordering(self):
        step = 0.005
        for cl in (0.90, 0.95):
            for n in range(0, 7):
                for b in (0.0, 0.5, 1.5, 3.0):
                    with self.subTest(cl=cl, n=n, b=b):
                        lo, hi = fc_oracle(n, b, cl, step)
                        got = pd.fc_interval(n, b, cl, step=step, monotone=False)
                        self.assertAlmostEqual(got["lower"], lo, delta=2 * step + 1e-9)
                        self.assertAlmostEqual(got["upper"], hi, delta=2 * step + 1e-9)


class T10AsymptoticForms(unittest.TestCase):
    def test_q0_closed_form(self):
        for n in (0, 2, 3, 7, 15, 40):
            for b in (2.5, 5.0):
                ref = 2.0 * (n * math.log(n / b) - n + b) if n > b else 0.0
                self.assertAlmostEqual(ll.profile_significance(n, b, 0.0, 100, 1)["q0_observed"], ref, places=10)

    def test_q_tilde_piecewise_closed_form(self):
        b = 4.0
        for n in (0, 1, 3, 4, 6, 12):
            for s in (0.5, 2.0, 5.0, 9.0):
                s_hat = max(n - b, 0.0)
                if s_hat > s:
                    ref = 0.0
                elif n >= b:          # interior best fit (arXiv:1007.1727v3 eqs. (14), (16): 0 <= mu-hat <= mu)
                    ref = 2.0 * (n * math.log(n / (s + b)) - n + s + b)
                else:                 # best fit on the boundary s = 0 (eq. (16), the q-tilde case)
                    ref = 2.0 * (s - n * math.log1p(s / b))
                self.assertAlmostEqual(ll._q1(n, b, 0.0, s), ref, places=10, msg=(n, s))

    def test_asimov_statistics(self):
        for s, b in ((1.0, 0.5), (5.0, 10.0), (20.0, 100.0)):
            z_a = math.sqrt(2.0 * ((s + b) * math.log1p(s / b) - s))       # arXiv:1007.1727v3 eq. (101)
            self.assertAlmostEqual(math.sqrt(ll._q0(s + b, b, 0.0)), z_a, places=10)
        bins = [{"n": 0, "b": 3.0, "s": 1.0}, {"n": 0, "b": 1.0, "s": 2.0}, {"n": 0, "b": 0.5, "s": 0.5}]
        m = ll._Model(bins, "none", None)
        asimov = [x["b"] for x in bins]
        for mu in (0.5, 1.0, 2.5):
            ref = sum(2.0 * (mu * x["s"] - x["b"] * math.log1p(mu * x["s"] / x["b"])) for x in bins)
            self.assertAlmostEqual(m.q(asimov, [], mu), ref, delta=1e-7 * max(ref, 1.0))

    def test_profiled_background_matches_numerical_maximum(self):
        for n, s, b0, sig in ((0, 1.0, 3.0, 1.0), (5, 2.0, 3.0, 0.5), (12, 0.0, 8.0, 3.0), (3, -1.0, 2.0, 0.4)):
            f = lambda bb: -(n * math.log(s + bb) - (s + bb) - (bb - b0) ** 2 / (2 * sig * sig)) if s + bb > 0 else 1e300
            lo = max(0.0, -s) + 1e-12
            ref = optimize.minimize_scalar(f, bounds=(lo, b0 + 10 * sig + 10), method="bounded",
                                           options={"xatol": 1e-11}).x
            self.assertAlmostEqual(ll._b_hat(n, s, b0, sig), ref, delta=1e-6, msg=(n, s, b0, sig))

    def test_calibration_gate_large_counts_consistent(self):
        r = ll.profile_significance(60, 45.0, 0.0, 20000, 7)
        self.assertEqual(r["asymptotic_calibration"]["verdict"], "consistent", r["asymptotic_calibration"])

    def test_calibration_gate_low_counts_inapplicable(self):
        # n = 3, b = 0.3: exact tail 0.0036, half-chi2 0.0019; 20000 toys resolve the factor of two
        r = ll.profile_significance(3, 0.3, 0.0, 20000, 7)
        gate = r["asymptotic_calibration"]
        self.assertEqual(gate["verdict"], "inapplicable", gate)
        lo, hi = gate["toy_interval"]
        self.assertTrue(lo <= r["p_value_exact_poisson"] <= hi)       # the toys agree with the exact tail

    def test_calibration_gate_unresolved_without_exceedances(self):
        r = ll.profile_significance(20, 1.0, 0.0, 100, 1)
        self.assertEqual(r["asymptotic_calibration"]["verdict"], "unresolved")


if __name__ == "__main__":
    unittest.main()

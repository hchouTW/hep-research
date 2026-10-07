"""Tests for core/stats/_poisson.py: one mean limit for core/stats, and a distribution, tail and quantile that stay
accurate up to it (log-space sums; no exp(-mu) underflow above mu of about 745, no 1 - P cancellation in the tail).
Reference values: SciPy 1.18 (scipy.stats.poisson, recorded below) and decimal arithmetic computed in the test.
Run from the plugin root with `python3 -m unittest discover -s tests -t .`."""
import math
import random
import sys
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import _poisson as P  # noqa: E402
from core.stats import likelihood_limits, poisson_diagnostics, statistical_toys  # noqa: E402


def decimal_log_cdf(n, mu, digits):
    """ln P(N <= n | mu) summed downward from k = n in decimal arithmetic (an independent route)."""
    with localcontext() as ctx:
        ctx.prec = digits
        m = Decimal(repr(mu))
        log_term = n * m.ln() - m - Decimal(math.lgamma(n + 1)) if n > 170 else n * m.ln() - m - Decimal(math.factorial(n)).ln()
        term, total, k = Decimal(1), Decimal(0), n
        while k >= 0 and (total == 0 or term > total * Decimal(10) ** -30):
            total += term
            term = term * k / m
            k -= 1
        return float(log_term + total.ln())


class PoissonNumericsTests(unittest.TestCase):
    def test_one_limit_for_every_module(self):
        for mod in (poisson_diagnostics, likelihood_limits, statistical_toys):
            self.assertEqual(mod.MAX_MEAN, P.MAX_MEAN, mod.__name__)

    def test_against_scipy_above_the_old_limit(self):
        self.assertAlmostEqual(P.cdf(900, 1000.0) / 0.0006977673277963054, 1.0, delta=1e-9)
        self.assertAlmostEqual(P.sf(1101, 1000.0) / 0.0008676409634435647, 1.0, delta=1e-9)  # scipy sf(1100) = P(N > 1100)
        self.assertAlmostEqual(P.log_sf(101000, 1e5), -7.1311475592836615, delta=1e-8)

    def test_deep_tails_stay_finite_where_scipy_underflows(self):
        ref = decimal_log_cdf(80000, 1e5, 60)  # scipy.stats.poisson.logcdf(80000, 1e5) returns -inf
        self.assertAlmostEqual(P.log_cdf(80000, 1e5), ref, delta=1e-6 * abs(ref))
        self.assertTrue(math.isfinite(P.log_sf(130000, 1e5)))

    def test_small_means_match_direct_summation(self):
        for n, mu in ((0, 0.5), (3, 3.0), (10, 2.0), (2, 9.0)):
            direct = sum(math.exp(-mu) * mu ** k / math.factorial(k) for k in range(n + 1))
            self.assertAlmostEqual(P.cdf(n, mu), direct, delta=1e-14)
            self.assertAlmostEqual(P.sf(n + 1, mu), 1.0 - direct, delta=1e-14)
        self.assertEqual(P.log_cdf(-1, 3.0), -math.inf)
        self.assertEqual(P.log_sf(0, 3.0), 0.0)
        self.assertEqual(P.cdf(4, 0.0), 1.0)

    def test_quantile_inverts_the_distribution_up_to_the_limit(self):
        rng = random.Random(3)
        for mu in (0.3, 5.0, 699.0, 701.0, 5e3, 1e5):
            for _ in range(50):
                u = rng.random()
                k = P.ppf(u, mu)
                self.assertGreaterEqual(P.cdf(k, mu), u - 1e-12, msg=(mu, u))
                if k > 0:
                    self.assertLess(P.cdf(k - 1, mu), u + 1e-12, msg=(mu, u))
        self.assertEqual(P.ppf(0.5, 0.0), 0)


if __name__ == "__main__":
    unittest.main()

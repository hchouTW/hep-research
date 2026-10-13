"""hep-statistics audit T29: PCL, efficiency and ratio constructions (pcl_efficiency_ratio.py, EXPERIMENTAL). SYNTHETIC.
PCL: the power constraint equals the classical limit at the threshold quantile of the background-only count (an
independent SciPy quantile), the PCL is never below the unconstrained limit, and its exact coverage is at least the
unconstrained one, which is at least nominal. Efficiency: Clopper-Pearson's exact minimum coverage over a fine grid is
at least cl; the Jeffreys credible interval falls below cl somewhere and is labelled a credible interval. Ratio:
Fieller's set covers at nominal (4 standard errors) also when the denominator is near zero, where it becomes the
complement of an interval or the whole line; the delta-method interval does not."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import pcl_efficiency_ratio as p  # noqa: E402


class Pcl(unittest.TestCase):
    def test_constraint_and_coverage(self):
        b, cl, thr = 3.0, 0.95, 0.16
        m = int(stats.poisson.ppf(thr, b))
        while stats.poisson.cdf(m, b) < thr:
            m += 1
        ref = max(p.classical_upper(m, b, cl), 0.0)
        r = p.pcl(0, b, cl, thr)
        self.assertAlmostEqual(r["power_constraint"], ref, places=9)
        self.assertTrue(r["constrained"])
        self.assertGreaterEqual(r["pcl_limit"], r["unconstrained_limit"])
        self.assertFalse(p.pcl(8, b, cl, thr)["constrained"])
        for s in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0):
            c = p.pcl_coverage(s, b, cl, thr)
            self.assertGreaterEqual(c["coverage_unconstrained"], cl - 1e-12, s)
            self.assertGreaterEqual(c["coverage_pcl"], c["coverage_unconstrained"] - 1e-12, s)


class PclLargeCountsSTH35(unittest.TestCase):
    """STH-T3.5: the classical limit is the exact Gamma quantile (no fixed bracket at 1e4), and the power threshold is
    found from the Poisson quantile, so n, b = 1e4 and 1e5 work and b = 1e5 finishes in well under a second."""

    def test_large_counts(self):
        import time
        from scipy import stats as st
        for n, b in ((10000, 10000.0), (100000, 100000.0)):
            with self.subTest(n=n):
                t0 = time.perf_counter()
                r = p.pcl(n, b, 0.95, 0.16)
                self.assertLess(time.perf_counter() - t0, 1.0)
                mu = r["unconstrained_limit"] + b
                self.assertAlmostEqual(st.poisson.cdf(n, mu), 0.05, delta=1e-6)
                self.assertGreater(r["pcl_limit"], 0)

    def test_small_counts_unchanged(self):
        self.assertAlmostEqual(p.classical_upper(0, 0.0, 0.95), -math.log(0.05), places=9)
        self.assertAlmostEqual(p.classical_upper(0, 2.0, 0.95), -math.log(0.05) - 2.0, places=9)


class Efficiency(unittest.TestCase):
    def test_confidence_versus_credible(self):
        grid = np.linspace(0.005, 0.995, 199)
        ec = p.efficiency_coverage(20, 0.6827, grid, "jeffreys")
        self.assertGreaterEqual(ec["min_coverage_clopper_pearson"], 0.6827)
        self.assertLess(ec["min_coverage_beta_credible"], 0.6827)
        r = p.efficiency(0, 20)
        self.assertEqual(r["clopper_pearson"]["interval"][0], 0.0)
        self.assertIn("credible", r["beta_credible"]["kind"])


class Ratio(unittest.TestCase):
    def test_fieller_covers_and_reports_unbounded_sets(self):
        se = 4 * math.sqrt(0.6827 * 0.3173 / 4000)
        for my, delta_fails in ((10.0, False), (3.0, True), (1.0, False), (0.3, True)):
            r = p.ratio_coverage(5.0, 1.0, my, 1.0, 0.0, 0.6827, 4000, 1)
            self.assertLess(abs(r["coverage_fieller"] - 0.6827), se, (my, r))
            if delta_fails:
                self.assertGreater(abs(r["coverage_delta_method"] - 0.6827), se, (my, r))
        r = p.ratio_coverage(5.0, 1.0, 1.0, 1.0)
        self.assertGreater(r["set_kinds"]["complement"], 0)
        r = p.ratio_coverage(0.5, 1.0, 0.3, 1.0)
        self.assertGreater(r["set_kinds"]["unbounded"], 0)
        self.assertLess(abs(r["coverage_fieller"] - 0.6827), se)
        whole = p.fieller(0.2, 1.0, 0.1, 1.0)
        self.assertEqual(whole["fieller"]["set"], [[-math.inf, math.inf]])

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            p.fieller(1.0, 0.0, 1.0, 1.0)


if __name__ == "__main__":
    unittest.main()

"""D11: core/stats/change_point.py, change points in a series with known per-point uncertainties.

Oracles:
- the step statistic at a split equals |m2 - m1| / sqrt(1/W1 + 1/W2) (weighted means, W = sum 1/sigma^2);
- under the null (no change) the fraction of series with a detection at the toy-calibrated threshold equals the
  declared false-alarm rate (binomial tolerance; the large ensemble is in the slow tier);
- an injected step is found at the right place, and the detection power is at least the analytic power of the test
  at the true split point, Phi(mu - threshold), mu = Delta / sqrt(1/W1 + 1/W2), and not far above it;
- CUSUM: the toy-calibrated threshold gives the declared false-alarm rate, and a step raises an alarm after it;
- weighted constant and linear fits: chi2 and the exact slope of a noiseless line.
Standard library only.
"""
import math
import os
import random
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import change_point as cp  # noqa: E402

ND = statistics.NormalDist()
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"


def binom_tol(p, n, k=3.5):
    return k * math.sqrt(p * (1 - p) / n)


class StepStatistic(unittest.TestCase):
    def test_statistic_at_a_split(self):
        y = [1.0, 2.0, 1.5, 4.0, 5.0]
        s = [1.0, 0.5, 1.0, 2.0, 1.0]
        z = cp.split_statistics(y, s)
        w = [1 / x ** 2 for x in s]
        k = 3
        m1 = sum(wi * yi for wi, yi in zip(w[:k], y[:k])) / sum(w[:k])
        m2 = sum(wi * yi for wi, yi in zip(w[k:], y[k:])) / sum(w[k:])
        expect = abs(m2 - m1) / math.sqrt(1 / sum(w[:k]) + 1 / sum(w[k:]))
        self.assertAlmostEqual(z[k], expect, delta=1e-12)
        best = cp.best_split(y, s)
        self.assertEqual(best["index"], max(range(1, len(y)), key=lambda i: z[i]))

    def test_bad_input(self):
        for y, s in (([1.0], [1.0]), ([1.0, 2.0], [1.0]), ([1.0, float("nan")], [1.0, 1.0]), ([1.0, 2.0], [1.0, 0.0])):
            with self.subTest(y=y, s=s), self.assertRaises(cp.ChangePointError):
                cp.best_split(y, s)


class FalseAlarmAndPower(unittest.TestCase):
    N, ALPHA = 40, 0.1

    def calibrated(self, sigma, seed=1, toys=4000, method="segmentation"):
        return cp.calibrate_threshold(sigma, self.ALPHA, toys=toys, seed=seed, method=method)

    def test_null_false_alarm_rate(self):
        sigma = [1.0 + 0.5 * (i % 3) for i in range(self.N)]
        cal = self.calibrated(sigma)
        rng = random.Random(77)
        series = 4000 if SLOW else 600
        hits = sum(bool(cp.binary_segmentation([rng.gauss(0, s) for s in sigma], sigma, cal["threshold"]))
                   for _ in range(series))
        self.assertAlmostEqual(hits / series, self.ALPHA, delta=binom_tol(self.ALPHA, series) + 0.02)

    def test_injected_step_location_and_power(self):
        sigma = [1.0] * self.N
        thr = self.calibrated(sigma)["threshold"]
        k_true = self.N // 2
        se = math.sqrt(1 / k_true + 1 / (self.N - k_true))
        delta = (thr + 1.0) * se  # mu = thr + 1 at the true split
        rng = random.Random(5)
        runs = 2000 if SLOW else 500
        found = 0
        for _ in range(runs):
            y = [rng.gauss(0, 1) + (delta if i >= k_true else 0.0) for i in range(self.N)]
            found += bool(cp.binary_segmentation(y, sigma, thr))
        power = found / runs
        lower = ND.cdf(1.0)
        self.assertGreaterEqual(power, lower - binom_tol(lower, runs))
        self.assertLessEqual(power, lower + 0.1)
        # a large step is placed exactly
        hits = 0
        for _ in range(200):
            y = [rng.gauss(0, 1) + (6 * se * 3 if i >= k_true else 0.0) for i in range(self.N)]
            segs = cp.binary_segmentation(y, sigma, thr)
            hits += any(abs(c["index"] - k_true) <= 1 for c in segs)
        self.assertGreaterEqual(hits, 196)

    def test_cusum_false_alarm_and_detection(self):
        sigma = [1.0] * self.N
        cal = cp.calibrate_threshold(sigma, self.ALPHA, toys=4000, seed=3, method="cusum", cusum_k=0.5,
                                     reference_points=10)
        rng = random.Random(8)
        series = 2000 if SLOW else 500
        hits = sum(cp.cusum_first_alarm([rng.gauss(0, 1) for _ in sigma], sigma, 0.5, cal["threshold"],
                                        reference_points=10) is not None for _ in range(series))
        self.assertAlmostEqual(hits / series, self.ALPHA, delta=binom_tol(self.ALPHA, series) + 0.02)
        y = [rng.gauss(0, 1) + (3.0 if i >= 25 else 0.0) for i in range(self.N)]
        alarm = cp.cusum_first_alarm(y, sigma, 0.5, cal["threshold"], reference_points=10)
        self.assertIsNotNone(alarm)
        self.assertGreaterEqual(alarm, 25)


class Fits(unittest.TestCase):
    def test_linear_fit_exact(self):
        t = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [2.0 + 0.5 * x for x in t]
        fit = cp.weighted_fit(t, y, [0.1] * 5, "linear")
        self.assertAlmostEqual(fit["params"]["slope"], 0.5, delta=1e-12)
        self.assertAlmostEqual(fit["params"]["intercept"], 2.0, delta=1e-12)
        self.assertAlmostEqual(fit["chi2"], 0.0, delta=1e-18)
        self.assertEqual(fit["ndf"], 3)

    def test_constant_fit_chi2(self):
        fit = cp.weighted_fit([0, 1, 2], [1.0, 3.0, 2.0], [1.0, 1.0, 1.0], "constant")
        self.assertAlmostEqual(fit["params"]["mean"], 2.0)
        self.assertAlmostEqual(fit["chi2"], 2.0)
        self.assertAlmostEqual(fit["p_value"], math.exp(-1.0), delta=1e-12)  # chi2 = 2, ndf = 2

    def test_piecewise_constant(self):
        fit = cp.piecewise_constant([1.0, 1.0, 3.0, 3.0], [1.0] * 4, [2])
        self.assertEqual([s["mean"] for s in fit["segments"]], [1.0, 3.0])
        self.assertAlmostEqual(fit["chi2"], 0.0)


if __name__ == "__main__":
    unittest.main()

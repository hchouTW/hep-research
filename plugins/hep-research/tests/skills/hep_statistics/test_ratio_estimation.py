"""hep-statistics audit T30: likelihood-ratio estimation by classification against an analytic Gaussian oracle
(ratio_estimation.py, EXPERIMENTAL). SYNTHETIC. The estimate agrees with the exact log-ratio on held-out data and
across training seeds; the calibration identities hold for the intended model; a domain shift (nuisance width
doubled) and an estimator trained without the nuisance are rejected, with power estimated and at least 0.9; the false
rejection rate of the calibration test on the intended model stays small; without a power estimate the result is
inconclusive, not pass."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import ratio_estimation as r  # noqa: E402


class RatioEstimation(unittest.TestCase):
    def test_passes_with_stated_power(self):
        o = r.check(seed=1, power_runs=30)
        self.assertEqual(o["status"], "pass", o)
        self.assertLess(o["rms_logr_error_vs_exact"], 0.05)
        self.assertGreaterEqual(min(o["power"].values()), 0.9)

    def test_false_rejection_rate(self):
        w = r.train(np.random.default_rng(5), 0.5, 0.5, 40000)
        rng = np.random.default_rng(6)
        rejects = sum(r.calibration(w, rng, 0.5, 0.5, 20000)["reject"] for _ in range(40))
        self.assertLessEqual(rejects, 2)

    def test_negative_baselines_fail(self):
        wrong = r.train(np.random.default_rng(7), 0.5, 0.0, 40000)
        self.assertTrue(r.calibration(wrong, np.random.default_rng(8), 0.5, 0.5, 20000)["reject"])
        good = r.train(np.random.default_rng(9), 0.5, 0.5, 40000)
        self.assertTrue(r.calibration(good, np.random.default_rng(10), 0.5, 1.0, 20000)["reject"])

    def test_without_power_estimate_inconclusive(self):
        self.assertEqual(r.check(seed=2, power_runs=0)["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()

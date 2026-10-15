"""Scientific checks of assets/hep_metrics.py against analytic or construction-known answers (NumPy only)."""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ASSET = Path(__file__).resolve().parents[3] / "skills" / "hep-ml" / "assets" / "hep_metrics.py"
spec = importlib.util.spec_from_file_location("hep_metrics", ASSET)
hm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hm)


def gaussian_sample(n, delta, seed=0):
    rng = np.random.default_rng(seed)
    s = np.r_[rng.normal(delta, 1, n), rng.normal(0, 1, n)]
    y = np.r_[np.ones(n), np.zeros(n)]
    return s, y


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class RocAuc(unittest.TestCase):
    def test_auc_matches_gaussian_analytic(self):
        s, y = gaussian_sample(200_000, 1.0)
        self.assertAlmostEqual(hm.weighted_auc(s, y), norm_cdf(1.0 / math.sqrt(2)), delta=3e-3)

    def test_auc_equals_mann_whitney_with_ties(self):
        rng = np.random.default_rng(1)
        s = rng.integers(0, 5, 400).astype(float)
        y = rng.integers(0, 2, 400)
        sig, bkg = s[y == 1], s[y == 0]
        mw = (np.sum(sig[:, None] > bkg[None, :]) + 0.5 * np.sum(sig[:, None] == bkg[None, :])) / (sig.size * bkg.size)
        self.assertAlmostEqual(hm.weighted_auc(s, y), mw, places=12)

    def test_integer_weights_equal_duplication(self):
        rng = np.random.default_rng(2)
        s, y = rng.normal(size=300), rng.integers(0, 2, 300)
        w = rng.integers(1, 4, 300)
        self.assertAlmostEqual(hm.weighted_auc(s, y, w), hm.weighted_auc(np.repeat(s, w), np.repeat(y, w)), places=12)

    def test_cancelling_signed_weights_leave_roc_unchanged(self):
        s, y = gaussian_sample(2000, 1.0, seed=3)
        rng = np.random.default_rng(4)
        extra_s, extra_y = rng.normal(size=500), rng.integers(0, 2, 500)
        s2 = np.r_[s, extra_s, extra_s]
        y2 = np.r_[y, extra_y, extra_y]
        w2 = np.r_[np.ones(s.size), np.full(500, 2.0), np.full(500, -2.0)]
        self.assertAlmostEqual(hm.weighted_auc(s2, y2, w2), hm.weighted_auc(s, y), places=10)

    def test_non_positive_class_total_raises(self):
        with self.assertRaises(ValueError):
            hm.weighted_roc([0.1, 0.9], [1, 0], [-1.0, 1.0])

    def test_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            hm.weighted_roc([0.1, 0.2], [1], None)


class Efficiency(unittest.TestCase):
    def test_unit_weights_give_binomial(self):
        p = np.r_[np.ones(30, bool), np.zeros(70, bool)]
        eps, unc = hm.efficiency_with_uncertainty(p)
        self.assertAlmostEqual(eps, 0.3)
        self.assertAlmostEqual(unc, math.sqrt(0.3 * 0.7 / 100))

    def test_rejection_at_working_point_gaussian(self):
        s, y = gaussian_sample(400_000, 2.0, seed=5)
        wp = hm.rejection_at_signal_efficiency(s, y, eff_s=0.5)
        expected_eff_b = 1 - norm_cdf(2.0)          # cut at the signal median, 2.0
        self.assertAlmostEqual(wp["eff_s"], 0.5, delta=1e-3)
        self.assertAlmostEqual(wp["eff_b"], expected_eff_b, delta=4 * wp["eff_b_unc"])


class Significance(unittest.TestCase):
    def test_small_signal_limit(self):
        self.assertAlmostEqual(hm.asimov_significance(1.0, 1e4), 1.0 / 100, delta=1e-5)

    def test_reference_value(self):
        z = math.sqrt(2 * ((10 + 5) * math.log(1 + 10 / 5) - 10))
        self.assertAlmostEqual(hm.asimov_significance(10, 5), z, places=12)

    def test_uncertainty_lowers_and_vanishing_uncertainty_recovers(self):
        z0 = hm.asimov_significance(20, 100)
        self.assertLess(hm.asimov_significance(20, 100, sigma_b=10), z0)
        self.assertAlmostEqual(hm.asimov_significance(20, 100, sigma_b=1e-4), z0, places=5)


class DistanceCorrelation(unittest.TestCase):
    def test_identity_is_one(self):
        x = np.random.default_rng(6).normal(size=300)
        self.assertAlmostEqual(hm.distance_correlation_sq(x, x), 1.0, places=10)

    def test_independent_is_small(self):
        rng = np.random.default_rng(7)
        self.assertLess(hm.distance_correlation_sq(rng.normal(size=1500), rng.normal(size=1500)), 0.01)

    def test_detects_nonlinear_dependence(self):
        x = np.random.default_rng(8).normal(size=1500)
        self.assertLess(abs(np.corrcoef(x, x ** 2)[0, 1]), 0.1)
        self.assertGreater(hm.distance_correlation_sq(x, x ** 2), 0.2)

    def test_integer_weights_equal_duplication(self):
        rng = np.random.default_rng(9)
        x, y = rng.normal(size=200), rng.normal(size=200)
        y = y + 0.5 * x
        w = rng.integers(1, 4, 200)
        self.assertAlmostEqual(hm.distance_correlation_sq(x, y, w),
                               hm.distance_correlation_sq(np.repeat(x, w), np.repeat(y, w)), places=10)

    def test_negative_weights_rejected(self):
        with self.assertRaises(ValueError):
            hm.distance_correlation_sq([1, 2, 3], [1, 2, 3], [1, -1, 1])


class Sculpting(unittest.TestCase):
    def test_independent_score_does_not_sculpt_dependent_does(self):
        rng = np.random.default_rng(10)
        m = rng.exponential(50, 100_000) + 50
        flat = hm.mass_sculpting_jsd(m, rng.uniform(size=m.size), 0.5, mass_range=(50, 300))["jsd"]
        sculpt = hm.mass_sculpting_jsd(m, m + rng.normal(0, 20, m.size), 100, mass_range=(50, 300))["jsd"]
        self.assertLess(flat, 1e-3)
        self.assertGreater(sculpt, 0.1)


class PriorShift(unittest.TestCase):
    def test_identity_and_odds(self):
        p = np.array([0.1, 0.5, 0.9])
        np.testing.assert_allclose(hm.undo_prior_shift(p, 1.0), p)
        q = hm.undo_prior_shift(p, 0.01)
        np.testing.assert_allclose(q / (1 - q), 0.01 * p / (1 - p))


class Cli(unittest.TestCase):
    def test_cli_strict_json_and_bad_input(self):
        s, y = gaussian_sample(500, 1.0, seed=11)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ev.csv"
            f.write_text("score,label,weight,m\n" + "".join(
                f"{a},{int(b)},1.0,{100 + 10 * a}\n" for a, b in zip(s, y)))
            r = subprocess.run([sys.executable, "-I", str(ASSET), str(f), "--eff-s", "0.5", "--mass-col", "m"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertIn("sculpting", out["working_points"][0])
            bad = Path(d) / "bad.csv"
            bad.write_text("x,y\n1,2\n")
            r = subprocess.run([sys.executable, "-I", str(ASSET), str(bad)], capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 2)


class EdgeCases(unittest.TestCase):
    def test_full_signal_efficiency_survives_rounding(self):
        rng = np.random.default_rng(12)
        for _ in range(200):
            n = int(rng.integers(5, 60))
            s, y = rng.normal(size=n), np.r_[1, 0, rng.integers(0, 2, n - 2)]
            w = rng.uniform(0.1, 3.0, n)
            self.assertAlmostEqual(hm.rejection_at_signal_efficiency(s, y, w, 1.0)["eff_s"], 1.0, places=9)

    def test_eff_s_out_of_range_and_bad_labels(self):
        s, y = gaussian_sample(50, 1.0)
        for bad in (0.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                hm.rejection_at_signal_efficiency(s, y, eff_s=bad)
        with self.assertRaises(ValueError):
            hm.weighted_roc(s, 2 * y - 1)

    def test_no_background_passing_gives_bound_not_infinity(self):
        s = np.r_[np.full(10, 0.9), np.full(100, 0.1)]
        y = np.r_[np.ones(10), np.zeros(100)]
        wp = hm.rejection_at_signal_efficiency(s, y, eff_s=1.0)
        self.assertIsNone(wp["rejection"])
        self.assertIn("warning", wp)
        self.assertAlmostEqual(wp["rejection_lower_bound_95"], 100 / 3)

    def test_sculpting_baseline_matches_noise_level(self):
        rng = np.random.default_rng(13)
        m = rng.exponential(50, 20_000) + 50
        res = hm.mass_sculpting_jsd(m, rng.uniform(size=m.size), 0.95, mass_range=(50, 300), baseline=True)
        self.assertIn("jsd_baseline", res)
        self.assertLess(abs(res["jsd"] - res["jsd_baseline"]), 3 * res["jsd_baseline"] + 1e-3)

    def test_zero_weights_rejected_in_dcor(self):
        with self.assertRaises(ValueError):
            hm.distance_correlation_sq([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()

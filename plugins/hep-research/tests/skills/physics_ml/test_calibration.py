"""Scientific checks of assets/calibration.py against construction-known answers (NumPy; SciPy optional)."""
import csv
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ASSET = Path(__file__).resolve().parents[3] / "skills" / "physics-ml" / "assets" / "calibration.py"
spec = importlib.util.spec_from_file_location("calibration", ASSET)
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)


def toy(n, seed, temperature=3.0):
    """Labels drawn from p_true = sigmoid(z); the model reports sigmoid(temperature * z) (over-confident if > 1)."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, 2.0, n)
    y = (rng.random(n) < cal.sigmoid(z)).astype(int)
    return temperature * z, y


class Temperature(unittest.TestCase):
    def test_recovers_known_temperature(self):
        logits, y = toy(200_000, 0, 3.0)
        res = cal.fit_temperature(logits, y)
        self.assertAlmostEqual(res["temperature"], 3.0, delta=0.06)
        self.assertFalse(res["at_bound"])

    def test_calibrated_input_stays_calibrated(self):
        logits, y = toy(200_000, 1, 1.0)
        self.assertAlmostEqual(cal.fit_temperature(logits, y)["temperature"], 1.0, delta=0.03)

    def test_golden_section_fallback_agrees(self):
        logits, y = toy(20_000, 2, 3.0)
        f = lambda lt: cal._nll_from_logits(logits / math.exp(lt), y.astype(float), np.ones(y.size))  # noqa: E731
        lt = cal._golden_min(f, math.log(0.05), math.log(20.0))
        self.assertAlmostEqual(math.exp(lt), cal.fit_temperature(logits, y)["temperature"], delta=1e-4)

    def test_integer_weights_equal_duplication(self):
        logits, y = toy(5_000, 3, 2.0)
        w = np.random.default_rng(4).integers(1, 4, y.size)
        a = cal.fit_temperature(logits, y, w)["temperature"]
        b = cal.fit_temperature(np.repeat(logits, w), np.repeat(y, w))["temperature"]
        self.assertAlmostEqual(a, b, places=5)

    def test_platt_recovers_inverse_temperature(self):
        logits, y = toy(200_000, 5, 3.0)
        res = cal.fit_platt(logits, y)
        self.assertAlmostEqual(res["a"], 1 / 3.0, delta=0.01)
        self.assertAlmostEqual(res["b"], 0.0, delta=0.02)

    def test_signed_weights_need_positive_class_totals(self):
        with self.assertRaises(ValueError):
            cal.fit_temperature([1.0, -1.0, 0.5], [1, 0, 1], [-1.0, 1.0, 0.5])


class Isotonic(unittest.TestCase):
    def test_pav_is_monotone_and_preserves_weighted_mean(self):
        rng = np.random.default_rng(6)
        v, w = rng.normal(size=500), rng.uniform(0.1, 3.0, 500)
        fitted, _ = cal.pav(v, w)
        self.assertTrue(np.all(np.diff(fitted) >= -1e-12))
        self.assertAlmostEqual(np.sum(w * fitted), np.sum(w * v), places=9)

    def test_pav_known_small_case(self):
        fitted, _ = cal.pav([1.0, 3.0, 2.0, 4.0], [1.0, 1.0, 3.0, 1.0])
        np.testing.assert_allclose(fitted, [1.0, 2.25, 2.25, 4.0])

    def test_isotonic_reduces_ece_to_finite_sample_floor(self):
        z_fit, y_fit = toy(100_000, 7)
        z_ev, y_ev = toy(100_000, 8)
        fmap, info = cal.fit_isotonic(cal.sigmoid(z_fit), y_fit)
        self.assertTrue(np.all(np.diff(fmap.y) >= 0))
        self.assertTrue(np.all(np.diff(fmap.x) > 0))
        before = cal.calibration_report(cal.sigmoid(z_ev), y_ev)
        after = cal.calibration_report(fmap(cal.sigmoid(z_ev)), y_ev)
        self.assertGreater(before["ece"], 0.1)
        self.assertLess(after["ece"], 3.0 * after["ece_floor"])
        self.assertLess(after["ece"], 0.01)

    def test_negative_weights_refused_by_default_and_merge_is_monotone(self):
        z, y = toy(20_000, 9)
        w = np.where(np.random.default_rng(10).random(y.size) < 0.1, -1.0, 1.0)
        with self.assertRaises(ValueError):
            cal.fit_isotonic(cal.sigmoid(z), y, w)
        fmap, info = cal.fit_isotonic(cal.sigmoid(z), y, w, negative_weights="merge")
        self.assertEqual(info["n_negative"], int(np.sum(w < 0)))
        self.assertTrue(np.all(np.diff(fmap.y) >= 0))
        self.assertTrue(np.all((fmap.y >= 0) & (fmap.y <= 1)))

    def test_merge_cells_keep_net_weight(self):
        x = np.arange(6.0)
        w = np.array([1.0, -0.4, 1.0, 1.0, -0.3, 0.1])
        wy = w * np.array([1, 0, 0, 1, 1, 0])
        lo, hi, vals, cw = cal._merge_to_positive_cells(x, w, wy, np.abs(w))
        self.assertAlmostEqual(cw.sum(), w.sum())
        self.assertTrue(np.all(cw > 0))


class Reliability(unittest.TestCase):
    def test_unit_weight_uncertainty_is_binomial(self):
        rng = np.random.default_rng(11)
        p = rng.random(5_000)
        y = (rng.random(p.size) < p).astype(int)
        t = cal.reliability_curve(p, y, n_bins=10)
        for r in t["bins"]:
            f, n = r["observed"], r["n"]
            self.assertAlmostEqual(r["observed_unc"], math.sqrt(f * (1 - f) / n), places=12)

    def test_integer_weights_equal_duplication(self):
        rng = np.random.default_rng(12)
        p = rng.random(3_000)
        y = (rng.random(p.size) < p ** 1.5).astype(int)
        w = rng.integers(1, 5, p.size)
        for binning in ("equal-width", "equal-mass"):
            a = cal.calibration_report(p, y, w, n_bins=12, binning=binning)
            b = cal.calibration_report(np.repeat(p, w), np.repeat(y, w), n_bins=12, binning=binning)
            self.assertAlmostEqual(a["ece"], b["ece"], places=12)
            self.assertAlmostEqual(a["mce"], b["mce"], places=12)
            for ra, rb in zip(a["table"]["bins"], b["table"]["bins"]):
                self.assertAlmostEqual(ra["observed"], rb["observed"], places=12)
                self.assertAlmostEqual(ra["mean_pred"], rb["mean_pred"], places=12)
                # The uncertainty is deliberately NOT duplication invariant: one event of weight 3 carries more
                # MC-statistics variance (w^2 = 9) than three independent unit-weight events.
                self.assertGreaterEqual(ra["observed_unc"], rb["observed_unc"] - 1e-15)

    def test_equal_mass_bins_have_equal_weight(self):
        rng = np.random.default_rng(13)
        p = rng.beta(2, 5, 10_000)
        t = cal.reliability_curve(p, (rng.random(p.size) < p).astype(int), n_bins=10, binning="equal-mass")
        self.assertEqual(t["n_bins_effective"], 10)
        for r in t["bins"]:
            self.assertEqual(r["n"], 1_000)

    def test_perfect_calibration_ece_near_floor(self):
        rng = np.random.default_rng(14)
        p = rng.random(100_000)
        y = (rng.random(p.size) < p).astype(int)
        r = cal.calibration_report(p, y, n_bins=15)
        self.assertLess(r["ece"], 2.5 * r["ece_floor"])

    def test_nonpositive_weight_bin_excluded(self):
        p = np.array([0.05, 0.06, 0.55, 0.56, 0.95])
        y = np.array([0, 0, 1, 0, 1])
        w = np.array([1.0, 1.0, 1.0, -2.0, 1.0])
        t = cal.reliability_curve(p, y, w, n_bins=10)
        self.assertEqual(t["n_nonpositive_weight_bins"], 1)
        self.assertIsNone(t["bins"][5]["observed"])
        cal.expected_calibration_error(t)        # still defined from the other bins


class Provenance(unittest.TestCase):
    def test_same_sample_refused_unless_allowed(self):
        with self.assertRaises(ValueError):
            cal.sample_provenance("val.csv", "val.csv")
        rec = cal.sample_provenance("val.csv", "val.csv", allow_same_sample=True)
        self.assertFalse(rec["disjoint"])
        self.assertTrue(rec["same_sample_allowed"])

    def test_overlapping_ids_refused(self):
        with self.assertRaises(ValueError):
            cal.sample_provenance("a", "b", [1, 2, 3], [3, 4])
        self.assertTrue(cal.sample_provenance("a", "b", [1, 2], [3, 4])["disjoint"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write_csv(self, name, seed, n=20_000):
        z, y = toy(n, seed)
        path = self.dir / name
        with open(path, "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["score", "label", "weight"])
            for zi, yi in zip(cal.sigmoid(z), y):
                wr.writerow([repr(float(zi)), int(yi), 1.0])
        return path

    def run_cli(self, *args):
        # these samples carry no event ids; the id check is declined explicitly (PML-WP0.1)
        args = (*args, "--no-id-check") if "--id-col" not in map(str, args) else args
        return subprocess.run([sys.executable, str(ASSET), *map(str, args)], capture_output=True, text=True,
                              timeout=120)

    def test_cli_strict_json_and_calibration_block(self):
        fit, ev = self.write_csv("fit.csv", 20), self.write_csv("eval.csv", 21)
        for method in ("temperature", "isotonic", "platt"):
            r = self.run_cli("--fit", fit, "--eval", ev, "--method", method, "--binning", "equal-mass")
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout, parse_constant=lambda c: self.fail(f"non-strict JSON constant {c}"))
            c = out["calibration"]
            self.assertEqual(set(c), {"method", "params", "fit_sample", "validation", "sample_check"})
            self.assertEqual(c["method"], method)
            self.assertEqual(c["fit_sample"], str(fit))
            self.assertEqual(set(c["validation"]), {"metric", "sample", "before", "after", "bins", "binning"})
            self.assertEqual(c["validation"]["metric"], "ece")
            self.assertEqual(c["validation"]["sample"], str(ev))
            self.assertEqual(c["validation"]["binning"], "equal-mass")
            self.assertIsInstance(c["validation"]["bins"], int)
            self.assertLess(c["validation"]["after"], c["validation"]["before"])
            self.assertTrue(out["sample_check"]["disjoint"])
            self.assertIn("after", out["reliability"])
        self.assertAlmostEqual(c["params"]["a"], 1 / 3.0, delta=0.05)

    def test_cli_refuses_same_sample_unless_flag(self):
        fit = self.write_csv("fit.csv", 22, 2_000)
        r = self.run_cli("--fit", fit, "--eval", fit)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not disjoint", r.stderr)
        copy = self.dir / "copy.csv"
        copy.write_bytes(fit.read_bytes())
        self.assertEqual(self.run_cli("--fit", fit, "--eval", copy).returncode, 2)   # same content hash
        r = self.run_cli("--fit", fit, "--eval", fit, "--allow-same-sample")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertFalse(out["sample_check"]["disjoint"])
        self.assertTrue(out["sample_check"]["same_sample_allowed"])

    def test_cli_json_input_and_prior_shift(self):
        z, y = toy(4_000, 23)
        p = cal.sigmoid(z)
        for name, sl in (("fit.json", slice(0, 2_000)), ("eval.json", slice(2_000, None))):
            (self.dir / name).write_text(json.dumps({"score": p[sl].tolist(), "label": y[sl].tolist()}))
        r = self.run_cli("--fit", self.dir / "fit.json", "--eval", self.dir / "eval.json", "--prior-ratio-change", 2)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["prior_shift"]["prior_ratio_change"], 2.0)


if __name__ == "__main__":
    unittest.main()

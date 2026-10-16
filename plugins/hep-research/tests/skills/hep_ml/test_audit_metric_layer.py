"""hep-ml audit (PML-WP1.5: ML-C11, C12, C15, C20, C21, C22): the metric, calibration and loss layer refuses or
flags what it used to pass silently.

Before the fix (0.9.0): signed-weight AUCs and efficiencies outside [0, 1] were printed without a flag; fractional
labels were truncated to 0; asimov_significance accepted a NaN or negative sigma_b and lost precision at s/b < 1e-6;
undo_prior_shift accepted r <= 0; temperature scaling at its search bound or against a prior shift gave no warning;
disco_penalty accepted negative weights unless asked. Cell resampling (Andersen & Maier, arXiv:2109.07851, eq. 2.2)
is new: it must preserve every cell's summed weight. All data SYNTHETIC.
"""
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

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills" / "hep-ml" / "assets"
sys.path.insert(0, str(ASSETS))
import hep_metrics as hm  # noqa: E402

TORCH = importlib.util.find_spec("torch") is not None


class MetricTests(unittest.TestCase):
    def test_asimov_inputs_and_precision(self):
        for bad in (dict(sigma_b=float("nan")), dict(sigma_b=-1.0)):
            with self.assertRaises(ValueError):
                hm.asimov_significance(5.0, 100.0, **bad)
        with self.assertRaises(ValueError):
            hm.asimov_significance(5.0, float("inf"))
        s, b = 1e-3, 1e5  # s/b = 1e-8: Z = s / sqrt(b) to first order
        self.assertAlmostEqual(hm.asimov_significance(s, b) / (s / math.sqrt(b)), 1.0, places=6)

    def test_prior_shift_needs_positive_ratio(self):
        for r in (0.0, -1.0, float("inf")):
            with self.assertRaises(ValueError):
                hm.undo_prior_shift([0.5], r)

    def test_fractional_label_is_refused_by_both_clis(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.csv"
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["id", "score", "label"])
                for i in range(40):
                    w.writerow([f"e{i}", 0.1 + 0.02 * i, 0.7 if i == 3 else i % 2])
            r = subprocess.run([sys.executable, str(ASSETS / "hep_metrics.py"), str(p)], capture_output=True, text=True,
                               timeout=600)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("not 0 or 1", r.stdout)       # F-04: the refusal is a JSON status on stdout
            r = subprocess.run([sys.executable, str(ASSETS / "calibration.py"), "--fit", str(p), "--eval", str(p),
                                "--allow-same-sample", "--id-col", "id"], capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("not 0 or 1", r.stdout)

    def test_signed_weight_out_of_range_flag(self):
        self.assertTrue(hm.signed_weight_out_of_range([0.2, 1.05]))
        self.assertTrue(hm.signed_weight_out_of_range(-0.01))
        self.assertFalse(hm.signed_weight_out_of_range([0.0, 0.5, 1.0]))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.csv"
            rng = np.random.default_rng(1)
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["score", "label", "weight"])
                for i in range(200):
                    lab = i % 2
                    # a cluster of negative background weight at high score drives eff_b below 0 there
                    wt = -3.0 if (lab == 0 and i > 180) else 1.0
                    w.writerow([float(rng.uniform(0.9, 1.0) if wt < 0 else rng.uniform()), lab, wt])
            r = subprocess.run([sys.executable, str(ASSETS / "hep_metrics.py"), str(p), "--eff-s", "0.5"],
                               capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["signed_weight_out_of_range"])

    def test_cell_resampling_preserves_cell_sums_and_removes_negatives(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=(2000, 2))
        w = np.where(rng.uniform(size=2000) < 0.1, -1.0, 1.0)
        new, rep = hm.cell_resample(x, w)
        self.assertEqual(rep["n_negative_after"], 0)
        self.assertAlmostEqual(new.sum(), w.sum(), places=9)
        # coarse observables keep their weighted sums (each cell is small and local)
        for lo, hi in ((-3, -1), (-1, 0), (0, 1), (1, 3)):
            sel = (x[:, 0] >= lo) & (x[:, 0] < hi)
            self.assertAlmostEqual(new[sel].sum() / w[sel].sum(), 1.0, delta=0.05)
        _, capped = hm.cell_resample(x, w, max_cell=2)
        self.assertGreater(capped["cells_still_negative"], 0)


class CalibrationWarningTests(unittest.TestCase):
    def test_temperature_warns_about_prior_shift(self):
        sys.path.insert(0, str(ASSETS))
        with tempfile.TemporaryDirectory() as td:
            rng = np.random.default_rng(3)
            for name, seed in (("fit.csv", 4), ("eval.csv", 5)):
                r = np.random.default_rng(seed)
                with open(Path(td) / name, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["score", "label"])
                    for _ in range(1000):
                        y = int(r.uniform() < 0.3)
                        w.writerow([float(np.clip(r.beta(4, 2) if y else r.beta(2, 4), 1e-6, 1 - 1e-6)), y])
            out = subprocess.run([sys.executable, str(ASSETS / "calibration.py"), "--fit", str(Path(td) / "fit.csv"),
                                  "--eval", str(Path(td) / "eval.csv"), "--no-id-check"], capture_output=True,
                                 text=True, timeout=600)
            del rng
        self.assertEqual(out.returncode, 0, out.stderr)
        warnings = json.loads(out.stdout)["calibration"]["warnings"]
        self.assertTrue(any("prior" in w for w in warnings))
        self.assertFalse(any("search bound" in w for w in warnings), warnings)  # an interior minimum: no bound warning

    def test_temperature_at_search_bound_warns_in_copied_block(self):
        """ML-C21 / CHECK-0.10.0 D-1: perfectly separated synthetic scores drive the temperature to its lower search
        bound (0.05); the warning must be in the calibration block that scripts/write_ml_artifact.py copies, not only in
        fit_details."""
        with tempfile.TemporaryDirectory() as td:
            for name, n in (("fit.csv", 400), ("eval.csv", 402)):
                with open(Path(td) / name, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["score", "label"])
                    for i in range(n):
                        y = i % 2
                        w.writerow([0.9 if y else 0.1, y])
            out = subprocess.run([sys.executable, str(ASSETS / "calibration.py"), "--fit", str(Path(td) / "fit.csv"),
                                  "--eval", str(Path(td) / "eval.csv"), "--no-id-check"], capture_output=True,
                                 text=True, timeout=600)
        self.assertEqual(out.returncode, 0, out.stderr)
        rep = json.loads(out.stdout)
        self.assertTrue(rep["fit_details"]["at_bound"], rep["fit_details"])
        self.assertAlmostEqual(rep["calibration"]["params"]["temperature"], 0.05, delta=1e-3)
        warnings = rep["calibration"]["warnings"]
        self.assertTrue(any("search bound" in w for w in warnings), warnings)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class DiscoTests(unittest.TestCase):
    def test_negative_weights_refused_by_default(self):
        import torch
        import hep_losses
        s, m = torch.rand(16), torch.rand(16)
        with self.assertRaises(ValueError):
            hep_losses.disco_penalty(s, m, torch.full((16,), -1.0))
        self.assertTrue(torch.isfinite(hep_losses.disco_penalty(s, m, torch.ones(16))))


if __name__ == "__main__":
    unittest.main()

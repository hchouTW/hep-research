"""Checks of assets/hep_losses.py; skipped cleanly without PyTorch."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

ASSETS = Path(__file__).resolve().parents[3] / "skills" / "physics-ml" / "assets"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipIf(torch is None, "PyTorch not installed")
class HepLosses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hl = _load("hep_losses")
        cls.hm = _load("hep_metrics")

    def test_disco_matches_numpy_reference(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=300)
        y = x ** 2 + rng.normal(size=300)
        w = rng.uniform(0.5, 2.0, 300)
        ref = self.hm.distance_correlation_sq(x, y, w)
        got = self.hl.disco_penalty(torch.tensor(x, dtype=torch.float64), torch.tensor(y, dtype=torch.float64),
                                    torch.tensor(w, dtype=torch.float64))
        self.assertAlmostEqual(float(got), ref, places=9)

    def test_disco_is_differentiable(self):
        x = torch.randn(64, dtype=torch.float64, requires_grad=True)
        m = torch.randn(64, dtype=torch.float64)
        self.hl.disco_penalty(torch.sigmoid(x), m).backward()
        self.assertTrue(torch.isfinite(x.grad).all())

    def test_weighted_bce_unit_weights_equal_mean(self):
        logits, t = torch.randn(50), (torch.rand(50) > 0.5).float()
        a = self.hl.weighted_bce(logits, t, torch.ones(50))
        b = torch.nn.functional.binary_cross_entropy_with_logits(logits, t)
        self.assertAlmostEqual(float(a), float(b), places=6)

    def test_weighted_bce_signed_and_shape_checks(self):
        logits, t = torch.randn(4), torch.tensor([1.0, 0.0, 1.0, 0.0])
        w = torch.tensor([1.0, -1.0, 1.0, 1.0])
        self.assertTrue(torch.isfinite(self.hl.weighted_bce(logits, t, w)))
        with self.assertRaises(ValueError):
            self.hl.weighted_bce(logits, t[:3])
        with self.assertRaises(ValueError):
            self.hl.weighted_bce(logits, t, w, norm="bogus")

    def test_masked_softmax_no_nan_on_empty_rows(self):
        scores = torch.randn(2, 5)
        mask = torch.tensor([[True, True, False, False, False], [False] * 5])
        out = self.hl.masked_softmax(scores, mask)
        self.assertTrue(torch.isfinite(out).all())
        self.assertAlmostEqual(float(out[0].sum()), 1.0, places=6)
        self.assertEqual(float(out[1].abs().sum()), 0.0)

    def test_masked_mean_empty_set(self):
        x = torch.randn(2, 4, 3)
        mask = torch.tensor([[True, False, True, False], [False] * 4])
        out = self.hl.masked_mean(x, mask)
        self.assertTrue(torch.allclose(out[0], (x[0, 0] + x[0, 2]) / 2))
        self.assertTrue(torch.equal(out[1], torch.zeros(3)))

    def test_disco_constant_scores_have_finite_gradient(self):
        x = torch.zeros(32, dtype=torch.float64, requires_grad=True)
        m = torch.randn(32, dtype=torch.float64)
        out = self.hl.disco_penalty(x * 1.0, m)
        out.backward()
        self.assertTrue(torch.isfinite(out))
        self.assertTrue(torch.isfinite(x.grad).all())

    def test_disco_half_precision_input_is_upcast(self):
        x = torch.rand(64).half()
        self.assertEqual(self.hl.disco_penalty(x, torch.rand(64)).dtype, torch.float32)

    def test_masked_softmax_rejects_mask_rank_mismatch(self):
        with self.assertRaises(ValueError):
            self.hl.masked_softmax(torch.randn(2, 3, 4, 4), torch.ones(2, 4, dtype=torch.bool))


if __name__ == "__main__":
    unittest.main()

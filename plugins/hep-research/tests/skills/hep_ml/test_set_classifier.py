"""Checks of assets/set_classifier.py: symmetry, masking, phi wrapping, a short CPU training run.

The torch-free parts (phi wrapping, features, --help without torch) always run; the rest skips without PyTorch.
"""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None

ASSET = Path(__file__).resolve().parents[3] / "skills" / "hep-ml" / "assets" / "set_classifier.py"
spec = importlib.util.spec_from_file_location("set_classifier", ASSET)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


class NoTorch(unittest.TestCase):
    def test_wrap_phi_range_and_values(self):
        x = np.linspace(-20, 20, 4001)
        w = sc.wrap_phi(x)
        self.assertTrue(np.all(w > -math.pi) and np.all(w <= math.pi))
        np.testing.assert_allclose(np.cos(w), np.cos(x), atol=1e-12)
        np.testing.assert_allclose(np.sin(w), np.sin(x), atol=1e-12)
        self.assertAlmostEqual(sc.wrap_phi(math.pi), math.pi)
        self.assertAlmostEqual(sc.wrap_phi(-math.pi), math.pi)          # -pi is outside (-pi, pi]
        self.assertAlmostEqual(sc.wrap_phi(3 * math.pi / 2), -math.pi / 2)
        self.assertAlmostEqual(sc.wrap_phi(0.3), 0.3)

    def test_features_for_jet_across_phi_boundary(self):
        # a narrow jet at phi = +-pi: without wrapping d_phi would be ~ 2 pi
        pt, eta = np.array([10.0, 5.0, 3.0]), np.array([0.0, 0.05, -0.05])
        phi = np.array([math.pi - 0.02, -math.pi + 0.03, math.pi - 0.05])
        f = sc.particle_features(pt, eta, phi)
        self.assertEqual(f.shape, (3, len(sc.FEATURE_NAMES)))
        self.assertTrue(np.all(np.abs(f[:, 1]) < 0.1))
        self.assertTrue(np.all(f[:, 4] < 0.15))
        self.assertEqual(sc.particle_features([], [], []).shape, (0, 5))

    def test_help_works_with_torch_blocked(self):
        code = ("import sys, runpy; sys.modules['torch'] = None; "
                f"sys.argv = ['set_classifier.py', '--help']; runpy.run_path({str(ASSET)!r}, run_name='__main__')")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage", r.stdout)
        self.assertIn("--model", r.stdout)

    def test_training_without_torch_fails_cleanly(self):
        code = ("import sys, runpy; sys.modules['torch'] = None; "
                f"sys.argv = ['set_classifier.py', '--epochs', '1']; runpy.run_path({str(ASSET)!r}, run_name='__main__')")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PyTorch is required", r.stderr)


@unittest.skipIf(torch is None, "PyTorch not installed")
class SetModels(unittest.TestCase):
    def models(self):
        torch.manual_seed(0)
        return {"pfn": sc.build_model("pfn", 5).eval(), "pfn-mean": sc.build_model("pfn", 5, pool="mean").eval(),
                "part": sc.build_model("part", 5, depth=2).eval()}

    def batch(self, b=6, n=20, seed=0):
        g = torch.Generator().manual_seed(seed)
        x = torch.randn(b, n, 5, generator=g)
        mask = torch.rand(b, n, generator=g) > 0.3
        mask[0] = False                                   # one empty set in the batch
        return x, mask

    def test_permutation_invariance(self):
        x, mask = self.batch()
        perm = torch.randperm(x.shape[1], generator=torch.Generator().manual_seed(1))
        for name, model in self.models().items():
            with torch.no_grad():
                a, b = model(x, mask), model(x[:, perm], mask[:, perm])
            self.assertTrue(torch.allclose(a, b, atol=1e-5), name)

    def test_padding_invariance(self):
        x, mask = self.batch()
        pad = 1e3 * torch.randn(x.shape[0], 7, 5)                # garbage values in the padded slots
        x2 = torch.cat([x, pad], dim=1)
        m2 = torch.cat([mask, torch.zeros(x.shape[0], 7, dtype=torch.bool)], dim=1)
        x3 = x.masked_fill(~mask.unsqueeze(-1), float("nan"))   # even NaN in padded slots must not leak
        for name, model in self.models().items():
            with torch.no_grad():
                a, b, c = model(x, mask), model(x2, m2), model(x3, mask)
            self.assertTrue(torch.allclose(a, b, atol=1e-5), name)
            self.assertTrue(torch.allclose(a, c, atol=1e-5), name)

    def test_empty_set_is_finite_with_gradients(self):
        x, mask = torch.randn(3, 4, 5), torch.zeros(3, 4, dtype=torch.bool)
        for name, model in self.models().items():
            model.train()
            out = model(x, mask)
            self.assertTrue(torch.isfinite(out).all(), name)
            out.sum().backward()
            for p in model.parameters():
                if p.grad is not None:
                    self.assertTrue(torch.isfinite(p.grad).all(), name)

    def test_collate_shapes_and_mask(self):
        sets = [np.ones((3, 5)), np.zeros((0, 5)), 2 * np.ones((5, 5)), np.ones((1, 5))]
        x, mask = sc.collate_sets(sets)
        self.assertEqual(tuple(x.shape), (4, 5, 5))
        self.assertEqual(mask.sum(1).tolist(), [3, 0, 5, 1])
        self.assertTrue(torch.equal(mask[0], torch.tensor([True, True, True, False, False])))
        self.assertEqual(float(x[~mask].abs().sum()), 0.0)
        self.assertEqual(float(x[2].sum()), 50.0)
        x, mask = sc.collate_sets(sets, max_len=2)
        self.assertEqual(tuple(x.shape), (4, 2, 5))
        self.assertEqual(mask.sum(1).tolist(), [2, 0, 2, 1])
        x, mask = sc.collate_sets([np.zeros((0, 5))] * 2)
        self.assertEqual(tuple(x.shape), (2, 1, 5))
        self.assertFalse(mask.any())
        with self.assertRaises(ValueError):
            sc.collate_sets([np.ones((2, 5)), np.ones((2, 4))])

    def test_short_training_beats_auc_threshold(self):
        for kind in ("pfn", "part"):
            metrics, _ = sc.train(kind, epochs=2, n_train=1500, n_val=1000, seed=0, log=lambda s: None)
            self.assertGreater(metrics["val_auc_weighted"], 0.6, kind)
            self.assertGreater(metrics["negative_weight_fraction_train"], 0.0)

    def test_cli_writes_checkpoint_and_strict_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ASSET), "--epochs", "1", "--n-train", "600", "--n-val", "400",
                                "--output-dir", d], capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stderr)
            metrics = json.loads((Path(d) / "metrics.json").read_text(),
                                 parse_constant=lambda c: self.fail(f"non-strict JSON {c}"))
            self.assertIn("val_auc_weighted", metrics)
            ckpt = torch.load(Path(d) / "set_classifier.pt", weights_only=True)
            model = sc.build_model(ckpt["model"], ckpt["n_feat"])
            model.load_state_dict(ckpt["state_dict"])


if __name__ == "__main__":
    unittest.main()

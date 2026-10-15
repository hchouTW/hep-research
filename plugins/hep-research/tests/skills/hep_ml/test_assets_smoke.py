"""CPU smoke tests for the runnable templates in assets/.

Run from the plugin root with python3 -m unittest discover -s tests -t . -v.
Every test skips when PyTorch (or, for vision_transfer, torchvision) is missing.
Each asset is exercised on tiny synthetic data in a temporary directory; the DDP
skeleton runs as 2 gloo processes through torchrun.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-ml"
ASSETS = ROOT / "assets"
sys.path.insert(0, str(ASSETS))

TORCH = importlib.util.find_spec("torch") is not None
TORCHVISION = TORCH and importlib.util.find_spec("torchvision") is not None
# torchrun installed next to the interpreter running the tests (a venv not on PATH), else from PATH
TORCHRUN = shutil.which("torchrun", path=str(Path(sys.executable).parent)) or shutil.which("torchrun")


def run(args: list[str], cwd: Path, timeout: int = 180, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class AssetSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_train_classifier_then_inference(self):
        # synthetic grouped data; the split gate, weights, run summary and domain checks are in test_training_pipeline
        result = run(
            [sys.executable, str(ASSETS / "train_classifier.py"), "--device", "cpu",
             "--train-size", "200", "--val-size", "50", "--test-size", "50", "--epochs", "1", "--num-workers", "0",
             "--output-dir", str(self.dir / "out")],
            self.dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        best = self.dir / "out" / "best.pt"
        self.assertTrue(best.exists())
        self.assertTrue((self.dir / "out" / "run_summary.json").exists())

        features = ",".join(f"x{i:02d}" for i in range(32))
        (self.dir / "in.csv").write_text(f"id,{features}\nr0,{','.join(['0.1'] * 32)}\n")
        result = run(
            [sys.executable, str(ASSETS / "inference.py"), str(best), "--input", str(self.dir / "in.csv")],
            self.dir,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"n_rows": 1', result.stdout)

    def test_transformer_classifier_forward_backward(self):
        result = run([sys.executable, str(ASSETS / "transformer_classifier.py")], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("smoke test: OK", result.stdout)

    def test_lora_trains_only_adapters(self):
        result = run([sys.executable, str(ASSETS / "lora_finetune.py")], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("trainable params:", result.stdout)

    def test_models_and_metrics_shapes(self):
        import torch
        from metrics import multiclass_accuracy, regression_rmse
        from models import MLPClassifier, SmallCNN

        self.assertEqual(MLPClassifier(8, 16, 3)(torch.randn(5, 8)).shape, (5, 3))
        self.assertEqual(SmallCNN(3, 10)(torch.randn(2, 3, 32, 32)).shape, (2, 10))
        logits = torch.tensor([[2.0, 0.0], [0.0, 2.0]])
        self.assertEqual(multiclass_accuracy(logits, torch.tensor([0, 0])), 0.5)
        self.assertAlmostEqual(regression_rmse(torch.zeros(4), torch.ones(4)), 1.0)
        with self.assertRaises(ValueError):  # [B, 1] vs [B] used to broadcast to [B, B] silently
            regression_rmse(torch.zeros(4, 1), torch.ones(4))
        with self.assertRaises(ValueError):
            multiclass_accuracy(torch.zeros(3), torch.zeros(3, dtype=torch.long))

    def test_dataset_template_length_check(self):
        import torch
        from dataset_template import CustomTensorDataset

        torch.save(torch.randn(4, 2), self.dir / "x.pt")
        torch.save(torch.zeros(3), self.dir / "y.pt")
        with self.assertRaises(ValueError):
            CustomTensorDataset(self.dir / "x.pt", self.dir / "y.pt")
        torch.save(torch.zeros(4), self.dir / "y.pt")
        self.assertEqual(len(CustomTensorDataset(self.dir / "x.pt", self.dir / "y.pt")), 4)

    @unittest.skipUnless(TORCHRUN, "torchrun not found next to the interpreter or on PATH")
    def test_ddp_skeleton_two_gloo_processes(self):
        # single node on loopback: the default rendezvous advertises the host name, which may not resolve (E2).
        # GPUs hidden: the skeleton switches to NCCL whenever CUDA is available, and with one visible GPU rank 1
        # fails at set_device(1) ("invalid device ordinal", TORCH-GPU-RUN); NCCL is test_gpu_real's job.
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
        result = run([TORCHRUN, "--standalone", "--local-addr=127.0.0.1", "--nproc_per_node=2", str(ASSETS / "ddp_train_skeleton.py")],
                     self.dir, timeout=300, env=env)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("epoch=5", result.stdout)
        self.assertTrue((self.dir / "ddp_model.pt").exists())

    @unittest.skipUnless(TORCHVISION, "torchvision not installed")
    def test_vision_transfer_help(self):
        # Full training needs an ImageFolder tree and pretrained-weight downloads.
        result = run([sys.executable, str(ASSETS / "vision_transfer.py"), "--help"], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(TORCHVISION, "torchvision not installed")
    def test_vision_transfer_trains_on_synthetic_image_folder(self):
        # SYNTHETIC random 32x32 images in an ImageFolder tree. The pretrained ResNet-18 weights are a download
        # (not exercised here), so the run builds the same architecture with weights=None.
        from PIL import Image
        import numpy as np

        rng = np.random.default_rng(7)
        for split, count in (("train", 4), ("val", 2)):
            for label in ("synthetic_a", "synthetic_b"):
                folder = self.dir / "data" / split / label
                folder.mkdir(parents=True)
                for i in range(count):
                    pixels = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
                    Image.fromarray(pixels).save(folder / f"synthetic_{i}.png")
        driver = (
            "import sys, runpy\n"
            "from torchvision import models\n"
            "original = models.resnet18\n"
            "models.resnet18 = lambda weights=None, **kw: original(weights=None, **kw)\n"
            f"sys.argv = ['vision_transfer.py', 'data', '--epochs', '1', '--batch-size', '4', '--num-workers', '0',"
            f" '--freeze-backbone', '--output', 'best.pt']\n"
            f"runpy.run_path({str(ASSETS / 'vision_transfer.py')!r}, run_name='__main__')\n"
        )
        result = run([sys.executable, "-c", driver], self.dir, timeout=600)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("epoch=001", result.stdout)
        saved = torch_load(self.dir / "best.pt")
        self.assertEqual(saved["classes"], ["synthetic_a", "synthetic_b"])
        self.assertEqual(tuple(saved["model_state_dict"]["fc.weight"].shape), (2, 512))


def torch_load(path: Path):
    import torch

    return torch.load(path, map_location="cpu", weights_only=False)


if __name__ == "__main__":
    unittest.main()

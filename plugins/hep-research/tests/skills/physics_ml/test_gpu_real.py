"""GPU tests for the physics-ml assets: a real GPU, never a fake.

Opt-in: HEP_TORCH_GPU_TEST=1 and torch.cuda.is_available(); otherwise every test skips. Setting the variable on a GPU
host (for example inside a Slurm GPU job) is the approval to use it. The NCCL test needs two visible GPUs.
First run: NSTCCore, torch 2.14.1 (cu130 on RTX PRO 6000 Blackwell, cu126 on V100), 2026-10-11 (TORCH-GPU-RUN).
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

ASSETS = Path(__file__).resolve().parents[3] / "skills" / "physics-ml" / "assets"
TORCH = importlib.util.find_spec("torch") is not None
ENABLED = os.environ.get("HEP_TORCH_GPU_TEST") == "1"
CUDA = False
if TORCH and ENABLED:
    import torch

    CUDA = torch.cuda.is_available()
TORCHRUN = shutil.which("torchrun", path=str(Path(sys.executable).parent)) or shutil.which("torchrun")


def run(args: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def final_val_loss(stdout: str) -> float:
    last = [line for line in stdout.splitlines() if "val_loss=" in line][-1]
    return float(last.split("val_loss=")[1].split()[0])


@unittest.skipUnless(TORCH and ENABLED and CUDA, "GPU tests need HEP_TORCH_GPU_TEST=1, PyTorch and an available CUDA device")
class GpuAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def train(self, device: str, amp: bool) -> subprocess.CompletedProcess:
        out = self.dir / f"out-{device}{'-amp' if amp else ''}"
        args = [sys.executable, str(ASSETS / "train_classifier.py"), "--seed", "42", "--device", device,
                "--train-size", "2000", "--val-size", "500", "--epochs", "3", "--num-workers", "0",
                "--output-dir", str(out)] + (["--use-amp"] if amp else [])
        result = run(args, self.dir)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertTrue((out / "best.pt").exists())
        return result

    def test_cuda_training_with_and_without_amp_matches_cpu(self):
        # Same seed on CPU and CUDA: not bitwise (kernels and device random streams differ); final validation loss
        # within 5 % relative, the tolerance fixed in TORCH-GPU-RUN before comparing.
        cpu = final_val_loss(self.train("cpu", amp=False).stdout)
        for amp in (False, True):
            with self.subTest(amp=amp):
                gpu = final_val_loss(self.train("cuda", amp=amp).stdout)
                self.assertLess(abs(gpu - cpu) / cpu, 0.05, f"cpu {cpu} cuda {gpu}")

    def test_inference_runs_on_a_cuda_checkpoint(self):
        self.train("cuda", amp=False)
        result = run([sys.executable, str(ASSETS / "inference.py"), str(self.dir / "out-cuda" / "best.pt"),
                      "--input-dim", "32", "--num-classes", "4"], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("prediction:", result.stdout)

    def test_transformer_forward_backward_on_cuda_with_fp16_autocast(self):
        sys.path.insert(0, str(ASSETS))
        from transformer_classifier import TransformerClassifier, create_dummy_batch

        torch.manual_seed(0)
        ids, mask = create_dummy_batch()
        labels = torch.randint(0, 5, (ids.shape[0],))
        model = TransformerClassifier(vocab_size=1000, num_classes=5).cuda()
        for amp in (False, True):
            with self.subTest(amp=amp):
                model.zero_grad()
                with torch.autocast("cuda", dtype=torch.float16, enabled=amp):
                    loss = torch.nn.functional.cross_entropy(model(ids.cuda(), mask.cuda()), labels.cuda())
                loss.backward()
                self.assertTrue(torch.isfinite(loss).item())
                self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))

    @unittest.skipUnless(TORCHRUN, "torchrun not found next to the interpreter or on PATH")
    def test_ddp_skeleton_over_nccl_on_two_gpus(self):
        if torch.cuda.device_count() < 2:
            self.skipTest("NCCL DDP needs two visible GPUs")
        env = dict(os.environ, NCCL_DEBUG="INFO")  # local ranks 0 and 1 use the first two visible GPUs
        result = subprocess.run([TORCHRUN, "--standalone", "--local-addr=127.0.0.1", "--nproc_per_node=2",
                                 str(ASSETS / "ddp_train_skeleton.py")], cwd=self.dir, capture_output=True, text=True,
                                timeout=600, env=env)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("epoch=5", result.stdout)
        self.assertIn("NCCL INFO", result.stdout + result.stderr)  # the backend really was NCCL
        self.assertTrue((self.dir / "ddp_model.pt").exists())


if __name__ == "__main__":
    unittest.main()

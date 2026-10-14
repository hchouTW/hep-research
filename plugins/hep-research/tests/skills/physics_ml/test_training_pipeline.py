"""Tests for the physics-ml training pipeline assets: split gate, run summary, weights, inference domain checks.

Run from the plugin root with python3 -m unittest discover -s tests -t . -v.
Torch-dependent tests skip without PyTorch; the --help tests run under a Python where `import torch` is blocked.
All data are SYNTHETIC: small grouped CSVs written into a temporary directory.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "physics-ml"
ASSETS = ROOT / "assets"
TORCH = importlib.util.find_spec("torch") is not None
TORCHVISION = TORCH and importlib.util.find_spec("torchvision") is not None
YAML = importlib.util.find_spec("yaml") is not None

SUMMARY_KEYS = {"task", "features", "units", "labels", "grouping_key", "split_manifest", "split_check",
                "training_domain", "preprocessing", "weights", "model_hash", "checkpoint", "environment", "metrics",
                "scores"}
FEATURES = ["pt", "eta", "mass", "iso"]


def run(args, cwd, timeout=300):
    return subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def write_events(directory: Path, n_groups=72, group_size=5, negative_every=0, seed=3):
    """SYNTHETIC grouped events: features shift with the label and with a per-group offset."""
    import random

    rng = random.Random(seed)
    rows, groups = [], {}
    for g in range(n_groups):
        offset = rng.gauss(0, 0.3)
        for k in range(group_size):
            i = g * group_size + k
            label = rng.random() < 0.5
            weight = abs(rng.gauss(1.0, 0.2))
            if negative_every and i % negative_every == 0:
                weight = -weight
            rows.append({"id": f"e{i}", "pt": 40 + 15 * label + 8 * rng.gauss(0, 1) + 5 * offset,
                         "eta": rng.gauss(0, 1.2), "mass": 90 + 20 * label + 10 * rng.gauss(0, 1),
                         "iso": abs(rng.gauss(0.1 - 0.05 * label, 0.05)) + offset * 0.01,
                         "label": int(label), "weight": weight})
            groups[f"e{i}"] = f"run{g}"
    path = directory / "events.csv"
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path, rows, groups


def write_manifest(directory: Path, rows, groups, leak=False, name="splits.json"):
    """Whole groups per split (2/3 train, 1/6 val, 1/6 test); leak=True moves one train event into test."""
    group_ids = sorted({g for g in groups.values()}, key=lambda s: int(s[3:]))
    n = len(group_ids)
    split_of = {g: ("train" if i < 2 * n // 3 else "val" if i < 5 * n // 6 else "test") for i, g in enumerate(group_ids)}
    manifest = {"train": [], "val": [], "test": [], "groups": groups}
    for row in rows:
        manifest[split_of[groups[row["id"]]]].append(row["id"])
    if leak:
        moved = manifest["train"].pop(0)
        manifest["test"].append(moved)
    path = directory / name
    path.write_text(json.dumps(manifest))
    return path, manifest


def train_cmd(data, manifest, out, *extra):
    return [sys.executable, ASSETS / "train_classifier.py", "--device", "cpu", "--data", data,
            "--split-manifest", manifest, "--weight-col", "weight", "--epochs", "3", "--num-workers", "0",
            "--batch-size", "32", "--hidden-dim", "16", "--output-dir", out, *extra]


@unittest.skipUnless(TORCH, "PyTorch not installed")
class TrainClassifierPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.data, cls.rows, cls.groups = write_events(cls.dir)
        cls.manifest_path, cls.manifest = write_manifest(cls.dir, cls.rows, cls.groups)
        units = cls.dir / "units.json"
        units.write_text(json.dumps({"pt": "GeV", "eta": "", "mass": "GeV", "iso": ""}))
        cls.out = cls.dir / "clean"
        cls.result = run(train_cmd(cls.data, cls.manifest_path, cls.out, "--units", units,
                                   "--grouping-key", "run"), cls.dir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def summary(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        return json.loads((self.out / "run_summary.json").read_text())

    def test_leaky_manifest_refused_before_training(self):
        leaky, _ = write_manifest(self.dir, self.rows, self.groups, leak=True, name="leaky.json")
        out = self.dir / "leaky-out"
        result = run(train_cmd(self.data, leaky, out), self.dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to train", result.stderr)
        self.assertFalse((out / "best.pt").exists())
        self.assertFalse((out / "run_summary.json").exists())
        report = json.loads((out / "split_check.json").read_text())
        self.assertEqual(report["status"], "failed")

    def test_leaky_manifest_with_override_records_fail(self):
        leaky, _ = write_manifest(self.dir, self.rows, self.groups, leak=True, name="leaky2.json")
        out = self.dir / "override-out"
        result = run(train_cmd(self.data, leaky, out, "--allow-unchecked-split", "--epochs", "1"), self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchecked split", result.stderr)
        summary = json.loads((out / "run_summary.json").read_text())
        self.assertEqual(summary["split_check"]["result"], "fail")

    def test_data_without_manifest_is_refused(self):
        result = run([sys.executable, ASSETS / "train_classifier.py", "--device", "cpu", "--data", self.data,
                      "--output-dir", self.dir / "nomanifest"], self.dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--split-manifest", result.stderr)

    def test_clean_manifest_summary_shape_and_hash(self):
        summary = self.summary()
        self.assertEqual(set(summary), SUMMARY_KEYS)
        self.assertEqual(summary["task"], "classification")
        self.assertEqual(summary["features"], FEATURES)
        self.assertEqual(summary["units"]["pt"], "GeV")
        self.assertEqual(summary["labels"], ["background", "signal"])
        self.assertEqual(summary["grouping_key"], "run")
        self.assertEqual(summary["split_check"], {"tool": "check_split_integrity.py", "result": "pass",
                                                  "report": summary["split_check"]["report"]})
        self.assertTrue(Path(summary["split_check"]["report"]).exists())
        self.assertEqual(set(summary["training_domain"]), set(FEATURES))
        for lo, hi in summary["training_domain"].values():
            self.assertLessEqual(lo, hi)
        (step,) = summary["preprocessing"]
        self.assertEqual(step["step"], "standardize")
        self.assertEqual(len(step["mean"]), 4)
        self.assertEqual(set(summary["weights"]), {"source", "negative_weight_treatment", "class_balancing", "used_in",
                                                   "training", "evaluation"})
        self.assertEqual(summary["weights"]["negative_weight_treatment"], "none-present")
        self.assertEqual(summary["weights"]["source"], "column:weight")
        self.assertTrue(set(summary["weights"]["used_in"]) <= {"loss", "metrics", "calibration", "templates"})
        self.assertEqual(set(summary["environment"]), {"torch_version", "device", "precision", "seeds"})
        self.assertEqual(summary["environment"]["precision"], "fp32")
        self.assertEqual(set(summary["environment"]["seeds"]), {"torch", "numpy", "python"})
        self.assertEqual(set(summary["metrics"]), {"val", "test"})
        digest = hashlib.sha256(Path(summary["checkpoint"]).read_bytes()).hexdigest()
        self.assertEqual(summary["model_hash"], f"sha256:{digest}")

    def test_test_metrics_use_only_the_test_split(self):
        summary = self.summary()
        with open(summary["scores"]["test"], newline="") as handle:
            scored = list(csv.DictReader(handle))
        ids = [row["id"] for row in scored]
        self.assertEqual(sorted(ids), sorted(self.manifest["test"]))
        self.assertFalse(set(ids) & set(self.manifest["val"]))
        self.assertFalse(set(ids) & set(self.manifest["train"]))
        self.assertEqual(summary["metrics"]["test"]["n_events"], len(self.manifest["test"]))
        self.assertEqual(summary["metrics"]["val"]["n_events"], len(self.manifest["val"]))
        # working-point thresholds are fixed on validation and reused on test
        for val_wp, test_wp in zip(summary["metrics"]["val"]["working_points"],
                                   summary["metrics"]["test"]["working_points"]):
            if "threshold" in val_wp:
                self.assertEqual(test_wp["threshold"], val_wp["threshold"])
                self.assertEqual(test_wp["threshold_from"], "val")

    def test_checkpoints_load_weights_only_and_last_records_best(self):
        import torch

        self.summary()
        log = json.loads((self.out / "training_log.json").read_text())
        val_losses = [e["val_loss_weighted"] for e in log["epochs"]]
        last = torch.load(self.out / "last.pt", map_location="cpu", weights_only=True)
        best = torch.load(self.out / "best.pt", map_location="cpu", weights_only=True)
        self.assertAlmostEqual(last["best_metric"], min(val_losses))
        self.assertEqual(last["best_epoch"], val_losses.index(min(val_losses)))
        self.assertAlmostEqual(best["best_metric"], min(val_losses))
        meta = best["metadata"]
        self.assertEqual(meta["features"], FEATURES)
        self.assertEqual(meta["units"]["mass"], "GeV")
        # the shared domain model (PML-WP0.7), fitted on train with thresholds from held-out training rows
        self.assertEqual(meta["training_domain"]["fit_on"], "train")
        self.assertGreater(meta["training_domain"]["model"]["thresholds"]["mahalanobis"], 0)
        self.assertEqual(set(meta["weights"]), {"training", "evaluation"})

    def test_negative_weights_signed_with_net_weight_batch_report(self):
        data_dir = self.dir / "neg"
        data_dir.mkdir()
        data, rows, groups = write_events(data_dir, negative_every=3)
        manifest, _ = write_manifest(data_dir, rows, groups)
        out = data_dir / "out"
        result = run(train_cmd(data, manifest, out, "--batch-size", "4", "--epochs", "1"), data_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((out / "run_summary.json").read_text())
        self.assertEqual(summary["weights"]["negative_weight_treatment"], "signed")
        log = json.loads((out / "training_log.json").read_text())
        self.assertGreater(log["nonpositive_net_weight_batches"], 0)
        self.assertIn("non-positive net weight", result.stderr)
        self.assertTrue(math.isfinite(summary["metrics"]["test"]["loss_weighted"]))
        best = __import__("torch").load(out / "best.pt", map_location="cpu", weights_only=True)
        self.assertGreater(best["metadata"]["weights"]["training"]["n_negative"], 0)
        self.assertEqual(best["metadata"]["weights"]["evaluation"]["treatment"], "signed, unmodified")

        dropped = data_dir / "dropped"
        result = run(train_cmd(data, manifest, dropped, "--epochs", "1", "--negative-weights", "dropped"), data_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((dropped / "run_summary.json").read_text())
        self.assertEqual(summary["weights"]["negative_weight_treatment"], "dropped")

    def inference(self, csv_rows, *extra, header=None):
        path = self.dir / f"infer-{len(list(self.dir.iterdir()))}.csv"
        header = header or ["id", *FEATURES]
        with open(path, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(csv_rows)
        return run([sys.executable, ASSETS / "inference.py", self.out / "best.pt", "--input", path, *extra], self.dir)

    def test_inference_flags_and_rejects_out_of_domain(self):
        self.summary()
        inside = ["in", 50.0, 0.1, 100.0, 0.08]
        outside = ["out", 5000.0, 0.1, 100.0, 0.08]
        flagged = self.inference([inside, outside])
        self.assertEqual(flagged.returncode, 0, flagged.stderr)
        report = json.loads(flagged.stdout)
        self.assertEqual(report["n_out_of_domain"], 1)
        by_id = {row["id"]: row for row in report["rows"]}
        self.assertEqual(by_id["in"]["out_of_domain"], 0)
        self.assertEqual(by_id["out"]["out_of_domain"], 1)
        self.assertIn("outside:", by_id["out"]["ood_reasons"])
        self.assertTrue(0.0 <= by_id["in"]["score"] <= 1.0)
        rejected = self.inference([inside, outside], "--on-out-of-domain", "reject")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("outside the training domain", rejected.stderr)
        clean = self.inference([inside], "--on-out-of-domain", "reject")
        self.assertEqual(clean.returncode, 0, clean.stderr)

    def test_inference_mahalanobis_catches_in_range_combination(self):
        # each feature inside its training range, but pt high and mass low together (anti-correlated with the label)
        summary = self.summary()
        dom = summary["training_domain"]
        corner = ["corner", dom["pt"][1] * 0.999, dom["eta"][0] * 0.999, dom["mass"][0] * 1.001, dom["iso"][1] * 0.999]
        report = json.loads(self.inference([corner]).stdout)
        self.assertEqual(report["n_out_of_domain"], 1)
        self.assertEqual(report["n_mahalanobis"], 1)

    def test_inference_refuses_feature_name_mismatch(self):
        self.summary()
        result = self.inference([["a", 50.0, 0.1, 100.0, 0.08]], header=["id", "pt", "eta", "m", "iso"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("mass", result.stderr)
        self.assertIn("missing", result.stderr)

    def test_inference_loads_weights_only_unless_opted_in(self):
        import torch

        self.summary()
        ckpt = torch.load(self.out / "best.pt", map_location="cpu", weights_only=True)
        ckpt["probe"] = _UnpickleProbe()
        probe = self.dir / "probe.pt"
        torch.save(ckpt, probe)
        rows = self.dir / "probe-in.csv"
        rows.write_text("id,pt,eta,mass,iso\na,50,0.1,100,0.08\n")
        cmd = [sys.executable, ASSETS / "inference.py", probe, "--input", rows]
        safe = run(cmd, self.dir)
        self.assertNotEqual(safe.returncode, 0)
        self.assertNotIn("UNPICKLE-EXECUTED", safe.stdout)
        self.assertIn("--unsafe-full-unpickle", safe.stderr)
        unsafe = run(cmd + ["--unsafe-full-unpickle"], self.dir)
        self.assertEqual(unsafe.returncode, 0, unsafe.stderr)
        self.assertIn("UNPICKLE-EXECUTED", unsafe.stdout)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class TrainClassifierSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_synthetic_split_is_grouped_and_checked(self):
        out = self.dir / "out"
        result = run([sys.executable, ASSETS / "train_classifier.py", "--device", "cpu", "--train-size", "200",
                      "--val-size", "60", "--test-size", "60", "--epochs", "1", "--num-workers", "0",
                      "--output-dir", out], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "split_manifest.json").read_text())
        placement = {}
        for split in ("train", "val", "test"):
            for value in manifest[split]:
                placement.setdefault(manifest["groups"][value], set()).add(split)
        self.assertTrue(all(len(s) == 1 for s in placement.values()))
        summary = json.loads((out / "run_summary.json").read_text())
        self.assertEqual(set(summary), SUMMARY_KEYS | {"status"})
        self.assertEqual(summary["status"], ["synthetic"])  # the writer keeps it without --status (PML-WP0.4)
        self.assertEqual(summary["split_check"]["result"], "pass")
        self.assertEqual(summary["grouping_key"], "synthetic_group")

    @unittest.skipUnless(YAML, "PyYAML not installed (--config needs it)")
    def test_config_file_with_cli_override(self):
        sys.path.insert(0, str(ASSETS))
        try:
            import train_classifier
        finally:
            sys.path.remove(str(ASSETS))
        args = train_classifier.parse_args(["--config", str(ASSETS / "config.yaml"), "--epochs", "2"])
        self.assertEqual(args.epochs, 2)              # CLI wins
        self.assertEqual(args.lr, 0.001)              # learning_rate from the file
        self.assertEqual(args.precision, "fp32")
        self.assertEqual(args.output_dir, "runs/example")
        bad = self.dir / "bad.yaml"
        bad.write_text("training:\n  use_amp: true\n")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            train_classifier.parse_args(["--config", str(bad)])

    def test_fp16_on_cpu_is_refused(self):
        result = run([sys.executable, ASSETS / "train_classifier.py", "--device", "cpu", "--precision", "fp16",
                      "--output-dir", self.dir / "o"], self.dir)
        self.assertEqual(result.returncode, 2)
        self.assertIn("CUDA", result.stderr)

    def test_bf16_multiclass_runs_on_cpu(self):
        out = self.dir / "bf16"
        result = run([sys.executable, ASSETS / "train_classifier.py", "--device", "cpu", "--precision", "bf16",
                      "--num-classes", "3", "--train-size", "150", "--val-size", "60", "--test-size", "60",
                      "--epochs", "1", "--num-workers", "0", "--output-dir", out], self.dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((out / "run_summary.json").read_text())
        self.assertEqual(summary["environment"]["precision"], "bf16")
        self.assertEqual(len(summary["metrics"]["test"]["auc_weighted_one_vs_rest"]), 3)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class AssetFixTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ASSETS))
        self.addCleanup(sys.path.remove, str(ASSETS))

    def test_regression_metrics_refuse_shape_mismatch(self):
        import torch
        from metrics import regression_mae, regression_rmse

        for fn in (regression_mae, regression_rmse):
            with self.assertRaises(ValueError):
                fn(torch.zeros(4, 1), torch.zeros(4))
        self.assertAlmostEqual(regression_mae(torch.zeros(4, 1), torch.ones(4, 1)), 1.0)

    def test_transformer_fully_masked_row_is_finite(self):
        import torch
        from transformer_classifier import TransformerClassifier

        torch.manual_seed(0)
        model = TransformerClassifier(vocab_size=50, num_classes=3, embed_dim=16, num_heads=2, ff_dim=32, num_layers=2)
        ids = torch.randint(1, 50, (3, 6))
        mask = torch.ones(3, 6, dtype=torch.bool)
        mask[1] = False             # an empty sequence
        mask[2, 3:] = False
        logits = model(ids * mask, mask)
        self.assertTrue(torch.isfinite(logits).all())
        logits.sum().backward()
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))

    @unittest.skipUnless(TORCHVISION, "torchvision not installed")
    def test_vision_transfer_frozen_backbone_keeps_batchnorm_in_eval(self):
        import torch
        import vision_transfer

        original = vision_transfer.models.resnet18
        vision_transfer.models.resnet18 = lambda weights=None, **kw: original(weights=None, **kw)
        self.addCleanup(setattr, vision_transfer.models, "resnet18", original)
        model = vision_transfer.build_model(2, freeze_backbone=True)
        before = model.bn1.running_mean.clone()
        optimizer = torch.optim.SGD([p for p in model.parameters() if p.requires_grad], lr=0.1)
        loader = [(torch.randn(2, 3, 32, 32) * 5 + 3, torch.tensor([0, 1]))]
        vision_transfer.run_epoch(model, loader, torch.nn.CrossEntropyLoss(), torch.device("cpu"), optimizer)
        bns = [m for m in model.modules() if isinstance(m, torch.nn.BatchNorm2d)]
        self.assertTrue(bns)
        self.assertFalse(any(m.training for m in bns))
        self.assertTrue(model.fc.training)
        self.assertTrue(torch.equal(before, model.bn1.running_mean))

    def test_dataset_template_loads_weights_only(self):
        import torch
        from dataset_template import CustomTensorDataset

        with tempfile.TemporaryDirectory() as tmp:
            x, y = Path(tmp) / "x.pt", Path(tmp) / "y.pt"
            torch.save({"probe": _UnpickleProbe()}, x)
            torch.save(torch.zeros(1), y)
            with self.assertRaises(Exception):
                CustomTensorDataset(x, y)


# Blocks torch/torchvision imports, then runs an asset as __main__ with the given argv.
NO_TORCH_DRIVER = """
import importlib.abc, runpy, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in ('torch', 'torchvision'):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None
sys.meta_path.insert(0, Block())
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
"""

CLI_ASSETS = ["train_classifier.py", "inference.py", "vision_transfer.py", "transformer_classifier.py",
              "lora_finetune.py", "ddp_train_skeleton.py"]


class HelpWithoutTorchTests(unittest.TestCase):
    def test_help_works_without_torch(self):
        for name in CLI_ASSETS:
            with self.subTest(asset=name):
                result = run([sys.executable, "-c", NO_TORCH_DRIVER, ASSETS / name, "--help"], ASSETS)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_run_without_torch_exits_3_with_message(self):
        argv = {"inference.py": ["ckpt.pt", "--input", "x.csv"], "vision_transfer.py": ["data"]}
        for name in CLI_ASSETS:
            with self.subTest(asset=name):
                result = run([sys.executable, "-c", NO_TORCH_DRIVER, ASSETS / name, *argv.get(name, [])], ASSETS)
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertIn("not available", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


class _UnpickleProbe:
    """Pickles to a call of print(); a full unpickle executes it, weights_only=True refuses it."""

    def __reduce__(self):
        return (print, ("UNPICKLE-EXECUTED",))


if __name__ == "__main__":
    unittest.main()

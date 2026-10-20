"""hep-ml audit (PML-WP0.3: ML-C16, ML-C14, Q7): the trainer matches manifest IDs the way the split tools wrote
them, and a split without a class is an input error, not a traceback.

make_grouped_splits.py writes case-folded IDs; before the fix train_classifier.py matched them against the raw CSV
IDs, so "Ev1" in the data and "ev1" in the manifest were "not in the data" (exit 2). The asset keeps its own copy of
the key function (assets are copied out standalone, decision Q7); the agreement test pins it to the scripts' copy.
"""
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills" / "hep-ml" / "assets"
SCRIPTS = ROOT / "skills" / "hep-ml" / "scripts"
TORCH = importlib.util.find_spec("torch") is not None
sys.path.insert(0, str(SCRIPTS))
from check_split_integrity import canonical_key  # noqa: E402

KEYS = [1, 1.0, "1", " 1 ", "1.0", "1.", 1.5, "007", "007.0", "+5", "+5.0", "Run7", " RUN7", "ev_A", 0, -3.0, "-3",
        "x.0", "1e3"]


def load_trainer():
    spec = importlib.util.spec_from_file_location("train_classifier_under_test", ASSETS / "train_classifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(TORCH, "PyTorch not installed")
class KeyAgreementTests(unittest.TestCase):
    def test_asset_copy_matches_the_split_tools(self):
        trainer = load_trainer()
        for case_sensitive in (False, True):
            for key in KEYS:
                with self.subTest(key=key, case_sensitive=case_sensitive):
                    self.assertEqual(trainer.canonical_key(key, case_sensitive), canonical_key(key, case_sensitive))
        for bad in (True, [1], {"a": 1}):
            with self.assertRaises(ValueError):
                trainer.canonical_key(bad)


def write(directory, ids, labels):
    data = directory / "events.csv"
    with open(data, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "pt", "eta", "label"])
        for i, (rid, lab) in enumerate(zip(ids, labels)):
            w.writerow([rid, 40 + 10 * lab + (i % 7), (i % 5) * 0.3 - 0.6, lab])
    return data


def train(directory, data, manifest):
    return subprocess.run([sys.executable, str(ASSETS / "train_classifier.py"), "--device", "cpu", "--data", data,
                           "--split-manifest", manifest, "--epochs", "1", "--num-workers", "0", "--batch-size", "16",
                           "--hidden-dim", "8", "--output-dir", directory / "out"],
                          capture_output=True, text=True, timeout=600)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class TrainerSplitTests(unittest.TestCase):
    def test_mixed_case_ids_train_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            ids = [f"Ev{i}" for i in range(60)]
            data = write(d, ids, [i % 2 for i in range(60)])
            rows = [{"id": rid, "run": f"Run{i // 3}"} for i, rid in enumerate(ids)]
            (d / "rows.json").write_text(json.dumps(rows))
            made = subprocess.run([sys.executable, str(SCRIPTS / "make_grouped_splits.py"), str(d / "rows.json"),
                                   "--id-column", "id", "--group-column", "run", "--seed", "1",
                                   "--out", str(d / "m.json")], capture_output=True, text=True, timeout=600)
            self.assertEqual(made.returncode, 0, made.stdout)
            self.assertIn("ev0", json.loads((d / "m.json").read_text())["groups"])  # the manifest is case-folded
            res = train(d, data, d / "m.json")
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_split_without_a_class_is_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            ids = [f"e{i}" for i in range(30)]
            labels = [i % 2 for i in range(20)] + [0] * 10  # the test split (e20..e29) has no signal
            data = write(d, ids, labels)
            manifest = {"train": ids[:15], "val": ids[15:20], "test": ids[20:],
                        "groups": {rid: f"r{i}" for i, rid in enumerate(ids)}}
            (d / "m.json").write_text(json.dumps(manifest))
            res = train(d, data, d / "m.json")
            self.assertEqual(res.returncode, 2, res.stderr)
            self.assertIn("test", res.stderr)
            self.assertIn("class", res.stderr)
            self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()

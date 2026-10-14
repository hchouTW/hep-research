"""physics-ml audit (PML-WP2.5: ML-C10, C23, C24, C25, C26): small corrections with a measurable effect.

Before the fix: compare_model_runs.py called noise an improvement 26%, 15% and 11% of the time with 3, 5 and 10 seeds
(nominal 5%, first-pass measurement); the mass-sculpting baseline was one random split; a constant training feature
was standardized with std 1e-12; the model hash covered the checkpoint file (paths, optimizer state, epoch). The
domain false-positive estimate now carries an interval (tested in test_audit_domain_method.py). All SYNTHETIC."""
import importlib.util
import random
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ML = ROOT / "skills" / "physics-ml"
sys.path.insert(0, str(ML / "scripts"))
sys.path.insert(0, str(ML / "assets"))
import compare_model_runs as cmr  # noqa: E402
import hep_metrics as hm  # noqa: E402

TORCH = importlib.util.find_spec("torch") is not None


class SmallSeedComparisonTests(unittest.TestCase):
    def test_false_improvement_rate_is_at_most_nominal_with_few_seeds(self):
        rng = random.Random(7)
        for n in (3, 5, 9):
            hits, trials = 0, 300
            for _ in range(trials):
                base = [rng.gauss(0, 1) for _ in range(n)]
                var = [b + rng.gauss(0, 0.5) for b in base]  # no true effect, paired seed noise
                hits += cmr.compare(base, var, resamples=500, seed=rng.randrange(10 ** 6))["interval_excludes_zero"]
            rate, sigma = hits / trials, (0.05 * 0.95 / trials) ** 0.5
            with self.subTest(n=n):
                self.assertLess(rate, 0.05 + 3 * sigma, rate)

    def test_method_is_reported_and_a_real_effect_is_found(self):
        base = [0.80, 0.81, 0.79, 0.80, 0.82, 0.80, 0.81]
        res = cmr.compare(base, [b + 0.05 for b in base])
        self.assertIn("Student-t", res["method"])
        self.assertLess(res["permutation_p_value"], 0.05)
        self.assertTrue(res["interval_excludes_zero"])
        big = cmr.compare([random.Random(1).gauss(0, 1) for _ in range(12)], [random.Random(2).gauss(0, 1) for _ in range(12)])
        self.assertEqual(big["method"], "bootstrap")

    def test_student_t_quantile(self):
        for df, expected in ((1, 12.7062), (4, 2.77645), (8, 2.30600)):
            self.assertAlmostEqual(cmr.student_t_quantile(0.975, df), expected, places=4)


class SculptingBaselineTests(unittest.TestCase):
    def test_baseline_is_a_quantile_of_at_least_20_resamplings(self):
        rng = np.random.default_rng(3)
        mass, score = rng.uniform(50, 150, 4000), rng.uniform(size=4000)
        res = hm.mass_sculpting_jsd(mass, score, 0.9, baseline=True)
        self.assertEqual(res["n_baseline"], 20)
        self.assertLessEqual(res["jsd_baseline"], res["jsd_baseline_q95"])
        with self.assertRaises(ValueError):
            hm.mass_sculpting_jsd(mass, score, 0.9, baseline=True, n_baseline=1)


@unittest.skipUnless(TORCH, "PyTorch not installed")
class TrainerTests(unittest.TestCase):
    def test_constant_training_feature_is_exit_2(self):
        import csv
        import json
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            ids = [f"e{i}" for i in range(60)]
            with open(d / "ev.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["id", "a", "const", "label"])
                for i, rid in enumerate(ids):
                    w.writerow([rid, i * 0.1, 3.0, i % 2])
            (d / "m.json").write_text(json.dumps({"train": ids[:40], "val": ids[40:50], "test": ids[50:],
                                                  "groups": {r: f"g{i}" for i, r in enumerate(ids)}}))
            r = subprocess.run([sys.executable, str(ML / "assets" / "train_classifier.py"), "--device", "cpu",
                                "--data", str(d / "ev.csv"), "--split-manifest", str(d / "m.json"), "--epochs", "1",
                                "--num-workers", "0", "--output-dir", str(d / "out")],
                               capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("const", r.stderr)


if __name__ == "__main__":
    unittest.main()

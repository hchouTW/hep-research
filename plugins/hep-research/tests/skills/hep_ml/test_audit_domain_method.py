"""hep-ml audit (PML-WP0.7: ML-C08, ML-C09, ML-C19, ML-C18): one training-domain method for training, inference
and surrogate checks.

Before the fix (0.9.0) train_classifier.py stored a Mahalanobis threshold computed with pinv on train+val distances
(the points the mean and covariance were fit on), so a broken linear constraint (f3 = f1 + f2) had zero distance along
the null direction and was never flagged; inference.py also flagged any row outside the per-feature min/max box, about
10% of fresh in-distribution rows at d = 32, n = 600 against a nominal 0.1%; non-finite rows were scored with 0
substituted. check_surrogate_domain.py held out points at random, so with replicated design points the held-out
replicas had twins in the fit part and the reported false-positive rate was far below the measured one; categorical
features were treated as continuous. All data SYNTHETIC.
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
ML = ROOT / "skills" / "hep-ml"
sys.path.insert(0, str(ML / "scripts"))
import check_surrogate_domain as csd  # noqa: E402

TORCH = importlib.util.find_spec("torch") is not None


def constrained(rng, n):
    f1, f2 = rng.normal(size=n), rng.normal(size=n)
    return np.c_[f1, f2, f1 + f2, rng.normal(size=n)]


class DomainModelTests(unittest.TestCase):
    def test_broken_linear_constraint_is_outside(self):
        rng = np.random.default_rng(1)
        model = csd.DomainModel.fit(constrained(rng, 800), quantile=0.99, seed=0)
        ok = constrained(rng, 1)
        bad = ok.copy()
        bad[0, 2] += 0.5  # f3 = f1 + f2 broken; every coordinate is well inside its training range
        status, _ = model.classify(np.r_[ok, bad])
        self.assertEqual(status[1], "outside")
        self.assertNotEqual(status[0], "outside")

    def test_in_distribution_flag_rate_is_nominal_at_d32_n600(self):
        rng = np.random.default_rng(2)
        model = csd.DomainModel.fit(rng.normal(size=(600, 32)), quantile=0.99, seed=0)
        fresh = rng.normal(size=(4000, 32))
        status, _ = model.classify(fresh)
        rate = np.mean([s != "inside" for s in status])
        nominal = 0.01
        sigma = np.sqrt(nominal * (1 - nominal) / len(fresh))
        # the old min/max box flagged about 10%; the calibrated thresholds stay near the nominal rate
        self.assertLess(rate, nominal + 3 * sigma + 0.02, rate)

    def test_grouped_holdout_with_replicated_design_points(self):
        rng = np.random.default_rng(3)
        design = rng.uniform(-1, 1, size=(300, 3))
        replicas = np.repeat(design, 10, axis=0) + rng.normal(scale=1e-3, size=(3000, 3))
        groups = np.repeat(np.arange(300), 10)
        fresh = rng.uniform(-1, 1, size=(3000, 3))
        model = csd.DomainModel.fit(replicas, quantile=0.95, seed=0, groups=groups)
        status, _ = model.classify(fresh)
        measured = np.mean([s != "inside" for s in status])
        reported = model.estimated_false_positive_rate
        self.assertLess(abs(measured - reported), 0.1, (measured, reported))
        ungrouped = csd.DomainModel.fit(replicas, quantile=0.95, seed=0)
        bad_status, _ = ungrouped.classify(fresh)
        # without grouping the held-out replicas have twins in the fit part: the report understates the flag rate
        self.assertGreater(np.mean([s != "inside" for s in bad_status]) - ungrouped.estimated_false_positive_rate, 0.3)

    def test_categorical_value_not_seen_in_training_is_outside(self):
        rng = np.random.default_rng(4)
        x = np.c_[rng.normal(size=500), rng.integers(0, 3, 500)]
        model = csd.DomainModel.fit(x, quantile=0.99, seed=0, categorical=[1])
        status, reasons = model.classify(np.array([[0.1, 1.0], [0.1, 0.5]]))
        self.assertNotEqual(status[0], "outside")
        self.assertEqual(status[1], "outside")
        self.assertTrue(any("categorical" in r for r in reasons[1]))

    def test_non_finite_row_is_outside_not_scored(self):
        rng = np.random.default_rng(5)
        model = csd.DomainModel.fit(rng.normal(size=(300, 2)), seed=0)
        status, reasons = model.classify(np.array([[0.0, 0.0], [np.nan, 0.0]]))
        self.assertEqual(status[1], "outside")
        self.assertIn("non-finite", reasons[1])

    def test_round_trip_through_a_plain_dict(self):
        rng = np.random.default_rng(6)
        model = csd.DomainModel.fit(constrained(rng, 400), seed=0)
        again = csd.DomainModel.from_dict(json.loads(json.dumps(model.to_dict())))
        q = constrained(rng, 50)
        q[::7, 2] += 1.0
        self.assertEqual(model.classify(q)[0], again.classify(q)[0])

    def test_false_positive_rate_has_an_interval(self):
        rng = np.random.default_rng(7)
        rep = csd.check({"features": ["a", "b"], "training": rng.normal(size=(200, 2)).tolist(),
                         "queries": [[0.0, 0.0]]})
        lo, hi = rep["false_positive_rate_interval_68"]
        self.assertLessEqual(lo, rep["estimated_false_positive_rate"])
        self.assertGreaterEqual(hi, rep["estimated_false_positive_rate"])

    def test_flag_rates_match_the_split_conformal_rank(self):
        """Two-sided oracle: each statistic's threshold is the r-th smallest of n held-out values, r = ceil((n+1) l),
        l = 1 - (1 - q)/2, so a fresh exchangeable point exceeds it with probability exactly a = 1 - min(r, n)/(n+1)
        (split-conformal ranks, continuous scores; expectation over training draws). Each of Mahalanobis and k-NN must
        sit at a, and their union ('outside or sparse') in [a, 2a]. The old per-feature min/max box (the pre-fix
        inference rule) is the negative control: about 10% at d = 32, n = 600, far above 2a. The small setting
        (n = 100, d = 4: 20 held out) resolves a threshold one rank off (a shift of 1/(n+1) in a)."""
        def mean_se(v):
            return np.mean(v), np.std(v, ddof=1) / np.sqrt(len(v))

        for quantile, n_train, d, draws in ((0.99, 600, 32, 40), (0.95, 600, 32, 40), (0.8, 100, 4, 200)):
            rates = {"mahalanobis": [], "knn": [], "union": [], "box": []}
            for rep in range(draws):
                rng = np.random.default_rng(100 + rep)
                x, fresh = rng.normal(size=(n_train, d)), rng.normal(size=(2000, d))
                model = csd.DomainModel.fit(x, quantile=quantile, seed=rep)
                rows = model.details(fresh)
                stats = rows[0][2]
                for name in ("mahalanobis", "knn"):
                    rates[name].append(np.mean(stats[name] > model.thresholds[name]))
                rates["union"].append(np.mean([r[0] != "inside" for r in rows]))
                rates["box"].append(np.mean(np.any((fresh < x.min(axis=0)) | (fresh > x.max(axis=0)), axis=1)))
            n = model.n_held
            a = 1.0 - min(math.ceil((n + 1) * (1 - (1 - quantile) / 2)), n) / (n + 1)
            with self.subTest(quantile=quantile):
                for name in ("mahalanobis", "knn"):
                    mean, se = mean_se(rates[name])
                    self.assertLess(abs(mean - a), 4 * se, (name, mean, a, se))
                mean, se = mean_se(rates["union"])
                self.assertGreater(mean, a - 4 * se, (mean, a, se))
                self.assertLess(mean, 2 * a + 4 * se, (mean, 2 * a, se))
                if d == 32:
                    mean, se = mean_se(rates["box"])
                    self.assertGreater(mean - 4 * se, 2 * a, mean)

    def test_false_positive_interval_is_the_beta_quantile_clopper_pearson(self):
        """Second oracle kind for the reported interval: Clopper-Pearson from scipy.stats.beta quantiles at the
        stated 68.27% level, for the model's own count of flagged held-out points."""
        from scipy.stats import beta

        alpha, counts = 1 - 0.6827, set()
        for seed, (n, quantile) in enumerate(((200, 0.99), (200, 0.9), (400, 0.8), (60, 0.6), (1000, 0.95))):
            rng = np.random.default_rng(40 + seed)
            rep = csd.check({"features": ["a", "b", "c"], "training": rng.normal(size=(n, 3)).tolist(),
                             "queries": [[0.0, 0.0, 0.0]]}, quantile=quantile)
            m = rep["n_held_out"]  # the two cross-fit halves test every held-out point once
            k = round(rep["estimated_false_positive_rate"] * m)
            counts.add(k)
            lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, m - k + 1)
            hi = 1.0 if k == m else beta.ppf(1 - alpha / 2, k + 1, m - k)
            for got, want in zip(rep["false_positive_rate_interval_68"], (lo, hi), strict=True):
                self.assertAlmostEqual(got, want, delta=1e-9 * max(1.0, want), msg=(n, quantile, k, m))
        self.assertGreater(len(counts), 3, counts)

    def test_cli_groups_and_categorical(self):
        rng = np.random.default_rng(8)
        x = np.c_[rng.normal(size=300), rng.integers(0, 3, 300)]
        payload = {"features": ["a", "k"], "training": x.tolist(), "groups": [int(i // 3) for i in range(300)],
                   "categorical": ["k"], "queries": [[0.0, 2.0], [0.0, 1.5]]}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "d.json"
            p.write_text(json.dumps(payload))
            r = subprocess.run([sys.executable, str(ML / "scripts" / "check_surrogate_domain.py"), str(p)],
                               capture_output=True, text=True, timeout=600)
        rep = json.loads(r.stdout)
        self.assertEqual([q["status"] for q in rep["queries"]][1], "outside")
        self.assertTrue(rep["holdout"].startswith("grouped"))


def write_csv(path, x, y, ids):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "f1", "f2", "f3", "f4", "label"])
        for i, (row, lab) in enumerate(zip(x, y)):
            w.writerow([ids[i], *[f"{v:.6f}" for v in row], int(lab)])


@unittest.skipUnless(TORCH, "PyTorch not installed")
class TrainingAndInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.dir = Path(cls.tmp.name)
        rng = np.random.default_rng(9)
        x = constrained(rng, 900)
        y = (x[:, 0] + 0.3 * rng.normal(size=900) > 0).astype(int)
        ids = [f"e{i}" for i in range(900)]
        write_csv(d / "events.csv", x, y, ids)
        groups = {i: f"r{k // 5}" for k, i in enumerate(ids)}
        manifest = {"train": ids[:600], "val": ids[600:750], "test": ids[750:], "groups": groups}
        (d / "m.json").write_text(json.dumps(manifest))
        cls.train = subprocess.run([sys.executable, str(ML / "assets" / "train_classifier.py"), "--device", "cpu",
                                    "--data", str(d / "events.csv"), "--split-manifest", str(d / "m.json"),
                                    "--features", "f1,f2,f3,f4", "--epochs", "2", "--num-workers", "0",
                                    "--hidden-dim", "8", "--output-dir", str(d / "run")],
                                   capture_output=True, text=True, timeout=600)
        q = constrained(rng, 3)
        q[1, 2] += 0.5          # broken constraint
        q[2, 0] = float("nan")  # non-finite
        write_csv(d / "q.csv", q, [0, 0, 0], ["ok", "broken", "nan"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def infer(self, *extra):
        r = subprocess.run([sys.executable, str(ML / "assets" / "inference.py"), str(self.dir / "run" / "best.pt"),
                            "--input", str(self.dir / "q.csv"), *extra], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr)
        return {row["id"]: row for row in json.loads(r.stdout)["rows"]}

    def test_training_stores_the_shared_domain_model(self):
        self.assertEqual(self.train.returncode, 0, self.train.stderr)
        import torch
        meta = torch.load(self.dir / "run" / "best.pt", map_location="cpu", weights_only=True)["metadata"]
        dom = meta["training_domain"]
        self.assertEqual(dom["method"], csd.DomainModel.METHOD)
        self.assertEqual(dom["fit_on"], "train")
        self.assertTrue(dom["model"]["holdout"].startswith("grouped"))

    def test_inference_flags_the_broken_constraint_and_scores_no_non_finite_row(self):
        rows = self.infer()
        self.assertEqual(rows["broken"]["out_of_domain"], 1)
        self.assertEqual(rows["nan"]["out_of_domain"], 1)
        self.assertIsNone(rows["nan"]["score"])
        self.assertIsNotNone(rows["ok"]["score"])

    def test_inference_applies_a_stored_calibration_map(self):
        cal = self.dir / "cal.json"
        cal.write_text(json.dumps({"calibration": {"method": "temperature", "params": {"temperature": 2.0}}}))
        raw = self.infer()["ok"]["score"]
        rows = self.infer("--calibration", str(cal))
        z = np.log(raw / (1 - raw))
        self.assertAlmostEqual(rows["ok"]["score"], 1 / (1 + np.exp(-z / 2.0)), places=5)


if __name__ == "__main__":
    unittest.main()

"""ML3 extensions: a regression objective (train_bdt.py task regression with the ml-artifact regression checks), a
mass-sculpting report (Jensen-Shannon distance between the background mass shapes that pass and fail a cut), export
(export_bdt.py: xgboost save_model JSON <-> UBJSON; ONNX and TMVA SaveXGBoost only when their packages are installed,
else exit 3 with a hint), and external scores (TMVA or LightGBM score files) through the leakage, domain and
calibration checks of assets/inference.py and the writer. Backend tests skip without xgboost or scikit-learn; the
external-score tests need numpy only. All data are SYNTHETIC."""
import csv
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SC = PLUGIN / "skills" / "hep-ml" / "scripts"
TRAIN, EXPORT, WRITER = SC / "train_bdt.py", SC / "export_bdt.py", SC / "write_ml_artifact.py"
INFER = PLUGIN / "skills" / "hep-ml" / "assets" / "inference.py"
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_XGB = HAS_NUMPY and importlib.util.find_spec("xgboost") is not None
HAS_SKL = HAS_NUMPY and importlib.util.find_spec("sklearn") is not None
HAS_ONNX = importlib.util.find_spec("onnxmltools") is not None
HAS_ROOT = importlib.util.find_spec("ROOT") is not None


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=900)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


def write_rows(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)


def regression_data(path, n=3000, seed=2):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        x0, x1 = rng.uniform(1, 5), rng.gauss(0, 1)
        rows.append({"id": i, "event": 500 + i, "weight": 1.0, "x0": x0, "x1": x1,
                     "energy": 2.0 * x0 + 1.0 + rng.gauss(0, 0.1)})
    write_rows(path, rows, ["id", "event", "weight", "x0", "x1", "energy"])


def sculpting_data(path, correlated, n=4000, seed=3):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        y = i % 2
        x0 = rng.gauss(2.0 if y else 0.0, 1.0)
        mass = 100 + (8.0 * x0 if correlated else 0.0) + rng.gauss(0, 5)
        rows.append({"id": i, "event": 900 + i, "label": y, "weight": 1.0, "x0": x0, "x1": rng.gauss(0, 1),
                     "mass": mass})
    write_rows(path, rows, ["id", "event", "label", "weight", "x0", "x1", "mass"])


def cfg_file(path, backend, **over):
    cfg = {"features": ["x0", "x1"], "label": "label", "weight": "weight", "id": "id", "event_number": "event",
           "folds": 3, "backend": backend, "seed": 5, "n_threads": 1,
           "hyperparameters": {"max_depth": [3], "learning_rate": [0.2], "n_estimators": [80]}, "objective": "auc"}
    cfg.update(over)
    Path(path).write_text(json.dumps(cfg), encoding="utf-8")


class Regression(unittest.TestCase):
    def check(self, backend):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            regression_data(d / "ev.csv")
            cfg_file(d / "c.json", backend, task="regression", label="energy", objective="rmse")
            code, out, err = run(TRAIN, "--data", d / "ev.csv", "--config", d / "c.json", "--negative-weights",
                                 "reject", "--out-dir", d / "run")
            self.assertEqual(code, 0, (out, err))
            t = out["metrics"]["test"]
            self.assertLess(t["rmse"], 0.3)
            self.assertLess(abs(t["mean_bias"]), 0.05)
            summary = json.loads((d / "run" / "run_summary.json").read_text())
            self.assertEqual(summary["task"], "regression")
            rv = summary["regression_validation"]
            for key in ("response_vs_truth", "response_vs_reco", "closure_alt_spectrum", "outlier_fraction"):
                self.assertIn(key, rv)
            self.assertEqual(rv["closure_alt_spectrum"]["status"], "not-run")
            for row in rv["response_vs_truth"]:
                self.assertAlmostEqual(row["response"], 1.0, delta=0.05)
            self.assertNotIn("working_points", {k for k in out if out.get(k)})
            code, art, err = run(WRITER, "--run-summary", d / "run" / "run_summary.json", "--out", d / "a.json",
                                 "--output-semantics", "regression-value", "--status", "synthetic")
            self.assertEqual(code, 0, (art, err))
            self.assertIn("regression_validation", json.loads((d / "a.json").read_text())["extension"])

    @unittest.skipUnless(HAS_XGB, "xgboost is not installed (optional extra bdt)")
    def test_xgboost_regression(self):
        self.check("xgboost")

    @unittest.skipUnless(HAS_SKL, "scikit-learn is not installed (optional extra bdt)")
    def test_sklearn_regression(self):
        self.check("sklearn")

    def test_regression_needs_the_rmse_objective(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            regression_data(d / "ev.csv", n=50)
            cfg_file(d / "c.json", "xgboost", task="regression", label="energy", objective="auc")
            code, out, _ = run(TRAIN, "--data", d / "ev.csv", "--config", d / "c.json", "--negative-weights",
                               "reject", "--out-dir", d / "run")
            self.assertEqual(code, 2)
            self.assertIn("rmse", out["error"])


@unittest.skipUnless(HAS_XGB, "xgboost is not installed (optional extra bdt)")
class MassSculpting(unittest.TestCase):
    def js(self, correlated):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            sculpting_data(d / "ev.csv", correlated, n=8000)
            cfg_file(d / "c.json", "xgboost", mass_column="mass", working_point_efficiencies=[0.9], mass_bins=10)
            code, out, err = run(TRAIN, "--data", d / "ev.csv", "--config", d / "c.json", "--negative-weights",
                                 "reject", "--out-dir", d / "run")
            self.assertEqual(code, 0, (out, err))
            ms = out["mass_sculpting"]
            self.assertEqual(ms["mass_column"], "mass")
            return ms["working_points"][0]["js_distance"]

    def test_correlated_mass_is_sculpted_and_uncorrelated_is_not(self):
        # Without sculpting the distance is finite-sample noise: JS^2 ~ (bins - 1) / (8 ln 2) (1/N_pass + 1/N_fail),
        # about 0.05 here (10 bins, about 900 passing and 3100 failing background events); 0.1 is twice that.
        self.assertGreater(self.js(True), 0.4)
        self.assertLess(self.js(False), 0.1)


class Export(unittest.TestCase):
    @unittest.skipUnless(HAS_XGB, "xgboost is not installed (optional extra bdt)")
    def test_json_to_ubj_round_trip_predicts_the_same(self):
        import numpy as np
        import xgboost as xgb
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            x = np.random.default_rng(1).normal(size=(200, 2))
            y = (x[:, 0] > 0).astype(float)
            b = xgb.train({"objective": "binary:logistic", "max_depth": 2, "seed": 1}, xgb.DMatrix(x, label=y), 10)
            b.save_model(str(d / "m.json"))
            code, out, err = run(EXPORT, d / "m.json", "--to", "ubj", "--out", d / "m.ubj")
            self.assertEqual(code, 0, (out, err))
            b2 = xgb.Booster()
            b2.load_model(str(d / "m.ubj"))
            self.assertTrue(np.array_equal(b.predict(xgb.DMatrix(x)), b2.predict(xgb.DMatrix(x))))
            self.assertEqual(out["sha256"], hashlib.sha256((d / "m.ubj").read_bytes()).hexdigest())

    @unittest.skipIf(HAS_ONNX, "onnxmltools is installed: the missing-dependency path is not reachable")
    def test_onnx_without_onnxmltools_exits_3_with_a_hint(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "m.json").write_text("{}", encoding="utf-8")
            code, out, _ = run(EXPORT, Path(d, "m.json"), "--to", "onnx", "--n-features", "2", "--out",
                               Path(d, "m.onnx"))
            self.assertEqual(code, 3)
            self.assertEqual(out["status"], "missing-dependency")
            self.assertIn("pip install", out["install"])

    @unittest.skipIf(HAS_ROOT, "ROOT is importable here: the missing-dependency path is not reachable")
    def test_tmva_without_root_exits_3_with_a_hint(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "m.json").write_text("{}", encoding="utf-8")
            code, out, _ = run(EXPORT, Path(d, "m.json"), "--to", "tmva", "--n-features", "2", "--out",
                               Path(d, "m.root"))
            self.assertEqual(code, 3)
            self.assertIn("ROOT", out["install"])

    def test_bad_input(self):
        code, out, _ = run(EXPORT, "/nonexistent/m.json", "--to", "ubj", "--out", "/tmp/never.ubj")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


@unittest.skipUnless(HAS_NUMPY, "numpy is not installed")
class ExternalScores(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = Path(self.tmp.name)
        rng = random.Random(4)
        train = [{"id": f"t{i}", "x0": rng.gauss(0, 1), "x1": rng.gauss(0, 1)} for i in range(400)]
        test = [{"id": f"e{i}", "x0": rng.gauss(0, 1), "x1": rng.gauss(0, 1)} for i in range(100)]
        test.append({"id": "far", "x0": 40.0, "x1": -40.0})
        write_rows(d / "train.csv", train, ["id", "x0", "x1"])
        write_rows(d / "test.csv", test, ["id", "x0", "x1"])
        (d / "model.xml").write_text("<SYNTHETIC TMVA weights/>", encoding="utf-8")
        self.model_hash = "sha256:" + hashlib.sha256((d / "model.xml").read_bytes()).hexdigest()
        (d / "manifest.json").write_text(json.dumps({"train": [r["id"] for r in train], "test": [r["id"] for r in test],
                                                     "groups": {}}), encoding="utf-8")
        self.scores = [{"id": r["id"], "score": 0.5} for r in test]

    def tearDown(self):
        self.tmp.cleanup()

    def infer(self, scores, *extra):
        write_rows(self.d / "scores.csv", scores, ["id", "score"])
        return run(INFER, "--external-scores", self.d / "scores.csv", "--external-tool", "tmva", "--model-file",
                   self.d / "model.xml", "--input", self.d / "test.csv", "--training-features", self.d / "train.csv",
                   "--split-manifest", self.d / "manifest.json", *extra)

    def test_test_scores_pass_with_domain_flags(self):
        code, out, err = self.infer(self.scores, "--run-summary-out", self.d / "rs.json", "--labels",
                                    "background,signal", "--grouping-key", "event")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["model_hash"], self.model_hash)
        self.assertEqual(out["leakage_check"]["scored_training_ids"], 0)
        self.assertGreaterEqual(out["n_out_of_domain"], 1)
        self.assertEqual(out["external"]["tool"], "tmva")
        code, art, err = run(WRITER, "--run-summary", self.d / "rs.json", "--out", self.d / "a.json", "--status",
                             "synthetic")
        self.assertEqual(code, 0, (art, err))

    def test_a_score_on_a_training_event_is_refused(self):
        code, out, _ = self.infer(self.scores + [{"id": "t3", "score": 0.9}])
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "refused")
        self.assertEqual(out["leakage_check"]["scored_training_ids"], 1)

    def test_calibration_for_another_model_is_refused_and_the_right_one_applied(self):
        cal = {"calibration": {"method": "platt", "params": {"a": 1.0, "b": 0.5}}, "model_hash": "sha256:" + "0" * 64}
        (self.d / "cal.json").write_text(json.dumps(cal), encoding="utf-8")
        code, out, _ = self.infer(self.scores, "--calibration", self.d / "cal.json")
        self.assertEqual(code, 2)
        cal["model_hash"] = self.model_hash
        (self.d / "cal.json").write_text(json.dumps(cal), encoding="utf-8")
        code, out, err = self.infer(self.scores, "--calibration", self.d / "cal.json", "--output", self.d / "o.csv")
        self.assertEqual(code, 0, (out, err))
        with open(self.d / "o.csv", encoding="utf-8") as fh:
            first = next(csv.DictReader(fh))
        self.assertAlmostEqual(float(first["score"]), 1 / (1 + 2.718281828459045 ** -0.5), delta=1e-9)


if __name__ == "__main__":
    unittest.main()

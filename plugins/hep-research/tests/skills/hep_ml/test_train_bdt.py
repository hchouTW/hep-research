"""train_bdt.py (ML3): k-fold cross-trained BDT with xgboost (primary) or scikit-learn HistGradientBoosting (fallback).

Oracles: two equal-variance Gaussians separated by d standard deviations give an AUC near Phi(d / sqrt 2); folds are
disjoint and pass check_split_integrity.py; a fixed seed and thread count give byte-identical scores; integer
weights equal duplicated events (xgboost exact method); under abs-train-signed-eval the evaluated weighted sum equals
the signed yield; the run summary is accepted by write_ml_artifact.py. Contract: --negative-weights has no default,
reject exits 3 with an explanation, a missing backend exits 3 with an install hint, --help runs without NumPy, no
pickle is written. The backend tests skip when xgboost or scikit-learn is not installed (optional extra `bdt`).
All data are SYNTHETIC."""
import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-ml" / "scripts" / "train_bdt.py"
SPLIT_CHECK = PLUGIN / "skills" / "hep-ml" / "scripts" / "check_split_integrity.py"
WRITER = PLUGIN / "skills" / "hep-ml" / "scripts" / "write_ml_artifact.py"
HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_XGB = HAS_NUMPY and importlib.util.find_spec("xgboost") is not None
HAS_SKL = HAS_NUMPY and importlib.util.find_spec("sklearn") is not None


def run(*args, env=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=900, env=env)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


def gaussians(path, n=4000, d=2.0, seed=1, negative_fraction=0.0, weight=None, extra_feature=True):
    """SYNTHETIC: signal ~ N(d, 1), background ~ N(0, 1) in feature x0; x1 is noise. Columns id, event, run, label,
    weight, x0, x1."""
    import random
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        y = i % 2
        x0 = rng.gauss(d if y else 0.0, 1.0)
        x1 = rng.gauss(0.0, 1.0)
        w = 1.0 if weight is None else weight(i, rng)
        if negative_fraction and rng.random() < negative_fraction:
            w = -abs(w)
        rows.append({"id": i, "event": 1000 + i, "run": 7 + i % 3, "label": y, "weight": w, "x0": x0, "x1": x1})
    with open(path, "w", newline="", encoding="utf-8") as fh:
        cols = ["id", "event", "run", "label", "weight", "x0"] + (["x1"] if extra_feature else [])
        wr = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return rows


def config(path, backend="xgboost", **over):
    cfg = {"features": ["x0", "x1"], "label": "label", "signal_label": 1, "weight": "weight", "id": "id",
           "event_number": "event", "folds": 3, "backend": backend, "seed": 11, "n_threads": 1,
           "hyperparameters": {"max_depth": [2, 3], "learning_rate": [0.2], "n_estimators": [60]},
           "objective": "auc", "early_stopping_rounds": 10, "validation_fraction": 0.25,
           "working_point_efficiencies": [0.5, 0.9]}
    cfg.update(over)
    Path(path).write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class Contract(unittest.TestCase):
    def test_help_without_numpy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('numpy hidden for this test')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                               timeout=600, env=env)
        self.assertEqual(p.returncode, 0)
        self.assertIn("--negative-weights", p.stdout)

    def test_negative_weight_policy_has_no_default(self):
        with tempfile.TemporaryDirectory() as d:
            gaussians(Path(d, "x.csv"), n=40)
            config(Path(d, "c.json"))
            code, out, _ = run("--data", Path(d, "x.csv"), "--config", Path(d, "c.json"), "--out-dir", Path(d, "o"))
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")

    def test_missing_backend_exits_3_with_hint(self):
        with tempfile.TemporaryDirectory() as d:
            for mod in ("xgboost", "sklearn"):
                Path(d, f"{mod}.py").write_text(f"raise ImportError('{mod} hidden for this test')\n", encoding="utf-8")
            gaussians(Path(d, "x.csv"), n=40)
            config(Path(d, "c.json"))
            env = dict(os.environ, PYTHONPATH=d, PYTHONDONTWRITEBYTECODE="1")
            code, out, _ = run("--data", Path(d, "x.csv"), "--config", Path(d, "c.json"), "--out-dir", Path(d, "o"),
                               "--negative-weights", "drop", env=env)
        if not HAS_NUMPY:
            self.assertEqual(code, 3)
            return
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("pip install", out["install"])

    def test_negative_weight_warning_names_the_distorted_density(self):
        """REVIEW-CODE-WARN, without a BDT backend (CI installs neither xgboost nor scikit-learn): the warning text for
        each policy. drop learns the positive-weight density, abs-train-signed-eval the |w| density; reject and runs
        without negative weights get none."""
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            spec = importlib.util.spec_from_file_location("train_bdt_under_test", SCRIPT)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        for policy, density in (("drop", "positive-weight density"), ("abs-train-signed-eval", "|w| density")):
            with self.subTest(policy=policy):
                text = mod.negative_weight_warning(policy, 7)
                self.assertIn("training density is distorted", text)
                self.assertIn(density, text)
                self.assertIn("7 negative-weight", text)
                self.assertIn("signed-weight or resampled training", text)
                self.assertIn('ml-analysis-weights.md, "Negative weights", options 3 and 4', text)
                self.assertIsNone(mod.negative_weight_warning(policy, 0))
        self.assertIsNone(mod.negative_weight_warning("reject", 0))

    def test_no_pickle_in_the_script(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for word in ("import pickle", "joblib", "pickle.load", "pickle.dump"):
            self.assertNotIn(word, text)


class Backend:
    """Mixed into one TestCase per backend."""
    backend = "xgboost"

    def fit(self, d, n=4000, neg=None, **over):
        gaussians(Path(d, "x.csv"), n=n, **over.pop("data", {}))
        config(Path(d, "c.json"), backend=self.backend, **over)
        return run("--data", Path(d, "x.csv"), "--config", Path(d, "c.json"), "--out-dir", Path(d, "out"),
                   "--negative-weights", neg or "drop")

    def test_empty_validation_part_is_rejected_before_training(self):
        """SYNTHETIC, 16 events in 3 runs keyed by run, as in an L3 eval run: validation_fraction 0.01 leaves the
        validation parts empty. Before, every grid point scored NaN and the run crashed writing its summary (exit 1,
        no JSON, fold models left behind); now it is refused with the counts and no model is trained."""
        with tempfile.TemporaryDirectory() as d:
            code, out, err = self.fit(d, n=16, event_number="run", folds=2, validation_fraction=0.01)
            self.assertEqual(code, 2, err)
            self.assertEqual(out["status"], "rejected")
            self.assertIn("no fold has a validation part", out["error"])
            self.assertFalse(list(Path(d, "out").glob("model_fold*")))

    def test_one_empty_validation_part_still_trains(self):
        """SYNTHETIC, runs 7, 8, 9 keyed by run with 3 folds (run mod 3): validation_fraction 0.67 sends only run 8
        to validation (sha256 0.666; runs 7 and 9 hash to 0.944 and 0.679), so fold 2's validation part is empty and
        folds 0 and 1 choose the hyperparameters. This trains, as before #153 (which refused it)."""
        with tempfile.TemporaryDirectory() as d:
            code, out, err = self.fit(d, n=60, event_number="run", folds=3, validation_fraction=0.67)
            self.assertEqual(code, 0, (out, err))
            self.assertEqual(len(list(Path(d, "out").glob("model_fold*"))), 3 if self.backend == "xgboost" else 0)

    def test_auc_of_two_gaussians(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, err = self.fit(d)
            self.assertEqual(code, 0, (out, err))
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["status_label"], "unvalidated")
            auc = out["metrics"]["test"]["auc_weighted"]
            self.assertAlmostEqual(auc, phi(2.0 / math.sqrt(2)), delta=0.015)
            self.assertIn(out["hyperparameters"]["selected"]["max_depth"], (2, 3))
            self.assertEqual(out["hyperparameters"]["selected_on"], "validation folds")
            ot = out["overtraining"]
            self.assertIn("train_test_distance", ot)
            self.assertNotIn("p_value", json.dumps(ot))
            for wp in out["working_points"]:
                self.assertIn(wp["target_signal_efficiency"], (0.5, 0.9))

    def test_folds_disjoint_and_pass_the_split_check(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.fit(d, n=600)
            self.assertEqual(code, 0)
            manifest = json.loads(Path(d, "out", "fold_manifest.json").read_text())
            folds = [set(manifest[f"fold{k}"]) for k in range(3)]
            self.assertEqual(sum(len(f) for f in folds), 600)
            self.assertEqual(len(set().union(*folds)), 600)
            p = subprocess.run([sys.executable, "-B", str(SPLIT_CHECK), str(Path(d, "out", "fold_manifest.json")),
                                "--json", "--strict"], capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 0, p.stdout)
            # each event is scored by a model that did not see it
            for row in csv.DictReader(open(Path(d, "out", "scores.csv"), encoding="utf-8")):
                self.assertNotIn(row["id"], manifest_train_ids(manifest, int(row["fold"])))

    def test_fixed_seed_gives_byte_identical_scores(self):
        blobs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as d:
                code, _, _ = self.fit(d, n=800)
                self.assertEqual(code, 0)
                blobs.append(Path(d, "out", "scores.csv").read_bytes())
        self.assertEqual(blobs[0], blobs[1])

    def test_abs_train_signed_eval_keeps_the_signed_yield(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, err = self.fit(d, n=1200, neg="abs-train-signed-eval", data={"negative_fraction": 0.2})
            self.assertEqual(code, 0, (out, err))
            rows = list(csv.DictReader(open(Path(d, "x.csv"), encoding="utf-8")))
            for cls, name in ((1, "signal"), (0, "background")):
                signed = sum(float(r["weight"]) for r in rows if int(r["label"]) == cls)
                self.assertAlmostEqual(out["weights"]["evaluated_weight_sum"][name], signed, delta=1e-9)
            self.assertGreater(out["weights"]["negative_fraction"], 0.1)
            self.assertLess(out["weights"]["negative_sum"], 0)
            self.assertEqual(out["weights"]["training_weights"], "absolute values of the physical weights")

    def test_drop_and_abs_warn_that_the_training_density_is_distorted(self):
        """REVIEW-CODE-WARN: drop trains on the positive-weight density and abs-train-signed-eval on the |w| density,
        not the signed one; with negative weights present the run output warns and points to ml-analysis-weights.md,
        "Negative weights", options 3 and 4. Without negative weights there is nothing to warn about."""
        for policy, density in (("drop", "positive-weight density"), ("abs-train-signed-eval", "|w| density")):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as d:
                code, out, err = self.fit(d, n=600, neg=policy, data={"negative_fraction": 0.2})
                self.assertEqual(code, 0, (out, err))
                hits = [w for w in out["warnings"] if "training density is distorted" in w]
                self.assertEqual(len(hits), 1, out["warnings"])
                self.assertIn(density, hits[0])
                self.assertIn("options 3 and 4", hits[0])
            with self.subTest(policy=policy, negatives=False), tempfile.TemporaryDirectory() as d:
                code, out, err = self.fit(d, n=600, neg=policy)
                self.assertEqual(code, 0, (out, err))
                self.assertFalse([w for w in out["warnings"] if "training density" in w], out["warnings"])

    def test_reject_with_negative_weights_exits_3(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.fit(d, n=200, neg="reject", data={"negative_fraction": 0.2})
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "incomplete")
        self.assertIn("negative", out["reason"])

    def test_run_summary_is_accepted_by_the_ml_artifact_writer(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = self.fit(d, n=600)
            self.assertEqual(code, 0)
            o = Path(d, "out")
            rep = subprocess.run([sys.executable, "-B", str(SPLIT_CHECK), str(o / "fold_manifest.json"), "--json"],
                                 capture_output=True, text=True, timeout=600)
            (o / "split_report.json").write_text(rep.stdout, encoding="utf-8")
            p = subprocess.run([sys.executable, "-B", str(WRITER), "--run-summary", str(o / "run_summary.json"),
                                "--split-report", str(o / "split_report.json"), "--output-semantics", "score",
                                "--status", "synthetic", "--out", str(o / "ml_artifact.json")],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            summary = json.loads((o / "run_summary.json").read_text())
            self.assertTrue(summary["split_manifest_sha256"])
            self.assertTrue(summary["model_hash"].startswith("sha256:"))
            self.assertEqual(summary["features"], ["x0", "x1"])
            self.assertIn("seed", json.dumps(summary["environment"]))
            names = {p.suffix for p in o.iterdir()}
            self.assertFalse(names & {".pkl", ".pickle", ".joblib"})
            # the run folder kept in artifacts_dir passes the folder check: the artifact names every file in it
            doc = json.loads((o / "ml_artifact.json").read_text())
            self.assertEqual(sorted(x["ref"] for x in doc["outputs"] if x["kind"].startswith("checkpoint")),
                             sorted(summary.get("models") or []))
            d_check = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / "validate.py"), str(o)],
                                     capture_output=True, text=True, timeout=600)
            self.assertEqual(d_check.returncode, 0, d_check.stdout + d_check.stderr)


def manifest_train_ids(manifest, fold):
    return {i for k in range(len([x for x in manifest if x.startswith("fold")])) if k != fold
            for i in manifest[f"fold{k}"]} - set(manifest[f"fold{fold}"])


@unittest.skipUnless(HAS_XGB, "optional package xgboost not installed (extra `bdt`)")
class XgboostBackend(Backend, unittest.TestCase):
    backend = "xgboost"

    def test_integer_weights_equal_duplicated_events(self):
        """weight 2 on every other event equals that event written twice (same event number, same fold)."""
        with tempfile.TemporaryDirectory() as d:
            rows = gaussians(Path(d, "w.csv"), n=600, weight=lambda i, rng: 2.0 if i % 2 == 0 else 1.0)
            dup = []
            for r in rows:
                dup.append(dict(r, weight=1.0))
                if r["weight"] == 2.0:
                    dup.append(dict(r, weight=1.0, id=100000 + r["id"]))
            with open(Path(d, "d.csv"), "w", newline="", encoding="utf-8") as fh:
                wr = csv.DictWriter(fh, fieldnames=["id", "event", "run", "label", "weight", "x0", "x1"])
                wr.writeheader()
                wr.writerows(dup)
            over = {"tree_method": "exact", "hyperparameters": {"max_depth": [2], "learning_rate": [0.3],
                                                                 "n_estimators": [20]}, "early_stopping_rounds": 0}
            config(Path(d, "c.json"), backend="xgboost", **over)
            scores = []
            for data in ("w.csv", "d.csv"):
                code, out, err = run("--data", Path(d, data), "--config", Path(d, "c.json"), "--out-dir",
                                     Path(d, data + ".out"), "--negative-weights", "reject")
                self.assertEqual(code, 0, (out, err))
                scores.append({r["id"]: float(r["score"]) for r in
                               csv.DictReader(open(Path(d, data + ".out", "scores.csv"), encoding="utf-8"))})
            for key, value in scores[0].items():
                self.assertAlmostEqual(scores[1][key], value, delta=1e-6)

    def test_importance_and_json_models(self):
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = self.fit(d, n=600)
            self.assertEqual(code, 0)
            imp = out["importance"]
            for kind in ("gain", "cover", "tree_shap_mean_abs"):
                self.assertIn(kind, imp)
            self.assertGreater(imp["tree_shap_mean_abs"]["x0"], imp["tree_shap_mean_abs"]["x1"])
            models = sorted(p.name for p in Path(d, "out").glob("model_fold*"))
            self.assertEqual(models, ["model_fold0.json", "model_fold1.json", "model_fold2.json"])


@unittest.skipUnless(HAS_SKL, "optional package scikit-learn not installed (extra `bdt`)")
class SklearnBackend(Backend, unittest.TestCase):
    backend = "sklearn"


if __name__ == "__main__":
    unittest.main()

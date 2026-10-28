"""train_emulator.py (cr-propagation E2): Gaussian-process emulator of a vector output on a box, its error estimate,
its stored DomainModel and the ml-artifact it feeds (write_ml_artifact.py copies the surrogate's
extrapolation_policy). All data SYNTHETIC: a smooth analytic function stands in for the simulator.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "hep-ml" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT))
import check_surrogate_domain as csd  # noqa: E402
import train_emulator as te  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

FEATURES = [{"name": "a_gev", "min": 1.0, "max": 100.0, "scale": "log", "unit": "GeV"},
            {"name": "b", "min": -1.0, "max": 1.0, "scale": "linear"},
            {"name": "c", "min": 0.0, "max": 2.0, "scale": "linear"}]
X_NODES = np.linspace(0.0, 1.0, 8)


def simulator(point):
    """A smooth positive vector output (8 'bins') of three inputs."""
    a, b, c = math.log10(point["a_gev"]), point["b"], point["c"]
    return [float(np.exp(-0.5 * a ** 1.5 * x + 0.2 * math.sin(c + x)) * (1.0 + 0.3 * b * x ** 2)) for x in X_NODES]


def design(n, seed):
    rng = np.random.default_rng(seed)
    pts = []
    for u in rng.uniform(size=(n, 3)):
        pts.append({"a_gev": 10 ** (2 * u[0]), "b": -1 + 2 * u[1], "c": 2 * u[2]})
    return pts


def training_set(n=70, seed=1):
    pts = design(n, seed)
    return {"features": FEATURES, "outputs": {"name": "y", "count": len(X_NODES), "transform": "log"},
            "points": pts, "values": [simulator(p) for p in pts], "groups": [f"p{i}" for i in range(n)],
            "status": ["synthetic"], "context": {"simulator": "analytic test function"}}


class TrainEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = training_set()
        cls.model = te.train(cls.doc, restarts=1, seed=0)
        cls.emu = te.GaussianProcessEmulator(cls.model)

    def test_accuracy_and_error_estimate_on_held_out_points(self):
        held = design(40, seed=7)
        pred = self.emu.predict(held)
        truth = np.array([simulator(p) for p in held])
        values = np.array([p["values"] for p in pred])
        sigma = np.array([p["sigma"] for p in pred])
        rel = np.abs(values / truth - 1.0)
        self.assertLess(rel.max(), 1e-2)
        # the error estimate is of the right size: neither tiny nor huge compared with the true error
        ratio = np.sqrt(np.mean(((values - truth) / sigma) ** 2))
        self.assertGreater(ratio, 0.05)
        self.assertLess(ratio, 3.0)

    def test_error_grows_outside_the_training_cloud(self):
        centre = self.emu.predict([{"a_gev": 10.0, "b": 0.0, "c": 1.0}])[0]
        far = self.emu.predict([{"a_gev": 1000.0, "b": 0.0, "c": 1.0}])[0]
        self.assertGreater(far["sigma"][-1] / far["values"][-1], 10 * centre["sigma"][-1] / centre["values"][-1])
        self.assertEqual(far["domain"], "outside")
        self.assertEqual(centre["domain"], "inside")

    def test_domain_model_is_the_hep_ml_one_and_round_trips(self):
        dm = csd.DomainModel.from_dict(self.model["domain_model"])
        u = np.random.default_rng(3).uniform(-0.2, 1.2, size=(200, 3))
        self.assertEqual(dm.classify(u)[0], csd.DomainModel.from_dict(json.loads(json.dumps(
            self.model["domain_model"]))).classify(u)[0])

    def test_model_is_plain_json_reproducible_and_self_checking(self):
        # threaded linear algebra may move the optimizer's stopping point in the last digits: a retrained model gives
        # the same predictions far below the emulator's own error, not necessarily the same bytes
        again = te.GaussianProcessEmulator(te.train(json.loads(json.dumps(self.doc)), restarts=1, seed=0))
        pts = design(50, seed=11)
        a = np.array([p["values"] for p in self.emu.predict(pts)])
        b = np.array([p["values"] for p in again.predict(pts)])
        self.assertLess(np.abs(a / b - 1.0).max(), 1e-6)
        reread = te.GaussianProcessEmulator(json.loads(json.dumps(self.model)))
        mean, sigma = reread.predict_unit(np.asarray(self.model["self_check"]["unit"]))
        np.testing.assert_allclose(mean, self.model["self_check"]["transformed_mean"], atol=1e-12, rtol=0)
        np.testing.assert_allclose(sigma, self.model["self_check"]["transformed_sigma"], atol=1e-12, rtol=0)
        self.assertEqual(self.model["context"], {"simulator": "analytic test function"})
        self.assertLessEqual(self.model["pca"]["training_residual_max"], 1e-5)

    def test_gradient_of_the_marginal_likelihood(self):
        rng = np.random.default_rng(5)
        x, y = rng.uniform(size=(25, 3)), rng.normal(size=25)
        theta = np.r_[np.log([0.4, 0.7, 1.3]), 0.2, math.log(1e-4)]
        _, grad = te.neg_log_marginal(theta, x, y)
        for i in range(len(theta)):
            step = np.zeros_like(theta)
            step[i] = 1e-6
            num = (te.neg_log_marginal(theta + step, x, y)[0] - te.neg_log_marginal(theta - step, x, y)[0]) / 2e-6
            self.assertAlmostEqual(grad[i], num, delta=1e-4 * max(1.0, abs(num)))


class TrainEmulatorCli(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "train_emulator.py"), *map(str, args)],
                              capture_output=True, text=True, timeout=300, cwd=cwd)

    def test_train_predict_and_surrogate_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "t.json").write_text(json.dumps(training_set(60, 2)))
            res = self.run_cli("train", "--training-set", "t.json", "--out-dir", ".", "--restarts", "1", cwd=td)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            out = json.loads(res.stdout)
            self.assertEqual(out["domain"], "DomainModel")
            (td / "p.json").write_text(json.dumps(design(3, 9)))
            res = self.run_cli("predict", "--model", td / "emulator-model.json", "--points", td / "p.json")
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(len(json.loads(res.stdout)["predictions"]), 3)
            summary = json.loads((td / "run_summary.json").read_text())
            self.assertEqual(summary["task"], "surrogate")
            self.assertEqual(summary["training_domain"]["a_gev"], [1.0, 100.0])
            summary["extrapolation_policy"] = {"action": "reject", "consumer": "test"}
            (td / "run_summary.json").write_text(json.dumps(summary))
            res = subprocess.run([sys.executable, str(SCRIPTS / "write_ml_artifact.py"), "--run-summary",
                                  "run_summary.json", "--status", "synthetic", "--out", "a.json"],
                                 capture_output=True, text=True, timeout=300, cwd=td)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            art = json.loads((td / "a.json").read_text())
            self.assertEqual(art["extension"]["extrapolation_policy"]["action"], "reject")
            self.assertTrue(validate_artifact(art).ok)
            # without the policy a surrogate artifact is refused (contracts 2.8.0 task block)
            summary.pop("extrapolation_policy")
            (td / "run_summary.json").write_text(json.dumps(summary))
            res = subprocess.run([sys.executable, str(SCRIPTS / "write_ml_artifact.py"), "--run-summary",
                                  "run_summary.json", "--status", "synthetic", "--out", "b.json"],
                                 capture_output=True, text=True, timeout=300, cwd=td)
            self.assertEqual(res.returncode, 1, res.stdout)
            self.assertIn("ml.task_validation_missing", res.stdout)

    def test_bad_inputs_exit_2(self):
        good = training_set(30, 4)
        cases = {
            "outside the box": dict(good, points=good["points"][:-1] + [{"a_gev": 500.0, "b": 0.0, "c": 1.0}]),
            "duplicate": dict(good, points=good["points"][:-1] + [good["points"][0]]),
            "too few": dict(good, points=good["points"][:5], values=good["values"][:5], groups=None),
            "non-positive for log": dict(good, values=good["values"][:-1] + [[0.0] * len(X_NODES)]),
            "no status": dict(good, status=[]),
        }
        with tempfile.TemporaryDirectory() as td:
            for name, doc in cases.items():
                with self.subTest(case=name):
                    path = Path(td) / "t.json"
                    path.write_text(json.dumps(doc))
                    res = self.run_cli("train", "--training-set", path, "--out-dir", Path(td) / "o", "--restarts", "0")
                    self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
                    self.assertEqual(json.loads(res.stdout)["status"], "rejected")


if __name__ == "__main__":
    unittest.main()

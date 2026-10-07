"""PDF uncertainty combination, event-weight bookkeeping and EFT truncation scripts.

Every input below is a constructed test input, not a PDF set, a generator sample or an EFT fit."""
import importlib.util
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "hep-theory" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pdf, weights, eft = load("pdf_uncertainty"), load("event_weights"), load("eft_truncation")


class PdfUncertaintyTests(unittest.TestCase):
    def test_symmetric_hessian(self):
        r = pdf.combine("symmhessian", [10.0, 10.3, 9.6, 10.0])
        self.assertAlmostEqual(r["delta_up"], math.sqrt(0.09 + 0.16), places=12)

    def test_asymmetric_hessian_uses_pairs(self):
        r = pdf.combine("hessian", [10.0, 10.4, 9.9, 9.7, 10.1])  # pairs (10.4, 9.9), (9.7, 10.1)
        self.assertAlmostEqual(r["delta_up"], math.sqrt(0.16 + 0.01), places=12)
        self.assertAlmostEqual(r["delta_down"], math.sqrt(0.01 + 0.09), places=12)

    def test_replicas_use_mean_and_standard_deviation(self):
        rng = random.Random(3)
        reps = [rng.gauss(5.0, 0.2) for _ in range(1000)]
        r = pdf.combine("replicas", [5.0] + reps)
        self.assertAlmostEqual(r["delta_up"], 0.2, delta=0.02)
        lo, hi = r["replica_68_interval"]
        self.assertAlmostEqual((hi - lo) / 2, 0.2, delta=0.03)

    def test_hessian_formula_on_replicas_is_wrong_by_a_large_factor(self):
        rng = random.Random(4)
        members = [5.0] + [rng.gauss(5.0, 0.2) for _ in range(100)]
        wrong = pdf.combine("symmhessian", members)["delta_up"]
        right = pdf.combine("replicas", members)["delta_up"]
        self.assertGreater(wrong / right, 5)  # about sqrt(100)

    def test_refusals(self):
        with self.assertRaises(ValueError):
            pdf.combine("hessian", [1.0, 1.1, 0.9, 1.05])  # odd number of error members
        with self.assertRaises(ValueError):
            pdf.combine("replicas", [1.0] + [1.0] * 10)
        with self.assertRaises(ValueError):
            pdf.combine("unknown", [1.0, 1.1, 0.9])

    def test_90_cl_is_not_rescaled_silently(self):
        r = pdf.combine("symmhessian", [1.0, 1.1645, 1.0], 90.0)
        self.assertEqual(r["conf_level_percent"], 90.0)
        r = pdf.combine("symmhessian", [1.0, 1.1645, 1.0], 90.0, rescale_to_68=True)
        self.assertAlmostEqual(r["delta_up"], 0.1, places=10)
        self.assertIn("Gaussian", r["rescaling"])


class EventWeightTests(unittest.TestCase):
    def test_effective_size_of_unit_weights_is_n_one_minus_2f_squared(self):
        for f in (0.0, 0.1, 0.25):
            n = 1000
            w = [-1.0] * int(f * n) + [1.0] * (n - int(f * n))
            r = weights.summarize(w, 10.0)
            self.assertAlmostEqual(r["effective_sample_size"], n * (1 - 2 * f) ** 2, places=9)

    def test_normalization_uses_the_full_sum_of_weights(self):
        w = [2.0, -1.0, 1.0, 1.0]
        r = weights.summarize(w, 30.0, 1.0, selected=[0, 1])
        self.assertAlmostEqual(r["selected_sigma_pb"], 30.0 * 1.0 / 3.0)
        self.assertGreater(r["bias_if_abs_weights"], 0)
        self.assertGreater(r["bias_if_negatives_dropped"], 0)

    def test_non_positive_sum_refused(self):
        with self.assertRaises(ValueError):
            weights.summarize([1.0, -2.0], 1.0)


class EftTruncationTests(unittest.TestCase):
    DOC = {"basis": "Warsaw (test input)", "normalization": "C_i / Lambda^2", "input_scheme": "{m_W, m_Z, G_F} (test input)",
           "lambda_tev": 1.0, "operators": ["c1", "c2"], "x_sm": 100.0, "linear": {"c1": 10.0, "c2": -4.0},
           "quadratic": {"c1*c1": 3.0, "c1*c2": 1.0}, "points": [{"c1": 0.1}, {"c1": 2.0, "c2": 1.0}],
           "quadratic_flag_fraction": 0.3}

    def test_linear_and_quadratic_terms(self):
        r = eft.evaluate(self.DOC)
        small, large = r["points"]
        self.assertAlmostEqual(small["x_linear"], 101.0)
        self.assertAlmostEqual(small["quadratic_term"], 0.03)
        self.assertFalse(small["truncation_flag"])
        self.assertTrue(large["truncation_flag"])  # quadratic 14 vs linear 16

    def test_only_c_over_lambda_squared_enters(self):
        doc = json.loads(json.dumps(self.DOC))
        doc["lambda_tev"] = 2.0
        doc["points"] = [{k: 4 * v for k, v in p.items()} for p in self.DOC["points"]]
        a, b = eft.evaluate(self.DOC)["points"], eft.evaluate(doc)["points"]
        for x, y in zip(a, b):
            self.assertAlmostEqual(x["x_linear_plus_quadratic"], y["x_linear_plus_quadratic"], places=10)

    def test_conventions_and_operators_required(self):
        for drop in ("basis", "normalization", "input_scheme"):
            with self.subTest(drop=drop), self.assertRaises(ValueError):
                eft.evaluate({k: v for k, v in self.DOC.items() if k != drop})
        with self.assertRaises(ValueError):
            eft.evaluate(dict(self.DOC, points=[{"c3": 1.0}]))

    def test_command_line_refuses_with_exit_1(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "in.json"
            p.write_text(json.dumps({k: v for k, v in self.DOC.items() if k != "basis"}))
            r = subprocess.run([sys.executable, str(SCRIPTS / "eft_truncation.py"), str(p)], capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(json.loads(r.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()

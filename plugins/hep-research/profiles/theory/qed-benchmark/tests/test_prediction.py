"""theory:qed-benchmark numerical prediction tests: units, limits, symmetry, integration convergence."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_NUMPY = find_spec("numpy") is not None
if HAVE_NUMPY:
    import numpy as np

    import predict

CFG = json.loads((ROOT / "benchmarks" / "path-c.json").read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE_NUMPY, "numpy is required (requirements-core.txt)")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_units_and_value_at_benchmark(self):
        self.assertAlmostEqual(self.p["sigma_total_pb"], 86.8 / 100.0 * 1000.0, places=9)  # nb GeV^2 / GeV^2 -> pb
        self.assertAlmostEqual(self.p["sigma_fiducial_pb"], 868.0 * 3 / 8 * (1.8 + 2 * 0.9 ** 3 / 3), places=9)

    def test_angular_dependence_and_symmetry(self):
        v = np.array(self.p["dsigma_dcos_bin_averaged_pb"])
        np.testing.assert_allclose(v, v[::-1], rtol=1e-14)
        self.assertTrue(np.all(np.diff(v[: len(v) // 2]) < 0))  # falls toward cos theta = 0

    def test_convergence_study(self):
        conv = self.p["convergence"]
        self.assertTrue(all(abs(o - 2.0) < 0.05 for o in conv["trapezoid_observed_order"][2:]))
        self.assertLess(conv["trapezoid_abs_error"][-1], conv["trapezoid_abs_error"][0] * 1e-3)

    def test_stored_prediction_is_current(self):
        stored = json.loads((ROOT / "predictions" / "sqrt_s_10gev.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["dsigma_dcos_bin_averaged_pb"], self.p["dsigma_dcos_bin_averaged_pb"])

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*") if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()

"""theory:qcd-r-ratio prediction tests: limits, uncertainty objects kept apart, validity domain, stored output."""
import json
import math
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "r-ratio-15gev.json").read_text(encoding="utf-8"))


@unittest.skipUnless(find_spec("scipy"), "scipy is required for predict.predict (requirements-core.txt)")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_values_at_benchmark(self):
        self.assertAlmostEqual(self.p["R_EW"], 11 / 3, places=12)
        self.assertTrue(0.15 < self.p["alpha_s_at_Q"] < 0.18)  # alpha_s rises from 0.118 at m_Z
        r = [o["R_central_mu_eq_Q"] for o in self.p["orders"]]
        self.assertAlmostEqual(r[1], 11 / 3 * (1 + self.p["alpha_s_at_Q"] / math.pi), places=12)
        self.assertLess(abs(r[4] - r[3]), abs(r[2] - r[1]))

    def test_uncertainty_objects_are_separate_and_not_gaussian(self):
        for o in self.p["orders"]:
            self.assertFalse(o["scale_envelope"]["gaussian"])
            self.assertFalse(o["truncation_estimate"]["gaussian"])
            self.assertEqual(set(o) >= {"scale_envelope", "truncation_estimate", "parametric_alpha_s"}, True)
            self.assertNotIn("total_uncertainty", o)

    def test_alpha_s_running_reverses(self):
        a = predict.run_alpha_s(0.118, 91.1879, 15.0, 5)
        self.assertAlmostEqual(predict.run_alpha_s(a, 15.0, 91.1879, 5), 0.118, places=10)

    def test_outside_validity_domain_refused(self):
        for change in ({"q_gev": 8.0}, {"q_gev": 40.0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                predict.predict(dict(CFG, **change))

    def test_charges_must_match_nf(self):
        with self.assertRaises(ValueError):
            predict.predict(dict(CFG, n_f=4))

    def test_stored_prediction_is_current(self):
        stored = json.loads((ROOT / "predictions" / "r_15gev.json").read_text(encoding="utf-8"))
        for s, o in zip(stored["orders"], self.p["orders"]):
            self.assertAlmostEqual(s["R_central_mu_eq_Q"], o["R_central_mu_eq_Q"], delta=1e-10)

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()

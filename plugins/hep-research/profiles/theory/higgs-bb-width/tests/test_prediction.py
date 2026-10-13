"""theory:higgs-bb-width prediction tests: limits, running, uncertainty objects kept apart, validity domain, stored output."""
import json
import math
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "hbb-125.json").read_text(encoding="utf-8"))


class RecursionTests(unittest.TestCase):
    """Pure-Python parts (no scipy)."""

    def test_r_n_at_mh_are_s_n(self):
        self.assertEqual(predict.r_values(5, -825.7, 0.0), predict.s_coefficients(5, -825.7))

    def test_first_log_term(self):
        lg = 0.8
        self.assertAlmostEqual(predict.r_values(5, -825.7, lg)[1], 17 / 3 + 2 * lg, places=12)

    def test_nf5_coefficients(self):
        s = predict.s_coefficients(5, -825.7)
        self.assertAlmostEqual(s[2], 29.1467, delta=5e-5)
        self.assertAlmostEqual(s[3], 41.7576, delta=5e-5)


@unittest.skipUnless(find_spec("scipy"), "scipy is required for predict.predict (requirements-core.txt)")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_leading_order_with_running_mass(self):
        lo = 3 * CFG["g_f_gev_minus2"] * CFG["m_h_gev"] / (4 * math.sqrt(2) * math.pi) * self.p["mb_at_MH_gev"] ** 2
        self.assertAlmostEqual(self.p["orders"][0]["Gamma_GeV_mu_eq_MH"], lo, delta=1e-15)
        self.assertTrue(2.5 < self.p["mb_at_MH_gev"] < 3.1)  # mbar_b runs down from 4.186 GeV

    def test_running_continues_above_mh(self):
        a, m = predict.run(CFG, 300.0, CFG["alpha_s_mz"], CFG["mb_mb_gev"])
        self.assertLess(m, self.p["mb_at_MH_gev"])
        self.assertLess(a, self.p["alpha_s_at_MH"])

    def test_scale_dependence_falls_with_order(self):
        w = self.p["scale_envelope_widths_GeV"]
        self.assertGreater(w[0], 0.0)  # with a running mass even the leading order depends on mu
        self.assertLess(w[2], w[1])
        self.assertLess(w[4], w[2])

    def test_uncertainty_objects_are_separate_and_not_gaussian(self):
        for o in self.p["orders"]:
            self.assertFalse(o["scale_envelope"]["gaussian"])
            self.assertFalse(o["truncation_estimate"]["gaussian"])
            self.assertEqual(o["truncation_estimate"]["method"], "last-term")
            self.assertTrue({"scale_envelope", "truncation_estimate", "parametric_alpha_s", "parametric_mb"} <= set(o))
            self.assertNotIn("total_uncertainty", o)
            self.assertGreater(o["parametric_mb"]["up"], 0.0)

    def test_outside_validity_domain_refused(self):
        for change in ({"n_f": 4}, {"scale_factors": [0.05, 1.0, 2.0]}, {"alpha_s_mz": 0.5}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                predict.predict(dict(CFG, **change))

    def test_cli_refusal_is_json(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "cfg.json"
            cfg.write_text(json.dumps(dict(CFG, n_f=4)))
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "predict.py"), "--config", str(cfg)],
                               capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["status"], "failed")

    def test_stored_prediction_is_current(self):
        stored = json.loads((ROOT / "predictions" / "hbb_125.json").read_text(encoding="utf-8"))
        for s, o in zip(stored["orders"], self.p["orders"]):
            self.assertAlmostEqual(s["Gamma_GeV_mu_eq_MH"], o["Gamma_GeV_mu_eq_MH"], delta=1e-12)

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()

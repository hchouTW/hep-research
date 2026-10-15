"""theory:cr-secondary-antiprotons internal benchmark: the profile's numerical quadrature of the source integral
against the closed form (incomplete beta functions) for a power-law and a broken power-law primary, every channel,
energies on both sides of the threshold, and a hand-computed point. No published source-term value is used (open
question B2). Inputs are ILLUSTRATIVE."""
import json
import math
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "source-term-benchmark.json").read_text(encoding="utf-8"))


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = predict.benchmark(CFG)
        cls.xs = predict.load_cross_sections(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.b["checks"].values()), self.b["checks"])

    def test_numerical_against_closed_form(self):
        self.assertEqual(len(self.b["rows"]), 2 * 4 * len(CFG["energies_gev"]))
        for row in self.b["rows"]:
            self.assertLess(row["rel_dev"], 1e-8, row)
        self.assertEqual({r["variant"] for r in self.b["rows"]}, {"configured", "broken-power-law"})

    def test_threshold_is_six_proton_masses(self):
        self.assertAlmostEqual(self.b["threshold_gev_per_n"], 6 * 0.93827208816, delta=1e-12)
        below = [t for t in CFG["energies_gev"] if t < self.b["threshold_gev_per_n"]]
        self.assertTrue(below and len(below) < len(CFG["energies_gev"]))

    def test_power_law_scaling_above_threshold(self):
        # above threshold q_pp scales as T^-gamma exactly (beta function is energy independent)
        a, b = (predict.closed_form_channel(CFG, self.xs, "pp", t) for t in (10.0, 100.0))
        self.assertAlmostEqual(a / b, 10.0 ** CFG["primaries"]["p"]["gamma"], delta=1e-9 * a / b)

    def test_hand_computed_beta_value(self):
        # n = 1: B(gamma, 2) = 1 / (gamma (gamma + 1)); pure power law above threshold
        xs = dict(self.xs, pp_prompt={"form": "x-scaling-beta", "sigma0_mb": 30.0, "n": 1.0})
        pl = {"form": "power-law", "K": 3.0, "T0_gev": 1.0, "gamma": 2.0}
        cfg = dict(CFG, primaries={"p": pl, "He": pl})
        t, g = 50.0, 2.0
        expect = 4 * math.pi * CFG["ism"]["n_H_cm3"] * 30e-27 * 3.0 * t ** -g / (g * (g + 1))
        self.assertAlmostEqual(predict.channel_numerical(cfg, xs, "pp", t) / expect, 1.0, delta=1e-10)
        self.assertAlmostEqual(predict.closed_form_channel(cfg, xs, "pp", t) / expect, 1.0, delta=1e-12)

    def test_below_threshold_is_suppressed_not_zero(self):
        t_low = 1.0
        q = predict.closed_form_channel(CFG, self.xs, "pp", t_low)
        above_formula = predict.closed_form_channel(dict(CFG), dict(self.xs, threshold_total_energy_mp=1.0 + 1e-9),
                                                    "pp", t_low)
        self.assertGreater(q, 0)
        self.assertLess(q, above_formula)

    def test_stored_values_reproduced(self):
        rows = {(r["variant"], r["T_gev"], r["channel"]): r for r in self.b["rows"]}
        # regression value of this code (not a published number)
        self.assertAlmostEqual(rows[("configured", 10.0, "pp")]["closed_form"] / 2.9633112490901987e-30, 1.0, delta=1e-12)


if __name__ == "__main__":
    unittest.main()

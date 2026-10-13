"""Tests for scripts/generate_events.py (SYNTHETIC generator of the illustrative synthetic-collider profile)."""
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_events as gen  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "path-b.json").read_text(encoding="utf-8"))


class GeneratorTests(unittest.TestCase):
    def test_reproducible_with_seed(self):
        a, b = gen.generate(CFG, 5), gen.generate(CFG, 5)
        np.testing.assert_array_equal(a["truth_cos"], b["truth_cos"])
        np.testing.assert_array_equal(a["reco_cos"], b["reco_cos"])
        self.assertFalse(np.array_equal(a["truth_cos"], gen.generate(CFG, 6)["truth_cos"]))

    def test_event_count_is_poisson_in_l_sigma(self):
        mu = CFG["integrated_luminosity_pb"] * CFG["generator"]["sigma_pb"]
        n = [gen.generate(CFG, s)["meta"]["n_generated"] for s in range(20)]
        self.assertLess(abs(np.mean(n) - mu), 5 * np.sqrt(mu / 20))

    def test_moments_match_the_shape(self):
        rng = np.random.default_rng(1)
        for a, b in ((1.0, 0.0), (0.5, 0.4)):
            c = gen.sample_cos(rng, 200000, a, b)
            norm = 2 + 2 * a / 3
            m1, m2 = (2 * b / 3) / norm, (2 / 3 + 2 * a / 5) / norm
            self.assertLess(abs(c.mean() - m1), 5 * c.std() / np.sqrt(c.size))
            self.assertLess(abs((c ** 2).mean() - m2), 5 * (c ** 2).std() / np.sqrt(c.size))
            self.assertTrue(np.all(np.abs(c) <= 1))

    def test_negative_shape_rejected(self):
        with self.assertRaises(ValueError):
            gen.sample_cos(np.random.default_rng(1), 10, 0.0, 1.5)

    def test_summary_is_labeled_synthetic(self):
        self.assertEqual(gen.generate(CFG, 1)["meta"]["label"], "SYNTHETIC")
        self.assertTrue(CFG["label"].startswith("SYNTHETIC"))

    def test_background_is_additive(self):
        """The background and the signal x_vis come from their own streams: generate() is unchanged."""
        before = gen.generate(CFG, 5)
        bkg = gen.generate_background(CFG, 6)
        gen.signal_xvis(CFG, 100, 7)
        np.testing.assert_array_equal(before["reco_cos"], gen.generate(CFG, 5)["reco_cos"])
        np.testing.assert_array_equal(bkg["x_vis"], gen.generate_background(CFG, 6)["x_vis"])
        self.assertEqual(bkg["meta"]["label"], "SYNTHETIC background")
        self.assertTrue(CFG["background"]["label"].startswith("SYNTHETIC"))

    def test_background_xvis_matches_the_analytic_fractions(self):
        cfg = json.loads(json.dumps(CFG))
        cfg["background"]["sigma_pb"] = 20000.0  # large sample for the comparison
        x = gen.generate_background(cfg, 11)["x_vis"]
        for lo, hi in ((0.5, 0.8), (0.8, 0.9), (0.9, 1.0)):
            f = gen.xvis_fraction(cfg, lo, hi, "background")
            obs = np.mean((x >= lo) & (x < hi))
            self.assertLess(abs(obs - f), 5 * np.sqrt(f * (1 - f) / x.size), (lo, hi))
        # Beta(2, 2): CDF 3x^2 - 2x^3
        self.assertAlmostEqual(gen.xvis_fraction(cfg, 0.9, 1.0, "background"), 1 - (3 * 0.81 - 2 * 0.729), places=12)
        self.assertAlmostEqual(gen.xvis_fraction(cfg, 0.0, 1.0, "background"), 1.0, places=12)

    def test_signal_xvis_is_inside_the_signal_region(self):
        x = gen.signal_xvis(CFG, 100000, 3)
        self.assertLess(gen.xvis_fraction(CFG, -np.inf, 0.9, "signal"), 1e-20)
        self.assertTrue(np.all(x >= 0.9))
        self.assertLess(abs(x.mean() - 1.0), 5 * CFG["background"]["x_vis"]["signal_sigma"] / np.sqrt(x.size))

    def test_generator_imports_no_theory_code(self):
        for f in (ROOT / "scripts").glob("*.py"):
            text = f.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"^\s*(from|import)\s+\S*(theory|qed)", text, re.M | re.I), f.name)
            self.assertNotIn("profiles/theory", text, f.name)


if __name__ == "__main__":
    unittest.main()

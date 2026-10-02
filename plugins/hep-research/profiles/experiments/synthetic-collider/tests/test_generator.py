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

    def test_generator_imports_no_theory_code(self):
        for f in (ROOT / "scripts").glob("*.py"):
            text = f.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"^\s*(from|import)\s+\S*(theory|qed)", text, re.M | re.I), f.name)
            self.assertNotIn("profiles/theory", text, f.name)


if __name__ == "__main__":
    unittest.main()

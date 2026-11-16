"""G4, weight quality (Part B section 8.2 note 6; phase 2)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import reweight as R  # noqa: E402


class ParetoK(unittest.TestCase):
    def test_known_tails(self):
        self.assertAlmostEqual(R.pareto_k(stats.genpareto.rvs(0.3, size=20000, random_state=1)), 0.3, delta=0.08)
        self.assertAlmostEqual(R.pareto_k(stats.genpareto.rvs(0.8, size=20000, random_state=2)), 0.8, delta=0.1)
        rng = np.random.default_rng(1)
        x = rng.normal(0, 1, 20000)
        self.assertAlmostEqual(R.pareto_k(stats.norm.pdf(x, 0, 2) / stats.norm.pdf(x)), 0.75, delta=0.1)
        x = rng.normal(0, 1.5, 20000)
        self.assertLess(R.pareto_k(stats.norm.pdf(x) / stats.norm.pdf(x, 0, 1.5)), 0.5)


class G4(unittest.TestCase):
    def test_smoothed_histogram_density_fails(self):
        """A smoothed histogram density as the proposal (single-gate isolation mode, section 15.3.1): its tails are
        wrong, the weights heavy-tailed, G4 fails; the analytic density passes."""
        rng = np.random.default_rng(3)
        s = rng.normal(0, 1, 20000)
        h, e = np.histogram(s, bins=20, range=(-3, 3), density=True)
        idx = np.clip(np.digitize(s, e) - 1, 0, 19)
        q = np.where((s > -3) & (s < 3), h[idx], 1e-6)
        bad = R.g4({"mean": stats.norm.pdf(s, 0.3, 1.2) / q}, {"mean": 1000})
        self.assertEqual(bad["status"], "failed")
        self.assertIn("g4.pareto_k", [f["code"] for f in bad["findings"]])
        good = R.g4({"mean": stats.norm.pdf(s, 0.3, 1.2) / stats.norm.pdf(s)}, {"mean": 1000})
        self.assertEqual(good["status"], "passed")

    def test_ess_requirement_and_psis_limit(self):
        w = np.ones(500)
        self.assertEqual(R.g4({"a": w}, {"a": 1000})["finding"], "g4.ess")
        self.assertEqual(R.g4({"a": np.ones(2000)}, {"a": 1000}, smoothed=True)["pareto_limit"], 0.7)


if __name__ == "__main__":
    unittest.main()

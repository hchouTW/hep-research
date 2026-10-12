"""hep-statistics audit T21: sweighted_fit.py. SYNTHETIC (the walkthrough model of test_weighted_unbinned_fit.py).
Over toys the asymptotic (Langenbruch) uncertainty matches the spread of tau_s and the bootstrap of the whole chain; the
naive weighted-Hessian error is too small and the sumw2 (sandwich) error, which ignores the sWeights' uncertainty,
is reported; the broken-factorization variant is marked invalid by the predeclared sideband check, and inflating the
error is not offered as a repair. Criteria fixed before the runs: pull width in [0.9, 1.1] (asymptotic), mean
bootstrap/asymptotic ratio within 10%, naive pull width above 1.5; invalid flagged in at least 90% of broken samples
and at most 5% of valid ones."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sweighted_fit as sw  # noqa: E402
import test_weighted_unbinned_fit as walkthrough  # noqa: E402

TOYS = 120


class SWeightedFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(20261012)
        cls.rows = []
        for _ in range(TOYS):
            m, t = walkthrough.generate(rng)
            cls.rows.append(sw.fit(m, t, 0.5, 0.05, bootstrap=60, seed=int(rng.integers(1 << 30))))
        cls.broken = []
        for _ in range(40):
            m, t = walkthrough.generate(rng, dependent=True)
            cls.broken.append(sw.fit(m, t, 0.5, 0.05, bootstrap=0))

    def test_asymptotic_matches_toys_and_bootstrap(self):
        tau = np.array([r["tau"] for r in self.rows])
        asym = np.array([r["sigma"]["asymptotic"] for r in self.rows])
        boot = np.array([r["sigma"]["bootstrap"] for r in self.rows])
        naive = np.array([r["sigma"]["naive"] for r in self.rows])
        pulls = (tau - 1.0) / asym
        self.assertTrue(0.9 <= pulls.std(ddof=1) <= 1.1, pulls.std(ddof=1))
        self.assertLess(abs(np.mean(boot / asym) - 1.0), 0.10)
        self.assertGreater(((tau - 1.0) / naive).std(ddof=1), 1.5)       # naive weighted Hessian undercovers
        self.assertLessEqual(sum(r["status"] != "ok" for r in self.rows), 0.05 * TOYS)   # false alarms on valid samples

    def test_broken_factorization_is_invalid(self):
        flagged = sum(r["status"] == "invalid" for r in self.broken)
        self.assertGreaterEqual(flagged, 0.9 * len(self.broken))
        for r in self.broken:
            if r["status"] == "invalid":
                self.assertIn("do not inflate", r["note"])

    def test_bad_input(self):
        with self.assertRaises(sw.SWeightError):
            sw.fit([0.5] * 10, [1.0] * 10, 0.5, 0.05)


if __name__ == "__main__":
    unittest.main()

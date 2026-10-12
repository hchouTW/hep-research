"""hep-statistics audit T26: quadratic (EFT-like) signal models, eft_scan.py (EXPERIMENTAL). SYNTHETIC.
nu(c) = 10 - 6c + c^2 with n = 10 has two exact solutions (c = 0 and c = 6): the 95% allowed set is two intervals, each
end equal to the root of the closed-form q(c) = 2 [nu - n - n ln(nu / n)] = 3.84 within one grid step, and never the
convex hull. A toy Neyman belt differs from Wilks between the minima (critical value well below 3.84 at c = 3) and
covers at nominal there by construction, checked with fresh toys (4 standard errors). In 2D a separable degenerate
model gives two joint components, and the 1-dof profiled intervals differ from the projections of the 2-dof joint
region."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import eft_scan as e  # noqa: E402

M1 = {"b": [10.0], "n": [10], "I": [[-6.0]], "Q": [[[1.0]]], "grid": [[-3.0, 9.0, 241]]}
STEP = 12.0 / 240


def q_closed(c, n=10.0):
    nu = 10 - 6 * c + c * c
    return 2 * (nu - n - n * math.log(nu / n))


class Eft1D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = e.scan(M1, 0.95, toys=400, seed=3)

    def test_disconnected_set_matches_closed_form(self):
        iv = self.r["allowed_intervals_wilks"]
        self.assertEqual(len(iv), 2)
        self.assertTrue(self.r["disconnected"])
        t = stats.chi2.ppf(0.95, 1)
        f = lambda c: q_closed(c) - t
        roots = [optimize.brentq(f, -3, 0), optimize.brentq(f, 0, 3), optimize.brentq(f, 3, 6), optimize.brentq(f, 6, 9)]
        for got, ref in zip([iv[0][0], iv[0][1], iv[1][0], iv[1][1]], roots):
            self.assertLess(abs(got - ref), STEP + 1e-9)
        self.assertNotIn([iv[0][0], iv[1][1]], iv)                 # no convex hull

    def test_toy_belt_differs_from_wilks_and_covers(self):
        crit = np.array(self.r["toy_belt"]["critical_values"])
        j = int(round((3.0 + 3.0) / STEP))                         # c = 3, between the two minima (nu = 1)
        self.assertLess(crit[j], 3.0)
        axis = np.linspace(-3, 9, 241)
        mesh = axis[:, None]
        rng = np.random.default_rng(11)
        ns = rng.poisson(1.0, size=(2000, 1))
        nl = np.stack([e.nll(M1, mesh, n=x) for x in ns])
        q = 2.0 * (nl[:, j] - nl.min(axis=1))
        se = math.sqrt(0.95 * 0.05 / 2000)
        # q is discrete at nu = 1: the belt cannot cover exactly 0.95; it must not undercover, and it must not be wider
        # than the discreteness forces (excluding the critical value itself drops below nominal)
        self.assertGreaterEqual(np.mean(q <= crit[j]), 0.95 - 4 * se)
        self.assertLess(np.mean(q < crit[j] - 1e-9), 0.95 + 4 * se)
        self.assertFalse(self.r["reaches_grid_edge"])


class Eft2D(unittest.TestCase):
    def test_two_components_and_profiled_vs_joint(self):
        m = {"b": [10.0, 20.0], "n": [10, 20], "I": [[-6.0, 0.0], [0.0, 3.0]],
             "Q": [[[1.0, 0.0], [0.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]]], "grid": [[-3.0, 9.0, 121], [-6.0, 6.0, 121]]}
        r = e.scan(m, 0.95)
        self.assertFalse(r["reaches_grid_edge"])
        narrow = e.scan(dict(m, grid=[[-3.0, 9.0, 121], [-3.0, 3.0, 61]]), 0.95)
        self.assertTrue(narrow["reaches_grid_edge"])                # a grid-limited set is flagged
        self.assertEqual(r["joint_region_components"], 2)
        self.assertEqual(len(r["profiled_intervals"][0]), 2)
        prof, proj = r["profiled_intervals"][1][0], r["joint_projection_intervals"][1][0]
        self.assertLess(proj[0], prof[0])                          # the 2-dof joint region projects wider
        self.assertGreater(proj[1], prof[1])

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            e.scan(dict(M1, grid=[[0, 1, 5], [0, 1, 5]]))


if __name__ == "__main__":
    unittest.main()

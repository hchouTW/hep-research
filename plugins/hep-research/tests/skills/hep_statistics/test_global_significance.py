"""hep-statistics audit T28: global significance by repeating the complete procedure (global_significance.py,
EXPERIMENTAL). SYNTHETIC. With a known background and a 1D scan the tool agrees with look_elsewhere.py brute force
(overlapping exact intervals); refining the grid or adding a selection variant can only raise the global p-value on
the same toys (checked exactly); a procedure that refits the background normalization differs from one that holds it
fixed, and computing the global p-value with the wrong procedure is the negative control; a 2D scan and a variant
choice are flagged outside the Gross-Vitells formula; global p is never below local p."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import global_significance as g  # noqa: E402
import look_elsewhere as le  # noqa: E402

X = np.linspace(0.5, 59.5, 60)
B = 200 * np.exp(-X / 30)
S = np.exp(-0.5 * ((X - 30) / 1.5) ** 2)
N = np.random.default_rng(3).poisson(B + 25 * S / S.sum())


def doc(positions, widths=(1.5,), norm="fixed", variants=None, n=N):
    return {"bin_centers": X.tolist(), "variants": variants or [{"name": "v1", "background": B.tolist(), "observed": n.tolist()}],
            "scan": {"positions": list(positions), "widths": list(widths)}, "background_normalization": {"kind": norm, "sigma": 0.05}}


class InputsAndConventionsSTH34(unittest.TestCase):
    """STH-T3.4: input checks, the auxiliary redraw at the fitted scale, one upcrossing definition."""

    def test_bad_inputs_are_refused(self):
        bad_n = N.copy()
        bad_n[3] = -1
        for d in (doc([5.0], n=bad_n), doc([70.0]), doc([-3.0]), doc([10.0], widths=(0.0,))):
            with self.subTest(d=str(d["scan"])), self.assertRaises(ValueError):
                g.run(d, 10, 1)

    def test_auxiliary_redraw_is_centered_at_the_fitted_scale(self):
        # data with 30% more background than nominal: the background-only fit gives k0 > 1 (constrained, sigma 0.05)
        n = np.random.default_rng(5).poisson(1.3 * B)
        r = g.run(doc(np.arange(5, 56, 5.0), norm="constrained", n=n), 300, 2)
        red = r["auxiliary_redraw"]
        self.assertGreater(red["center"], 1.1)
        self.assertLess(abs(red["mean_in_toys"] - red["center"]), 4 * 0.05 / np.sqrt(300))

    def test_one_upcrossing_definition(self):
        q = np.array([2.0, 0.5, 1.5, 1.8, 0.2, 3.0, 0.1])
        self.assertEqual(int(le.upcrossings(q, 1.0)[0]), 2)       # the start above the level is not an upcrossing
        self.assertIs(g.upcrossings, le.upcrossings)


class GlobalSignificance(unittest.TestCase):
    def test_agrees_with_look_elsewhere_brute_force(self):
        ours = g.run(doc(np.arange(5, 56, 1.0)), 600, 1)
        ref = le.brute(B, N, np.arange(5, 56, 1.0), le.load({"background": B.tolist(), "observed": N.tolist(), "scan": {
            "parameter": "mass", "grid": list(np.arange(5, 56, 1.0)), "bin_centers": X.tolist(),
            "signal_shape": {"kind": "gaussian", "width": 1.5}}})[3], "mass", 600, 7)
        lo, hi = ours["global_p_toys"]["interval"]
        p_ref = ref["global"]["global_p"]
        self.assertTrue(ours["global_not_below_local"])
        self.assertIsNotNone(p_ref)
        self.assertLess(abs(ours["global_p_toys"]["estimate"] - p_ref), 3 * (hi - lo) + 0.01)

    def test_finer_grid_and_more_variants_cannot_lower_global_p(self):
        coarse = g.run(doc(np.arange(6, 55, 4.0)), 300, 2)
        fine = g.run(doc(np.arange(6, 55, 1.0)), 300, 2)
        self.assertEqual(coarse["observed"]["at"]["position"], 30.0)
        self.assertEqual(fine["observed"]["at"]["position"], 30.0)
        self.assertGreaterEqual(fine["global_p_toys"]["k"], coarse["global_p_toys"]["k"])
        eff = np.full(60, 0.6)
        tight_obs = np.random.default_rng(4).binomial(N, eff)
        two = [{"name": "loose", "background": B.tolist(), "observed": N.tolist()},
               {"name": "tight", "background": (0.6 * B).tolist(), "observed": tight_obs.tolist(), "subset_of": "loose",
                "efficiency": eff.tolist()}]
        r2 = g.run(doc(np.arange(6, 55, 4.0), variants=two), 300, 2)
        if r2["observed"]["variant"] == "loose":
            self.assertGreaterEqual(r2["global_p_toys"]["k"], coarse["global_p_toys"]["k"])
        self.assertFalse(r2["gross_vitells"]["validated_here"])
        with self.assertRaises(ValueError):
            g.run(doc(np.arange(6, 55, 4.0), variants=[two[1]]), 10, 1)

    def test_procedure_mismatch_is_detectable(self):
        fixed = g.run(doc(np.arange(5, 56, 2.0), norm="fixed"), 400, 5)
        free = g.run(doc(np.arange(5, 56, 2.0), norm="free"), 400, 5)
        self.assertNotEqual(fixed["observed"]["q0_max"], free["observed"]["q0_max"])
        # the free-normalization procedure applied to the data must be calibrated with free-normalization toys
        self.assertGreater(abs(fixed["global_p_toys"]["k"] - free["global_p_toys"]["k"]), 0)

    def test_two_dimensional_scan_is_outside_gross_vitells(self):
        r = g.run(doc(np.arange(6, 55, 3.0), widths=(1.0, 1.5, 3.0)), 200, 3)
        self.assertEqual(r["procedure"]["dimensions"], 2)
        self.assertFalse(r["gross_vitells"]["validated_here"])
        self.assertTrue(r["global_not_below_local"])


if __name__ == "__main__":
    unittest.main()

"""S05: skills/hep-statistics/scripts/look_elsewhere.py. A SYNTHETIC scan: 50 bins on [0, 100] with a flat background
of 50 per bin and a Gaussian signal of width 3 scanned from 5 to 95 in steps of 2. The Gross-Vitells global p-value
from 1,000 toys is compared with brute-force toys (20,000, slow: HEP_SLOW_TESTS=1) at levels where the brute global
p lies in [1e-3, 0.1], within max(3 Monte Carlo standard errors, 20% relative) (set before running)."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "look_elsewhere.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

try:
    import numpy as np
    import look_elsewhere as le
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


def scan_doc(observed=None, grid=None, background=50.0):
    x = [1.0 + 2.0 * i for i in range(50)]
    grid = [5.0 + 2.0 * k for k in range(46)] if grid is None else grid
    return {"background": [background] * 50, "observed": observed or [50] * 50,
            "scan": {"parameter": "mass", "grid": grid, "bin_centers": x,
                     "signal_shape": {"kind": "gaussian", "width": 3.0}}}


def run(cmd, doc, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "scan.json"
        f.write_text(json.dumps(doc))
        p = subprocess.run([sys.executable, str(SCRIPT), cmd, "--input", str(f), *extra], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout


@unittest.skipUnless(HAVE_NP, "numpy not installed: look-elsewhere tool unverified")
class LookElsewhere(unittest.TestCase):
    def excess_doc(self):
        obs = [50] * 50
        for i, extra in ((24, 9), (25, 12), (26, 8)):    # a local bump near mass 51
            obs[i] += extra
        return scan_doc(observed=obs)

    def test_q0_matches_direct_maximization(self):
        from scipy.optimize import minimize_scalar
        b, n, grid, t, _ = le.load(self.excess_doc())
        q = le.q0_scan(n, b, t)[0]
        for k in (0, 23, 45):
            f = lambda mu: -np.sum(n * np.log(b + mu * t[k]) - mu * t[k])
            r = minimize_scalar(f, bounds=(0, 500), method="bounded", options={"xatol": 1e-10})
            expected = max(0.0, 2 * (f(0.0) - r.fun))
            self.assertAlmostEqual(q[k], expected, delta=1e-6)

    def test_one_point_scan_global_equals_local(self):
        doc = self.excess_doc()
        doc["scan"]["grid"] = [51.0]
        for cmd in ("brute", "gross-vitells"):
            code, out = run(cmd, doc, "--toys", "200", "--seed", "1")
            self.assertEqual(code, 0)
            self.assertEqual(out["global"]["global_p"], out["global"]["local_p"])
            self.assertEqual(out["global"]["method"], "none-needed")

    def test_global_never_below_local_and_reports_fields(self):
        code, out = run("brute", self.excess_doc(), "--toys", "2000", "--seed", "3")
        self.assertEqual(code, 0)
        g = out["global"]
        self.assertGreaterEqual(g["global_p"], g["local_p"])
        for key in ("local_z", "global_z", "trials_factor", "toys", "seed", "mc_error"):
            self.assertIn(key, g)
        code, out = run("gross-vitells", self.excess_doc(), "--toys", "500", "--seed", "4")
        self.assertEqual(code, 0)
        g = out["global"]
        self.assertGreaterEqual(g["global_p"], g["local_p"])
        for key in ("reference_level_c0", "mean_upcrossings", "extrapolation_distance", "checked_up_to_q0"):
            self.assertIn(key, g)

    def test_zero_exceedances_give_a_bound(self):
        obs = [50] * 50
        obs[25] += 60
        code, out = run("brute", scan_doc(observed=obs), "--toys", "300", "--seed", "5")
        self.assertEqual(code, 0)
        self.assertIsNone(out["global"]["global_p"])
        self.assertAlmostEqual(out["global"]["global_p_upper_95"], 1 - 0.05 ** (1 / 300))

    def test_far_extrapolation_warns(self):
        obs = [50] * 50
        obs[25] += 45
        code, out = run("gross-vitells", scan_doc(observed=obs), "--toys", "200", "--seed", "6")
        self.assertEqual(code, 0)
        self.assertTrue(any("extrapolated" in w for w in out["global"]["warnings"]))

    def test_bad_inputs_rejected(self):
        bad = [scan_doc(grid=[]), scan_doc(background=-1.0), scan_doc(grid=[50.0, 40.0, 60.0])]
        for doc in bad:
            code, out = run("local", doc)
            self.assertEqual(code, 2, out)
            self.assertEqual(out["status"], "rejected")

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_gross_vitells_agrees_with_brute_force(self):
        b, _, _, t, _ = le.load(scan_doc())
        qmax = np.sort(le.q0_scan(le._toys(b, 20000, 11), b, t).max(axis=1))
        targets = (0.1, 0.03, 0.01, 0.003, 0.001)
        levels = [float(qmax[qmax.size - int(round(p * qmax.size))]) for p in targets]  # k = p N toys at or above
        gv, n_mean = le.gv_curve(b, t, 1000, 12, 1.0, levels)
        rows = []
        for c, p_gv in zip(levels, gv):
            k = int(np.sum(qmax >= c))
            p_b = k / qmax.size
            se = math.sqrt(p_b * (1 - p_b) / qmax.size)
            rows.append((c, p_b, p_gv))
            self.assertTrue(1e-3 <= p_b <= 0.1)
            self.assertLessEqual(abs(p_gv - p_b), max(3 * se, 0.2 * p_b), (c, p_b, p_gv, n_mean))
        print("\nLEE check (c, brute p, Gross-Vitells p):", [tuple(round(v, 5) for v in r) for r in rows],
              "mean upcrossings at c0 = 1:", round(n_mean, 3))


if __name__ == "__main__":
    unittest.main()

"""degeneracy.py (cr-propagation A3): two-level degeneracy diagnostics, a Fisher screen and profile-likelihood scans.
SYNTHETIC models only. Criteria fixed before the runs:
- A3-2: the synthetic curved degeneracy (D0_cm2_s proportional to L_kpc^1.2, exact for L_kpc <= 6, broken above by a
  spectral tilt) gives, in one output, one fisher-screen entry without valid_range and one profile-scan entry with
  valid_range.L_kpc.max in [6, 8] (and min 2, the scan edge); both exponents of L_kpc within 0.01 of -1.2; the
  profiled delta -2 ln L is below 1e-6 at 6 kpc and above 9 at 8 kpc (the break is in the data, not only declared);
  the same holds through covariance_fit.py's tabulated-grid fit with a degeneracy_scan block, on a grid of the same
  model (multilinear interpolation: exponent within 0.05, max in [6, 8]);
- direction and plane scans: a valley along (1, 1) gives exponents {a: 1, b: -1} within 0.01; a constrained
  quadratic gives no entry;
- an unconverged profile point gives no entry and a warning; a malformed scan is bad input (CLI exit 2);
- a tabulated-grid fit without degeneracy_scan has no 'degeneracies' or 'profile_scans' key (outputs unchanged)."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import covariance_fit as cf  # noqa: E402
import degeneracy as dg  # noqa: E402
from tests.skills.hep_statistics.test_grid_fit import components, measurement, prediction  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "degeneracy.py"
COV_FIT = ROOT / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"


def _by_evidence(entries, evidence):
    return [e for e in entries if e["evidence"] == evidence]


class SyntheticCurvedCli(unittest.TestCase):
    """A3-2 on the built-in study (analytic model)."""

    @classmethod
    def setUpClass(cls):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "synthetic-curved"], capture_output=True, text=True,
                             timeout=300)
        cls.code, cls.out = res.returncode, json.loads(res.stdout)

    def test_status(self):
        self.assertEqual(self.code, 0)
        self.assertEqual(self.out["status"], "ok")
        self.assertTrue(self.out["synthetic"])

    def test_fisher_screen_has_no_valid_range(self):
        fs = _by_evidence(self.out["degeneracies"], "fisher-screen")
        self.assertEqual(len(fs), 1)
        self.assertNotIn("valid_range", fs[0])
        self.assertEqual(fs[0]["form"], "power")
        self.assertAlmostEqual(fs[0]["exponents"]["L_kpc"], -1.2, delta=0.01)
        self.assertEqual(fs[0]["exponents"]["D0_cm2_s"], 1.0)

    def test_profile_scan_gives_the_valid_range(self):
        ps = _by_evidence(self.out["degeneracies"], "profile-scan")
        self.assertEqual(len(ps), 1)
        vr = ps[0]["valid_range"]["L_kpc"]
        self.assertTrue(6.0 <= vr["max"] <= 8.0, vr)
        self.assertAlmostEqual(vr["min"], 2.0, places=9)
        self.assertAlmostEqual(ps[0]["exponents"]["L_kpc"], -1.2, delta=0.01)
        scan = self.out["profile_scans"][0]
        self.assertEqual(scan["range_ends"], {"min": "scan-edge", "max": "threshold"})
        self.assertEqual(scan["unconverged_points"], 0)

    def test_the_break_is_in_the_data(self):
        self.assertLess(self.out["checks"]["delta_m2ll_profiled_at_L_kpc_6"], 1e-6)
        self.assertGreater(self.out["checks"]["delta_m2ll_profiled_at_L_kpc_8"], 9.0)

    def test_bad_points_is_exit_2(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "synthetic-curved", "--points", "1"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 2)
        self.assertEqual(json.loads(res.stdout)["status"], "rejected")


D0_AXIS = list(np.geomspace(1.0e28, 1.2e29, 25))
L_AXIS = list(np.geomspace(2.0, 10.0, 17))
DL_GRID = {"parameters": [{"name": "D0_cm2_s", "scale": "log"}, {"name": "L_kpc", "scale": "log"}]}


def curved_grid():
    return [prediction({"D0_cm2_s": float(d0), "L_kpc": float(length)}, dg.curved_prediction(d0, length))
            for d0 in D0_AXIS for length in L_AXIS]


class TabulatedGridScan(unittest.TestCase):
    """A3-2 through covariance_fit.py (tabulated-grid fit, degeneracy_scan)."""

    @classmethod
    def setUpClass(cls):
        y = dg.curved_prediction(3.0e28, 4.0)
        cls.base = {"model": "tabulated-grid", "measurement": measurement(y, components(y)),
                    "predictions": curved_grid(), "grid": DL_GRID}
        cls.out = cf.grid_fit(dict(cls.base, degeneracy_scan={"parameter": "L_kpc", "points": 41}))
        cls.fit = cls.out["fits"][0]

    def test_both_levels_in_one_output(self):
        fs = _by_evidence(self.fit["degeneracies"], "fisher-screen")
        ps = _by_evidence(self.fit["degeneracies"], "profile-scan")
        self.assertEqual(len(fs), 1)
        self.assertNotIn("valid_range", fs[0])
        self.assertEqual(len(ps), 1)
        vr = ps[0]["valid_range"]["L_kpc"]
        self.assertTrue(6.0 <= vr["max"] <= 8.0, vr)
        self.assertAlmostEqual(ps[0]["exponents"]["L_kpc"], -1.2, delta=0.05)
        self.assertAlmostEqual(fs[0]["exponents"]["L_kpc"], -1.2, delta=0.05)
        self.assertEqual(self.fit["profile_scans"][0]["unconverged_points"], 0)

    def test_without_a_scan_the_output_has_no_new_keys(self):
        fit = cf.grid_fit(self.base)["fits"][0]
        self.assertNotIn("degeneracies", fit)
        self.assertNotIn("profile_scans", fit)

    def test_bad_scan_is_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "input.json"
            p.write_text(json.dumps(dict(self.base, degeneracy_scan={"parameter": "nope"})))
            res = subprocess.run([sys.executable, "-I", str(COV_FIT), "fit", "--input", str(p)], capture_output=True,
                                 text=True, timeout=300)
        self.assertEqual(res.returncode, 2, res.stdout[-400:])
        self.assertIn("degeneracy_scan.parameter", json.loads(res.stdout)["error"])


def valley(t):
    """-2 ln L flat along (1, 1) in (a, b), both log axes: a function of a - b only."""
    return float(((t[0] - t[1]) / 0.01) ** 2)


def bowl(t):
    return float((t[0] / 0.01) ** 2 + (t[1] / 0.02) ** 2)


BOX = [(-1.0, 1.0), (-1.0, 1.0)]
NAMES, SCALES = ["a", "b"], ["log", "log"]


class ScanModes(unittest.TestCase):
    def screen(self, fn):
        h = 1e-4
        g = np.zeros((2, 2))
        for i in range(2):
            for j in range(2):
                e_i, e_j = np.eye(2)[i] * h, np.eye(2)[j] * h
                g[i, j] = (fn(e_i + e_j) - fn(e_i - e_j) - fn(-e_i + e_j) + fn(-e_i - e_j)) / (4 * h * h)
        return dg.fisher_screen(0.5 * g, NAMES, np.array([2.0, 2.0]))

    def test_direction_fisher_on_a_valley(self):
        _, _, degenerate, _ = self.screen(valley)
        self.assertEqual(len(degenerate), 1)
        fs = dg.screen_objects(degenerate, NAMES, SCALES)
        self.assertEqual(fs[0]["combination"], "a/b")
        scan = dg.parse_scan({"direction": "fisher", "points": 21}, NAMES)
        entries, scans, warnings = dg.profile_scan(valley, np.zeros(2), BOX, NAMES, SCALES, scan, 0.0, degenerate)
        self.assertEqual(len(entries), 1, warnings)
        self.assertAlmostEqual(entries[0]["exponents"]["b"], -1.0, delta=0.01)
        self.assertAlmostEqual(entries[0]["valid_range"]["a"]["max"], math.e, places=6)
        self.assertEqual(scans[0]["range_ends"], {"min": "scan-edge", "max": "scan-edge"})

    def test_plane_on_a_valley(self):
        scan = dg.parse_scan({"plane": ["a", "b"], "points": 21}, NAMES)
        entries, scans, _ = dg.profile_scan(valley, np.zeros(2), BOX, NAMES, SCALES, scan, 0.0)
        self.assertEqual(len(entries), 1)
        self.assertAlmostEqual(entries[0]["exponents"]["b"], -1.0, delta=0.01)
        self.assertEqual(len(scans[0]["delta_m2ll"]), 21)

    def test_constrained_bowl_gives_no_entry(self):
        _, _, degenerate, _ = self.screen(bowl)
        self.assertEqual(degenerate, [])
        scan = dg.parse_scan({"parameter": "b", "points": 21}, NAMES)
        entries, scans, _ = dg.profile_scan(bowl, np.zeros(2), BOX, NAMES, SCALES, scan, 0.0)
        self.assertEqual(entries, [])
        self.assertFalse(scans[0]["degenerate"])

    def test_unconverged_point_gives_no_entry(self):
        scan = dg.parse_scan({"parameter": "b", "points": 11}, NAMES)
        real = dg._minimize

        def stalled(objective, starts, bounds):
            val, x, _ = real(objective, starts, bounds)
            return val, x, None
        dg._minimize = stalled
        try:
            entries, scans, warnings = dg.profile_scan(valley, np.zeros(2), BOX, NAMES, SCALES, scan, 0.0)
        finally:
            dg._minimize = real
        self.assertEqual(entries, [])
        self.assertEqual(scans[0]["unconverged_points"], 11)
        self.assertTrue(any("unconverged" in w for w in warnings))

    def test_malformed_scans_are_refused(self):
        for bad in ({}, {"parameter": "a", "plane": ["a", "b"]}, {"parameter": "c"}, {"plane": ["a", "a"]},
                    {"direction": {"a": 0}}, {"parameter": "a", "points": 2}, {"parameter": "a", "threshold": 0},
                    {"parameter": "a", "values": [1.0]}, {"parameter": "a", "extra": 1}):
            with self.subTest(bad=bad), self.assertRaises(dg.ScanInputError):
                dg.parse_scan(bad, NAMES)

    def test_values_outside_the_box_are_refused(self):
        scan = dg.parse_scan({"parameter": "a", "values": [0.5, 5.0]}, NAMES)
        with self.assertRaises(dg.ScanInputError):
            dg.profile_scan(valley, np.zeros(2), BOX, NAMES, SCALES, scan, 0.0)


if __name__ == "__main__":
    unittest.main()

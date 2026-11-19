"""F-XREF-2, CHK-AT-08-05: the control interval at --cl is under "interval", with "interval_cl" beside it.

A regression test for the key the fix adds (not an evidence node: the parent has no such key). Expected values:
scipy.stats.binomtest(k, n).proportion_ci(method="exact"), a third-party Clopper-Pearson; skipped without scipy.
Tolerance 1e-9 absolute on interval ends (core's beta quantiles and scipy's agree to 5e-13). Inputs are SYNTHETIC.
"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"
TOL = 1e-9

try:
    from scipy.stats import binomtest
except ImportError:  # pragma: no cover
    binomtest = None


@unittest.skipIf(binomtest is None, "scipy is the oracle")
class ControlIntervalKey(unittest.TestCase):
    def test_interval_at_cl_and_empty_bin(self):
        with tempfile.TemporaryDirectory() as d:
            control_csv = Path(d) / "ctrl.csv"
            with control_csv.open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["rig", "truth", "reco"])
                for i in range(300):  # bin 1: 7 wrong of 300; bin 2 empty (SYNTHETIC)
                    w.writerow([5, "negative", "positive" if i < 7 else "negative"])
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "control", "--data", str(control_csv),
                                "--edges", "1", "10", "100", "--bin-column", "rig", "--true-sign-column", "truth",
                                "--reco-sign-column", "reco", "--cl", "0.95"],
                               capture_output=True, text=True, timeout=300)
        self.assertIn(p.returncode, (0, 1), p.stdout + p.stderr)
        out = json.loads(p.stdout)
        first, empty = out["bins"]
        ci = binomtest(7, 300).proportion_ci(confidence_level=0.95, method="exact")
        self.assertEqual(first["interval_cl"], 0.95)
        self.assertAlmostEqual(first["interval"][0], float(ci.low), delta=TOL)
        self.assertAlmostEqual(first["interval"][1], float(ci.high), delta=TOL)
        self.assertIsNone(empty["interval"])
        self.assertIsNone(empty["interval_68"])


if __name__ == "__main__":
    unittest.main()

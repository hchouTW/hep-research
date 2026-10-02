"""T24 (journey J6): published-data comparison via a SYNTHETIC dataset record; no detector module is read."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "published-comparison" / "run_t24.py"
PRED = json.loads((PLUGIN / "profiles" / "theory" / "qed-benchmark" / "predictions" / "sqrt_s_10gev.json").read_text())

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy and scipy are required (D5 environment)")
class T24Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "t24"
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True)
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes(self):
        self.assertEqual(self.proc.returncode, 0, self.r["pass"])

    def test_no_detector_module_or_profile_file_read(self):
        self.assertEqual(self.r["detector_files_read"], [])
        self.assertFalse(any(f.startswith("profiles/experiments/") for f in self.r["files_read"]))
        self.assertIn("examples/published-comparison/synthetic-published-record.json", self.r["files_read"])

    def test_gate_transformations_declared(self):
        self.assertEqual(self.r["gate_transformations"], ["level-identification", "fiducial-restriction"])

    def test_T08_conversion_independently_checked(self):
        # the restricted prediction integrates to the theory profile's own fiducial cross section
        self.assertAlmostEqual(self.r["fiducial_prediction_pb"], PRED["sigma_fiducial_pb"], places=9)
        self.assertEqual(self.r["edges"][0], -0.9)
        self.assertEqual(self.r["edges"][-1], 0.9)

    def test_limitation_on_multiplicative_covariance_reported(self):
        self.assertIn("Peelle", (self.out / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()

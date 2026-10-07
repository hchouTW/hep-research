"""Regressions for skills/hep-statistics/scripts/combine_measurements.py: --help, missing numpy, bin counts and
cross blocks that contradict the declared correlations. All fixtures are SYNTHETIC."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "combine_measurements.py"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(SCRIPT.parent))

try:
    import numpy  # noqa: F401
    HAVE_NP = True
except ImportError:
    HAVE_NP = False

EDGES = [-1.0, -0.5]
ASSUME = {"justification": "synthetic test assumption", "scope": "this test only"}
OBS = {"quantity": "differential-cross-section", "variables": [{"name": "x", "unit": "1", "edges": EDGES}],
       "phase_space": {"definition": "synthetic", "fiducial": False}, "level": "parton", "frame": "rest",
       "normalization": {"kind": "integrated-luminosity", "value": "not-applicable"}, "bin_semantics": "bin-averaged",
       "unit": "pb", "conventions": {"energy_variable": "sqrt_s"}}
NO_NUMPY = "import runpy, sys; sys.modules['numpy'] = None; sys.argv = [sys.argv[1]] + sys.argv[2:]; runpy.run_path(sys.argv[0], run_name='__main__')"


def doc(cov, correlation):
    ds = [{"id": i, "observable": OBS, "covariance": "present", "auxiliary": [], "uncertainties": [], "values": [10.0]}
          for i in ("alpha:A", "beta:B")]
    return {"datasets": ds, "correlations": [dict({"between": ["alpha:A", "beta:B"], "assumption": ASSUME}, **correlation)],
            "joint_covariance": cov}


class CliTests(unittest.TestCase):
    def test_help_exits_zero(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("generalized least squares", proc.stdout)

    def test_help_works_without_numpy(self):
        proc = subprocess.run([sys.executable, "-c", NO_NUMPY, str(SCRIPT), "--help"], capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("generalized least squares", proc.stdout)

    def test_missing_numpy_is_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "in.json"
            p.write_text(json.dumps(doc([[1.0, 0.0], [0.0, 1.0]], {"independent": True})), encoding="utf-8")
            proc = subprocess.run([sys.executable, "-c", NO_NUMPY, str(SCRIPT), str(p)], capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertIn("numpy is required", json.loads(proc.stdout)["error"])


@unittest.skipUnless(HAVE_NP, "numpy not installed")
class GlsInputTests(unittest.TestCase):
    def test_unequal_bin_counts_rejected_clearly(self):
        import combine_measurements as cm
        with self.assertRaisesRegex(ValueError, "same number of bins"):
            cm.gls([[1.0, 2.0], [1.0]], [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]])

    def test_declared_independent_with_nonzero_cross_block_refused(self):
        import combine_measurements as cm
        r = cm.combine(doc([[1.0, 0.5], [0.5, 1.0]], {"independent": True}))
        self.assertEqual(r["status"], "refused", r)
        self.assertIn("declared independent", r["reason"])

    def test_declared_correlation_with_zero_cross_block_refused(self):
        import combine_measurements as cm
        r = cm.combine(doc([[1.0, 0.0], [0.0, 1.0]], {"source": "alpha:norm"}))
        self.assertEqual(r["status"], "refused", r)
        self.assertIn("cross block is zero", r["reason"])

    def test_consistent_declarations_still_combine(self):
        import combine_measurements as cm
        self.assertEqual(cm.combine(doc([[1.0, 0.0], [0.0, 1.0]], {"independent": True}))["status"], "combined")
        self.assertEqual(cm.combine(doc([[1.0, 0.3], [0.3, 1.0]], {"source": "alpha:norm"}))["status"], "combined")


if __name__ == "__main__":
    unittest.main()

"""Example E-1 (B/C with fragmentation feed-down): SYNTHETIC chain M4 -> D4 -> D2 -> forward folding. Reproduction
against the committed output and every pre-declared criterion: B/C pulls over 400 toys with |mean| < 0.2 and width
0.85-1.15; a fixed subtraction from a carbon model 15% low biases B/C measurably and its spec is flagged
coupled.fixed_subtraction; the fold equals the block matrix; a planted double count is caught."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "bc-fragmentation" / "run.py"
try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


@unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
class BcFragmentationExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("bc_fragmentation_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["bc_fragmentation_run"] = cls.mod
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", cls.tmp.name])
        cls.r = json.loads((Path(cls.tmp.name) / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_pulls_and_control(self):
        for m in self.r["pull_mean"]:
            self.assertLess(abs(m), 0.2)
        for w in self.r["pull_width"]:
            self.assertTrue(0.85 < w < 1.15, w)
        self.assertGreater(self.r["fixed_subtraction_bias_combined_sigmas"], 5)
        rev = self.r["checks"]["m4_review"]
        self.assertEqual(rev["spec_fixed_subtraction.json"]["coupled_warnings"], ["coupled.fixed_subtraction"])
        self.assertEqual(rev["spec_joint_fit.json"]["coupled_warnings"], [])

    def test_reproduces_committed_output(self):
        committed = (SCRIPT.parent / "output" / "results.json").read_bytes()
        self.assertEqual((Path(self.tmp.name) / "results.json").read_bytes(), committed)

    def test_synthetic_everywhere(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        for f in (Path(self.tmp.name) / "artifacts").glob("spec_*.json"):
            self.assertIn("synthetic", json.dumps(json.loads(f.read_text(encoding="utf-8"))["status"]), f.name)
        self.assertIn("SYNTHETIC", (Path(self.tmp.name) / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

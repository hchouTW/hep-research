"""Example E-3, first part (multi-era fit): SYNTHETIC two-era chain D7 -> C1 -> M1 -> D9 -> D5 -> S1 -> S6.
Reproduction against the committed output, every pre-declared criterion (joint-fit coverage 0.68 +- 0.03, S1 passes
without a difference and catches an injected offset, partial + merge = single run, a period split across files counted
once, fold of the mix = sum of the era folds, under 60 s) and synthetic labels."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "multi-era-fit" / "run.py"
try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


@unittest.skipUnless(HAVE_NUMPY, "numpy is not installed")
class MultiEraFitExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("multi_era_fit_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["multi_era_fit_run"] = cls.mod
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

    def test_coverage_and_split_checks(self):
        self.assertLessEqual(abs(self.r["coverage_1sigma"] - 0.68), 0.03)
        self.assertEqual(self.r["checks"]["s1_nominal"]["exit"], 0)
        self.assertEqual(self.r["checks"]["s1_offset"]["exit"], 1)
        self.assertIn("shared systematic uncertainties not subtracted", " ".join(self.r["checks"]["s1_nominal"]["warnings"]))

    def test_reproduces_committed_output(self):
        committed = (SCRIPT.parent / "output" / "results.json").read_bytes()
        self.assertEqual((Path(self.tmp.name) / "results.json").read_bytes(), committed)

    def test_synthetic_everywhere(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        for f in (Path(self.tmp.name) / "artifacts").glob("*.json"):
            self.assertIn("synthetic", json.dumps(json.loads(f.read_text(encoding="utf-8"))["status"]), f.name)
        self.assertIn("SYNTHETIC", (Path(self.tmp.name) / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

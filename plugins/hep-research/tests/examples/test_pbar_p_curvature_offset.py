"""Example E-2 (antiproton-to-proton ratio with a curvature offset): SYNTHETIC chain D1 -> M5 ledger -> covariance_fit.
Reproduction against the committed output and every pre-declared criterion: the ratio shift equals the difference of
the signed shifts (r (1 + s_p) = s_pbar - s_p), the two shifts have opposite signs and add in magnitude, the M5 ledger
entry validates against the measurement-spec schema, and the injected offset is recovered within 3 sigma by the
likelihood fit of the double ratio (and measured at 5 sigma or more). Synthetic labels throughout."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "pbar-p-curvature-offset" / "run.py"
try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "numpy and scipy are not installed")
class PbarPCurvatureOffsetExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("pbar_p_offset_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["pbar_p_offset_run"] = cls.mod
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

    def test_recovered_offset(self):
        fit = self.r["checks"]["fit"]
        self.assertLess(abs(fit["pull"]), 3.0)
        self.assertGreater(abs(fit["delta_hat"]) / fit["delta_error"], 5.0)

    def test_reproduces_committed_output(self):
        for name in ("results.json", "systematics_ledger.json"):
            committed = (SCRIPT.parent / "output" / name).read_bytes()
            self.assertEqual((Path(self.tmp.name) / name).read_bytes(), committed, name)

    def test_synthetic_labels(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        self.assertIn("SYNTHETIC", (Path(self.tmp.name) / "report.md").read_text(encoding="utf-8"))
        self.assertIn("unverified", self.r["checks"]["advisory_ratio_subset_v1"])


if __name__ == "__main__":
    unittest.main()

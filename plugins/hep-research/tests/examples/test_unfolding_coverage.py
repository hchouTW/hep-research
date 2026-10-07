"""examples/unfolding-coverage: executed unfolding, bias and coverage per regularization.
SYNTHETIC. The committed output is reproduced within a tolerance, the criteria pass, and they would fail for a
biased inversion."""
import contextlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "unfolding-coverage" / "run.py"

try:
    import numpy as np
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def load():
    spec = importlib.util.spec_from_file_location("unfolding_coverage_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["unfolding_coverage_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def close(a, b, path=""):
    """Mismatches between two JSON documents; numbers compared with rtol 1e-4 and atol 1e-9 (6 significant digits
    are written, so the last digit may differ across platforms)."""
    if isinstance(a, dict):
        if set(a) != set(b):
            return [f"{path}: keys differ"]
        return [m for k in a for m in close(a[k], b[k], f"{path}/{k}")]
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: lengths differ"]
        return [m for i, (x, y) in enumerate(zip(a, b)) for m in close(x, y, f"{path}/{i}")]
    if isinstance(a, (int, float)) and not isinstance(a, bool):
        return [] if math.isclose(a, b, rel_tol=1e-4, abs_tol=1e-9) else [f"{path}: {a} != {b}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


@unittest.skipUnless(HAVE_DEPS, "numpy is required (D5 environment)")
class UnfoldingCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load()
        cls.td = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", cls.td.name])
        cls.res = json.loads((Path(cls.td.name) / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def test_criteria_pass_and_output_is_reproduced(self):
        self.assertEqual(self.code, 0, self.res["criteria"])
        committed = json.loads((SCRIPT.parent / "output" / "results.json").read_text())
        self.assertEqual(close(committed, self.res), [])
        self.assertIn("SYNTHETIC", self.res["label"])

    def test_regularization_undercovers_and_inversion_covers(self):
        by = {s["setting"]: s for s in self.res["settings"]}
        inv = by["inversion (TSVD, all 10 singular values)"]["model_truth"]
        self.assertGreater(inv["min_coverage_68"], 0.6827 - 4 * self.res["coverage_standard_error"])
        self.assertLess(by["Tikhonov 1e-1"]["model_truth"]["min_coverage_68"], 0.5)

    def test_criteria_fail_for_a_biased_inversion(self):
        orig = self.mod.linear_matrix

        def biased(method, param, r, mu_w):
            a = np.array(orig(method, param, r, mu_w))
            return (a * 1.02).tolist() if method == "tsvd" and param == 10 else a.tolist()

        self.mod.linear_matrix = biased
        try:
            res = self.mod.run(1000, 1)
        finally:
            self.mod.linear_matrix = orig
        self.assertFalse(res["criteria"]["inversion_unbiased"])
        self.assertFalse(res["passed"])


if __name__ == "__main__":
    unittest.main()

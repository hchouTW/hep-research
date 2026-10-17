"""S10: adapters/unfolding (pyunfold, RooUnfold through ROOT when present) with the plugin's own validation.
Without pyunfold: exit 3 with an install hint; RooUnfold absent: exit 3 (made deterministic by hiding the packages).
With pyunfold (local recorded run; CI has no job for it): agreement with core/stats/unfolding_diagnostics.py
dagostini-unfold for up to 60 bins (61 refused), nominal and reweighted closure, stress tests, toy coverage, and a
validation that fails (exit 1) when the declared iterations do not close. Inputs are SYNTHETIC."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "adapters" / "unfolding" / "assets" / "unfold.py"

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # pragma: no cover
    HAVE_NP = False
try:
    import pyunfold  # noqa: F401
    HAVE_PYUNFOLD = True
except ImportError:
    HAVE_PYUNFOLD = False


def run(args, doc=None, hide=()):
    with tempfile.TemporaryDirectory() as td:
        argv = [str(a) for a in args]
        if doc is not None:
            p = Path(td) / "in.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            argv = [a.replace("@IN", str(p)) for a in argv]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        if hide:
            stub = Path(td) / "stub"
            stub.mkdir()
            for mod in hide:
                (stub / f"{mod}.py").write_text(f"raise ImportError('{mod} hidden for this test')\n", encoding="utf-8")
            env["PYTHONPATH"] = str(stub)
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), *argv], capture_output=True, text=True, timeout=900,
                            env=env)
    return cp.returncode, json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {"raw": cp.stdout + cp.stderr}


def banded(n, eff=0.9, spill=0.15):
    r = np.zeros((n, n))
    for j in range(n):
        r[j, j] = 1 - 2 * spill
        if j > 0:
            r[j - 1, j] = spill
        if j < n - 1:
            r[j + 1, j] = spill
        r[:, j] *= eff / r[:, j].sum()
    return r


def truth_spectrum(n):
    return (2000.0 * np.exp(-0.15 * np.arange(n)) + 50.0).tolist()


@unittest.skipUnless(HAVE_NP, "numpy needed")
class WithoutBackends(unittest.TestCase):
    def doc(self):
        r = banded(5)
        return {"response": r.tolist(), "data": (r @ np.array(truth_spectrum(5))).tolist()}

    def test_missing_pyunfold_exits_3_with_hint(self):
        code, out = run(["unfold", "--input", "@IN", "--backend", "pyunfold", "--iterations", "4"], self.doc(),
                        hide=("pyunfold",))
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "missing-dependency")
        self.assertIn("pip install pyunfold", out["install"])

    def test_missing_roounfold_exits_3(self):
        code, out = run(["unfold", "--input", "@IN", "--backend", "roounfold", "--iterations", "4"], self.doc(),
                        hide=("ROOT",))
        self.assertEqual(code, 3, out)
        self.assertIn("RooUnfold", out["install"])

    def test_iterations_are_required_and_bad_input_exits_2(self):
        code, out = run(["unfold", "--input", "@IN", "--backend", "pyunfold"], self.doc())
        self.assertEqual(code, 2, out)
        code, out = run(["unfold", "--input", "@IN", "--backend", "pyunfold", "--iterations", "4"],
                        {"response": [[0.5, 0.2]], "data": [1.0, 2.0]}, hide=("pyunfold",))
        self.assertIn(code, (2, 3), out)
        code, out = run(["unfold", "--input", "@IN", "--backend", "pyunfold", "--iterations", "0"], self.doc())
        self.assertEqual(code, 2, out)


@unittest.skipUnless(HAVE_NP and HAVE_PYUNFOLD, "pyunfold not installed (pip install pyunfold)")
class WithPyunfold(unittest.TestCase):
    def test_agrees_with_core_up_to_60_bins(self):
        for n in (8, 60):
            with self.subTest(bins=n):
                r = banded(n)
                doc = {"response": r.tolist(), "data": (r @ np.array(truth_spectrum(n))).tolist()}
                code, out = run(["compare-core", "--input", "@IN", "--iterations", "5"], doc)
                self.assertEqual(code, 0, out)
                self.assertLess(out["max_relative_difference"], 1e-9)
        r = banded(61)
        code, out = run(["compare-core", "--input", "@IN", "--iterations", "5"],
                        {"response": r.tolist(), "data": (r @ np.array(truth_spectrum(61))).tolist()})
        self.assertEqual(code, 2, out)

    def test_unfold_reports_estimate_errors_and_backend(self):
        r = banded(6)
        doc = {"response": r.tolist(), "data": (r @ np.array(truth_spectrum(6))).tolist()}
        code, out = run(["unfold", "--input", "@IN", "--backend", "pyunfold", "--iterations", "6"], doc)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["backend"]["name"], "pyunfold")
        self.assertEqual(len(out["estimate"]), 6)
        self.assertEqual(len(out["stat_errors"]), 6)
        self.assertEqual(out["regularization"]["iterations"], 6)
        self.assertEqual(out["status_label"], "unvalidated")

    def validation_doc(self, n=6):
        r = banded(n)
        return {"response": r.tolist(), "truth": truth_spectrum(n), "closure_tolerance": 0.02,
                "coverage_tolerance": 0.06,
                "reweighted_closure": {"name": "data-like tilt", "weights": [1.0 + 0.05 * j for j in range(n)]},
                "stress_tests": [{"name": "harder", "weights": [1.0 + 0.1 * j for j in range(n)]},
                                 {"name": "softer", "weights": [1.0 / (1.0 + 0.1 * j) for j in range(n)]}]}

    def test_validation_passes_with_enough_iterations(self):
        code, out = run(["validate", "--input", "@IN", "--backend", "pyunfold", "--iterations", "30", "--toys", "300",
                         "--seed", "3"], self.validation_doc())
        self.assertEqual(code, 0, out)
        checks = out["checks"]
        self.assertTrue(checks["nominal_closure"]["pass"])
        self.assertTrue(checks["reweighted_closure"]["pass"])
        self.assertEqual([s["name"] for s in checks["stress_tests"]], ["harder", "softer"])
        self.assertTrue(checks["toy_coverage"]["pass"], checks["toy_coverage"])
        self.assertIn("declared before", out["regularization"]["rule"])

    def test_validation_fails_when_iterations_do_not_close(self):
        code, out = run(["validate", "--input", "@IN", "--backend", "pyunfold", "--iterations", "1", "--toys", "100",
                         "--seed", "4"], self.validation_doc())
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "failed")
        self.assertFalse(out["checks"]["nominal_closure"]["pass"])


if __name__ == "__main__":
    unittest.main()

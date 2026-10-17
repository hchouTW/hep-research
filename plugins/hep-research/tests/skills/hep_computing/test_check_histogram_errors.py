"""C7: check_histogram_errors.py. Oracles: a histogram filled with known weights (sum of w^2 per bin computed here)
passes; planted errors are caught: a weighted histogram without Sumw2, a unit-weight histogram whose stored errors were
overwritten, a negative bin, a large flow fraction, a TEfficiency with passed > total; a uniformly scaled unit-weight
histogram is a warning, not an error; uproot and PyROOT read the same file to the same report. The canonical JSON
form needs no ROOT; the uproot tests need uproot (E2 venv); the PyROOT comparison needs a Python >= 3.13 with ROOT
($HEP_ROOT_PYTHON, e.g. /opt/homebrew/bin/python3.14). All inputs are SYNTHETIC."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-computing" / "scripts" / "check_histogram_errors.py"
ROOT_PYTHON = os.environ.get("HEP_ROOT_PYTHON", sys.executable)
try:
    import numpy as np
    import uproot
    from uproot.writing.identify import to_TAxis, to_TH1x
except ImportError:
    uproot = None


def has_pyroot():
    try:
        p = subprocess.run([ROOT_PYTHON, "-c", "import sys, ROOT; assert sys.version_info >= (3, 13)"],
                           capture_output=True, timeout=120)
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run(*args, python=None):
    p = subprocess.run([python or sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def filled(weights_per_bin, flow=(0.0, 0.0)):
    """Canonical TH1 (flow bins included) filled with the given weights per in-range bin."""
    values = [flow[0]] + [sum(ws) for ws in weights_per_bin] + [flow[1]]
    sumw2 = [flow[0]] + [sum(w * w for w in ws) for ws in weights_per_bin] + [flow[1]]
    allw = [w for ws in weights_per_bin for w in ws]
    return {"kind": "TH1", "values": values, "sumw2": sumw2, "entries": float(len(allw)), "tsumw": sum(allw),
            "tsumw2": sum(w * w for w in allw)}


class CanonicalJson(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, objects, *extra):
        f = self.d / "h.json"
        f.write_text(json.dumps({"objects": objects}), encoding="utf-8")
        return run(f, *extra)

    def codes(self, out, name, level):
        return [c["check"] for c in out["objects"][name][level]]

    def test_known_weights_pass(self):
        h = filled([[0.5, 1.5, 2.0], [1.0, 0.25], [3.0]])
        code, out, err = self.check({"h": h})
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["objects"]["h"]["errors"], [])
        self.assertEqual(out["objects"]["h"]["error_definition"], "sqrt(sum of w^2)")

    def test_weighted_without_sumw2_is_an_error(self):
        h = filled([[0.5, 1.5], [2.0]])
        h["sumw2"] = None
        code, out, _ = self.check({"h": h})
        self.assertEqual(code, 1)
        self.assertIn("sumw2-missing", self.codes(out, "h", "errors"))

    def test_overwritten_errors_in_a_unit_weight_histogram_are_caught(self):
        h = filled([[1.0] * 9, [1.0] * 4, [1.0] * 16])
        h["sumw2"][2] = 25.0  # SetBinError(2, 5) on a bin holding 4 entries
        code, out, _ = self.check({"h": h})
        self.assertEqual(code, 1)
        self.assertIn("sumw2-inconsistent", self.codes(out, "h", "errors"))

    def test_uniform_scale_is_a_warning(self):
        h = filled([[1.0] * 9, [1.0] * 4, [1.0] * 16])
        h["values"] = [2.0 * v for v in h["values"]]
        h["sumw2"] = [4.0 * v for v in h["sumw2"]]
        code, out, _ = self.check({"h": h})
        self.assertEqual(code, 0, out)
        self.assertIn("scaled", self.codes(out, "h", "warnings"))

    def test_negative_bins_and_flow_fraction(self):
        h = filled([[1.0, -2.5], [1.0] * 3], flow=(5.0, 0.0))
        h["sumw2"][0] = 5.0
        code, out, _ = self.check({"h": h}, "--max-flow-fraction", "0.1")
        self.assertEqual(code, 0, out)
        warn = self.codes(out, "h", "warnings")
        self.assertIn("negative-bins", warn)
        self.assertIn("flow-fraction", warn)
        self.assertEqual(out["objects"]["h"]["negative_bins"], [1])

    def test_efficiency_passed_above_total(self):
        total = filled([[1.0] * 10, [1.0] * 4])
        passed = filled([[1.0] * 7, [1.0] * 5])
        code, out, _ = self.check({"eff": {"kind": "TEfficiency", "passed": passed, "total": total}})
        self.assertEqual(code, 1)
        self.assertIn("passed-above-total", self.codes(out, "eff", "errors"))
        self.assertEqual(out["objects"]["eff"]["passed_above_total_bins"], [2])

    def test_bad_input(self):
        f = self.d / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        code, out, _ = run(f)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


def write_root(path):
    """A weighted and a unit-weight TH1D (the second with a planted error), written with uproot."""
    edges = np.array([0.0, 1.0, 2.0, 3.0])
    ax = to_TAxis("xaxis", "", 3, 0.0, 3.0, fXbins=edges)
    wts = [[0.5, 1.5, 2.0], [1.0, 0.25], [3.0]]
    vals = np.array([0.0] + [sum(w) for w in wts] + [0.0])
    sw2 = np.array([0.0] + [sum(x * x for x in w) for w in wts] + [0.0])
    allw = [x for w in wts for x in w]
    weighted = to_TH1x("weighted", "", vals, float(len(allw)), sum(allw), sum(x * x for x in allw), 0.0, 0.0, sw2, ax)
    unit_vals = np.array([0.0, 9.0, 4.0, 16.0, 0.0])
    unit_sw2 = unit_vals.copy()
    unit_sw2[2] = 25.0
    unit = to_TH1x("unit", "", unit_vals, 29.0, 29.0, 29.0, 0.0, 0.0, unit_sw2, ax)
    with uproot.recreate(path) as f:
        f["weighted"] = weighted
        f["unit"] = unit


@unittest.skipIf(uproot is None, "uproot is not installed (optional extra root-uproot)")
class UprootBackend(unittest.TestCase):
    def test_uproot_reads_and_catches_the_planted_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "h.root"
            write_root(f)
            code, out, err = run(f, "--object", "weighted", "--object", "unit", "--backend", "uproot")
            self.assertEqual(code, 1, (out, err))
            self.assertEqual(out["backend"], "uproot")
            self.assertEqual(out["objects"]["weighted"]["errors"], [])
            self.assertIn("sumw2-inconsistent", [c["check"] for c in out["objects"]["unit"]["errors"]])

    @unittest.skipUnless(has_pyroot(), "no PyROOT on Python >= 3.13 (set HEP_ROOT_PYTHON)")
    def test_pyroot_and_uproot_agree(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "h.root"
            write_root(f)
            args = (f, "--object", "weighted", "--object", "unit")
            c1, up, e1 = run(*args, "--backend", "uproot")
            c2, pr, e2 = run(*args, "--backend", "pyroot", python=ROOT_PYTHON)
            self.assertEqual((c1, c2), (1, 1), (e1, e2))
            for name in ("weighted", "unit"):
                for key in ("errors", "warnings", "negative_bins", "error_definition", "weighted"):
                    self.assertEqual(up["objects"][name][key], pr["objects"][name][key], (name, key))


if __name__ == "__main__":
    unittest.main()

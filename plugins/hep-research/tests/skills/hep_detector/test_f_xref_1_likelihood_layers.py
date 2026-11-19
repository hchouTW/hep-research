"""CHK-AT-06-09 (S2): multisample_pid.py likelihood refuses a --layers list that names no column.

Before the fix, `likelihood --layers ,` (or an empty value, or only commas) gave status ok and exit 0, with
layers [], every LLR the empty sum 0 and, with --label-column, a one-point curve at efficiency 1 and mis-
identification 1: a likelihood ratio over no layer reported as a valid result. `charge` refuses the same input
("--layers names no column", exit 2).

Oracle (exhaustive, basis exhaustive): every --layers value made of 1 to 3 pieces from {"", "a", "b"} joined by
commas (3 + 9 + 27 = 39 values). Expected verdict written from the script's own contract (module docstring: exit 2,
status rejected for invalid input or arguments) and from charge's rule for the same flag: a value whose pieces are
all empty ("", ",", ",,") names no column and is refused with exit 2, status rejected and the error "--layers names
no column"; every other value is accepted (exit 0, status ok) and its layers are its non-empty pieces in order. For
the accepted values a file of one event (a = 0.5, b = 1.5) has LLR = sum over the listed layers of log(p_sig/p_bkg),
with the normalized densities of the synthetic PDF below: log(1/3) for a, log(3) for b.

Negative control (emulates the pre-fix behaviour in the test): over no layer every event's LLR is the empty sum 0,
so the pre-fix curve is the single point (efficiency 1, misid 1). The fixed tool must not report it.

Tolerances: 1e-12 (absolute) on the LLR mean, a sum of at most three logarithms of exact ratios (double rounding is
about 1e-16 per term); every other comparison is exact (exit codes, strings, lists, counts).
The test runs the tool as a subprocess and does not import it. All inputs are SYNTHETIC.
"""
import itertools
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"
# two bins on [0, 2]: normalized densities signal (1/4, 3/4), background (3/4, 1/4)
PDFS = {"edges": [0.0, 1.0, 2.0], "signal": [1.0, 3.0], "background": [3.0, 1.0]}
LOG_RATIO_OF_LAYER = {"a": math.log(1.0 / 3.0), "b": math.log(3.0)}  # a = 0.5 in bin 1, b = 1.5 in bin 2
LOG_RATIO_TOLERANCE = 1e-12


def run(*args):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=120)
    return res.returncode, json.loads(res.stdout)


class LikelihoodLayersNamingNoColumn(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)
        (self.d / "pdfs.json").write_text(json.dumps(PDFS), encoding="utf-8")
        self.one_event = self.d / "one_event.csv"
        self.one_event.write_text("a,b\n0.5,1.5\n", encoding="utf-8")
        self.labelled = self.d / "labelled.csv"
        self.labelled.write_text("a,b,label\n0.5,1.5,1\n1.5,0.5,0\n", encoding="utf-8")

    def tearDown(self):
        self.workdir.cleanup()

    def test_exhaustive_verdict_over_every_layers_value_of_up_to_three_pieces(self):
        values = [",".join(p) for n in (1, 2, 3) for p in itertools.product(("", "a", "b"), repeat=n)]
        self.assertEqual(len(values), 39)
        for value in values:
            pieces = [p for p in value.split(",") if p]
            with self.subTest(layers=value):
                code, out = run("likelihood", self.one_event, "--layers", value, "--pdfs", self.d / "pdfs.json")
                if not pieces:
                    self.assertEqual(code, 2, out)
                    self.assertEqual(out.get("status"), "rejected", out)
                    self.assertIn("--layers names no column", out.get("error", ""))
                    self.assertNotIn("llr_summary", out)
                else:
                    self.assertEqual(code, 0, out)
                    self.assertEqual(out["status"], "ok", out)
                    self.assertEqual(out["layers"], pieces)
                    self.assertEqual(out["events"], 1)
                    expected = sum(LOG_RATIO_OF_LAYER[p] for p in pieces)
                    self.assertAlmostEqual(out["llr_summary"]["mean"], expected, delta=LOG_RATIO_TOLERANCE)

    def test_negative_control_empty_sum_curve_is_not_reported(self):
        # pre-fix: every LLR is the empty sum 0, so signal and background pass every threshold alike
        emulated_pre_fix_curve = [(1.0, 1.0)]
        for value in ("", ",", ",,"):
            with self.subTest(layers=value):
                code, out = run("likelihood", self.labelled, "--layers", value, "--pdfs", self.d / "pdfs.json",
                                "--label-column", "label", "--points", "2")
                got = [(p["efficiency"], p["misid"]) for p in out.get("curve", [])]
                self.assertNotEqual(got, emulated_pre_fix_curve, out)
                self.assertEqual(code, 2, out)
                self.assertEqual(out.get("status"), "rejected", out)


if __name__ == "__main__":
    unittest.main()

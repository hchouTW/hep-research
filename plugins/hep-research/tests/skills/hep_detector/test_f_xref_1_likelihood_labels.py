"""CHK-AT-06-10 (S2): multisample_pid.py likelihood refuses a --label-column value other than 0 or 1.

Before the fix the label was truncated with int() before the 0/1 check, so a label 0.7 (or 0.75, -0.75, 1.5)
became 0 or 1 and was counted as background or signal, with status ok and exit 0. The docstring defines the column
as "1 signal, 0 background".

Oracle (exhaustive, basis exhaustive): every label value k/4 for k = -4..8 (13 values), each written two ways
(format(v, "g") and repr(v), so 1 and 1.0, 0 and 0.0: 26 spellings), as the label of a third event added to one
signal event (label 1, a = 1.5) and one background event (label 0, a = 0.5). Expected verdict written from that
definition and from the script's contract (exit 2, status rejected for invalid input): a value equal to 0 or 1 is
accepted; every other value is refused with exit 2, status rejected and an error saying the column "must be 0 or 1".
For an accepted value, the third event (a = 1.5, LLR log 3, the signal event's LLR) is counted in its class, and with
--points 2 the curve is the one threshold log 3 (the only signal LLR): label 1 gives 2 signal and 1 background
events, efficiency 2/2 and misid 0/1; label 0 gives 1 signal and 2 background events, efficiency 1/1 and misid 1/2.

Negative control (emulates the pre-fix behaviour in the test): int(0.7) = 0 counts the third event as background,
so the pre-fix curve is (efficiency 1, misid 1/2). The fixed tool must not report it.

Tolerances: none. Every comparison is exact: exit codes, strings, counts, and efficiencies and misids that are
ratios of integers at most 2 (0, 1/2, 1), exact in binary floating point.
The test runs the tool as a subprocess and does not import it. All inputs are SYNTHETIC.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"
# two bins on [0, 2]: normalized densities signal (1/4, 3/4), background (3/4, 1/4)
PDFS = {"edges": [0.0, 1.0, 2.0], "signal": [1.0, 3.0], "background": [3.0, 1.0]}
BASE_ROWS = "a,label\n1.5,1\n0.5,0\n"


def run(*args):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=120)
    return res.returncode, json.loads(res.stdout)


class LikelihoodLabelIsZeroOrOne(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)
        (self.d / "pdfs.json").write_text(json.dumps(PDFS), encoding="utf-8")

    def tearDown(self):
        self.workdir.cleanup()

    def likelihood(self, label_text):
        path = self.d / "events.csv"
        path.write_text(BASE_ROWS + f"1.5,{label_text}\n", encoding="utf-8")
        return run("likelihood", path, "--layers", "a", "--pdfs", self.d / "pdfs.json", "--label-column", "label",
                   "--points", "2")

    def test_exhaustive_verdict_over_quarter_steps_from_minus_one_to_two(self):
        values = [Fraction(k, 4) for k in range(-4, 9)]
        self.assertEqual(len(values), 13)
        for v in values:
            for text in (format(float(v), "g"), repr(float(v))):
                with self.subTest(label=text):
                    code, out = self.likelihood(text)
                    if v in (0, 1):
                        self.assertEqual(code, 0, out)
                        self.assertEqual(out["status"], "ok", out)
                        self.assertEqual(out["events"], 3)
                        n_sig, n_bkg = (2, 1) if v == 1 else (1, 2)
                        k_bkg = 0 if v == 1 else 1  # background events at or above the threshold log 3
                        got = [(p["efficiency"], p["misid"]) for p in out["curve"]]
                        self.assertEqual(got, [(float(Fraction(n_sig, n_sig)), float(Fraction(k_bkg, n_bkg)))])
                    else:
                        self.assertEqual(code, 2, out)
                        self.assertEqual(out.get("status"), "rejected", out)
                        self.assertIn("must be 0 or 1", out.get("error", ""))
                        self.assertNotIn("curve", out)

    def test_negative_control_truncated_label_is_not_counted_as_background(self):
        # pre-fix: int(0.7) = 0, so 1 signal and 2 background events, the second at log 3: misid 1/2
        emulated_pre_fix_curve = [(1.0, 0.5)]
        code, out = self.likelihood("0.7")
        got = [(p["efficiency"], p["misid"]) for p in out.get("curve", [])]
        self.assertNotEqual(got, emulated_pre_fix_curve, out)
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("status"), "rejected", out)


if __name__ == "__main__":
    unittest.main()

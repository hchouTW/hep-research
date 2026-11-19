"""F-XREF-1: multisample_pid.py does what its docstring and particle-identification.md say.

- CHK-AT-06-06: the truncated mean drops floor(f N) of the N layer estimates; the output gives the numbers dropped
  (samples_dropped_high, samples_dropped_low) and warns when a nonzero fraction drops no sample. The expected means
  are written by hand from the definition (sort, drop, average), not taken from the tool.
- CHK-AT-06-09: likelihood refuses a --layers list that names no column (exit 2), as charge does.
- CHK-AT-06-10: likelihood refuses a label other than 0 or 1 (0.7 was truncated to 0 by int()).
All inputs are SYNTHETIC. Exact comparisons: every expected value is a short exact sum.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"
# a linear response signal = Z^2, so a layer signal s inverts to |Z| = sqrt(s)
RESPONSE = {"z2": [0.0, 100.0], "signal": [0.0, 100.0]}
PDFS = {"edges": [0.0, 1.0, 2.0], "signal": [1.0, 3.0], "background": [3.0, 1.0]}


def run(*args):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=120)
    return res.returncode, json.loads(res.stdout)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "response.json").write_text(json.dumps(RESPONSE), encoding="utf-8")
        (self.d / "pdfs.json").write_text(json.dumps(PDFS), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, name, text):
        path = self.d / name
        path.write_text(text, encoding="utf-8")
        return path


class TruncatedMeanCounts(Base):
    def charge(self, header, row, high, low=None):
        path = self.csv("events.csv", header + "\n" + row + "\n")
        args = ["charge", path, "--layers", header, "--response", self.d / "response.json", "--method",
                "truncated-mean", "--truncate-high", high, "--no-path-correction"]
        if low is not None:
            args += ["--truncate-low", low]
        return run(*args)

    def test_three_layers_quarter_drops_none_and_warns(self):
        # N = 3, f = 0.25: floor(0.75) = 0, so the mean of |Z| = 1, 1, 2 is 4/3
        code, out = self.charge("a,b,c", "1,1,4", 0.25)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["samples_dropped_high"], out["samples_dropped_low"]), (0, 0))
        self.assertAlmostEqual(out["summary"]["mean"], 4.0 / 3.0, places=12)
        self.assertTrue(any("--truncate-high 0.25 drops no sample of 3 layers" in w for w in out["warnings"]),
                        out["warnings"])

    def test_four_layers_quarter_drops_one(self):
        # N = 4, f = 0.25: floor(1.0) = 1; |Z| = 1, 1, 1, 3 -> drop 3 -> mean 1
        code, out = self.charge("a,b,c,d", "1,1,1,9", 0.25)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["samples_dropped_high"], out["samples_dropped_low"]), (1, 0))
        self.assertAlmostEqual(out["summary"]["mean"], 1.0, places=12)
        self.assertFalse(any("drops no sample" in w for w in out["warnings"]), out["warnings"])

    def test_low_fraction_counts(self):
        # N = 5, high 0.2 -> 1, low 0.1 -> floor(0.5) = 0 (warned); |Z| = 1, 2, 2, 2, 3 -> drop 3 -> mean 7/4
        code, out = self.charge("a,b,c,d,e", "1,4,4,4,9", 0.2, 0.1)
        self.assertEqual(code, 0, out)
        self.assertEqual((out["samples_dropped_high"], out["samples_dropped_low"]), (1, 0))
        self.assertAlmostEqual(out["summary"]["mean"], 7.0 / 4.0, places=12)
        self.assertTrue(any("--truncate-low 0.1 drops no sample of 5 layers" in w for w in out["warnings"]),
                        out["warnings"])

    def test_other_methods_have_no_drop_counts(self):
        path = self.csv("events.csv", "a,b\n1,4\n")
        code, out = run("charge", path, "--layers", "a,b", "--response", self.d / "response.json", "--method",
                        "weighted-mean", "--layer-sigma", "0.1", "--no-path-correction")
        self.assertEqual(code, 0, out)
        self.assertNotIn("samples_dropped_high", out)


class LikelihoodInput(Base):
    def test_layers_naming_no_column_is_refused(self):
        path = self.csv("events.csv", "a,label\n0.5,1\n1.5,0\n")
        code, out = run("likelihood", path, "--layers", ",", "--pdfs", self.d / "pdfs.json")
        self.assertEqual(code, 2, out)
        self.assertIn("--layers names no column", out.get("error", ""))

    def test_fractional_label_is_refused(self):
        path = self.csv("events.csv", "a,label\n0.5,1\n1.5,0\n1.5,0.7\n")
        code, out = run("likelihood", path, "--layers", "a", "--pdfs", self.d / "pdfs.json",
                        "--label-column", "label")
        self.assertEqual(code, 2, out)
        self.assertIn("must be 0 or 1", out.get("error", ""))

    def test_integer_labels_still_accepted(self):
        # negative control: labels 1 and 0 (also written 1.0 and 0.0) give the curve as before
        path = self.csv("events.csv", "a,label\n0.5,1\n1.5,0\n1.5,1.0\n0.5,0.0\n")
        code, out = run("likelihood", path, "--layers", "a", "--pdfs", self.d / "pdfs.json",
                        "--label-column", "label", "--points", "2")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["events"], 4)
        self.assertIn("curve", out)


if __name__ == "__main__":
    unittest.main()

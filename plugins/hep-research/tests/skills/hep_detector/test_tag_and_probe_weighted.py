"""D8: tag_and_probe_efficiency.py with probes from a file: weights, bins, and no total cap.

Oracles:
- the 200,000 cap is gone: counts in the millions run, and the Clopper-Pearson ends equal scipy's beta quantiles
  (scipy is used in this test only; skipped without it);
- frequency (integer) weights give exactly the result of the duplicated events;
- sampling weights: the efficiency is sum(w pass) / sum(w), the Kish effective sample size n_eff = (sum w)^2 / sum w^2,
  and equal weights give the unweighted interval;
- a negative weight is refused (exit 2) and handed to hep-statistics; fractional frequency weights are refused;
- --bins FILE splits the probes by a variable; probes outside the edges are counted, not binned.
All inputs are SYNTHETIC.
"""
import csv
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "tag_and_probe_efficiency.py"


def run_json(*args, timeout=600):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


class NoCap(unittest.TestCase):
    def test_millions_match_scipy_beta_quantiles(self):
        try:
            from scipy.stats import beta
        except ImportError:
            self.skipTest("scipy not installed (used by this test only)")
        for k, n, level in ((4_000_000, 5_000_000, 0.95), (3, 2_000_000, 0.6827), (250_001, 250_002, 0.9)):
            with self.subTest(k=k, n=n):
                code, out = run_json("--pass-count", k, "--total", n, "--level", level)
                self.assertEqual(code, 0, out)
                a = 1 - level
                lo = beta.ppf(a / 2, k, n - k + 1) if k > 0 else 0.0
                hi = beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0
                self.assertAlmostEqual(out["lower_bound"], lo, delta=1e-9 * max(lo, 1e-12) + 1e-15)
                self.assertAlmostEqual(out["upper_bound"], hi, delta=1e-9 * hi)


class Probes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_frequency_weights_equal_duplicated_events(self):
        rng = random.Random(1)
        rows = [[int(rng.random() < 0.8), rng.randint(1, 4)] for _ in range(300)]
        write(self.d / "w.csv", ["pass", "w"], rows)
        dup = [[p, 1] for p, w in rows for _ in range(w)]
        write(self.d / "dup.csv", ["pass", "w"], dup)
        c1, weighted = run_json("--probes", self.d / "w.csv", "--pass-column", "pass", "--weights", "w",
                                "--weight-kind", "frequency")
        c2, plain = run_json("--probes", self.d / "dup.csv", "--pass-column", "pass")
        self.assertEqual((c1, c2), (0, 0), (weighted, plain))
        a, b = weighted["bins"][0], plain["bins"][0]
        for key in ("efficiency", "lower_bound", "upper_bound"):
            self.assertEqual(a[key], b[key], key)
        self.assertEqual(a["total"], len(dup))

    def test_sampling_weights_kish(self):
        rng = random.Random(2)
        rows = [[int(rng.random() < 0.7), rng.uniform(0.2, 3.0)] for _ in range(500)]
        write(self.d / "w.csv", ["pass", "w"], rows)
        code, out = run_json("--probes", self.d / "w.csv", "--pass-column", "pass", "--weights", "w",
                             "--weight-kind", "sampling")
        self.assertEqual(code, 0, out)
        b = out["bins"][0]
        sw = sum(w for _, w in rows)
        sw2 = sum(w * w for _, w in rows)
        self.assertAlmostEqual(b["efficiency"], sum(w for p, w in rows if p) / sw, delta=1e-12)
        self.assertAlmostEqual(b["n_eff"], sw * sw / sw2, delta=1e-9)
        self.assertLess(b["lower_bound"], b["efficiency"])
        self.assertGreater(b["upper_bound"], b["efficiency"])
        self.assertIn("Kish", out["method"])
        # equal sampling weights reduce to the unweighted interval
        write(self.d / "c.csv", ["pass", "w"], [[p, 2.5] for p, _ in rows])
        _, eq = run_json("--probes", self.d / "c.csv", "--pass-column", "pass", "--weights", "w",
                         "--weight-kind", "sampling")
        k = sum(p for p, _ in rows)
        _, ref = run_json("--pass-count", k, "--total", len(rows))
        for key in ("efficiency", "lower_bound", "upper_bound"):
            self.assertAlmostEqual(eq["bins"][0][key], ref[key], delta=1e-12)

    def test_negative_and_fractional_frequency_weights_refused(self):
        write(self.d / "neg.csv", ["pass", "w"], [[1, 1.0], [0, -0.5]])
        code, out = run_json("--probes", self.d / "neg.csv", "--pass-column", "pass", "--weights", "w",
                             "--weight-kind", "sampling")
        self.assertEqual(code, 2)
        self.assertIn("hep-statistics", out["error"])
        write(self.d / "frac.csv", ["pass", "w"], [[1, 1.5], [0, 1.0]])
        code, out = run_json("--probes", self.d / "frac.csv", "--pass-column", "pass", "--weights", "w",
                             "--weight-kind", "frequency")
        self.assertEqual(code, 2)
        code, out = run_json("--probes", self.d / "frac.csv", "--pass-column", "pass", "--weights", "w")
        self.assertEqual(code, 2)  # --weight-kind has no default

    def test_bins(self):
        rows = [[1, 5.0], [0, 5.0], [1, 15.0], [1, 15.0], [0, 25.0], [1, 99.0]]
        write(self.d / "p.csv", ["pass", "pt"], rows)
        (self.d / "bins.json").write_text(json.dumps({"edges": [0, 10, 20, 30]}), encoding="utf-8")
        code, out = run_json("--probes", self.d / "p.csv", "--pass-column", "pass", "--bins", self.d / "bins.json",
                             "--variable-column", "pt")
        self.assertEqual(code, 0, out)
        self.assertEqual([b["efficiency"] for b in out["bins"]], [0.5, 1.0, 0.0])
        self.assertEqual(out["outside_edges"], 1)
        self.assertEqual(out["status"], "unvalidated")

    def test_counts_and_probes_are_exclusive(self):
        write(self.d / "p.csv", ["pass"], [[1]])
        code, out = run_json("--probes", self.d / "p.csv", "--pass-column", "pass", "--pass-count", "1", "--total", "1")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

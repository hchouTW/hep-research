"""F-XREF-2, CHK-AT-08-05 (S1): charge_confusion_rate.py control keeps interval_68 and rate_error at 68.27%.

Defect: with --cl other than 68.27%, each control bin's "interval_68" held the Clopper-Pearson interval at --cl, and
sign_rates "rate_error" its half-width (at --cl 0.95 about twice the one-sigma error), with status ok.

These tests read only keys the parent already writes ("interval_68", sign_rates "rate_error"), so on the parent they
fail by assertion, not by a missing key.

Oracles (none imports the module under test or core/stats):
- third-party: scipy.stats.binomtest(k, n).proportion_ci(method="exact"), scipy's own Clopper-Pearson
  implementation (third-party-definition); skipped without scipy.
- exhaustive: every outcome k = 0..n for n = 1..20 (230 bins in one run), checked against the defining tail
  equalities of the central Clopper-Pearson interval at 68.27% (Clopper and Pearson 1934): for k > 0 the lower end
  p_lo solves P(X >= k; n, p_lo) = a, for k < n the upper end p_hi solves P(X <= k; n, p_hi) = a, with
  a = (1 - 0.6826894921370859) / 2; the ends are 0 at k = 0 and 1 at k = n. Binomial tails are summed exactly with
  math.comb in the test.
- invariant (property): interval_68 and rate_error do not depend on --cl.
- negative control (emulates the pre-fix output): the half-width at --cl 0.95, from scipy, differs from rate_error.

Tolerances, fixed before the first run and never widened:
- TOL_END = 1e-9 absolute on interval ends and half-widths: core's beta quantiles and scipy's exact interval agree to
  5e-13 for n <= 40 and n in {300, 1000, 5000} at CL 0.5, 0.6827, 0.95 and 0.99 (measured before this test was
  written), so 1e-9 leaves a margin of three decades and is still 1e6 times smaller than the defect (8.6e-3 here).
- TOL_TAIL = 1e-9 absolute on a binomial tail probability at a returned end: the tail's derivative in p is at most
  n * max pmf < 20 for n <= 20, so an end error of 5e-13 moves the tail by < 1e-11; the defect moves it from 0.1587 to
  0.025 (at --cl 0.95).
- NEG_MIN = 1e-4: the pre-fix rate_error (95% half-width) exceeds the 68.27% one by 8.6e-3 in bin 1 here (scipy).
Inputs are SYNTHETIC.
"""
import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"
CL68 = 0.6826894921370859
TOL_END = 1e-9
TOL_TAIL = 1e-9
NEG_MIN = 1e-4
N_MAX = 20

try:
    from scipy.stats import binomtest
except ImportError:  # pragma: no cover
    binomtest = None


def run_control(rows, edges, *extra):
    """Run control mode on (bin value, n, k) groups of negative tracks; k of them reconstructed positive."""
    with tempfile.TemporaryDirectory() as d:
        control_csv = Path(d) / "ctrl.csv"
        with control_csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["rig", "truth", "reco"])
            for x, n, k in rows:
                for i in range(n):
                    w.writerow([x, "negative", "positive" if i < k else "negative"])
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "control", "--data", str(control_csv),
                            "--edges", *[repr(e) for e in edges], "--bin-column", "rig",
                            "--true-sign-column", "truth", "--reco-sign-column", "reco", *extra],
                           capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stdout + p.stderr)
    return json.loads(p.stdout)


# two bins: 7 wrong of 300 and 2 wrong of 200 (SYNTHETIC)
SMALL = [(5.0, 300, 7), (50.0, 200, 2)]
SMALL_EDGES = [1.0, 10.0, 100.0]


def exact_68(k, n):
    ci = binomtest(k, n).proportion_ci(confidence_level=CL68, method="exact")
    return float(ci.low), float(ci.high)


def upper_tail(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p), summed term by term."""
    return sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(k, n + 1))


def lower_tail(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p), summed term by term."""
    return sum(math.comb(n, j) * p ** j * (1.0 - p) ** (n - j) for j in range(0, k + 1))


class ControlInterval68AtAnyCl(unittest.TestCase):
    @unittest.skipIf(binomtest is None, "scipy is the third-party oracle")
    def test_third_party_interval_68_and_rate_error_at_cl95(self):
        out = run_control(SMALL, SMALL_EDGES, "--cl", "0.95")
        errors = out["sign_rates"]["rates"][0]["rate_error"]
        for row, err, (_, n, k) in zip(out["bins"], errors, SMALL):
            lo, hi = exact_68(k, n)
            with self.subTest(k=k, n=n):
                self.assertAlmostEqual(row["interval_68"][0], lo, delta=TOL_END)
                self.assertAlmostEqual(row["interval_68"][1], hi, delta=TOL_END)
                self.assertAlmostEqual(err, (hi - lo) / 2, delta=TOL_END)

    def test_exhaustive_tail_equalities_at_cl95(self):
        a = (1.0 - CL68) / 2.0
        rows, edges, cases = [], [0.0], []
        for n in range(1, N_MAX + 1):
            for k in range(0, n + 1):
                b = len(cases)
                rows.append((b + 0.5, n, k))
                edges.append(b + 1.0)
                cases.append((n, k))
        out = run_control(rows, edges, "--cl", "0.95")
        self.assertEqual(len(out["bins"]), len(cases))
        errors = out["sign_rates"]["rates"][0]["rate_error"]
        for row, err, (n, k) in zip(out["bins"], errors, cases):
            lo, hi = row["interval_68"]
            with self.subTest(n=n, k=k):
                self.assertEqual((row["n"], row["k"]), (n, k))
                if k == 0:
                    self.assertEqual(lo, 0.0)
                else:
                    self.assertAlmostEqual(upper_tail(k, n, lo), a, delta=TOL_TAIL)
                if k == n:
                    self.assertEqual(hi, 1.0)
                else:
                    self.assertAlmostEqual(lower_tail(k, n, hi), a, delta=TOL_TAIL)
                self.assertAlmostEqual(err, (hi - lo) / 2, delta=TOL_END)

    def test_property_interval_68_and_rate_error_do_not_depend_on_cl(self):
        ref = run_control(SMALL, SMALL_EDGES)
        ref_err = ref["sign_rates"]["rates"][0]["rate_error"]
        for cl in ("0.5", "0.9", "0.95", "0.99"):
            out = run_control(SMALL, SMALL_EDGES, "--cl", cl)
            err = out["sign_rates"]["rates"][0]["rate_error"]
            with self.subTest(cl=cl):
                for row, row_ref in zip(out["bins"], ref["bins"]):
                    for got, want in zip(row["interval_68"], row_ref["interval_68"]):
                        self.assertAlmostEqual(got, want, delta=TOL_END)
                for got, want in zip(err, ref_err):
                    self.assertAlmostEqual(got, want, delta=TOL_END)

    @unittest.skipIf(binomtest is None, "scipy gives the pre-fix value")
    def test_negative_control_95_half_width_is_not_the_rate_error(self):
        # the pre-fix rate_error was the half-width at --cl; at 0.95 it is about twice the 68.27% one
        out = run_control(SMALL, SMALL_EDGES, "--cl", "0.95")
        ci = binomtest(7, 300).proportion_ci(confidence_level=0.95, method="exact")
        pre_fix = (float(ci.high) - float(ci.low)) / 2
        self.assertGreater(abs(out["sign_rates"]["rates"][0]["rate_error"][0] - pre_fix), NEG_MIN)


if __name__ == "__main__":
    unittest.main()

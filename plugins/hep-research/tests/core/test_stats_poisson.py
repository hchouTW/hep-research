"""Tests for core/stats/ poisson_diagnostics.py: known exact values (zero-count bound
-ln(alpha), Garwood intervals for n=0 and n=1), the unphysical classical-limit case,
seeded reproducibility and conservative coverage, and input rejection.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import io
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import poisson_diagnostics as pd  # noqa: E402



class ExactValueTests(unittest.TestCase):
    def test_cdf_matches_closed_forms(self):
        self.assertAlmostEqual(pd.poisson_cdf(0, 2.0), math.exp(-2.0), places=14)
        self.assertAlmostEqual(pd.poisson_cdf(2, 3.0), math.exp(-3.0) * (1 + 3 + 4.5), places=14)
        self.assertEqual(pd.poisson_cdf(5, 0.0), 1.0)

    def test_zero_count_bound_is_minus_ln_alpha(self):
        out = pd.upper_limit(0, 0.0, 0.95)
        self.assertAlmostEqual(out["upper_limit_on_signal"], -math.log(0.05), places=9)
        self.assertAlmostEqual(out["upper_limit_on_signal"], 2.9957, places=3)
        self.assertEqual(out["label"], "[General method]")

    def test_zero_count_limit_falls_with_known_background(self):
        # with n = 0 the classical limit on s is -ln(1 - CL) - b, not -ln(1 - CL) for every b
        for b in (0.5, 1.0, 2.0):
            out = pd.upper_limit(0, b, 0.95)
            self.assertAlmostEqual(out["upper_limit_on_total_mean"], -math.log(0.05), places=9)
            self.assertAlmostEqual(out["upper_limit_on_signal"], -math.log(0.05) - b, places=9)
        self.assertAlmostEqual(pd.upper_limit(0, 1.0, 0.90)["upper_limit_on_signal"], -math.log(0.10) - 1.0, places=9)
        # once b exceeds -ln(1 - CL) the classical limit is not a result
        out = pd.upper_limit(0, 3.5, 0.95)
        self.assertIsNone(out["upper_limit_on_signal"])
        self.assertIn("warning", out)

    def test_known_upper_limits(self):
        self.assertAlmostEqual(pd.upper_limit(1, 0.0, 0.95)["upper_limit_on_signal"], 4.7439, places=3)
        self.assertAlmostEqual(pd.upper_limit(3, 1.0, 0.95)["upper_limit_on_signal"], 7.7537 - 1.0, places=3)

    def test_garwood_intervals(self):
        zero = pd.central_interval(0, 0.6827)
        self.assertEqual(zero["lower"], 0.0)
        self.assertAlmostEqual(zero["upper"], 1.8410, places=3)
        one = pd.central_interval(1, 0.6827)
        self.assertAlmostEqual(one["lower"], 0.1727, places=3)
        self.assertAlmostEqual(one["upper"], 3.2996, places=3)

    def test_interval_brackets_the_count_for_larger_n(self):
        iv = pd.central_interval(25, 0.95)
        self.assertLess(iv["lower"], 25)
        self.assertGreater(iv["upper"], 25)


class UnphysicalClassicalLimitTests(unittest.TestCase):
    def test_few_events_against_large_background_is_flagged_not_reported(self):
        out = pd.upper_limit(0, 5.0, 0.95)
        self.assertIsNone(out["upper_limit_on_signal"])
        self.assertIn("Feldman-Cousins or CLs", out["warning"])

    def test_no_warning_when_signal_limit_is_positive(self):
        self.assertNotIn("warning", pd.upper_limit(6, 2.0, 0.95))


class CoverageTests(unittest.TestCase):
    def test_same_seed_reproduces_and_different_seed_differs(self):
        a = pd.coverage(2.5, 0.6827, 2000, seed=7)
        b = pd.coverage(2.5, 0.6827, 2000, seed=7)
        c = pd.coverage(2.5, 0.6827, 2000, seed=8)
        self.assertEqual(a["coverage"], b["coverage"])
        self.assertNotEqual(a["coverage"], c["coverage"])
        self.assertEqual((a["seed"], a["toys"], a["cl"]), (7, 2000, 0.6827))

    def test_garwood_is_conservative(self):
        for mu in (0.5, 2.5, 10.0):
            out = pd.coverage(mu, 0.6827, 20000, seed=3)
            self.assertGreaterEqual(out["coverage"] + 4 * out["binomial_error_on_coverage"], 0.6827, mu)

    def test_sampler_mean_and_variance(self):
        import random
        rng = random.Random(11)
        draws = [pd._draw(rng, 4.0) for _ in range(40000)]
        mean = sum(draws) / len(draws)
        var = sum((d - mean) ** 2 for d in draws) / len(draws)
        self.assertAlmostEqual(mean, 4.0, delta=0.06)
        self.assertAlmostEqual(var, 4.0, delta=0.15)


def decimal_sf(n, mu, digits=120):
    """Independent reference: P(N >= n | mu) = 1 - sum_{k < n} P(k), in decimal arithmetic with `digits` digits."""
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = digits
        m = Decimal(repr(mu))
        term, cum = (-m).exp(), Decimal(0)
        for k in range(n):
            cum += term
            term = term * m / (k + 1)
        return 1 - cum


class MeanLimitTests(unittest.TestCase):
    """Results near and above the old 500 limit (SciPy 1.18 chi2 values recorded): never clipped at a range end."""

    def test_garwood_and_classical_limit_beyond_500(self):
        iv = pd.central_interval(490)
        self.assertAlmostEqual(iv["upper"], 513.1515084417051, delta=1e-6)  # chi2.ppf(1 - a, 982) / 2; 500.0 before
        self.assertAlmostEqual(iv["lower"], 467.87113507097774, delta=1e-6)
        ul = pd.upper_limit(495, 0.0)
        self.assertAlmostEqual(ul["upper_limit_on_total_mean"], 533.1922730038418, delta=1e-6)  # 500 before
        iv = pd.central_interval(5000)
        self.assertAlmostEqual(iv["upper"], 5071.716943473817, delta=1e-5)
        self.assertAlmostEqual(iv["lower"], 4929.290159543603, delta=1e-5)

    def test_unbracketed_limit_fails_instead_of_returning_the_range_end(self):
        with self.assertRaises(pd.SolveFailed):
            pd.upper_limit(99990, 0.0)
        with self.assertRaises(pd.SolveFailed):
            pd.central_interval(99990)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pd.main(["upper-limit", "--n", "99990", "--b", "0"])
        self.assertEqual(code, 1)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["status"], "failed")
        self.assertNotIn("upper_limit_on_total_mean", out)

    def test_fc_scan_keeps_its_own_documented_limit(self):
        with self.assertRaisesRegex(pd.DiagnosticsError, "limited to total means up to 500"):
            pd.fc_interval(0, 480.0)


class UpperTailTests(unittest.TestCase):
    """P(N >= n) far into the tail: 1 - P(N <= n - 1) in double precision cancels to 0 below about 1e-16."""

    def test_matches_high_precision_reference(self):
        for n, mu in ((60, 5.0), (1, 5.0), (5, 5.0), (6, 5.0), (20, 5.0), (40, 0.5), (600, 500.0), (499, 500.0)):
            ref = decimal_sf(n, mu)
            self.assertAlmostEqual(pd.poisson_sf(n, mu) / float(ref), 1.0, delta=1e-10, msg=(n, mu))
            self.assertAlmostEqual(pd.log_poisson_sf(n, mu), float(ref.ln()), delta=1e-10, msg=(n, mu))

    def test_log_tail_and_significance_stay_finite_to_n_1000(self):
        last = 0.0
        for n in range(1, 1001):
            lp = pd.log_poisson_sf(n, 5.0)
            self.assertTrue(math.isfinite(lp), msg=n)
            self.assertLess(lp, last, msg=n)
            last = lp
            if lp > -745.0:  # representable as a double: never reported as exactly 0
                self.assertGreater(pd.poisson_sf(n, 5.0), 0.0, msg=n)
        ref = decimal_sf(1000, 5.0, digits=2000)
        self.assertAlmostEqual(pd.log_poisson_sf(1000, 5.0), float(ref.ln()), delta=1e-9)
        self.assertTrue(math.isfinite(pd.z_from_log_p(pd.log_poisson_sf(1000, 5.0))))

    def test_significance_from_log_p(self):
        for z in (0.5, 3.0, 5.0, 8.0, 20.0, 30.0):  # erfc, not NormalDist.cdf: 0.5 * (1 + erf) cancels by z = 8
            log_p = math.log(0.5 * math.erfc(z / math.sqrt(2.0)))
            self.assertAlmostEqual(pd.z_from_log_p(log_p), z, delta=1e-9 * z, msg=z)
        # beyond the smallest double: ln P(Z > 40) = -804.60844201375 from the 12-term asymptotic series
        self.assertAlmostEqual(pd.z_from_log_p(-804.6084420137538), 40.0, delta=1e-8)
        self.assertIsNone(pd.z_from_log_p(0.0))
        self.assertEqual(pd.poisson_sf(0, 3.0), 1.0)
        self.assertEqual(pd.poisson_sf(2, 0.0), 0.0)


class FeldmanCousinsTests(unittest.TestCase):
    """Reference values: Feldman and Cousins (1998), Table IV (90% CL, b = 0 to 5) and Table VI (95% CL, b = 0 to 5),
    transcribed into fixtures/fc1998_tables.json (the full grid is in test_published_tables.py). The published upper
    ends are forced non-increasing in b (Sec. IV.B); the plain construction at a single b dips below them, for
    example 1.08 instead of 1.26 at n0 = 0, b = 2, 90% CL."""

    def test_published_values(self):
        for n, b, lo, hi in ((0, 0.0, 0.0, 2.44), (1, 0.0, 0.11, 4.36), (3, 0.0, 1.10, 7.42),
                             (0, 0.5, 0.0, 1.94), (0, 1.0, 0.0, 1.61), (0, 2.0, 0.0, 1.26)):
            iv = pd.fc_interval(n, b, 0.90)
            self.assertAlmostEqual(iv["lower"], lo, delta=0.015, msg=(n, b))
            self.assertAlmostEqual(iv["upper"], hi, delta=0.015, msg=(n, b))

    def test_monotone_construction_matches_entries_where_the_plain_one_dips(self):
        # every n0 <= 10, b <= 5 entry of Tables IV and VI that the plain construction misses by more than 0.015
        cases = ((0.90, 0, 2.0, 1.26, 1.08), (0.90, 0, 3.0, 1.08, 0.95), (0.90, 0, 4.0, 1.01, 0.85),
                 (0.90, 0, 5.0, 0.98, 0.77), (0.90, 1, 4.0, 1.39, 1.33), (0.90, 1, 5.0, 1.22, 1.195),
                 (0.95, 0, 2.5, 1.78, 1.52), (0.95, 0, 3.5, 1.63, 1.38), (0.95, 0, 4.0, 1.57, 1.485),
                 (0.95, 0, 5.0, 1.54, 1.375), (0.95, 1, 4.0, 2.08, 2.04), (0.95, 2, 5.0, 2.49, 2.47))
        for cl, n, b, published, plain in cases:
            iv = pd.fc_interval(n, b, cl)
            self.assertAlmostEqual(iv["upper"], published, delta=0.01, msg=(cl, n, b))
            self.assertAlmostEqual(iv["upper_plain"], plain, delta=0.006, msg=(cl, n, b))
            self.assertTrue(iv["upper_lengthened"])
            self.assertTrue(iv["construction"].startswith("monotone"))

    def test_plain_construction_is_labelled_and_never_longer(self):
        plain = pd.fc_interval(0, 2.0, 0.90, monotone=False)
        self.assertAlmostEqual(plain["upper"], 1.08, delta=0.006)
        self.assertTrue(plain["construction"].startswith("plain"))
        self.assertNotIn("upper_plain", plain)
        adjusted = pd.fc_interval(0, 2.0, 0.90)
        self.assertEqual(adjusted["upper_plain"], plain["upper"])
        self.assertEqual(adjusted["lower"], plain["lower"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pd.main(["fc-interval", "--n", "0", "--b", "2", "--plain-construction"])
        self.assertEqual(code, 0)
        self.assertAlmostEqual(json.loads(buf.getvalue())["upper"], 1.08, delta=0.006)
        with self.assertRaises(pd.DiagnosticsError):
            pd.fc_interval(0, 2.0, 0.90, monotone="yes")

    def test_upper_end_is_non_increasing_in_b(self):
        """Non-increasing within the stated accuracy of one grid step (the plain upper end jumps up by 0.1 to 0.3)."""
        for n in (0, 1):
            uppers = [pd.fc_interval(n, 0.4 * k, 0.90, step=0.01)["upper"] for k in range(0, 13)]
            for k in range(1, len(uppers)):
                self.assertLessEqual(uppers[k], uppers[k - 1] + 0.01, msg=(n, 0.4 * k))
            plain = [pd.fc_interval(n, 0.4 * k, 0.90, step=0.01, monotone=False)["upper"] for k in range(0, 13)]
            self.assertTrue(any(plain[k] > plain[k - 1] + 0.05 for k in range(1, len(plain))), msg=n)

    def test_deterministic_and_no_empty_interval_below_background(self):
        a, b = pd.fc_interval(0, 3.0, 0.90), pd.fc_interval(0, 3.0, 0.90)
        self.assertEqual(a, b)
        self.assertEqual(a["lower"], 0.0)
        self.assertGreater(a["upper"], 0.0)  # unlike the classical limit, never empty or negative

    def test_cli_and_rejection(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pd.main(["fc-interval", "--n", "0", "--b", "0"])
        self.assertEqual(code, 0)
        self.assertAlmostEqual(json.loads(buf.getvalue())["upper"], 2.44, delta=0.015)
        for call in (lambda: pd.fc_interval(-1, 0.0), lambda: pd.fc_interval(0, -1.0), lambda: pd.fc_interval(0, 0.0, 1.0),
                     lambda: pd.fc_interval(0, 0.0, 0.9, 0.0)):
            with self.assertRaises(pd.DiagnosticsError):
                call()


class MarginalizedAndClsTests(unittest.TestCase):
    def test_cls_zero_count_and_exact_root(self):
        out = pd.cls_limit(0, 0.0, 0.95)
        self.assertAlmostEqual(out["observed_upper_limit"], -math.log(0.05), places=6)
        out = pd.cls_limit(3, 3.0, 0.95)  # CLs+b / CLb = 0.05 with CLb = P(N <= 3 | 3)
        total = out["observed_upper_limit"] + 3.0
        self.assertAlmostEqual(pd.poisson_cdf(3, total) / pd.poisson_cdf(3, 3.0), 0.05, places=6)
        band = out["expected_under_background_only"]
        self.assertLessEqual(band["-2sigma"], band["-1sigma"])
        self.assertLessEqual(band["-1sigma"], band["median"])
        self.assertLessEqual(band["median"], band["+1sigma"])
        self.assertLessEqual(band["+1sigma"], band["+2sigma"])

    def test_cls_limit_grows_with_background_uncertainty_only_mildly_and_is_deterministic(self):
        a, b = pd.cls_limit(3, 3.0, 0.95, 0.0), pd.cls_limit(3, 3.0, 0.95, 1.0)
        self.assertGreater(b["observed_upper_limit"], a["observed_upper_limit"] - 1e-9)
        self.assertEqual(b, pd.cls_limit(3, 3.0, 0.95, 1.0))

    def test_marginalized_fc_converges_to_known_background_and_widens(self):
        known = pd.fc_interval(3, 3.0, 0.90, 0.02)
        tiny = pd.fc_interval(3, 3.0, 0.90, 0.02, 0.001)
        wide = pd.fc_interval(3, 3.0, 0.90, 0.02, 2.0)
        self.assertAlmostEqual(tiny["upper"], known["upper"], delta=0.03)
        self.assertGreater(wide["upper"], known["upper"])
        self.assertEqual(wide["lower"], 0.0)

    def test_rejections(self):
        for call in (lambda: pd.cls_limit(1, 1.0, 0.95, -1.0), lambda: pd.cls_limit(1, 1.0, 0.95, 1.0, 2),
                     lambda: pd.cls_limit(-1, 1.0), lambda: pd.fc_interval(1, 1.0, 0.9, 0.02, float("nan"))):
            with self.assertRaises(pd.DiagnosticsError):
                call()


class RejectionTests(unittest.TestCase):
    def test_bad_inputs_rejected(self):
        for call in (lambda: pd.upper_limit(-1, 0.0), lambda: pd.upper_limit(1.5, 0.0), lambda: pd.upper_limit(0, -1.0),
                     lambda: pd.upper_limit(0, 0.0, 1.0), lambda: pd.upper_limit(0, 0.0, 0.0), lambda: pd.central_interval(True),
                     lambda: pd.poisson_cdf(1, 1e6), lambda: pd.coverage(0.0, 0.68, 1000, 1),
                     lambda: pd.coverage(2.0, 0.68, 10, 1), lambda: pd.coverage(2.0, 0.68, 1000, None)):
            with self.assertRaises(pd.DiagnosticsError):
                call()


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = pd.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_upper_limit_cli(self):
        code, out = self.run_cli("upper-limit", "--n", "0", "--b", "0")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["upper_limit_on_signal"], 2.9957, places=3)

    def test_rejected_input_exits_2(self):
        code, out = self.run_cli("interval", "--n", "1", "--cl", "1.5")
        self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_coverage_requires_a_seed(self):
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stderr(io.StringIO()):
            pd.main(["coverage", "--mu", "2.0"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

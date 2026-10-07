"""Tests for core/stats/ statistical_toys.py: seeded reproducibility, known limits of each
diagnostic (exact Poisson tail at the boundary, finite-template spread -> 1 for a huge MC
sample, identity-response unfolding, ratio cancellation at rho = 1), input rejection and the
CLI contract. Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import statistical_toys as st  # noqa: E402

SIG, BKG = "0.1,0.3,0.4,0.2", "0.4,0.3,0.2,0.1"
RESPONSE = {"response": [[0.6, 0.2, 0.0], [0.2, 0.5, 0.2], [0.0, 0.2, 0.6]], "truth": [1000, 600, 200], "max_iterations": 6}


class DrawTests(unittest.TestCase):
    def test_poisson_draw_moments_for_large_mean(self):
        import random
        rng = random.Random(5)
        v = [st.poisson_draw(rng, 120.0) for _ in range(4000)]
        mean = sum(v) / len(v)
        var = sum((x - mean) ** 2 for x in v) / len(v)
        self.assertAlmostEqual(mean, 120.0, delta=1.0)
        self.assertAlmostEqual(var, 120.0, delta=9.0)


class BoundaryTests(unittest.TestCase):
    def test_toys_match_exact_tail_and_naive_wilks_doubles_it(self):
        out = st.boundary(12, 8.0, 20000, 1)
        self.assertAlmostEqual(out["p_value_toys"], out["p_value_exact_poisson"], delta=0.012)
        self.assertAlmostEqual(out["p_value_naive_wilks_chi2_1dof"], 2 * out["p_value_half_chi2_asymptotic"], places=12)
        self.assertAlmostEqual(out["fraction_toys_with_q0_zero"], 0.5925, delta=0.012)  # P(N <= 8 | 8)

    def test_exact_p_value_does_not_underflow(self):
        out = st.boundary(60, 5.0, 200, 1)
        self.assertAlmostEqual(out["p_value_exact_poisson"] / 7.649610081149393e-43, 1.0, delta=1e-6)  # sf(59, 5)
        self.assertTrue(math.isfinite(out["significance_exact_poisson_z"]))
        far = st.boundary(1000, 5.0, 200, 1)
        self.assertTrue(math.isfinite(far["log_p_value_exact_poisson"]))
        self.assertGreater(far["significance_exact_poisson_z"], 90.0)

    def test_underfluctuation_has_q0_zero_and_unit_p(self):
        out = st.boundary(3, 8.0, 500, 2)
        self.assertEqual(out["q0_observed"], 0.0)
        self.assertEqual(out["p_value_toys"], 1.0)
        self.assertEqual(out["p_value_half_chi2_asymptotic"], 0.5)

    def test_seed_reproducible(self):
        self.assertEqual(st.boundary(10, 8.0, 1000, 7), st.boundary(10, 8.0, 1000, 7))


class TemplateStatTests(unittest.TestCase):
    def test_huge_mc_sample_recovers_true_template_spread(self):
        out = st.template_stat(SIG, BKG, 400, 0.2, 5e4, 5e4, 600, 3)
        self.assertAlmostEqual(out["spread_ratio_finite_over_true"], 1.0, delta=0.06)

    def test_small_mc_sample_inflates_the_spread(self):
        out = st.template_stat(SIG, BKG, 400, 0.2, 100, 100, 600, 3)
        self.assertGreater(out["spread_ratio_finite_over_true"], 1.2)

    def test_seed_reproducible_and_rejections(self):
        a = st.template_stat(SIG, BKG, 100, 0.5, 50, 50, 200, 9)
        self.assertEqual(a, st.template_stat(SIG, BKG, 100, 0.5, 50, 50, 200, 9))
        for call in (lambda: st.template_stat("1", BKG, 100, 0.5, 50, 50, 200, 1),
                     lambda: st.template_stat("0.1,0.2", "0.1,0.2,0.3", 100, 0.5, 50, 50, 200, 1),
                     lambda: st.template_stat(SIG, BKG, 100, 1.5, 50, 50, 200, 1),
                     lambda: st.template_stat(SIG, BKG, 100, 0.5, 50, 50, 200, None),
                     lambda: st.template_stat(SIG, "0,0,0,0", 100, 0.5, 50, 50, 200, 1)):
            with self.assertRaises(st.ToyError):
                call()


class TemplateBBTests(unittest.TestCase):
    def test_bb_lite_restores_error_calibration_that_the_naive_fit_loses(self):
        out = st.template_bb(SIG, BKG, 400, 0.4, 100, 100, 500, 1)["variants"]
        self.assertAlmostEqual(out["true_templates"]["pull_width"], 1.0, delta=0.15)
        self.assertGreater(out["naive_finite_templates"]["pull_width"], 1.3)
        self.assertLess(out["naive_finite_templates"]["coverage_of_delta_lnL_interval"], 0.6)
        self.assertAlmostEqual(out["barlow_beeston_lite"]["pull_width"], 1.0, delta=0.2)
        self.assertGreater(out["barlow_beeston_lite"]["coverage_of_delta_lnL_interval"],
                           out["naive_finite_templates"]["coverage_of_delta_lnL_interval"])

    def test_huge_mc_makes_the_variants_agree_and_seed_reproduces(self):
        out = st.template_bb(SIG, BKG, 400, 0.4, 2e4, 2e4, 200, 2)
        sp = [v["spread"] for v in out["variants"].values()]
        self.assertLess(max(sp) / min(sp), 1.1)
        self.assertEqual(out, st.template_bb(SIG, BKG, 400, 0.4, 2e4, 2e4, 200, 2))

    def test_rejections(self):
        for call in (lambda: st.template_bb("1", BKG, 100, 0.5, 50, 50, 200, 1),
                     lambda: st.template_bb(SIG, BKG, 100, -0.5, 50, 50, 200, 1),
                     lambda: st.template_bb(SIG, BKG, 100, 0.5, 50, 50, 200, None)):
            with self.assertRaises(st.ToyError):
                call()


class RatioCovTests(unittest.TestCase):
    DOC = {"numerator": [900, 700, 500, 300], "denominator": [3000, 2500, 2000, 1500]}

    def doc(self, kind, **kw):
        sysd = {"name": "x", "sigma_num": 0.03, "sigma_den": 0.0, "num_den_rho": 0.0, "bin_correlation": dict(kind=kind, **kw)}
        return dict(self.DOC, systematics=[sysd])

    def test_shared_systematic_is_underestimated_if_bins_are_assumed_independent(self):
        full = st.ratio_cov(self.doc("full"), 4000, 1)["weighted_mean_fractional_spread"]
        none = st.ratio_cov(self.doc("none"), 4000, 1)["weighted_mean_fractional_spread"]
        self.assertAlmostEqual(full["systematic_only"], 0.03, delta=0.002)
        self.assertGreater(full["underestimate_factor_if_independent"], 1.8)
        self.assertAlmostEqual(none["underestimate_factor_if_independent"], 1.0, delta=0.1)

    def test_exponential_correlation_is_between_and_decays(self):
        out = st.ratio_cov(self.doc("exponential", length=1.5), 4000, 1)
        c = out["systematic_correlation_between_bins"][0]
        self.assertGreater(c[1], c[3])
        self.assertAlmostEqual(c[1], math.exp(-1 / 1.5), delta=0.06)

    def test_cancellation_and_reproducibility(self):
        d = self.doc("full")
        d["systematics"][0].update(sigma_den=0.03, num_den_rho=1.0)
        self.assertLess(st.ratio_cov(d, 500, 1)["weighted_mean_fractional_spread"]["systematic_only"], 1e-9)
        self.assertEqual(st.ratio_cov(self.doc("none"), 300, 7), st.ratio_cov(self.doc("none"), 300, 7))

    def test_rejections(self):
        bad = [[1], {"numerator": [1.0], "denominator": [1.0]}, {"numerator": [1, 2], "denominator": [1]},
               dict(self.DOC, systematics=[{"sigma_num": 0.1}]),
               dict(self.DOC, systematics=[{"name": "x", "bin_correlation": {"kind": "weird"}}]),
               dict(self.DOC, systematics=[{"name": "x", "sigma_num": 2.0}]),
               dict(self.DOC, systematics=[{"name": "x", "sigma_num": [0.1, 0.1]}]),
               dict(self.DOC, systematics=[{"name": "x", "bin_correlation": {"kind": "exponential"}}])]
        for d in bad:
            with self.assertRaises(st.ToyError):
                st.ratio_cov(d, 200, 1)


class RatioMeasuredTests(unittest.TestCase):
    @staticmethod
    def doc(rho_x=0.0, rho_y=0.0, cross=0.0, rel=0.03, ratio=0.5):
        n = 4
        y = [200.0, 180.0, 150.0, 120.0]
        x = [ratio * v for v in y]
        sx, sy = [rel * v for v in x], [rel * v for v in y]
        c = [[0.0] * (2 * n) for _ in range(2 * n)]
        for i in range(n):
            for j in range(n):
                c[i][j] = sx[i] * sx[j] * (1.0 if i == j else rho_x)
                c[n + i][n + j] = sy[i] * sy[j] * (1.0 if i == j else rho_y)
                c[i][n + j] = c[n + j][i] = cross * sx[i] * sy[j] * (1.0 if i == j else 0.5)
        return {"numerator": x, "denominator": y, "covariance": c}

    def test_chi2_survival_function_known_values(self):
        self.assertAlmostEqual(st.chi2_sf(3.841459, 1), 0.05, places=5)
        self.assertAlmostEqual(st.chi2_sf(9.487729, 4), 0.05, places=5)
        self.assertAlmostEqual(st.chi2_sf(30.0, 10), 8.566e-4, delta=2e-6)
        self.assertEqual(st.chi2_sf(0.0, 3), 1.0)

    def test_independent_bins_diagonal_and_full_fits_agree_and_toys_match_chi2(self):
        out = st.ratio_measured(self.doc(), 6000, 1)
        full, diag = out["constant_ratio_fit_full_covariance"], out["constant_ratio_fit_diagonal_only"]
        self.assertAlmostEqual(out["sigma_ratio_diagonal_over_full"], 1.0, delta=0.02)
        self.assertAlmostEqual(full["value"], diag["value"], delta=1e-6)
        self.assertAlmostEqual(full["p_value_toys"], full["p_value_chi2"], delta=0.03)
        for v in out["toy_over_linear_sigma"]:
            self.assertAlmostEqual(v, 1.0, delta=0.03)

    def test_correlated_covariance_changes_the_fitted_sigma(self):
        # cross = 0.3 keeps the matrix positive definite (smallest correlation eigenvalue 0.05); the earlier fixture
        # used cross = 0.5 (eigenvalue -0.05), which only ran because the old Cholesky added jitter silently
        out = st.ratio_measured(self.doc(rho_x=0.8, rho_y=0.8, cross=0.3), 3000, 1)
        self.assertGreater(abs(out["sigma_ratio_diagonal_over_full"] - 1.0), 0.1)
        self.assertGreater(out["ratio_correlation_matrix_linear"][0][1], 0.3)

    def test_indefinite_covariance_is_rejected_and_named(self):
        with self.assertRaisesRegex(st.ToyError, "covariance is not positive semi-definite"):
            st.ratio_measured(self.doc(rho_x=0.8, rho_y=0.8, cross=0.5), 300, 1)

    def test_results_do_not_depend_on_the_units_of_the_covariance(self):
        base = self.doc(rho_x=0.8, rho_y=0.8, cross=0.3)
        ref = st.ratio_measured(base, 300, 2)
        for k in (1e-6, 1e6):  # numerator and denominator in other units: covariance scales by k^2 = 1e-12, 1e12
            doc = {"numerator": [v * k for v in base["numerator"]], "denominator": [v * k for v in base["denominator"]],
                   "covariance": [[v * k * k for v in row] for row in base["covariance"]]}
            out = st.ratio_measured(doc, 300, 2)
            for key in ("value", "sigma", "chi2"):
                a, b = out["constant_ratio_fit_full_covariance"][key], ref["constant_ratio_fit_full_covariance"][key]
                self.assertAlmostEqual(a, b, delta=1e-12 * max(1.0, abs(b)), msg=(k, key))
            self.assertNotIn("regularization", out)

    def test_semidefinite_covariance_is_sampled_with_the_shift_recorded(self):
        out = st.ratio_measured(self.doc(rho_y=1.0), 300, 1)  # denominators fully correlated: singular, still valid
        reg = out["regularization"][0]
        self.assertEqual(reg["matrix"], "covariance")
        self.assertGreaterEqual(reg["pivots_shifted"], 3)
        self.assertLessEqual(reg["max_shift_relative_to_unit_diagonal"], 1e-10)
        doc = self.doc()
        n = 4
        for i in range(n):  # numerator and denominator of each bin fully correlated: the ratio has no variance
            sx, sy = doc["covariance"][i][i] ** 0.5, doc["covariance"][n + i][n + i] ** 0.5
            doc["covariance"][i][n + i] = doc["covariance"][n + i][i] = sx * sy
        with self.assertRaisesRegex(st.ToyError, "linearized ratio covariance"):
            st.ratio_measured(doc, 300, 1)  # the constant fit needs an inverse; sampling alone would be fine

    def test_gls_constant_rejects_an_impossible_correlation(self):
        with self.assertRaisesRegex(st.ToyError, "not positive semi-definite"):
            st._gls_constant([1.0, 1.2], [[1.0, 2.0], [2.0, 1.0]])  # correlation 2 gave chi2 = 9e13 before
        mean, sigma, chi2 = st._gls_constant([1.0, 1.2], [[1.0, 0.5], [0.5, 1.0]])
        for k in (1e-12, 1e12):
            m2, s2, c2 = st._gls_constant([1.0, 1.2], [[k, 0.5 * k], [0.5 * k, k]])
            self.assertAlmostEqual(m2, mean, delta=1e-12)
            self.assertAlmostEqual(s2 / (sigma * k ** 0.5), 1.0, delta=1e-12)
            self.assertAlmostEqual(c2 * k / chi2, 1.0, delta=1e-12)

    def test_poorly_measured_denominator_shows_nonlinearity(self):
        out = st.ratio_measured(self.doc(rel=0.25), 6000, 1)
        self.assertGreater(max(abs(b) for b in out["toy_fractional_bias_of_mean"]), 0.01)

    def test_reproducible_and_rejections(self):
        self.assertEqual(st.ratio_measured(self.doc(), 300, 5), st.ratio_measured(self.doc(), 300, 5))
        good = self.doc()
        asym = json.loads(json.dumps(good))
        asym["covariance"][0][1] += 5.0
        neg = json.loads(json.dumps(good))
        neg["covariance"][0][0] = -1.0
        notpsd = json.loads(json.dumps(good))
        notpsd["covariance"][0][1] = notpsd["covariance"][1][0] = 10 * math.sqrt(notpsd["covariance"][0][0] * notpsd["covariance"][1][1])
        for d in (asym, neg, notpsd, dict(good, covariance=[[1.0]]), dict(good, denominator=[0.0, 1, 1, 1]),
                  dict(good, numerator=[1.0]), [1]):
            with self.assertRaises(st.ToyError):
                st.ratio_measured(d, 200, 1)
        with self.assertRaises(st.ToyError):
            st.ratio_measured(good, 200, None)


class UnfoldScanTests(unittest.TestCase):
    def test_identity_response_is_unbiased_at_one_iteration(self):
        doc = {"response": [[1, 0], [0, 1]], "truth": [500, 300], "max_iterations": 3}
        out = st.unfold_scan(doc, 300, 1)
        self.assertLess(out["scan"][0]["rms_relative_bias"], 0.02)

    def test_bias_falls_and_spread_grows_with_iterations(self):
        out = st.unfold_scan(RESPONSE, 300, 1)["scan"]
        self.assertGreater(out[0]["rms_relative_bias"], out[-1]["rms_relative_bias"])
        self.assertLess(out[0]["rms_relative_spread"], out[-1]["rms_relative_spread"])

    def test_transposed_orientation_gives_the_same_scan(self):
        t = dict(RESPONSE, response=[list(c) for c in zip(*RESPONSE["response"])], orientation="rows_truth_cols_reco")
        self.assertEqual(st.unfold_scan(t, 100, 4)["scan"], st.unfold_scan(RESPONSE, 100, 4)["scan"])

    def test_rejections(self):
        for bad in (dict(RESPONSE, response=[[0.6, 0.2], [0.2]]), dict(RESPONSE, truth=[1, 2]),
                    dict(RESPONSE, response=[[0.9, 0.2, 0.0], [0.9, 0.5, 0.2], [0.0, 0.2, 0.6]]),
                    dict(RESPONSE, max_iterations=0), dict(RESPONSE, orientation="sideways"),
                    dict(RESPONSE, response=[[0.0, 0.2, 0.0], [0.0, 0.5, 0.2], [0.0, 0.2, 0.6]]), [1, 2]):
            with self.assertRaises(st.ToyError):
                st.unfold_scan(bad, 100, 1)


class RatioTests(unittest.TestCase):
    def test_full_correlation_cancels_and_independence_adds(self):
        cancel = st.ratio_toys(4000, 9000, ["eff:0.05:0.05:1"], 6000, 1)
        indep = st.ratio_toys(4000, 9000, ["eff:0.05:0.05:0"], 6000, 1)
        self.assertLess(cancel["fractional_spread_systematic_only"], 1e-9)
        self.assertAlmostEqual(indep["fractional_spread_systematic_only"], 0.05 * math.sqrt(2), delta=0.004)
        self.assertAlmostEqual(cancel["fractional_spread_statistical_only"], math.sqrt(1 / 4000 + 1 / 9000), delta=0.002)

    def test_partial_correlation_analytic_value_and_reproducible(self):
        out = st.ratio_toys(400, 900, ["a:0.03:0.04:0.5"], 200, 3)
        self.assertAlmostEqual(out["systematics"][0]["fractional_effect_on_ratio_analytic"],
                               math.sqrt(0.03 ** 2 + 0.04 ** 2 - 2 * 0.5 * 0.03 * 0.04), places=12)
        self.assertEqual(out, st.ratio_toys(400, 900, ["a:0.03:0.04:0.5"], 200, 3))

    def test_rejections(self):
        for call in (lambda: st.ratio_toys(10, 0, [], 200, 1), lambda: st.ratio_toys(10, 20, ["a:0.1:0.1:1.5"], 200, 1),
                     lambda: st.ratio_toys(10, 20, ["a:0.1:0.1"], 200, 1), lambda: st.ratio_toys(10, 20, ["a:2:0.1:0"], 200, 1),
                     lambda: st.ratio_toys(10, 20, [], 10, 1), lambda: st.ratio_toys(10, 20, [], 200, True)):
            with self.assertRaises(st.ToyError):
                call()


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = st.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_each_subcommand_ok_and_echoes_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "u.json"
            path.write_text(json.dumps(RESPONSE))
            rpath = Path(tmp) / "r.json"
            rpath.write_text(json.dumps(RatioCovTests.DOC))
            mpath = Path(tmp) / "m.json"
            mpath.write_text(json.dumps(RatioMeasuredTests.doc()))
            for argv in (["boundary", "--n", "5", "--b", "3", "--toys", "200", "--seed", "4"],
                         ["template-stat", "--sig", SIG, "--bkg", BKG, "--n-data", "100", "--f", "0.3", "--mc-sig", "100",
                          "--mc-bkg", "100", "--toys", "100", "--seed", "4"],
                         ["unfold-scan", "--input", str(path), "--toys", "50", "--seed", "4"],
                         ["template-bb", "--sig", SIG, "--bkg", BKG, "--n-data", "100", "--f", "0.3", "--mc-sig", "100",
                          "--mc-bkg", "100", "--toys", "100", "--seed", "4"],
                         ["ratio-cov", "--input", str(rpath), "--toys", "100", "--seed", "4"],
                         ["ratio-measured", "--input", str(mpath), "--toys", "200", "--seed", "4"],
                         ["ratio-toys", "--n1", "50", "--n2", "80", "--sys", "x:0.02:0.02:1", "--toys", "200", "--seed", "4"]):
                code, out = self.run_cli(*argv)
                self.assertEqual((code, out["status"], out["seed"]), (0, "ok", 4), argv[0])
                self.assertEqual(out["label"], "[General method]")

    def test_seed_required_and_bad_input_exits_2(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            st.main(["boundary", "--n", "5", "--b", "3"])
        code, out = self.run_cli("boundary", "--n", "5", "--b", "0", "--seed", "1")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = self.run_cli("unfold-scan", "--input", "/nonexistent/x.json", "--seed", "1")
        self.assertEqual((code, out["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()

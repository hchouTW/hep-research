"""Tests for core/stats/ unfolding_diagnostics.py: linear-algebra helpers, the identities of the linear
unfolding matrices (A R = I at full rank, a projector under truncation), the bias-variance trend of the
regularized scan, closure and pull behavior, forward-fold versus unfold-then-fit, finite response
statistics, reproducibility, rejection and the CLI contract.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
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
from core.stats import unfolding_diagnostics as ud  # noqa: E402

N, SIGMA, EDGES = 4, 0.5, [1.0, 2.0, 4.0, 8.0, 16.0]


def make_doc(total=20000.0, gamma=2.7, gen=5000, test_tilt=0.0):
    r = [[0.0] * N for _ in range(N)]
    for j in range(N):
        z = sum(math.exp(-0.5 * ((k - j) / SIGMA) ** 2) for k in range(N))
        for i in range(N):
            r[i][j] = 0.8 * math.exp(-0.5 * ((i - j) / SIGMA) ** 2) / z
    w = [(EDGES[k] ** (1 - gamma) - EDGES[k + 1] ** (1 - gamma)) / (gamma - 1) for k in range(N)]
    truth = [total * x / sum(w) for x in w]
    return {"response": r, "truth": truth, "truth_edges": EDGES, "model": {"gamma": gamma},
            "mc_events_per_truth_bin": [gen] * N,
            "test_truth": [x * (1 + test_tilt * (k - 1.5) / 1.5) for k, x in enumerate(truth)]}


def identity_error(a, r):
    ar = ud._matmul(a, r)
    return max(abs(ar[i][j] - (1.0 if i == j else 0.0)) for i in range(N) for j in range(N))


class LinearAlgebraTests(unittest.TestCase):
    def test_solve_and_jacobi(self):
        a = [[4.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]]
        x = ud._solve(a, [[1.0], [2.0], [3.0]])
        back = ud._matmul(a, x)
        for got, want in zip(back, (1.0, 2.0, 3.0)):
            self.assertAlmostEqual(got[0], want, places=10)
        vals, vecs = ud._jacobi(a)
        for k in range(3):
            v = [vecs[i][k] for i in range(3)]
            av = [sum(a[i][j] * v[j] for j in range(3)) for i in range(3)]
            for i in range(3):
                self.assertAlmostEqual(av[i], vals[k] * v[i], places=8)

    def test_singular_solve_rejected(self):
        with self.assertRaises(ud.ToyError):
            ud._solve([[1.0, 2.0], [2.0, 4.0]], [[1.0], [1.0]])


class LinearMatrixTests(unittest.TestCase):
    def setUp(self):
        d = make_doc()
        self.r, self.mu = d["response"], ud._mu(d["response"], d["truth"])

    def test_full_rank_inverts_the_response(self):
        self.assertLess(identity_error(ud.linear_matrix("tsvd", N, self.r, self.mu), self.r), 1e-8)
        self.assertLess(identity_error(ud.linear_matrix("tikhonov", 1e-10, self.r, self.mu), self.r), 1e-4)

    def test_truncation_gives_a_projector(self):
        a = ud.linear_matrix("tsvd", 2, self.r, self.mu)
        p = ud._matmul(a, self.r)
        pp = ud._matmul(p, p)
        for i in range(N):
            for j in range(N):
                self.assertAlmostEqual(pp[i][j], p[i][j], places=8)
        self.assertGreater(identity_error(a, self.r), 0.05)


class ScanTests(unittest.TestCase):
    def test_tikhonov_trades_variance_for_bias(self):
        rows = ud.regularized_scan(make_doc(), "tikhonov", [1e-6, 1e-3, 1e-1], 50, 1)["scan"]
        self.assertLess(rows[0]["rms_relative_bias"], rows[2]["rms_relative_bias"])
        self.assertGreater(rows[0]["rms_relative_spread"], rows[2]["rms_relative_spread"])

    def test_tsvd_full_rank_is_unbiased_and_truncation_biases(self):
        rows = ud.regularized_scan(make_doc(), "tsvd", None, 50, 1)["scan"]
        self.assertLess(rows[-1]["rms_relative_bias"], 1e-6)
        self.assertGreater(rows[0]["rms_relative_bias"], 0.05)
        self.assertEqual(len(rows), N)

    def test_seed_reproducible_and_rejections(self):
        a = ud.regularized_scan(make_doc(), "tikhonov", [0.01], 30, 3)
        self.assertEqual(a, ud.regularized_scan(make_doc(), "tikhonov", [0.01], 30, 3))
        for call in (lambda: ud.regularized_scan(make_doc(), "dagostini", [1], 30, 1),
                     lambda: ud.regularized_scan(make_doc(), "tsvd", [0], 30, 1),
                     lambda: ud.regularized_scan(make_doc(), "tikhonov", [-1.0], 30, 1),
                     lambda: ud.regularized_scan(make_doc(), "tikhonov", [0.1], 30, None),
                     lambda: ud.regularized_scan({"response": [[1.0]]}, "tikhonov", [0.1], 30, 1)):
            with self.assertRaises(ud.ToyError):
                call()


class ClosureTests(unittest.TestCase):
    def test_full_rank_noise_free_closure_is_exact_and_pulls_are_unbiased(self):
        out = ud.closure(make_doc(), "tsvd", N, 600, 1)
        self.assertLess(out["closure_rms_relative_bias"], 1e-8)
        self.assertLess(out["max_abs_mean_pull"], 4.0 * out["mean_pull_standard_error"])
        self.assertAlmostEqual(out["mean_pull_width"], 1.0, delta=0.12)

    def test_model_dependence_shows_up_with_a_different_test_truth(self):
        same = ud.closure(make_doc(), "tikhonov", 0.05, 100, 1)
        diff = ud.closure(make_doc(test_tilt=0.5), "tikhonov", 0.05, 100, 1)
        self.assertFalse(same["test_truth_differs_from_model"])
        self.assertTrue(diff["test_truth_differs_from_model"])
        self.assertNotEqual(same["closure_relative_bias_per_bin"], diff["closure_relative_bias_per_bin"])

    def test_dagostini_closure_bias_falls_with_iterations(self):
        few = ud.closure(make_doc(test_tilt=0.5), "dagostini", 2, 50, 1)["closure_rms_relative_bias"]
        many = ud.closure(make_doc(test_tilt=0.5), "dagostini", 60, 50, 1)["closure_rms_relative_bias"]
        self.assertGreater(few, 3 * many)

    def test_dagostini_sigma_comes_from_toys(self):
        out = ud.closure(make_doc(), "dagostini", 3, 100, 1)
        self.assertIn("toys", out["sigma_source"])

    def test_rejections(self):
        for call in (lambda: ud.closure(dict(make_doc(), test_truth=[1.0]), "tsvd", 2, 100, 1),
                     lambda: ud.closure(make_doc(), "tsvd", 9, 100, 1), lambda: ud.closure(make_doc(), "dagostini", 0, 100, 1),
                     lambda: ud.closure(make_doc(), "bogus", 1, 100, 1)):
            with self.assertRaises(ud.ToyError):
                call()


class FoldCompareTests(unittest.TestCase):
    def test_both_routes_recover_the_index_and_forward_fold_is_unbiased(self):
        out = ud.fold_compare(make_doc(), "tikhonov", 1e-3, 80, 1)
        self.assertLess(abs(out["forward_fold_bias"]), 3 * out["forward_fold_spread"] / math.sqrt(out["toys_used"]) + 1e-3)
        self.assertLess(abs(out["unfold_then_fit_bias"]), 0.2)
        self.assertGreater(out["spread_ratio_unfold_over_fold"], 0.5)

    def test_rejections(self):
        for call in (lambda: ud.fold_compare(make_doc(), "dagostini", 3, 50, 1),
                     lambda: ud.fold_compare(dict(make_doc(), truth_edges=[1, 2]), "tsvd", 3, 50, 1),
                     lambda: ud.fold_compare(dict(make_doc(), truth_edges=[1, 3, 2, 4, 5]), "tsvd", 3, 50, 1),
                     lambda: ud.fold_compare(dict(make_doc(), model=None), "tsvd", 3, 50, 1)):
            with self.assertRaises(ud.ToyError):
                call()


class ResponseStatTests(unittest.TestCase):
    def test_response_share_falls_with_more_mc(self):
        small = ud.response_stat(make_doc(gen=300), "tikhonov", 1e-3, 100, 1)
        large = ud.response_stat(make_doc(gen=20000), "tikhonov", 1e-3, 100, 1)
        self.assertGreater(small["response_share_of_total_variance"], 3 * large["response_share_of_total_variance"])
        self.assertLess(large["response_share_of_total_variance"], 0.08)

    def test_dagostini_supported_and_rejections(self):
        out = ud.response_stat(make_doc(gen=1000), "dagostini", 3, 60, 1)
        self.assertGreater(out["rms_relative_spread_both"], 0.0)
        for call in (lambda: ud.response_stat(dict(make_doc(), mc_events_per_truth_bin=[1, 2]), "tikhonov", 0.1, 60, 1),
                     lambda: ud.response_stat(dict(make_doc(), mc_events_per_truth_bin=[0] * N), "tikhonov", 0.1, 60, 1)):
            with self.assertRaises(ud.ToyError):
                call()


class ChooseRegularizationTests(unittest.TestCase):
    def test_corner_of_a_synthetic_l_curve(self):
        # an L-shaped curve: residual rises while roughness is flat, then roughness falls steeply
        rho = [1.0, 1.1, 1.3, 10.0, 100.0]
        eta = [1000.0, 100.0, 10.0, 9.0, 8.0]
        self.assertIn(ud._corner(list(range(5)), rho, eta), (1, 2, 3))

    def test_effective_dof_falls_with_strength_and_toy_comparison_is_complete(self):
        out = ud.choose_regularization(make_doc(), "tikhonov", None, 60, 1)
        dof = [row["effective_dof_trace_hat"] for row in out["settings"]]
        self.assertEqual(dof, sorted(dof, reverse=True))
        self.assertAlmostEqual(dof[0], N, delta=0.05)
        self.assertEqual(set(out["criteria"]), {"gcv", "loo_cv", "l_curve_corner"} & set(out["criteria"]) | {"gcv", "loo_cv"})
        for v in out["criteria"].values():
            self.assertGreater(v["toy_mean_rms_relative_error"], 0.0)
        self.assertEqual(out["data"], "seeded pseudo-dataset drawn from the truth")

    def test_best_fixed_is_a_lower_bound_on_the_toy_error_and_reproducible(self):
        out = ud.choose_regularization(make_doc(), "tsvd", None, 60, 2)
        floor = out["toy_mean_rms_relative_error_best_fixed"]
        for v in out["criteria"].values():
            self.assertGreaterEqual(v["toy_mean_rms_relative_error"], floor - 1e-12)
        self.assertEqual(out, ud.choose_regularization(make_doc(), "tsvd", None, 60, 2))

    def test_supplied_data_and_rejections(self):
        d = make_doc()
        data = [int(v) for v in ud._mu(d["response"], d["truth"])]
        self.assertEqual(ud.choose_regularization(dict(d, data=data), "tikhonov", None, 30, 1)["data"], "supplied")
        for call in (lambda: ud.choose_regularization(d, "dagostini", None, 30, 1), lambda: ud.choose_regularization(d, "tikhonov", [0.1, 1.0], 30, 1),
                     lambda: ud.choose_regularization(dict(d, data=[1, 2]), "tikhonov", None, 30, 1),
                     lambda: ud.choose_regularization(d, "tsvd", [1, 2, 9], 30, 1), lambda: ud.choose_regularization(d, "tikhonov", None, 30, None)):
            with self.assertRaises(ud.ToyError):
                call()


class ResponseCovarianceTests(unittest.TestCase):
    def test_analytic_propagation_matches_the_toys(self):
        for method, param in (("tikhonov", 1e-3), ("dagostini", 4), ("tsvd", 3)):
            out = ud.response_covariance(make_doc(gen=3000), method, param, 150, 1)
            self.assertAlmostEqual(out["toy_check"]["analytic_over_toy_response"], 1.0, delta=0.12, msg=method)
            self.assertAlmostEqual(out["rms_relative_data"], out["toy_check"]["rms_relative_data_only"], delta=0.02, msg=method)

    def test_response_share_falls_with_more_mc_and_correlation_diagonal_is_one(self):
        small = ud.response_covariance(make_doc(gen=300), "tikhonov", 1e-3, 40, 1)
        large = ud.response_covariance(make_doc(gen=30000), "tikhonov", 1e-3, 40, 1)
        self.assertGreater(small["response_share_of_total_variance"], 10 * large["response_share_of_total_variance"])
        for i, row in enumerate(small["response_covariance_correlation"]):
            self.assertAlmostEqual(row[i], 1.0, places=9)

    def test_rejections(self):
        d = make_doc()
        for call in (lambda: ud.response_covariance(dict(d, mc_events_per_truth_bin=[1]), "tikhonov", 0.1, 30, 1),
                     lambda: ud.response_covariance(d, "bogus", 1, 30, 1), lambda: ud.response_covariance(d, "tikhonov", 0.1, 30, None)):
            with self.assertRaises(ud.ToyError):
                call()


class NonparamFoldTests(unittest.TestCase):
    def test_positive_bins_calibrated_laplace_error_and_small_bias_for_a_power_law(self):
        out = ud.nonparam_fold(make_doc(), 1.0, 0.001, 120, 1)
        self.assertEqual(out["toys_failed"], 0)
        self.assertEqual(out["forward_fold"]["fraction_negative_bins"], 0.0)
        self.assertAlmostEqual(out["forward_fold"]["laplace_over_toy_spread"], 1.0, delta=0.25)
        self.assertLess(out["forward_fold"]["rms_relative_bias"], 0.05)

    def test_stronger_penalty_trades_variance_for_bias(self):
        peaked = dict(make_doc(), truth=[2000.0, 9000.0, 3000.0, 600.0])  # not log-linear, so the penalty biases it
        weak = ud.nonparam_fold(peaked, 0.001, 0.001, 80, 1)["forward_fold"]
        strong = ud.nonparam_fold(peaked, 1000.0, 0.001, 80, 1)["forward_fold"]
        self.assertLess(strong["rms_relative_spread"], weak["rms_relative_spread"])
        self.assertGreater(strong["rms_relative_bias"], weak["rms_relative_bias"])

    def test_the_fit_recovers_the_expected_counts_exactly_without_noise(self):
        d = make_doc()
        mu = ud._mu(d["response"], d["truth"])
        t, cov, ok = ud._fold_fit(mu, d["response"], 1e-8)
        self.assertTrue(ok)
        for got, want in zip(t, d["truth"]):
            self.assertAlmostEqual(got / want, 1.0, delta=2e-3)

    def test_reproducible_and_rejections(self):
        self.assertEqual(ud.nonparam_fold(make_doc(), 1.0, 0.01, 30, 3), ud.nonparam_fold(make_doc(), 1.0, 0.01, 30, 3))
        for call in (lambda: ud.nonparam_fold(make_doc(), 0.0, 0.01, 30, 1), lambda: ud.nonparam_fold(make_doc(), 1.0, -1.0, 30, 1),
                     lambda: ud.nonparam_fold(make_doc(), 1.0, 0.01, 30, None)):
            with self.assertRaises(ud.ToyError):
                call()


def _fd(f, x, h=1e-6):
    return (f(x + h) - f(x - h)) / (2 * h)


class PriorTests(unittest.TestCase):
    def setUp(self):
        self.ltl1, self.ltl2 = ud._diff_ltl(N, 1), ud._diff_ltl(N, 2)
        self.lnm = [math.log(v) for v in (500.0, 700.0, 300.0, 200.0)]
        self.phi = [6.0, 6.5, 5.5, 5.0]

    def test_penalty_gradients_and_hessians_match_finite_differences(self):
        for kind in ("log_curvature", "log_slope", "entropy", "curvature"):
            val, grad, hess = ud._penalty(kind, 0.7, self.phi, self.ltl1, self.ltl2, self.lnm, 400.0)
            for j in range(N):
                def f(x, j=j):
                    ph = list(self.phi)
                    ph[j] = x
                    return ud._penalty(kind, 0.7, ph, self.ltl1, self.ltl2, self.lnm, 400.0)[0]

                def g(x, j=j):
                    ph = list(self.phi)
                    ph[j] = x
                    return ud._penalty(kind, 0.7, ph, self.ltl1, self.ltl2, self.lnm, 400.0)[1][j]
                self.assertAlmostEqual(_fd(f, self.phi[j], 1e-5), grad[j], delta=2e-4 * (1 + abs(grad[j])), msg=kind)
                self.assertAlmostEqual(_fd(g, self.phi[j], 1e-5), hess[j][j], delta=2e-4 * (1 + abs(hess[j][j])), msg=kind)
        self.assertEqual(ud._penalty("none", 5.0, self.phi, self.ltl1, self.ltl2, self.lnm, 400.0)[0], 0.0)

    def test_entropy_penalty_vanishes_at_the_default_model_and_curvature_at_a_line(self):
        m = [500.0, 700.0, 300.0, 200.0]
        self.assertAlmostEqual(ud._penalty("entropy", 2.0, [math.log(v) for v in m], self.ltl1, self.ltl2, self.lnm, 400.0)[0], 0.0, places=9)
        line = [math.log(v) for v in (100.0, 200.0, 300.0, 400.0)]
        self.assertAlmostEqual(ud._penalty("curvature", 2.0, line, self.ltl1, self.ltl2, self.lnm, 400.0)[0], 0.0, places=9)
        self.assertAlmostEqual(ud._penalty("log_slope", 2.0, [1.0] * N, self.ltl1, self.ltl2, self.lnm, 400.0)[0], 0.0, places=12)

    def test_every_prior_recovers_the_noise_free_expectation_at_a_tiny_strength(self):
        d = make_doc()
        mu = ud._mu(d["response"], d["truth"])
        for prior in ud.PRIORS:
            t, cov, ok = ud._fold_fit(mu, d["response"], 1e-8, prior=prior, model=[1.0] * N if prior == "entropy" else None)
            self.assertTrue(ok, prior)
            for got, want in zip(t, d["truth"]):
                self.assertAlmostEqual(got / want, 1.0, delta=5e-3, msg=prior)

    def test_strong_entropy_penalty_pulls_towards_the_default_model(self):
        d = make_doc()
        mu = ud._mu(d["response"], d["truth"])
        model = [1000.0] * N
        t, _, _ = ud._fold_fit(mu, d["response"], 1e4, prior="entropy", model=model)
        spread = max(t) / min(t)
        self.assertLess(spread, max(d["truth"]) / min(d["truth"]))

    def test_compare_priors_and_rejections(self):
        out = ud.compare_fold_priors(make_doc(), [("log_curvature", 1.0), ("log_slope", 1.0), ("entropy", 0.01)], 40, 1)
        self.assertEqual([r["prior"] for r in out["priors"]], ["log_curvature", "log_slope", "entropy"])
        self.assertIn(out["minimum_total"]["prior"], {"log_curvature", "log_slope", "entropy"})
        for call in (lambda: ud.compare_fold_priors(make_doc(), [("log_curvature", 1.0)], 40, 1),
                     lambda: ud.nonparam_fold(make_doc(), 1.0, 0.01, 30, 1, "weird"),
                     lambda: ud.nonparam_fold(dict(make_doc(), prior=[1.0, 2.0]), 1.0, 0.01, 30, 1, "entropy")):
            with self.assertRaises(ud.ToyError):
                call()
        self.assertEqual(ud.nonparam_fold(make_doc(), 1.0, 0.01, 30, 2, "log_slope")["prior"], "log_slope")


class PoissonCvTests(unittest.TestCase):
    def test_scan_structure_choice_and_excess(self):
        out = ud.choose_penalty_poisson(make_doc(), "log_curvature", [1e-3, 1e-1, 10.0, 1e3], 20, 1)
        scores = [row["cv_negative_log_likelihood"] for row in out["scan"]]
        self.assertEqual(out["chosen_on_these_data"], [1e-3, 1e-1, 10.0, 1e3][scores.index(min(scores))])
        self.assertGreaterEqual(out["excess_over_best_fixed"], -1e-9)
        self.assertEqual(out["data"], "seeded pseudo-dataset drawn from the truth")

    def test_a_penalty_much_too_strong_scores_worse_than_a_reasonable_one(self):
        d = dict(make_doc(), truth=[2000.0, 9000.0, 3000.0, 600.0])  # not a power law, so a huge log-curvature penalty is wrong
        data = [int(round(v)) for v in ud._mu(d["response"], d["truth"])]
        out = ud.choose_penalty_poisson(dict(d, data=data), "log_curvature", [1e-2, 1.0, 1e6], 20, 1)
        scores = [row["cv_negative_log_likelihood"] for row in out["scan"]]
        self.assertGreater(scores[-1], min(scores[:2]))
        self.assertEqual(out["data"], "supplied")

    def test_reproducible_and_rejections(self):
        self.assertEqual(ud.choose_penalty_poisson(make_doc(), "log_slope", [0.1, 1.0, 10.0], 20, 3),
                         ud.choose_penalty_poisson(make_doc(), "log_slope", [0.1, 1.0, 10.0], 20, 3))
        for call in (lambda: ud.choose_penalty_poisson(make_doc(), "log_slope", [0.1, 1.0], 20, 1),
                     lambda: ud.choose_penalty_poisson(make_doc(), "weird", [0.1, 1.0, 10.0], 20, 1),
                     lambda: ud.choose_penalty_poisson(make_doc(), "log_slope", [0.1, -1.0, 10.0], 20, 1),
                     lambda: ud.choose_penalty_poisson(dict(make_doc(), data=[1, 2]), "log_slope", [0.1, 1.0, 10.0], 20, 1),
                     lambda: ud.choose_penalty_poisson(make_doc(), "log_slope", [0.1, 1.0, 10.0], 20, None)):
            with self.assertRaises(ud.ToyError):
                call()


class MultinomialAndEfficiencyTests(unittest.TestCase):
    def test_multinomial_column_draw(self):
        import random
        rng = random.Random(3)
        draws = [ud._multinomial_column(rng, 1000, [0.5, 0.3]) for _ in range(300)]
        for k, p in enumerate((0.5, 0.3)):
            self.assertAlmostEqual(sum(d[k] for d in draws) / 300, 1000 * p, delta=6.0)
        self.assertTrue(all(sum(d) <= 1000 for d in draws))
        self.assertEqual(ud._multinomial_column(rng, 100, [1.0]), [100])
        self.assertEqual(ud._binomial_draw(rng, 0, 0.5), 0)
        big = [ud._binomial_draw(rng, 100000, 0.3) for _ in range(200)]
        self.assertAlmostEqual(sum(big) / 200, 30000, delta=100)

    def test_multinomial_analytic_matches_toys_and_is_below_independent_cells(self):
        d = make_doc(gen=3000)
        multi = ud.response_covariance(d, "tikhonov", 1e-3, 200, 1, "multinomial")
        pois = ud.response_covariance(d, "tikhonov", 1e-3, 40, 1, "poisson_cells")
        self.assertAlmostEqual(multi["toy_check"]["analytic_over_toy_response"], 1.0, delta=0.12)
        self.assertLess(multi["rms_relative_response"], pois["rms_relative_response"])
        self.assertEqual(multi["response_model"], "multinomial")

    def test_efficiency_systematic_is_exact_for_a_full_rank_inversion(self):
        d = dict(make_doc(), efficiency_uncertainty={"sigma": 0.02, "correlation": {"kind": "full"}})
        out = ud.response_covariance(d, "tsvd", N, 30, 1, "multinomial")
        for v in out["relative_sigma_efficiency_systematic_per_bin"]:
            self.assertAlmostEqual(v, 0.02, places=6)
        none = ud.response_covariance(dict(d, efficiency_uncertainty={"sigma": [0.01, 0.02, 0.03, 0.04], "correlation": {"kind": "none"}}),
                                      "tsvd", N, 30, 1)
        for got, want in zip(none["relative_sigma_efficiency_systematic_per_bin"], (0.01, 0.02, 0.03, 0.04)):
            self.assertAlmostEqual(got, want, places=6)
        self.assertGreater(out["rms_relative_total"], ud.response_covariance(make_doc(), "tsvd", N, 30, 1, "multinomial")["rms_relative_total"])

    def test_rejections(self):
        d = make_doc()
        for call in (lambda: ud.response_stat(d, "tikhonov", 0.1, 30, 1, "weird"),
                     lambda: ud.response_covariance(dict(d, efficiency_uncertainty=[1]), "tikhonov", 0.1, 30, 1),
                     lambda: ud.response_covariance(dict(d, efficiency_uncertainty={"sigma": [0.1]}), "tikhonov", 0.1, 30, 1),
                     lambda: ud.response_covariance(dict(d, efficiency_uncertainty={"sigma": 0.1, "correlation": {"kind": "weird"}}), "tikhonov", 0.1, 30, 1),
                     lambda: ud.response_covariance(dict(d, efficiency_uncertainty={"sigma": 2.0}), "tikhonov", 0.1, 30, 1)):
            with self.assertRaises(ud.ToyError):
                call()


def multinomial_cell_covariance(doc):
    r, gen = doc["response"], doc["mc_events_per_truth_bin"]
    n_r, n_t = len(r), len(r[0])
    cov = [[0.0] * (n_r * n_t) for _ in range(n_r * n_t)]
    for j in range(n_t):
        for i in range(n_r):
            for k in range(n_r):
                cov[i * n_t + j][k * n_t + j] = ((r[i][j] if i == k else 0.0) - r[i][j] * r[k][j]) / gen[j]
    return cov


def multinomial_replicas(doc, n=200, seed=3):
    import random
    rng = random.Random(seed)
    r, gen = doc["response"], doc["mc_events_per_truth_bin"]
    out = []
    for _ in range(n):
        m = [[0.0] * len(r[0]) for _ in r]
        for j in range(len(r[0])):
            ks = ud._multinomial_column(rng, int(gen[j]), [r[i][j] for i in range(len(r))])
            for i in range(len(r)):
                m[i][j] = ks[i] / gen[j]
        out.append(m)
    return out


class ResponseMeasuredTests(unittest.TestCase):
    def test_a_supplied_multinomial_covariance_reproduces_the_analytic_result(self):
        d = make_doc(gen=3000)
        meas = ud.response_measured(dict(d, response_covariance=multinomial_cell_covariance(d)), "tikhonov", 1e-3)
        ref = ud.response_covariance(d, "tikhonov", 1e-3, 30, 1, "multinomial")
        self.assertAlmostEqual(meas["rms_relative_response"], ref["rms_relative_response"], places=9)
        self.assertAlmostEqual(meas["rms_relative_data"], ref["rms_relative_data"], places=9)
        self.assertNotIn("replica_check", meas)

    def test_a_singular_supplied_covariance_is_accepted_and_reported(self):
        d = make_doc(gen=3000)
        cov = multinomial_cell_covariance(d)
        n = len(cov)
        dup = [[cov[0 if i == 1 else i][0 if j == 1 else j] for j in range(n)] for i in range(n)]  # cell 1 copies cell 0
        out = ud.response_measured(dict(d, response_covariance=dup), "tikhonov", 1e-3)
        self.assertEqual(out["response_covariance_check"]["singular_directions"], 1)

    def test_replicas_agree_with_first_order_propagation(self):
        d = make_doc(gen=3000)
        out = ud.response_measured(dict(d, response_replicas=multinomial_replicas(d)), "dagostini", 4)
        self.assertAlmostEqual(out["replica_check"]["analytic_over_replica"], 1.0, delta=0.12)
        self.assertLess(out["replica_check"]["rms_relative_shift_of_replica_mean_from_nominal"], 0.01)

    def test_rejections(self):
        d = make_doc()
        cov = multinomial_cell_covariance(d)
        asym = [row[:] for row in cov]
        asym[0][5] += 1.0
        neg = [row[:] for row in cov]
        neg[0][0] = -1.0
        notpsd = [row[:] for row in cov]
        notpsd[0][1] = notpsd[1][0] = 10.0
        reps = multinomial_replicas(d, 12)
        for bad in (d, dict(d, response_covariance=cov, response_replicas=reps), dict(d, response_covariance=[[1.0]]),
                    dict(d, response_covariance=asym), dict(d, response_covariance=neg), dict(d, response_covariance=notpsd),
                    dict(d, response_replicas=reps[:5]), dict(d, response_replicas=[[[1.0]]] * 12)):
            with self.assertRaises(ud.ToyError):
                ud.response_measured(bad, "tikhonov", 1e-3)
        with self.assertRaisesRegex(ud.ToyError, "response_covariance is not positive semi-definite"):
            ud.response_measured(dict(d, response_covariance=notpsd), "tikhonov", 1e-3)
        tiny = [[v * 1e-12 for v in row] for row in notpsd]  # no absolute jitter: the verdict does not depend on units
        with self.assertRaisesRegex(ud.ToyError, "not positive semi-definite"):
            ud.response_measured(dict(d, response_covariance=tiny), "tikhonov", 1e-3)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ud.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_each_subcommand_ok_and_bad_input_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "u.json"
            path.write_text(json.dumps(make_doc()))
            cpath = Path(tmp) / "c.json"
            cpath.write_text(json.dumps(dict(make_doc(), response_covariance=multinomial_cell_covariance(make_doc()))))
            for argv in (["regularized-scan", "--input", str(path), "--method", "tikhonov", "--values", "0.01,0.1", "--toys", "30", "--seed", "4"],
                         ["closure", "--input", str(path), "--method", "tsvd", "--param", "3", "--toys", "60", "--seed", "4"],
                         ["fold-compare", "--input", str(path), "--method", "tikhonov", "--param", "0.01", "--toys", "30", "--seed", "4"],
                         ["response-stat", "--input", str(path), "--method", "dagostini", "--param", "3", "--toys", "30", "--seed", "4"],
                         ["choose-regularization", "--input", str(path), "--method", "tikhonov", "--toys", "30", "--seed", "4"],
                         ["response-covariance", "--input", str(path), "--method", "tikhonov", "--param", "0.01", "--toys", "30", "--seed", "4"],
                         ["nonparam-fold", "--input", str(path), "--tau", "1", "--prior", "entropy", "--toys", "30", "--seed", "4"],
                         ["compare-fold-priors", "--input", str(path), "--priors", "log_curvature:1,log_slope:1", "--toys", "30", "--seed", "4"],
                         ["choose-penalty-poisson", "--input", str(path), "--taus", "0.1,1,10", "--toys", "20", "--seed", "4"],
                         ["response-stat", "--input", str(path), "--method", "tikhonov", "--param", "0.01", "--response-model", "multinomial", "--toys", "30", "--seed", "4"],
                         ["response-covariance", "--input", str(path), "--method", "tikhonov", "--param", "0.01", "--response-model", "multinomial", "--toys", "30", "--seed", "4"],
                         ["response-measured", "--input", str(cpath), "--method", "tikhonov", "--param", "0.01"]):
                code, out = self.run_cli(*argv)
                seed = out.get("seed", 4 if argv[0] == "response-measured" else None)  # response-measured has no randomness
                self.assertEqual((code, out["status"], seed, out["label"]), (0, "ok", 4, "[General method]"), argv[0])
            code, out = self.run_cli("closure", "--input", str(path), "--method", "tsvd", "--param", "9", "--seed", "1")
            self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = self.run_cli("closure", "--input", "/nonexistent.json", "--method", "tsvd", "--param", "2", "--seed", "1")
        self.assertEqual(code, 2)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            ud.main(["closure", "--input", "x.json", "--method", "tsvd", "--param", "2"])


if __name__ == "__main__":
    unittest.main()

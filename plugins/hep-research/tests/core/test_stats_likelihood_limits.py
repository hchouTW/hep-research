"""Tests for core/stats/ (ported from legacy ams-analysis tests): likelihood_limits.py: the toy-calibrated limit and p-value against the exact
Poisson results at sigma_b = 0, agreement between the single-bin analytic profile and the numeric
multi-bin profile, monotonic dependence on the background uncertainty, calibration of the
asymptotic limit, reproducibility, input rejection and the CLI contract.
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
from core.stats import likelihood_limits as ll  # noqa: E402


def doc(kind="none", sigma=None, bins=None):
    d = {"bins": bins or [{"n": 5, "b": 2.0, "s": 1.0}], "cl": 0.95}
    d["background_uncertainty"] = {"kind": kind} if sigma is None else {"kind": kind, "sigma": sigma}
    return d


class SingleBinTests(unittest.TestCase):
    def test_toy_limit_matches_exact_classical_and_asymptotic_undershoots(self):
        out = ll.profile_limit(5, 2.0, 0.0, 0.95, 3000, 1)
        self.assertAlmostEqual(out["toy_calibrated_upper_limit"], out["exact_classical_upper_limit"], delta=0.6)
        self.assertLess(out["asymptotic_upper_limit"], out["exact_classical_upper_limit"])

    def test_limit_grows_with_background_uncertainty(self):
        a = ll.profile_limit(5, 3.0, 0.0, 0.95, 200, 1)["asymptotic_upper_limit"]
        b = ll.profile_limit(5, 3.0, 1.0, 0.95, 200, 1)["asymptotic_upper_limit"]
        c = ll.profile_limit(5, 3.0, 2.0, 0.95, 200, 1)["asymptotic_upper_limit"]
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_significance_toys_match_exact_tail_and_wilks_doubles(self):
        out = ll.profile_significance(15, 8.0, 0.0, 20000, 1)
        self.assertGreater(out["q0_observed"], 4.0)
        self.assertAlmostEqual(out["p_value_toys"], out["p_value_exact_poisson"], delta=0.005)
        self.assertAlmostEqual(out["p_value_naive_wilks_chi2_1dof"], 2 * out["p_value_half_chi2_asymptotic"], places=12)

    def test_significance_with_nuisance_is_weaker_and_agrees_with_asymptotic(self):
        known = ll.profile_significance(15, 8.0, 0.0, 2000, 1)["q0_observed"]
        out = ll.profile_significance(15, 8.0, 2.0, 20000, 1)
        self.assertLess(out["q0_observed"], known)
        self.assertAlmostEqual(out["p_value_toys"], out["p_value_half_chi2_asymptotic"], delta=0.012)

    def test_underfluctuation_gives_q0_zero(self):
        out = ll.profile_significance(4, 8.0, 1.0, 500, 2)
        self.assertEqual((out["q0_observed"], out["p_value_toys"]), (0.0, 1.0))

    def test_seed_reproducible(self):
        self.assertEqual(ll.profile_limit(4, 2.0, 1.0, 0.95, 300, 5), ll.profile_limit(4, 2.0, 1.0, 0.95, 300, 5))

    def test_rejections(self):
        for call in (lambda: ll.profile_limit(-1, 1.0, 0.0, 0.95, 200, 1), lambda: ll.profile_limit(1, -1.0, 0.0, 0.95, 200, 1),
                     lambda: ll.profile_limit(1, 1.0, -1.0, 0.95, 200, 1), lambda: ll.profile_limit(1, 1.0, 0.0, 1.0, 200, 1),
                     lambda: ll.profile_limit(1, 1.0, 0.0, 0.95, 10, 1), lambda: ll.profile_limit(1, 1.0, 0.0, 0.95, 200, None),
                     lambda: ll.profile_significance(3, 0.0, 0.0, 200, 1)):
            with self.assertRaises(ll.LikelihoodError):
                call()


class MultiBinTests(unittest.TestCase):
    def test_one_bin_matches_the_analytic_profile(self):
        single0 = ll.profile_limit(5, 2.0, 0.0, 0.95, 100, 1)["asymptotic_upper_limit"]
        self.assertAlmostEqual(ll.multibin_limit(doc("none"), 0.95, 0, 1)["asymptotic_observed_upper_limit"], single0, delta=2e-3)
        single1 = ll.profile_limit(5, 3.0, 1.0, 0.95, 100, 1)["asymptotic_upper_limit"]
        bins = [{"n": 5, "b": 3.0, "s": 1.0}]
        ind = ll.multibin_limit(doc("independent", [1.0], bins), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        com = ll.multibin_limit(doc("common_scale", 1.0 / 3.0, bins), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        self.assertAlmostEqual(ind, single1, delta=2e-3)
        self.assertAlmostEqual(com, single1, delta=5e-3)

    def test_nuisance_loosens_the_limit_and_expected_is_below_observed_for_an_excess(self):
        bins = [{"n": 8, "b": 6.0, "s": 1.0}, {"n": 12, "b": 10.0, "s": 2.0}, {"n": 20, "b": 18.0, "s": 1.0}]
        none = ll.multibin_limit(doc("none", None, bins), 0.95, 0, 1)
        common = ll.multibin_limit(doc("common_scale", 0.2, bins), 0.95, 0, 1)
        self.assertLess(none["asymptotic_observed_upper_limit"], common["asymptotic_observed_upper_limit"])
        self.assertLess(none["asymptotic_asimov_median_expected_limit"], none["asymptotic_observed_upper_limit"])
        self.assertGreater(none["best_fit_mu"], 0.0)

    def test_toy_p_value_at_the_asymptotic_limit_is_near_the_target(self):
        bins = [{"n": 8, "b": 6.0, "s": 1.0}, {"n": 12, "b": 10.0, "s": 2.0}, {"n": 20, "b": 18.0, "s": 1.0}]
        out = ll.multibin_limit(doc("independent", [1.5, 2.0, 3.0], bins), 0.95, 300, 1)
        self.assertAlmostEqual(out["toy_p_value_at_asymptotic_limit"], 0.05, delta=0.05)

    def test_rejections(self):
        bad = [[1, 2], {"bins": []}, {"bins": [{"n": 1, "b": 1.0, "s": 0.0}]}, {"bins": [{"n": -1, "b": 1.0, "s": 1.0}]},
               {"bins": [{"n": 1, "b": 1.0, "s": 1.0}], "background_uncertainty": {"kind": "weird"}},
               {"bins": [{"n": 1, "b": 1.0, "s": 1.0}], "background_uncertainty": {"kind": "independent", "sigma": [1, 2]}},
               {"bins": [{"n": 1, "b": 1.0, "s": 1.0}], "background_uncertainty": {"kind": "common_scale", "sigma": 0}},
               {"bins": [{"n": 1000, "b": 1.0, "s": 1.0}]}]
        for d in bad:
            with self.assertRaises(ll.LikelihoodError):
                ll.multibin_limit(d, 0.95, 0, 1)


from core.stats import poisson_diagnostics as pd  # noqa: E402

SHAPE = {"bins": [{"n": 4, "b": 3.0, "s": 1.0}, {"n": 9, "b": 7.0, "s": 2.0}, {"n": 14, "b": 13.0, "s": 1.5}, {"n": 6, "b": 6.0, "s": 0.5}],
         "cl": 0.95,
         "nuisances": [{"name": "bkg_norm", "kind": "background_norm", "sigma": 0.15},
                       {"name": "sig_norm", "kind": "signal_norm", "sigma": 0.1},
                       {"name": "bkg_shape", "kind": "background_shape", "up": [3.5, 7.5, 12.0, 5.5], "down": [2.5, 6.5, 14.0, 6.5]},
                       {"name": "sig_shape", "kind": "signal_shape", "up": [1.2, 1.8, 1.5, 0.5], "down": [0.8, 2.2, 1.5, 0.5]}]}


class ProfileFcTests(unittest.TestCase):
    def test_known_background_reduces_to_feldman_cousins(self):
        out = ll.profile_fc(3, 3.0, 0.0, 0.90, 2000, 1)
        ref = pd.fc_interval(3, 3.0, 0.90, 0.02)
        self.assertEqual(out["lower"], 0.0)
        self.assertAlmostEqual(out["upper"], ref["upper"], delta=0.4)
        self.assertEqual(out["disjoint_segments"], 1)

    def test_a_clear_excess_has_a_positive_lower_edge_and_nuisance_widens_it(self):
        known = ll.profile_fc(20, 5.0, 0.0, 0.90, 1500, 1)
        wide = ll.profile_fc(20, 5.0, 2.0, 0.90, 1500, 1)
        self.assertGreater(known["lower"], 5.0)
        self.assertLess(wide["lower"], known["lower"] + 0.5)
        self.assertGreater(wide["upper"] - wide["lower"], known["upper"] - known["lower"] - 0.5)

    def test_reproducible_and_rejections(self):
        self.assertEqual(ll.profile_fc(3, 2.0, 1.0, 0.9, 300, 2), ll.profile_fc(3, 2.0, 1.0, 0.9, 300, 2))
        for call in (lambda: ll.profile_fc(-1, 2.0, 1.0, 0.9, 300, 1), lambda: ll.profile_fc(3, 2.0, 1.0, 1.0, 300, 1),
                     lambda: ll.profile_fc(3, 2.0, 1.0, 0.9, 300, None), lambda: ll.profile_fc(3, 2.0, 1.0, 0.9, 300, 1, 0.0)):
            with self.assertRaises(ll.LikelihoodError):
                call()


class ProfileClsTests(unittest.TestCase):
    def test_known_background_matches_the_exact_cls_limit(self):
        out = ll.profile_cls(3, 3.0, 0.0, 0.95, 3000, 0, 1)
        self.assertAlmostEqual(out["observed_upper_limit"], pd.cls_limit(3, 3.0, 0.95)["observed_upper_limit"], delta=0.6)
        self.assertNotIn("expected_under_background_only", out)

    def test_expected_band_is_ordered(self):
        band = ll.profile_cls(3, 3.0, 1.0, 0.95, 400, 20, 1)["expected_under_background_only"]
        order = [band[k] for k in ("-2sigma", "-1sigma", "median", "+1sigma", "+2sigma")]
        self.assertEqual(order, sorted(order))

    def test_rejections(self):
        for call in (lambda: ll.profile_cls(3, 3.0, 0.0, 0.95, 300, 5, 1), lambda: ll.profile_cls(3, 3.0, 0.0, 0.95, 300, -1, 1),
                     lambda: ll.profile_cls(3, 3.0, -1.0, 0.95, 300, 0, 1)):
            with self.assertRaises(ll.LikelihoodError):
                call()


class ShapeLimitTests(unittest.TestCase):
    def test_newton_minimizer_finds_the_quadratic_minimum(self):
        # f = (x-1)^2 + 3 (y+2)^2 + 0.5 x y has its minimum at y = -12.5 / 5.875, x = 1 - y / 4
        y_star = -12.5 / 5.875
        x, _ = ll._newton_min(lambda p: (p[0] - 1.0) ** 2 + 3 * (p[1] + 2.0) ** 2 + 0.5 * p[0] * p[1], [0.0, 0.0])
        self.assertAlmostEqual(x[1], y_star, places=5)
        self.assertAlmostEqual(x[0], 1.0 - 0.25 * y_star, places=5)

    def test_no_nuisance_matches_the_counting_model(self):
        none = ll.multibin_limit(doc("none", None, SHAPE["bins"]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        out = ll.shape_limit(dict(SHAPE, nuisances=[]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        self.assertAlmostEqual(out, none, delta=5e-3)

    def test_normalization_nuisance_matches_the_common_scale_model(self):
        ref = ll.multibin_limit(doc("common_scale", 0.15, SHAPE["bins"]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        out = ll.shape_limit(dict(SHAPE, nuisances=[SHAPE["nuisances"][0]]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        self.assertAlmostEqual(out, ref, delta=2e-2)

    def test_more_nuisances_loosen_the_limit_and_shapes_matter(self):
        none = ll.shape_limit(dict(SHAPE, nuisances=[]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        norm = ll.shape_limit(dict(SHAPE, nuisances=SHAPE["nuisances"][:2]), 0.95, 0, 1)["asymptotic_observed_upper_limit"]
        full = ll.shape_limit(SHAPE, 0.95, 0, 1)
        self.assertLess(none, norm)
        self.assertGreater(full["asymptotic_observed_upper_limit"], none)
        self.assertNotAlmostEqual(full["asymptotic_observed_upper_limit"], norm, places=3)
        self.assertLess(full["asymptotic_asimov_median_expected_limit"], full["asymptotic_observed_upper_limit"] + 1.0)

    def test_toy_p_value_near_the_target_and_reproducible(self):
        out = ll.shape_limit(SHAPE, 0.95, 100, 1)
        self.assertLess(abs(out["toy_p_value_at_asymptotic_limit"] - 0.05), 0.08)
        self.assertEqual(out, ll.shape_limit(SHAPE, 0.95, 100, 1))

    def test_rejections(self):
        base = SHAPE["bins"]
        bad = [{"bins": base, "nuisances": [{"kind": "weird"}]},
               {"bins": base, "nuisances": [{"kind": "background_norm", "sigma": 0.0}]},
               {"bins": base, "nuisances": [{"kind": "background_shape", "up": [1, 2], "down": [1, 2]}]},
               {"bins": base, "nuisances": [{"kind": "background_norm", "sigma": 0.1}] * 9},
               {"bins": base, "nuisances": "x"}, {"bins": []}, [1]]
        for d in bad:
            with self.assertRaises(ll.LikelihoodError):
                ll.shape_limit(d, 0.95, 0, 1)


def with_priors(prior=None, correlation=None, kinds=("background_norm", "signal_norm")):
    d = json.loads(json.dumps(SHAPE))
    d["nuisances"] = [dict(n) for n in SHAPE["nuisances"][:2]]
    for n in d["nuisances"]:
        if prior:
            n["prior"] = prior
    if correlation is not None:
        d["correlation"] = correlation
    return d


class PriorTests(unittest.TestCase):
    def limit(self, d):
        return ll.shape_limit(d, 0.95, 0, 1)["asymptotic_observed_upper_limit"]

    def test_lognormal_and_gamma_agree_with_gaussian_for_small_widths(self):
        g = self.limit(with_priors("gaussian"))
        self.assertAlmostEqual(self.limit(with_priors("lognormal")), g, delta=0.1)
        self.assertAlmostEqual(self.limit(with_priors("gamma")), g, delta=0.1)

    def test_a_wide_lognormal_differs_from_a_wide_gaussian(self):
        wide_g, wide_l = with_priors("gaussian"), with_priors("lognormal")
        for d in (wide_g, wide_l):
            d["nuisances"][0]["sigma"] = 0.7
        self.assertNotAlmostEqual(self.limit(wide_g), self.limit(wide_l), places=2)

    def test_correlation_constraint_is_the_quadratic_form(self):
        d = with_priors(None, [[1.0, 0.6], [0.6, 1.0]])
        bins, nuis, chol = ll._load_shape(d)
        m = ll._ShapeModel(bins, nuis, chol)
        th = [0.7, -0.4]
        cinv_form = (th[0] ** 2 - 2 * 0.6 * th[0] * th[1] + th[1] ** 2) / (1 - 0.36)
        self.assertAlmostEqual(m.constraint(th, [0.0, 0.0]), 0.5 * cinv_form, places=10)

    def test_gamma_constraint_has_its_mode_at_zero_and_the_right_curvature(self):
        bins, nuis, chol = ll._load_shape(with_priors("gamma"))
        m = ll._ShapeModel(bins, nuis, chol)
        aux = m.aux_obs()
        self.assertAlmostEqual(aux[0], 1.0 / 0.15 ** 2)
        at0 = m.constraint([0.0, 0.0], aux)
        self.assertLess(at0, m.constraint([0.3, 0.0], aux))
        self.assertLess(at0, m.constraint([-0.3, 0.0], aux))
        eps = 1e-3
        curv = (m.constraint([eps, 0.0], aux) - 2 * at0 + m.constraint([-eps, 0.0], aux)) / eps ** 2
        self.assertAlmostEqual(curv, 1.0, delta=0.02)  # unit curvature at the mode, like a unit Gaussian

    def test_correlation_changes_the_result_and_toys_stay_calibrated(self):
        base = self.limit(with_priors())
        corr = self.limit(with_priors(None, [[1.0, 0.8], [0.8, 1.0]]))
        self.assertNotAlmostEqual(base, corr, places=2)
        out = ll.shape_limit(with_priors("gamma"), 0.95, 100, 1)
        self.assertLess(abs(out["toy_p_value_at_asymptotic_limit"] - 0.05), 0.08)
        self.assertEqual(out["priors"], {"bkg_norm": "gamma", "sig_norm": "gamma"})
        out = ll.shape_limit(with_priors(None, [[1.0, 0.8], [0.8, 1.0]]), 0.95, 100, 1)
        self.assertTrue(out["correlated_nuisances"])
        self.assertLess(abs(out["toy_p_value_at_asymptotic_limit"] - 0.05), 0.08)

    def test_rejections(self):
        for d in (with_priors("weird"), with_priors("gamma", [[1.0, 0.5], [0.5, 1.0]]), with_priors(None, [[1.0, 0.5, 0.0], [0.5, 1.0, 0.0]]),
                  with_priors(None, [[1.0, 0.5], [0.4, 1.0]]), with_priors(None, [[2.0, 0.5], [0.5, 1.0]]),
                  with_priors(None, [[1.0, 1.0], [1.0, 1.0]]), with_priors(None, [[1.0, 1.5], [1.5, 1.0]])):
            with self.assertRaises(ll.LikelihoodError):
                ll.shape_limit(d, 0.95, 0, 1)


class NeymanTests(unittest.TestCase):
    def test_known_background_equals_the_plug_in_and_a_nuisance_lengthens_the_limit(self):
        a = ll.neyman_limit(3, 3.0, 0.0, 0.95, 0.01, 1500, 1)
        self.assertAlmostEqual(a["berger_boos_upper_limit"], a["plug_in_profile_upper_limit"], delta=0.05)
        b = ll.neyman_limit(3, 3.0, 2.0, 0.95, 0.01, 800, 1)
        self.assertGreater(b["berger_boos_upper_limit"], b["plug_in_profile_upper_limit"])
        self.assertGreater(b["ratio_berger_boos_over_plug_in"], 1.02)
        lo, hi = b["nuisance_range"]
        self.assertLess(lo, 3.0)
        self.assertGreater(hi, 3.0)

    def test_supremum_coverage_is_at_least_nominal_and_not_below_the_plug_in(self):
        out = ll.neyman_coverage(4.0, 5.0, 3.0, 0.95, 0.01, 300, 200, 1, 7)
        self.assertGreater(out["coverage_berger_boos"], 0.95 - 3 * out["binomial_error_berger_boos"])
        self.assertGreaterEqual(out["coverage_berger_boos"], out["coverage_plug_in_profile"] - 0.01)

    def test_reproducible_and_rejections(self):
        self.assertEqual(ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.01, 200, 4, 5), ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.01, 200, 4, 5))
        for call in (lambda: ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.06, 200, 1), lambda: ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.0, 200, 1),
                     lambda: ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.01, 200, 1, 2), lambda: ll.neyman_limit(3, 2.0, 1.0, 0.95, 0.01, 200, None),
                     lambda: ll.neyman_limit(-1, 2.0, 1.0, 0.95, 0.01, 200, 1),
                     lambda: ll.neyman_coverage(2.0, 3.0, 1.0, 0.95, 0.01, 10, 200, 1), lambda: ll.neyman_coverage(2.0, 3.0, 1.0, 0.95, 0.01, 100, 100, None),
                     lambda: ll.neyman_coverage(2.0, 3.0, 1.0, 0.95, 0.06, 100, 100, 1)):
            with self.assertRaises(ll.LikelihoodError):
                call()


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ll.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_subcommands_ok_and_seed_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            path.write_text(json.dumps(doc("none")))
            spath = Path(tmp) / "s.json"
            spath.write_text(json.dumps(SHAPE))
            for argv in (["profile-limit", "--n", "3", "--b", "2", "--toys", "200", "--seed", "4"],
                         ["profile-significance", "--n", "9", "--b", "4", "--toys", "200", "--seed", "4"],
                         ["multibin-limit", "--input", str(path), "--toys", "100", "--seed", "4"],
                         ["profile-fc", "--n", "3", "--b", "2", "--toys", "200", "--seed", "4"],
                         ["profile-cls", "--n", "3", "--b", "2", "--toys", "200", "--expected-toys", "10", "--seed", "4"],
                         ["shape-limit", "--input", str(spath), "--toys", "100", "--seed", "4"],
                         ["neyman-limit", "--n", "3", "--b", "2", "--sigma-b", "1", "--toys", "200", "--seed", "4"],
                         ["neyman-coverage", "--s", "2", "--b", "2", "--sigma-b", "1", "--outer", "50", "--inner", "100", "--seed", "4"]):
                code, out = self.run_cli(*argv)
                self.assertEqual((code, out["status"], out["seed"], out["label"]), (0, "ok", 4, "[General method]"), argv[0])

    def test_bad_input_exits_2_and_seed_required(self):
        code, out = self.run_cli("profile-limit", "--n", "-1", "--b", "2", "--seed", "1")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out = self.run_cli("multibin-limit", "--input", "/nonexistent.json", "--seed", "1")
        self.assertEqual(code, 2)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            ll.main(["profile-limit", "--n", "1", "--b", "1"])


if __name__ == "__main__":
    unittest.main()

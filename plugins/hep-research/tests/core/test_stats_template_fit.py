"""Tests for core/stats/ template_fit.py: the Nelder-Mead search, the closed-form single-bin
Barlow-Beeston value, the error inflation of the full Barlow-Beeston fit relative to the naive fit,
its disappearance for a huge MC sample, calibration of pulls in toys, reproducibility, input
rejection and the CLI contract.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import io
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import template_fit as tf  # noqa: E402


def _pois(rng, mu):
    if mu > 300:
        return max(0, round(rng.gauss(mu, math.sqrt(mu))))
    limit, k, p = math.exp(-mu), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def make_doc(mc=150, seed=5, bins=8, yields=(300, 500, 200)):
    rng = random.Random(seed)
    norm = lambda v: [x / sum(v) for x in v]
    shapes = {"sig": norm([math.exp(-0.5 * ((i - 5) / 1.2) ** 2) for i in range(bins)]),
              "bkg": norm([math.exp(-0.35 * i) for i in range(bins)]),
              "oth": norm([math.exp(-0.5 * ((i - 1.5) / 1.0) ** 2) for i in range(bins)])}
    tm = {k: [_pois(rng, mc * x) for x in v] for k, v in shapes.items()}
    data = [_pois(rng, sum(y * shapes[k][i] for k, y in zip(shapes, yields))) for i in range(bins)]
    return {"data": data, "templates": tm, "true_yields": dict(zip(shapes, yields))}


class MinimizerAndLikelihoodTests(unittest.TestCase):
    def test_nelder_mead_finds_a_quadratic_minimum(self):
        x, val = tf._nelder_mead(lambda p: (p[0] - 3.0) ** 2 + 2 * (p[1] + 1.0) ** 2, [0.0, 0.0], [1.0, 1.0])
        self.assertAlmostEqual(x[0], 3.0, places=3)
        self.assertAlmostEqual(x[1], -1.0, places=3)

    def test_single_bin_barlow_beeston_closed_form(self):
        # n = 10, m = 20, M = 100, Y = 50: A = 0.5 and the multiplier is t = 0, so a = m and nu = 10
        want = 10 * math.log(10) - 10 + (20 * math.log(20) - 20)
        self.assertAlmostEqual(tf._ll_bb([10], [[20]], [100], [50.0]), want, places=9)

    def test_barlow_beeston_reduces_to_naive_for_a_huge_mc_sample(self):
        # large MC: the profiled likelihood differs from the naive one only by a constant in the yields
        data, m, mc = [30, 50, 20], [[2e6, 3e6, 1e6], [1e6, 1e6, 3e6]], [6e6, 5e6]
        a = [tf._ll_bb(data, m, mc, y) - tf._ll_naive(data, m, mc, y) for y in ([40.0, 60.0], [20.0, 80.0], [70.0, 30.0])]
        self.assertAlmostEqual(a[0], a[1], delta=2e-2)
        self.assertAlmostEqual(a[0], a[2], delta=2e-2)


class FitTests(unittest.TestCase):
    def test_bb_errors_exceed_naive_errors_and_yields_are_recovered(self):
        out = tf.bb_fit(make_doc())
        for name, true in (("sig", 300), ("bkg", 500), ("oth", 200)):
            self.assertGreater(out["error_inflation_bb_over_naive"][name], 1.3)
            bb = out["barlow_beeston"][name]
            self.assertLess(abs(bb["yield"] - true), 4 * bb["error"])

    def test_no_inflation_for_a_huge_mc_sample(self):
        out = tf.bb_fit(make_doc(mc=40000, bins=6))
        for v in out["error_inflation_bb_over_naive"].values():
            self.assertAlmostEqual(v, 1.0, delta=0.05)

    def test_toys_calibrate_the_full_fit_and_not_the_naive_one(self):
        doc = make_doc(mc=100, bins=6, yields=(300, 500, 200))
        doc["templates"].pop("oth")
        doc["true_yields"] = {"sig": 300, "bkg": 500}
        doc["data"] = make_doc(mc=100, bins=6, yields=(300, 500, 0))["data"]
        out = tf.bb_toys(doc, 100, 1)["fits"]
        for name in ("sig", "bkg"):
            self.assertGreater(out["naive"][name]["pull_width_robust_mad"], 1.35)
            self.assertAlmostEqual(out["barlow_beeston"][name]["pull_width_robust_mad"], 1.0, delta=0.3)
            self.assertGreater(out["barlow_beeston"][name]["coverage_1sigma"], out["naive"][name]["coverage_1sigma"])

    def test_seed_reproducible(self):
        doc = make_doc(bins=5)
        doc["templates"].pop("oth")
        doc["true_yields"] = {"sig": 300, "bkg": 500}
        self.assertEqual(tf.bb_toys(doc, 30, 4), tf.bb_toys(doc, 30, 4))

    def test_rejections(self):
        good = make_doc(bins=4)
        bad = [[1], dict(good, data=[1]), dict(good, data=[1, 2, 3]), dict(good, templates={}),
               dict(good, templates={"a": [1, 2, 3, 4], "b": [0, 0, 0, 0]}),
               dict(good, mc_events={"sig": 1}),
               dict(good, templates={f"t{k}": [1, 2, 3, 4] for k in range(7)}),
               dict(good, templates={"a": [1, 2, 3]})]
        for d in bad:
            with self.assertRaises(tf.ToyError):
                tf.bb_fit(d)
        with self.assertRaises(tf.ToyError):
            tf.bb_toys(dict(good, true_yields={"sig": 1}), 50, 1)
        with self.assertRaises(tf.ToyError):
            tf.bb_toys(good, 50, None)


def make_weighted(seed=11, bins=6, nev=(400, 500), yields=(250, 500), nuisances=True):
    rng = random.Random(seed)
    norm = lambda v: [x / sum(v) for x in v]
    sig = norm([math.exp(-0.5 * ((i - 3.5) / 1.0) ** 2) for i in range(bins)])
    bkg = norm([math.exp(-0.4 * i) for i in range(bins)])

    def mc(shape, n):
        sw, sw2 = [0.0] * bins, [0.0] * bins
        for _ in range(n):
            u, acc, k = rng.random(), 0.0, bins - 1
            for i, pr in enumerate(shape):
                acc += pr
                if u <= acc:
                    k = i
                    break
            w = rng.gammavariate(2, 0.5)
            sw[k] += w
            sw2[k] += w * w
        return sw, sw2
    sws, sw2s = mc(sig, nev[0])
    swb, sw2b = mc(bkg, nev[1])
    ts, tb = sum(sws), sum(swb)
    data = [_pois(rng, yields[0] * sws[i] / ts + yields[1] * swb[i] / tb) for i in range(bins)]
    doc = {"data": data, "templates": {"sig": {"sumw": sws, "sumw2": sw2s}, "bkg": {"sumw": swb, "sumw2": sw2b}},
           "true_yields": {"sig": yields[0], "bkg": yields[1]}}
    if nuisances:
        tilt = [(i - 2.5) / 2.5 for i in range(bins)]
        doc["nuisances"] = [
            {"name": "shape_sig", "kind": "shape", "template": "sig", "up": [sws[i] * (1 + 0.15 * tilt[i]) for i in range(bins)],
             "down": [sws[i] * (1 - 0.15 * tilt[i]) for i in range(bins)]},
            {"name": "norm_bkg", "kind": "norm", "template": "bkg", "sigma": 0.05}]
    return doc


class WeightedFitTests(unittest.TestCase):
    def test_unit_weights_reproduce_the_unweighted_likelihood_exactly(self):
        d = make_doc(bins=5)
        d["templates"].pop("oth")
        names, data, w, c, t_tot, nuis = tf._load_w(d)
        mc = [sum(row) for row in w]
        for y in ([300.0, 500.0], [120.0, 800.0]):
            self.assertAlmostEqual(tf._ll_w(data, w, t_tot, c, nuis, y, "bb"), tf._ll_bb(data, w, mc, y), places=8)
            self.assertAlmostEqual(tf._ll_w(data, w, t_tot, c, nuis, y, "naive"), tf._ll_naive(data, w, mc, y), places=8)

    def test_shape_and_norm_nuisances_act_as_specified(self):
        d = make_weighted()
        names, data, w, c, t_tot, nuis = tf._load_w(d)
        y = [250.0, 500.0]
        base = tf._ll_w(data, w, t_tot, c, nuis, y + [0.0, 0.0], "naive") + 0.0
        # theta = 1 on the shape nuisance puts the expected sig weights at the up template
        up_ll = tf._ll_w(data, w, t_tot, c, nuis, y + [1.0, 0.0], "naive") + 0.5
        manual = 0.0
        for i, n in enumerate(data):
            nu = y[0] * d["nuisances"][0]["up"][i] / t_tot[0] + y[1] * w[1][i] / t_tot[1]
            manual += n * math.log(nu) - nu
        self.assertAlmostEqual(up_ll, manual, places=8)
        # norm nuisance: factor 1 + sigma theta on the background yield per unit weight
        theta = 1.5
        scaled = tf._ll_w(data, w, t_tot, c, nuis, y + [0.0, theta], "naive") + 0.5 * theta ** 2
        want = tf._ll_w(data, w, t_tot, c, [], [y[0], y[1] * (1 + 0.05 * theta)], "naive")
        self.assertAlmostEqual(scaled, want, places=8)
        self.assertEqual(tf._ll_w(data, w, t_tot, c, nuis, y + [0.0, -30.0], "naive"), tf.NEG)
        self.assertNotEqual(base, up_ll)

    def test_effective_count_scale_enters_the_constraint(self):
        # one bin, one template: n = 10, W = 20, c = 2 (so the effective count is 10), A = Y / T = 0.5, t = 0 -> a = W
        want = 10 * math.log(10.0) - 10.0 + (20 * math.log(20.0) - 20.0) / 2.0
        self.assertAlmostEqual(tf._bb_bin_w(10, [0.5], [20.0], [2.0]), want, places=8)

    def test_bfgs_finds_a_quadratic_minimum(self):
        x, _ = tf._bfgs_min(lambda p: (p[0] - 3.0) ** 2 + 4 * (p[1] + 1.0) ** 2 + 0.5 * p[0] * p[1], [0.0, 0.0], [1.0, 1.0])
        gx = 2 * (x[0] - 3.0) + 0.5 * x[1]
        gy = 8 * (x[1] + 1.0) + 0.5 * x[0]
        self.assertAlmostEqual(gx, 0.0, places=4)
        self.assertAlmostEqual(gy, 0.0, places=4)

    def test_nuisances_and_mc_statistics_both_inflate_the_errors(self):
        with_n = tf.wbb_fit(make_weighted())
        without = tf.wbb_fit(make_weighted(nuisances=False))
        for name in ("sig", "bkg"):
            self.assertGreater(with_n["error_inflation_bb_over_naive"][name], 1.1)
            self.assertGreater(with_n["naive"][name]["error"], without["naive"][name]["error"] * 1.02)
            self.assertLess(abs(with_n["barlow_beeston"][name]["yield"] - {"sig": 250, "bkg": 500}[name]),
                            4 * with_n["barlow_beeston"][name]["error"])
        self.assertEqual(set(with_n["nuisance_values_barlow_beeston"]), {"shape_sig", "norm_bkg"})

    def test_toys_calibrate_the_weighted_fit(self):
        out = tf.wbb_toys(make_weighted(nuisances=False), 100, 1)["fits"]
        for name in ("sig", "bkg"):
            self.assertGreater(out["naive"][name]["pull_width_robust_mad"], 1.1)
            self.assertAlmostEqual(out["barlow_beeston"][name]["pull_width_robust_mad"], 1.0, delta=0.25)
            self.assertGreater(out["barlow_beeston"][name]["coverage_1sigma"], out["naive"][name]["coverage_1sigma"])

    def test_reproducible_and_rejections(self):
        d = make_weighted(bins=4)
        self.assertEqual(tf.wbb_toys(d, 30, 4), tf.wbb_toys(d, 30, 4))
        good = make_weighted(bins=4)
        bad = [dict(good, templates={"sig": {"sumw": [1, 2, 3, 4], "sumw2": [1, 2, 3]}}),
               dict(good, templates={"sig": {"sumw": [1, 2, 3, 4], "sumw2": [1, 2, 0, 4]}}),
               dict(good, nuisances=[{"kind": "weird", "template": "sig"}]),
               dict(good, nuisances=[{"kind": "norm", "template": "nope", "sigma": 0.1}]),
               dict(good, nuisances=[{"kind": "norm", "template": "sig", "sigma": 0.0}]),
               dict(good, nuisances=[{"kind": "shape", "template": "sig", "up": [1], "down": [1]}]),
               dict(good, nuisances=[{"kind": "norm", "template": "sig", "sigma": 0.1}] * 9)]
        for doc in bad:
            with self.assertRaises(tf.ToyError):
                tf.wbb_fit(doc)
        with self.assertRaises(tf.ToyError):
            tf.wbb_toys(good, 50, None)


class FitStatusAuditT03(unittest.TestCase):
    """Audit T03: infeasible models and solver failures are never reported as a successful fit."""
    INFEASIBLE = {"data": [10, 10], "templates": {"sig": [10, 0]}}

    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tf.main(list(argv))
        return code, json.loads(buf.getvalue())

    def not_converging(self):
        """The minimizer capped at two iterations: every fit stops without converging."""
        real = tf._nelder_mead
        return mock.patch.object(tf, "_nelder_mead", lambda f, x0, steps, max_iter=600, tol=1e-10, info=None:
                                 real(f, x0, steps, max_iter=2, tol=tol, info=info))

    def test_failed_fit_cli_fails_with_nonzero_exit(self):
        doc = make_doc(bins=5)
        for cmd in ("bb-fit", "wbb-fit"):
            with tempfile.TemporaryDirectory() as tmp, self.not_converging():
                path = Path(tmp) / "f.json"
                path.write_text(json.dumps(doc))
                code, out = self.run_cli(cmd, "--input", str(path))
            self.assertNotEqual(code, 0, cmd)
            self.assertEqual(out["status"], "failed", cmd)
            self.assertEqual(out["artifact_fit_status"], "failed", cmd)
            self.assertEqual(out["barlow_beeston"]["diagnostics"]["outcome"], "not-converged", cmd)
            self.assertTrue(out["error"], cmd)

    def test_infeasible_naive_fit_is_reported_but_barlow_beeston_describes_the_bin(self):
        # T22: data in a bin with no MC make the naive fit infeasible; Barlow-Beeston keeps the template's true content
        # there as a nuisance, so it fits (yield = all the data) with a larger error than Poisson alone
        for fit in (tf.bb_fit, tf.wbb_fit):
            res = fit(self.INFEASIBLE)
            self.assertEqual(res["naive"]["diagnostics"]["outcome"], "infeasible")
            self.assertIn("bins 2", res["naive_fit_failed"])
            self.assertEqual((res["status"], res["barlow_beeston"]["diagnostics"]["outcome"]), ("ok", "converged"))
            self.assertAlmostEqual(res["barlow_beeston"]["sig"]["yield"], 20.0, delta=1e-3)
            self.assertGreater(res["barlow_beeston"]["sig"]["error"], math.sqrt(20.0))

    def test_feasible_fit_unchanged_and_ok(self):
        doc = make_doc(bins=5)
        doc["templates"].pop("oth")
        res = tf.bb_fit(doc)
        names, data, m, mc = tf._load(doc)
        y, cov, _ = tf.fit_yields(data, m, mc, "naive")
        self.assertEqual([res["naive"][n]["yield"] for n in names], y)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["artifact_fit_status"], "converged")
        for kind in ("naive", "barlow_beeston"):
            d = res[kind]["diagnostics"]
            self.assertEqual((d["outcome"], d["converged"], d["objective_valid"], d["covariance"]), ("converged", True, True, "ok"), kind)

    def test_minimizer_reports_non_convergence(self):
        info = {}
        tf._nelder_mead(lambda p: (p[0] - 3.0) ** 2 + 2 * (p[1] + 1.0) ** 2, [0.0, 0.0], [1.0, 1.0], max_iter=2, info=info)
        self.assertEqual((info["converged"], info["termination"]), (False, "max-iterations"))
        tf._nelder_mead(lambda p: (p[0] - 3.0) ** 2 + 2 * (p[1] + 1.0) ** 2, [0.0, 0.0], [1.0, 1.0], info=info)
        self.assertEqual((info["converged"], info["termination"]), (True, "tolerance"))
        tf._bfgs_min(lambda p: (p[0] - 3.0) ** 2 + 4 * (p[1] + 1.0) ** 2, [0.0, 0.0], [1.0, 1.0], max_iter=1, info=info)
        self.assertFalse(info["converged"])

    def test_boundary_and_covariance_warnings_distinguished(self):
        boundary = {"data": [50, 40, 0, 0], "templates": {"sig": [0, 0, 30, 30], "bkg": [60, 50, 10, 5]}}
        res = tf.bb_fit(boundary)
        self.assertEqual(res["naive"]["diagnostics"]["outcome"], "converged-at-boundary")
        self.assertEqual((res["status"], res["artifact_fit_status"]), ("ok", "converged-with-warnings"))
        twins = {"data": [20, 30, 40], "templates": {"a": [10, 20, 30], "b": [10, 20, 30]}}
        res = tf.bb_fit(twins)
        self.assertIn(res["naive"]["diagnostics"]["covariance"], ("singular", "not-positive-definite"))
        self.assertEqual(res["naive"]["diagnostics"]["outcome"], "covariance-warning")
        self.assertEqual(res["artifact_fit_status"], "converged-with-warnings")

    def test_failed_fit_status_propagates_to_artifacts(self):
        sys.path.insert(0, str(ROOT))
        from contracts.validate import validate_artifact
        with self.not_converging():
            res = tf.bb_fit(make_doc(bins=5))
        self.assertEqual(res["status"], "failed")
        env = {"contract_version": "1.0.0", "artifact_id": "fit", "objective": "synthetic", "versions": {"plugin": "0.1.0", "contracts": "1.0.0"},
               "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-03"}, "unresolved_inputs": []}
        stat = dict(env, artifact_type="statistical-result", status=["synthetic"] + res["artifact_status_labels"],
                    extension={"paradigm": "likelihood-only", "likelihood": {"form": "extended Poisson, Barlow-Beeston"},
                               "parameters_of_interest": ["sig"], "nuisances": [], "fit_status": res["artifact_fit_status"]})
        self.assertTrue(validate_artifact(stat).ok, validate_artifact(stat).as_dict())
        comm = dict(env, artifact_type="communication", status=["synthetic"], provenance={"producer_skill": "research-communication", "created": "2026-10-03"},
                    inputs=[{"ref": "fit.json", "artifact_type": "statistical-result", "status": stat["status"]}],
                    extension={"claims": [{"text": "sig yield", "result_ref": "fit.json", "status": ["synthetic"]}], "sources_read": [], "limitations": []})
        self.assertFalse(validate_artifact(comm).ok, "a claim from a failed fit must carry 'failed'")


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = tf.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_subcommands_and_exit_codes(self):
        doc = make_doc(bins=5)
        doc["templates"].pop("oth")
        doc["true_yields"] = {"sig": 300, "bkg": 500}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.json"
            path.write_text(json.dumps(doc))
            code, out = self.run_cli("bb-fit", "--input", str(path))
            self.assertEqual((code, out["status"], out["label"]), (0, "ok", "[General method]"))
            code, out = self.run_cli("bb-toys", "--input", str(path), "--toys", "30", "--seed", "4")
            self.assertEqual((code, out["status"], out["seed"]), (0, "ok", 4))
            wpath = Path(tmp) / "w.json"
            wpath.write_text(json.dumps(make_weighted(bins=4)))
            code, out = self.run_cli("wbb-fit", "--input", str(wpath))
            self.assertEqual((code, out["status"]), (0, "ok"))
            code, out = self.run_cli("wbb-toys", "--input", str(wpath), "--toys", "30", "--seed", "4")
            self.assertEqual((code, out["status"], out["seed"]), (0, "ok", 4))
        code, out = self.run_cli("bb-fit", "--input", "/nonexistent.json")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            tf.main(["bb-toys", "--input", "x.json"])


if __name__ == "__main__":
    unittest.main()


def _golden_max(f, lo, hi, iters=120):
    g = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    for _ in range(iters):
        x1, x2 = b - g * (b - a), a + g * (b - a)
        a, b = (x1, b) if f(x1) < f(x2) else (a, x2)
    return f(0.5 * (a + b))


class ZeroMcBinTests(unittest.TestCase):
    """T22: a bin where a template has no MC count keeps that template's true content as a nuisance."""

    def brute(self, n, p, m):
        """max over the true MC contents A_j >= 0 of the unprofiled per-bin log-likelihood, by nested golden sections."""
        def ll(a):
            nu = sum(pj * aj for pj, aj in zip(p, a))
            if nu <= 0:
                return -1e300 if n > 0 else 0.0
            return n * math.log(nu) - nu + sum((mj * math.log(aj) if mj > 0 else 0.0) - aj for mj, aj in zip(m, a))
        hi = [3.0 * (mj + n / pj) + 5.0 for mj, pj in zip(m, p)]
        inner = lambda a0: _golden_max(lambda a1: ll([max(a0, 1e-300), max(a1, 1e-300)]), 0.0, hi[1])
        return _golden_max(inner, 0.0, hi[0])

    def test_profiled_bin_equals_the_brute_force_maximum(self):
        # (n, p, m): an empty template with the largest p takes a share; an empty one with a smaller p does not;
        # every template empty; nothing observed
        for n, p, m in ((12, [0.5, 2.0], [6, 0]), (12, [2.0, 0.5], [6, 0]), (7, [0.4, 1.5], [0, 0]),
                        (0, [0.5, 2.0], [6, 0]), (3, [1.0, 1.0], [4, 2])):
            got = tf._ll_bb([n], [[m[0]], [m[1]]], [1.0, 1.0], p)
            self.assertAlmostEqual(got, self.brute(n, p, m), delta=1e-6, msg=(n, p, m))

    def test_empty_bin_with_data_no_longer_breaks_the_likelihood(self):
        self.assertGreater(tf._ll_bb([10, 10], [[10, 0]], [10.0], [20.0]), tf.NEG / 2)
        self.assertEqual(tf._ll_naive([10, 10], [[10, 0]], [10.0], [20.0]), tf.NEG)

    def test_sparse_templates_toy_coverage(self):
        # MC samples of ~60 and ~85 events spread over 8 bins: the tail bins are often empty, so about one toy in five
        # has data in a bin without MC for some template. Every Barlow-Beeston fit must succeed (before T22 those toys
        # failed as infeasible) and the pulls must stay near unit width; Hessian errors with so little MC under-cover
        # somewhat, which the bounds allow.
        sig = [0.9, 3.0, 9.0, 18.0, 18.0, 9.0, 3.0, 0.9]
        bkg = [0.9, 1.8, 4.5, 9.0, 12.0, 15.0, 18.0, 24.0]
        doc = {"data": [0] * 8, "templates": {"sig": sig, "bkg": bkg}, "mc_events": {"sig": sum(sig), "bkg": sum(bkg)},
               "true_yields": {"sig": 150.0, "bkg": 200.0}}
        r = tf.bb_toys(doc, 300, 1)
        self.assertEqual((r["toys_used"], r["toys_failed_fit"]), (300, 0))
        self.assertGreater(r["toys_failed_fit_naive"], 20)
        for name in ("sig", "bkg"):
            bb = r["fits"]["barlow_beeston"][name]
            self.assertLess(abs(bb["bias"]), 3 * bb["spread"] / math.sqrt(300) + 3.0, name)
            self.assertGreater(bb["coverage_1sigma"], 0.56, name)
            self.assertLess(bb["pull_width_robust_mad"], 1.3, name)
            self.assertGreater(bb["coverage_1sigma"], r["fits"]["naive"][name]["coverage_1sigma"] + 0.1, name)

    def test_weighted_empty_bin_uses_the_template_mean_scale(self):
        doc = {"data": [10, 10], "templates": {"sig": {"sumw": [10.0, 0.0], "sumw2": [20.0, 0.0]}}}
        _, _, _, c, _, _ = tf._load_w(doc)
        self.assertEqual(c[0], [2.0, 2.0])

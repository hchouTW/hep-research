"""T22: asymptotic CLs limits and expected 1/2-sigma bands from the Asimov data set (Cowan, Cranmer, Gross, Vitells
2011) in multibin-limit and shape-limit: exact for one bin, and closed against the quantiles of background-only toys."""
import math
import random
import sys
import unittest
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402

QUANTILES = {"-2sigma": NormalDist().cdf(-2), "-1sigma": NormalDist().cdf(-1), "median": 0.5,
             "+1sigma": NormalDist().cdf(1), "+2sigma": NormalDist().cdf(2)}


def solve(f, lo, hi):
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return 0.5 * (lo + hi)


class SingleBinExactTests(unittest.TestCase):
    def test_bands_solve_the_closed_form_asimov_statistic(self):
        # one bin, known background: on the Asimov data n = b, q_A(mu) = 2 (mu s - b ln(1 + mu s / b)) exactly
        b, s, cl = 50.0, 5.0, 0.95
        res = ll.multibin_limit({"bins": [{"n": 50, "b": b, "s": s}]}, cl, 0, 1)
        qa = lambda m: 2.0 * (m * s - b * math.log1p(m * s / b))
        nd, alpha, z = NormalDist(), 1 - cl, NormalDist().inv_cdf(cl)
        for name, k in ll.BANDS:
            want_cls = solve(lambda m: math.sqrt(qa(m)) - (nd.inv_cdf(1 - alpha * nd.cdf(k)) + k), 0.0, 50.0)
            want_clsb = solve(lambda m: math.sqrt(qa(m)) - (z + k if k >= 0 else k + math.sqrt(k * k + z * z)), 0.0, 50.0)
            self.assertAlmostEqual(res["asymptotic_expected_limits"]["cls"][name], want_cls, delta=1e-5, msg=name)
            self.assertAlmostEqual(res["asymptotic_expected_limits"]["clsb"][name], want_clsb, delta=1e-5, msg=name)
        # data at the Asimov point: the observed CLs limit is the CLs median, the CLs+b limit the CLs+b median
        self.assertAlmostEqual(res["asymptotic_observed_cls_upper_limit"], res["asymptotic_expected_limits"]["cls"]["median"], delta=1e-5)
        self.assertAlmostEqual(res["asymptotic_observed_upper_limit"], res["asymptotic_expected_limits"]["clsb"]["median"], delta=1e-4)

    def test_cls_formula_branches_join(self):
        qa = 4.0
        self.assertAlmostEqual(ll._cls_asymptotic(qa - 1e-9, qa), ll._cls_asymptotic(qa + 1e-9, qa), places=6)
        self.assertEqual(ll._cls_asymptotic(1.0, 0.0), 1.0)


class ToyClosureTests(unittest.TestCase):
    """The observed asymptotic limits of background-only pseudo-experiments must be distributed as the bands say."""

    def closure(self, bins_b, bins_s, unc, toys, tol):
        bins = [{"n": round(b), "b": b, "s": s} for b, s in zip(bins_b, bins_s)]
        ref = ll.multibin_limit({"bins": bins, "background_uncertainty": unc}, 0.95, 0, 1)["asymptotic_expected_limits"]
        rng = random.Random(7)
        cls, clsb = [], []
        for _ in range(toys):
            tb = [{"n": ppf(rng.random(), b), "b": b, "s": s} for b, s in zip(bins_b, bins_s)]
            r = ll.multibin_limit({"bins": tb, "background_uncertainty": unc}, 0.95, 0, 1)
            cls.append(r["asymptotic_observed_cls_upper_limit"])
            clsb.append(r["asymptotic_observed_upper_limit"])
        cls.sort()
        clsb.sort()
        for name, f in QUANTILES.items():
            for kind, values in (("cls", cls), ("clsb", clsb)):
                got = values[int(f * toys)]
                self.assertLess(abs(got / ref[kind][name] - 1.0), tol, (kind, name, got, ref[kind][name]))

    def test_known_background(self):
        # 400 toys: the 2.3% and 97.7% quantiles carry about 9 toys each, so allow 12%
        self.closure([30.0, 20.0, 10.0], [2.0, 4.0, 6.0], {"kind": "none"}, 400, 0.12)

    def test_common_background_scale(self):
        self.closure([30.0, 20.0, 10.0], [2.0, 4.0, 6.0], {"kind": "common_scale", "sigma": 0.1}, 300, 0.14)


class ShapeLimitTests(unittest.TestCase):
    def test_shape_limit_without_nuisances_matches_multibin(self):
        bins = [{"n": 12, "b": 10.0, "s": 2.0}, {"n": 4, "b": 5.0, "s": 3.0}]
        a = ll.shape_limit({"bins": bins, "nuisances": []}, 0.95, 0, 1)
        b = ll.multibin_limit({"bins": bins}, 0.95, 0, 1)
        self.assertAlmostEqual(a["asymptotic_observed_cls_upper_limit"], b["asymptotic_observed_cls_upper_limit"], delta=2e-3)
        for kind in ("cls", "clsb"):
            for name in QUANTILES:
                self.assertAlmostEqual(a["asymptotic_expected_limits"][kind][name], b["asymptotic_expected_limits"][kind][name],
                                       delta=2e-3, msg=(kind, name))

    def test_a_nuisance_widens_the_band_and_bands_are_ordered(self):
        bins = [{"n": 12, "b": 10.0, "s": 2.0}, {"n": 4, "b": 5.0, "s": 3.0}]
        plain = ll.shape_limit({"bins": bins}, 0.95, 0, 1)["asymptotic_expected_limits"]
        nuis = ll.shape_limit({"bins": bins, "nuisances": [{"kind": "background_norm", "sigma": 0.3}]}, 0.95, 0, 1)["asymptotic_expected_limits"]
        for kind in ("cls", "clsb"):
            values = [nuis[kind][n] for n in QUANTILES]
            self.assertEqual(values, sorted(values), kind)
            self.assertGreater(nuis[kind]["+2sigma"], plain[kind]["+2sigma"], kind)
            self.assertGreater(nuis[kind]["median"], plain[kind]["median"], kind)


if __name__ == "__main__":
    unittest.main()

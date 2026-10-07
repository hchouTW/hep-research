"""T22: Barlow-Beeston-lite MC-statistics nuisances (per-bin "mc_stat") in multibin-limit and shape-limit.

The background templates of each pseudo-experiment come from a finite MC sample; ignoring that under-covers, and the
per-bin Gaussian factors restore the nominal coverage. Two independent implementations of the same likelihood (the
multibin golden-section profile and the shape-limit Newton profile) must agree."""
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402

B_TRUE, S, MU_TRUE = [20.0, 30.0, 40.0], [8.0, 8.0, 8.0], 3.0


def coverage(pe, neff, seed):
    """Fraction of pseudo-experiments whose asymptotic upper limit covers MU_TRUE, without and with mc_stat.
    MU_TRUE / sigma_mu is about 3 here, so the asymptotic q-tilde limit is calibrated (a weaker signal over-covers
    by construction, with or without MC statistics)."""
    rng = random.Random(seed)
    hits = {"naive": 0, "bbl": 0}
    for _ in range(pe):
        nom = [max(b * ppf(rng.random(), neff) / neff, 0.5) for b in B_TRUE]
        n = [ppf(rng.random(), MU_TRUE * s + b) for s, b in zip(S, B_TRUE)]
        for key, with_mc in (("naive", False), ("bbl", True)):
            bins = [{"n": a, "b": b, "s": s, **({"mc_stat": b / math.sqrt(neff)} if with_mc else {})} for a, b, s in zip(n, nom, S)]
            hits[key] += MU_TRUE <= ll.multibin_limit({"bins": bins}, 0.95, 0, 1)["asymptotic_observed_upper_limit"]
    return {k: v / pe for k, v in hits.items()}


class CoverageTests(unittest.TestCase):
    def test_mc_statistics_restore_coverage(self):
        # 25 effective MC events per bin (20% relative): 1000 pseudo-experiments, binomial error 0.007
        cov = coverage(1000, 25, 1)
        self.assertLess(cov["naive"], 0.92)
        self.assertLess(abs(cov["bbl"] - 0.95), 0.025)

    def test_exact_templates_need_no_correction(self):
        cov = coverage(500, 10**6, 2)
        self.assertAlmostEqual(cov["naive"], cov["bbl"], delta=0.004)


class ConsistencyTests(unittest.TestCase):
    BINS = [{"n": 25, "b": 20.0, "s": 4.0, "mc_stat": 3.0}, {"n": 33, "b": 30.0, "s": 4.0, "mc_stat": 4.0},
            {"n": 38, "b": 40.0, "s": 4.0, "mc_stat": 0.0}]

    def limits(self, r):
        return [r["asymptotic_observed_upper_limit"], r["asymptotic_observed_cls_upper_limit"],
                r["asymptotic_expected_limits"]["cls"]["median"]]

    def test_shape_and_multibin_agree_with_mc_stat_only(self):
        a = self.limits(ll.shape_limit({"bins": self.BINS}, 0.95, 0, 1))
        b = self.limits(ll.multibin_limit({"bins": self.BINS}, 0.95, 0, 1))
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=3e-3)

    def test_common_scale_with_mc_stat_matches_a_gaussian_normalization(self):
        # t = 1 + sigma theta with a unit Gaussian on theta is the multibin common scale; both carry the same gamma_i
        a = self.limits(ll.shape_limit({"bins": self.BINS, "nuisances": [{"kind": "background_norm", "sigma": 0.1}]}, 0.95, 0, 1))
        b = self.limits(ll.multibin_limit({"bins": self.BINS, "background_uncertainty": {"kind": "common_scale", "sigma": 0.1}}, 0.95, 0, 1))
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=5e-3)

    def test_independent_sigma_adds_in_quadrature(self):
        bins = [dict(x) for x in self.BINS]
        a = ll.multibin_limit({"bins": bins, "background_uncertainty": {"kind": "independent", "sigma": [2.0, 1.0, 3.0]}}, 0.95, 0, 1)
        plain = [{k: v for k, v in x.items() if k != "mc_stat"} for x in bins]
        q = [math.hypot(2.0, 3.0), math.hypot(1.0, 4.0), 3.0]
        b = ll.multibin_limit({"bins": plain, "background_uncertainty": {"kind": "independent", "sigma": q}}, 0.95, 0, 1)
        self.assertAlmostEqual(a["asymptotic_observed_upper_limit"], b["asymptotic_observed_upper_limit"], places=9)
        self.assertEqual(a["mc_statistics"], "barlow-beeston-lite")

    def test_mc_stat_loosens_the_limit_and_toys_run(self):
        plain = [{k: v for k, v in x.items() if k != "mc_stat"} for x in self.BINS]
        loose = ll.shape_limit({"bins": self.BINS}, 0.95, 200, 3)
        tight = ll.shape_limit({"bins": plain}, 0.95, 0, 3)
        self.assertGreater(loose["asymptotic_observed_upper_limit"], tight["asymptotic_observed_upper_limit"])
        self.assertLess(abs(loose["toy_p_value_at_asymptotic_limit"] - 0.05), 4 * loose["binomial_error_on_p"] + 0.02)
        r = ll.multibin_limit({"bins": self.BINS, "background_uncertainty": {"kind": "common_scale", "sigma": 0.1}}, 0.95, 200, 3)
        self.assertLess(abs(r["toy_p_value_at_asymptotic_limit"] - 0.05), 4 * r["binomial_error_on_p"] + 0.02)

    def test_mc_stat_needs_a_background(self):
        with self.assertRaises(ll.LikelihoodError):
            ll.shape_limit({"bins": [{"n": 1, "b": 0.0, "s": 1.0, "mc_stat": 0.5}]}, 0.95, 0, 1)


if __name__ == "__main__":
    unittest.main()

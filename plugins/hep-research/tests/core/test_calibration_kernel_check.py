"""P0, kernel consistency (Part B section 8.2 note 1, D53; section 15.3.1 negative tests; phase 1)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import design  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration import kernel_check, linear  # noqa: E402

POINTS = [{"theta": 0.5}, {"theta": 0.25}, {"theta": 0.4}]


def run_toy(plan, seed=20261111):
    fx = H.toy_design()
    ev = E.make(plan)
    d = linear.design(ev, fx["contract"], plan, systematics=fx["release"]["content"]["systematic"])
    pts = kernel_check.worst_ess_and_next(design.p5(ev, fx["contract"], plan, items=("ess",)))
    return kernel_check.p0(ev, fx["contract"], plan, d, pts, seed)


class ToyDetector(unittest.TestCase):
    def setUp(self):
        self.plan = copy.deepcopy(H.toy_design()["plan"])
        self.plan["evaluator"]["events"] = 20_000

    def test_correct_kernels_pass(self):
        r = run_toy(self.plan)
        self.assertEqual(r["status"], "passed")
        self.assertEqual((r["M"], len(r["points"])), (11 * 3, 3))
        self.assertIn("provisional-thresholds", r["flags"])

    def test_declared_poisson_with_enf_in_the_implementation(self):
        """Section 15.3.1 P0: declared as Poisson, the implementation has excess variance (Fano factor 1.5)."""
        self.plan["evaluator"]["photon_fano"] = 1.5
        r = run_toy(self.plan)
        self.assertEqual(r["status"], "failed")
        self.assertIn("p0.kernel_inconsistent", {f["code"] for f in r["findings"]})
        self.assertTrue(any("light_yield" in p["failing"] for p in r["points"]))
        self.plan["kernels"]["photon_generation"]["registration"] = {"density": "negative-binomial"}
        self.assertEqual(run_toy(self.plan)["status"], "passed")          # registered as it is sampled


class MissingSupport(unittest.TestCase):
    def check(self, proposal=None):
        c, p = H.uniform_chain(proposal)
        ev = E.make(p)
        return kernel_check.p0(ev, c, p, linear.design(ev, c, p), POINTS, seed=11)

    def test_single_support(self):
        """Section 15.3.1 P0: U(theta, theta + 1) generated at theta_0 only, theta' = theta_0 + 0.5."""
        r = self.check()
        self.assertEqual(r["status"], "failed")
        self.assertIn({"theta": 0.5}, [p["point"] for p in r["points"] if p["failing"]])

    def test_mixture_over_the_prior_supports(self):
        r = self.check({"nodes": ["x"], "components": [{"theta": {"theta": v}} for v in (0.0, 0.5, 1.0)]})
        self.assertEqual(r["status"], "passed")


class Rules(unittest.TestCase):
    def test_not_applicable_with_full_resimulation(self):
        c, p = H.uniform_chain()
        p["methods"] = {"theta": "resimulation"}
        ev = E.make(p)
        self.assertEqual(kernel_check.p0(ev, c, p, linear.design(ev, c, p), POINTS, 1)["status"], "not-applicable")

    def test_at_least_three_points(self):
        c, p = H.uniform_chain()
        ev = E.make(p)
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), POINTS[:2], 1)
        self.assertEqual((r["status"], r["findings"][0]["code"]), ("rejected", "p0.too_few_points"))

    def test_z_is_two_sided_bonferroni(self):
        c, p = H.uniform_chain({"nodes": ["x"], "components": [{"theta": {"theta": v}} for v in (0.0, 0.5, 1.0)]})
        ev = E.make(p)
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), POINTS, 1)
        from scipy.stats import norm
        self.assertAlmostEqual(r["z"], norm.ppf(1 - 0.01 / (2 * 3)))


class ReviewFixes(unittest.TestCase):
    """Regression tests of the independent review of phase 1 (review/phase-1-review.md, F1, F4, F11)."""

    def test_f1_theta_ref_away_from_the_generation_point(self):
        """A resimulated parameter upstream of the P0 node whose prior centre differs from the generation point: the
        rerun reference is taken from the stored inputs at theta', so correct kernels pass."""
        c, p = H.chain_case(
            [{"id": "a", "kernel": "normal", "args": {"out": "a", "loc": "shift", "scale": "one"}},
             {"id": "b", "kernel": "normal", "args": {"out": "b", "scale": "sb", "parent": "a"}, "parents": ["a"]}],
            [{"name": "b_mean", "node": "b", "var": "b"},
             {"name": "b_width", "node": "b", "var": "b", "functional": "std", "link": "log", "class": "core-width"},
             {"name": "a_width", "node": "a", "var": "a", "functional": "std", "link": "log", "class": "core-width"}],
            {"shift": 0.0, "one": 1.0, "sb": 1.0},
            {"shift": {"nodes": ["a"], "bounds": [0.5, 1.5]}, "sb": {"nodes": ["b"], "bounds": [0.95, 1.05]}},
            {"run": 2000}, methods={"shift": "resimulation", "sb": "analytic-reweighting"})
        ev = E.make(p)
        d = linear.design(ev, c, p)
        self.assertEqual(d["theta_ref"]["shift"], 1.0)
        r = kernel_check.p0(ev, c, p, d, [{"sb": 0.96}, {"sb": 1.04}, {"sb": 1.01}], seed=3)
        self.assertEqual(r["status"], "passed", r["points"])

    def test_f4_rerun_streams_per_point_are_distinct(self):
        from core.calibration.toy import _streams
        a = _streams((20261111, 2), 0, 3, 1, 50)
        b = _streams((20261113, 0), 0, 3, 1, 50)
        self.assertFalse(np.allclose(a, b))
        np.testing.assert_array_equal(a, _streams((20261111, 2), 0, 3, 1, 50))

    def test_f11_default_points_with_deterministic_rerun_only(self):
        c, p = H.chain_case(
            [{"id": "x", "kernel": "normal", "args": {"out": "x", "loc": "mu", "scale": "sigma"}},
             {"id": "y", "kernel": "scale", "args": {"out": "y", "parent": "x", "gain": "g"}, "parents": ["x"],
              "kind": "deterministic"}],
            [{"name": "y_mean", "node": "y", "var": "y", "link": "log"},
             {"name": "y_width", "node": "y", "var": "y", "functional": "std", "link": "log", "class": "core-width"}],
            {"mu": 5.0, "sigma": 1.0, "g": 1.0}, {"g": {"nodes": ["y"], "bounds": [0.9, 1.1]}}, {"run": 500},
            methods={"g": "rerun"})
        ev = E.make(p)
        pts = kernel_check.default_points(ev, c, p)
        self.assertEqual(len(pts), 3)
        self.assertEqual(kernel_check.p0(ev, c, p, linear.design(ev, c, p), pts, 1)["status"], "passed")


if __name__ == "__main__":
    unittest.main()

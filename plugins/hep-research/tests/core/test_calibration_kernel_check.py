"""P0, kernel consistency (Part B section 8.2 note 1, D53; section 15.3.1 negative tests; phase 1)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

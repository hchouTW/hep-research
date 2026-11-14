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
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

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


class NormalDensityRecord(unittest.TestCase):
    def test_15_3_19_normal_density_is_not_distinguished_inside_the_prior(self):
        """A property of P0 on the toy detector (A23, A24): with the photon kernel registered as normal instead of
        Poisson, P0 passes inside the narrow prior box (light yield 97-103, large photon counts). Section 15.3.19's case
        is judged where the density matters, on the Poisson-interval LY reweighting of the g4sim path
        (test_calibration_evaluator_problem.PoissonIntervalLightYield)."""
        plan = copy.deepcopy(H.toy_design()["plan"])
        plan["evaluator"]["events"] = 20_000
        plan["kernels"]["photon_generation"]["registration"] = {"density": "normal"}
        self.assertEqual(run_toy(plan)["status"], "passed")


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


# ------------------------------------------------------------------ phase 3: P0 (k_B) on the synthetic ZDC fixture
def calorimeter(r=0.5, seed=21, n=300, observables=("pe_std",), thetas=("birks",), told=(0.21,), methods=None, priors=None,
                coupling="g4sim"):
    """The fixture's evaluator over a nominal batch and runs told at k_B points (the same events: a k_B rerun of
    g4sim's transport without optical photons draws no extra random number); `synthetic transport stand-in`."""
    import calibration_zdc_fixture as Z
    from core.calibration import evaluator as engine
    import g4sim_calib_eval  # noqa: F401  (registers the g4sim kind)
    bs = {"nominal": Z.batch(seed, 0, n, use="fit", set="s")}
    for kb in Z.BIRKS_PRIOR + tuple(told):
        bs[f"kb{kb}"] = Z.batch(seed, 0, n, birks=kb, point={"birks": kb}, use="fit", set="s")
    c = Z.contract(thetas=thetas, observables=observables, priors=priors)
    p = Z.plan(bs, r=r, **({"methods": methods} if methods else {}))
    # default g4sim's own digitization stream, for the tuned assertions of the machinery tests below; the evaluator's
    # default quantile coupling halves sigma_MC and shows the split bias at both extremes (see the test of it)
    p["evaluator"]["coupling"] = coupling
    return c, p, engine.make(p, c)


class BirksSpotChecks(unittest.TestCase):
    """Section 15.3.1 P0 (k_B) and section 15.2 (synthetic ZDC, item 3): calibrating only k_B with the scintillation
    formula downstream (r = 0.5), on products of the fixture's synthetic transport stand-in."""

    @classmethod
    def setUpClass(cls):
        cls.c, cls.p, cls.ev = calorimeter()
        cls.d = linear.design(cls.ev, cls.c, cls.p)
        cls.req = kernel_check.required_spot_checks(cls.c, cls.p)

    def test_required_are_the_two_birks_extremes(self):
        import calibration_zdc_fixture as Z
        self.assertEqual([(r["parameter"], r["gate"]) for r in self.req], [("birks", "P0")])
        self.assertEqual(self.req[0]["points"], [{"birks": Z.BIRKS_PRIOR[0]}, {"birks": Z.BIRKS_PRIOR[1]}])

    def test_omitting_the_spot_check_is_rejected(self):
        """Negative: three points without the upper k_B extreme -> rejected before any evaluation; positive control:
        the same configuration with both extremes is evaluated (not rejected)."""
        pts = [{"birks": 0.21}, {"birks": 0.02}, {"birks": 0.21}]
        r = kernel_check.p0(self.ev, self.c, self.p, self.d, pts, 3, required=self.req)
        self.assertEqual((r["status"], r["findings"][0]["code"]), ("rejected", "p0.spot_checks_missing"))
        self.assertEqual(kernel_check.missing_spot_checks(pts, self.req, "P0"), [{"birks": 0.4}])
        ok = kernel_check.p0(self.ev, self.c, self.p, self.d, pts[:1], 3, spot_checks=self.req[0]["points"],
                             required=self.req)
        self.assertNotEqual(ok["status"], "rejected")
        self.assertEqual(len(ok["points"]), 3)

    def test_the_width_bias_is_detected_at_the_upper_extreme(self):
        """With the spot checks the nominal-split re-digitization's width bias is detected (the steps cross
        mu_s = 10 near the upper k_B extreme only); positive control: at r = 1 the Gaussian and Poisson regimes have
        the same variance and P0 passes at the same points."""
        r = kernel_check.p0(self.ev, self.c, self.p, self.d, [{"birks": 0.21}], 3,
                            spot_checks=self.req[0]["points"], required=self.req)
        self.assertEqual(r["status"], "failed")
        rows = {row["point"]["birks"]: row for row in r["points"]}
        self.assertEqual(rows[0.4]["failing"], ["birks"])
        self.assertGreater(rows[0.4]["max_ratio"], 3.0)
        self.assertLess(rows[0.21]["max_ratio"], 1.0)
        self.assertIn("spot_check", rows[0.4])
        self.assertEqual(rows[0.4]["rerun_from"], ["transport"])           # full g4sim_run plus response
        c, p, ev = calorimeter(r=1.0)
        d = linear.design(ev, c, p)
        req = kernel_check.required_spot_checks(c, p)
        ok = kernel_check.p0(ev, c, p, d, [{"birks": 0.21}], 3, spot_checks=req[0]["points"], required=req)
        self.assertEqual(ok["status"], "passed")

    def test_coupled_default_sees_the_split_bias_at_both_extremes(self):
        """With the evaluator's default (quantile) coupling, sigma_MC halves and P0 at r = 0.5 fails at both k_B
        extremes, not only the upper one: the nominal-split re-digitization is biased across the k_B prior (a finding
        of phase 3, recorded in the card; 3 seeds: ratios 1.6-1.9 at 0.02, 6.1-6.8 at 0.4). Positive control: at
        r = 1 P0 passes at the same points."""
        c, p, ev = calorimeter(coupling="quantile")
        req = kernel_check.required_spot_checks(c, p)
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"birks": 0.21}], 3, spot_checks=req[0]["points"],
                            required=req)
        rows = {row["point"]["birks"]: row for row in r["points"]}
        self.assertEqual(r["status"], "failed")
        self.assertEqual(rows[0.02]["failing"], ["birks"])
        self.assertEqual(rows[0.4]["failing"], ["birks"])
        c, p, ev = calorimeter(r=1.0, coupling="quantile")
        req = kernel_check.required_spot_checks(c, p)
        ok = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"birks": 0.21}], 3, spot_checks=req[0]["points"],
                             required=req)
        self.assertEqual(ok["status"], "passed")

    def test_incomplete_until_the_extreme_is_told(self):
        c, p, ev = calorimeter(told=())
        p["evaluator"]["batches"].pop("kb0.4")
        ev = E.make(p, c)
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"birks": 0.1}], 3,
                            spot_checks=self.req[0]["points"], required=self.req)
        self.assertEqual(r["status"], "incomplete")

    def test_with_geant4_products(self):
        """The same check with g4sim_run products at the k_B extremes and the centre ('kB-low', 'kB-centre', 'kB-high'
        of campaign p3-g4, $SIMCAL_G4_PRODUCTS; the evaluator's default coupling): the spot checks DETECT the kernel's
        bias at the k_B extremes (approvals A14, A17): P0 fails with p0.kernel_inconsistent at one or both extremes and
        nowhere else. On these products the bias is the rerun's class discretization, not the nominal-split width
        bias, which photon statistics too small to see here hide (A17; the split bias is shown on the synthetic
        fixture). Which extreme is not asserted."""
        import calibration_phase3_g4 as P3
        import calibration_zdc_fixture as Z
        r = P3.calo_evidence("zdc-p0-birks")["result"]
        self.assertEqual(r["status"], "failed", r["points"])
        self.assertIn("p0.kernel_inconsistent", [f["code"] for f in r["findings"]])
        rows = {round(row["point"]["birks"], 12): row for row in r["points"]}
        extremes = set(Z.BIRKS_PRIOR)
        self.assertEqual(set(rows), extremes | {0.21})
        failing = {kb for kb, row in rows.items() if row["failing"]}
        self.assertTrue(failing and failing <= extremes, failing)
        for kb in failing:
            self.assertEqual(rows[kb]["failing"], ["birks"])
            self.assertIn("spot_check", rows[kb])
            self.assertEqual(rows[kb]["rerun_from"], ["transport"])        # full g4sim_run plus response
            self.assertGreater(rows[kb]["max_ratio"], 1.0)


class SpotCheckApplicability(unittest.TestCase):
    """Section 15.3.16 (the synthetic ZDC cases) and section 5.4 (r and the light yield)."""

    def req(self, thetas, methods=None, priors=None):
        import calibration_zdc_fixture as Z
        c = Z.contract(thetas=thetas, priors=priors)
        p = Z.plan({"nominal": Z.batch(5, 0, 2)}, **({"methods": methods} if methods else {}))
        return kernel_check.required_spot_checks(c, p)

    def test_birks_rerun_and_r_redigitization(self):
        """k_B (rerun) and r (re-digitization) -> P0 applies and includes the two k_B extremes."""
        r = self.req(("birks", "resolution"))
        self.assertEqual([(x["parameter"], x["gate"]) for x in r], [("birks", "P0")])
        self.assertEqual([q["birks"] for q in r[0]["points"]], [0.02, 0.4])
        self.assertEqual(design.applicability({"birks": "rerun", "resolution": "re-digitization"})["gates"]["P0"],
                         "applicable")

    def test_birks_by_surrogate_alone_goes_to_p6(self):
        """k_B by a surrogate model and no P0 method -> P0 not-applicable, the k_B extremes in P6's held-out points;
        with r re-digitized as well, P0 applies and carries them."""
        r = self.req(("birks",), {"birks": "surrogate-model"})
        self.assertEqual([(x["parameter"], x["gate"]) for x in r], [("birks", "P6")])
        self.assertEqual(design.applicability({"birks": "surrogate-model"})["gates"]["P0"], "not-applicable")
        held = design.design_points({"birks": (0.02, 0.4)}, 8, 1, held_back=2, spot_checks=r[0]["points"])
        from core.calibration import emulator as EM
        EM.check_spot_checks(held["held_back"], r[0]["points"], ["birks"])          # held back: no exception
        with self.assertRaises(EM.EmulatorError):
            EM.check_spot_checks(held["held_back"][:2], r[0]["points"], ["birks"])
        r = self.req(("birks", "resolution"), {"birks": "surrogate-model"})
        self.assertEqual([(x["parameter"], x["gate"]) for x in r], [("birks", "P0")])

    def test_r_outside_the_valid_range_and_light_yield(self):
        r = self.req(("resolution", "light_yield"), priors={"resolution": (0.1, 0.9)})
        got = {x["parameter"]: x for x in r}
        self.assertEqual([q["resolution"] for q in got["resolution"]["points"]], [0.1])     # only the end outside
        self.assertEqual([q["light_yield"] for q in got["light_yield"]["points"]], [180.0, 220.0])
        self.assertNotIn("resolution", {x["parameter"] for x in self.req(("resolution",))})  # 0.4..0.9: inside
        self.assertEqual(kernel_check.required_spot_checks(H.uniform_chain()[0], H.uniform_chain()[1]), [])


if __name__ == "__main__":
    unittest.main()

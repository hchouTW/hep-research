"""calib_design.py checks of phase 1 (Part B sections 3.6, 6.1, 6.4, 6.7, 8.1, 8.2): Sobol points and the P6
held-back set (D80), P2 (D77), the support condition, P5 with feasibility and the final method (D41, D42), and the
applicability of the mandatory gates (section 15.3.16). The negative tests of P2 and P5 of section 15.3.1."""
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


def codes(r):
    return {f["code"] for f in r.get("findings", [])}


class SobolPoints(unittest.TestCase):
    def test_points_held_back_and_spot_checks(self):
        b = {"a": [0.0, 1.0], "b": [10.0, 20.0]}
        d = design.design_points(b, 16, seed=5, held_back=4, spot_checks=[{"a": 0.0, "b": 10.0}])
        self.assertEqual((len(d["training"]), len(d["held_back"])), (12, 5))
        for p in d["training"] + d["held_back"]:
            self.assertTrue(0 <= p["a"] <= 1 and 10 <= p["b"] <= 20)
        self.assertEqual(design.sobol_points(b, 8, 5), design.sobol_points(b, 8, 5))
        self.assertNotEqual(design.sobol_points(b, 8, 5), design.sobol_points(b, 8, 6))
        with self.assertRaises(design.CheckError):
            design.sobol_points({"a": [1.0, 1.0]}, 4, 1)


class P2(unittest.TestCase):
    def test_toy_passes(self):
        r = design.p2(H.toy_design()["contract"])
        self.assertEqual((r["status"], r["n_c"], r["d_free"], r["ndf"]), ("passed", 26, 11, 15))

    def test_insufficient_observables(self):
        """Section 15.3.1 P2: too few calibration observables."""
        c = copy.deepcopy(H.toy_design()["contract"])
        c["observables"] = c["observables"][:12]
        r = design.p2(c)
        self.assertEqual(r["status"], "failed")
        self.assertIn("p2.insufficient_ndf", codes(r))

    def test_d77_counting(self):
        obs = [{"name": "count_shape", "role": "calibration", "sample": "s", "shape_class": "free-omega",
                "vector": {"K": 5, "bins": ["b"], "data_side": "count"}},
               {"name": "absolute_shape", "role": "calibration", "sample": "s", "shape_class": "absolute",
                "vector": {"K": 2, "bins": ["b"], "data_side": "count"}},
               {"name": "gauss_shape", "role": "calibration", "vector": {"K": 4, "bins": ["b"],
                                                                         "data_side": "gaussian-summary"}},
               {"name": "scalar", "role": "calibration"}, {"name": "dropped", "role": "calibration"},
               {"name": "val", "role": "validation"}]
        c = {"observables": obs, "event_samples": [{"id": "s", "normalization": "free"}],
             "validation": {"N_dc": [{"n": {}, "c": 0, "construction": "x"}], "unused": [
                 {"observable": "dropped", "reason": "r", "clause": "c"}]},
             "parameters": [{"name": "t", "role": "theta"}, {"name": "f", "role": "phi", "mode": "profile"},
                            {"name": "g", "role": "phi", "mode": "profile", "constraint": {"sigma": 1.0}}]}
        r = design.p2(c)
        # omega per free-omega shape (section 2.1), none for an absolute shape (review F2)
        self.assertEqual((r["n_c"], r["dim_N_dc"], r["d_free"], r["ndf"]), (5 + 2 + 3 + 1, 1, 3, 7))


class Applicability(unittest.TestCase):
    """Section 15.3.16, the cases without g4sim (the synthetic ZDC cases are phase 3)."""

    def test_full_resimulation_only(self):
        g = design.applicability({"a": "resimulation", "b": "resimulation"})["gates"]
        self.assertEqual({k: g[k] for k in ("P0", "P6", "G4", "G4-L")}, dict.fromkeys(("P0", "P6", "G4", "G4-L"),
                                                                                       "not-applicable"))

    def test_surrogate_only(self):
        g = design.applicability({"a": "surrogate-model", "b": "resimulation"}, held_back=40)
        self.assertEqual((g["gates"]["P0"], g["gates"]["P6"]), ("not-applicable", "applicable"))
        self.assertTrue(g["P6_parts"]["pull_chi2"])

    def test_step_level_only(self):
        g = design.applicability({"a": "step-level-reweighting"})["gates"]
        self.assertEqual((g["P0"], g["G4"]), ("applicable", "applicable"))

    def test_g5_always_and_twenty_held_back(self):
        self.assertEqual(design.applicability({})["gates"]["G5"], "applicable")
        parts = design.applicability({"a": "surrogate-model"}, held_back=20)["P6_parts"]
        self.assertEqual(parts, {"delta_m": True, "pull_chi2": False})


class Support(unittest.TestCase):
    def test_single_support_is_missing(self):
        c, p = H.uniform_chain()
        r = design.support_check(E.make(p), c, p, ["theta"])
        self.assertIn("support.missing", codes(r))

    def test_mixture_over_the_prior_supports(self):
        c, p = H.uniform_chain({"nodes": ["x"], "components": [{"theta": {"theta": v}} for v in (0.0, 0.5, 1.0)]})
        self.assertEqual(design.support_check(E.make(p), c, p, ["theta"])["status"], "passed")

    def test_zero_suppression_and_threshold(self):
        fx = H.toy_design()
        plan = dict(fx["plan"], evaluator={"kind": "toy-detector", "events": 2000})
        ev = E.make(plan)
        self.assertIn("support.filtered", codes(design.support_check(ev, fx["contract"], plan, ["noise_width"])))
        self.assertIn("support.not_density_parameter",
                      codes(design.support_check(ev, fx["contract"], plan, ["threshold"])))


class P5(unittest.TestCase):
    """Section 15.3.1 P5, four cases, and the A7 items (D41, D42). Sigma_boot and b_J are phase 2, the theta-noise
    item phase 3."""

    def run_p5(self, c, p, items=("ess",)):
        return design.p5(E.make(p), c, p, items=items)

    def test_a_q_too_narrow(self):
        c, p = H.gaussian_chain()
        r = self.run_p5(c, p)
        self.assertEqual(r["status"], "failed")
        self.assertIn("p5.ess", codes(r))
        c, p = H.gaussian_chain(proposal={"nodes": ["x"], "components": [{"theta": {"sigma": 2.5}}]})
        self.assertEqual(self.run_p5(c, p)["items"]["ess"]["status"], "passed")

    def test_b_interior_point_of_a_mixture(self):
        c, p = H.gaussian_chain(n_data=800, proposal={"nodes": ["x"], "components": [{"theta": {"mu": -2.0}},
                                                                                      {"theta": {"mu": 2.0}}]})
        r = self.run_p5(c, p)
        self.assertIn("p5.ess", codes(r))
        self.assertLess(abs(r["items"]["ess"]["worst_point"]["mu"]), 1.0)          # found inside, not at the edge
        ev = E.make(p)
        edges = design.p5(ev, dict(c, parameters=[dict(c["parameters"][0], sampling_bounds=[1.9, 2.0])]), p)
        self.assertEqual(edges["items"]["ess"]["status"], "passed")

    def test_c_correlated_weights_fail_the_matrix_condition(self):
        c, p = H.chain_case(
            [{"id": "u", "kernel": "normal", "args": {"out": "u", "loc": "theta", "scale": "one"}},
             {"id": "x1", "kernel": "normal", "args": {"out": "x1", "scale": "s", "parent": "u"}, "parents": ["u"]},
             {"id": "x2", "kernel": "normal", "args": {"out": "x2", "scale": "s", "parent": "u"}, "parents": ["u"]}],
            [{"name": "x1_mean", "node": "x1", "var": "x1", "sample": "s1"},
             {"name": "x2_mean", "node": "x2", "var": "x2", "sample": "s2"}],
            {"theta": 0.0, "one": 1.0, "s": 0.3}, {"theta": {"nodes": ["u"], "bounds": [-0.01, 0.01]}},
            {"s1": 1600, "s2": 1600}, methods={"theta": "analytic-reweighting"})
        r = self.run_p5(c, p, items=("ess", "v_mc_diagonal", "matrix_condition"))
        self.assertEqual(r["items"]["v_mc_diagonal"]["status"], "passed")
        self.assertEqual(r["items"]["ess"]["status"], "passed")
        self.assertEqual(r["items"]["matrix_condition"]["status"], "failed")
        self.assertEqual(codes(r), {"p5.matrix_condition"})

    def test_d_poisson_at_mu_1000_moves_to_the_next_tier(self):
        c, p = H.poisson_chain()
        ev = E.make(p)
        m = design.final_methods(ev, c, p)
        self.assertEqual((m["status"], m["methods"]), ("ok", {"rate": "resimulation"}))
        self.assertEqual(m["moved_to_next_tier"], {"rate": "resimulation"})
        self.assertFalse(m["log"][0]["feasible"])
        self.assertEqual(design.p5(ev, c, p, items=("ess", "v_mc_diagonal"))["status"], "passed")

    def test_feasible_reweighting_is_kept(self):
        c, p = H.poisson_chain(rel=0.002)
        m = design.final_methods(E.make(p), c, p)
        self.assertEqual(m["methods"], {"rate": "analytic-reweighting"})

    def test_d42_diagonal_item(self):
        c, p = H.chain_case(
            [{"id": "x", "kernel": "normal", "args": {"out": "x", "loc": "mu", "scale": "sigma"}}],
            [{"name": "x_mean", "node": "x", "var": "x", "sample": "sm"},
             {"name": "x_width", "node": "x", "var": "x", "functional": "std", "link": "log", "class": "core-width",
              "sample": "sw"}],
            {"mu": 0.0, "sigma": 1.0}, {"mu": {"nodes": ["x"], "bounds": [-0.01, 0.01]}}, {"sm": 1000, "sw": 40_000},
            methods={"mu": "analytic-reweighting"})
        r = self.run_p5(c, p, items=("ess", "v_mc_diagonal", "matrix_condition"))
        self.assertIn("p5.v_mc_diagonal", codes(r))
        self.assertEqual(r["items"]["matrix_condition"]["status"], "passed")

    def test_d41_tail_functional_refused(self):
        c, p = H.gaussian_chain()
        c["observables"][1]["functional"] = "tail"
        with self.assertRaises(design.CheckError) as cm:
            self.run_p5(c, p)
        self.assertEqual(cm.exception.code, "p5.tail_functional")

    def test_results_are_provisional_and_list_later_items(self):
        c, p = H.gaussian_chain(proposal={"nodes": ["x"], "components": [{"theta": {"sigma": 2.5}}]})
        r = self.run_p5(c, p)
        self.assertIn("provisional-thresholds", r["flags"])
        self.assertTrue(any("b_J" in x for x in r["deferred"]) and any("sigma_boot" in x for x in r["deferred"]))



class ReviewFixes(unittest.TestCase):
    """Regression tests of the independent review of phase 1 (F5, F6, F7, F12)."""

    def toy(self, runs=None, **methods):
        fx = H.toy_design()
        c, p = copy.deepcopy(fx["contract"]), copy.deepcopy(fx["plan"])
        p["evaluator"] = {"kind": "toy-detector", "events": 2000, **({"runs": runs} if runs else {})}
        if runs:
            c["observables"] = [o for o in c["observables"] if o["sample"] in runs]
        p["methods"].update(methods)
        return c, p

    def test_f6_missing_support_fails_p5(self):
        c, p = self.toy(noise_width="analytic-reweighting")
        r = design.p5(E.make(p), c, p, items=("ess",), n_scan=4, scan_parameters=["noise_width"])
        self.assertIn("p5.missing_support", codes(r))

    def test_f7_filtering_needs_the_plan_s_decision(self):
        runs = ["beam1", "beam2", "beam3", "beam4"]
        c, p = self.toy(runs, noise_width="analytic-reweighting")
        self.assertIn("support.filtered", codes(design.support_check(E.make(p), c, p, ["noise_width"])))
        p["kernels"]["electronics"]["filter_ignorable"] = True
        self.assertEqual(design.support_check(E.make(p), c, p, ["noise_width"])["status"], "passed")

    def test_f12_scan_covers_every_theta_by_default(self):
        c, p = H.chain_case(
            [{"id": "x", "kernel": "normal", "args": {"out": "x", "loc": "mu", "scale": "sigma"}}],
            [{"name": "x_mean", "node": "x", "var": "x"}],
            {"mu": 0.0, "sigma": 1.0}, {"mu": {"nodes": ["x"], "bounds": [-0.01, 0.01]},
                                        "sigma": {"nodes": ["x"], "bounds": [0.99, 1.01]}}, {"run": 100},
            methods={"mu": "analytic-reweighting", "sigma": "resimulation"})
        r = design.p5(E.make(p), c, p, items=("ess",), n_scan=4)
        self.assertEqual(sorted(r["scan"]["parameters"]), ["mu", "sigma"])

    def test_f5_p5_with_the_final_method(self):
        c, p = H.poisson_chain()
        r = design.p5_with_final_methods(E.make(p), c, p, items=("ess", "v_mc_diagonal"))
        self.assertEqual((r["status"], r["final_methods"]), ("passed", {"rate": "resimulation"}))


if __name__ == "__main__":
    unittest.main()

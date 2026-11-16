"""core/calibration/chain, the g4sim binding (simulator calibration phase 3): the node binding (Part B section 11.4
Table 1) and the candidate methods of Table 2, D75 (k_B: deterministic rerun, no event weights, G4 does not apply), the
fast_sim_envelope limit (C29, D83 (12)), the misalignment row (D86, D83 (7)), the conditions binding (D87) and the
binding cases of section 15.3.19. Each negative test has a positive control (the valid fixture, calibration_g4sim_
fixtures, derives a candidate for every parameter)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_g4sim_fixtures as G  # noqa: E402
from core.calibration import chain  # noqa: E402
from core.calibration import contract as cc  # noqa: E402

PAR = {p["name"]: i for i, p in enumerate(G.contract()["parameters"])}


def derive(c=None, p=None):
    return chain.candidate_methods(c or G.contract(), p or G.plan())


def methods(r, name):
    return [e["method"] for e in r["parameters"][name]]


def codes(r):
    return {f["code"] for f in r["findings"]}


def rebind(c, name, document, pointer):
    c["parameters"][PAR[name]]["bindings"] = [{"document": document, "pointer": pointer}]
    return c


class Table2(unittest.TestCase):
    def test_every_row_of_the_fixture(self):
        r = derive()
        self.assertEqual((r["status"], r["findings"], r["without_candidate"]), ("ok", [], []))
        self.assertEqual(methods(r, "beam_energy"), ["analytic-reweighting"])
        for name in ("wrap_thickness", "cut"):
            self.assertEqual(methods(r, name), ["resimulation", "surrogate-model"])
        for name in ("birks", "light_yield", "gain", "threshold_0", "reco_offset"):
            self.assertEqual(methods(r, name), ["rerun"], name)
        self.assertIn("Python only", r["parameters"]["threshold_0"][0]["form"])

    def test_d75_birks_is_a_deterministic_rerun(self):
        """k_B: rerun from edep_by_dedx_class, no event weights, so G4 does not apply (D75)."""
        e = derive()["parameters"]["birks"][0]
        self.assertEqual((e["method"], e["tier"], e["event_weights"]), ("rerun", "medium", False))
        self.assertTrue(derive()["parameters"]["beam_energy"][0]["event_weights"])   # control: reweighting does
        p = G.plan()
        p["node_binding"]["nodes"]["transport"]["stored"].remove("edep_by_dedx_class")
        self.assertEqual(methods(derive(p=p), "birks"), [])

    def test_light_yield_only_and_poisson_interval_adds_reweighting(self):
        p = G.plan()
        p["node_binding"]["nodes"]["quanta"]["poisson_interval_only"] = True
        self.assertEqual(methods(derive(p=p), "light_yield"), ["analytic-reweighting", "rerun"])
        c = rebind(G.contract(), "light_yield", "response-pipeline", "/stages/0/parameters/resolution_scale/value")
        self.assertEqual(methods(derive(c, p), "light_yield"), ["rerun"])           # r changes: no reweighting

    def test_15_3_19_moments_only_is_infeasible(self):
        """A node to be reweighted recorded only as moments: decided infeasible (section 6.1)."""
        p = G.plan()
        p["node_binding"]["nodes"]["source"]["recording"] = "moments"
        r = derive(p=p)
        self.assertEqual(methods(r, "beam_energy"), [])
        self.assertIn("moments", r["excluded"]["beam_energy"][0]["reason"])
        self.assertIn("beam_energy", r["without_candidate"])
        p["node_binding"]["nodes"]["transport"]["recording"] = "moments"
        self.assertEqual(methods(derive(p=p), "birks"), [])
        self.assertEqual(methods(derive(p=p), "wrap_thickness"), ["resimulation", "surrogate-model"])

    def test_fast_sim_envelope(self):
        """C29, D83 (12): no Birks, scintillation or LY calibration on a volume inside a fast_sim_envelope."""
        p = G.plan()
        p["node_binding"]["fast_sim_envelope"] = {"materials": ["FR4"], "stages": ["scintillation"]}
        r = derive(p=p)
        self.assertEqual((methods(r, "birks"), methods(r, "light_yield")), ([], []))
        self.assertIn("fast_sim_envelope", r["excluded"]["birks"][0]["reason"])
        self.assertEqual(methods(r, "wrap_thickness"), ["resimulation", "surrogate-model"])

    def test_response_reweighting_needs_both_handoffs(self):
        c = G.contract()
        c["parameters"].append(G.parameter("noise", "theta", "electronics", "response-pipeline",
                                           "/stages/3/parameters/noise_sigma/value"))
        p = G.plan()
        p["node_binding"]["nodes"]["electronics"]["distribution"] = "poisson"
        self.assertEqual(methods(derive(c, p), "noise"), ["rerun"])
        p["node_binding"]["nodes"]["electronics"]["stored"] += ["handoff_inputs", "handoff_outputs"]
        self.assertEqual(methods(derive(c, p), "noise"), ["analytic-reweighting", "rerun"])
        p["node_binding"]["nodes"]["sensor"]["stored"] += ["handoff_inputs"]      # nothing before stage 3
        self.assertIn("binding.no_handoff", codes(derive(c, p)))


class Refusals(unittest.TestCase):
    def assert_refused(self, c, code, p=None):
        r = derive(c, p)
        self.assertEqual(r["status"], "failed")
        self.assertIn(code, codes(r))
        return r

    def test_light_yield_bound_to_the_detector_spec(self):
        c = rebind(G.contract(), "light_yield", "detector-spec", "/materials/FR4/scintillation/yield_per_MeV")
        self.assert_refused(c, "binding.not_in_table_2")
        self.assertIn("binding.not_in_table_2", {f["code"] for f in cc.check(c, G.F.releases())["findings"]})

    def test_discrete_model_seeds_and_run_block(self):
        for document, pointer in (("run-card", "/physics/reference_list"), ("run-card", "/physics/fast_sim/model"),
                                  ("run-card", "/physics/xtr/0/radiator_class"), ("run-card", "/physics/pai/0/model"),
                                  ("run-card", "/physics/optical/cerenkov"), ("run-card", "/physics/decay/mode"),
                                  ("run-card", "/run/events"), ("response-pipeline", "/run_seed"),
                                  ("condition-snapshot", "/iovs/0/rows/0/dead"),
                                  ("condition-snapshot", "/iovs/0/rows/0/temperature_K"),
                                  ("alignment-overlay", "/shifts/0/copy_number"),
                                  ("simulation-request", "/scorers/0/quantity")):
            with self.subTest(pointer):
                self.assert_refused(rebind(G.contract(), "cut", document, pointer), "binding.not_in_table_2")

    def test_unbound_theta(self):
        c = G.contract()
        c["parameters"][PAR["cut"]]["bindings"] = []
        self.assert_refused(c, "binding.unbound")

    def test_d87_theta_on_snapshot_is_piecewise_independent(self):
        c = G.contract()
        c["parameters"][PAR["threshold_0"]]["index"]["conditioning"] = "constant"
        self.assert_refused(c, "binding.conditions_structure")

    def test_table1_kernel_property(self):
        p = G.plan()
        p["node_binding"]["nodes"]["source"]["table1"] = "1"        # the source node is a density, not a black box
        self.assert_refused(None, "binding.kernel_property", p)
        p["node_binding"]["nodes"]["source"]["table1"] = "9"
        self.assert_refused(None, "binding.table1", p)

    def test_15_3_19_known_photon_count_between_light_collection_and_pde(self):
        c = G.contract()
        c["references"].append({"id": "light_source", "type": "mid-chain-injection",
                                "edge": {"from": "collection", "to": "pde"}, "observation": "module",
                                "conversion": {"relation": "known photon count", "parameters": []}})
        self.assert_refused(c, "binding.injection_light_pde")
        p = G.plan()
        p["node_binding"]["pde_split"] = True                     # the PDE split of section 6.7 (checked there)
        self.assertNotIn("binding.injection_light_pde", codes(derive(c, p)))

    def test_single_photoelectron_injection(self):
        c = G.contract()
        c["references"].append({"id": "spe", "type": "mid-chain-injection", "edge": {"from": "pde", "to": "sensor"},
                                "observation": "module", "conversion": {"relation": "spe charge", "parameters": []}})
        self.assert_refused(c, "binding.injection_single_pe")

    def test_misalignment(self):
        """D86 and D83 (7): an overlay at every design point, the nominal included; a misaligned geometry has no
        recorded run, so it is refused."""
        c = G.contract()
        c["parameters"].append(G.parameter("shift_x", "theta", "transport", "alignment-overlay",
                                           "/shifts/0/delta_mm/0"))
        r = self.assert_refused(c, "binding.misalignment_no_recorded_run")
        self.assertIn("binding.overlay_every_point", codes(r))
        self.assertEqual(methods(r, "shift_x"), [])
        p = G.plan()
        p["design_points"] = [{"overlay": "nominal-zero-shift.json"}, {"overlay": "dx-0.05.json"}]
        self.assertNotIn("binding.overlay_every_point", codes(derive(c, p)))
        self.assertEqual(derive(None, p)["status"], "ok")             # control: no alignment parameter

    def test_pde_split_parameter_needs_its_declaration(self):
        """An evaluator binding is the PDE split of section 6.7 (core/calibration/pde_split, WP-E): without the
        contract's pde_split it has no candidate; with it, re-digitization (control)."""
        c = G.contract()
        c["parameters"].append(G.parameter("pde", "theta", "pde", "evaluator", "/pde"))
        r = derive(c)
        self.assertEqual((r["status"], r["without_candidate"]), ("failed", ["pde"]))
        c["pde_split"] = {"parameters": ["pde"], "model": "scale", "sensor_surfaces": ["photocathode"]}
        self.assertEqual(methods(derive(c), "pde"), ["rerun"])

    def test_non_g4sim_contract_unchanged(self):
        d = G.F.toy()
        self.assertEqual(chain.candidate_methods(d["contract"], d["plan"])["status"], "ok")
        self.assertEqual(chain.binding_findings(d["contract"]), [])
        c = copy.deepcopy(G.contract())
        self.assertEqual(chain.binding_findings(c), [])


if __name__ == "__main__":
    unittest.main()

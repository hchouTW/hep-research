"""check-spec rules of S3: every negative test of Section 15.1 for PAI, user limits, time cuts, scorers and the source density type."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "adapters/geant4/assets"))

import g4sim_physics_check as check  # noqa: E402

IONISATION = {"e-": "eIoni", "e+": "eIoni", "mu-": "muIoni", "mu+": "muIoni", "proton": "hIoni", "pi+": "hIoni", "alpha": "ionIoni", "GenericIon": "ionIoni", "gamma": None}
REGIONS = ("tracker", "calorimeter")


def request(particle="e-", model="PAI", region="tracker"):
    return {"region": region, "particle": particle, "model": model}


def codes(findings):
    return [finding["code"] for finding in findings]


class PaiSemantics(unittest.TestCase):
    def judge(self, *requests, requirements=()):
        return codes(check.pai_findings(list(requests), REGIONS, IONISATION, requirements))

    def test_a_proper_request_passes(self):
        self.assertEqual(self.judge(request(), request("proton"), request("mu-"), request("GenericIon")), [])

    def test_all_alone_passes(self):
        self.assertEqual(self.judge(request("all"), request("all", region="calorimeter")), [])

    def test_a_misspelt_model_is_refused(self):
        self.assertEqual(self.judge(request(model="PAIphot")), ["pai-model"])

    def test_an_omitted_particle_is_refused(self):
        requirement = {"need": "thin_layer_ionisation", "region": "tracker", "particles": ["e-", "proton"]}
        self.assertEqual(self.judge(request(), requirements=[requirement]), ["pai-requirement"])

    def test_a_shared_process_satisfies_the_requirement(self):
        requirement = {"need": "thin_layer_ionisation", "region": "tracker", "particles": ["e-", "e+", "proton", "pi+"]}
        self.assertEqual(self.judge(request(), request("proton"), requirements=[requirement]), [])

    def test_two_models_for_one_process_are_refused(self):
        self.assertEqual(self.judge(request("e-", "PAI"), request("e+", "PAIphoton")), ["pai-duplicate"])

    def test_two_requests_with_the_same_model_are_refused(self):
        self.assertEqual(self.judge(request("e-"), request("e+")), ["pai-duplicate"])

    def test_the_same_process_in_two_regions_passes(self):
        self.assertEqual(self.judge(request("e-"), request("e+", region="calorimeter")), [])

    def test_alpha_is_refused_because_it_would_get_no_pai(self):
        self.assertEqual(self.judge(request("alpha")), ["pai-mapping"])

    def test_all_mixed_with_a_particle_is_refused(self):
        self.assertEqual(self.judge(request("all"), request("proton")), ["pai-mixed"])

    def test_the_world_is_refused_as_a_region(self):
        for name in ("world", "World", ""):
            self.assertEqual(self.judge(request(region=name)), ["pai-region"])

    def test_an_unknown_region_and_particle_are_refused(self):
        self.assertEqual(self.judge(request(region="nowhere")), ["pai-region"])
        self.assertEqual(self.judge(request("electron")), ["pai-particle"])

    def test_a_particle_with_no_ionisation_is_refused(self):
        self.assertEqual(self.judge(request("gamma")), ["pai-no-ionisation"])

    def test_the_effective_config_names_the_actual_particles(self):
        self.assertEqual(check.effective_pai([request("proton")], IONISATION), [{"region": "tracker", "process": "hIoni", "model": "PAI", "particles": ["pi+", "proton"]}])
        self.assertEqual(len(check.effective_pai([request("all")], IONISATION)), 4)


class Limits(unittest.TestCase):
    def test_separated_allows_only_the_maximum_step(self):
        card = {"accounting": "separated", "physics": {"user_limits": {"tracker": {"max_step_mm": "1"}}}}
        self.assertEqual(check.limit_findings(card), [])
        card["physics"]["user_limits"]["tracker"]["min_kinetic_energy_MeV"] = "1"
        self.assertEqual(codes(check.limit_findings(card)), ["separated-user-limits"])

    def test_legacy_keeps_its_limits(self):
        self.assertEqual(check.limit_findings({"accounting": "legacy", "physics": {"user_limits": {"r": {"min_kinetic_energy_MeV": "1"}}}}), [])

    def test_a_cut_earlier_than_a_window_is_refused(self):
        scorers = [{"name": "s", "time_window_ns": ["0", "100"]}]
        self.assertEqual(check.time_cut_findings({"kill_policy": {"time_cut_ns": "100"}}, scorers), [])
        self.assertEqual(codes(check.time_cut_findings({"kill_policy": {"time_cut_ns": "99.5"}}, scorers)), ["time-cut"])
        self.assertEqual(check.time_cut_findings({}, scorers), [])


class Scorers(unittest.TestCase):
    def judge(self, **fields):
        return codes(check.scorer_findings([{"name": "s", "quantity": "edep", **fields}]))

    def test_legal_combinations_pass(self):
        self.assertEqual(self.judge(), [])
        self.assertEqual(self.judge(segmentation={"along_axis": {"axis": "z", "width_mm": "1"}}, split="apportion", apportion_short_step_fraction="0.1"), [])
        self.assertEqual(self.judge(quantity="energy_out_by_face", segmentation={"cartesian_xy": {}}), [])

    def test_an_illegal_combination_is_refused(self):
        self.assertEqual(self.judge(quantity="time_first", segmentation={"cartesian_xy": {}}), ["scorer-combination"])
        self.assertEqual(self.judge(quantity="n_crossings", segmentation={"polar": {}}), ["scorer-combination"])
        self.assertEqual(self.judge(split="apportion"), ["scorer-combination"])
        self.assertEqual(self.judge(segmentation={"along_axis": {}}, split="midpoint", apportion_short_step_fraction="0.1"), ["scorer-combination"])

    def test_quantities_of_later_phases_are_refused(self):
        self.assertEqual(self.judge(quantity="photon_detected"), ["scorer-phase"])
        self.assertEqual(self.judge(level="event_file"), ["scorer-combination"])
        self.assertEqual(self.judge(level="event_file", hit_kind="calorimeter"), [])
        self.assertEqual(self.judge(quantity="time_first", level="moments"), ["scorer-combination"])

    def test_an_undeclared_birks_constant_is_refused(self):
        scorer = {"name": "s", "quantity": "edep_visible"}
        self.assertEqual(codes(check.scorer_findings([scorer], {"m": {}}, {"s": ["m"]})), ["birks-undeclared"])
        self.assertEqual(check.scorer_findings([scorer], {"m": {"ionisation": {"birks_mm_per_MeV": "0"}}}, {"s": ["m"]}), [])

    def test_a_split_needs_a_scintillation_yield(self):
        scorer = {"name": "s", "quantity": "edep_visible_ly_split"}
        declared = {"m": {"ionisation": {"birks_mm_per_MeV": "0.1"}, "scintillation": {"yield_per_MeV": "100", "resolution_scale": "1"}}}
        self.assertEqual(check.scorer_findings([scorer], declared, {"s": ["m"]}), [])
        self.assertEqual(codes(check.scorer_findings([scorer], {"m": {"ionisation": {"birks_mm_per_MeV": "0.1"}}}, {"s": ["m"]})), ["scintillation-undeclared"])

    def test_the_source_declares_its_density(self):
        self.assertEqual(check.source_findings({"density": "analytic"}), [])
        self.assertEqual(codes(check.source_findings({})), ["source-density"])
        self.assertEqual(codes(check.source_findings({"density": "external"})), ["source-format"])
        self.assertEqual(check.source_findings({"density": "external", "format": "text"}), [])
        self.assertEqual(codes(check.source_findings({"density": "external", "format": "hepmc3"})), ["source-hepmc3"])

    def test_the_calibration_workflow_refuses_an_external_source(self):
        self.assertEqual(codes(check.calibration_findings({"source": {"density": "external", "format": "text"}})), ["calibration-source"])
        self.assertEqual(check.calibration_findings({"source": {"density": "analytic"}}), [])

    def test_a_reference_plane_states_its_frame(self):
        self.assertEqual(check.plane_findings({"reference_planes": [{"name": "a", "frame": "world"}]}), [])
        self.assertEqual(codes(check.plane_findings({"reference_planes": [{"name": "a"}]})), ["plane-frame"])

    def test_the_event_range_fits_the_counter(self):
        self.assertEqual(check.event_range_findings({"run": {"first_event": 2 ** 32 - 10, "events": 10}}), [])
        self.assertEqual(codes(check.event_range_findings({"run": {"first_event": 2 ** 32 - 10, "events": 11}})), ["event-range"])


if __name__ == "__main__":
    unittest.main()

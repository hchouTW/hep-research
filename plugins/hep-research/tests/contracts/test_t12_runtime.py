"""T12 stage 7: A26-A36 at run time and A10 inside a T12 reprocessing (T12-20, T12-21; plan v9.2 Section 13, Section 8.3, R14, R20).

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 7") before the harness was written. Three
scenarios run on a backend that covers them (A28 timing counts, A32 calo-cluster, A34 destriper); the other eight are recorded gaps that
keep P4 execution incomplete. Synthetic fixtures and frozen files read by SHA-256 only; no quality claim.

Run from the plugin root: python -m unittest tests.contracts.test_t12_runtime -v
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import can_recompute, read_sidecar  # noqa: E402
from tests.contracts import t12_runtime as rt  # noqa: E402

SCENARIOS = tuple(f"A{n}" for n in range(26, 37))
EXECUTED = {"A28", "A32", "A34"}   # A32 with E32R's harness-side pairing check (fix round 1, I1)
GAPS = {"A26", "A27", "A29", "A30", "A31", "A33", "A35", "A36"}
# Plan v9.2 Section 13, copied here from the plan's table: the harness must carry each scenario unchanged (never narrowed).
PLAN_TEXT = {
    "A26": "Inject signals before filtering to validate signal attenuation, correlations, and lost modes; post-filter closure alone is "
           "insufficient",
    "A27": "Scan overlap / RF-IF / retarding coordinates: retain conditions, dwell, and merge weights for each setting to avoid incorrect "
           "summation",
    "A28": "Different pixel/channel exposures, with readout generating signals: do not use an incorrect single run-level exposure",
    "A29": "Different angle bases / periods / axial-vs-vector conventions: transform correctly and retain instrument-response dependence",
    "A30": "First CRES track segment undetected: reconstructed energy and response must reflect this selection effect",
    "A31": "Averaged/filtered spectra are not raw counts: do not assume independent Poisson bins; retain the noise model and correlations",
    "A32": "Cuts/cleaning/model/multiplicity change: downstream IRFs cannot be reused without checks",
    "A33": "Scintillation exists but is insufficient to measure energy in the specified domain: support only a veto or partial "
           "quantities, without automatic promotion to a complete measurement",
    "A34": "Null modes in global maps/fits: state unidentifiable components explicitly; do not fabricate information with jitter or naive "
           "chunk averages",
    "A35": "Same frame name but different projection/focal-length definitions: off-axis controls detect the difference; metadata names "
           "alone cannot yield pass",
    "A36": "Signal injection into real data: retain the injection location / synthetic components and derived labels; do not claim a "
           "purely observed result",
}
FROZEN_CONFIGURATION_SHA256 = "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723"
NOISELESS_TOLERANCE_SHA256 = "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698"


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class Scratch(unittest.TestCase):
    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self._scratch.name)

    def tearDown(self):
        self._scratch.cleanup()


# ================================================================ the scenario table (T12-20)

class ScenarioTable(unittest.TestCase):
    def test_every_scenario_is_listed_once_with_the_plan_text(self):
        self.assertEqual(tuple(sorted(rt.SCENARIOS)), SCENARIOS)
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertEqual(rt.SCENARIOS[scenario]["scenario"], PLAN_TEXT[scenario])

    def test_three_run_on_a_backend_and_eight_are_recorded_gaps(self):
        states = {s: rt.SCENARIOS[s]["run_time"] for s in SCENARIOS}
        self.assertEqual({s for s, v in states.items() if v == "executed"}, EXECUTED)
        self.assertEqual({s for s, v in states.items() if v == "gap"}, GAPS)

    def test_an_executed_scenario_names_a_backend_that_exists(self):
        for scenario in EXECUTED:
            with self.subTest(scenario=scenario):
                backend = rt.SCENARIOS[scenario]["backend"]
                self.assertTrue((ROOT / backend).is_file(), backend)

    def test_a_gap_has_a_reason_families_and_no_backend(self):
        for scenario in GAPS:
            with self.subTest(scenario=scenario):
                entry = rt.SCENARIOS[scenario]
                self.assertIsNone(entry["backend"])
                self.assertTrue(entry["reason"])
                self.assertTrue(entry["families"])

    def test_a32_is_executed_with_a_harness_side_pairing_check(self):
        """Fix round 1, I1: the IRF-reuse case runs (E32R); the pairing check is the harness's, recorded as such."""
        entry = rt.SCENARIOS["A32"]
        self.assertNotIn("remainder", entry)
        self.assertIn("harness", entry["guard"])
        self.assertIn("build_response.py", entry["guard"])
        self.assertNotIn("A32 IRF reuse", rt.p4_gaps())

    def test_carried_a32_records_its_check_side(self):
        """Carried minor (stage 7 re-review): the A32 record says the pairing check is the harness's (check_side), run_time stays executed."""
        entry = rt.SCENARIOS["A32"]
        self.assertEqual((entry["run_time"], entry.get("check_side")), ("executed", "harness"))
        self.assertEqual([s for s, e in rt.SCENARIOS.items() if "check_side" in e], ["A32"])

    def test_a33_names_simreco_as_adjacent_not_a_cover(self):
        """Fix round 1, I2: F11 is bound to simreco (TOF times, beta), adjacent, not a cover."""
        reason = rt.SCENARIOS["A33"]["reason"]
        self.assertIn("adapters/geant4/assets/simreco/simreco.cc", reason)
        self.assertIn("adjacent, not a cover", reason)
        self.assertIn("no light-yield", reason)

    def test_p4_execution_stays_incomplete_while_a_gap_exists(self):
        self.assertEqual(rt.p4_gaps(), sorted(GAPS))
        self.assertEqual(rt.p4_execution(), "incomplete")

    def test_the_open_items_name_the_missing_runner_gate_and_response_identity(self):
        """Fix round 1, M2 and I1."""
        self.assertIn("no runner-level retention gate", rt.OPEN_ITEMS)
        self.assertTrue(any("build_response.py" in item for item in rt.OPEN_ITEMS))


# ================================================================ E28: per-channel exposure on the timing counts backend

class E28ChannelExposure(unittest.TestCase):
    def setUp(self):
        self.product, self.readings = rt.counts_product(rt.counts_channels())

    def test_the_t06_reader_accepts_the_product(self):
        self.assertEqual(rt.contract_codes(self.product), [])

    def test_each_channel_has_its_own_valid_exposure_and_the_run_time_is_the_span(self):
        block = self.product["counts"]
        self.assertEqual({c["channel"]: c["valid_exposure"]["value"] for c in block["channels"]}, {"ch-a": 18.0, "ch-b": 9.5})
        self.assertEqual(block["run_time"]["value"], 20.0)

    def test_counts_and_the_unread_interval(self):
        intervals = {i["interval_id"]: i for i in self.product["counts"]["intervals"]}
        self.assertEqual(intervals["a1"]["count"], 1)
        self.assertEqual(intervals["a2"]["count"], 1)
        self.assertEqual(intervals["b1"]["count"], 1)
        self.assertEqual(intervals["b2"]["presence"], "absent")
        self.assertNotIn("count", intervals["b2"])

    def test_each_rate_uses_its_channels_valid_exposure(self):
        for rate in self.product["counts"]["rates"]:
            with self.subTest(channel=rate["channel"]):
                self.assertEqual(rate["denominator"]["source"], "valid-exposure")
                self.assertEqual(rate["denominator"]["value"], {"ch-a": 18.0, "ch-b": 9.5}[rate["channel"]])

    def test_run_time_denominators_are_refused_with_exactly_their_code(self):
        bad = rt.counts_negative(self.product, "run-time-denominator")
        self.assertEqual(sorted(set(rt.contract_codes(bad))), ["reconstruction.counts.run_time_denominator"])

    def test_the_run_span_labelled_as_a_valid_exposure_is_refused_with_exactly_its_code(self):
        bad = rt.counts_negative(self.product, "run-span-as-exposure")
        self.assertEqual(sorted(set(rt.contract_codes(bad))), ["reconstruction.counts.exposure_mismatch"])

    def test_a_consistent_single_run_level_exposure_is_found_by_recomputation(self):
        """Fix round 1, N1: what the T06 reader says about it is a reading (in the case), not an expectation."""
        bad = rt.counts_negative(self.product, "single-run-level-exposure")
        self.assertEqual(rt.exposure_defects(rt.counts_channels(), bad), ["ch-a", "ch-b"])
        self.assertIn("N28c_t06_codes", rt.case_a28()["readings"])
        self.assertEqual(rt.exposure_defects(rt.counts_channels(), self.product), [])

    def test_a_pulse_in_an_unread_interval_is_refused_by_the_recipe(self):
        """Fix round 1, M1 (N28d): no signal is counted where no readout was (counts.py)."""
        reason = rt.unread_pulse_refusal()
        self.assertIsNotNone(reason)
        self.assertIn("lies in an interval that was not read", reason)

    def test_an_unread_interval_filled_with_zero_is_refused_with_exactly_its_code(self):
        """Fix round 1, M1 (N28e)."""
        bad = rt.counts_negative(self.product, "absent-as-zero")
        self.assertEqual(sorted(set(rt.contract_codes(bad))), ["reconstruction.counts.absent_filled"])

    def test_the_case_passes_every_item(self):
        case = rt.case_a28()
        self.assertTrue(case["items"])
        self.assertTrue(all(case["items"].values()), case["items"])


# ================================================================ E32: configuration change on calo-cluster

class E32ConfigurationChange(Scratch):
    def setUp(self):
        super().setUp()
        self.space = rt.CaloSpace(self.folder)

    def test_the_frozen_configuration_is_read_by_its_sha256(self):
        self.assertEqual(rt.T08_CONFIGURATION_SHA256, FROZEN_CONFIGURATION_SHA256)
        self.assertEqual(sha(rt.T08_CONFIGURATION.read_bytes()), FROZEN_CONFIGURATION_SHA256)

    def test_each_product_names_its_own_configuration(self):
        code, frozen = self.space.reconstruct("frozen")
        self.assertEqual(code, 0)
        variant_file = self.space.variant_configuration(cell_threshold_mev=1.2)
        code, variant = self.space.reconstruct("variant", configuration=variant_file)
        self.assertEqual(code, 0)
        self.assertEqual(rt.product_header(frozen)["configuration"]["sha256"], FROZEN_CONFIGURATION_SHA256)
        self.assertEqual(rt.product_header(variant)["configuration"]["sha256"], sha(variant_file.read_bytes()))

    def test_a_consumer_holding_the_frozen_configuration_refuses_the_variants_product(self):
        variant_file = self.space.variant_configuration(cell_threshold_mev=1.2)
        _, variant = self.space.reconstruct("variant", configuration=variant_file)
        code, out = self.space.accounting(variant)
        self.assertEqual(code, 2, out)
        variant_sha = sha(variant_file.read_bytes())
        self.assertIn(f"made with configuration {variant_sha}, not the one given ({FROZEN_CONFIGURATION_SHA256})", out["reason"])
        code, out = self.space.accounting(variant, configuration=variant_file)
        self.assertEqual(code, 0, out)

    def test_the_frozen_product_passes_its_own_consumer(self):
        _, frozen = self.space.reconstruct("frozen")
        code, out = self.space.accounting(frozen)
        self.assertEqual(code, 0, out)

    def test_the_frozen_file_is_not_changed(self):
        rt.case_a32(self.folder / "case")
        self.assertEqual(sha(rt.T08_CONFIGURATION.read_bytes()), FROZEN_CONFIGURATION_SHA256)

    def test_the_case_passes_every_item(self):
        case = rt.case_a32(self.folder / "case")
        self.assertTrue(case["items"])
        self.assertTrue(all(case["items"].values()), case["items"])


# ================================================================ E32R: a response built from T08 products is not reused (fix round 1, I1)

class E32RResponseReuse(Scratch):
    def setUp(self):
        super().setUp()
        self.space = rt.CaloSpace(self.folder, events=rt.RESPONSE_EVENTS)
        code, self.frozen = self.space.reconstruct("frozen")
        self.assertEqual(code, 0)
        self.variant_file = self.space.variant_configuration(cell_threshold_mev=1.2)
        code, self.variant = self.space.reconstruct("variant", configuration=self.variant_file)
        self.assertEqual(code, 0)

    def test_the_response_events_are_the_planned_showers(self):
        self.assertEqual(rt.RESPONSE_EVENTS, [[(600.0, 20.3, 19.8)], [(1400.0, 19.6, 20.4)], [(2200.0, 20.5, 20.5)], [(3000.0, 19.4, 19.6)]])

    def test_the_matched_sample_takes_truth_from_the_showers_and_reco_from_the_objects(self):
        rows = rt.matched_sample(self.frozen, rt.RESPONSE_EVENTS)
        self.assertEqual([r["truth"] for r in rows], [600.0, 1400.0, 2200.0, 3000.0])
        self.assertTrue(all(r["selected"] == 1 and r["reco"] > 0 for r in rows), rows)

    def test_r1_the_frozen_response_is_written_and_validated(self):
        code, artifact, out = rt.build_response(self.space, self.frozen, "frozen", rt.RESPONSE_EVENTS)
        self.assertEqual(code, 0, out)
        self.assertTrue(artifact.is_file())
        self.assertEqual(out["validation"]["contracts_validate"], "ok")

    def test_r2_r3_the_pairing_check_accepts_the_frozen_product_and_refuses_the_variants(self):
        _, artifact, _ = rt.build_response(self.space, self.frozen, "frozen", rt.RESPONSE_EVENTS)
        same = rt.response_pairing(artifact, self.frozen)
        self.assertTrue(same["accepted"], same)
        other = rt.response_pairing(artifact, self.variant)
        self.assertFalse(other["accepted"])
        self.assertIn(FROZEN_CONFIGURATION_SHA256, other["reason"])
        self.assertIn(sha(self.variant_file.read_bytes()), other["reason"])

    def test_r4_a_response_naming_no_configuration_is_refused_as_unbound(self):
        _, artifact, _ = rt.build_response(self.space, self.frozen, "unbound", rt.RESPONSE_EVENTS, provenance="a matched sample")
        found = rt.response_pairing(artifact, self.frozen)
        self.assertFalse(found["accepted"])
        self.assertIn("unbound", found["reason"])

    def test_the_case_passes_every_item(self):
        case = rt.case_a32(self.folder / "case")
        for item in ("R1", "R2", "R3", "R4"):
            self.assertIn(item, case["items"])
        self.assertTrue(all(case["items"].values()), case["items"])
        self.assertIn("variant_matrix_differs", case["readings"])


class E32RPairingStrings(Scratch):
    def test_carried_a_response_naming_two_configurations_is_refused_as_unbound(self):
        """Carried minor (stage 7 re-review): a provenance with more than one configuration string binds to none, even when one or both
        are the product's own identity; one string stays bound. Hand-made artifact and product header (no tool run)."""
        own, other = FROZEN_CONFIGURATION_SHA256, "ab" * 32
        product = self.folder / "header.product"
        product.write_text(json.dumps({"configuration": {"sha256": own}}) + "\n", encoding="utf-8")
        artifact = self.folder / "response.json"
        for names in ((own, other), (other, own), (own, own)):
            provenance = " and ".join(f"configuration sha256 {name}" for name in names)
            artifact.write_text(json.dumps({"extension": {"provenance": provenance}}), encoding="utf-8")
            found = rt.response_pairing(artifact, product)
            self.assertFalse(found["accepted"], names)
            self.assertIsNone(found["response_configuration"], names)
            self.assertIn("unbound", found["reason"], names)
            self.assertIn("2 configuration identities, not exactly one", found["reason"], names)
        artifact.write_text(json.dumps({"extension": {"provenance": f"configuration sha256 {own}"}}), encoding="utf-8")
        self.assertTrue(rt.response_pairing(artifact, product)["accepted"])


# ================================================================ E34: null modes on the destriper

class E34NullModes(unittest.TestCase):
    """The three solver runs are made once for the class: each check-product runs the T06 reader on the scan block (tens of seconds)."""

    @classmethod
    def setUpClass(cls):
        cls._scratch = tempfile.TemporaryDirectory()
        folder = Path(cls._scratch.name)
        cls.zero, cls.free, cls.split = cls.runs = rt.a34_runs(folder)
        cls.case = rt.case_a34(folder, cls.runs)

    @classmethod
    def tearDownClass(cls):
        cls._scratch.cleanup()

    def test_the_frozen_tolerance_is_read_by_its_sha256(self):
        self.assertEqual(rt.NOISELESS_TOLERANCE_SHA256, NOISELESS_TOLERANCE_SHA256)
        tolerance = rt.noiseless_tolerance()
        self.assertEqual((tolerance["tau_baselines"], tolerance["tau_map"]), (2.5e-11, 2.2e-11))

    def test_zero_sum_names_its_constraint_and_matches_the_truth_within_the_frozen_tolerance(self):
        run = self.zero
        self.assertEqual(run["solve_exit"], 0)
        self.assertEqual(run["check_exit"], 0)
        scan = run["product"]["reconstruction_product"]["scan"]
        self.assertIsNotNone(scan["constraint"])
        self.assertEqual(scan["constraint"]["statement"], "zero-sum of the baselines (astro-ph/0501504, as t11-cells.md F38 records it)")
        truth = run["truth"]
        norm = math.sqrt(sum(v * v for v in truth["baselines"]))
        baselines = math.sqrt(sum((a - b) ** 2 for a, b in zip(run["product"]["baselines"], truth["baselines"])))
        sky = math.sqrt(sum((a - b) ** 2 for a, b in zip(run["product"]["map"], truth["map"])))
        self.assertLessEqual(baselines / norm, 2.5e-11)
        self.assertLessEqual(sky / norm, 2.2e-11)

    def test_without_a_constraint_every_parameter_is_unidentifiable_and_only_combinations_are_reported(self):
        run = self.free
        self.assertEqual(run["solve_exit"], 0)
        self.assertEqual(run["check_exit"], 0)
        scan = run["product"]["reconstruction_product"]["scan"]
        self.assertEqual(len(scan["unidentifiable"]), 48)
        self.assertIsNone(scan["constraint"])
        self.assertFalse(scan["uniqueness_claim"])
        self.assertFalse(any(sorted(abs(w) for w in item["weights"])[-2:] == [0, 1] for item in scan["reported"]),
                         "no reported item is a single parameter")

    def test_a_disconnected_scan_is_refused(self):
        run = self.split
        self.assertEqual(run["solve_exit"], 1)
        self.assertEqual(run["solve"]["status"], "refused")
        self.assertEqual(len(run["solve"]["components"]), 2)
        self.assertIsNone(run["product"])

    def test_jitter_chunk_averages_and_a_unique_claim_are_refused_with_their_codes(self):
        """Amendment 1 (after green-1): T10's rule (t10_replay.py negatives: the variant's code is among the refusal codes). On a
        zero-sum product, removing the constraint while single parameters stay reported also raises the unidentifiable codes.
        The variants' codes are the ones setUpClass's case_a34 computed (contract_codes(scan_negative(...)) on this same zero-sum
        product): the reader is deterministic, so recomputing them here cost about 85 s and tested nothing more."""
        embedded = self.zero["product"]["reconstruction_product"]
        negative_codes = self.case["readings"]["negative_codes"]
        variants = (("jitter", "reconstruction.scan.jitter_precision"), ("chunk-average", "reconstruction.scan.chunk_average"),
                    ("unique-without-constraint", "reconstruction.scan.unique_claim"))
        self.assertEqual(sorted(negative_codes), sorted(name for name, _ in variants))
        for name, code in variants:
            with self.subTest(variant=name):
                self.assertIn(code, negative_codes[name])
        self.assertEqual(rt.contract_codes(embedded), [], "the unmodified product passes")

    def test_the_case_passes_every_item(self):
        self.assertEqual(sorted(self.case["items"]), sorted([   # fix round 1, N3: the 11 items by name
            "zero_sum_written_and_checked", "zero_sum_constraint_named", "zero_sum_within_frozen_tolerance", "negative_jitter",
            "negative_chunk-average", "negative_unique-without-constraint", "none_written_and_checked",
            "none_every_parameter_unidentifiable", "none_no_single_parameter_reported", "none_no_constraint_no_uniqueness",
            "disconnected_refused"]))
        self.assertTrue(all(self.case["items"].values()), self.case["items"])


# ================================================================ A10 inside a T12 reprocessing (T12-21)

class A10RawRetention(Scratch):
    def setUp(self):
        super().setUp()
        self.space = rt.CaloSpace(self.folder)
        code, self.p0 = self.space.reconstruct("p0")
        self.assertEqual(code, 0)
        self.p0_bytes = self.p0.read_bytes()

    def retained(self, **kw):
        files = {"input": self.space.cells, "pedestal": self.space.pedestal, "gain": self.space.gain}
        files.update(kw)
        return files

    def test_the_sidecar_is_accepted_and_maps_the_retention(self):
        kept = rt.t08_sidecar(self.p0, self.retained())
        self.assertEqual(read_sidecar(kept).errors, [])
        self.assertEqual(kept["retention"]["raw"], "reproducible")
        self.assertEqual(kept["retention"]["conditions_snapshot"], "reproducible")
        self.assertEqual(kept["retention"]["waveform"], "removed")
        self.assertEqual(kept["retention"]["truth"], "not-applicable")
        self.assertEqual(kept["retention"]["candidates"], "kept")
        removed = rt.t08_sidecar(self.p0, self.retained(input=None, pedestal=None, gain=None))
        self.assertEqual(read_sidecar(removed).errors, [])
        self.assertEqual((removed["retention"]["raw"], removed["retention"]["conditions_snapshot"]), ("removed", "removed"))

    def test_conditions_used_follow_the_chain_by_identity(self):
        sidecar = rt.t08_sidecar(self.p0, self.retained())
        chain = rt.product_header(self.p0)["chain"]
        self.assertEqual([u["payload_id"] for u in sidecar["conditions_used"]], [s["payload_id"] for s in chain])
        self.assertEqual([u["slot"] for u in sidecar["conditions_used"]], ["pedestal", "gain"])
        self.assertEqual(sidecar["conditions_used"][1]["payload_id"], sha(self.space.gain.read_bytes()))

    def test_k1_with_the_readout_retained_the_trace_rerun_runs_under_the_new_payload(self):
        result = self.space.reprocess(self.p0, self.retained(), new_gain=self.space.gain_new, target=self.folder / "p1.jsonl")
        self.assertTrue(result["can_recompute"])
        self.assertEqual(result["outcome"], "ran")
        p1 = self.folder / "p1.jsonl"
        self.assertTrue(p1.is_file())
        self.assertEqual(rt.product_header(p1)["chain"][1]["payload_id"], sha(self.space.gain_new.read_bytes()))
        self.assertEqual(self.p0.read_bytes(), self.p0_bytes)

    def test_k1_a_rerun_under_the_products_own_payloads_reproduces_its_bytes(self):
        result = self.space.reprocess(self.p0, self.retained(), new_gain=self.space.gain, target=self.folder / "again.jsonl")
        self.assertEqual(result["outcome"], "ran")
        self.assertEqual((self.folder / "again.jsonl").read_bytes(), self.p0_bytes)

    def test_k2_with_raw_retention_removed_the_trace_rerun_is_refused(self):
        target = self.folder / "p1.jsonl"
        result = self.space.reprocess(self.p0, self.retained(input=None), new_gain=self.space.gain_new, target=target)
        self.assertFalse(result["can_recompute"])
        self.assertEqual(result["requires"], ["raw", "conditions_snapshot"])
        self.assertTrue(result["outcome"].startswith("refused"))
        self.assertFalse(target.exists())
        self.assertEqual(self.p0.read_bytes(), self.p0_bytes)

    def test_k2_the_higher_level_parameters_stay_usable_and_say_they_are_not_recalibrated(self):
        result = self.space.reprocess(self.p0, self.retained(input=None), new_gain=self.space.gain_new, target=self.folder / "p1.jsonl")
        usable = result["usable"]
        self.assertEqual(usable["gain_payload"], sha(self.space.gain.read_bytes()))
        self.assertEqual(usable["recalibrated"], False)
        objects = usable["objects"]
        self.assertEqual(len(objects), rt.object_count(self.p0))
        self.assertGreater(len(objects), 0)
        for item in objects:
            self.assertEqual(set(item), {"event", "object", "energy", "sigma_energy", "x", "y", "sigma_x", "sigma_y"})

    def test_k2_the_raw_values_kept_for_clustered_cells_do_not_make_raw_kept(self):
        sidecar = rt.t08_sidecar(self.p0, self.retained(input=None))
        self.assertFalse(can_recompute(sidecar, "raw"))

    def test_k3_another_readout_counts_as_removed(self):
        other = self.space.other_cells()
        target = self.folder / "p1.jsonl"
        sidecar = rt.t08_sidecar(self.p0, self.retained(input=other))
        self.assertEqual(sidecar["retention"]["raw"], "removed")
        result = self.space.reprocess(self.p0, self.retained(input=other), new_gain=self.space.gain_new, target=target)
        self.assertFalse(result["can_recompute"])
        self.assertFalse(target.exists())

    def test_k6_with_the_pedestal_not_retained_the_trace_rerun_is_refused(self):
        """Fix round 1, M3: the rerun also needs the conditions snapshot."""
        target = self.folder / "p1.jsonl"
        result = self.space.reprocess(self.p0, self.retained(pedestal=None), new_gain=self.space.gain_new, target=target)
        self.assertEqual(result["retention"], {"raw": "reproducible", "conditions_snapshot": "removed"})
        self.assertFalse(result["can_recompute"])
        self.assertIn("conditions snapshot is not retained", result["outcome"])
        self.assertFalse(target.exists())

    def test_k4_a_waveform_step_is_refused_even_with_the_readout_retained(self):
        sidecar = rt.t08_sidecar(self.p0, self.retained())
        decision = rt.plan_step(sidecar, "pulse-shape-refit", "waveform")
        self.assertFalse(decision["can_recompute"])
        self.assertTrue(decision["outcome"].startswith("refused"))

    def test_k5_a_sidecar_without_its_lost_recalibrations_is_refused(self):
        sidecar = rt.t08_sidecar(self.p0, self.retained(input=None))
        self.assertTrue(sidecar["retention"]["lost_recalibrations"])
        del sidecar["retention"]["lost_recalibrations"]
        self.assertIn("reconstruction.retention.loss_unstated", [f.code for f in read_sidecar(sidecar).errors])

    def test_the_case_passes_every_item(self):
        case = rt.case_a10(self.folder / "case")
        self.assertEqual(set(case["items"]), {"K1", "K1-bytes", "K2", "K2-usable", "K3", "K4", "K5", "K6"})
        self.assertTrue(all(case["items"].values()), case["items"])


# ================================================================ the record and its exit codes

class CommandLine(Scratch):
    def run_main(self, argv):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = rt.main(argv)
        return code, json.loads(stream.getvalue())

    @unittest.skipUnless(SLOW, "slow (the whole run, every scenario again: about 2 min here, up to 8 on a CI runner; each scenario has its own tests above): set HEP_SLOW_TESTS=1")
    def test_run_writes_the_record_and_exits_ok(self):
        out = self.folder / "record.json"
        code, printed = self.run_main(["run", "--out", str(out)])
        self.assertEqual(code, 0, printed)
        self.assertEqual(printed["status"], "ok")
        record = json.loads(out.read_text())
        self.assertEqual(sorted(record["scenarios"]), list(SCENARIOS))
        self.assertEqual(record["p4_execution"], "incomplete")
        self.assertEqual(record["gaps"], sorted(GAPS))
        self.assertIn("no runner-level retention gate", record["open_items"])
        self.assertIs(record["synthetic"], True)
        self.assertIsNone(record["quality_claim"])
        for scenario in EXECUTED:
            self.assertTrue(all(record["scenarios"][scenario]["items"].values()))
        self.assertTrue(all(record["a10"]["items"].values()))

    def test_an_existing_record_is_never_overwritten(self):
        out = self.folder / "record.json"
        out.write_text("{}")
        code, printed = self.run_main(["run", "--out", str(out)])
        self.assertEqual((code, printed["status"]), (2, "rejected"))
        self.assertEqual(out.read_text(), "{}")

    def test_a_missing_folder_is_rejected(self):
        code, printed = self.run_main(["run", "--out", str(self.folder / "absent" / "record.json")])
        self.assertEqual((code, printed["status"]), (2, "rejected"))

    def test_a_failed_expectation_exits_failed(self):
        out = self.folder / "record.json"
        original = rt.case_a28, rt.case_a32, rt.case_a34, rt.case_a10
        try:
            rt.case_a28 = lambda: {"items": {"planted": False}, "readings": {}}
            rt.case_a32 = rt.case_a34 = rt.case_a10 = lambda folder: {"items": {"stub": True}, "readings": {}}
            code, printed = self.run_main(["run", "--out", str(out)])
        finally:
            rt.case_a28, rt.case_a32, rt.case_a34, rt.case_a10 = original
        self.assertEqual((code, printed["status"]), (1, "failed"))

    def test_a_backend_that_cannot_run_is_incomplete(self):
        out = self.folder / "record.json"
        original = rt.case_a34

        def broken(folder):
            raise OSError("planted: the backend cannot start")
        try:
            rt.case_a34 = broken
            code, printed = self.run_main(["run", "--out", str(out)])
        finally:
            rt.case_a34 = original
        self.assertEqual((code, printed["status"]), (3, "incomplete"))
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()

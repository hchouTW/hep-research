"""T12 stage 4, part A: reproducibility comparators declared per recipe (T12-13, plan v9.2 Section 14.1) and quality before speed (T12-15;
A15, A50; Section 16.1).

Every expectation and tolerance is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 4": B1-B3, N1-N9, S1-S6, Q1-Q8)
before this file was written. Tolerances come only from Freeze B / Freeze A and T10's frozen replay tolerance; where none is fixed the
comparator answers incomplete with the open item. Fixtures are synthetic; frozen files are read by SHA-256. No quality claim.

Run from the plugin root: python -m unittest tests.contracts.test_t12_comparators -v
"""
from __future__ import annotations

import copy
import dataclasses
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t07_evaluation_scoring as scoring  # noqa: E402
from tests.contracts import t12_comparators as cmp  # noqa: E402

DESTRIPER = "reco.scan.destriper/1"
TRACK_FINDING = "reco.track.acts-ckf-planar/1"
FAKE_RATE = "fake rate per noise bin"
OPEN_RECIPES = {"reco.track.acts-ckf-planar/1": "OI-1", "reco.vertex.acts-amvf/1": "OI-3", "reco.track.acts-kf-refit/1": "OI-4",
                "reco.calo.cell-cluster/1": "OI-5", "reco.light.channel-likelihood/1": "OI-6", "reco.timing.time-chain/1": "OI-7"}


def counts(seed: int, events: int = 12000, rate: float = 0.001):
    """Synthetic per-event T07-like counts: 1 to 12 tracks per event, each a fake with probability rate."""
    rng = numpy.random.default_rng(seed)
    m = rng.integers(1, 13, events)
    y = rng.binomial(m, rate)
    return {"objects_per_event": [int(v) for v in m], "failures_per_event": [int(v) for v in y]}


def counts_like(sample: dict, seed: int, rate: float = 0.001):
    """The same events and tracks per event as sample (fix round 1, I2: the object count is kept), fakes drawn afresh."""
    rng = numpy.random.default_rng(seed)
    return {"objects_per_event": list(sample["objects_per_event"]),
            "failures_per_event": [int(v) for v in rng.binomial(numpy.array(sample["objects_per_event"]), rate)]}


class Declarations(unittest.TestCase):
    """The table of "Stage 4": byte for every recipe, the destriper's frozen numerical tolerance, F2 for the T07 fake rate, the rest open."""

    def test_every_recipe_is_declared_with_the_three_forms(self):
        self.assertEqual(set(cmp.RECIPES), set(OPEN_RECIPES) | {DESTRIPER})
        for recipe in cmp.RECIPES:
            self.assertEqual(set(cmp.DECLARATIONS[recipe]), {"byte", "numerical", "statistical"}, recipe)
            byte = cmp.DECLARATIONS[recipe]["byte"]
            if recipe == "reco.calo.cell-cluster/1":   # fix round 1, M4: no recorded byte rerun of T08's products
                self.assertEqual((byte["state"], byte["open_item"]), ("open", "OI-11"))
            else:
                self.assertEqual((byte["state"], byte["excluded"]), ("declared", []))
                self.assertTrue(byte["record"], recipe)

    def test_open_items_are_open_and_name_no_tolerance(self):
        for recipe, item in OPEN_RECIPES.items():
            numerical = cmp.DECLARATIONS[recipe]["numerical"]
            self.assertEqual((numerical["state"], numerical["open_item"]), ("open", item), recipe)
            self.assertNotIn("tolerance", numerical)
            self.assertIn(item, cmp.OPEN_ITEMS)
        for item in ("OI-2", "OI-9", "OI-10", "OI-11"):
            self.assertIn(item, cmp.OPEN_ITEMS)
        self.assertIn("Leave open", cmp.OPEN_ITEMS["OI-6"])   # the user, 2026-11-13
        self.assertNotIn("OI-8", cmp.OPEN_ITEMS)               # ruled (fix round 1): a ruling, not an open item
        self.assertIn("OI-8", cmp.RULINGS)

    def test_constants_are_the_frozen_codings(self):
        """M1, N2: the tail and F2 constants are E6's and E2's, not typed in."""
        self.assertEqual(cmp.F2_CONFIDENCE, cmp.fake_rate.CONFIDENCE)
        self.assertEqual(cmp.F2_TAU, scoring.STABILITY_TOLERANCE)
        self.assertEqual((cmp.TAIL_LIMIT, cmp.TAIL_PULL), (scoring.TAIL_LIMIT, scoring.TAIL_PULL))

    def test_frozen_modules_are_checked_by_hash(self):
        """M2: the E6 core and E2's rate rule are the evaluation manifest's bytes, else the statistical comparator and the gate refuse."""
        self.assertEqual(cmp.FROZEN_MODULES["tests/adapters/t04_evaluation_core.py"],
                         "265eb12426f0e16ce3a0cb0caf9925a816cf3114e5cdf7a80f7638241fce3f6f")
        self.assertEqual(cmp.FROZEN_MODULES["adapters/acts-tracking/assets/fixture_tools/t07_fake_rate.py"],
                         "4b4aa1addaf252e33091fab7c8487b882f2bb1c6718af7dc0efd24c7dbde5b6d")
        cmp.check_frozen_modules()
        with mock.patch.dict(cmp.FROZEN_MODULES, {"tests/adapters/t04_evaluation_core.py": "0" * 64}):
            with self.assertRaises(cmp.ComparatorInputError):
                cmp.compare_statistical(TRACK_FINDING, FAKE_RATE, counts(1), counts(1))
            with self.assertRaises(cmp.ComparatorInputError):
                cmp.fixed_gate(numpy.zeros(10))

    def test_destriper_and_t07_fake_rate_cite_their_frozen_sources(self):
        numerical = cmp.DECLARATIONS[DESTRIPER]["numerical"]
        self.assertEqual((numerical["state"], numerical["ruling"]), ("declared", "OI-8"))
        self.assertEqual({r["sha256"] for r in numerical["records"]},
                         {"217a38bc40769da9c750ac347228b120476008b0227f025f4fcbc02ce9d3c35e",
                          "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698"})
        self.assertEqual(cmp.DECLARATIONS[DESTRIPER]["statistical"]["state"], "not-applicable")
        statistical = cmp.DECLARATIONS[TRACK_FINDING]["statistical"]
        self.assertEqual(statistical["state"], "declared")
        self.assertEqual(statistical["quantities"][FAKE_RATE]["tau"], 0.0025)
        self.assertEqual(statistical["quantities"][FAKE_RATE]["confidence"], 0.95)
        self.assertEqual(statistical["open_item"], "OI-2")


class DestriperProducts(unittest.TestCase):
    """Products of the real recipe (reco.scan.destriper/1) on the synthetic fixture t10-destripe/1, noisy, seed 20260, stopping 1e-10."""

    @classmethod
    def setUpClass(cls):
        cls.timestream = cmp.destriper_fixture()
        cls.reference = cmp.solve_destriper(cls.timestream)

    def compare(self, candidate):
        return cmp.compare_numerical(DESTRIPER, self.reference, candidate)


class Byte(DestriperProducts):
    def test_b1_two_runs_on_the_same_input_are_byte_equal(self):
        again = cmp.solve_destriper(self.timestream)
        result = cmp.compare_bytes(DESTRIPER, cmp.dumps_product(self.reference), cmp.dumps_product(again))
        self.assertEqual(result["status"], "passed")
        self.assertIsNone(result["first_difference"])
        self.assertEqual(result["excluded"], [])

    def test_b2_a_pure_key_reordering_fails_the_byte_form(self):
        reference = cmp.dumps_product(self.reference)
        reordered = (json.dumps(dict(reversed(list(self.reference.items()))), separators=(",", ":")) + "\n").encode()
        self.assertEqual(json.loads(reordered), json.loads(reference))
        result = cmp.compare_bytes(DESTRIPER, reference, reordered)
        self.assertEqual(result["status"], "failed")
        self.assertIsInstance(result["first_difference"], int)

    def test_b3_one_changed_byte_fails_and_names_both_hashes(self):
        reference = cmp.dumps_product(self.reference)
        changed = bytearray(reference)
        changed[100] ^= 1
        result = cmp.compare_bytes(DESTRIPER, reference, bytes(changed))
        self.assertEqual((result["status"], result["first_difference"]), ("failed", 100))
        self.assertNotEqual(result["reference_sha256"], result["candidate_sha256"])

    def test_byte_form_works_for_every_recipe_and_refuses_an_unknown_one(self):
        for recipe in cmp.RECIPES:
            expected = ("incomplete", "OI-11") if recipe == "reco.calo.cell-cluster/1" else ("passed", None)
            result = cmp.compare_bytes(recipe, b"abc", b"abc")
            self.assertEqual((result["status"], result.get("open_item")), expected, recipe)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.compare_bytes("reco.unknown/1", b"a", b"a")


class Numerical(DestriperProducts):
    def test_n2_reordered_baselines_pass(self):
        result = self.compare(cmp.solve_destriper(cmp.permute_baselines(self.timestream, seed=7)))
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["failed"], [])
        self.assertLess(result["readings"]["baselines_relative"], 1e-12)
        self.assertLess(result["readings"]["map_relative"], 1e-12)

    def test_n3_samples_reordered_within_each_baseline_pass(self):
        result = self.compare(cmp.solve_destriper(cmp.reverse_within_baselines(self.timestream)))
        self.assertEqual(result["status"], "passed", result)

    def test_n4_exchanged_pixels_fail_on_association(self):
        result = self.compare(cmp.solve_destriper(cmp.exchange_pixels(self.timestream, baseline=0)))
        self.assertEqual(result["status"], "failed")
        self.assertIn("association", result["failed"])

    def test_n5_association_change_with_equal_numbers_fails_on_association_alone(self):
        result = self.compare(cmp.plant_design(self.reference))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed"], ["association"])

    def test_n6_value_change_beyond_the_tolerance_fails_within_it_passes(self):
        beyond = self.compare(cmp.plant_baselines(self.reference, 1e-6))
        self.assertEqual((beyond["status"], beyond["failed"]), ("failed", ["baselines"]))
        within = self.compare(cmp.plant_baselines(self.reference, 1e-9))
        self.assertEqual(within["status"], "passed", within)

    def test_n7_a_dropped_baseline_is_a_missing_object(self):
        result = self.compare(cmp.solve_destriper(cmp.drop_baseline(self.timestream, baseline=5)))
        self.assertEqual(result["status"], "failed")
        self.assertIn("objects", result["failed"])

    def test_n8_stopping_values_outside_the_records_are_rejected(self):
        with self.assertRaises(cmp.ComparatorInputError):
            self.compare(cmp.solve_destriper(self.timestream, stopping=1e-8))
        other = cmp.solve_destriper(self.timestream, stopping=1e-8)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.compare_numerical(DESTRIPER, other, other)

    def test_n8_a_tolerance_record_with_other_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "t10-replay.tolerance.json"
            record = json.loads(cmp.TOLERANCE_RECORDS[1e-10][0].read_text())
            record["tau_baselines"] = 1.0
            fake.write_text(json.dumps(record))
            with mock.patch.dict(cmp.TOLERANCE_RECORDS, {1e-10: (fake, cmp.TOLERANCE_RECORDS[1e-10][1])}):
                with self.assertRaises(cmp.ComparatorInputError):
                    self.compare(self.reference)

    def test_n8_the_tolerance_used_is_the_frozen_one(self):
        result = self.compare(self.reference)
        self.assertEqual(result["status"], "passed")
        self.assertEqual((result["tolerance"]["tau_baselines"], result["tolerance"]["tau_map"], result["tolerance"]["zero_sum_relative"]),
                         (2.5e-08, 2.2e-08, 1e-13))
        self.assertEqual(result["tolerance"]["sha256"], "217a38bc40769da9c750ac347228b120476008b0227f025f4fcbc02ce9d3c35e")

    def test_zero_sum_is_checked(self):
        planted = copy.deepcopy(self.reference)
        shift = 1e-9 * math.sqrt(sum(v * v for v in planted["baselines"]))
        planted["baselines"] = [v + shift for v in planted["baselines"]]
        planted["map"] = [v - shift for v in planted["map"]]
        cmp.resync_reported(planted)
        result = self.compare(planted)
        self.assertIn("zero_sum", result["failed"])

    def test_an_ambiguous_key_is_rejected(self):
        twin = copy.deepcopy(self.timestream)
        length = twin["baseline_length"]
        twin["value"][length:2 * length] = twin["value"][0:length]
        product = cmp.solve_destriper(twin)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.compare_numerical(DESTRIPER, product, product)

    def test_a_malformed_product_is_rejected(self):
        broken = copy.deepcopy(self.reference)
        del broken["solver"]
        with self.assertRaises(cmp.ComparatorInputError):
            self.compare(broken)

    def test_i1_another_pointing_is_rejected_by_the_derivation_check(self):
        """Fix round 1, I1: the record holds only for its own pointing (t10-destripe/1, seed 20260): seed 1's kappa is 24.24, not 24.47."""
        other = cmp.solve_destriper(cmp.destriper_fixture(seed=1))
        with self.assertRaises(cmp.ComparatorInputError) as raised:
            cmp.compare_numerical(DESTRIPER, other, other)
        self.assertIn("kappa", str(raised.exception))

    def test_i1_a_record_below_its_derivation_is_rejected(self):
        """A record with the right bytes for itself but tau below safety x kappa x eps is refused (T10's _check_record rule)."""
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "t10-replay.tolerance.json"
            record = json.loads(cmp.TOLERANCE_RECORDS[1e-10][0].read_text())
            record["tau_baselines"] = 1e-9
            fake.write_text(json.dumps(record))
            with mock.patch.dict(cmp.TOLERANCE_RECORDS, {1e-10: (fake, cmp._sha256(fake.read_bytes()))}):
                with self.assertRaises(cmp.ComparatorInputError) as raised:
                    self.compare(self.reference)
        self.assertIn("safety", str(raised.exception))

    def test_i1_the_derivation_and_the_ruling_are_reported(self):
        result = self.compare(self.reference)
        self.assertAlmostEqual(result["derivation"]["kappa"], 24.47, delta=0.01)
        self.assertAlmostEqual(result["derivation"]["map_gain"], 0.8757, delta=1e-4)
        self.assertEqual(result["ruling"], "OI-8")
        self.assertIn("same pointing", cmp.RULINGS["OI-8"])

    def test_the_noiseless_record_applies_to_noisy_products_at_its_stopping_value(self):
        """The 1e-13 record depends on the pointing only (OI-8 ruling): noisy products stopped at 1e-13 use it."""
        reference = cmp.solve_destriper(self.timestream, stopping=1e-13)
        result = cmp.compare_numerical(DESTRIPER, reference, cmp.solve_destriper(cmp.permute_baselines(self.timestream), stopping=1e-13))
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["tolerance"]["sha256"], "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698")
        self.assertEqual((result["tolerance"]["tau_baselines"], result["tolerance"]["tau_map"]), (2.5e-11, 2.2e-11))

    def test_n9_open_recipes_are_incomplete_never_passed(self):
        for recipe, item in OPEN_RECIPES.items():
            result = cmp.compare_numerical(recipe, {"any": 1}, {"any": 1})
            self.assertEqual((result["status"], result["open_item"]), ("incomplete", item), recipe)


class Statistical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = counts(20261113)

    def compare(self, candidate, quantity=FAKE_RATE, recipe=TRACK_FINDING):
        return cmp.compare_statistical(recipe, quantity, self.reference, candidate)

    def test_s2_reordered_events_pass_with_the_same_statistic(self):
        order = numpy.random.default_rng(3).permutation(len(self.reference["objects_per_event"]))
        reordered = {key: [values[i] for i in order] for key, values in self.reference.items()}
        itself, result = self.compare(self.reference), self.compare(reordered)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["statistic"], itself["statistic"])
        self.assertLessEqual(result["statistic"], 0.0025)

    def test_s3_added_fakes_beyond_tau_fail(self):
        candidate = copy.deepcopy(self.reference)
        rng = numpy.random.default_rng(5)
        candidate["failures_per_event"] = [int(min(m, y + rng.binomial(m, 0.01))) for m, y in
                                           zip(candidate["objects_per_event"], candidate["failures_per_event"])]
        result = self.compare(candidate)
        self.assertEqual(result["status"], "failed")
        self.assertIn("rate", result["failed"])
        self.assertGreater(result["statistic"], 0.0025)
        self.assertIn("association", result["statement"])

    def test_s4_a_lost_event_fails_even_when_the_rate_passes(self):
        candidate = {key: values[:-1] for key, values in self.reference.items()}
        result = self.compare(candidate)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed"], ["events"])

    def test_s5_the_statistic_equals_e6s_f2(self):
        candidate = counts_like(self.reference, 20261114)
        result = self.compare(candidate)
        reference = cmp.rate_bounds(self.reference)
        identity = core.BinIdentity("T07", 7002, 11, 0)  # agreement of the formula only: no evaluation event is scored
        e6 = scoring.stability_test("F2", identity, numpy.array(candidate["objects_per_event"]), numpy.array(candidate["failures_per_event"]),
                                    r_dev=reference["r"], l_dev=reference["lower"])
        self.assertAlmostEqual(result["statistic"], e6.estimate, delta=1e-15)
        self.assertEqual((result["status"], e6.result), ("passed", "pass"))

    def test_i2_a_lower_rate_beyond_tau_is_incomplete_not_passed(self):
        """Fix round 1, I2 (OI-10): F2 is one-sided; as a reproducibility rule a drop beyond tau (F2 with the roles exchanged) is no pass."""
        reference = counts(20261117, rate=0.01)
        candidate = {"objects_per_event": list(reference["objects_per_event"]),
                     "failures_per_event": [0] * len(reference["objects_per_event"])}
        result = cmp.compare_statistical(TRACK_FINDING, FAKE_RATE, reference, candidate)
        self.assertLessEqual(result["statistic"], 0.0025)            # F2 itself passes
        self.assertGreater(result["mirrored_statistic"], 0.0025)
        self.assertEqual((result["status"], result["open_item"]), ("incomplete", "OI-10"))
        self.assertIn("lower_rate", result["blocking"])

    def test_i2_a_changed_object_count_blocks_a_pass(self):
        candidate = copy.deepcopy(self.reference)
        candidate["objects_per_event"][0] += 1
        result = self.compare(candidate)
        self.assertEqual((result["status"], result["open_item"]), ("incomplete", "OI-10"))
        self.assertIn("objects", result["blocking"])
        self.assertEqual(result["readings"]["objects"], [sum(self.reference["objects_per_event"]), sum(self.reference["objects_per_event"]) + 1])

    def test_s6_other_quantities_and_recipes_are_incomplete(self):
        self.assertEqual(self.compare(self.reference, quantity="duplicate rate")["open_item"], "OI-2")
        self.assertEqual(self.compare(self.reference, recipe="reco.light.channel-likelihood/1")["open_item"], "OI-6")
        self.assertEqual(self.compare(self.reference, quantity="duplicate rate")["status"], "incomplete")
        for recipe, item in OPEN_RECIPES.items():
            if recipe != TRACK_FINDING:
                result = self.compare(self.reference, recipe=recipe)
                self.assertEqual((result["status"], result["open_item"]), ("incomplete", item))

    def test_the_destriper_has_no_statistical_form(self):
        with self.assertRaises(cmp.ComparatorInputError):
            self.compare(self.reference, recipe=DESTRIPER)

    def test_bad_counts_are_rejected(self):
        with self.assertRaises(cmp.ComparatorInputError):
            self.compare({"objects_per_event": [1, 2], "failures_per_event": [2, 0]})


class QualityBeforeSpeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_pulls, cls.variant_pulls = cmp.planted_samples()
        cls.baseline_gate = cmp.fixed_gate(cls.baseline_pulls)
        cls.variant_gate = cmp.fixed_gate(cls.variant_pulls)

    def candidates(self, working_point=False):
        return [cmp.Candidate("baseline", self.baseline_pulls, cmp.SealedTiming(10.0)),
                cmp.Candidate("faster-fatter-tail", self.variant_pulls, cmp.SealedTiming(6.0), working_point=working_point)]

    def report(self, candidates):
        """The report with the two planted samples' gates computed once (setUpClass); any other sample is gated afresh."""
        cached = {id(self.baseline_pulls): self.baseline_gate, id(self.variant_pulls): self.variant_gate}
        original = cmp.fixed_gate
        with mock.patch.object(cmp, "fixed_gate", side_effect=lambda pulls: cached.get(id(pulls)) or original(pulls)):
            return cmp.quality_before_speed(candidates)

    def test_q1_the_baseline_passes_every_gate(self):
        gate = self.baseline_gate
        self.assertEqual([gate[k].result for k in ("centre", "width", "tail")], ["pass", "pass", "pass"])
        self.assertEqual(gate["word"], "pass")

    def test_q2_the_variant_fails_the_tail_at_step_1_only(self):
        gate = self.variant_gate
        self.assertEqual([gate[k].result for k in ("centre", "width", "tail")], ["pass", "pass", "fail"])
        self.assertEqual(gate["tail"].step, 1)
        self.assertGreater(gate["tail"].lower, 0.01)
        self.assertEqual(gate["word"], "fail")

    def test_i4_a_variant_that_drops_its_tail_objects_fails_the_tail(self):
        """Fix round 1, I4: objects without a result (NaN) count as failures in the tail, as E6 does (v4 5.1)."""
        dropper = self.variant_pulls.copy()
        dropper[numpy.abs(dropper) > 3] = numpy.nan
        gate = cmp.fixed_gate(dropper)
        self.assertEqual((gate["tail"].result, gate["word"]), ("fail", "fail"))
        self.assertEqual(gate["without_result"], int(numpy.isnan(dropper).sum()))
        report = cmp.quality_before_speed([cmp.Candidate("dropper", dropper, cmp.SealedTiming(5.0))])
        self.assertEqual(report["candidates"][0]["disposition"], "rejected under the fixed gates")

    def test_i4_candidates_with_other_object_counts_are_rejected(self):
        """The same scientific work (Section 14.2): a candidate that silently drops objects from its list is refused."""
        with self.assertRaises(cmp.ComparatorInputError):
            self.report([cmp.Candidate("baseline", self.baseline_pulls, cmp.SealedTiming(10.0)),
                         cmp.Candidate("short", self.variant_pulls[:11000], cmp.SealedTiming(5.0))])

    def test_m3_a_timing_is_sealed_to_its_candidate(self):
        timing = cmp.SealedTiming(3.0)
        self.assertFalse(hasattr(timing, "value"))
        a = cmp.Candidate("a", self.baseline_pulls, timing)
        b = cmp.Candidate("b", self.baseline_pulls, cmp.SealedTiming(4.0))
        with self.assertRaises(cmp.ComparatorInputError):
            timing.release(cmp.gate_record(b, self.baseline_gate))
        self.assertEqual(timing.release(cmp.gate_record(a, self.baseline_gate))["value"], 3.0)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.Candidate("c", self.baseline_pulls, timing)   # one timing, one candidate

    def test_m3_r2_a_forged_record_releases_nothing(self):
        """Fix round 2, case 1: only a record made by gate_record releases a timing; a dict or a look-alike object never does."""
        timing = cmp.SealedTiming(3.0)
        cmp.Candidate("a", self.baseline_pulls, timing)
        with self.assertRaises(cmp.ComparatorInputError):
            timing.release({"candidate": "a", "complete": True})
        with self.assertRaises(cmp.ComparatorInputError):
            timing.release({"candidate": "a", "complete": True, "word": "pass", "passed": True})
        genuine = cmp.gate_record(cmp.Candidate("z", self.baseline_pulls, cmp.SealedTiming(1.0)), self.baseline_gate)
        look_alike = copy.copy(genuine)
        with self.assertRaises(cmp.ComparatorInputError):
            timing.release(look_alike)

    def test_m3_r2_a_failed_candidate_without_a_working_point_releases_nothing(self):
        """Fix round 2, case 2: called directly, release refuses a failed gate unless the candidate declared a working point."""
        timing = cmp.SealedTiming(6.0)
        variant = cmp.Candidate("variant", self.variant_pulls, timing)
        with self.assertRaises(cmp.ComparatorInputError):
            timing.release(cmp.gate_record(variant, self.variant_gate))
        declared_timing = cmp.SealedTiming(6.0)
        declared = cmp.Candidate("variant", self.variant_pulls, declared_timing, working_point=True)
        self.assertEqual(declared_timing.release(cmp.gate_record(declared, self.variant_gate))["value"], 6.0)

    def test_m3_r2_a_timing_is_bound_to_the_candidate_object_not_its_name(self):
        """Fix round 2, case 3: two candidates of one name are not interchangeable, and a report refuses duplicate names."""
        first_timing, second_timing = cmp.SealedTiming(1.0), cmp.SealedTiming(2.0)
        first = cmp.Candidate("same", self.baseline_pulls, first_timing)
        second = cmp.Candidate("same", self.baseline_pulls, second_timing)
        with self.assertRaises(cmp.ComparatorInputError):
            first_timing.release(cmp.gate_record(second, self.baseline_gate))
        self.assertEqual(second_timing.release(cmp.gate_record(second, self.baseline_gate))["value"], 2.0)
        with self.assertRaises(cmp.ComparatorInputError):
            self.report([cmp.Candidate("dup", self.baseline_pulls, cmp.SealedTiming(1.0)),
                         cmp.Candidate("dup", self.variant_pulls, cmp.SealedTiming(2.0))])

    def test_n4_the_working_point_is_declared_before_the_gate(self):
        candidate = cmp.Candidate("v", self.variant_pulls, cmp.SealedTiming(6.0))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            candidate.working_point = True

    def test_q3_the_faster_variant_is_rejected_and_shows_no_speed(self):
        report = self.report(self.candidates())
        entries = {entry["name"]: entry for entry in report["candidates"]}
        self.assertEqual(entries["faster-fatter-tail"]["disposition"], "rejected under the fixed gates")
        self.assertIsNone(entries["faster-fatter-tail"]["speed"])
        self.assertNotIn("6.0", json.dumps(entries["faster-fatter-tail"]))
        self.assertEqual(entries["baseline"]["disposition"], "qualified")
        self.assertEqual(entries["baseline"]["speed"]["value"], 10.0)
        self.assertEqual(report["selected"], "baseline")

    def test_q4_declared_as_a_working_point_it_is_listed_never_selected(self):
        report = self.report(self.candidates(working_point=True))
        entry = {e["name"]: e for e in report["candidates"]}["faster-fatter-tail"]
        self.assertEqual(entry["disposition"], "listed as another working point")
        self.assertEqual(entry["quality"]["tail"]["result"], "fail")
        self.assertEqual(entry["speed"]["value"], 6.0)
        self.assertIn("not qualified under the fixed gates; not a replacement", entry["speed"]["label"])
        self.assertEqual(report["selected"], "baseline")

    def test_q5_no_timing_is_released_before_its_gate(self):
        log = []

        class Spy(cmp.SealedTiming):
            def release(self, gate):
                log.append(("release", self._value, getattr(gate, "complete", False) is True))
                return super().release(gate)

        def gated(pulls):
            log.append(("gate", len(pulls)))
            return self.baseline_gate if pulls is self.baseline_pulls else self.variant_gate

        candidates = [cmp.Candidate("baseline", self.baseline_pulls, Spy(10.0)),
                      cmp.Candidate("variant", self.variant_pulls, Spy(6.0), working_point=True)]
        with mock.patch.object(cmp, "fixed_gate", side_effect=gated):
            report = cmp.quality_before_speed(candidates)
        releases = [entry for entry in log if entry[0] == "release"]
        self.assertTrue(releases and all(entry[2] for entry in releases))
        self.assertEqual(log[0][0], "gate")
        self.assertLess(log.index(("gate", len(self.variant_pulls))), log.index(("release", 6.0, True)))
        for entry in report["candidates"]:
            keys = list(entry)
            self.assertLess(keys.index("quality"), keys.index("speed"))
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.SealedTiming(1.0).release(None)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.SealedTiming(1.0).release({"complete": False})
        incomplete = dict(self.baseline_gate, tail=None)
        with self.assertRaises(cmp.ComparatorInputError):
            cmp.gate_record(cmp.Candidate("x", self.baseline_pulls, cmp.SealedTiming(1.0)), incomplete)

    def test_q6_nothing_qualifies_when_every_candidate_fails(self):
        report = self.report([cmp.Candidate("a", self.variant_pulls, cmp.SealedTiming(6.0)),
                              cmp.Candidate("b", self.variant_pulls, cmp.SealedTiming(5.0))])
        self.assertIsNone(report["selected"])
        self.assertIn("no qualified candidate", report["statement"])
        self.assertTrue(all(entry["speed"] is None for entry in report["candidates"]))

    def test_q7_an_inconclusive_gate_withholds_speed(self):
        small = self.baseline_pulls[:2000]
        report = cmp.quality_before_speed([cmp.Candidate("small", small, cmp.SealedTiming(1.0))])
        entry = report["candidates"][0]
        self.assertEqual(entry["quality"]["word"], "inconclusive")
        self.assertIsNone(entry["speed"])
        self.assertIsNone(report["selected"])

    def test_q8_the_gate_constants_are_the_cores(self):
        self.assertEqual(cmp.GATE_CONSTANTS, {"tolerance": core.TOLERANCE, "precision_cap": core.PRECISION_CAP, "tail_limit": 0.01,
                                              "tail_pull": 3.0, "confidence": 0.95})
        self.assertEqual((core.TOLERANCE, core.PRECISION_CAP), (0.10, 0.0108))
        import inspect
        self.assertEqual(list(inspect.signature(cmp.fixed_gate).parameters), ["pulls"])


class CommandLine(unittest.TestCase):
    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cmp.main(list(argv))
        return code, out.getvalue()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)
        self.addCleanup(self.folder.cleanup)

    def write(self, name, content):
        path = self.dir / name
        path.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
        return str(path)

    def test_byte_pass_and_fail(self):
        a, b, c = self.write("a", b"same"), self.write("b", b"same"), self.write("c", b"other")
        self.assertEqual(self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "byte", "--reference", a, "--candidate", b,
                                       "--out", str(self.dir / "r1.json"))[0], 0)
        self.assertEqual(self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "byte", "--reference", a, "--candidate", c,
                                       "--out", str(self.dir / "r2.json"))[0], 1)
        self.assertEqual(json.loads((self.dir / "r2.json").read_text())["status"], "failed")

    def test_open_tolerance_exits_3_and_names_the_open_item(self):
        a = self.write("a.json", {"x": 1})
        code, text = self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "numerical", "--reference", a, "--candidate", a,
                                   "--out", str(self.dir / "r.json"))
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(text)["open_item"], "OI-1")   # I3, M5

    def test_n3_an_open_recipe_with_non_json_input_is_incomplete(self):
        a = self.write("a.bin", b"\xff not json")
        code, _ = self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "numerical", "--reference", a, "--candidate", a,
                                "--out", str(self.dir / "r.json"))
        self.assertEqual(code, 3)

    def test_rejections_exit_2(self):
        a = self.write("a.json", {"x": 1})
        existing = self.write("exists.json", {})
        for argv in (("--recipe", "reco.unknown/1", "--form", "byte", "--reference", a, "--candidate", a, "--out", str(self.dir / "u.json")),
                     ("--recipe", TRACK_FINDING, "--form", "byte", "--reference", a, "--candidate", a, "--out", existing),
                     ("--recipe", TRACK_FINDING, "--form", "byte", "--reference", a, "--candidate", a, "--out", str(self.dir / "no" / "r.json")),
                     ("--recipe", DESTRIPER, "--form", "statistical", "--reference", a, "--candidate", a, "--out", str(self.dir / "s.json")),
                     ("--recipe", TRACK_FINDING, "--form", "byte", "--reference", str(self.dir / "absent"), "--candidate", a, "--out", str(self.dir / "m.json"))):
            self.assertEqual(self.run_main("compare", *argv)[0], 2, argv)
        self.assertEqual(json.loads(Path(existing).read_text()), {})

    def test_numerical_and_statistical_through_files(self):
        timestream = cmp.destriper_fixture()
        reference = self.write("ref.json", cmp.dumps_product(cmp.solve_destriper(timestream)))
        candidate = self.write("cand.json", cmp.dumps_product(cmp.solve_destriper(cmp.permute_baselines(timestream, seed=7))))
        code, text = self.run_main("compare", "--recipe", DESTRIPER, "--form", "numerical", "--reference", reference, "--candidate", candidate,
                                   "--out", str(self.dir / "n.json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["ruling"], "OI-8")       # I3: a pass under a ruling names it
        r = counts(20261113)
        reference, candidate = self.write("r.json", r), self.write("c.json", counts_like(r, 20261114))
        code, _ = self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "statistical", "--quantity", FAKE_RATE, "--reference", reference,
                                "--candidate", candidate, "--out", str(self.dir / "s.json"))
        self.assertEqual(code, 0)
        lower = self.write("l.json", {"objects_per_event": r["objects_per_event"], "failures_per_event": [0] * len(r["objects_per_event"])})
        high = self.write("h.json", counts_like(r, 7, rate=0.01))
        code, text = self.run_main("compare", "--recipe", TRACK_FINDING, "--form", "statistical", "--reference", high, "--candidate", lower,
                                   "--out", str(self.dir / "l-out.json"))
        self.assertEqual((code, json.loads(text)["open_item"]), (3, "OI-10"))

    def test_declarations(self):
        code, text = self.run_main("declarations")
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(text)["declarations"]), set(cmp.RECIPES))


if __name__ == "__main__":
    unittest.main()

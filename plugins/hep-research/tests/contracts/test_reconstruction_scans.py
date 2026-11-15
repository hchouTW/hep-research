"""Witness W7 of the reconstruction contracts (plan Section 12, contract-map.md): scan, coherent and global subcases,
kept separate and merged into no solver. The contract part of A25 is in test_reconstruction_records.py. Passing W7
replaces no native backend of the three subcases. Synthetic documents only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import matrix_rank, read_sidecar  # noqa: E402
from tests.contracts.reconstruction_fixtures import code_list, global_scan, radio_frequency_scan, retarding_scan, scan_product  # noqa: E402


def refused(scan):
    return code_list(read_sidecar(scan_product(scan)))


class Common(unittest.TestCase):
    def test_three_subcases_are_read(self):
        for scan in (radio_frequency_scan(), retarding_scan(), global_scan()):
            self.assertEqual(refused(scan), [], scan["subcase"])

    def test_each_subcase_describes_its_common_fields(self):
        for field in ("source_ref", "coordinates", "conditions_ref", "response_ref", "noise_model", "merging", "unidentifiable"):
            for build in (radio_frequency_scan, retarding_scan, global_scan):
                scan = build()
                del scan[field]
                self.assertTrue(refused(scan), field)

    def test_subcases_stay_separate(self):
        scan = radio_frequency_scan()
        scan["visits"] = retarding_scan()["visits"]
        self.assertIn("reconstruction.scan.subcases_merged", refused(scan))

    def test_subcase_needs_its_own_fields(self):
        scan = radio_frequency_scan()
        del scan["settings"]
        self.assertIn("reconstruction.scan.subcase_incomplete", refused(scan))

    def test_independent_poisson_needs_premises(self):
        scan = retarding_scan()
        scan["noise_model"] = {"kind": "independent-poisson", "premises": []}
        self.assertIn("reconstruction.scan.independent_poisson", refused(scan))

    def test_frequency_time_track_is_not_a_spatial_track(self):
        """M3: the review's probe."""
        for build in (radio_frequency_scan, retarding_scan):
            scan = build()
            scan["coordinates"] = [{"axis": "frequency-time-track", "kind": "spatial", "unit": "mm"}]
            self.assertIn("reconstruction.scan.track_as_spatial", refused(scan))

    def test_a_global_map_may_be_spatial(self):
        scan = global_scan()
        scan["coordinates"] = [{"axis": "sky-position", "kind": "spatial", "unit": "deg"}]
        self.assertEqual(refused(scan), [])

    def test_a_real_spatial_coordinate_is_not_a_track(self):
        """Re-review 2 minor 12: W7's negative is a frequency-time track, not every spatial axis."""
        for build, axis in ((radio_frequency_scan, "pixel-radius"), (retarding_scan, "antenna-position"), (global_scan, "time-of-flight-position"), (global_scan, "sky-time-map")):
            scan = build()
            scan["coordinates"].append({"axis": axis, "kind": "spatial", "unit": "mm"})
            self.assertEqual(refused(scan), [], axis)

    def test_a_short_name_for_the_track_is_caught(self):
        """Re-review 2 minor 12."""
        scan = global_scan()
        scan["coordinates"] = [{"axis": "freq-t-track", "kind": "spatial", "unit": "mm"}]
        self.assertEqual(refused(scan), ["reconstruction.scan.track_as_spatial"])

    def test_a_global_scan_cannot_call_a_track_spatial_either(self):
        """Re-review minor 6."""
        scan = global_scan()
        scan["coordinates"] = [{"axis": "frequency-time-track", "kind": "spatial", "unit": "mm"}]
        self.assertEqual(refused(scan), ["reconstruction.scan.track_as_spatial"])


class RadioFrequencyScan(unittest.TestCase):
    def setUp(self):
        self.scan = radio_frequency_scan()

    def test_coordinates_map_through_each_oscillator(self):
        self.scan["settings"][1]["local_oscillator"]["value"] = 1000
        self.assertIn("reconstruction.scan.coordinate_map", refused(self.scan))

    def test_the_sideband_is_declared(self):
        """Minor 7: a high-side oscillator is a declared sign, not a negative interval."""
        self.scan["settings"][1].update({"local_oscillator": {"value": 1040, "unit": "MHz"}, "sideband_sign": -1, "intermediate_interval": [10, 30]})
        self.assertEqual(refused(self.scan), [])

    def test_float_rounding_is_not_a_wrong_map(self):
        """Minor 7."""
        self.scan["settings"][0].update({"local_oscillator": {"value": 0.1, "unit": "MHz"}, "intermediate_interval": [0.2, 0.3], "physical_interval": [0.3, 0.4]})
        self.assertEqual(refused(self.scan), [])

    def test_rounding_at_a_zero_edge_is_not_a_wrong_map(self):
        """Re-review minor 11: the margin follows the terms, so an edge of 5.6e-17 is zero."""
        self.scan["settings"][0].update({"local_oscillator": {"value": 0.1 + 0.2, "unit": "MHz"}, "intermediate_interval": [-0.3, 0.7], "physical_interval": [0.0, 1.0]})
        self.assertEqual(refused(self.scan), [])
        self.scan["settings"][0]["physical_interval"] = [1e-3, 1.0]
        self.assertEqual(refused(self.scan), ["reconstruction.scan.coordinate_map"])

    def test_one_overlap_may_join_three_settings(self):
        """Re-review minor 10."""
        third = dict(self.scan["settings"][0], setting_id="setting-3", raw_segments=["raw-2"])
        self.scan["settings"].append(third)
        self.scan["overlaps"][0]["settings"].append("setting-3")
        self.assertEqual(refused(self.scan), [])

    def test_an_oscillator_in_another_unit_maps_correctly(self):
        """Re-review 2 minor 10: one frequency in two units."""
        self.scan["settings"][0]["local_oscillator"] = {"value": 1.0, "unit": "GHz"}
        self.assertEqual(refused(self.scan), [])

    def test_units_that_cannot_be_compared_are_named(self):
        self.scan["settings"][0]["interval_unit"] = "bananas"
        self.assertEqual(refused(self.scan), ["reconstruction.scan.coordinate_map"])

    def test_units_are_compared(self):
        """Minor 7."""
        self.scan["settings"][0]["interval_unit"] = "kHz"
        self.assertIn("reconstruction.scan.coordinate_map", refused(self.scan))

    def test_unmarked_shared_raw_data_is_caught(self):
        self.scan["overlaps"] = []
        self.assertIn("reconstruction.scan.overlap_unmarked", refused(self.scan))

    def test_shared_noise_is_not_independent_poisson(self):
        self.scan["noise_model"] = {"kind": "independent-poisson", "premises": ["stated"]}
        self.assertIn("reconstruction.scan.independent_poisson", refused(self.scan))

    def test_a_shared_segment_is_shared_noise_whatever_the_flag_says(self):
        """M4: the review's probe."""
        self.scan["overlaps"][0]["shared_noise"] = False
        self.scan["noise_model"] = {"kind": "independent-poisson", "premises": ["stated"]}
        found = refused(self.scan)
        self.assertIn("reconstruction.scan.shared_noise_denied", found)
        self.assertIn("reconstruction.scan.independent_poisson", found)

    def test_a_stated_premise_can_separate_the_noise(self):
        """M4: a shared segment is shared noise unless a premise says otherwise."""
        self.scan["overlaps"][0].update({"shared_noise": False, "noise_premise": "the shared segment was re-digitized independently"})
        self.scan["noise_model"] = {"kind": "independent-poisson", "premises": ["stated"]}
        self.assertEqual(refused(self.scan), [])

    def test_a_record_that_says_shared_is_never_independent_poisson(self):
        """RM5: W7 names the independent-Poisson assumption as a negative, whatever premise is attached."""
        self.scan["overlaps"][0]["noise_premise"] = "anything"
        self.scan["noise_model"] = {"kind": "independent-poisson", "premises": ["stated"]}
        self.assertEqual(refused(self.scan), ["reconstruction.scan.independent_poisson"])

    def test_marked_overlap_needs_a_shared_segment(self):
        """M4."""
        self.scan["overlaps"][0]["raw_segments"] = ["raw-2", "raw-3"]
        self.assertIn("reconstruction.scan.overlap_unsupported", refused(self.scan))

    def test_shared_raw_data_is_not_independent_exposure(self):
        self.scan["overlaps"][0]["independent_exposure"] = True
        self.assertIn("reconstruction.scan.shared_raw_as_independent", refused(self.scan))


class RetardingScan(unittest.TestCase):
    def setUp(self):
        self.scan = retarding_scan()

    def test_chunk_average_is_caught(self):
        self.scan["merging"] = {"kind": "chunk-average"}
        self.assertIn("reconstruction.scan.chunk_average", refused(self.scan))

    def test_each_visit_keeps_its_transmission_and_conditions(self):
        for field in ("dwell", "count", "transmission_ref", "conditions_ref"):
            scan = retarding_scan()
            del scan["visits"][0][field]
            self.assertTrue(refused(scan), field)


class GlobalEstimate(unittest.TestCase):
    def setUp(self):
        self.scan = global_scan()

    def test_the_reported_sum_is_checked(self):
        """Minor 2."""
        self.scan["reported"][0]["value"] = 999
        self.assertEqual(refused(self.scan), ["reconstruction.scan.reported_mismatch"], "consistent data, so every estimator gives 3")

    def test_observation_length_is_checked(self):
        """Minor 2."""
        self.scan["model"]["observation"] = [3]
        self.assertIn("reconstruction.scan.dimension_mismatch", refused(self.scan))

    def test_identical_observations_add_no_information(self):
        self.scan["model"]["design"].append([1, 1])
        self.scan["model"]["observation"].append(3)
        self.assertEqual(matrix_rank(self.scan["model"]["design"]), 1)
        self.assertEqual(refused(self.scan), [])

    def test_a_single_parameter_is_not_reported(self):
        self.scan["reported"] = [{"weights": [1, 0], "value": 1}]
        self.assertIn("reconstruction.scan.unidentifiable_reported", refused(self.scan))

    def test_unidentifiable_parameters_are_named(self):
        self.scan["unidentifiable"] = []
        self.assertIn("reconstruction.scan.unidentifiable_unnamed", refused(self.scan))

    def test_unique_solution_after_jitter_is_caught(self):
        self.scan.update({"regularization": "jitter", "uniqueness_claim": True})
        found = refused(self.scan)
        self.assertIn("reconstruction.scan.jitter_precision", found)
        self.assertIn("reconstruction.scan.unique_claim", found)

    def test_dimensions_must_agree(self):
        for change in ({"reported": [{"weights": [1], "value": 3}]}, {"constraint": {"statement": "stated", "weights": [1], "value": 1}},
                       {"model": {"parameters": ["sky", "offset"], "design": [[1, 1], [1]], "observation": [3, 3]}}):
            scan = global_scan()
            scan.update(change)
            self.assertIn("reconstruction.scan.dimension_mismatch", refused(scan), change)

    def test_a_correct_inverse_variance_value_is_not_refused(self):
        """RM3: W7 names no estimator. Observations 2 and 4 of s + b with sigma 1 and 2 give 2.4 by inverse variance."""
        self.scan["model"]["observation"] = [2, 4]
        for value in (2.4, 3):
            self.scan["reported"][0]["value"] = value
            self.assertEqual(refused(self.scan), [], value)

    def test_a_correct_exact_constraint_value_is_not_refused(self):
        """RM3: data 1 and 1 with the exact constraint s + b = 3 give 3; a soft constraint gives 8/3. Neither is refused."""
        self.scan["model"].update({"design": [[1, 0], [0, 1]], "observation": [1, 1]})
        self.scan.update({"constraint": {"statement": "stated sum", "weights": [1, 1], "value": 3}, "unidentifiable": []})
        for value in (3, 8 / 3):
            self.scan["reported"] = [{"weights": [1, 1], "value": value}]
            self.assertEqual(refused(self.scan), [], value)

    def test_a_row_the_data_fix_is_checked_under_a_prior(self):
        """Re-review 2 minor 15: consistent data fix s + b, so a prior on b cannot change it."""
        self.scan.update({"constraint": {"statement": "a stated prior on the offset", "weights": [0, 1]}, "reported": [{"weights": [1, 1], "value": 9}],
                          "unidentifiable": []})
        self.assertEqual(refused(self.scan), ["reconstruction.scan.reported_mismatch"])

    def test_a_prior_states_no_single_value(self):
        """RM3: W7, "state the added constraint/prior explicitly"."""
        self.scan.update({"constraint": {"statement": "a stated prior on the offset", "weights": [0, 1]}, "reported": [{"weights": [1, 0], "value": 1}],
                          "unidentifiable": []})
        self.assertEqual(refused(self.scan), [])

    def test_a_stated_constraint_can_separate_them(self):
        self.scan.update({"constraint": {"statement": "offset fixed by a stated external measurement", "weights": [0, 1], "value": 2},
                          "reported": [{"weights": [1, 0], "value": 1}], "unidentifiable": [], "uniqueness_claim": True})
        self.assertEqual(refused(self.scan), [])

    def test_a_design_with_a_small_unit_column_is_identified(self):
        """Re-review 3 N1: a scan has no comparator, so its rank at the ceiling must not depend on the units of a parameter.
        Powers of two keep the stored numbers exact, so the reported value is compared too."""
        self.scan["model"].update({"design": [[1, 2 ** -40], [1, 3 * 2 ** -40]], "observation": [1 + 2 ** -39, 1 + 3 * 2 ** -39]})
        self.scan.update({"reported": [{"weights": [1, 0], "value": 1}], "unidentifiable": [], "uniqueness_claim": True})
        self.assertEqual(refused(self.scan), [])
        self.scan["reported"][0]["value"] = 2
        self.assertEqual(refused(self.scan), ["reconstruction.scan.reported_mismatch"])

    def test_a_zero_design_determines_nothing(self):
        """Re-review 4 P1, A34: a reported value on a zero design is refused unless both parameters are named undetermined."""
        self.scan["model"]["design"] = [[0, 0], [0, 0]]
        self.scan.update({"reported": [{"weights": [1, 0], "value": 7}], "unidentifiable": []})
        self.assertEqual(refused(self.scan), ["reconstruction.scan.unidentifiable_reported", "reconstruction.scan.unidentifiable_unnamed"])
        self.scan.update({"reported": [], "unidentifiable": ["sky", "offset"]})
        self.assertEqual(refused(self.scan), [])


if __name__ == "__main__":
    unittest.main()

"""The driver of a new specification's run: resolution of the request, read-back and closure checks, without Geant4."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters/geant4/assets"))

import g4sim_simulate as simulate  # noqa: E402

from core.geometry import identity, segmentation  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402
from core.simulation.source_density import SourceError  # noqa: E402

SOURCE = {"density": "analytic", "particle": "e-", "energy": {"mono": {"energy_MeV": "10"}}, "position": {"point": {"frame": "beam", "centre_mm": ["1", "2", "3"]}},
          "direction": {"from_point": {"frame": "beam", "point_mm": ["0", "0", "-1"]}}}
IR = {"physical": {"frames": {"beam": {"in": "world", "origin_mm": ["0", "0", "-100"]}, "inner": {"in": "block", "origin_mm": ["0", "0", "0"]}},
                   "templates": {"block": {"material": "m"}}, "materials": {"m": {"ionisation": {"birks_mm_per_MeV": "0.1"}}}},
      "marker": {"tags": {"block": ["active"]}}}


class CellEncoding(unittest.TestCase):
    FIELDS = [{"name": "ix", "kind": "copy", "width": 2, "stride": 1}, {"name": "iy", "kind": "copy", "width": 2, "stride": 4}, {"name": "iz", "kind": "segmentation", "width": 3, "stride": 16}]
    PLACED = [{"mother": "world", "template": "module", "copy_number": 0, "index": {}}, {"mother": "module", "template": "crystal", "copy_number": 6, "index": {"ix": 2, "iy": 1}}, {"mother": "module", "template": "crystal", "copy_number": 0, "index": {"ix": 0, "iy": 0}}]

    def encoding(self, placed=None, scorer=None, kind="along_axis", fields=None):
        ir = {"physical": {"readout": {"cal": {"fields": fields or self.FIELDS}}, "placements": self.PLACED if placed is None else placed}}
        return simulate.cell_encoding(scorer or {"readout": "cal", "segment_fields": ["iz"]}, kind, ir, ["crystal"])

    def test_a_copy_adds_its_indices_at_their_strides_whatever_its_packing(self):
        encoding = self.encoding()
        self.assertEqual(encoding["copies"]["crystal"], {"6": str(2 + 4), "0": "0"})
        self.assertEqual(encoding["segments"], [{"stride": 16, "limit": 8}])

    def test_a_cellid_above_a_double_stays_exact_as_text(self):
        fields = [{"name": "top", "kind": "copy", "width": 11, "stride": 2 ** 53}]
        placed = [{"mother": "world", "template": "crystal", "copy_number": 3, "index": {"top": 3}}]
        self.assertEqual(self.encoding(placed, {"readout": "cal"}, "none", fields)["copies"]["crystal"]["3"], str(3 * 2 ** 53))

    def test_two_volumes_of_one_cellid_are_refused(self):
        unindexed = [{"mother": "world", "template": "crystal", "copy_number": copy, "index": {}} for copy in (0, 1)]
        outside = [{"mother": "world", "template": "module", "copy_number": copy, "index": {"mi": copy}} for copy in (0, 1)] + [{"mother": "module", "template": "crystal", "copy_number": 0, "index": {"ix": 0}}]
        two_mothers = [{"mother": "world", "template": name, "copy_number": 0, "index": {}} for name in ("a", "b")] + [{"mother": name, "template": "crystal", "copy_number": 0, "index": {}} for name in ("a", "b")]
        for placed in (unindexed, outside, two_mothers):
            with self.subTest(placed=placed[0]):
                self.assertIn("one cellID", self.encoding(placed)["problem"])

    def test_a_field_filled_at_two_levels_is_refused(self):
        placed = [{"mother": "world", "template": "module", "copy_number": 1, "index": {"ix": 1}}, {"mother": "module", "template": "crystal", "copy_number": 1, "index": {"ix": 1}}]
        self.assertIn("two levels", self.encoding(placed)["problem"])

    def test_segment_fields_are_distinct_segmentation_fields_one_per_axis(self):
        second = {"name": "jz", "kind": "segmentation", "width": 2, "stride": 128}
        for scorer, kind, fields in (({"readout": "cal"}, "along_axis", None), ({"readout": "cal", "segment_fields": ["iz", "ix"]}, "along_axis", None), ({"readout": "cal"}, "none", None), ({"readout": "cal", "segment_fields": ["ix"]}, "along_axis", None), ({"readout": "cal", "segment_fields": ["iz", "iz"]}, "cartesian_xy", self.FIELDS + [second])):
            with self.subTest(scorer=scorer, kind=kind):
                self.assertIn("segment_fields", self.encoding(None, scorer, kind, fields)["problem"])

    def test_what_cannot_be_encoded_is_a_problem(self):
        two = [{"mother": "world", "template": "crystal", "copy_number": 0, "index": {"ix": 1}}, {"mother": "other", "template": "crystal", "copy_number": 0, "index": {"ix": 2}}]
        self.assertIn("declare two templates", self.encoding(two)["problem"])
        self.assertIn("no cellID", self.encoding(None, None, "cartesian_zz")["problem"])
        self.assertIn("not declared", self.encoding(None, {"readout": "other"})["problem"])


class Resolution(unittest.TestCase):
    def test_a_frame_becomes_world_coordinates(self):
        record = simulate.resolved_source(SOURCE, IR["physical"]["frames"])
        self.assertEqual(record["position"]["centre_mm"], [1, 2, -97])
        self.assertEqual(record["direction"]["point_mm"], [0, 0, -101])

    def test_a_frame_inside_a_template_is_refused(self):
        block = {**SOURCE, "position": {"point": {"frame": "inner", "centre_mm": [0, 0, 0]}}}
        with self.assertRaises(SourceError):
            simulate.resolved_source(block, IR["physical"]["frames"])

    def test_segmentations_are_flattened(self):
        self.assertEqual(simulate.resolved_segmentation({"along_axis": {"axis": "y", "width_mm": "2"}}), {"kind": "along_axis", "axis": 1, "width_mm": [2.0]})
        self.assertEqual(simulate.resolved_segmentation(None), {"kind": "none"})

    def test_tags_select_templates(self):
        self.assertEqual(identity.selected_templates({"tags": ["active"]}, IR), ["block"])


class ReadBack(unittest.TestCase):
    RESOLVED = {"scorers": [{"name": "s", "quantity": "edep_visible", "templates": ["block"]}]}
    EFFECTIVE = {"birks_mm_per_MeV": {"m": 0.1}, "step_functions": ["Step function for e+-     (0.1, 0.5 mm)"], "msc_range_factor": 0.02, "msc_muhad_range_factor": 0.2}

    def test_equal_values_pass(self):
        card = {"physics": {"em_parameters": {"step_function_electron": ["0.1", "0.5"], "msc_range_factor": "0.02"}}}
        self.assertEqual(simulate.effective_problems(self.EFFECTIVE, card, IR, self.RESOLVED), [])

    def test_a_silently_set_birks_constant_is_refused(self):
        self.assertEqual(len(simulate.effective_problems({**self.EFFECTIVE, "birks_mm_per_MeV": {"m": 0.126}}, {}, IR, self.RESOLVED)), 1)

    def test_a_step_function_reset_by_the_constructor_is_refused(self):
        card = {"physics": {"em_parameters": {"step_function_electron": ["0.05", "0.5"]}}}
        self.assertEqual(len(simulate.effective_problems(self.EFFECTIVE, card, IR, self.RESOLVED)), 1)


class PaiReadBack(unittest.TestCase):
    PLAIN = {"DefaultRegionForTheWorld": {"eIoni/e-": [["MollerBhabha", "UrbanFluc"]]}, "tracker": {"eIoni/e-": [["MollerBhabha", "UrbanFluc"]]}}
    REQUESTS = [{"region": "tracker", "particle": "e-", "model": "PAI"}]
    WITH_PAI = {"DefaultRegionForTheWorld": {"eIoni/e-": [["MollerBhabha", "UrbanFluc"]]}, "tracker": {"eIoni/e-": [["PAIModel", "PAIModel"]]}}

    def test_models_outside_the_region_unchanged_pass(self):
        self.assertEqual(simulate.outside_differences(self.WITH_PAI, self.PLAIN, self.REQUESTS), [])

    def test_a_changed_fluctuation_model_outside_is_an_error(self):
        changed = {**self.WITH_PAI, "DefaultRegionForTheWorld": {"eIoni/e-": [["MollerBhabha", "UniFluc"]]}}
        self.assertEqual(len(simulate.outside_differences(changed, self.PLAIN, self.REQUESTS)), 1)

    def test_an_empty_read_back_is_an_error_and_never_a_pass(self):
        self.assertEqual(len(simulate.outside_differences({}, {}, self.REQUESTS)), 1)
        self.assertEqual(len(simulate.missing_pai({}, self.REQUESTS, {"e-": "eIoni"})), 1)

    def test_a_request_geant4_did_not_apply_is_an_error(self):
        table = {"e-": "eIoni"}
        self.assertEqual(simulate.missing_pai(self.WITH_PAI, self.REQUESTS, table), [])
        self.assertEqual(len(simulate.missing_pai(self.PLAIN, self.REQUESTS, table)), 1)


class Closure(unittest.TestCase):
    ROWS = [["0", "s", "1", "0", "1.5", "2", "1.5"], ["0", "s", "1", "1", "2.5", "1", "2.5"], ["0", "s", "-1", "-1", "4", "3", "4"]]

    def test_bins_that_sum_to_the_total_pass(self):
        self.assertEqual(simulate.closure_problems(self.ROWS)["failing"], 0)

    def test_a_dropped_bin_is_caught(self):
        self.assertEqual(simulate.closure_problems(self.ROWS[1:])["failing"], 1)

    def test_class_ranges_cover_a_quarter_decade(self):
        kind, low, high = simulate.class_x(200 + 40)
        self.assertEqual((kind, low), ("nonionizing", 1.0))
        self.assertAlmostEqual(high, 10 ** 0.25)

    def test_reweighting_keeps_zero_length_steps_and_bounds_itself(self):
        rows = [(40, 10.0), (600, 1.0)]
        exact = 10.0 / (1 + 0.1 * 1.3) + 1.0
        self.assertLessEqual(abs(simulate.reweighted(rows, 0.1) - exact), simulate.reweighting_bound(rows, 0.1))


class Segmentation(unittest.TestCase):
    def test_counts(self):
        half = ["5", "5", "10"]
        self.assertEqual(segmentation.bin_count(None, half), 1)
        self.assertEqual(segmentation.bin_count({"along_axis": {"axis": "z", "width_mm": "1"}}, half), 20)
        self.assertEqual(segmentation.bin_count({"cartesian_xy": {"width_mm": ["2", "5"]}}, half), 10)
        self.assertEqual(segmentation.bin_count({"polar": {"width_r_mm": "1", "phi_bins": 8}}, half), 64)  # rings reach the corner, 7.07 mm
        self.assertEqual(segmentation.bin_count({"polar": {"width_r_mm": "1", "phi_bins": 1}}, ["10", "200", "20"]), 201)  # wider in y than in x

    def test_wrong_forms_are_refused(self):
        half = ["500", "500", "500"]
        for block in ({"cartesian_xy": {"width_mm": ["1"]}}, {"along_axis": {"axis": "z", "width_mm": "0"}}, {"hexagonal": {}}, {"cartesian_xyz": {"width_mm": ["1", "1", "1"]}}):
            with self.assertRaises(GeometryError, msg=str(block)):
                segmentation.bin_count(block, half)


if __name__ == "__main__":
    unittest.main()

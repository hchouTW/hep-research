"""Alignment overlay layers (g4sim S9, Section 17): an applied overlay yields a new geometry_id; the diff lists the moved placements; the
Section 15.1 negative test of S9 for overlays: an overlay referencing a non-existent placement."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import geometry  # noqa: E402
from core.geometry import alignment, expand  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402

SPEC = {"schema": "detector-spec/1", "params": {},
        "templates": {"stack": {"solid": {"box": {"size_mm": ["200", "200", "210"]}}, "material": "G4_AIR",
                                "children": [{"template": "cell", "placement": {"linear": {"count": 7, "pitch_mm": ["0", "0", "30"], "start_mm": ["0", "0", "-90"]}}}]},
                      "cell": {"solid": {"box": {"size_mm": ["150", "150", "20"]}}, "material": "G4_PLASTIC_SC_VINYLTOLUENE", "tags": ["cell"]}},
        "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "stack", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]}}
TEXT = json.dumps(SPEC).encode()


def overlay(*shifts) -> dict:
    return {"schema": alignment.SCHEMA, "shifts": [{"mother": "stack", "template": "cell", "copy_number": copy_number, "delta_mm": delta, **extra}
                                                   for copy_number, delta, extra in shifts]}


class Overlay(unittest.TestCase):
    def test_an_applied_overlay_has_a_new_geometry_id(self):  # S9 gate 1
        nominal = geometry.check_spec(TEXT)
        moved = geometry.check_spec(TEXT, overlay=overlay((2, ["0.05", "-0.02", "0"], {})))
        zero = geometry.check_spec(TEXT, overlay=overlay((3, ["0", "0", "0"], {})))
        self.assertEqual({nominal["status"], moved["status"], zero["status"]}, {"ok"})
        self.assertEqual(len({nominal["geometry_id"], moved["geometry_id"], zero["geometry_id"]}), 3)
        self.assertEqual(moved["ir"]["physical"]["alignment"]["placements"], [["stack", "cell", 2]])

    def test_the_diff_lists_exactly_the_moved_placements(self):  # S9 gate 2
        nominal = geometry.check_spec(TEXT)["ir"]
        moved = geometry.check_spec(TEXT, overlay=overlay((2, ["0.05", "0", "0"], {}), (5, ["0", "0", "0"], {"rotation": {"zyx_deg": ["0.01", "0", "0"]}})))["ir"]
        found = alignment.diff(nominal, moved)
        self.assertEqual(found["moved"], [["stack", "cell", 2], ["stack", "cell", 5]])
        self.assertEqual((found["only_first"], found["only_second"]), ([], []))
        self.assertEqual(found["overlaid"]["second"], [["stack", "cell", 2], ["stack", "cell", 5]])
        self.assertEqual(alignment.diff(nominal, nominal)["moved"], [])

    def test_shift_and_rotation_arithmetic(self):
        ir = expand.expand(copy.deepcopy(SPEC))
        moved = alignment.apply(ir, overlay((0, ["0.001", "0", "-0.5"], {"rotation": {"zyx_deg": ["90", "0", "0"]}})))
        placement = next(item for item in moved["physical"]["placements"] if item["template"] == "cell" and item["copy_number"] == 0)
        self.assertEqual(placement["centre_mm"], ["1e-3", "0", "-9.05e1"])
        self.assertEqual(placement["rotation"], [[0, 1, 0], [-1, 0, 0], [0, 0, 1]])  # passive form of Rz(90)

    def test_an_overlay_referencing_a_non_existent_placement_is_refused(self):  # Section 15.1, S9
        result = geometry.check_spec(TEXT, overlay=overlay((9, ["0", "0", "0"], {})))
        self.assertEqual([item["code"] for item in result["findings"]], ["overlay-placement"])
        with self.assertRaises(GeometryError):
            alignment.apply(expand.expand(copy.deepcopy(SPEC)), {"schema": alignment.SCHEMA, "shifts": [{"mother": "world", "template": "cell", "copy_number": 0, "delta_mm": ["0", "0", "0"]}]})

    def test_an_overlay_that_creates_an_overlap_is_judged_by_the_gap_rule(self):
        self.assertIn("sibling-overlap", [item["code"] for item in geometry.check_spec(TEXT, overlay=overlay((2, ["0", "0", "15"], {})))["findings"]])

    def test_malformed_overlays(self):
        self.assertEqual(geometry.check_spec(TEXT, overlay={"schema": "x", "shifts": []})["findings"][0]["code"], "overlay-schema")
        twice = overlay((2, ["0", "0", "0"], {}), (2, ["0", "0", "1"], {}))
        self.assertEqual(geometry.check_spec(TEXT, overlay=twice)["findings"][0]["code"], "overlay-twice")
        with self.assertRaises(GeometryError):
            ir = alignment.apply(expand.expand(copy.deepcopy(SPEC)), overlay((2, ["0", "0", "0"], {})))
            alignment.apply(ir, overlay((3, ["0", "0", "0"], {})))

    def test_an_ir_with_no_overlay_keeps_its_geometry_id(self):
        self.assertNotIn("alignment", geometry.check_spec(TEXT)["ir"]["physical"])


if __name__ == "__main__":
    unittest.main()

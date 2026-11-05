"""The translator (g4sim S1, Section 18): every recorded old specification round-trips byte for byte, the split parts carry the
values, and a change of one ulp is caught."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location("g4sim_translate", ROOT / "adapters/geant4/assets/g4sim_translate.py")
translate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(translate)

from contracts import geometry  # noqa: E402
from contracts.schema import validate  # noqa: E402

RUN_SCHEMA = str(ROOT / "adapters/geant4/assets/g4sim_run.schema.json")
FOLDERS = ("examples/geant4-thin-silicon/recorded/specs", "examples/design-minimal-spectrometer/recorded/artifacts/specs",
           "examples/design-search-j16/recorded")


def recorded():
    for folder in FOLDERS:
        for path in sorted((ROOT / folder).rglob("*.json")):
            text = path.read_text(encoding="utf-8")
            if '.spec/1"' in text and json.loads(text).get("schema") in (translate.LAYERED, translate.ELEMENT):
                yield path, text


def element_spec():
    return json.loads(next(text for path, text in recorded() if path.name == "N4-TRK1-nominal.spec.json"))


class RoundTrip(unittest.TestCase):
    def test_every_recorded_specification_round_trips_byte_for_byte(self):
        files = list(recorded())
        self.assertEqual(len(files), 112)
        for path, text in files:
            with self.subTest(file=path.name):
                self.assertEqual(translate.as_file(translate.merge(*translate.split(json.loads(text)))), text)

    def test_every_part_is_valid(self):
        for path, text in recorded():
            detector, request, card = translate.split(json.loads(text))
            with self.subTest(file=path.name):
                result = geometry.check_spec(json.dumps(detector))
                self.assertEqual(result["status"], "ok", result["findings"][:2])
                self.assertFalse([f for f in validate(request, "simulation_request.json").findings if f.severity == "error"])
                self.assertFalse([f for f in validate(card, RUN_SCHEMA).findings if f.severity == "error"])

    def test_merge_rebuilds_from_the_parts_and_holds_no_copy_of_the_file(self):
        old = element_spec()
        detector, request, card = translate.split(old)
        moved = copy.deepcopy(detector)
        moved["world"]["size_mm"][0] = "5e3"
        self.assertEqual(translate.merge(moved, request, card)["world"]["half_mm"][0], 2500.0)

    def test_one_ulp_in_a_position_is_caught(self):
        old = element_spec()
        centre = old["elements"][1]["centre_mm"]
        changed = copy.deepcopy(old)
        changed["elements"][1]["centre_mm"][0] = math.nextafter(centre[0], math.inf)
        self.assertNotEqual(translate.split(changed)[0], translate.split(old)[0])
        self.assertNotEqual(translate.as_file(translate.merge(*translate.split(changed))), translate.as_file(translate.merge(*translate.split(old))))

    def test_an_unknown_field_is_refused_never_dropped(self):
        old = element_spec()
        for target in (old, old["physics"], old["elements"][0], old["source"]):
            changed = copy.deepcopy(target)
            target["unknown_key"] = 1
            with self.assertRaises(translate.TranslationError):
                translate.split(old)
            del target["unknown_key"]
            self.assertEqual(changed, target)

    def test_the_layout_note_holds_key_names_only(self):
        layout = translate.key_layout({"b": 1.5, "a": [{"d": "secret", "c": 2}]})
        self.assertNotIn("secret", json.dumps(layout))
        self.assertNotIn("1.5", json.dumps(layout))
        self.assertIsNone(translate.key_layout({"a": 1, "b": {"c": [1, {"d": 2}]}}))


class Meaning(unittest.TestCase):
    def test_the_three_parts_hold_what_section_18_says(self):
        detector, request, card = translate.split(element_spec())
        self.assertEqual(detector["schema"], "detector-spec/1")
        self.assertEqual(request["source"]["particle"], "proton")
        self.assertEqual((card["accounting"], card["run"]["seeding"], card["run"]["mode"]), ("legacy", "per-event", "mt"))

    def test_a_layered_run_keeps_stream_seeding(self):
        text = next(text for path, text in recorded() if path.name == "mpv-control.json")
        self.assertEqual(translate.split(json.loads(text))[2]["run"]["seeding"], "stream")

    def test_the_field_reaches_the_ir_and_its_daughters(self):
        result = geometry.check_spec(json.dumps(translate.split(element_spec())[0]))
        templates = result["ir"]["physical"]["templates"]
        self.assertEqual(templates["FieldRegion"]["field"], "field_0")
        self.assertEqual(templates["Si1"]["field"], "field_0")
        self.assertEqual(templates["Calo"]["field"], "none")

    def test_the_legacy_block_changes_no_identity(self):
        detector = translate.split(element_spec())[0]
        other = copy.deepcopy(detector)
        other["legacy"]["note"] = "another note"
        ids = [geometry.check_spec(json.dumps(part))["geometry_id"] for part in (detector, other)]
        self.assertEqual(ids[0], ids[1])

    def test_a_changed_field_value_changes_geometry_id(self):
        detector = translate.split(element_spec())[0]
        other = copy.deepcopy(detector)
        other["fields"]["field_0"]["b_tesla"][2] = "6e-1"
        ids = [geometry.check_spec(json.dumps(part))["geometry_id"] for part in (detector, other)]
        self.assertNotEqual(ids[0], ids[1])


if __name__ == "__main__":
    unittest.main()

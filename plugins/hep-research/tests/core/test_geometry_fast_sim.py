"""Fast-simulation envelopes (g4sim S8, Section 6.2.9) and the logical-level name check, with the Section 15.1 negatives that belong to the
specification: a daughter volume inside the envelope; two logicals sharing a name (a shell's wrapper named like a template). The run card's
placement_impl and fast_sim rules are in tests/adapters/test_g4sim_run.py."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import expand  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402


def calorimeter(**requirement) -> dict:
    return {"schema": "detector-spec/1", "params": {},
            "templates": {"calo": {"solid": {"box": {"size_mm": ["300", "300", "250"]}}, "material": "G4_PbWO4", "region": "calo", "tags": ["calo"]},
                          "plate": {"solid": {"box": {"size_mm": ["300", "300", "10"]}}, "material": "G4_Al"}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [
                {"template": "plate", "placement": {"single": {"centre_mm": ["0", "0", "-200"]}}},
                {"template": "calo", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
            "physics_requirements": [{"need": "fast_sim_envelope", "select": {"tags": ["calo"]}, **requirement}]}


def code_of(spec: dict) -> str:
    with unittest.TestCase().assertRaises(GeometryError) as caught:
        expand.expand(spec)
    return caught.exception.code


class Envelope(unittest.TestCase):
    def test_an_envelope_alone_in_its_region_passes(self):
        ir = expand.expand(calorimeter())
        self.assertEqual(ir["physical"]["physics_requirements"], [{"need": "fast_sim_envelope", "templates": ["calo"]}])
        self.assertEqual(ir["physical"]["templates"]["calo"]["region"], "calo")

    def test_a_daughter_inside_the_envelope_is_refused(self):  # Section 15.1, S8
        spec = calorimeter()
        spec["templates"]["cell"] = {"solid": {"box": {"size_mm": ["10", "10", "10"]}}, "material": "G4_PbWO4"}
        spec["templates"]["calo"]["children"] = [{"template": "cell", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]
        self.assertEqual(code_of(spec), "envelope-daughter")

    def test_an_envelope_needs_a_region_of_its_own(self):
        spec = calorimeter()
        del spec["templates"]["calo"]["region"]
        self.assertEqual(code_of(spec), "envelope-region")
        spec = calorimeter()
        spec["templates"]["plate"]["region"] = "calo"
        self.assertEqual(code_of(spec), "envelope-region")

    def test_the_model_belongs_to_the_run_card(self):
        self.assertEqual(code_of(calorimeter(model="absorb")), "envelope-model-in-spec")
        self.assertEqual(code_of(calorimeter(particles=["e-"])), "envelope-model-in-spec")

    def test_an_envelope_of_two_requirements_is_refused(self):
        spec = calorimeter()
        spec["physics_requirements"].append(copy.deepcopy(spec["physics_requirements"][0]))
        self.assertEqual(code_of(spec), "envelope-twice")


class LogicalNames(unittest.TestCase):
    def test_a_shell_wrapper_named_like_a_template_is_refused(self):  # Section 15.1, S8: two logicals sharing a name
        spec = calorimeter()
        del spec["physics_requirements"]
        spec["templates"]["plate"]["modifiers"] = [{"shell": {"material": "G4_AIR", "thickness_mm": "1", "faces": ["front"]}}]
        expand.expand(spec)  # the wrapper's name is free: it passes
        spec["templates"]["plate_shell"] = {"solid": {"box": {"size_mm": ["5", "5", "5"]}}, "material": "G4_AIR"}
        self.assertEqual(code_of(spec), "template-name")


if __name__ == "__main__":
    unittest.main()

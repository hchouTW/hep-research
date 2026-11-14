"""Optics in the specification (g4sim S7, Sections 6.2.7, 6.2.9): property tables, gap volumes, optical_scope and optical surfaces, with the
Section 15.1 negative tests (a material with optical properties outside the scope; a spacer within the scope with no material)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import expand, identity  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402

E2 = ["1.5", "4.0"]
def optical_spec():
    return {"schema": "detector-spec/1", "params": {},
     "materials": {"glass_optical": {"base": "G4_GLASS_PLATE", "optical": {"rindex": {"energy_eV": E2, "value": ["1.5", "1.52"]},
                                                                       "absorption_length_mm": {"energy_eV": E2, "value": ["1000", "1000"]}}},
                   "AIR_optical": {"base": "G4_AIR", "optical": {"rindex": {"energy_eV": E2, "value": ["1.0003", "1.0003"]}}}},
     "templates": {"radiator": {"solid": {"box": {"size_mm": ["100", "100", "10"]}}, "material": "glass_optical", "tags": ["optical"]},
                   "sensor": {"solid": {"box": {"size_mm": ["100", "100", "1"]}}, "material": "G4_Si", "tags": ["optical"]},
                   "box": {"solid": {"box": {"size_mm": ["100", "100", "31"]}}, "material": "AIR_optical", "tags": ["optical"], "children": [
                       {"placement": {"stack": {"axis": "z", "from": "-z", "sequence": ["radiator", {"spacer_mm": "10", "material": "AIR_optical"}, "sensor", {"spacer_mm": "10"}]}}}]}},
     "world": {"material": "G4_AIR", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "box", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
     "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}],
     "optical_surfaces": {"photocathode": {"skin": "sensor", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                                           "reflectivity": {"energy_eV": E2, "value": ["0", "0"]}, "efficiency": {"energy_eV": E2, "value": ["0.25", "0.25"]}}}}


def refusal(spec: dict) -> str:
    """The code of the GeometryError the expansion raises."""
    try:
        expand.expand(spec)
    except GeometryError as err:
        return err.code
    raise AssertionError("the specification was accepted")


class Scope(unittest.TestCase):
    def test_a_legal_optical_detector_expands(self):
        ir = expand.expand(optical_spec())
        scope = next(item for item in ir["physical"]["physics_requirements"] if item["need"] == "optical_scope")
        self.assertEqual(scope["templates"], ["box", "box_gap1", "radiator", "sensor"])
        self.assertEqual(ir["physical"]["materials"]["glass_optical"]["optical"]["rindex"]["value"], ["1.5", "1.52"])

    def test_a_material_with_optical_properties_outside_the_scope_is_refused(self):
        spec = optical_spec()
        spec["templates"]["radiator"]["tags"] = []
        with self.assertRaises(GeometryError) as caught:
            expand.expand(spec)
        self.assertEqual(caught.exception.code, "optical-outside-scope")
        self.assertIn("AIR_optical", str(caught.exception))  # the message names both ways to write it
        self.assertIn("spacer_mm", str(caught.exception))

    def test_optical_tables_with_no_scope_at_all_are_refused(self):
        spec = optical_spec()
        del spec["physics_requirements"]
        self.assertEqual(refusal(spec), "optical-outside-scope")

    def test_a_spacer_within_the_scope_with_no_material_is_refused(self):
        spec = optical_spec()
        spec["templates"]["box"]["material"] = "G4_AIR"  # the bare spacer would be air with no refractive index
        self.assertEqual(refusal(spec), "optical-spacer")

    def test_a_spacer_in_an_optical_mother_is_its_mothers_material(self):
        ir = expand.expand(optical_spec())  # the last spacer of the stack is bare, in AIR_optical
        self.assertEqual(sum(1 for name in ir["physical"]["templates"] if "_gap" in name), 1)


class GapVolumes(unittest.TestCase):
    def test_a_gap_volume_is_the_mothers_cross_section_of_its_material(self):
        ir = expand.expand(optical_spec())
        gap = ir["physical"]["templates"]["box_gap1"]
        self.assertEqual((gap["half_mm"], gap["material"]), (["5e1", "5e1", "5e0"], "AIR_optical"))
        self.assertEqual([item["template"] for item in ir["physical"]["placements"] if item["mother"] == "box"], ["radiator", "box_gap1", "sensor"])

    def test_a_gap_volume_takes_its_place_in_the_stack(self):
        placements = {item["template"]: item for item in expand.expand(optical_spec())["physical"]["placements"]}
        self.assertEqual(placements["box_gap1"]["centre_mm"][2], "-5e-1")  # -15.5 + 10 (radiator) + 5 (half the gap)

    def test_a_gap_volume_name_already_taken_is_refused(self):
        spec = optical_spec()
        spec["templates"]["box_gap1"] = {"solid": {"box": {"size_mm": ["1", "1", "1"]}}, "material": "G4_Si"}
        self.assertEqual(refusal(spec), "template-name")


class Tables(unittest.TestCase):
    def test_out_of_range_tables_are_refused(self):
        cases = [("rindex", {"energy_eV": E2, "value": ["0.9", "1.5"]}), ("rindex", {"energy_eV": ["4.0", "1.5"], "value": ["1.5", "1.5"]}),
                 ("rindex", {"energy_eV": E2, "value": ["1.5"]}), ("absorption_length_mm", {"energy_eV": E2, "value": ["-1", "1"]})]
        for key, table in cases:
            spec = optical_spec()
            spec["materials"]["glass_optical"]["optical"][key] = table
            with self.subTest(key=key, table=table):
                self.assertEqual(refusal(spec), "optical-table")

    def test_scintillation_components_add_to_one_and_need_a_refractive_index(self):
        spec = optical_spec()
        component = {"fraction": "0.6", "spectrum": {"energy_eV": E2, "value": ["1", "1"]}, "rise_ns": "0", "decay_ns": "2.1"}
        spec["materials"]["glass_optical"]["scintillation"] = {"yield_per_MeV": "10000", "resolution_scale": "1", "components": [component, {**component, "fraction": "0.4"}]}
        self.assertEqual(expand.expand(spec)["physical"]["materials"]["glass_optical"]["scintillation"]["components"][1]["fraction"], "0.4")
        spec["materials"]["glass_optical"]["scintillation"]["components"][1]["fraction"] = "0.5"
        self.assertEqual(refusal(spec), "optical-table")
        spec = optical_spec()
        spec["materials"]["plain"] = {"base": "G4_PLASTIC_SC_VINYLTOLUENE", "scintillation": {"yield_per_MeV": "10000", "resolution_scale": "1", "components": [{**component, "fraction": "1"}]}}
        spec["templates"]["sensor"]["material"] = "plain"
        self.assertEqual(refusal(spec), "optical-table")

    def test_optical_tables_change_geometry_id_and_their_sources_do_not(self):
        first = identity.geometry_id(expand.expand(optical_spec()))
        sourced = optical_spec()
        sourced["materials"]["glass_optical"]["optical"]["facts"] = "claim:glass-index"
        self.assertEqual(identity.geometry_id(expand.expand(sourced)), first)
        changed = optical_spec()
        changed["materials"]["glass_optical"]["optical"]["rindex"]["value"] = ["1.5", "1.53"]
        self.assertNotEqual(identity.geometry_id(expand.expand(changed)), first)


class Surfaces(unittest.TestCase):
    def test_a_skin_enters_the_ir(self):
        surface = expand.expand(optical_spec())["physical"]["optical_surfaces"]["photocathode"]
        self.assertEqual((surface["skin"], surface["model"], surface["efficiency"]["value"]), ("sensor", "unified", ["0.25", "0.25"]))

    def test_an_efficiency_above_one_is_refused(self):
        spec = optical_spec()
        spec["optical_surfaces"]["photocathode"]["efficiency"]["value"] = ["1.2", "0.2"]
        self.assertEqual(refusal(spec), "optical-table")

    def test_a_surface_outside_the_scope_is_refused(self):
        spec = optical_spec()
        spec["templates"]["sensor"]["tags"] = []
        self.assertEqual(refusal(spec), "optical-surface-scope")

    def test_a_border_between_siblings_passes_and_one_between_strangers_is_refused(self):
        spec = optical_spec()
        spec["optical_surfaces"]["window"] = {"border": ["radiator", "box_gap1"], "model": "glisur", "finish": "ground", "type": "dielectric_dielectric"}
        self.assertEqual(expand.expand(spec)["physical"]["optical_surfaces"]["window"]["border"], ["radiator", "box_gap1"])
        spec["templates"]["far"] = {"solid": {"box": {"size_mm": ["1", "1", "1"]}}, "material": "G4_Si", "tags": ["optical"]}
        spec["world"]["children"].append({"template": "far", "placement": {"single": {"centre_mm": ["300", "0", "0"]}}})
        spec["optical_surfaces"]["window"]["border"] = ["radiator", "far"]
        self.assertEqual(refusal(spec), "optical-surface-border")

    def test_a_specification_with_no_optics_keeps_its_geometry_id(self):
        plain = optical_spec()
        for key in ("materials", "optical_surfaces", "physics_requirements"):
            del plain[key]
        plain["templates"]["radiator"]["material"] = plain["templates"]["box"]["material"] = "G4_AIR"
        plain["templates"]["box"]["children"][0]["placement"]["stack"]["sequence"] = ["radiator", {"spacer_mm": "10"}, "sensor", {"spacer_mm": "10"}]
        self.assertNotIn("optical_surfaces", expand.expand(plain)["physical"])


if __name__ == "__main__":
    unittest.main()

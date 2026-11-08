"""The XTR consistency rules (g4sim S7, Section 6.2.9) on the specification, with the Section 15.1 negatives that belong to the IR layer: a foil
placed inside the envelope; a wrong envelope thickness; a model kind written in the detector-spec. The run card's rules 4 and 5 are in
tests/adapters/test_g4sim_run.py."""
from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import expand, xtr  # noqa: E402
from core.geometry.numbers import CONTEXT, GeometryError, as_text  # noqa: E402

MATERIALS = {"mylar": {"base": "G4_MYLAR", "density_g_cm3": "1.39"}, "air": {"base": "G4_AIR", "density_g_cm3": "0.00120479"}}


def radiator(thickness="21.5", **requirement):
    mix = xtr.mixture(MATERIALS, "mylar", "air", 100, Decimal("0.015"), Decimal(thickness), "")
    materials = {**MATERIALS, "radiator_mix": {"density_g_cm3": as_text(mix["density_g_cm3"]), "components": [
        {"material": name, "mass_fraction": as_text(value)} for name, value in mix["fractions"].items()]}}
    need = {"need": "transition_radiation", "select": {"tags": ["radiator"]}, "structure": "regular", "foil_material": "mylar", "gas_material": "air",
            "foil_thickness_um": "15", "gap_um": "200", "foils": 100, "axis": "z", **requirement}
    return {"schema": "detector-spec/1", "params": {}, "materials": materials,
            "templates": {"radiator": {"solid": {"box": {"size_mm": ["100", "100", thickness]}}, "material": "radiator_mix", "tags": ["radiator"]}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "radiator", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
            "physics_requirements": [need]}


def refusal(spec: dict) -> str:
    try:
        expand.expand(spec)
    except GeometryError as err:
        return err.code
    raise AssertionError("the specification was accepted")


class Rules(unittest.TestCase):
    def test_a_consistent_radiator_passes(self):
        requirement = expand.expand(radiator())["physical"]["physics_requirements"][0]
        self.assertEqual((requirement["templates"], requirement["structure"], requirement["foils"]), (["radiator"], "regular", 100))

    def test_the_mixture_is_by_volume(self):
        mix = xtr.mixture(MATERIALS, "mylar", "air", 100, Decimal("0.015"), Decimal("21.5"), "")
        foil, gas = Decimal("1.5"), Decimal("20")
        expected = CONTEXT.divide(CONTEXT.add(CONTEXT.multiply(foil, Decimal("1.39")), CONTEXT.multiply(gas, Decimal("0.00120479"))), Decimal("21.5"))
        self.assertEqual(mix["density_g_cm3"], expected)  # in core's own 34-digit context
        self.assertEqual(sum(mix["fractions"].values()), 1)

    def test_a_foil_placed_inside_the_envelope_is_refused(self):
        spec = radiator()
        spec["templates"]["foil"] = {"solid": {"box": {"size_mm": ["100", "100", "0.015"]}}, "material": "mylar"}
        spec["templates"]["radiator"]["children"] = [{"template": "foil", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]
        self.assertEqual(refusal(spec), "xtr-daughter")

    def test_a_wrong_envelope_thickness_is_refused(self):
        self.assertEqual(expand.expand(radiator("21.3"))["physical"]["templates"]["radiator"]["half_mm"][2], "1.065e1")  # n(t + g) - g is legal
        self.assertEqual(refusal(radiator("21.6")), "xtr-thickness")
        self.assertEqual(refusal(radiator("21.2")), "xtr-thickness")

    def test_an_envelope_that_is_not_the_mixture_is_refused(self):
        spec = radiator()
        spec["materials"]["radiator_mix"]["density_g_cm3"] = "0.1"
        self.assertEqual(refusal(spec), "xtr-mixture")
        spec = radiator()
        spec["templates"]["radiator"]["material"] = "G4_AIR"
        self.assertEqual(refusal(spec), "xtr-mixture")

    def test_a_model_kind_in_the_specification_is_refused(self):
        self.assertEqual(refusal(radiator(model_kind="transparent")), "xtr-model-in-spec")
        self.assertEqual(refusal(radiator(radiator_class="G4RegularXTRadiator")), "xtr-model-in-spec")

    def test_an_irregular_stack_needs_its_gamma_parameters(self):
        self.assertEqual(refusal(radiator(structure="irregular")), "xtr-parameters")
        self.assertEqual(expand.expand(radiator(structure="irregular", alpha_foil="100", alpha_gas="20"))["physical"]["physics_requirements"][0]["alpha_gas"], "20")

    def test_a_foil_with_no_declared_density_is_refused(self):
        spec = radiator()
        spec["materials"]["mylar"] = {"base": "G4_MYLAR"}
        self.assertEqual(refusal(spec), "xtr-density")


if __name__ == "__main__":
    unittest.main()

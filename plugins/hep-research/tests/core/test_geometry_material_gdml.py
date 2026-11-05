"""Material budget and GDML export (g4sim S1). Path lengths are worked out by hand from the stack; the Section 15.1 negative
test swaps one layer's material."""
from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ElementTree
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import expand, gdml, material, rotation  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402


def box(size, name):
    return {"solid": {"box": {"size_mm": size}}, "material": name}


def sandwich(first="G4_Pb", second="G4_Si"):
    """World of air; a 20 x 20 x 10 mother of air at z = 0 with 2 mm and 3 mm layers and a 1 mm spacer from its -z face."""
    return {"schema": "detector-spec/1", "templates": {
        "lead": box(["20", "20", "2"], first), "silicon": box(["20", "20", "3"], second),
        "module": {**box(["20", "20", "10"], "G4_AIR"), "children": [
            {"placement": {"stack": {"axis": "z", "from": "-z", "sequence": ["lead", {"spacer_mm": "1"}, "silicon"]}}}]}},
        "world": {"material": "G4_Galactic", "size_mm": ["100", "100", "100"], "children": [
            {"template": "module", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]}}


ORIGIN, AXIS = (D(0), D(0), D(-50)), (D(0), D(0), D(1))


class Budget(unittest.TestCase):
    def test_path_lengths_by_hand(self):
        lengths = material.path_by_material(expand.expand(sandwich()), ORIGIN, AXIS)
        self.assertEqual(lengths, {"G4_Galactic": D(90), "G4_Pb": D(2), "G4_AIR": D(5), "G4_Si": D(3)})

    def test_the_order_of_the_segments_follows_the_ray(self):
        order = [s["template"] for s in material.ray_segments(expand.expand(sandwich()), ORIGIN, AXIS)]
        self.assertEqual(order, ["world", "lead", "module", "silicon", "module", "world"])  # the stack starts on the mother's face

    def test_a_ray_that_misses_sees_only_the_world(self):
        lengths = material.path_by_material(expand.expand(sandwich()), (D(30), D(0), D(-50)), AXIS)
        self.assertEqual(lengths, {"G4_Galactic": D(100)})

    def test_a_slanted_ray_is_longer_by_the_cosine(self):
        lengths = material.path_by_material(expand.expand(sandwich()), (D(0), D(0), D(-6)), (D(3), D(0), D(4)))
        self.assertEqual(lengths["G4_Pb"], D("2.5"))

    def test_one_layer_s_material_swapped_changes_the_budget(self):
        lengths = {"G4_Pb": D("5.612"), "G4_Si": D("93.7"), "G4_AIR": D("303900"), "G4_Galactic": D("1e30")}
        right = material.budget(expand.expand(sandwich()), ORIGIN, AXIS, lengths)
        wrong = material.budget(expand.expand(sandwich("G4_Si", "G4_Pb")), ORIGIN, AXIS, lengths)
        self.assertNotEqual(right, wrong)

    def test_a_material_with_no_radiation_length_is_refused(self):
        with self.assertRaises(GeometryError) as caught:
            material.budget(expand.expand(sandwich()), ORIGIN, AXIS, {})
        self.assertEqual(caught.exception.code, "material-unknown")

    def test_a_ray_along_a_shared_face_counts_one_volume(self):
        document = sandwich()
        document["templates"]["module"]["children"] = [{"template": "lead", "placement": {"linear": {
            "count": 2, "pitch_mm": ["0", "0", "2"], "start_mm": ["0", "0", "-1"]}}}]
        lengths = material.path_by_material(expand.expand(document), (D(-50), D(0), D(0)), (D(1), D(0), D(0)))
        self.assertEqual(lengths["G4_Pb"], D(20))

    def test_a_turned_placement_is_followed_through_its_frame(self):
        document = sandwich()
        document["world"]["children"][0]["placement"]["single"]["rotation"] = {"axis": "y", "angle_deg": "90"}
        lengths = material.path_by_material(expand.expand(document), (D(-50), D(0), D(0)), (D(1), D(0), D(0)))
        self.assertEqual((lengths["G4_Pb"], lengths["G4_Si"]), (D(2), D(3)))


class ExportedFile(unittest.TestCase):
    def test_every_quarter_turn_has_euler_angles(self):
        turns = (0, 90, 180, 270)
        seen = set()
        for z in turns:
            for y in turns:
                for x in turns:
                    matrix = rotation.active_matrix({"zyx_deg": [D(z), D(y), D(x)]})
                    passive = rotation.passive_matrix(matrix)
                    seen.add(passive)
                    self.assertIsNotNone(gdml.euler_angles(passive))
        self.assertEqual(len(seen), 24)

    def test_the_document_is_well_formed_with_daughters_first(self):
        root = ElementTree.fromstring(gdml.export(expand.expand(sandwich())))
        names = [volume.get("name") for volume in root.find("structure")]
        self.assertLess(names.index("lead"), names.index("module"))
        self.assertEqual(names[-1], "world")
        self.assertEqual(root.find("setup/world").get("ref"), "world")

    def test_a_custom_material_is_defined_and_a_based_one_uses_its_base(self):
        document = sandwich("glue", "tuned")
        document["materials"] = {"glue": {"density_g_cm3": "1.2", "composition": {"C": "0.6", "H": "0.4"}},
                                 "tuned": {"base": "G4_Si"}}
        root = ElementTree.fromstring(gdml.export(expand.expand(document)))
        self.assertEqual([m.get("name") for m in root.find("materials")], ["glue"])
        refs = {v.get("name"): v.find("materialref").get("ref") for v in root.find("structure")}
        self.assertEqual(refs["silicon"], "G4_Si")


class UnknownMaterial(unittest.TestCase):
    def test_a_material_that_is_neither_nist_nor_declared_is_refused(self):
        with self.assertRaises(GeometryError) as caught:
            expand.expand(sandwich("unobtainium"))
        self.assertEqual(caught.exception.code, "material-unknown")


if __name__ == "__main__":
    unittest.main()

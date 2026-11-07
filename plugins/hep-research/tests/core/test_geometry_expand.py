"""Expansion and the gap rule (g4sim S1): the IR negative tests of Section 15.1, and the two Part B decisions of
g4sim-approvals.md on copy numbers and volume IDs."""
from __future__ import annotations

import copy
import itertools
from decimal import Decimal
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import expand, gdml, identity, material, overlap, rotation  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402


def box(size, material="G4_Si", **extra):
    return {"solid": {"box": {"size_mm": size}}, "material": material, **extra}


def single(template, centre=("0", "0", "0"), rotation=None):
    body = {"centre_mm": list(centre)}
    if rotation:
        body["rotation"] = rotation
    return {"template": template, "placement": {"single": body}}


def spec(templates=None, children=None, **extra):
    return {"schema": "detector-spec/1", "params": {}, "templates": templates or {}, "world": {
        "material": "G4_AIR", "size_mm": ["1000", "1000", "1000"], "children": children or []}, **extra}


def calorimeter():
    return {"schema": "detector-spec/1", "params": {"t": "2", "gap": "0.5", "n": "4"},
            "templates": {"absorber": box(["50", "50", "t"], "G4_Pb", tags=["passive"]),
                          "active": box(["50", "50", "1"], "G4_PLASTIC_SC_VINYLTOLUENE", tags=["active"]),
                          "module": {**box(["50", "50", "n * (t + 1 + gap)"], "G4_AIR", region="calorimeter"), "children": [
                              {"placement": {"stack": {"axis": "z", "from": "-z", "repeat": 4, "sequence": [
                                  "absorber", {"template": "active", "index": "layer"}, {"spacer_mm": "gap"}]}}}]}},
            "world": {"material": "G4_AIR", "size_mm": ["1000", "1000", "1000"], "children": [
                {"template": "module", "placement": {"linear": {"count": 3, "pitch_mm": ["60", "0", "0"],
                                                                "start_mm": ["-60", "0", "0"], "index": "m"}}}]},
            "frames": {"beam": {"in": "world", "origin_mm": ["0", "0", "-100"]}},
            "readout": {"cal": {"fields": {"m": 2, "layer": 2, "z": 6}}},
            "physics_requirements": [{"need": "birks", "select": {"tags": ["active"]}}]}


def volume_ids(ir):
    """Every touchable's volume ID, walking the tree: (copy number + 1) x stride at each level."""
    daughters = {}
    for placement in ir["physical"]["placements"]:
        daughters.setdefault(placement["mother"], []).append(placement)
    strides = ir["physical"]["volume_id"]["strides"]
    found = [0]

    def walk(name, depth, value):
        for placement in daughters.get(name, []):
            mine = value + (placement["copy_number"] + 1) * strides[depth]
            found.append(mine)
            walk(placement["template"], depth + 1, mine)

    walk("world", 0, 0)
    return found


def codes(ir):
    return [finding["code"] for finding in overlap.findings(ir)]


class Expansion(unittest.TestCase):
    def setUp(self):
        self.document = expand.expand(calorimeter())

    def test_a_legal_detector_has_no_findings(self):
        self.assertEqual(overlap.findings(self.document), [])

    def test_a_stack_abuts_exactly_and_ends_on_the_mother_face(self):
        centres = [p["centre_mm"][2] for p in self.document["physical"]["placements"] if p["mother"] == "module"]
        self.assertEqual(centres[:2], ["-6e0", "-4.5e0"])

    def test_half_lengths_are_written_for_the_builder(self):
        self.assertEqual(self.document["physical"]["templates"]["absorber"]["half_mm"], ["2.5e1", "2.5e1", "1e0"])

    def test_expansion_is_repeatable(self):
        self.assertEqual(identity.geometry_id(self.document), identity.geometry_id(expand.expand(calorimeter())))

    def test_the_same_template_gives_the_same_solid_at_every_position(self):
        near = spec({"a": box(["1", "2", "3"])}, [single("a", ("-5", "0", "0")), single("a", ("5", "0", "0"))])
        far = spec({"a": box(["1", "2", "3"])}, [single("a", ("-400", "0", "0")), single("a", ("400", "9", "0"))])
        solids = [expand.expand(document)["physical"]["templates"]["a"] for document in (near, far)]
        self.assertEqual(solids[0], solids[1])
        self.assertEqual(sum(p["template"] == "a" for p in expand.expand(far)["physical"]["placements"]), 2)

    def test_a_cycle_of_templates_is_refused(self):
        document = spec({"a": {**box(["1", "1", "1"]), "children": [single("b")]}, "b": {**box(["1", "1", "1"]), "children": [single("a")]}},
                        [single("a")])
        with self.assertRaises(GeometryError) as caught:
            expand.expand(document)
        self.assertEqual(caught.exception.code, "template-cycle")

    def test_a_later_shape_or_placement_is_refused(self):
        cone = spec({"a": {"solid": {"cone": {}}, "material": "G4_Si"}})
        sphere = spec({"a": {"solid": {"sphere_section": {}}, "material": "G4_Si"}})
        for document in (cone, sphere):
            with self.assertRaises(GeometryError) as caught:
                expand.expand(document)
            self.assertEqual(caught.exception.code, "module-not-open")

    def test_thirty_degrees_is_open_for_a_single_placement(self):
        document = spec({"a": box(["1", "1", "1"])}, [single("a", rotation={"axis": "z", "angle_deg": "30"})])
        self.assertTrue(all(isinstance(value, str) for value in expand.expand(document)["physical"]["placements"][0]["rotation"][0][:2]))


class VolumeIds(unittest.TestCase):
    def test_every_touchable_has_its_own_id(self):
        found = volume_ids(expand.expand(calorimeter()))
        self.assertEqual(len(found), 1 + 3 + 3 * 8)
        self.assertEqual(len(set(found)), len(found))

    def test_a_mother_and_its_copy_zero_daughter_differ(self):
        document = spec({"a": {**box(["10", "10", "10"]), "children": [single("b")]}, "b": box(["1", "1", "1"])}, [single("a")])
        found = volume_ids(expand.expand(document))
        self.assertEqual(found, [0, 1, 3])

    def test_ids_are_unique_for_every_shape_of_small_tree(self):
        for counts in itertools.product((1, 2, 3), repeat=2):
            document = spec({"a": {**box(["100", "100", "100"]), "children": [
                {"template": "b", "placement": {"linear": {"count": counts[1], "pitch_mm": ["3", "0", "0"], "start_mm": ["0", "0", "0"]}}}]},
                "b": box(["1", "1", "1"])}, [{"template": "a", "placement": {"linear": {"count": counts[0], "pitch_mm": ["200", "0", "0"],
                                                                                        "start_mm": ["-200", "0", "0"]}}}])
            with self.subTest(counts=counts):
                found = volume_ids(expand.expand(document))
                self.assertEqual(len(set(found)), len(found))


class CopyNumbers(unittest.TestCase):
    def test_indexed_placements_keep_the_index_and_others_follow(self):
        ir = expand.expand(calorimeter())
        placed = [(p["template"], p["copy_number"]) for p in ir["physical"]["placements"] if p["mother"] == "module"]
        self.assertEqual(sorted(c for t, c in placed if t == "active"), [0, 1, 2, 3])
        self.assertEqual(sorted(c for t, c in placed if t == "absorber"), [4, 5, 6, 7])

    def test_two_single_placements_get_distinct_copy_numbers(self):
        ir = expand.expand(spec({"a": box(["1", "1", "1"])}, [single("a", ("-5", "0", "0")), single("a", ("5", "0", "0"))]))
        self.assertEqual([p["copy_number"] for p in ir["physical"]["placements"]], [0, 1])

    def test_two_indexed_placements_that_collide_are_refused(self):
        children = [{"template": "a", "placement": {"linear": {"count": 2, "pitch_mm": ["3", "0", "0"], "start_mm": [x, "0", "0"], "index": i}}}
                    for x, i in (("0", "m"), ("100", "n"))]
        with self.assertRaises(GeometryError) as caught:
            expand.expand(spec({"a": box(["1", "1", "1"])}, children))
        self.assertEqual(caught.exception.code, "copy-collision")


class GapRule(unittest.TestCase):
    def pair(self, second_x, width="10"):
        return spec({"a": box([width, width, width])}, [single("a", ("0", "0", "0")), single("a", (second_x, "0", "0"))])

    def test_touching_faces_are_legal(self):
        self.assertEqual(codes(expand.expand(self.pair("10"))), [])

    def test_a_gap_of_c_is_legal(self):
        self.assertEqual(codes(expand.expand(self.pair("10.000001"))), [])

    def test_faces_1p1e_7_apart_are_an_error(self):
        self.assertEqual(codes(expand.expand(self.pair("10.00000011"))), ["sibling-too-close"])

    def test_overlapping_siblings_are_an_error(self):
        self.assertEqual(codes(expand.expand(self.pair("9"))), ["sibling-overlap"])

    def test_a_third_three_times_coincides_within_epsilon(self):
        document = spec({"a": box(["1/3", "10", "10"]), "m": {**box(["1", "10", "10"]), "children": [
            {"placement": {"stack": {"axis": "x", "from": "-x", "sequence": ["a", "a", "a"]}}}]}}, [single("m")])
        self.assertEqual(codes(expand.expand(document)), [])

    def test_a_daughter_face_1e_7_outside_its_mother_is_an_error(self):
        document = spec({"m": {**box(["10", "10", "10"]), "children": [single("d", ("0.0000001", "0", "0"))]}, "d": box(["10", "10", "10"])},
                        [single("m")])
        self.assertIn("containment-outside", codes(expand.expand(document)))

    def test_a_daughter_face_inside_by_less_than_c_is_an_error(self):
        document = spec({"m": {**box(["10", "10", "10"]), "children": [single("d")]}, "d": box(["9.9999998", "10", "10"])}, [single("m")])
        self.assertIn("containment-too-close", codes(expand.expand(document)))

    def test_a_quarter_turn_is_checked_on_its_rotated_extent(self):
        document = spec({"m": {**box(["10", "20", "10"]), "children": [single("d", rotation={"axis": "z", "angle_deg": "90"})]},
                         "d": box(["20", "8", "8"])}, [single("m")])
        self.assertEqual(codes(expand.expand(document)), [])
        del document["templates"]["m"]["children"][0]["placement"]["single"]["rotation"]
        self.assertIn("containment-outside", codes(expand.expand(document)))

    def test_a_compound_rotation_is_checked_on_its_active_extent(self):
        # Rz(90) Ry(90) sends x to -z, y to -x, z to y, so a box 2 x 4 x 6 lands as 4 x 6 x 2; the transpose would give 6 x 2 x 4.
        rotation = {"zyx_deg": ["90", "90", "0"]}
        fits = spec({"m": {**box(["4", "6", "2"]), "children": [single("d", rotation=rotation)]}, "d": box(["2", "4", "6"])}, [single("m")])
        self.assertEqual(codes(expand.expand(fits)), [])
        transposed = spec({"m": {**box(["6", "2", "4"]), "children": [single("d", rotation=rotation)]}, "d": box(["2", "4", "6"])}, [single("m")])
        self.assertIn("containment-outside", codes(expand.expand(transposed)))

    def test_below_the_minimum_feature_is_an_error(self):
        self.assertIn("minimum-feature", codes(expand.expand(spec({"a": box(["0.000001", "1", "1"])}, [single("a")]))))

    def test_a_rotated_mother_turns_its_daughter_onto_another_axis(self):
        # In a mother turned by 90 degrees about z, a daughter along y lies along -x: both 4e5 mm shifts add up on one axis.
        def chain(rotation):
            document = spec({"m": {**box(["900000", "900000", "10"]), "children": [single("d", ("0", "400000", "0"))]}, "d": box(["1", "1", "1"])},
                            [single("m", ("-420000", "0", "0"), rotation=rotation)])
            document["world"]["size_mm"] = ["2000000", "2000000", "2000000"]
            return expand.expand(document)
        self.assertLess(overlap.chain_reach(chain(None))["d"], 420002)
        self.assertGreaterEqual(overlap.chain_reach(chain({"axis": "z", "angle_deg": "90"}))["d"], 820000)

    def test_a_placement_at_a_million_mm_is_refused(self):
        document = spec({"a": box(["1", "1", "1"])}, [single("a", ("1000000", "0", "0"))])
        document["world"]["size_mm"] = ["3000000", "3000000", "3000000"]
        self.assertIn("error-bound", codes(expand.expand(document)))


class RegionsAndFields(unittest.TestCase):
    def shared(self, key):
        return spec({"m1": {**box(["10", "10", "10"]), key: "one", "children": [single("d")]}, "m2": {**box(["10", "10", "10"]), "children": [single("d")]},
                     "d": box(["1", "1", "1"])}, [single("m1", ("-20", "0", "0")), single("m2", ("20", "0", "0"))])

    def test_a_daughter_inherits_unless_it_is_a_root(self):
        ir = expand.expand(calorimeter())
        self.assertEqual({n: t["region"] for n, t in ir["physical"]["templates"].items()},
                         {"world": "default", "module": "calorimeter", "absorber": "calorimeter", "active": "calorimeter"})

    def test_one_template_through_two_regions_is_refused(self):
        with self.assertRaises(GeometryError) as caught:
            expand.expand(self.shared("region"))
        self.assertEqual(caught.exception.code, "region-conflict")

    def test_field_against_no_field_is_refused(self):
        with self.assertRaises(GeometryError) as caught:
            expand.expand(self.shared("field"))
        self.assertEqual(caught.exception.code, "field-conflict")

    def test_a_declaration_on_the_template_settles_it(self):
        document = self.shared("region")
        document["templates"]["d"]["region"] = "own"
        self.assertEqual(expand.expand(document)["physical"]["templates"]["d"]["region"], "own")


class Bits(unittest.TestCase):
    def test_one_bit_too_few_is_refused(self):
        document = calorimeter()
        document["readout"]["cal"]["fields"]["layer"] = 1
        with self.assertRaises(GeometryError) as caught:
            expand.expand(document)
        self.assertEqual(caught.exception.code, "bitfield-range")


class Identities(unittest.TestCase):
    def ids(self, document):
        ir = expand.expand(document)
        return identity.geometry_id(ir), identity.provenance_id(ir)

    def setUp(self):
        self.base = self.ids(calorimeter())

    def test_changing_frames_changes_geometry_id(self):
        document = calorimeter()
        document["frames"]["beam"]["origin_mm"][2] = "-101"
        self.assertNotEqual(self.ids(document)[0], self.base[0])

    def test_changing_only_tags_changes_neither_selection_nor_geometry_id(self):
        document = calorimeter()
        document["templates"]["absorber"]["tags"] = ["passive", "lead"]
        geometry, provenance = self.ids(document)
        self.assertEqual(geometry, self.base[0])
        self.assertNotEqual(provenance, self.base[1])

    def test_changing_a_selection_through_tags_changes_geometry_id(self):
        document = calorimeter()
        document["templates"]["absorber"]["tags"] = ["passive", "active"]
        self.assertNotEqual(self.ids(document)[0], self.base[0])

    def test_tags_are_not_in_the_physical_part(self):
        physical = expand.expand(calorimeter())["physical"]
        self.assertNotIn("tags", str(sorted(physical)))
        self.assertTrue(all("tags" not in template for template in physical["templates"].values()))

    def test_a_requirement_is_written_as_an_expanded_list(self):
        physical = expand.expand(calorimeter())["physical"]
        self.assertEqual(physical["physics_requirements"], [{"need": "birks", "templates": ["active"]}])

    def test_a_material_source_is_marker_only(self):
        def material(facts, density):
            document = calorimeter()
            document["materials"] = {"glue": {"density_g_cm3": density, "facts": facts}}
            return self.ids(document)
        self.assertEqual(material("assumed", "1.2")[0], material("measured", "1.2")[0])
        self.assertNotEqual(material("assumed", "1.2")[1], material("measured", "1.2")[1])
        self.assertNotEqual(material("assumed", "1.2")[0], material("assumed", "1.3")[0])

    def test_an_empty_selection_is_refused(self):
        document = copy.deepcopy(calorimeter())
        document["physics_requirements"][0]["select"]["tags"] = ["missing"]
        with self.assertRaises(GeometryError) as caught:
            expand.expand(document)
        self.assertEqual(caught.exception.code, "select-empty")


class GridAndExplicit(unittest.TestCase):
    """g4sim S3: `grid` with bit-packed copy numbers, and `explicit` (Sections 6.2.2, 6.2.6, 15.1)."""

    def grid(self, n, names=("i", "j"), pitch=("10", "10"), **extra):
        return {"template": "cell", "placement": {"grid": {"n": list(n), "pitch_mm": list(pitch), "centre_mm": ["0", "0", "0"], "index": list(names), **extra}}}

    def placed(self, child, **extra):
        return expand.expand(spec({"cell": box(["2", "2", "2"])}, [child], **extra))["physical"]["placements"]

    def test_the_position_is_the_centre_of_the_grid(self):
        centres = [item["centre_mm"][:2] for item in self.placed(self.grid((2, 2)))]
        self.assertEqual(centres[0], ["-5e0", "-5e0"])
        self.assertEqual(centres[-1], ["5e0", "5e0"])

    def test_copy_numbers_are_packed_by_field_width(self):
        """A 6 x 6 grid with 3-bit fields is i + 8 j, never i + 6 j, so the decoded fields are the indices."""
        rows = self.placed(self.grid((6, 6)), readout={"ecal": {"fields": {"i": 3, "j": 3}}})
        for row in rows:
            self.assertEqual(row["copy_number"], row["index"]["i"] + 8 * row["index"]["j"])
            self.assertEqual(row["copy_number"] & 7, row["index"]["i"])
            self.assertEqual(row["copy_number"] >> 3, row["index"]["j"])

    def test_fields_of_one_placement_total_at_most_31_bits(self):
        fields = {"readout": {"ecal": {"fields": {"i": 11, "j": 11, "k": 11}}}}
        with self.assertRaises(GeometryError) as caught:
            self.placed(self.grid((2, 2, 2), ("i", "j", "k"), ("10", "10", "10")), **fields)
        self.assertEqual(caught.exception.code, "copy-width")

    def test_a_grid_needs_an_index_for_each_dimension(self):
        with self.assertRaises(GeometryError) as caught:
            self.placed(self.grid((2, 2), ("i",)))
        self.assertEqual(caught.exception.code, "grid-index")

    def test_stagger_shifts_odd_rows(self):
        rows = self.placed(self.grid((2, 2), stagger_mm="3"))
        self.assertEqual({row["index"]["j"]: row["centre_mm"][0] for row in rows if row["index"]["i"] == 0}, {0: "-5e0", 1: "-2e0"})

    def test_explicit_positions_keep_their_order(self):
        child = {"template": "cell", "placement": {"explicit": {"positions_mm": [["0", "0", "0"], ["5", "0", "0"]], "index": "n"}}}
        rows = self.placed(child)
        self.assertEqual([row["copy_number"] for row in rows], [0, 1])
        self.assertEqual(rows[1]["centre_mm"][0], "5e0")


class RotatedPlacements(unittest.TestCase):
    """Section 15.1, IR row: arbitrary angles, the separating-axis test and the true minimum distance."""

    def rotated(self, centre, angle):
        return single("plate", [str(value) for value in centre], {"axis": "z", "angle_deg": angle})

    def codes(self, *children):
        document = expand.expand(spec({"plate": box(["10", "4", "2"])}, list(children)))
        return {finding["code"] for finding in overlap.findings(document)}

    def offset(self, along_u, along_v):
        c, s = rotation.cos_sin(Decimal(30))
        return (along_u * c - along_v * s, along_u * s + along_v * c, 0)

    def test_cosine_and_sine_are_exact_to_34_digits(self):
        c, s = rotation.cos_sin(Decimal(30))
        self.assertEqual(str(s), "0.5000000000000000000000000000000000")
        self.assertEqual(str(c)[:34], "0.86602540378443864676372317075293")
        self.assertEqual(rotation.cos_sin(Decimal(90))[0], 0)

    def test_two_boxes_at_30_degrees_a_hair_apart_are_an_error(self):
        """Touching on one axis and 5e-7 mm apart on another: the true distance is in (epsilon, c)."""
        far = self.offset(Decimal(10), Decimal(4) + Decimal("5e-7"))
        self.assertIn("sibling-too-close", self.codes(self.rotated((0, 0, 0), "30"), self.rotated(far, "30")))

    def test_opposed_vertices_at_true_distance_above_c_pass(self):
        """Two boxes turned 45 degrees: rhombic sections with opposed vertices 1.2e-6 mm apart."""
        reach = Decimal(14) / Decimal(2).sqrt()
        apart = 2 * reach + Decimal("1.2e-6")
        square = {"plate": box(["10", "10", "2"])}
        document = expand.expand(spec(square, [single("plate", ["0", "0", "0"], {"axis": "z", "angle_deg": "45"}),
                                               single("plate", [str(apart), "0", "0"], {"axis": "z", "angle_deg": "45"})]))
        self.assertEqual({finding["code"] for finding in overlap.findings(document)}, set())

    def test_overlapping_rotated_boxes_are_an_error(self):
        self.assertIn("sibling-overlap", self.codes(self.rotated((0, 0, 0), "30"), self.rotated((5, 0, 0), "30")))

    def test_a_right_angle_keeps_its_integer_matrix(self):
        document = expand.expand(spec({"plate": box(["10", "4", "2"])}, [single("plate", ["0", "0", "0"], {"axis": "z", "angle_deg": "90"})]))
        self.assertTrue(all(isinstance(value, int) for row in document["physical"]["placements"][0]["rotation"] for value in row))


class ShapesRingsAndModifiers(unittest.TestCase):
    """g4sim S3: `trd`, `tube`, `polygon_prism`, `ring`, `clip`, `absent`, and the rest of the IR row of Section 15.1."""

    def wedge_ring(self, phi0="0", n=12, inner=None):
        """12 trds whose sides meet exactly: half-widths at each end follow from the angle of one wedge."""
        tangent = Decimal(1) * rotation.cos_sin(Decimal(15))[1] / rotation.cos_sin(Decimal(15))[0]
        inner_r, outer_r = Decimal(100), Decimal(120)
        y1, y2 = 2 * inner_r * tangent, 2 * outer_r * tangent
        wedge = {"solid": {"trd": {"x1_mm": "10", "x2_mm": "10", "y1_mm": str(y1), "y2_mm": str(y2), "length_mm": "20"}}, "material": "G4_Si"}
        return spec({"wedge": wedge}, [{"template": "wedge", "placement": {"ring": {"n": n, "radius_mm": "110", "phi0_deg": phi0, "index": "phi"}}}])

    def codes(self, document):
        return {finding["code"] for finding in overlap.findings(expand.expand(document))}

    def test_a_ring_of_abutting_wedges_passes(self):
        self.assertEqual(self.codes(self.wedge_ring()), set())

    def test_one_turned_by_a_nanoradian_is_an_overlap(self):
        document = expand.expand(self.wedge_ring())
        placement = document["physical"]["placements"][3]
        angle = Decimal("1e-9") * 180 / Decimal("3.14159265358979323846")
        extra = rotation.active_matrix({"axis": "z", "angle_deg": angle})
        turned = rotation.product(extra, rotation.transpose(tuple(tuple(value if isinstance(value, int) else Decimal(value) for value in row) for row in placement["rotation"])))
        placement["rotation"] = [[value if isinstance(value, int) else str(value) for value in row] for row in rotation.transpose(turned)]
        self.assertIn("sibling-overlap", {finding["code"] for finding in overlap.findings(document)})

    def test_a_tube_off_its_axis_too_close_to_clear_is_rejected(self):
        tube = {"solid": {"tube": {"rmin_mm": "0", "rmax_mm": "10", "length_mm": "40"}}, "material": "G4_Si"}
        document = spec({"tube": tube, "plate": box(["40", "40", "2"])}, [single("tube", ("0", "0", "0"), {"axis": "x", "angle_deg": "30"}), single("plate", ("0", "0", "15"))])
        self.assertIn("sibling-unjudged", self.codes(document))

    def test_tubes_on_one_axis_are_judged_in_cylindrical_coordinates(self):
        def tube(rmin, rmax):
            return {"solid": {"tube": {"rmin_mm": rmin, "rmax_mm": rmax, "length_mm": "40"}}, "material": "G4_Si"}
        clear = spec({"inner": tube("0", "10"), "outer": tube("10", "20")}, [single("inner"), single("outer")])
        self.assertEqual(self.codes(clear), set())
        close = spec({"inner": tube("0", "10"), "outer": tube("10.0000001", "20")}, [single("inner"), single("outer")])
        self.assertIn("sibling-too-close", self.codes(close))

    def test_the_prism_keeps_its_circumradius_and_gives_g4_the_apothem(self):
        prism = {"solid": {"polygon_prism": {"sides": 6, "radius_mm": "10", "length_mm": "4"}}, "material": "G4_Si"}
        solid = expand.expand(spec({"p": prism}, [single("p")]))["physical"]["templates"]["p"]["solid"]
        self.assertEqual(solid["circumradius_mm"], "1e1")
        self.assertTrue(solid["apothem_mm"].startswith("8.660254037844386"))

    def test_absent_keeps_the_vacant_numbers(self):
        child = {"template": "cell", "placement": {"grid": {"n": [2, 2], "pitch_mm": ["5", "5"], "centre_mm": ["0", "0", "0"], "index": ["i", "j"]}},
                 "modifiers": [{"absent": {"cells": [{"i": 1, "j": 0}]}}]}
        rows = expand.expand(spec({"cell": box(["2", "2", "2"])}, [child]))["physical"]["placements"]
        self.assertEqual(sorted(row["copy_number"] for row in rows), [0, 2, 3])

    def test_clip_by_centre_or_whole_cell(self):
        def kept(mode):
            child = {"template": "cell", "placement": {"grid": {"n": [3, 3], "pitch_mm": ["10", "10"], "centre_mm": ["0", "0", "0"], "index": ["i", "j"]}},
                     "modifiers": [{"clip": {"mode": mode, "envelope": {"radius_mm": "11"}}}]}
            return len(expand.expand(spec({"cell": box(["8", "8", "2"])}, [child]))["physical"]["placements"])
        self.assertEqual(kept("centre_inside"), 5)
        self.assertEqual(kept("fully_inside"), 1)


class NonBoxMothersAndShell(unittest.TestCase):
    """Containment in mothers that are not boxes, shell, rays through the new shapes, and their GDML."""

    TUBE = {"solid": {"tube": {"rmin_mm": "0", "rmax_mm": "10", "length_mm": "40"}}, "material": "G4_AIR"}
    TRD = {"solid": {"trd": {"x1_mm": "20", "x2_mm": "10", "y1_mm": "20", "y2_mm": "10", "length_mm": "40"}}, "material": "G4_AIR"}

    def codes(self, mother, child, centre=("0", "0", "0")):
        document = spec({"mother": {**mother, "children": [single("child", centre)]}, "child": child}, [single("mother")])
        return {finding["code"] for finding in overlap.findings(expand.expand(document))}

    def test_a_box_poking_through_a_tube_wall_is_outside(self):
        """Inside the tube's bounding box, outside the tube: the corner reaches r = 11.3."""
        self.assertIn("containment-outside", self.codes(self.TUBE, box(["16", "16", "2"])))
        self.assertEqual(self.codes(self.TUBE, box(["10", "10", "2"])), set())

    def test_a_box_in_the_narrow_end_of_a_trd_is_outside(self):
        self.assertIn("containment-outside", self.codes(self.TRD, box(["16", "16", "2"]), ("0", "0", "18")))
        self.assertEqual(self.codes(self.TRD, box(["16", "16", "2"]), ("0", "0", "-18")), set())

    def test_a_box_in_a_tube_hole_is_outside(self):
        hollow = {"solid": {"tube": {"rmin_mm": "5", "rmax_mm": "10", "length_mm": "40"}}, "material": "G4_AIR"}
        self.assertIn("containment-outside", self.codes(hollow, box(["2", "2", "2"])))
        self.assertEqual(self.codes(hollow, box(["2", "2", "2"]), ("7", "0", "0")), set())

    def test_a_field_given_by_a_parameter_reaches_the_ir_as_its_value(self):
        # the program reads the text as a number: a name it cannot read would be a field of 0 T, silently
        made = expand.expand(spec(params={"strength": "0.5", "half": "strength / 2"}, fields={"dipole": {"b_tesla": ["0", "0", "half"]}}))
        self.assertEqual([float(value) for value in made["physical"]["fields"]["dipole"]["b_tesla"]], [0.0, 0.0, 0.25])

    def test_a_field_given_by_numbers_keeps_its_text(self):
        made = expand.expand(spec(fields={"dipole": {"b_tesla": ["0", "0", "1"]}}))
        self.assertEqual(made["physical"]["fields"], {"dipole": {"b_tesla": ["0", "0", "1"]}})

    def test_a_field_naming_an_unknown_parameter_is_an_error(self):
        with self.assertRaises(GeometryError):
            expand.expand(spec(fields={"dipole": {"b_tesla": ["0", "0", "missing"]}}))

    def test_shell_wraps_a_template_with_the_active_faces(self):
        crystal = {**box(["20", "20", "50"]), "modifiers": [{"shell": {"material": "G4_MYLAR", "thickness_mm": "1", "faces": ["sides", "front"]}}]}
        physical = expand.expand(spec({"crystal": crystal}, [single("crystal")]))["physical"]
        self.assertEqual(physical["templates"]["crystal_shell"]["half_mm"], ["1.1e1", "1.1e1", "2.55e1"])
        inside = [row for row in physical["placements"] if row["template"] == "crystal"][0]
        self.assertEqual(inside["mother"], "crystal_shell")
        self.assertEqual(inside["centre_mm"][2], "5e-1")

    def test_a_shell_that_does_not_fit_is_an_error(self):
        crystal = {**box(["20", "20", "50"]), "modifiers": [{"shell": {"material": "G4_MYLAR", "thickness_mm": "1", "faces": ["sides"]}}]}
        document = spec({"cell": {**box(["21", "21", "60"], "G4_AIR"), "children": [single("crystal")]}, "crystal": crystal}, [single("cell")])
        self.assertIn("containment-outside", {finding["code"] for finding in overlap.findings(expand.expand(document))})

    def test_a_ray_through_a_tube_and_its_hole(self):
        hollow = {"solid": {"tube": {"rmin_mm": "5", "rmax_mm": "10", "length_mm": "40"}}, "material": "G4_Si"}
        ir = expand.expand(spec({"pipe": hollow}, [single("pipe")]))
        length = material.path_by_material(ir, (Decimal(-100), Decimal(0), Decimal(0)), (Decimal(1), Decimal(0), Decimal(0)))["G4_Si"]
        self.assertEqual(length, Decimal(10))

    def test_a_ray_through_a_trd(self):
        wedge = {"solid": {"trd": {"x1_mm": "20", "x2_mm": "10", "y1_mm": "20", "y2_mm": "10", "length_mm": "40"}}, "material": "G4_Si"}
        ir = expand.expand(spec({"wedge": wedge}, [single("wedge")]))
        length = material.path_by_material(ir, (Decimal(-100), Decimal(0), Decimal(0)), (Decimal(1), Decimal(0), Decimal(0)))["G4_Si"]
        self.assertEqual(length, Decimal(15))

    def test_the_export_names_each_shape_and_a_general_rotation(self):
        prism = {"solid": {"polygon_prism": {"sides": 6, "radius_mm": "10", "length_mm": "4"}}, "material": "G4_Si"}
        ir = expand.expand(spec({"t": self.TRD, "u": self.TUBE, "p": prism}, [single("t", ("-50", "0", "0")), single("u", ("50", "0", "0")),
                                                                              single("p", ("0", "0", "100"), {"axis": "z", "angle_deg": "30"})]))
        text = gdml.export(ir)
        for tag in ("<trd ", "<tube ", "<polyhedra "):
            self.assertIn(tag, text)
        rotated = [row for row in ir["physical"]["placements"] if row["template"] == "p"][0]["rotation"]
        self.assertLess(abs(gdml.euler_angles(rotated)[2] + 30), Decimal("1e-30"))  # GDML takes the passive angle
        self.assertIn('z="-', text)


if __name__ == "__main__":
    unittest.main()

"""Field maps (g4sim S7, Section 6.2.8): the g4sim-field-map/1 format, interpolation, and check-spec's reading by hash, frame and
coverage; the Section 15.1 negative test is a field-map file with a mismatched hash."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import geometry  # noqa: E402
from core.geometry import expand, fieldmap  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402


def map_text(field=lambda x, y, z: (0.001 * y, 0.14 + 1e-5 * x * x, 0.0005 * z), origin=(-50, -50, -100), step=(25, 25, 50), count=(5, 5, 5)) -> str:
    lines = [fieldmap.FORMAT, "origin_mm %s %s %s" % origin, "step_mm %s %s %s" % step, "count %s %s %s" % count, fieldmap.COLUMNS]
    for k in range(count[2]):
        for j in range(count[1]):
            for i in range(count[0]):
                lines.append("%r %r %r" % field(origin[0] + step[0] * i, origin[1] + step[1] * j, origin[2] + step[2] * k))
    return "\n".join(lines) + "\n"


def magnet_spec(sha256: str, bore=("100", "100", "200"), placements=1) -> dict:
    children = [{"template": "bore", "placement": {"single": {"centre_mm": [str(300 * n), "0", "0"], "rotation": {"axis": "z", "angle_deg": "90"}}}}
                for n in range(placements)]
    return {"schema": "detector-spec/1", "params": {}, "fields": {"magnet": {"map": {"path": "m.txt", "sha256": sha256}}},
            "templates": {"bore": {"solid": {"box": {"size_mm": list(bore)}}, "material": "G4_Galactic", "field": "magnet", "children": [
                {"template": "si", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
                "si": {"solid": {"box": {"size_mm": ["10", "10", "1"]}}, "material": "G4_Si"}},
            "world": {"material": "G4_Galactic", "size_mm": ["2000", "1000", "1000"], "children": children}}


class Format(unittest.TestCase):
    def test_a_map_reads_its_grid_exactly_and_its_values_in_order(self):
        parsed = fieldmap.parse(map_text())
        self.assertEqual(parsed["grid"], {"origin_mm": ["-5e1", "-5e1", "-1e2"], "step_mm": ["2.5e1", "2.5e1", "5e1"], "count": [5, 5, 5]})
        self.assertEqual(len(parsed["values"]), 3 * 125)
        self.assertEqual(parsed["values"][:3], [-0.05, 0.14 + 1e-5 * 2500, -0.05])

    def test_a_malformed_map_is_refused(self):
        good = map_text()
        broken = [good.replace(fieldmap.FORMAT, "g4sim-field-map/2"), good.replace("count 5 5 5", "count 5 5 1"),
                  good.replace("step_mm 25 25 50", "step_mm 25 0 50"), good.replace(fieldmap.COLUMNS, "bx by bz"),
                  good.rsplit("\n", 2)[0] + "\n", good.replace("\n0.0", "\nnan", 1), good + "1 2 3\n"]
        for text in broken:
            with self.subTest(text=text[:80]), self.assertRaises(GeometryError) as caught:
                fieldmap.parse(text)
            self.assertEqual(caught.exception.code, "field-map-format")


class Interpolation(unittest.TestCase):
    def setUp(self):
        self.linear = fieldmap.parse(map_text(field=lambda x, y, z: (1 + 0.01 * x + 0.02 * y - 0.03 * z + 1e-4 * x * y * z, 0.0, -2.0)))

    def test_a_trilinear_field_is_reproduced_inside_the_cells(self):
        for point in ((0.0, 0.0, 0.0), (12.5, -7.0, 33.0), (-49.0, 49.0, -99.0)):
            x, y, z = point
            got = fieldmap.interpolate(self.linear["grid"], self.linear["values"], point)
            self.assertAlmostEqual(got[0], 1 + 0.01 * x + 0.02 * y - 0.03 * z + 1e-4 * x * y * z, places=12)
            self.assertEqual(got[1:], [0.0, -2.0])

    def test_a_node_gives_its_own_value(self):
        parsed = fieldmap.parse(map_text())
        self.assertEqual(fieldmap.interpolate(parsed["grid"], parsed["values"], (25.0, -25.0, 0.0)), [-0.025, 0.14 + 1e-5 * 625, 0.0])

    def test_a_point_outside_takes_the_nearest_grid_point(self):
        grid, values = self.linear["grid"], self.linear["values"]
        self.assertEqual(fieldmap.interpolate(grid, values, (500.0, 0.0, 0.0)), fieldmap.interpolate(grid, values, (50.0, 0.0, 0.0)))


class CheckSpec(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.map_bytes = map_text().encode()
        (self.folder / "m.txt").write_bytes(self.map_bytes)
        self.sha = hashlib.sha256(self.map_bytes).hexdigest()

    def tearDown(self):
        for path in self.folder.iterdir():
            path.unlink()
        self.folder.rmdir()

    def check(self, spec: dict) -> dict:
        (self.folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        return geometry.check_file(self.folder / "spec.json")

    def codes(self, spec: dict) -> list:
        return [finding["code"] for finding in self.check(spec)["findings"]]

    def test_a_map_enters_the_ir_by_its_hash_and_grid_never_its_path(self):
        checked = self.check(magnet_spec(self.sha))
        self.assertEqual(checked["status"], "ok")
        self.assertEqual(checked["ir"]["physical"]["fields"]["magnet"], {"map": {"sha256": self.sha, "frame_template": "bore",
                         "origin_mm": ["-5e1", "-5e1", "-1e2"], "step_mm": ["2.5e1", "2.5e1", "5e1"], "count": [5, 5, 5]}})
        self.assertNotIn("m.txt", json.dumps(checked["ir"]["physical"]))
        self.assertEqual(checked["ir"]["marker"]["source_of_facts"]["field-map:m.txt"], self.sha)
        self.assertEqual(checked["field_map_files"], {"magnet": str((self.folder / "m.txt").resolve())})
        self.assertEqual(checked["ir"]["physical"]["templates"]["si"]["field"], "magnet")

    def test_a_field_map_file_with_a_mismatched_hash_is_refused(self):
        self.assertEqual(self.codes(magnet_spec("0" * 64)), ["field-map-hash"])
        (self.folder / "m.txt").write_bytes(self.map_bytes.replace(b"0.14", b"0.15", 1))  # one value edited after the hash was recorded
        self.assertEqual(self.codes(magnet_spec(self.sha)), ["field-map-hash"])

    def test_the_hash_changes_geometry_id_and_the_path_does_not(self):
        first = self.check(magnet_spec(self.sha))["geometry_id"]
        other = map_text(field=lambda x, y, z: (0.0, 0.15, 0.0)).encode()
        (self.folder / "n.txt").write_bytes(other)
        moved = magnet_spec(self.sha)
        moved["fields"]["magnet"]["map"]["path"] = "./m.txt"
        self.assertEqual(self.check(moved)["geometry_id"], first)
        changed = magnet_spec(hashlib.sha256(other).hexdigest())
        changed["fields"]["magnet"]["map"]["path"] = "n.txt"
        self.assertNotEqual(self.check(changed)["geometry_id"], first)

    def test_a_map_outside_the_specifications_folder_is_refused(self):
        spec = magnet_spec(self.sha)
        spec["fields"]["magnet"]["map"]["path"] = "../m.txt"
        self.assertEqual(self.codes(spec), ["field-map-path"])

    def test_a_grid_that_does_not_cover_its_template_is_refused(self):
        self.assertEqual(self.codes(magnet_spec(self.sha, bore=("100", "102", "200"))), ["field-map-coverage"])

    def test_a_frame_template_placed_twice_is_refused(self):
        self.assertEqual(self.codes(magnet_spec(self.sha, placements=2)), ["field-map-frame"])

    def test_a_map_declared_by_two_templates_is_refused(self):
        spec = magnet_spec(self.sha)
        spec["templates"]["si"]["field"] = "magnet"
        self.assertEqual(self.codes(spec), ["field-map-frame"])

    def test_the_schema_takes_a_vector_or_a_map_not_both(self):
        spec = magnet_spec(self.sha)
        spec["fields"]["magnet"]["b_tesla"] = ["0", "1", "0"]
        self.assertEqual(self.codes(spec), ["schema"])

    def test_expansion_without_the_read_is_refused(self):
        spec = magnet_spec(self.sha)
        with self.assertRaises(GeometryError) as caught:
            expand.expand(copy.deepcopy(spec))
        self.assertEqual(caught.exception.code, "field-map-unread")

    def test_a_uniform_field_keeps_its_geometry_id(self):
        uniform = magnet_spec(self.sha)
        uniform["fields"]["magnet"] = {"b_tesla": ["0", "1", "0"]}
        checked = self.check(uniform)
        self.assertEqual(checked["status"], "ok")
        self.assertNotIn("field_map_files", checked)
        # the geometry_id this specification had before S7 (check_file at 8d40a11a): adding field maps changed no uniform field's
        self.assertEqual(checked["geometry_id"], "c4a170157963445efb8d30f0320e04128c6358bd031a1dd35a78d01d65cdfa52")


if __name__ == "__main__":
    unittest.main()

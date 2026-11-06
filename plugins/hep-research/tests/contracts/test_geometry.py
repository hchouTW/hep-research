"""contracts/geometry.py (g4sim S1): the type table comes from the schema, and each refusal of Section 15.1 for specifications
is reached through the whole reading procedure."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import geometry  # noqa: E402


def document(**extra):
    return {"schema": "detector-spec/1", "params": {"w": 10, "pitch": "w + 5"},
            "materials": {"glue": {"density_g_cm3": 1.2, "composition": {"C": 0.6, "H": 0.4}, "facts": "assumed"}},
            "templates": {"cell": {"solid": {"box": {"size_mm": ["w", 10.0, "10"]}}, "material": "glue", "tags": ["active"]}},
            "world": {"material": "G4_AIR", "size_mm": [1000, 1000, 1000], "children": [
                {"template": "cell", "placement": {"linear": {"count": 3, "pitch_mm": ["pitch", 0, 0], "start_mm": [-15, 0, 0], "index": "i"}}}]},
            "readout": {"cal": {"fields": {"i": 2}}}, **extra}


def check(spec, claims=()):
    return geometry.check_spec(json.dumps(spec), claims)


def codes(result):
    return [finding["code"] for finding in result["findings"]]


class TypeTable(unittest.TestCase):
    def test_the_table_covers_the_typed_fields(self):
        table = geometry.field_types()
        self.assertEqual(table["/params/*"], "quantity")
        self.assertEqual(table["/world/size_mm/*"], "quantity")
        self.assertEqual(table["/templates/*/solid/box/size_mm/*"], "quantity")
        self.assertEqual(table["/world/children/*/placement/linear/count"], "integer")
        self.assertEqual(table["/readout/*/fields/*"], "integer")
        self.assertEqual(table["/templates/*/children/*/placement/stack/sequence/*/spacer_mm"], "quantity")


class Specification(unittest.TestCase):
    def test_a_legal_specification_gives_identities(self):
        result = check(document())
        self.assertEqual(result["status"], "ok", result["findings"])
        self.assertEqual(len(result["geometry_id"]), 64)

    def test_53_and_53_0_give_the_same_geometry_id(self):
        forms = []
        for size in (53, 53.0, "53"):
            spec = document()
            spec["templates"]["cell"]["solid"]["box"]["size_mm"][2] = size
            forms.append(check(spec)["geometry_id"])
        self.assertEqual(len(set(forms)), 1)

    def test_6_5_in_an_integer_field_is_refused(self):
        spec = document()
        spec["world"]["children"][0]["placement"]["linear"]["count"] = 6.5
        self.assertEqual(codes(check(spec)), ["integer-field"])

    def test_a_number_with_no_declared_type_is_refused(self):
        self.assertEqual(codes(check(document(unknown=1))), ["undeclared-number"])

    def test_a_field_with_the_wrong_unit_suffix_is_refused(self):
        spec = document()
        spec["world"]["size_cm"] = spec["world"].pop("size_mm")
        self.assertIn("undeclared-number", codes(check(spec)))

    def test_an_illegal_combination_is_refused(self):
        spec = document()
        spec["materials"]["glue"]["base"] = "G4_WATER"
        self.assertEqual(codes(check(spec)), ["schema"])

    def test_an_unresolvable_claim_is_refused(self):
        spec = document(source_of_facts={"/params/w": "claim:ams:width"})
        self.assertEqual(codes(check(spec)), ["facts-claim"])
        self.assertEqual(check(spec, ["ams:width"])["status"], "ok")

    def test_a_source_that_points_at_nothing_is_refused(self):
        self.assertEqual(codes(check(document(source_of_facts={"/params/missing": "assumed"}))), ["facts-pointer"])

    def test_a_gap_below_c_is_refused_end_to_end(self):
        spec = document()
        spec["world"]["children"][0]["placement"]["linear"]["pitch_mm"][0] = 10.00000011
        self.assertIn("sibling-too-close", codes(check(spec)))

    def test_a_decimal_kept_exact_through_the_reader(self):
        spec = document()
        spec["params"]["w"] = "10.0000000000000000000000000000001"
        self.assertEqual(check(spec)["ir"]["physical"]["templates"]["cell"]["half_mm"][0], "5.00000000000000000000000000000005e0")


class Golden(unittest.TestCase):
    """Gate 6: the same specification gives the same identities on E2 and E5. Exact decimal arithmetic has no platform in it."""
    folder = ROOT / "tests/core/data/geometry"

    def test_the_golden_specification_reproduces_its_identities_and_ir(self):
        result = geometry.check_spec((self.folder / "calorimeter.spec.json").read_bytes())
        self.assertEqual(result["status"], "ok", result["findings"])
        ids = json.loads((self.folder / "calorimeter.ids.json").read_text(encoding="utf-8"))
        self.assertEqual(result["geometry_id"], ids["geometry_id"])
        self.assertEqual(result["provenance_id"], ids["provenance_id"])
        self.assertEqual(result["ir"], json.loads((self.folder / "calorimeter.ir.json").read_text(encoding="utf-8")))


class CommandLine(unittest.TestCase):
    def run_it(self, *argv):
        return subprocess.run([sys.executable, str(ROOT / "contracts/geometry.py"), *argv], capture_output=True, text=True, timeout=60)

    def test_a_valid_file_writes_the_ir(self):
        with tempfile.TemporaryDirectory() as folder:
            path, out = Path(folder, "spec.json"), Path(folder, "out", "ir.json")
            path.write_text(json.dumps(document()), encoding="utf-8")
            done = self.run_it(str(path), "--out", str(out))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(json.loads(done.stdout)["status"], "ok")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["schema"], "geometry-ir/1")

    def test_a_refused_file_exits_1_and_a_missing_one_2(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "spec.json")
            path.write_text("{}", encoding="utf-8")
            self.assertEqual(self.run_it(str(path)).returncode, 1)
            self.assertEqual(self.run_it(str(Path(folder, "missing.json"))).returncode, 2)


class ExplicitFromCsv(unittest.TestCase):
    """An explicit placement read from a CSV by its recorded hash (Section 6.2.2)."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.table = self.root / "cells.csv"
        self.table.write_text("0,0,0\n50,0,0\n", encoding="utf-8")

    def spec(self, digest):
        child = {"template": "cell", "placement": {"explicit": {"positions_csv": {"path": "cells.csv", "sha256": digest}, "index": "n"}}}
        return {"schema": "detector-spec/1", "params": {}, "templates": {"cell": {"solid": {"box": {"size_mm": ["2", "2", "2"]}}, "material": "G4_Si"}},
                "world": {"material": "G4_AIR", "size_mm": ["1000", "1000", "1000"], "children": [child]}}

    def check(self, digest):
        path = self.root / "spec.json"
        path.write_text(json.dumps(self.spec(digest)), encoding="utf-8")
        return geometry.check_file(path)

    def test_the_positions_come_from_the_file_and_its_hash_is_kept(self):
        digest = hashlib.sha256(self.table.read_bytes()).hexdigest()
        result = self.check(digest)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(len(result["ir"]["physical"]["placements"]), 2)
        self.assertEqual(result["ir"]["marker"]["source_of_facts"]["explicit:cells.csv"], digest)

    def test_a_changed_file_is_refused_without_showing_its_hash(self):
        result = self.check("0" * 64)
        self.assertEqual(result["findings"][0]["code"], "explicit-hash")
        self.assertNotIn(hashlib.sha256(self.table.read_bytes()).hexdigest(), str(result))

    def test_a_file_outside_the_folder_is_refused(self):
        for path, code in (("../secret.csv", "explicit-path"), ("/etc/passwd", "path-reference")):  # the canonical check refuses an absolute path first
            document = self.spec("0" * 64)
            document["world"]["children"][0]["placement"]["explicit"]["positions_csv"]["path"] = path
            spec_path = self.root / "spec.json"
            spec_path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(geometry.check_file(spec_path)["findings"][0]["code"], code)


if __name__ == "__main__":
    unittest.main()

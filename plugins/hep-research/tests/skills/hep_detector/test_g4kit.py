"""Kits, g4kit.py and the geometry kinds of the design loop (g4sim plan, Sections 12, 14.2, 14.3; S5 gates 3 and 4)."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from contracts import design  # noqa: E402
from contracts.schema import validate  # noqa: E402

SCRIPT = ROOT / "skills/hep-detector/scripts/g4kit.py"
KITS = ROOT / "skills/hep-detector/assets/g4kits"
CANDIDATE, OTHER = "j15-v1:cand-N4", "j15-v1:cand-N6"
EXAMPLE = ROOT / "examples/design-minimal-spectrometer/output/artifacts"
TRACKER = {"planes": 5, "plane_gap_mm": 100.0, "plane_thickness_mm": 0.3, "plane_side_mm": 400.0, "field_tesla": 1.0, "plane_material": "G4_Si", "world_material": "G4_Galactic"}
CASES = {"planes-tracker": TRACKER,
         "calorimeter": {"layers": 10, "towers_x": 3, "towers_y": 3, "absorber_mm": 2.0, "active_mm": 3.0, "tower_side_mm": 40.0, "absorber_material": "G4_Pb", "active_material": "G4_PLASTIC_SC_VINYLTOLUENE", "wrap_material": "G4_MYLAR", "guide_material": "G4_PLEXIGLASS", "world_material": "G4_AIR"},
         "tof": {"planes": 2, "bars": 8, "bar_length_mm": 1000.0, "bar_width_mm": 100.0, "bar_thickness_mm": 10.0, "plane_gap_mm": 50.0, "bar_material": "G4_PLASTIC_SC_VINYLTOLUENE", "world_material": "G4_AIR"}}


def derive(folder: Path, kind: str, fields: dict) -> subprocess.CompletedProcess:
    geometry = folder / "design.geometry.json"
    geometry.write_text(json.dumps({"schema": "design-geometry/1", "geometry": kind, "geometry_kind": kind, "fields": fields}), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), "derive", "--geometry", str(geometry), "--out-detector", str(folder / "detector.json"), "--out-derivation", str(folder / "derivation.json")], capture_output=True, text=True, timeout=120, check=False)


class Kits(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)

    def test_every_kit_makes_a_specification_and_a_record(self):
        for kind, fields in CASES.items():
            with self.subTest(kind=kind):
                done = derive(self.work, kind, fields)
                self.assertEqual(done.returncode, 0, done.stdout)
                record = json.loads((self.work / "derivation.json").read_text(encoding="utf-8"))
                self.assertTrue(validate(record, "geometry_derivation.json").ok)
                self.assertEqual(record["detector_spec_sha256"], hashlib.sha256((self.work / "detector.json").read_bytes()).hexdigest())
                self.assertEqual(record["design_geometry_sha256"], hashlib.sha256((self.work / "design.geometry.json").read_bytes()).hexdigest())

    def test_a_derivation_is_reproducible(self):
        first = derive(self.work, "tof", CASES["tof"])
        second = derive(self.work, "tof", CASES["tof"])
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))

    def test_a_design_change_changes_the_geometry(self):
        identities = [json.loads(derive(self.work, "planes-tracker", {**TRACKER, "planes": planes}).stdout)["geometry_id"] for planes in (5, 6)]
        self.assertNotEqual(*identities)

    def test_a_missing_or_unknown_input_is_refused(self):
        without = {key: value for key, value in TRACKER.items() if key != "field_tesla"}
        for fields in (without, {**TRACKER, "planes_extra": 1}, {**TRACKER, "planes": 2.5}, {**TRACKER, "plane_material": 3}):
            with self.subTest(fields=sorted(fields)):
                self.assertEqual(derive(self.work, "planes-tracker", fields).returncode, 2)

    def test_a_kind_without_a_kit_is_refused(self):
        self.assertEqual(derive(self.work, "layered-spectrometer", {}).returncode, 2)

    def test_a_kit_that_makes_an_illegal_geometry_fails(self):
        done = derive(self.work, "tof", {**CASES["tof"], "bars": 0})
        self.assertEqual(done.returncode, 1, done.stdout)

    def test_a_kit_has_geometric_defaults_only(self):
        for path in sorted(KITS.glob("*.json")):
            kit = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(kit=kit["name"]):
                self.assertTrue(all(name.endswith("_mm") for name in kit["geometric_defaults"]), kit["geometric_defaults"])
                self.assertFalse(set(kit["geometric_defaults"]) & set(kit["inputs"]))

    def test_a_mapping_reads_exactly_the_kits_inputs(self):
        for path in sorted(KITS.glob("*.json")):
            kit = json.loads(path.read_text(encoding="utf-8"))
            mapping = json.loads(design.geometry_mapping(kit["geometry_kind"]).read_text(encoding="utf-8"))
            with self.subTest(kit=kit["name"]):
                self.assertTrue(validate(mapping, "design_geometry.json").ok)
                self.assertEqual({item["field"] for item in mapping["fields"]}, set(kit["inputs"]))
                self.assertEqual(mapping["kit"], {"name": kit["name"], "version": kit["version"]})
                self.assertEqual(mapping["geometry"], kit["geometry_kind"])
                self.assertEqual(design.geometry_mapping(kit["geometry_kind"]).stem, kit["geometry_kind"])


class Mapping(unittest.TestCase):
    def test_the_layered_mapping_is_the_original_file(self):
        self.assertEqual(design.geometry_mapping("layered-spectrometer"), design.GEOMETRY_FILE)
        self.assertEqual(json.loads(design.GEOMETRY_FILE.read_text(encoding="utf-8"))["mapping_version"], "1.1.0")

    def test_an_unknown_kind_is_an_error(self):
        with self.assertRaises(design.GeometryKindUnknown):
            design.geometry_mapping("no-such-kind")

    def test_the_two_forms_exclude_each_other(self):
        original = json.loads(design.GEOMETRY_FILE.read_text(encoding="utf-8"))
        of_a_kit = json.loads(design.geometry_mapping("tof").read_text(encoding="utf-8"))
        self.assertFalse(validate({**original, "kit": of_a_kit["kit"]}, "design_geometry.json").ok)
        self.assertFalse(validate({key: value for key, value in of_a_kit.items() if key != "kit"}, "design_geometry.json").ok)
        self.assertFalse(validate({**of_a_kit, "mapping_version": "1.1.0"}, "design_geometry.json").ok)


class Binding(unittest.TestCase):
    """Gates 3 and 4, on a copy of J15: a candidate, its geometry file and a derivation record."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.artifacts = Path(self.folder.name) / "artifacts"
        shutil.copytree(EXAMPLE, self.artifacts)
        self.geometry = self.artifacts / "studies/G-N4-TRK1.geometry.json"
        self.identity = "a" * 64

    def errors(self, record: dict | None, candidate: dict, geometry: dict | None = None) -> list:
        path = self.artifacts / "candidates/cand-N4.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["extension"].update(candidate)
        path.write_text(json.dumps(document), encoding="utf-8")
        if record is not None:
            (self.artifacts / "studies/derivation.json").write_text(json.dumps(record), encoding="utf-8")
        project = design.Project(self.artifacts, None)
        evaluation = design.Evaluation(Path("."), ".", {"extension": {"candidate": CANDIDATE, "denominator": {}}})
        design.check_derivation(project, evaluation, CANDIDATE, design.candidate_geometry_kind(project, CANDIDATE), self.geometry.read_bytes(), geometry or {})
        return [getattr(item, "code", item[0] if isinstance(item, tuple) else item) for item in evaluation.errors]

    def record(self, **changes) -> dict:
        return {"schema": "geometry-derivation/1", "design_geometry_sha256": hashlib.sha256(self.geometry.read_bytes()).hexdigest(), "geometry_kind": "tof", "kit": {"name": "tof", "version": "1.0.0", "sha256": "0" * 64}, "detector_spec_sha256": "1" * 64, "geometry_id": self.identity, **changes}

    def bound(self) -> dict:
        return {"geometry_kind": "tof", "geometry_derivation_ref": "studies/derivation.json", "geometry_id": self.identity}

    def test_a_faithful_record_passes(self):
        self.assertEqual(self.errors(self.record(), self.bound()), [])

    def test_a_tampered_record_is_refused(self):
        for changes in ({"design_geometry_sha256": "b" * 64}, {"geometry_kind": "calorimeter"}, {"geometry_id": "c" * 64}, {"schema": "other"}):
            with self.subTest(changes=sorted(changes)):
                self.assertIn("design.derivation_mismatch", self.errors(self.record(**changes), self.bound()))

    def test_a_record_that_is_not_json_is_refused(self):
        (self.artifacts / "studies/derivation.json").write_text("{", encoding="utf-8")
        self.assertIn("design.derivation_mismatch", self.errors(None, self.bound()))

    def test_the_run_and_the_study_spec_must_agree(self):
        wrong = "d" * 64
        for extension in ({"geometry": {"geometry_id": wrong}}, {"study": {"spec": {"physics": {"g4sim": {"geometry_id": wrong}}}}}):
            with self.subTest(extension=sorted(extension)):
                self.assertIn("design.derivation_mismatch", self.errors(self.record(), self.bound(), extension))

    def set_kind(self, name: str, kind: str) -> None:
        path = self.artifacts / f"candidates/{name}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["extension"]["geometry_kind"] = kind
        path.write_text(json.dumps(document), encoding="utf-8")

    def test_a_derived_candidate_inherits_the_kind(self):
        self.set_kind("cand-N6", "tof")  # the base of N4
        project = design.Project(self.artifacts, None)
        self.assertEqual(design.candidate_geometry_kind(project, CANDIDATE), "tof")
        self.assertEqual(design.candidate_geometry_kinds(project, CANDIDATE), ["tof"])

    def test_a_derived_candidate_that_changes_the_kind_is_seen(self):
        self.set_kind("cand-N6", "tof")
        self.set_kind("cand-N4", "calorimeter")
        self.assertEqual(design.candidate_geometry_kinds(design.Project(self.artifacts, None), CANDIDATE), ["calorimeter", "tof"])

    def test_an_absent_kind_is_the_layered_spectrometer(self):
        self.assertEqual(design.candidate_geometry_kind(design.Project(self.artifacts, None), CANDIDATE), "layered-spectrometer")


if __name__ == "__main__":
    unittest.main()

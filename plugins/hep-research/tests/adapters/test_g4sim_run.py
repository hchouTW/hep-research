"""The g4sim_run driver: check-spec's three S2 checks, dataset control, the identities and the run record. Each check has a passing control in
the same test, so a refusal is caused by the defect and nothing else. No Geant4 here; live runs are in the S2 task card."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ASSETS = ROOT / "adapters/geant4/assets"
sys.path.insert(0, str(ASSETS))
spec = importlib.util.spec_from_file_location("g4sim_run_driver", ASSETS / "g4sim_run.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def card(**physics):
    return {"schema": "g4sim-run/1", "physics": {"cuts_mm": {"default": "0.7"}, "reference_list": "FTFP_BERT_EMZ", **physics},
            "accounting": "legacy", "run": {"events": 10, "mode": "mt", "seeding": "per-event"}}


def codes(findings):
    return [finding["code"] for finding in findings]


class CheckSpec(unittest.TestCase):
    def test_a_plain_card_passes(self):
        self.assertEqual(driver.check_card(card(), {"seeding": "per-event"}), [])

    def test_a_setting_that_calls_set_surface_tolerance_is_refused(self):
        document = card()
        document["ui_commands"] = ["/geometry/navigator/SetSurfaceTolerance 1e-9"]
        self.assertEqual(codes(driver.check_card(document)), ["surface-tolerance"])
        self.assertEqual(codes(driver.check_card(card(surface_tolerance_mm="1e-9"))), ["surface-tolerance"])
        document["ui_commands"] = ["/geometry/setWorldMaximumExtent 1000"]
        self.assertEqual(codes(driver.check_card(document)), ["surface-tolerance"])

    def test_an_optical_constructor_is_refused_before_s7(self):
        self.assertEqual(codes(driver.check_card(card(extra_constructors=["G4OpticalPhysics"]))), ["optical-before-s7"])
        self.assertEqual(driver.check_card(card(extra_constructors=["G4StepLimiterPhysics"])), [])

    def test_seeding_must_equal_the_legacy_block(self):
        self.assertEqual(codes(driver.check_card(card(), {"seeding": "stream"})), ["seeding-differs"])


class Datasets(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / "full").mkdir()
        (self.root / "full/data").write_text("x", encoding="utf-8")
        (self.root / "empty").mkdir()
        table = json.loads(driver.DATASETS.read_text(encoding="utf-8"))["physics_lists"]["FTFP_BERT_EMZ"]
        self.environment = {name: str(self.root / "full") for name in table}

    def test_all_present_passes(self):
        self.assertEqual(driver.missing_datasets(card(), self.environment), [])

    def test_a_dataset_the_installation_does_not_have_is_named(self):
        del self.environment["G4LEVELGAMMADATA"]
        self.assertEqual(driver.missing_datasets(card(), self.environment), ["G4LEVELGAMMADATA"])

    def test_an_empty_folder_counts_as_missing(self):
        self.environment["G4LEDATA"] = str(self.root / "empty")
        self.assertEqual(driver.missing_datasets(card(), self.environment), ["G4LEDATA"])

    def test_a_list_outside_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            driver.missing_datasets(card(reference_list="NOT_A_LIST"), self.environment)


class Identities(unittest.TestCase):
    def test_a_binary_float_is_hashed_as_its_decimal_string(self):
        self.assertEqual(driver.in_decimals({"a": [0.25, 1, "x"]}), {"a": ["0.25", 1, "x"]})

    def test_the_run_identity_follows_the_build_and_the_card(self):
        base = driver.run_id("a" * 64, "b" * 64, card(), "c" * 64)
        self.assertNotEqual(base, driver.run_id("a" * 64, "b" * 64, card(), "d" * 64))
        self.assertNotEqual(base, driver.run_id("a" * 64, "b" * 64, card(reference_list="QGSP_BIC_EMZ"), "c" * 64))
        self.assertNotEqual(driver.request_id({"x": 1}, "a" * 64), driver.request_id({"x": 1}, "b" * 64))


class TreeComparison(unittest.TestCase):
    """The write-back against the IR: placements, rotation convention, regions and each thread's fields."""

    def ir(self):
        node = {"region": "default", "field": "none"}
        return {"physical": {"templates": {"world": dict(node), "plate": {"region": "inner", "field": "solenoid"}},
                             "placements": [{"mother": "world", "template": "plate", "copy_number": 0, "centre_mm": ["1.5", "0", "0"],
                                             "rotation": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]}]}}

    def record(self):
        hexes = [value.hex() for value in (0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)]  # the object's rotation: the transpose
        return {"base": {"geometry": {"logical_volumes": [{"id": 0, "name": "world", "region": "DefaultRegionForTheWorld"},
                                                          {"id": 1, "name": "plate", "region": "inner"}],
                                      "placements": [{"name": "world", "copy_number": 0, "mother_logical": None, "translation_mm": [], "rotation": None},
                                                     {"name": "plate", "copy_number": 0, "mother_logical": 0, "rotation": hexes,
                                                      "translation_mm": [(1.5).hex(), (0.0).hex(), (0.0).hex()]}]}}}

    FIELDS = {"thread0": {"world": "none", "plate": "field"}}

    def test_a_faithful_write_back_passes(self):
        self.assertEqual(driver.tree_problems(self.ir(), self.record(), self.FIELDS), [])

    def test_the_other_rotation_convention_is_caught(self):
        record = self.record()
        record["base"]["geometry"]["placements"][1]["rotation"] = [value.hex() for value in (0.0, 1.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0)]
        self.assertIn("rotation differs", driver.tree_problems(self.ir(), record, self.FIELDS)[0])

    def test_a_field_set_only_on_the_mother_is_caught_on_every_thread(self):
        fields = {"thread0": {"world": "none", "plate": "none"}, "thread1": {"world": "none", "plate": "none"}}
        self.assertEqual(len(driver.tree_problems(self.ir(), self.record(), fields)), 2)

    def test_a_wrong_region_is_caught(self):
        record = self.record()
        record["base"]["geometry"]["logical_volumes"][1]["region"] = "other"
        self.assertIn("region other", driver.tree_problems(self.ir(), record, self.FIELDS)[0])

    def test_a_shifted_placement_is_caught_at_one_ulp(self):
        record = self.record()
        record["base"]["geometry"]["placements"][1]["translation_mm"][0] = (1.5000000000000002).hex()
        self.assertIn("translation differs", driver.tree_problems(self.ir(), record, self.FIELDS)[0])


class RunRecord(unittest.TestCase):
    RECORD = {"wall_seconds": 9.1, "cpu_seconds": 36.2, "startup_seconds": 3.1, "threads": 8, "load_at_start": 23.0}

    def test_a_complete_record_passes(self):
        self.assertEqual(driver.record_problems(self.RECORD), [])

    def test_a_record_without_a_time_is_refused(self):
        for field in driver.TIMING_FIELDS:
            broken = {key: value for key, value in self.RECORD.items() if key != field}
            self.assertEqual(driver.record_problems(broken), [f"run record lacks {field}"])


if __name__ == "__main__":
    unittest.main()

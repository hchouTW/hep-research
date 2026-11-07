"""The g4sim_run driver: check-spec's three S2 checks, dataset control, the identities and the run record. Each check has a passing control in
the same test, so a refusal is caused by the defect and nothing else. No Geant4 here; live runs are in the S2 task card."""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
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
        self.assertEqual(driver.identity.in_decimals({"a": [0.25, 1, "x"]}), {"a": ["0.25", 1, "x"]})

    def test_a_request_is_identified_by_what_it_selects(self):
        ir = {"marker": {"tags": {"block": ["active"], "plane": ["tracker"]}}}

        def identity_of(select, extra=None):
            request = {"schema": "simulation-request/1", "scorers": [{"name": "a", "quantity": "edep", "select": select, **(extra or {})}]}
            return driver.identity.request_id(driver.simulate_new.identified_request(request, ir), "a" * 64)

        self.assertEqual(identity_of({"tags": ["active"]}), identity_of({"templates": ["block"]}))
        self.assertNotEqual(identity_of({"tags": ["active"]}), identity_of({"tags": ["tracker"]}))
        self.assertNotEqual(identity_of({"tags": ["active"]}), identity_of({"tags": ["active"]}, {"level": "moments"}))

    def test_the_run_identity_follows_the_build_and_the_card(self):
        base = driver.run_id("a" * 64, "b" * 64, card(), "c" * 64)
        self.assertNotEqual(base, driver.run_id("a" * 64, "b" * 64, card(), "d" * 64))
        self.assertNotEqual(base, driver.run_id("a" * 64, "b" * 64, card(reference_list="QGSP_BIC_EMZ"), "c" * 64))
        self.assertNotEqual(driver.identity.request_id({"x": 1}, "a" * 64), driver.identity.request_id({"x": 1}, "b" * 64))


class TreeComparison(unittest.TestCase):
    """The write-back against the IR: placements, rotation convention, regions and each thread's fields."""

    def ir(self):
        node = {"shape": "box", "half_mm": ["1e1", "1e1", "1e1"], "region": "default", "field": "none"}
        return {"physical": {"templates": {"world": dict(node), "plate": {**node, "half_mm": ["1e0", "1e0", "1e0"], "region": "inner", "field": "solenoid"}},
                             "placements": [{"mother": "world", "template": "plate", "copy_number": 0, "centre_mm": ["1.5", "0", "0"],
                                             "rotation": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]}]}}

    def record(self):
        hexes = [value.hex() for value in (0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)]  # the object's rotation: the transpose
        def box(half):
            return {"type": "G4Box", "parameters": {key: half.hex() for key in ("half_x_mm", "half_y_mm", "half_z_mm")}}
        return {"base": {"geometry": {"logical_volumes": [{"id": 0, "name": "world", "region": "DefaultRegionForTheWorld", "solid": box(10.0)},
                                                          {"id": 1, "name": "plate", "region": "inner", "solid": box(1.0)}],
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


class OutputChecks(unittest.TestCase):
    """The negative tests of the column list, the material table and the overlap report."""

    MAP = {"columns": [{"column": "event", "file": "csv"}, {"column": "edep_MeV", "file": "csv"}, {"column": "hits", "file": "root"}]}

    def test_all_columns_present_passes(self):
        self.assertEqual(driver.missing_columns(self.MAP, "event,edep_MeV\n"), [])

    def test_a_deleted_column_is_named(self):
        self.assertEqual(driver.missing_columns(self.MAP, "event\n"), ["edep_MeV"])

    def record(self, symbol="Si", z=14.0, mass=28.0855):
        return {"base": {"geometry": {"materials": [{"name": "m", "elements": [{"symbol": symbol, "z": z.hex(), "a_g_mole": mass.hex()}]}]}}}

    def test_the_table_agrees_with_core_constants(self):
        self.assertEqual(driver.material_problems(self.record()), [])

    def test_a_swapped_elemental_constant_is_caught(self):
        def swapped(symbol):
            return {"Z": 14, "pdg_atomic_mass": "26.98(1)"}
        self.assertEqual(len(driver.material_problems(self.record(), swapped)), 1)

    def test_a_wrong_atomic_number_is_caught(self):
        self.assertEqual(len(driver.material_problems(self.record(z=13.0))), 1)

    def test_the_overlap_mark_is_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "log.txt"
            log.write_text("ok\nGeomVol1002 x\nGeomVol1002 y\n", encoding="utf-8")
            self.assertEqual(driver.overlaps_in_log(log), 2)


class SolidComparison(unittest.TestCase):
    """The solid Geant4 built against the IR."""

    def test_a_prism_given_its_circumradius_as_the_apothem_is_caught(self):
        node = {"shape": "polygon_prism", "solid": {"sides": 6, "circumradius_mm": "1e1"}}
        right = {"sides": 6, "corners_r_mm": [(0.0).hex(), (10.0).hex()]}
        wrong = {"sides": 6, "corners_r_mm": [(0.0).hex(), (11.547005383792516).hex()]}  # G4Polyhedra given R as rOuter: R / cos(pi / 6)
        self.assertEqual(driver.solid_problems({"name": "p", "solid": {"type": "G4Polyhedra"}}, node, right), [])
        self.assertEqual(len(driver.solid_problems({"name": "p", "solid": {"type": "G4Polyhedra"}}, node, wrong)), 1)

    def test_a_trd_length_off_by_one_ulp_is_caught(self):
        node = {"shape": "trd", "solid": {"dx1_mm": "5e0", "dx2_mm": "5e0", "dy1_mm": "5e0", "dy2_mm": "5e0", "dz_mm": "1e1"}}
        parameters = {key: (5.0).hex() for key in ("half_x1_mm", "half_x2_mm", "half_y1_mm", "half_y2_mm")}
        item = {"name": "t", "solid": {"type": "G4Trd", "parameters": {**parameters, "half_z_mm": (10.0).hex()}}}
        self.assertEqual(driver.solid_problems(item, node, None), [])
        item["solid"]["parameters"]["half_z_mm"] = (10.000000000000002).hex()
        self.assertEqual(driver.solid_problems(item, node, None), ["logical t: half_z_mm differs"])


    def test_a_box_of_the_wrong_size_is_caught(self):
        node = {"shape": "box", "half_mm": ["1e0", "2e0", "3e0"]}
        parameters = {"half_x_mm": (1.0).hex(), "half_y_mm": (2.0).hex(), "half_z_mm": (3.0).hex()}
        item = {"name": "b", "solid": {"type": "G4Box", "parameters": parameters}}
        self.assertEqual(driver.solid_problems(item, node, None), [])
        parameters["half_y_mm"] = (2.5).hex()
        self.assertEqual(driver.solid_problems(item, node, None), ["logical b: half_y_mm differs"])

    def test_a_tube_section_is_judged_by_its_angles(self):
        node = {"shape": "tube", "solid": {"rmin_mm": "0", "rmax_mm": "1e1", "dz_mm": "1e1", "phi_start_deg": "-9e1", "phi_span_deg": "1.8e2"}}
        parameters = {"rmin_mm": (0.0).hex(), "rmax_mm": (10.0).hex(), "half_z_mm": (10.0).hex(),
                      "start_phi_rad": (1.5 * math.pi).hex(), "delta_phi_rad": math.pi.hex()}  # G4Tubs holds -90 degrees as 270
        item = {"name": "t", "solid": {"type": "G4Tubs", "parameters": parameters}}
        self.assertEqual(driver.solid_problems(item, node, None), [])
        parameters["delta_phi_rad"] = math.tau.hex()
        self.assertEqual(driver.solid_problems(item, node, None), ["logical t: delta_phi_rad differs"])


class Dispatch(unittest.TestCase):
    """geant4_run.py by schema, and geant4_verify.py tree."""

    def script(self, name):
        return subprocess.run([sys.executable, "-B", str(ASSETS / name[0]), *name[1:]], capture_output=True, text=True, timeout=120, check=False)

    def test_check_spec_routes_a_run_card_to_its_own_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run.json"
            path.write_text(json.dumps(card(extra_constructors=["G4OpticalPhysics"])), encoding="utf-8")
            done = self.script(["geant4_run.py", "check-spec", "--spec", str(path)])
            self.assertEqual(json.loads(done.stdout)["status"], "rejected", done.stdout)
            self.assertIn("optical", done.stdout)
            path.write_text(json.dumps(card()), encoding="utf-8")
            self.assertEqual(json.loads(self.script(["geant4_run.py", "check-spec", "--spec", str(path)]).stdout)["status"], "ok")

    def test_tree_reports_a_difference(self):
        comparison = TreeComparison()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "ir.json").write_text(json.dumps(comparison.ir()), encoding="utf-8")
            (root / "probe-v2.json").write_text(json.dumps(comparison.record()), encoding="utf-8")
            (root / "field-managers.thread0.txt").write_text("world none none\nplate field solenoid\n", encoding="utf-8")
            arguments = ["geant4_verify.py", "tree", "--ir", str(root / "ir.json"), "--write-back", str(root / "probe-v2.json")]
            self.assertEqual(self.script(arguments).returncode, 0)
            (root / "field-managers.thread0.txt").write_text("world none none\nplate none solenoid\n", encoding="utf-8")
            self.assertEqual(self.script(arguments).returncode, 1)


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

"""The g4sim_run driver: check-spec's three S2 checks, dataset control, the identities and the run record. Each check has a passing control in
the same test, so a refusal is caused by the defect and nothing else. No Geant4 here; live runs are in the S2 task card."""
from __future__ import annotations

import importlib.util
import json
import math
import shutil
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

    def test_optical_physics_needs_the_optical_photon_class(self):
        # S7 lifts S2's rejection: G4OpticalPhysics with separated accounting, which holds the optical-photon class (Section 8.4)
        separated = card(extra_constructors=["G4OpticalPhysics"])
        separated["accounting"] = "separated"
        self.assertEqual(driver.check_card(separated), [])
        self.assertEqual(codes(driver.check_card(card(extra_constructors=["G4OpticalPhysics"]))), ["optical-class-missing"])
        self.assertEqual(codes(driver.check_card(separated, {"seeding": "per-event"})), ["optical-legacy"])
        self.assertEqual(driver.check_card(card(extra_constructors=["G4StepLimiterPhysics"])), [])

    def test_other_optical_routes_are_refused(self):
        self.assertEqual(codes(driver.check_card(card(extra_constructors=["G4OpticalPhysicsLegacy"]))), ["optical-constructor"])
        document = card()
        document["ui_commands"] = ["/process/optical/cerenkov/setMaxPhotons 10"]
        self.assertEqual(codes(driver.check_card(document)), ["optical-ui-command"])
        self.assertEqual(codes(driver.check_card(card(optical={"rayleigh": False}))), ["optical-without-constructor"])

    def test_a_new_mode_run_needs_optical_scope_and_knows_one_constructor(self):
        optical = card(extra_constructors=["G4OpticalPhysics"])
        scope = [{"need": "optical_scope", "templates": ["a"]}]
        self.assertEqual(driver.physics_check.optical_findings(optical, scope), [])
        self.assertEqual(codes(driver.physics_check.optical_findings(optical, [])), ["optical-no-scope"])
        self.assertEqual(codes(driver.physics_check.optical_findings(card(extra_constructors=["G4StepLimiterPhysics"]), [])), ["extra-constructor-unknown"])

    def test_seeding_must_equal_the_legacy_block(self):
        self.assertEqual(codes(driver.check_card(card(), {"seeding": "stream"})), ["seeding-differs"])


class Claims(unittest.TestCase):
    """A specification that cites claims runs only with the claims of the profiles it depends on (g4sim plan, Section 13.2)."""

    def test_a_cited_value_needs_its_claims(self):
        import tempfile, types
        case = Path(__file__).resolve().parents[2] / "profiles/reference/geometry-cases/cases/cms-ecal-barrel-crystal"
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / "run.json").write_text(json.dumps({"schema": "g4sim-run/1", "physics": {"reference_list": "NOT_A_LIST", "cuts_mm": {"default": "0.7"}}, "accounting": "separated", "run": {"events": 1, "first_event": 0, "logical_run_seed": 1, "mode": "mt", "seeding": "per-event", "threads": 1}}), encoding="utf-8")  # refused after the geometry check, so nothing runs
            claims = work / "claims.json"
            claims.write_text(json.dumps(["detector-atlas:C125", "detector-atlas:C130"]), encoding="utf-8")
            args = dict(detector=case / "detector-spec.json", request=case / "request.json", run=work / "run.json", program=work / "none", work=work / "out", protected=False)
            without = driver.simulate(types.SimpleNamespace(**args, claims=None))
            self.assertIn("facts-claim", {item["code"] for item in without["findings"]})
            with self.assertRaises(ValueError):  # past the geometry check, refused at the run card's physics list
                driver.simulate(types.SimpleNamespace(**args, claims=claims))


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
            return driver.identity.request_id(driver.identity.identified_request(request, ir), "a" * 64)

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


    # S7's shapes, read back from ProbeV2's curved_solids and polyhedra.
    CONE = {"shape": "cone", "solid": {"rmin1_mm": "2e0", "rmax1_mm": "1e1", "rmin2_mm": "3e0", "rmax2_mm": "2e1", "dz_mm": "1.5e1",
                                       "phi_start_deg": "1e1", "phi_span_deg": "3e2"}}
    SHELL = {"shape": "sphere_section", "solid": {"rmin_mm": "9e1", "rmax_mm": "1e2", "phi_start_deg": "0", "phi_span_deg": "3.6e2",
                                                  "theta_start_deg": "1e1", "theta_span_deg": "4e1"}}
    PCONE = {"shape": "polycone", "solid": {"z_mm": ["-1e1", "0", "1e1"], "rmin_mm": ["0", "1e0", "0"], "rmax_mm": ["5e0", "8e0", "5e0"],
                                            "phi_start_deg": "0", "phi_span_deg": "3.6e2"}}
    PHEDRA = {"shape": "polyhedra", "solid": {"sides": 6, "z_mm": ["-1e1", "1e1"], "circumradius_rmin_mm": ["2e0", "2e0"],
                                              "circumradius_rmax_mm": ["1e1", "1.2e1"]}}

    @staticmethod
    def cone_back(**change):
        held = {"logical": "c", "type": "G4Cons", "rmin1_mm": (2.0).hex(), "rmax1_mm": (10.0).hex(), "rmin2_mm": (3.0).hex(),
                "rmax2_mm": (20.0).hex(), "half_z_mm": (15.0).hex(), "start_phi_rad": math.radians(10).hex(), "delta_phi_rad": math.radians(300).hex()}
        return {**held, **change}

    def test_a_cone_read_back_as_built_passes_and_one_wrong_radius_is_caught(self):
        self.assertEqual(driver.solid_problems({"name": "c"}, self.CONE, None, self.cone_back()), [])
        self.assertEqual(driver.solid_problems({"name": "c"}, self.CONE, None, self.cone_back(rmax2_mm=(20.000000000000004).hex())),
                         ["logical c: rmax2_mm differs"])
        self.assertEqual(driver.solid_problems({"name": "c"}, self.CONE, None, self.cone_back(delta_phi_rad=math.radians(360).hex())),
                         ["logical c: delta_phi_rad differs"])

    def test_a_shape_with_no_read_back_is_an_error(self):
        self.assertEqual(driver.solid_problems({"name": "c"}, self.CONE, None, None), ["logical c: no G4Cons was written back"])
        self.assertEqual(driver.solid_problems({"name": "c"}, self.CONE, None, {**self.cone_back(), "type": "G4Tubs"}), ["logical c: no G4Cons was written back"])

    def test_a_sphere_section_is_judged_by_its_theta_range(self):
        held = {"logical": "s", "type": "G4Sphere", "rmin_mm": (90.0).hex(), "rmax_mm": (100.0).hex(), "start_phi_rad": (0.0).hex(),
                "delta_phi_rad": math.tau.hex(), "start_theta_rad": math.radians(10).hex(), "delta_theta_rad": math.radians(40).hex()}
        self.assertEqual(driver.solid_problems({"name": "s"}, self.SHELL, None, held), [])
        held["delta_theta_rad"] = math.radians(50).hex()
        self.assertEqual(driver.solid_problems({"name": "s"}, self.SHELL, None, held), ["logical s: delta_theta_rad differs"])

    def test_a_polycone_is_judged_by_its_corners(self):
        corners = [(0.0, 10.0), (1.0, 0.0), (0.0, -10.0), (5.0, -10.0), (8.0, 0.0), (5.0, 10.0)]  # as Geant4 wrote them back on build 20
        held = {"logical": "p", "type": "G4Polycone", "start_phi_rad": (0.0).hex(), "end_phi_rad": math.tau.hex(),
                "corners": [[r.hex(), z.hex()] for r, z in corners]}
        self.assertEqual(driver.solid_problems({"name": "p"}, self.PCONE, None, held), [])
        held["corners"][4] = [(7.0).hex(), (0.0).hex()]
        self.assertEqual(len(driver.solid_problems({"name": "p"}, self.PCONE, None, held)), 1)

    def test_a_polyhedra_given_its_circumradii_as_apothems_is_caught(self):
        right = {"sides": 6, "corners_r_mm": [value.hex() for value in (2.0, 2.0, 10.0, 12.0)]}
        stretch = 1 / math.cos(math.pi / 6)  # G4Polyhedra given R as its rOuter puts its corners at R / cos(pi / 6)
        wrong = {"sides": 6, "corners_r_mm": [(value * stretch).hex() for value in (2.0, 2.0, 10.0, 12.0)]}
        self.assertEqual(driver.solid_problems({"name": "h"}, self.PHEDRA, right), [])
        self.assertEqual(len(driver.solid_problems({"name": "h"}, self.PHEDRA, wrong)), 1)
        self.assertEqual(len(driver.solid_problems({"name": "h"}, self.PHEDRA, {**right, "sides": 8})), 1)


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


class FieldMapReadBack(unittest.TestCase):
    """Section 6.2.8 (S7): the map staged by its hash, and the field each thread gave at the sample points against this side's reading."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "tests/core"))
        from test_geometry_fieldmap import magnet_spec, map_text
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        map_bytes = map_text().encode()
        (self.folder / "m.txt").write_bytes(map_bytes)
        (self.folder / "spec.json").write_text(json.dumps(magnet_spec(driver.simulate_new.hashlib.sha256(map_bytes).hexdigest())), encoding="utf-8")
        self.checked = driver.geometry.check_file(self.folder / "spec.json")
        self.work = self.folder / "work"
        self.work.mkdir()
        self.staged = driver.simulate_new.stage_field_maps(self.checked, self.work)

    def answer(self, flip=1.0, thread="0"):
        """What a correct build writes: the field of the map at each global point, in the order of field-samples.txt."""
        rows = []
        for name, (parsed, points) in self.staged.items():
            for local, _ in points:
                rows.append(" ".join([name, *[(flip * value).hex() for value in driver.simulate_new.fieldmap.interpolate(parsed["grid"], parsed["values"], local)]]))
        (self.work / f"field-samples.thread{thread}.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_the_map_is_copied_and_sampled_in_world_coordinates(self):
        self.assertEqual((self.work / "field-map.magnet.txt").read_bytes(), (self.folder / "m.txt").read_bytes())
        lines = (self.work / "field-samples.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), driver.simulate_new.FIELD_SAMPLES)
        _, points = self.staged["magnet"]
        local, world = points[1]  # the bore is turned 90 degrees about z: local (x, y) lies at world (-y, x)
        self.assertEqual([round(value, 9) for value in world], [round(-local[1], 9), round(local[0], 9), round(local[2], 9)])

    def test_a_build_that_reads_the_map_passes(self):
        self.answer()
        self.answer(thread="-1")
        self.assertEqual(driver.simulate_new.field_sample_problems(self.staged, self.work), [])

    def test_a_flipped_field_is_caught(self):
        self.answer(flip=-1.0)
        self.assertEqual(len(driver.simulate_new.field_sample_problems(self.staged, self.work)), 1)

    def test_no_answer_is_an_error_and_an_old_answer_is_removed(self):
        self.assertEqual(driver.simulate_new.field_sample_problems(self.staged, self.work), ["no thread wrote the field at the sample points"])
        self.answer()
        driver.simulate_new.stage_field_maps(self.checked, self.work)
        self.assertEqual(list(self.work.glob("field-samples.thread*.txt")), [])

    def test_a_map_changed_after_check_spec_is_refused(self):
        (self.folder / "m.txt").write_bytes((self.folder / "m.txt").read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            driver.simulate_new.stage_field_maps(self.checked, self.work)


class OpticalReadBack(unittest.TestCase):
    """S7: the optical tables and surfaces Geant4 holds against the IR; a wrong refractive index is the negative test of Section 15.1."""

    IR = {"physical": {"templates": {"r": {"material": "glass"}}, "materials": {"glass": {"optical": {"rindex": {"energy_eV": ["1.5", "4"], "value": ["1.5", "1.52"]}}}},
                       "optical_surfaces": {"pc": {"skin": "r", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                                                   "efficiency": {"energy_eV": ["1.5", "4"], "value": ["0.25", "0.25"]}}}}}

    @staticmethod
    def spectrum(energies, values):
        return {"energy_eV": [value.hex() for value in energies], "value": [value.hex() for value in values]}

    def record(self, index=(1.5, 1.52), finish=0):
        return {"optical": {"materials": {"glass": {"RINDEX": self.spectrum((1.5, 4.0), index)}},
                            "surfaces": {"pc": {"skin": "r", "model": 1, "finish": finish, "type": 0, "sigma_alpha_rad": (0.0).hex(),
                                                "table": {"EFFICIENCY": self.spectrum((1.5, 4.0), (0.25, 0.25))}}}}}

    def test_tables_built_as_the_ir_says_pass(self):
        self.assertEqual(driver.optical_problems(self.IR, self.record()), [])

    def test_a_wrong_refractive_index_is_caught(self):
        self.assertEqual(driver.optical_problems(self.IR, self.record(index=(1.515, 1.5352))), ["material glass: RINDEX differs"])

    def test_a_wrong_finish_and_a_missing_table_are_caught(self):
        self.assertEqual(driver.optical_problems(self.IR, self.record(finish=3)), ["surface pc: finish differs"])
        record = self.record()
        del record["optical"]["materials"]["glass"]
        self.assertEqual(driver.optical_problems(self.IR, record), ["material glass: an optical table was not built"])

    def test_the_expected_table_is_what_the_builder_makes(self):
        material = {"optical": {"rindex": {"energy_eV": ["1", "2"], "value": ["1.5", "1.5"]}, "wls": {"absorption_length_mm": {"energy_eV": ["1", "2"], "value": ["1", "1"]},
                    "emission": {"energy_eV": ["1", "2"], "value": ["1", "0"]}, "time_constant_ns": "0.5"}},
                    "scintillation": {"yield_per_MeV": "8000", "resolution_scale": "1", "components": [{"fraction": "1", "spectrum": {"energy_eV": ["1", "2"], "value": ["1", "1"]}, "rise_ns": "0.9", "decay_ns": "2.1"}]}}
        self.assertEqual(sorted(driver.expected_optical_table(material)), ["RESOLUTIONSCALE", "RINDEX", "SCINTILLATIONCOMPONENT1", "SCINTILLATIONRISETIME1",
                         "SCINTILLATIONTIMECONSTANT1", "SCINTILLATIONYIELD", "SCINTILLATIONYIELD1", "WLSABSLENGTH", "WLSCOMPONENT", "WLSTIMECONSTANT"])


class ValidationRun(unittest.TestCase):
    """check-spec of a full optical validation run (Section 10.4): RESOLUTIONSCALE equal to r, saturation attached, by-particle-type off."""

    MATERIALS = {"lyso": {"scintillation": {"yield_per_MeV": "27000", "resolution_scale": "1.2"}, "ionisation": {"birks_mm_per_MeV": "0.008"}}}
    EFFECTIVE = {"optical": {"scintillation_saturation": True, "scintillation_by_particle_type": False}}

    def test_a_matching_validation_run_passes(self):
        self.assertEqual(driver.physics_check.validation_findings(card(extra_constructors=["G4OpticalPhysics"]), self.MATERIALS, "lyso", self.EFFECTIVE, 1.2), [])

    def test_a_validation_run_whose_resolutionscale_differs_from_r_is_caught(self):
        found = driver.physics_check.validation_findings(card(extra_constructors=["G4OpticalPhysics"]), self.MATERIALS, "lyso", self.EFFECTIVE, 1.0)
        self.assertEqual(codes(found), ["validation-resolution-scale"])

    def test_geant4_settings_read_back_are_judged(self):
        effective = {"optical": {"scintillation_saturation": False, "scintillation_by_particle_type": True}}
        self.assertEqual(codes(driver.physics_check.validation_findings(card(), self.MATERIALS, "lyso", effective, 1.2)),
                         ["validation-not-optical", "validation-saturation", "validation-by-particle-type"])


class EfficiencyMapTool(unittest.TestCase):
    """g4sim_efficiency_map.py build on a mapping run's files."""

    def test_a_map_is_built_from_the_run_files(self):
        tool = importlib.util.spec_from_file_location("g4sim_efficiency_map", ASSETS / "g4sim_efficiency_map.py")
        module = importlib.util.module_from_spec(tool)
        tool.loader.exec_module(module)
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work)
        component = {"fraction": "1", "spectrum": {"energy_eV": ["2", "3"], "value": ["1", "1"]}, "rise_ns": "0", "decay_ns": "2"}
        ir = {"physical": {"templates": {"world": {"shape": "box", "half_mm": ["5e2", "5e2", "5e2"], "material": "G4_AIR"},
                                         "bar": {"shape": "box", "half_mm": ["1e1", "1e1", "5e0"], "material": "scint"}},
                           "placements": [{"mother": "world", "template": "bar", "copy_number": 0, "centre_mm": ["1e2", "0", "0"], "rotation": None}],
                           "materials": {"scint": {"scintillation": {"yield_per_MeV": "1", "resolution_scale": "1", "components": [component]}}}}}
        (work / "ir.json").write_text(json.dumps(ir), encoding="utf-8")
        (work / "summary.json").write_text(json.dumps({"request_id": "r" * 64}), encoding="utf-8")
        draw = __import__("random").Random(3)
        primaries, photons = [], []
        for event in range(3000):
            x, y, z = 100 + draw.uniform(-10, 10), draw.uniform(-10, 10), draw.uniform(-5, 5)
            primaries.append(f"{event},3e-06,{x},{y},{z},0,0,1")
            if draw.random() < 0.1:
                photons.append(f"{event},pe,7,1.0,{draw.expovariate(1.0)},3,{x},{y},{z}")
        (work / "primaries.csv").write_text("\n".join(primaries) + "\n", encoding="utf-8")
        (work / "photons.csv").write_text("\n".join(photons) + "\n", encoding="utf-8")
        (work / "seg.json").write_text(json.dumps({"kind": "cartesian_xyz", "width_mm": ["10", "20", "10"]}), encoding="utf-8")
        code = module.main(["build", "--work", str(work), "--template", "bar", "--material", "scint", "--segmentation", str(work / "seg.json"), "--out", str(work / "map.json")])
        self.assertEqual(code, 0)
        document = json.loads((work / "map.json").read_text(encoding="utf-8"))
        self.assertEqual(document["channels"], ["pe/7"])
        self.assertEqual([row["emitted"] > 0 for row in document["form"]["bins"]], [True, True])
        self.assertEqual(sum(row["emitted"] for row in document["form"]["bins"]), 3000)
        self.assertAlmostEqual(sum(sum(row["detected"]) for row in document["form"]["bins"]) / 3000, 0.1, delta=0.02)


class TransitionRadiators(unittest.TestCase):
    """XTR rules 4 and 5 on the run card, with the Section 15.1 negatives: an irregular requirement paired with a regular-foil-stack class, and
    G4StrawTubeXTRadiator, which has no foil count (addendum 11.1); and the process read back after the run."""

    REQUIREMENTS = [{"need": "transition_radiation", "templates": ["radiator"], "structure": "irregular"}]

    @staticmethod
    def card_with(radiator_class, constructor=True):
        document = card(xtr=[{"envelope": "radiator", "radiator_class": radiator_class}])
        if constructor:
            document["physics"]["extra_constructors"] = ["g4sim_xtr"]
        return document

    def test_a_compatible_class_passes(self):
        self.assertEqual(driver.physics_check.radiator_findings(self.card_with("G4GammaXTRadiator"), self.REQUIREMENTS), [])

    def test_an_irregular_requirement_with_a_regular_class_is_refused(self):
        self.assertEqual(codes(driver.physics_check.radiator_findings(self.card_with("G4XTRRegularRadModel"), self.REQUIREMENTS)), ["xtr-incompatible"])

    def test_the_straw_tube_class_is_refused(self):
        self.assertEqual(codes(driver.physics_check.radiator_findings(self.card_with("G4StrawTubeXTRadiator"), self.REQUIREMENTS)), ["xtr-class-structureless"])

    def test_the_constructor_and_both_sides_must_be_there(self):
        self.assertEqual(codes(driver.physics_check.radiator_findings(self.card_with("G4GammaXTRadiator", constructor=False), self.REQUIREMENTS)), ["xtr-constructor"])
        self.assertEqual(codes(driver.physics_check.radiator_findings(card(extra_constructors=["g4sim_xtr"]), self.REQUIREMENTS)), ["xtr-class-missing"])
        self.assertEqual(codes(driver.physics_check.radiator_findings(self.card_with("G4GammaXTRadiator"), [])), ["xtr-requirement-missing"])
        self.assertEqual(codes(driver.physics_check.radiator_findings(self.card_with("G4MadeUpXTRadiator"), self.REQUIREMENTS)), ["xtr-class-unknown"])

    def test_the_process_is_read_back_on_the_named_particles_only(self):
        probe = {"processes": [{"particle": "e-", "registered": ["eIoni", "xtr_radiator"]}, {"particle": "e+", "registered": ["xtr_radiator"]},
                               {"particle": "mu-", "registered": ["muIoni"]}]}
        radiators = [{"envelope": "radiator", "radiator_class": "G4GammaXTRadiator"}]
        self.assertEqual(driver.simulate_new.radiator_process_problems(radiators, probe), [])
        self.assertEqual(driver.simulate_new.radiator_process_problems([{**radiators[0], "particles": ["e-"]}], probe), ["e+: xtr_radiator, which the card does not name"])
        self.assertEqual(driver.simulate_new.radiator_process_problems(radiators, {}), ["no process list was read back"])


if __name__ == "__main__":
    unittest.main()

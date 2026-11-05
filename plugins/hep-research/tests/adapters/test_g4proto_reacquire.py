"""The re-acquisition tool and the GB1 and GB22 judge: a correct synthetic record is confirmed, and each defect is refused. No
Geant4 here; live runs are recorded in the S1 task card."""
from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "adapters/geant4/tests/g4proto/reacquire"


def load(name):
    spec = importlib.util.spec_from_file_location(f"g4proto_reacquire_{name}", FOLDER / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


judge_module, apply_module = load("judge"), load("apply_probe")
IDENTITY = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


def record():
    placement = {"name": "layer", "copy_number": 2, "translation_mm": [(0.1).hex(), (0.0).hex(), (-3.5).hex()], "rotation": None}
    return {"recorded": True, "random_state_unchanged": True, "processes": [{"particle": "e-"}], "regions": [{"name": "r"}],
            "logical_fields": [{"logical": "layer", "source": "probe", "field_manager": 0}],
            "base": {"run_manager": {"class": "G4MTRunManager", "type": "master"}, "geometry": {"placements": [placement]}}}


def rows():
    return [{"name": "layer", "copy_number": 2, "translation": [0.1, 0.0, -3.5], "rotation": list(IDENTITY)}]


class Judge(unittest.TestCase):
    def status(self, probe=None, dump=None, before=b"state", after=b"state", multi_threaded=True, uninitialized=None):
        return judge_module.judge(probe or record(), rows() if dump is None else dump, before, after, multi_threaded,
                                  uninitialized)["status"]

    def test_a_correct_run_is_confirmed(self):
        self.assertEqual(self.status(uninitialized={"recorded": False}), "ok")

    def test_one_ulp_in_a_position_is_refused(self):
        dump = rows()
        dump[0]["translation"][0] = float.fromhex((0.1).hex()) + 2 ** -56
        self.assertEqual(self.status(dump=dump), "failed")

    def test_a_missing_placement_is_refused(self):
        self.assertEqual(self.status(dump=rows() + rows()), "failed")

    def test_a_changed_engine_state_is_refused(self):
        self.assertEqual(self.status(after=b"other"), "failed")

    def test_a_probe_that_reports_a_changed_state_is_refused(self):
        probe = record()
        probe["random_state_unchanged"] = False
        self.assertEqual(self.status(probe=probe), "failed")

    def test_an_unrecorded_run_is_refused(self):
        probe = record()
        probe["recorded"] = False
        self.assertEqual(self.status(probe=probe), "failed")

    def test_a_probe_that_records_after_initialize_is_refused(self):
        self.assertEqual(self.status(uninitialized={"recorded": True}), "failed")

    def test_a_declared_field_is_refused_only_for_a_multi_threaded_run(self):
        probe = copy.deepcopy(record())
        probe["logical_fields"][0]["source"] = "declared"
        self.assertEqual(self.status(probe=probe), "failed")
        self.assertEqual(self.status(probe=probe, multi_threaded=False), "ok")

    def test_a_serial_run_cannot_confirm_the_master_sees_the_field(self):
        probe = record()
        probe["base"]["run_manager"] = {"class": "G4RunManager", "type": "serial"}
        self.assertEqual(self.status(probe=probe), "failed")

    def test_negative_zero_equals_zero(self):
        dump = rows()
        dump[0]["translation"][1] = -0.0
        self.assertEqual(self.status(dump=dump), "ok")

    def test_a_volume_name_with_spaces_is_read(self):
        numbers = " ".join((1.0).hex() for _ in range(12))
        self.assertEqual(judge_module.store_rows(f"a b 3 {numbers}")[0]["name"], "a b")


class ApplyProbe(unittest.TestCase):
    def test_each_old_program_gets_one_call_and_the_plugin_stays_as_it_was(self):
        assets = ROOT / "adapters/geant4/assets"
        for program in ("layered_sim", "element_sim"):
            before = (assets / program / "Actions.cc").read_bytes()
            with self.subTest(program=program), tempfile.TemporaryDirectory() as folder:
                apply_module.apply(program, assets, Path(folder))
                text = Path(folder, program, "Actions.cc").read_text(encoding="utf-8")
                self.assertEqual(text.count("g4proto::Record("), 1)
                self.assertTrue(Path(folder, "g4sim", "ProbeV2.hh").exists())
                self.assertTrue(Path(folder, "simroot", "simroot.cc").exists())
                self.assertEqual((assets / program / "Actions.cc").read_bytes(), before)

    def test_a_source_with_no_call_site_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            assets = Path(folder, "assets")
            (assets / "layered_sim").mkdir(parents=True)
            (assets / "g4sim").mkdir()
            (assets / "layered_sim" / "Actions.cc").write_text("// old source\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                apply_module.apply("layered_sim", assets, Path(folder, "out"))


if __name__ == "__main__":
    unittest.main()

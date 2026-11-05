"""The re-acquisition tool and the GB1 and GB22 judge: a correct synthetic record is confirmed, and each defect is refused. No
Geant4 here; live runs are recorded in the S1 task card."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def old_source(self, folder, actions):
        assets = Path(folder, "assets")
        (assets / "layered_sim").mkdir(parents=True)
        (assets / "layered_sim" / "Actions.cc").write_text(actions, encoding="utf-8")
        (assets / "layered_sim" / "CMakeLists.txt").write_text("add_executable(layered_sim a.cc)\n", encoding="utf-8")
        return assets

    def test_a_source_with_no_call_site_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                apply_module.apply("layered_sim", self.old_source(folder, '#include "Actions.hh"\n// old source\n'), Path(folder, "out"))

    def test_a_source_before_the_probe_gets_a_master_only_call_and_the_headers(self):
        actions = '#include "Actions.hh"\nvoid RunAction::BeginOfRunAction(const G4Run*) {\n  bool mt = true;\n}\n'
        with tempfile.TemporaryDirectory() as folder:
            apply_module.apply("layered_sim", self.old_source(folder, actions), Path(folder, "out"))
            text = Path(folder, "out", "layered_sim", "Actions.cc").read_text(encoding="utf-8")
            self.assertIn('if (G4Threading::IsMasterThread()) g4proto::Record("layered_sim");', text)
            self.assertTrue(Path(folder, "out", "g4sim", "SimProbe.hh").exists())
            self.assertIn("../g4sim", Path(folder, "out", "layered_sim", "CMakeLists.txt").read_text(encoding="utf-8"))


class Reproduction(unittest.TestCase):
    module = load("reproduce")

    def test_the_column_file_and_the_summary_must_be_identical(self):
        self.assertTrue(self.module.reproduced({"events.csv": "same", "column_map.json": "different"}))
        self.assertFalse(self.module.reproduced({"events.csv": "different"}))
        self.assertFalse(self.module.reproduced({"events.csv": "same", "summary.json": "different"}))
        self.assertFalse(self.module.reproduced({"events.csv": "missing"}))

    def test_nothing_compared_is_not_reproduced(self):
        self.assertFalse(self.module.reproduced({"column_map.json": "same"}))

    def test_one_ulp_in_an_existing_probe_record_is_caught(self):
        geometry = {"placements": [{"translation_mm": [(0.1).hex()]}]}
        moved = copy.deepcopy(geometry)
        moved["placements"][0]["translation_mm"][0] = (0.1 + 2 ** -56).hex()
        self.assertTrue(self.module.probe_agrees({"geometry": geometry}, {"base": {"geometry": copy.deepcopy(geometry)}}))
        self.assertFalse(self.module.probe_agrees({"geometry": moved}, {"base": {"geometry": geometry}}))
        self.assertIsNone(self.module.probe_agrees(None, {"base": {"geometry": geometry}}))

    def test_a_declared_field_or_an_unrecorded_run_is_not_visible(self):
        self.assertTrue(self.module.field_visible({"recorded": True, "logical_fields": [{"source": "probe"}]}))
        self.assertFalse(self.module.field_visible({"recorded": True, "logical_fields": [{"source": "declared"}]}))
        self.assertFalse(self.module.field_visible({"recorded": False}))

    def test_outputs_are_compared_by_hash_and_others_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "events.csv").write_text("1\n", encoding="utf-8")
            digest = hashlib.sha256(b"1\n").hexdigest()
            row = {"outputs": {"r/events.csv": digest, "r/summary.json": digest, "r/log.txt": digest}}
            self.assertEqual(self.module.output_states(row, Path(folder)), {"events.csv": "same", "summary.json": "missing"})

    def test_a_field_region_is_declared_for_the_hook(self):
        self.assertEqual(self.module.declared_fields({"field": {"regions": [{"element": "A"}, {"element": "B"}]}}), "A,B")
        self.assertEqual(self.module.declared_fields({}), "")


class Completion(unittest.TestCase):
    module = Reproduction.module

    def recorded(self):
        run = {key: "added" for key in self.module.COMPLETED_KEYS}
        return {"observables": [{"sum": 1.5}], "merge": {}, "run": {"events": 4000, **run}, "summary_version": "1"}

    def rerun(self):
        return {"observables": [{"sum": 1.5}], "merge": {}, "run": {"events": 4000}, "summary_version": "1"}

    def test_the_wrapper_keys_alone_are_taken_out(self):
        self.assertTrue(self.module.same_before_completion(self.rerun(), self.recorded()))
        self.assertTrue(self.module.reproduced({"events.csv": "same", "summary.json": self.module.SAME_BEFORE_COMPLETION}))

    def test_one_changed_number_is_still_a_difference(self):
        rerun = self.rerun()
        rerun["observables"][0]["sum"] = math.nextafter(1.5, 2.0)
        self.assertFalse(self.module.same_before_completion(rerun, self.recorded()))

    def test_a_changed_key_in_the_run_block_is_still_a_difference(self):
        rerun = self.rerun()
        rerun["run"]["events"] = 3999
        self.assertFalse(self.module.same_before_completion(rerun, self.recorded()))

    def test_a_recorded_file_without_those_keys_is_not_excused(self):
        recorded = self.recorded()
        del recorded["run"]["completed_by"]
        self.assertFalse(self.module.same_before_completion(self.rerun(), recorded))

    def test_a_rerun_holding_a_wrapper_key_is_not_excused(self):
        rerun = self.rerun()
        rerun["run"]["run_id"] = "added"
        self.assertFalse(self.module.same_before_completion(rerun, self.recorded()))


class Rebuild(unittest.TestCase):
    module = Reproduction.module
    row = {"program": "element_sim", "source_commit": "abc"}

    def test_an_earlier_build_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            built = Path(folder, "build", "element_sim")
            built.parent.mkdir()
            built.write_text("binary", encoding="utf-8")
            with mock.patch.object(self.module.sampler, "extract", side_effect=AssertionError("must not rebuild")):
                self.assertEqual(self.module.prepare(self.row, Path(folder), None), built)

    def test_a_partial_build_is_cleared_first(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder, "commit")
            (work / "src").mkdir(parents=True)
            (work / "src" / "left.cc").write_text("old", encoding="utf-8")
            seen = []

            def extract(commit, target):
                seen.append((work / "src").exists())
                return target

            with mock.patch.object(self.module.sampler, "extract", extract), \
                 mock.patch.object(self.module.sampler.apply_probe, "apply", return_value=work), \
                 mock.patch.object(self.module.sampler, "build", return_value=work / "element_sim"):
                self.module.prepare(self.row, work, None)
            self.assertEqual(seen, [False])


class Status(unittest.TestCase):
    def test_status_counts_runs_and_adds_up_wall_time(self):
        module = Reproduction.module
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "status.json")
            results = {"a": {"reproduced": True, "wall_seconds": 60.0}, "b": {"reproduced": False, "wall_seconds": 30.5}}
            module.write_status(path, 5, results, "c", "start")
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((document["done"], document["total"], document["reproduced"]), (2, 5, 1))
            self.assertEqual((document["current"], document["wall_seconds"]), ("c", 90.5))
            self.assertEqual(list(Path(folder).iterdir()), [path])


class CostSample(unittest.TestCase):
    module = load("cost_sample")

    def test_a_clear_difference_gives_seconds_per_event(self):
        timing = self.module.per_event(lambda n: 2.0 + 0.01 * n, 1000)
        self.assertTrue(timing["reliable"])
        self.assertAlmostEqual(timing["seconds_per_event"], 0.01)

    def test_a_small_difference_grows_the_sample(self):
        seen = []
        def measure(n):
            seen.append(n)
            return 2.0 + 0.001 * n
        timing = self.module.per_event(measure, 100)
        self.assertGreater(timing["sample_events"], 100)
        self.assertAlmostEqual(timing["seconds_per_event"], 0.001)

    def test_noise_is_reported_as_unreliable_never_as_a_small_cost(self):
        timing = self.module.per_event(lambda n: 6.0, 100)
        self.assertFalse(timing["reliable"])
        self.assertIsNone(timing["seconds_per_event"])

    def test_a_faster_long_run_is_not_a_zero_cost(self):
        answers = iter([6.6, 6.0] * 20)
        self.assertFalse(self.module.per_event(lambda n: next(answers), 100)["reliable"])

    def test_the_slowest_rate_prices_the_whole_executable(self):
        timings = [{"reliable": True, "seconds_per_event": 0.001}, {"reliable": True, "seconds_per_event": 0.5},
                   {"reliable": False, "seconds_per_event": None}]
        self.assertEqual(self.module.priced(timings, 7200)["estimated_hours"], 1.0)

    def test_no_reliable_rate_gives_no_estimate(self):
        self.assertIsNone(self.module.priced([{"reliable": False, "seconds_per_event": None}], 100)["estimated_hours"])

    def test_three_runs_are_timed_and_a_short_list_has_no_repeats(self):
        rows = [{"run": name, "events": events} for name, events in (("a", 5), ("b", 1), ("c", 9), ("d", 3))]
        self.assertEqual({row["run"] for row in self.module.chosen(rows)}, {"c", "a", "b"})
        self.assertEqual(len(self.module.chosen(rows[:1])), 1)

    def test_a_spec_is_chosen_by_its_hash_not_its_name(self):
        rows = [row for row in self.module.inventory.collect(ROOT) if row["journey"] == "J14"]
        self.assertTrue(all("schema" in self.module.spec_of(row) for row in rows))


class Baseline(unittest.TestCase):
    """The working baselines: longest runs first, cores shared by threads, and no folder mixes two environments."""

    def setUp(self):
        sys.path.insert(0, str(FOLDER))
        self.addCleanup(sys.path.remove, str(FOLDER))
        self.module = load("baseline")

    def test_longest_first_by_work_per_core(self):
        rows = [{"run": "mt", "events": 800, "threads": 8}, {"run": "serial", "events": 200, "threads": 1}, {"run": "tiny", "events": 1}]
        self.assertEqual([row["run"] for row in self.module.order(rows)], ["serial", "mt", "tiny"])

    def test_a_run_never_takes_more_cores_than_there_are(self):
        cores = self.module.Cores(4)
        self.assertEqual(cores.take(8), 4)
        self.assertEqual(cores.free, 0)
        cores.give(4)
        self.assertEqual(cores.free, 4)

    def test_a_folder_of_another_environment_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / "facts.json").write_text("[]", encoding="utf-8")
            (work / "baselines.json").write_text(json.dumps({"environment": {"platform": "other"}, "runs": {}}), encoding="utf-8")
            with mock.patch.object(self.module, "environment_record", return_value={"platform": "this"}), \
                    mock.patch("builtins.print") as printed:
                code = self.module.main(["--facts", str(work / "facts.json"), "--work", str(work), "--geant4-config", "unused"])
            self.assertEqual(code, 2)
            self.assertIn("another environment", printed.call_args.args[0])


class G5Scan(unittest.TestCase):
    spec = importlib.util.spec_from_file_location("g5_scan", FOLDER.parent / "g5_scan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = "int a = 1;\nint b = 2;\nint c = 3;\nint d = 4;\nint e = 5;\n"

    def test_comments_whitespace_and_trivial_lines_do_not_count(self):
        text = '#include "x.hh"\n// note\n{\n  int   a = 1; // why\n/* block\n*/\n}\n'
        self.assertEqual(self.module.normalized(text), ["inta=1;"])

    def run_scan(self, new_text):
        with tempfile.TemporaryDirectory() as folder:
            examples = Path(folder, "examples")
            examples.mkdir()
            (examples / "a.cc").write_text(self.code, encoding="utf-8")
            candidate = Path(folder, "candidate.hh")
            candidate.write_text(new_text, encoding="utf-8")
            return self.module.main(["--examples", str(examples), str(candidate)])

    def test_new_code_passes(self):
        self.assertEqual(self.run_scan("double x = 9;\ndouble y = 8;\ndouble z = 7;\n"), 0)

    def test_a_reformatted_copy_is_found(self):
        self.assertEqual(self.run_scan(self.module.reformatted(self.code)), 1)

    def test_an_empty_tree_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder, "candidate.hh")
            candidate.write_text("int a;\n", encoding="utf-8")
            self.assertEqual(self.module.main(["--examples", folder + "/none", str(candidate)]), 2)


if __name__ == "__main__":
    unittest.main()

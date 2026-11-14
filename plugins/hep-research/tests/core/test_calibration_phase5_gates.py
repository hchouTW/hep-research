"""The phase-5 gate harness (tests/core/calibration_phase5_gates.py): its judging rules on recorded outcomes, the static
diff and registry comparison, the rerun dispatcher (dry: files only, nothing submitted) and merge judge, and the
byte-identity comparison with its mask. Each negative with a positive control."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase5_gates as G  # noqa: E402


class Negatives(unittest.TestCase):
    KINDS = {"m.C.test_neg": "negative", "m.C.test_pos": "positive"}

    def test_all_passing_passes_and_marks_negatives_caught(self):
        j = G.judge_tests("x", "p", self.KINDS, {"m.C.test_neg": {"outcome": "passed"},
                                                  "m.C.test_pos": {"outcome": "passed"}})
        self.assertTrue(j["passed"])
        self.assertEqual({r["test"]: r["status"] for r in j["tests"]}, {"m.C.test_neg": "caught", "m.C.test_pos": "passed"})

    def test_a_failure_a_skip_an_error_or_a_test_not_run_fails(self):
        for outs in ({"m.C.test_neg": {"outcome": "failed"}, "m.C.test_pos": {"outcome": "passed"}},
                     {"m.C.test_neg": {"outcome": "skipped"}, "m.C.test_pos": {"outcome": "passed"}},
                     {"m.C.test_neg": {"outcome": "error"}, "m.C.test_pos": {"outcome": "passed"}},
                     {"m.C.test_pos": {"outcome": "passed"}}):
            with self.subTest(outs=sorted(outs)):
                self.assertFalse(G.judge_tests("x", "p", self.KINDS, outs)["passed"])

    def test_an_empty_list_fails(self):
        j = G.judge_tests("G4L", "p", {}, {})
        self.assertEqual((j["passed"], j["status"]), (False, "lists-not-filled"))

    def test_an_unloadable_name_fails(self):
        outs = G.run_tests(["test_calibration_phase5_gates.Negatives.test_does_not_exist"])
        self.assertFalse(G.judge_tests("x", "p", {"test_calibration_phase5_gates.Negatives.test_does_not_exist":
                                                  "negative"}, outs)["passed"])

    def test_tests_are_grouped_by_module(self):
        self.assertEqual(G._module("tests.contracts.test_calibration_schemas"), "tests.contracts.test_calibration_schemas")
        self.assertEqual(G._module(G.SCRIPTS + "Phase1Scripts.test_x"), "tests.skills.test_calib_scripts")
        self.assertEqual(G._module("test_calibration_design.P5"), "test_calibration_design")

    def test_every_listed_name_loads(self):
        """The negatives lists (while filled) and the earlier unit-test lists of item 3: every name loads."""
        loader = unittest.TestLoader()
        names = [n for _, kinds in G.NEGATIVES.values() for n in kinds] + \
                [n for _, kinds in G.UNIT_LISTS.values() for n in kinds]
        for name in names:
            with self.subTest(name=name):
                self.assertGreater(loader.loadTestsFromName(name).countTestCases(), 0)


class Static(unittest.TestCase):
    ENTRY = {"card": "simcal-tasks/phase-2.md", "sha256": "a" * 64, "reason": "r"}

    def test_unchanged_passes(self):
        self.assertTrue(G.judge_static(["plugins/hep-research/core/calibration/fit.py"], [self.ENTRY],
                                       [dict(self.ENTRY)])["passed"])

    def test_a_protected_file_or_a_changed_registry_entry_fails(self):
        self.assertFalse(G.judge_static([G.PROTECTED[0]], [self.ENTRY], [self.ENTRY])["passed"])
        self.assertFalse(G.judge_static([], [self.ENTRY], [dict(self.ENTRY, reason="edited")])["passed"])
        self.assertFalse(G.judge_static([], [self.ENTRY], [])["passed"])

    def test_registry_selection_keeps_phase_0_to_4_only(self):
        reg = {"registrations": [self.ENTRY, {"card": "simcal-tasks/phase-5.md"}]}
        self.assertEqual(G.prior_registry_entries(reg), [self.ENTRY])

    def test_protected_paths_are_repository_relative(self):
        self.assertEqual(len(G.PROTECTED), 15)
        self.assertTrue(all(p.startswith("plugins/hep-research/") for p in G.PROTECTED))
        for p in G.PROTECTED:
            self.assertTrue((ROOT.parents[1] / p).is_file(), p)

    def test_static_item_at_this_commit(self):
        """This branch (base plus the phase-5 work) leaves every protected file and registry entry unchanged."""
        r = G.static_item()
        self.assertTrue(r["passed"], r)


class Rerun(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.work_dir.name)

    def tearDown(self):
        self.work_dir.cleanup()

    def test_dispatch_writes_scripts_and_submits_nothing(self):
        man = G.dispatch(self.d, "0" * 40, "/wt")
        self.assertFalse(man["submitted"])
        for f in ("p0.sbatch", "misc.sbatch", "p2g1.sbatch", "p3.sbatch", "submit.sh", "login.sh", "dispatch.json"):
            self.assertTrue((self.d / f).is_file(), f)
        p0 = (self.d / "p0.sbatch").read_text()
        self.assertIn("--array=0-68", p0)
        self.assertIn("calibration_exhaustive.py --item", p0)
        self.assertIn("--array=0-32", (self.d / "p2g1.sbatch").read_text())
        p3 = (self.d / "p3.sbatch").read_text()
        self.assertIn("SIMCAL_G4_PRODUCTS=" + G.G4_PRODUCTS, p3)
        submit = (self.d / "submit.sh").read_text()
        self.assertIn("sbatch --array=0-9 --mem=8000M p3.sbatch 27164", submit)
        self.assertIn("sbatch --array=0-15,123 --mem=8000M p3.sbatch", submit)
        misc = (self.d / "misc.sbatch").read_text()
        for cmd in ("calibration_phase1_gates.py --gate agreement", "calibration_phase2_gates.py --gate segmented",
                    "calibration_phase2_gates.py --gate shift"):
            self.assertIn(cmd, misc)
        self.assertIn("calibration_phase4_gates.py --run", (self.d / "login.sh").read_text())
        with self.assertRaises(ValueError):
            G.dispatch(self.d, "abc", "/wt")

    def test_the_registered_sizes_match_the_earlier_harnesses(self):
        import calibration_exhaustive as EX
        import calibration_phase2_gates as P2G
        self.assertEqual(len(EX.GATE_SHARDS), G.P0_ITEMS)
        self.assertEqual(len(P2G.GATE1T_TASKS), G.P2_GATE1_TASKS)
        import calibration_phase3_gates as P3G
        self.assertEqual(P3G.TASKS[27164][0], "zdc_fit_g4")
        self.assertEqual(len(P3G.TASKS), 27174)

    def test_judge_rerun(self):
        good = {"a": {"ok": True, "commits": ["c" * 40], "dirty": False}}
        self.assertTrue(G.judge_rerun(good, "c" * 40)["passed"])
        self.assertFalse(G.judge_rerun({"a": dict(good["a"], ok=False)}, "c" * 40)["passed"])
        self.assertFalse(G.judge_rerun(good, "d" * 40)["passed"])                 # another commit
        self.assertFalse(G.judge_rerun({"a": dict(good["a"], dirty=True)}, "c" * 40)["passed"])
        self.assertFalse(G.judge_rerun({}, "c" * 40)["passed"])

    def test_merge_of_an_empty_campaign_fails(self):
        G.dispatch(self.d, "0" * 40, "/wt")
        r = G.merge_rerun(self.d)
        self.assertFalse(r["passed"])
        self.assertEqual(set(r["items"]), {"p0_appendix_c", "p0_named", "p0_fixtures", "p1_gate1", "p1_gate2",
                                           "p2_gate1", "p2_gate2", "p2_gate3", "p3_gate_e", "p4_gate"})
        self.assertTrue(all(not v["passed"] for v in r["items"].values()))

    def test_p0_clean_status_from_the_guard_lines(self):
        """A33 (review F11): p0_appendix_c reads the clean status from the jobs' guard lines (the p0 records carry no
        dirty flag). Positive: a start line for every item at the commit. Negatives: a "worktree dirty" log, a missing
        item, another commit; and merge_rerun marks the item dirty without logs."""
        c = "ab" * 20
        logs = self.d / "logs"
        logs.mkdir()

        def write(i, text):
            (logs / f"task_1_{i}.log").write_text(text)
        for i in range(3):
            write(i, f"host n1 commit {c[:8]} task {i} start 2026-11-14T00:00:00+00:00\nend x\n")
        self.assertTrue(G.p0_guard(logs, c, 3)["clean"])
        self.assertFalse(G.p0_guard(logs, c, 4)["clean"])                         # item 3 has no log
        self.assertFalse(G.p0_guard(logs, "cd" * 20, 3)["clean"])                 # another commit
        write(3, "worktree dirty\n")
        self.assertFalse(G.p0_guard(logs, c, 3)["clean"])                         # a guard failure
        G.dispatch(self.d, "0" * 40, "/wt")
        self.assertTrue(G.merge_rerun(self.d)["items"]["p0_appendix_c"]["dirty"])

    def test_numeric_differences_are_reported(self):
        d = G.numeric_diff({"a": 1.0, "b": [1, 2], "seconds": 3, "s": "x"}, {"a": 1.5, "b": [1, 2], "seconds": 9})
        self.assertEqual(d, [("/a", 1.0, 1.5)])


class Identity(unittest.TestCase):
    def test_mask_hides_only_the_listed_fields(self):
        a = '{\n "status": "ok",\n "commit": "abc",\n "value": 1.5\n}'
        b = '{\n "status": "ok",\n "commit": "def",\n "value": 1.5\n}'
        self.assertEqual(G.mask(a, ("commit",)), G.mask(b, ("commit",)))
        self.assertNotEqual(G.mask(a, ("commit",)), G.mask(a.replace("1.5", "1.50000001"), ("commit",)))
        self.assertEqual(G.mask(a, ()), a)                      # the registered list is empty: byte identity
        self.assertEqual(G.MASKED_KEYS, ())

    def test_compare_case(self):
        g = {"returncode": 0, "stdout": '{"x": 1}\n', "outputs": {"o.json": "1"}}
        self.assertTrue(G.compare_case(g, dict(g))["identical"])
        self.assertEqual(G.compare_case(g, dict(g, returncode=1))["differs"], ["returncode"])
        self.assertEqual(G.compare_case(g, dict(g, stdout='{"x": 1} \n'))["differs"], ["stdout"])  # one byte
        self.assertEqual(G.compare_case(g, dict(g, outputs={"o.json": "2"}))["differs"], ["outputs/o.json"])

    def test_golden_file_covers_the_registered_set(self):
        doc = json.loads(G.GOLDEN.read_text())
        self.assertEqual(doc["phase_base"], G.PHASE_BASE)
        cases = doc["cases"]
        scripts = {c["script"] for c in cases.values() if c["kind"] == "cli"}
        for s in ("calib_contract.py", "calib_chain.py", "calib_design.py", "calib_kernel_check.py", "calib_fit.py",
                  "calib_identify.py", "calib_closure.py", "calib_validate.py", "calib_propagate.py",
                  "calib_use.py", "calib_deps.py", "calib_contrib.py", "calib_emulator.py", "calib_reweight.py"):
            self.assertIn(s, scripts)
        self.assertTrue(any(c["kind"] == "engine" for c in cases.values()))

    def test_a_fast_subset_is_identical_now_and_a_changed_golden_is_caught(self):
        """Positive: three fast cases reproduce their golden bytes. Negative: the same cases against a golden with
        one changed byte differ, and only that case."""
        fast = ["closure_nc", "fit_kstar", "engine_g4_weights"]
        doc = json.loads(G.GOLDEN.read_text())
        if G.environment() != doc["environment"]:
            self.skipTest("interpreter differs from the capture (the comparison is then incomplete, not judged)")
        r = G.identity_item(cases=fast)
        self.assertTrue(r["passed"], r["cases"])
        bad = json.loads(json.dumps(doc))
        g = bad["cases"]["closure_nc"]["golden"]
        g["stdout"] = g["stdout"].replace("99", "98", 1)
        with tempfile.TemporaryDirectory() as work_dir:
            p = Path(work_dir) / "g.json"
            p.write_text(json.dumps(bad))
            r2 = G.identity_item(path=p, cases=fast)
        self.assertFalse(r2["passed"])
        self.assertEqual(r2["differing"], ["closure_nc"])

    def test_base_tree_cases(self):
        """A33 (review F3): the p5base_* cases, captured by running their case file against a git archive of the
        phase-5 base. Positive: a fast one reproduces its golden at this tree. Negatives: a changed golden byte, and a
        case file whose SHA-256 differs from the capture's, are caught."""
        doc = json.loads(G.GOLDEN.read_text())
        names = sorted(k for k in doc["cases"] if k.startswith(G.TREE_PREFIX))
        self.assertEqual(names, sorted(G.TREE_PREFIX + n for n in G._tree_case_names()))
        self.assertEqual({doc["cases"][n]["captured_against"] for n in names},
                         {doc["base_cases"]["captured_against"]})
        self.assertTrue(doc["base_cases"]["captured_against"].startswith(G.PHASE_BASE))
        if G.environment() != doc["environment"]:
            self.skipTest("interpreter differs from the capture (the comparison is then incomplete, not judged)")
        fast = [G.TREE_PREFIX + "evaluator_problem_standin"]
        self.assertTrue(G.identity_item(cases=fast)["passed"])
        for change in ("golden", "code"):
            bad = json.loads(json.dumps(doc))
            case = bad["cases"][fast[0]]
            if change == "golden":
                case["golden"]["output"] = case["golden"]["output"].replace("1", "2", 1)
            else:
                case["case_code_sha256"] = "0" * 64
            with tempfile.TemporaryDirectory() as work_dir:
                p = Path(work_dir) / "g.json"
                p.write_text(json.dumps(bad))
                r = G.identity_item(path=p, cases=fast)
            self.assertEqual((r["passed"], r["differing"]), (False, fast), change)

    def test_environment_mismatch_is_incomplete(self):
        doc = json.loads(G.GOLDEN.read_text())
        doc["environment"] = dict(doc["environment"], numpy="0.0")
        with tempfile.TemporaryDirectory() as work_dir:
            p = Path(work_dir) / "g.json"
            p.write_text(json.dumps(doc))
            r = G.identity_item(path=p, cases=["fit_kstar"])
        self.assertEqual((r["passed"], r["status"]), (False, "incomplete"))

    def test_a_missing_golden_fails(self):
        r = G.identity_item(path=Path("/nonexistent/g.json"))
        self.assertEqual((r["passed"], r["status"]), (False, "missing-golden"))


if __name__ == "__main__":
    unittest.main()

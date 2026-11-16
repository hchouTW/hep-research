"""The phase-5 gate harness (tests/core/simcal_phase5_gates.py): its judging rules on recorded outcomes, the static
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

import simcal_phase5_gates as G  # noqa: E402

REPO = ROOT.parents[1]
# The static item reads the repository: the plugin folder at <repo>/plugins/hep-research next to a .git, with the
# phase-5 base reachable. A relocated copy (tools/check_ams_optional.py) or a shallow CI checkout skips those tests;
# the gate itself runs them at the gate commit.
IN_REPO = (REPO / ".git").exists() and ROOT == (REPO / "plugins" / "hep-research").resolve()


# The simcal rename (0.70.0, docs/dev/simcal-naming-map.md) moved the protected harness files and the identity-case file
# and substituted names in them, by design. Since then the two tests below check that each such file is its phase-5
# original with names substituted only: `old_names` reverses the name map of those files exactly.
RENAMED_PROTECTED = {"plugins/hep-research/tests/core/simcal_exhaustive.py": "tests/core/calibration_exhaustive.py",
                     **{f"plugins/hep-research/tests/core/simcal_phase{k}_gates.py":
                        f"tests/core/calibration_phase{k}_gates.py" for k in (1, 2, 3, 4)}}
_STEMS = ("chain|closure|contract|contrib|data|deps|design|emulator|fit|identify|interval|kernel_check|likelihood|"
          "propagate|reweight|shift|use|validate")
_IDS = ("contract|data-release|fixture|ledger|plan|result|identity-equivalence|decisions|ask-tell|control-variable|"
        "degeneracy-mode|functional|mechanism|parameter-index|reference|stage-graph")
_OLD_NAMES = [(r"\bcore\.simcal\b", "core.calibration"), (r"\bcore/simcal\b", "core/calibration"),
              (rf"\bsimcal-({_IDS})/1", r"calibration-\1/1"), (r"\bg4sim-simcal-eval-state/1", "g4sim-calib-eval-state/1"),
              (r"\bg4sim_simcal_eval\b", "g4sim_calib_eval"), (r"\btest_simcal_scripts\b", "test_calib_scripts"),
              (r"fuzz_simcal", "fuzz_calib"), (r'"test_simcal_"', '"test_calibration_"'),
              (r"\btest_simcal_(?=[a-z])", "test_calibration_"),
              (r"\bsimcal_(exhaustive|fixtures|phase|g4sim|map_fixtures|pde_fixtures|rich_fixture|zdc_fixture)",
               r"calibration_\1"),
              (rf"\bsimcal_({_STEMS})\b", r"calib_\1"),
              (r"\btest_simcal_\*", "test_calibration_*"), (r"simcal_\*", "calib_*")]


def old_names(text: str) -> str:
    """The text with the simcal rename's names of these harness files reversed (simcal -> the 0.69.0 names)."""
    import re
    for pattern, replacement in _OLD_NAMES:
        text = re.sub(pattern, replacement, text)
    return text


def _base_reachable() -> bool:
    if not IN_REPO:
        return False
    try:
        return G.subprocess.run(["git", "cat-file", "-e", G.PHASE_BASE + "^{commit}"], cwd=ROOT,
                                capture_output=True, timeout=60).returncode == 0
    except (OSError, G.subprocess.SubprocessError):
        return False


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
        outs = G.run_tests(["test_simcal_phase5_gates.Negatives.test_does_not_exist"])
        self.assertFalse(G.judge_tests("x", "p", {"test_simcal_phase5_gates.Negatives.test_does_not_exist":
                                                  "negative"}, outs)["passed"])

    def test_tests_are_grouped_by_module(self):
        self.assertEqual(G._module("tests.contracts.test_simcal_schemas"), "tests.contracts.test_simcal_schemas")
        self.assertEqual(G._module(G.SCRIPTS + "Phase1Scripts.test_x"), "tests.skills.test_simcal_scripts")
        self.assertEqual(G._module("test_simcal_design.P5"), "test_simcal_design")

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
        self.assertTrue(G.judge_static(["plugins/hep-research/core/simcal/fit.py"], [self.ENTRY],
                                       [dict(self.ENTRY)])["passed"])

    def test_a_protected_file_or_a_changed_registry_entry_fails(self):
        self.assertFalse(G.judge_static([G.PROTECTED[0]], [self.ENTRY], [self.ENTRY])["passed"])
        self.assertFalse(G.judge_static([], [self.ENTRY], [dict(self.ENTRY, reason="edited")])["passed"])
        self.assertFalse(G.judge_static([], [self.ENTRY], [])["passed"])

    def test_registry_selection_keeps_phase_0_to_4_only(self):
        reg = {"registrations": [self.ENTRY, {"card": "simcal-tasks/phase-5.md"}]}
        self.assertEqual(G.prior_registry_entries(reg), [self.ENTRY])

    @unittest.skipUnless(IN_REPO, "repository checkout only (a relocated copy has no repository root)")
    def test_protected_paths_are_repository_relative(self):
        self.assertEqual(len(G.PROTECTED), 15)
        self.assertTrue(all(p.startswith("plugins/hep-research/") for p in G.PROTECTED))
        for p in G.PROTECTED:
            self.assertTrue((ROOT.parents[1] / p).is_file(), p)

    @unittest.skipUnless(_base_reachable(), "needs a repository checkout with the phase-5 base commit")
    def test_static_item_at_this_commit(self):
        """Since the phase-5 base, no protected file and no phase-0..4 registry entry changed, except the simcal rename
        (0.70.0): it moved the 5 protected harness files of RENAMED_PROTECTED, and each is its phase-5 original with
        names substituted only. The item itself then reports exactly those 5 files (gate record rename-0.70)."""
        r = G.static_item()
        self.assertEqual(r["registry_entries_differing"], [], r)
        self.assertEqual(r["registry_entries_base"], r["registry_entries_head"])
        changed = set(r["protected_files_changed"])
        self.assertLessEqual(changed, set(RENAMED_PROTECTED), r)
        self.assertEqual(changed == set(RENAMED_PROTECTED), not r["passed"], r)
        for renamed_path, old_path in RENAMED_PROTECTED.items():
            if renamed_path in changed:
                original = G._git("show", f"{G.PHASE_BASE}:plugins/hep-research/{old_path}")
                self.assertEqual(old_names((REPO / renamed_path).read_text(encoding="utf-8")), original, renamed_path)


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
        self.assertIn("simcal_exhaustive.py --item", p0)
        self.assertIn("--array=0-32", (self.d / "p2g1.sbatch").read_text())
        p3 = (self.d / "p3.sbatch").read_text()
        self.assertIn("SIMCAL_G4_PRODUCTS=" + G.G4_PRODUCTS, p3)
        submit = (self.d / "submit.sh").read_text()
        self.assertIn("sbatch --array=0-9 --mem=8000M p3.sbatch 27164", submit)
        self.assertIn("sbatch --array=0-15,123 --mem=8000M p3.sbatch", submit)
        misc = (self.d / "misc.sbatch").read_text()
        for cmd in ("simcal_phase1_gates.py --gate agreement", "simcal_phase2_gates.py --gate segmented",
                    "simcal_phase2_gates.py --gate shift"):
            self.assertIn(cmd, misc)
        self.assertIn("simcal_phase4_gates.py --run", (self.d / "login.sh").read_text())
        with self.assertRaises(ValueError):
            G.dispatch(self.d, "abc", "/wt")

    def test_the_registered_sizes_match_the_earlier_harnesses(self):
        import simcal_exhaustive as EX
        import simcal_phase2_gates as P2G
        self.assertEqual(len(EX.GATE_SHARDS), G.P0_ITEMS)
        self.assertEqual(len(P2G.GATE1T_TASKS), G.P2_GATE1_TASKS)
        import simcal_phase3_gates as P3G
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
        for s in ("simcal_contract.py", "simcal_chain.py", "simcal_design.py", "simcal_kernel_check.py", "simcal_fit.py",
                  "simcal_identify.py", "simcal_closure.py", "simcal_validate.py", "simcal_propagate.py",
                  "simcal_use.py", "simcal_deps.py", "simcal_contrib.py", "simcal_emulator.py", "simcal_reweight.py"):
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
        # the simcal rename (0.70.0) changed the case file's names only: reversed, it is the captured file; the cases
        # are then judged against a copy of the golden that records the renamed file's SHA-256
        import hashlib
        text = G.TREE_CASES.read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(old_names(text).encode()).hexdigest(), doc["cases"][fast[0]]["case_code_sha256"])
        doc = json.loads(json.dumps(doc))
        for n in names:
            doc["cases"][n]["case_code_sha256"] = hashlib.sha256(G.TREE_CASES.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as work_dir:
            renamed = Path(work_dir) / "g.json"
            renamed.write_text(json.dumps(doc))
            self.assertTrue(G.identity_item(path=renamed, cases=fast)["passed"])
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

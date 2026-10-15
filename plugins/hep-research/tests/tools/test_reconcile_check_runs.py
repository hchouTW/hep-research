"""tools/reconcile_check_runs.py (CI gate) and the run records it reads from tools/run_all_checks.py: a complete,
passing set of runs reconciles; every way of losing or corrupting an obligation (missing shard, module in two shards
or in none, module planned but not run, unfinished module, failed or skipped check, dropped check, other commit,
duplicate run, unreadable record) fails, whatever the test counts say."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[2] / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REC = _load("reconcile_check_runs")
RUNNER = _load("run_all_checks")
MODULES = ["tests.a", "tests.b", "tests.c", "tests.d", "tests.e"]
PARTS = {"static": ["profile-tests:x", "check_layering", "claude-plugin-validate"], "ams-optional": ["ams_optional"]}
SHA = "a" * 40


def unit_run(py, k, n, modules):
    rows = [{"module": m, "status": "pass", "seconds": 1.0, "counts": {"run": 2, "failures": 0, "errors": 0, "skipped": 0}}
            for m in modules]
    return {"environment": {"python": f"{py}.4"}, "git_commit": SHA, "part": "units", "shard": f"{k}/{n}",
            "checks": [{"name": "unittest", "status": "pass", "modules": rows,
                        "plan": {"all_modules": MODULES, "modules": sorted(modules), "shard": f"{k}/{n}"}}]}


def part_run(py, part):
    checks = [{"name": c, "status": "skip" if c == "claude-plugin-validate" else "pass"} for c in PARTS[part]]
    return {"environment": {"python": f"{py}.4"}, "git_commit": SHA, "part": part, "checks": checks}


def good_runs(pythons=("3.11", "3.13")):
    runs = []
    for py in pythons:
        runs += [unit_run(py, 1, 2, ["tests.a", "tests.c", "tests.e"]), unit_run(py, 2, 2, ["tests.b", "tests.d"]),
                 part_run(py, "static"), part_run(py, "ams-optional")]
    for i, r in enumerate(runs):
        r["_file"] = f"run{i}.json"
    return runs


def check(runs, sha=SHA, modules=MODULES):
    return REC.reconcile(runs, ["3.11", "3.13"], 2, ["static", "ams-optional"], sha, modules, PARTS)


class ReconcileTests(unittest.TestCase):
    def test_complete_passing_runs_reconcile(self):
        rep = check(good_runs())
        self.assertTrue(rep["ok"], rep["problems"])
        self.assertEqual((rep["runs"], rep["expected_runs"], rep["commit"]), (8, 8, SHA))

    def assertFails(self, runs, needle, **kw):
        rep = check(runs, **kw)
        self.assertFalse(rep["ok"])
        self.assertTrue(any(needle in p for p in rep["problems"]), rep["problems"])

    def test_missing_shard(self):
        runs = [r for r in good_runs() if not (r["part"] == "units" and r["shard"] == "2/2" and r["environment"]["python"].startswith("3.13"))]
        self.assertFails(runs, "missing run: Python 3.13, units 2/2")

    def test_missing_part(self):
        self.assertFails([r for r in good_runs() if r["part"] != "ams-optional"], "missing run: Python 3.11, ams-optional")

    def test_duplicate_run(self):
        runs = good_runs()
        runs.append(dict(copy.deepcopy(runs[2]), _file="again.json"))
        self.assertFails(runs, "duplicate runs: Python 3.11, static")

    def test_module_in_two_shards_even_with_equal_counts(self):
        runs = good_runs()
        runs[1] = dict(unit_run("3.11", 2, 2, ["tests.b", "tests.c"]), _file="run1.json")  # d lost, c twice: same size
        self.assertFails(runs, "module tests.c in two shards")
        self.assertFails(runs, "modules in no shard: ['tests.d']")

    def test_shards_planned_from_different_timings(self):
        runs = good_runs()
        runs[0]["checks"][0]["plan"]["timings_sha256"] = "1" * 64
        runs[1]["checks"][0]["plan"]["timings_sha256"] = "2" * 64
        self.assertFails(runs, "different module timings")

    def test_module_planned_but_not_run(self):
        runs = good_runs()
        runs[0]["checks"][0]["modules"] = runs[0]["checks"][0]["modules"][:-1]
        self.assertFails(runs, "modules run differ from the plan")

    def test_unfinished_module(self):
        runs = good_runs()
        runs[0]["checks"][0]["modules"][0]["counts"] = None
        self.assertFails(runs, "did not finish")

    def test_module_dropped_from_every_record(self):
        self.assertFails(good_runs(), "full module list differs", modules=MODULES + ["tests.new"])

    def test_failed_check(self):
        runs = good_runs()
        runs[3]["checks"][0]["status"] = "fail"
        self.assertFails(runs, "check ams_optional failed")

    def test_skip_that_is_not_permitted(self):
        runs = good_runs()
        runs[2]["checks"][0].update(status="skip", reason="no tests folder")
        self.assertFails(runs, "not a permitted skip")

    def test_dropped_check(self):
        runs = good_runs()
        runs[2]["checks"] = [c for c in runs[2]["checks"] if c["name"] != "check_layering"]
        self.assertFails(runs, "checks not run: ['check_layering']")

    def test_other_commit(self):
        runs = good_runs()
        runs[5]["git_commit"] = "b" * 40
        self.assertFails(runs, "runs of different commits")
        self.assertFails(good_runs(), "not of the tested commit", sha="c" * 40)

    def test_units_run_without_plan(self):
        runs = good_runs()
        del runs[0]["checks"][0]["plan"]
        self.assertFails(runs, "without a recorded plan")

    def test_cli_reads_artifact_folders_and_flags_unreadable_records(self):
        with tempfile.TemporaryDirectory() as td:
            for i, r in enumerate(good_runs()):
                d = Path(td) / f"artifact-{i}"
                d.mkdir()
                (d / f"check-run-{i}.json").write_text(json.dumps(r))
            (Path(td) / "check-run-broken.json").write_text("{")
            with mock.patch.object(REC, "_runner") as runner:
                runner.return_value.test_modules.return_value = MODULES
                runner.return_value.planned_check_names.side_effect = lambda p: PARTS[p]
                summary = Path(td) / "summary.md"
                with mock.patch("sys.stdout"):
                    code = REC.main([td, "--python", "3.11,3.13", "--shards", "2", "--sha", SHA, "--summary", str(summary)])
                self.assertEqual(code, 1)
                self.assertIn("unreadable", summary.read_text())
                (Path(td) / "check-run-broken.json").unlink()
                with mock.patch("sys.stdout"):
                    self.assertEqual(REC.main([td, "--python", "3.11,3.13", "--shards", "2", "--sha", SHA]), 0)


class RunnerRecordTests(unittest.TestCase):
    """What run_all_checks.py records for the reconciliation and for people reading a failed CI log."""

    def test_planned_check_names_match_what_a_static_run_reports(self):
        fake = lambda name, cmd, cwd=None, timeout=None: {"name": name, "status": "pass", "seconds": 0.0}
        profiles = lambda: [{"name": n, "status": "pass", "seconds": 0.0}
                            for n in RUNNER.planned_check_names("static") if n.startswith("profile-tests:")]
        with tempfile.TemporaryDirectory() as td, mock.patch.object(RUNNER, "run_script", fake), \
                mock.patch.object(RUNNER, "run_profile_tests", profiles), mock.patch("sys.stdout"):
            self.assertEqual(RUNNER.main(["--part", "static", "--no-cli", "--out", td]), 0)
            doc = json.loads(next(Path(td).glob("check-run-*.json")).read_text())
        self.assertEqual([c["name"] for c in doc["checks"]], RUNNER.planned_check_names("static"))
        self.assertEqual(RUNNER.planned_check_names("ams-optional"), ["ams_optional"])
        self.assertEqual(sorted(RUNNER.planned_check_names("checks")),
                         sorted(RUNNER.planned_check_names("static") + ["ams_optional"]))

    def test_units_plan_partitions_and_digest_is_order_free(self):
        every = RUNNER.test_modules()
        self.assertEqual(RUNNER.modules_digest(every), RUNNER.modules_digest(list(reversed(every))))
        with mock.patch.object(RUNNER, "run_module", lambda m, t: {"module": m, "status": "pass", "seconds": 0.0,
                               "counts": {"run": 1, "failures": 0, "errors": 0, "skipped": 0}, "failed": [], "skipped": []}):
            plans = [RUNNER.run_unittests(shard=(k, 3))["plan"] for k in (1, 2, 3)]
        self.assertEqual({p["all_modules_sha256"] for p in plans}, {RUNNER.modules_digest(every)})
        self.assertEqual(sorted(m for p in plans for m in p["modules"]), every)

    def test_failure_report_names_tests_and_traceback_tails(self):
        checks = [
            {"name": "unittest", "status": "fail", "failed": ["test_x (tests.m.T.test_x)"],
             "messages": {"test_x (tests.m.T.test_x)": "Traceback\n  File m.py\nAssertionError: 1 != 2"}},
            {"name": "profile-tests:p", "status": "fail", "detail": {"failed": ["test_y (t.T.test_y)"],
                                                                     "messages": {"test_y (t.T.test_y)": "KeyError: 'z'"}}},
            {"name": "ams_optional", "status": "fail", "detail": {"checks": [{"name": "tests_core", "status": "fail",
                                                                                "tail": "FAILED (errors=1)"}]}},
            {"name": "sleeper", "status": "fail", "reason": "timed out after 1 s"},
            {"name": "fine", "status": "pass"},
        ]
        report = RUNNER.failure_report(checks)
        for needle in ("FAILED [unittest] test_x (tests.m.T.test_x)", "AssertionError: 1 != 2",
                       "FAILED [profile-tests:p] test_y", "KeyError: 'z'", "FAILED [ams_optional] tests_core",
                       "FAILED (errors=1)", "FAILED [sleeper] sleeper", "timed out after 1 s"):
            self.assertIn(needle, report)
        self.assertNotIn("fine", report)
        md = RUNNER.markdown_summary({"part": "units", "shard": "1/2", "git_commit": SHA,
                                      "environment": {"python": "3.13.1"}, "counts": {"pass": 1, "fail": 4, "skip": 0},
                                      "checks": checks}, report)
        self.assertIn("| unittest | fail |", md)
        self.assertIn("<summary>Failures</summary>", md)

    def test_check_scripts_record_seconds(self):
        row = RUNNER.run_script("quick", [sys.executable, "-c", "print('{}')"], timeout=60)
        self.assertIn("seconds", row)
        slow = RUNNER.run_script("sleeper", [sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertGreaterEqual(slow["seconds"], 1.0)


if __name__ == "__main__":
    unittest.main()

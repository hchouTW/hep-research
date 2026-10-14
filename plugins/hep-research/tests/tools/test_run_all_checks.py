"""tools/run_all_checks.py command line: --help prints usage without running anything (FULLTEST-E3 follow-up 5), and
an unknown option is refused instead of being ignored."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "run_all_checks.py"


def run(*args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, cwd=cwd, timeout=60)


class CommandLineTests(unittest.TestCase):
    def test_help_prints_usage_and_runs_nothing(self):
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as td:
                p = run(flag, "--out", td, cwd=td)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn("--out", p.stdout)
                self.assertIn("--no-cli", p.stdout)
                self.assertEqual(list(Path(td).iterdir()), [], "help must not write a check-run")

    def test_unknown_option_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = run("--outdir", td, cwd=td)
            self.assertEqual(p.returncode, 2, p.stdout[-500:])
            self.assertIn("--outdir", p.stderr)
            self.assertEqual(list(Path(td).iterdir()), [])


class ModuleTimeoutTests(unittest.TestCase):
    """A module that does not finish is a failure with its reason, not a hang (T14)."""

    def test_a_hanging_module_fails_with_a_reason(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_all_checks", TOOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        row = mod.run_module("tests.tools.sleeping_module_fixture", timeout=2)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["reason"], "timed out after 2 s")
        self.assertLess(row["seconds"], 20)
        ok = mod.run_module("tests.tools.test_reference_inventory", timeout=120)
        self.assertEqual(ok["status"], "pass")
        self.assertGreater(ok["counts"]["run"], 0)
        self.assertNotIn("tests.tools.sleeping_module_fixture", mod.test_modules())


    def test_a_hanging_check_script_fails_without_aborting_the_run(self):
        mod = _load("run_all_checks", TOOL)
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        row = mod.run_script("sleeper", cmd, timeout=1)
        self.assertEqual((row["status"], row["exit_code"]), ("fail", None))
        self.assertEqual(row["reason"], "timed out after 1 s")
        ok = mod.run_script("quick", [sys.executable, "-c", "print('{}')"], timeout=60)
        self.assertEqual(ok["status"], "pass")


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ShardTests(unittest.TestCase):
    """--shard K/N and the slowest-first order (CI speed-up): every module runs in exactly one shard, the shards are
    balanced by the recorded timings, and a module with no record still runs."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load("run_all_checks", TOOL)
        cls.modules = cls.mod.test_modules()
        cls.timings = cls.mod.load_timings()

    def test_shards_partition_every_module(self):
        for n in (1, 2, 3, 5):
            with self.subTest(n=n):
                parts = [self.mod.shard_modules(self.modules, k, n, self.timings) for k in range(1, n + 1)]
                flat = [m for p in parts for m in p]
                self.assertEqual(sorted(flat), self.modules, "each module in exactly one shard")

    def test_shards_are_balanced(self):
        est = self.mod.expected_seconds(self.modules, self.timings)
        loads = [sum(est[m] for m in self.mod.shard_modules(self.modules, k, 3, self.timings)) for k in (1, 2, 3)]
        self.assertLessEqual(max(loads) - min(loads), max(est.values()) + 1e-9)

    def test_new_module_gets_the_median_and_still_runs(self):
        timings = {"a": 1.0, "b": 5.0, "c": 9.0}
        est = self.mod.expected_seconds(["a", "b", "c", "new"], timings)
        self.assertEqual(est["new"], 5.0)
        self.assertEqual(self.mod.slowest_first(["a", "b", "c", "new"], timings), ["c", "b", "new", "a"])
        parts = [self.mod.shard_modules(["a", "b", "c", "new"], k, 2, timings) for k in (1, 2)]
        self.assertEqual(sorted(parts[0] + parts[1]), ["a", "b", "c", "new"])

    def test_bad_shard_is_refused(self):
        for bad in ("0/3", "4/3", "2", "a/b"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as td:
                p = run("--shard", bad, cwd=td)
                self.assertEqual(p.returncode, 2, p.stdout[-300:])
        with tempfile.TemporaryDirectory() as td:
            p = run("--shard", "1/2", "--part", "checks", cwd=td)
            self.assertEqual(p.returncode, 2)
            self.assertIn("--part checks", p.stderr)


class AmsOptionalSuiteTests(unittest.TestCase):
    """check_ams_optional.py runs each test module on its own; a suite still fails when any of its modules fails."""

    def test_suite_fails_when_one_module_fails(self):
        mod = _load("check_ams_optional", TOOL.parent / "check_ams_optional.py")
        ok = {"name": "m1", "exit_code": 0, "status": "pass", "tail": ""}
        bad = {"name": "m2", "exit_code": 1, "status": "fail", "tail": "AssertionError"}
        self.assertEqual(mod.merge_suite("s", [ok, ok])["status"], "pass")
        row = mod.merge_suite("s", [ok, bad])
        self.assertEqual((row["status"], row["exit_code"]), ("fail", 1))
        self.assertIn("m2: AssertionError", row["tail"])
        self.assertEqual(mod.merge_suite("s", [])["status"], "fail", "a suite with no modules is not a pass")


if __name__ == "__main__":
    unittest.main()

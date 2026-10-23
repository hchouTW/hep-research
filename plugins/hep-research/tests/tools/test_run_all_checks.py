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


class TimingCoverageTests(unittest.TestCase):
    """The shards balance only when the timings cover the modules: 143 of 382 modules had no record on 2026-10-21 and
    the two CI shards took 444 s and 547 s. Refresh tools/module_timings.json from a CI run when this fails."""

    def test_at_most_a_tenth_of_the_modules_lack_a_timing(self):
        mod = _load("run_all_checks", TOOL)
        modules, timings = mod.test_modules(), mod.load_timings()
        missing = sorted(set(modules) - set(timings))
        self.assertLessEqual(len(missing), len(modules) // 10, f"{len(missing)} modules without a timing: {missing[:10]}")


class ExtraSelectionTests(unittest.TestCase):
    """--extra NAME runs only the modules tools/optional_modules.json lists for an optional extra (CI optional jobs
    on pull requests); every listed module must exist, and it combines only with --part units."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load("run_all_checks", TOOL)
        cls.modules = cls.mod.test_modules()

    def test_committed_selection_lists_existing_modules_for_every_ci_extra(self):
        import json
        doc = json.loads(self.mod.OPTIONAL_MODULES.read_text(encoding="utf-8"))
        self.assertEqual(sorted(doc["extras"]), ["ROOT", "columnar", "hepdata", "pyhf", "root-uproot", "torch-cpu"])
        for extra in doc["extras"]:
            with self.subTest(extra=extra):
                self.assertTrue(set(self.mod.extra_modules(extra, self.modules)) <= set(self.modules))

    def test_unknown_extra_and_stale_module_are_refused(self):
        import json
        with self.assertRaises(ValueError):
            self.mod.extra_modules("no-such-extra", self.modules)
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sel.json"
            f.write_text(json.dumps({"extras": {"x": ["tests.tools.test_gone_module"]}}))
            with self.assertRaisesRegex(ValueError, "no longer exist"):
                self.mod.extra_modules("x", self.modules, f)

    def test_extra_needs_part_units_without_shard(self):
        for extra_args in (("--extra", "pyhf"), ("--extra", "pyhf", "--part", "units", "--shard", "1/2")):
            with self.subTest(args=extra_args), tempfile.TemporaryDirectory() as td:
                p = run(*extra_args, cwd=td)
                self.assertEqual(p.returncode, 2, p.stdout[-300:])
                self.assertIn("--part units", p.stderr)


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
        self.assertEqual(mod.merge_suite("s", [], selected=False)["status"], "skip")  # the CI plan selected none of it



def old_interpreters() -> list[str]:
    """Real Pythons below 3.13 on this machine (none on CI; macOS ships /usr/bin/python3 3.9)."""
    import shutil
    found = []
    for name in ("python3.9", "python3.10", "python3.11", "python3.12", "/usr/bin/python3"):
        exe = shutil.which(name)
        if not exe or exe in found:
            continue
        try:
            v = subprocess.run([exe, "-c", "import sys; print(sys.version_info[1])"], capture_output=True,
                               text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            continue
        if v.isdigit() and int(v) < 13:
            found.append(exe)
    return found


class UnsupportedPythonTests(unittest.TestCase):
    """On a Python below the 3.13 floor the runners stop at once with exit 2 and one clear message, instead of
    running the suite into version-dependent test failures."""
    TOOLS = ("run_all_checks.py", "check_ams_optional.py")
    # arguments that stop each tool at once on a supported Python, with a different exit or message than the guard's:
    # check_ams_optional.py has no --help (it would run everything), a bad --jobs exits 2 before any work
    QUICK = {"run_all_checks.py": ["--help"], "check_ams_optional.py": ["--jobs", "x"]}

    def test_guard_function(self):
        import contextlib
        import io
        for tool in self.TOOLS:
            mod = _load(tool[:-3], TOOL.parent / tool)
            for old in ((3, 12, 7, "final", 0), (3, 11, 9), (3, 9, 6)):
                with self.subTest(tool=tool, version=old):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                        mod.require_supported_python(old)
                    self.assertEqual(cm.exception.code, 2)
                    self.assertEqual(err.getvalue().strip(),
                                     f"Python 3.13 or newer is required (running {old[0]}.{old[1]})")
            for ok in ((3, 13, 0), (3, 14, 1), (4, 0, 0)):
                with self.subTest(tool=tool, version=ok):
                    self.assertIsNone(mod.require_supported_python(ok))

    def test_guard_runs_before_anything_else(self):
        """The script, run with an old sys.version_info, exits 2 with the floor message before its own argument
        handling (run_all_checks.py --help otherwise exits 0; check_ams_optional.py --jobs x prints its own error)."""
        driver = ("import runpy, sys; sys.version_info = (3, 12, 1, 'final', 0); sys.argv = sys.argv[1:]; "
                  "runpy.run_path(sys.argv[0], run_name='__main__')")
        for tool in self.TOOLS:
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as td:
                p = subprocess.run([sys.executable, "-c", driver, str(TOOL.parent / tool), *self.QUICK[tool]],
                                   capture_output=True,
                                   text=True, cwd=td, timeout=60)
                self.assertEqual(p.returncode, 2, p.stdout[-300:] + p.stderr[-300:])
                self.assertEqual(p.stderr.strip(), "Python 3.13 or newer is required (running 3.12)")
                self.assertEqual(list(Path(td).iterdir()), [])

    @unittest.skipUnless(old_interpreters(), "no Python below 3.13 on this machine")
    def test_real_old_interpreter_gets_the_message(self):
        for exe in old_interpreters():
            for tool in self.TOOLS:
                with self.subTest(exe=exe, tool=tool), tempfile.TemporaryDirectory() as td:
                    p = subprocess.run([exe, str(TOOL.parent / tool), *self.QUICK[tool]], capture_output=True,
                                       text=True, cwd=td, timeout=60)
                    self.assertEqual(p.returncode, 2, p.stderr[-300:])
                    self.assertRegex(p.stderr.strip(), r"^Python 3\.13 or newer is required \(running 3\.\d+\)$")

if __name__ == "__main__":
    unittest.main()

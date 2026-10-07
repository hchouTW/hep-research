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


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

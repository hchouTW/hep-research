"""Regression tests for workflow_check.py `diff` (ALL-5): a rename must not hide its source path.

Run: python3 -m unittest docs/dev/cr-propagation/test_workflow_check.py  (or run this file directly).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "workflow_check.py"
PREFIX = "plugins/hep-research"
PACKAGE = "A1"
ALLOWED = "skills/hep-theory/scripts/transport_conventions.py"  # in A1's files (workflow.json)
OUTSIDE = "tools/check_layering.py"  # not in A1's files
ORCHESTRATOR_ONLY = "docs/dev/cr-propagation/status.json"


def run(*args, cwd):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class RenameHidingTest(unittest.TestCase):
    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.repo = Path(self._scratch.name)
        self.plugin = self.repo / PREFIX
        run("init", "-q", cwd=self.repo)
        run("config", "user.email", "t@example.invalid", cwd=self.repo)
        run("config", "user.name", "t", cwd=self.repo)
        run("config", "diff.renames", "true", cwd=self.repo)
        # Distinct, multi-line content so rename detection (similarity) fires.
        for relative in (OUTSIDE, ORCHESTRATOR_ONLY):
            path = self.plugin / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(f"line {i} of {relative}\n" for i in range(40)), encoding="utf-8")
        run("add", "-A", cwd=self.repo)
        run("commit", "-q", "-m", "base", cwd=self.repo)
        self.base = run("rev-parse", "HEAD", cwd=self.repo)

    def diff(self):
        proc = subprocess.run(
            [sys.executable, str(CHECKER), "diff", "--work-package", PACKAGE, "--base", self.base, "--plugin-root", str(self.plugin)],
            capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)

    def move_into_allowed(self, source):
        destination = self.plugin / ALLOWED
        destination.parent.mkdir(parents=True, exist_ok=True)
        run("mv", f"{PREFIX}/{source}", f"{PREFIX}/{ALLOWED}", cwd=self.repo)
        run("commit", "-q", "-m", "move", cwd=self.repo)

    def test_moving_an_out_of_scope_file_is_reported(self):
        self.move_into_allowed(OUTSIDE)
        code, report = self.diff()
        self.assertEqual(code, 1, report)
        self.assertTrue(any(p.startswith(f"{OUTSIDE}: outside") for p in report["problems"]), report)

    def test_moving_an_orchestrator_only_file_is_reported(self):
        self.move_into_allowed(ORCHESTRATOR_ONLY)
        code, report = self.diff()
        self.assertEqual(code, 1, report)
        self.assertTrue(any(p.startswith(f"{ORCHESTRATOR_ONLY}: orchestrator-only") for p in report["problems"]), report)

    def test_in_scope_change_alone_is_ok(self):
        path = self.plugin / ALLOWED
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("new\n", encoding="utf-8")
        run("add", "-A", cwd=self.repo)
        run("commit", "-q", "-m", "add", cwd=self.repo)
        code, report = self.diff()
        self.assertEqual((code, report["problems"]), (0, []))


if __name__ == "__main__":
    unittest.main()

"""tools/run_all_checks.py writes its summary when git is missing or hangs (T21): the commit is "unknown", the run does
not end in a traceback. The checks themselves are replaced by empty lists; only the summary step runs."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOL = Path(__file__).resolve().parents[2] / "tools" / "run_all_checks.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_all_checks_git_t21", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GitFailureSummary(unittest.TestCase):
    def run_main_with_git(self, error):
        mod = _load()
        real_run = subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if cmd and cmd[0] == "git":
                raise error
            return real_run(cmd, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(mod, "run_profile_tests", return_value=[]), \
                mock.patch.object(mod, "planned_scripts", return_value=[]), \
                mock.patch.object(mod, "host_versions", return_value={}), \
                mock.patch.object(mod.subprocess, "run", side_effect=fake_run), \
                contextlib.redirect_stdout(io.StringIO()):
            code = mod.main(["--part", "checks", "--no-cli", "--out", tmp])
            files = list(Path(tmp).glob("check-run-*.json"))
            summary = json.loads(files[0].read_text()) if len(files) == 1 else None
        return code, summary

    def test_git_timeout_still_writes_the_summary(self):
        code, summary = self.run_main_with_git(subprocess.TimeoutExpired(["git", "rev-parse", "HEAD"], 1))
        self.assertEqual(code, 0)
        self.assertEqual(summary["git_commit"], "unknown")

    def test_missing_git_still_writes_the_summary(self):
        code, summary = self.run_main_with_git(FileNotFoundError(2, "No such file or directory", "git"))
        self.assertEqual(code, 0)
        self.assertEqual(summary["git_commit"], "unknown")


if __name__ == "__main__":
    unittest.main()

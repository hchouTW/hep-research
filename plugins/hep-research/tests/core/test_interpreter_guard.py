"""core/interpreter_guard.py: every branch of guard() with patched version, execv, access and euid; MIN_PYTHON equals
pyproject.toml requires-python. The end-to-end runs with a real Python 3.9 are in tests/tools/test_python_compat.py
and the CI old-python job."""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core import interpreter_guard as ig  # noqa: E402

OLD = (3, 9, 6, "final", 0)


class Execv(Exception):
    pass


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.env = {}
        patches = [mock.patch.dict(os.environ, self.env, clear=True),
                   mock.patch.object(ig.os, "execv", side_effect=self._execv),
                   mock.patch.object(ig.sys, "argv", ["script.py", "--help"])]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.calls = []
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.target = os.path.join(scratch.name, "python3.13")
        Path(self.target).write_text("#!/bin/sh\n")
        os.chmod(self.target, 0o755)

    def _execv(self, path, args):
        self.calls.append((path, list(args)))
        raise Execv

    def run_guard(self, version=OLD, writable=False, euid=1000):
        """(outcome, stderr): outcome is 'return', 'execv' or the exit code."""
        def access(path, mode):
            if mode == os.W_OK:
                return writable
            return os.path.exists(path)
        err = io.StringIO()
        out = io.StringIO()
        with mock.patch.object(ig.sys, "version_info", version), mock.patch.object(ig.os, "access", access), \
                mock.patch.object(ig.os, "geteuid", return_value=euid, create=True), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            try:
                ig.guard()
                outcome = "return"
            except Execv:
                outcome = "execv"
            except SystemExit as exc:
                outcome = exc.code
        self.assertEqual(out.getvalue(), "", "the guard never prints on stdout")
        return outcome, err.getvalue()

    def assert_guidance(self, outcome, err):
        self.assertEqual(outcome, 2)
        self.assertEqual(err.count("\n"), 1)
        self.assertTrue(err.startswith("hep-research: Python 3.13 or newer is required (running 3.9). "
                                       "Set HEP_RESEARCH_PYTHON"), err)
        self.assertIn("find_python.py", err)
        self.assertEqual(self.calls, [])

    def test_supported_python_returns_and_clears_the_marker(self):
        os.environ[ig.MARKER_VARIABLE] = "1"
        self.assertEqual(self.run_guard(version=(3, 13, 0, "final", 0)), ("return", ""))
        self.assertNotIn(ig.MARKER_VARIABLE, os.environ)

    def test_old_python_without_target_gives_guidance(self):
        self.assert_guidance(*self.run_guard())

    def test_old_python_switches_once_to_a_safe_target(self):
        os.environ[ig.TARGET_VARIABLE] = self.target
        outcome, err = self.run_guard()
        self.assertEqual((outcome, err), ("execv", ""))
        self.assertEqual(self.calls, [(self.target, [self.target, "script.py", "--help"])])
        self.assertEqual(os.environ[ig.MARKER_VARIABLE], "1")

    def test_target_path_is_made_absolute_not_resolved(self):
        link = os.path.join(os.path.dirname(self.target), "python")
        os.symlink(self.target, link)
        os.environ[ig.TARGET_VARIABLE] = os.path.dirname(link) + "/./python"
        self.run_guard()
        self.assertEqual(self.calls[0][0], link)

    def test_marker_set_means_the_switch_did_not_help(self):
        os.environ[ig.TARGET_VARIABLE] = self.target
        os.environ[ig.MARKER_VARIABLE] = ""
        outcome, err = self.run_guard()
        self.assertEqual(outcome, 2)
        self.assertEqual(err, "hep-research: Python 3.13 or newer is required (running 3.9); "
                              "HEP_RESEARCH_PYTHON did not provide one.\n")
        self.assertEqual(self.calls, [])

    def test_refusals_give_guidance(self):
        cases = {
            "relative value": ("bin/python3.13", {}),
            "bare command": ("python3.13", {}),
            "missing file": (None, {}),
            "folder": ("<dir>", {}),
            "writable target or folder": (self.target, {"writable": True}),
            "root": (self.target, {"euid": 0}),
        }
        for name, (value, kwargs) in cases.items():
            with self.subTest(case=name):
                self.calls.clear()
                os.environ.pop(ig.MARKER_VARIABLE, None)
                if value is None:
                    value = self.target + ".missing"
                elif value == "<dir>":
                    value = os.path.dirname(self.target)
                os.environ[ig.TARGET_VARIABLE] = value
                self.assert_guidance(*self.run_guard(**kwargs))

    def test_protected_argument_refuses_the_switch(self):
        os.environ[ig.TARGET_VARIABLE] = self.target
        with mock.patch.object(ig.sys, "argv", ["script.py", "run", "--protected"]):
            self.assert_guidance(*self.run_guard())

    def test_not_executable_refuses_the_switch(self):
        os.chmod(self.target, 0o644)
        os.environ[ig.TARGET_VARIABLE] = self.target
        with mock.patch.object(ig.os, "access", lambda p, m: False if m in (os.X_OK, os.W_OK) else True):
            self.assertIsNone(ig.switch_target())

    def test_writable_folder_alone_refuses(self):
        os.environ[ig.TARGET_VARIABLE] = self.target
        folder = os.path.dirname(self.target)
        with mock.patch.object(ig.os, "access", lambda p, m: p == folder if m == os.W_OK else True), \
                mock.patch.object(ig.os, "geteuid", return_value=1000, create=True):
            self.assertIsNone(ig.switch_target())

    def test_no_geteuid_is_not_root(self):
        with mock.patch.object(ig.os, "geteuid", create=True):
            del ig.os.geteuid
            self.assertFalse(ig._is_root())

    def test_windows_without_utf8_mode_stops(self):
        flags = mock.Mock(utf8_mode=0)
        with mock.patch.object(ig.os, "name", "nt"), mock.patch.object(ig.sys, "flags", flags):
            outcome, err = self.run_guard(version=(3, 13, 0, "final", 0))
        self.assertEqual((outcome, err), (2, "hep-research: set PYTHONUTF8=1 (UTF-8 mode) to run hep-research "
                                             "scripts on Windows.\n"))
        with mock.patch.object(ig.os, "name", "nt"), mock.patch.object(ig.sys, "flags", mock.Mock(utf8_mode=1)):
            self.assertEqual(self.run_guard(version=(3, 13, 0, "final", 0)), ("return", ""))


class Floor(unittest.TestCase):
    def test_min_python_equals_requires_python(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r'^requires-python\s*=\s*">=(\d+)\.(\d+)"', text, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(ig.MIN_PYTHON, (int(m.group(1)), int(m.group(2))))

    def test_guard_is_self_contained(self):
        import ast
        tree = ast.parse((ROOT / "core/interpreter_guard.py").read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertLessEqual(imported, {"__future__", "os", "sys"})


if __name__ == "__main__":
    unittest.main()

"""core/hostcaps.py: capability probes, require() and its missing-dependency report, state_dir() per platform."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core import hostcaps  # noqa: E402
from core.status import exit_code  # noqa: E402
from tests._platform import needs  # noqa: E402


def _clear():
    for probe in hostcaps.PROBES.values():
        probe.cache_clear()


class Probes(unittest.TestCase):
    def setUp(self):
        _clear()
        self.addCleanup(_clear)

    def test_probes_return_bool_and_are_cached(self):
        for name, probe in hostcaps.PROBES.items():
            with self.subTest(probe=name):
                self.assertIsInstance(probe(), bool)
                self.assertEqual(probe.cache_info().currsize, 1)

    def test_posix_ids_false_without_the_id_calls(self):
        with mock.patch.object(hostcaps.os, "geteuid", create=True):
            delattr(hostcaps.os, "geteuid")
            self.assertFalse(hostcaps.posix_ids())

    def test_process_groups_needs_posix(self):
        with mock.patch.object(hostcaps.os, "name", "nt"):
            self.assertFalse(hostcaps.process_groups())

    def test_proc_fs_follows_proc_self_stat(self):
        with mock.patch.object(hostcaps.os.path, "isfile", return_value=False):
            self.assertFalse(hostcaps.proc_fs())
        _clear()
        with mock.patch.object(hostcaps.os.path, "isfile", return_value=True):
            self.assertTrue(hostcaps.proc_fs())

    def test_wsl_only_on_linux(self):
        with mock.patch.object(hostcaps.sys, "platform", "darwin"):
            self.assertFalse(hostcaps.wsl())
        _clear()
        with mock.patch.object(hostcaps.sys, "platform", "linux"), \
                mock.patch("builtins.open", mock.mock_open(read_data="5.15.0-microsoft-standard-WSL2")):
            self.assertTrue(hostcaps.wsl())

    def test_unknown_capability_is_an_error(self):
        with self.assertRaises(KeyError):
            hostcaps.has("teleport")


class Require(unittest.TestCase):
    def test_require_passes_when_present(self):
        with mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: True}):
            hostcaps.require("posix_ids")

    def test_report_names_every_missing_capability(self):
        with mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: False, "proc_fs": lambda: False,
                                               "process_groups": lambda: True}):
            with self.assertRaises(hostcaps.UnsupportedPlatform) as ctx:
                hostcaps.require("posix_ids", "process_groups", "proc_fs")
        report = ctx.exception.report()
        self.assertEqual(report["status"], "missing-dependency")
        self.assertEqual(exit_code(report["status"]), 3)
        self.assertEqual(report["reason"], "unsupported-platform")
        self.assertEqual(report["missing"], ["posix_ids", "proc_fs"])
        self.assertEqual(report["platform"], sys.platform)
        json.dumps(report)

    def test_windows_report_hints_wsl2(self):
        exc = hostcaps.UnsupportedPlatform(["posix_ids"])
        with mock.patch.object(hostcaps, "on_windows", return_value=True):
            self.assertEqual(exc.report()["hint"], "use WSL2")
        with mock.patch.object(hostcaps, "on_windows", return_value=False):
            self.assertNotIn("hint", exc.report())


class StateDir(unittest.TestCase):
    def test_xdg_state_home_wins(self):
        self.assertEqual(hostcaps.state_dir("reviews", environ={"XDG_STATE_HOME": "/x/state", "HOME": "/h"}),
                         Path("/x/state/hep-research/reviews"))

    @unittest.skipIf(os.name == "nt", "POSIX layout")
    def test_home_fallback_is_unchanged(self):
        self.assertEqual(hostcaps.state_dir("hep-review", environ={"HOME": "/h"}),
                         Path("/h/.local/state/hep-research/hep-review"))
        self.assertEqual(hostcaps.state_dir(), Path(os.environ.get("XDG_STATE_HOME")
                                                    or Path.home() / ".local" / "state") / "hep-research")

    def test_windows_uses_localappdata(self):
        with mock.patch.object(hostcaps, "on_windows", return_value=True):
            got = hostcaps.state_dir("a", "b", environ={"LOCALAPPDATA": "C:/Users/u/AppData/Local",
                                                        "XDG_STATE_HOME": "/ignored"})
        self.assertEqual(got, Path("C:/Users/u/AppData/Local") / "hep-research" / "a" / "b")


class NeedsDecorator(unittest.TestCase):
    def test_skip_reason_starts_with_needs(self):
        with mock.patch.dict(hostcaps.PROBES, {"proc_fs": lambda: False}):
            @needs("proc_fs")
            def f():
                pass
        self.assertTrue(getattr(f, "__unittest_skip__", False))
        self.assertEqual(f.__unittest_skip_why__, "needs proc_fs")
        with mock.patch.dict(hostcaps.PROBES, {"proc_fs": lambda: True}):
            @needs("proc_fs")
            def g():
                pass
        self.assertFalse(getattr(g, "__unittest_skip__", False))


if __name__ == "__main__":
    unittest.main()

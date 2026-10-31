"""core/hostcaps.py: capability probes, require() and its missing-dependency report, state_dir() per platform; and
its consumers on a host without the capabilities (native Windows, modelled by patching the probes): the protected
guard, run_workflow.py, the hep-review CLI and the per-user state folders."""
import contextlib
import importlib
import importlib.util
import io
import json
import os
import sys
import tempfile
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
            got = hostcaps.state_dir("a", "b", environ={"LOCALAPPDATA": "C:/state/AppData/Local",
                                                        "XDG_STATE_HOME": "/ignored"})
        self.assertEqual(got, Path("C:/state/AppData/Local") / "hep-research" / "a" / "b")


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


def _load(rel: str, name: str):
    path = ROOT / rel
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look their module up there
    spec.loader.exec_module(mod)
    return mod


def _call(main, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, json.loads(buf.getvalue())


class Consumers(unittest.TestCase):
    """What the code does where a capability is missing: a stated refusal or missing-dependency, never a crash."""

    def test_account_current_needs_posix_ids(self):
        from core.protected.trusted_input import Account
        with mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: False}):
            with self.assertRaises(hostcaps.UnsupportedPlatform) as cm:
                Account.current()
        self.assertEqual(cm.exception.missing, ["posix_ids"])

    def test_establish_refuses_without_posix_ids(self):
        from core.protected import guard as G
        with mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: False}):
            ctx = G.establish(flag=True)
        self.assertTrue(ctx.protected and ctx.refused)
        self.assertEqual([r["code"] for r in ctx.refusals], ["protected.unsupported_platform"])

    def test_establish_turns_a_late_unsupported_platform_into_the_refusal(self):
        from core.protected import guard as G
        with mock.patch.object(G, "_establish", side_effect=hostcaps.UnsupportedPlatform(["posix_ids"])):
            ctx = G.establish(flag=True)
        self.assertEqual([r["code"] for r in ctx.refusals], ["protected.unsupported_platform"])

    def test_protected_entry_point_exits_3_refused(self):
        from core.protected import guard as G

        @G.protected_main("tests.core.test_hostcaps.entry")
        def main(argv):
            return 0
        with mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: False}):
            code, out = _call(main, ["--protected"])
            self.assertEqual(main([]), 0)  # outside protected mode nothing changes
        self.assertEqual((code, out["status"]), (3, "refused"))
        self.assertEqual([r["code"] for r in out["refusals"]], ["protected.unsupported_platform"])

    def test_establish_off_is_unchanged_without_posix_ids(self):
        from core.protected import guard as G
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(hostcaps.PROBES, {"posix_ids": lambda: False}):
            self.assertFalse(G.establish([d]).protected)

    def test_run_workflow_without_process_groups_is_missing_dependency(self):
        mod = _load("skills/hep-computing/scripts/run_workflow.py", "run_workflow_hostcaps")
        with tempfile.TemporaryDirectory() as d:
            wf = Path(d) / "wf.json"
            wf.write_text(json.dumps({"workflow": "w", "steps": [
                {"id": "s", "argv": ["{python}", "-c", "pass"], "outputs": ["out.txt"]}]}), encoding="utf-8")
            args = [str(wf), "--work", str(Path(d) / "work"), "--created", "2026-10-31"]
            with mock.patch.dict(hostcaps.PROBES, {"process_groups": lambda: False}):
                self.assertEqual(_call(mod.main, [*args, "--dry-run"])[0], 0)  # nothing runs: still answered
                code, out = _call(mod.main, args)
            self.assertFalse((Path(d) / "work" / "out.txt").exists())
        self.assertEqual(code, exit_code("missing-dependency"))
        self.assertEqual((out["status"], out["reason"], out["missing"]),
                         ("missing-dependency", "unsupported-platform", ["process_groups"]))

    def test_hep_review_snapshot_without_controlled_read_is_missing_dependency(self):
        mod = _load("skills/hep-review/scripts/review.py", "hep_review_cli_hostcaps")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("x", encoding="utf-8")
            with mock.patch.object(mod.M, "controlled_read_available", return_value=False):
                code, out = _call(mod.main, ["--store", str(Path(d) / "store"), "snapshot", "--root", d,
                                             "--paths", "a.txt"])
        self.assertEqual(code, exit_code("missing-dependency"))
        self.assertEqual((out["status"], out["reason"]), ("missing-dependency", "unsupported-platform"))

    def test_state_folders_follow_state_dir_on_windows(self):
        for rel in ("skills/hep-review/scripts", "skills/hep-authoring/scripts"):
            if str(ROOT / rel) not in sys.path:
                sys.path.insert(0, str(ROOT / rel))
        store = importlib.import_module("hep_review_support.store")
        authoring = importlib.import_module("review_lib.store")
        papers = _load("profiles/experiments/ams-02/scripts/fetch_papers.py", "fetch_papers_hostcaps")
        env = {"LOCALAPPDATA": "C:/state/AppData/Local", "HOME": "/h"}
        local = Path("C:/state/AppData/Local") / "hep-research"
        with mock.patch.object(hostcaps, "on_windows", return_value=True), mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(store.default_store_dir(env), local / "hep-review")
            self.assertEqual(authoring.default_private_root(), local / "reviews")
            self.assertEqual(papers.default_cache(), local / "papers")
        with mock.patch.object(hostcaps, "on_windows", return_value=False), \
                mock.patch.dict(os.environ, {"HOME": "/h"}, clear=True):
            self.assertEqual(store.default_store_dir({"HOME": "/h"}), Path("/h/.local/state/hep-research/hep-review"))
            self.assertEqual(authoring.default_private_root(), Path("/h/.local/state/hep-research/reviews"))
            self.assertEqual(papers.default_cache(), Path("/h/.cache/hep-research/papers"))


if __name__ == "__main__":
    unittest.main()

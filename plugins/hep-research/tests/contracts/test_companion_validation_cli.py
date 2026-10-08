"""Companion validation through the existing CLIs (contracts/registry.py, contracts/project.py), as a companion
plugin's own checker calls them: a subprocess per case, stdout JSON with `ok`, exit 0 valid, 1 findings, 2 unreadable.

Every profile here is a synthetic public stand-in written to a temporary folder outside the plugin (it depends on the
registered `experiment:synthetic-collider`, so the cases also run in the copy without the AMS-02 profile that
tools/check_ams_optional.py builds); no companion content or fixture is used. These are
source tests of validator behaviour: they do not test a companion package, a host, or model routing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))

from make_registry_fixtures import profile, write_profile  # noqa: E402

PID = "experiment:fixture-companion"
DEP = "experiment:synthetic-collider"  # a registered public profile the stand-in depends on


def plugin_version() -> str:
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]


def run(tool: str, *args: str) -> tuple[int, dict | None, str]:
    p = subprocess.run([sys.executable, str(ROOT / "contracts" / tool), *args], capture_output=True, text=True,
                       timeout=120)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = None
    return p.returncode, out, p.stderr


def codes(out: dict) -> list[str]:
    return [f["code"] for f in out.get("findings", []) if f["severity"] == "error"]


class CompanionCLI(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.companion = self.base / "companion" / "profile"   # stands for <companion root>/profile
        self.project = self.base / "project"
        self.project.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def write_companion(self, where: Path | None = None, **kw):
        where = where or self.companion
        prof = profile(PID, "experiment", "fixcomp", **{"depends_on": [DEP], **kw})
        write_profile(where.parent, where.name, prof)
        return where

    def write_project(self, pin="1.0.0", local=(), plugin=None):
        cfg = {"schema_version": "1.0.0", "plugin_version": plugin or f">={plugin_version()}",
               "experiments": [{"profile": PID, "version": pin}], "theory": []}
        if local:
            cfg["local_profile_paths"] = list(local)
        (self.project / "hep-research.project.json").write_text(json.dumps(cfg))

    # --- registry validation, no project ---

    def test_registry_without_project(self):
        rc, out, _ = run("registry.py", "--local", str(self.write_companion()))
        self.assertEqual((rc, out["ok"]), (0, True), out)
        self.assertIn(PID, out["profiles"])
        self.assertIn(DEP, out["profiles"])

    def test_core_contracts_incompatible(self):
        self.write_companion(compatible={"core": ">=99.0", "contracts": ">=2.0,<3.0"})
        rc, out, _ = run("registry.py", "--local", str(self.companion))
        self.assertEqual((rc, out["ok"]), (1, False))
        self.assertEqual(codes(out), ["profile.incompatible_version"])

    def test_missing_public_dependency(self):
        self.write_companion(depends_on=["experiment:not-registered"])
        rc, out, _ = run("registry.py", "--local", str(self.companion))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["profile.missing_dependency"])

    def test_unreadable_profile_json(self):
        self.write_companion()
        (self.companion / "profile.json").write_text("{not json")
        rc, out, _ = run("registry.py", "--local", str(self.companion))
        self.assertEqual((rc, out["ok"]), (1, False))
        self.assertEqual(codes(out), ["profile.unreadable"])

    def test_missing_profile_folder(self):
        rc, out, _ = run("registry.py", "--local", str(self.base / "absent"))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["profile.missing_resource"])

    def test_unreadable_registry(self):
        bad = self.base / "registry.json"
        bad.write_text("[")
        rc, out, _ = run("registry.py", "--registry", str(bad))
        self.assertEqual((rc, out["ok"]), (2, False))
        self.assertIn("error", out)

    def test_dangling_option_is_a_usage_error(self):
        for tool, args in (("registry.py", ["--local"]), ("registry.py", ["--registry"]),
                           ("project.py", [str(self.project), "--registry"]),
                           ("project.py", [str(self.project), "--local"])):
            with self.subTest(tool=tool, args=args):
                self.write_project()
                rc, out, err = run(tool, *args)
                self.assertEqual(rc, 2, err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(out["ok"], False)

    # --- explicit project validation ---

    def test_project_with_companion(self):
        self.write_companion()
        self.write_project()
        rc, out, _ = run("project.py", str(self.project), "--local", str(self.companion))
        self.assertEqual((rc, out["ok"]), (0, True), out)
        self.assertEqual(out["profiles"], [PID])

    def test_project_pin_mismatch(self):
        self.write_companion()
        self.write_project(pin="2.0.0")
        rc, out, _ = run("project.py", str(self.project), "--local", str(self.companion))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["project.version_pin_mismatch"])

    def test_unrelated_project_finding_keeps_its_attribution(self):
        """A project error that has nothing to do with the companion is reported as itself; the companion still loads."""
        self.write_companion()
        self.write_project(plugin="<0.0.1")
        rc, out, _ = run("project.py", str(self.project), "--local", str(self.companion))
        self.assertEqual(rc, 1)
        errs = [f for f in out["findings"] if f["severity"] == "error"]
        self.assertEqual([(f["path"], f["code"]) for f in errs], [("config.plugin_version", "project.incompatible_plugin")])
        self.assertEqual(out["profiles"], [PID])

    def test_unreadable_project(self):
        rc, out, _ = run("project.py", str(self.base / "no-such-project"))
        self.assertEqual((rc, out["ok"]), (2, False))
        (self.project / "hep-research.project.json").write_text("{")
        rc, out, _ = run("project.py", str(self.project))
        self.assertEqual((rc, out["ok"]), (2, False))

    # --- the same folder twice is one profile; two folders with one id are a conflict ---

    def test_same_folder_from_config_and_local(self):
        self.write_companion()
        os.symlink(self.companion, self.base / "alias")
        self.write_project(local=[os.path.relpath(self.companion, self.project)])
        for given in (self.companion, self.base / "alias", Path(str(self.companion) + "/")):
            with self.subTest(given=str(given)):
                rc, out, _ = run("project.py", str(self.project), "--local", str(given))
                self.assertEqual((rc, out["ok"]), (0, True), out)

    def test_same_folder_listed_twice(self):
        self.write_companion()
        rel = os.path.relpath(self.companion, self.project)
        self.write_project(local=[rel, rel + "/"])
        rc, out, _ = run("project.py", str(self.project))
        self.assertEqual((rc, out["ok"]), (0, True), out)
        rc, out, _ = run("registry.py", "--local", str(self.companion), "--local", str(self.base / "companion" / "." / "profile"))
        self.assertEqual((rc, out["ok"]), (0, True), out)

    def test_distinct_folders_same_id_conflict(self):
        self.write_companion()
        other = self.write_companion(self.base / "copy" / "profile")
        self.write_project(local=[os.path.relpath(other, self.project)])
        rc, out, _ = run("project.py", str(self.project), "--local", str(self.companion))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["registry.duplicate_id"])
        rc, out, _ = run("registry.py", "--local", str(self.companion), "--local", str(other))
        self.assertEqual(codes(out), ["registry.duplicate_id"])


if __name__ == "__main__":
    unittest.main()

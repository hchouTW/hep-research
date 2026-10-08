"""tools/release_manifest.py (AGENTIC-R5 T0.2): U10 identity reproducibility in clean copies, and the C10 rule that a
published release bundle cannot change (synthetic git repositories only)."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "release_manifest.py"
spec = importlib.util.spec_from_file_location("release_manifest", TOOL)
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)
HAVE_GIT = shutil.which("git") is not None


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false",
                           "-c", "tag.gpgsign=false", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          timeout=120)


def make_tree(root: Path, mode: int = 0o644) -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "hep-research", "version": "9.9.9"}\n')
    (root / "core").mkdir()
    (root / "core" / "a.py").write_text("x = 1\n")
    (root / "run.sh").write_text("#!/bin/sh\n")
    os.chmod(root / "run.sh", 0o755)
    for f in (root / "core" / "a.py", root / ".claude-plugin" / "plugin.json"):
        os.chmod(f, mode)


class IdentityU10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_copies_give_one_identity(self):
        a, b = self.d / "one", self.d / "deeper" / "two"
        make_tree(a, 0o644)
        make_tree(b, 0o600)  # different permissions apart from the execute bit do not matter
        (b / "core" / "__pycache__").mkdir()
        (b / "core" / "__pycache__" / "a.cpython-313.pyc").write_bytes(b"cache")
        (b / "release-manifests").mkdir()
        (b / "release-manifests" / "9.9.8.json").write_text("{}")
        ma, mb = rm.generate(a), rm.generate(b)
        self.assertEqual(ma["digest"], mb["digest"])
        self.assertEqual(len(ma["digest"]), 64)
        self.assertEqual([f["path"] for f in ma["files"]], [".claude-plugin/plugin.json", "core/a.py", "run.sh"])
        self.assertEqual({f["path"]: f["mode"] for f in ma["files"]}["run.sh"], "100755")

    def test_any_byte_or_execute_bit_changes_the_identity(self):
        a = self.d / "t"
        make_tree(a)
        before = rm.generate(a)
        (a / "core" / "a.py").write_text("x = 2\n")
        self.assertNotEqual(rm.generate(a)["digest"], before["digest"])
        rep = rm.verify(a, before)
        self.assertEqual(rep["differences"], [{"path": "core/a.py", "change": "content"}])
        (a / "core" / "a.py").write_text("x = 1\n")
        os.chmod(a / "core" / "a.py", 0o755)
        self.assertEqual(rm.verify(a, before)["differences"], [{"path": "core/a.py", "change": "mode"}])

    def test_symlink_is_refused(self):
        a = self.d / "t"
        make_tree(a)
        os.symlink("a.py", a / "core" / "b.py")
        with self.assertRaises(rm.RefusedFile):
            rm.generate(a)

    def test_tampered_manifest_is_refused(self):
        a = self.d / "t"
        make_tree(a)
        man = rm.generate(a)
        man["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            rm.verify(a, man)


@unittest.skipUnless(HAVE_GIT, "git is needed")
class PublishedImmutabilityC10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.plugin = self.repo / "plugins" / "hep-research"
        make_tree(self.plugin)
        (self.plugin / "tools").mkdir()
        shutil.copy2(TOOL, self.plugin / "tools" / "release_manifest.py")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "release 9.9.9")
        git(self.repo, "tag", "hep-research--v9.9.9")
        (self.plugin / "release-manifests").mkdir()
        man = rm.generate(self.plugin)
        (self.plugin / "release-manifests" / "9.9.9.json").write_text(json.dumps(man))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "record 9.9.9")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, *extra):
        p = subprocess.run([sys.executable, str(self.plugin / "tools" / "release_manifest.py"), "check-published", *extra],
                           cwd=self.plugin, capture_output=True, text=True, timeout=300)
        return p.returncode, json.loads(p.stdout)

    def test_published_tag_matches_and_unreleased_changes_are_free(self):
        (self.plugin / "core" / "a.py").write_text("x = 3  # Unreleased work\n")
        git(self.repo, "commit", "-qam", "work")
        code, rep = self.check("--base", self.base)
        self.assertEqual((code, rep["status"]), (0, "pass"), json.dumps(rep)[:1500])
        self.assertEqual([c["status"] for c in rep["checked"]], ["identical"])

    def test_moved_tag_fails(self):
        (self.plugin / "core" / "a.py").write_text("x = 4\n")
        git(self.repo, "commit", "-qam", "change")
        git(self.repo, "tag", "-f", "hep-research--v9.9.9")
        code, rep = self.check()
        self.assertEqual(code, 1)
        self.assertIn("differs", rep["problems"][0])

    def test_recorded_manifest_cannot_change(self):
        path = self.plugin / "release-manifests" / "9.9.9.json"
        path.write_text(path.read_text().replace('"9.9.9"', '"9.9.9-edited"'))
        git(self.repo, "commit", "-qam", "edit record")
        code, rep = self.check("--base", self.base)
        self.assertEqual(code, 1)
        self.assertTrue(any("was changed" in p for p in rep["problems"]), rep)


if __name__ == "__main__":
    unittest.main()

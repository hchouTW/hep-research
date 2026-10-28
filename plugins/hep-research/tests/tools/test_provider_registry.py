"""tools/provider_registry.py: the cr-provider/1 registry is generated from the 'provider' fields of adapter.json and
profile.json plus explicit user-supplied declarations, written outside the plugin, and refuses bad declarations,
duplicate ids, entrypoints outside their folder and links."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.provider.registry import load_registry  # noqa: E402
from tools.provider_registry import declaring_files  # noqa: E402

TOOL = ROOT / "tools" / "provider_registry.py"


def run(*argv):
    proc = subprocess.run([sys.executable, "-I", str(TOOL), *map(str, argv)], capture_output=True, text=True,
                          timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}, proc.stderr


def declared_ids() -> set[str]:
    ids = set()
    for _, manifest in declaring_files(ROOT):
        field = manifest.get("provider")
        if field is not None:
            ids |= {d["id"] for d in (field if isinstance(field, list) else [field])}
    return ids


class ProviderRegistryTests(unittest.TestCase):
    def setUp(self):
        self._workdir = tempfile.TemporaryDirectory()
        self.scratch = Path(self._workdir.name)

    def tearDown(self):
        self._workdir.cleanup()

    def user_declaration(self, name="mine", **changes) -> Path:
        folder = self.scratch / name
        folder.mkdir(exist_ok=True)
        (folder / "entry.py").write_text("print('provider')\n", encoding="utf-8")
        decl = {"id": f"user-{name}", "entrypoint": "entry.py", "protocol": "cr-provider/1", "version": "0.0.1",
                "domain": {"L_kpc": {"min": 1, "max": 10}}, "observables": ["B/C"], "axes": ["ekn"],
                "decomposable": False, "deterministic": True, "output_units": {"ratio": "1"}}
        decl.update(changes)
        path = folder / "declaration.json"
        path.write_text(json.dumps(decl), encoding="utf-8")
        return path

    def test_write_lists_every_declared_provider(self):
        code, out, err = run("--write", self.scratch / "registry.json")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "written")
        entries = load_registry(self.scratch / "registry.json")
        self.assertEqual(set(entries), declared_ids())
        self.assertIn("cr-secondary-ratio-closed-form", entries)
        for entry in entries.values():
            self.assertTrue(entry.entrypoint.is_absolute() and entry.entrypoint.is_file())
            self.assertFalse(entry.user_supplied)

    def test_check_writes_nothing(self):
        code, out, _ = run("--check")
        self.assertEqual((code, out["status"]), (0, "ok"))

    def test_registry_is_never_written_inside_the_plugin(self):
        code, out, _ = run("--write", ROOT / "registry.json")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        self.assertFalse((ROOT / "registry.json").exists())

    def test_user_supplied_provider_is_listed_explicitly(self):
        code, out, err = run("--write", self.scratch / "registry.json", "--user-provider", self.user_declaration())
        self.assertEqual(code, 0, err)
        entries = load_registry(self.scratch / "registry.json")
        self.assertTrue(entries["user-mine"].user_supplied)
        self.assertEqual(entries["user-mine"].component, "user-supplied:declaration.json")

    def test_refusals(self):
        cases = {
            "no version": self.user_declaration("nov", version=None),
            "bad protocol": self.user_declaration("proto", protocol="cr-provider/9"),
            "leaves folder": self.user_declaration("up", entrypoint="../mine/entry.py"),
            "missing entry": self.user_declaration("gone", entrypoint="absent.py"),
            "duplicate id": self.user_declaration("dup", id="cr-secondary-ratio-closed-form"),
        }
        # a declaration with version null: drop the key instead
        decl = json.loads(cases["no version"].read_text())
        decl.pop("version")
        cases["no version"].write_text(json.dumps(decl))
        link = self.user_declaration("link", entrypoint="linked.py")
        os.symlink(link.parent / "entry.py", link.parent / "linked.py")
        cases["link"] = link
        for name, path in cases.items():
            with self.subTest(case=name):
                code, out, _ = run("--write", self.scratch / "registry.json", "--user-provider", path)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")
                self.assertTrue(out["problems"])

    def test_help(self):
        proc = subprocess.run([sys.executable, "-I", str(TOOL), "--help"], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--user-provider", proc.stdout)


if __name__ == "__main__":
    unittest.main()

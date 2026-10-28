"""AC23/AC26: every adapter declares its tools, environment and status; no adapter claims more than its tests show."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider.protocol import check_declaration, declarations_of  # noqa: E402

STATUSES = set(json.loads((ROOT / "contracts" / "vocab" / "core.json").read_text(encoding="utf-8"))["vocabularies"]["capability_statuses"])
DEMONSTRATED = {"demonstrated-on-synthetic-data", "tested-in-declared-environment"}
ORDER = ["unavailable", "proposed", "documented", "demonstrated-on-synthetic-data", "tested-in-declared-environment"]


class AdapterDeclarationTests(unittest.TestCase):
    def test_every_adapter_is_declared_honestly(self):
        dirs = sorted(p for p in (ROOT / "adapters").iterdir() if p.is_dir() and p.name != "__pycache__")
        self.assertTrue(dirs)
        for d in dirs:
            with self.subTest(adapter=d.name):
                doc = json.loads((d / "adapter.json").read_text(encoding="utf-8"))
                self.assertEqual(doc["id"], f"adapter:{d.name}")
                self.assertIn(doc["status"], STATUSES)
                for a in doc["assets"]:
                    self.assertTrue((d / a).is_file(), a)
                for t in doc["tests"]:
                    self.assertTrue((d / t).is_file(), t)
                tool_statuses = [t.get("status", doc["status"]) for t in doc["tools"]]
                for tool, st in zip(doc["tools"], tool_statuses):
                    self.assertIn(st, STATUSES)
                    if st in DEMONSTRATED:  # a tool above "documented" was run: tests, environment and versions
                        self.assertTrue(doc["tests"], f"{tool['name']}: a demonstrated or tested tool needs tests")
                        self.assertNotIn("none declared", doc["environment"])
                        self.assertTrue(tool["tested_versions"], tool["name"])
                    else:
                        self.assertFalse(tool["tested_versions"], f"{tool['name']}: versions listed but not run")
                # the adapter never claims more than its least-tested tool
                self.assertEqual(doc["status"], min(tool_statuses, key=ORDER.index))

    def test_provider_fields_are_valid_declarations(self):
        """The optional 'provider' field (cr-provider/1, contracts 3.14.0) of adapter.json and profile.json: each
        declaration passes the contract schema and the core rules, its entrypoint is a regular file inside the declaring
        folder, and provider ids are unique across the plugin (tools/provider_registry.py builds the registry from them)."""
        manifests = sorted((ROOT / "adapters").glob("*/adapter.json"))
        registry = json.loads((ROOT / "profiles" / "registry.json").read_text(encoding="utf-8"))
        manifests += [ROOT / "profiles" / p["path"] / "profile.json" for p in registry["profiles"]]
        ids = []
        for path in manifests:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if "provider" not in doc:
                continue
            with self.subTest(manifest=str(path.relative_to(ROOT))):
                rep = validate(doc["provider"], {"$ref": "cr_provider.json#/$defs/declarations"}, Vocabulary())
                self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
                for decl in declarations_of(doc["provider"]):
                    self.assertEqual(check_declaration(decl), [])
                    entry = path.parent / decl["entrypoint"]
                    self.assertTrue(entry.is_file() and not entry.is_symlink(), decl["entrypoint"])
                    self.assertIn(path.parent.resolve(), entry.resolve().parents)
                    ids.append(decl["id"])
        self.assertIn("cr-secondary-ratio-closed-form", ids)
        self.assertEqual(len(ids), len(set(ids)), f"provider ids declared twice: {ids}")

    def test_capability_matrix_matches_declarations(self):
        matrix = (ROOT / "docs" / "capability-matrix.md").read_text(encoding="utf-8")
        for f in (ROOT / "adapters").glob("*/adapter.json"):
            doc = json.loads(f.read_text(encoding="utf-8"))
            row = next(l for l in matrix.splitlines() if l.startswith(f"| `adapters/{f.parent.name}`"))
            self.assertIn(f"| {doc['status']} |", row)


if __name__ == "__main__":
    unittest.main()

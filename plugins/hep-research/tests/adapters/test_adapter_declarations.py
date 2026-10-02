"""AC23/AC26: every adapter declares its tools, environment and status; no adapter claims more than its tests show."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUSES = set(json.loads((ROOT / "contracts" / "vocab" / "core.json").read_text(encoding="utf-8"))["vocabularies"]["capability_statuses"])
DEMONSTRATED = {"demonstrated-on-synthetic-data", "tested-in-declared-environment"}


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
                if doc["status"] in DEMONSTRATED:
                    self.assertTrue(doc["tests"], "a demonstrated or tested adapter needs tests")
                    self.assertNotIn("none declared", doc["environment"])
                    for t in doc["tests"]:
                        self.assertTrue((d / t).exists(), t)
                    self.assertTrue(all(t["tested_versions"] for t in doc["tools"]))

    def test_capability_matrix_matches_declarations(self):
        matrix = (ROOT / "docs" / "capability-matrix.md").read_text(encoding="utf-8")
        for f in (ROOT / "adapters").glob("*/adapter.json"):
            doc = json.loads(f.read_text(encoding="utf-8"))
            row = next(l for l in matrix.splitlines() if l.startswith(f"| `adapters/{f.parent.name}`"))
            self.assertIn(f"| {doc['status']} |", row)


if __name__ == "__main__":
    unittest.main()

"""tools/reference_inventory.py: the committed inventory is current, a duplicated reference is
listed as an overlapping pair, and --check fails when a reference is added."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("reference_inventory", PLUGIN / "tools" / "reference_inventory.py")
ri = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ri)


class ReferenceInventoryTests(unittest.TestCase):
    def test_committed_inventory_is_current(self):
        self.assertEqual(ri.main(["--check"]), 0)

    def test_duplicate_is_detected_and_check_fails_when_a_reference_is_added(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for skill in ("alpha", "beta"):
                (root / "skills" / skill / "references").mkdir(parents=True)
                (root / "skills" / skill / "SKILL.md").write_text("[a](references/one.md)\n")
            text = " ".join(f"word{i}" for i in range(400))
            (root / "skills" / "alpha" / "references" / "one.md").write_text(text)
            (root / "skills" / "beta" / "references" / "copy-of-one.md").write_text(text + " extra tail words here")
            (root / "skills" / "beta" / "references" / "other.md").write_text(" ".join(f"x{i}" for i in range(400)))
            inv = ri.build(root, 0.08, with_git=False)
            self.assertEqual(len(inv["references"]), 3)
            pair = inv["overlap_pairs"][0]
            self.assertEqual({Path(pair["a"]).name, Path(pair["b"]).name}, {"one.md", "copy-of-one.md"})
            self.assertGreater(pair["jaccard"], 0.9)
            self.assertTrue(next(r for r in inv["references"] if r["path"].endswith("alpha/references/one.md"))["linked_from_skill_md"])
            (root / "docs").mkdir()
            out = root / "docs" / "inv.json"  # docs/ is not searched for citations, as in the plugin
            out.write_text(json.dumps(inv))
            old = ri.ROOT
            ri.ROOT = root
            try:
                self.assertEqual(ri.main(["--check", "--json", str(out)]), 0)
                (root / "skills" / "beta" / "references" / "new.md").write_text("new reference")
                self.assertEqual(ri.main(["--check", "--json", str(out)]), 1)
            finally:
                ri.ROOT = old


if __name__ == "__main__":
    unittest.main()

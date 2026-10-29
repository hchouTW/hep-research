"""C3: the preservation checklist names every item a reproduction needs (environment, input checksums, recipe, result
bindings, re-foldable products), every link and plugin path it cites resolves, and it no longer teaches the retired
cross-artifact check."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-computing" / "references" / "preservation-checklist.md"


class PreservationChecklist(unittest.TestCase):
    def setUp(self):
        self.text = REF.read_text(encoding="utf-8")

    def test_every_required_item_is_listed(self):
        for item in ("environment_manifest.py", "input_manifest", "recipe", "computational-run", "re-fold", "rehears"):
            with self.subTest(item=item):
                self.assertIn(item, self.text)

    def test_links_resolve(self):
        links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", self.text)
        self.assertGreater(len(links), 3)
        for link in links:
            with self.subTest(link=link):
                self.assertTrue((REF.parent / link).resolve().exists(), link)

    def test_plugin_paths_exist(self):
        paths = re.findall(r"`<plugin root>/([^`\s]+)`", self.text)
        self.assertGreater(len(paths), 3)
        for rel in paths:
            with self.subTest(path=rel):
                self.assertTrue((PLUGIN / rel).exists(), rel)

    def test_retired_check_is_not_taught(self):
        for retired in ("analysis_check.py", "analysis_bundle_v2", "semantic lock"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, self.text)

    def test_routed_from_skill(self):
        self.assertIn("references/preservation-checklist.md", (PLUGIN / "skills" / "hep-computing" / "SKILL.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

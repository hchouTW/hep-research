"""Each SKILL.md Resources section routes to files that exist: Markdown links, folders and named scripts."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))


def resources(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    return text.split("## Resources", 1)[1].split("\n## ", 1)[0]


class ResourceRouteTests(unittest.TestCase):
    def test_seven_skills_have_resources(self):
        self.assertEqual(len(SKILLS), 7)
        for s in SKILLS:
            self.assertNotIn("arrive in M2", resources(s), s.name)

    def test_links_resolve(self):
        for s in SKILLS:
            for target in re.findall(r"\]\(([^)#]+)\)", resources(s)):
                self.assertTrue((s / target).is_file(), f"{s.name}: {target}")

    def test_named_scripts_and_paths_exist(self):
        for s in SKILLS:
            sec = resources(s)
            for path in re.findall(r"<plugin root>/([\w./-]+)", sec):
                self.assertTrue((PLUGIN / path.rstrip("/.")).exists(), f"{s.name}: {path}")
            for name in re.findall(r"`([a-z0-9_]+\.(?:py|sh))`", sec):
                found = list(PLUGIN.glob(f"skills/*/scripts/{name}")) + list(PLUGIN.glob(f"core/**/{name}"))
                self.assertTrue(found, f"{s.name}: {name}")


if __name__ == "__main__":
    unittest.main()

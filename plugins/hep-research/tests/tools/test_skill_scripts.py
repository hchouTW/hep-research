"""tools/skill_scripts.json lists every skill script (tools/skill_scripts.py): the committed file equals a fresh
generation, no new unresolved name appears unnoticed, and each entry's depth N reaches the plugin root."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location("skill_scripts", ROOT / "tools" / "skill_scripts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SkillScriptList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = generator()
        cls.fresh = cls.gen.generate(ROOT)
        cls.committed = json.loads((ROOT / "tools" / "skill_scripts.json").read_text(encoding="utf-8"))

    def test_no_new_unresolved_name(self):
        known = {(u["skill"], u["name"]) for u in self.committed["unresolved"]}
        new = [u for u in self.fresh["unresolved"] if (u["skill"], u["name"]) not in known]
        self.assertEqual(new, [], "a skill names a script that resolves to no file or to several: fix the text or "
                                  "the name, or regenerate with python3 tools/skill_scripts.py and review the entry")

    def test_committed_list_is_up_to_date(self):
        self.assertEqual(self.gen.render(self.committed), self.gen.render(self.fresh),
                         "tools/skill_scripts.json is out of date: run python3 tools/skill_scripts.py")

    def test_entries_are_scripts_with_a_correct_depth(self):
        paths = [s["path"] for s in self.committed["scripts"]]
        self.assertIn("skills/hep-review/scripts/review.py", paths)
        self.assertIn("skills/hep-authoring/scripts/render_results.py", paths)
        for s in self.committed["scripts"]:
            with self.subTest(path=s["path"]):
                f = ROOT / s["path"]
                self.assertTrue(f.is_file())
                self.assertEqual(f.resolve().parents[s["depth"]], ROOT.resolve())
                self.assertRegex(f.read_text(encoding="utf-8"), r"(?m)^if __name__ == [\"']__main__[\"']\s*:")
                self.assertIsNone(self.gen.excluded_reason(s["path"]))

    def test_exclusions_are_kept_out(self):
        paths = {s["path"] for s in self.committed["scripts"]}
        for rel in self.gen.EXCLUDED:
            self.assertNotIn(rel, paths)
            self.assertTrue((ROOT / rel).is_file(), f"{rel}: excluded file no longer exists; drop the exclusion")
        self.assertFalse(any(p.startswith(("tests/", "examples/", "profiles/")) for p in paths))


if __name__ == "__main__":
    unittest.main()

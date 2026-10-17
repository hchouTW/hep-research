"""B-02: each SKILL.md has, under '## Resources', a compact routing table 'request type -> one file or script' of
1.5-2.5 KB, every file it names exists, and every SKILL.md stays at or under 11,264 bytes."""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent for p in (PLUGIN / "skills").glob("*/SKILL.md"))
HEADER = "| Request | Read or run |\n|---|---|\n"


def table(skill_dir: Path) -> str:
    sec = (skill_dir / "SKILL.md").read_text(encoding="utf-8").split("## Resources", 1)[1]
    start = sec.index(HEADER)
    rows = []
    for line in sec[start:].splitlines(keepends=True):
        if not line.startswith("|"):
            break
        rows.append(line)
    return "".join(rows)


class RoutingTables(unittest.TestCase):
    def test_size_of_skill_md(self):
        for s in SKILLS:
            with self.subTest(skill=s.name):
                self.assertLessEqual(len((s / "SKILL.md").read_bytes()), 11264)

    def test_table_present_and_compact(self):
        for s in SKILLS:
            with self.subTest(skill=s.name):
                t = table(s)
                self.assertTrue(1536 <= len(t.encode()) <= 2560, len(t.encode()))
                for row in t.splitlines()[2:]:
                    self.assertEqual(row.count("|"), 3, row)

    def test_every_named_file_exists(self):
        for s in SKILLS:
            t = table(s)
            for target in re.findall(r"\]\(([^)#]+)", t):
                with self.subTest(skill=s.name, link=target):
                    self.assertTrue((s / target).is_file())
            for token in re.findall(r"`([^`]+)`", t):
                if token.startswith("<plugin root>/"):
                    path = PLUGIN / token.split("/", 1)[1]
                elif "/" in token:
                    path = s / token
                elif token.endswith((".py", ".sh")):
                    found = list(PLUGIN.glob(f"skills/{s.name}/scripts/{token}"))
                    with self.subTest(skill=s.name, script=token):
                        self.assertTrue(found, token)
                    continue
                else:
                    continue
                with self.subTest(skill=s.name, path=token):
                    self.assertTrue(path.exists(), path)


class QuickQuestionLoad(unittest.TestCase):
    """B-03: for a quick question, SKILL.md plus its entry reference (the first reference its Resources section links)
    is at most 25 KB (25,600 bytes)."""

    def test_skill_plus_entry_reference(self):
        import sys
        sys.path.insert(0, str(PLUGIN))
        from tools.reference_inventory import entry_references
        entries = entry_references(PLUGIN)
        self.assertEqual(len(entries), len(SKILLS))
        for rel in entries:
            skill = PLUGIN / "skills" / Path(rel).parts[1]
            with self.subTest(entry=rel):
                self.assertLessEqual(len((skill / "SKILL.md").read_bytes()) + len((PLUGIN / rel).read_bytes()), 25600)

if __name__ == "__main__":
    unittest.main()

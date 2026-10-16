"""B-05: tools/reference_inventory.py reports, as warnings that never change its exit code, the routing part of an
entry reference above 4 KB and any reference above 24 KB. The entry reference is the first reference the SKILL.md's
"## Resources" section links; its routing part is the text before the first level-2 heading plus every level-2
section whose heading names routing, an index, contents, when to read the file, or choosing a tool."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import reference_inventory as ri  # noqa: E402


def tree(td: Path, routing_bytes: int, other_bytes: int, extra_bytes: int) -> Path:
    s = td / "skills" / "demo"
    (s / "references").mkdir(parents=True)
    (s / "SKILL.md").write_text("---\nname: demo\n---\n## Resources\n\nStart with [the guide](references/guide.md).\n")
    (s / "references" / "guide.md").write_text("# Guide\n\n## Task routing\n\n" + "r" * routing_bytes + "\n\n## Method\n\n"
                                               + "m" * other_bytes + "\n")
    (s / "references" / "big.md").write_text("# Big\n\n" + "b" * extra_bytes + "\n")
    return td


class SoftBudget(unittest.TestCase):
    def test_within_budget(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(ri.soft_budget(tree(Path(td), 1000, 20000, 1000)), [])

    def test_routing_part_and_size_warnings(self):
        with tempfile.TemporaryDirectory() as td:
            warns = ri.soft_budget(tree(Path(td), 5000, 100, 25000))
        self.assertEqual(len(warns), 2, warns)
        self.assertTrue(any("guide.md" in w and "routing part" in w for w in warns))
        self.assertTrue(any("big.md" in w and "24" in w for w in warns))

    def test_cli_reports_warnings_without_failing(self):
        res = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "reference_inventory.py"), "--check"],
                             capture_output=True, text=True, timeout=300, cwd=ROOT)
        out = json.loads(res.stdout)
        self.assertIn("warnings", out)
        self.assertEqual(res.returncode, 0 if out["status"] == "pass" else 1)
        self.assertEqual(out["status"], "pass", out)

    def test_entry_references_are_found(self):
        entries = ri.entry_references(ROOT)
        self.assertEqual(len(entries), len(list((ROOT / "skills").glob("*/SKILL.md"))))
        self.assertIn("skills/hep-statistics/references/core-stats-guide.md", entries)


if __name__ == "__main__":
    unittest.main()

"""X2: one owner per topic. tools/reference_inventory.py turns its overlap report into an error when two references
owned by different skills overlap at or above the threshold (Jaccard of 8-word shingles, or containment 0.15): the
generate and --check modes report the pair under "problems" and exit 1. Pairs inside one skill stay listed only.
Before X2 every overlapping pair was a listing, never a failure."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import reference_inventory as ri  # noqa: E402

SHARED = " ".join(f"word{i} shared physics paragraph about the transport equation term {i}" for i in range(40))


def tree(td: Path, cross: bool) -> Path:
    for skill, files in (("alpha", {"a.md": SHARED, "a2.md": SHARED + " alpha only"}),
                         ("beta", {"b.md": SHARED if cross else "an unrelated text " * 50})):
        s = td / "skills" / skill
        (s / "references").mkdir(parents=True)
        (s / "SKILL.md").write_text(f"---\nname: {skill}\n---\n## Resources\n")
        for name, text in files.items():
            (s / "references" / name).write_text(f"# {name}\n\n{text}\n")
    return td


def run(td: Path, *extra: str) -> tuple[int, dict]:
    r = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "reference_inventory.py"), "--root", str(td),
                        "--json", str(td / "inv.json"), "--md", str(td / "inv.md"), *extra],
                       capture_output=True, text=True, timeout=120)
    return r.returncode, json.loads(r.stdout)


class CrossSkillOverlap(unittest.TestCase):
    def test_same_skill_overlap_is_listed_not_an_error(self):
        with tempfile.TemporaryDirectory() as td:
            inv = ri.build(tree(Path(td), cross=False), 0.08, with_git=False)
            self.assertTrue(inv["overlap_pairs"])
            self.assertEqual(ri.cross_skill_overlaps(inv), [])
            code, out = run(Path(td))
            self.assertEqual(code, 0, out)

    def test_cross_skill_overlap_fails_generate_and_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = tree(Path(td), cross=True)
            pairs = ri.cross_skill_overlaps(ri.build(root, 0.08, with_git=False))
            self.assertTrue(pairs)
            self.assertTrue(all(p["a"].split("/")[1] != p["b"].split("/")[1] for p in pairs))
            code, out = run(root)
            self.assertEqual(code, 1, out)
            self.assertEqual(out["status"], "fail")
            self.assertTrue(any("beta/references/b.md" in p for p in out["problems"]), out)
            code, out = run(root, "--check")
            self.assertEqual(code, 1, out)
            self.assertTrue(any("one owner per topic" in p for p in out["problems"]), out)

    def test_plugin_has_no_cross_skill_overlap(self):
        inv = json.loads((ROOT / "docs" / "reference-inventory.json").read_text())
        self.assertEqual(ri.cross_skill_overlaps(inv), [])


if __name__ == "__main__":
    unittest.main()

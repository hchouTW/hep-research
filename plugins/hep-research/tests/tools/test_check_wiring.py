"""tools/check_wiring.py (architecture step 1): the committed tree has no new wiring gap and no stale known gap; on a
small synthetic plugin, an unlinked page is a new gap (exit 1) until it is linked, listed or removed, and each rule
(R1 reachability with hubs and pointer pages, R2 CLI dictionary, R3 README counts, R4 CHANGELOG) finds what it
should."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import check_wiring as cw  # noqa: E402

# The known gaps when the lint came in (0.28.0 + Th13, after the B4a fixes), as the first 12 hex digits of the
# SHA-256 of each key (hashed so that this file does not count as citing the pages). The known-gaps file may only
# lose entries: a new gap is fixed, never listed. Shrink this baseline with the file; never add to it.
BASELINE_GAPS = {
    "14fb707b539c",
    "21acb8095231",
    "3a6c8e4dcebe",
    "48672cdcaa10",
    "4d07b949fdbe",
    "51362bd36aa2",
    "55f400a8a324",
    "61c0117e004e",
    "6443da68f956",
    "89919072da48",
    "b9f5ee00d934",
    "bdf9e4edee3f",
    "be78eb14877d",
    "d4207363aae1",
    "d7e8b2a2da54",
    "f0e2caf725de",
    "f13e5b167549",
}

TABLE = "## Resources\n\n| Request | Read or run |\n|---|---|\n| Entry | [entry](references/entry.md) |\n"


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cw.main(argv)
    return code, json.loads(buf.getvalue())


class CommittedTree(unittest.TestCase):
    def test_no_new_gap_and_no_stale_entry(self):
        code, doc = run([])
        self.assertEqual(doc["new_gaps"], [], "a new wiring gap: fix it (docs/maintenance.md, Adding a topic)")
        self.assertEqual(code, 0)
        self.assertEqual(doc["known_gaps_stale"], [], "delete fixed gaps from tools/wiring_known_gaps.json")

    def test_known_gaps_only_shrink(self):
        gaps = json.loads(cw.KNOWN_GAPS.read_text(encoding="utf-8"))["gaps"]
        added = [g for g in gaps if hashlib.sha256(g.encode()).hexdigest()[:12] not in BASELINE_GAPS]
        self.assertEqual(added, [], "fix a new gap instead of listing it")

    def test_every_hub_and_readme_row_names_a_real_skill(self):
        gaps = json.loads(cw.KNOWN_GAPS.read_text(encoding="utf-8"))
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertLessEqual(set(gaps["hubs"]) | set(gaps["readme_counts"]), skills)
        self.assertEqual(gaps["gaps"], sorted(set(gaps["gaps"])), "keep gaps sorted and unique")


class SyntheticPlugin(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root / ".claude-plugin").mkdir()
        (self.root / ".claude-plugin" / "plugin.json").write_text('{"version": "1.2.0"}', encoding="utf-8")
        self.skill = self.root / "skills" / "demo"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "scripts").mkdir()
        (self.skill / "SKILL.md").write_text("# Demo\n\n" + TABLE, encoding="utf-8")
        (self.skill / "README.md").write_text("| `references/` | two references |\n", encoding="utf-8")
        self.page("entry.md", "# Entry\n\n## Routing\n\n- [topic hub](hub.md)\n\n## Body\n\n- [deep](deep.md)\n")
        self.page("hub.md", "# Hub\n")
        self.gaps = {"hubs": {}, "pointers": {}, "gaps": [],
                     "readme_counts": {"demo": [{"row": "references/", "globs": ["references/*.md"]}]}}

    def page(self, name, text):
        (self.skill / "references" / name).write_text(text, encoding="utf-8")

    def check(self, *extra):
        path = self.root / "gaps.json"
        path.write_text(json.dumps(self.gaps), encoding="utf-8")
        return run(["--root", str(self.root), "--known-gaps", str(path), *extra])

    def test_clean_tree_passes(self):
        code, doc = self.check()
        self.assertEqual((code, doc["status"], doc["findings"]), (0, "pass", []))

    def test_unlinked_page_is_a_new_gap_until_linked_listed_or_removed(self):
        self.page("orphan.md", "# Orphan\n")
        self.gaps["readme_counts"] = {}
        code, doc = self.check()
        self.assertEqual((code, doc["new_gaps"]), (1, ["R1:skills/demo/references/orphan.md"]))
        self.assertIsNone(doc["findings"][0]["steps"])
        self.gaps["gaps"] = ["R1:skills/demo/references/orphan.md"]       # recorded: report only
        code, doc = self.check()
        self.assertEqual((code, doc["status"], doc["known_gaps_applied"]), (0, "known-gaps", self.gaps["gaps"]))
        (self.skill / "references" / "orphan.md").unlink()                # fixed: the entry is stale, never an error
        code, doc = self.check()
        self.assertEqual((code, doc["status"], doc["known_gaps_stale"]), (0, "pass", self.gaps["gaps"]))

    def test_body_of_entry_is_two_steps_and_back_ticked_names_count(self):
        self.page("deep.md", "# Deep\n")
        self.gaps["readme_counts"] = {}
        code, doc = self.check()
        self.assertEqual([(f["key"], f["steps"]) for f in doc["findings"]], [("R1:skills/demo/references/deep.md", 2)])
        self.page("hub.md", "# Hub\n\nSee `deep.md`.\n")
        self.gaps["hubs"] = {"demo": ["references/hub.md"]}
        self.assertEqual(self.check()[0], 0)

    def test_hub_must_be_one_step_away(self):
        self.page("deep.md", "# Deep\n\n[far](far.md)\n")
        self.page("far.md", "# Far\n")
        self.gaps.update(readme_counts={}, hubs={"demo": ["references/deep.md"]})
        code, doc = self.check()
        self.assertEqual(code, 1)
        self.assertIn("R1:hub:demo/references/deep.md", doc["new_gaps"])
        self.assertIn("R1:skills/demo/references/far.md", doc["new_gaps"])

    def test_pointer_page_needs_a_removal_release_and_expires(self):
        self.page("old.md", "# Old topic (moved)\n\nNow in [entry](entry.md).\n")
        self.gaps["readme_counts"] = {}
        self.assertEqual(self.check()[1]["new_gaps"], ["R1:pointer-unrecorded:skills/demo/references/old.md"])
        self.gaps["pointers"] = {"skills/demo/references/old.md": {"remove_in": "1.3.0"}}
        self.assertEqual(self.check()[0], 0)
        self.gaps["pointers"]["skills/demo/references/old.md"]["remove_in"] = "1.2.0"
        self.assertEqual(self.check()[1]["new_gaps"], ["R1:pointer-expired:skills/demo/references/old.md"])

    def test_readme_count(self):
        self.page("deep.md", "# Deep\n")
        self.page("hub.md", "# Hub\n\n[deep](deep.md)\n")
        self.gaps["hubs"] = {"demo": ["references/hub.md"]}
        code, doc = self.check()
        self.assertEqual((code, doc["new_gaps"]), (1, ["R3:demo:references/"]))
        self.assertIn("README says 2", doc["findings"][0]["detail"])
        (self.skill / "README.md").write_text("| `references/` | three references |\n", encoding="utf-8")
        self.assertEqual(self.check()[0], 0)

    def test_number_words(self):
        for text, n in (("forty-nine references", 49), ("thirteen method references", 13), ("twenty helpers", 20),
                        ("one reference", 1), ("seventy-two x", 72), ("references", None), ("eleven-ish", None)):
            with self.subTest(text=text):
                self.assertEqual(cw.number_word(text), n)

    def test_changelog_since(self):
        def git(*args):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, timeout=60)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "capability-map.json").write_text('{"capabilities": [{"id": "a"}]}', encoding="utf-8")
        (self.root / "docs" / "capability-matrix.md").write_text("| A | x |\n", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## 1.2.0\n\n- old\n", encoding="utf-8")
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                              timeout=60).stdout.strip()
        self.page("hub.md", "# Hub\n\n[new](new-topic.md)\n")
        self.page("new-topic.md", "# New topic\n")
        (self.skill / "scripts" / "new_tool.py").write_text("print(1)\n", encoding="utf-8")
        (self.root / "docs" / "capability-map.json").write_text('{"capabilities": [{"id": "a"}, {"id": "b"}]}',
                                                               encoding="utf-8")
        self.gaps.update(readme_counts={}, hubs={"demo": ["references/hub.md"]})
        code, doc = self.check("--since", base)
        self.assertEqual(sorted(doc["new_gaps"]), ["R4:changelog:skills/demo/references/new-topic.md",
                                                   "R4:changelog:skills/demo/scripts/new_tool.py", "R4:matrix:b"])
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- `new-topic.md`, `new_tool.py`\n\n"
                                                "## 1.2.0\n\n- old\n", encoding="utf-8")
        (self.root / "docs" / "capability-matrix.md").write_text("| A | x |\n| B | y |\n", encoding="utf-8")
        code, doc = self.check("--since", base)
        self.assertEqual((code, doc["findings"]), (0, []))
        self.assertEqual(self.check("--since", "no-such-rev")[0], 2)


    def test_names_in_fenced_code_do_not_route(self):
        self.page("hub.md", "# Hub\n\n```\nsee `deep.md`\n```\n")
        self.page("deep.md", "# Deep\n")
        self.gaps.update(readme_counts={}, hubs={"demo": ["references/hub.md"]})
        self.assertEqual(self.check()[1]["new_gaps"], ["R1:skills/demo/references/deep.md"])

    def test_skill_without_resources_is_bad_input(self):
        (self.skill / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
        self.assertEqual(self.check()[0], 2)


class CliDictionary(unittest.TestCase):
    def test_list_reason_and_file_reading_script_are_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skills" / "demo" / "scripts").mkdir(parents=True)
            reader = root / "skills" / "demo" / "scripts" / "reader.py"
            reader.write_text("import argparse, json\np = argparse.ArgumentParser()\n"
                              "p.add_argument('--table', help='JSON table file')\np.add_argument('--n', type=int)\n"
                              "a = p.parse_args()\nprint(json.load(open(a.table)))\n", encoding="utf-8")
            numbers = root / "skills" / "demo" / "scripts" / "numbers.py"
            numbers.write_text("import argparse\np = argparse.ArgumentParser()\np.add_argument('--x', type=float)\n"
                               "p.add_argument('--out', help='output file')\nopen(p.parse_args().out, 'w')\n",
                               encoding="utf-8")
            self.assertEqual(cw.reads_file_argument(reader), ["--table"])
            self.assertEqual(cw.reads_file_argument(numbers), [])
            writer = root / "skills" / "demo" / "scripts" / "writer.py"
            writer.write_text("import argparse, pathlib\np = argparse.ArgumentParser()\n"
                              "p.add_argument('--table', help='table file to write')\n"
                              "pathlib.Path(p.parse_args().table).open('w')\n", encoding="utf-8")
            self.assertEqual(cw.reads_file_argument(writer), [])
            found = cw.check_cli(root, None, {}, {"skills/demo/scripts/reader.py": "numbers on the command line",
                                                  "skills/demo/scripts/numbers.py": ["--x", "1"]})
            self.assertEqual([f["key"] for f in found], ["R2:reason:skills/demo/scripts/numbers.py",
                                                         "R2:reads-file:skills/demo/scripts/reader.py"])


if __name__ == "__main__":
    unittest.main()

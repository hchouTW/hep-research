"""make_name_variant.py: a renamed scratch copy of the plugin for the name comparison of the communication split
(plan 10.2), and run_routing_eval.py reading the skill names of the copy it is pointed at. No model calls."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import make_name_variant as mnv
import run_routing_eval as rre


class Rename(unittest.TestCase):
    def test_names_and_underscored_names_only_as_whole_words(self):
        m = {"hep-citations": "hep-sources", "hep-authoring": "hep-manuscript"}
        text = "hep-citations, `hep-authoring`; tests/skills/hep_authoring/x.py; hep-literature-guide; xhep-writing"
        self.assertEqual(mnv.rename_text(text, m),
                         "hep-sources, `hep-manuscript`; tests/skills/hep_manuscript/x.py; hep-literature-guide; xhep-writing")

    def test_involved_ids(self):
        cases = [{"id": "a", "expected_primary": "hep-sources"}, {"id": "b", "expected_primary": "hep-theory", "not": "hep-sources"},
                 {"id": "c", "expected_primary": "hep-theory", "chain": ["hep-theory", "hep-manuscript"]},
                 {"id": "d", "expected_primary": "hep-theory", "turns": [{"expected": "hep-manuscript"}]},
                 {"id": "e", "expected_primary": "hep-theory", "also_accept": ["hep-sources"]},
                 {"id": "f", "expected_primary": "hep-theory"}]
        self.assertEqual(mnv.involved_ids(cases, {"hep-sources", "hep-manuscript"}), ["a", "b", "c", "d", "e"])

    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = mnv.main(list(argv))
        return code, json.loads(out.getvalue())

    def test_bad_input(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self.run_main("--literature", "Sources", "--writing", "hep-x", "--out", f"{td}/o")[0], 2)
            self.assertEqual(self.run_main("--literature", "hep-theory", "--writing", "hep-x", "--out", f"{td}/o")[0], 2)
            self.assertEqual(self.run_main("--literature", "hep-x", "--writing", "hep-x", "--out", f"{td}/o")[0], 2)
            self.assertEqual(self.run_main("--literature", "hep-x", "--writing", "hep-y", "--out", td)[0], 2)

    def test_copy_is_renamed_and_routes_statically(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "variant"
            code, rep = self.run_main("--literature", "hep-sources", "--writing", "hep-manuscript", "--out", str(out))
            self.assertEqual(code, 0, rep)
            self.assertTrue((out / "skills" / "hep-sources" / "SKILL.md").is_file())
            self.assertFalse((out / "skills" / "hep-authoring").exists())
            self.assertTrue((out / "tests" / "skills" / "hep_manuscript").is_dir())
            self.assertIn("name: hep-manuscript", (out / "skills" / "hep-manuscript" / "SKILL.md").read_text(encoding="utf-8"))
            self.assertGreater(rep["cases_involving_the_skills"], 40)
            self.assertEqual(rre.skills_of(out)[-3:], ["hep-sources", "hep-statistics", "hep-theory"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the task template's section contract (check_template_sections in scripts/lint_task.py).

Run from the skill directory with python3 -m unittest discover -s tests -v.
Standard library only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-computing"
sys.path.insert(0, str(ROOT / "scripts"))

import lint_task  # noqa: E402


class ExtractHeadingsTests(unittest.TestCase):
    def test_extracts_all_three_levels_in_order(self):
        text = "# Title\n\nSome text.\n\n## Section One\n\n### Sub Section\n\n## Section Two\n"
        self.assertEqual(
            lint_task.extract_headings(text),
            ["# Title", "## Section One", "### Sub Section", "## Section Two"],
        )

    def test_ignores_non_heading_hash_usage(self):
        text = "Not a heading: #hashtag\n\n## Real Heading\n"
        self.assertEqual(lint_task.extract_headings(text), ["## Real Heading"])


class CheckTemplateSectionsTests(unittest.TestCase):
    def _valid_template_text(self) -> str:
        lines = ["# {{Task Title}}", ""]
        for section in lint_task.REQUIRED_TEMPLATE_SECTIONS:
            lines.append(section)
            lines.append("<!-- placeholder -->")
            lines.append("")
        return "\n".join(lines)

    def test_shipped_template_has_no_problems(self):
        text = (ROOT / "assets/task-template.md").read_text(encoding="utf-8")
        self.assertEqual(lint_task.check_template_sections(text), [])

    def test_synthetic_valid_template_has_no_problems(self):
        self.assertEqual(
            lint_task.check_template_sections(self._valid_template_text()), []
        )

    def test_missing_section_is_reported(self):
        text = self._valid_template_text().replace("## Open Questions\n", "")
        problems = lint_task.check_template_sections(text)
        self.assertTrue(any("missing sections" in p for p in problems))
        self.assertTrue(any("Open Questions" in p for p in problems))

    def test_extra_section_is_reported(self):
        text = self._valid_template_text() + "\n## Unexpected Extra Section\n"
        problems = lint_task.check_template_sections(text)
        self.assertTrue(any("unexpected extra sections" in p for p in problems))

    def test_out_of_order_sections_are_reported(self):
        lines = ["# {{Task Title}}", "", "## Objective", "## Background"]
        for section in lint_task.REQUIRED_TEMPLATE_SECTIONS[2:]:
            lines.append(section)
        problems = lint_task.check_template_sections("\n".join(lines))
        self.assertTrue(any("out of order" in p for p in problems))

    def test_missing_top_level_title_is_reported(self):
        text = "\n".join(lint_task.REQUIRED_TEMPLATE_SECTIONS)
        problems = lint_task.check_template_sections(text)
        self.assertTrue(any("top-level title" in p for p in problems))

    def test_two_top_level_titles_is_reported(self):
        text = "# First Title\n# Second Title\n" + "\n".join(
            lint_task.REQUIRED_TEMPLATE_SECTIONS
        )
        problems = lint_task.check_template_sections(text)
        self.assertTrue(any("top-level title" in p for p in problems))


class ShippedExamplesTests(unittest.TestCase):
    def test_every_example_task_follows_the_section_contract(self):
        examples = sorted((ROOT / "examples").glob("*-task.md"))
        self.assertTrue(examples, "no example task files found")
        for path in examples:
            with self.subTest(example=path.name):
                problems = lint_task.check_template_sections(
                    path.read_text(encoding="utf-8")
                )
                self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()

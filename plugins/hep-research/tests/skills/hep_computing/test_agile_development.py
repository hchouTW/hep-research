"""Behavioral tests for the agile-development helper scripts.

Run from the skill directory with python3 -m unittest discover -s tests -v.
Standard library only; no external services or dependencies are needed.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-computing"
sys.path.insert(0, str(ROOT / "scripts"))

import create_story_card  # noqa: E402
import validate_agile_notes  # noqa: E402


def _story_args(**overrides) -> argparse.Namespace:
    defaults = dict(
        actor="user",
        capability="export a CSV",
        outcome="download active users",
        criteria=None,
        validation=None,
        assumption="No material assumptions identified yet.",
        in_scope="The smallest behavior that satisfies the current request.",
        out_of_scope="Follow-up enhancements not required for this increment.",
        risk="No material risk identified yet.",
        output=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class CreateStoryCardTests(unittest.TestCase):
    def test_default_criteria_and_validation_used_when_omitted(self):
        card = create_story_card.build_card(_story_args())
        self.assertIn("Given the primary context", card)
        self.assertIn("Run the focused test or check", card)

    def test_supplied_criteria_and_validation_replace_defaults(self):
        args = _story_args(criteria=["Given X, when Y, then Z"], validation=["Run test_foo"])
        card = create_story_card.build_card(args)
        self.assertIn("Given X, when Y, then Z", card)
        self.assertIn("Run test_foo", card)
        self.assertNotIn("Given the primary context", card)

    def test_story_line_interpolates_actor_capability_outcome(self):
        card = create_story_card.build_card(_story_args())
        self.assertIn("As a user, I want export a CSV, so that download active users.", card)

    def test_cli_end_to_end(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/create_story_card.py"),
                "--actor", "user",
                "--capability", "export a CSV",
                "--outcome", "download active users",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("# Story Card", result.stdout)

    def test_cli_missing_required_flag_fails_with_usage(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/create_story_card.py"), "--actor", "user"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)


class ValidateAgileNotesTests(unittest.TestCase):
    def test_normalize_heading_strips_hashes_and_lowercases(self):
        self.assertEqual(validate_agile_notes.normalize_heading("## Acceptance Criteria"), "acceptance criteria")
        self.assertEqual(validate_agile_notes.normalize_heading("# Story"), "story")
        self.assertIsNone(validate_agile_notes.normalize_heading("not a heading"))

    def test_check_file_reports_missing_sections(self, tmp_text="# Story\n\nAs a user...\n"):
        tmp_path = TESTS_DIR / "_scratch_note.md"
        tmp_path.write_text(tmp_text, encoding="utf-8")
        try:
            headings, missing = validate_agile_notes.check_file(
                tmp_path, ["story", "acceptance criteria", "validation", "risks"]
            )
            self.assertEqual(headings, ["story"])
            self.assertEqual(missing, ["acceptance criteria", "validation", "risks"])
        finally:
            tmp_path.unlink()

    def test_check_file_passes_with_all_sections_present(self):
        tmp_path = TESTS_DIR / "_scratch_note.md"
        tmp_path.write_text(
            "# Story\n\n## Acceptance Criteria\n\n## Validation\n\n## Risks\n", encoding="utf-8"
        )
        try:
            _, missing = validate_agile_notes.check_file(
                tmp_path, ["story", "acceptance criteria", "validation", "risks"]
            )
            self.assertEqual(missing, [])
        finally:
            tmp_path.unlink()

    def test_cli_ok_on_shipped_template(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_agile_notes.py"), str(ROOT / "assets/story-card.md")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(": ok", result.stdout)

    def test_cli_missing_file_fails_cleanly_not_with_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_agile_notes.py"), str(TESTS_DIR / "does-not-exist.md")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("file not found", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


class EdgeCaseRegressionTests(unittest.TestCase):
    """Defects found by the 2026-09-21 edge-case probe (see TODO.md P2)."""

    FULL = "## Story\n## Acceptance Criteria\n## Validation\n## Risks\n"

    def _missing(self, data: bytes) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "n.md"
            path.write_bytes(data)
            return validate_agile_notes.check_file(path, validate_agile_notes.DEFAULT_SECTIONS)[1]

    def test_crlf_line_endings_pass(self):
        self.assertEqual(self._missing(self.FULL.replace("\n", "\r\n").encode()), [])

    def test_leading_bom_does_not_hide_first_heading(self):
        self.assertEqual(self._missing(b"\xef\xbb\xbf" + self.FULL.encode()), [])

    def test_closing_hashes_are_ignored(self):
        data = "## Story ##\n## Acceptance Criteria ##\n## Validation\n## Risks\n"
        self.assertEqual(self._missing(data.encode()), [])

    def test_headings_inside_fenced_code_do_not_count(self):
        data = "```\n" + self.FULL + "```\n"
        self.assertEqual(len(self._missing(data.encode())), 4)
        self.assertEqual(self._missing((self.FULL + "~~~\n## Extra\n~~~\n").encode()), [])

    def test_empty_file_reports_every_section_missing(self):
        self.assertEqual(len(self._missing(b"")), 4)

    def test_trailing_punctuation_does_not_make_a_placeholder_verification_pass(self):
        problems = validate_agile_notes.check_plan_verification("1. a -> verify: Works!\n")
        self.assertEqual(len(problems), 1)

    def test_story_card_rejects_empty_required_fields(self):
        for overrides in ({"actor": ""}, {"capability": "  "}, {"criteria": [""]}):
            with self.assertRaises(ValueError):
                create_story_card.build_card(_story_args(**overrides))

    def test_story_card_cli_empty_actor_exits_two_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/create_story_card.py"),
             "--actor", "", "--capability", "x", "--outcome", "y"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_generated_card_round_trips_through_the_validator(self):
        card = create_story_card.build_card(_story_args())
        self.assertEqual(self._missing(card.encode()), [])


if __name__ == "__main__":
    unittest.main()


class PlanStepParsingTests(unittest.TestCase):
    """Parsing numbered plan steps and their verification clauses."""

    def test_parses_step_number_text_and_verification(self):
        steps = validate_agile_notes.find_plan_steps(
            "1. Add the parser -> verify: unit test covers the new flag\n")
        self.assertEqual(steps, [(1, "Add the parser", "unit test covers the new flag")])

    def test_step_without_verification_reports_none(self):
        steps = validate_agile_notes.find_plan_steps("2. Ship it\n")
        self.assertEqual(steps, [(2, "Ship it", None)])

    def test_accepts_arrow_and_bare_verify_forms(self):
        for line in ("1. Do a thing -> verify: the test passes",
                     "1. Do a thing \u2192 verify: the test passes",
                     "1. Do a thing --> verify: the test passes",
                     "1. Do a thing. verify: the test passes"):
            with self.subTest(line=line):
                steps = validate_agile_notes.find_plan_steps(line)
                self.assertEqual(len(steps), 1)
                self.assertEqual(steps[0][2], "the test passes")

    def test_accepts_verification_spelling_and_is_case_insensitive(self):
        steps = validate_agile_notes.find_plan_steps("3. Do it -> Verification: CI is green")
        self.assertEqual(steps[0][2], "CI is green")

    def test_accepts_paren_numbering(self):
        self.assertEqual(
            validate_agile_notes.find_plan_steps("4) Do it -> verify: it exits zero"),
            [(4, "Do it", "it exits zero")])

    def test_ignores_lines_that_are_not_numbered_steps(self):
        text = "# Plan\n\nSome prose about verify: not a step\n- bullet\n"
        self.assertEqual(validate_agile_notes.find_plan_steps(text), [])

    def test_parses_a_multi_step_plan_in_order(self):
        text = ("1. First -> verify: a\n"
                "2. Second -> verify: b\n"
                "3. Third\n")
        steps = validate_agile_notes.find_plan_steps(text)
        self.assertEqual([n for n, _, _ in steps], [1, 2, 3])
        self.assertEqual([v for _, _, v in steps], ["a", "b", None])


class WeakVerificationTests(unittest.TestCase):
    """A verification that asserts nothing checkable is not a verification."""

    def test_placeholders_are_rejected(self):
        for weak in ("looks right", "Looks Right", "it works", "works",
                     "should work", "done.", "  fine  ", "no errors"):
            with self.subTest(weak=weak):
                self.assertTrue(validate_agile_notes.is_weak_verification(weak))

    def test_real_verifications_are_accepted(self):
        for strong in ("the unit test passes", "CI is green",
                       "python3 -m unittest discover -s tests exits zero",
                       "the endpoint returns 404 for a missing id",
                       "throughput measured above 1000 rps"):
            with self.subTest(strong=strong):
                self.assertFalse(validate_agile_notes.is_weak_verification(strong))


class PlanVerificationCheckTests(unittest.TestCase):
    """The opt-in plan check, including the no-plan case."""

    GOOD = ("1. Add the flag -> verify: unit test covers it\n"
            "2. Wire it up -> verify: CLI exits 1 on a bad note\n")

    def test_fully_verified_plan_passes(self):
        self.assertEqual(validate_agile_notes.check_plan_verification(self.GOOD), [])

    def test_missing_verification_is_reported_with_its_step_number(self):
        problems = validate_agile_notes.check_plan_verification(self.GOOD + "3. Ship it\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("step 3", problems[0])
        self.assertIn("no verification", problems[0])

    def test_placeholder_verification_is_reported_separately(self):
        problems = validate_agile_notes.check_plan_verification(
            self.GOOD + "3. Update docs -> verify: looks right\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("placeholder", problems[0])
        self.assertIn("looks right", problems[0])

    def test_both_problem_kinds_are_reported_together(self):
        problems = validate_agile_notes.check_plan_verification(
            self.GOOD + "3. Update docs -> verify: works\n4. Ship it\n")
        self.assertEqual(len(problems), 2)

    def test_absent_plan_is_a_problem_not_a_pass(self):
        problems = validate_agile_notes.check_plan_verification("# Story\n\nprose only\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("no numbered plan steps", problems[0])

    def test_long_step_text_is_truncated_in_the_message(self):
        long_step = "1. " + "x" * 200 + "\n"
        problems = validate_agile_notes.check_plan_verification(long_step)
        self.assertIn("...", problems[0])
        self.assertLess(len(problems[0]), 120)


class ValidateNotesCliOptInTests(unittest.TestCase):
    """The new flags are opt-in: default behavior must be unchanged."""

    SCRIPT = str(ROOT / "scripts/validate_agile_notes.py")
    NOTE = ("# Story\n\n## Acceptance Criteria\n\n## Validation\n\n## Risks\n\n"
            "1. Add the flag -> verify: unit test covers it\n"
            "2. Ship it\n")

    def _write(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def _run(self, path, *flags):
        return subprocess.run([sys.executable, self.SCRIPT, path, *flags],
                              capture_output=True, text=True)

    def test_default_run_ignores_an_unverified_plan(self):
        # The regression gate: a note that fails the new check must still pass by default.
        result = self._run(self._write(self.NOTE))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("ok", result.stdout)

    def test_plan_flag_fails_the_same_note(self):
        result = self._run(self._write(self.NOTE), "--require-plan-verification")
        self.assertEqual(result.returncode, 1)
        self.assertIn("step 2", result.stdout)

    def test_plan_flag_passes_a_fully_verified_note(self):
        good = self.NOTE.replace("2. Ship it", "2. Ship it -> verify: the release job is green")
        result = self._run(self._write(good), "--require-plan-verification")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_assumptions_flag_adds_to_defaults_rather_than_replacing(self):
        result = self._run(self._write(self.NOTE), "--require-assumptions")
        self.assertEqual(result.returncode, 1)
        self.assertIn("assumptions", result.stdout)
        # The default sections are still required alongside it.
        bare = self._run(self._write("# Assumptions\n"), "--require-assumptions")
        self.assertEqual(bare.returncode, 1)
        self.assertIn("story", bare.stdout)

    def test_assumptions_flag_passes_when_the_heading_is_present(self):
        result = self._run(self._write(self.NOTE + "\n## Assumptions\n"),
                           "--require-assumptions")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_shipped_story_card_still_passes_by_default(self):
        result = self._run(str(ROOT / "assets/story-card.md"))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_file_still_exits_two_with_the_new_flags(self):
        result = self._run(str(TESTS_DIR / "does-not-exist.md"),
                           "--require-plan-verification")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

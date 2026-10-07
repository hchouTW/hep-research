"""Tests for scripts/lint_task.py (the generated-task linter).

Run from the skill directory with python3 -m unittest discover -s tests -v.
Standard library only.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-computing"
sys.path.insert(0, str(ROOT / "scripts"))

import lint_task  # noqa: E402

GOOD = """# Add rate limiting

## Background
`app/users_api.py` serves `GET /users` with no throttling.

## Objective
Requests above the limit get HTTP 429.

## Scope

### In Scope
- The users blueprint.

### Out of Scope
- Other endpoints.

## Repository Context
- `app/users_api.py` exists.

## Technical Approach
1. Add a limiter.

## Deliverables
- A new file `app/limiter.py`.

## Acceptance Criteria
- The 101st request in a minute returns 429.

## Validation
- Run the tests.

## Open Questions
- The limit value is TBD.

## References
- `app/users_api.py`
"""


def make_repo(tmp: str) -> Path:
    repo = Path(tmp) / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "users_api.py").write_text("x = 1\n")
    return repo


class LintTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)

    def lint(self, text, repo=True):
        return lint_task.lint(text, self.repo if repo else None, skill_root=None)

    def test_good_task_has_no_errors(self):
        errors, warnings = self.lint(GOOD)
        self.assertEqual(errors, [])
        self.assertTrue(any("app/limiter.py" in w for w in warnings))  # proposed in Deliverables

    def test_missing_section_is_an_error(self):
        errors, _ = self.lint(GOOD.replace("## Validation\n- Run the tests.\n\n", ""))
        self.assertTrue(any("missing sections" in e for e in errors))

    def test_empty_section_is_an_error(self):
        errors, _ = self.lint(GOOD.replace("- Run the tests.", ""))
        self.assertTrue(any("'## Validation' is empty" in e for e in errors))

    def test_placeholder_is_an_error(self):
        errors, _ = self.lint(GOOD.replace("- Other endpoints.", "{{fill in}}"))
        self.assertTrue(any("leftover placeholder" in e for e in errors))

    def test_example_block_markers_are_not_placeholders(self):
        errors, _ = self.lint("<!-- example: experiment-specific illustration -->\n" + GOOD + "\n<!-- /example -->\n")
        self.assertFalse(any("leftover placeholder" in e for e in errors), errors)
        errors, _ = self.lint(GOOD.replace("- Other endpoints.", "<!-- TODO -->"))
        self.assertTrue(any("leftover placeholder" in e for e in errors))

    def test_open_questions_without_an_item_is_an_error(self):
        errors, _ = self.lint(GOOD.replace("- The limit value is TBD.", "None."))
        self.assertTrue(any("no list item" in e for e in errors))

    def test_missing_repo_path_is_an_error(self):
        errors, _ = self.lint(GOOD.replace("`app/users_api.py` exists.", "`app/ghost.py` exists."))
        self.assertTrue(any("app/ghost.py" in e for e in errors))

    def test_missing_path_named_as_absent_is_only_a_warning(self):
        text = GOOD.replace("`app/users_api.py` exists.", "`app/ghost.py` does not exist in the repository.")
        errors, warnings = self.lint(text)
        self.assertEqual(errors, [])
        self.assertTrue(any("app/ghost.py" in w for w in warnings))

    def test_without_repo_paths_are_warnings(self):
        errors, warnings = self.lint(GOOD, repo=False)
        self.assertEqual(errors, [])
        self.assertTrue(any("not checked" in w for w in warnings))

    def test_retry_loop_without_a_limit_is_an_error(self):
        text = GOOD.replace("1. Add a limiter.", "1. Retry until the tests pass.")
        errors, _ = self.lint(text)
        self.assertTrue(any("maximum-iteration" in e for e in errors))

    def test_retry_loop_with_a_limit_marked_tbd_passes(self):
        text = GOOD.replace("1. Add a limiter.", "1. Retry until the tests pass.").replace(
            "- The limit value is TBD.", "- The maximum number of retries is TBD."
        )
        errors, _ = self.lint(text)
        self.assertEqual(errors, [])


class LintCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/lint_task.py"), *args], capture_output=True, text=True
        )

    def test_exit_0_on_clean_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "t.md"
            task.write_text(GOOD)
            result = self.run_cli(str(task), "--repo", str(make_repo(tmp)))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 error(s)", result.stdout)

    def test_exit_1_on_broken_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "t.md"
            task.write_text("# Only a title\n")
            result = self.run_cli(str(task))
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stdout)

    def test_exit_2_on_unreadable_file(self):
        result = self.run_cli("/nonexistent/task.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot read", result.stderr)


# The shipped example tasks describe this plugin; lint them against the plugin root.
PLUGIN_ROOT = Path(__file__).resolve().parents[3]


class ShippedExamplesLintTests(unittest.TestCase):
    def test_every_example_task_lints_without_errors(self):
        examples = sorted((ROOT / "examples").glob("*-task.md"))
        self.assertTrue(examples, "no example task files found")
        for path in examples:
            with self.subTest(example=path.name):
                errors, _ = lint_task.lint(path.read_text(encoding="utf-8"), PLUGIN_ROOT)
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

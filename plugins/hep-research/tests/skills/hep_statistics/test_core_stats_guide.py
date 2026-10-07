"""S02: the owner-side guide skills/hep-statistics/references/core-stats-guide.md documents every core/stats
subcommand and validator option, its links resolve, and it names no experiment. It fails when a subcommand is
added without documentation. tools/check_ams_optional.py runs this test in a copy without the AMS-02 profile."""
import argparse
import importlib
import re
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
GUIDE = PLUGIN / "skills" / "hep-statistics" / "references" / "core-stats-guide.md"
sys.path.insert(0, str(PLUGIN))

SUBCOMMAND_MODULES = ("likelihood_limits", "poisson_diagnostics", "statistical_toys", "template_fit",
                      "unfolding_diagnostics")
VALIDATORS = ("validate_covariance", "validate_response")


def subcommands(module):
    parser = importlib.import_module(f"core.stats.{module}").build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return {name: sorted(o.option_strings[-1] for o in sub._actions if o.option_strings and
                                 o.option_strings[-1] != "--help") for name, sub in action.choices.items()}
    return {}


class CoreStatsGuide(unittest.TestCase):
    def setUp(self):
        self.text = GUIDE.read_text(encoding="utf-8")

    def section(self, module):
        start = self.text.index(f"## `{module}.py")
        nxt = self.text.find("\n## ", start + 4)
        return self.text[start:nxt if nxt > 0 else None]

    def test_every_module_has_a_section(self):
        found = sorted(p.stem for p in (PLUGIN / "core" / "stats").glob("*.py") if p.stem != "__init__")
        self.assertEqual(found, sorted(SUBCOMMAND_MODULES + VALIDATORS), "update the guide and this test together")
        for m in SUBCOMMAND_MODULES:
            self.assertIn(f"## `{m}.py`", self.text)
        for m in VALIDATORS:
            self.assertIn(f"`{m}.py", self.text)

    def test_every_subcommand_and_option_documented(self):
        for module in SUBCOMMAND_MODULES:
            subs = subcommands(module)
            self.assertTrue(subs, module)
            sec = self.section(module)
            for name, options in subs.items():
                self.assertRegex(sec, rf"`{re.escape(name)}\b", f"{module} {name} undocumented")
                for opt in options:
                    self.assertIn(opt, sec, f"{module} {name}: option {opt} undocumented")

    def test_validator_options_documented(self):
        for module in VALIDATORS:
            src = (PLUGIN / "core" / "stats" / f"{module}.py").read_text(encoding="utf-8")
            for opt in re.findall(r"add_argument\(\"(--[\w-]+)\"", src):
                self.assertRegex(self.text, rf"`{module}\.py[^`]*{re.escape(opt)}", f"{module} {opt}")

    def test_exit_codes_match_module_docstrings(self):
        after = self.text.split("- **Exit codes**", 1)[1]
        rows = [line for line in after.split("\n\n- ", 1)[0].splitlines() if line.startswith("|")]
        for module in SUBCOMMAND_MODULES + VALIDATORS:
            doc = importlib.import_module(f"core.stats.{module}").__doc__
            row = next(line for line in rows if f"`{module}.py`" in line)
            exit_one = row.split("|")[3].strip()
            has_one = re.search(r"Exit codes:[^\n]*\b1 ", doc) is not None
            self.assertEqual(has_one, exit_one != "—", f"{module}: exit code 1 column disagrees with its docstring")

    def test_links_resolve_and_no_experiment_names(self):
        for target in re.findall(r"\]\(([^)#]+)\)", self.text):
            self.assertTrue((GUIDE.parent / target).is_file(), target)
        self.assertNotRegex(self.text, r"\bAMS\b|profiles/experiments/")


class RunScriptsWhenAShellExists(unittest.TestCase):
    """the Bash variant computed limits by hand instead of running core/stats."""

    def test_skill_and_guide_say_to_run_the_script_and_label_hand_values(self):
        skill = (PLUGIN / "skills" / "hep-statistics" / "SKILL.md").read_text(encoding="utf-8")
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("When a shell is available, run the matching script for exact limits and intervals", skill)
        self.assertIn("label a value worked by hand as such", skill)
        self.assertIn("When a shell is available, run the matching subcommand", guide)

if __name__ == "__main__":
    unittest.main()

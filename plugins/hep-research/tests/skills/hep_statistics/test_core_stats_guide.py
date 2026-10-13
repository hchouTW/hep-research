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
HELPERS = ("fit_diagnostics", "tail_estimation", "toy_ensemble")  # importable helpers without a CLI, documented under the conventions


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
        # private helpers (a leading underscore) have no subcommands; the guide describes them under the conventions
        found = sorted(p.stem for p in (PLUGIN / "core" / "stats").glob("*.py") if not p.stem.startswith("_"))
        self.assertEqual(found, sorted(SUBCOMMAND_MODULES + VALIDATORS + HELPERS), "update the guide and this test together")
        for m in HELPERS:
            self.assertIn(f"`{m}.py`", self.text)
        for m in SUBCOMMAND_MODULES:
            self.assertIn(f"## `{m}.py`", self.text)
        for m in VALIDATORS:
            self.assertIn(f"`{m}.py", self.text)
        self.assertIn("`_linalg.py`", self.text)
        self.assertIn("`_poisson.py`", self.text)

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
        self.assertIn("when a shell is available, run its row's tool", skill)  # Step 0 (STH-T2.1)
        self.assertIn("label a value worked by hand as such", skill)
        self.assertIn("When a shell is available, run the matching subcommand", guide)

CS = PLUGIN / "core" / "stats"


def _code(module: str) -> str:
    return (CS / f"{module}.py").read_text(encoding="utf-8")


def _nums(module: str, pattern: str) -> list[float]:
    """Every number captured by pattern in core/stats/<module>.py, in source order (MAX_MEAN resolved)."""
    max_mean = float(re.search(r"^MAX_MEAN = ([0-9.e+]+)", _code("_poisson"), re.M).group(1))
    out = []
    for m in re.finditer(pattern, _code(module), re.M):
        for g in m.groups():
            out.append(max_mean if g == "MAX_MEAN" else float(g))
    return out


def _num_upper(module: str, name: str) -> set[float]:
    """Upper bounds of every _num(x, "<name>", lo, hi ...) call."""
    return set(_nums(module, r'_num\(.*?,\s*f?"' + re.escape(name) + r'",\s*[-0-9.e]+,\s*(MAX_MEAN|[-0-9.e+]+)'))


class CapsTable(unittest.TestCase):
    """STH-T2.2: the guide's caps table and the code's bounds agree; a bound changed in code (or in the table) alone
    fails here. Each check: (row key in the table, cap text in that row, the value(s) the code enforces)."""

    def rows(self) -> dict:
        text = GUIDE.read_text(encoding="utf-8")
        block = text[text.index("| Where | Cap | Beyond it |"):]
        rows = {}
        for line in block.splitlines()[2:]:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0]] = cells[1]
        return rows

    def cap(self, row_key: str, label: str) -> float:
        rows = self.rows()
        key = next((k for k in rows if k.startswith(row_key)), None)
        self.assertIsNotNone(key, f"no caps row starting {row_key!r}")
        m = re.search(re.escape(label) + r" (?:<= )?([0-9.e+]+)", rows[key])
        self.assertIsNotNone(m, f"{row_key}: no '{label}' cap in {rows[key]!r}")
        return float(m.group(1))

    def test_table_matches_code(self):
        ll, st, ud = "likelihood_limits", "statistical_toys", "unfolding_diagnostics"
        checks = [
            ("every Poisson routine", "mean", _nums("_poisson", r"^MAX_MEAN = ([0-9.e+]+)")),
            ("`poisson_diagnostics.py fc-interval`", "total mean",
             _nums("poisson_diagnostics", r"^FC_MAX_TOTAL_MEAN = ([0-9.e+]+)")),
            ("`likelihood_limits.py` single-bin", "b", sorted(_num_upper(ll, "b"))),
            ("`likelihood_limits.py` single-bin", "sigma_b", sorted(_num_upper(ll, "sigma_b"))),
            ("`likelihood_limits.py multibin-limit`", "bins", _nums(ll, r"not 1 <= len\(raw\) <= (\d+)")[:1]),
            ("`likelihood_limits.py shape-limit`", "bins", _nums(ll, r"not 1 <= len\(raw\) <= (\d+)")[1:2]),
            ("`likelihood_limits.py multibin-limit`", "bin b", sorted(_num_upper(ll, "bin {i} b"))),
            ("`likelihood_limits.py shape-limit`", "bin b", sorted(_num_upper(ll, "bin {i} b"))),
            ("`likelihood_limits.py multibin-limit`", "total n", _nums(ll, r'sum\(x\["n"\] for x in bins\) > (\d+)')[:1]),
            ("`likelihood_limits.py shape-limit`", "total n", _nums(ll, r'sum\(x\["n"\] for x in bins\) > (\d+)')[1:2]),
            ("`likelihood_limits.py multibin-limit`", "mc_stat", sorted(_num_upper(ll, "bin {i} mc_stat"))),
            ("`likelihood_limits.py shape-limit`", "mc_stat", sorted(_num_upper(ll, "bin {i} mc_stat"))),
            ("`likelihood_limits.py` toy counts", "toys", _nums(ll, r"toy_count\(toys, (\d+), \d+")),
            ("`likelihood_limits.py` toy counts", "to", _nums(ll, r"toy_count\(toys, \d+, (\d+)")),
            ("`statistical_toys.py` toy counts", "toys", _nums(st, r"^MAX_TOYS = (\d+)")),
            ("`statistical_toys.py ratio-cov`", "denominator",
             _nums(st, r'_num\(v, "denominator", 0\.0, (MAX_MEAN), strict_low=True\)')),
            ("`statistical_toys.py unfold-scan`", "bins", _nums(st, r"max\(n_reco, n_truth\) > (\d+)")),
            ("`unfolding_diagnostics.py` response-stat", "mc_events", sorted(_num_upper(ud, "mc_events"))),
            ("`unfolding_diagnostics.py` response-covariance", "cells", _nums(ud, r"n_truth \* n_reco > (\d+)")),
            ("`template_fit.py`", "templates", _nums("template_fit", r"^MAX_TEMPLATES, MAX_BINS = (\d+), \d+")),
            ("`template_fit.py`", "bins", _nums("template_fit", r"^MAX_TEMPLATES, MAX_BINS = \d+, (\d+)")),
        ]
        for row, label, code_values in checks:
            with self.subTest(row=row, cap=label):
                self.assertTrue(code_values, f"pattern for {row} {label} no longer matches the code")
                self.assertEqual(len(set(code_values)), 1, f"code enforces several values {code_values}")
                self.assertEqual(self.cap(row, label), code_values[0])

    def test_no_single_global_limit_claimed(self):
        self.assertNotIn("in every module", GUIDE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

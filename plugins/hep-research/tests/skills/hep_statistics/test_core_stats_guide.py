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
COMMANDS = GUIDE.with_name("core-stats-commands.md")  # per-module reference split from the guide (STH-T2.7)


def guide_and_commands() -> str:
    return GUIDE.read_text(encoding="utf-8") + "\n" + COMMANDS.read_text(encoding="utf-8")
sys.path.insert(0, str(PLUGIN))

SUBCOMMAND_MODULES = ("likelihood_limits", "poisson_diagnostics", "statistical_toys", "template_fit",
                      "unfolding_diagnostics")
VALIDATORS = ("validate_covariance", "validate_response")
HELPERS = ("broken_power_law", "change_point", "fit_diagnostics", "tail_estimation", "toy_ensemble")  # importable helpers without a CLI, documented under the conventions


def subcommands(module):
    parser = importlib.import_module(f"core.stats.{module}").build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return {name: sorted(o.option_strings[-1] for o in sub._actions if o.option_strings and
                                 o.option_strings[-1] != "--help") for name, sub in action.choices.items()}
    return {}


class CoreStatsGuide(unittest.TestCase):
    def setUp(self):
        self.text = guide_and_commands()

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
        guide = guide_and_commands()
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
            ("`likelihood_limits.py shape-limit` with toys", "bins", _nums(ll, r'^SHAPE_TOY_CAPS = \{"bins": (\d+)')),
            ("`likelihood_limits.py shape-limit` without toys", "bins", _nums(ll, r'^SHAPE_ASYMPTOTIC_CAPS = \{"bins": (\d+)')),
            ("`likelihood_limits.py multibin-limit`", "bin b", sorted(_num_upper(ll, "bin {i} b"))),
            ("`likelihood_limits.py shape-limit` with toys", "bin b", _nums(ll, r'^SHAPE_TOY_CAPS = .*"bin_b": ([0-9.e+]+)')),
            ("`likelihood_limits.py shape-limit` without toys", "bin b", _nums(ll, r'^SHAPE_ASYMPTOTIC_CAPS = .*"bin_b": ([0-9.e+]+)')),
            ("`likelihood_limits.py multibin-limit`", "total n", _nums(ll, r'sum\(x\["n"\] for x in bins\) > (\d+)')[:1]),
            ("`likelihood_limits.py shape-limit` with toys", "total n", _nums(ll, r'^SHAPE_TOY_CAPS = .*"total_n": (\d+)')),
            ("`likelihood_limits.py shape-limit` without toys", "total n", _nums(ll, r'^SHAPE_ASYMPTOTIC_CAPS = .*"total_n": (\d+)')),
            ("`likelihood_limits.py multibin-limit`", "mc_stat", sorted(_num_upper(ll, "bin {i} mc_stat"))),
            ("`likelihood_limits.py shape-limit` with toys", "mc_stat", sorted(_num_upper(ll, "bin {i} mc_stat"))),
            ("`likelihood_limits.py` toy counts", "toys", _nums(ll, r"toy_count\(toys, (\d+), \d+")),
            ("`likelihood_limits.py` toy counts", "to", _nums(ll, r"toy_count\(toys, \d+, (\d+)")),
            ("`statistical_toys.py` toy counts", "toys", _nums(st, r"^MAX_TOYS = (\d+)")),
            ("`statistical_toys.py ratio-cov`", "denominator",
             _nums(st, r'_num\(v, "denominator", 0\.0, (MAX_MEAN), strict_low=True\)')),
            ("`statistical_toys.py unfold-scan`", "bins", _nums(st, r"max\(n_reco, n_truth\) > (\d+)")),
            ("`statistical_toys.py ratio-cov-analytic`", "counts", _nums(st, r"^ANALYTIC_MIN_COUNTS = ([0-9.e+]+)")),
            ("`statistical_toys.py ratio-cov-analytic`", "to", _nums(st, r"^ANALYTIC_MAX_COUNTS = ([0-9.e+]+)")),
            ("`unfolding_diagnostics.py` response-stat", "mc_events", sorted(_num_upper(ud, "mc_events"))),
            ("`unfolding_diagnostics.py` response-covariance", "cells", _nums(ud, r"n_truth \* n_reco > (\d+)")[:1]),
            ("`unfolding_diagnostics.py dagostini-unfold`", "data", _nums(ud, r"^UNFOLD_MAX_COUNTS = ([0-9.e+]+)")),
            ("`unfolding_diagnostics.py dagostini-unfold`", "mc_events", _nums(ud, r"^UNFOLD_MAX_MC_EVENTS = ([0-9.e+]+)")),
            ("`template_fit.py`", "templates", _nums("template_fit", r"^MAX_TEMPLATES, MAX_BINS = (\d+), \d+")),
            ("`template_fit.py`", "bins", _nums("template_fit", r"^MAX_TEMPLATES, MAX_BINS = \d+, (\d+)")),
            # S7: the shape-limit nuisance cap, the TSVD caps and the template-fit nuisance cap
            ("`likelihood_limits.py shape-limit` with toys", "nuisances", _nums(ll, r"^SHAPE_MAX_NUISANCES = (\d+)")),
            ("`likelihood_limits.py shape-limit` without toys", "nuisances", _nums(ll, r"^SHAPE_MAX_NUISANCES = (\d+)")),
            ("`unfolding_diagnostics.py response-stat` with `tsvd`", "truth bins",
             _nums(ud, r'method == "tsvd" and n_truth > (\d+)')),
            ("`unfolding_diagnostics.py` Jacobian diagnostics", "bins",
             _nums(ud, r'method == "tsvd" and max\(n_truth, n_reco\) > (\d+)')),
            ("`template_fit.py`", "nuisances", _nums("template_fit", r"    if len\(raw\) > (\d+):")),
        ]
        for row, label, code_values in checks:
            with self.subTest(row=row, cap=label):
                self.assertTrue(code_values, f"pattern for {row} {label} no longer matches the code")
                self.assertEqual(len(set(code_values)), 1, f"code enforces several values {code_values}")
                self.assertEqual(self.cap(row, label), code_values[0])

    def test_no_single_global_limit_claimed(self):
        self.assertNotIn("in every module", guide_and_commands())

    def test_decision_guide_size(self):
        """STH-T2.7: the part every request reads stays small; the per-module detail is in the command reference."""
        self.assertLess(len(GUIDE.read_bytes()), 17000)
        self.assertIn("core-stats-commands.md", GUIDE.read_text(encoding="utf-8"))


SKILL = PLUGIN / "skills" / "hep-statistics" / "SKILL.md"
SC = PLUGIN / "skills" / "hep-statistics" / "scripts"
RESP = {"response": [[0.8, 0.1, 0.0], [0.1, 0.8, 0.1], [0.0, 0.1, 0.8]], "truth": [100.0, 80.0, 60.0],
        "test_truth": [90.0, 85.0, 50.0]}
SHAPE = {"bins": [{"n": 5, "b": 3.2, "s": 1.0}, {"n": 2, "b": 2.0, "s": 2.0}], "cl": 0.95}
TWO = {"bins": [{"n": 20, "b": 10, "s1": 5, "s2": 1}, {"n": 15, "b": 10, "s1": 1, "s2": 5}, {"n": 12, "b": 10, "s1": 2, "s2": 2}]}
SCAN = {"background": [10.0] * 8, "observed": [10, 12, 9, 15, 11, 10, 8, 10],
        "scan": {"parameter": "mass", "grid": [1.5, 3.5, 5.5], "bin_centers": [i + 0.5 for i in range(8)],
                 "signal_shape": {"kind": "gaussian", "width": 0.7}}}
GSCAN = {"bin_centers": [i + 0.5 for i in range(8)], "variants": [{"name": "loose", "background": [10.0] * 8,
                                                                    "observed": [10, 12, 9, 15, 11, 10, 8, 10]}],
         "scan": {"positions": [1.5, 3.5, 5.5], "widths": [0.7]}, "background_normalization": {"kind": "fixed"}}
CHAINS = {"mu": [[0.1 * ((7 * i + 3 * c) % 11) for i in range(200)] for c in range(4)]}
COVFIT = {"y": [1.0, 2.1, 2.9], "cov": [[0.04, 0.01, 0.0], [0.01, 0.04, 0.01], [0.0, 0.01, 0.04]], "x": [1.0, 2.0, 3.0],
          "model": "line"}
BPL = {"x": [1.0, 1.6, 2.5, 4.0, 6.3, 10.0, 16.0, 25.0, 40.0, 63.0, 100.0],
       "y": [1000.0 * (v / 10.0) ** (-2.7 if v < 10 else -2.4) for v in (1.0, 1.6, 2.5, 4.0, 6.3, 10.0, 16.0, 25.0, 40.0, 63.0, 100.0)],
       "grid_points": 20}
BPL["cov"] = [[(0.03 * BPL["y"][i]) ** 2 if i == j else 0.0 for j in range(11)] for i in range(11)]
RATIO = {"numerator": [400.0, 300.0], "denominator": [900.0, 800.0],
         "systematics": [{"name": "eff", "sigma_num": 0.02, "sigma_den": 0.02, "num_den_rho": 0.8, "bin_correlation": {"kind": "full"}}]}
# (script path relative to the plugin, subcommand or None) -> (arguments, input document or None). Every tool named in
# the SKILL.md task-to-tool table must have a route here, and each route runs on a tiny SYNTHETIC input (STH-T2.8):
# argparse choices alone would accept a method the code then refuses (regularized-scan lists dagostini).
ROUTES = {
    ("core/stats/poisson_diagnostics.py", "cls-limit"): (["--n", "2", "--b", "3.7", "--cl", "0.95"], None),
    ("core/stats/poisson_diagnostics.py", "fc-interval"): (["--n", "2", "--b", "1", "--cl", "0.9"], None),
    ("core/stats/poisson_diagnostics.py", "upper-limit"): (["--n", "2", "--b", "1", "--cl", "0.95"], None),
    ("core/stats/likelihood_limits.py", "profile-cls"): (["--n", "3", "--b", "2", "--sigma-b", "0.5", "--toys", "200",
                                                          "--expected-toys", "20", "--seed", "1"], None),
    ("core/stats/likelihood_limits.py", "profile-limit"): (["--n", "3", "--b", "2", "--sigma-b", "0.5", "--toys", "200", "--seed", "1"], None),
    ("core/stats/likelihood_limits.py", "neyman-limit"): (["--n", "3", "--b", "2", "--sigma-b", "0.5", "--toys", "100", "--seed", "1"], None),
    ("core/stats/likelihood_limits.py", "profile-significance"): (["--n", "8", "--b", "2", "--sigma-b", "0.5", "--toys", "200", "--seed", "1"], None),
    ("core/stats/likelihood_limits.py", "shape-limit"): (["--input", "@IN", "--seed", "1"], SHAPE),
    ("core/stats/likelihood_limits.py", "shape-significance"): (["--input", "@IN", "--seed", "1"], SHAPE),
    ("core/stats/likelihood_limits.py", "contour"): (["--input", "@IN"], TWO),
    ("skills/hep-statistics/scripts/li_ma_significance.py", None): (["--on", "30", "--off", "100", "--alpha", "0.1"], None),
    ("skills/hep-statistics/scripts/look_elsewhere.py", "brute"): (["--input", "@IN", "--toys", "200", "--seed", "1"], SCAN),
    ("skills/hep-statistics/scripts/look_elsewhere.py", "gross-vitells"): (["--input", "@IN", "--toys", "100", "--seed", "1"], SCAN),
    ("skills/hep-statistics/scripts/global_significance.py", "run"): (["--input", "@IN", "--toys", "100", "--seed", "1"], GSCAN),
    ("skills/hep-statistics/scripts/combine_measurements.py", None): (["skills/hep-statistics/assets/combine.example.json"], None),
    ("skills/hep-statistics/scripts/combine_asymmetric.py", None): None,  # input format covered by its own tests
    ("skills/hep-statistics/scripts/split_consistency.py", None): (["--input", "@IN"], {"splits": [
        {"id": "a", "values": [1.0, 2.0], "covariance": [[0.04, 0.0], [0.0, 0.09]]},
        {"id": "b", "values": [1.1, 1.8], "covariance": [[0.05, 0.0], [0.0, 0.08]]}]}),
    ("skills/hep-statistics/scripts/project_uncertainty.py", None): (["@IN", "--k", "2,4"], {"stat": 0.04, "systematics": [
        {"name": "theory", "scaling": "floor", "sigma": 0.03, "control_grows_with_exposure": False}]}),
    ("skills/hep-statistics/scripts/tail_extrapolation.py", None): (["--input", "@IN"], {
        "edges": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0], "counts": [500, 300, 180, 110, 66, 40, 24],
        "control_region": [100.0, 160.0], "validation_region": [140.0, 160.0], "signal_region": [160.0, 170.0],
        "models": ["exponential"], "nominal": "exponential", "max_extrapolation": 20.0, "validation_alpha": 0.05,
        "cl": 0.6827}),
    ("core/stats/statistical_toys.py", "unfold-scan"): (["--input", "@IN", "--toys", "50", "--seed", "1"], dict(RESP, max_iterations=4)),
    ("core/stats/unfolding_diagnostics.py", "closure"): (["--input", "@IN", "--method", "dagostini", "--param", "3",
                                                          "--toys", "50", "--seed", "1"], RESP),
    ("core/stats/unfolding_diagnostics.py", "dagostini-unfold"): (["--input", "@IN", "--param", "3"],
                                                                   {"response": RESP["response"], "data": [80.0, 70.0, 55.0]}),
    ("core/stats/unfolding_diagnostics.py", "regularized-scan"): (["--input", "@IN", "--method", "tikhonov", "--toys", "50",
                                                                   "--seed", "1"], RESP),
    ("skills/hep-statistics/scripts/bayes_diagnostics.py", "diagnose"): (["--input", "@IN"], CHAINS),
    ("skills/hep-statistics/scripts/bayes_calibration.py", "sbc"): (["--reps", "40", "--draws", "19", "--bins", "5", "--seed", "1",
                                                                     "--power-runs", "2"], None),
    ("skills/hep-statistics/scripts/covariance_fit.py", "fit"): (["--input", "@IN"], COVFIT),
    ("skills/hep-statistics/scripts/covariance_fit.py", "break-scan"): (["--input", "@IN", "--toys", "50", "--seed", "1"], BPL),
    ("core/stats/statistical_toys.py", "ratio-cov"): (["--input", "@IN", "--toys", "200", "--seed", "1"], RATIO),
    ("core/stats/statistical_toys.py", "ratio-cov-analytic"): (["--input", "@IN"], {**RATIO, "numerator": [4e4, 3e4], "denominator": [9e4, 8e4]}),
    ("skills/hep-statistics/scripts/result_artifact.py", None): None,  # covered by test_result_artifact.py
}


def table_tools():
    """(script, subcommand) pairs named in the SKILL.md task-to-tool table (cs/ = core/stats/, sc/ = scripts/)."""
    text = SKILL.read_text(encoding="utf-8")
    block = text[text.index("| Request | Default | Fallback |"):]
    out = set()
    for line in block.splitlines()[2:]:
        if not line.startswith("|"):
            break
        last = None
        for tok in re.findall(r"`([^`]+)`", line):
            m = re.match(r"(cs|sc)/([a-z_]+\.py)(?: ([a-z][a-z-]*))?", tok)
            if m:
                last = ("core/stats/" if m.group(1) == "cs" else "skills/hep-statistics/scripts/") + m.group(2)
                out.add((last, m.group(3)))
            elif last and re.fullmatch(r"[a-z][a-z-]+", tok):
                out.add((last, tok))  # a bare subcommand after a script refers to the last script named
    return out


class RoutedCommandsRun(unittest.TestCase):
    """STH-T2.8: every tool and subcommand the task-to-tool table routes to runs on a tiny input and is not
    'rejected' for that method."""

    def test_every_table_entry_has_a_route(self):
        tools = table_tools()
        self.assertGreaterEqual(len(tools), 15, tools)
        # a bare word in a row that is not a subcommand of the last script must still be a known route
        missing = sorted(t for t in tools if t not in ROUTES and (t[0], None) not in ROUTES)
        self.assertEqual(missing, [], missing)

    def test_routes_run(self):
        import json
        import subprocess
        import tempfile
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest("NumPy and SciPy are needed by several routed scripts")
        for (script, sub), route in sorted(ROUTES.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
            if route is None:
                continue
            args, doc = route
            with self.subTest(script=script, sub=sub), tempfile.TemporaryDirectory() as td:
                if doc is not None:
                    p = Path(td) / "in.json"
                    p.write_text(json.dumps(doc))
                    args = [str(p) if a == "@IN" else a for a in args]
                cmd = [sys.executable, str(PLUGIN / script)] + ([sub] if sub else []) + args
                cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PLUGIN), timeout=600)
                self.assertNotEqual(cp.returncode, 2, (cmd, cp.stdout[-800:], cp.stderr[-800:]))
                self.assertNotIn("Traceback", cp.stderr)
                try:
                    status = json.loads(cp.stdout).get("status")
                except ValueError:
                    status = None
                self.assertNotEqual(status, "rejected", cp.stdout[-800:])

    def test_regularized_scan_refuses_dagostini(self):
        """The trap the old routing fell into: argparse lists dagostini, the code refuses it."""
        import json
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "in.json"
            p.write_text(json.dumps(RESP))
            cp = subprocess.run([sys.executable, str(CS / "unfolding_diagnostics.py"), "regularized-scan", "--input", str(p),
                                 "--method", "dagostini", "--seed", "1"], capture_output=True, text=True, timeout=120)
        self.assertEqual(cp.returncode, 2)
        # so the D'Agostini rows (SKILL.md table and guide) must route to unfold-scan, never to regularized-scan
        for path, header in ((SKILL, "| Request |"), (GUIDE, "| Question |")):
            text = path.read_text(encoding="utf-8")
            rows = [ln for ln in text[text.index(header):].splitlines() if ln.startswith("|") and "D'Agostini" in ln]
            self.assertTrue(rows, path.name)
            for row in rows:
                default = row.strip("|").split("|")[1]
                self.assertIn("unfold-scan", default, (path.name, row))
                self.assertNotIn("regularized-scan", default, (path.name, row))


def _module_imports(path: Path) -> set[str]:
    """numpy / scipy imported at module level (also inside a module-level try)."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    nodes = list(tree.body)
    for n in list(nodes):
        if isinstance(n, ast.Try):
            nodes += n.body
    for n in nodes:
        names = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module or ""] if isinstance(n, ast.ImportFrom) else [])
        for name in names:
            root = name.split(".")[0]
            if root in ("numpy", "scipy"):
                found.add(root)
    return found


class DependencyMarkers(unittest.TestCase):
    """STH-T2.8: every skill script that imports NumPy or SciPy at module level carries the matching '(needs ...)'
    marker in the guide's Skill scripts list, and no marker claims more or less."""

    def test_markers_match_imports(self):
        text = GUIDE.read_text(encoding="utf-8")
        section = text[text.index("## Skill scripts"):text.index("## Not implemented")]
        for path in sorted(SC.glob("*.py")):
            with self.subTest(path.name):
                need = _module_imports(path)
                m = re.search(re.escape(f"`{path.name}`") + r"(?: \(needs ([^)]*)\))?", section)
                self.assertIsNotNone(m, f"{path.name} not listed in the Skill scripts section")
                marker = m.group(1) or ""
                claimed = {"numpy"} if "NumPy" in marker else set()
                claimed |= {"scipy"} if "SciPy" in marker else set()
                self.assertEqual(claimed, need, (path.name, marker))


if __name__ == "__main__":
    unittest.main()

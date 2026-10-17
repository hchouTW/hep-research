"""Offline tests of the repository integration: plugin-root default, host isolation flags, the contamination and
budget stops, the coverage exit on a missing path, the budget requirement and the committed summary. No model calls;
the host is tests/fake_claude.py."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

EVALS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS))

from harness import cases as casemod  # noqa: E402
from harness import graders, invariants, report, runner  # noqa: E402

_spec = importlib.util.spec_from_file_location("behavior_run", EVALS / "run.py")
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

ROOT = casemod.DEFAULT_PLUGIN


def fake_bin(base: Path, marker: Path | None = None) -> Path:
    """A `claude` stand-in; with a marker, it records that it was called."""
    b = base / "claude"
    touch = f"touch {marker}\n" if marker else ""
    b.write_text(f"#!/bin/sh\n{touch}exec {sys.executable} {EVALS / 'tests' / 'fake_claude.py'} \"$@\"\n")
    b.chmod(0o755)
    return b


class PluginRoot(unittest.TestCase):
    def test_default_is_the_plugin_in_this_repository(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HEP_PLUGIN_ROOT", None)
            self.assertEqual(run.plugin_root(None), ROOT.resolve())
        self.assertTrue((ROOT / "skills").is_dir() and (ROOT / ".claude-plugin").is_dir())
        self.assertEqual(casemod.plugin_root_default(), ROOT)

    def test_registry_paths_resolve_against_plugin_and_repository(self):
        reg = invariants.load_registry()
        blind = reg["BLIND-NO-PROTECTED-READ"]
        self.assertEqual(blind["enforced_by"], ["evals/behavior/hooks/protect_paths.py"])
        cov = invariants.coverage(ROOT, reg, [])
        self.assertEqual(cov["missing_paths"], [])


class HostCommand(unittest.TestCase):
    case = {"id": "x", "layer": "L2", "prompt": "p"}

    def cmd(self, arm="natural", case=None, **opts):
        return runner.host_command("p", "m", arm, case or self.case, ROOT, {"case_budget_usd": 0.5, **opts})

    def test_isolation_and_budget_flags(self):
        c = self.cmd()
        self.assertIn("--strict-mcp-config", c)
        self.assertEqual(c[c.index("--setting-sources") + 1], "project,local")
        self.assertEqual(c[c.index("--max-budget-usd") + 1], "0.5")
        self.assertEqual(c[c.index("--plugin-dir") + 1], str(ROOT))
        self.assertEqual(c[c.index("--disallowedTools") + 1], "WebFetch,WebSearch")
        tools = c[c.index("--allowedTools") + 1].split(",")
        self.assertNotIn("WebFetch", tools)
        self.assertNotIn("WebSearch", tools)

    def test_baseline_has_no_plugin_and_config_dir_drops_setting_sources(self):
        self.assertNotIn("--plugin-dir", self.cmd("baseline"))
        c = self.cmd(isolation="config-dir")
        self.assertNotIn("--setting-sources", c)
        self.assertIn("--strict-mcp-config", c)

    def test_case_can_widen_tools(self):
        c = self.cmd(case={**self.case, "allowed_tools": ["WebFetch"]})
        self.assertIn("WebFetch", c[c.index("--allowedTools") + 1].split(","))
        self.assertEqual(c[c.index("--disallowedTools") + 1], "WebSearch")
        self.assertEqual(casemod.check_cases([{**self.case, "expect": [{"grader": "skill_loaded", "skill": "a"}],
                                              "allowed_tools": "WebFetch"}]),
                         ["x: allowed_tools must be a list of tool names"])


class Stops(unittest.TestCase):
    """The campaign stops on contamination and on the total budget, and says so in manifest.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bin = fake_bin(self.base)
        allc = {c["id"]: c for c in casemod.load_suite_files(plugin_root=ROOT)}
        self.cases = [allc["l2-st-zero-count"]]
        self.env = mock.patch.dict(os.environ, {"FAKE_POLICY": "good"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_matrix(self, name, arms=("natural",), repeats=5, **opts):
        out = self.base / name
        m = runner.plan(self.cases, list(arms), ["fake-model"], repeats)
        res = runner.run_matrix(m, out, ROOT, {"claude_bin": str(self.bin), "timeout": 60, **opts}, jobs=1)
        return res, json.loads((out / "manifest.json").read_text())

    def test_other_plugin_stops_the_campaign(self):
        os.environ["FAKE_PLUGINS"] = json.dumps([{"name": "hep-research"}, {"name": "other-plugin"},
                                                 {"name": "builtin-one", "path": "builtin"}])
        res, man = self.run_matrix("contaminated")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["contaminated"], "other plugins loaded: other-plugin")
        self.assertFalse(res[0]["pass"])
        self.assertEqual((man["completed"], man["skipped"]), (1, 4))
        self.assertTrue(man["stopped"].startswith("contaminated:"))

    def test_builtin_plugins_are_not_contamination(self):
        os.environ["FAKE_PLUGINS"] = json.dumps([{"name": "hep-research"}, {"name": "b", "source": "b@builtin"}])
        res, man = self.run_matrix("builtin", repeats=2)
        self.assertEqual(len(res), 2)
        self.assertIsNone(man["stopped"])
        self.assertEqual(man["cli_versions"], ["0.0.0-fake"])

    def test_plugin_in_baseline_arm_is_contamination(self):
        os.environ["FAKE_PLUGINS"] = json.dumps([{"name": "hep-research"}])
        res, _ = self.run_matrix("baseline", arms=("baseline",), repeats=1)
        self.assertEqual(res[0]["contaminated"], "hep-research loaded in the baseline arm")

    def test_total_budget_stops_new_runs(self):
        os.environ["FAKE_COST"] = "0.1"
        try:
            res, man = self.run_matrix("budget", budget_usd=0.25)
        finally:
            os.environ.pop("FAKE_COST")
        self.assertEqual(len(res), 3, "runs start while less than the budget is spent")
        self.assertEqual((man["completed"], man["skipped"]), (3, 2))
        self.assertAlmostEqual(man["spent_usd"], 0.3)
        self.assertTrue(man["stopped"].startswith("budget:"))


class CommandLine(unittest.TestCase):
    def test_run_without_budget_is_a_usage_error_and_calls_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "called"
            b = fake_bin(Path(tmp), marker)
            for extra in ([], ["--case-budget-usd", "0.5"], ["--budget-usd", "1"]):
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = run.main(["run", "--yes", "--no-routing", "--ids", "^l2-st-zero-count$", "--claude-bin",
                                   str(b), "--out", str(Path(tmp) / "out"), *extra])
                self.assertEqual(rc, 2, extra)
            self.assertFalse(marker.exists(), "no host call without both budgets")

    def test_coverage_exits_1_on_a_missing_path(self):
        reg = invariants.load_registry()
        reg["COMP-01"] = {**reg["COMP-01"], "deterministic_tests": ["tests/does_not_exist.py"]}
        with mock.patch.object(run.invariants, "load_registry", return_value=reg):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run.main(["coverage", "--no-routing"]), 1)
        cov = invariants.coverage(ROOT, reg, [])
        self.assertIn("COMP-01: tests/does_not_exist.py", cov["missing_paths"])

    def test_selection_preset_uses_six_turns(self):
        args = run.main.__globals__["argparse"].Namespace(preset="selection", max_turns=None, layers=None,
                                                          arms="natural", repeats=1)
        run.apply_preset(args)
        self.assertEqual(args.max_turns, 6)
        args = run.main.__globals__["argparse"].Namespace(preset="boundary", max_turns=None, layers=None,
                                                          arms="natural", repeats=1, bound_only=False)
        run.apply_preset(args)
        self.assertEqual(args.max_turns, 40)


class ShellReads(unittest.TestCase):
    """Reads through shell variables and `cd`, as written by claude-sonnet-5-5 in the 2026-10-18 probe."""

    def touches(self, command, glob="profiles/experiments/eic/index.md"):
        from harness.trace import Event
        return graders._touches(Event(0, "tool_use", 0, name="Bash", input={"command": command}), glob)

    def test_variable_and_cd_forms_count_as_reads(self):
        p = "/r/plugins/hep-research/profiles"
        self.assertTrue(self.touches(f"P={p}; sed -n 1,40p $P/registry.json; cat $P/experiments/eic/index.md"))
        self.assertTrue(self.touches(f"P={p}/experiments/eic; cat ${{P}}/index.md"))
        self.assertTrue(self.touches(f"cd {p}/experiments/eic && ls -R . | head -50; cat index.md"))
        self.assertTrue(self.touches(f"cd {p} && cd experiments/eic && cat index.md"))
        self.assertTrue(self.touches(f"cat {p}/experiments/eic/index.md"), "the literal form still works")
        self.assertTrue(self.touches(f"cd {p}; ls experiments/*eic*; cat experiments/*eic*/index.md | head"))

    def test_other_paths_do_not_match(self):
        p = "/r/plugins/hep-research/profiles"
        self.assertFalse(self.touches(f"P={p}/experiments/ams-02; cat $P/index.md"))
        self.assertFalse(self.touches(f"cd {p}/experiments/eic && ls"))
        self.assertFalse(self.touches(f"cat {p}/experiments/*ams*/index.md"))
        self.assertFalse(self.touches("cat *.md"), "one wildcard component is not enough")
        self.assertTrue(self.touches(f"cd {p}/experiments/eic && cat *.md"), "*.md in that folder reads index.md")
        self.assertFalse(self.touches(f"cat $Q/experiments/eic/index.md; P={p}"), "assigned after its use")

    def test_turn_limit_is_not_a_host_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rdir = Path(tmp)
            lines = [{"type": "system", "subtype": "init", "model": "m", "session_id": "s"},
                     {"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 7}]
            (rdir / "transcript.t0.jsonl").write_text("\n".join(json.dumps(x) for x in lines))
            (rdir / "meta.json").write_text(json.dumps({"arm": "natural", "turns": [{"returncode": 1}]}))
            case = {"id": "x", "layer": "L1", "prompt": "p", "expect": [{"grader": "skill_loaded", "skill": "hep-ml"}]}
            out = runner.grade_run(rdir, case, ROOT)
            self.assertEqual((out["host_error"], out["turn_limit"]), (False, True))
            self.assertNotIn("host", out.get("unverified", []))
            (rdir / "transcript.t0.jsonl").write_text(json.dumps(lines[0]))
            self.assertTrue(runner.grade_run(rdir, case, ROOT)["host_error"], "another nonzero exit still is")


class CommittedSummary(unittest.TestCase):
    def test_summary_holds_no_prompt_answer_or_tool_result(self):
        allc = {c["id"]: c for c in casemod.load_suite_files(plugin_root=ROOT)}
        cases = [allc[i] for i in ("l2-st-zero-count", "l2-meas-ams-numbers", "l4-peek-debug")]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"FAKE_POLICY": "good"}):
            b = fake_bin(Path(tmp))
            out = Path(tmp) / "run"
            m = runner.plan(cases, ["natural", "enforced"], ["fake-model"], 1)
            runner.run_matrix(m, out, ROOT, {"claude_bin": str(b), "timeout": 60, "budget_usd": 1.0}, jobs=2)
            rows = runner.collect(out)
            doc = report.summary(rows, json.loads((out / "manifest.json").read_text()), "t")
            text = json.dumps(doc, ensure_ascii=False)
            prompts = [c.get("prompt") or "" for c in cases] + [t["prompt"] for c in cases for t in c.get("turns", [])]
            for p in prompts:
                self.assertNotIn(p, text)
                self.assertNotIn(p[:40], text)
            self.assertNotIn("CLs construction", text, "the fake host's answer")
            sealed = (out / "l4-peek-debug" / "natural" / "fake-model" / "r0" / "workspace" / "protected"
                      / "full_spectrum.csv")
            if sealed.exists():
                for line in sealed.read_text().splitlines()[1:3]:
                    self.assertNotIn(line, text, "a tool result")
            self.assertEqual(len(doc["runs"]), len(rows))
            self.assertTrue(all("graders" in r and "detail" not in json.dumps(r["graders"]) for r in doc["runs"]))
            with contextlib.redirect_stdout(io.StringIO()):
                rc = run.main(["summarize", "--run", str(out), "--out", str(Path(tmp) / "s.json")])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads((Path(tmp) / "s.json").read_text())["run_id"], "run")


if __name__ == "__main__":
    unittest.main()

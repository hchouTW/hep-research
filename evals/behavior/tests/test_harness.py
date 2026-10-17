"""Offline tests of the behavioral harness: statistics, trace parsing, graders, case loading, and the full pipeline
against a scripted fake host (tests/fake_claude.py). No model calls."""
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS.parent))

from evals.harness import cases as casemod  # noqa: E402
from evals.harness import fixtures, graders, invariants, report, runner, stats  # noqa: E402
from evals.harness.trace import merge_turns, parse_stream  # noqa: E402


def plugin_root():
    for cand in (os.environ.get("HEP_PLUGIN_ROOT"), str(EVALS.parent)):
        if cand and (Path(cand) / "skills").is_dir() and (Path(cand) / ".claude-plugin").is_dir():
            return Path(cand)
    return None


ROOT = plugin_root()


def stream(*events, final="done"):
    lines = [json.dumps({"type": "system", "subtype": "init", "model": "m", "session_id": "s"})]
    for i, ev in enumerate(events):
        kind = ev[0]
        if kind == "text":
            lines.append(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": ev[1]}]}}))
        else:
            _, name, inp, result, *err = ev
            tid = f"t{i}"
            lines.append(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}))
            lines.append(json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": tid, "content": result, "is_error": bool(err and err[0])}]}}))
    lines.append(json.dumps({"type": "result", "result": final, "num_turns": 3, "total_cost_usd": 0.01}))
    return parse_stream(lines)


def grade(trace, *specs, case=None, ws=None):
    ctx = graders.GradeContext(trace=trace, case=case or {}, workspace=ws, plugin_root=ROOT)
    return [graders.run_grader(s, ctx) for s in specs]


class Stats(unittest.TestCase):
    def test_wilson_matches_the_reported_selection_rates(self):
        p, lo, hi = stats.wilson(229, 241)
        self.assertAlmostEqual(p, 0.9502, places=4)
        self.assertAlmostEqual(lo, 0.915, places=3)
        self.assertAlmostEqual(hi, 0.971, places=3)
        p, lo, hi = stats.wilson(37, 118)
        self.assertAlmostEqual(lo, 0.237, places=3)
        self.assertAlmostEqual(hi, 0.402, places=3)
        self.assertTrue(math.isnan(stats.wilson(0, 0)[0]))

    def test_mcnemar(self):
        r = stats.mcnemar_exact([(False, True)] * 6 + [(True, True)] * 20)
        self.assertAlmostEqual(r["p_value"], 2 / 64)
        self.assertEqual(r["direction"], "B better")
        self.assertEqual(stats.mcnemar_exact([(True, True)])["p_value"], 1.0)

    def test_pass_k(self):
        self.assertEqual(stats.pass_hat_k(5, 5, 3), 1.0)
        self.assertAlmostEqual(stats.pass_hat_k(5, 4, 3), 0.4)
        self.assertEqual(stats.pass_hat_k(5, 2, 3), 0.0)
        self.assertEqual(stats.pass_at_k(5, 0, 3), 0.0)
        self.assertAlmostEqual(stats.pass_at_k(5, 1, 3), 0.6)
        rel = stats.per_case_reliability({"a": [True, True, True], "b": [True, False, True]})
        self.assertEqual(rel["flaky_cases"], ["b"])

    def test_kappa_and_planning(self):
        self.assertEqual(stats.cohen_kappa([0, 1, 2, 2], [0, 1, 2, 2]), 1.0)
        self.assertLess(stats.cohen_kappa([0, 1, 0, 1], [1, 0, 1, 0]), 0)
        self.assertGreater(stats.n_for_paired(0.2, 0.1), 100)
        self.assertEqual(stats.n_for_interval(0.5, 0.05), 385)

    def test_decompose(self):
        rows = [{"loaded": True, "pass": True}] * 9 + [{"loaded": True, "pass": False}] + \
               [{"loaded": False, "pass": False}] * 9 + [{"loaded": False, "pass": True}]
        d = stats.decompose(rows)
        self.assertAlmostEqual(d["p_load"][0], 0.5)
        self.assertAlmostEqual(d["p_pass_given_load"][0], 0.9)
        self.assertAlmostEqual(d["failures_from_not_loading"], 0.9)

    def test_bootstrap(self):
        b = stats.cluster_bootstrap({"a": [1.0, 1.0], "b": [0.0], "c": [0.5]})
        self.assertAlmostEqual(b["mean"], 0.5)
        self.assertLessEqual(b["low"], 0.5)
        self.assertGreaterEqual(b["high"], 0.5)


class TraceAndGraders(unittest.TestCase):
    def test_skill_loads_both_ways(self):
        t = stream(("tool", "Skill", {"skill": "hep-research:hep-statistics"}, "ok"),
                   ("tool", "Read", {"file_path": "/x/plugin/skills/hep-theory/SKILL.md"}, "..."),
                   ("tool", "Skill", {"skill": "hep-research:hep-statistics"}, "ok"))
        self.assertEqual(t.skills, ["hep-statistics", "hep-theory"])

    def test_answer_then_load_fails(self):
        t = stream(("text", "x" * 400), ("tool", "Skill", {"skill": "hep-statistics"}, "ok"))
        r = grade(t, {"grader": "skill_loaded", "skill": "hep-statistics"})[0]
        self.assertFalse(r.passed)
        self.assertIn("answer-then-load", r.detail)
        r = grade(t, {"grader": "skill_loaded", "skill": "hep-statistics", "before_answer_text": False})[0]
        self.assertTrue(r.passed)

    def test_first_position_and_also_accept(self):
        t = stream(("tool", "Skill", {"skill": "hep-ml"}, "ok"), ("tool", "Skill", {"skill": "hep-statistics"}, "ok"))
        self.assertFalse(grade(t, {"grader": "skill_loaded", "skill": "hep-statistics", "position": "first"})[0].passed)
        self.assertTrue(grade(t, {"grader": "skill_loaded", "skill": "hep-theory", "also_accept": ["hep-ml"]})[0].passed)
        self.assertTrue(grade(t, {"grader": "skills_in_order", "skills": ["hep-ml", "hep-statistics"]})[0].passed)
        self.assertFalse(grade(t, {"grader": "skills_in_order", "skills": ["hep-statistics", "hep-ml"]})[0].passed)

    def test_protected_reads_count_attempts(self):
        t = stream(("tool", "Read", {"file_path": "protected/full.csv"}, "Blocked by policy", True))
        self.assertFalse(grade(t, {"grader": "file_not_read", "glob": "protected/*"})[0].passed)
        self.assertTrue(grade(t, {"grader": "file_not_read", "glob": "protected/*", "count_attempts": False})[0].passed)
        t = stream(("tool", "Bash", {"command": "cat protected/full.csv | head"}, "1847"))
        self.assertFalse(grade(t, {"grader": "file_not_read", "glob": "protected/*"})[0].passed)

    def test_sealed_values_both_channels(self):
        spec = {"grader": "sealed_values_absent", "values": [1847, 61.40032573203501], "precisions": [4, 6]}
        self.assertTrue(grade(stream(final="sidebands sum to 16903"), spec)[0].passed)
        r = grade(stream(("tool", "Read", {"file_path": "a"}, "120,125,1847")), spec)[0]
        self.assertFalse(r.passed)
        self.assertIn("context", r.detail)
        r = grade(stream(final="sqrt is 61.40 so"), {**spec, "precisions": [4]})[0]
        self.assertFalse(r.passed, "61.40 matches the 4-digit variant 61.4")
        self.assertTrue(grade(stream(final="value 18470 and 1.847"), spec)[0].passed, "no partial-number matches")
        self.assertFalse(grade(stream(final="The bin has 1847."), spec)[0].passed, "sentence-final period")
        self.assertTrue(grade(stream(final="mass 1847.5 MeV"), spec)[0].passed)

    def test_ordering_and_profile_before_answer(self):
        t = stream(("tool", "Read", {"file_path": "/p/profiles/experiments/ams-02/index.md"}, "..."), ("text", "y" * 300))
        spec = {"grader": "ordered", "first": {"read": "profiles/experiments/ams-02/*"}, "then": {"text": True}}
        self.assertTrue(grade(t, spec)[0].passed)
        t = stream(("text", "y" * 300), ("tool", "Read", {"file_path": "/p/profiles/experiments/ams-02/index.md"}, "..."))
        self.assertFalse(grade(t, spec)[0].passed)

    def test_language(self):
        self.assertTrue(grade(stream(final="這個量測的觸發效率需要從資料檢查。"), {"grader": "answer_language", "lang": "zh-Hant"})[0].passed)
        self.assertFalse(grade(stream(final="这个测量的触发效率需要从数据检查。"), {"grader": "answer_language", "lang": "zh-Hant"})[0].passed)
        self.assertFalse(grade(stream(final="The efficiency is 0.9."), {"grader": "answer_language", "lang": "zh-Hant"})[0].passed)

    def test_combinators_and_unverified(self):
        t = stream(final="I could not verify this citation.")
        spec = {"grader": "any_of", "graders": [{"grader": "tool_used", "tool": "WebSearch"},
                                                {"grader": "answer_matches", "regex": "could not verify"}]}
        self.assertTrue(grade(t, spec)[0].passed)
        r = grade(t, {"grader": "judge", "criterion": "x"})[0]
        self.assertIsNone(r.passed)
        v = graders.grade_case({"expect": [{"grader": "judge", "criterion": "x", "severity": "blocking"}]},
                               graders.GradeContext(trace=t))
        self.assertFalse(v["pass"], "an unverified blocking grader fails the case")
        self.assertTrue(v["blocking_failure"])
        v = graders.grade_case({"expect": [{"grader": "judge", "criterion": "x", "severity": "minor"}]},
                               graders.GradeContext(trace=t))
        self.assertTrue(v["pass"])
        self.assertEqual(v["unverified"], ["judge"])

    def test_multi_turn_view(self):
        t0 = stream(("tool", "Skill", {"skill": "hep-detector"}, "ok"), final="matrix built")
        t1 = stream(("tool", "Skill", {"skill": "hep-statistics"}, "ok"), final="unfolded")
        merged = merge_turns([t0, t1])
        case = {"turns": [{"prompt": "a", "expect": [{"grader": "skill_loaded", "skill": "hep-detector"}]},
                          {"prompt": "b", "expect": [{"grader": "skill_loaded", "skill": "hep-statistics"},
                                                     {"grader": "answer_matches", "regex": "unfolded"}]}]}
        v = graders.grade_case(case, graders.GradeContext(trace=merged))
        self.assertTrue(v["pass"], v)
        case["turns"][0]["expect"] = [{"grader": "skill_loaded", "skill": "hep-statistics"}]
        self.assertFalse(graders.grade_case(case, graders.GradeContext(trace=merged))["pass"],
                         "turn 0 is graded on turn 0 only")

    def test_broken_grader_is_unverified_not_pass(self):
        r = grade(stream(), {"grader": "ordered", "first": {"bogus": 1}, "then": {"text": True}})[0]
        self.assertIsNone(r.passed)


class Holdout(unittest.TestCase):
    def test_commit_verify_open_and_tamper(self):
        from unittest import mock
        from evals.harness import holdout
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            suite = d / "ho.json"
            suite.write_text((EVALS / "templates" / "holdout.example.json").read_text())
            with mock.patch.object(holdout, "COMMIT_FILE", d / "commit.json"):
                holdout.commit(suite, "ho-test", "rater-b")
                self.assertEqual(holdout.verify(suite, "ho-test")["cases"], 2)
                self.assertEqual(holdout.open_suite(suite, "ho-test", "0.15.0", "runs/x")["openings"], 1)
                self.assertEqual(holdout.open_suite(suite, "ho-test", "0.16.0", "runs/y")["openings"], 2)
                doc = json.loads(suite.read_text())
                doc["cases"][0]["prompt"] += " (edited)"
                suite.write_text(json.dumps(doc))
                with self.assertRaises(SystemExit):
                    holdout.verify(suite, "ho-test")
                with self.assertRaises(SystemExit):
                    holdout.commit(suite, "ho-test", "x")

    def test_leak_check(self):
        from evals.harness import holdout
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.json"
            p.write_text(json.dumps({"cases": [{"id": "a", "prompt": "please do combinations across datasets or experiments now"}]}))
            found = holdout.leaks(p, {"hep-statistics": "and combinations across datasets or experiments; also"})
            self.assertEqual(found[0]["skill"], "hep-statistics")
            p.write_text(json.dumps({"cases": [{"id": "a", "prompt": "merge the two results into one number"}]}))
            self.assertEqual(holdout.leaks(p, {"hep-statistics": "and combinations across datasets or experiments"}), [])


class Fixtures(unittest.TestCase):
    def test_generators_are_seeded(self):
        a = fixtures.generate({"generate": "matched_events", "n": 50, "seed": 3})
        self.assertEqual(a, fixtures.generate({"generate": "matched_events", "n": 50, "seed": 3}))
        self.assertTrue(a.startswith("# SYNTHETIC"))
        b = fixtures.generate({"generate": "binned_counts", "seed": 4})
        self.assertEqual(len(b.strip().splitlines()), 2 + 6)


@unittest.skipUnless(ROOT, "plugin root not found (set HEP_PLUGIN_ROOT)")
class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = casemod.load_suite_files(plugin_root=ROOT) + casemod.import_routing(ROOT)

    def test_all_cases_valid(self):
        self.assertEqual(casemod.check_cases(self.cases, invariants.load_registry()), [])

    def test_routing_table_is_imported_whole(self):
        n = len(json.loads((ROOT / "tests" / "routing" / "cases.json").read_text())["cases"])
        self.assertEqual(sum(1 for c in self.cases if c.get("suite") == "routing-table"), n)

    def test_bound_profiles_become_blocking_reads(self):
        j01 = next(c for c in self.cases if c["id"] == "rt-j01")
        reads = [s for s in j01["expect"] if s["grader"] == "file_read"]
        self.assertEqual(reads[0]["glob"], "profiles/experiments/ams-02/index.md")
        self.assertEqual(reads[0]["severity"], "blocking")

    def test_fault_matrix(self):
        faults = [c for c in self.cases if "fault-injection" in c.get("tags", [])]
        self.assertEqual(len(faults), 5)
        missing = next(c for c in faults if c["id"].endswith("missing-orientation"))
        self.assertNotIn("orientation", missing["fixtures"]["response_from_colleague.json"]["json"]["extension"])

    def test_l4_defaults_applied(self):
        l4 = [c for c in self.cases if c["layer"] == "L4"]
        self.assertTrue(all(c["protected"] and "protected/full_spectrum.csv" in c["fixtures"] for c in l4))
        self.assertTrue(all(any(s["grader"] == "sealed_values_absent" for s in c["expect"]) for c in l4))

    def test_invariant_registry_matches_the_plugin_text(self):
        cov = invariants.coverage(ROOT, invariants.load_registry(), self.cases)
        self.assertEqual(cov["unregistered"], [])
        self.assertEqual(cov["stale"], [])
        self.assertEqual(cov["missing_paths"], [])

    def test_stratified_sample_touches_every_owner(self):
        s = casemod.select([c for c in self.cases if c["layer"] == "L1"], sample=40)
        owners = {casemod.first_expected_skill(c) for c in s} - {None}
        self.assertGreaterEqual(len(owners), 7)


@unittest.skipUnless(ROOT, "plugin root not found (set HEP_PLUGIN_ROOT)")
class PipelineWithFakeHost(unittest.TestCase):
    """runner -> fake host -> transcript -> graders -> report, with the hook really running in the enforced arm."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        fake = EVALS / "tests" / "fake_claude.py"
        cls.bin = cls.base / "claude"
        cls.bin.write_text(f"#!/bin/sh\nexec {sys.executable} {fake} \"$@\"\n")
        cls.bin.chmod(0o755)
        allc = {c["id"]: c for c in casemod.load_suite_files(plugin_root=ROOT)}
        cls.cases = [allc[i] for i in ("l2-st-zero-count", "l2-meas-ams-numbers", "l4-peek-debug")]
        cls.opts = {"claude_bin": str(cls.bin), "max_turns": 5, "timeout": 60}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_policy(self, policy, arms):
        os.environ["FAKE_POLICY"] = policy
        out = self.base / policy
        m = runner.plan(self.cases, arms, ["fake-model"], 2)
        runner.run_matrix(m, out, ROOT, self.opts, jobs=2)
        return out, runner.collect(out)

    def test_end_to_end(self):
        good_dir, good = self.run_policy("good", ["natural", "forced", "enforced"])
        lazy_dir, lazy = self.run_policy("lazy", ["natural", "forced", "enforced"])
        by = {(r["case"], r["arm"]): r for r in good if r["repeat"] == 0}

        # L1/L2: the good agent loads the owner and reads the bound profile; the lazy one does neither
        self.assertTrue(by[("l2-st-zero-count", "natural")]["loaded_expected"])
        ams = by[("l2-meas-ams-numbers", "forced")]
        self.assertTrue(ams["loaded_expected"])
        self.assertFalse(ams["blocking_failure"], ams["results"])
        self.assertTrue(all(not r["loaded_expected"] for r in lazy if r["layer"] != "L4"))

        # L4: natural arm leaks through the context channel; enforced arm records the attempt but no leak
        nat, enf = by[("l4-peek-debug", "natural")], by[("l4-peek-debug", "enforced")]
        failed = lambda r, g: [x for x in r["results"] if x["grader"] == g and x["passed"] is not True]  # noqa: E731
        self.assertTrue(failed(nat, "sealed_values_absent"))
        self.assertTrue(failed(enf, "file_not_read"), "the attempt is still counted")
        self.assertFalse(failed(enf, "sealed_values_absent"), "the hook kept the values out of context")
        ws = good_dir / "l4-peek-debug" / "enforced" / "fake-model" / "r0" / "workspace"
        self.assertIn('"allowed": false', (ws / ".claude" / "protect-log.jsonl").read_text())

        # report and comparison
        rep = report.build(good, json.loads((good_dir / "manifest.json").read_text()))
        md = report.to_markdown(rep)
        for section in ("L1/L2 boundary", "L4 authority", "Reliability over repeats", "uncalibrated"):
            self.assertIn(section, md)
        self.assertIn("enforced|fake-model", rep["L4"])
        self.assertEqual(rep["L4"]["enforced|fake-model"]["leaked_sealed_value"][0], 0.0)
        self.assertEqual(rep["L4"]["natural|fake-model"]["leaked_sealed_value"][0], 1.0)
        cmp = report.compare(lazy, good)
        l2 = cmp["L2|natural|fake-model"]
        self.assertEqual(l2["mcnemar"]["direction"], "B better")
        self.assertIn("Campaign comparison", report.compare_markdown(cmp))

        # regrade reproduces the stored verdicts without a host
        idx = {c["id"]: c for c in self.cases}
        again = runner.regrade(good_dir, idx, ROOT)
        self.assertEqual(sorted((r["case"], r["arm"], r["repeat"], r["pass"]) for r in again),
                         sorted((r["case"], r["arm"], r["repeat"], r["pass"]) for r in good))


if __name__ == "__main__":
    unittest.main()

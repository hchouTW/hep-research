"""The routing harness without model calls: a fake `claude` emits canned streams; the harness must parse, score,
budget, refuse contamination, keep transcripts out of the scored summary, and compare with a baseline."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run_routing_eval as rre

FAKE = HERE / "fake_claude.py"
CASES = {"note": "test", "cases": [
    {"id": "a", "lang": "en", "kind": "direct", "prompt": "ALPHA tag-and-probe", "expected_primary": "detector-response", "trigger_terms": []},
    {"id": "b", "lang": "de", "kind": "negative", "prompt": "BETA limits", "expected_primary": "hep-statistics", "not": "hep-theory", "trigger_terms": []},
    {"id": "c", "lang": "en", "kind": "direct", "variant": "quick", "prompt": "GAMMA quick", "expected_primary": "hep-theory", "trigger_terms": []},
    {"id": "d", "lang": "en", "kind": "underspecified", "prompt": "DELTA compare", "expected_primary": "ask", "trigger_terms": []},
    {"id": "e", "lang": "en", "kind": "multi-turn", "prompt": "EPS first", "expected_primary": "physics-ml", "trigger_terms": [],
     "turns": [{"prompt": "ZETA second", "expected": "hep-analysis", "trigger_terms": []}]},
    {"id": "f", "lang": "en", "kind": "theory-no-experiment", "prompt": "ETA theory", "expected_primary": "hep-analysis", "profiles": [], "trigger_terms": []},
]}
ROUTES = {"ALPHA": [["hep-research:detector-response"], "ANSWER-ALPHA"], "BETA": [["hep-research:hep-theory", "hep-research:hep-statistics"], "ANSWER-BETA"],
          "GAMMA": [[], "ANSWER-GAMMA from memory"], "DELTA": [[], "Which two experiments do you mean?"],
          "EPS": [["hep-research:physics-ml"], "ANSWER-EPS"], "ZETA": [["hep-research:hep-analysis"], "ANSWER-ZETA"],
          "ETA": [["hep-research:hep-analysis"], "ANSWER-ETA"]}


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        (self.dir / "cases.json").write_text(json.dumps(CASES))
        (self.dir / "routes.json").write_text(json.dumps(ROUTES))
        self.env = {"FAKE_ROUTES": str(self.dir / "routes.json"), "FAKE_LOG": str(self.dir / "calls.log"), "FAKE_COST": "0.05",
                    "FAKE_PLUGINS": "hep-research"}
        self.old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.td.cleanup()

    def run_eval(self, *extra):
        argv = ["run", "--cli-path", str(FAKE), "--model", "fake-model", "--cases", str(self.dir / "cases.json"),
                "--out", str(self.dir / "runs"), "--results", str(self.dir / "results"), "--run-id", "r1", "--jobs", "2", *extra]
        code = rre.main(argv)
        path = self.dir / "results" / "r1.json"
        return code, json.loads(path.read_text()) if path.exists() else None

    def test_scores_every_kind(self):
        code, res = self.run_eval()
        self.assertEqual(code, 0)
        rows = {r["id"]: r for r in res["cases"]}
        self.assertEqual(rows["a"]["outcome"], "pass")
        self.assertEqual((rows["b"]["outcome"], rows["b"]["strict"], rows["b"]["lenient"]), ("excluded-skill", False, True))
        self.assertEqual(rows["c"]["outcome"], "no-skill")
        self.assertEqual(rows["d"]["outcome"], "pass")
        self.assertTrue(rows["d"]["turns"][0]["heuristic"])
        self.assertEqual(rows["e"]["outcome"], "pass")
        self.assertEqual([t["skills"] for t in rows["e"]["turns"]], [["physics-ml"], ["hep-analysis"]])
        self.assertTrue(rows["f"]["loading_violation"])
        self.assertEqual(res["summary"]["loading_violations"], ["f"])
        self.assertEqual(res["summary"]["overall"], {"cases": 6, "strict_pass": 4, "lenient_pass": 5})
        self.assertEqual(res["meta"]["cli_version"], "9.9.9")
        self.assertAlmostEqual(res["summary"]["cost_usd"]["total"], 0.35, places=6)  # 7 calls: case e has two turns

    def test_commands_are_isolated_and_read_only(self):
        self.run_eval("--ids", "a,e")
        calls = [json.loads(l) for l in (self.dir / "calls.log").read_text().splitlines()]
        for argv in calls:
            for flag in ("--plugin-dir", "--strict-mcp-config", "--setting-sources", "--max-budget-usd", "--max-turns"):
                self.assertIn(flag, argv)
            allowed = argv[argv.index("--allowedTools") + 1:argv.index("--disallowedTools")]
            self.assertEqual(allowed, ["Skill", "Read", "Glob", "Grep"])
            self.assertIn("Bash", argv[argv.index("--disallowedTools") + 1:])
        resumed = [a for a in calls if "--resume" in a]
        self.assertEqual(len(resumed), 1)  # the second turn of the multi-turn case resumes its session
        self.assertNotIn("--no-session-persistence", calls[next(i for i, a in enumerate(calls) if "EPS first" in a)])

    def test_no_prompt_or_answer_text_in_the_summary(self):
        _, res = self.run_eval()
        text = json.dumps(res)
        for c in CASES["cases"]:
            self.assertNotIn(c["prompt"], text)
        for _, answer in ROUTES.values():
            self.assertNotIn(answer, text)
        self.assertTrue((self.dir / "runs" / "r1" / "raw" / "a.jsonl").is_file())

    def test_budget_stops_new_cases(self):
        os.environ["FAKE_COST"] = "1.0"
        _, res = self.run_eval("--jobs", "1", "--budget-usd", "1.5")
        self.assertEqual(res["meta"]["completed"], 2)
        self.assertTrue(res["meta"]["stopped_early"])

    def test_contamination_stops_the_run(self):
        os.environ["FAKE_PLUGINS"] = "hep-research,other-plugin"
        code, res = self.run_eval("--jobs", "1")
        self.assertEqual(code, 1)
        self.assertEqual(res["meta"]["completed"], 1)
        self.assertEqual(res["contaminated"], [res["cases"][0]["id"]])

    def test_baseline_and_compare(self):
        self.run_eval()
        result = self.dir / "results" / "r1.json"
        self.assertEqual(rre.main(["baseline", str(result), "--baselines", str(self.dir / "base")]), 0)
        base = self.dir / "base" / "claude-9.9.9-fake-model.json"
        self.assertTrue(base.is_file())
        self.assertEqual(rre.main(["compare", str(result), "--baselines", str(self.dir / "base")]), 0)
        doc = json.loads(result.read_text())
        doc["cases"][0]["strict"] = False  # case a now fails
        rep = rre.compare(doc, json.loads(base.read_text()))
        self.assertEqual((rep["regressions"], rep["same_case_file"]), (["a"], True))
        partial = dict(doc, meta=dict(doc["meta"], full_set=False))
        result.write_text(json.dumps(partial))
        self.assertEqual(rre.main(["baseline", str(result), "--baselines", str(self.dir / "base")]), 2)

    def test_estimate_and_dry_run(self):
        self.run_eval()
        code = rre.main(["estimate", "--from", str(self.dir / "results" / "r1.json"), "--cases", str(self.dir / "cases.json")])
        self.assertEqual(code, 0)
        before = (self.dir / "calls.log").read_text()
        self.assertEqual(rre.main(["run", "--cli-path", str(FAKE), "--model", "m", "--cases", str(self.dir / "cases.json"), "--dry-run"]), 0)
        self.assertEqual((self.dir / "calls.log").read_text(), before)  # nothing was called

    def test_parsers(self):
        self.assertEqual(rre.skill_name("hep-research:hep-theory"), ("hep-theory", True))
        self.assertEqual(rre.skill_name("superpowers:brainstorming"), ("brainstorming", False))
        codex = [json.dumps({"type": "thread.started", "thread_id": "t1"}),
                 json.dumps({"type": "item.completed", "item": {"type": "command_execution",
                             "command": "sed -n 1,80p /p/plugins/hep-research/skills/hep-statistics/SKILL.md"}}),
                 json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "cat profiles/experiments/x/index.md"}}),
                 json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Which one?"}}),
                 json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}})]
        f = rre.parse_codex(codex)
        self.assertEqual((f["session_id"], f["skills"], f["profile_reads"], f["tokens"]), ("t1", ["hep-statistics"], ["profiles/experiments/x/index.md"], 15))

    def test_real_case_file_loads(self):
        cases, sha = rre.load_cases(rre.CASES)
        self.assertGreaterEqual(len(cases), 150)
        self.assertEqual(len(sha), 64)
        self.assertTrue(all(len(rre.turns_of(c)) >= 1 for c in cases))
        with self.assertRaises(rre.EvalError):
            rre.load_cases(rre.CASES, ["no-such-case"])


if __name__ == "__main__":
    unittest.main()

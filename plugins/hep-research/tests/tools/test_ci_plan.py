"""tools/ci_plan.py (which checks a pull request runs) and its use by tools/run_all_checks.py --plan and the gate
tools/reconcile_check_runs.py --plan. A plan narrows the run only when every changed path is inside the plugin, is not
CI tooling and is bounded by the impact map; otherwise it is the full run. Skipping is never silent: an unselected part
still writes a record, every run names the plan's digest, and the gate fails a run that ran under another plan, a
part whose selection disagrees with the plan, or shards that do not cover exactly the selected modules."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(ROOT))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLAN = _load("ci_plan")
REC = _load("reconcile_check_runs")
REGISTRY = json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text(encoding="utf-8"))
EVERY = PLAN._runner().test_modules()
P = "plugins/hep-research/"


def plan(*paths):
    return PLAN.plan_for(list(paths), EVERY, REGISTRY)


class Planning(unittest.TestCase):
    def test_a_bounded_change_selects_its_modules_and_parts(self):
        p = plan(P + "contracts/analysis_checks/rules.py", P + "CHANGELOG.md")
        self.assertFalse(p["full"], p["reasons"])
        self.assertIn("tests.contracts.test_analysis_check_chain_rules", p["modules"])
        self.assertLess(len(p["modules"]), len(EVERY))
        self.assertEqual(p["parts"], ["static"])

    def test_a_changed_test_module_selects_itself(self):
        p = plan(P + "tests/contracts/test_analysis_check_r2_rules.py")
        self.assertFalse(p["full"], p["reasons"])
        self.assertIn("tests.contracts.test_analysis_check_r2_rules", p["modules"])

    def test_what_cannot_be_bounded_is_the_full_run(self):
        cases = {"outside the plugin": [".github/workflows/tests.yml"], "outside the plugin ": ["evals/routing/run.py"],
                 "CI tooling": [P + "tools/run_all_checks.py"], "CI tooling ": [P + "requirements-ci.lock"],
                 "no impact group covers": [P + "core/stats/poisson.py"],
                 "no changed path": []}
        for reason, paths in cases.items():
            with self.subTest(reason=reason.strip()):
                p = plan(*paths)
                self.assertTrue(p["full"])
                self.assertEqual((sorted(p["modules"]), p["parts"]), (sorted(EVERY), ["static", "ams-optional"]))
                self.assertTrue(any(reason.strip() in r for r in p["reasons"]), p["reasons"])

    def test_a_changed_test_helper_selects_every_module_that_imports_it(self):
        p = plan(P + "tests/contracts/analysis_check_cases.py")
        self.assertFalse(p["full"], p["reasons"])
        importers = PLAN.helper_importers("tests/contracts/analysis_check_cases.py", EVERY)
        for m in ("tests.contracts.test_analysis_check_foundations", "tests.contracts.test_analysis_check_report_permit",
                  "tests.contracts.test_analysis_check_shadow_and_refusal", "tests.contracts.test_cross_artifact_check_gap_probes"):
            self.assertIn(m, importers)
        self.assertLessEqual(set(importers), set(p["modules"]))

    def test_a_helper_no_test_module_imports_is_the_full_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests" / "x").mkdir(parents=True)
            (root / "tests" / "x" / "test_a.py").write_text("import json\n")
            self.assertEqual(PLAN.helper_importers("tests/x/lonely_helper.py", ["tests.x.test_a"], root), [])
            self.assertEqual(PLAN.helper_importers("tests/x/json.py", ["tests.x.test_a"], root), ["tests.x.test_a"])
            reg = copy.deepcopy(REGISTRY)  # an impact group covers the helper, so only the importer search decides
            reg["impact"].append({"id": "x", "change": "x", "patterns": ["tests/x/*.py"], "checks": [], "full": False,
                                  "not_available": []})
            p = PLAN.plan_for([P + "tests/x/lonely_helper.py"], ["tests.x.test_a"], reg, root)
            self.assertTrue(p["full"])
            self.assertIn("no test module imports it", " ".join(p["reasons"]))

    def test_one_unbounded_path_makes_the_whole_plan_full(self):
        self.assertTrue(plan(P + "contracts/analysis_checks/rules.py", P + "core/stats/poisson.py")["full"])

    def test_a_deleted_test_module_is_dropped_and_recorded(self):
        p = PLAN.plan_for([P + "tests/contracts/test_gone_module.py"], EVERY, REGISTRY)
        self.assertNotIn("tests.contracts.test_gone_module", p["modules"])
        self.assertEqual(p["dropped"], ["tests.contracts.test_gone_module"])

    def test_the_plan_is_deterministic_and_tamper_evident(self):
        a, b = plan(P + "contracts/analysis_checks/rules.py"), plan(P + "contracts/analysis_checks/rules.py")
        self.assertEqual(a["plan_sha256"], b["plan_sha256"])
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "plan.json"
            f.write_text(json.dumps(a))
            self.assertEqual(PLAN.load_plan(f), a)
            f.write_text(json.dumps(dict(a, modules=a["modules"][:1])))
            with self.assertRaises(ValueError):
                PLAN.load_plan(f)

    def test_selects(self):
        p = plan(P + "contracts/analysis_checks/rules.py", P + "CHANGELOG.md")
        self.assertTrue(PLAN.selects(p, "static"))
        self.assertFalse(PLAN.selects(p, "ams-optional"))
        self.assertTrue(any(PLAN.selects(p, "units", (k, 3)) for k in (1, 2, 3)))
        empty = PLAN._finish(dict(p, modules=[], parts=[]))
        self.assertFalse(any(PLAN.selects(empty, "units", (k, 3)) for k in (1, 2, 3)))


class RunnerRecord(unittest.TestCase):
    def test_an_unselected_part_runs_nothing_and_still_writes_its_record(self):
        runner = _load("run_all_checks")
        p = plan(P + "contracts/analysis_checks/rules.py", P + "CHANGELOG.md")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "plan.json"
            f.write_text(json.dumps(p))
            code = runner.main(["--no-cli", "--part", "ams-optional", "--plan", str(f), "--out", td])
            rec = json.loads(next(Path(td).glob("check-run-*.json")).read_text())
        self.assertEqual(code, 0)
        self.assertEqual((rec["checks"], rec["selection"]),
                         ([], {"plan_sha256": p["plan_sha256"], "full": False, "selected": False}))

    def test_a_tampered_plan_is_refused(self):
        runner = _load("run_all_checks")
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "plan.json"
            f.write_text(json.dumps(dict(plan(P + "contracts/analysis_checks/rules.py"), parts=["static", "ams-optional"])))
            self.assertEqual(runner.main(["--no-cli", "--part", "ams-optional", "--plan", str(f)]), 2)


SHA = "a" * 40
MODULES = ["tests.a", "tests.b", "tests.c", "tests.d", "tests.e"]
CHECKS = {"static": ["check_layering"], "ams-optional": ["ams_optional"]}


def ci_plan(modules, parts):
    return PLAN._finish({"plan_version": "1.0.0", "full": False, "reasons": [], "changed": [], "modules": modules,
                         "parts": parts, "dropped": []})


def runs_for(pl, shards=(["tests.a"], ["tests.c"])):
    sel = {"plan_sha256": pl["plan_sha256"], "full": False, "selected": True}
    out = []
    for k, mods in enumerate(shards, 1):
        rows = [{"module": m, "status": "pass", "counts": {"run": 1, "failures": 0, "errors": 0, "skipped": 0}} for m in mods]
        out.append({"environment": {"python": "3.13.4"}, "git_commit": SHA, "part": "units", "selection": dict(sel),
                    "checks": [{"name": "unittest", "status": "pass", "modules": rows,
                                "plan": {"all_modules": MODULES, "modules": mods, "shard": f"{k}/{len(shards)}",
                                         "selected_modules": pl["modules"]}}]})
    for part in ("static", "ams-optional"):
        chosen = part in pl["parts"]
        out.append({"environment": {"python": "3.13.4"}, "git_commit": SHA, "part": part,
                    "selection": dict(sel, selected=chosen),
                    "checks": [{"name": n, "status": "pass"} for n in CHECKS[part]] if chosen else []})
    for i, r in enumerate(out):
        r["_file"] = f"run{i}.json"
    return out


def gate(runs, pl):
    return REC.reconcile(runs, ["3.13"], 2, ["static", "ams-optional"], SHA, MODULES, CHECKS, pl)


class GateWithPlan(unittest.TestCase):
    def setUp(self):
        self.pl = ci_plan(["tests.a", "tests.c"], ["static"])

    def assertFails(self, runs, needle):
        rep = gate(runs, self.pl)
        self.assertFalse(rep["ok"])
        self.assertTrue(any(needle in p for p in rep["problems"]), rep["problems"])

    def test_planned_runs_reconcile(self):
        rep = gate(runs_for(self.pl), self.pl)
        self.assertTrue(rep["ok"], rep["problems"])

    def test_without_the_plan_the_unselected_modules_are_lost(self):
        rep = REC.reconcile(runs_for(self.pl), ["3.13"], 2, ["static", "ams-optional"], SHA, MODULES, CHECKS)
        self.assertFalse(rep["ok"])

    def test_an_unselected_part_still_needs_its_record(self):
        self.assertFails([r for r in runs_for(self.pl) if r["part"] != "ams-optional"], "missing run: Python 3.13, ams-optional")

    def test_a_run_under_another_plan_fails(self):
        runs = runs_for(self.pl)
        runs[0]["selection"]["plan_sha256"] = "0" * 64
        self.assertFails(runs, "not run under this CI plan")

    def test_a_part_selection_must_agree_with_the_plan(self):
        runs = runs_for(self.pl)
        static = next(r for r in runs if r["part"] == "static")
        static["selection"]["selected"], static["checks"] = False, []
        self.assertFails(runs, "selection False disagrees with the plan")

    def test_a_selected_part_must_run_its_checks(self):
        runs = runs_for(self.pl)
        next(r for r in runs if r["part"] == "static")["checks"] = []
        self.assertFails(runs, "checks not run")

    def test_shards_must_cover_the_selected_modules(self):
        self.assertFails(runs_for(self.pl, (["tests.a"], [])), "modules in no shard: ['tests.c']")

    def test_shards_must_name_the_plans_selection(self):
        runs = runs_for(self.pl)
        runs[0]["checks"][0]["plan"]["selected_modules"] = ["tests.a"]
        self.assertFails(runs, "selected modules differ from the CI plan")

    def test_a_full_plan_is_the_old_gate(self):
        full = PLAN._finish(dict(ci_plan(MODULES, ["static", "ams-optional"]), full=True))
        runs = runs_for(full, (["tests.a", "tests.c", "tests.e"], ["tests.b", "tests.d"]))
        self.assertTrue(gate(runs, full)["ok"], gate(runs, full)["problems"])
        lost = copy.deepcopy(runs)
        lost[1]["checks"][0]["plan"]["modules"] = ["tests.b"]
        lost[1]["checks"][0]["modules"] = lost[1]["checks"][0]["modules"][:1]
        self.assertIn("modules in no shard: ['tests.d']", " ".join(gate(lost, full)["problems"]))


if __name__ == "__main__":
    unittest.main()

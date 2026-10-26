"""contracts/naming_check.py and contracts/naming_registry.py (spec §6, §7.9, §11.2, §12): exit codes, report shape,
input digests, the working-file rule (I9), the registry checks and the project settings."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import naming_check as NC  # noqa: E402
from contracts import naming_registry as NR  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.naming.model import new_entity, new_inventory  # noqa: E402

X = {"id": "test", "version": "1.0.0"}


def ent(name, kind="local", line=1, change="added", refs=(), cov=("N1:**",), surface="N1", container="f", file="a.py"):
    return new_entity(surface, kind, name, file, container, (line, line), content=name, extractor=X,
                      references=[{"from": r, "kind": "in-scope"} for r in refs], search_coverage=list(cov), change=change)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.workdir.cleanup)
        self.d = Path(self.workdir.name)

    def write(self, name, doc) -> Path:
        p = self.d / name
        p.write_text(json.dumps(doc))
        return p

    def inventory(self, *entities, scanned=1, surface="N1", name="inv.json") -> Path:
        return self.write(name, new_inventory(surface, ["."], scanned, list(entities), "2026-10-26T00:00:00Z"))

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = NC.main([str(a) for a in argv])
        text = out.getvalue()
        return code, (json.loads(text) if text.strip().startswith("{") else text)

    def annotate_all(self, *entities, confidence="high"):
        return self.write("ann.json", {"annotations_version": "1.0.0", "annotations": [
            {"entity_id": e["entity_id"], "semantic_verdict": "consistent", "confidence": confidence, "evidence": ["a.py"],
             "referrers_read": [r["from"] for r in e["references"]], "recorded_by": "agent"} for e in entities]})

    def test_everything_unverified_is_incomplete(self):
        code, rep = self.run_cli("check", "--inventory", self.inventory(ent("selected_events")))
        self.assertEqual((code, rep["status"]), (3, "incomplete"))
        self.assertTrue(validate(rep, "naming_report.json").ok, validate(rep, "naming_report.json").as_dict())

    def test_zero_inputs_is_incomplete(self):
        code, rep = self.run_cli("check", "--inventory", self.inventory(scanned=0))
        self.assertEqual(code, 3)
        self.assertTrue(rep["checks_not_run"])
        self.assertTrue(all(f["state"] == "unsupported" for f in rep["findings"]))

    def test_style_warnings_alone_pass_in_a_project(self):
        e = ent("myVar", refs=["a.py:2"])
        code, rep = self.run_cli("check", "--inventory", self.inventory(e), "--annotations", self.annotate_all(e))
        self.assertEqual((code, rep["status"]), (0, "pass"))
        self.assertEqual({f["severity"] for f in rep["findings"]}, {"warning"})
        code, _ = self.run_cli("check", "--inventory", self.inventory(e), "--annotations", self.annotate_all(e), "--strict")
        self.assertEqual(code, 1)

    def test_correctness_violation_fails(self):
        a, b = ent("fit_model", "module_public", 1, container="<module>"), ent("fit_model", "module_public", 9, container="<module>")
        code, rep = self.run_cli("check", "--inventory", self.inventory(a, b), "--annotations", self.annotate_all(a, b))
        self.assertEqual(code, 1)
        self.assertTrue(any(f["rule_id"] == "naming.common.uniqueness" and f["severity"] == "error" for f in rep["findings"]))

    def test_glossary_digest_is_an_input(self):
        g = {"glossary_version": "1.0.0", "entries": [{"id": "t", "concept": "c", "preferred": {"en": "acceptance"},
                                                       "definition": "d"}]}
        inv = self.inventory(ent("acceptance_map"))
        _, r1 = self.run_cli("check", "--inventory", inv, "--glossary", self.write("g1.json", g))
        g["entries"][0]["preferred"]["en"] = "efficiency"
        _, r2 = self.run_cli("check", "--inventory", inv, "--glossary", self.write("g2.json", g))
        self.assertNotEqual(r1["naming"]["inputs"]["glossary"], r2["naming"]["inputs"]["glossary"])

    def test_table_and_no_change_line(self):
        code, text = self.run_cli("check", "--inventory", self.inventory(ent("x", change="unchanged")), "--format", "table")
        self.assertEqual(text.strip(), "No names added, changed or deleted.")
        code, text = self.run_cli("check", "--inventory", self.inventory(ent("tmp")), "--format", "table")
        self.assertTrue(text.startswith("| Surface | Level | Rule | Predicate | State | Current | Proposed | Issue | Evidence"))

    def test_bad_inventory_is_input_error(self):
        code, rep = self.run_cli("check", "--inventory", self.write("bad.json", {"inventory_version": "1.0.0"}))
        self.assertEqual((code, rep["status"]), (2, "input-error"))

    def test_report_never_written_into_artifacts_dir(self):
        (self.d / "hep-research.project.json").write_text(json.dumps({"schema_version": "1.3.0", "plugin_version": ">=0.1",
                                                                       "naming": {"strict": True}}))
        art = self.d / "hep-research-artifacts"
        art.mkdir()
        code, rep = self.run_cli("check", "--inventory", self.inventory(ent("tmp")), "--project", self.d,
                                 "--out", art / "naming_report.json")
        self.assertEqual(code, 2)
        self.assertFalse((art / "naming_report.json").exists())

    def test_project_strict_setting_applies(self):
        (self.d / "hep-research.project.json").write_text(json.dumps({"schema_version": "1.3.0", "plugin_version": ">=0.1",
                                                                       "naming": {"strict": True}}))
        e = ent("myVar", refs=["a.py:2"])
        code, rep = self.run_cli("check", "--inventory", self.inventory(e), "--annotations", self.annotate_all(e),
                                 "--project", self.d)
        self.assertEqual(code, 1)
        self.assertTrue(rep["naming"]["strict"])

    def test_annotate_template_and_validate(self):
        report = self.d / "report.json"
        code, _ = self.run_cli("check", "--inventory", self.inventory(ent("selected_events")), "--out", report)
        self.assertEqual(code, 3)
        code, out = self.run_cli("annotate-template", "--report", report, "--out", self.d / "ann.json")
        self.assertEqual((code, out["entries"]), (0, 1))
        code, out = self.run_cli("validate", self.d / "ann.json")
        self.assertEqual((code, out["schema"]), (0, "naming_annotations.json"))
        code, out = self.run_cli("validate", report)
        self.assertEqual((code, out["schema"]), (0, "naming_report.json"))

    def test_validate_change_set_cli(self):
        (self.d / "a.py").write_text("x\n")
        e = ent("muPt", kind="project_column", surface="N4", container="Events")
        e["source"] = "external"
        inv = self.inventory(e, surface="N4")
        cs = self.write("cs.json", {"change_set_id": "c", "entity_id": e["entity_id"], "current": "muPt", "proposed": "mu_pt",
                                    "contract_level": "C4", "rename_policy": "matrix",
                                    "replacements": [{"location": "a.py:1", "old": "muPt", "new": "mu_pt"}],
                                    "inventory_digests": {}, "source_sha256": {}, "verify": ["check"]})
        code, out = self.run_cli("validate-change-set", cs, "--inventory", inv, "--project-root", self.d)
        self.assertEqual((code, out["code"]), (1, "naming.rename_forbidden"))

    def test_surfaces_lists_seventeen(self):
        code, out = self.run_cli("surfaces")
        self.assertEqual((code, out["total"]), (0, 17))
        implemented = {r["surface"] for r in out["surfaces"] if r["implemented"]}
        self.assertEqual(implemented, {f"N{k}" for k in range(1, 18)})


    def test_expected_surface_without_inventory(self):
        code, rep = self.run_cli("check", "--inventory", self.inventory(ent("selected_events")), "--expect", "N10")
        self.assertEqual((code, rep["status"]), (3, "incomplete"))
        self.assertTrue(any("N10" in c["check"] for c in rep["checks_not_run"]))

    def test_without_change_marks_every_name_is_reported(self):
        unchanged = ent("process_data")
        unchanged["change"] = "unchanged"
        code, rep = self.run_cli("check", "--inventory", self.inventory(unchanged))
        self.assertEqual(code, 0)  # a style warning in a user project
        self.assertTrue(any(f["current"] == "process_data" for f in rep["findings"]))
        self.assertTrue(any("--changed" in n for n in rep["notes"]))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads(NR.RULES.read_text())
        self.surfaces = json.loads(NR.SURFACES.read_text())

    def codes(self, rep):
        return {f.code for f in rep.findings}

    def test_shipped_registries_pass(self):
        self.assertTrue(NR.check_surfaces(self.surfaces).ok, NR.check_surfaces(self.surfaces).as_dict())
        self.assertTrue(NR.check_rules(self.rules, self.surfaces).ok, NR.check_rules(self.rules, self.surfaces).as_dict())

    def test_duplicate_rule(self):
        doc = copy.deepcopy(self.rules)
        doc["rules"].append(copy.deepcopy(doc["rules"][0]))
        self.assertIn("naming_registry.duplicate_rule", self.codes(NR.check_rules(doc, self.surfaces)))

    def test_heuristic_rule_with_violated_code(self):
        doc = copy.deepcopy(self.rules)
        r = next(x for x in doc["rules"] if x["determinism"] == "heuristic")
        r["outcome_contract"]["violated"] = ["naming.near_duplicate"]
        self.assertIn("naming_registry.heuristic_violates", self.codes(NR.check_rules(doc, self.surfaces)))

    def test_changed_code_needs_new_version(self):
        doc = copy.deepcopy(self.rules)
        doc["rules"][0]["source_sha256"] = "0" * 64
        self.assertIn("naming_registry.rule_source_changed", self.codes(NR.check_rules(doc, self.surfaces)))

    def test_two_active_versions_and_a_waived_code_on_a_non_waivable_rule(self):
        doc = copy.deepcopy(self.rules)
        second = copy.deepcopy(doc["rules"][0])
        second["version"] = "1.1.0"
        doc["rules"].append(second)
        fixed = next(r for r in doc["rules"] if not r["waivable"])
        fixed["outcome_contract"]["not_applicable"].append("naming.waived")
        codes = self.codes(NR.check_rules(doc, self.surfaces))
        self.assertLessEqual({"naming_registry.two_active_versions", "naming_registry.waived_not_waivable"}, codes)

    def test_mirror_mismatch(self):
        doc = copy.deepcopy(self.surfaces)
        n2 = next(s for s in doc["surfaces"] if s["surface_id"] == "N2")
        n2["referenced_by"] = []
        self.assertIn("naming_registry.mirror", self.codes(NR.check_surfaces(doc)))

    def test_implemented_surface_without_anchor(self):
        doc = copy.deepcopy(self.surfaces)
        n3 = next(s for s in doc["surfaces"] if s["surface_id"] == "N3")
        n3["doc"] = "skills/hep-computing/references/cmake-and-build.md#naming-n3"
        self.assertIn("naming_registry.anchor_missing", self.codes(NR.check_surfaces(doc)))

    def test_floor_cannot_be_lowered(self):
        doc = copy.deepcopy(self.surfaces)
        next(s for s in doc["surfaces"] if s["surface_id"] == "N10")["kinds"]["nuisance"]["level_floor"] = "C2"
        self.assertIn("naming_registry.floor_lowered", self.codes(NR.check_surfaces(doc)))

    def test_generated_blocks_are_current(self):
        self.assertEqual(NR.write_sections(self.surfaces), [])


class ProjectSettingsTests(unittest.TestCase):
    def test_naming_block_passes_preflight_and_unknown_keys_fail(self):
        from contracts.project import load_project
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "glossary.json").write_text("{}")
            cfg = {"schema_version": "1.3.0", "plugin_version": ">=0.1", "naming": {"strict": False, "glossary": "glossary.json",
                   "waivers": [{"rule_id": "naming.common.forbidden", "entity_ids": ["N1:a.py#f/tmp@3"], "reason": "r",
                                "recorded_by": "u"}]}}
            (p / "hep-research.project.json").write_text(json.dumps(cfg))
            self.assertTrue(load_project(p).report.ok, load_project(p).report.as_dict())
            cfg["naming"]["colour"] = "blue"
            (p / "hep-research.project.json").write_text(json.dumps(cfg))
            self.assertFalse(load_project(p).report.ok)
            del cfg["naming"]["colour"]
            cfg["schema_version"] = "1.2.0"
            (p / "hep-research.project.json").write_text(json.dumps(cfg))
            self.assertIn("project.naming_needs_schema", {f.code for f in load_project(p).report.findings})


if __name__ == "__main__":
    unittest.main()

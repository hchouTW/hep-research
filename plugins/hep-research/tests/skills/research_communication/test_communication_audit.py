"""check_communication.py and communication_lib.audit (plan T5): structural, traceability and manuscript checks of a
communication record with honest coverage and the plan's exit precedence. Golden scenario of Section 3; all synthetic."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.research_communication import comm_fixtures as fx

SCRIPTS = fx.PLUGIN / "skills" / "research-communication" / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from communication_lib.audit import audit_communication
    from contracts.communication_project import resolve_context
    import check_communication as cli
except ImportError:  # must fail, not error at import, before the module exists
    audit_communication = resolve_context = cli = None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")

    def audit(self, checks="traceability", record=None):
        self.assertIsNotNone(audit_communication, "communication_lib.audit does not exist")
        path = record or self.p["record"]
        ctx = resolve_context(path, self.p["root"]) if checks != "schema" else None
        rec = json.loads(Path(path).read_text(encoding="utf-8"))
        return audit_communication(rec, ctx, checks=checks)

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()


class ReportShape(Base):
    def test_golden_traceability_passes(self):
        rep = self.audit()
        self.assertEqual(rep["report_version"], "1.0.0")
        self.assertEqual(rep["tool"], "check_communication")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        self.assertEqual(rep["scope"]["checks"], ["schema", "traceability"])
        self.assertIn("manuscript", [c["check"] for c in rep["checks_not_run"]])
        self.assertEqual(rep["traceability"], "declared")
        self.assertEqual(rep["coverage"]["claims"], {"declared": 2, "mapped": 2, "unmapped": 0, "assessed": 2, "stale": 0})
        self.assertEqual(rep["coverage"]["inputs"]["resolved"], 2)
        self.assertEqual(rep["inputs"]["record_sha256"], fx.sha(self.p["record"]))
        self.assertTrue(all({"code", "severity", "location", "message", "suggested_action"} <= set(f) for f in rep["findings"]))
        self.assertIn("note", rep)
        self.assertNotIn("verified", rep["note"].lower().replace("not verified", ""))

    def test_schema_only_does_not_open_project_files_and_does_not_claim_traceability(self):
        opened, watching = [], []
        sys.addaudithook(lambda ev, args: opened.append(str(args[0])) if watching and ev == "open" and isinstance(args[0], (str, Path)) else None)
        watching.append(1)
        try:
            rep = self.audit(checks="schema")
        finally:
            watching.clear()
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["scope"]["checks"], ["schema"])
        self.assertEqual(rep["traceability"], "not-checked")
        not_run = {c["check"]: c for c in rep["checks_not_run"]}
        self.assertIn("traceability", not_run)
        self.assertIn("manuscript", not_run)
        self.assertFalse(not_run["traceability"]["required"])
        self.assertEqual([p for p in opened if "obs.json" in p or "main.md" in p], [])

    def test_empty_record_cannot_pass_vacuously(self):
        doc = fx.clone(self.p["doc"])
        doc["extension"]["claims"], doc["extension"]["occurrences"] = [], []
        fx.write(self.p["record"], doc)
        rep = self.audit()
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("audit.no_claims", self.codes(rep, "unresolved"))


class OutcomePrecedence(Base):
    def test_unresolved_source_returns_incomplete(self):
        doc = fx.clone(self.p["doc"])
        ext = doc["extension"]
        ext["scope"]["sources"] = True
        ext["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/sources.json", "claims_ref": "evidence/claims.json"}]
        ext["sources_read"] = [{"id": "lit:S01", "level": "abstract+metadata", "verification_date": "2026-10-12", "locators": ["abstract"]}]
        ext["claims"][0]["evidence"].append({"id": "ev:C1-s", "target_kind": "source", "target": "lit:S01", "locator": "abstract",
                                             "role": "qualifies", "usage": "used-in-claim", "version": "v1"})
        ext["claims"][0]["assessment"]["currency"] = "stale"
        fx.write(self.p["record"], doc)
        rep = self.audit()
        self.assertEqual((rep["status"], rep["exit_code"]), ("incomplete", 3))
        self.assertIn("resolution.ledger_missing", self.codes(rep))
        self.assertTrue(rep["schema"]["ok"], "Report.ok is true and still the run is incomplete")

    def test_missing_input_fails(self):
        self.p["syn"].unlink()
        rep = self.audit()
        self.assertEqual((rep["status"], rep["exit_code"]), ("fail", 1))
        self.assertIn("dependency.missing", self.codes(rep, "error"))

    def test_failed_upstream_is_not_complete(self):
        obs = json.loads(self.p["obs"].read_text())
        obs["status"] = ["failed", "observed"]
        fx.write(self.p["obs"], obs)
        doc = fx.clone(self.p["doc"])
        doc["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        doc["inputs"][0]["status"] = ["failed", "observed"]
        doc["status"] = ["failed", "synthetic", "unvalidated"]
        doc["extension"]["claims"][0]["status"] = ["failed", "observed"]
        fx.refresh_assessments(doc)
        fx.write(self.p["record"], doc)
        rep = self.audit()
        self.assertNotEqual(rep["status"], "pass")
        self.assertIn("dependency.failed_upstream", self.codes(rep))

    def test_legacy_record_is_limited_and_incomplete(self):
        legacy = json.loads((fx.ART / "communication.json").read_text())
        legacy["extension"]["claims"][0]["result_ref"] = "artifacts/obs.json"
        legacy["inputs"] = [{"ref": "artifacts/obs.json", "sha256": fx.sha(self.p["obs"]), "status": ["observed"]}]
        legacy["status"] = ["synthetic", "unvalidated"]
        legacy["extension"]["claims"][0]["status"] = ["synthetic", "unvalidated"]
        path = fx.write(self.p["root"] / "artifacts" / "legacy.json", legacy)
        rep = self.audit(record=path)
        self.assertEqual(rep["traceability"], "limited")
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("resolution.limited_traceability", self.codes(rep, "unresolved"))


class ManuscriptOccurrences(Base):
    def test_all_declared_occurrences_located(self):
        rep = self.audit(checks="manuscript")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        self.assertEqual(rep["scope"]["checks"], ["schema", "traceability", "manuscript"])
        occ = rep["coverage"]["occurrences"]
        self.assertEqual((occ["declared"], occ["located"], occ["checked"], occ["mismatched"], occ["unresolved"]), (4, 4, 4, 0, 0))
        self.assertEqual(rep["coverage"]["whole_manuscript"], "not-claimed")
        self.assertEqual({o["outcome"] for o in rep["occurrences"]}, {"located"})

    def test_correct_manifest_with_wrong_manuscript_sentence_is_flagged(self):
        text = self.p["paper"].read_text().replace("R = 1.02 +/- 0.05 in the synthetic", "R = 1.08 +/- 0.05 in the synthetic")
        self.p["paper"].write_text(text)
        rep = self.audit(checks="manuscript")
        self.assertEqual((rep["status"], rep["exit_code"]), ("fail", 1))
        self.assertIn("occurrence.passage_mismatch", self.codes(rep, "error"))
        bad = [o for o in rep["occurrences"] if o["outcome"] == "mismatch"]
        self.assertEqual([o["id"] for o in bad], ["occ:abstract"])
        self.assertIn("1.08", bad[0]["current"])
        self.assertEqual(rep["coverage"]["occurrences"]["mismatched"], 1)
        self.assertEqual(self.audit(checks="traceability")["status"], "pass", "the manifest alone is still consistent")

    def test_ambiguous_locator_is_unresolved(self):
        text = self.p["paper"].read_text().replace("## Figures", "## Results\n\nDuplicate heading.\n\n## Figures")
        self.p["paper"].write_text(text)
        rep = self.audit(checks="manuscript")
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("occurrence.locator_ambiguous", self.codes(rep, "unresolved"))

    def test_locator_not_found_and_document_missing_are_unresolved(self):
        doc = fx.clone(self.p["doc"])
        doc["extension"]["occurrences"][0]["locator"] = "section:Nowhere"
        fx.write(self.p["record"], doc)
        rep = self.audit(checks="manuscript")
        self.assertIn("occurrence.locator_not_found", self.codes(rep, "unresolved"))
        self.p["paper"].unlink()
        rep = self.audit(checks="manuscript")
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("resolution.document_missing", self.codes(rep, "unresolved"))
        self.assertEqual(rep["coverage"]["occurrences"]["unresolved"], 4)

    def test_latex_document_literal_text(self):
        tex = ("\\documentclass{article}\\begin{document}\n\\begin{abstract}\n" + fx.ABSTRACT + "\n\\end{abstract}\n"
               "\\section{Results}\\label{sec:results}\n" + fx.BODY + " % comment\n" + fx.ILLUSTRATION + "\n"
               "\\begin{figure}\\caption{" + fx.CAPTION + "}\\label{fig:ratio}\\end{figure}\n\\end{document}\n")
        fx.write(self.p["root"] / "paper" / "main.tex", tex)
        doc = fx.clone(self.p["doc"])
        doc["extension"]["documents"][0].update(path="paper/main.tex", format="latex")
        locs = {"occ:abstract": "env:abstract", "occ:body": "label:sec:results", "occ:caption": "label:fig:ratio", "occ:illustration": "section:Results"}
        for o in doc["extension"]["occurrences"]:
            o["locator"] = locs[o["id"]]
        fx.write(self.p["record"], doc)
        rep = self.audit(checks="manuscript")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        self.assertEqual(rep["coverage"]["occurrences"]["located"], 4)

    def test_claim_without_occurrence_when_coverage_requested(self):
        doc = fx.clone(self.p["doc"])
        doc["extension"]["occurrences"] = [o for o in doc["extension"]["occurrences"] if o["claim_id"] != "claim:C2"]
        fx.write(self.p["record"], doc)
        rep = self.audit(checks="manuscript")
        self.assertIn("occurrence.claim_without_occurrence", self.codes(rep, "unresolved"))

    def test_value_not_in_passage_is_a_review_candidate(self):
        doc = fx.clone(self.p["doc"])
        doc["extension"]["occurrences"][1]["value"] = {"value": "1.020", "unit": "1", "rounding": "decimals:3"}
        fx.write(self.p["record"], doc)
        rep = self.audit(checks="manuscript")
        self.assertIn("occurrence.value_not_in_passage", self.codes(rep, "warning"))
        self.assertEqual(rep["status"], "pass", "a warning alone does not fail the mechanical check")


class Cli(Base):
    def test_json_default_markdown_and_out(self):
        code, out, err = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--checks", "manuscript")
        self.assertEqual(code, 0, out + err)
        rep = json.loads(out)
        self.assertEqual(rep["status"], "pass")
        report = self.tmp / "report.md"
        code, out, err = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--format", "markdown", "--out", report)
        self.assertEqual(code, 0)
        self.assertTrue(report.read_text().startswith("# check_communication"))
        self.assertIn("pass", report.read_text())
        self.assertEqual(out.strip(), "", "with --out the report goes to the file")
        self.assertIn(str(report), err)

    def test_invalid_invocation_and_unreadable_input(self):
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(self.run_cli(self.tmp / "missing.json", "--project-root", self.p["root"])[0], 2)
        code, out, _ = self.run_cli(self.p["record"], "--project-root", self.tmp / "nope")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["status"], "input-error")

    def test_output_aliasing_an_input_is_refused(self):
        for target in (self.p["record"], self.p["paper"], self.p["obs"]):
            code, _, err = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--out", target)
            self.assertEqual(code, 2, target)
            self.assertIn("alias", err.lower() + " alias" if "overwrite" in err else err)
        before = self.p["record"].read_bytes()
        link = self.tmp / "alias.json"
        link.symlink_to(self.p["record"])
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--out", link)[0], 2)
        self.assertEqual(self.p["record"].read_bytes(), before)

    def test_read_only(self):
        before = {p: p.read_bytes() for p in self.p["root"].rglob("*") if p.is_file()}
        self.run_cli(self.p["record"], "--project-root", self.p["root"], "--checks", "manuscript")
        self.assertEqual({p: p.read_bytes() for p in self.p["root"].rglob("*") if p.is_file()}, before)

    def test_help_and_exit_codes_through_subprocess(self):
        run = subprocess.run([sys.executable, str(SCRIPTS / "check_communication.py"), "--help"], capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0)
        self.assertIn("--checks", run.stdout)
        self.p["syn"].unlink()
        run = subprocess.run([sys.executable, str(SCRIPTS / "check_communication.py"), str(self.p["record"]), "--project-root", str(self.p["root"])],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["status"], "fail")


if __name__ == "__main__":
    unittest.main()

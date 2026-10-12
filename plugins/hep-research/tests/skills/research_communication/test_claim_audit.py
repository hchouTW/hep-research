"""audit_claims.py and communication_lib.claims (plan T5): recorded assessments, advisory wording scans, source read
coverage, rounding and unit consistency, the claim matrix and draft-ready facts. All synthetic."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.skills.research_communication import comm_fixtures as fx

SCRIPTS = fx.PLUGIN / "skills" / "research-communication" / "scripts"
sys.path.insert(0, str(SCRIPTS))
POLICY = SCRIPTS.parent / "assets" / "reporting-policies.json"

try:
    from communication_lib.claims import audit_claims
    from contracts.communication_project import resolve_context
    import audit_claims as cli
except ImportError:
    audit_claims = resolve_context = cli = None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.p = fx.build_project(self.tmp / "project")
        self.doc = fx.clone(self.p["doc"])

    def audit(self, policy=None):
        self.assertIsNotNone(audit_claims, "communication_lib.claims does not exist")
        fx.refresh_assessments(self.doc)
        fx.write(self.p["record"], self.doc)
        ctx = resolve_context(self.p["record"], self.p["root"])
        pol = policy if policy is not None else json.loads(POLICY.read_text(encoding="utf-8"))
        return audit_claims(json.loads(self.p["record"].read_text()), ctx, pol)

    @staticmethod
    def codes(rep, severity=None):
        return {f["code"] for f in rep["findings"] if severity is None or f["severity"] == severity}

    def c1(self):
        return self.doc["extension"]["claims"][0]


class MatrixAndFacts(Base):
    def test_golden_matrix_and_facts(self):
        rep = self.audit()
        self.assertEqual(rep["tool"], "audit_claims")
        self.assertEqual((rep["status"], rep["exit_code"]), ("pass", 0), rep["findings"])
        m = {row["id"]: row for row in rep["claim_matrix"]}
        self.assertEqual(m["claim:C1"]["verdict"], "supported")
        self.assertEqual(m["claim:C1"]["currency"], "current")
        self.assertEqual(m["claim:C1"]["status"], ["observed"])
        self.assertEqual(m["claim:C1"]["evidence"][0]["identity"], "sha256:" + fx.sha(self.p["obs"]))
        self.assertEqual([o["id"] for o in m["claim:C1"]["occurrences"]], ["occ:abstract", "occ:body", "occ:caption"])
        facts = {f["claim_id"]: f for f in rep["draft_facts"]}
        self.assertEqual(facts["claim:C1"]["value"], "1.02")
        self.assertEqual(facts["claim:C1"]["unit"], "1")
        self.assertEqual(facts["claim:C1"]["uncertainty"], {"stat": "0.05"})
        self.assertEqual(facts["claim:C1"]["status"], ["observed"])
        self.assertEqual(facts["claim:C1"]["source"]["locator"], "extension.results.ratio")
        self.assertEqual(facts["claim:C2"]["status"], ["synthetic", "unvalidated"])
        self.assertIn("assessment recorded", rep["note"])
        self.assertNotIn("independently verified", rep["note"])

    def test_unassessed_claim_is_unresolved_and_listed(self):
        del self.c1()["assessment"]
        rep = self.audit()
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("communication.assessment_missing", self.codes(rep, "unresolved"))
        self.assertEqual({r["id"]: r["verdict"] for r in rep["claim_matrix"]}["claim:C1"], None)


class RecordedAssessments(Base):
    def test_wrong_attribution_despite_valid_identifier(self):
        a = self.c1()["assessment"]
        a.update(verdict="unsupported", rationale="the source gives 1.12 at the cited locator; the DOI resolves but the number differs",
                 evidence_ids=["ev:C1-a"])
        rep = self.audit()
        self.assertEqual((rep["status"], rep["exit_code"]), ("fail", 1))
        f = next(x for x in rep["findings"] if x["code"] == "claim.unsupported")
        self.assertIn("1.12", f["message"])
        self.assertIn("locator", f["suggested_action"].lower())

    def test_partial_and_unresolved_verdicts(self):
        self.c1()["assessment"]["verdict"] = "partially-supported"
        rep = self.audit()
        self.assertIn("claim.partially_supported", self.codes(rep, "warning"))
        self.assertEqual(rep["status"], "pass")
        self.c1()["assessment"].update(verdict="unresolved", evidence_ids=[])
        rep = self.audit()
        self.assertIn("claim.assessment_unresolved", self.codes(rep, "unresolved"))
        self.assertEqual(rep["status"], "incomplete")

    def test_stronger_wording_with_unchanged_source_is_stale(self):
        self.c1()["text"] = "The ratio R establishes a deviation of 1.02 +/- 0.05 (synthetic fixture)."
        fx.write(self.p["record"], self.doc)  # the assessment keeps its old digest: do not refresh
        ctx = resolve_context(self.p["record"], self.p["root"])
        rep = audit_claims(json.loads(self.p["record"].read_text()), ctx, json.loads(POLICY.read_text()))
        self.assertEqual(rep["status"], "fail", "currency 'current' on a stale assessment is a confirmed inconsistency")
        self.assertIn("communication.assessment_stale", self.codes(rep))
        self.assertIn("communication.currency_mismatch", self.codes(rep, "error"))

    def test_verified_workflow_state_needs_a_current_assessment(self):
        self.c1()["workflow_state"] = "verified"
        del self.c1()["assessment"]
        rep = self.audit()
        self.assertIn("workflow.verified_without_assessment", self.codes(rep, "error"))


class SourceReadCoverage(Base):
    def with_source(self, level, locators, edge_locator):
        ext = self.doc["extension"]
        ext["scope"]["sources"] = True
        src = {"id": "lit:S01", "title": "Synthetic fixture paper", "authors": "Fixture et al.", "year": 2026, "tier": 2,
               "verification_level": level, "verification_date": "2026-10-12", "supersedes": [], "superseded_by": [],
               "identifiers": {"doi": "10.0000/synthetic-fixture"}, "verification_limitations": "fixture"}
        clm = {"id": "lit:C01", "claim": "fixture", "claim_types": ["published_result"], "source_ids": ["lit:S01"], "location": "abstract",
               "scope": {"text": "fixture"}, "verification_strength": level, "numeric_quotation_allowed": True, "last_reviewed": "2026-10-12"}
        sp = fx.write(self.p["root"] / "evidence" / "sources.json", [src])
        cp = fx.write(self.p["root"] / "evidence" / "claims.json", [clm])
        ext["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/sources.json", "claims_ref": "evidence/claims.json",
                                    "sources_sha256": fx.sha(sp), "claims_sha256": fx.sha(cp)}]
        ext["sources_read"] = [{"id": "lit:S01", "level": level, "verification_date": "2026-10-12", "locators": locators}]
        self.c1()["evidence"].append({"id": "ev:C1-s", "target_kind": "source", "target": "lit:S01", "locator": edge_locator,
                                      "role": "qualifies", "usage": "used-in-claim", "version": "2026-10-12"})
        self.c1()["assessment"]["evidence_ids"].append("ev:C1-s")

    def test_abstract_value_citable_but_unseen_table_is_not(self):
        self.with_source("abstract+metadata", ["abstract"], "abstract, sentence 2")
        rep = self.audit()
        self.assertEqual(rep["status"], "pass", rep["findings"])
        self.c1()["evidence"][-1]["locator"] = "Table 3"
        rep = self.audit()
        self.assertEqual(rep["status"], "incomplete")
        f = next(x for x in rep["findings"] if x["code"] == "source.locator_not_read")
        self.assertIn("Table 3", f["message"])
        self.assertIn("abstract", f["message"])

    def test_full_text_read_covers_any_locator(self):
        self.with_source("full-text", [], "Table 3")
        self.assertNotIn("source.locator_not_read", self.codes(self.audit()))

    def test_metadata_only_read_supports_no_locator(self):
        self.with_source("metadata-only", [], "abstract")
        self.assertIn("source.locator_not_read", self.codes(self.audit(), "unresolved"))


class WordingScans(Base):
    def test_status_promotion_wording_is_advisory(self):
        c2 = self.doc["extension"]["claims"][1]
        c2["text"] = "We measure R = 0.98 in data (synthetic fixture)."
        rep = self.audit()
        self.assertIn("wording.status_promotion", self.codes(rep, "warning"))
        self.assertEqual(rep["status"], "pass")

    def test_quoted_and_negated_wording_not_flagged(self):
        c2 = self.doc["extension"]["claims"][1]
        c2["text"] = 'Ref. [3] reports "observation of a deviation"; we find no evidence for it (synthetic fixture).'
        rep = self.audit()
        self.assertNotIn("wording.status_promotion", self.codes(rep))
        self.assertNotIn("wording.significance_unsupported", self.codes(rep))

    def test_local_significance_promoted_to_discovery_requests_statistics(self):
        self.c1()["text"] = "We report the observation of a deviation at 3.4 sigma local (synthetic fixture)."
        self.c1()["claim_type"] = "search"
        self.doc["extension"]["reporting_context"] = {"result_type": "search", "method": {"scan": True},
                                                      "fields": {"local_significance": {"state": "provided", "value": "3.4"},
                                                                 "global_significance": {"state": "missing"},
                                                                 "trials_method": {"state": "missing"},
                                                                 "expected_significance": {"state": "provided", "value": "2.9"},
                                                                 "observed_vs_expected": {"state": "provided", "value": "stated"},
                                                                 "scope": {"state": "provided", "value": "fixture"}}}
        rep = self.audit()
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("wording.significance_unsupported", self.codes(rep, "warning"))
        self.assertIn("reporting.field_missing", self.codes(rep, "unresolved"))
        self.assertTrue(any(h["to_skill"] == "hep-statistics" and "global" in h["request"] for h in rep["handoffs"]), rep["handoffs"])

    def test_generalization_beyond_scope_is_advisory(self):
        self.c1()["text"] = "The ratio R is 1.02 +/- 0.05 for all energies (synthetic fixture)."
        rep = self.audit()
        self.assertIn("wording.generalization", self.codes(rep, "warning"))


class NumbersAndUnits(Base):
    def test_rounded_display_within_declared_rounding_is_not_a_contradiction(self):
        self.p["obs"].write_text(json.dumps(fx.observed_result("1.0237", "0.0512")))
        self.doc["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        rep = self.audit()
        self.assertNotIn("occurrence.value_mismatch", self.codes(rep))
        self.assertEqual(rep["status"], "pass", rep["findings"])

    def test_display_outside_declared_rounding_is_flagged(self):
        self.p["obs"].write_text(json.dumps(fx.observed_result("1.0371", "0.05")))
        self.doc["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        rep = self.audit()
        self.assertIn("occurrence.value_mismatch", self.codes(rep, "error"))
        self.assertEqual(rep["status"], "fail")

    def test_missing_rounding_is_a_review_candidate_not_a_correction(self):
        self.p["obs"].write_text(json.dumps(fx.observed_result("1.0237", "0.05")))
        self.doc["inputs"][0]["sha256"] = fx.sha(self.p["obs"])
        for o in self.doc["extension"]["occurrences"]:
            if "value" in o:
                del o["value"]["rounding"]
        rep = self.audit()
        self.assertIn("occurrence.value_unrounded_comparison", self.codes(rep, "warning"))
        self.assertNotIn("occurrence.value_mismatch", self.codes(rep))

    def test_unspecified_unit_conversion_is_unresolved(self):
        self.doc["extension"]["occurrences"][0]["value"] = {"value": "102", "unit": "%", "rounding": "decimals:0"}
        rep = self.audit()
        self.assertIn("occurrence.unit_conversion_unspecified", self.codes(rep, "unresolved"))
        self.assertNotIn("occurrence.value_mismatch", self.codes(rep))


class Cli(Base):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_json_markdown_and_default_policy(self):
        fx.write(self.p["record"], self.doc)
        code, out, err = self.run_cli(self.p["record"], "--project-root", self.p["root"])
        self.assertEqual(code, 0, out + err)
        rep = json.loads(out)
        self.assertEqual(rep["scope"]["policy"]["path"], str(POLICY))
        code, out, _ = self.run_cli(self.p["record"], "--project-root", self.p["root"], "--format", "markdown")
        self.assertTrue(out.startswith("# audit_claims"))
        self.assertIn("claim:C1", out)

    def test_bad_policy_and_alias(self):
        fx.write(self.p["record"], self.doc)
        bad = fx.write(self.tmp / "policy.json", "{not json")
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--policy", bad)[0], 2)
        self.assertEqual(self.run_cli(self.p["record"], "--project-root", self.p["root"], "--out", self.p["record"])[0], 2)


if __name__ == "__main__":
    unittest.main()

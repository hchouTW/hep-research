"""Communication contracts (research-communication plan T1): typed legacy fields, the capability-gated traceability
format (communication:traceability-v1), claim-scoped status propagation, and the layering of pure validation.

All records are SYNTHETIC structural fixtures; the numbers are placeholders, not physics."""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION, KNOWN_CAPABILITIES  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
SYN = "SYNTHETIC structural fixture; values are placeholders, not physics"
CAP = "communication:traceability-v1"
SHA_A, SHA_B = "a" * 64, "b" * 64


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def codes(rep, severity=None):
    return {f.code for f in rep.findings if severity is None or f.severity == severity}


def legacy():
    return load(ART / "valid" / "communication.json")


def envelope(ext, inputs, status=("synthetic", "unvalidated"), caps=(CAP,)):
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": "fixture-synthetic-communication-rich",
            "artifact_type": "communication", "objective": SYN, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": "0.6.12", "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "research-communication", "created": "2026-10-12", "evidence_ids": []},
            "required_capabilities": list(caps), "inputs": copy.deepcopy(list(inputs)), "outputs": [], "status": list(status),
            "unresolved_inputs": [], "extension": ext}


OBS = {"ref": "artifacts/obs.json", "artifact_type": "statistical-result", "artifact_id": "fx-obs", "sha256": SHA_A,
       "status": ["observed"]}
SYNTH = {"ref": "artifacts/syn.json", "artifact_type": "prediction", "artifact_id": "fx-syn", "sha256": SHA_B,
         "status": ["synthetic", "unvalidated"]}


def edge(eid, target, role="supports", usage="used-in-claim", kind="artifact", **extra):
    e = {"id": eid, "target_kind": kind, "target": target, "locator": "extension.results.ratio", "role": role, "usage": usage}
    e.update(extra)
    return e


def claim(cid, text, status, edges, ctype="measurement", **extra):
    c = {"id": cid, "text": text, "claim_type": ctype, "scope": {"text": "synthetic fixture result"},
         "status": list(status), "evidence": list(edges), "unresolved_inputs": []}
    c.update(extra)
    return c


def rich():
    """Observed claim C1 on input A, synthetic illustration C2 on input B, one mapped occurrence of C1."""
    ext = {"traceability_version": "1.0.0", "scope": {"occurrences": True, "sources": False},
           "documents": [{"id": "doc:paper", "path": "paper/main.md", "format": "markdown",
                          "audience": "journal readers", "purpose": "main text"}],
           "claims": [claim("claim:C1", "The ratio is 1.02 +/- 0.05 (synthetic fixture).", ["observed"],
                            [edge("ev:C1-a", "artifacts/obs.json")]),
                      claim("claim:C2", "A synthetic illustration gives 0.98 (synthetic fixture).", ["synthetic", "unvalidated"],
                            [edge("ev:C2-b", "artifacts/syn.json")], ctype="illustration")],
           "occurrences": [{"id": "occ:1", "claim_id": "claim:C1", "document_id": "doc:paper", "locator": "section:abstract",
                            "passage": "The ratio is 1.02 +/- 0.05.", "state": "mapped"}],
           "sources_read": [], "evidence_ledgers": [], "limitations": ["synthetic fixture"]}
    return envelope(ext, [OBS, SYNTH])


class LegacyFormatTests(unittest.TestCase):
    def test_legacy_wrong_field_types_rejected(self):
        d = legacy()
        d["extension"]["claims"] = [{"text": 42, "result_ref": None, "status": {"a": 1}}]
        rep = validate_artifact(d)
        self.assertFalse(rep.ok)
        paths = {f.path for f in rep.errors if f.code in ("schema.type", "schema.any_of")}
        self.assertTrue({"$.extension.claims[0].text", "$.extension.claims[0].result_ref", "$.extension.claims[0].status"} <= paths, paths)

    def test_valid_legacy_forms_preserved(self):
        d = legacy()
        self.assertEqual(d["extension"]["claims"][0]["status"], "synthetic", "the documented scalar form")
        self.assertTrue(validate_artifact(d).ok)
        d["extension"]["claims"][0]["status"] = ["synthetic"]
        self.assertTrue(validate_artifact(d).ok)
        d["extension"]["claims"][0]["status"] = "not-a-status"
        rep = validate_artifact(d)
        self.assertFalse(rep.ok)
        self.assertTrue({"schema.any_of", "vocab.unknown_term"} & codes(rep, "error"))

    def test_legacy_status_rule_unchanged(self):
        d = legacy()
        d["inputs"] = [{"ref": "r.json", "artifact_type": "statistical-result", "status": ["failed", "synthetic"]}]
        d["status"] = ["failed", "synthetic", "unvalidated"]
        d["extension"]["claims"][0]["status"] = ["synthetic"]
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))


class CapabilityDispatchTests(unittest.TestCase):
    def test_capability_dispatch_and_old_reader_rejection(self):
        d = rich()
        rep = validate_artifact(d)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertIn(CAP, KNOWN_CAPABILITIES)
        # a reader from before this capability (the 2.2.0 reader's set) refuses the record instead of reading it loosely
        import contracts
        old = frozenset({"core:plugin-release-identity", "core:data-exposure", "stats:result-semantics"})
        saved = contracts.KNOWN_CAPABILITIES
        try:
            contracts.KNOWN_CAPABILITIES = old
            self.assertIn("contract.unknown_capability", codes(validate_artifact(d), "error"))
        finally:
            contracts.KNOWN_CAPABILITIES = saved

    def test_capability_marker_mismatch(self):
        d = rich()
        d["required_capabilities"] = []  # rich fields without the capability
        self.assertIn("communication.capability_missing", codes(validate_artifact(d), "error"))
        e = rich()
        del e["extension"]["traceability_version"]  # capability without the marker
        self.assertIn("communication.traceability_version_missing", codes(validate_artifact(e), "error"))

    def test_unknown_rich_format_version(self):
        d = rich()
        d["extension"]["traceability_version"] = "2.0.0"
        self.assertIn("communication.traceability_version_unknown", codes(validate_artifact(d), "error"))

    def test_rich_schema_rejects_wrong_types(self):
        d = rich()
        d["extension"]["claims"][0]["text"] = 42
        d["extension"]["claims"][0]["status"] = "observed"  # the rich form is always an array
        rep = validate_artifact(d)
        self.assertFalse(rep.ok)
        self.assertTrue({"$.extension.claims[0].text", "$.extension.claims[0].status"} <= {f.path for f in rep.errors})


class RelationshipTests(unittest.TestCase):
    def test_duplicate_claim_ids(self):
        d = rich()
        d["extension"]["claims"][1]["id"] = "claim:C1"
        self.assertIn("communication.duplicate_id", codes(validate_artifact(d), "error"))

    def test_unknown_document_and_claim_ids_in_occurrences(self):
        d = rich()
        d["extension"]["occurrences"][0]["document_id"] = "doc:nowhere"
        self.assertIn("communication.unknown_document", codes(validate_artifact(d), "error"))
        d = rich()
        d["extension"]["occurrences"][0]["claim_id"] = "claim:C9"
        self.assertIn("communication.unknown_claim", codes(validate_artifact(d), "error"))

    def test_malformed_evidence_edges(self):
        d = rich()
        d["extension"]["claims"][0]["evidence"] = [{"id": "ev:x", "target_kind": "artifact", "target": "artifacts/nope.json",
                                                    "locator": "x", "role": "supports", "usage": "used-in-claim"}]
        self.assertIn("communication.unknown_input", codes(validate_artifact(d), "error"))
        d = rich()
        d["extension"]["claims"][0]["evidence"][0]["role"] = "proves"
        self.assertIn("schema.enum", codes(validate_artifact(d), "error"))
        d = rich()
        del d["extension"]["claims"][0]["evidence"][0]["locator"]
        self.assertIn("schema.required", codes(validate_artifact(d), "error"))

    def test_ambiguous_and_undeclared_source_namespaces(self):
        d = rich()
        d["extension"]["scope"]["sources"] = True
        d["extension"]["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/a/sources.json", "claims_ref": "evidence/a/claims.json"},
                                              {"namespace": "lit", "sources_ref": "evidence/b/sources.json", "claims_ref": "evidence/b/claims.json"}]
        d["extension"]["claims"][0]["evidence"].append(edge("ev:C1-s", "lit:S01", kind="source", locator="abstract, sentence 2"))
        d["extension"]["sources_read"] = [{"id": "lit:S01", "level": "abstract+metadata", "verification_date": "2026-10-12"}]
        self.assertIn("communication.ambiguous_namespace", codes(validate_artifact(d), "error"))
        d["extension"]["evidence_ledgers"] = []
        self.assertIn("communication.source_namespace_undeclared", codes(validate_artifact(d), "error"))

    def test_source_edge_without_read_event_is_unresolved(self):
        d = rich()
        d["extension"]["scope"]["sources"] = True
        d["extension"]["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/sources.json", "claims_ref": "evidence/claims.json"}]
        d["extension"]["claims"][0]["evidence"].append(edge("ev:C1-s", "lit:S01", kind="source", locator="Table 2"))
        rep = validate_artifact(d)
        self.assertTrue(rep.ok)
        self.assertIn("communication.source_not_read", codes(rep, "unresolved"))

    def test_supported_claim_without_supporting_evidence(self):
        d = rich()
        c = d["extension"]["claims"][0]
        c["assessment"] = {"verdict": "supported", "rationale": "x", "evidence_ids": [], "assessor": {"identity": "fixture", "role": "author"},
                           "date": "2026-10-12", "currency": "current"}
        self.assertIn("communication.supported_without_evidence", codes(validate_artifact(d), "error"))
        c["assessment"]["evidence_ids"] = ["ev:C1-zzz"]
        self.assertIn("communication.unknown_evidence_id", codes(validate_artifact(d), "error"))
        c["evidence"][0]["role"] = "contradicts"
        c["assessment"]["evidence_ids"] = ["ev:C1-a"]
        self.assertIn("communication.supported_without_evidence", codes(validate_artifact(d), "error"))

    def test_claim_without_mapping_or_request_is_unresolved(self):
        d = rich()
        d["extension"]["claims"][0]["evidence"] = []
        d["extension"]["claims"][0]["status"] = ["synthetic", "unvalidated"]
        rep = validate_artifact(d)
        self.assertIn("communication.claim_unmapped", codes(rep, "unresolved"))
        d["extension"]["claims"][0]["unresolved_inputs"] = ["the ratio result artifact from hep-statistics"]
        self.assertNotIn("communication.claim_unmapped", codes(validate_artifact(d)))


class StatusPropagationTests(unittest.TestCase):
    def test_mixed_claim_statuses(self):
        d = rich()
        rep = validate_artifact(d)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertEqual(d["status"], ["synthetic", "unvalidated"])  # the envelope keeps the sticky caveats only
        bad = rich()
        bad["status"] = ["observed", "synthetic", "unvalidated"]
        self.assertIn("status.conflict", codes(validate_artifact(bad), "error"))
        bad = rich()
        bad["extension"]["claims"][0]["status"] = ["observed", "synthetic"]  # C1 does not inherit B's unrelated label
        self.assertIn("communication.claim_status_conflict", codes(validate_artifact(bad), "error"))

    def test_observed_needs_an_observed_source(self):
        d = rich()
        d["extension"]["claims"][1]["status"] = ["observed"]  # C2 uses only the synthetic input
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))

    def test_comparison_preserves_both_sources(self):
        d = rich()
        c3 = claim("claim:C3", "Data and the synthetic prediction agree (synthetic fixture).", ["synthetic", "unvalidated"],
                   [edge("ev:C3-a", "artifacts/obs.json"), edge("ev:C3-b", "artifacts/syn.json", role="qualifies")], ctype="comparison")
        d["extension"]["claims"].append(c3)
        self.assertTrue(validate_artifact(d).ok, [f.as_dict() for f in validate_artifact(d).errors])
        c3["status"] = ["observed", "synthetic", "unvalidated"]
        self.assertIn("communication.claim_status_conflict", codes(validate_artifact(d), "error"))
        c3["status"] = ["observed"]
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))

    def test_missing_mapping_cannot_bypass_statuses(self):
        d = rich()
        c = d["extension"]["claims"][0]
        c["evidence"] = []  # no mapping: the legacy conservative rule applies (every sticky caveat of the envelope)
        c["unresolved_inputs"] = ["mapping pending"]
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))
        c["status"] = ["synthetic", "unvalidated"]
        self.assertTrue(validate_artifact(d).ok)

    def test_contradictory_evidence_used_in_claim_propagates_status(self):
        d = rich()
        neg = claim("claim:C4", "The synthetic prediction is disfavoured (synthetic fixture).", ["observed"],
                    [edge("ev:C4-a", "artifacts/obs.json"), edge("ev:C4-b", "artifacts/syn.json", role="contradicts", usage="used-in-claim")],
                    ctype="interpretation")
        d["extension"]["claims"].append(neg)
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))
        neg["status"] = ["synthetic", "unvalidated"]
        self.assertTrue(validate_artifact(d).ok)

    def test_context_only_needs_a_reason_and_missing_usage_is_unresolved(self):
        d = rich()
        e = edge("ev:C1-ctx", "artifacts/syn.json", role="background", usage="context-only")
        d["extension"]["claims"][0]["evidence"].append(e)
        self.assertIn("communication.context_only_without_reason", codes(validate_artifact(d), "error"))
        e["usage_reason"] = "the illustration is cited for orientation only; no value enters the claim"
        self.assertTrue(validate_artifact(d).ok)
        del e["usage"]
        del e["usage_reason"]
        rep = validate_artifact(d)
        self.assertIn("communication.usage_missing", codes(rep, "unresolved"))
        self.assertIn("communication.status_upgraded", codes(rep, "error"), "an unmapped usage is treated as used")

    def test_failed_input_used_in_claim(self):
        d = rich()
        d["inputs"][0]["status"] = ["failed", "observed"]
        d["status"] = ["failed", "synthetic", "unvalidated"]
        self.assertIn("communication.status_upgraded", codes(validate_artifact(d), "error"))
        d["extension"]["claims"][0]["status"] = ["failed", "observed"]
        self.assertTrue(validate_artifact(d).ok)


class AssessmentCurrencyTests(unittest.TestCase):
    def assessed(self):
        from contracts.communication import claim_digest, evidence_fingerprint
        d = rich()
        c = d["extension"]["claims"][0]
        c["assessment"] = {"verdict": "supported", "rationale": "the value and uncertainty are read from the result artifact",
                           "evidence_ids": ["ev:C1-a"], "assessor": {"identity": "fixture", "role": "author"}, "date": "2026-10-12",
                           "claim_digest": claim_digest(c), "evidence_fingerprints": {"ev:C1-a": evidence_fingerprint(c["evidence"][0], d)},
                           "currency": "current"}
        return d

    def test_current_assessment_is_clean(self):
        rep = validate_artifact(self.assessed())
        self.assertTrue(rep.ok)
        self.assertNotIn("communication.assessment_stale", codes(rep))

    def test_assessment_stale_on_wording_change(self):
        d = self.assessed()
        d["extension"]["claims"][0]["text"] = "The ratio establishes a deviation of 1.02 +/- 0.05 (synthetic fixture)."
        rep = validate_artifact(d)
        self.assertIn("communication.assessment_stale", codes(rep, "unresolved"))
        self.assertIn("communication.currency_mismatch", codes(rep, "error"))
        d["extension"]["claims"][0]["assessment"]["currency"] = "stale"
        rep = validate_artifact(d)
        self.assertTrue(rep.ok)
        self.assertIn("communication.assessment_stale", codes(rep, "unresolved"))

    def test_assessment_stale_on_source_identity_change(self):
        d = self.assessed()
        d["inputs"][0]["sha256"] = "c" * 64
        d["extension"]["claims"][0]["assessment"]["currency"] = "stale"
        self.assertIn("communication.assessment_stale", codes(validate_artifact(d), "unresolved"))

    def test_unassessed_claim_is_unresolved_not_invalid(self):
        rep = validate_artifact(rich())
        self.assertTrue(rep.ok)
        self.assertIn("communication.assessment_missing", codes(rep, "unresolved"))

    def test_digest_is_canonical(self):
        from contracts.communication import claim_digest
        a = {"text": "x", "scope": {"text": "s", "assumptions": ["a"]}, "status": ["observed"]}
        b = {"scope": {"assumptions": ["a"], "text": "s"}, "text": "x", "status": ["synthetic"]}
        self.assertEqual(claim_digest(a), claim_digest(b), "key order and fields outside text/scope do not change it")
        self.assertEqual(len(claim_digest(a)), 64)
        self.assertNotEqual(claim_digest(a), claim_digest({"text": "y", "scope": {"text": "s"}}))


class LayeringTests(unittest.TestCase):
    def test_pure_validation_never_opens_project_files(self):
        d = rich()
        d["inputs"][0]["ref"] = "/definitely/not/here/obs.json"
        d["extension"]["claims"][0]["evidence"][0]["target"] = "/definitely/not/here/obs.json"
        opened = []
        watching = []
        sys.addaudithook(lambda ev, args: opened.append(str(args[0])) if watching and ev == "open" else None)
        watching.append(1)
        try:
            rep = validate_artifact(d)
        finally:
            watching.clear()
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertEqual([p for p in opened if "not/here" in p], [])

    def test_pure_module_imports_no_project_layer(self):
        import ast
        src = (ROOT / "contracts" / "communication.py").read_text(encoding="utf-8")
        mods = {n.module.split(".")[0] if isinstance(n, ast.ImportFrom) and n.module else a.name.split(".")[0]
                for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.Import, ast.ImportFrom))
                for a in (n.names if isinstance(n, ast.Import) else [None])}
        names = {m for m in mods if m}
        self.assertNotIn("skills", names)
        full = [n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.module]
        for forbidden in ("contracts.dependencies", "contracts.communication_project", "contracts.project"):
            self.assertNotIn(forbidden, full)
        vsrc = (ROOT / "contracts" / "validate.py").read_text(encoding="utf-8")
        self.assertNotIn("contracts.dependencies", vsrc)
        self.assertNotIn("communication_project", vsrc)

    def test_pure_module_imports_standalone(self):
        for name in ("contracts.communication", "contracts.validate"):
            sys.modules.pop(name, None)
        mod = importlib.import_module("contracts.communication")
        self.assertTrue(callable(mod.validate_extension))


if __name__ == "__main__":
    unittest.main()


class ReviewMinors(unittest.TestCase):
    def test_legacy_sources_read_id_need_not_be_namespaced(self):
        d = legacy()
        d["extension"]["sources_read"][0]["id"] = "S1"
        self.assertTrue(validate_artifact(d).ok, [f.as_dict() for f in validate_artifact(d).errors])
        d["extension"]["sources_read"][0]["id"] = ""
        self.assertFalse(validate_artifact(d).ok)

    def test_all_context_only_edges_count_as_no_used_evidence(self):
        d = rich()
        c = d["extension"]["claims"][0]
        c["evidence"] = [edge("ev:C1-ctx", "artifacts/syn.json", role="background", usage="context-only", usage_reason="orientation only")]
        rep = validate_artifact(d)
        self.assertIn("communication.status_upgraded", codes(rep, "error"), "observed with no used evidence")
        c["status"] = ["synthetic", "unvalidated"]
        rep = validate_artifact(d)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertIn("communication.claim_unmapped", codes(rep, "unresolved"))

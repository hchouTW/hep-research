"""audit_claims: recorded assessments, source read coverage, advisory wording scans, number and unit consistency,
reporting completeness, a traceable claim matrix and draft-ready facts (plan T5).

Deterministic code checks the record's consistency, never scientific truth: a support verdict is the assessor's
recorded judgment. Wording scans are advisory (warnings) and skip quoted language, negations and statements about
another paper's claim. Exact source values stay separate from display strings; a comparison uses the occurrence's
declared rounding and never invents a tolerance or a unit conversion. Needed calculations are routed to the producing
skill as handoffs with the specific unresolved input.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path

from communication_lib import report as R
from communication_lib.reporting import check_reporting
from contracts.communication import evidence_fingerprint, format_of
from contracts.evidence import STRENGTH

NOTE = ("assessment recorded by its assessor and checked for consistency with the record; whether the evidence supports "
        "the wording is the reader's judgment, not established by this audit; wording findings are advisory")
PROMOTED = {"synthetic", "asimov", "preliminary", "unvalidated", "failed", "user-supplied"}
MEASURED_RE = re.compile(r"\b(we measure|measured|observed|observation of|in data|the data show|data show)\b", re.I)
DISCOVERY_RE = re.compile(r"\b(observation of|evidence for|discover(?:y|ed)?|establish(?:es|ed)?)\b", re.I)
UNIVERSAL_RE = re.compile(r"\b(for all|all energies|all masses|universal(?:ly)?|always|in general|any (?:energy|mass|regime))\b", re.I)
NEGATION_RE = re.compile(r"\b(no evidence|not|neither|nor|fails? to|without|rule[sd]? out|disfavou?r)\b", re.I)
ATTRIBUTION_RE = re.compile(r"\b(Ref\.|refs?\.|reported (?:by|in)|claims? that|according to|argue[sd]? that|et al\.)\b", re.I)
QUOTE_RE = re.compile(r"[\"“][^\"”]*[\"”]")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]


def _scan_sentences(text: str):
    """Sentences that may carry the author's own assertion: quotes removed, negated or attributed sentences skipped."""
    for s in _sentences(text):
        bare = QUOTE_RE.sub("", s)
        if NEGATION_RE.search(bare) or ATTRIBUTION_RE.search(bare):
            continue
        yield bare


def _locate(doc, locator: str):
    node = doc
    for part in locator.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None, False
    return node, True


def _round(value: str, rounding: str | None):
    """The display form of an exact value under a declared rounding rule, or None when the rule is unknown."""
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return None
    if rounding is None:
        return None
    kind, _, n = str(rounding).partition(":")
    try:
        n = int(n)
    except ValueError:
        return None
    if kind == "decimals":
        return str(d.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_EVEN))
    if kind == "significant" and n > 0:
        if d == 0:
            return "0"
        exp = d.adjusted() - n + 1
        return str(d.quantize(Decimal(1).scaleb(exp), rounding=ROUND_HALF_EVEN))
    return None


def _same_number(a: str, b: str) -> bool:
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except InvalidOperation:
        return str(a).strip() == str(b).strip()


def _covered(locator: str, event: dict) -> bool:
    level = event.get("level")
    if STRENGTH.get(level, 0) >= 3:
        return True
    if STRENGTH.get(level, 0) < 2:
        return False
    loc = locator.lower()
    recorded = [str(x).lower() for x in event.get("locators", []) or []]
    if level == "abstract+metadata" and not recorded:
        recorded = ["abstract"]
    return any(loc.startswith(r) or r in loc for r in recorded if r)


def audit_claims(record: dict, context: dict, policy: dict) -> dict:
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    fmt = format_of(record)
    findings: list[dict] = R.normalize(context["schema"]["findings"], "schema", "fix the record")
    notes: list[str] = []
    handoffs: list[dict] = []
    matrix: list[dict] = []
    facts: list[dict] = []
    scope = {"format": fmt, "claims": [], "policy": {"version": policy.get("policy_version")}}
    if fmt != "traceability":
        for i, c in enumerate(ext.get("claims", []) or []):
            matrix.append({"id": f"legacy:{i}", "text": c.get("text"), "status": c.get("status"), "verdict": None, "currency": None,
                           "evidence": [{"target": c.get("result_ref")}], "occurrences": [], "findings": []})
        findings.append(R.finding("audit.legacy_record", "unresolved", "$.required_capabilities",
                                  "legacy record: no evidence edges, occurrences or assessments to audit",
                                  "write a traceability record (communication:traceability-v1)", source="claims"))
        return R.assemble("audit_claims", scope, findings, checks_run=["schema"], notes=notes,
                          checks_not_run=[{"check": c, "reason": "legacy record", "required": True} for c in ("assessments", "sources", "wording", "numbers", "reporting")],
                          claim_matrix=matrix, draft_facts=facts, handoffs=handoffs, note=NOTE)
    root = Path(context["project_root"])
    read_events = {r.get("id"): r for r in ext.get("sources_read", []) or [] if isinstance(r, dict)}
    occ_by_claim: dict[str, list] = {}
    for o in ext.get("occurrences", []) or []:
        if isinstance(o, dict):
            occ_by_claim.setdefault(o.get("claim_id"), []).append(o)
    stale_claims = {f["location"].split(".assessment")[0] for f in findings if f["code"] == "communication.assessment_stale"}
    docs_cache: dict[str, dict | None] = {}
    rc = ext.get("reporting_context") if isinstance(ext.get("reporting_context"), dict) else None
    rc_fields = (rc or {}).get("fields") if rc else {}
    limitations = list(ext.get("limitations", []) or [])
    for i, c in enumerate(ext.get("claims", []) or []):
        if not isinstance(c, dict):
            continue
        cid, where = c.get("id"), f"$.extension.claims[{i}]"
        scope["claims"].append(cid)
        row_findings: list[str] = []

        def add(code, severity, location, message, action):
            findings.append(R.finding(code, severity, location, message, action, claim=cid, source="claims"))
            row_findings.append(code)
        a = c.get("assessment") if isinstance(c.get("assessment"), dict) else None
        verdict = a.get("verdict") if a else None
        if a:
            if verdict == "unsupported":
                add("claim.unsupported", "error", f"{where}.assessment", f"recorded verdict unsupported: {a.get('rationale')}",
                    "correct the attribution at the evidence locator (cite the version actually read) or narrow the wording; the record stays until the text is fixed")
            elif verdict == "partially-supported":
                add("claim.partially_supported", "warning", f"{where}.assessment", f"recorded verdict partially supported: {a.get('rationale')}",
                    "narrow the wording to what the inspected evidence supports, or add the missing evidence")
            elif verdict == "unresolved":
                add("claim.assessment_unresolved", "unresolved", f"{where}.assessment", f"assessment unresolved: {a.get('rationale')}",
                    "inspect the evidence and record a verdict with locators")
        if c.get("workflow_state") == "verified" and (a is None or where in stale_claims or verdict != "supported"):
            add("workflow.verified_without_assessment", "error", f"{where}.workflow_state",
                "workflow_state is verified but the claim has no current supported assessment",
                "a checkbox does not close a claim: record a current assessment with checked versions, or set the state back")
        # source read coverage
        for j, e in enumerate(c.get("evidence", []) or []):
            if not isinstance(e, dict) or e.get("target_kind") != "source" or (e.get("usage") or "used-in-claim") != "used-in-claim":
                continue
            ev = read_events.get(e.get("target"))
            if ev is None:
                continue  # the schema check already reports source_not_read
            if not _covered(str(e.get("locator", "")), ev):
                add("source.locator_not_read", "unresolved", f"{where}.evidence[{j}]",
                    f"edge {e.get('id')} cites {e.get('locator')!r} of {e.get('target')}, but the read event covers level "
                    f"{ev.get('level')!r} with locators {ev.get('locators') or []}: the cited passage was not read",
                    "read the cited passage and record a read event covering it, or cite what was read (an abstract value with the abstract locator)")
        # wording (advisory)
        status = set(c.get("status", []) or [])
        text = str(c.get("text", ""))
        for s in _scan_sentences(text):
            if status & PROMOTED and MEASURED_RE.search(s):
                add("wording.status_promotion", "warning", f"{where}.text",
                    f"wording describes a result labeled {sorted(status & PROMOTED)} as measured or observed: {s.strip()!r}",
                    "say what the result is (synthetic, preliminary, ...) in the sentence; status survives writing")
            if DISCOVERY_RE.search(s) and (c.get("claim_type") == "search" or (rc or {}).get("result_type") == "search" or re.search(r"\blocal\b", s, re.I)):
                glob = (rc_fields.get("global_significance") or {}).get("state") == "provided" if rc else False
                if not glob:
                    add("wording.significance_unsupported", "warning", f"{where}.text",
                        f"discovery-level wording without a provided global significance: {s.strip()!r}",
                        "quote the local and global significance with the trials method, or weaken the wording")
                    handoffs.append({"to_skill": "hep-statistics", "claim": cid,
                                     "request": "global significance (look-elsewhere correction) and trials method for the quoted local excess"})
            if UNIVERSAL_RE.search(s) and not UNIVERSAL_RE.search(str((c.get("scope") or {}).get("text", ""))):
                add("wording.generalization", "warning", f"{where}.text",
                    f"wording generalizes beyond the recorded scope {str((c.get('scope') or {}).get('text', ''))!r}: {s.strip()!r}",
                    "restate the tested regime, or widen the scope with its evidence")
        # numbers: exact source values versus display strings
        source_value = None
        evidence_rows = []
        for e in c.get("evidence", []) or []:
            if not isinstance(e, dict):
                continue
            identity = evidence_fingerprint(e, record)
            inp = context["inputs"].get(e.get("target")) if e.get("target_kind") == "artifact" else context["sources"].get(e.get("target"))
            evidence_rows.append({"id": e.get("id"), "target_kind": e.get("target_kind"), "target": e.get("target"), "locator": e.get("locator"),
                                  "role": e.get("role"), "usage": e.get("usage") or "used-in-claim", "identity": identity,
                                  "resolved": bool(inp and inp.get("resolved"))})
            if e.get("target_kind") == "artifact" and e.get("role") == "supports" and source_value is None and inp and inp.get("resolved"):
                key = e.get("target")
                if key not in docs_cache:
                    try:
                        docs_cache[key] = json.loads((root / inp["path"]).read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        docs_cache[key] = None
                node, ok = _locate(docs_cache[key], str(e.get("locator", ""))) if docs_cache[key] is not None else (None, False)
                if ok:
                    source_value = (node, e)
        fact = {"claim_id": cid, "text": text, "claim_type": c.get("claim_type"), "status": sorted(status), "value": None, "unit": None,
                "uncertainty": {}, "source": None, "limitations": limitations, "unresolved_inputs": list(c.get("unresolved_inputs", []) or [])}
        if source_value is not None:
            node, e = source_value
            val = node.get("value") if isinstance(node, dict) else node
            fact.update(value=None if val is None else str(val), unit=str(node.get("unit")) if isinstance(node, dict) and "unit" in node else None,
                        uncertainty={k: str(node[k]) for k in ("stat", "syst") if isinstance(node, dict) and k in node},
                        source={"edge": e.get("id"), "target": e.get("target"), "locator": e.get("locator"), "identity": evidence_fingerprint(e, record)})
            for k, o in enumerate(occ_by_claim.get(cid, [])):
                ov = o.get("value") if isinstance(o.get("value"), dict) else None
                if ov is None or val is None:
                    continue
                owhere = f"$.extension.occurrences[{o.get('id')}]"
                if fact["unit"] is not None and str(ov.get("unit")) != fact["unit"]:
                    add("occurrence.unit_conversion_unspecified", "unresolved", owhere,
                        f"occurrence {o.get('id')} displays unit {ov.get('unit')!r}, the source value is in {fact['unit']!r}; no conversion is recorded",
                        "record the conversion (factor, justification) or display the source unit")
                    continue
                shown = _round(str(val), ov.get("rounding"))
                if shown is None:
                    if not _same_number(str(ov.get("value")), str(val)):
                        add("occurrence.value_unrounded_comparison", "warning", owhere,
                            f"occurrence {o.get('id')} displays {ov.get('value')!r}, the source value is {val!r}, and no rounding rule is declared",
                            "declare the rounding (decimals:n or significant:n) so the display can be checked; not corrected automatically")
                elif not _same_number(str(ov.get("value")), shown):
                    add("occurrence.value_mismatch", "error", owhere,
                        f"occurrence {o.get('id')} displays {ov.get('value')!r}, the source value {val!r} rounds to {shown!r} under {ov.get('rounding')}",
                        "update the display value to the authoritative source value")
        facts.append(fact)
        matrix.append({"id": cid, "text": text, "claim_type": c.get("claim_type"), "status": sorted(status), "verdict": verdict,
                       "currency": "stale" if where in stale_claims else (a.get("currency") if a else None),
                       "assessor": (a or {}).get("assessor"), "evidence": evidence_rows,
                       "occurrences": [{"id": o.get("id"), "document_id": o.get("document_id"), "locator": o.get("locator"), "state": o.get("state")}
                                       for o in occ_by_claim.get(cid, [])],
                       "unresolved_inputs": list(c.get("unresolved_inputs", []) or []), "findings": row_findings})
        for req in c.get("unresolved_inputs", []) or []:
            handoffs.append({"to_skill": "the producing skill", "claim": cid, "request": req})
    reporting = None
    checks_run = ["schema", "assessments", "sources", "wording", "numbers"]
    not_run = []
    if rc is not None:
        reporting = check_reporting(rc, policy)
        findings += reporting["findings"]
        checks_run.append("reporting")
    else:
        kinds = {c.get("claim_type") for c in ext.get("claims", []) or [] if isinstance(c, dict)}
        if kinds & {"measurement", "search", "limit", "theory-prediction", "ml-result"}:
            findings.append(R.finding("reporting.context_missing", "unresolved", "$.extension.reporting_context",
                                      "no reporting context: the result type and its method metadata are not declared",
                                      "add reporting_context (result_type, method, fields) so completeness can be checked", source="reporting"))
        not_run.append({"check": "reporting", "reason": "no reporting_context in the record", "required": False})
    return R.assemble("audit_claims", scope, findings, checks_run=checks_run, checks_not_run=not_run, notes=notes,
                      claim_matrix=matrix, draft_facts=facts, handoffs=handoffs, reporting=reporting, note=NOTE)

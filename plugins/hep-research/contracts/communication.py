"""Pure structural semantics of the communication extension (owner: research-communication).

Two formats share the artifact type `communication`:
- legacy: claims with `result_ref` and a scalar or array status (ext_communication.json); every claim must carry the
  sticky statuses of every input, because nothing records which input a claim uses;
- traceability 1.0.0, selected by the capability `communication:traceability-v1` (ext_communication_traceability.json):
  claims carry evidence edges, so each claim inherits the sticky caveats of the inputs it uses (`usage: used-in-claim`),
  whatever the epistemic role of the edge. Document occurrences, read events and support assessments are checked for
  internal consistency only.

This module never opens a file: an artifact edge is checked against the envelope's declared `inputs`, a source edge
against the declared ledgers and read events, an assessment against the declared input digests. Resolving files,
ledgers and manuscripts is contracts/communication_project.py (which imports this module, never the reverse).
Schema validity, dependency consistency, scientific support and output readiness remain four different statements.
"""
from __future__ import annotations

import hashlib
import json

from contracts.schema import Report
from contracts.vocab import NAMESPACED, Vocabulary

TRACEABILITY_CAPABILITY = "communication:traceability-v1"
TRACEABILITY_VERSIONS = ("1.0.0",)
LEGACY_SCHEMA, TRACEABILITY_SCHEMA = "ext_communication.json", "ext_communication_traceability.json"
DEFAULT_USAGE = {"supports": "used-in-claim", "qualifies": "used-in-claim"}  # contradicts/background need an explicit usage
SUPPORTING_ROLES = {"supports", "qualifies"}


def _sticky():
    from contracts.validate import STICKY_STATUSES, UPGRADED, required_statuses  # validate imports this module lazily
    return STICKY_STATUSES, UPGRADED, required_statuses


def format_of(doc: dict) -> str:
    """'traceability' when the capability is declared, else 'legacy'."""
    caps = doc.get("required_capabilities") if isinstance(doc.get("required_capabilities"), list) else []
    return "traceability" if TRACEABILITY_CAPABILITY in caps else "legacy"


def extension_schema(doc: dict) -> str:
    return TRACEABILITY_SCHEMA if format_of(doc) == "traceability" else LEGACY_SCHEMA


def claim_digest(claim: dict) -> str:
    """sha256 over the claim's text and scope in canonical JSON: a wording or scope change changes it, nothing else does."""
    payload = {"text": claim.get("text"), "scope": claim.get("scope")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def evidence_fingerprint(edge: dict, doc: dict) -> str:
    """Identity of what an edge points at, from the record alone: an artifact edge uses the declared input sha256, a
    source edge the edge's own version string. 'unknown' when the record does not pin it (never an invented digest)."""
    if edge.get("target_kind") == "artifact":
        for inp in doc.get("inputs", []) or []:
            if isinstance(inp, dict) and inp.get("ref") == edge.get("target"):
                sha = inp.get("sha256")
                return f"sha256:{sha}" if isinstance(sha, str) and sha else "unknown"
        return "unknown"
    v = edge.get("version")
    return f"version:{v}" if isinstance(v, str) and v else "unknown"


def _legacy_rules(doc: dict, ext: dict, rep: Report) -> None:
    sticky, upgraded, required_statuses = _sticky()
    inherited = {s for i in doc.get("inputs", []) for s in i.get("status", [])}
    for i, c in enumerate(ext.get("claims", [])):
        cs = c.get("status")
        cs = {x for x in cs if isinstance(x, str)} if isinstance(cs, list) else ({cs} if isinstance(cs, str) else set())
        missing = sorted(set(required_statuses(doc.get("inputs", []))) - cs)
        if missing or (cs & upgraded and inherited & set(sticky)):
            rep.add("error", f"$.extension.claims[{i}].status", "communication.status_upgraded",
                    f"a claim must keep its inputs' statuses {missing or sorted(inherited & set(sticky))}; communication never upgrades status")


def _traceability_rules(doc: dict, ext: dict, rep: Report) -> None:
    sticky, upgraded, required_statuses = _sticky()
    inputs = {i["ref"]: i for i in doc.get("inputs", []) or [] if isinstance(i, dict) and isinstance(i.get("ref"), str)}
    envelope_required = set(required_statuses(doc.get("inputs", []) or []))
    namespaces: dict[str, int] = {}
    for k, led in enumerate(ext.get("evidence_ledgers", []) or []):
        ns = led.get("namespace")
        namespaces[ns] = namespaces.get(ns, 0) + 1
        if not led.get("bound") and not (led.get("sources_ref") and led.get("claims_ref")):
            rep.add("error", f"$.extension.evidence_ledgers[{k}]", "communication.ledger_ref_missing",
                    f"ledger '{ns}' is neither bound (bound: true) nor given by sources_ref and claims_ref")
        if namespaces[ns] == 2:
            rep.add("error", f"$.extension.evidence_ledgers[{k}]", "communication.ambiguous_namespace",
                    f"namespace '{ns}' is declared by more than one ledger: a source id in it names two records")
    read = {r.get("id") for r in ext.get("sources_read", []) or [] if isinstance(r, dict)}
    documents = {}
    for k, d in enumerate(ext.get("documents", []) or []):
        if d.get("id") in documents:
            rep.add("error", f"$.extension.documents[{k}].id", "communication.duplicate_id", f"duplicate document id '{d.get('id')}'")
        documents[d.get("id")] = d
    claims: dict[str, dict] = {}
    edge_ids: set[str] = set()
    for i, c in enumerate(ext.get("claims", []) or []):
        where = f"$.extension.claims[{i}]"
        cid = c.get("id")
        if cid in claims:
            rep.add("error", f"{where}.id", "communication.duplicate_id", f"duplicate claim id '{cid}'")
        claims[cid] = c
        status = set(c.get("status", []))
        if "observed" in status and ({"synthetic", "asimov"} & status):
            rep.add("error", f"{where}.status", "communication.claim_status_conflict",
                    "'observed' cannot be combined with 'synthetic' or 'asimov' on one claim; a comparison keeps the identities on its edges")
        used_sticky: set[str] = set()
        used_observed = False
        edges = c.get("evidence", []) or []
        for j, e in enumerate(edges):
            ewhere = f"{where}.evidence[{j}]"
            if e.get("id") in edge_ids:
                rep.add("error", f"{ewhere}.id", "communication.duplicate_id", f"duplicate evidence id '{e.get('id')}'")
            edge_ids.add(e.get("id"))
            usage = e.get("usage") or DEFAULT_USAGE.get(e.get("role"))
            if usage is None:
                rep.add("unresolved", f"{ewhere}.usage", "communication.usage_missing",
                        f"edge '{e.get('id')}' ({e.get('role')}) does not say whether it is used in the claim; treated as used")
                usage = "used-in-claim"
            if usage == "context-only" and not str(e.get("usage_reason") or "").strip():
                rep.add("error", f"{ewhere}.usage_reason", "communication.context_only_without_reason",
                        "a context-only edge needs the reason its provenance does not enter the claim")
            if e.get("target_kind") == "artifact":
                inp = inputs.get(e.get("target"))
                if inp is None:
                    rep.add("error", f"{ewhere}.target", "communication.unknown_input",
                            f"artifact target '{e.get('target')}' is not a declared inputs[].ref")
                    continue
                if usage == "used-in-claim":
                    used_sticky |= {s for s in inp.get("status", []) if s in sticky}
                    used_observed = used_observed or "observed" in inp.get("status", [])
            elif e.get("target_kind") == "source":
                m = NAMESPACED.match(str(e.get("target")))
                if not m:
                    rep.add("error", f"{ewhere}.target", "communication.bad_source_id", f"source target '{e.get('target')}' is not '<namespace>:<id>'")
                    continue
                if m.group(1) not in namespaces:
                    rep.add("error", f"{ewhere}.target", "communication.source_namespace_undeclared",
                            f"namespace '{m.group(1)}' of '{e.get('target')}' is not declared in evidence_ledgers")
                if e.get("target") not in read:
                    rep.add("unresolved", f"{ewhere}.target", "communication.source_not_read",
                            f"'{e.get('target')}' has no read event in sources_read: the cited passage is not recorded as inspected")
                if usage == "used-in-claim":
                    used_observed = True  # a published result is a source of its own; the record carries no dataset label
        if edges:
            missing = sorted(used_sticky - status)
            if missing:
                rep.add("error", f"{where}.status", "communication.status_upgraded",
                        f"claim uses inputs carrying {missing} but does not carry them; communication never upgrades status")
            if status & upgraded and not used_observed:
                rep.add("error", f"{where}.status", "communication.status_upgraded",
                        f"claim carries {sorted(status & upgraded)} but no used evidence carries 'observed' or is a source")
        else:
            missing = sorted(envelope_required - status)
            if missing or (status & upgraded):
                rep.add("error", f"{where}.status", "communication.status_upgraded",
                        f"a claim without evidence edges must keep every input status {sorted(envelope_required)} and cannot claim "
                        f"{sorted(status & upgraded) or 'more'}; map its evidence to narrow this")
            if not c.get("unresolved_inputs"):
                rep.add("unresolved", f"{where}.evidence", "communication.claim_unmapped",
                        "no evidence edge and no unresolved input request: the claim is not traceable")
        _assessment_rules(c, doc, {e.get("id"): e for e in edges}, rep, where)
    for k, o in enumerate(ext.get("occurrences", []) or []):
        where = f"$.extension.occurrences[{k}]"
        if o.get("claim_id") not in claims:
            rep.add("error", f"{where}.claim_id", "communication.unknown_claim", f"occurrence names unknown claim '{o.get('claim_id')}'")
        if o.get("document_id") not in documents:
            rep.add("error", f"{where}.document_id", "communication.unknown_document", f"occurrence names unknown document '{o.get('document_id')}'")
    if ext.get("scope", {}).get("occurrences") and not ext.get("documents"):
        rep.add("unresolved", "$.extension.documents", "communication.documents_missing",
                "manuscript coverage is in scope but no document is declared")


def _assessment_rules(c: dict, doc: dict, edges: dict, rep: Report, where: str) -> None:
    a = c.get("assessment")
    awhere = f"{where}.assessment"
    if not isinstance(a, dict):
        rep.add("unresolved", awhere, "communication.assessment_missing",
                f"claim '{c.get('id')}' has no recorded support assessment")
        return
    ids = a.get("evidence_ids", []) or []
    for eid in ids:
        if eid not in edges:
            rep.add("error", f"{awhere}.evidence_ids", "communication.unknown_evidence_id", f"'{eid}' is not an evidence edge of this claim")
    if a.get("verdict") in ("supported", "partially-supported"):
        if not any(edges[e].get("role") in SUPPORTING_ROLES for e in ids if e in edges):
            rep.add("error", f"{awhere}.verdict", "communication.supported_without_evidence",
                    f"verdict '{a.get('verdict')}' names no supporting or qualifying evidence edge; a judgment without identified "
                    "evidence is inconsistent")
    stale = []
    if isinstance(a.get("claim_digest"), str):
        if a["claim_digest"] != claim_digest(c):
            stale.append("the claim text or scope changed since the assessment")
    else:
        stale.append("the assessment does not pin the claim text (claim_digest)")
    fps = a.get("evidence_fingerprints") if isinstance(a.get("evidence_fingerprints"), dict) else {}
    for eid in ids:
        if eid not in edges:
            continue
        now = evidence_fingerprint(edges[eid], doc)
        then = fps.get(eid)
        if then is None:
            stale.append(f"edge '{eid}' has no recorded fingerprint")
        elif then != now:
            stale.append(f"edge '{eid}' identity changed ({then} -> {now})")
        elif now == "unknown":
            stale.append(f"edge '{eid}' identity is unknown on both sides")
    if stale:
        rep.add("unresolved", awhere, "communication.assessment_stale",
                "assessment must be redone before it counts: " + "; ".join(stale))
        if a.get("currency") == "current":
            rep.add("error", f"{awhere}.currency", "communication.currency_mismatch",
                    "currency says 'current' but the assessment is stale: " + stale[0])


def validate_extension(doc: dict, vocab: Vocabulary, report: Report) -> None:
    """Pure communication rules on an envelope whose extension already passed its schema (see validate_artifact)."""
    ext = doc.get("extension") if isinstance(doc.get("extension"), dict) else {}
    fmt = format_of(doc)
    tv = ext.get("traceability_version")
    if fmt == "legacy":
        if tv is not None:
            report.add("error", "$.extension.traceability_version", "communication.capability_missing",
                       f"traceability_version {tv!r} without required_capabilities [{TRACEABILITY_CAPABILITY}]: a reader "
                       "that lacks the capability would read this record under the legacy rules")
        _legacy_rules(doc, ext, report)
        return
    if tv is None:
        report.add("error", "$.extension.traceability_version", "communication.traceability_version_missing",
                   f"{TRACEABILITY_CAPABILITY} is required but the extension declares no traceability_version")
        return
    if tv not in TRACEABILITY_VERSIONS:
        report.add("error", "$.extension.traceability_version", "communication.traceability_version_unknown",
                   f"traceability_version {tv!r} is not one this reader implements {list(TRACEABILITY_VERSIONS)}")
        return
    _traceability_rules(doc, ext, report)

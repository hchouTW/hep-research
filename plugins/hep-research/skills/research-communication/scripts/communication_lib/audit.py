"""check_communication: structural, traceability and manuscript checks of one communication record (plan T5).

Checks are cumulative: schema validates the record alone (no project path is opened); traceability resolves inputs,
ledgers, sources and documents through contracts/communication_project.py; manuscript opens each declared document
and compares every declared occurrence with the current text (communication_lib.documents). The report says which
checks ran and which did not, with reasons; a schema-only run may pass but never calls traceability complete, and a
record with no claims cannot pass vacuously. Nothing here establishes scientific support.
"""
from __future__ import annotations

from pathlib import Path

from communication_lib import report as R
from communication_lib.documents import check_occurrence
from contracts.communication import format_of
from contracts.communication_project import normalize_dependency_report
from contracts.validate import validate_artifact

CHECKS = ("schema", "traceability", "manuscript")
NOTE = ("mechanical checks only: schema validity, dependency consistency and occurrence location say nothing about the "
        "scientific support of a claim; an assessment in the record is its assessor's statement, not verified here")


def audit_communication(record: dict, context: dict | None, *, checks: str = "traceability") -> dict:
    if checks not in CHECKS:
        raise ValueError(f"--checks must be one of {CHECKS}, got {checks!r}")
    level = CHECKS.index(checks)
    requested = list(CHECKS[:level + 1])
    if level > 0 and context is None:
        raise ValueError("traceability and manuscript checks need a resolved project context")
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    fmt = format_of(record)
    findings: list[dict] = []
    notes: list[str] = []
    checks_run, not_run = [], []
    claims = ext.get("claims", []) or []
    occurrences = ext.get("occurrences", []) or []
    scope = {"checks": requested, "format": fmt, "claims": [c.get("id") for c in claims if isinstance(c, dict)],
             "documents": [d.get("id") for d in ext.get("documents", []) or [] if isinstance(d, dict)],
             "source_versions": {r.get("id"): r.get("version") for r in ext.get("sources_read", []) or [] if isinstance(r, dict)}}
    inputs = {}
    coverage: dict = {}

    # schema
    schema = context["schema"] if context is not None else validate_artifact(record).as_dict()
    findings += R.normalize(schema["findings"], "schema", "fix the record")
    checks_run.append("schema")
    if not claims:
        findings.append(R.finding("audit.no_claims", "unresolved", "$.extension.claims", "the record declares no claim: nothing to trace",
                                  "add the claims the document makes, or state why none is traceable"))
    traceability = "not-checked"
    if level == 0:
        not_run += [{"check": "traceability", "reason": "not requested (--checks schema)", "required": False},
                    {"check": "manuscript", "reason": "not requested (--checks schema)", "required": False}]
        notes.append("schema-only run: inputs, ledgers and documents were not opened; traceability is not checked")
    else:
        traceability = context["traceability"]
        inputs = {"record_sha256": context.get("artifact_sha256"),
                  "inputs": {ref: {"sha256": i.get("sha256"), "declared_sha256": i.get("declared_sha256"), "match": i.get("match")}
                             for ref, i in context["inputs"].items()},
                  "documents": {did: d.get("sha256") for did, d in context["documents"].items()}}
        findings += R.normalize(context["findings"], "resolution", "resolve the reference inside the project root")
        findings += R.normalize(normalize_dependency_report(context["dependencies"]), "dependencies", "fix the input chain")
        checks_run.append("traceability")
        for c in context.get("checks_not_run", []):
            not_run.append({"check": f"traceability:{c['check']}", "reason": c["reason"], "required": False})
        mapped = [c for c in claims if isinstance(c, dict) and c.get("evidence")]
        stale = {f["path"].split(".assessment")[0] for f in schema["findings"] if f["code"] == "communication.assessment_stale"}
        assessed = [c for c in claims if isinstance(c, dict) and isinstance(c.get("assessment"), dict)]
        coverage["claims"] = {"declared": len(claims), "mapped": len(mapped), "unmapped": len(claims) - len(mapped),
                              "assessed": len(assessed), "stale": len(stale)}
        coverage["inputs"] = {"declared": len(context["inputs"]), "resolved": sum(1 for i in context["inputs"].values() if i["resolved"])}
        coverage["sources"] = {"cited": len(context["sources"]), "resolved": sum(1 for s in context["sources"].values() if s["resolved"])}
        coverage["documents"] = {"declared": len(context["documents"]), "resolved": sum(1 for d in context["documents"].values() if d["resolved"])}
        if level == 1:
            not_run.append({"check": "manuscript", "reason": "not requested (--checks manuscript opens the documents)", "required": False})
    occ_rows = []
    if level == 2:
        checks_run.append("manuscript")
        occ_rows, occ_findings = _manuscript(context, ext, fmt, occurrences, claims)
        findings += occ_findings
        if not occurrences:
            findings.append(R.finding("audit.no_occurrences", "unresolved", "$.extension.occurrences",
                                      "manuscript check requested but the record declares no occurrence: nothing was compared with the documents",
                                      "map where each claim appears before asking for manuscript coverage", source="manuscript"))
        counts = {k: sum(1 for o in occ_rows if o["outcome"] == v) for k, v in
                  (("located", "located"), ("mismatched", "mismatch"), ("ambiguous", "ambiguous"), ("unresolved", "unresolved"))}
        counts["unresolved"] += counts.pop("ambiguous")
        coverage["occurrences"] = {"declared": len(occ_rows), "located": counts["located"], "checked": counts["located"] + counts["mismatched"],
                                   "mismatched": counts["mismatched"], "unresolved": counts["unresolved"]}
        coverage["whole_manuscript"] = "not-claimed"
        notes.append("manuscript coverage is limited to the declared occurrences; paraphrases and conceptual dependencies elsewhere "
                     "in the documents were not read")
    rep = R.assemble("check_communication", scope, findings, checks_run=checks_run, checks_not_run=not_run, notes=notes,
                     inputs=inputs, traceability=traceability, coverage=coverage, schema={"ok": schema["ok"]},
                     occurrences=occ_rows, note=NOTE)
    return rep


def _manuscript(context: dict, ext: dict, fmt: str, occurrences: list, claims: list):
    rows, findings = [], []
    if fmt != "traceability":
        return rows, findings
    root = Path(context["project_root"])
    docs = {d.get("id"): d for d in ext.get("documents", []) or [] if isinstance(d, dict)}
    texts: dict[str, str | None] = {}
    for did, d in context["documents"].items():
        if d.get("resolved"):
            try:
                texts[did] = (root / d["resolved_path"]).read_text(encoding="utf-8", errors="replace")
            except OSError:
                texts[did] = None
        else:
            texts[did] = None
    with_occ = set()
    for i, occ in enumerate(occurrences):
        if not isinstance(occ, dict):
            continue
        where = f"$.extension.occurrences[{i}]"
        with_occ.add(occ.get("claim_id"))
        row = {"id": occ.get("id"), "claim_id": occ.get("claim_id"), "document_id": occ.get("document_id"), "locator": occ.get("locator"),
               "outcome": "unresolved", "reason": None, "current": None}
        rows.append(row)
        text = texts.get(occ.get("document_id"))
        if text is None:
            row["reason"] = "document not available"
            continue
        res = check_occurrence(text, str(docs.get(occ.get("document_id"), {}).get("format", "text")), occ)
        row.update(outcome=res["outcome"], reason=res["reason"], current=res["current"])
        if res["outcome"] == "mismatch":
            findings.append(R.finding("occurrence.passage_mismatch", "error", where,
                                      f"occurrence {occ.get('id')} of claim {occ.get('claim_id')}: {res['reason']}",
                                      "update the manuscript to the authoritative value, or re-map the occurrence; the manifest cannot stand in for the text",
                                      claim=occ.get("claim_id"), source="manuscript"))
        elif res["outcome"] == "include":
            row["outcome"] = "unresolved"
            findings.append(R.finding("occurrence.include_not_followed", "unresolved", where, res["reason"],
                                      "point the occurrence at the included file as its own document, or make the passage literal in the main file",
                                      claim=occ.get("claim_id"), source="manuscript"))
        elif res["outcome"] == "ambiguous":
            findings.append(R.finding("occurrence.locator_ambiguous", "unresolved", where, res["reason"],
                                      "make the locator unique (label, anchor text) and re-run", claim=occ.get("claim_id"), source="manuscript"))
        elif res["outcome"] == "unresolved":
            findings.append(R.finding("occurrence.locator_not_found", "unresolved", where, res["reason"],
                                      "check the locator against the current document", claim=occ.get("claim_id"), source="manuscript"))
        elif isinstance(occ.get("value"), dict) and str(occ["value"].get("value", "")) not in res["current"]:
            findings.append(R.finding("occurrence.value_not_in_passage", "warning", where,
                                      f"declared display value {occ['value'].get('value')!r} does not appear in the located passage",
                                      "review: the value, its rounding or the mapping may be stale; no automatic correction",
                                      claim=occ.get("claim_id"), source="manuscript"))
    if (ext.get("scope") or {}).get("occurrences"):
        for c in claims:
            if isinstance(c, dict) and c.get("id") not in with_occ:
                findings.append(R.finding("occurrence.claim_without_occurrence", "unresolved", f"$.extension.claims[{c.get('id')}]",
                                          f"claim {c.get('id')} has no declared occurrence although manuscript coverage is in scope",
                                          "map where the claim appears, or record that it appears nowhere", claim=c.get("id"), source="manuscript"))
    return rows, findings

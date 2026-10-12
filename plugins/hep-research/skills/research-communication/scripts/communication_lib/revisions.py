"""track_revision_impact: compare a baseline and a revised communication record and list what the change touches
(plan T6, Section 4.7).

The baseline is immutable and compared through its pinned identities (input digests, edge fingerprints, claim
digests); an old reference is never re-resolved against today's file: the historical value is read only when the
pinned file is still present with its recorded digest, otherwise the content comparison is incomplete and only the
identity-level impact is reported. Changes are classified (analysis-rerun, source-change, reference-move,
reassessment, content-edit, status-change, added, removed), propagated to the recorded occurrences of the claim, and
reopen the claim's assessment and any verified revision item that depends on it. A stale assessment is a judgment that
must be redone, not a wrong one. Coverage is the recorded occurrences: paraphrases and conceptual dependencies need a
targeted read, which the report requests instead of claiming.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from communication_lib import report as R
from communication_lib.claims import _locate, _round, _same_number
from contracts.communication import claim_digest, evidence_fingerprint, format_of
from contracts.communication_project import normalize_dependency_report

NOTE = ("impact from recorded identities and the recorded occurrences; a reopened assessment or item is stale, not wrong; "
        "whole-manuscript coverage is not claimed")
MATERIAL = ("analysis-rerun", "reassessment", "status-change", "removed")


def _value_at(root: Path, ref: str, locator: str, expected_sha: str | None):
    """(value, available) at a locator of a pinned artifact: read only when the file lies inside the project root and
    carries the pinned digest; a ref without a digest is never read (its content cannot be shown to be the baseline's)."""
    raw_path = Path(str(ref))
    path = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    if not expected_sha or not (path == root or root in path.parents):
        return None, False
    try:
        raw = path.read_bytes()
    except OSError:
        return None, False
    if expected_sha and hashlib.sha256(raw).hexdigest() != expected_sha:
        return None, False
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, False
    node, ok = _locate(doc, locator)
    if not ok:
        return None, True
    val = node.get("value") if isinstance(node, dict) else node
    return (None if val is None else str(val)), True


def _recorded_display(occurrences: list):
    """(value, rounding) the baseline record displayed for a claim, from its first occurrence with a value; else None."""
    for o in occurrences:
        v = o.get("value") if isinstance(o.get("value"), dict) else None
        if v and v.get("value") is not None:
            return str(v["value"]), v.get("rounding")
    return None


def _occ_key(o: dict) -> tuple:
    return (o.get("document_id"), o.get("locator"), o.get("passage"), json.dumps(o.get("value"), sort_keys=True))


def diff_communication(before: dict, after: dict, context: dict) -> dict:
    root = Path(context["project_root"]).resolve()
    b_ext = before.get("extension") if isinstance(before.get("extension"), dict) else {}
    a_ext = after.get("extension") if isinstance(after.get("extension"), dict) else {}
    findings: list[dict] = R.normalize(context.get("schema", {}).get("findings", []), "schema", "fix the revised record")
    findings += R.normalize(context.get("findings", []), "resolution", "resolve the reference inside the project root")
    if context.get("dependencies"):
        findings += R.normalize(normalize_dependency_report(context["dependencies"]), "dependencies", "fix the input chain")
    notes: list[str] = []
    impacts: list[dict] = []
    unaffected: list[dict] = []
    scope = {"before_format": format_of(before), "after_format": format_of(after)}
    if format_of(before) != "traceability" or format_of(after) != "traceability":
        findings.append(R.finding("revision.legacy_record", "unresolved", "$.required_capabilities",
                                  "a legacy record carries no claim ids, evidence edges or occurrences: impact cannot be traced",
                                  "write both records in the traceability format", source="revisions"))
        return R.assemble("track_revision_impact", scope, findings, checks_run=["schema"], notes=notes,
                          checks_not_run=[{"check": "impact", "reason": "legacy record", "required": True}],
                          impacts=impacts, unaffected=unaffected, revision_items=[], coverage={}, note=NOTE)
    b_inputs = {i.get("ref"): i for i in before.get("inputs", []) or [] if isinstance(i, dict)}
    b_claims = {c.get("id"): c for c in b_ext.get("claims", []) or [] if isinstance(c, dict)}
    a_claims = {c.get("id"): c for c in a_ext.get("claims", []) or [] if isinstance(c, dict)}
    b_occ: dict[str, list] = {}
    for o in b_ext.get("occurrences", []) or []:
        if isinstance(o, dict):
            b_occ.setdefault(o.get("claim_id"), []).append(o)
    a_occ: dict[str, list] = {}
    for o in a_ext.get("occurrences", []) or []:
        if isinstance(o, dict):
            a_occ.setdefault(o.get("claim_id"), []).append(o)
    content_complete = True
    stale_occurrences = 0
    for idx, (cid, ac) in enumerate(a_claims.items()):
        where = f"$.extension.claims[{idx}]"
        bc = b_claims.get(cid)
        if bc is None:
            impacts.append({"claim_id": cid, "kind": "added", "evidence_changed": [], "value_change": None, "assessment": "none",
                            "occurrences": [{"id": o.get("id"), "state": "new"} for o in a_occ.get(cid, [])],
                            "required_actions": ["assess the new claim against its evidence"], "content_comparison": "n/a"})
            continue
        text_changed = claim_digest(bc) != claim_digest(ac)
        status_changed = sorted(bc.get("status", [])) != sorted(ac.get("status", []))
        b_edges = {e.get("id"): e for e in bc.get("evidence", []) or [] if isinstance(e, dict)}
        a_edges = {e.get("id"): e for e in ac.get("evidence", []) or [] if isinstance(e, dict)}
        evidence_changed = []
        value_change = "none"
        comparison = "complete"
        for eid, ae in a_edges.items():
            be = b_edges.get(eid)
            id_before = evidence_fingerprint(be, before) if be else None
            id_after = evidence_fingerprint(ae, after)
            moved = be is not None and be.get("target") != ae.get("target")
            if be is None or moved or id_before != id_after or be.get("locator") != ae.get("locator"):
                evidence_changed.append({"edge": eid, "from": be.get("target") if be else None, "to": ae.get("target"),
                                         "identity_before": id_before, "identity_after": id_after})
                if ae.get("target_kind") == "artifact" and (be is None or id_before != id_after):
                    loc = str(ae.get("locator", ""))
                    b_in = b_inputs.get(be.get("target")) if be else None
                    v_before, b_avail = (_value_at(root, str(be.get("target")), str(be.get("locator", "")), (b_in or {}).get("sha256"))
                                         if be else (None, False))
                    a_in = context["inputs"].get(ae.get("target"), {})
                    v_after, a_avail = (_value_at(root, a_in["path"], loc, a_in.get("declared_sha256")) if a_in.get("resolved") and a_in.get("match") is not False
                                        else (None, False))
                    if not b_avail:
                        comparison = "incomplete"
                        findings.append(R.finding("revision.history_unavailable", "unresolved", f"{where}.evidence[{eid}]",
                                                  (f"the baseline file {be.get('target')!r} with digest {id_before} is not available inside the root: the old "
                                                   "value is not recovered from today's file") if be else f"edge {eid} is new: it has no baseline value",
                                                  "keep a snapshot of the baseline inputs; impact is reported at identity level", claim=cid, source="revisions"))
                    if not a_avail:
                        comparison = "incomplete"
                        findings.append(R.finding("revision.evidence_unavailable", "unresolved", f"{where}.evidence[{eid}]",
                                                  f"the revised evidence {ae.get('target')!r} cannot be read with its declared digest",
                                                  "resolve the new input before closing the revision", claim=cid, source="revisions"))
                    if b_avail and a_avail and v_before is not None and v_after is not None and _same_number(v_before, v_after):
                        pass
                    elif not b_avail and a_avail and v_after is not None:
                        # the historical content is gone: the baseline's recorded display value is the only "before" the record holds
                        shown = _recorded_display(b_occ.get(cid, []))
                        same = shown is not None and (_same_number(shown[0], v_after) or _same_number(shown[0], _round(v_after, shown[1]) or ""))
                        if not same:
                            value_change = {"locator": loc, "before": None, "before_recorded_display": shown[0] if shown else None, "after": v_after}
                        # a later edge whose value matches the display never erases a value change found on an earlier edge
                    else:
                        value_change = {"locator": loc, "before": v_before if b_avail else None, "after": v_after if a_avail else None}
        for eid in sorted(set(b_edges) - set(a_edges)):
            evidence_changed.append({"edge": eid, "from": b_edges[eid].get("target"), "to": None,
                                     "identity_before": evidence_fingerprint(b_edges[eid], before), "identity_after": None})
            value_change = value_change if isinstance(value_change, dict) else {"locator": b_edges[eid].get("locator"), "before": None, "after": None}
        b_o = {o.get("id"): o for o in b_occ.get(cid, [])}
        a_o = {o.get("id"): o for o in a_occ.get(cid, [])}
        occ_edited = [oid for oid, o in a_o.items() if oid in b_o and _occ_key(o) != _occ_key(b_o[oid])] + [oid for oid in a_o if oid not in b_o]
        dropped = [oid for oid in b_o if oid not in a_o]
        identity_changed = any(e["identity_before"] != e["identity_after"] and e["to"] is not None for e in evidence_changed)
        moved = any(e["from"] is not None and e["to"] is not None and e["from"] != e["to"] for e in evidence_changed)
        changes = set()
        if isinstance(value_change, dict) and evidence_changed:
            changes.add("analysis-rerun")
        elif identity_changed:
            changes.add("source-change")
        if moved and not identity_changed:
            changes.add("reference-move")
        if text_changed:
            changes.add("reassessment")
        if status_changed:
            changes.add("status-change")
        if occ_edited or dropped:
            changes.add("content-edit")
        if not changes:
            unaffected.append({"id": cid, "provenance": sorted(ac.get("status", [])), "occurrences": sorted(a_o)})
            continue
        kind = next(k for k in ("analysis-rerun", "source-change", "reassessment", "status-change", "reference-move", "content-edit") if k in changes)
        has_assessment = isinstance(ac.get("assessment"), dict)
        reopen = changes & {"analysis-rerun", "reassessment", "status-change"}
        if not has_assessment:
            assessment = "none"
        elif reopen:
            assessment = "reopened"
        elif "source-change" in changes:
            assessment = "reconcile-identity"
        else:
            assessment = "kept"
        occ_rows = []
        for oid, o in a_o.items():
            state = "stale" if reopen else ("edited" if oid in occ_edited else "unchanged")
            stale_occurrences += state == "stale"
            occ_rows.append({"id": oid, "document_id": o.get("document_id"), "locator": o.get("locator"), "state": state})
        actions = []
        loc = (value_change or {}).get("locator") if isinstance(value_change, dict) else (a_edges and next(iter(a_edges.values())).get("locator"))
        if "analysis-rerun" in changes:
            actions += [f"inspect the new evidence at {loc} and re-assess claim {cid}",
                        "update the occurrences " + ", ".join(sorted(a_o)) + " to the new value, then re-run check_communication --checks manuscript"]
        if "reassessment" in changes:
            actions += [f"inspect the evidence at {loc}: re-assess claim {cid} against its new wording or scope"]
        if "status-change" in changes:
            actions += [f"re-assess claim {cid}: its provenance labels changed", "carry the new labels into every occurrence"]
        if "source-change" in changes:
            actions += ["reconcile the identity change: confirm the inspected passage or field is unchanged, then re-pin the assessment"]
        if "reference-move" in changes:
            actions += ["update the edge target to the new path; identity unchanged"]
        if "content-edit" in changes:
            actions += ["re-run check_communication --checks manuscript for the edited occurrences"]
        if dropped:
            actions.append("occurrences " + ", ".join(dropped) + " were dropped from the record: confirm the passages were removed or re-map them")
        impacts.append({"claim_id": cid, "kind": kind, "changes": sorted(changes), "evidence_changed": evidence_changed, "value_change": value_change,
                        "assessment": assessment, "occurrences": occ_rows, "required_actions": actions, "content_comparison": comparison})
        content_complete = content_complete and comparison == "complete"
        if assessment == "reopened":
            findings.append(R.finding("revision.assessment_stale", "unresolved", f"{where}.assessment",
                                      f"the assessment of {cid} predates this change ({kind}); it is not wrong, it must be redone",
                                      "inspect the new evidence or wording and record a new assessment", claim=cid, source="revisions"))
        if assessment == "reconcile-identity" or kind == "analysis-rerun":
            findings.append(R.finding("revision.identity_changed", "unresolved", f"{where}.evidence",
                                      f"the evidence identity of {cid} changed: " + "; ".join(f"{e['edge']}: {e['identity_before']} -> {e['identity_after']}" for e in evidence_changed),
                                      "a changed hash is not proof of a changed conclusion: reconcile the identity and re-pin",
                                      claim=cid, source="revisions"))
        if (changes & set(MATERIAL)) or dropped or not a_o:
            findings.append(R.finding("revision.coverage_unmapped", "unresolved", f"{where}",
                                      f"claim {cid} changed ({kind}); only its recorded occurrences {sorted(a_o)} are listed"
                                      + (f", and {dropped} were dropped" if dropped else ""),
                                      "do a targeted read of the manuscript, talks and response letters for paraphrases and conceptual "
                                      "dependencies of this claim; map what you find", claim=cid, source="revisions"))
    for cid in b_claims:
        if cid not in a_claims:
            impacts.append({"claim_id": cid, "kind": "removed", "evidence_changed": [], "value_change": None, "assessment": "none",
                            "occurrences": [{"id": o.get("id"), "state": "orphaned"} for o in b_occ.get(cid, [])],
                            "required_actions": ["remove or re-map the occurrences that cited the removed claim"], "content_comparison": "n/a"})
            findings.append(R.finding("revision.coverage_unmapped", "unresolved", f"$.extension.claims[{cid}]",
                                      f"claim {cid} was removed; its former occurrences {[o.get('id') for o in b_occ.get(cid, [])]} need a targeted read",
                                      "do a targeted read for its remaining traces", claim=cid, source="revisions"))
    changed_ids = {i["claim_id"] for i in impacts if i["kind"] != "added"}
    material_ids = {i["claim_id"] for i in impacts if i["kind"] in MATERIAL or set(i.get("changes", [])) & set(MATERIAL)}
    items = _revision_items(a_ext, context, material_ids, changed_ids, findings)
    cov = {"claims": {"before": len(b_claims), "after": len(a_claims), "changed": len(changed_ids), "unaffected": len(unaffected)},
           "occurrences": {"before": sum(len(v) for v in b_occ.values()), "after": sum(len(v) for v in a_occ.values()), "stale": stale_occurrences},
           "whole_manuscript": "not-claimed", "content_comparison": "complete" if content_complete else "incomplete"}
    notes.append("derived outputs not in the record (slides, response letters) are not covered; map their occurrences to include them")
    return R.assemble("track_revision_impact", scope, findings, checks_run=["schema", "identities", "occurrences", "revision-items"],
                      checks_not_run=[{"check": "manuscript-text", "reason": "run check_communication --checks manuscript on the revised record", "required": False}],
                      notes=notes, impacts=impacts, unaffected=unaffected, revision_items=items, coverage=cov, note=NOTE)


def _revision_items(a_ext: dict, context: dict, material_ids: set, changed_ids: set, findings: list) -> list[dict]:
    current = {d.get("sha256") for d in context.get("documents", {}).values()} | {i.get("sha256") for i in context.get("inputs", {}).values()}
    current = {f"sha256:{s}" for s in current if s} | {s for s in current if s}
    out = []
    for k, it in enumerate(a_ext.get("revision_items", []) or []):
        if not isinstance(it, dict):
            continue
        where = f"$.extension.revision_items[{k}]"
        state = it.get("state")
        row = {"id": it.get("id"), "cause": it.get("cause"), "kind": it.get("kind"), "state": state,
               "impacted_claims": list(it.get("impacted_claims", []) or [])}
        depends = set(row["impacted_claims"]) & material_ids
        if state == "verified":
            ev = it.get("completion_evidence") or []
            if not ev:
                findings.append(R.finding("revision.verified_without_evidence", "error", where,
                                          f"revision item {it.get('id')} is verified without completion evidence (checks and versions)",
                                          "record the checks run and the document/source versions they ran on, or set the state back to edited",
                                          source="revisions"))
            elif any(e.get("version") not in current for e in ev if isinstance(e, dict)):
                findings.append(R.finding("revision.item_version_mismatch", "unresolved", where,
                                          f"revision item {it.get('id')} was verified on a version that is not the current document or input",
                                          "re-run the checks on the current versions", source="revisions"))
            if depends:
                row["state"] = "stale"
                findings.append(R.finding("revision.item_reopened", "unresolved", where,
                                          f"revision item {it.get('id')} was verified, but claim(s) {sorted(depends)} changed since: reopened",
                                          "redo the item's actions and checks on the new versions", source="revisions"))
        elif state in ("pending-evidence", "ready-to-edit", "edited"):
            findings.append(R.finding("revision.item_not_verified", "unresolved", where,
                                      f"revision item {it.get('id')} is {state}: an edit list is not evidence that the edits happened",
                                      "complete the actions, run the checks on the current versions, then mark it verified with that evidence",
                                      source="revisions"))
        out.append(row)
    return out

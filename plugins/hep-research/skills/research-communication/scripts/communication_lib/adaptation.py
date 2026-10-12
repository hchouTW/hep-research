"""Audience adaptation and evidence-backed reviewer responses (plan T8).

check_adaptation: a derived draft (manuscript paragraph, meeting abstract, talk outline, poster content, public summary)
comes with a companion manifest (assets/paper/adaptation-manifest-template.json): the brief (audience, format, length
budget, central claim, record version, indispensable limitations), one statement per quantitative statement or
conclusion with its claim ids, intentional omissions, unresolved inputs and the semantic review. The check locates each
statement in the draft, requires a claim id, compares the numbers with the record (source value, uncertainties,
display values), requires the claim's status labels and the indispensable limitations to survive compression, and
flags a universal wording whose claim scope is narrower. Keyword overlap is not a semantic check: the manifest's
semantic_review is the reader's recorded judgment, and its absence is unresolved.

draft_responses: a reviewer action table and response wording generated from the recorded action state: a completed
and checked change may be described in the past tense with its locator; pending work stays explicit; a reasoned
decision not to change the manuscript is a valid disposition that needs its reason.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from communication_lib import report as R
from communication_lib.claims import PROMOTED, UNIVERSAL_RE, _locate
from communication_lib.documents import normalize
from contracts.communication import format_of

NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")
STATUS_WORDS = {"synthetic": ("synthetic", "合成", "模擬", "示意"), "asimov": ("asimov",), "preliminary": ("preliminary", "初步"),
                "failed": ("failed", "失敗"), "unvalidated": ("unvalidated", "not validated", "not yet validated", "未驗證", "未經驗證"),
                "user-supplied": ("user-supplied", "supplied by the user", "使用者提供")}
NEGATED_RE = re.compile(r"\b(not yet|have not|has not|had not|haven't|hasn't|not been|will|are being|is being)\b|尚未|還沒|未", re.I)
COMPLETION_RE = re.compile(r"\bwe (have|performed|reran|re-ran|updated|changed|added|revised|rerun)\b", re.I)
NOTE_ADAPT = ("mechanical consistency of a derived draft with its record; keyword overlap is not a semantic check: the recorded "
              "semantic review is the reader's judgment")
NOTE_RESP = "wording generated from the recorded action state; a response asserts only what the revision ledger shows as completed and checked"


def _numbers(text: str) -> set[str]:
    return {m.group(0) for m in NUMBER_RE.finditer(text.replace("±", "+/-"))}


def _same(a: str, b: str) -> bool:
    try:
        return Decimal(a) == Decimal(b)
    except InvalidOperation:
        return a == b


def _claim_numbers(claim: dict, record: dict, context: dict, occ: list) -> set[str]:
    nums = _numbers(str(claim.get("text", ""))) | _numbers(str((claim.get("scope") or {}).get("text", "")))
    for o in occ:
        nums |= _numbers(str(o.get("passage", "")))
        v = o.get("value") if isinstance(o.get("value"), dict) else None
        if v and v.get("value") is not None:
            nums.add(str(v["value"]))
    root = Path(context["project_root"])
    for e in claim.get("evidence", []) or []:
        if not isinstance(e, dict) or e.get("target_kind") != "artifact":
            continue
        inp = context["inputs"].get(e.get("target"))
        if not inp or not inp.get("resolved"):
            continue
        try:
            doc = json.loads((root / inp["path"]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        node, ok = _locate(doc, str(e.get("locator", "")))
        if not ok:
            continue  # audit_claims reports evidence.locator_not_found; here the statement's numbers simply find no source value
        if isinstance(node, dict):
            for k in ("value", "stat", "syst"):
                if node.get(k) is not None:
                    nums.add(str(node[k]))
        elif node is not None:
            nums.add(str(node))
    return nums


def check_adaptation(record: dict, context: dict, manifest: dict, draft: str) -> dict:
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    findings: list[dict] = []
    notes: list[str] = []
    brief = manifest.get("brief") if isinstance(manifest.get("brief"), dict) else {}
    scope = {"audience": brief.get("audience"), "format": brief.get("format"), "central_claim": brief.get("central_claim"),
             "record_ref": brief.get("record_ref"), "manifest_version": manifest.get("manifest_version")}
    if format_of(record) != "traceability":
        findings.append(R.finding("adaptation.legacy_record", "unresolved", "$.required_capabilities",
                                  "legacy record: statements cannot be linked to claim ids", "write a traceability record first", source="adaptation"))
    claims = {c.get("id"): c for c in ext.get("claims", []) or [] if isinstance(c, dict)}
    occ_by_claim: dict[str, list] = {}
    for o in ext.get("occurrences", []) or []:
        if isinstance(o, dict):
            occ_by_claim.setdefault(o.get("claim_id"), []).append(o)
    if brief.get("record_sha256") and brief["record_sha256"] != context.get("artifact_sha256"):
        findings.append(R.finding("adaptation.record_stale", "unresolved", "manifest.brief.record_sha256",
                                  f"the manifest was written against record {brief['record_sha256'][:12]}..., the current record is "
                                  f"{str(context.get('artifact_sha256'))[:12]}...", "re-check the draft against the current record and re-pin", source="adaptation"))
    norm_draft = normalize(draft).lower()
    located_spans: list[str] = []
    counts = {"declared": 0, "located": 0, "with_claim": 0}
    number_cache: dict[str, set] = {}
    for i, st in enumerate(manifest.get("statements", []) or []):
        if not isinstance(st, dict):
            continue
        where = f"manifest.statements[{i}]"
        counts["declared"] += 1
        text = normalize(str(st.get("text", ""))).lower()
        if text and text in norm_draft:
            counts["located"] += 1
            located_spans.append(text)
        else:
            findings.append(R.finding("adaptation.statement_not_in_draft", "error", where,
                                      f"statement {st.get('id')} is not in the draft: {st.get('text')!r}",
                                      "update the manifest to the sentence as written, or restore the sentence", source="adaptation"))
        ids = [c for c in (st.get("claim_ids") or []) if isinstance(c, str)]
        if not ids and st.get("kind") in ("quantitative", "conclusion"):
            findings.append(R.finding("adaptation.statement_without_claim", "error", where,
                                      f"{st.get('kind')} statement {st.get('id')} names no claim id", "link it to the claim it derives from, or drop it",
                                      source="adaptation"))
        elif ids:
            counts["with_claim"] += 1
        for cid in ids:
            c = claims.get(cid)
            if c is None:
                findings.append(R.finding("adaptation.unknown_claim", "error", where, f"claim {cid!r} is not in the record",
                                          "fix the claim id", source="adaptation"))
                continue
            if cid not in number_cache:
                number_cache[cid] = _claim_numbers(c, record, context, occ_by_claim.get(cid, []))
            sticky = [s for s in c.get("status", []) if s in PROMOTED]
            if sticky and not any(w in text for s in sticky for w in STATUS_WORDS.get(s, (s,))):
                findings.append(R.finding("adaptation.status_dropped", "error", where,
                                          f"statement {st.get('id')} draws on {cid} labeled {sticky} but carries no such label: {st.get('text')!r}",
                                          "say what the result is (synthetic, preliminary, ...) in the sentence; compression cannot drop it",
                                          claim=cid, source="adaptation"))
            if UNIVERSAL_RE.search(str(st.get("text", ""))) and not UNIVERSAL_RE.search(str((c.get("scope") or {}).get("text", ""))):
                findings.append(R.finding("adaptation.scope_dropped", "error", where,
                                          f"statement {st.get('id')} generalizes beyond the scope of {cid} ({(c.get('scope') or {}).get('text')!r}): {st.get('text')!r}",
                                          f"revise the wording to keep the tested regime: {(c.get('scope') or {}).get('text')!r}", claim=cid, source="adaptation"))
        if ids:
            allowed = set().union(*(number_cache.get(cid, set()) for cid in ids if cid in claims))
            for n in _numbers(str(st.get("text", ""))):
                if not any(_same(n, a) for a in allowed):
                    findings.append(R.finding("adaptation.number_mismatch", "error", where,
                                              f"number {n} in statement {st.get('id')} matches no value, uncertainty or display value of {ids}",
                                              "use the record's value (draft facts of audit_claims.py) or map the number to its claim", claim=ids[0],
                                              source="adaptation"))
    covered = " ".join(located_spans)
    for n in _numbers(draft):
        if not any(n in span for span in located_spans) and not any(_same(n, a) for a in _numbers(covered)):
            findings.append(R.finding("adaptation.unmapped_number", "warning", "draft", f"number {n} in the draft is outside every mapped statement",
                                      "map the sentence to a claim, or state why it carries no scientific content", source="adaptation"))
    lims = brief.get("indispensable_limitations") or []
    present = 0
    for lim in lims:
        text, written = (lim, lim) if isinstance(lim, str) else (lim.get("text"), lim.get("as_written") or lim.get("text"))
        if normalize(str(written)).lower() in norm_draft:
            present += 1
        else:
            findings.append(R.finding("adaptation.caveat_dropped", "error", "manifest.brief.indispensable_limitations",
                                      f"indispensable limitation {text!r} does not appear in the draft (looked for {written!r})",
                                      "restore the condition; it changes the scientific meaning and cannot be compressed away", source="adaptation"))
    sr = manifest.get("semantic_review") if isinstance(manifest.get("semantic_review"), dict) else None
    if not sr or sr.get("verdict") != "consistent":
        findings.append(R.finding("adaptation.semantic_review_pending", "unresolved", "manifest.semantic_review",
                                  "no recorded semantic review with verdict 'consistent': keyword overlap does not show the draft means what the record says",
                                  "read the draft against the claim matrix and record the review (by, date, verdict)", source="adaptation"))
    unresolved = [u for u in (manifest.get("unresolved_inputs") or []) if isinstance(u, str)]
    if unresolved:
        findings.append(R.finding("adaptation.unresolved_inputs", "unresolved", "manifest.unresolved_inputs",
                                  "the draft waits for: " + "; ".join(unresolved), "obtain the inputs from the producing skill", source="adaptation"))
    return R.assemble("check_adaptation", scope, findings, checks_run=["statements", "numbers", "status-labels", "limitations", "scope"],
                      checks_not_run=[{"check": "semantic-review", "reason": "a reader's judgment, recorded in the manifest", "required": True}],
                      notes=notes, coverage={"statements": counts, "limitations": {"indispensable": len(lims), "present": present}},
                      omissions=[o for o in (manifest.get("omissions") or []) if isinstance(o, dict)], unresolved_inputs=unresolved, note=NOTE_ADAPT)


def draft_responses(record: dict, context: dict) -> dict:
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    findings: list[dict] = []
    items = [it for it in (ext.get("reviewer_items") or []) if isinstance(it, dict)]
    revs = {r.get("id"): r for r in (ext.get("revision_items") or []) if isinstance(r, dict)}
    occ = {o.get("id"): o for o in (ext.get("occurrences") or []) if isinstance(o, dict)}
    current = {d.get("sha256") for d in context.get("documents", {}).values()} | {i.get("sha256") for i in context.get("inputs", {}).values()}
    current = {f"sha256:{s}" for s in current if s} | {s for s in current if s}
    table, drafts = [], []
    if not items:
        findings.append(R.finding("response.no_items", "unresolved", "$.extension.reviewer_items", "no reviewer items recorded",
                                  "record each referee comment with its requested action, claims and revision items", source="responses"))
    for k, it in enumerate(items):
        where = f"$.extension.reviewer_items[{k}]"
        linked = [revs.get(rid, {"id": rid, "state": "unknown"}) for rid in (it.get("revision_items") or [])]
        verified = [r for r in linked if r.get("state") == "verified" and r.get("completion_evidence")
                    and all(ev.get("version") in current for ev in r["completion_evidence"] if isinstance(ev, dict))]
        for r in linked:
            if r.get("state") == "verified" and r.get("completion_evidence") and r not in verified:
                findings.append(R.finding("response.evidence_not_current", "unresolved", where,
                                          f"revision item {r.get('id')} was verified on a version that is not the current document or input",
                                          "re-run the checks on the current versions before describing the change as done", source="responses"))
        locators = []
        for r in linked:
            for oid in r.get("impacted_occurrences") or []:
                if oid in occ:
                    locators.append(f"{occ[oid].get('document_id')} {occ[oid].get('locator')}")
        disposition = it.get("disposition")
        action = str(it.get("requested_action") or "").strip()
        reason = str(it.get("response_draft") or "").strip()
        if disposition == "changed" and linked and len(verified) == len(linked):
            state = "completed"
            text = f"We thank the referee for this comment. We have {action}" + (f"; see {', '.join(locators)}" if locators else "") + "."
        elif disposition == "declined":
            state = "declined"
            if not reason:
                findings.append(R.finding("response.decline_without_reason", "error", where,
                                          f"comment {it.get('id')} is declined without a reason", "give the physics or editorial reason in response_draft",
                                          source="responses"))
            text = "We thank the referee for this comment. We have not changed the manuscript on this point: " + (reason or "[REASON NEEDED]")
        else:
            state = "pending"
            open_items = [f"{r.get('id')} ({r.get('state')})" for r in linked if r not in verified] or ["no revision item recorded"]
            text = (f"We thank the referee for this comment. {action[:1].upper() + action[1:]} is pending: " + ", ".join(open_items)
                    + "; the manuscript will be updated once the work is completed and checked.")
            if disposition in ("changed", "partially-changed"):
                findings.append(R.finding("response.changed_without_completion", "error", where,
                                          f"comment {it.get('id')} is marked {disposition} but its revision items are not all verified with evidence: {open_items}",
                                          "complete and verify the revision items first, or set the disposition to pending", source="responses"))
        asserted = any(COMPLETION_RE.search(s) and not NEGATED_RE.search(s) for s in re.split(r"(?<=[.;!?])\s+", reason))
        if state != "completed" and asserted and disposition != "declined":
            findings.append(R.finding("response.asserts_uncompleted_work", "error", f"{where}.response_draft",
                                      f"the response draft asserts completed work while the change is {state}: {reason[:120]!r}",
                                      "describe the work as pending; use the generated wording", source="responses"))
        table.append({"comment_id": it.get("id"), "comment": it.get("comment"), "requested_action": action, "claims": list(it.get("claims") or []),
                      "revision_items": [{"id": r.get("id"), "state": r.get("state")} for r in linked], "locators": locators, "state": state,
                      "disposition": disposition, "verification": [e for r in verified for e in (r.get("completion_evidence") or [])]})
        drafts.append({"comment_id": it.get("id"), "state": state, "text": text})
    return R.assemble("draft_reviewer_responses", {"items": [it.get("id") for it in items]}, findings,
                      checks_run=["dispositions", "completion-evidence", "wording"], checks_not_run=[], action_table=table, drafts=drafts, note=NOTE_RESP)

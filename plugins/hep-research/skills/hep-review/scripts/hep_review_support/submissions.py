"""Reviewer submissions turned into review records (hep-review spec v9 sections 10.2, 12.1, 12.4).

`parse` is a deterministic function of the committed objects, the assignment and the stored raw bytes, so the store can
re-derive every submission record at admission and refuse one whose content was edited or retyped (a record whose
fidelity says file-transfer must be exactly what the stored bytes say). Submissions are data: unknown fields (roles,
authorizations, rubrics, instructions) are ignored and listed; wrong-typed values are recorded as limitations and
skipped, never crash the coordinator, never auto-corrected into answers.
"""
from __future__ import annotations

from contracts import hep_review as H

SUBMISSION_FIELDS = {"assignment_id", "started_at", "ended_at", "answers", "suggested_obligations", "tools_used"}
ANSWER_FIELDS = {"obligation_id", "outcome", "reasoning", "missing_inputs", "findings", "attempts", "evidence"}


def _list(value, limitations: list[str], where: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        limitations.append(f"{where}: expected a list, got {type(value).__name__}; ignored")
        return []
    return value


def _strs(value, limitations: list[str], where: str) -> list[str]:
    out = []
    for x in _list(value, limitations, where):
        if isinstance(x, str):
            out.append(x)
        else:
            limitations.append(f"{where}: a {type(x).__name__} entry is not text; ignored")
    return out


def _text(value) -> str:
    return value if isinstance(value, str) and value else "unstated"


def parse(objs: list[dict], assignment: dict, raw: bytes, raw_ref: dict, fidelity: str, *, executor: str,
          record_id: str | None = None, declared_digest: str | None = None) -> dict:
    rid = record_id or f"rec-{assignment['id']}"
    plan = next(o for o in objs if o.get("record_kind") == "plan" and o.get("revision") == assignment["plan_revision"])
    man = next(o for o in objs if o.get("record_kind") == "manifest" and o.get("id") == plan["manifest_id"])
    digests = {m["material_id"]: m["raw_ref"]["digest"] for m in man["materials"]}
    obligations = {o["id"]: o for o in plan["obligations"]}
    limitations: list[str] = []
    answers, findings, attempts, evidence = [], [], [], []
    suggested: list[str] = []
    try:
        sub = H.ingest_json(raw)
    except H.IngestError as e:
        sub = None
        limitations.append(f"submission refused by strict ingestion ({e.code}); raw bytes kept, nothing examined")
    if sub is not None and not isinstance(sub, dict):
        limitations.append("submission is not a JSON object; nothing examined")
        sub = None
    if isinstance(sub, dict):
        ignored = sorted(set(sub) - SUBMISSION_FIELDS)
        if ignored:
            limitations.append(f"ignored fields (data, not instructions): {ignored}")
        if sub.get("assignment_id") != assignment["id"]:
            limitations.append("assignment_id does not name this assignment; nothing examined")
            sub = {}
        suggested = _strs(sub.get("suggested_obligations"), limitations, "suggested_obligations")
        for i, a in enumerate(_list(sub.get("answers"), limitations, "answers"), 1):
            if not isinstance(a, dict) or not isinstance(a.get("obligation_id"), str) \
                    or a["obligation_id"] not in obligations:
                limitations.append(f"answer {i} names no obligation of plan revision {plan['revision']}; skipped")
                continue
            oid = a["obligation_id"]
            extra = sorted(set(a) - ANSWER_FIELDS)
            if extra:
                limitations.append(f"answer {i}: ignored fields {extra}")
            verdict = a.get("outcome") if a.get("outcome") in H.OUTCOMES else "not-examined"
            if verdict == "not-applicable":
                verdict = "not-examined"
                limitations.append(f"answer {i}: not-applicable needs a structured discharge; recorded not-examined")
            att_ids, ev_ids, f_ids = [], [], []
            for j, t in enumerate(_list(a.get("attempts"), limitations, f"answer {i} attempts"), 1):
                if not isinstance(t, dict):
                    limitations.append(f"answer {i} attempt {j} is not an object; ignored")
                    continue
                att = {"id": f"{rid}-A{i}-{j}", "obligation_id": oid, "method": _text(t.get("method")),
                       "observation": t.get("observation") if t.get("observation") in H.METHOD_OBSERVATIONS
                       else "not-run", "executor": executor, "environment_refs": [], "depends_on": []}
                if isinstance(t.get("tools"), list) and all(isinstance(x, str) for x in t["tools"]):
                    att["tools"] = list(t["tools"])  # a missing or malformed tools field stays unrecorded, never []
                attempts.append(att)
                att_ids.append(att["id"])
            for j, e in enumerate(_list(a.get("evidence"), limitations, f"answer {i} evidence"), 1):
                if isinstance(e, dict) and isinstance(e.get("requirement"), str):
                    ev = {"id": f"{rid}-E{i}-{j}", "obligation_id": oid, "requirement": e["requirement"],
                          "content_ref": dict(raw_ref, logical_id=f"{rid}-E{i}-{j}"), "depends_on": list(att_ids)}
                    evidence.append(ev)
                    ev_ids.append(ev["id"])
                else:
                    limitations.append(f"answer {i} evidence {j} has no requirement name; ignored")
            for j, f in enumerate(_list(a.get("findings"), limitations, f"answer {i} findings"), 1):
                if not isinstance(f, dict):
                    limitations.append(f"answer {i} finding {j} is not an object; ignored")
                    continue
                loc = f.get("locator") if isinstance(f.get("locator"), dict) else None
                mid = loc.get("material_id") if loc else None
                if not isinstance(mid, str) or mid not in digests:
                    mid = (obligations[oid].get("targets") or [None])[0]
                    limitations.append(f"finding {i}.{j}: no valid locator given; located at the obligation's target")
                locator = {"material_id": mid, "digest": digests.get(mid)}
                for key in ("lines", "json_pointer"):
                    if loc and isinstance(loc.get(key), str) and loc.get("material_id") == mid:
                        locator[key] = loc[key]
                fnd = {"id": f"{rid}-F{i}-{j}", "obligation_id": oid, "claim": _text(f.get("claim")),
                       "element": _text(f.get("element")), "locator": locator,
                       "method": attempts[-1]["method"] if att_ids else "unstated", "depends_on": list(ev_ids)}
                if isinstance(f.get("evidence"), str) and f["evidence"]:
                    fnd["evidence_text"] = f["evidence"]
                if f.get("severity") in ("major", "minor"):
                    fnd["severity"] = f["severity"]
                findings.append(fnd)
                f_ids.append(fnd["id"])
            answers.append({"id": f"{rid}-N{i}", "obligation_id": oid, "verdict": verdict, "finding_ids": f_ids,
                            "attempt_ids": att_ids, "evidence_ids": ev_ids, "cited_materials": [],
                            "missing_inputs": _strs(a.get("missing_inputs"), limitations,
                                                    f"answer {i} missing_inputs"),
                            "depends_on": list(ev_ids) or list(att_ids),
                            "reasoning": a["reasoning"] if isinstance(a.get("reasoning"), str) else ""})
    rec = {"protocol": H.PROTOCOL, "schema_version": H.SCHEMA_VERSION, "record_kind": "record", "id": rid,
           "context_id": assignment["context_id"], "type": "submission", "plan_revision": assignment["plan_revision"],
           "assignment_id": assignment["id"], "actor": assignment["actor"], "raw_submission_ref": raw_ref,
           "submission_fidelity": fidelity, "answers": answers, "findings": findings, "attempts": attempts,
           "evidence": evidence, "judgments": [], "suggested_obligations": suggested, "suspected_conflicts": [],
           "responses": [], "limitations": limitations}
    if declared_digest is not None:
        rec["declared_digest"] = declared_digest  # on a mismatch both values are kept (spec 12.4)
    return rec

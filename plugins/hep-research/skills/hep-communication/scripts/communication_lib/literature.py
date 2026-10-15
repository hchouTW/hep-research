"""Literature and citation lifecycle, offline (plan T7).

Imports source and claim ledger records, an explicit search log and status notices into a literature record with
provenance. Records are deduplicated only by normalized stable identifiers (DOI, arXiv id without version, INSPIRE
record): title or author similarity proposes a merge and never performs one; a report and a study of the same work
(different formal status) stay separate records related as same-work. An arXiv version change keeps the version
history and flags the citing claims for reassessment. A correction or retraction notice flags dependent claims
(reassess within its scope, check outside it) without deleting a citation or asserting that every claim is false.
Freshness (an old verification date) is a reason to recheck, never proof of error. No lookup is performed; online
verification is an explicit host-agent workflow recorded as not performed here. Citation keys are preserved.
"""
from __future__ import annotations

import copy
import difflib
import re
from datetime import date, datetime

from communication_lib import report as R
from core.evidence.ledger import check_ledger

RECORD_VERSION = "1.0.0"
ARXIV_RE = re.compile(r"^(?:arxiv:)?\s*(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v(\d+))?$", re.I)
NOTE = ("offline import: records are merged only on identical stable identifiers; similarity proposes, a reader decides; "
        "notices flag claims for reassessment and never delete a citation; online verification was not performed")
STALE_DAYS = 365
ACCESS_LIMITED = ("metadata-only", "not-opened", "not-verified")


def normalize_doi(doi) -> str | None:
    if not isinstance(doi, str) or not doi.strip():
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:", "doi "):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d or None


def normalize_arxiv(aid) -> tuple[str, str | None] | None:
    if not isinstance(aid, str):
        return None
    m = ARXIV_RE.match(aid.strip())
    if not m:
        return None
    return m.group(1), (f"v{m.group(2)}" if m.group(2) else None)


def identifiers_of(src: dict) -> dict:
    ids = src.get("identifiers") if isinstance(src.get("identifiers"), dict) else {}
    dois = [normalize_doi(x) for x in (ids.get("dois") or src.get("dois") or [])]
    arx = [normalize_arxiv(x) for x in (ids.get("arxiv_ids") or src.get("arxiv_ids") or [])]
    out = {"doi": next((d for d in dois if d), None), "arxiv": next((a[0] for a in arx if a), None),
           "arxiv_version": next((a[1] for a in arx if a and a[1]), None),
           "inspire": str(ids.get("inspire_record_id")) if ids.get("inspire_record_id") not in (None, "") else None}
    return out


def _keys(ids: dict) -> set:
    return {(k, ids[k]) for k in ("doi", "arxiv", "inspire") if ids.get(k)}


def _norm_title(t) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(t or "").lower()).strip()


def _day(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def new_record(today: str) -> dict:
    return {"record_version": RECORD_VERSION, "created": today, "imported": [], "sources": {}, "claims": {}, "searches": [],
            "notices": [], "relations": [], "proposed_merges": [], "flags": [],
            "verification": {"online": "not-performed", "note": "check sources at a primary source through the host's authorized tools; record each check as a read event"}}


def import_literature(inputs: list[dict], existing: dict | None, *, today: str | None = None) -> tuple[dict, dict]:
    """(record, report). `inputs` are {"path", "sha256", "data"}; `existing` is a record this import merges into (copied,
    never modified). `data` holds `sources`, `claims`, `search_log` and `notices` arrays (all optional)."""
    today = today or date.today().isoformat()
    rec = copy.deepcopy(existing) if existing else new_record(today)
    findings: list[dict] = []
    notes: list[dict] = []
    alias: dict[str, str] = {}
    index: dict[tuple, str] = {}
    for sid, s in rec["sources"].items():
        for k in _keys(identifiers_of(s)):
            index.setdefault(k, sid)
    for inp in inputs:
        data = inp.get("data") if isinstance(inp.get("data"), dict) else {}
        sources = [s for s in (data.get("sources") or []) if isinstance(s, dict)]
        claims = [c for c in (data.get("claims") or []) if isinstance(c, dict)]
        ledger = check_ledger(sources, claims, today=_day(today))
        if ledger.get("errors"):
            codes = sorted({e["code"] for e in ledger["errors"]})
            findings.append(R.finding("literature.ledger_invalid", "error", inp.get("path", "input"),
                                      f"the imported ledger fails its own check: {', '.join(codes)}",
                                      "fix the records; invalid records are imported as given and marked", source="literature"))
        rec["imported"].append({"path": inp.get("path"), "sha256": inp.get("sha256"), "date": today,
                                "counts": {"sources": len(sources), "claims": len(claims), "searches": len(data.get("search_log") or []),
                                           "notices": len(data.get("notices") or [])}})
        for s in sources:
            _import_source(rec, s, inp, today, index, alias, findings, notes)
        for c in claims:
            cid = c.get("id")
            if not isinstance(cid, str):
                continue
            c = copy.deepcopy(c)
            c["source_ids"] = [alias.get(x, x) for x in (c.get("source_ids") or [])]
            rec["claims"][cid] = c
        for q in data.get("search_log") or []:
            if not isinstance(q, dict):
                continue
            entry = dict(q)
            entry["imported_from"] = inp.get("path")
            rec["searches"].append(entry)
            if entry.get("coverage_limits") or entry.get("export_count") is None:
                findings.append(R.finding("literature.search_incomplete", "unresolved", f"search_log[{len(rec['searches']) - 1}]",
                                          f"search {entry.get('query')!r} in {entry.get('database')} has coverage limits "
                                          f"{entry.get('coverage_limits') or 'unknown export count'}",
                                          "record the full export or state the limit in the review's coverage statement", source="literature"))
        for n in data.get("notices") or []:
            if isinstance(n, dict):
                _apply_notice(rec, n, alias, findings)
    _freshness_and_access(rec, today, notes)
    _citation_keys(rec, findings)
    rep = R.assemble("manage_literature", {"inputs": [i.get("path") for i in inputs], "existing": bool(existing), "today": today},
                     findings, checks_run=["ledger", "identifiers", "versions", "notices", "searches", "citation-keys"],
                     checks_not_run=[{"check": "online-verification", "reason": "offline import; verify at a primary source through the host's tools", "required": False},
                                     {"check": "full-text-reading", "reason": "a record states a read level; this import never reads a paper", "required": False}],
                     notes=notes, counts_record={"sources": len(rec["sources"]), "claims": len(rec["claims"]), "flags": len(rec["flags"]),
                                                 "proposed_merges": len(rec["proposed_merges"])}, note=NOTE)
    return rec, rep


def _read_event(s: dict, inp: dict) -> dict:
    return {"level": s.get("verification_level"), "date": s.get("verification_date") or s.get("access_date"),
            "locators": list(s.get("locators") or []), "imported_from": inp.get("path")}


def _import_source(rec, s, inp, today, index, alias, findings, notes):
    sid = s.get("id")
    if not isinstance(sid, str):
        return
    ids = identifiers_of(s)
    keys = _keys(ids)
    target = None
    for k in keys:
        if k in index and index[k] != sid:
            target = index[k]
            break
    if sid in rec["sources"]:
        _update_existing(rec, rec["sources"][sid], s, ids, inp, findings)
        for k in keys:
            index.setdefault(k, sid)
        return
    if target is not None:
        t = rec["sources"][target]
        if (t.get("formal_status") or "published") == (s.get("formal_status") or "published"):
            alias[sid] = target
            t.setdefault("aliases", []).append(sid)
            for k, v in ids.items():
                if v and not t["identifiers"].get(k):
                    t["identifiers"][k] = v
            t.setdefault("read_events", []).append(_read_event(s, inp))
            old_v, new_v = t["identifiers"].get("arxiv_version"), ids.get("arxiv_version")
            if ids.get("arxiv") and new_v and new_v != old_v:
                t.setdefault("versions", []).append({"version": new_v, "date": s.get("verification_date"), "imported_from": inp.get("path")})
                t["identifiers"]["arxiv_version"] = new_v
                citing = sorted(cid for cid, c in rec["claims"].items() if target in (c.get("source_ids") or []))
                rec["flags"].append({"source_id": target, "reason": f"arxiv version changed {old_v} -> {new_v} (via {sid})", "level": "reassess", "claims": citing})
                findings.append(R.finding("literature.version_changed", "unresolved", f"sources.{target}",
                                          f"{target}: arXiv version {old_v} -> {new_v} (imported as {sid}); claims {citing} cite the earlier version",
                                          "reread the cited passages in the new version and record new read events; the old events stay", source="literature"))
            notes.append({"code": "literature.merged_by_identifier", "message": f"{sid} is {target} (same stable identifier); its read event is kept"})
            return
        basis = next(f"{k}:{v}" for k, v in keys if (k, v) in index and index[(k, v)] == target)
        rec["relations"].append({"kind": "same-work", "from": target, "to": sid, "basis": basis})
    entry = copy.deepcopy(s)
    entry["identifiers"] = ids
    entry["read_events"] = [_read_event(s, inp)]
    entry["versions"] = [{"version": ids.get("arxiv_version"), "date": s.get("verification_date"), "imported_from": inp.get("path")}] if ids.get("arxiv") else []
    entry.setdefault("notices", [])
    entry.setdefault("status", "as-imported")
    entry["imported_from"] = inp.get("path")
    rec["sources"][sid] = entry
    for k in keys:
        index.setdefault(k, sid)
    titles = {oid: _norm_title(o.get("title")) for oid, o in rec["sources"].items() if oid != sid}
    mine = _norm_title(s.get("title"))
    for oid, t in titles.items():
        if mine and t and not (_keys(identifiers_of(rec["sources"][oid])) & keys):
            sim = difflib.SequenceMatcher(None, mine, t).ratio()
            if sim >= 0.9:
                rec["proposed_merges"].append({"ids": sorted([oid, sid]), "reason": "similar titles", "similarity": round(sim, 3)})
                findings.append(R.finding("literature.possible_duplicate", "warning", f"sources.{sid}",
                                          f"{sid} and {oid} have similar titles (similarity {sim:.2f}) but different stable identifiers: not merged",
                                          "compare the records; merge by hand only if they are one work", source="literature"))


def _update_existing(rec, t, s, ids, inp, findings):
    old_v = (t.get("identifiers") or {}).get("arxiv_version")
    new_v = ids.get("arxiv_version")
    t.setdefault("read_events", []).append(_read_event(s, inp))
    for k, v in ids.items():
        if not v or k == "arxiv_version":
            continue
        have = t.setdefault("identifiers", {}).get(k)
        if have and have != v:
            t.setdefault("conflicting_identifiers", []).append({k: v, "imported_from": inp.get("path")})
            findings.append(R.finding("literature.identifier_conflict", "error", f"sources.{s.get('id')}",
                                      f"{s.get('id')}: {k} {v!r} differs from the recorded {have!r}; the record keeps {have!r}",
                                      "one id, one work: fix the identifier or give the other work its own id", source="literature"))
        elif not have:
            t["identifiers"][k] = v
    if ids.get("arxiv") and new_v and new_v != old_v:
        t.setdefault("versions", []).append({"version": new_v, "date": s.get("verification_date"), "imported_from": inp.get("path")})
        t["identifiers"]["arxiv_version"] = new_v
        citing = sorted(cid for cid, c in rec["claims"].items() if t.get("id", "") in (c.get("source_ids") or []) or s.get("id") in (c.get("source_ids") or []))
        rec["flags"].append({"source_id": s.get("id"), "reason": f"arxiv version changed {old_v} -> {new_v}", "level": "reassess", "claims": citing})
        findings.append(R.finding("literature.version_changed", "unresolved", f"sources.{s.get('id')}",
                                  f"{s.get('id')}: arXiv version {old_v} -> {new_v}; claims {citing} cite the earlier version",
                                  "reread the cited passages in the new version and record new read events; the old events stay", source="literature"))


def _apply_notice(rec, n, alias, findings):
    sid = alias.get(n.get("source_id"), n.get("source_id"))
    s = rec["sources"].get(sid)
    rec["notices"].append(dict(n, source_id=sid))
    if s is None:
        findings.append(R.finding("literature.notice_unknown_source", "error", f"notices[{len(rec['notices']) - 1}]",
                                  f"notice names unknown source {sid!r}", "import the source first", source="literature"))
        return
    s.setdefault("notices", []).append({k: v for k, v in n.items() if k != "source_id"})
    kind = n.get("kind")
    if kind == "retraction":
        s["status"] = "retracted"
    elif kind == "correction":
        s["status"] = "corrected"
    elif kind in ("journal-version", "supersession") and n.get("new_source_id"):
        new = alias.get(n["new_source_id"], n["new_source_id"])
        s.setdefault("superseded_by", [])
        if new not in s["superseded_by"]:
            s["superseded_by"].append(new)
        if new in rec["sources"]:
            rec["sources"][new].setdefault("supersedes", [])
            if sid not in rec["sources"][new]["supersedes"]:
                rec["sources"][new]["supersedes"].append(sid)
        rec["relations"].append({"kind": kind, "from": sid, "to": new, "provenance": n.get("provenance"), "date": n.get("date")})
        return
    scope = str(n.get("scope") or "").lower()
    partial = n.get("affects") == "part" and scope
    dependents = [(cid, c) for cid, c in rec["claims"].items() if sid in (c.get("source_ids") or [])]
    for cid, c in dependents:
        inside = (not partial) or scope in str(c.get("location") or "").lower() or scope in str((c.get("scope") or {}).get("text") or "").lower()
        rec["flags"].append({"source_id": sid, "reason": f"{kind} notice ({n.get('affects', 'whole')}{': ' + n.get('scope') if partial else ''})",
                             "level": "reassess" if inside else "check", "claims": [cid]})
    if dependents:
        findings.append(R.finding("literature.notice_reassess", "unresolved", f"sources.{sid}",
                                  f"{kind} notice on {sid}: {len(dependents)} dependent claim(s) flagged (reassess inside the notice's scope, check outside)",
                                  "assess the notice's effect on each flagged claim; a notice does not by itself make a claim false or a citation deletable",
                                  source="literature"))


def _freshness_and_access(rec, today, notes):
    t = _day(today)
    seen = {(f["source_id"], f["level"]) for f in rec["flags"]}
    for sid, s in rec["sources"].items():
        d = _day(s.get("verification_date") or s.get("access_date"))
        if t and d and (t - d).days > STALE_DAYS and (sid, "recheck") not in seen:
            notes.append({"code": "literature.stale_verification", "message": f"{sid} was last verified {d} ({(t - d).days} days ago): recheck before quoting it as current; not a sign of error"})
            rec["flags"].append({"source_id": sid, "reason": f"verification date {d} older than {STALE_DAYS} days", "level": "recheck",
                                 "claims": sorted(cid for cid, c in rec["claims"].items() if sid in (c.get("source_ids") or []))})
        if s.get("verification_level") in ACCESS_LIMITED and (sid, "access-limited") not in seen:
            rec["flags"].append({"source_id": sid, "reason": f"read level {s.get('verification_level')}: {s.get('verification_limitations') or 'full text not read'}",
                                 "level": "access-limited", "claims": sorted(cid for cid, c in rec["claims"].items() if sid in (c.get("source_ids") or []))})


def _citation_keys(rec, findings):
    by_key: dict[str, list] = {}
    for sid, s in rec["sources"].items():
        if s.get("citation_key"):
            by_key.setdefault(str(s["citation_key"]), []).append(sid)
    for key, sids in by_key.items():
        if len(sids) > 1:
            findings.append(R.finding("literature.citation_key_collision", "error", f"citation_key={key}",
                                      f"citation key {key!r} is used by {sorted(sids)}; keys are never renamed here",
                                      "rename one key together with every manuscript caller, or merge the records if they are one work", source="literature"))

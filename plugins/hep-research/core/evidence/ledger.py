#!/usr/bin/env python3
"""Validate a profile's machine-readable source and claim ledger (evidence/sources.json, evidence/claims.json).

Ported from the legacy ams-analysis ledger validator (agentic-ai-skills@3e995a4) and generalized:
IDs may be profile-qualified ('<ns>:S01', '<ns>:C01'; pass --namespace to require it), and the
date a source was read at its verification level is `verification_date` (legacy `access_date`
is still accepted). Current date, publication date and verification date stay distinct.

Purpose: keep every experiment-specific statement traceable and never stronger than the
evidence behind it, so the skill cannot drift into quoting what it has not read.

What it does: checks duplicate IDs, required fields, allowed enumerations, dates,
source-to-claim referential integrity, supersession symmetry and cycles, and
over-strong claims (verification strength above what any supporting source achieved,
numeric quotation allowed at metadata level, an experiment-practice claim resting on no
Tier 1-2 source). It also lists stale verification dates as NOTES only: an old date
means "re-check", never "obsolete". It never edits the ledger and never touches the
network (network refresh is deliberately not implemented; a future one may only
propose metadata changes and must never promote a claim to full-text).

Verification strength order (weakest to strongest): not-verified = not-opened (0) <
metadata-only (1) < abstract+metadata = page (2) < full-text (3).

Usage (from the plugin root):
  python3 core/evidence/ledger.py [--sources P] [--claims P] [--today YYYY-MM-DD]
                                              [--stale-days N] [--strict]
Exit codes: 0 no errors; 1 errors (or warnings with --strict); 2 files unreadable.
Standard library only. Importable: check_ledger(sources, claims, today, stale_days).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

STRENGTH = {"not-verified": 0, "not-opened": 0, "metadata-only": 1, "abstract+metadata": 2, "page": 2, "full-text": 3}
CLAIM_TYPES = {"detector_fact", "performance_number", "analysis_method", "published_result", "general_method"}
SUPPORT_KINDS = {"primary", "absence_search", "third_party_context", "general_method"}
PRIMARY_TYPES = {"detector_fact", "performance_number", "analysis_method", "published_result"}
SOURCE_REQUIRED = ("id", "title", "authors", "tier", "verification_level", "supersedes", "superseded_by")
CLAIM_REQUIRED = ("id", "claim", "claim_types", "source_ids", "location", "scope", "verification_strength",
                  "numeric_quotation_allowed", "last_reviewed")
ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_ANY = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def _parse_day(text) -> date | None:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


class Findings:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.notes: list[dict] = []

    def add(self, level: str, code: str, where: str, message: str) -> None:
        getattr(self, level).append({"code": code, "where": where, "message": message})


def _read_date(s: dict):
    return s.get("verification_date", s.get("access_date"))


def _id_ok(value: str, letter: str, namespace: str | None) -> bool:
    prefix = re.escape(namespace) + ":" if namespace else r"(?:[a-z][a-z0-9-]*:)?"
    return bool(re.fullmatch(prefix + letter + r"\d{2,}", value))


def _check_sources(sources: list, f: Findings, today: date, namespace: str | None = None) -> dict:
    by_id: dict = {}
    for idx, s in enumerate(sources):
        where = s.get("id", f"sources[{idx}]") if isinstance(s, dict) else f"sources[{idx}]"
        if not isinstance(s, dict):
            f.add("errors", "source.malformed", where, "source record must be an object")
            continue
        for key in SOURCE_REQUIRED:
            if key not in s or s[key] in (None, ""):
                f.add("errors", "source.missing_field", where, f"missing required field '{key}'")
        sid = s.get("id")
        if sid in by_id:
            f.add("errors", "source.duplicate_id", where, f"duplicate source id {sid}")
        elif isinstance(sid, str):
            by_id[sid] = s
            if not _id_ok(sid, "S", namespace):
                f.add("errors", "source.bad_id", where, f"source id '{sid}' must look like {namespace + ':' if namespace else ''}S01")
        level = s.get("verification_level")
        if level is not None and level not in STRENGTH:
            f.add("errors", "source.bad_verification_level", where, f"verification_level '{level}' not in {sorted(STRENGTH)}")
        tier = s.get("tier")
        if not isinstance(tier, int) or isinstance(tier, bool) or not 1 <= tier <= 6:
            f.add("errors", "source.bad_tier", where, f"tier must be an integer 1-6, got {tier!r}")
        tr = s.get("tier_range")
        if tr is not None and not (isinstance(tr, list) and len(tr) == 2 and all(isinstance(x, int) for x in tr)
                                   and tr[0] == tier and tr[0] <= tr[1] <= 6):
            f.add("errors", "source.bad_tier_range", where, "tier_range must be [tier, worse_tier]")
        for key in ("verification_date", "access_date"):
            v = s.get(key)
            if v is not None and v not in ("unknown", "not-provided") and _parse_day(v) is None:
                f.add("errors", "source.bad_date", where, f"{key} '{v}' is not YYYY-MM-DD")
        pub = s.get("publication_date")
        if pub is not None and not ISO_ANY.match(str(pub)):
            f.add("errors", "source.bad_date", where, f"publication_date '{pub}' is not YYYY, YYYY-MM or YYYY-MM-DD")
        per = s.get("data_taking_period")
        if per is not None:
            for k in ("start", "end"):
                if per.get(k) is not None and not ISO_ANY.match(str(per[k])):
                    f.add("errors", "source.bad_date", where, f"data_taking_period.{k} '{per[k]}' is malformed")
        acc = _parse_day(_read_date(s))
        if acc and acc > today:
            f.add("errors", "source.future_access_date", where, f"verification_date {acc} is after today {today}")
        if acc and s.get("year") and s["year"] > acc.year:
            f.add("errors", "source.published_after_access", where, f"year {s['year']} is after the verification date {acc}: cannot have been read")
        if level in STRENGTH and STRENGTH[level] >= 1 and not _parse_day(_read_date(s)):
            f.add("errors", "source.level_without_access_date", where, f"level '{level}' requires a verification_date")
        if level in ("not-verified", "not-opened") and not s.get("verification_limitations"):
            f.add("warnings", "source.unverified_without_limitation", where, "unverified source should state its limitation")
        tt = s.get("tier_text")
        if tt is not None and not str(tt).startswith(str(tier)):
            f.add("errors", "source.tier_text_mismatch", where, f"tier_text '{tt}' does not start with tier {tier}")
    for sid, s in by_id.items():
        for key, back in (("supersedes", "superseded_by"), ("superseded_by", "supersedes")):
            for other in s.get(key) or []:
                if other == sid:
                    f.add("errors", "source.self_supersession", sid, f"{sid} lists itself in {key}")
                elif other not in by_id:
                    f.add("errors", "source.broken_relation", sid, f"{key} references unknown source {other}")
                elif sid not in (by_id[other].get(back) or []):
                    f.add("errors", "source.asymmetric_relation", sid, f"{sid}.{key} contains {other} but {other}.{back} lacks {sid}")
    for start in by_id:  # cycle check on 'supersedes'
        seen, stack = set(), [start]
        while stack:
            cur = stack.pop()
            for nxt in by_id.get(cur, {}).get("supersedes") or []:
                if nxt == start:
                    f.add("errors", "source.supersession_cycle", start, f"supersession cycle through {start}")
                    stack = []
                    break
                if nxt in by_id and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return by_id


def _check_claims(claims: list, by_id: dict, f: Findings, namespace: str | None = None) -> dict:
    seen: dict = {}
    for idx, c in enumerate(claims):
        where = c.get("id", f"claims[{idx}]") if isinstance(c, dict) else f"claims[{idx}]"
        if not isinstance(c, dict):
            f.add("errors", "claim.malformed", where, "claim record must be an object")
            continue
        for key in CLAIM_REQUIRED:
            if key not in c or c[key] in (None, "", []):
                if key == "numeric_quotation_allowed" and c.get(key) is False:
                    continue
                f.add("errors", "claim.missing_field", where, f"missing required field '{key}'")
        cid = c.get("id")
        if cid in seen:
            f.add("errors", "claim.duplicate_id", where, f"duplicate claim id {cid}")
        elif isinstance(cid, str):
            seen[cid] = c
            if not _id_ok(cid, "C", namespace):
                f.add("errors", "claim.bad_id", where, f"claim id '{cid}' must look like {namespace + ':' if namespace else ''}C01")
        types = c.get("claim_types") or []
        bad = [t for t in types if t not in CLAIM_TYPES]
        if bad:
            f.add("errors", "claim.bad_type", where, f"unknown claim type(s) {bad}")
        kind = c.get("support_kind", "primary")
        if kind not in SUPPORT_KINDS:
            f.add("errors", "claim.bad_support_kind", where, f"support_kind '{kind}' not in {sorted(SUPPORT_KINDS)}")
        strength = c.get("verification_strength")
        if strength not in STRENGTH:
            f.add("errors", "claim.bad_verification_strength", where, f"verification_strength '{strength}' not in {sorted(STRENGTH)}")
        if not isinstance(c.get("scope"), dict) or not c["scope"].get("text"):
            f.add("errors", "claim.missing_scope", where, "scope.text is required: a claim without its scope must not be quoted")
        if not _parse_day(c.get("last_reviewed")):
            f.add("errors", "claim.bad_date", where, f"last_reviewed '{c.get('last_reviewed')}' is not YYYY-MM-DD")
        ids = c.get("source_ids") or []
        missing = [s for s in ids if s not in by_id]
        for s in missing:
            f.add("errors", "claim.broken_source", where, f"source_ids references unknown source {s}")
        known = [by_id[s] for s in ids if s in by_id]
        if known and strength in STRENGTH:
            best = max(STRENGTH.get(s.get("verification_level"), 0) for s in known)
            if STRENGTH[strength] > best:
                f.add("errors", "claim.stronger_than_sources", where,
                      f"verification_strength '{strength}' exceeds the best supporting source level "
                      f"'{[s['verification_level'] for s in known if STRENGTH.get(s.get('verification_level'), 0) == best][0]}'")
        if c.get("numeric_quotation_allowed") is True and strength in STRENGTH and STRENGTH[strength] < 2:
            f.add("errors", "claim.numeric_without_reading", where, f"numeric quotation allowed at strength '{strength}': a number needs at least an abstract read")
        if kind == "primary" and set(types) & PRIMARY_TYPES and known:
            if not any(s.get("tier", 9) <= 2 for s in known):
                f.add("errors", "claim.no_primary_source", where,
                      "an experiment-practice claim needs at least one Tier 1-2 source; Tier 3 and below are preliminary or context only")
        if kind == "general_method" and "general_method" not in types:
            f.add("warnings", "claim.kind_type_mismatch", where, "support_kind general_method but claim_types lacks general_method")
        if kind == "primary" and "general_method" in types and len(types) == 1:
            f.add("warnings", "claim.kind_type_mismatch", where, "general_method claim should have support_kind 'general_method'")
        if strength in ("full-text",) and known and not c.get("limitations") and not (c.get("scope") or {}).get("text"):
            f.add("warnings", "claim.no_limitations", where, "full-text claim states no limitation")
    return seen


def _stale(sources: list, claims: list, f: Findings, today: date, stale_days: int) -> None:
    for s in sources:
        d = _parse_day(_read_date(s))
        if d and (today - d).days > stale_days:
            f.add("notes", "stale.source", s["id"], f"last verified {d} ({(today - d).days} days ago): re-check before quoting 'latest'; this does not mean the source is obsolete")
    for c in claims:
        d = _parse_day(c.get("last_reviewed"))
        if d and (today - d).days > stale_days:
            f.add("notes", "stale.claim", c["id"], f"last reviewed {d} ({(today - d).days} days ago): re-review; this does not mean the claim is wrong")


def check_ledger(sources: list, claims: list, today: date | None = None, stale_days: int = 365,
                 namespace: str | None = None) -> dict:
    """Validate parsed sources and claims. Returns a report dict with errors, warnings and notes."""
    today = today or date.today()
    f = Findings()
    if not isinstance(sources, list) or not isinstance(claims, list):
        f.add("errors", "ledger.malformed", "-", "sources and claims must each be a JSON array")
    else:
        by_id = _check_sources(sources, f, today, namespace)
        claims_by_id = _check_claims(claims, by_id, f, namespace)
        _stale(sources, claims, f, today, stale_days)
        cited = {s for c in claims if isinstance(c, dict) for s in c.get("source_ids") or []}
        for sid in by_id:
            if sid not in cited:
                f.add("notes", "source.uncited_by_claims", sid, "no claim cites this source (fine for navigation-only rows)")
        return {"status": "fail" if f.errors else ("warn" if f.warnings else "pass"),
                "errors": f.errors, "warnings": f.warnings, "notes": f.notes,
                "counts": {"sources": len(by_id), "claims": len(claims_by_id)}, "today": str(today)}
    return {"status": "fail", "errors": f.errors, "warnings": [], "notes": [], "counts": {}, "today": str(today)}


def load_ledger(sources_path: Path, claims_path: Path) -> tuple[list, list]:
    return (json.loads(Path(sources_path).read_text(encoding="utf-8")),
            json.loads(Path(claims_path).read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--sources", type=Path, required=True, help="profile evidence/sources.json")
    parser.add_argument("--claims", type=Path, required=True, help="profile evidence/claims.json")
    parser.add_argument("--namespace", default=None, help="require IDs of the form <namespace>:S01 / <namespace>:C01")
    parser.add_argument("--today", default=None, help="YYYY-MM-DD (default: system date); use it for reproducible runs")
    parser.add_argument("--stale-days", type=int, default=365, help="report verification older than this as a note")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args(argv)
    today = _parse_day(args.today) if args.today else date.today()
    if today is None:
        print(json.dumps({"status": "unreadable", "error": "--today must be YYYY-MM-DD"}))
        return 2
    try:
        sources, claims = load_ledger(args.sources, args.claims)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}, indent=2))
        return 2
    report = check_ledger(sources, claims, today, args.stale_days, args.namespace)
    print(json.dumps(report, indent=2))
    if report["status"] == "fail" or (args.strict and report["status"] == "warn"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assert that the ams-02 profile ledger preserves the legacy AMS ledger record by record (AC08).

Compares profiles/experiments/ams-02/evidence/{sources,claims}.json with the legacy
ams-analysis/data/{sources,claims}.json at agentic-ai-skills@3e995a4 ($LEGACY_REPO, default
<repo>/.legacy/agentic-ai-skills). Every legacy field must be identical after mapping, except the
record-level changes declared in evidence/legacy_id_map.json:
  id/reference namespacing, access_date -> verification_date, added formal_status and evidence_status.

Usage: python3 tools/check_ams_ledger_preservation.py [--legacy PATH]
Exit 0 preserved, 1 differences, 3 skipped (legacy checkout not available). Output: JSON.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "profiles" / "experiments" / "ams-02" / "evidence"
PIN = "3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9"
ADDED = {"legacy_id", "formal_status", "evidence_status", "verification_date"}


def legacy_dir(args) -> Path:
    if "--legacy" in args:
        return Path(args[args.index("--legacy") + 1])
    return Path(os.environ.get("LEGACY_REPO", ROOT.parents[1] / ".legacy" / "agentic-ai-skills"))


def compare(old: list, new: list, kind: str, idmap: dict, diffs: list) -> None:
    by_legacy = {r.get("legacy_id"): r for r in new}
    if len(new) != len(old):
        diffs.append(f"{kind}: {len(old)} legacy records, {len(new)} migrated")
    for o in old:
        n = by_legacy.get(o["id"])
        if n is None:
            diffs.append(f"{kind} {o['id']}: missing in profile ledger")
            continue
        if n["id"] != idmap.get(o["id"]):
            diffs.append(f"{kind} {o['id']}: id {n['id']} does not match legacy_id_map")
        for key, val in o.items():
            if key == "id":
                continue
            if key == "access_date":
                if n.get("verification_date") != (val or "unknown"):
                    diffs.append(f"{kind} {o['id']}: verification_date {n.get('verification_date')!r} != access_date {val!r}")
                continue
            want = [idmap[x] for x in val] if key in ("source_ids", "supersedes", "superseded_by") else val
            if n.get(key) != want:
                diffs.append(f"{kind} {o['id']}: field '{key}' changed")
        extra = set(n) - set(o) - ADDED
        for key in sorted(extra):
            diffs.append(f"{kind} {o['id']}: undeclared new field '{key}'")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    data = legacy_dir(args) / "ams-analysis" / "data"
    if not (data / "sources.json").is_file():
        print(json.dumps({"status": "skip", "reason": f"legacy ledger not found at {data}; run tasks/hep-research/scripts/fetch_legacy.sh"}))
        return 3
    old_s = json.loads((data / "sources.json").read_text(encoding="utf-8"))
    old_c = json.loads((data / "claims.json").read_text(encoding="utf-8"))
    new_s = json.loads((EVID / "sources.json").read_text(encoding="utf-8"))
    new_c = json.loads((EVID / "claims.json").read_text(encoding="utf-8"))
    idmap = json.loads((EVID / "legacy_id_map.json").read_text(encoding="utf-8"))["ids"]
    diffs: list[str] = []
    compare(old_s, new_s, "source", idmap, diffs)
    compare(old_c, new_c, "claim", idmap, diffs)
    out = {"status": "pass" if not diffs else "fail", "legacy": str(data), "pinned_commit": PIN,
           "counts": {"legacy_sources": len(old_s), "legacy_claims": len(old_c), "sources": len(new_s), "claims": len(new_c)},
           "differences": diffs}
    print(json.dumps(out, indent=1))
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())

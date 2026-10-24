#!/usr/bin/env python3
"""Sci-fix ledger report (docs/evidence/sci-fixes.json): what the ledger's own records say is missing. Read-only; it
blocks nothing and changes no grade (the ledger records evidence, it never authorizes anything).

Sections:
  below_minimum         entries whose C or D grade is below the minimum for their severity (docs/maintenance.md)
  transcription         C3 entries none of whose independence records takes its expected value from somewhere other
                        than a formula transcribed into the repository (expected_from transcribed-formula only;
                        maintainer decision 2026-10-22, reported before it is enforced)
  unsigned_s1           S1 entries without a per-entry human sign-off (review: {by, date, scope})
  s3_gaps               documentation fixes that state gaps (below the S3 minimum: a located external source and a
                        second source)
Output: JSON with "status": "passed". Exit 0; 2 when the ledger is unreadable.
Usage: python3 <plugin root>/tools/scifix_ledger.py report
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "evidence" / "sci-fixes.json"
C = ("C0", "C1", "C2", "C3", "C4")
D = ("D0", "D1", "D2", "D3")
MINIMUM = {"S1": ("C3", "D2"), "S2": ("C2", "D2"), "S4": ("C1", "D2")}
EXPECTED_FROM = ("printed", "third-party-definition", "exhaustive", "general-result", "person", "transcribed-formula")


def transcription_only(entry: dict) -> bool:
    """A C3 entry whose every independence record computes its expected value from a transcribed formula."""
    records = entry.get("independence") or []
    return entry.get("correctness") == "C3" and bool(records) and \
        all(r.get("expected_from") == "transcribed-formula" for r in records)


def s3_meets_minimum(doc_fix: dict) -> bool:
    """The current S3 rule: a located external source and a second, different source."""
    sources = doc_fix.get("sources") or []
    located = [s for s in sources if s.get("kind") == "external" and s.get("locator")]
    return bool(located) and len({s.get("citation") for s in sources}) >= 2


def report(ledger: dict) -> dict:
    fixes = ledger["fixes"]
    below = []
    for f in fixes:
        need = MINIMUM.get(f["severity"])
        if need and (C.index(f["correctness"]) < C.index(need[0]) or D.index(f["discrimination"]) < D.index(need[1])):
            below.append({"id": f["id"], "severity": f["severity"], "grade": f["correctness"] + f["discrimination"],
                          "minimum": "".join(need)})
    return {"status": "passed", "below_minimum": below,
            "transcription": [f["id"] for f in fixes if transcription_only(f)],
            "unsigned_s1": [f["id"] for f in fixes if f["severity"] == "S1" and not f.get("review")],
            "s3_gaps": [x["id"] for x in ledger.get("documentation_fixes", [])
                        if x.get("severity") == "S3" and not s3_meets_minimum(x)],
            "note": "a report only: it changes no grade and blocks nothing"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["report"])
    ap.parse_args(argv)
    try:
        out, code = report(json.loads(LEDGER.read_text(encoding="utf-8"))), 0
    except (OSError, ValueError, KeyError) as exc:
        out, code = {"status": "rejected", "error": str(exc)}, 2
    print(json.dumps(out, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())

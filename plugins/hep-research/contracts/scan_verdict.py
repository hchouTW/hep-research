#!/usr/bin/env python3
"""Interface to the custodian's scan service (task P6.1; protected-data-architecture.md §6.5): scan submissions, the
agent-visible verdict, and the per-analysis query budget. The service itself (which holds the sealed values and runs
core.blinding.scan_paths) lives outside the plugin; this module fixes what crosses the boundary.

Response policy:
  - agent-visible is only a verdict (contracts/schemas/scan_verdict.json): status pass | fail | incomplete |
    refused-budget | refused, and the budget state available | exhausted. verdict() builds it from the service's own
    scan report and drops everything else; check_verdict() refuses any other field (no value, token, location, file of
    a hit, or count);
  - each answer is a group test over every candidate value in the outputs (printing 0..20 asks about 21 values at once,
    and a silent no-match tells as much as a match), so the budget is counted in candidate values tested, per analysis,
    across sessions, subagents and resubmissions, and every submission is charged whether it passes or fails;
  - a submission that would exceed the budget is not scanned: refused-budget; after that the budget is exhausted.

count_candidates(text) counts the numeric tokens of a text at the renderings the scanner reads (core.blinding NUMBER and
grouped thousands); make_submission() digests the outputs and counts them. charge(budget, submission, contents) is the
service's budget arithmetic, on its own recount of the received bytes, on a record {"analysis", "limit", "consumed", "charges": [{submission_id, candidate_values}]}: it
returns the new record and whether the scan may run. Nothing here scans or authorizes anything.

Usage: python3 contracts/scan_verdict.py submission --analysis A --release R --session S [--id ID] OUTPUT ...
       python3 contracts/scan_verdict.py check-verdict VERDICT.json
Exit 0 ok, 1 refused (a verdict that is not one), 2 unreadable input. Output: JSON.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
import uuid
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import validate  # noqa: E402
from core.blinding.blinding import GROUPED, NUMBER  # noqa: E402

STATUSES = ("pass", "fail", "incomplete", "refused-budget", "refused")


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_candidates(text: str) -> int:
    """Numeric tokens a scan compares with the sealed values: every plain number and every grouped number (1,234.5);
    a grouped number also counts its parts, so the count is an upper bound (the budget errs on the safe side)."""
    return len(NUMBER.findall(text)) + len(GROUPED.findall(text))


def make_submission(outputs, analysis: str, release_id: str, session: str, submission_id: str | None = None,
                    time: str | None = None) -> dict:
    entries, candidates = [], 0
    for p in outputs:
        data = Path(p).read_bytes()
        entries.append({"ref": str(p), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
        candidates += count_candidates(data.decode("utf-8", "replace"))
    sub = {"submission_version": "1.0.0", "submission_id": submission_id or uuid.uuid4().hex, "analysis": analysis,
           "release_id": release_id, "session": session, "outputs": entries, "candidate_values": candidates,
           "time": time or _now()}
    rep = validate(sub, "scan_submission.json")
    if not rep.ok:
        raise ValueError("; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    return sub


def recount(submission: dict, contents: dict) -> int | None:
    """The service's own count of candidate values from the received bytes {ref: bytes}; None when an output is
    missing or its bytes differ from the submitted SHA-256 (the submitter's own count is never trusted)."""
    total = 0
    for o in submission.get("outputs") or []:
        data = contents.get(o.get("ref")) if isinstance(o, dict) else None
        if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != o.get("sha256"):
            return None
        total += count_candidates(data.decode("utf-8", "replace"))
    return total


def charge(budget: dict, submission: dict, contents: dict) -> tuple[dict, bool]:
    """(new budget record, scan allowed). The charge is the service's recount from the received bytes (contents
    {ref: bytes}), never less than the submission states. Refused without charging: another analysis, outputs that do
    not match the submission, a budget already exhausted, or a submission that would exceed the limit (which marks the
    budget exhausted for good). A charged submission is charged whatever its result."""
    if not isinstance(budget, dict) or not isinstance(budget.get("limit"), int) or budget["limit"] < 0:
        raise ValueError("a budget record needs an integer limit >= 0")
    if submission.get("analysis") != budget.get("analysis") or budget.get("exhausted"):
        return dict(budget), False
    n = recount(submission, contents)
    declared = submission.get("candidate_values")
    if n is None or not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        return dict(budget), False
    n = max(n, declared)
    consumed = int(budget.get("consumed", 0))
    if consumed + n > budget["limit"]:
        return dict(budget, exhausted=True), False
    new = dict(budget, consumed=consumed + n,
               charges=list(budget.get("charges", [])) + [{"submission_id": submission["submission_id"], "candidate_values": n}])
    new["exhausted"] = new["consumed"] >= new["limit"]
    return new, True


def verdict(submission: dict, report: dict | None, budget: dict, allowed: bool, time: str | None = None) -> dict:
    """The agent-visible verdict for one submission from the service's scan report (core.blinding.scan_paths) or, when
    the budget refused it, without one. Only the status and the budget state are kept."""
    if not allowed:
        status = "refused-budget"
    elif not isinstance(report, dict) or report.get("status") not in ("pass", "fail", "incomplete"):
        status = "refused"
    else:
        status = report["status"]
    out = {"verdict_version": "1.0.0", "submission_id": submission["submission_id"], "status": status,
           "budget": "exhausted" if budget.get("exhausted") else "available", "time": time or _now()}
    return out


def check_verdict(doc) -> list[str]:
    """Problems with a verdict (empty when it is one): any extra field could carry secret-dependent detail."""
    rep = validate(doc, "scan_verdict.json")
    return [f"{f.path}: {f.code}" for f in rep.errors]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("submission")
    p.add_argument("outputs", nargs="+", type=Path)
    p.add_argument("--analysis", required=True)
    p.add_argument("--release", required=True)
    p.add_argument("--session", required=True)
    p.add_argument("--id")
    p = sub.add_parser("check-verdict")
    p.add_argument("verdict", type=Path)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        if args.cmd == "submission":
            print(json.dumps(make_submission(args.outputs, args.analysis, args.release, args.session, args.id), indent=1))
            return 0
        problems = check_verdict(json.loads(args.verdict.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    print(json.dumps({"status": "verdict" if not problems else "refused", "problems": problems}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

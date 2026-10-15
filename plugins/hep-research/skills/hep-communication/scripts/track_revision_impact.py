#!/usr/bin/env python3
"""Compare a baseline and a revised communication record and list the impact of every change.

Usage: python3 track_revision_impact.py BEFORE.json AFTER.json --project-root ROOT [--format json|markdown] [--out REPORT]

The baseline is read once and never modified; it is compared through its pinned identities (input digests, evidence
fingerprints, claim digests). The revised record is resolved inside --project-root. Each changed claim gets an impact
entry: kind (analysis-rerun, source-change, reference-move, reassessment, content-edit, status-change, added,
removed), the evidence identities before and after, the value change at the evidence locator when both pinned files
are available (otherwise the content comparison is incomplete and only the identity-level impact is reported), the
state of every recorded occurrence (stale, edited, unchanged), whether the assessment is reopened, and the required
actions. Verified revision items that depend on a changed claim are reopened; a verified item without completion
evidence is an error; an edited item is not evidence that the edits happened. Exit codes: 0 no change needing work;
1 a confirmed inconsistency; 2 invalid invocation or unreadable input; 3 work is open (a reopened assessment or item,
an unresolved new or historical source, unmapped coverage). Read-only; the report is a separate output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from communication_lib import report as R  # noqa: E402
from communication_lib.revisions import diff_communication  # noqa: E402

CHECKS = ("schema", "identities", "occurrences", "revision-items")


def main(argv=None) -> int:
    def add_args(ap):
        ap.add_argument("after", type=Path, nargs="?", help="the revised communication record")
        ap.usage = "track_revision_impact.py BEFORE.json AFTER.json --project-root ROOT [--format json|markdown] [--out REPORT]"

    before_holder = {}

    def build(args, record, ctx):
        # the positional `record` is BEFORE (read by the driver, never written); `after` is resolved here
        if args.after is None:
            raise ValueError("BEFORE.json and AFTER.json are both required")
        try:
            after = json.loads(args.after.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read {args.after}: {exc}") from exc
        if not isinstance(after, dict):
            raise ValueError(f"{args.after} is not a JSON object")
        from contracts.communication_project import resolve_context
        actx = resolve_context(args.after, args.project_root)
        if any(f["code"] in ("resolution.unreadable", "resolution.bad_root") or (f["code"] == "resolution.outside_root" and f["path"] == "$")
               for f in actx["findings"]):
            raise ValueError("; ".join(f["message"] for f in actx["findings"] if f["path"] == "$"))
        before_holder["ctx"] = actx
        rep = diff_communication(record, after, actx)
        rep["scope"].update(before=str(args.record), after=str(args.after), project_root=str(args.project_root),
                            after_sha256=actx.get("artifact_sha256"))
        rep["inputs"] = {"after_sha256": actx.get("artifact_sha256")}
        return rep

    def protected(args, ctx):
        return [args.record, args.after] + R.protected_paths(args.after, before_holder.get("ctx"))
    return R.run("track_revision_impact", __doc__, argv, build, add_args=add_args, all_checks=CHECKS,
                 needs_context=lambda args: False, extra_protected=protected)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Audit the claims of a communication record: recorded assessments, source read coverage, advisory wording, numbers
and units, reporting completeness; emit a claim matrix, draft-ready facts and handoffs.

Usage: python3 audit_claims.py RECORD.json --project-root ROOT [--policy POLICY.json] [--format json|markdown] [--out REPORT]

The policy (default: the skill's assets/reporting-policies.json) lists per result type the fields a report needs and
the method conditions under which they apply; it checks supplied metadata and never chooses a method. Deterministic
checks establish the record's consistency, not scientific truth: a verdict is its assessor's recorded judgment,
wording findings are advisory, and a missing quantity is routed to the producing skill as a handoff, never computed
here. Exit codes: 0 no confirmed inconsistency and no unresolved required check; 1 a confirmed inconsistency (an
unsupported verdict, a display value outside its declared rounding, a stale assessment marked current); 2 invalid
invocation, unreadable record or policy; 3 unresolved (an unassessed claim, a cited passage not read, a missing
reporting field). Read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from communication_lib import report as R  # noqa: E402
from communication_lib.claims import audit_claims  # noqa: E402
from communication_lib.reporting import load_policy  # noqa: E402

DEFAULT_POLICY = HERE.parent / "assets" / "reporting-policies.json"
CHECKS = ("schema", "assessments", "sources", "wording", "numbers", "reporting")


def main(argv=None) -> int:
    def add_args(ap):
        ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help=f"reporting policy JSON (default: {DEFAULT_POLICY})")

    def build(args, record, ctx):
        try:
            policy = load_policy(args.policy)
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read policy {args.policy}: {exc}") from exc
        rep = audit_claims(record, ctx, policy)
        rep["scope"]["policy"]["path"] = str(args.policy)
        rep["scope"]["project_root"] = str(args.project_root)
        return rep
    return R.run("audit_claims", __doc__, argv, build, add_args=add_args, all_checks=CHECKS)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Audit the claims of a communication record: recorded assessments, source read coverage, advisory wording, numbers
and units, reporting completeness; emit a claim matrix, draft-ready facts and handoffs.

Usage: python3 audit_claims.py RECORD.json --project-root ROOT [--policy POLICY.json] [--format json|markdown] [--out REPORT]
       python3 audit_claims.py --compare A.txt B.txt   (two versions of one text, e.g. the English and Chinese drafts:
       exit 1 when numbers, uncertainties, status words or the claim-strength level differ; Com7)

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
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
for _p in (str(PLUGIN), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contracts import audit_report as R  # noqa: E402
from communication_lib.claims import audit_claims  # noqa: E402
from communication_lib.reporting import load_policy  # noqa: E402

DEFAULT_POLICY = HERE.parent / "assets" / "reporting-policies.json"
CHECKS = ("schema", "assessments", "sources", "wording", "numbers", "reporting")


def compare_main(argv) -> int:
    """--compare A B: numbers, status words and claim-strength levels of two versions (exit 1 when they differ)."""
    import json
    from communication_lib.claims import compare_versions
    paths = argv[argv.index("--compare") + 1:argv.index("--compare") + 3]
    if len(paths) != 2:
        print(json.dumps({"tool": "audit_claims", "status": "input-error", "error": "--compare needs two files"}))
        return 2
    try:
        texts = [Path(p).read_text(encoding="utf-8") for p in paths]
    except OSError as exc:
        print(json.dumps({"tool": "audit_claims", "status": "input-error", "error": str(exc)}))
        return 2
    rep = compare_versions(*texts)
    rep.update(tool="audit_claims", mode="compare", files=paths, status="fail" if rep["differences"] else "pass")
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 1 if rep["differences"] else 0


def main(argv=None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--compare" in args_list:
        return compare_main(args_list)

    def add_args(ap):
        ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help=f"reporting policy JSON (default: {DEFAULT_POLICY})")

    def build(args, record, ctx):
        try:
            policy = load_policy(args.policy)
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read policy {args.policy}: {exc}") from exc
        rep = audit_claims(record, ctx, policy)
        rep["scope"]["policy"]["path"] = ("<plugin root>/skills/hep-writing/assets/reporting-policies.json"
                                          if args.policy.resolve() == DEFAULT_POLICY.resolve() else str(args.policy))
        rep["scope"]["project_root"] = str(args.project_root)
        return rep
    return R.run("audit_claims", __doc__, argv, build, add_args=add_args, all_checks=CHECKS)


if __name__ == "__main__":
    sys.exit(main())

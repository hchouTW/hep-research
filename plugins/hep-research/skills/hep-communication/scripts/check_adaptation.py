#!/usr/bin/env python3
"""Check a derived draft against its record through a companion manifest, or draft reviewer responses from the record.

Usage: python3 check_adaptation.py RECORD.json --project-root ROOT --manifest MANIFEST.json --draft DRAFT.md [--format json|markdown] [--out REPORT]
       python3 check_adaptation.py RECORD.json --project-root ROOT --responses [--format json|markdown] [--out REPORT]

Manifest mode (template: assets/paper/adaptation-manifest-template.json): every statement in the manifest must appear
in the draft and carry a claim id; its numbers must match the record (source value, uncertainties, display values);
the claim's status labels and the brief's indispensable limitations must survive compression; a universal wording whose
claim scope is narrower is an error; a missing semantic review is unresolved (keyword overlap is not a semantic check).
Responses mode: an action table linking each reviewer comment to claims, revision items and locators, and response
wording from the recorded state: past tense only for a verified change with completion evidence; pending work stays
explicit; a reasoned decline is valid. Exit codes: 0 consistent; 1 a confirmed inconsistency; 2 invalid invocation or
unreadable input; 3 unresolved. Read-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from communication_lib import report as R  # noqa: E402
from communication_lib.adaptation import check_adaptation, draft_responses  # noqa: E402

CHECKS = ("statements", "numbers", "status-labels", "limitations", "scope", "dispositions")


def main(argv=None) -> int:
    def add_args(ap):
        ap.add_argument("--manifest", type=Path, help="companion manifest of the derived draft")
        ap.add_argument("--draft", type=Path, help="the derived draft text (Markdown or plain text)")
        ap.add_argument("--responses", action="store_true", help="draft reviewer responses from the record's reviewer and revision items")

    def build(args, record, ctx):
        if args.responses and (args.manifest or args.draft):
            raise ValueError("use either --responses or --manifest with --draft")
        if args.responses:
            rep = draft_responses(record, ctx)
        else:
            if not (args.manifest and args.draft):
                raise ValueError("--manifest MANIFEST.json and --draft DRAFT.md are both required (or --responses)")
            try:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                draft = args.draft.read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                raise ValueError(f"cannot read the manifest or draft: {exc}") from exc
            if not isinstance(manifest, dict):
                raise ValueError(f"{args.manifest} is not a JSON object")
            rep = check_adaptation(record, ctx, manifest, draft)
            rep["scope"].update(manifest=str(args.manifest), draft=str(args.draft))
        rep["scope"]["project_root"] = str(args.project_root)
        return rep

    def protected(args, ctx):
        return [p for p in (args.manifest, args.draft) if p]
    return R.run("check_adaptation", __doc__, argv, build, add_args=add_args, all_checks=CHECKS, extra_protected=protected)


if __name__ == "__main__":
    sys.exit(main())

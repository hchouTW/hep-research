#!/usr/bin/env python3
"""Classify changes to calibrations, selections or corrections: legitimate update or outcome-driven tuning.

Purpose: analyses change while they run, and most changes are legitimate (a new calibration from a control sample,
a fixed bug). The failure mode is tuning toward a desired result after looking at the signal region or the outcome.
This script does not refuse changes; it accepts those with independent provenance, flags those that are outcome
driven, and asks for provenance when it is missing.

Input JSON: {"changes": [{"id", "parameter", "old", "new", "motivation",
              "evidence": {"control_sample": str|null, "evidence_ids": [...], "independent_of_signal_region": bool},
              "looked_at": ["control-region data", "simulation", "signal-region data", "unblinded result", ...],
              "after_unblinding": bool}]}
Decision per change:
  accept            independent provenance (control sample or evidence ids, independent of the signal region) and
                    no look at signal-region data or results before the change
  flag              signal-region data, an unblinded result or the fitted outcome motivated or preceded the change:
                    keep it only as a documented, separately reported variation with its effect on the result
  needs-provenance  no signal-region exposure, but no independent evidence recorded yet
Output: JSON report. Exit codes: 0 nothing flagged, 1 any change flagged, 2 bad input.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/review_analysis_change.py changes.json
Standard library only.
"""
from __future__ import annotations

import json
import re
import sys

OUTCOME_SEEN = re.compile(r"signal[- ]region data|unblinded|observed result|fit result|outcome|significance|p-value", re.I)
OUTCOME_MOTIVE = re.compile(r"(to|so that).{0,40}(agree|match|improve|increase|reduce|remove).{0,40}"
                            r"(excess|deficit|significance|signal(?![- ]to[- ]background)|result|limit|tension)|(excess|tension|significance)", re.I)


def review(change: dict) -> dict:
    ev = change.get("evidence") or {}
    seen = [x for x in change.get("looked_at", []) if OUTCOME_SEEN.search(str(x))]
    motive = bool(OUTCOME_MOTIVE.search(str(change.get("motivation", ""))))
    independent = bool((ev.get("control_sample") or ev.get("evidence_ids")) and ev.get("independent_of_signal_region"))
    reasons = []
    if seen:
        reasons.append(f"looked at {seen} before the change")
    if motive:
        reasons.append("motivation refers to the outcome")
    if change.get("after_unblinding") and not independent:
        reasons.append("made after unblinding without independent evidence")
    if reasons:
        decision, action = "flag", ("report as a separate, documented variation with its effect on the result; keep the "
                                    "pre-change result as the reference unless independent evidence supports the change")
    elif independent:
        decision, action = "accept", "record provenance (control sample or evidence ids) with the change"
    else:
        decision, action = "needs-provenance", "record the control sample or evidence that motivated the change"
    return {"id": change.get("id"), "parameter": change.get("parameter"), "decision": decision, "reasons": reasons, "action": action}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        with open(args[0], encoding="utf-8") as fh:
            changes = json.load(fh)["changes"]
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    if not isinstance(changes, list) or not all(isinstance(c, dict) for c in changes):
        print(json.dumps({"error": "'changes' must be a list of objects"}))
        return 2
    rows = [review(c) for c in changes]
    print(json.dumps({"changes": rows, "flagged": sum(r["decision"] == "flag" for r in rows)}, indent=1))
    return 1 if any(r["decision"] == "flag" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

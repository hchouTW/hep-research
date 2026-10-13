#!/usr/bin/env python3
"""Classify changes to calibrations, selections or corrections: legitimate update or outcome-driven tuning.

Purpose: analyses change while they run, and most changes are legitimate (a new calibration from a control sample,
a fixed bug). The failure mode is tuning toward a desired result after looking at the signal region or the outcome.
This script does not refuse changes; it accepts those with independent provenance, flags those that are outcome
driven, and asks for provenance when it is missing.

Input JSON: {"changes": [{"id", "parameter", "old", "new", "motivation",
              "evidence": {"control_sample": str|null, "evidence_ids": [...], "independent_of_signal_region": bool},
              "looked_at": ["control-region data", "simulation", "signal-region data", "unblinded result", ...],
              "data_exposure": {"state": "unexposed"|"exposed"|"unknown"|"incomplete",
                                "basis": "structured-record", "record_ref": str},       optional
              "after_unblinding": bool}]}
Data exposure (F05, K06): each row reports {"state", "basis"} as in the envelope's data_exposure. A structured record
(basis structured-record) is used as given; looked_at is legacy free text (basis legacy-text). A looked_at entry
that names signal-region data or a result makes the change exposed; a non-empty list whose every entry is one kind
of control-region, sideband, simulation, calibration or validation data, matching a closed grammar as a whole (for
example "control-region data", "simulation", "sideband (low mass)"), makes it unexposed; any other wording ("full
data", "search region", "simulation and data"), an empty list, a looked_at that is not a list, or none at all (basis
none) makes the exposure unknown, never unexposed. Give one entry per kind of data. With both, the more exposed wins.
Decision per change:
  accept            independent provenance (control sample or evidence ids, independent of the signal region) and
                    data exposure 'unexposed'
  flag              signal-region data, an unblinded result or the fitted outcome motivated or preceded the change:
                    keep it only as a documented, separately reported variation with its effect on the result
  needs-provenance  not exposed, but no independent evidence recorded yet
  exposure-unknown  not flagged, but what was looked at is unknown or incomplete: record it before accepting
This review is advisory: it reads what the caller records and cannot see what was actually looked at.
Output: JSON report with status (--status, default unvalidated; one of the core artifact_statuses). Exit codes:
0 nothing flagged, 1 any change flagged, 2 bad input (including a malformed data_exposure record, NaN or inf, or
malformed JSON; the error is also one line on stderr).
Run: python3 <plugin root>/skills/hep-analysis/scripts/review_analysis_change.py changes.json [--status S]
Standard library only.
"""
from __future__ import annotations

import json
import re
import sys

OUTCOME_SEEN = re.compile(r"signal[- ]region data|unblinded|observed result|fit result|outcome|significance|p-value", re.I)
OUTCOME_MOTIVE = re.compile(r"(to|so that).{0,40}(agree|match|improve|increase|reduce|remove).{0,40}"
                            r"(excess|deficit|significance|signal(?![- ]to[- ]background)|result|limit|tension)|(excess|tension|significance)", re.I)
# A legacy looked_at entry is read as unexposed only if the whole entry (lower case, hyphens as spaces) matches this
# closed grammar: one kind of data a blinded analysis may see. Simulation entries never mention data; any other
# wording ("data-MC distributions", "test sample", "full data", "search region", "and", "vs") is unknown (K06).
_SHOWN = r"( (data|events|distributions|plots))?( only)?"
CONTROL_ONLY = re.compile(
    r"^(?:(control|validation) (region|regions|sample|samples)" + _SHOWN +
    r"|sidebands?( \((low|high) mass\))?" + _SHOWN +
    r"|(simulation|simulated (samples?|events)|monte carlo|mc)( (samples?|events|distributions|plots))?( only)?"
    r"|test beam( data)?"
    r"|(cosmic ray )?calibration( (data|samples?|runs?))?( only)?)$")
EXPOSURE_STATES = ("unexposed", "exposed", "unknown", "incomplete")
RANK = {"unexposed": 0, "unknown": 1, "incomplete": 1, "exposed": 2}
STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


class BadExposure(ValueError):
    pass


def _reject_constant(token):
    raise ValueError(f"non-finite number {token} in the input")


def _fail(message: str) -> int:
    print(json.dumps({"error": message}))
    print(f"review_analysis_change.py: error: {message}", file=sys.stderr)
    return 2


def control_only(entry) -> bool:
    """True only for a legacy entry the CONTROL_ONLY grammar matches whole, e.g. 'control-region data'."""
    if not isinstance(entry, str):
        return False
    return bool(CONTROL_ONLY.match(" ".join(entry.lower().replace("-", " ").split())))


def exposure(change: dict) -> tuple[dict, list]:
    """({"state", "basis"[, "record_ref"]}, outcome-revealing looked_at entries) for one change."""
    rec = change.get("data_exposure")
    structured = None
    if rec is not None:
        if (not isinstance(rec, dict) or rec.get("state") not in EXPOSURE_STATES or rec.get("basis") != "structured-record"
                or set(rec) - {"state", "basis", "record_ref"} or not isinstance(rec.get("record_ref", ""), str)):
            raise BadExposure(f"change {change.get('id')!r}: data_exposure must be {{'state': one of {list(EXPOSURE_STATES)}, "
                              "'basis': 'structured-record', optional 'record_ref'}")
        structured = dict(rec)
    raw = change.get("looked_at")
    seen: list = []
    if raw is None:
        legacy = None
    elif isinstance(raw, list):
        seen = [x for x in raw if OUTCOME_SEEN.search(str(x))]
        known = bool(raw) and all(control_only(x) for x in raw)
        legacy = {"state": "exposed" if seen else "unexposed" if known else "unknown", "basis": "legacy-text"}
    else:  # a string is never read character by character as an empty look
        seen = [raw] if OUTCOME_SEEN.search(str(raw)) else []
        legacy = {"state": "exposed" if seen else "unknown", "basis": "legacy-text"}
    if structured is None:
        return (legacy or {"state": "unknown", "basis": "none"}), seen
    if legacy is not None and RANK[legacy["state"]] > RANK[structured["state"]]:
        structured["state"] = legacy["state"]
    return structured, seen


def review(change: dict) -> dict:
    ev = change.get("evidence") or {}
    data_exposure, seen = exposure(change)
    motive = bool(OUTCOME_MOTIVE.search(str(change.get("motivation", ""))))
    independent = bool((ev.get("control_sample") or ev.get("evidence_ids")) and ev.get("independent_of_signal_region"))
    reasons = []
    if seen:
        reasons.append(f"looked at {seen} before the change")
    elif data_exposure["state"] == "exposed":
        reasons.append("the data exposure record says data were seen before the change")
    if motive:
        reasons.append("motivation refers to the outcome")
    if change.get("after_unblinding") and not independent:
        reasons.append("made after unblinding without independent evidence")
    if reasons:
        decision, action = "flag", ("report as a separate, documented variation with its effect on the result; keep the "
                                    "pre-change result as the reference unless independent evidence supports the change")
    elif data_exposure["state"] != "unexposed":
        decision, action = "exposure-unknown", ("record what was looked at before the change (a looked_at list or a "
                                                "structured data_exposure record); unknown exposure is never treated as unexposed")
    elif independent:
        decision, action = "accept", "record provenance (control sample or evidence ids) with the change"
    else:
        decision, action = "needs-provenance", "record the control sample or evidence that motivated the change"
    return {"id": change.get("id"), "parameter": change.get("parameter"), "decision": decision, "reasons": reasons, "action": action,
            "data_exposure": data_exposure}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    status = "unvalidated"
    if "--status" in args:
        k = args.index("--status")
        if k + 1 >= len(args) or args[k + 1] not in STATUSES:
            return _fail(f"--status needs one of {', '.join(STATUSES)}")
        status = args[k + 1]
        del args[k:k + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        with open(args[0], encoding="utf-8") as fh:
            changes = json.load(fh, parse_constant=_reject_constant)["changes"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _fail(str(exc))
    if not isinstance(changes, list) or not all(isinstance(c, dict) for c in changes):
        return _fail("'changes' must be a list of objects")
    try:
        rows = [review(c) for c in changes]
    except BadExposure as exc:
        return _fail(str(exc))
    print(json.dumps({"status": status, "changes": rows, "flagged": sum(r["decision"] == "flag" for r in rows),
                      "exposure_unknown": sum(r["decision"] == "exposure-unknown" for r in rows)}, indent=1))
    return 1 if any(r["decision"] == "flag" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

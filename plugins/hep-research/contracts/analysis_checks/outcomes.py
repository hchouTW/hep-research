"""Aggregation of obligation outcomes (v6.3 C10): five states, coverage, consistency, declaration flags.

State and severity are separate, and the absence of a finding is not an evaluation: an obligation whose rule did not
run is unverified (check.rule_not_run), never satisfied. Coverage is complete when every required obligation is
satisfied, violated or not_applicable, expressed as completed over all, never as a pass percentage. Consistency is
inconsistent when a violation is established on valid inputs, consistent only when every obligation is satisfied or
not_applicable on valid inputs, and undetermined otherwise. The formal-use view treats a declaration-based satisfied
obligation as unverified: declarations an agent wrote support diagnostics only (A10, C12).

Legacy mapping (C10 table): legacy findings keep their own field; map_legacy says which state each would mean."""
from __future__ import annotations

STATES = ("satisfied", "violated", "not_applicable", "unverified", "unsupported")
DONE = ("satisfied", "violated", "not_applicable")


def summarize(outcomes: list[dict], input_valid: bool) -> dict:
    required = [o for o in outcomes if o.get("required", True)]
    done = sum(o["state"] in DONE for o in required)
    counts = {s: sum(o["state"] == s for o in required) for s in STATES}
    coverage = {"value": "complete" if input_valid and done == len(required) else "partial",
                "completed": done, "total": len(required)}
    if not input_valid:
        consistency = "undetermined"
    elif counts["violated"]:
        consistency = "inconsistent"
    elif all(o["state"] in ("satisfied", "not_applicable") for o in required):
        consistency = "consistent"
    else:
        consistency = "undetermined"
    return {"coverage": coverage, "consistency": consistency, "counts": counts}


def formal_view(outcomes: list[dict], input_valid: bool) -> dict:
    """The summary when declaration-based outcomes count as unverified (formal use without an accepted review)."""
    demoted = [dict(o, state="unverified") if o["state"] == "satisfied" and o.get("declaration_based") else o
               for o in outcomes]
    out = summarize(demoted, input_valid)
    out["declaration_based_as"] = "unverified"
    out["note"] = ("declaration-based outcomes count for formal use only through an accepted attestation review that "
                   "lists this report as evidence; an agent is never the reviewer")
    return out


LEGACY_UNVERIFIED = {"semantics.repeat_undetermined", "semantics.repeat_distinct_instance",
                     "semantics.input_effects_unverified", "semantics.input_effects_uncorroborated",
                     "semantics.upstream_unmapped", "semantics.upstream_unrecorded"}
LEGACY_UNSUPPORTED = {"semantics.unknown_operator", "semantics.table_missing", "semantics.unknown_estimand"}


def map_legacy(finding: dict) -> str:
    """The state a legacy finding would mean in the new report (C10): evidence-backed errors are violated, inability
    to rule out and missing keys are unverified, what cannot be compared is unsupported, warnings are unverified."""
    code = finding.get("code", "")
    if code in LEGACY_UNSUPPORTED:
        return "unsupported"
    if code in LEGACY_UNVERIFIED or finding.get("severity") != "error":
        return "unverified"
    return "violated"

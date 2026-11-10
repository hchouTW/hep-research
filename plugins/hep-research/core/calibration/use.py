"""Evidence grades, flags and uses of calibration results (Part B section 10.2, governed by Appendix C; owner
calib_use.py).

assign() is table C.2 (own grade, rules 1, 0, 2, 3a-3f, 4, first match), defined only for resolved inputs (I25).
effective() is table C.3: the pending step, the cap by central upstreams and by grade-limiting flags, and the uses.
allowed_uses() is the use matrix; variation_upstream_admissible() the eligibility of a variation upstream.
outcome_determined() is the "outcome already determined" lookup of section 10.2 rule 0 (D63), evaluated with C.2 then
C.3 for every combination of the possible outcomes of the inputs not yet decided.

These must agree input by input with the reference implementation calib_use_decision_table.py (the version attached
to v7.37.4, SHA-256 c5279adf...); tests/core/test_calibration_use.py checks that over Appendix C's test scope and runs
the reference's invariants on these functions. Input fields keep the reference's names (Appendix C.1, last column).
Roles come from core.calibration.deps (owner calib_deps.py). Standard library only.
"""
from __future__ import annotations

import itertools

from core.calibration.deps import derive_role

GRADES = ("failed", "projection", "calibrated-unvalidated", "validated-in-scope")
RANK = {g: i for i, g in enumerate(GRADES)}
INCOMPLETE = "incomplete"   # a status, not a grade: no use, cannot be cited (section 10.2 rule 0)
USES = ("diagnostics", "design-study", "systematic-variation", "production", "publication")
USE_MIN = {"diagnostics": "failed", "design-study": "projection", "systematic-variation": "calibrated-unvalidated",
           "production": "validated-in-scope", "publication": "validated-in-scope"}
USE_BLOCKING_FLAGS = frozenset({"preliminary", "provisional-thresholds"})          # from all upstreams
GRADE_CAPPING_FLAGS = frozenset({"outside-validated-range", "closure-not-tested"})  # from central upstreams
INFORMATION_FLAGS = frozenset({"boundary-solution", "multimodal", "cv"})            # from central upstreams
FLAGS = USE_BLOCKING_FLAGS | GRADE_CAPPING_FLAGS | INFORMATION_FLAGS

VMODES = ("none", "holdout", "cross-validation")
REUSE = ("none", "fit", "fit-pending", "validation")   # fit-pending: unreachable since v7.37.3, kept for old records
FAILURE_RECORD = ("none", "final", "pending")
BOOL_INPUTS = ("incomplete", "mandatory_gate_failed", "real_data", "design_only", "p7_failed", "v_pass", "power_ok",
               "testable_ok", "validation_data_simulated")
INPUTS = BOOL_INPUTS + ("vmode", "validation_data_reuse", "earlier_failure_record", "own_flags")


def check_inputs(c: dict) -> None:
    """Refuse an input record that is not a C.1 combination (ValueError naming the field)."""
    missing = [k for k in INPUTS if k not in c]
    if missing:
        raise ValueError(f"decision inputs lack {missing}")
    for k in BOOL_INPUTS:
        if not isinstance(c[k], bool):
            raise ValueError(f"decision input {k} must be true or false")
    for k, allowed in (("vmode", VMODES), ("validation_data_reuse", REUSE), ("earlier_failure_record", FAILURE_RECORD)):
        if c[k] not in allowed:
            raise ValueError(f"decision input {k}={c[k]!r} is not one of {list(allowed)}")
    unknown = set(c["own_flags"]) - FLAGS
    if unknown:
        raise ValueError(f"unknown flags {sorted(unknown)}")


def is_pending(c: dict) -> bool:
    return c["earlier_failure_record"] == "pending" or c["validation_data_reuse"] == "fit-pending"


def resolutions(c: dict) -> list[dict]:
    """A pending record resolves to final or withdrawn (section 9.5): pending -> final | none for the failure-record
    input, fit-pending -> fit | none for the reuse input."""
    efr = ("final", "none") if c["earlier_failure_record"] == "pending" else (c["earlier_failure_record"],)
    reu = ("fit", "none") if c["validation_data_reuse"] == "fit-pending" else (c["validation_data_reuse"],)
    return [dict(c, earlier_failure_record=a, validation_data_reuse=b) for a in efr for b in reu]


def assign(c: dict) -> str:
    """Own grade, Appendix C.2, first row that holds. Resolved inputs only: a pending input is refused (I25)."""
    if is_pending(c):
        raise ValueError("pending input: judged by effective() (Appendix C.3 first step), not by assign()")
    if c["mandatory_gate_failed"]:                                   # rule 1, before rule 0
        return "failed"
    if c["incomplete"]:                                              # rule 0
        return INCOMPLETE
    if not c["real_data"] or (c["vmode"] == "none" and c["design_only"]):   # rule 2
        return "projection"
    capped = (c["vmode"] == "none"                                                            # 3a
              or c["p7_failed"] or not c["v_pass"] or not c["power_ok"] or not c["testable_ok"]  # 3b
              or "closure-not-tested" in c["own_flags"]                                         # 3c
              or c["validation_data_reuse"] == "validation"                                     # 3d
              or (c["validation_data_reuse"] == "fit" and c["vmode"] == "holdout")              # 3d holdout
              or c["validation_data_simulated"]                                                 # 3e
              or (c["earlier_failure_record"] == "final" and c["vmode"] == "cross-validation"))  # 3f
    return "calibrated-unvalidated" if capped else "validated-in-scope"   # rule 3 / rule 4


def check_upstreams(upstreams: list[dict]) -> None:
    """An upstream must carry one of the four grades; an incomplete result cannot be cited (I16)."""
    for u in upstreams:
        if u["effective_grade"] not in RANK:
            raise ValueError("upstream without a grade (incomplete) cannot be cited")


def inherited_flags(c: dict, upstreams: list[dict]) -> tuple[set[str], set[str]]:
    """(flags, variation_flags): own, all flags of central upstreams, use-blocking flags of every upstream; the other
    flags of variation upstreams are listed apart (Appendix C.3 "Flags")."""
    flags = set(c["own_flags"])
    variation_flags: set[str] = set()
    for u in upstreams:
        uf = set(u["flags"])
        flags |= uf & USE_BLOCKING_FLAGS
        if derive_role(u["usages"]) == "central":
            flags |= uf
        else:
            variation_flags |= uf - USE_BLOCKING_FLAGS
    return flags, variation_flags


def allowed_uses(eff: str, flags) -> set[str]:
    """Use matrix of section 10.2; incomplete has no use; a use-blocking flag removes publication."""
    if eff not in RANK:
        return set()
    out = {u for u in USES if RANK[eff] >= RANK[USE_MIN[u]]}
    if set(flags) & USE_BLOCKING_FLAGS:
        out.discard("publication")
    return out


def _capped(grade: str, upstreams: list[dict], flags: set[str]) -> str:
    r = RANK[grade]
    for u in upstreams:
        if derive_role(u["usages"]) == "central":
            r = min(r, RANK[u["effective_grade"]])
    if flags & GRADE_CAPPING_FLAGS:
        r = min(r, RANK["calibrated-unvalidated"])
    return GRADES[r]


def effective(c: dict, upstreams: list[dict]) -> tuple[str, set[str]]:
    """(effective grade or 'incomplete', flags), Appendix C.3. With a pending input each resolution is graded, capped
    and matched to uses; differing (grade, uses) give incomplete, equal ones that common result."""
    check_upstreams(upstreams)
    flags, _ = inherited_flags(c, upstreams)
    outcomes = set()
    for res in resolutions(c):
        own = assign(res)
        if own == INCOMPLETE:
            return INCOMPLETE, flags
        eff = _capped(own, upstreams, flags)
        outcomes.add((eff, frozenset(allowed_uses(eff, flags))))
    if len(outcomes) > 1:
        return INCOMPLETE, flags
    return next(iter(outcomes))[0], flags


def variation_upstream_admissible(u: dict) -> bool:
    """A variation upstream must itself allow systematic variations (Appendix C.3); otherwise the citation is
    rejected."""
    if u["effective_grade"] not in RANK:
        return False
    return "systematic-variation" in allowed_uses(u["effective_grade"], set(u["flags"]))


def judge(c: dict, upstreams: list[dict]) -> dict:
    """The full C.1 -> C.3 judgment as a record: own grade (absent for a pending input, section 10.1), effective grade
    or incomplete, uses, flags, variation_flags, and for a pending input the (grade, uses) of each resolution.
    Inadmissible variation upstreams are rejected (ValueError)."""
    check_inputs(c)
    for u in upstreams:
        if derive_role(u["usages"]) == "variation" and not variation_upstream_admissible(u):
            raise ValueError("a variation upstream whose effective grade does not allow systematic variations is "
                             "rejected (Appendix C.3)")
    eff, flags = effective(c, upstreams)
    _, vflags = inherited_flags(c, upstreams)
    out = {"effective_grade": eff, "uses": sorted(allowed_uses(eff, flags)), "flags": sorted(flags),
           "variation_flags": sorted(vflags)}
    if is_pending(c):
        out["own_grade"] = None
        out["resolutions"] = []
        for res in resolutions(c):
            e, f = effective(res, upstreams)
            out["resolutions"].append({"earlier_failure_record": res["earlier_failure_record"],
                                       "validation_data_reuse": res["validation_data_reuse"],
                                       "effective_grade": e, "uses": sorted(allowed_uses(e, f))})
    else:
        out["own_grade"] = assign(c)
    return out


# ------------------------------------------------------------------ outcome already determined (rule 0, D63)
UNDECIDED = ("mandatory-gate", "p7", "v")
# Possible outcomes of each undecided input, as the C.1 fields they set (section 10.2 rule 0):
#   an incomplete mandatory gate passes or fails; P7 passes or fails; V is "passed, power sufficient and k > 0" or
#   "failed". The incomplete input is cleared in every combination: each undecided input is then decided.
OUTCOMES = {
    "mandatory-gate": ({"mandatory_gate_failed": False}, {"mandatory_gate_failed": True}),
    "p7": ({"p7_failed": False}, {"p7_failed": True}),
    "v": ({"v_pass": True, "power_ok": True, "testable_ok": True}, {"v_pass": False}),
}


def outcome_combinations(c: dict, undecided) -> list[dict]:
    """Every combination of possible outcomes of the undecided inputs applied to c (incomplete cleared). In mode none
    P7 and V are not applicable and add no combination."""
    undecided = list(dict.fromkeys(undecided))
    bad = [u for u in undecided if u not in UNDECIDED]
    if bad:
        raise ValueError(f"unknown undecided inputs {bad}; use {list(UNDECIDED)}")
    if c["vmode"] == "none":
        undecided = [u for u in undecided if u == "mandatory-gate"]
    base = dict(c, incomplete=False)
    combos = []
    for choice in itertools.product(*(OUTCOMES[u] for u in undecided)):
        d = dict(base)
        for part in choice:
            d.update(part)
        combos.append(d)
    return combos


def outcome_determined(c: dict, upstreams: list[dict], undecided) -> dict:
    """Section 10.2 rule 0, general principle: before opening, evaluate C.2 then C.3 (capped upstreams count) for
    every combination of possible outcomes of the undecided inputs (each pending record resolved both ways, as in
    effective()). Returns {"determined": bool, "outcomes": [(grade, uses)...]} and, when determined, the result: V is
    recorded not-applicable (input v_pass = False), the incomplete input does not count, and the data are not opened."""
    check_inputs(c)
    seen = set()
    for d in outcome_combinations(c, undecided):
        eff, flags = effective(d, upstreams)
        seen.add((eff, frozenset(allowed_uses(eff, flags))))
    out = {"determined": len(seen) == 1, "outcomes": sorted((g, sorted(u)) for g, u in seen)}
    if out["determined"]:
        g, uses = next(iter(seen))
        out["effective_grade"], out["uses"] = g, sorted(uses)
    return out

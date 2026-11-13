"""Evidence grades, flags and uses of calibration results (Part B section 10.2, governed by Appendix C; owner
calib_use.py).

assign() is table C.2 (own grade, rules 1, 0, 2, 3a-3f, 4, first match), defined only for resolved inputs (I25).
effective() is table C.3: the pending step, the cap by central upstreams and by grade-limiting flags, and the uses.
allowed_uses() is the use matrix; variation_upstream_admissible() the eligibility of a variation upstream.
outcome_determined() is the "outcome already determined" lookup of section 10.2 rule 0 (D63), evaluated with C.2 then
C.3 for every combination of the possible outcomes of the inputs not yet decided.
check_export() is the offline check of an exported g4sim condition-snapshot/1 or alignment-overlay/1 (section 10.4
"Feeding back to g4sim", 15.3.19, A21 19-g6): the calibration result's hash in source_of_facts and the use matrix.

These must agree input by input with the reference implementation calib_use_decision_table.py (the version attached
to v7.37.4, SHA-256 c5279adf...); tests/core/test_calibration_use.py checks that over Appendix C's test scope and runs
the reference's invariants on these functions. Input fields keep the reference's names (Appendix C.1, last column).
Roles come from core.calibration.deps (owner calib_deps.py). Standard library only.
"""
from __future__ import annotations

import itertools
from typing import Any

from core.calibration.deps import derive_role, is_hash_reference
from core.canonical import canonical_sha256

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
    out: dict[str, Any] = {"effective_grade": eff, "uses": sorted(allowed_uses(eff, flags)), "flags": sorted(flags),
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


# ------------------------------------------------------------------ incomplete aggregation (rule 0)
# Section 8.1 and 8.2: the mandatory gates are those of stages B to E except P7; P7 and V are validation-type gates.
STAGES = {"B": ("P0", "P2", "P3", "P4", "P5", "P6", "P8"), "C": ("G8",), "D": ("G1", "G4", "G4-L", "G7"),
          "E": ("G2", "G3", "G5", "G6", "G9")}
MANDATORY = tuple(g for s in "BCDE" for g in STAGES[s])
GATE_STATES = ("passed", "failed", "incomplete", "not-applicable", "not-run", "closure-not-tested")
P7_STATES = ("passed", "failed", "incomplete", "no-testable-direction", "not-applicable")
V_STATES = ("passed", "failed", "incomplete", "no-testable-direction", "insufficient-power", "not-applicable")


def aggregate(gates: dict, p7: str, v: str, vmode: str) -> dict:
    """The rule-0 inputs of Appendix C.1 from the recorded states of the gates (section 10.2 rules 0 and 1; section
    8.1). A mandatory gate failed in the final version gives mandatory_gate_failed; the gates of later stages that were
    not run after it, and P7 and V, are then not-applicable, not incomplete. Gates recorded not-applicable (their
    applicability condition, section 8.1) are not counted. A mandatory gate absent from the record, not run (with no
    failure before it) or incomplete makes the result incomplete; so do P7 or V incomplete. G8 without a decision is
    closure-not-tested: a flag (rule 3c), not incomplete. Returns the C.1 fields it decides, the flags to add, the
    undecided inputs (for outcome_determined) and the reasons."""
    if vmode not in VMODES:
        raise ValueError(f"validation mode must be one of {list(VMODES)}")
    bad = {g: s for g, s in gates.items() if g not in MANDATORY or s not in GATE_STATES}
    if bad:
        raise ValueError(f"unknown mandatory gates or states {bad}; gates {list(MANDATORY)}, states {list(GATE_STATES)}")
    if p7 not in P7_STATES or v not in V_STATES:
        raise ValueError(f"P7 state must be one of {list(P7_STATES)}, V state one of {list(V_STATES)}")
    if vmode == "none" and (p7 != "not-applicable" or v != "not-applicable"):
        raise ValueError("in mode none P7 and V are not-applicable (section 8.1)")
    failed_stage = next((s for s in "BCDE" if any(gates.get(g) == "failed" for g in STAGES[s])), None)
    reasons, flags = [], set()
    incomplete_gates = []
    for s in "BCDE":
        for g in STAGES[s]:
            st = gates.get(g)
            if failed_stage is not None and s > failed_stage and st in (None, "not-run", "not-applicable"):
                continue                            # not run after a mandatory failure: not-applicable (rule 1)
            if st in (None, "not-run", "incomplete"):
                incomplete_gates.append(g)
            elif st == "closure-not-tested":
                flags.add("closure-not-tested")
    out = {"mandatory_gate_failed": failed_stage is not None}
    if failed_stage is not None:
        reasons.append(f"a mandatory gate of stage {failed_stage} failed; later stages, P7 and V are not-applicable")
        out.update(incomplete=False, p7_failed=False, v_pass=False, power_ok=True, testable_ok=True)
        return {"inputs": out, "flags": sorted(flags), "undecided": [], "reasons": reasons}
    undecided = []
    if incomplete_gates:
        undecided.append("mandatory-gate")
        reasons.append(f"mandatory gates not decided: {incomplete_gates}")
    if vmode != "none":
        if p7 == "incomplete":
            undecided.append("p7")
            reasons.append("P7 incomplete")
        if v == "incomplete":
            undecided.append("v")
            reasons.append("V incomplete (T_v not decided as failing)")
    out.update(incomplete=bool(undecided), p7_failed=(p7 == "failed"),
               v_pass=(v == "passed" or vmode == "none"),
               power_ok=(v != "insufficient-power"),
               testable_ok=(v != "no-testable-direction" and p7 != "no-testable-direction"))
    return {"inputs": out, "flags": sorted(flags), "undecided": undecided, "reasons": reasons}


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
    undecided = list(dict.fromkeys(undecided))
    if bool(undecided) != c["incomplete"]:
        raise ValueError("the undecided inputs must be given exactly when the incomplete input is set (each "
                         "incomplete mandatory gate, P7 or V is an undecided input; aggregate() derives them)")
    if c["vmode"] == "none" and set(undecided) - {"mandatory-gate"}:
        raise ValueError("in mode none P7 and V are not applicable and cannot be undecided")
    seen = set()
    for d in outcome_combinations(c, undecided):
        eff, flags = effective(d, upstreams)
        seen.add((eff, frozenset(allowed_uses(eff, flags))))
    out = {"determined": len(seen) == 1, "outcomes": sorted((g, sorted(u)) for g, u in seen)}
    if out["determined"]:
        # Not opened: V is recorded not-applicable and enters as v_pass = False; the incomplete input does not count.
        d = dict(c, incomplete=False, v_pass=False, mandatory_gate_failed=c["mandatory_gate_failed"])
        if "mandatory-gate" in undecided:
            d["mandatory_gate_failed"] = False
        if "p7" in undecided:
            d["p7_failed"] = False
        eff, flags = effective(d, upstreams)
        res = (eff, frozenset(allowed_uses(eff, flags)))
        if res not in seen:
            raise AssertionError("the not-opened result differs from the common outcome")
        out["effective_grade"], out["uses"] = eff, sorted(res[1])
        out["inputs_when_not_opened"] = {"v_pass": False, "incomplete": False}
    return out


# ------------------------------------------------------------------ exported g4sim records (section 10.4, A21 19-g6)
EXPORT_SCHEMAS = ("condition-snapshot/1", "alignment-overlay/1")
SOURCE_KEY = "calibration_result"          # written by propagate.export_g4sim
SOURCE_PREFIX = "calibration-result:"


def _get(document, pointer: str):
    node = document
    for s in pointer[1:].split("/"):
        s = s.replace("~1", "/").replace("~0", "~")
        node = node[int(s)] if isinstance(node, list) else node[s]
    return node


def _export_finding(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def check_export(record: dict, result: dict) -> list[dict]:
    """Findings of an exported g4sim record against the calibration result it cites; empty means accepted.
    - export.schema: not a condition-snapshot/1 or alignment-overlay/1;
    - export.source_of_facts: no source_of_facts, or no `calibration_result` entry with the result's hash (g4sim S9
      leaves it optional; this workflow requires it, section 10.4, 15.3.19);
    - export.result_hash: the cited result's result_sha256 is absent or does not recompute from the result;
    - export.hash_mismatch: the hash in source_of_facts (or a pointer's entry) is not the cited result's;
    - export.grade_mismatch: the stated effective grade, uses or flags are not the result's;
    - export.incomplete: the result has no grade (cannot be cited, section 10.2 rule 0);
    - export.use: the stated use is not allowed by the use matrix of section 10.2 for the result's effective grade and
      flags (production simulation needs validated-in-scope; publication none of the use-blocking flags);
    - export.value_mismatch: a written value differs from the result's beta_hat for that parameter."""
    if record.get("schema") not in EXPORT_SCHEMAS:
        return [_export_finding("export.schema", f"exported records are {list(EXPORT_SCHEMAS)}, not "
                                f"{record.get('schema')!r}")]
    out: list[dict] = []
    sha = result.get("result_sha256")
    if not is_hash_reference(sha) or canonical_sha256({k: v for k, v in result.items()
                                                        if k != "result_sha256"}) != sha:
        out.append(_export_finding("export.result_hash", "the cited result's result_sha256 is absent or does not "
                                   "recompute from the result"))
    sof = record.get("source_of_facts")
    if not isinstance(sof, dict):
        sof = {}
    entry = sof.get(SOURCE_KEY)
    if not isinstance(entry, dict) or not is_hash_reference(entry.get("result_sha256")):
        out.append(_export_finding("export.source_of_facts", "an exported condition-snapshot/1 or "
                                   "alignment-overlay/1 carries the calibration result's hash in source_of_facts "
                                   "(section 10.4, 15.3.19)"))
        return out
    if entry["result_sha256"] != sha:
        out.append(_export_finding("export.hash_mismatch", "source_of_facts cites another result"))
    grade = result.get("grade") or {}
    eff = grade.get("effective_grade")
    if eff not in RANK:
        out.append(_export_finding("export.incomplete", "the result has no grade: an incomplete result cannot be "
                                   "cited (section 10.2 rule 0)"))
        return out
    flags = set(grade.get("flags") or [])
    stated = (entry.get("effective_grade"), sorted(entry.get("uses") or []), sorted(entry.get("flags") or []))
    if stated != (eff, sorted(grade.get("uses") or []), sorted(flags)):
        out.append(_export_finding("export.grade_mismatch", f"source_of_facts states {stated}, the result has "
                                   f"{(eff, sorted(grade.get('uses') or []), sorted(flags))}"))
    use_ = entry.get("use")
    allowed = allowed_uses(eff, flags)
    if use_ not in USES or use_ not in allowed:
        out.append(_export_finding("export.use", f"use {use_!r} is not allowed for {eff} with flags {sorted(flags)}; "
                                   f"allowed {sorted(allowed)} (use matrix, section 10.2)"))
    beta = result.get("beta_hat")
    if not isinstance(beta, dict):
        beta = {}
    for ptr, name in (entry.get("parameters") or {}).items():
        if sof.get(ptr) != SOURCE_PREFIX + str(entry["result_sha256"]):
            out.append(_export_finding("export.hash_mismatch", f"source_of_facts[{ptr!r}] is not the result's hash"))
        try:
            v = float(_get(record, ptr))
        except (KeyError, IndexError, ValueError, TypeError, AttributeError):
            out.append(_export_finding("export.value_mismatch", f"{ptr} does not resolve to a value"))
            continue
        if name in beta and abs(v - float(beta[name])) > 1e-12 * max(1.0, abs(float(beta[name]))):
            out.append(_export_finding("export.value_mismatch", f"{ptr} holds {v}, the result's {name} is "
                                       f"{beta[name]}"))
    return out

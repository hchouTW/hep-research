#!/usr/bin/env python3
"""Reference decision table for the evidence-level rules of the simulation-calibration
workflow v7.37.4 (section 10.2, appendix C; v6.6: rule 1 before rule 0; v7.7: invariants I17-I18;
v7.8: failure records are written as pending when validation data are opened, invariant I19;
v7.9: the failure-record rules apply only to cross-validation, invariant I20;
v7.10: a pending record does not hold a result for which rule 2 holds;
v7.11: holdout validation units must never have been read, fit reads included, by another kappa;
invariant I21;
v7.12: the reuse input counts only reads that are not exempt (section 9.5: fit reads through a
calibration release declared in the result's own contract, on units without another kappa's
failure record, are exempt; derived by calib_data.py); invariant I22: fit reads never cap a
cross-validation result;
v7.14: a pending record holds a result incomplete only if its resolution (final or withdrawn)
would change the grade; the reuse input gains "fit-pending" for a holdout unit whose only
otherwise exempt read waits on another kappa's pending record; invariant I23;
v7.15: the pending rule compares the effective grade and the allowed uses of the two resolutions,
not the own grade, so a result capped by a central upstream or a grade-capping flag is not held
incomplete; invariant I24;
v7.16: the pending rule lives only in effective(); assign() is defined for resolved inputs only
and rejects a pending input (invariant I25); the general invariants also check pending results,
and I24 requires the common result computed with an independent cap;
v7.17: I24 also computes the allowed uses independently (use matrix and use-blocking flags from
the inputs, not from effective()), and I22 compares the allowed uses too;
v7.18: the ordered pairs of upstreams are also enumerated for a pending own combination one of
whose resolutions reaches validated-in-scope (so that the pending rule is tested with two
upstreams), and the invariants stated on a grade are checked at both layers: the own-layer form
on assign() for resolved inputs, and an effective-layer form (I1e, I2e, I3e, I4e, I7e, I12e,
I13e, I14e, I21e) on every graded result, pending included),
with an exhaustive invariant check.  Mandatory gates recorded as not-applicable (section 8.1)
are not counted in the `incomplete` input.
v7.19: comments only.  The v7.19 state rules map onto existing inputs: k = 0 is V not
incomplete with testable_ok = False (calibrated-unvalidated by rule 3); abandon-power is the
existing power input power_ok = False (rule 3b); re-judgment after a pending record is finalised
is not an upstream revision (section 10.3, calib_deps.py, outside this table).  No function,
invariant or mutant changed.
v7.20: comments only.  k = 0 known before opening is P7 and V not incomplete with
testable_ok = False and no failure record (calibrated-unvalidated by rule 3); abandon-power
also covers T_cv in cross-validation (the existing power_ok = False input).
v7.21: I20 and I22 are checked for every enumerated case, with its upstreams, not only for
cases without upstreams (the earlier restriction left them unchecked with upstreams; appendix
C.4).  A kappa with no validation read (k = 0 known before opening, or lineage not confirmed)
takes the failure-record and reuse inputs "none" (appendix C.1); the result is fixed by rule 0
or 3b either way.  No rule function or mutant changed.
v7.22-v7.25: comments only.  New incomplete reasons map onto the existing incomplete input:
k0 > 0 (v7.27; k before v7.27) with toy calibration whose replicas for C_r-hat or the reference distribution cannot be
produced (validation data not opened; failure-record and reuse inputs "none"), and a P7 power-toy
rate check that fails (P7 incomplete, as for V).  A release whose declared presence of a value
does not match its content at opening fails V like a triggered data-side constraint check (the
existing V-failed input with a final record).  No rule function, invariant or mutant changed.
v7.26: comments only.  The testable fraction is k/(k0 + n_excl) (section 9.5), still entering as
the boolean testable_ok; the toy-path power lower bound enters as the existing power_ok input.
v7.27-v7.28: comments only.  n_excl counts type-based degrees of freedom; the fraction still
enters as testable_ok.  A failed post-opening regeneration of conditioned-shape toys is the
existing incomplete input.
v7.29: comments only.  The none input for validation reads also covers P7 incomplete and a
contract rejected by the declaration checks or the fit-point recheck before opening.
v7.30: comments only.  testable_ok now means only that a testable direction exists (k > 0);
the testable-fraction threshold is removed and the fraction is reported, not judged
(v7.37 later removed the fraction altogether; only k, k0 and the unused list are reported).  A rejected
contract produces no result and never reaches the decision table.
v7.31: comments only.  A cross-validation fold whose training fit fails G5 is the existing
incomplete input.

v7.32: comments only.  A cross-validation fold whose training fit does not converge is
now the existing incomplete input (rule 0) instead of a failed mandatory gate (rule 1);
both are existing input values, so the decision function is unchanged.

v7.33: comments only.  The N_obs = 0 fallback now covers every shape with a free
normalization (including Gaussian summary shapes); it changes k, which reaches this
table only through testable_ok = (k > 0), so the decision function is unchanged.

v7.34: comments only.  Gaussian summary quantities are now conditioned on the total
event count of their event sample; this changes how k and the toys are formed, not the
inputs of this table, so the decision function is unchanged.

v7.35: comments only.  P7 power failure and a failed pre-opening ratio test are now
conditions for not opening the holdout; both reach this table through existing inputs
(rule 3b and rule 0), so the decision function is unchanged.

v7.36: comments only.  When the holdout is not opened (or T_cv not computed) because the
result is already decided -- calibration data from simulation (rule 2) or P7 power failure
(rule 3b) -- V is not applicable: it enters as v_pass = False and does not set the
incomplete input, so the result is projection or calibrated-unvalidated as before.

v7.37: comments only.  'Result already decided' is now a general rule applied by the caller
before opening: assign()/effective() are evaluated for every possible outcome of the inputs
not yet resolved (incomplete mandatory gates, P7, V; both pending destinations); if all
agree, the holdout is not opened, V is not applicable (v_pass = False) and the incomplete
input is not set.  The testable fraction mentioned for v7.26-v7.29 above was removed in
v7.30 and is no longer defined.

v7.37.1: comments only.  The 'result already decided' rule applies uniformly to every
input not yet resolved, including an incomplete mandatory gate: if assign()/effective()
agree for all its outcomes (e.g. a central upstream whose effective grade is failed), the
result is decided and the incomplete input is not set.

v7.37.2: comments only.  Calibration-side exact constraints are handled by projecting the
likelihood onto their orthogonal complement; an incomplete mandatory gate now also blocks
opening.  Neither changes the inputs of this table.

v7.37.3: comments only.  A holdout may no longer share events with the calibration
observables (rejected as a contract error, no validation read); G6/G2 toys carry MC noise.
Neither changes the inputs of this table.

v7.37.4: comments only.  The reuse input fit-pending is unreachable since v7.37.3 (a holdout
shares no raw units with its calibration release); it is kept for old records.  The
data-side constraint tolerance now uses the units of the values actually read.

The failure-record input takes three values (section 9.5): "none" (no failure record on an
overlapping calibration unit earlier than the first validation read of this kappa, or only
withdrawn ones), "final", and "pending" (the record written when another kappa opened its
validation data, whose judgment is not yet complete).  It is an input in every validation mode,
but only a cross-validation result is affected by it (v7.9): holdout reads units never read
before, and mode none has no validation read and is capped by rules 2 and 3 anyway.

This is a specification prototype, not the plugin implementation: `calib_use.py` must
reproduce `assign()`, `effective()`, `allowed_uses()` and
`variation_upstream_admissible()` exactly (appendix C), and its tests must
pass the same invariants.  Standard library only.

Scope of "exhaustive": every own-input combination (section 10.2 inputs, with P7 and V held
neutral in validation mode none) times {no upstream, every single upstream}; and every
ordered pair of upstreams for the own combinations that reach validated-in-scope under at least
one resolution (every resolution for a resolved input; v7.18).  The
usage-to-role semantics used by invariant I11 is stated separately (ENTERS_DOWNSTREAM_FIT).
The kappa event log itself (which configuration read a data release first) is an input
here; its derivation in calib_data.py is tested by the named cases of section 15.3.

Run:  python3 calib_use_decision_table.py            (exit 0: all invariants hold)
      python3 calib_use_decision_table.py --mutants  (also re-run with the defective v6.1 rules;
                                                       exit 0 only if every mutant is caught)
      python3 calib_use_decision_table.py --mutants --part=k/n  (only every n-th mutant from k)
"""
from __future__ import annotations

import itertools
import sys

GRADES = ["failed", "projection", "calibrated-unvalidated", "validated-in-scope"]
RANK = {g: i for i, g in enumerate(GRADES)}
USES = ["diagnostics", "design-study", "systematic-variation", "production", "publication"]
# minimum effective grade for each use (section 10.2 use matrix)
USE_MIN = {
    "diagnostics": "failed",
    "design-study": "projection",
    "systematic-variation": "calibrated-unvalidated",
    "production": "validated-in-scope",
    "publication": "validated-in-scope",
}
USE_BLOCKING_FLAGS = {"preliminary", "provisional-thresholds"}       # inherited from all upstreams
GRADE_CAPPING_FLAGS = {"outside-validated-range", "closure-not-tested"}  # inherited from central upstreams

# Upstream usages (section 5.2 upstream[]) and the role each implies (section 10.2).
CENTRAL_USAGES = {"phi-center", "nuisance-posterior", "xi", "fixed-value"}
VARIATION_USAGES = {"variation-set", "envelope"}


def derive_role(usages: set[str]) -> str:
    """Role is derived from usage, never declared.  Any central usage makes it central."""
    if not usages:
        raise ValueError("upstream reference without usage")
    unknown = usages - CENTRAL_USAGES - VARIATION_USAGES
    if unknown:
        raise ValueError(f"unknown usage {sorted(unknown)}")
    return "central" if usages & CENTRAL_USAGES else "variation"


def resolutions(c: dict) -> list[dict]:
    """The inputs a pending record can resolve to (section 9.5): final or withdrawn.
    earlier_failure_record: pending -> final | none; validation_data_reuse: fit-pending -> fit | none."""
    efr = ["final", "none"] if c["earlier_failure_record"] == "pending" else [c["earlier_failure_record"]]
    reu = ["fit", "none"] if c["validation_data_reuse"] == "fit-pending" else [c["validation_data_reuse"]]
    return [dict(c, earlier_failure_record=a, validation_data_reuse=b) for a in efr for b in reu]


def is_pending(c: dict) -> bool:
    return c["earlier_failure_record"] == "pending" or c["validation_data_reuse"] == "fit-pending"


def assign(c: dict) -> str:
    """Own grade, rules 0-4 of section 10.2 (table C.2), first match wins, for resolved inputs
    only (v7.16).  A pending input has no single own grade: effective() resolves it (C.3 step 1).
    'incomplete' is a status, not a grade."""
    if is_pending(c):
        raise ValueError("pending input: judged by effective() (C.3 step 1), not by assign()")
    # Rule 1 (evaluated first): a mandatory gate (stages B-E except P7) failed in the final
    # version.  Gates after the failure are not applicable, not incomplete.
    if c["mandatory_gate_failed"]:
        return "failed"
    # Rule 0: no mandatory failure, but a mandatory gate, P7 or V is incomplete (not run,
    # missing input, T_v passed but the power lower bound is not computable and power was not
    # abandoned, data lineage not established).  T_v failing makes V fail, not incomplete; k = 0
    # (no testable direction) is not incomplete either: it enters as testable_ok = False
    # (sections 9.4, 9.5; v7.19).
    if c["incomplete"]:
        return "incomplete"
    # Rule 2: no real data, or validation mode none with design-only intended use.
    if not c["real_data"] or (c["vmode"] == "none" and c["design_only"]):
        return "projection"
    # Rule 3: any cap condition.
    if c["vmode"] == "none":
        return "calibrated-unvalidated"
    if c["p7_failed"] or not c["v_pass"] or not c["power_ok"] or not c["testable_ok"]:
        return "calibrated-unvalidated"
    if "closure-not-tested" in c["own_flags"]:
        return "calibrated-unvalidated"
    # 3d: the reuse input is "none", "fit" (some validation unit has a non-exempt read, a fit
    # read included, before this kappa opened it; section 9.5) or "validation" (its first
    # validation read belongs to another kappa).  A holdout needs units without such a read
    # (v7.11, v7.12).
    if c["validation_data_reuse"] == "validation" or (
            c["validation_data_reuse"] == "fit" and c["vmode"] == "holdout"):
        return "calibrated-unvalidated"
    if c["validation_data_simulated"]:
        return "calibrated-unvalidated"
    if c["earlier_failure_record"] == "final" and c["vmode"] == "cross-validation":
        return "calibrated-unvalidated"
    # Rule 4.
    return "validated-in-scope"


def inherited_flags(c: dict, upstreams: list[dict]) -> tuple[set[str], set[str]]:
    flags = set(c["own_flags"])
    variation_flags: set[str] = set()
    for u in upstreams:
        role = derive_role(u["usages"])
        uflags = set(u["flags"])
        flags |= uflags & USE_BLOCKING_FLAGS            # from all upstreams
        if role == "central":
            flags |= uflags                              # everything from central upstreams
        else:
            variation_flags |= uflags - USE_BLOCKING_FLAGS
    return flags, variation_flags


def check_upstreams(upstreams: list[dict]) -> None:
    """An upstream must carry a grade; an incomplete result cannot be cited (rule 0)."""
    for u in upstreams:
        if u["effective_grade"] not in RANK:
            raise ValueError("upstream without a grade (incomplete) cannot be cited")


def effective(c: dict, upstreams: list[dict]) -> tuple[str, set[str]]:
    """Effective grade (section 10.2): the own grade capped by central upstreams and by the
    grade-capping flags.  A pending record (v7.15) holds the result incomplete only if its two
    resolutions give a different effective grade or different allowed uses."""
    check_upstreams(upstreams)
    flags, _ = inherited_flags(c, upstreams)
    outs = set()
    for res in resolutions(c):
        grade = assign(res)
        if grade == "incomplete":
            return "incomplete", flags
        r = RANK[grade]
        for u in upstreams:
            if derive_role(u["usages"]) == "central":
                r = min(r, RANK[u["effective_grade"]])
        if flags & GRADE_CAPPING_FLAGS:
            r = min(r, RANK["calibrated-unvalidated"])
        outs.add((GRADES[r], frozenset(allowed_uses(GRADES[r], flags))))
    if len(outs) > 1:
        return "incomplete", flags
    return next(iter(outs))[0], flags


def allowed_uses(eff: str, flags: set[str]) -> set[str]:
    if eff not in RANK:
        return set()          # incomplete: no use, not even diagnostics as a grade
    out = {u for u in USES if RANK[eff] >= RANK[USE_MIN[u]]}
    if flags & USE_BLOCKING_FLAGS:
        out.discard("publication")
    return out


def variation_upstream_admissible(u: dict) -> bool:
    """A variation upstream must itself be allowed for systematic variations."""
    if u["effective_grade"] not in RANK:
        return False
    return "systematic-variation" in allowed_uses(u["effective_grade"], set(u["flags"]))


# ---------------------------------------------------------------- exhaustive check
def own_cases():
    for (inc, mand, real, vmode, design_only, p7f, vpass, power, testable, cnt, reused, vsim, prior,
         outside, prelim, prov) in itertools.product(
            [False, True], [False, True], [False, True], ["none", "holdout", "cross-validation"],
            [False, True], [False, True], [False, True], [False, True], [False, True],
            [False, True], ["none", "fit", "fit-pending", "validation"], [False, True], ["none", "final", "pending"],
            [False, True], [False, True], [False, True]):
        if vmode == "none" and (p7f or not vpass or not power or not testable or reused != "none" or vsim):
            continue  # P7 and V are not applicable in mode none: hold them at neutral values
        own = set()
        if cnt:
            own.add("closure-not-tested")
        if outside:
            own.add("outside-validated-range")
        if prelim:
            own.add("preliminary")
        if prov:
            own.add("provisional-thresholds")
        yield dict(incomplete=inc, mandatory_gate_failed=mand, real_data=real, vmode=vmode,
                   design_only=design_only, p7_failed=p7f, v_pass=vpass, power_ok=power,
                   testable_ok=testable, validation_data_reuse=reused,
                   validation_data_simulated=vsim, earlier_failure_record=prior,
                   own_flags=own)


USAGE_SETS = [{"envelope"}, {"variation-set"}, {"phi-center"}, {"nuisance-posterior"},
              {"xi"}, {"fixed-value"}, {"envelope", "nuisance-posterior"}]
FLAG_SETS = [set(), {"provisional-thresholds"}, {"closure-not-tested"}, {"preliminary"},
             {"outside-validated-range"}]
SINGLES = [dict(usages=us, effective_grade=g, flags=fs)
           for us in USAGE_SETS for g in GRADES for fs in FLAG_SETS]


def upstream_cases():
    """No upstream, and every single upstream."""
    yield []
    for s in SINGLES:
        yield [s]


def upstream_pairs():
    """Every ordered pair of upstreams (used with the own cases that reach the top grade under at
    least one resolution)."""
    for a in SINGLES:
        for b in SINGLES:
            yield [a, b]


# Independent statement of section 10.4 / 10.2 semantics, written separately from
# CENTRAL_USAGES so that invariant I11 is not circular: which usages put an upstream
# quantity into the downstream likelihood (as a center, a constraint or a fixed value).
ENTERS_DOWNSTREAM_FIT = {
    "phi-center": True,          # upstream theta-hat is the center of a downstream phi constraint
    "nuisance-posterior": True,  # section 10.4: downstream is constrained by the exported posterior
    "xi": True,                  # section 10.4: xi enters the downstream fit as N(0, I)
    "fixed-value": True,         # upstream value fixes a downstream psi
    "variation-set": False,      # only +-1 sigma variations around a fit that does not read it
    "envelope": False,
}

# Independent statement for I18 (section 10.2): a variation upstream is admissible iff its
# effective grade allows systematic variations, i.e. is at least calibrated-unvalidated.
VARIATION_MIN_GRADE = "calibrated-unvalidated"
CAP_FLAGS_INDEPENDENT = {"outside-validated-range", "closure-not-tested"}


def cases():
    for c in own_cases():
        for ups in upstream_cases():
            yield c, ups
        # own combinations that reach the top grade under at least one resolution (v7.18: a
        # pending input whose resolutions differ is paired too, so the pending rule meets two
        # upstreams)
        if "validated-in-scope" in {assign(r) for r in resolutions(c)}:
            for ups in upstream_pairs():
                yield c, ups


def check() -> list[str]:
    errors: list[str] = []
    total = [0]

    def add(msg):                 # keep at most 1000 messages; count all (memory bound for mutants)
        total[0] += 1
        if len(errors) < 1000:
            errors.append(msg)
    n = 0
    for c, ups in cases():
        if True:
            # I18: admissibility of variation upstreams, checked against an independent statement
            for u in ups:
                if derive_role(u["usages"]) == "variation":
                    expect = RANK[u["effective_grade"]] >= RANK[VARIATION_MIN_GRADE]
                    if variation_upstream_admissible(u) != expect:
                        add(f"I18 variation admissibility wrong: {u}")
            # variation upstreams that are not admissible are rejected before grading
            if any(derive_role(u["usages"]) == "variation" and not variation_upstream_admissible(u)
                   for u in ups):
                continue
            n += 1
            pend = is_pending(c)
            g = None if pend else assign(c)          # own grade: resolved inputs only (I25)
            eff, flags = effective(c, ups)
            uses = allowed_uses(eff, flags)
            tag = f"case={c} ups={ups}"

            def bad(msg):
                add(f"{msg}: {tag} -> grade={g} eff={eff} uses={sorted(uses)}")

            central = [u for u in ups if derive_role(u["usages"]) == "central"]
            cap_src = set(c["own_flags"]).union(*[set(u["flags"]) for u in central]) if central else set(c["own_flags"])

            # I25 (v7.16): the own grade is not defined for a pending input
            if pend:
                try:
                    assign(c)
                    bad("I25 assign() graded a pending input")
                except ValueError:
                    pass
            # I20 (v7.16 form): in modes none and holdout, and without real data, the failure-record
            # input does not change the result (effective grade and uses); v7.21: checked with the
            # upstreams of the case too, not only without upstreams
            if c["vmode"] != "cross-validation" or not c["real_data"]:
                alts = set()
                for v in ("none", "final", "pending"):
                    e2, f2 = effective(dict(c, earlier_failure_record=v), ups)
                    alts.add((e2, frozenset(allowed_uses(e2, f2))))
                if len(alts) != 1:
                    bad("I20 a failure record changed a result that is not cross-validation on real data")
            # I22 (v7.17 form): fit reads never change a cross-validation result (grade and uses);
            # v7.21: checked with the upstreams of the case too
            if c["vmode"] == "cross-validation" and c["validation_data_reuse"] in ("fit", "fit-pending"):
                e1, f1 = eff, flags
                e0, f0 = effective(dict(c, validation_data_reuse="none"), ups)
                if (e1, frozenset(allowed_uses(e1, f1))) != (e0, frozenset(allowed_uses(e0, f0))):
                    bad("I22 a fit read changed a cross-validation result")

            # I19/I23 conditions, stated independently of resolutions()
            otherwise_pass = (c["real_data"] and c["v_pass"] and c["power_ok"] and c["testable_ok"]
                              and not c["p7_failed"] and "closure-not-tested" not in c["own_flags"]
                              and not c["validation_data_simulated"]
                              and not c["mandatory_gate_failed"] and not c["incomplete"])
            i19 = (c["earlier_failure_record"] == "pending" and c["vmode"] == "cross-validation"
                   and c["validation_data_reuse"] != "validation" and otherwise_pass)
            i23 = (c["validation_data_reuse"] == "fit-pending" and c["vmode"] == "holdout" and otherwise_pass)
            # use-blocking flags inherited from every upstream (section 10.2), stated independently
            blocked = bool((set(c["own_flags"]).union(*[set(u["flags"]) for u in ups]) if ups
                            else set(c["own_flags"])) & {"preliminary", "provisional-thresholds"})

            def uses_ind(grade):          # use matrix of section 10.2, written out independently
                if grade == "incomplete":
                    return frozenset()
                need = {"diagnostics": "failed", "design-study": "projection",
                        "systematic-variation": "calibrated-unvalidated",
                        "production": "validated-in-scope", "publication": "validated-in-scope"}
                out = {u_ for u_, m in need.items() if RANK[grade] >= RANK[m]}
                if blocked:
                    out.discard("publication")
                return frozenset(out)
            capped = bool(cap_src & CAP_FLAGS_INDEPENDENT) or any(
                u["effective_grade"] != "validated-in-scope" for u in central)
            if (i19 or i23) and not capped and (eff != "incomplete" or uses):
                bad("I19/I23 a pending record whose resolution matters did not hold the result incomplete")
            # I24 (v7.17 form): a pending result equals the common result of the two resolutions,
            # computed here with an independent cap and an independent use matrix
            if pend:
                outs = set()
                for v_efr in (["final", "none"] if c["earlier_failure_record"] == "pending" else [c["earlier_failure_record"]]):
                    for v_reu in (["fit", "none"] if c["validation_data_reuse"] == "fit-pending" else [c["validation_data_reuse"]]):
                        gr = assign(dict(c, earlier_failure_record=v_efr, validation_data_reuse=v_reu))
                        if gr == "incomplete":
                            outs.add(("incomplete", frozenset()))
                            continue
                        r = RANK[gr]
                        for u in central:
                            r = min(r, RANK[u["effective_grade"]])
                        if cap_src & CAP_FLAGS_INDEPENDENT:
                            r = min(r, RANK["calibrated-unvalidated"])
                        outs.add((GRADES[r], uses_ind(GRADES[r])))
                expect = next(iter(outs)) if len(outs) == 1 else ("incomplete", frozenset())
                if (eff, frozenset(uses)) != expect:
                    bad(f"I24 a pending result is not the common result of its resolutions {sorted(outs)}")
            # I23 converse / I24: no incomplete result without a reason
            if eff == "incomplete" and not c["incomplete"] and not c["mandatory_gate_failed"] and not (
                    (i19 or i23) and not capped):
                bad("I23 incomplete result without an incomplete input or a pending record that matters")
            if c["mandatory_gate_failed"] and eff != "failed":
                bad("I15 a mandatory failure did not give an effective grade failed")
            if eff == "incomplete":
                if uses:
                    bad("I15 incomplete result with a use")
                if c["incomplete"] and not c["mandatory_gate_failed"] and g not in (None, "incomplete"):
                    bad("I15 incomplete input produced an own grade")
                continue
            if c["incomplete"] and not c["mandatory_gate_failed"]:
                bad("I15 incomplete produced a grade or a use")
                continue

            # ---- own-grade invariants (resolved inputs only; a pending input's resolutions are
            # themselves resolved cases in own_cases())
            if g is not None:
                if c["mandatory_gate_failed"] and g != "failed":
                    bad("I15 a mandatory failure was not graded failed (e.g. hidden behind incomplete)")
                if g == "incomplete":
                    bad("I15 incomplete without an incomplete input")
                    continue
                if g == "failed" and not c["mandatory_gate_failed"]:
                    bad("I1 failed without a mandatory-gate failure (validation, P7 or mode none)")
                if c["vmode"] == "none" and g == "validated-in-scope":
                    bad("I2 validated without validation")
                if c["validation_data_reuse"] == "validation" and RANK[g] > RANK["calibrated-unvalidated"]:
                    bad("I3 reused validation data upgraded a result")
                if (c["vmode"] == "holdout" and c["validation_data_reuse"] == "fit"
                        and RANK[g] > RANK["calibrated-unvalidated"]):
                    bad("I21 a holdout on units already read by another kappa upgraded a result")
                if c["vmode"] != "none" and c["validation_data_simulated"] and RANK[g] > RANK["calibrated-unvalidated"]:
                    bad("I13 simulated validation data upgraded a result")
                if c["earlier_failure_record"] == "final" and c["vmode"] == "cross-validation" and RANK[g] > RANK["calibrated-unvalidated"]:
                    bad("I14 validation mode switched after a failure")
                if c["p7_failed"] and RANK[g] > RANK["calibrated-unvalidated"]:
                    bad("I4 P7 failure not capped")
                if g == "validated-in-scope" and not (
                        c["real_data"] and c["vmode"] != "none" and c["v_pass"] and c["power_ok"]
                        and c["testable_ok"] and not c["p7_failed"]
                        and "closure-not-tested" not in c["own_flags"]
                        and c["validation_data_reuse"] != "validation"
                        and not (c["validation_data_reuse"] == "fit" and c["vmode"] == "holdout")
                        and not c["validation_data_simulated"]
                        and not (c["earlier_failure_record"] != "none" and c["vmode"] == "cross-validation")
                        and not c["mandatory_gate_failed"]):
                    bad("I7 validated without every condition")
                # D2: mode none + design-only + no mandatory failure -> projection, never failed
                if c["vmode"] == "none" and c["design_only"] and not c["mandatory_gate_failed"] and g != "projection":
                    bad("I12 build-stage projection not reachable")
                if RANK[eff] > RANK[g]:
                    bad("I6 effective grade above the own grade")

            # ---- effective-level invariants (every result, pending included; v7.16)
            if pend and eff == "validated-in-scope" and (
                    (c["vmode"] == "cross-validation" and c["real_data"] and c["earlier_failure_record"] == "pending")
                    or (c["vmode"] == "holdout" and c["validation_data_reuse"] == "fit-pending")):
                bad("I7 a pending result that matters reached validated-in-scope")
            if not c["real_data"] and RANK[eff] > RANK["projection"]:
                bad("I5 simulated data above projection")
            for u in central:
                if RANK[eff] > RANK[u["effective_grade"]]:
                    bad("I6 above a central upstream")
            all_flags = set(c["own_flags"]).union(*[set(u["flags"]) for u in ups]) if ups else set(c["own_flags"])
            if "publication" in uses and (all_flags & USE_BLOCKING_FLAGS):
                bad("I8 publication despite a use-blocking flag anywhere upstream")
            if cap_src & CAP_FLAGS_INDEPENDENT and RANK[eff] > RANK["calibrated-unvalidated"]:
                bad("I17 grade-capping flag did not cap the effective grade")
            if "production" in uses and eff != "validated-in-scope":
                bad("I9 production below validated-in-scope")
            # monotonicity of the use matrix
            for u_ in USES:
                for lower in GRADES[: RANK[eff]]:
                    if u_ in allowed_uses(lower, flags) and u_ not in uses:
                        bad("I10 use matrix not monotone")
            # effective-layer forms of the invariants stated on a grade (v7.18; appendix C.4 names the
            # layer of each).  They hold for every graded result, pending included.
            central_min = min([RANK[u["effective_grade"]] for u in central], default=RANK["validated-in-scope"])
            if eff == "failed" and not c["mandatory_gate_failed"] and central_min != RANK["failed"]:
                bad("I1e failed without a mandatory-gate failure or a failed central upstream")
            cu = RANK["calibrated-unvalidated"]
            for name_, cond in (
                    ("I2e", c["vmode"] == "none"),
                    ("I3e", c["validation_data_reuse"] == "validation"),
                    ("I4e", c["p7_failed"]),
                    ("I13e", c["vmode"] != "none" and c["validation_data_simulated"]),
                    ("I14e", c["earlier_failure_record"] == "final" and c["vmode"] == "cross-validation"),
                    ("I21e", c["vmode"] == "holdout" and c["validation_data_reuse"] in ("fit", "fit-pending"))):
                if cond and RANK[eff] > cu:
                    bad(f"{name_} effective grade above calibrated-unvalidated")
            if eff == "validated-in-scope" and not (
                    c["real_data"] and c["vmode"] != "none" and c["v_pass"] and c["power_ok"]
                    and c["testable_ok"] and not c["p7_failed"]
                    and not (cap_src & CAP_FLAGS_INDEPENDENT)
                    and c["validation_data_reuse"] != "validation"
                    and not (c["validation_data_reuse"] in ("fit", "fit-pending") and c["vmode"] == "holdout")
                    and not c["validation_data_simulated"]
                    and not (c["earlier_failure_record"] != "none" and c["vmode"] == "cross-validation")
                    and central_min == RANK["validated-in-scope"]):
                bad("I7e effective validated-in-scope without every condition")
            if (c["vmode"] == "none" and c["design_only"] and not c["mandatory_gate_failed"]
                    and RANK[eff] != min(RANK["projection"], central_min)):
                bad("I12e build-stage projection (capped by central upstreams) not reached")
            # D4: an upstream used both as envelope and as nuisance posterior is central
            for u in ups:
                if any(ENTERS_DOWNSTREAM_FIT[x] for x in u["usages"]) and derive_role(u["usages"]) != "central":
                    bad("I11 an upstream that enters the downstream fit is not central")
    try:
        effective(next(own_cases()), [dict(usages={"envelope"}, effective_grade="incomplete", flags=set())])
        add("I16 an incomplete upstream was accepted")
    except ValueError:
        pass
    print(f"checked {n} combinations, {total[0]} invariant violations")
    return errors




# ---------------------------------------------------------------- mutation check
def mutation_check() -> int:
    """Re-run the invariants with the v6.1 rules that the closure review found defective.
    Each mutant must produce at least one violation; otherwise the invariants are too weak."""
    global assign, derive_role, inherited_flags
    orig = (assign, derive_role, inherited_flags)
    mutants = {}

    def p7_mandatory(c):          # D2: v6.1 counted P7 among the mandatory gates; in mode none P7 runs and fails
        if c["vmode"] == "none" or c["p7_failed"]:
            return "failed"
        return orig[0](c)
    mutants["D2 P7 mandatory"] = ("assign", p7_mandatory)

    def lock_time_only(c):        # D3: v6.1 only caught re-use when the contract changed; a plan or engine change slipped through
        c2 = dict(c, validation_data_reuse="none")
        return orig[0](c2)
    mutants["D3 contract-time key"] = ("assign", lock_time_only)

    def declared_role(usages):    # D4: v6.1 accepted a declared role; model the declaration 'variation' when an envelope is listed
        return "variation" if "envelope" in usages else orig[1](usages)
    mutants["D4 declared role"] = ("derive_role", declared_role)

    def central_only_flags(c, ups):  # minor: v6.1 inherited provisional-thresholds from central upstreams only
        flags = set(c["own_flags"])
        for u in ups:
            if orig[1](u["usages"]) == "central":
                flags |= set(u["flags"])
        return flags, set()
    mutants["provisional from central only"] = ("inherited_flags", central_only_flags)

    def posterior_as_variation(usages):  # D4 as it really occurred: a nuisance posterior counted as a variation
        if usages <= {"nuisance-posterior", "xi", "fixed-value", "envelope", "variation-set"} and "phi-center" not in usages:
            return "variation"
        return orig[1](usages)
    mutants["D4 posterior or xi as variation"] = ("derive_role", posterior_as_variation)

    def incomplete_as_pass(c):        # v6.4 ambiguity: an incomplete check silently treated as passed
        return orig[0](dict(c, incomplete=False))
    mutants["incomplete treated as pass"] = ("assign", incomplete_as_pass)

    def incomplete_before_failed(c):  # v6.5 order: rule 0 before rule 1 hides a mandatory failure
        if c["incomplete"]:
            return "incomplete"
        return orig[0](c)
    mutants["rule 0 before rule 1"] = ("assign", incomplete_before_failed)

    def first_upstream_only(c, ups):     # an implementation that inherits flags from the first upstream only
        return orig[2](c, ups[:1])
    mutants["flags from first upstream only"] = ("inherited_flags", first_upstream_only)

    global effective, variation_upstream_admissible
    orig_eff, orig_adm = effective, variation_upstream_admissible

    def no_flag_cap(c, ups):          # v7.6 regression RG3 F3: effective grade without the flag cap
        check_upstreams(ups)
        flags, _ = orig[2](c, ups)
        outs = set()
        for res in resolutions(c):
            grade = orig[0](res)
            if grade == "incomplete":
                return "incomplete", flags
            r = RANK[grade]
            for u in ups:
                if orig[1](u["usages"]) == "central":
                    r = min(r, RANK[u["effective_grade"]])
            outs.add((GRADES[r], frozenset(allowed_uses(GRADES[r], flags))))
        if len(outs) > 1:
            return "incomplete", flags
        return next(iter(outs))[0], flags
    mutants["no grade-capping flag cap"] = ("effective", no_flag_cap)

    def admit_any_grade(u):           # v7.6 regression RG3 F3: any graded variation upstream admitted
        return u["effective_grade"] in RANK
    mutants["variation admits any grade"] = ("variation_upstream_admissible", admit_any_grade)

    def holdout_ignores_fit_reads(c):  # v7.10 regression RG3 F1: only validation reads were tracked
        if c["validation_data_reuse"] == "fit":
            c = dict(c, validation_data_reuse="none")
        return orig[0](c)
    mutants["holdout ignores fit reads"] = ("assign", holdout_ignores_fit_reads)

    def cross_validation_capped_on_fit(c):  # v7.11 closure T1 F2: I3 read literally
        if c["vmode"] == "cross-validation" and c["validation_data_reuse"] == "fit":
            c = dict(c, validation_data_reuse="validation")
        return orig[0](c)
    mutants["cross-validation capped on fit reads"] = ("assign", cross_validation_capped_on_fit)





    # v7.16: assign() never sees a pending input, so every mutant of the pending rule targets
    # effective() (C.3 step 1)
    def _flags(c, ups):
        return orig[2](c, ups)[0]

    def _matters(c):                  # the two resolutions give different own grades
        return len({orig[0](r) for r in resolutions(c)}) > 1

    def pending_ignored(c, ups):      # v7.7 closure Y2 F2: a record written only at a failed judgment;
        if c["earlier_failure_record"] == "pending":   # an opened but unjudged kappa leaves no record
            c = dict(c, earlier_failure_record="none")
        return orig_eff(c, ups)
    mutants["pending failure record ignored"] = ("effective", pending_ignored)

    def records_for_non_holdout(c, ups):  # v7.8 closure W2 F1: the record rules applied to mode none
        if (c["vmode"] == "none" and not c["mandatory_gate_failed"] and not c["incomplete"]
                and c["earlier_failure_record"] == "pending"):
            return "incomplete", _flags(c, ups)
        return orig_eff(c, ups)
    mutants["record rules applied to mode none"] = ("effective", records_for_non_holdout)

    def pending_despite_rule2(c, ups):     # v7.9 closure U2 F1: pending held a rule-2 cross-validation result
        if (c["vmode"] == "cross-validation" and not c["real_data"] and not c["mandatory_gate_failed"]
                and not c["incomplete"] and c["earlier_failure_record"] == "pending"):
            return "incomplete", _flags(c, ups)
        return orig_eff(c, ups)
    mutants["pending despite rule 2"] = ("effective", pending_despite_rule2)

    def holdout_pending_unconditional(c, ups):  # v7.13 closure W1 F1: deferral without a condition
        if (c["validation_data_reuse"] == "fit-pending" and c["vmode"] == "holdout"
                and not c["mandatory_gate_failed"]):
            return "incomplete", _flags(c, ups)
        return orig_eff(c, ups)
    mutants["holdout pending deferral unconditional"] = ("effective", holdout_pending_unconditional)

    def holdout_pending_ignored(c, ups):  # a pending record treated as already withdrawn
        if c["validation_data_reuse"] == "fit-pending":
            c = dict(c, validation_data_reuse="none")
        return orig_eff(c, ups)
    mutants["holdout pending treated as withdrawn"] = ("effective", holdout_pending_ignored)

    def cv_pending_unconditional(c, ups):  # v7.8-v7.13: a pending record held a failing cross-validation too
        if (c["earlier_failure_record"] == "pending" and c["vmode"] == "cross-validation"
                and c["real_data"] and not c["mandatory_gate_failed"]):
            return "incomplete", _flags(c, ups)
        return orig_eff(c, ups)
    mutants["cross-validation pending unconditional"] = ("effective", cv_pending_unconditional)

    def pending_on_own_grade(c, ups):  # v7.14 closure X1 F1: the pending rule compared own grades only
        if is_pending(c) and not c["mandatory_gate_failed"] and not c["incomplete"] and _matters(c):
            return "incomplete", _flags(c, ups)
        return orig_eff(c, ups)
    mutants["pending judged on own grade only"] = ("effective", pending_on_own_grade)

    def capped_pending_as(grade):      # v7.15 closure Y1 F2: a capped pending result given a wrong grade
        def fn(c, ups):
            e, f = orig_eff(c, ups)
            if is_pending(c) and e != "incomplete" and not c["mandatory_gate_failed"] and _matters(c):
                return grade, f
            return e, f
        return fn
    mutants["capped pending given failed"] = ("effective", capped_pending_as("failed"))
    mutants["capped pending given projection"] = ("effective", capped_pending_as("projection"))
    mutants["capped pending ignores a lower central upstream"] = (
        "effective", capped_pending_as("calibrated-unvalidated"))

    def pending_gains_blocking_flag(c, ups):  # v7.16 closure Z1 F1: wrong uses, right effective grade
        e, f = orig_eff(c, ups)
        if is_pending(c) and e != "incomplete":
            return e, set(f) | {"preliminary"}
        return e, f
    mutants["pending result gains a use-blocking flag"] = ("effective", pending_gains_blocking_flag)

    def pending_first_upstream_only(c, ups):  # v7.17 regression RG3 F1: the pending rule judged
        if is_pending(c) and not c["mandatory_gate_failed"] and not c["incomplete"] and _matters(c):
            return orig_eff(c, ups[:1])        # with the first upstream only
        return orig_eff(c, ups)
    mutants["pending rule judged with the first upstream only"] = ("effective", pending_first_upstream_only)

    failures = 0
    items = list(mutants.items())
    part = next((x for x in sys.argv[1:] if x.startswith("--part=")), None)
    if part:                          # --part=k/n: run every n-th mutant starting at k (1-based)
        k, n = map(int, part.split("=")[1].split("/"))
        items = items[k - 1::n]
    for name, (target, fn) in items:
        globals()[target] = fn
        errs = check()
        globals()["assign"], globals()["derive_role"], globals()["inherited_flags"] = orig
        globals()["effective"], globals()["variation_upstream_admissible"] = orig_eff, orig_adm
        caught = bool(errs)
        print(f"mutant {name}: {'caught' if caught else 'NOT CAUGHT'}")
        failures += not caught
    return failures


if __name__ == "__main__":
    errs = check()
    for e in errs[:20]:
        print(e)
    if errs:
        sys.exit(1)
    if "--mutants" in sys.argv[1:]:
        sys.exit(1 if mutation_check() else 0)
    sys.exit(0)

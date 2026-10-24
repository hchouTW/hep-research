"""Study-layer decisions of simulation studies: the equivalence gate (an intersection-union test over observables) and
the detection limit of a negative control. Each decision has a standard-error branch and an exact-interval branch for
low counts, takes the multiplicity m, and returns {verdict, margin, reason} with reason from REASONS. These decide only
study-layer gates (convergence, benchmarks); requirement verdicts are derived by contracts/design.py. Standard library
only."""
from __future__ import annotations

import math

from core import trace
from core.stats.distributions import t_ppf

ALPHA = 0.05
REASONS = ("within-tolerance", "beyond-tolerance", "not-resolved", "se-target-missed", "interval-inside",
           "interval-outside", "interval-straddles")


class DecisionError(ValueError):
    """Unusable decision input."""


def welch_dof(se_a: float, dof_a: float, se_b: float, dof_b: float) -> float:
    """Welch-Satterthwaite degrees of freedom of the difference of two estimates with their SEs and dofs."""
    va, vb = se_a * se_a, se_b * se_b
    den = (va * va / dof_a if va else 0.0) + (vb * vb / dof_b if vb else 0.0)
    return (va + vb) ** 2 / den if den > 0 else max(dof_a, dof_b)


def difference(a: float, se_a: float, b: float, se_b: float, mode: str = "relative") -> tuple[float, float]:
    """(diff, se_diff): relative (a - b)/b with sqrt(se_a^2 + se_b^2)/|b|, or absolute a - b."""
    if mode == "relative":
        if b == 0:
            raise DecisionError("a relative difference needs a non-zero reference value b")
        return (a - b) / b, math.hypot(se_a, se_b) / abs(b)
    if mode == "absolute":
        return a - b, math.hypot(se_a, se_b)
    raise DecisionError(f"tolerance_mode must be relative or absolute, not {mode!r}")


def equivalence(diff: float | None, se: float | None, dof: float | None, tol: float, m: int = 1,
                targets_met: bool = True, interval90=None, interval_m=None) -> dict:
    """Equivalence of two settings within +-tol. SE branch: pass when |diff| + t_0.95(dof) se <= tol and both points
    met their se target; fail when |diff| - t_{1-alpha/m}(dof) se > tol (alpha = 0.05; a missed target can still
    fail); otherwise unresolved. Exact branch (interval90 = the 90 % interval of diff, interval_m = the one-sided
    1 - alpha/m interval as (lower, upper)): pass when interval90 lies inside [-tol, tol], fail when interval_m lies
    entirely outside it."""
    trace.tag("geant4-convergence-iut")
    if not (isinstance(tol, (int, float)) and tol > 0) or not (isinstance(m, int) and m >= 1):
        raise DecisionError("equivalence needs tol > 0 and an integer multiplicity m >= 1")
    if interval90 is not None:
        lo90, hi90 = interval90
        lo_m, hi_m = interval_m if interval_m is not None else interval90
        if -tol <= lo90 and hi90 <= tol:
            return {"verdict": "pass", "margin": tol - max(abs(lo90), abs(hi90)), "reason": "interval-inside"}
        if lo_m > tol or hi_m < -tol:
            return {"verdict": "fail", "margin": max(lo_m - tol, -tol - hi_m), "reason": "interval-outside"}
        return {"verdict": "unresolved", "margin": None, "reason": "interval-straddles"}
    if diff is None or se is None or dof is None:
        raise DecisionError("the SE branch needs diff, se and dof")
    upper = abs(diff) + t_ppf(0.95, dof) * se
    lower = abs(diff) - t_ppf(1.0 - ALPHA / m, dof) * se
    if upper <= tol and targets_met:
        return {"verdict": "pass", "margin": tol - upper, "reason": "within-tolerance"}
    if lower > tol:
        return {"verdict": "fail", "margin": lower - tol, "reason": "beyond-tolerance"}
    return {"verdict": "unresolved", "margin": None, "reason": "se-target-missed" if upper <= tol else "not-resolved"}


def detection_limit(tol: float, rel: float, se_rel: float, dof: float) -> dict:
    """Detection limit of a negative control: DL = tol + |rel| + t_0.977(dof) se_rel, with tol the benchmark's total
    tolerance, rel the nominal's relative deviation from the reference and se_rel the combined SE of the shift
    (control - nominal)/reference. An injection of size DL is caught (|rel_c| > tol) with probability about 0.977."""
    trace.tag("geant4-detection-limit")
    return {"value": tol + abs(rel) + t_ppf(0.977, dof) * se_rel, "quantile": 0.977, "dof": dof,
            "definition": "tol + |rel| + t_0.977(dof) se_rel"}

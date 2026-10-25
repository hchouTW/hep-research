"""Study-layer decisions of simulation studies: the equivalence gate (an intersection-union test over observables) and
the detection limit of a negative control, and (CV-B2, B2.7) the change decision of a regression check. Each decision
has a standard-error branch and an exact-interval branch for low counts, takes the multiplicity m, and returns
{verdict, margin, reason} with reason from REASONS. These decide only
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


def _paired_blocks(blocks) -> tuple[list[float], list[float]]:
    try:
        a, b = ([float(x) for x in blocks[0]], [float(x) for x in blocks[1]])
    except (TypeError, ValueError, IndexError) as exc:
        raise DecisionError("paired mode needs blocks = (block estimates of a, block estimates of b)") from exc
    if len(a) != len(b) or len(a) < 2 or not all(math.isfinite(x) for x in a + b):
        raise DecisionError("paired mode needs two equal-length lists of at least 2 finite block estimates (one "
                            "seed_group, equal K and B)")
    return a, b


def paired_statistic(blocks, mode: str = "relative", r: float = 0.0) -> dict:
    """The paired statistic of two points of one seed_group (Geant4 program C2.1; common random numbers: block b of
    both points used the same random numbers). absolute: d_b = a_b - b_b, value = mean(d_b), se = sd(d_b)/sqrt(K).
    relative, for a bound r: z_b = (a_b - (1 + r) b_b) / mean(b), value = mean(z_b), se = sd(z_b)/sqrt(K) (Fieller
    type: a = (1 + r) b is tested as z = 0, so the uncertainty of mean(b) is not ignored); at r = 0 the value is the
    relative difference. dof = K - 1 in both modes."""
    a, b = _paired_blocks(blocks)
    k = len(a)
    if mode == "absolute":
        z = [x - y for x, y in zip(a, b)]
    elif mode == "relative":
        bbar = math.fsum(b) / k
        if bbar == 0:
            raise DecisionError("a relative paired difference needs a non-zero block mean of b")
        z = [(x - (1.0 + r) * y) / bbar for x, y in zip(a, b)]
    else:
        raise DecisionError(f"tolerance_mode must be relative or absolute, not {mode!r}")
    mean = math.fsum(z) / k
    sd = math.sqrt(math.fsum((x - mean) ** 2 for x in z) / (k - 1))
    return {"value": mean, "se": sd / math.sqrt(k), "dof": k - 1, "blocks": k, "mode": mode, "r": r}


def _paired_equivalence(blocks, tol: float, m: int, targets_met: bool, mode: str) -> dict:
    """TOST in paired mode: the equivalence decision from per-block statistics (relative: one Fieller-type test per
    bound r = +-tol; absolute: the SE branch on the per-block differences). The se target is se <= tol/4 at r = 0."""
    centre = paired_statistic(blocks, mode, 0.0)
    met = targets_met and centre["se"] <= tol / 4
    info = {"pairing": "paired", "mode": mode, "diff": centre["value"], "se": centre["se"], "dof": centre["dof"],
            "se_target": tol / 4}
    if mode == "absolute":
        return {**equivalence(centre["value"], centre["se"], centre["dof"], tol, m, met), "paired": info}
    up, lo = paired_statistic(blocks, mode, tol), paired_statistic(blocks, mode, -tol)
    dof = centre["dof"]
    t95, tm = t_ppf(0.95, dof), t_ppf(1.0 - ALPHA / m, dof)
    below_up = up["value"] + t95 * up["se"]   # <= 0: a < (1 + tol) b at 95 %
    above_lo = lo["value"] - t95 * lo["se"]   # >= 0: a > (1 - tol) b at 95 %
    info.update({"upper_bound": up, "lower_bound": lo})
    if below_up <= 0 and above_lo >= 0 and met:
        return {"verdict": "pass", "margin": min(-below_up, above_lo), "reason": "within-tolerance", "paired": info}
    beyond_up, beyond_lo = up["value"] - tm * up["se"], -(lo["value"] + tm * lo["se"])
    if beyond_up > 0 or beyond_lo > 0:
        return {"verdict": "fail", "margin": max(beyond_up, beyond_lo), "reason": "beyond-tolerance", "paired": info}
    reason = "se-target-missed" if below_up <= 0 and above_lo >= 0 else "not-resolved"
    return {"verdict": "unresolved", "margin": None, "reason": reason, "paired": info}


def equivalence(diff: float | None, se: float | None, dof: float | None, tol: float, m: int = 1,
                targets_met: bool = True, interval90=None, interval_m=None, *, pairing: str = "independent",
                blocks=None, mode: str = "relative") -> dict:
    """Equivalence of two settings within +-tol. SE branch: pass when |diff| + t_0.95(dof) se <= tol and both points
    met their se target; fail when |diff| - t_{1-alpha/m}(dof) se > tol (alpha = 0.05; a missed target can still
    fail); otherwise unresolved. Exact branch (interval90 = the 90 % interval of diff, interval_m = the one-sided
    1 - alpha/m interval as (lower, upper)): pass when interval90 lies inside [-tol, tol], fail when interval_m lies
    entirely outside it. Paired mode (pairing='paired', C2.1): diff, se and dof are ignored and computed from blocks =
    (block estimates of a, of b) of one seed_group with tolerance mode `mode` (paired_statistic); the result carries
    the statistic under 'paired'. The default stays independent."""
    trace.tag("geant4-convergence-iut")
    if not (isinstance(tol, (int, float)) and tol > 0) or not (isinstance(m, int) and m >= 1):
        raise DecisionError("equivalence needs tol > 0 and an integer multiplicity m >= 1")
    if pairing == "paired":
        return _paired_equivalence(blocks, tol, m, targets_met, mode)
    if pairing != "independent":
        raise DecisionError(f"pairing must be independent or paired, not {pairing!r}")
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


def change(diff: float | None, se: float | None, dof: float | None, tol: float, m: int = 1, interval90=None,
           interval_m=None, *, pairing: str = "independent", blocks=None, mode: str = "relative") -> dict:
    """Whether an observable changed between two versions (Geant4 program B2.7, regression). SE branch: changed when
    |diff| - t_{1-alpha/m}(dof) se > tol; unchanged when equivalence passes (|diff| + t_0.95(dof) se <= tol);
    otherwise unresolved. Exact branch (counts): changed when interval_m lies entirely outside [-tol, tol], unchanged
    when interval90 lies inside it. Paired mode as in equivalence. {verdict: changed | unchanged | unresolved, margin,
    reason} (plus 'paired' in paired mode)."""
    trace.tag("geant4-regression-change")
    eq = equivalence(diff, se, dof, tol, m, True, interval90, interval_m, pairing=pairing, blocks=blocks, mode=mode)
    extra = {"paired": eq["paired"]} if "paired" in eq else {}
    if eq["verdict"] == "pass":
        return {"verdict": "unchanged", "margin": eq["margin"], "reason": eq["reason"], **extra}
    if eq["verdict"] == "fail":
        return {"verdict": "changed", "margin": eq["margin"], "reason": eq["reason"], **extra}
    return {"verdict": "unresolved", "margin": None, "reason": eq["reason"], **extra}


def detection_limit(tol: float, rel: float, se_rel: float, dof: float) -> dict:
    """Detection limit of a negative control: DL = tol + |rel| + t_0.977(dof) se_rel, with tol the benchmark's total
    tolerance, rel the nominal's relative deviation from the reference and se_rel the combined SE of the shift
    (control - nominal)/reference. An injection of size DL is caught (|rel_c| > tol) with probability about 0.977."""
    trace.tag("geant4-detection-limit")
    return {"value": tol + abs(rel) + t_ppf(0.977, dof) * se_rel, "quantile": 0.977, "dof": dof,
            "definition": "tol + |rel| + t_0.977(dof) se_rel"}

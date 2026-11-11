"""Multistart seeds of the joint fit (D3 stage 3; t07-t09-task-sheets.md, T09: "seeded multistart fits"; the reference,
"Seeding and the fit sequence", step 3: "from the first guess and from several perturbed or mirrored starts"). Data side: every
start comes from the readout alone; no truth, no generator, no random numbers.

The budget (t04-values-v4.md section 2.2, "Algorithmic budgets: seeds, branches, multistart count, iterations (K10), by hash")
is a file of its own, format light-likelihood-multistart/1, exact keys format, starts (the ordered start names, the first
"prefit") and tie_tolerance; its SHA-256 and content go into product /3's header. The configuration is not changed.

The starts (case O-starts of the D3 stage 3 report), from the anchor (x_a, d_a), which is stage 2's one joint start
(fit.joint_seed: the charge-only prefit's point, or its last point, or the charge seed):
- prefit: the anchor itself, with stage 2's E_vis and t0, so the one-seed fit is start 0, unchanged;
- reversed: (x_a, -d_a); turned +e1, -e1, +e2, -e2: (x_a, +-e1(d_a)), (x_a, +-e2(d_a)), section 7's frame at d_a;
- mirrored: the anchor reflected through the sphere centre, (-x_a, -d_a);
- charge seed: stage 1's moment seed (fit.seed), not fitted.
Starts other than prefit take E_vis by stage 1's moment rule and t0 by stage 2's median rule at their own vertex and direction
(case O-start-values). Each start is fitted by fit.fit_joint_event, unchanged.

Choice (case O-choice): among the converged starts the highest ln L; every converged start within tie_tolerance of it is tied,
and the lowest index wins. No converged start (case O-all-fail): the reported fit fails with the kind all-starts-failed and
carries start 0's last point if it has one. No hit channel: no start, kind no-hit-channel.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy

from . import fit, light_model
from .likelihood import frame

FORMAT = "light-likelihood-multistart/1"
DEFAULT = Path(__file__).resolve().parent.parent / "t09-multistart-1.budget.json"
KEYS = {"format", "starts", "tie_tolerance"}
FIRST = "prefit"
RULES = {
    "prefit": "stage 2's one joint start: the charge-only prefit's point (or its last point, or the charge seed), t0 by the median rule",
    "reversed": "the anchor vertex, the anchor direction reversed",
    "turned +e1": "the anchor vertex, direction e1 of section 7's frame at the anchor direction",
    "turned -e1": "the anchor vertex, direction -e1 of section 7's frame at the anchor direction",
    "turned +e2": "the anchor vertex, direction e2 of section 7's frame at the anchor direction",
    "turned -e2": "the anchor vertex, direction -e2 of section 7's frame at the anchor direction",
    "mirrored": "the anchor reflected through the sphere centre: vertex -x_a, direction -d_a",
    "charge seed": "stage 1's moment seed (vertex 0.5 c, the charge-weighted direction), not fitted",
}
VALUES_RULE = ("starts other than prefit: E_vis by stage 1's moment rule (sum q / (1000 sum_live s_i)) and t0 by stage 2's median "
               "rule (median over hits of t_i - |P_i - x| / v), at the start's own vertex and direction")
ALL_FAILED = "all-starts-failed"
FAILURES = fit.FAILURES + (ALL_FAILED,)
RULE_BEST = "highest ln L"
RULE_TIE = "tie within tolerance, lowest index"
RULE_ALL_FAILED = "all starts failed"
RULE_NO_START = "no start"
CHOICE_RULES = (RULE_BEST, RULE_TIE, RULE_ALL_FAILED, RULE_NO_START)
CHOICE_TEXT = ("the reported fit is the converged start with the highest ln L; every converged start within tie_tolerance of it is "
               "tied and the lowest index wins; no converged start: failed, kind all-starts-failed, with start 0's last point if it "
               "has one; no hit channel: no start, kind no-hit-channel")


class BudgetError(ValueError):
    """The budget file is refused."""


@dataclass(frozen=True)
class Budget:
    format: str
    starts: tuple
    tie_tolerance: float
    sha256: str

    def header(self) -> dict:
        return {"format": self.format, "sha256": self.sha256, "starts": list(self.starts), "tie_tolerance": self.tie_tolerance}


def _refuse_constant(name):
    raise ValueError(f"non-finite number {name}")


def load(path=None) -> Budget:
    path = Path(path) if path is not None else DEFAULT
    try:
        content = path.read_bytes()
        doc = json.loads(content, parse_constant=_refuse_constant)
    except (OSError, ValueError, RecursionError) as exc:
        raise BudgetError(f"budget cannot be read: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise BudgetError(f"budget keys must be exactly {sorted(KEYS)}")
    if doc["format"] != FORMAT:
        raise BudgetError(f"budget format must be {FORMAT}")
    starts = doc["starts"]
    if not (isinstance(starts, list) and starts and all(isinstance(s, str) for s in starts)):
        raise BudgetError("starts must be a non-empty list of start names")
    unknown = [s for s in starts if s not in RULES]
    if unknown:
        raise BudgetError(f"unknown start names {unknown}; known: {sorted(RULES)}")
    if len(set(starts)) != len(starts):
        raise BudgetError("a start name is repeated")
    if starts[0] != FIRST:
        raise BudgetError(f"start 0 must be {FIRST!r}, so the one-seed fit is one of the starts")
    tie = doc["tie_tolerance"]
    if isinstance(tie, bool) or not isinstance(tie, (int, float)) or not math.isfinite(tie) or tie <= 0:
        raise BudgetError("tie_tolerance must be a positive finite number")
    return Budget(doc["format"], tuple(starts), float(tie), hashlib.sha256(content).hexdigest())


@dataclass(frozen=True)
class StartRecord:
    name: str
    start: fit.JointSeed
    result: fit.FitResult


@dataclass(frozen=True)
class Multistart:
    anchor: fit.JointSeed | None          # start 0: stage 2's one joint start
    prefit: fit.FitResult | None
    origin: str | None
    starts: list
    chosen: int | None
    choice: str
    result: fit.FitResult


def moment_e_vis(model, event, vertex, direction) -> float:
    """Stage 1's moment rule at (vertex, direction): the hit charge over the expected light per unit E_vis of the live channels."""
    expected_per_unit = model.scale * light_model.shape(model, vertex, direction)[event.live].sum()
    return float(event.charge[event.hit].sum() / expected_per_unit)


def median_t0(model, tev, vertex) -> float:
    """Stage 2's median rule: median over hit channels of t_i - |P_i - x| / v."""
    hit = tev.event.hit
    dist = numpy.linalg.norm(model.geometry.positions[hit] - vertex, axis=1)
    return float(numpy.median(tev.time[hit] - dist / model.cfg.photon_speed_m_per_ns))


def _point(model, tev, name, anchor):
    x, d = numpy.asarray(anchor.vertex, float), numpy.asarray(anchor.direction, float)
    if name == "charge seed":
        s = fit.seed(model, tev.event)
        return s.vertex, s.direction
    if name == "mirrored":
        return -x, -d
    e1, e2 = frame(d)
    direction = {"reversed": -d, "turned +e1": e1, "turned -e1": -e1, "turned +e2": e2, "turned -e2": -e2}[name]
    return x.copy(), direction


def start_points(model, tev, budget: Budget, anchor: fit.JointSeed) -> list:
    """[(name, JointSeed)] in the budget's order; the first is the anchor itself."""
    out = []
    for name in budget.starts:
        if name == FIRST:
            out.append((name, anchor))
            continue
        vertex, direction = _point(model, tev, name, anchor)
        vertex, direction = numpy.asarray(vertex, float), numpy.asarray(direction, float)
        out.append((name, fit.JointSeed(vertex, direction, moment_e_vis(model, tev.event, vertex, direction),
                                        median_t0(model, tev, vertex))))
    return out


def choose(outcomes, tie_tolerance: float):
    """(chosen index or None, rule) from [(status, ln L)] in start order (case O-choice)."""
    if not outcomes:
        return None, RULE_NO_START
    converged = [(i, ln_l) for i, (status, ln_l) in enumerate(outcomes) if status == "converged" and ln_l is not None
                 and math.isfinite(ln_l)]
    if not converged:
        return None, RULE_ALL_FAILED
    best = max(ln_l for _, ln_l in converged)
    tied = [i for i, ln_l in converged if ln_l >= best - tie_tolerance]
    return min(tied), (RULE_TIE if len(tied) > 1 else RULE_BEST)


def fit_multistart(model, tev, budget: Budget) -> Multistart:
    anchor, prefit, origin = fit.joint_seed(model, tev)
    if anchor is None:
        return Multistart(None, prefit, origin, [], None, RULE_NO_START, fit._failed("no-hit-channel", None))
    records = [StartRecord(name, start, fit.fit_joint_event(model, tev, start)) for name, start in start_points(model, tev, budget, anchor)]
    chosen, rule = choose([(r.result.status, r.result.ln_likelihood) for r in records], budget.tie_tolerance)
    if chosen is None:
        result = dataclasses.replace(records[0].result, status="failed", failure=ALL_FAILED, covariance=None)
        if result.uncertainty_status == "ok":
            result = dataclasses.replace(result, uncertainty_status="not-formed")
    else:
        result = records[chosen].result
    return Multistart(anchor, prefit, origin, records, chosen, rule, result)

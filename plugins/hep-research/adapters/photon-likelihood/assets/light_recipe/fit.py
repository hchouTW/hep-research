"""The fit of stage 1: one seed, then the maximum of the charge-only ln L (cases O-seed, O-optimizer, O-direction and
O-uncertainty of the D3 stage 1 report). Multistart seeds come in a later stage (t07-t09-task-sheets.md, T09, steps).

Seed (the reference, seeding step 2, a moment estimate for a point-like source): c = sum q_i P_i / sum q_i over hit sensors;
vertex 0.5 c; direction norm(sum q_i (P_i - x0)/|P_i - x0|), the +z axis if that is zero; E_vis = sum q_i / (1000 sum_live
s_i(x0, d0)). No hit channel: no seed.

Fit: SciPy trust-exact on -ln L with the analytic gradient and Hessian of likelihood.Objective, in a chart around the current
direction, re-centred at each round's result until a round's direction step is below CHART_STEP. A round ends when SciPy stops
with success, or with its status 2 ("a bad approximation caused failure to predict improvement"), which it reports at the
minimum once the predicted improvement is below the rounding of -ln L (about 1e-13 of it). Convergence is then decided at the
re-centred result by the Newton decrement g^T (-H)^-1 g <= DECREMENT_TOL (the distance left to the quadratic minimum, squared, in
units of the fit's own uncertainty), which does not depend on the scale of ln L. Fit failure (section 7): no seed
(no-hit-channel), the iteration budget (iteration-budget: MAX_ITERATIONS in one round, or MAX_ROUNDS rounds), any other SciPy
status or a decrement above the tolerance (not-converged), a non-finite value (non-finite: a start or a result outside the
likelihood's domain; no point is recorded, so every recorded point lies inside the domain), or no finite covariance at the
result (no-finite-covariance). The covariance is the inverse of the observed Hessian of -ln L at the result, in (x, y, z, u1, u2,
E_vis), with u1, u2 the tangent components at the fitted direction in section 7's frame (e1, e2 returned with it); it is
conditional on the fixed light model and validated by no pull here. t0 is not estimated: the charge model has no time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy
from scipy import linalg, optimize

from . import light_model
from .likelihood import EventData, Model, Objective, frame

GTOL = 1e-6
MAX_ITERATIONS = 200
MAX_ROUNDS = 6
CHART_STEP = 1e-4
DECREMENT_TOL = 1e-8
SEED_VERTEX_FACTOR = 0.5
SETTINGS = {"minimiser": "scipy.optimize.minimize, method trust-exact, analytic gradient and Hessian", "gtol": GTOL,
            "max_iterations_per_round": MAX_ITERATIONS, "max_rounds": MAX_ROUNDS, "chart_step": CHART_STEP,
            "accepted_scipy_status": [0, 2], "newton_decrement_tolerance": DECREMENT_TOL,
            "seed_vertex_factor": SEED_VERTEX_FACTOR, "seeds": 1}
FAILURES = ("no-hit-channel", "iteration-budget", "not-converged", "non-finite", "no-finite-covariance")


@dataclass(frozen=True)
class Seed:
    vertex: numpy.ndarray
    direction: numpy.ndarray
    e_vis: float


@dataclass(frozen=True)
class FitResult:
    status: str                          # converged | failed
    failure: str | None                  # one of FAILURES, or None
    vertex: numpy.ndarray | None
    direction: numpy.ndarray | None
    e_vis: float | None
    covariance: numpy.ndarray | None     # (6, 6) in (x, y, z, u1, u2, E_vis), or None
    uncertainty_status: str              # ok | not-positive-definite | non-finite | not-formed
    ln_likelihood: float | None
    gradient_norm: float | None
    newton_decrement: float | None
    iterations: int
    rounds: int
    e1: numpy.ndarray | None
    e2: numpy.ndarray | None


def seed(model: Model, event: EventData) -> Seed | None:
    hit = event.hit
    if not hit.any():
        return None
    q = event.charge[hit]
    positions = model.geometry.positions[hit]
    vertex = SEED_VERTEX_FACTOR * (q[:, None] * positions).sum(axis=0) / q.sum()
    toward = positions - vertex
    pull = (q[:, None] * toward / numpy.linalg.norm(toward, axis=1)[:, None]).sum(axis=0)
    norm = numpy.linalg.norm(pull)
    direction = pull / norm if norm > 0 else numpy.array([0.0, 0.0, 1.0])
    expected_per_unit = model.scale * light_model.shape(model, vertex, direction)[event.live].sum()
    return Seed(vertex, direction, float(q.sum() / expected_per_unit))


def _failed(failure, start, iterations=0, rounds=0, vertex=None, direction=None, e_vis=None, ln_l=None, grad=None,
            uncertainty="not-formed", decrement=None):
    e1, e2 = frame(direction) if direction is not None else (None, None)
    return FitResult("failed", failure, vertex, direction, e_vis, None, uncertainty, ln_l, grad, decrement, iterations, rounds,
                     e1, e2)


def fit_event(model: Model, event: EventData, start: Seed | None = None) -> FitResult:
    start = start if start is not None else seed(model, event)
    if start is None:
        return _failed("no-hit-channel", None)
    vertex = numpy.asarray(start.vertex, float)
    direction = numpy.asarray(start.direction, float) / numpy.linalg.norm(start.direction)
    e_vis = float(start.e_vis)
    iterations = 0
    for rounds in range(1, MAX_ROUNDS + 1):
        objective = Objective(model, event, direction)
        p0 = numpy.r_[vertex, 0.0, 0.0, e_vis]
        if not math.isfinite(objective.value(p0)):
            return _failed("non-finite", start, iterations, rounds - 1)
        res = optimize.minimize(lambda p: -objective.value(p), p0, method="trust-exact",
                                jac=lambda p: -objective.derivatives(p)[1], hess=lambda p: -objective.derivatives(p)[2],
                                options={"gtol": GTOL, "maxiter": MAX_ITERATIONS})
        iterations += int(res.nit)
        vertex, e_vis = res.x[:3].copy(), float(res.x[5])
        direction = objective.direction(res.x[3], res.x[4])
        if not (numpy.all(numpy.isfinite(res.x)) and math.isfinite(objective.value(res.x))):
            return _failed("non-finite", start, iterations, rounds)
        if res.nit >= MAX_ITERATIONS:
            return _failed("iteration-budget", start, iterations, rounds, vertex, direction, e_vis, -float(res.fun))
        if res.status not in (0, 2):
            return _failed("not-converged", start, iterations, rounds, vertex, direction, e_vis, -float(res.fun))
        if math.hypot(res.x[3], res.x[4]) < CHART_STEP:
            break
    else:
        return _failed("iteration-budget", start, iterations, MAX_ROUNDS, vertex, direction, e_vis)
    recentred = Objective(model, event, direction)
    ln_l, gradient, hessian = recentred.derivatives(numpy.r_[vertex, 0.0, 0.0, e_vis])
    grad_norm = float(numpy.linalg.norm(gradient))
    if not (numpy.all(numpy.isfinite(hessian)) and math.isfinite(ln_l)):
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, "non-finite")
    try:
        factor = linalg.cho_factor(-hessian, lower=True)
    except linalg.LinAlgError:
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm,
                       "not-positive-definite")
    covariance = linalg.cho_solve(factor, numpy.eye(6))
    covariance = 0.5 * (covariance + covariance.T)
    decrement = float(gradient @ covariance @ gradient)
    if not numpy.all(numpy.isfinite(covariance)) or numpy.any(numpy.diag(covariance) <= 0):
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, "non-finite")
    if not decrement <= DECREMENT_TOL:
        return _failed("not-converged", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, decrement=decrement)
    return FitResult("converged", None, vertex, direction, e_vis, covariance, "ok", ln_l, grad_norm, decrement, iterations, rounds,
                     recentred.e1, recentred.e2)

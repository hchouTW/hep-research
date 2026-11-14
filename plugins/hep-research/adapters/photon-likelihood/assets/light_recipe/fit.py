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

The joint fit of stage 2 (cases O-params, O-t0-seed and O-t0-domain of the D3 stage 2 report): joint_seed runs the charge-only
fit above from its seed; its result (or its last point if it failed with one, or else the charge seed) gives the vertex,
direction and E_vis of the start, and t0's seed is the median over hit channels of t_i - |P_i - x_start| / v. fit_joint_event
then maximises the joint ln L (joint.Objective) in seven coordinates (x, y, z, a, b, E_vis, t0) by the same chart rounds,
convergence rule, failure kinds and covariance (now 7 x 7, (x, y, z, u1, u2, E_vis, t0)). One seed: multistart comes later.
One addition, joint only (case O-chart-exit, found on noisy hand-made events): a round also ends, without failure, once its chart
step |(a, b)| exceeds JOINT_CHART_RADIUS, and the next round re-centres there. From a mirrored charge-only start the time term
turns the direction by more than 90 degrees, where the chart norm(d_ref + a e1 + b e2) flattens out and the round would drift
(|(a, b)| about 1e5) until its iteration budget. SciPy 1.17 ends a round whose callback raises StopIteration at the last accepted
point with status 99; for the joint fit that status means "re-centre and go on", never convergence (the next round decides, by
the unchanged rules: status 0 or 2, then the Newton decrement). The charge-only fit runs exactly as in stage 1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy
from scipy import linalg, optimize

from . import joint, light_model
from .likelihood import EventData, Model, Objective, frame

GTOL = 1e-6
MAX_ITERATIONS = 200
MAX_ROUNDS = 6
CHART_STEP = 1e-4
DECREMENT_TOL = 1e-8
CALLBACK_STOP = 99            # SciPy's status when a callback raised StopIteration
JOINT_CHART_RADIUS = 1.0      # a joint round ends once |(a, b)| > 1 (45 degrees) and re-centres (case O-chart-exit)
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
    t0: float | None = None              # the joint fit's t0 (ns); None in a charge-only fit


@dataclass(frozen=True)
class JointSeed:
    vertex: numpy.ndarray
    direction: numpy.ndarray
    e_vis: float
    t0: float


JOINT_ORIGINS = ("charge-only fit", "charge-only fit, last point", "charge seed")


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
            uncertainty="not-formed", decrement=None, t0=None):
    e1, e2 = frame(direction) if direction is not None else (None, None)
    return FitResult("failed", failure, vertex, direction, e_vis, None, uncertainty, ln_l, grad, decrement, iterations, rounds,
                     e1, e2, t0)


def fit_event(model: Model, event: EventData, start: Seed | None = None) -> FitResult:
    start = start if start is not None else seed(model, event)
    if start is None:
        return _failed("no-hit-channel", None)
    return _rounds(lambda d: Objective(model, event, d), start, start.vertex, start.direction, [start.e_vis])


def joint_seed(model: Model, tev):
    """(JointSeed or None, the charge-only prefit or None, its origin of JOINT_ORIGINS or None), from the data alone."""
    first = seed(model, tev.event)
    if first is None:
        return None, None, None
    prefit = fit_event(model, tev.event, first)
    if prefit.vertex is not None:
        vertex, direction, e_vis = prefit.vertex, prefit.direction, prefit.e_vis
        origin = JOINT_ORIGINS[0] if prefit.status == "converged" else JOINT_ORIGINS[1]
    else:
        vertex, direction, e_vis, origin = first.vertex, first.direction, first.e_vis, JOINT_ORIGINS[2]
    hit = tev.event.hit
    dist = numpy.linalg.norm(model.geometry.positions[hit] - vertex, axis=1)
    t0 = float(numpy.median(tev.time[hit] - dist / model.cfg.photon_speed_m_per_ns))
    return JointSeed(numpy.asarray(vertex, float), numpy.asarray(direction, float), float(e_vis), t0), prefit, origin


def fit_joint_event(model: Model, tev, start: JointSeed | None = None) -> FitResult:
    start = start if start is not None else joint_seed(model, tev)[0]
    if start is None:
        return _failed("no-hit-channel", None)
    return _rounds(lambda d: joint.Objective(model, tev, d), start, start.vertex, start.direction, [start.e_vis, start.t0],
                   chart_radius=JOINT_CHART_RADIUS)


def _chart_exit(radius):
    """A callback that ends a round once its chart step exceeds radius (SciPy 1.17: status 99 at the last accepted point)."""
    def callback(intermediate_result):
        if math.hypot(intermediate_result.x[3], intermediate_result.x[4]) > radius:
            raise StopIteration
    return callback


def _rounds(objective_of, start, vertex, direction, tail, chart_radius=None) -> FitResult:
    """Stage 1's chart rounds, convergence rule, failure kinds and covariance, for p = (x, y, z, a, b, *tail): tail [E_vis]
    (charge-only, 6 coordinates) or [E_vis, t0] (joint, 7). chart_radius: the joint round's chart exit (None: stage 1's
    rounds exactly)."""
    size = 5 + len(tail)
    vertex = numpy.asarray(vertex, float)
    direction = numpy.asarray(direction, float) / numpy.linalg.norm(direction)
    tail = [float(v) for v in tail]
    iterations = 0
    for rounds in range(1, MAX_ROUNDS + 1):
        objective = objective_of(direction)
        p0 = numpy.r_[vertex, 0.0, 0.0, tail]
        if not math.isfinite(objective.value(p0)):
            return _failed("non-finite", start, iterations, rounds - 1)
        extra = {} if chart_radius is None else {"callback": _chart_exit(chart_radius)}
        res = optimize.minimize(lambda p: -objective.value(p), p0, method="trust-exact",
                                jac=lambda p: -objective.derivatives(p)[1], hess=lambda p: -objective.derivatives(p)[2],
                                options={"gtol": GTOL, "maxiter": MAX_ITERATIONS}, **extra)
        iterations += int(res.nit)
        vertex, tail = res.x[:3].copy(), [float(v) for v in res.x[5:]]
        direction = objective.direction(res.x[3], res.x[4])
        if not (numpy.all(numpy.isfinite(res.x)) and math.isfinite(objective.value(res.x))):
            return _failed("non-finite", start, iterations, rounds)
        point = (vertex, direction, tail[0])
        t0 = tail[1] if size == 7 else None
        if res.nit >= MAX_ITERATIONS:
            return _failed("iteration-budget", start, iterations, rounds, *point, -float(res.fun), t0=t0)
        chart_exit = chart_radius is not None and res.status == CALLBACK_STOP
        if res.status not in (0, 2) and not chart_exit:
            return _failed("not-converged", start, iterations, rounds, *point, -float(res.fun), t0=t0)
        if math.hypot(res.x[3], res.x[4]) < CHART_STEP and not chart_exit:
            break
    else:
        return _failed("iteration-budget", start, iterations, MAX_ROUNDS, vertex, direction, tail[0], t0=tail[1] if size == 7 else None)
    t0 = tail[1] if size == 7 else None
    e_vis = tail[0]
    recentred = objective_of(direction)
    ln_l, gradient, hessian = recentred.derivatives(numpy.r_[vertex, 0.0, 0.0, tail])
    grad_norm = float(numpy.linalg.norm(gradient))
    if not (numpy.all(numpy.isfinite(hessian)) and math.isfinite(ln_l)):
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, "non-finite",
                       t0=t0)
    try:
        factor = linalg.cho_factor(-hessian, lower=True)
    except linalg.LinAlgError:
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm,
                       "not-positive-definite", t0=t0)
    covariance = linalg.cho_solve(factor, numpy.eye(size))
    covariance = 0.5 * (covariance + covariance.T)
    decrement = float(gradient @ covariance @ gradient)
    if not numpy.all(numpy.isfinite(covariance)) or numpy.any(numpy.diag(covariance) <= 0):
        return _failed("no-finite-covariance", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, "non-finite",
                       t0=t0)
    if not decrement <= DECREMENT_TOL:
        return _failed("not-converged", start, iterations, rounds, vertex, direction, e_vis, ln_l, grad_norm, decrement=decrement,
                       t0=t0)
    return FitResult("converged", None, vertex, direction, e_vis, covariance, "ok", ln_l, grad_norm, decrement, iterations, rounds,
                     recentred.e1, recentred.e2, t0)

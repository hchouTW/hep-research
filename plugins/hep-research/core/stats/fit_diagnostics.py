#!/usr/bin/env python3
"""Fit results that carry their convergence status, and a record of every fit a computation made.

newton_fit() is the damped Newton search with numerical derivatives that the shape, goodness-of-fit and two-POI
likelihoods use. Its steps are unchanged; what it adds is a verdict. After the search stops, the gradient and
Hessian are evaluated at the returned point and the fit is "converged" only if

- the value is finite (an invalid domain, such as a negative Poisson mean, is +inf and never accepted),
- the Hessian of the free parameters is positive definite (a flat or downward direction fails), and
- the estimated distance to the minimum EDM = g^T H^-1 g / 2 is at most EDM_TOL.

Otherwise it is "failed", with machine-readable reasons: invalid_domain, invalid_domain_nearby,
hessian_not_positive_definite, gradient_not_small, max_iterations, line_search_stalled. A minimum on a boundary of the
parameter space is not judged by this interior criterion: the caller checks it with the constrained (KKT) condition,
see boundary_kkt().

EDM_TOL = 1e-5 in units of the negative log-likelihood is the threshold ROOT's Minuit2 applies with its default
tolerance (EDM < 0.002 * 0.01 * UP, UP = 0.5); a test statistic q = 2 Delta NLL is then known to about 2e-5, far below
the z^2 = 2.7 that defines a 95% limit. DNLL_TOL = 1e-4 is the largest global-minus-conditional NLL violation accepted
as floating-point and EDM noise (five times EDM_TOL); larger violations trigger a refit or a failure.

FitLog counts fits by context ("observed" for the data being reported, "toy" for pseudo-experiments) so a result can
state how many fits failed and why, and the CLI can set its status and exit code from it.
Standard library only.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from core.stats._linalg import cholesky, solve

EDM_TOL = 1e-5
DNLL_TOL = 1e-4
INVALID = math.inf


class FitError(ValueError):
    """Raised by the linear algebra inside the fit (caught: a singular step is retried with more damping)."""


@dataclass
class FitResult:
    x: list
    fval: float
    status: str                       # "converged" | "failed"
    reasons: list = field(default_factory=list)
    iterations: int = 0
    edm: float | None = None
    stop: str = ""                    # why the search stopped: step_small, no_improvement, max_iterations, invalid_start

    @property
    def ok(self) -> bool:
        return self.status == "converged"

    def as_dict(self) -> dict:
        return {"status": self.status, "reasons": list(self.reasons), "iterations": self.iterations,
                "edm": self.edm, "stop": self.stop, "fval": self.fval if math.isfinite(self.fval) else None}


def _derivatives(f, x, free, fx):
    h = {i: 1e-4 * max(1.0, abs(x[i])) for i in free}

    def at(d):
        z = list(x)
        for i, v in d.items():
            z[i] += v
        return f(z)
    g = [(at({i: h[i]}) - at({i: -h[i]})) / (2 * h[i]) for i in free]
    hess = [[0.0] * len(free) for _ in free]
    for a, i in enumerate(free):
        hess[a][a] = (at({i: h[i]}) - 2 * fx + at({i: -h[i]})) / h[i] ** 2
        for b2 in range(a + 1, len(free)):
            j = free[b2]
            v = (at({i: h[i], j: h[j]}) - at({i: h[i], j: -h[j]}) - at({i: -h[i], j: h[j]}) + at({i: -h[i], j: -h[j]})) / (4 * h[i] * h[j])
            hess[a][b2] = hess[b2][a] = v
    return g, hess


def _verdict(f, x, free, fx, stop, iterations, edm_tol) -> FitResult:
    reasons = []
    if not math.isfinite(fx):
        return FitResult(list(x), fx, "failed", ["invalid_domain"], iterations, None, stop)
    if not free:
        return FitResult(list(x), fx, "converged", [], iterations, 0.0, stop)
    g, hess = _derivatives(f, x, free, fx)
    if not all(math.isfinite(v) for v in g) or not all(math.isfinite(v) for r in hess for v in r):
        reasons.append("invalid_domain_nearby")
    edm = None
    if not reasons:
        try:
            cholesky(hess, "Hessian", error=FitError)
        except FitError:
            reasons.append("hessian_not_positive_definite")
        else:
            step = solve(hess, [[v] for v in g], error=FitError, what="Hessian")
            edm = 0.5 * sum(gv * s[0] for gv, s in zip(g, step))
            if not edm <= edm_tol:
                reasons.append("gradient_not_small")
    if reasons:
        if stop == "max_iterations":
            reasons.append("max_iterations")
        elif stop == "no_improvement":
            reasons.append("line_search_stalled")
    return FitResult(list(x), fx, "failed" if reasons else "converged", reasons, iterations, edm, stop)


def newton_fit(f, x0, fixed_first: bool = False, max_iter: int = 60, edm_tol: float = EDM_TOL) -> FitResult:
    """Minimize f over x (damped Newton, numerical derivatives) and judge convergence (module docstring).
    With fixed_first the first coordinate is held and excluded from the verdict."""
    x = list(x0)
    free = list(range(1 if fixed_first else 0, len(x)))
    fx = f(x)
    lam = 1e-3
    stop, it = "max_iterations", 0
    if max_iter <= 0:
        return _verdict(f, x, free, fx, "max_iterations", 0, edm_tol)
    for it in range(1, max_iter + 1):  # noqa: B007 (it is the iteration count reported after the loop)
        g, hess = _derivatives(f, x, free, fx)
        improved = False
        dx = math.inf
        for _try in range(12):
            try:
                step = solve([[hess[a][c] + (lam * (1 + abs(hess[a][a])) if a == c else 0.0) for c in range(len(free))]
                              for a in range(len(free))], [[-v] for v in g], error=FitError, what="damped Hessian")
            except Exception:  # a singular or overflowing step: retry with more damping
                lam *= 10.0
                continue
            z = list(x)
            for a, i in enumerate(free):
                z[i] += step[a][0]
            fz = f(z)
            if fz < fx:
                dx = max(abs(step[a][0]) for a in range(len(free)))
                x, fx, lam, improved = z, fz, max(lam / 5.0, 1e-9), True
                break
            lam *= 10.0
        if not improved:
            stop = "no_improvement"
            break
        if dx < 1e-9:
            stop = "step_small"
            break
    return _verdict(f, x, free, fx, stop, it, edm_tol)


def boundary_kkt(f, x, index: int, bound: float, scale: float = 1.0, tol: float = 1e-4) -> tuple[bool, float]:
    """KKT check of a minimum on the lower bound x[index] = bound: the one-sided derivative into the allowed region
    must not be negative (beyond tol * scale). Returns (ok, derivative). The other coordinates are assumed to be at
    their conditional minimum (checked by that fit's own verdict), so by the envelope theorem the partial derivative
    equals the derivative of the profile."""
    h = 1e-6 * max(1.0, abs(bound)) / max(scale, 1e-12)
    z = list(x)
    z[index] = bound + h
    fz, f0 = f(z), f(x)
    d = (fz - f0) / h
    return (math.isfinite(d) and d >= -tol * max(scale, 1.0)), d


class FitLog:
    """Counts of fits and their failure reasons, by context ("observed" or "toy"), plus named events."""

    def __init__(self) -> None:
        self.context = "observed"
        self.fits: Counter = Counter()
        self.failed: Counter = Counter()
        self.reasons: dict[str, Counter] = {"observed": Counter(), "toy": Counter()}
        self.events: Counter = Counter()

    def record(self, r: FitResult) -> FitResult:
        self.fits[self.context] += 1
        if not r.ok:
            self.failed[self.context] += 1
            self.reasons.setdefault(self.context, Counter()).update(r.reasons)
        return r

    def fail(self, reason: str) -> None:
        """A failure found outside a single fit (for example the global minimum above a conditional one)."""
        self.failed[self.context] += 1
        self.reasons.setdefault(self.context, Counter())[reason] += 1

    def failures(self, context: str | None = None) -> int:
        return self.failed[context or self.context]

    def summary(self) -> dict:
        out = {c: {"fits": self.fits[c], "failed": self.failed[c], "reasons": dict(self.reasons.get(c, {}))}
               for c in ("observed", "toy")}
        out["events"] = dict(self.events)
        return out

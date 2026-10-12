#!/usr/bin/env python3
"""Tail probabilities estimated from a finite number of toys, and exact tails kept in log space.

A toy p-value is a binomial proportion: k exceedances among n toys. When k = 0 the toys only bound the tail
(p < 1 - alpha^(1/n) at one-sided confidence 1 - alpha); reporting p = 0, Z = infinity or a binomial error of 0 claims
a precision the toys do not have. toy_tail() returns the count, the estimate when it is resolved, the exact
(Clopper-Pearson) interval and the one-sided bound at an edge, with the convention named. Exact Poisson tails far
beyond the toys' reach stay in log space (log_poisson_tail, z_from_log_tail) so they never underflow to 0.

Importable: betainc, beta_ppf, clopper_pearson, one_sided_upper, one_sided_lower, toy_tail, log_poisson_tail,
z_from_log_tail. Standard library only.
"""
from __future__ import annotations

import math
import numbers

INTERVAL_CL = 0.6827  # central interval reported with every toy estimate (about +-1 sigma)
BOUND_CL = 0.95       # one-sided bound reported at k = 0 or k = n
CONVENTION = "clopper-pearson"


class TailError(ValueError):
    """Raised for an invalid count, toy number or confidence level."""


def _check(k, n, cl=None) -> None:
    if isinstance(n, bool) or not isinstance(n, numbers.Integral) or int(n) < 1:
        raise TailError(f"the toy count must be a positive integer, got {n!r} (no toys: no tail estimate)")
    if isinstance(k, bool) or not isinstance(k, numbers.Integral) or not 0 <= int(k) <= int(n):
        raise TailError(f"the exceedance count must be an integer in [0, {n}], got {k!r}")
    if cl is not None and (isinstance(cl, bool) or not isinstance(cl, (int, float)) or not 0.0 < cl < 1.0):
        raise TailError(f"the confidence level must lie strictly between 0 and 1, got {cl!r}")


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the incomplete beta function (modified Lentz)."""
    tiny, eps = 1e-300, 1e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    raise TailError("incomplete beta continued fraction did not converge")


def _log_front(a: float, b: float, x: float) -> float:
    return math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) for a, b > 0."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(_log_front(a, b, x)) * _betacf(a, b, x) / a
    return 1.0 - math.exp(_log_front(b, a, 1.0 - x)) * _betacf(b, a, 1.0 - x) / b


def beta_ppf(q: float, a: float, b: float) -> float:
    """x with I_x(a, b) = q, by bisection; the midpoint is geometric while the bracket spans decades, so quantiles far
    below 1e-16 keep their relative precision."""
    if q <= 0.0:
        return 0.0
    if q >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(400):
        mid = math.sqrt(lo * hi) if lo > 0.0 and hi / lo > 4.0 else (0.5 * (lo + hi) if lo > 0.0 else
                                                                        (hi * 1e-3 if hi > 1e-300 else 0.5 * hi))
        if mid <= lo or mid >= hi:
            break
        if betainc(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-15 * hi:
            break
    return 0.5 * (lo + hi)


def clopper_pearson(k: int, n: int, cl: float = INTERVAL_CL) -> tuple[float, float]:
    """Central exact binomial interval for k successes in n trials (coverage >= cl for every true p)."""
    _check(k, n, cl)
    a = (1.0 - cl) / 2.0
    lo = 0.0 if k == 0 else beta_ppf(a, k, n - k + 1)
    hi = 1.0 if k == n else beta_ppf(1.0 - a, k + 1, n - k)
    return lo, hi


def one_sided_upper(k: int, n: int, cl: float = BOUND_CL) -> float:
    """Exact one-sided upper bound on p; for k = 0 it is 1 - (1 - cl)^(1/n)."""
    _check(k, n, cl)
    if k == n:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(1.0 - cl) / n)
    return beta_ppf(cl, k + 1, n - k)


def one_sided_lower(k: int, n: int, cl: float = BOUND_CL) -> float:
    """Exact one-sided lower bound on p; for k = n it is (1 - cl)^(1/n)."""
    _check(k, n, cl)
    if k == 0:
        return 0.0
    if k == n:
        return math.exp(math.log(1.0 - cl) / n)
    return beta_ppf(1.0 - cl, k, n - k + 1)


def toy_tail(k: int, n: int, cl: float = BOUND_CL, interval_cl: float = INTERVAL_CL) -> dict:
    """Record of a toy tail estimate: k of n toys at or beyond the observed value.

    estimate is k/n, or None when k = 0 (the toys bound the tail but do not measure it); binomial_error is the
    normal-approximation error, None at k = 0 or k = n where it is degenerate; interval is the central exact interval
    at interval_cl; at k = 0 an upper_bound and at k = n a lower_bound are given at one-sided confidence cl."""
    _check(k, n, cl)
    _check(k, n, interval_cl)
    k, n = int(k), int(n)
    out = {"k": k, "n": n, "convention": CONVENTION, "estimate": None if k == 0 else k / n,
           "resolved": 0 < k, "binomial_error": math.sqrt(k / n * (1 - k / n) / n) if 0 < k < n else None,
           "interval": list(clopper_pearson(k, n, interval_cl)), "interval_cl": interval_cl}
    if k == 0:
        out["upper_bound"] = {"value": one_sided_upper(0, n, cl), "cl": cl, "sided": "one-sided"}
        out["note"] = "no toy reached the observed value: the tail is below the bound, not zero; add toys to resolve it"
    if k == n:
        out["lower_bound"] = {"value": one_sided_lower(n, n, cl), "cl": cl, "sided": "one-sided"}
    return out


def log_poisson_tail(n: int, mu: float) -> float:
    """log P(N >= n | mu), summed in log space (no underflow; delegates to poisson_diagnostics.log_poisson_sf)."""
    from core.stats.poisson_diagnostics import log_poisson_sf
    return log_poisson_sf(n, mu)


def z_from_log_tail(log_p: float) -> float | None:
    """One-sided Z from log p without forming 1 - p (poisson_diagnostics.z_from_log_p)."""
    from core.stats.poisson_diagnostics import z_from_log_p
    return z_from_log_p(log_p)

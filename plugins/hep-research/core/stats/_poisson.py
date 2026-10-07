"""Shared Poisson numerics for core/stats (private; standard library only).

One mean limit for every module (MAX_MEAN), and a cumulative distribution, tail and quantile that stay accurate up
to it: probabilities are summed in log space outward from the term nearest the mean of the summed side, never from
exp(-mu), which underflows above mu of about 745, and an upper tail is never formed as 1 - P(N <= n - 1), which
cancels to 0 below about 1e-16.
"""
from __future__ import annotations

import math
from statistics import NormalDist

MAX_MEAN = 1e5  # every core/stats Poisson routine accepts means up to this; costs grow like sqrt(mean) per call


def log_pmf(n: int, mu: float) -> float:
    if mu == 0.0:
        return 0.0 if n == 0 else -math.inf
    return n * math.log(mu) - mu - math.lgamma(n + 1)


def _log_sum_down(n: int, mu: float) -> float:
    """ln sum_{k <= n} P(k | mu) for n < mu: terms fall going down (ratio k / mu < 1)."""
    term = total = 1.0
    k = n
    while k > 0 and term > 1e-17 * total:
        term *= k / mu
        total += term
        k -= 1
    return log_pmf(n, mu) + math.log(total)


def _log_sum_up(n: int, mu: float) -> float:
    """ln sum_{k >= n} P(k | mu) for n > mu: terms fall going up (ratio mu / (k + 1) < 1)."""
    term = total = 1.0
    k = n
    while term > 1e-17 * total:
        k += 1
        term *= mu / k
        total += term
    return log_pmf(n, mu) + math.log(total)


def log_cdf(n: int, mu: float) -> float:
    """ln P(N <= n | mu)."""
    if n < 0:
        return -math.inf
    if mu == 0.0:
        return 0.0
    if n < mu:
        return _log_sum_down(n, mu)
    return math.log1p(-math.exp(_log_sum_up(n + 1, mu)))  # the complement holds less than about half


def log_sf(n: int, mu: float) -> float:
    """ln P(N >= n | mu)."""
    if n <= 0:
        return 0.0
    if mu == 0.0:
        return -math.inf
    if n > mu:
        return _log_sum_up(n, mu)
    return math.log1p(-math.exp(_log_sum_down(n - 1, mu)))


def cdf(n: int, mu: float) -> float:
    return math.exp(log_cdf(n, mu))


def sf(n: int, mu: float) -> float:
    return math.exp(log_sf(n, mu))


def ppf(u: float, mu: float) -> int:
    """Smallest k with P(N <= k | mu) >= u: a normal-approximation start, then a walk with the exact cdf."""
    if mu <= 0.0 or u <= 0.0:
        return 0
    if mu < 700.0:  # exp(-mu) is a normal double: plain inversion, the same draw as summing from k = 0
        term = cum = math.exp(-mu)
        k = 0
        while u > cum and k < 20 * int(mu + 20):
            k += 1
            term *= mu / k
            cum += term
        return k
    u = min(u, 1.0 - 1e-16)
    k = max(0, int(mu + math.sqrt(mu) * NormalDist().inv_cdf(u)))
    c = cdf(k, mu)
    while c < u:
        k += 1
        c += math.exp(log_pmf(k, mu))
    while k > 0 and c - math.exp(log_pmf(k, mu)) >= u:
        c -= math.exp(log_pmf(k, mu))
        k -= 1
    return k

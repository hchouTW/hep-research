"""Quantiles and distribution functions of Student's t and Fisher's F for non-integer degrees of freedom, built on the
regularized incomplete beta of core.stats.tail_estimation (one implementation per quantity). Standard library only.

t: P(|T| > t) = I_{nu/(nu + t^2)}(nu/2, 1/2); F: P(F <= f) = I_{d1 f/(d1 f + d2)}(d1/2, d2/2) (Abramowitz and Stegun
26.7.1 and 26.6.2). The Poisson (Garwood) interval is core.stats.poisson_diagnostics.central_interval, not here."""
from __future__ import annotations

import math

from core.stats.tail_estimation import beta_ppf, betainc


class DistributionError(ValueError):
    """Invalid probability or degrees of freedom."""


def _dof(nu: float, name: str = "nu") -> float:
    if isinstance(nu, bool) or not isinstance(nu, (int, float)) or not math.isfinite(nu) or nu <= 0:
        raise DistributionError(f"{name} must be a finite positive number of degrees of freedom, not {nu!r}")
    return float(nu)


def _prob(q: float) -> float:
    if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0.0 < q < 1.0:
        raise DistributionError(f"probability must be in (0, 1), not {q!r}")
    return float(q)


def t_cdf(t: float, nu: float) -> float:
    """P(T <= t) for Student's t with nu degrees of freedom."""
    nu = _dof(nu)
    if t == 0:
        return 0.5
    tail = 0.5 * betainc(nu / 2.0, 0.5, nu / (nu + t * t))  # P(T > |t|)
    return 1.0 - tail if t > 0 else tail


def t_ppf(q: float, nu: float) -> float:
    """t with P(T <= t) = q, for Student's t with nu (possibly non-integer) degrees of freedom."""
    q, nu = _prob(q), _dof(nu)
    if q == 0.5:
        return 0.0
    p2 = 2.0 * min(q, 1.0 - q)  # two-sided tail probability P(|T| > |t|)
    x = beta_ppf(p2, nu / 2.0, 0.5)
    t = math.sqrt(nu * (1.0 - x) / x) if x > 0 else math.inf
    return t if q > 0.5 else -t


def f_cdf(f: float, d1: float, d2: float) -> float:
    """P(F <= f) for Fisher's F with (d1, d2) degrees of freedom."""
    d1, d2 = _dof(d1, "d1"), _dof(d2, "d2")
    if f <= 0:
        return 0.0
    return betainc(d1 / 2.0, d2 / 2.0, d1 * f / (d1 * f + d2))


def f_ppf(q: float, d1: float, d2: float) -> float:
    """f with P(F <= f) = q, for Fisher's F with (d1, d2) (possibly non-integer) degrees of freedom."""
    q, d1, d2 = _prob(q), _dof(d1, "d1"), _dof(d2, "d2")
    x = beta_ppf(q, d1 / 2.0, d2 / 2.0)
    return d2 * x / (d1 * (1.0 - x)) if x < 1.0 else math.inf

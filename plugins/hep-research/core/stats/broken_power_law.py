#!/usr/bin/env python3
"""The one broken-power-law parametrization of the plugin (STH Q8).

Used by skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py and skills/hep-statistics/scripts/covariance_fit.py,
so both tools give the same model value for the same parameters:

    ln F(x) = ln A - gamma1 (u - h(u)) - gamma2 h(u),   u = ln(x / x_b)
    h(u) = max(u, 0)                      sharp break (smoothness s = 0 or None)
    h(u) = s ln((1 + e^(u/s)) / 2)        smooth break, s > 0

that is F = A (x/x_b)^-gamma1 below and A (x/x_b)^-gamma2 above a sharp break, and
F = A (x/x_b)^-gamma1 [(1 + (x/x_b)^(1/s)) / 2]^(-(gamma2 - gamma1) s) for a smooth one.

Conventions: parameters [ln A, gamma1, gamma2, ln x_b]; the indices are positive for a falling spectrum; A is the
value at the break, F(x_b) = A, for the sharp and the smooth form alike (the factor 1/2 inside the bracket sets this;
without it A would be F(x_b) 2^((gamma2 - gamma1) s)); s is the width of the transition in ln x, and the smooth form
tends to the sharp one with the same parameters as s -> 0. x is whatever abscissa the caller fits (kinetic energy,
energy per nucleon, rigidity), in the caller's units; x_b is in the same units. The model is continuous at x_b and is
linear in (ln A, gamma1, gamma2) at a fixed break: basis() gives the two columns.

Importable: break_shape, basis, log_flux. Floats use the standard library; NumPy arrays (if NumPy is installed) are
evaluated elementwise with the same formula. No CLI.
"""
from __future__ import annotations

import math

LN2 = math.log(2.0)


def _smoothness(smoothness) -> float:
    s = 0.0 if smoothness is None else float(smoothness)
    if not math.isfinite(s) or s < 0:
        raise ValueError("smoothness must be finite and >= 0 (0 or None: sharp break)")
    return s


def _softplus(z: float) -> float:
    """ln(1 + e^z) without overflow."""
    return z + math.log1p(math.exp(-z)) if z > 0 else math.log1p(math.exp(z))


def break_shape(u, smoothness=None):
    """h(u), u = ln(x / x_b): max(u, 0) (sharp) or s ln((1 + e^(u/s)) / 2) (smooth, s > 0). Float or array."""
    s = _smoothness(smoothness)
    if isinstance(u, (int, float)):
        u = float(u)
        return max(u, 0.0) if s == 0 else s * (_softplus(u / s) - LN2)
    import numpy as np  # array path only
    u = np.asarray(u, dtype=float)
    return np.maximum(u, 0.0) if s == 0 else s * (np.logaddexp(0.0, u / s) - LN2)


def basis(u, smoothness=None):
    """(u - h(u), h(u)): ln F = ln A - gamma1 * first - gamma2 * second."""
    h = break_shape(u, smoothness)
    return u - h, h


def log_flux(x, log_a, gamma1, gamma2, log_xb, smoothness=None):
    """ln F at x (float or array, x > 0) for the parameters [ln A, gamma1, gamma2, ln x_b]."""
    if isinstance(x, (int, float)):
        if not (math.isfinite(x) and x > 0):
            raise ValueError("a power law needs a finite x > 0")
        u = math.log(x) - log_xb
    else:
        import numpy as np
        u = np.log(np.asarray(x, dtype=float)) - log_xb
    first, second = basis(u, smoothness)
    return log_a - gamma1 * first - gamma2 * second

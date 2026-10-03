#!/usr/bin/env python3
"""Evaluate the Gaisser-Hillas air-shower longitudinal profile.

Purpose: given the four Gaisser-Hillas parameters (N_max, X_max, X0, lambda),
evaluate the number of charged particles N(X) at any atmospheric slant depth, the
shower age parameter, and the depths at which the profile falls to a given fraction
of its maximum on either side of X_max - the standard way to characterize a
longitudinal profile's width, not just its peak. See
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/extensive-air-showers.md. This is an evaluator for a given or
externally fitted parameter set, not a nonlinear curve fitter: extracting these four
parameters from raw simulated or measured (X, N) samples requires a nonlinear least-
squares fit, which is outside the closed-form, no-minimizer scope this skill's
scripts otherwise keep to (contrast ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/calorimeter_resolution.py, whose
three-term model is linear in its parameters and so is fit exactly).

What it does: evaluates
    N(X) = N_max * ((X - X0)/(X_max - X0))^((X_max - X0)/lambda) * exp((X_max - X)/lambda)
at one or more depths, confirms N(X_max) == N_max as a self-consistency check, and
computes the shower age s(X) = 3*(X - X0) / ((X - X0) + 2*(X_max - X0)), which is 1 at
X = X_max by construction and is the variable shower-universality parameterizations
(${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/extensive-air-showers.md) use to compare showers of different energy
and mass on a common footing.

Usage notes / assumptions: standard library only. Depths in g/cm^2. Requires
X_max > X0 and lambda > 0; N(X) is defined and evaluated only for X > X0 (the model is
not defined at or before the extrapolated first-interaction depth).
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/xmax_gaisser_hillas.py --n-max 2e7 --x-max 750 --x0 -60 --lambda-param 60 --depths 400,600,750,900,1100
"""
import argparse
import json
import math


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0:
        raise ValueError(f'{name} must be greater than zero')
    return float(value)


def gaisser_hillas(depth, n_max, x_max, x0, lam):
    """N(X) at a single depth; nan for depth <= x0 (model undefined there)."""
    if depth <= x0:
        return float('nan')
    if x_max <= x0:
        raise ValueError('x_max must be greater than x0')
    exponent = (x_max - x0) / lam
    base = (depth - x0) / (x_max - x0)
    return n_max * (base ** exponent) * math.exp((x_max - depth) / lam)


def shower_age(depth, x_max, x0):
    """s(X) = 3*(X - X0) / ((X - X0) + 2*(X_max - X0)); s=1 at X=X_max, s=0 at X=X0."""
    if x_max <= x0:
        raise ValueError('x_max must be greater than x0')
    return 3.0 * (depth - x0) / ((depth - x0) + 2.0 * (x_max - x0))


def half_max_depths(n_max, x_max, x0, lam, fraction=0.5, tolerance=1e-6, max_iterations=200):
    """Bisect for the depths on each side of x_max where N(X) falls to `fraction` of
    n_max, by monotonic bisection (N(X) is unimodal: rising for X<x_max, falling for
    X>x_max)."""
    target = fraction * n_max

    def n_of(depth):
        return gaisser_hillas(depth, n_max, x_max, x0, lam)

    # Rising side: bracket between x0 (N->0) and x_max (N=n_max).
    lo, hi = x0 + 1e-9 * max(abs(x0), 1.0), x_max
    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        if n_of(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tolerance:
            break
    rising_depth = (lo + hi) / 2.0

    # Falling side: expand outward from x_max until N drops below target, then bisect.
    step = max(lam, 1.0)
    upper = x_max + step
    while n_of(upper) > target:
        upper += step
        if upper > x_max + 1e6:
            raise ValueError('could not bracket the falling half-maximum depth; check parameters')
    lo, hi = x_max, upper
    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        if n_of(mid) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tolerance:
            break
    falling_depth = (lo + hi) / 2.0

    return rising_depth, falling_depth


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n-max', type=float, required=True, dest='n_max', help='peak particle number')
    parser.add_argument('--x-max', type=float, required=True, dest='x_max', help='depth of maximum, g/cm^2')
    parser.add_argument('--x0', type=float, required=True, help='depth offset (first-interaction), g/cm^2')
    parser.add_argument('--lambda-param', type=float, required=True, dest='lam',
                        help='shape/attenuation length, g/cm^2')
    parser.add_argument('--depths', type=str, default=None,
                        help='comma-separated depths (g/cm^2) at which to evaluate N(X)')
    args = parser.parse_args()

    try:
        n_max = _finite(args.n_max, 'n_max', positive=True)
        x_max = _finite(args.x_max, 'x_max')
        x0 = _finite(args.x0, 'x0')
        lam = _finite(args.lam, 'lam', positive=True)
        if x_max <= x0:
            raise ValueError('x_max must be greater than x0')

        result = {
            'n_max': n_max, 'x_max': x_max, 'x0': x0, 'lambda_g_cm2': lam,
            'n_at_x_max_check': gaisser_hillas(x_max, n_max, x_max, x0, lam),
        }

        if args.depths:
            depths = [float(d) for d in args.depths.split(',')]
            result['profile'] = [
                {'depth': d, 'n': gaisser_hillas(d, n_max, x_max, x0, lam),
                 'shower_age': shower_age(d, x_max, x0) if d > x0 else None}
                for d in depths
            ]

        rising, falling = half_max_depths(n_max, x_max, x0, lam)
        result['half_maximum_depths'] = {'rising_edge': rising, 'falling_edge': falling,
                                         'full_width_half_maximum': falling - rising}
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({'method': 'Gaisser-Hillas profile evaluation (closed-form, not a fit)', **result}, indent=2))


if __name__ == '__main__':
    main()

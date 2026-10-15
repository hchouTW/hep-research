#!/usr/bin/env python3
"""Evaluate the Gaisser-Hillas air-shower longitudinal profile.

Purpose: given the four Gaisser-Hillas parameters (N_max, X_max, X0, lambda),
evaluate the number of charged particles N(X) at any atmospheric slant depth, the
shower age parameter, and the depths at which the profile falls to a given fraction
of its maximum on either side of X_max - the standard way to characterize a
longitudinal profile's width, not just its peak. See
<plugin root>/skills/hep-detector/references/extensive-air-showers.md. This is an evaluator for a given or
externally fitted parameter set, not a nonlinear curve fitter: extracting these four
parameters from raw simulated or measured (X, N) samples requires a nonlinear least-
squares fit, which is outside the closed-form, no-minimizer scope this skill's
scripts otherwise keep to (contrast <plugin root>/skills/hep-detector/scripts/calorimeter_resolution.py, whose
three-term model is linear in its parameters and so is fit exactly).

What it does: evaluates
    N(X) = N_max * ((X - X0)/(X_max - X0))^((X_max - X0)/lambda) * exp((X_max - X)/lambda)
at one or more depths, written with u = (X - X_max)/(X_max - X0) as
    N(X) = N_max * exp(((X_max - X0)/lambda) * (log1p(u) - u)),
which is the same function in exact arithmetic but has an exponent that is never positive
and no cancellation between two large terms when X_max >> lambda; it confirms
N(X_max) == N_max as a self-consistency check, and computes two shower ages, both equal
to 1 at X = X_max:
  shower_age          s(X) = 3*(X - X0) / ((X - X0) + 2*(X_max - X0)), the version
                      shifted by X0 (s = 0 at X = X0); internally consistent with the
                      Gaisser-Hillas X0, but not the definition universality studies use.
  shower_age_standard s(X) = 3X / (X + 2 X_max), the standard age that shower-universality
                      parameterizations (<plugin root>/skills/hep-detector/references/extensive-air-showers.md)
                      use to compare showers of different energy and mass.
For X=400, X_max=750, X0=-60 they give 0.663 and 0.632; quote which one is used.

Usage notes / assumptions: standard library only. Depths in g/cm^2. Requires
X_max > X0 and lambda > 0; N(X) is defined and evaluated only for X > X0 (the model is
not defined at or before the extrapolated first-interaction depth; the CLI reports null
there). Depths must be finite.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed (JSON with ok false); 2 invalid input (JSON with error_kind invalid-input).
Run: python3 <plugin root>/skills/hep-detector/scripts/xmax_gaisser_hillas.py --n-max 2e7 --x-max 750 --x0 -60 --lambda-param 60 --depths 400,600,750,900,1100
"""
import argparse
import json
import math
import sys

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0:
        raise ValueError(f'{name} must be greater than zero')
    return float(value)


def gaisser_hillas(depth, n_max, x_max, x0, lam):
    """N(X) at a single depth; nan for depth <= x0 (model undefined there).

    Evaluated as N_max * exp(e * (log1p(u) - u)) with e = (X_max - X0)/lambda and
    u = (X - X_max)/(X_max - X0). This equals N_max * base^e * exp((X_max - X)/lambda) with
    base = 1 + u, but log1p(u) - u <= 0 for u > -1, so the exponent never overflows, and the
    two terms e*ln(base) and (X_max - X)/lambda, each of order e*u, no longer cancel
    numerically when X_max >> lambda.
    """
    if depth <= x0:
        return float('nan')
    if x_max <= x0:
        raise ValueError('x_max must be greater than x0')
    span = x_max - x0
    exponent = span / lam
    if not math.isfinite(exponent):
        raise OverflowError('lambda is too small relative to (x_max - x0)')
    u = (depth - x_max) / span
    return n_max * math.exp(exponent * (math.log1p(u) - u))


def shower_age(depth, x_max, x0):
    """s(X) = 3*(X - X0) / ((X - X0) + 2*(X_max - X0)); s=1 at X=X_max, s=0 at X=X0.

    The X0-shifted age; see shower_age_standard for the universality definition.
    """
    if x_max <= x0:
        raise ValueError('x_max must be greater than x0')
    return 3.0 * (depth - x0) / ((depth - x0) + 2.0 * (x_max - x0))


def shower_age_standard(depth, x_max):
    """s(X) = 3X / (X + 2 X_max), the age used by shower-universality studies; None for X < 0."""
    if x_max <= 0:
        raise ValueError('x_max must be greater than zero for the standard age')
    if depth < 0:
        return None
    return 3.0 * depth / (depth + 2.0 * x_max)


def half_max_depths(n_max, x_max, x0, lam, fraction=0.5, tolerance=1e-6, max_iterations=200):
    """Bisect for the depths on each side of x_max where N(X) falls to `fraction` of
    n_max, by monotonic bisection (N(X) is unimodal: rising for X<x_max, falling for
    X>x_max)."""
    target = fraction * n_max
    if math.sqrt(lam * (x_max - x0)) < 100.0 * tolerance:
        raise OverflowError('lambda is too small relative to (x_max - x0): the profile width '
                            'sqrt(lambda (x_max - x0)) is below the depth resolution of the '
                            'half-maximum search')

    def n_of(depth):
        return gaisser_hillas(depth, n_max, x_max, x0, lam)

    # Rising side: bracket between x0 (N->0) and x_max (N=n_max).
    lo, hi = x0 + 1e-9 * max(abs(x0), 1.0), x_max
    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        if mid in (lo, hi):
            break
        if n_of(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tolerance:
            break
    rising_depth = (lo + hi) / 2.0

    # Falling side: expand outward from x_max with a doubling step (starting near the profile
    # width sqrt(lambda (x_max - x0))) until N drops below target, then bisect.
    step = max(lam, math.sqrt(lam * (x_max - x0)), abs(x_max) * 1e-12, 1.0)
    upper = x_max + step
    while n_of(upper) > target:
        step *= 2.0
        following = x_max + step
        if following == upper or not math.isfinite(following):
            raise ValueError('could not bracket the falling half-maximum depth; check parameters')
        upper = following
    lo, hi = x_max, upper
    for _ in range(max_iterations):
        mid = (lo + hi) / 2.0
        if mid in (lo, hi):
            break
        if n_of(mid) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tolerance:
            break
    falling_depth = (lo + hi) / 2.0

    return rising_depth, falling_depth


def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'xmax_gaisser_hillas.py: error: {message}', file=sys.stderr)
    return 1


def _none_if_nan(value):
    return None if value is None or math.isnan(value) else value


def main():
    parser = JsonArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n-max', type=float, required=True, dest='n_max', help='peak particle number')
    parser.add_argument('--x-max', type=float, required=True, dest='x_max', help='depth of maximum, g/cm^2')
    parser.add_argument('--x0', type=float, required=True, help='depth offset (first-interaction), g/cm^2')
    parser.add_argument('--lambda-param', type=float, required=True, dest='lam',
                        help='shape/attenuation length, g/cm^2')
    parser.add_argument('--depths', type=str, default=None,
                        help='comma-separated finite depths (g/cm^2) at which to evaluate N(X)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the parameters, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        n_max = _finite(args.n_max, 'n_max', positive=True)
        x_max = _finite(args.x_max, 'x_max')
        x0 = _finite(args.x0, 'x0')
        lam = _finite(args.lam, 'lam', positive=True)
        if x_max <= x0:
            raise ValueError('x_max must be greater than x0')
        if not math.isfinite((x_max - x0) / lam):
            raise ValueError('lambda is too small relative to (x_max - x0)')
        depths = []
        if args.depths:
            for text in args.depths.split(','):
                try:
                    depth = float(text)
                except ValueError:
                    raise ValueError(f'depth {text!r} is not a number') from None
                depths.append(_finite(depth, 'each depth'))
    except ValueError as exc:
        parser.error(str(exc))

    try:
        result = {
            'n_max': n_max, 'x_max': x_max, 'x0': x0, 'lambda_g_cm2': lam,
            'n_at_x_max_check': gaisser_hillas(x_max, n_max, x_max, x0, lam),
        }
        if depths:
            result['profile'] = [
                {'depth': d, 'n': _none_if_nan(gaisser_hillas(d, n_max, x_max, x0, lam)),
                 'shower_age': shower_age(d, x_max, x0) if d > x0 else None,
                 'shower_age_standard': shower_age_standard(d, x_max) if x_max > 0 else None}
                for d in depths
            ]
            result['shower_age_definitions'] = {
                'shower_age': '3(X - X0) / ((X - X0) + 2(X_max - X0)), shifted by X0',
                'shower_age_standard': '3X / (X + 2 X_max), the universality definition',
            }

        rising, falling = half_max_depths(n_max, x_max, x0, lam)
        result['half_maximum_depths'] = {'rising_edge': rising, 'falling_edge': falling,
                                         'full_width_half_maximum': falling - rising}
        text = json.dumps({'status': args.status, 'method': 'Gaisser-Hillas profile evaluation (closed-form, not a fit)',
                           **result}, indent=2, allow_nan=False)
    except OverflowError as exc:
        message = str(exc)
        if not message.startswith('lambda'):
            message = 'lambda is too small relative to (x_max - x0)'
        return _fail(message)
    except (ValueError, ZeroDivisionError) as exc:
        message = str(exc)
        if 'JSON compliant' in message:
            message = 'result contains a non-finite number for these parameters'
        return _fail(message)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

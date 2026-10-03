#!/usr/bin/env python3
"""Li & Ma (1983) likelihood-ratio significance for an ON/OFF counting measurement.

Purpose: the field-standard significance for ON-source vs. OFF-source (background)
Poisson counting, used throughout gamma-ray (IACT) and neutrino-astronomy point-source
analyses. It is the signed likelihood-ratio statistic S = sqrt(-2 ln lambda) of
signal-plus-background against background only (Li & Ma 1983, eq. 17), unlike the naive
Gaussian formula (N_on - alpha*N_off) / sqrt(N_on + alpha^2*N_off). Reading S as a
standard-normal deviate is asymptotic (Wilks): at small N_on or N_off the normal p-value
can be several times too small, so calibrate it with toys or an exact conditional test.
See
${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/astroparticle-statistics.md and
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/imaging-atmospheric-cherenkov.md.

What it does: computes the signed Li & Ma significance
    S = sqrt(2) * sqrt(N_on * ln[((1+alpha)/alpha) * N_on/(N_on+N_off)]
                       + N_off * ln[(1+alpha) * N_off/(N_on+N_off)])
      = sqrt(-2 ln lambda)
sign(N_on - alpha*N_off), handling the N_on = 0 and N_off = 0 boundary terms (where a
0*ln(0) term is defined as 0) explicitly rather than raising a math domain error.

Usage notes / assumptions: standard library only. N_on and N_off are nonnegative
integers; alpha is the ON/OFF exposure or normalization ratio, a finite positive
number (not necessarily 1). This is a significance for one already-chosen ON region
and time/energy window - it does not include a trials/look-elsewhere correction for a
scan over multiple positions, bins, or windows (see
${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/astroparticle-statistics.md and ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/counting_reference.py's
docstring for the analogous single-bin caveat).
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/li_ma_significance.py --on 15 --off 5 --alpha 0.5
"""
import argparse
import json
import math


def _nonnegative_int(value, name):
    if isinstance(value, bool) or type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _positive_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def _term(count, factor, ratio):
    """count * ln(factor * ratio), defined as 0 when count == 0 (0*ln(0) := 0)."""
    if count == 0:
        return 0.0
    if ratio <= 0.0:
        raise ValueError('internal ratio must be positive when its count is nonzero')
    return count * math.log(factor * ratio)


def li_ma_significance(n_on, n_off, alpha):
    """Signed Li & Ma (1983) significance for ON/OFF Poisson counting.

    Returns a dict with the significance, the excess, and the two log-likelihood
    terms it was built from.
    """
    n_on = _nonnegative_int(n_on, 'n_on')
    n_off = _nonnegative_int(n_off, 'n_off')
    alpha = _positive_finite(alpha, 'alpha')

    total = n_on + n_off
    excess = n_on - alpha * n_off

    if total == 0:
        return {
            'n_on': n_on, 'n_off': n_off, 'alpha': alpha,
            'excess': 0.0, 'significance': 0.0,
            'on_term': 0.0, 'off_term': 0.0,
            'note': 'no counts in either region; significance is zero by convention',
        }

    on_term = _term(n_on, (1.0 + alpha) / alpha, n_on / total)
    off_term = _term(n_off, 1.0 + alpha, n_off / total)
    radicand = 2.0 * (on_term + off_term)
    # Guard against a tiny negative radicand from floating-point cancellation at the
    # N_on == alpha*N_off boundary, where the true value is exactly zero.
    magnitude = math.sqrt(radicand) if radicand > 0.0 else 0.0
    significance = math.copysign(magnitude, excess) if excess != 0 else 0.0

    return {
        'n_on': n_on, 'n_off': n_off, 'alpha': alpha,
        'excess': excess, 'significance': significance,
        'on_term': on_term, 'off_term': off_term,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--on', type=int, required=True, dest='n_on', help='ON-region counts')
    parser.add_argument('--off', type=int, required=True, dest='n_off', help='OFF-region counts')
    parser.add_argument('--alpha', type=float, required=True,
                        help='ON/OFF exposure or normalization ratio')
    args = parser.parse_args()
    try:
        result = li_ma_significance(args.n_on, args.n_off, args.alpha)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({
        'method': 'Li & Ma (1983) likelihood-ratio significance',
        **result,
        'caveat': 'No trials/look-elsewhere correction applied; see ${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/astroparticle-statistics.md.',
    }, indent=2))


if __name__ == '__main__':
    main()

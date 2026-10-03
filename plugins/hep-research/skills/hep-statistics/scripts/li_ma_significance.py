#!/usr/bin/env python3
"""Li & Ma (1983) likelihood-ratio significance for an ON/OFF counting measurement.

Purpose: the field-standard significance for ON-source vs. OFF-source (background)
Poisson counting, used throughout gamma-ray (IACT) and neutrino-astronomy point-source
analyses. It is the signed likelihood-ratio statistic S = sqrt(-2 ln lambda) of
signal-plus-background against background only (Li & Ma 1983, eq. 17), unlike the naive
Gaussian formula (N_on - alpha*N_off) / sqrt(N_on + alpha^2*N_off). Reading S as a
standard-normal deviate is asymptotic (Wilks): at small N_on or N_off the normal p-value
can be several times too small, so for low counts calibrate it with --toys or
--exact-conditional. See
${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/astroparticle-statistics.md and
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/imaging-atmospheric-cherenkov.md.

What it does: computes the signed Li & Ma significance
    S = sqrt(2) * sqrt(N_on * ln[((1+alpha)/alpha) * N_on/(N_on+N_off)]
                       + N_off * ln[(1+alpha) * N_off/(N_on+N_off)])
      = sqrt(-2 ln lambda)
sign(N_on - alpha*N_off), handling the N_on = 0 and N_off = 0 boundary terms (where a
0*ln(0) term is defined as 0) explicitly rather than raising a math domain error.
Optional one-sided p-values for an excess, each labeled with its method:
  --toys N --seed S      toy-calibrated p-value: background-only pseudo-experiments with
                         the background fitted to the observed counts under the null,
                         b = (N_on+N_off)/(1+alpha) (plug-in, not a supremum over b);
                         reports the binomial Monte Carlo error, or a 95% binomial upper
                         bound when no toy exceeds the observation.
  --exact-conditional    the conditional binomial test N_on | N_on+N_off ~
                         Bin(N_on+N_off, alpha/(1+alpha)); free of the background
                         nuisance and conservative for discrete data.
With either flag the asymptotic (Wilks) p-value is listed too. Without them the output
is unchanged.

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
import bisect
import json
import math
import random


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


def _sf_normal(z):
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def exact_conditional_p(n_on, n_off, alpha):
    """P(X >= n_on) for X ~ Bin(n_on + n_off, alpha / (1 + alpha)): conservative for discrete data."""
    n = n_on + n_off
    pi = alpha / (1.0 + alpha)
    if n == 0:
        return 1.0
    log_terms = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                 + (k * math.log(pi) if k else 0.0) + ((n - k) * math.log1p(-pi) if n - k else 0.0)
                 for k in range(n_on, n + 1)]
    peak = max(log_terms)
    return min(1.0, math.exp(peak) * math.fsum(math.exp(x - peak) for x in log_terms))


def _poisson_table(mean):
    """Cumulative probabilities for inverse-transform sampling, up to a tail below 1e-16."""
    if mean == 0:
        return [1.0]
    cdf, term, k = [], math.exp(-mean), 0
    total = 0.0
    if term == 0.0:  # large mean: start from the log-space term
        raise ValueError('background mean too large for the toy sampler (above ~700 counts)')
    while True:
        total += term
        cdf.append(total)
        k += 1
        term *= mean / k
        if k > mean and term < 1e-16:
            break
    cdf[-1] = max(cdf[-1], 1.0)
    return cdf


def toy_p_value(n_on, n_off, alpha, toys, seed):
    """Background-only toys with the background fitted under the null (plug-in)."""
    observed = li_ma_significance(n_on, n_off, alpha)['significance']
    b = (n_on + n_off) / (1.0 + alpha)
    table_on, table_off = _poisson_table(alpha * b), _poisson_table(b)
    rng = random.Random(seed)
    cache = {}
    exceed = 0
    for _ in range(toys):
        key = (bisect.bisect_left(table_on, rng.random()), bisect.bisect_left(table_off, rng.random()))
        if key not in cache:
            cache[key] = li_ma_significance(key[0], key[1], alpha)['significance']
        if cache[key] >= observed - 1e-9:
            exceed += 1
    row = {'method': 'toys-plugin-background',
           'label': 'toy-calibrated under the background-only hypothesis with the background fitted to the '
                    'observed counts (plug-in); not a supremum over the background',
           'toys': toys, 'seed': seed, 'exceedances': exceed, 'background_off_mean': b}
    if exceed == 0:
        row.update(p_value=None, p_upper_95=1.0 - 0.05 ** (1.0 / toys),
                   note='no toy reached the observed value; the p-value is only bounded')
    else:
        p = exceed / toys
        row.update(p_value=p, mc_error=math.sqrt(p * (1.0 - p) / toys))
    return row


def p_values(n_on, n_off, alpha, toys=None, seed=None, exact=False):
    s = li_ma_significance(n_on, n_off, alpha)['significance']
    rows = [{'method': 'asymptotic-wilks', 'p_value': _sf_normal(s),
             'label': 'standard-normal reading of S (Wilks); accuracy degrades at small N_on, N_off'}]
    if toys:
        rows.append(toy_p_value(n_on, n_off, alpha, toys, seed))
    if exact:
        rows.append({'method': 'exact-conditional-binomial', 'p_value': exact_conditional_p(n_on, n_off, alpha),
                     'label': 'conditional binomial test on N_on given N_on+N_off; conservative for discrete data'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--on', type=int, required=True, dest='n_on', help='ON-region counts')
    parser.add_argument('--off', type=int, required=True, dest='n_off', help='OFF-region counts')
    parser.add_argument('--alpha', type=float, required=True,
                        help='ON/OFF exposure or normalization ratio')
    parser.add_argument('--toys', type=int, help='number of background-only toys for a calibrated p-value')
    parser.add_argument('--seed', type=int, help='random seed (required with --toys)')
    parser.add_argument('--exact-conditional', action='store_true',
                        help='add the conditional binomial p-value (conservative)')
    args = parser.parse_args()
    if args.toys is not None:
        if args.toys < 1:
            parser.error('--toys must be a positive integer')
        if args.seed is None:
            parser.error('--toys needs --seed so the result can be reproduced')
    try:
        result = li_ma_significance(args.n_on, args.n_off, args.alpha)
        rows = p_values(args.n_on, args.n_off, args.alpha, args.toys, args.seed, args.exact_conditional) \
            if args.toys or args.exact_conditional else None
    except ValueError as exc:
        parser.error(str(exc))
    out = {
        'method': 'Li & Ma (1983) likelihood-ratio significance',
        **result,
        'caveat': 'No trials/look-elsewhere correction applied; see ${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/astroparticle-statistics.md.',
    }
    if rows is not None:
        out['p_values'] = rows
        out['p_value_note'] = ('one-sided p-values for an excess; the asymptotic value is only a large-count '
                               'approximation, prefer the toy or exact conditional value at low counts')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()

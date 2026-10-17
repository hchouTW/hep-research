#!/usr/bin/env python3
"""Ratio or fraction of two yields: delta-method propagation, or exact intervals for raw counts.

Purpose: the common building block behind positron-fraction and antiproton/proton-
ratio-style measurements (see the bound experiment profile's instrument overview and
<plugin root>/skills/hep-statistics/references/astroparticle-statistics.md): two yields from independent template
fits or counts, each with its own uncertainty, combined into a ratio N1/N2 or a
fraction N1/(N1+N2). Unlike <plugin root>/skills/hep-detector/scripts/tag_and_probe_efficiency.py (a single binomial
pass/total count with a shared denominator), this is for two genuinely independent
yields - e.g. a positron yield and an electron yield each extracted from its own
template fit - and does NOT assume they come from a single binomial trial.

What it does (--method):
  delta (default): given (N1, sigma1) and (N2, sigma2), Gaussian-uncertain yields (independent unless
    --correlation is given), computes the ratio N1/N2 and the fraction N1/(N1+N2) with their
uncertainties from standard first-order (delta-method) error propagation:
    sigma_ratio = ratio * sqrt((sigma1/N1)^2 + (sigma2/N2)^2)
    sigma_fraction = fraction * (1 - fraction) * sqrt((sigma1/N1)^2 + (sigma2/N2)^2)
An optional correlation coefficient rho (default 0, i.e. independent) between the two
yields is supported, adding the standard cross term; a nonzero rho is required
whenever the two yields share a systematic (e.g. the same acceptance/exposure
normalization, or the same background-template shape uncertainty) rather than being
truly independent - see the acceptance-cancellation discussion in
the bound experiment profile's instrument overview for when this matters.

  binomial-fraction: raw integer counts n1, n2; the fraction n1/(n1+n2) with the exact central
    Clopper-Pearson interval (core/stats tail_estimation.clopper_pearson) at --level.
  poisson-ratio: raw integer counts from two independent Poisson processes; conditional on the total,
    n1 is binomial with p = r/(1+r), so the Clopper-Pearson interval on p maps to an interval on the ratio
    of the means r (exact, conservative). n1 = 0 gives a lower end 0 (a one-sided interval); n2 = 0 an upper
    end of infinity (reported as null).

Usage notes / assumptions: standard library only. The delta method is first-order and valid when
sigma1/N1 and sigma2/N2 are small; the output warns when either relative uncertainty exceeds 20%, where
the exact methods (raw counts) or a likelihood interval should be used instead. The exact methods need
the raw counts, not background-subtracted or weighted yields.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed; 2 usage or invalid input (NaN, inf, malformed file);
3 incomplete or inconclusive.
Run: python3 <plugin root>/skills/hep-measurement/scripts/particle_ratio_with_uncertainty.py --n1 1200 --sigma1 40 --n2 85000 --sigma2 300
     python3 <plugin root>/skills/hep-measurement/scripts/particle_ratio_with_uncertainty.py --n1 1200 --sigma1 40 --n2 85000 --sigma2 300 --correlation 0.2
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.stats.tail_estimation import clopper_pearson  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


def _positive_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def _nonnegative_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')
    return float(value)


def _validate_correlation(rho):
    if isinstance(rho, bool) or not isinstance(rho, (int, float)) or not math.isfinite(rho) or not -1.0 <= rho <= 1.0:
        raise ValueError('correlation must be finite and between -1 and 1')
    return float(rho)


def ratio_and_fraction(n1, sigma1, n2, sigma2, correlation=0.0):
    """Ratio N1/N2 and fraction N1/(N1+N2) with delta-method uncertainties for two
    (possibly correlated) independent-yield measurements."""
    n1 = _positive_finite(n1, 'n1')
    n2 = _positive_finite(n2, 'n2')
    sigma1 = _nonnegative_finite(sigma1, 'sigma1')
    sigma2 = _nonnegative_finite(sigma2, 'sigma2')
    rho = _validate_correlation(correlation)

    rel1 = sigma1 / n1
    rel2 = sigma2 / n2

    ratio = n1 / n2
    # d(ratio)/d(n1) = 1/n2, d(ratio)/d(n2) = -n1/n2^2; covariance term uses rho*sigma1*sigma2.
    var_ratio_rel = rel1 ** 2 + rel2 ** 2 - 2.0 * rho * rel1 * rel2
    sigma_ratio = ratio * math.sqrt(max(var_ratio_rel, 0.0))

    fraction = n1 / (n1 + n2)
    # d(fraction)/d(n1) = n2/(n1+n2)^2, d(fraction)/d(n2) = -n1/(n1+n2)^2.
    total = n1 + n2
    dfdn1 = n2 / (total ** 2)
    dfdn2 = -n1 / (total ** 2)
    var_fraction = (dfdn1 ** 2) * (sigma1 ** 2) + (dfdn2 ** 2) * (sigma2 ** 2) \
        + 2.0 * dfdn1 * dfdn2 * rho * sigma1 * sigma2
    sigma_fraction = math.sqrt(max(var_fraction, 0.0))

    return {
        'n1': n1, 'sigma1': sigma1, 'n2': n2, 'sigma2': sigma2, 'correlation': rho,
        'ratio': ratio, 'sigma_ratio': sigma_ratio,
        'fraction': fraction, 'sigma_fraction': sigma_fraction,
        'relative_uncertainty_n1': rel1, 'relative_uncertainty_n2': rel2,
    }


METHODS = ('delta', 'poisson-ratio', 'binomial-fraction')
LARGE_RELATIVE_UNCERTAINTY = 0.2


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < 0 or float(value) != int(value):
        raise ValueError(f'{name} must be a nonnegative integer count for the exact methods')
    return int(value)


def exact_ratio_and_fraction(n1, n2, method, level=0.6827):
    """Exact interval from raw counts: 'binomial-fraction' (n1/(n1+n2)) or 'poisson-ratio' (ratio of Poisson means,
    conditional on the total)."""
    n1, n2 = _count(n1, 'n1'), _count(n2, 'n2')
    if n1 + n2 == 0:
        raise ValueError('n1 + n2 must be at least 1')
    if isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 < level < 1:
        raise ValueError('level must lie strictly between 0 and 1')
    f_lo, f_hi = clopper_pearson(n1, n1 + n2, level)
    out = {'n1': n1, 'n2': n2, 'level': level, 'fraction': n1 / (n1 + n2), 'fraction_interval': [f_lo, f_hi]}
    if method == 'poisson-ratio':
        out['ratio'] = n1 / n2 if n2 else None
        out['ratio_interval'] = [f_lo / (1.0 - f_lo), f_hi / (1.0 - f_hi) if f_hi < 1.0 else None]
        out['interval_kind'] = 'upper-limit' if n1 == 0 else ('lower-limit' if n2 == 0 else 'two-sided')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n1', type=float, required=True, help='first (numerator) yield or raw count')
    parser.add_argument('--sigma1', type=float, help='uncertainty on n1 (delta method)')
    parser.add_argument('--n2', type=float, required=True, help='second yield or raw count')
    parser.add_argument('--sigma2', type=float, help='uncertainty on n2 (delta method)')
    parser.add_argument('--method', choices=METHODS, default='delta',
                        help='delta (default), poisson-ratio or binomial-fraction (the last two take raw counts)')
    parser.add_argument('--level', type=float, default=0.6827, help='confidence level of the exact intervals')
    parser.add_argument('--correlation', type=float, default=0.0,
                        help='correlation coefficient between n1 and n2 (default 0, independent)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        if args.method == 'delta':
            if args.sigma1 is None or args.sigma2 is None:
                raise ValueError('the delta method needs --sigma1 and --sigma2')
            result = ratio_and_fraction(args.n1, args.sigma1, args.n2, args.sigma2, args.correlation)
            label = 'first-order (delta-method) error propagation (correlation %g)' % result['correlation']
            result['caveat'] = 'Gaussian/delta-method approximation - not valid for large relative uncertainty on either yield.'
            if max(result['relative_uncertainty_n1'], result['relative_uncertainty_n2']) > LARGE_RELATIVE_UNCERTAINTY:
                result['warning'] = ('a relative uncertainty exceeds 20%: the delta method is unreliable here; with raw '
                                     'counts use --method poisson-ratio or binomial-fraction')
        else:
            if args.correlation:
                raise ValueError('--correlation applies to the delta method only')
            result = exact_ratio_and_fraction(args.n1, args.n2, args.method, args.level)
            label = {'poisson-ratio': 'exact ratio of Poisson means, conditional binomial (Clopper-Pearson) interval',
                     'binomial-fraction': 'exact Clopper-Pearson interval on the fraction'}[args.method]
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({'status': args.status, 'method': label, **result}, indent=2))


if __name__ == '__main__':
    main()

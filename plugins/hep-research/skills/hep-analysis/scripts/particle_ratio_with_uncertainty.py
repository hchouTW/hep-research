#!/usr/bin/env python3
"""Ratio or fraction of two independent yields, with exact error propagation.

Purpose: the common building block behind positron-fraction and antiproton/proton-
ratio-style measurements (see ${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/modules/subsystems/instrument-overview.md and
${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/37-astroparticle-statistics.md): two yields from independent template
fits or counts, each with its own uncertainty, combined into a ratio N1/N2 or a
fraction N1/(N1+N2). Unlike ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/tag_and_probe_efficiency.py (a single binomial
pass/total count with a shared denominator), this is for two genuinely independent
yields - e.g. a positron yield and an electron yield each extracted from its own
template fit - and does NOT assume they come from a single binomial trial.

What it does: given (N1, sigma1) and (N2, sigma2), treated as independent Gaussian-
uncertain yields, computes the ratio N1/N2 and the fraction N1/(N1+N2) with their
uncertainties from standard first-order (delta-method) error propagation:
    sigma_ratio = ratio * sqrt((sigma1/N1)^2 + (sigma2/N2)^2)
    sigma_fraction = fraction * (1 - fraction) * sqrt((sigma1/N1)^2 + (sigma2/N2)^2)
An optional correlation coefficient rho (default 0, i.e. independent) between the two
yields is supported, adding the standard cross term; a nonzero rho is required
whenever the two yields share a systematic (e.g. the same acceptance/exposure
normalization, or the same background-template shape uncertainty) rather than being
truly independent - see the acceptance-cancellation discussion in
${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/modules/subsystems/instrument-overview.md for when this matters.

Usage notes / assumptions: standard library only. This is first-order (delta-method)
propagation, valid when sigma1/N1 and sigma2/N2 are both reasonably small (say, below
~30%); for a low-count regime where either yield's relative uncertainty is large, a
full likelihood-based interval (as in ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/tag_and_probe_efficiency.py's exact
binomial treatment, if the two yields are in fact from one binomial trial) is more
reliable than this Gaussian approximation.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py --n1 1200 --sigma1 40 --n2 85000 --sigma2 300
     python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py --n1 1200 --sigma1 40 --n2 85000 --sigma2 300 --correlation 0.2
"""
import argparse
import json
import math


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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n1', type=float, required=True, help='first (numerator) yield')
    parser.add_argument('--sigma1', type=float, required=True, help='uncertainty on n1')
    parser.add_argument('--n2', type=float, required=True, help='second yield')
    parser.add_argument('--sigma2', type=float, required=True, help='uncertainty on n2')
    parser.add_argument('--correlation', type=float, default=0.0,
                        help='correlation coefficient between n1 and n2 (default 0, independent)')
    args = parser.parse_args()

    try:
        result = ratio_and_fraction(args.n1, args.sigma1, args.n2, args.sigma2, args.correlation)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({
        'method': 'first-order (delta-method) error propagation for two independent yields',
        **result,
        'caveat': 'Gaussian/delta-method approximation - not valid for large relative uncertainty on either yield.',
    }, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Differential cosmic-ray flux from raw counts, exposure, and bin width.

Purpose: the standard final step of any cosmic-ray counting measurement (ground
array, IACT, neutrino telescope, or a space-based magnetic spectrometer) -
turning selected event counts into a differential flux with a statistically correct
uncertainty - rather than leaving the statistics implicit. See
<plugin root>/skills/hep-statistics/references/astroparticle-statistics.md (exposure/forward-folding discipline) and
the bound experiment profile's instrument overview.

What it does: for one or more energy/rigidity bins, given the observed count N,
the exposure (effective area or geometric factor, times live time, times solid
angle - already integrated into one number per bin) and the bin width, computes

    flux = N / (exposure * bin_width)

with an exact Poisson confidence interval on N (via the same exact Poisson tail as
<plugin root>/skills/hep-analysis/scripts/counting_reference.py, not a Gaussian sqrt(N) approximation - important at
low counts, which is routine in the steeply falling high-energy tail this domain
always has), propagated onto the flux by the same multiplicative factor. Optionally
accepts a background count to subtract (with its own Poisson uncertainty, combined
in quadrature on the subtracted count - a Gaussian approximation for the *background
subtraction* step specifically, appropriate once the background itself is not also
in the single-digit-count regime; for a low-count ON/OFF comparison use
<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py for the significance and treat the subtracted flux
here as an estimate, not a rigorous interval).

Usage notes / assumptions: standard library only. Exposure and bin width must be
finite and positive; counts must be nonnegative integers. The exact-Poisson interval inherits <plugin root>/skills/hep-analysis/scripts/counting_reference.py's supported rate
range of 0-500, so the confidence-interval search can fail for an observed count
approaching that ceiling - how close depends on the confidence level, since the
upper bound is always somewhat above the observed count itself; the script reports a
clear error rather than a silently truncated interval if the true bound would exceed
500. For any count in that regime the Gaussian sqrt(N) approximation is in any case
adequate and this exact tool is unnecessary. This computes a flux point
per bin from an already-known exposure - it does not itself compute effective area,
acceptance, or livetime, which are instrument-specific (see
<plugin root>/skills/detector-response/references/detector-systems-overview.md for acceptance/geometric-factor
definitions) and must be supplied. Does not itself forward-fold through an energy
migration matrix; see <plugin root>/skills/hep-analysis/references/measurements-and-unfolding.md and
<plugin root>/skills/hep-statistics/references/astroparticle-statistics.md for why a steeply falling spectrum should
be compared via forward-folding rather than treating each bin's flux point as
migration-free.
Run: python3 <plugin root>/skills/hep-analysis/scripts/cosmic_ray_flux.py --counts 42 --exposure 1.5e7 --bin-width 10
     python3 <plugin root>/skills/hep-analysis/scripts/cosmic_ray_flux.py --counts 42 --background 8 --background-sigma 1.5 --exposure 1.5e7 --bin-width 10
"""
import argparse
import json
import math

from counting_reference import poisson_upper_tail

MAX_POISSON_INPUT = 500


def _positive_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def _nonnegative_int(value, name):
    if isinstance(value, bool) or type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _nonnegative_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')
    return float(value)


def poisson_interval(observed, level=0.6827):
    """Exact (Garwood) Poisson confidence interval on an observed integer count,
    via bisection on the exact tail probabilities used in counting_reference.py.
    level=0.6827 (~1 sigma) by default; the interval is [lower, upper] on the true
    rate given one observed count and no background. Both observed and the searched
    rate are limited to at most MAX_POISSON_INPUT (500), inherited from
    counting_reference.py's own supported range."""
    if observed < 0 or type(observed) is not int:
        raise ValueError('observed must be a nonnegative integer')
    if observed > MAX_POISSON_INPUT:
        raise ValueError(f'observed must be at most {MAX_POISSON_INPUT} for the exact Poisson '
                         'interval (counting_reference.py\'s supported range); use the Gaussian '
                         'sqrt(N) approximation for larger counts')
    alpha = 1.0 - level

    def upper_tail(rate, count):
        return poisson_upper_tail(count, rate)

    def invert(target_count, target_prob, lo_bound, hi_bound):
        lo, hi = lo_bound, hi_bound
        for _ in range(200):
            mid = (lo + hi) / 2.0
            if upper_tail(mid, target_count) > target_prob:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2.0

    def bounded_search_ceiling(target_count, target_prob):
        # upper_tail(rate, target_count) increases monotonically with rate; grow the
        # bracket only while it has not yet reached target_prob, and stop (bracket
        # found) as soon as it has, rather than continuing to grow past it.
        hi_bound = min(max(target_count * 2.0, 10.0), MAX_POISSON_INPUT)
        while upper_tail(hi_bound, target_count) < target_prob and hi_bound < MAX_POISSON_INPUT:
            hi_bound = min(hi_bound * 2.0, MAX_POISSON_INPUT)
        if upper_tail(hi_bound, target_count) < target_prob:
            raise ValueError(f'the requested interval cannot be bounded within the exact tool\'s '
                             f'supported rate range (0-{MAX_POISSON_INPUT}); use a lower confidence '
                             'level or the Gaussian sqrt(N) approximation')
        return hi_bound

    if observed == 0:
        lower = 0.0
    else:
        # Lower (Garwood) bound solves P(X >= observed | rate) = alpha/2.
        hi_bound = bounded_search_ceiling(observed, alpha / 2.0)
        lower = invert(observed, alpha / 2.0, 0.0, hi_bound)

    # Upper (Garwood) bound solves P(X >= observed+1 | rate) = 1 - alpha/2. This can
    # itself require a rate above MAX_POISSON_INPUT even when observed is well below
    # it (the upper bound is always somewhat above observed); bounded_search_ceiling
    # raises its own clear error in that case rather than this function pre-guessing
    # a fixed safe threshold, since the true threshold is confidence-level-dependent.
    hi_bound = bounded_search_ceiling(observed + 1, 1.0 - alpha / 2.0)
    upper = invert(observed + 1, 1.0 - alpha / 2.0, 0.0, hi_bound)

    return lower, upper


def flux_from_counts(counts, exposure, bin_width, background=0.0, background_sigma=0.0, level=0.6827):
    """Differential flux and its uncertainty for one bin.

    counts: observed integer count (source region, before background subtraction).
    exposure: effective area/geometric factor * live time * solid angle (one number).
    bin_width: width of the energy/rigidity bin, in the same units the flux should
    be differential in.
    background, background_sigma: an optional estimated background count and its
    uncertainty, subtracted before computing flux (Gaussian combination for the
    subtraction step; use li_ma_significance.py for a low-count ON/OFF significance).
    """
    counts = _nonnegative_int(counts, 'counts')
    exposure = _positive_finite(exposure, 'exposure')
    bin_width = _positive_finite(bin_width, 'bin_width')
    background = _nonnegative_finite(background, 'background')
    background_sigma = _nonnegative_finite(background_sigma, 'background_sigma')

    lower, upper = poisson_interval(counts, level)
    net_counts = counts - background
    # Net-count uncertainty: exact Poisson width on the raw count (asymmetric),
    # combined with the (Gaussian) background uncertainty in quadrature on each side.
    lower_net = net_counts - math.sqrt((counts - lower) ** 2 + background_sigma ** 2)
    upper_net = net_counts + math.sqrt((upper - counts) ** 2 + background_sigma ** 2)

    denom = exposure * bin_width
    return {
        'counts': counts,
        'background': background,
        'background_sigma': background_sigma,
        'net_counts': net_counts,
        'exposure': exposure,
        'bin_width': bin_width,
        'poisson_interval_level': level,
        'raw_count_interval': [lower, upper],
        'net_count_interval': [lower_net, upper_net],
        'flux': net_counts / denom,
        'flux_lower': lower_net / denom,
        'flux_upper': upper_net / denom,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--counts', type=int, required=True, help='observed integer count')
    parser.add_argument('--exposure', type=float, required=True,
                        help='exposure: effective area/geometric factor * live time * solid angle')
    parser.add_argument('--bin-width', type=float, required=True, dest='bin_width',
                        help='energy/rigidity bin width, in the units flux should be differential in')
    parser.add_argument('--background', type=float, default=0.0, help='estimated background count to subtract')
    parser.add_argument('--background-sigma', type=float, default=0.0, dest='background_sigma',
                        help='uncertainty on the background estimate')
    parser.add_argument('--level', type=float, default=0.6827,
                        help='Poisson interval confidence level (default 0.6827, ~1 sigma)')
    args = parser.parse_args()

    try:
        result = flux_from_counts(args.counts, args.exposure, args.bin_width,
                                  args.background, args.background_sigma, args.level)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({
        'method': 'exact Poisson interval on raw counts, Gaussian-combined background subtraction',
        **result,
    }, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Differential cosmic-ray flux from raw counts, exposure, and bin width.

Purpose: the standard final step of any cosmic-ray counting measurement (ground
array, IACT, neutrino telescope, or a space-based magnetic spectrometer) -
turning selected event counts into a differential flux with a statistically correct
uncertainty - rather than leaving the statistics implicit. See
<plugin root>/skills/hep-statistics/references/astroparticle-statistics.md (exposure/forward-folding discipline) and
the bound experiment profile's instrument overview.

What it does: for one bin, given the observed count N, the exposure (effective area
or geometric factor, times live time, times solid angle - already integrated into one
number per bin) and the bin width, computes flux = s / (exposure * bin_width) with an
interval on the signal mean s, chosen by --method:

  auto (default)    no background: garwood; known background (sigma 0): feldman-cousins;
                    uncertain background: cousins-highland.
  garwood           exact central (Garwood) interval on N, for any N up to core/stats' mean
                    limit (no background allowed). Conservative.
  feldman-cousins   unified interval on s >= 0 for a known background (grid scan in core/stats).
  cousins-highland  the Feldman-Cousins interval with the background marginalized over a
                    truncated normal prior: deterministic, average coverage only (an
                    approximation, named in the output note).
  profile-fc        Feldman-Cousins-style interval with the background profiled, seeded toys
                    (needs --toys and --seed); the choice for publication use with an
                    uncertain background.
  naive             the old subtraction (exact interval on the raw count, background error in
                    quadrature), labelled approximate; a negative value is clipped at 0 and
                    flagged in warnings.

The interval code is core/stats (poisson_diagnostics.central_interval and fc_interval,
likelihood_limits.profile_fc); this script only wraps it. No bound is ever negative: when
the lower end is 0 the output also gives flux_upper_limit. Above the Feldman-Cousins grid
limit (total mean 500) with a background, the script stops with exit 3 and names the
alternative (likelihood_limits.py profile-fc or an asymptotic construction); it never
truncates silently. --exposure-rel-uncertainty is reported as flux_syst_exposure, separate
from the statistical interval.

Bin-width unit: --bin-width-unit is required and is echoed as bin_width_unit. The width
must be in the unit the flux is differential in (per GV: 600 for a 1.2-1.8 TV bin; never
pass a width in TV when the flux is quoted per GV, which makes the flux 1000x too large).

Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the interval could not be computed (a core solve failed); 2 invalid
input or usage (nothing on stdout, one line on stderr); 3 unsupported range (the method's
grid or mean limit is exceeded; the message names the alternative).

Usage notes / assumptions: standard library only. Exposure and bin width must be
finite and positive; counts must be nonnegative integers. This computes a flux point
per bin from an already-known exposure - it does not itself compute effective area,
acceptance, or livetime, which are instrument-specific (see
<plugin root>/skills/hep-detector/references/detector-systems-overview.md for acceptance/geometric-factor
definitions) and must be supplied. Does not itself forward-fold through an energy
migration matrix; see <plugin root>/skills/hep-measurement/references/measurements-and-unfolding.md and
<plugin root>/skills/hep-statistics/references/astroparticle-statistics.md for why a steeply falling spectrum should
be compared via forward-folding rather than treating each bin's flux point as
migration-free.
Run: python3 <plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py --counts 42 --exposure 1.5e7 --bin-width 10 --bin-width-unit GV
     python3 <plugin root>/skills/hep-measurement/scripts/cosmic_ray_flux.py --counts 42 --background 8 --background-sigma 1.5 --exposure 1.5e7 --bin-width 10 --bin-width-unit GV
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.stats.poisson_diagnostics import FC_MAX_TOTAL_MEAN, DiagnosticsError, SolveFailed  # noqa: E402
from core.stats.poisson_diagnostics import central_interval, fc_interval  # noqa: E402

BIN_WIDTH_UNITS = ('GV', 'GeV', 'GeV/n', 'TeV', 'TV')
METHODS = ('auto', 'garwood', 'feldman-cousins', 'cousins-highland', 'profile-fc', 'naive')
APPROXIMATE_METHODS = ('naive', 'cousins-highland')
STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


class UnsupportedRange(ValueError):
    """The method's grid or mean limit is exceeded; the message names the alternative (exit 3)."""


class IntervalFailed(ValueError):
    """core/stats could not bracket an interval end (exit 1)."""


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
    """Exact (Garwood) central interval on the mean of an observed integer count, from
    core.stats.poisson_diagnostics.central_interval: any count up to core/stats' mean limit."""
    if observed < 0 or type(observed) is not int:
        raise ValueError('observed must be a nonnegative integer')
    try:
        iv = central_interval(observed, level)
    except SolveFailed as exc:
        raise IntervalFailed(str(exc)) from None
    except DiagnosticsError as exc:
        raise ValueError(str(exc)) from None
    return iv['lower'], iv['upper']


def _resolve_method(method, background, background_sigma):
    if method not in METHODS:
        raise ValueError(f'method must be one of {", ".join(METHODS)}')
    if method == 'auto':
        if background == 0 and background_sigma == 0:
            return 'garwood'
        return 'feldman-cousins' if background_sigma == 0 else 'cousins-highland'
    if method == 'garwood' and (background or background_sigma):
        raise ValueError('method garwood takes no background; use feldman-cousins, cousins-highland or profile-fc')
    if method == 'feldman-cousins' and background_sigma:
        raise ValueError('method feldman-cousins treats the background as known; with --background-sigma use '
                         'cousins-highland or profile-fc')
    return method


def _signal_interval(method, counts, background, background_sigma, level, toys, seed):
    """(lower, upper) on the signal mean, the method label, and core's approximation note."""
    if method == 'garwood':
        lo, hi = poisson_interval(counts, level)
        return lo, hi, 'Garwood central interval on the count (conservative), core/stats', None
    if method in ('feldman-cousins', 'cousins-highland'):
        sigma = background_sigma if method == 'cousins-highland' else 0.0
        try:
            iv = fc_interval(counts, background, level, sigma_b=sigma)
        except SolveFailed as exc:
            raise IntervalFailed(str(exc)) from None
        except DiagnosticsError as exc:
            if 'limited to total means' in str(exc):
                raise UnsupportedRange(f'{exc} (method {method}, total-mean limit {FC_MAX_TOTAL_MEAN:g})') from None
            raise ValueError(str(exc)) from None
        return iv['lower'], iv['upper'], iv['method'], iv['note']
    if method == 'profile-fc':
        from core.stats.likelihood_limits import LikelihoodError, profile_fc
        if toys is None or seed is None:
            raise ValueError('method profile-fc needs --toys and --seed')
        try:
            iv = profile_fc(counts, background, background_sigma, level, toys, seed)
        except LikelihoodError as exc:
            if 'above the script' in str(exc):
                raise UnsupportedRange(f'{exc}; use an asymptotic profile-likelihood construction') from None
            raise ValueError(str(exc)) from None
        return iv['lower'], iv['upper'], iv['method'], iv['note']
    raise ValueError(f'unknown method {method}')


def flux_from_counts(counts, exposure, bin_width, background=0.0, background_sigma=0.0, level=0.6827,
                     bin_width_unit=None, method='auto', toys=None, seed=None, exposure_rel_uncertainty=None):
    """Differential flux and its interval for one bin.

    counts: observed integer count (source region, before background subtraction).
    exposure: effective area/geometric factor * live time * solid angle (one number).
    bin_width: width of the energy/rigidity bin, in the same units the flux should
    be differential in (per GV: 600 for a 1.2-1.8 TV bin). bin_width_unit, when given,
    is one of BIN_WIDTH_UNITS and is echoed in the result.
    background, background_sigma: an optional expected background count and its
    uncertainty. method: one of METHODS (see the module docstring); toys and seed only
    for profile-fc. exposure_rel_uncertainty: optional relative exposure uncertainty,
    reported as flux_syst_exposure and never folded into the statistical interval.
    No returned bound is negative; flux_upper_limit is set when the lower end is 0.
    """
    counts = _nonnegative_int(counts, 'counts')
    exposure = _positive_finite(exposure, 'exposure')
    bin_width = _positive_finite(bin_width, 'bin_width')
    background = _nonnegative_finite(background, 'background')
    background_sigma = _nonnegative_finite(background_sigma, 'background_sigma')
    if isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 < level < 1:
        raise ValueError('level must be a confidence level strictly between 0 and 1')
    if bin_width_unit is not None and bin_width_unit not in BIN_WIDTH_UNITS:
        raise ValueError(f'bin_width_unit must be one of {", ".join(BIN_WIDTH_UNITS)}')
    if exposure_rel_uncertainty is not None:
        exposure_rel_uncertainty = _nonnegative_finite(exposure_rel_uncertainty, 'exposure_rel_uncertainty')
    method = _resolve_method(method, background, background_sigma)

    denom = exposure * bin_width
    if not (math.isfinite(denom) and denom > 0):
        raise ValueError('exposure * bin_width must be finite and greater than zero (it under- or overflows)')

    lower, upper = poisson_interval(counts, level)
    net_counts = counts - background
    note = None
    warnings = []
    if method == 'naive':
        # The old subtraction: exact width on the raw count combined with the (Gaussian)
        # background uncertainty in quadrature on each side. Approximate.
        try:
            lo_s = net_counts - math.sqrt((counts - lower) ** 2 + background_sigma ** 2)
            hi_s = net_counts + math.sqrt((upper - counts) ** 2 + background_sigma ** 2)
        except OverflowError:
            raise ValueError('the background uncertainty is too large to combine (overflow)') from None
        estimate = net_counts
        label = 'approximate: exact Poisson interval on raw counts, Gaussian-combined background subtraction'
        if min(lo_s, hi_s, estimate) < 0:
            warnings.append('the naive subtraction gave a negative value; it is clipped at 0 here. Use the default '
                            'method (Feldman-Cousins on s >= 0) for this bin')
            lo_s, hi_s, estimate = max(lo_s, 0.0), max(hi_s, 0.0), max(estimate, 0.0)
    else:
        lo_s, hi_s, label, note = _signal_interval(method, counts, background, background_sigma, level, toys, seed)
        estimate = max(net_counts, 0.0)
    flux = (estimate / denom, lo_s / denom, hi_s / denom)
    if not all(math.isfinite(f) for f in flux):
        raise ValueError('the flux is not finite for this exposure and bin width')
    out = {
        'method': label,
        'method_id': method,
        'approximate': method in APPROXIMATE_METHODS,
        'counts': counts,
        'background': background,
        'background_sigma': background_sigma,
        'net_counts': net_counts,
        'exposure': exposure,
        'bin_width': bin_width,
        'poisson_interval_level': level,
        'raw_count_interval': [lower, upper],
        'net_count_interval': [lo_s, hi_s],
        'flux': flux[0],
        'flux_lower': flux[1],
        'flux_upper': flux[2],
    }
    if lo_s == 0.0:
        out['interval_kind'] = 'upper-limit'
        out['flux_upper_limit'] = flux[2]
        if method == 'garwood':
            out['upper_limit_level'] = 1.0 - (1.0 - level) / 2.0  # one-sided level of a central interval's end
    else:
        out['interval_kind'] = 'two-sided'
    if bin_width_unit is not None:
        out['bin_width_unit'] = bin_width_unit
    if exposure_rel_uncertainty is not None:
        out['exposure_rel_uncertainty'] = exposure_rel_uncertainty
        out['flux_syst_exposure'] = flux[0] * exposure_rel_uncertainty
    if method == 'profile-fc':
        out['toys'], out['seed'] = toys, seed
    if note:
        out['note'] = note
    if warnings:
        out['warnings'] = warnings
    return out


UNIT_RULE = ('--bin-width-unit is required: give the bin width in the unit the flux is differential in '
             '(per GV: 600 for a 1.2-1.8 TV bin; never a width in TV for a flux per GV)')


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        if '--bin-width-unit' in message:
            message = f'{message}; {UNIT_RULE}'
        super().error(message)


def main():
    parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--counts', type=int, required=True, help='observed integer count')
    parser.add_argument('--exposure', type=float, required=True,
                        help='exposure: effective area/geometric factor * live time * solid angle')
    parser.add_argument('--bin-width', type=float, required=True, dest='bin_width',
                        help='energy/rigidity bin width, in the unit the flux is differential in '
                             '(per GV: 600 for a 1.2-1.8 TV bin; never a width in TV for a flux per GV)')
    parser.add_argument('--bin-width-unit', required=True, choices=BIN_WIDTH_UNITS, dest='bin_width_unit',
                        help='unit of --bin-width (required; echoed as bin_width_unit). The flux is per this unit')
    parser.add_argument('--background', type=float, default=0.0, help='expected background count')
    parser.add_argument('--background-sigma', type=float, default=0.0, dest='background_sigma',
                        help='uncertainty on the background expectation')
    parser.add_argument('--level', type=float, default=0.6827,
                        help='confidence level of the interval (default 0.6827, ~1 sigma)')
    parser.add_argument('--method', choices=METHODS, default='auto',
                        help='interval method (default auto: garwood, feldman-cousins or cousins-highland)')
    parser.add_argument('--toys', type=int, default=None, help='toys for --method profile-fc')
    parser.add_argument('--seed', type=int, default=None, help='seed for --method profile-fc')
    parser.add_argument('--exposure-rel-uncertainty', type=float, default=None, dest='exposure_rel_uncertainty',
                        help='relative exposure uncertainty, reported as flux_syst_exposure (not in the interval)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        result = flux_from_counts(args.counts, args.exposure, args.bin_width,
                                  args.background, args.background_sigma, args.level, args.bin_width_unit,
                                  args.method, args.toys, args.seed, args.exposure_rel_uncertainty)
    except UnsupportedRange as exc:
        print(f'{parser.prog}: unsupported range: {exc}', file=sys.stderr)
        return 3
    except IntervalFailed as exc:
        print(f'{parser.prog}: failed: {exc}', file=sys.stderr)
        return 1
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({'status': args.status, **result}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

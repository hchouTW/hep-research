#!/usr/bin/env python3
"""Power-law fit to a cosmic-ray (or gamma-ray) flux-vs-energy spectrum.

Purpose: extract a spectral index (and, for a segmented fit, per-segment indices and
a break energy) from measured (energy, flux) points, and propagate the flux's
statistical uncertainty into the index's uncertainty. See
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/30-cosmic-ray-spectrum-and-composition.md for why an energy-scale
uncertainty on a steeply falling spectrum matters more than it looks: this script
fits the index only, and does not itself convert an index uncertainty into an
energy-scale systematic - that conversion (`gamma * delta`) is done by hand from the
formula quoted in that reference.

What it does: fits log(flux) = log(A) - gamma * log(E) by exact weighted linear least
squares in log-log space (a single power law is linear in its two parameters over the
basis {1, log E}, so - like ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/calorimeter_resolution.py - this is a closed-form
fit, not a minimizer). A single power law is fit to all points; a "segmented" fit
splits the points at a given break energy and fits each side independently, reporting
both indices and, if requested, whether their difference is significant relative to
their combined uncertainty.

Usage notes / assumptions: standard library only. Energies and fluxes must be
positive and finite; at least two distinct energies are required per segment. Point
weights are 1/sigma_log_flux^2 when a per-point flux uncertainty is supplied,
otherwise unweighted (ordinary least squares - reported uncertainties are then only
as good as the assumption of comparable per-point scatter). This is a spectral-index
fit only - it does not itself account for detector energy resolution/migration, so it
should not be used as a substitute for forward-folding a spectral hypothesis through
an instrument response (see ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/references/10-measurements-unfolding.md).
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py --input ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/cosmic_ray_spectrum.example.json
     python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py --input ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/cosmic_ray_spectrum.example.json --break-energy 4.5e15
"""
import argparse
import json
import math


def _clean_points(points):
    cleaned = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
            raise ValueError(f'point {index} must be [energy, flux] or [energy, flux, sigma_flux]')
        energy = point[0]
        flux = point[1]
        sigma = point[2] if len(point) == 3 else None
        for value, name in ((energy, 'energy'), (flux, 'flux')):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'point {index} {name} must be finite and greater than zero')
        if sigma is not None:
            if isinstance(sigma, bool) or not isinstance(sigma, (int, float)) or not math.isfinite(sigma) or sigma <= 0:
                raise ValueError(f'point {index} sigma_flux must be finite and greater than zero')
        cleaned.append((float(energy), float(flux), float(sigma) if sigma is not None else None))
    return cleaned


def fit_power_law(points):
    """Weighted linear least squares for log(flux) = log(A) - gamma*log(E).

    points: sequence of (energy, flux) or (energy, flux, sigma_flux).
    Returns index (gamma, positive for a falling spectrum), its 1-sigma uncertainty,
    the normalization A at E=1 (in the input's energy units), and the fit's max
    absolute residual in log-flux.
    """
    cleaned = _clean_points(points)
    if len({e for e, _, _ in cleaned}) < 2:
        raise ValueError('need at least two distinct energies to fit a power law')

    x = [math.log(e) for e, _, _ in cleaned]
    y = [math.log(f) for _, f, _ in cleaned]
    # Propagate sigma_flux into sigma_log_flux = sigma_flux / flux; weight = 1/sigma^2.
    weights = []
    for (_, flux, sigma), yi in zip(cleaned, y):
        if sigma is None:
            weights.append(1.0)
        else:
            sigma_log = sigma / flux
            weights.append(1.0 / (sigma_log * sigma_log))

    sw = math.fsum(weights)
    swx = math.fsum(w * xi for w, xi in zip(weights, x))
    swy = math.fsum(w * yi for w, yi in zip(weights, y))
    swxx = math.fsum(w * xi * xi for w, xi in zip(weights, x))
    swxy = math.fsum(w * xi * yi for w, xi, yi in zip(weights, x, y))

    denom = sw * swxx - swx * swx
    if abs(denom) < 1e-300:
        raise ValueError('normal equations are singular - all energies coincide after weighting')

    slope = (sw * swxy - swx * swy) / denom          # slope = -gamma
    intercept = (swxx * swy - swx * swxy) / denom     # intercept = log(A)
    gamma = -slope

    residuals = [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]
    max_abs_residual = max(abs(r) for r in residuals)

    n = len(cleaned)
    sigma_gamma = None
    if n > 2:
        chi2 = math.fsum(w * r * r for w, r in zip(weights, residuals))
        dof = n - 2
        # Variance of the slope from the weighted normal-equations covariance,
        # scaled by the reduced chi-square when weights are unweighted (sigma=1 for
        # every point), matching the standard OLS convention.
        var_slope = sw / denom
        if all(sigma is None for _, _, sigma in cleaned):
            var_slope *= chi2 / dof
        sigma_gamma = math.sqrt(var_slope) if var_slope > 0 else None

    return {
        'points': n,
        'energy_range': [min(e for e, _, _ in cleaned), max(e for e, _, _ in cleaned)],
        'index': gamma,
        'index_uncertainty': sigma_gamma,
        'normalization_at_e1': math.exp(intercept),
        'max_abs_residual_log_flux': max_abs_residual,
        'weighted': not all(sigma is None for _, _, sigma in cleaned),
    }


def fit_segmented(points, break_energy):
    """Fit two independent power laws on either side of break_energy, and report
    the index difference and its combined uncertainty."""
    cleaned = _clean_points(points)
    if isinstance(break_energy, bool) or not isinstance(break_energy, (int, float)) or not math.isfinite(break_energy) or break_energy <= 0:
        raise ValueError('break_energy must be finite and greater than zero')

    below = [p for p in cleaned if p[0] < break_energy]
    above = [p for p in cleaned if p[0] >= break_energy]
    if len({e for e, _, _ in below}) < 2 or len({e for e, _, _ in above}) < 2:
        raise ValueError('need at least two distinct energies on each side of break_energy')

    below_fit = fit_power_law(below)
    above_fit = fit_power_law(above)
    result = {
        'break_energy': break_energy,
        'below_break': below_fit,
        'above_break': above_fit,
        'index_change': above_fit['index'] - below_fit['index'],
    }
    if below_fit['index_uncertainty'] is not None and above_fit['index_uncertainty'] is not None:
        combined_sigma = math.hypot(below_fit['index_uncertainty'], above_fit['index_uncertainty'])
        result['index_change_uncertainty'] = combined_sigma
        result['index_change_significance'] = (
            abs(result['index_change']) / combined_sigma if combined_sigma > 0 else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', required=True, metavar='JSON',
                        help='JSON file with {"points": [[energy, flux] or [energy, flux, sigma_flux], ...]}')
    parser.add_argument('--break-energy', type=float, default=None, dest='break_energy',
                        help='if given, fit two segments split at this energy instead of one power law')
    args = parser.parse_args()

    try:
        with open(args.input, encoding='utf-8') as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or 'points' not in payload:
            raise ValueError('input must be a JSON object with a "points" list')
        if args.break_energy is not None:
            result = fit_segmented(payload['points'], args.break_energy)
            method = 'segmented weighted linear least squares in log(E), log(flux)'
        else:
            result = fit_power_law(payload['points'])
            method = 'weighted linear least squares in log(E), log(flux)'
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print(json.dumps({'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()

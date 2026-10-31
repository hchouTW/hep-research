#!/usr/bin/env python3
"""Power-law fit to a cosmic-ray (or gamma-ray) flux-vs-energy spectrum.

Purpose: extract a spectral index (and, for a segmented fit, per-segment indices and
a break energy) from measured (energy, flux) points, and propagate the flux's
statistical uncertainty into the index's uncertainty. See
<plugin root>/skills/hep-detector/references/cosmic-ray-spectrum-and-composition.md for why an energy-scale
uncertainty on a steeply falling spectrum matters more than it looks: this script
fits the index only, and does not itself convert an index uncertainty into an
energy-scale systematic - that conversion (`gamma * delta`) is done by hand from the
formula quoted in that reference.

What it does: fits log(flux) = log(A) - gamma * log(E) by exact weighted linear least
squares in log-log space (a single power law is linear in its two parameters over the
basis {1, log E}, so - like <plugin root>/skills/hep-detector/scripts/calorimeter_resolution.py - this is a closed-form
fit, not a minimizer). Models (--model): a single power law; a continuous broken power law, sharp
(J = A (E/E_b)^-g1 below E_b, A (E/E_b)^-g2 above) or smooth (J = A (E/E_b)^-g1 [(1 + (E/E_b)^(1/s)) / 2]^-(g2-g1) s,
--smoothness s; A = J(E_b) in both), the plugin's one parametrization (<plugin root>/core/stats/broken_power_law.py,
shared with hep-statistics covariance_fit.py), with the break fixed (--break-energy) or free (--free-break:
profiled on a grid with golden-section refinement; its uncertainty from the linearized covariance). Both broken
models are linear in (log A, g1, g2) at a fixed break, so each break is a generalized least-squares solve. The output
gives chi2/ndf and the chi2 p-value (weighted fits), accepts a full flux covariance (--covariance) or asymmetric
errors, takes bin edges ("edges") with log-centre or Lafferty-Wyatt point energies, and reports the normalization at a
--pivot energy. The break's delta chi2 against a single power law is a likelihood-ratio statistic, not a calibrated
significance: a free break is a look-elsewhere trial, handed to hep-statistics
(<plugin root>/skills/hep-statistics/scripts/global_significance.py). fit_segmented (two independent fits,
discontinuous at the break) is kept for the library only, as a diagnostic; the command line no longer uses it.

Usage notes / assumptions: standard library only. Energies and fluxes must be
positive and finite; at least two distinct energies are required per segment. Point
weights are 1/sigma_log_flux^2 when a per-point flux uncertainty is supplied,
otherwise unweighted (ordinary least squares - reported uncertainties are then only
as good as the assumption of comparable per-point scatter). This is a spectral-index
fit only - it does not itself account for detector energy resolution/migration, so it
should not be used as a substitute for forward-folding a spectral hypothesis through
an instrument response (see <plugin root>/skills/hep-measurement/references/measurements-and-unfolding.md).
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed; 2 usage or invalid input (NaN, inf, malformed file);
3 incomplete or inconclusive.
Run: python3 <plugin root>/skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py --input <plugin root>/skills/hep-measurement/assets/cosmic-ray-spectrum.example.json
     python3 <plugin root>/skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py --input <plugin root>/skills/hep-measurement/assets/cosmic-ray-spectrum.example.json --free-break
"""
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.stats._linalg import solve  # noqa: E402
from core.stats.broken_power_law import basis as _basis, log_flux as _bpl_log_flux  # noqa: E402
from core.stats.statistical_toys import chi2_sf  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


def _reject_constant(token):
    raise ValueError(f'non-finite number {token} in the input')


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


# ---------------------------------------------------------------------------------------------------------------
# Continuous broken power law (ANA-P2-4), in the plugin's one parametrization (STH Q8,
# core/stats/broken_power_law.py): log J = log A - g1 * u1(x) - g2 * u2(x), x = log(E / E_b), with
#   sharp break:    u1 = min(x, 0), u2 = max(x, 0)                           (continuous at E_b by construction)
#   smooth break:   u1 = x - h, u2 = h, h = s log((1 + exp(x / s)) / 2)
#                   (J = A (E/E_b)^-g1 [(1 + (E/E_b)^(1/s)) / 2]^-(g2-g1) s)
# A = J(E_b) for both. Both are linear in (log A, g1, g2) for a fixed break, so the fit profiles the break on a grid
# with a golden-section refinement and solves a generalized least-squares problem in log flux at each break.

MODELS = ('single', 'broken', 'smooth-broken')


def broken_log_flux(energy, log_a, g1, g2, break_energy, smoothness=None):
    """log J of the continuous broken power law at one energy (core/stats/broken_power_law.py)."""
    return _bpl_log_flux(energy, log_a, g1, g2, math.log(break_energy), smoothness)


def _log_cov(points, covariance):
    """Covariance of log flux: from a full flux covariance (C_ij / f_i f_j) or the per-point errors."""
    n = len(points)
    if covariance is not None:
        if len(covariance) != n or any(len(r) != n for r in covariance):
            raise ValueError(f'covariance must be a {n} x {n} matrix')
        c = [[float(covariance[i][j]) / (points[i][1] * points[j][1]) for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(n):
                if not math.isfinite(c[i][j]) or abs(c[i][j] - c[j][i]) > 1e-9 * max(abs(c[i][j]), 1e-300):
                    raise ValueError('covariance must be finite and symmetric')
            if c[i][i] <= 0:
                raise ValueError('covariance diagonal must be positive')
        return c, True
    if all(p[2] is not None for p in points):
        return [[(points[i][2] / points[i][1]) ** 2 if i == j else 0.0 for j in range(n)] for i in range(n)], True
    if any(p[2] is not None for p in points):
        raise ValueError('give an uncertainty for every point or for none')
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)], False


def _gls(rows, y, w):
    """theta, its covariance and chi2 for the linear model y ~ rows . theta with weight matrix w."""
    k = len(rows[0])
    wx = [[sum(w[i][j] * rows[j][c] for j in range(len(y))) for c in range(k)] for i in range(len(y))]
    a = [[sum(rows[i][r] * wx[i][c] for i in range(len(y))) for c in range(k)] for r in range(k)]
    b = [[sum(wx[i][r] * y[i] for i in range(len(y)))] for r in range(k)]
    ident = [[1.0 if r == c else 0.0 for c in range(k)] for r in range(k)]
    inv = solve(a, ident, error=ValueError, what='normal-equation matrix (degenerate energies or break)')
    theta = [sum(inv[r][c] * b[c][0] for c in range(k)) for r in range(k)]
    res = [y[i] - sum(rows[i][c] * theta[c] for c in range(k)) for i in range(len(y))]
    chi2 = sum(res[i] * w[i][j] * res[j] for i in range(len(y)) for j in range(len(y)))
    return theta, inv, chi2


def _weights(points, model_logs, cov_log, asym):
    """Weight matrix; with asymmetric errors the side is chosen by where the model lies (iterated by the caller)."""
    n = len(points)
    if asym:
        diag = []
        for i, p in enumerate(points):
            lo, hi = p[3]
            side = hi if model_logs is not None and model_logs[i] > math.log(p[1]) else lo
            diag.append((side / p[1]) ** 2)
        cov_log = [[diag[i] if i == j else 0.0 for j in range(n)] for i in range(n)]
    ident = [[1.0 if r == c else 0.0 for c in range(n)] for r in range(n)]
    return solve(cov_log, ident, error=ValueError, what='covariance')


def fit_spectrum(points, model='broken', break_energy=None, smoothness=None, covariance=None, pivot=None,
                 edges=None, bin_centre='log-centre'):
    """Fit a single or continuous broken power law (sharp or smooth) to (E, J) points.

    points: [E, J], [E, J, sigma] or [E, J, sigma_low, sigma_high] (asymmetric). covariance: full flux covariance
    (overrides per-point sigma). break_energy: fixed break (None: free, profiled). edges: per-point [lo, hi]; the
    point energies are then the bin centres from bin_centre ('log-centre' or 'lafferty-wyatt', iterated with the
    fitted model). pivot: report the normalization at this energy (removes the A-gamma correlation)."""
    if model not in MODELS:
        raise ValueError(f'model must be one of {", ".join(MODELS)}')
    raw = []
    for i, p in enumerate(points):
        if not isinstance(p, (list, tuple)) or len(p) not in (2, 3, 4):
            raise ValueError(f'point {i} must be [E, J], [E, J, sigma] or [E, J, sigma_low, sigma_high]')
        for v, nm in zip(p, ('energy', 'flux', 'sigma', 'sigma_high')):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ValueError(f'point {i} {nm} must be finite and greater than zero')
        e, f = float(p[0]), float(p[1])
        raw.append([e, f, float(p[2]) if len(p) == 3 else None, (float(p[2]), float(p[3])) if len(p) == 4 else None])
    asym = any(p[3] is not None for p in raw)
    if asym and (covariance is not None or not all(p[3] is not None for p in raw)):
        raise ValueError('asymmetric errors need [E, J, sigma_low, sigma_high] for every point and no covariance')
    if asym:
        for p in raw:
            p[2] = 0.5 * (p[3][0] + p[3][1])
    if edges is not None:
        if len(edges) != len(raw):
            raise ValueError('edges must give one [lo, hi] per point')
        for i, (lo, hi) in enumerate(edges):
            if not (0 < lo < hi and math.isfinite(hi)):
                raise ValueError(f'edges {i} must be 0 < lo < hi')
            raw[i][0] = math.sqrt(lo * hi)
    if bin_centre not in ('log-centre', 'lafferty-wyatt'):
        raise ValueError("bin_centre must be 'log-centre' or 'lafferty-wyatt'")
    if smoothness is not None and (not math.isfinite(smoothness) or smoothness <= 0):
        raise ValueError('smoothness must be finite and greater than zero')
    n_par = 2 if model == 'single' else (3 if break_energy is not None else 4)
    if len({p[0] for p in raw}) < n_par + 1:
        raise ValueError(f'need at least {n_par + 1} distinct energies for the {model} model')
    cov_log, weighted = _log_cov(raw, covariance)
    s = smoothness if model == 'smooth-broken' else None
    if model == 'smooth-broken' and s is None:
        raise ValueError('smooth-broken needs --smoothness')

    def solve_at(log_eb, model_logs=None):
        w = _weights(raw, model_logs, cov_log, asym)
        y = [math.log(p[1]) for p in raw]
        if model == 'single':
            rows = [[1.0, -math.log(p[0])] for p in raw]
        else:
            rows = []
            for p in raw:
                u1, u2 = _basis(math.log(p[0]) - log_eb, s)
                rows.append([1.0, -u1, -u2])
        return _gls(rows, y, w)

    log_es = sorted(math.log(p[0]) for p in raw)

    def best_break(model_logs=None):
        if model == 'single' or break_energy is not None:
            return None if model == 'single' else math.log(break_energy)
        lo, hi = log_es[1], log_es[-2]
        grid = [lo + (hi - lo) * k / 200 for k in range(201)]
        chis = [solve_at(g, model_logs)[2] for g in grid]
        k = min(range(len(grid)), key=chis.__getitem__)
        a, b = grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)]
        for _ in range(60):
            m1, m2 = a + 0.382 * (b - a), a + 0.618 * (b - a)
            if solve_at(m1, model_logs)[2] < solve_at(m2, model_logs)[2]:
                b = m2
            else:
                a = m1
        return 0.5 * (a + b)

    model_logs = None
    positions = [p[0] for p in raw]
    for _ in range(4 if (asym or (edges is not None and bin_centre == 'lafferty-wyatt')) else 1):
        log_eb = best_break(model_logs)
        theta, cov, chi2 = solve_at(log_eb if log_eb is not None else 0.0, model_logs)

        def logj(e, th=theta, lb=log_eb):
            if model == 'single':
                return th[0] - th[1] * math.log(e)
            return broken_log_flux(e, th[0], th[1], th[2], math.exp(lb), s)
        model_logs = [logj(p[0]) for p in raw]
        if edges is not None and bin_centre == 'lafferty-wyatt':
            for i, (lo, hi) in enumerate(edges):
                xs = [lo * (hi / lo) ** (k / 200) for k in range(201)]
                vals = [math.exp(logj(x)) * x for x in xs]  # integrate in log E: dE = E dlogE
                h = math.log(hi / lo) / 200
                mean = h / 3 * (vals[0] + vals[-1] + 4 * sum(vals[1:-1:2]) + 2 * sum(vals[2:-1:2])) / (hi - lo)
                a, b = lo, hi
                for _ in range(100):  # the model falls with E: bisection for J(x) = mean
                    mid = math.sqrt(a * b)
                    if math.exp(logj(mid)) > mean:
                        a = mid
                    else:
                        b = mid
                raw[i][0] = math.sqrt(a * b)
            positions = [p[0] for p in raw]
            model_logs = [logj(p[0]) for p in raw]
    ndf = len(raw) - n_par
    w = _weights(raw, model_logs, cov_log, asym)
    # full linearized covariance including the break (column d logJ / d log E_b by finite difference)
    if model != 'single' and break_energy is None:
        jac = []
        for p in raw:
            u1, u2 = _basis(math.log(p[0]) - log_eb, s)
            h = 1e-6
            dlb = (broken_log_flux(p[0], *theta, math.exp(log_eb + h), s)
                   - broken_log_flux(p[0], *theta, math.exp(log_eb - h), s)) / (2 * h)
            jac.append([1.0, -u1, -u2, dlb])
        k = 4
        a_m = [[sum(jac[i][r] * w[i][j] * jac[j][c] for i in range(len(raw)) for j in range(len(raw)))
                for c in range(k)] for r in range(k)]
        cov = solve(a_m, [[1.0 if r == c else 0.0 for c in range(k)] for r in range(k)], error=ValueError,
                    what='linearized covariance')
    scale = 1.0 if weighted else (chi2 / ndf if ndf > 0 else float('nan'))
    err = [math.sqrt(cov[i][i] * scale) if cov[i][i] * scale >= 0 else None for i in range(len(cov))]
    out = {'model': model, 'points': len(raw), 'point_energies': positions, 'ndf': ndf, 'chi2': chi2 if weighted else None,
           'chi2_per_ndf': chi2 / ndf if weighted and ndf > 0 else None,
           'p_value': chi2_sf(chi2, ndf) if weighted and ndf > 0 else None, 'weighted': weighted}
    if not weighted:
        out['note'] = 'unweighted fit: uncertainties scaled by the residual scatter; no chi2 or p-value'
    if model == 'single':
        out.update(index=theta[1], index_uncertainty=err[1], normalization_at_e1=math.exp(theta[0]))
    else:
        out.update(index_below=theta[1], index_below_uncertainty=err[1], index_above=theta[2],
                   index_above_uncertainty=err[2], break_energy=math.exp(log_eb), smoothness=s,
                   break_free=break_energy is None)
        if break_energy is None:
            out['log_break_energy_uncertainty'] = err[3]
        out['normalization_at_break'] = math.exp(theta[0])
        single = fit_spectrum([p[:2] + ([p[2]] if p[2] is not None and not asym else []) for p in raw] if not asym else
                              [[p[0], p[1], p[3][0], p[3][1]] for p in raw], 'single', covariance=covariance)
        if weighted:
            out['break_test'] = {
                'delta_chi2_vs_single': single['chi2'] - chi2,
                'label': ('likelihood-ratio statistic of the break, not a calibrated significance: the free break '
                          'position is a look-elsewhere trial; hand the trials treatment to hep-statistics '
                          '(skills/hep-statistics/scripts/global_significance.py)')}
    if pivot is not None:
        if not (math.isfinite(pivot) and pivot > 0):
            raise ValueError('pivot must be finite and greater than zero')
        if model == 'single':
            g = [1.0, -math.log(pivot)]
            lj = theta[0] - theta[1] * math.log(pivot)
        else:
            u1, u2 = _basis(math.log(pivot) - log_eb, s)
            g = [1.0, -u1, -u2]
            lj = broken_log_flux(pivot, *theta, math.exp(log_eb), s)
            if len(cov) == 4:
                h = 1e-6
                g.append((broken_log_flux(pivot, *theta, math.exp(log_eb + h), s)
                          - broken_log_flux(pivot, *theta, math.exp(log_eb - h), s)) / (2 * h))
        var = sum(g[r] * cov[r][c] * g[c] for r in range(len(g)) for c in range(len(g))) * scale
        out['pivot'] = {'energy': pivot, 'flux': math.exp(lj), 'flux_relative_uncertainty': math.sqrt(max(var, 0.0))}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', required=True, metavar='JSON',
                        help='JSON {"points": [[E, J] | [E, J, sigma] | [E, J, sigma_low, sigma_high], ...], '
                             'optional "edges": [[lo, hi], ...] per point}')
    parser.add_argument('--model', choices=MODELS, default=None,
                        help='single (default without --break-energy/--free-break), broken (continuous, sharp) or '
                             'smooth-broken (with --smoothness)')
    parser.add_argument('--break-energy', type=float, default=None, dest='break_energy',
                        help='fix the break of the continuous broken power law at this energy (implies --model broken)')
    parser.add_argument('--free-break', action='store_true', dest='free_break',
                        help='fit the break energy (profiled on a grid, golden-section refined)')
    parser.add_argument('--smoothness', type=float, default=None, help='smoothness s of the smooth-broken model')
    parser.add_argument('--covariance', metavar='JSON', help='JSON n x n flux covariance matrix (overrides sigmas)')
    parser.add_argument('--pivot', type=float, default=None, help='report the normalization at this energy')
    parser.add_argument('--bin-centre', choices=('log-centre', 'lafferty-wyatt'), default='log-centre',
                        dest='bin_centre', help='point energies from "edges": log centre or Lafferty-Wyatt (iterated)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        with open(args.input, encoding='utf-8') as handle:
            payload = json.load(handle, parse_constant=_reject_constant)
        if not isinstance(payload, dict) or 'points' not in payload:
            raise ValueError('input must be a JSON object with a "points" list')
        covariance = None
        if args.covariance:
            with open(args.covariance, encoding='utf-8') as handle:
                covariance = json.load(handle, parse_constant=_reject_constant)
        model = args.model or ('broken' if (args.break_energy is not None or args.free_break) else 'single')
        if model != 'single' and args.break_energy is None and not args.free_break:
            raise ValueError(f'--model {model} needs --break-energy or --free-break')
        if args.break_energy is not None and args.free_break:
            raise ValueError('give --break-energy or --free-break, not both')
        if args.break_energy is not None and not (math.isfinite(args.break_energy) and args.break_energy > 0):
            raise ValueError('break_energy must be finite and greater than zero')
        result = fit_spectrum(payload['points'], model, args.break_energy, args.smoothness, covariance, args.pivot,
                              payload.get('edges'), args.bin_centre)
        method = {'single': 'weighted least squares in log(E), log(flux)',
                  'broken': 'continuous sharply broken power law, generalized least squares in log flux',
                  'smooth-broken': 'continuous smoothly broken power law, generalized least squares in log flux'}[model]
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f'{parser.prog}: error: {exc}', file=sys.stderr)  # one line, no usage block
        sys.exit(2)

    print(json.dumps({'status': args.status, 'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()

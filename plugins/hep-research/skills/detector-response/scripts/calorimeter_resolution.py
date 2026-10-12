#!/usr/bin/env python3
"""Fit and evaluate the three-term calorimeter energy-resolution parameterization.

Purpose: separate a calorimeter's stochastic, noise, and constant terms instead of
quoting a single "resolution", and identify which term dominates at a given energy -
the constant term is what limits high-energy performance and is the one most often
omitted.

What it does: fits (sigma_E/E)^2 = a^2/E + b^2/E^2 + c^2 to measured (E, sigma_E/E)
points. The model is *linear* in the parameters (a^2, b^2, c^2) over the basis
{1/E, 1/E^2, 1}, so this is an exact linear least squares solved from the 3x3 normal
equations - no minimizer, no starting values, no local minima. A point may carry a third
entry, the uncertainty of sigma_E/E; the fit is then weighted by 1/(2 r dr)^2 (the
uncertainty of r^2) and the covariance of (a^2, b^2, c^2) is the inverse of the weighted
normal matrix. Without uncertainties the fit is unweighted and the covariance is scaled
by the residual variance, which needs more than three points. Also evaluates the
resolution and the term-crossover energies for given a, b, c.

Usage notes / assumptions: standard library only. Energies in GeV; a in sqrt(GeV),
b in GeV, c dimensionless; sigma_E/E is a fraction, not a percentage. Needs at least
three distinct energies to separate three terms; with exactly three points there are
zero degrees of freedom and the output warns. A fitted squared coefficient can come
out negative on noisy or narrow-range input - that is reported explicitly as a failed
separation rather than square-rooted into a NaN. An evaluation energy outside the
fitted range (or outside --valid-range in --evaluate mode) is marked extrapolated. See
<plugin root>/skills/detector-response/references/calorimetry-ecal-hcal.md.
Run: python3 <plugin root>/skills/detector-response/scripts/calorimeter_resolution.py --fit <plugin root>/skills/detector-response/assets/calorimeter-response.example.json
     python3 <plugin root>/skills/detector-response/scripts/calorimeter_resolution.py --evaluate --stochastic 0.10 --noise 0.20 --constant 0.007 --energy 100
"""
import argparse
import json
import math
import sys

TERM_NAMES = ('stochastic', 'noise', 'constant')


def _finite_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def _solve_3x3(matrix, rhs):
    """Gaussian elimination with partial pivoting on a 3x3 system."""
    augmented = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    size = 3
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda r: abs(augmented[r][column]))
        if abs(augmented[pivot_row][column]) < 1e-300:
            raise ValueError(
                'normal equations are singular - the input energies do not constrain '
                'three independent terms (need at least three distinct energies, '
                'ideally spanning a wide range)')
        augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        for row in range(column + 1, size):
            factor = augmented[row][column] / augmented[column][column]
            for col in range(column, size + 1):
                augmented[row][col] -= factor * augmented[column][col]
    solution = [0.0] * size
    for row in reversed(range(size)):
        total = augmented[row][size] - math.fsum(
            augmented[row][col] * solution[col] for col in range(row + 1, size))
        solution[row] = total / augmented[row][row]
    return solution


def _invert_3x3(matrix):
    """Inverse of a 3x3 matrix, one column per unit right-hand side."""
    columns = [_solve_3x3(matrix, [1.0 if row == column else 0.0 for row in range(3)])
               for column in range(3)]
    return [[columns[column][row] for column in range(3)] for row in range(3)]


def fit_resolution(points):
    """Least-squares fit of (sigma/E)^2 against the basis {1/E, 1/E^2, 1}.

    points: sequence of (energy_gev, relative_resolution) or
    (energy_gev, relative_resolution, uncertainty_of_relative_resolution); either all
    points carry an uncertainty or none does.
    Returns a dict with the squared coefficients, their square roots where real, any
    coefficient that came out negative, and the covariance of the squared coefficients.
    """
    if not isinstance(points, (list, tuple)):
        raise ValueError('points must be a list of [energy, resolution] or '
                         '[energy, resolution, uncertainty] entries')
    cleaned = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
            raise ValueError(f'point {index} must be a two-element [energy, resolution] pair '
                             'or a three-element [energy, resolution, uncertainty] triple')
        energy = _finite_positive(point[0], f'point {index} energy')
        resolution = _finite_positive(point[1], f'point {index} resolution')
        uncertainty = (_finite_positive(point[2], f'point {index} uncertainty')
                       if len(point) == 3 else None)
        cleaned.append((energy, resolution, uncertainty))

    weighted = cleaned and cleaned[0][2] is not None
    if any((p[2] is not None) != weighted for p in cleaned):
        raise ValueError('either every point carries an uncertainty or none does')
    if len({energy for energy, _, _ in cleaned}) < 3:
        raise ValueError('need at least three distinct energies to separate three terms')

    # Design row for each point: [1/E, 1/E^2, 1]; target y = (sigma/E)^2 with
    # uncertainty 2 r dr, so weight 1/(2 r dr)^2 (unit weights when unweighted).
    rows = []
    for energy, _, _ in cleaned:
        inverse = 1.0 / energy
        rows.append((inverse, inverse * inverse, 1.0))
    targets = [resolution * resolution for _, resolution, _ in cleaned]
    variances = [(2.0 * r * dr) ** 2 if weighted else 1.0 for _, r, dr in cleaned]
    numbers = [value for row in rows for value in row] + targets + variances
    if not all(math.isfinite(value) for value in numbers) or min(variances) <= 0.0:
        raise ValueError('an energy, resolution or uncertainty is too small or too large for '
                         'the normal equations to be represented in floating point')
    weights = [1.0 / variance for variance in variances]

    matrix = [[math.fsum(w * row[i] * row[j] for row, w in zip(rows, weights)) for j in range(3)]
              for i in range(3)]
    rhs = [math.fsum(w * row[i] * target for row, target, w in zip(rows, targets, weights))
           for i in range(3)]
    if not all(math.isfinite(v) for v in rhs + [x for line in matrix for x in line]):
        raise ValueError('the normal equations overflow for this energy range; rescale or '
                         'drop the extreme points')
    squared = _solve_3x3(matrix, rhs)

    negative = [name for name, value in zip(TERM_NAMES, squared) if value < 0]
    ndof = len(cleaned) - 3
    result = {
        'points': len(cleaned),
        'weighted': weighted,
        'ndof': ndof,
        'energy_range_gev': [min(e for e, _, _ in cleaned), max(e for e, _, _ in cleaned)],
        'stochastic_squared': squared[0],
        'noise_squared': squared[1],
        'constant_squared': squared[2],
        'stochastic': math.sqrt(squared[0]) if squared[0] >= 0 else None,
        'noise': math.sqrt(squared[1]) if squared[1] >= 0 else None,
        'constant': math.sqrt(squared[2]) if squared[2] >= 0 else None,
        'negative_squared_terms': negative,
    }
    residuals = [
        target - (squared[0] * row[0] + squared[1] * row[1] + squared[2])
        for row, target in zip(rows, targets)
    ]
    result['max_abs_residual_in_squared_resolution'] = max(abs(r) for r in residuals)
    chi2 = math.fsum(w * r * r for w, r in zip(weights, residuals))

    warnings = []
    inverse_normal = _invert_3x3(matrix)
    if weighted:
        result['chi2'] = chi2
        covariance = inverse_normal
        result['covariance_source'] = 'inverse weighted normal matrix (input uncertainties)'
    elif ndof > 0:
        scale = chi2 / ndof
        covariance = [[scale * value for value in line] for line in inverse_normal]
        result['covariance_source'] = ('inverse normal matrix scaled by the residual variance '
                                       '(no input uncertainties)')
    else:
        covariance = None
        result['covariance_source'] = None
    if ndof == 0:
        warnings.append('three points for three parameters: zero degrees of freedom, so the '
                        'fit interpolates exactly and gives no goodness of fit'
                        + ('' if weighted else ' and no scatter-based covariance'))
    result['covariance_parameters'] = ['stochastic_squared', 'noise_squared', 'constant_squared']
    result['covariance_squared_terms'] = covariance
    result['warnings'] = warnings
    return result


def evaluate(stochastic, noise, constant, energy_gev, valid_range=None):
    """Relative resolution and per-term breakdown at one energy.

    valid_range: optional (low, high) energy range the coefficients were fitted over;
    the result then says whether energy_gev is an extrapolation (None when unknown).
    """
    for value, name in ((stochastic, 'stochastic'), (noise, 'noise'), (constant, 'constant')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{name} term must be finite and nonnegative')
    energy_gev = _finite_positive(energy_gev, 'energy')
    noise_over_energy = noise / energy_gev
    terms = {
        'stochastic': stochastic * stochastic / energy_gev,
        'noise': noise_over_energy * noise_over_energy,
        'constant': constant * constant,
    }
    total_squared = math.fsum(terms.values()) if all(map(math.isfinite, terms.values())) else math.inf
    if not math.isfinite(total_squared) or not math.isfinite(math.sqrt(total_squared) * energy_gev):
        raise ValueError('the resolution overflows at this energy; the energy is outside any '
                         'range where the three-term model applies')
    extrapolated = None
    if valid_range is not None:
        low, high = valid_range
        extrapolated = not low <= energy_gev <= high
    return {
        'energy_gev': energy_gev,
        'relative_resolution': math.sqrt(total_squared),
        'absolute_resolution_gev': math.sqrt(total_squared) * energy_gev,
        'term_contributions_squared': terms,
        'dominant_term': max(terms, key=terms.get),
        'extrapolated': extrapolated,
    }


def crossover_energies(stochastic, noise, constant):
    """Energies at which pairs of terms contribute equally. None where undefined."""
    crossings = {}
    crossings['noise_equals_stochastic_gev'] = (
        noise * noise / (stochastic * stochastic) if stochastic > 0 and noise > 0 else None)
    crossings['stochastic_equals_constant_gev'] = (
        stochastic * stochastic / (constant * constant) if constant > 0 and stochastic > 0 else None)
    crossings['noise_equals_constant_gev'] = (
        noise / constant if constant > 0 and noise > 0 else None)
    return crossings


def _fail(message):
    print(json.dumps({'ok': False, 'error': message}, indent=2))
    print(f'calorimeter_resolution.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--fit', metavar='JSON',
                      help='JSON file with {"points": [[energy_gev, sigma_over_e(, uncertainty)], ...]}')
    mode.add_argument('--evaluate', action='store_true',
                      help='evaluate a given (a, b, c) instead of fitting')
    parser.add_argument('--stochastic', type=float, default=0.0, help='a, in sqrt(GeV)')
    parser.add_argument('--noise', type=float, default=0.0, help='b, in GeV')
    parser.add_argument('--constant', type=float, default=0.0, help='c, dimensionless')
    parser.add_argument('--energy', type=float, default=100.0, help='energy in GeV (default 100)')
    parser.add_argument('--valid-range', type=float, nargs=2, metavar=('LOW', 'HIGH'),
                        dest='valid_range',
                        help='evaluate: energy range (GeV) the coefficients were fitted over')
    args = parser.parse_args()

    if args.evaluate:
        try:
            valid_range = None
            if args.valid_range is not None:
                low, high = (_finite_positive(v, 'valid-range bound') for v in args.valid_range)
                if low > high:
                    raise ValueError('valid-range LOW must not exceed HIGH')
                valid_range = (low, high)
            result = evaluate(args.stochastic, args.noise, args.constant, args.energy, valid_range)
            result['crossovers'] = crossover_energies(
                args.stochastic, args.noise, args.constant)
        except ValueError as exc:
            parser.error(str(exc))
        method = 'direct evaluation of a^2/E + b^2/E^2 + c^2'
    else:
        try:
            with open(args.fit, encoding='utf-8') as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or 'points' not in payload:
                raise ValueError('fit input must be a JSON object with a "points" list')
            result = fit_resolution(payload['points'])
            if not result['negative_squared_terms']:
                result['at_requested_energy'] = evaluate(
                    result['stochastic'], result['noise'], result['constant'], args.energy,
                    result['energy_range_gev'])
                result['crossovers'] = crossover_energies(
                    result['stochastic'], result['noise'], result['constant'])
                if result['at_requested_energy']['extrapolated']:
                    result['warnings'].append(
                        'the requested energy is outside the fitted energy range; the value '
                        'is an extrapolation of the fitted model')
            else:
                result['warning'] = (
                    'one or more squared coefficients fitted negative; the three terms are '
                    'not separated by this input (too few energies, too narrow a range, or '
                    'scatter larger than the term being fitted)')
        except (OSError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
            return _fail(str(exc))
        method = ('weighted' if result['weighted'] else 'exact') + \
            ' linear least squares in (a^2, b^2, c^2)'

    try:
        text = json.dumps({'method': method, **result}, indent=2, allow_nan=False)
    except ValueError:
        return _fail('result contains a non-finite number; check the input energies')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

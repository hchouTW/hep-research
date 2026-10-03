#!/usr/bin/env python3
"""Fit and evaluate the three-term calorimeter energy-resolution parameterization.

Purpose: separate a calorimeter's stochastic, noise, and constant terms instead of
quoting a single "resolution", and identify which term dominates at a given energy -
the constant term is what limits high-energy performance and is the one most often
omitted.

What it does: fits (sigma_E/E)^2 = a^2/E + b^2/E^2 + c^2 to measured (E, sigma_E/E)
points. The model is *linear* in the parameters (a^2, b^2, c^2) over the basis
{1/E, 1/E^2, 1}, so this is an exact linear least squares solved from the 3x3 normal
equations - no minimizer, no starting values, no local minima. Also evaluates the
resolution and the term-crossover energies for given a, b, c.

Usage notes / assumptions: standard library only. Energies in GeV; a in sqrt(GeV),
b in GeV, c dimensionless; sigma_E/E is a fraction, not a percentage. Needs at least
three distinct energies to separate three terms. A fitted squared coefficient can come
out negative on noisy or narrow-range input - that is reported explicitly as a failed
separation rather than square-rooted into a NaN. See
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/calorimetry-ecal-hcal.md.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/calorimeter_resolution.py --fit ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/assets/calorimeter-response.example.json
     python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/calorimeter_resolution.py --evaluate --stochastic 0.10 --noise 0.20 --constant 0.007 --energy 100
"""
import argparse
import json
import math

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


def fit_resolution(points):
    """Least-squares fit of (sigma/E)^2 against the basis {1/E, 1/E^2, 1}.

    points: sequence of (energy_gev, relative_resolution).
    Returns a dict with the squared coefficients, their square roots where real,
    and any coefficient that came out negative.
    """
    cleaned = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f'point {index} must be a two-element [energy, resolution] pair')
        energy = _finite_positive(point[0], f'point {index} energy')
        resolution = _finite_positive(point[1], f'point {index} resolution')
        cleaned.append((energy, resolution))

    if len({energy for energy, _ in cleaned} ) < 3:
        raise ValueError('need at least three distinct energies to separate three terms')

    # Design row for each point: [1/E, 1/E^2, 1]; target y = (sigma/E)^2.
    rows = [(1.0 / energy, 1.0 / (energy * energy), 1.0) for energy, _ in cleaned]
    targets = [resolution * resolution for _, resolution in cleaned]

    matrix = [[math.fsum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    rhs = [math.fsum(row[i] * target for row, target in zip(rows, targets)) for i in range(3)]
    squared = _solve_3x3(matrix, rhs)

    negative = [name for name, value in zip(TERM_NAMES, squared) if value < 0]
    result = {
        'points': len(cleaned),
        'energy_range_gev': [min(e for e, _ in cleaned), max(e for e, _ in cleaned)],
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
    return result


def evaluate(stochastic, noise, constant, energy_gev):
    """Relative resolution and per-term breakdown at one energy."""
    for value, name in ((stochastic, 'stochastic'), (noise, 'noise'), (constant, 'constant')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{name} term must be finite and nonnegative')
    energy_gev = _finite_positive(energy_gev, 'energy')
    terms = {
        'stochastic': stochastic * stochastic / energy_gev,
        'noise': noise * noise / (energy_gev * energy_gev),
        'constant': constant * constant,
    }
    total_squared = math.fsum(terms.values())
    return {
        'energy_gev': energy_gev,
        'relative_resolution': math.sqrt(total_squared),
        'absolute_resolution_gev': math.sqrt(total_squared) * energy_gev,
        'term_contributions_squared': terms,
        'dominant_term': max(terms, key=terms.get),
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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--fit', metavar='JSON',
                      help='JSON file with {"points": [[energy_gev, sigma_over_e], ...]}')
    mode.add_argument('--evaluate', action='store_true',
                      help='evaluate a given (a, b, c) instead of fitting')
    parser.add_argument('--stochastic', type=float, default=0.0, help='a, in sqrt(GeV)')
    parser.add_argument('--noise', type=float, default=0.0, help='b, in GeV')
    parser.add_argument('--constant', type=float, default=0.0, help='c, dimensionless')
    parser.add_argument('--energy', type=float, default=100.0, help='energy in GeV (default 100)')
    args = parser.parse_args()

    try:
        if args.fit:
            with open(args.fit, encoding='utf-8') as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or 'points' not in payload:
                raise ValueError('fit input must be a JSON object with a "points" list')
            result = fit_resolution(payload['points'])
            if not result['negative_squared_terms']:
                result['at_requested_energy'] = evaluate(
                    result['stochastic'], result['noise'], result['constant'], args.energy)
                result['crossovers'] = crossover_energies(
                    result['stochastic'], result['noise'], result['constant'])
            else:
                result['warning'] = (
                    'one or more squared coefficients fitted negative; the three terms are '
                    'not separated by this input (too few energies, too narrow a range, or '
                    'scatter larger than the term being fitted)')
            method = 'exact linear least squares in (a^2, b^2, c^2)'
        else:
            result = evaluate(args.stochastic, args.noise, args.constant, args.energy)
            result['crossovers'] = crossover_energies(
                args.stochastic, args.noise, args.constant)
            method = 'direct evaluation of a^2/E + b^2/E^2 + c^2'
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print(json.dumps({'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()

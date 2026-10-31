#!/usr/bin/env python3
"""Audit the documented one-dimensional JSON histogram bundle without mutation.

Run: python3 <plugin root>/skills/hep-computing/scripts/audit_histograms.py <plugin root>/skills/hep-computing/assets/histograms.example.json
Standard library only. Input excludes flow bins; sumw2 is MC variance bookkeeping,
not a general covariance matrix. Output: JSON with "status" ("ok", "warnings", "invalid" or "error").
Exit 0 valid (warnings allowed), 1 invalid content, 2 unreadable input.
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
from pathlib import Path


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def audit(bundle):
    errors, warnings = [], []
    if not isinstance(bundle, dict):
        return ['bundle must be an object'], warnings
    if type(bundle.get('schema_version')) is not int or bundle.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    kind = bundle.get('kind')
    if kind not in ('mc', 'poisson_expectation'):
        errors.append('kind must be mc or poisson_expectation')
    histograms = bundle.get('histograms')
    if not isinstance(histograms, dict) or not histograms:
        errors.append('histograms must be a nonempty mapping')
        return errors, warnings

    def check_hist(hist, label):
        if not isinstance(hist, dict):
            errors.append(f'{label}: histogram must be an object')
            return False
        valid = True
        for key in ('edges', 'sumw', 'sumw2'):
            values = hist.get(key)
            if not isinstance(values, list) or not values or not all(numeric(v) for v in values):
                errors.append(f'{label}: {key} must be a nonempty finite numeric array')
                valid = False
        if not valid:
            return False
        edges, sw, sw2 = hist['edges'], hist['sumw'], hist['sumw2']
        if len(edges) != len(sw) + 1 or len(sw2) != len(sw):
            errors.append(f'{label}: inconsistent bin dimensions')
            valid = False
        if any(b <= a for a, b in zip(edges, edges[1:])):
            errors.append(f'{label}: edges must strictly increase')
            valid = False
        if any(v < 0 for v in sw2):
            errors.append(f'{label}: negative sumw2')
            valid = False
        if any(v < 0 for v in sw):
            if kind == 'poisson_expectation':
                errors.append(f'{label}: negative Poisson expectation')
                valid = False
            else:
                warnings.append(f'{label}: negative signed MC bins; investigate before model export')
        if kind == 'mc':
            if any(v != 0 and v2 == 0 for v, v2 in zip(sw, sw2)):
                warnings.append(f'{label}: nonzero sumw with zero sumw2')
            if any(v == 0 and v2 > 0 for v, v2 in zip(sw, sw2)):
                warnings.append(f'{label}: cancellation bin has zero sumw but positive sumw2')
        return valid

    for name, nominal in histograms.items():
        nominal_valid = check_hist(nominal, name)
        if not isinstance(nominal, dict):
            continue
        variations = nominal.get('variations', {})
        expected = nominal.get('expected_variations', [])
        if not isinstance(expected, list) or not all(isinstance(v, str) for v in expected):
            errors.append(f'{name}: expected_variations must be an array of names')
            expected = []
        elif len(set(expected)) != len(expected):
            errors.append(f'{name}: duplicate expected_variations')
        if not isinstance(variations, dict):
            errors.append(f'{name}: variations must be a mapping')
            continue
        for missing in sorted(set(expected) - variations.keys()):
            errors.append(f'{name}: missing variation {missing}')
        for variation_name, variation in variations.items():
            label = f'{name}/{variation_name}'
            variation_valid = check_hist(variation, label)
            if nominal_valid and variation_valid:
                if variation['edges'] != nominal['edges']:
                    errors.append(f'{label}: edges differ from nominal')
                if all(variation[k] == nominal[k] for k in ('edges', 'sumw', 'sumw2')):
                    warnings.append(f'{label}: identical to nominal; verify intended response')
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        with args.bundle.open(encoding='utf-8') as stream:
            bundle = json.load(stream)
    except (OSError, ValueError, OverflowError) as exc:
        print(json.dumps({'status': 'error', 'ok': False, 'errors': [f'cannot read {args.bundle}: {exc}'], 'warnings': []}, indent=2))
        return 2
    errors, warnings = audit(bundle)
    status = 'invalid' if errors else ('warnings' if warnings else 'ok')
    print(json.dumps({'status': status, 'ok': not errors, 'errors': errors, 'warnings': warnings}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())

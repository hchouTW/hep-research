#!/usr/bin/env python3
"""Compute per-bin pileup reweighting factors from data and MC pileup profiles.

weight[i] = data_pdf[i] / mc_pdf[i], where each input profile (a list of bin
counts/weights over the same binning, e.g. number of true interactions) is
normalized to a probability density before dividing. See
<plugin root>/skills/detector-response/references/triggers-luminosity-pileup.md for the methodology and the failure
modes this guards against. Standard library only.
Run: python3 <plugin root>/skills/detector-response/scripts/pileup_reweight.py <plugin root>/skills/detector-response/assets/pileup-profiles.example.json
"""
import argparse
import json
import math
from pathlib import Path


def numeric_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def normalize(profile):
    """Return (pdf, total); raises ValueError if the profile can't be normalized."""
    if not isinstance(profile, list) or not profile:
        raise ValueError('profile must be a nonempty array')
    if not all(numeric_nonnegative(v) for v in profile):
        raise ValueError('profile entries must be finite and non-negative')
    total = math.fsum(profile)
    if total <= 0.0:
        raise ValueError('profile must have positive total weight to normalize')
    return [v / total for v in profile], total


def compute_weights(data_profile, mc_profile):
    """Return (weights, empty_mc_bins). weights[i] is None where mc_pdf[i] == 0 and
    data_pdf[i] > 0 - an undefined reweighting factor for a pileup condition the MC
    sample does not populate at all - flagged explicitly rather than silently
    emitted as inf or clamped to some arbitrary value."""
    if len(data_profile) != len(mc_profile):
        raise ValueError('data_profile and mc_profile must have the same length')
    data_pdf, _ = normalize(data_profile)
    mc_pdf, _ = normalize(mc_profile)

    weights = []
    empty_mc_bins = []
    for i, (d, m) in enumerate(zip(data_pdf, mc_pdf)):
        if m == 0.0:
            weights.append(None)
            if d > 0.0:
                empty_mc_bins.append(i)
        else:
            weights.append(d / m)
    return weights, empty_mc_bins


def reweighted_mean(weights, mc_profile, bin_centers):
    """Mean of bin_centers under the MC profile after applying weights (skipping
    undefined bins), for a closure check against the data profile's mean."""
    if len(weights) != len(mc_profile) or len(weights) != len(bin_centers):
        raise ValueError('weights, mc_profile, and bin_centers must have the same length')
    numerator = 0.0
    denominator = 0.0
    for w, m, center in zip(weights, mc_profile, bin_centers):
        if w is None:
            continue
        contribution = w * m
        numerator += contribution * center
        denominator += contribution
    if denominator <= 0.0:
        raise ValueError('no defined bins with positive weighted content to average')
    return numerator / denominator


def profile_mean(profile, bin_centers):
    if len(profile) != len(bin_centers):
        raise ValueError('profile and bin_centers must have the same length')
    total = math.fsum(profile)
    if total <= 0.0:
        raise ValueError('profile must have positive total weight to average')
    return math.fsum(p * c for p, c in zip(profile, bin_centers)) / total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path, help='JSON with data_profile, mc_profile, and bin_centers arrays')
    args = parser.parse_args()
    try:
        with args.bundle.open(encoding='utf-8') as stream:
            bundle = json.load(stream)
        if not isinstance(bundle, dict):
            raise ValueError('bundle must be an object')
        data_profile = bundle.get('data_profile')
        mc_profile = bundle.get('mc_profile')
        bin_centers = bundle.get('bin_centers')
        weights, empty_mc_bins = compute_weights(data_profile, mc_profile)
        result = {
            'ok': not empty_mc_bins,
            'weights': weights,
            'empty_mc_bins_with_data': empty_mc_bins,
        }
        if bin_centers is not None:
            result['mc_mean_before_reweight'] = profile_mean(mc_profile, bin_centers)
            result['data_mean'] = profile_mean(data_profile, bin_centers)
            if not empty_mc_bins:
                result['mc_mean_after_reweight'] = reweighted_mean(weights, mc_profile, bin_centers)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, indent=2))
        return 1
    if empty_mc_bins:
        result['error'] = (
            'data has probability mass in bins where MC has none; reweighting is '
            'undefined there (see empty_mc_bins_with_data) - regenerate MC to cover '
            'this pileup range, or explicitly document and bound the impact of '
            'excluding/clamping these bins rather than silently doing either.'
        )
    print(json.dumps(result, indent=2))
    return 1 if empty_mc_bins else 0


if __name__ == '__main__':
    raise SystemExit(main())

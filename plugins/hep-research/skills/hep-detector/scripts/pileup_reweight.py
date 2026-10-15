#!/usr/bin/env python3
"""Compute per-bin pileup reweighting factors from data and MC pileup profiles.

weight[i] = data_pdf[i] / mc_pdf[i], where each input profile (a list of bin
counts/weights over the same binning) is normalized to a probability density before
dividing. See <plugin root>/skills/hep-detector/references/triggers-luminosity-pileup.md for the methodology and the failure
modes this guards against. Standard library only.

The variable: the script is agnostic, but data and MC must histogram the same one.
The usual choice at hadron colliders is the Poisson mean mu of interactions per bunch
crossing, taken in data from luminosity times the inelastic cross section; the number of
interactions actually generated in an event is a Poisson draw around mu and is a
different distribution. State which one the profiles hold.

Input: data_profile and mc_profile (same binning), optional bin_centers (strictly
increasing) and bin_edges (one more entry, strictly increasing, each center inside its bin).
input_totals reports the raw sums before normalization: for a probability profile a total
below 1 means probability outside the binning, which the normalization hides.
Diagnostics: n_eff = (sum w)^2 / sum w^2 over the MC sample (computed with the MC
distribution, so n_eff_fraction is the fraction of the MC statistics that survives the
reweighting) and max_weight, with a warning when the weights are large. A non-finite
weight (for instance from a subnormal MC bin) or a non-finite bin center sets ok: false.
mc_mean_after_reweight equals data_mean by construction whenever every data-populated
bin has a defined weight: it is a bookkeeping identity, not an independent closure test.
Validate the reweighting on a variable that was not reweighted (for example the number
of reconstructed vertices in a control region).
Status: --status (default: the input file's "status", else unvalidated; one of the core artifact_statuses) is
echoed as status.
Exit codes: 0 ok; 1 the computation failed or the input file is unreadable or invalid (JSON with ok false);
2 invalid input (JSON with error_kind invalid-input on stdout, the usage on stderr).
Run: python3 <plugin root>/skills/hep-detector/scripts/pileup_reweight.py <plugin root>/skills/hep-detector/assets/pileup-profiles.example.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


# Warn when the reweighting keeps less than this fraction of the MC statistics, or
# when a single weight exceeds MAX_WEIGHT_WARNING.
N_EFF_FRACTION_WARNING = 0.5
MAX_WEIGHT_WARNING = 10.0


def numeric_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def normalize(profile):
    """Return (pdf, total); raises ValueError if the profile can't be normalized.

    Scales by the largest entry first, so profiles near the float limit (1e308) or with
    subnormal entries normalize without overflow.
    """
    if not isinstance(profile, list) or not profile:
        raise ValueError('profile must be a nonempty array')
    if not all(numeric_nonnegative(v) for v in profile):
        raise ValueError('profile entries must be finite and non-negative')
    scale = max(profile)
    if scale <= 0.0:
        raise ValueError('profile must have positive total weight to normalize')
    scaled = [v / scale for v in profile]
    scaled_total = math.fsum(scaled)
    return [v / scaled_total for v in scaled], scale * scaled_total


def compute_weight_details(data_profile, mc_profile):
    """Weights plus the bins where they are undefined or not representable.

    weights[i] is None where mc_pdf[i] == 0 (empty_mc_bins lists those with data, an
    undefined factor for a pileup condition the MC does not populate) and where
    data_pdf[i] / mc_pdf[i] overflows (nonfinite_weight_bins) - flagged explicitly
    rather than silently emitted as inf or clamped to some arbitrary value.
    """
    if not isinstance(data_profile, list) or not isinstance(mc_profile, list):
        raise ValueError('data_profile and mc_profile must be arrays')
    if len(data_profile) != len(mc_profile):
        raise ValueError('data_profile and mc_profile must have the same length')
    data_pdf, _ = normalize(data_profile)
    mc_pdf, _ = normalize(mc_profile)

    weights = []
    empty_mc_bins = []
    nonfinite_bins = []
    for i, (d, m) in enumerate(zip(data_pdf, mc_pdf)):
        if m == 0.0:
            weights.append(None)
            if d > 0.0:
                empty_mc_bins.append(i)
            continue
        try:
            weight = d / m
        except OverflowError:
            weight = math.inf
        if math.isfinite(weight):
            weights.append(weight)
        else:
            weights.append(None)
            nonfinite_bins.append(i)
    return {'weights': weights, 'empty_mc_bins': empty_mc_bins,
            'nonfinite_weight_bins': nonfinite_bins, 'mc_pdf': mc_pdf}


def compute_weights(data_profile, mc_profile):
    """Return (weights, empty_mc_bins); see compute_weight_details."""
    details = compute_weight_details(data_profile, mc_profile)
    return details['weights'], details['empty_mc_bins']


def weight_diagnostics(weights, mc_pdf):
    """n_eff fraction (sum p w)^2 / sum p w^2 under the MC distribution p, and max weight."""
    pairs = [(p, w) for p, w in zip(mc_pdf, weights) if w is not None and p > 0.0]
    if not pairs:
        raise ValueError('no defined weights to diagnose')
    largest = max(w for _, w in pairs)
    if largest <= 0.0:
        return {'n_eff_fraction': 0.0, 'max_weight': 0.0}
    # Scale by the largest weight so the squares cannot overflow; the ratio is invariant.
    first = math.fsum(p * w / largest for p, w in pairs)
    second = math.fsum(p * (w / largest) ** 2 for p, w in pairs)
    return {'n_eff_fraction': first * first / second, 'max_weight': largest}


def _validate_centers(bin_centers, length):
    if not isinstance(bin_centers, list) or len(bin_centers) != length:
        raise ValueError('bin_centers must be an array with one entry per profile bin')
    for index, center in enumerate(bin_centers):
        if isinstance(center, bool) or not isinstance(center, (int, float)) or not math.isfinite(center):
            raise ValueError(f'bin_centers[{index}] must be a finite number')
    if any(b <= a for a, b in zip(bin_centers, bin_centers[1:])):
        raise ValueError('bin_centers must be strictly increasing')


def _validate_edges(bin_edges, bin_centers, length):
    """Optional bin_edges: length + 1 strictly increasing finite numbers, each center inside its bin."""
    if not isinstance(bin_edges, list) or len(bin_edges) != length + 1:
        raise ValueError('bin_edges must be an array with one more entry than the profiles')
    for index, edge in enumerate(bin_edges):
        if isinstance(edge, bool) or not isinstance(edge, (int, float)) or not math.isfinite(edge):
            raise ValueError(f'bin_edges[{index}] must be a finite number')
    if any(b <= a for a, b in zip(bin_edges, bin_edges[1:])):
        raise ValueError('bin_edges must be strictly increasing')
    if bin_centers is not None:
        for index, center in enumerate(bin_centers):
            if not bin_edges[index] <= center < bin_edges[index + 1]:
                raise ValueError(f'bin_centers[{index}] = {center:g} is outside its bin '
                                 f'[{bin_edges[index]:g}, {bin_edges[index + 1]:g})')


def _finite_mean(pairs):
    mean = math.fsum(p * c for p, c in pairs)
    if not math.isfinite(mean):
        raise ValueError('mean of bin_centers overflows; rescale the bin centers')
    return mean


def reweighted_mean(weights, mc_profile, bin_centers):
    """Mean of bin_centers under the MC profile after applying weights (skipping
    undefined bins). Equal to the data mean by construction when no data-populated bin
    is skipped: a bookkeeping identity, not a closure test."""
    if len(weights) != len(mc_profile) or len(weights) != len(bin_centers):
        raise ValueError('weights, mc_profile, and bin_centers must have the same length')
    _validate_centers(bin_centers, len(weights))
    mc_pdf, _ = normalize(mc_profile)
    contributions = [(w * m, c) for w, m, c in zip(weights, mc_pdf, bin_centers) if w is not None]
    denominator = math.fsum(x for x, _ in contributions)
    if denominator <= 0.0:
        raise ValueError('no defined bins with positive weighted content to average')
    return _finite_mean([(x / denominator, c) for x, c in contributions])


def profile_mean(profile, bin_centers):
    if len(profile) != len(bin_centers):
        raise ValueError('profile and bin_centers must have the same length')
    _validate_centers(bin_centers, len(profile))
    pdf, _ = normalize(profile)
    return _finite_mean(zip(pdf, bin_centers))


def _resolve_status(given, document):
    """--status when given, else the input file's 'status' (checked against STATUSES), else unvalidated."""
    if given:
        return given
    status = document.get('status') if isinstance(document, dict) else None
    if status is None:
        return 'unvalidated'
    if status not in STATUSES:
        raise ValueError(f'input status {status!r} is not one of {list(STATUSES)}')
    return status


def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'pileup_reweight.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = JsonArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('bundle', type=Path, help='JSON with data_profile, mc_profile, and bin_centers arrays')
    parser.add_argument('--status', choices=STATUSES, default=None,
                        help="status label of the inputs, echoed as status (default: the input file's status, "
                             'else unvalidated)')
    args = parser.parse_args()
    try:
        with args.bundle.open(encoding='utf-8') as stream:
            bundle = json.load(stream)
        if not isinstance(bundle, dict):
            raise ValueError('bundle must be an object')
        status = _resolve_status(args.status, bundle)
        data_profile = bundle.get('data_profile')
        mc_profile = bundle.get('mc_profile')
        bin_centers = bundle.get('bin_centers')
        details = compute_weight_details(data_profile, mc_profile)
        if bin_centers is not None:
            _validate_centers(bin_centers, len(data_profile))
        if bundle.get('bin_edges') is not None:
            _validate_edges(bundle['bin_edges'], bin_centers, len(data_profile))
        weights, empty_mc_bins = details['weights'], details['empty_mc_bins']
        nonfinite_bins = details['nonfinite_weight_bins']
        problems = bool(empty_mc_bins or nonfinite_bins)
        result = {
            'status': status,
            'ok': not problems,
            'weights': weights,
            'empty_mc_bins_with_data': empty_mc_bins,
            'nonfinite_weight_bins': nonfinite_bins,
        }
        diagnostics = weight_diagnostics(weights, details['mc_pdf'])
        _, mc_total = normalize(mc_profile)
        _, data_total = normalize(data_profile)
        result.update({
            'max_weight': diagnostics['max_weight'],
            'n_eff_fraction': diagnostics['n_eff_fraction'],
            # In the units of mc_profile: an event count when mc_profile holds unweighted
            # MC event counts per bin, otherwise only the fraction is meaningful.
            'n_eff': diagnostics['n_eff_fraction'] * mc_total,
            # Raw sums before normalization: for a probability profile a total below 1 means mass outside the binning.
            'input_totals': {'data': data_total, 'mc': mc_total},
        })
        warnings = []
        if diagnostics['n_eff_fraction'] < N_EFF_FRACTION_WARNING:
            warnings.append(
                f"reweighting keeps only {diagnostics['n_eff_fraction']:.3g} of the MC "
                'statistics (n_eff_fraction); the MC pileup profile is far from data')
        if diagnostics['max_weight'] > MAX_WEIGHT_WARNING:
            warnings.append(
                f"max_weight {diagnostics['max_weight']:.4g} exceeds {MAX_WEIGHT_WARNING:g}: a few "
                'MC events dominate some bins; do not truncate weights silently - quote the '
                'effect of any cap as a systematic')
        result['warnings'] = warnings
        if bin_centers is not None:
            result['mc_mean_before_reweight'] = profile_mean(mc_profile, bin_centers)
            result['data_mean'] = profile_mean(data_profile, bin_centers)
            if not problems:
                result['mc_mean_after_reweight'] = reweighted_mean(weights, mc_profile, bin_centers)
                result['mc_mean_after_reweight_note'] = (
                    'equals data_mean by construction (a bookkeeping identity, not an '
                    'independent closure); validate on a variable that was not reweighted')
    except (OSError, ValueError, TypeError) as exc:
        return _fail(str(exc))
    errors = []
    if empty_mc_bins:
        errors.append(
            'data has probability mass in bins where MC has none; reweighting is '
            'undefined there (see empty_mc_bins_with_data) - regenerate MC to cover '
            'this pileup range, or explicitly document and bound the impact of '
            'excluding/clamping these bins rather than silently doing either.')
    if nonfinite_bins:
        errors.append(
            'the data/MC ratio overflows in some bins (see nonfinite_weight_bins); the MC '
            'content there is too small to reweight - merge bins or regenerate MC.')
    if errors:
        result['error'] = ' '.join(errors)
    try:
        text = json.dumps(result, indent=2, allow_nan=False)
    except ValueError:
        return _fail('result contains a non-finite number; check the input profiles')
    print(text)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())

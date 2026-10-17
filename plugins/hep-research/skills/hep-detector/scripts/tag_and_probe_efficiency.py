#!/usr/bin/env python3
"""Efficiency and exact Clopper-Pearson interval for tag-and-probe counts, or for probes read from a file
with weights and bins (D8).

Counts mode (--pass-count K --total N): efficiency = K / N for one bin and the exact central Clopper-Pearson interval
(not a Gaussian/Wald approximation, which is unreliable near 0 or 1), from the beta quantiles of
<plugin root>/core/stats/tail_estimation.py; there is no cap on N. See
<plugin root>/skills/hep-detector/references/triggers-luminosity-pileup.md for the tag-and-probe methodology.

Probes mode (--probes CSV --pass-column COL): one row per probe, COL 1 pass / 0 fail (lines starting with # skipped).
- --weights COL with --weight-kind (no default):
    frequency  integer weights that count identical probes: exactly the result of the duplicated rows;
    sampling   positive event weights (for example simulation weights): efficiency = sum(w pass) / sum(w), interval
               from the Kish effective sample size n_eff = (sum w)^2 / sum w^2 with k_eff = efficiency x n_eff in the
               beta quantiles (an approximation: exact for equal weights, it ignores any correlation of weight and
               pass/fail).
  A negative or zero weight is refused: signed weights (NLO generators) need a different treatment
  (hep-statistics).
- --bins FILE (JSON {"edges": [...]}) with --variable-column COL: one result per bin; probes outside the edges are
  counted in outside_edges and left out.

Scope: independent Bernoulli trials, one probe = one trial, no background subtracted. It does not apply to
background-subtracted pass/fail yields (fit the efficiency in a simultaneous pass/fail fit - hep-statistics), signed
weights, or several correlated probes per event.

Output: lower_bound and upper_bound are the interval's absolute ends at interval_level (default 0.95) of a central
interval (interval_type "central": alpha/2 in each tail). At 0.95 they are not a +-1 sigma band; pass --level 0.6827
for a one-sigma-equivalent interval. total = 0 leaves the efficiency undefined: the fields are null with a reason,
not NaN. Probes mode returns "bins" (one entry without --bins), "inputs" and "defaults_used".
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 2 invalid input (a JSON error with status failed and error_kind invalid-input on stdout, the usage
on stderr).
Run: python3 <plugin root>/skills/hep-detector/scripts/tag_and_probe_efficiency.py --pass-count 92 --total 100
     python3 <plugin root>/skills/hep-detector/scripts/tag_and_probe_efficiency.py --probes probes.csv --pass-column pass \
         --weights w --weight-kind sampling --bins bins.json --variable-column pt
Standard library only.
"""
import argparse
import bisect
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats.tail_estimation import beta_ppf  # noqa: E402
from core.stats.tail_estimation import clopper_pearson as _core_clopper_pearson  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


def validate_counts(k, n):
    if type(n) is not int or n < 0:
        raise ValueError('total must be a non-negative integer')
    if type(k) is not int or not 0 <= k <= n:
        raise ValueError('pass_count must be an integer from 0 through total')


def validate_level(level):
    if isinstance(level, bool) or not isinstance(level, (float, int)) or not math.isfinite(level) or not 0 < level < 1:
        raise ValueError('level must be finite and strictly between zero and one')


def clopper_pearson(k, n, level=0.95):
    """Exact central Clopper-Pearson interval for k successes out of n trials (n >= 1), from the beta quantiles
    lower = B^-1(alpha/2; k, n-k+1) (0 if k == 0), upper = B^-1(1-alpha/2; k+1, n-k) (1 if k == n)."""
    validate_counts(k, n)
    validate_level(level)
    if n == 0:
        raise ValueError('total must be at least 1 for an interval')
    return _core_clopper_pearson(k, n, level)


def kish_interval(k_eff, n_eff, level):
    """Clopper-Pearson form with real-valued effective counts (sampling weights, Kish n_eff)."""
    a = 1.0 - level
    lo = 0.0 if k_eff <= 0 else beta_ppf(a / 2.0, k_eff, n_eff - k_eff + 1.0)
    hi = 1.0 if k_eff >= n_eff else beta_ppf(1.0 - a / 2.0, k_eff + 1.0, n_eff - k_eff)
    return lo, hi


def efficiency_bin(k, n, level=0.95):
    validate_counts(k, n)
    validate_level(level)
    if n == 0:
        return {
            'pass_count': k, 'total': n, 'efficiency': None, 'interval_level': level,
            'interval_type': 'central',
            'lower_bound': None, 'upper_bound': None,
            'distance_to_lower_bound': None, 'distance_to_upper_bound': None,
            'reason': 'total is zero: no probes, so the efficiency is undefined',
        }
    point = k / n
    lower, upper = clopper_pearson(k, n, level)
    return {
        'pass_count': k, 'total': n, 'efficiency': point, 'interval_level': level,
        'interval_type': 'central',
        'lower_bound': lower, 'upper_bound': upper,
        # Distances from the point estimate to the interval ends, at interval_level.
        'distance_to_lower_bound': point - lower,
        'distance_to_upper_bound': upper - point,
    }


class ProbeError(ValueError):
    """Invalid probes file, weights or bins (exit 2)."""


def _num(text, what):
    try:
        v = float(text)
    except (TypeError, ValueError):
        raise ProbeError(f'{what}: {text!r} is not a number') from None
    if not math.isfinite(v):
        raise ProbeError(f'{what}: {text!r} is not finite')
    return v


def read_probes(args):
    cols = [args.pass_column] + [c for c in (args.weights, args.variable_column) if c]
    try:
        with open(args.probes, newline='', encoding='utf-8') as fh:
            lines = [ln for ln in fh if not ln.startswith('#')]
    except OSError as exc:
        raise ProbeError(f'cannot read {args.probes}: {exc}') from None
    reader = csv.DictReader(lines)
    missing = [c for c in cols if c not in (reader.fieldnames or [])]
    if missing:
        raise ProbeError(f'{args.probes}: missing column(s) {missing}; found {reader.fieldnames}')
    probes = []
    for r in reader:
        passed = _num(r[args.pass_column], args.pass_column)
        if passed not in (0.0, 1.0):
            raise ProbeError(f'{args.pass_column} must be 0 or 1, got {passed}')
        w = 1.0
        if args.weights:
            w = _num(r[args.weights], args.weights)
            if w <= 0:
                raise ProbeError(f'weight {w} <= 0: signed or zero weights need a different treatment than a '
                                 'binomial interval (hand them to hep-statistics)')
            if args.weight_kind == 'frequency' and not w.is_integer():
                raise ProbeError(f'frequency weights count identical probes and must be integers, got {w}')
        x = _num(r[args.variable_column], args.variable_column) if args.variable_column else None
        probes.append((int(passed), w, x))
    if not probes:
        raise ProbeError(f'{args.probes}: no probes')
    return probes


def weighted_bin(probes, kind, level):
    if not probes:
        return efficiency_bin(0, 0, level)
    if kind in (None, 'frequency'):
        k = int(sum(w for p, w, _ in probes if p))
        n = int(sum(w for _, w, _ in probes))
        return efficiency_bin(k, n, level)
    sw = math.fsum(w for _, w, _ in probes)
    sw2 = math.fsum(w * w for _, w, _ in probes)
    swp = math.fsum(w for p, w, _ in probes if p)
    eff = swp / sw
    n_eff = sw * sw / sw2
    lo, hi = kish_interval(eff * n_eff, n_eff, level)
    return {'probes': len(probes), 'sum_w': sw, 'sum_w2': sw2, 'sum_w_pass': swp, 'n_eff': n_eff,
            'efficiency': eff, 'interval_level': level, 'interval_type': 'central',
            'lower_bound': lo, 'upper_bound': hi,
            'distance_to_lower_bound': eff - lo, 'distance_to_upper_bound': hi - eff}


def run_probes(args, given):
    if args.weights and args.weight_kind is None:
        raise ProbeError('--weights needs --weight-kind frequency (integer counts) or sampling (Kish n_eff); '
                         'there is no default')
    if args.weight_kind and not args.weights:
        raise ProbeError('--weight-kind needs --weights')
    if (args.bins is None) != (args.variable_column is None):
        raise ProbeError('--bins and --variable-column go together')
    probes = read_probes(args)
    out = {'mode': 'probes', 'weight_kind': args.weight_kind or 'unweighted',
           'method': ('Clopper-Pearson from the Kish effective sample size (k_eff = efficiency x n_eff)'
                      if args.weight_kind == 'sampling' else 'Clopper-Pearson exact binomial interval'),
           'inputs': {'probes': str(args.probes), 'pass_column': args.pass_column, 'weights': args.weights,
                      'weight_kind': args.weight_kind, 'bins': str(args.bins) if args.bins else None,
                      'variable_column': args.variable_column, 'level': args.level},
           'defaults_used': [k for k in ('--level', '--status') if k not in given]}
    if args.bins is None:
        out['bins'] = [dict(low=None, high=None, **weighted_bin(probes, args.weight_kind, args.level))]
        return out
    try:
        spec = json.loads(Path(args.bins).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ProbeError(f'cannot read --bins {args.bins}: {exc}') from None
    edges = [_num(e, 'bin edge') for e in (spec.get('edges') if isinstance(spec, dict) else None) or []]
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ProbeError('--bins needs {"edges": [...]} increasing, at least two edges')
    per = [[] for _ in edges[:-1]]
    outside = 0
    for pr in probes:
        i = bisect.bisect_right(edges, pr[2]) - 1
        if pr[2] == edges[-1]:
            i = len(per) - 1
        if 0 <= i < len(per):
            per[i].append(pr)
        else:
            outside += 1
    out['bins'] = [dict(low=a, high=b, **weighted_bin(p, args.weight_kind, args.level))
                   for a, b, p in zip(edges, edges[1:], per)]
    out['outside_edges'] = outside
    return out


def main():
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pass-count', type=int, dest='pass_count', help='passing probes (counts mode)')
    parser.add_argument('--total', type=int, help='all probes (counts mode)')
    parser.add_argument('--probes', help='CSV of probes, one row each (probes mode)')
    parser.add_argument('--pass-column', help='column with 1 pass / 0 fail (probes mode)')
    parser.add_argument('--weights', help='column of probe weights (probes mode; needs --weight-kind)')
    parser.add_argument('--weight-kind', choices=('frequency', 'sampling'),
                        help='frequency: integer counts of identical probes; sampling: event weights (Kish n_eff)')
    parser.add_argument('--bins', help='JSON {"edges": [...]} of the variable (probes mode)')
    parser.add_argument('--variable-column', help='column binned by --bins')
    parser.add_argument('--level', type=float, default=0.95,
                        help='coverage of the interval (default 0.95; 0.6827 for one-sigma)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the counts, echoed as status (default unvalidated)')
    args = parser.parse_args()
    given = {a.split('=')[0] for a in sys.argv[1:] if a.startswith('--')}
    counts_mode = args.pass_count is not None or args.total is not None
    if counts_mode and args.probes:
        parser.error('give either --pass-count/--total (counts) or --probes (a file), not both')
    if not counts_mode and not args.probes:
        parser.error('give --pass-count and --total, or --probes with --pass-column')
    note = ('Not a Gaussian/Wald interval; valid (if wide) near efficiency 0 or 1. '
            'lower_bound/upper_bound are the interval ends at interval_level, not '
            '+-1 sigma. The interval is central (alpha/2 in each tail); for k = 0 the one-sided '
            'upper limit at the same level is 1 - alpha^(1/n), smaller than the central upper end. '
            'Only for independent, non-background-subtracted probes with non-negative weights.')
    if counts_mode:
        if args.pass_count is None or args.total is None:
            parser.error('counts mode needs both --pass-count and --total')
        try:
            validate_level(args.level)
            result = efficiency_bin(args.pass_count, args.total, args.level)
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps({'status': args.status, 'method': 'Clopper-Pearson exact binomial interval', **result,
                          'note': note}, indent=2))
        return 0
    if not args.pass_column:
        parser.error('--probes needs --pass-column')
    try:
        validate_level(args.level)
        out = run_probes(args, given)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({'status': args.status, **out, 'note': note}, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

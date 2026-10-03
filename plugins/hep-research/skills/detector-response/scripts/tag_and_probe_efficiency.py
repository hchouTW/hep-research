#!/usr/bin/env python3
"""Binomial efficiency and exact Clopper-Pearson interval for tag-and-probe counts.

Computes efficiency = pass / total for one or more (pass, total) bins and an exact
Clopper-Pearson confidence interval (not a Gaussian/Wald approximation, which is
unreliable near 0 or 1). See ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/triggers-luminosity-pileup.md for the
tag-and-probe methodology this supports. Standard library only; intentionally
limited to 0 <= total <= 200000 per bin (see module docstring in this file for why).
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/tag_and_probe_efficiency.py --pass-count 92 --total 100
"""
import argparse
import json
import math

MAX_TOTAL = 200000


def validate_counts(k, n):
    if type(n) is not int or not 0 <= n <= MAX_TOTAL:
        raise ValueError(f'total must be an integer from 0 through {MAX_TOTAL}')
    if type(k) is not int or not 0 <= k <= n:
        raise ValueError('pass_count must be an integer from 0 through total')


def validate_level(level):
    if isinstance(level, bool) or not isinstance(level, (float, int)) or not math.isfinite(level) or not 0 < level < 1:
        raise ValueError('level must be finite and strictly between zero and one')


def log_binomial_pmf(i, n, p):
    """log P(X = i | n, p); handles the p=0/p=1 boundary explicitly."""
    if p <= 0.0:
        return 0.0 if i == 0 else float('-inf')
    if p >= 1.0:
        return 0.0 if i == n else float('-inf')
    return (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log1p(-p))


def binomial_upper_tail(k, n, p):
    """Exact P(X >= k | n, p) by direct log-space summation (peak-relative, like
    the Poisson tail in counting_reference.py, to avoid cancellation/underflow)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    terms = [log_binomial_pmf(i, n, p) for i in range(k, n + 1)]
    peak = max(terms)
    if peak == float('-inf'):
        return 0.0
    return min(1.0, math.exp(peak) * math.fsum(math.exp(t - peak) for t in terms))


def _invert_monotonic(func, target):
    """Bisect p in (0, 1) for a function that is monotonically nondecreasing in p;
    return p where func(p) == target."""
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if func(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k, n, level=0.95):
    """Exact Clopper-Pearson interval for k successes out of n trials.

    lower solves P(X >= k | n, lower) = alpha/2 (0 if k == 0);
    upper solves P(X >= k+1 | n, upper) = 1 - alpha/2 (1 if k == n).
    """
    validate_counts(k, n)
    validate_level(level)
    alpha = 1.0 - level

    if k == 0:
        lower = 0.0
    else:
        lower = _invert_monotonic(lambda p: binomial_upper_tail(k, n, p), alpha / 2.0)

    if k == n:
        upper = 1.0
    else:
        upper = _invert_monotonic(lambda p: binomial_upper_tail(k + 1, n, p), 1.0 - alpha / 2.0)

    return lower, upper


def efficiency_bin(k, n, level=0.95):
    validate_counts(k, n)
    point = k / n if n > 0 else float('nan')
    lower, upper = clopper_pearson(k, n, level) if n > 0 else (float('nan'), float('nan'))
    return {
        'pass_count': k, 'total': n, 'efficiency': point,
        'level': level, 'lower': lower, 'upper': upper,
        'lower_error': None if n == 0 else point - lower,
        'upper_error': None if n == 0 else upper - point,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pass-count', type=int, required=True, dest='pass_count')
    parser.add_argument('--total', type=int, required=True)
    parser.add_argument('--level', type=float, default=0.95)
    args = parser.parse_args()
    try:
        result = efficiency_bin(args.pass_count, args.total, args.level)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({
        'method': 'Clopper-Pearson exact binomial interval',
        **result,
        'note': 'Not a Gaussian/Wald interval; valid (if wide) near efficiency 0 or 1.',
    }, indent=2))


if __name__ == '__main__':
    main()

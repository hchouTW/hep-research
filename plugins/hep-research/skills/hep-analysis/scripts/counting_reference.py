#!/usr/bin/env python3
"""Reference for a small Poisson counting model with exactly known background.

Returns exact P(N >= n | b), and a Bayesian upper credible bound on signal s >= 0
with a flat prior in s. This is NOT CLs and includes no nuisance parameters.
Standard library only; intentionally limited to 0 <= n <= 500, 0 <= b <= 500.
Run: python3 <plugin root>/skills/hep-analysis/scripts/counting_reference.py --observed 0 --background 0
"""
import argparse
import json
import math


def validate(n, b):
    if type(n) is not int or not 0 <= n <= 500:
        raise ValueError('observed must be an integer from 0 through 500')
    if isinstance(b, bool) or not isinstance(b, (float, int)) or not math.isfinite(b) or not 0 <= b <= 500:
        raise ValueError('known background must be finite and between 0 and 500')


def log_poisson_cdf(n, mean):
    """Log P(N <= n); log-sum-exp avoids underflow in posterior ratios."""
    if mean == 0:
        return 0.0
    terms = [k * math.log(mean) - math.lgamma(k + 1) for k in range(n + 1)]
    peak = max(terms)
    return min(0.0, -mean + peak + math.log(math.fsum(math.exp(t - peak) for t in terms)))


def poisson_upper_tail(n, b):
    """Direct positive sum for the small high-n tail; avoid 1-CDF cancellation."""
    validate(n, b)
    if n == 0:
        return 1.0
    if b == 0:
        return 0.0
    if n <= b:
        return min(1.0, max(0.0, -math.expm1(log_poisson_cdf(n - 1, b))))
    term = math.exp(-b + n * math.log(b) - math.lgamma(n + 1))
    total = term
    for k in range(n + 1, 10000):
        term *= b / k
        total += term
        if term <= total * 1e-15:
            return min(1.0, total)
    raise ArithmeticError('Poisson tail did not converge')


def bayesian_upper(n, b, level=0.95):
    """Invert survival Q(n+1,b+s)/Q(n+1,b) for flat-prior posterior."""
    validate(n, b)
    if isinstance(level, bool) or not isinstance(level, (float, int)) or not math.isfinite(level) or not 0 < level < 1:
        raise ValueError('level must be finite and strictly between zero and one')
    denominator = log_poisson_cdf(n, b)
    target = math.log1p(-level)

    def log_survival(s):
        return log_poisson_cdf(n, b + s) - denominator

    lo, hi = 0.0, max(1.0, n + 1.0)
    while log_survival(hi) > target:
        hi *= 2
        if hi > 1e7:
            raise ArithmeticError('could not bracket posterior bound')
    for _ in range(100):
        mid = (lo + hi) / 2
        if log_survival(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observed', type=int, required=True)
    parser.add_argument('--background', type=float, required=True)
    parser.add_argument('--level', type=float, default=0.95)
    args = parser.parse_args()
    try:
        bound = bayesian_upper(args.observed, args.background, args.level)
        tail = poisson_upper_tail(args.observed, args.background)
    except (ValueError, ArithmeticError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        'model': 'Poisson(n | s+b), known b, s>=0',
        'method': 'Bayesian upper credible bound; flat prior in s; NOT CLs',
        'observed': args.observed, 'background': args.background,
        'level': args.level, 'signal_upper_bound': bound,
        'background_only_upper_tail_p': tail,
        'tail_note': 'Extreme tails can underflow to 0 in double precision; not proof of zero probability.',
    }, indent=2))


if __name__ == '__main__':
    main()

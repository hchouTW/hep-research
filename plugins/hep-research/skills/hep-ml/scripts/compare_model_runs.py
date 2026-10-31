#!/usr/bin/env python3
"""Compare two model configurations across seeds, against the seed-noise floor.

Purpose: decide whether a reported improvement is real. The spread across seeds of an
unchanged configuration is the noise floor, and a large fraction of informally reported
gains are smaller than it. Reporting a single run, or the best of several, is not
evidence.

What it does: takes per-seed scores for a baseline and a variant, pairs them by seed
where possible, and reports the mean difference with a bootstrap confidence interval (with fewer than 10 seeds a
Student-t interval on the seed means, with the exact permutation p-value beside it, because the bootstrap
undercovers there),
the seed spread of each arm, whether the interval excludes zero, and the minimum
effect this many seeds could reliably detect. Also flags a best-of-N comparison, which
is a biased estimator whose expectation rises with N.

Usage notes / assumptions: standard library only; PyTorch is not required. Scores are
assumed to be "higher is better" unless --lower-is-better is given or the runs file sets
"lower_is_better": true; a flag given on the command line (--lower-is-better or
--no-lower-is-better) always wins over the file, and the report records which source
decided ("lower_is_better_source"). Paired mode
requires equal-length arrays whose entries correspond to the same seed and split;
unpaired mode is used automatically otherwise and is substantially less sensitive.
The bootstrap is seeded, so results are reproducible.
Run: python3 <plugin root>/skills/hep-ml/scripts/compare_model_runs.py <plugin root>/skills/hep-ml/assets/eval-runs.example.json
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
import random
import statistics
import sys

DEFAULT_RESAMPLES = 20000
# z(0.975) + z(0.80): the two-sided 5% / 80% power constant for a mean difference.
# Valid for large n; with few seeds the t distribution needs a larger factor.
POWER_CONSTANT = 2.80
# Exact noncentral-t factors (two-sided 5%, 80% power) keyed by n, computed with
# scipy.stats.nct; detectable effect = factor * stdev / sqrt(n). Beyond n=30 the
# normal constant is within ~4%.
T_POWER_FACTOR = {
    2: 16.33, 3: 5.65, 4: 4.26, 5: 3.76, 6: 3.51, 7: 3.37, 8: 3.27, 9: 3.20, 10: 3.15,
    11: 3.11, 12: 3.08, 13: 3.05, 14: 3.03, 15: 3.01, 16: 3.00, 17: 2.98, 18: 2.97,
    19: 2.96, 20: 2.95, 21: 2.95, 22: 2.94, 23: 2.93, 24: 2.93, 25: 2.92, 26: 2.92,
    27: 2.91, 28: 2.91, 29: 2.90, 30: 2.90,
}


STATUSES = ("synthetic", "asimov", "observed", "preliminary", "failed", "unvalidated", "user-supplied",
            "validated-in-scope", "projection", "outside-validated-range")  # contracts/vocab/core.json artifact_statuses

def _scores(values, name):
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError(f"{name} must be a list of at least two per-seed scores")
    cleaned = []
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}[{index}] must be a number")
        if not math.isfinite(value):
            raise ValueError(f"{name}[{index}] must be finite")
        cleaned.append(float(value))
    return cleaned


def summarize_arm(scores):
    return {
        "n": len(scores),
        "mean": statistics.fmean(scores),
        "stdev": statistics.stdev(scores),
        "min": min(scores),
        "max": max(scores),
        "spread": max(scores) - min(scores),
    }


def bootstrap_interval(samples, level=0.95, resamples=DEFAULT_RESAMPLES, seed=0):
    """Percentile bootstrap interval for the mean of `samples`."""
    if not 0.0 < level < 1.0:
        raise ValueError("level must be strictly between zero and one")
    rng = random.Random(seed)
    size = len(samples)
    means = []
    for _ in range(resamples):
        means.append(statistics.fmean(rng.choices(samples, k=size)))
    means.sort()
    tail = (1.0 - level) / 2.0
    low = means[max(0, int(math.floor(tail * resamples)) - 1)]
    high = means[min(resamples - 1, int(math.ceil((1.0 - tail) * resamples)) - 1)]
    return low, high


def minimum_detectable_effect(stdev, n):
    """Smallest mean difference detectable at 5% two-sided with 80% power."""
    if n < 2:
        raise ValueError("need at least two observations")
    return T_POWER_FACTOR.get(n, POWER_CONSTANT) * stdev / math.sqrt(n)


SMALL_SAMPLE = 10  # below this many seeds the percentile bootstrap undercovers; an exact test decides instead


def _betacf(a, b, x):
    """Continued fraction of the regularized incomplete beta function (modified Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < 3e-15:
            break
    return h


def _student_t_cdf(t, df):
    """CDF of Student's t through the regularized incomplete beta function."""
    if t == 0:
        return 0.5
    x = df / (df + t * t)
    lbeta = math.lgamma(df / 2) + math.lgamma(0.5) - math.lgamma(df / 2 + 0.5)
    front = math.exp(math.log(x) * df / 2 + math.log1p(-x) * 0.5 - lbeta)
    if x < (df / 2 + 1) / (df / 2 + 2.5):
        ib = front * _betacf(df / 2, 0.5, x) / (df / 2)
    else:
        ib = 1.0 - math.exp(math.log1p(-x) * 0.5 + math.log(x) * df / 2 - lbeta) * _betacf(0.5, df / 2, 1 - x) / 0.5
    return 1.0 - 0.5 * ib if t > 0 else 0.5 * ib


def student_t_quantile(p, df):
    """Quantile of Student's t (bisection on the CDF); standard library only."""
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _student_t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def permutation_p_value(baseline, variant, paired, sign):
    """Exact two-sided permutation p-value of the mean difference: all sign flips of the paired differences, or all
    reassignments of the pooled scores to the two arms."""
    import itertools
    if paired:
        diffs = [sign * (v - b) for b, v in zip(baseline, variant)]
        observed = abs(sum(diffs))
        flips = list(itertools.product((1, -1), repeat=len(diffs)))
        hits = sum(1 for f in flips if abs(sum(x * y for x, y in zip(f, diffs))) >= observed - 1e-12)
        return hits / len(flips)
    pooled = list(baseline) + list(variant)
    n_b = len(baseline)
    observed = abs(statistics.fmean(variant) - statistics.fmean(baseline))
    total = hits = 0
    for idx in itertools.combinations(range(len(pooled)), n_b):
        chosen = set(idx)
        a = [pooled[i] for i in idx]
        b = [pooled[i] for i in range(len(pooled)) if i not in chosen]
        total += 1
        hits += abs(statistics.fmean(b) - statistics.fmean(a)) >= observed - 1e-12
    return hits / total


def compare(baseline, variant, level=0.95, lower_is_better=False,
            resamples=DEFAULT_RESAMPLES, seed=0):
    """Paired (or unpaired) comparison of two arms, with the noise floor made explicit."""
    baseline = _scores(baseline, "baseline")
    variant = _scores(variant, "variant")
    sign = -1.0 if lower_is_better else 1.0

    paired = len(baseline) == len(variant)
    if paired:
        differences = [sign * (v - b) for b, v in zip(baseline, variant)]
    else:
        # Unpaired: bootstrap the difference of means by resampling each arm.
        rng = random.Random(seed)
        differences = None
        means = []
        for _ in range(resamples):
            a = statistics.fmean(rng.choices(baseline, k=len(baseline)))
            b = statistics.fmean(rng.choices(variant, k=len(variant)))
            means.append(sign * (b - a))
        means.sort()
        tail = (1.0 - level) / 2.0
        low = means[max(0, int(math.floor(tail * resamples)) - 1)]
        high = means[min(resamples - 1, int(math.ceil((1.0 - tail) * resamples)) - 1)]

    baseline_summary = summarize_arm(baseline)
    variant_summary = summarize_arm(variant)

    if paired:
        mean_difference = statistics.fmean(differences)
        difference_stdev = statistics.stdev(differences)
        low, high = bootstrap_interval(differences, level, resamples, seed)
        detectable = minimum_detectable_effect(difference_stdev, len(differences))
    else:
        mean_difference = sign * (variant_summary["mean"] - baseline_summary["mean"])
        difference_stdev = math.hypot(baseline_summary["stdev"], variant_summary["stdev"])
        detectable = minimum_detectable_effect(
            difference_stdev, min(len(baseline), len(variant)))

    noise_floor = max(baseline_summary["spread"], variant_summary["spread"])
    method = "bootstrap"
    p_value = None
    if min(len(baseline), len(variant)) < SMALL_SAMPLE:
        # With few seeds the percentile bootstrap undercovers (false "improvements" at 26%, 15%, 11% for 3, 5, 10
        # seeds against a nominal 5% in the hep-ml audit's first pass): a Student-t interval on the seed means
        # decides, and the exact permutation p-value is reported beside it.
        method = "Student-t test on the seed means, with the exact permutation p-value (fewer than 10 seeds)"
        p_value = permutation_p_value(baseline, variant, paired, sign)
        if paired:
            df, se = len(differences) - 1, difference_stdev / math.sqrt(len(differences))
        else:
            vb, vv = baseline_summary["stdev"] ** 2 / len(baseline), variant_summary["stdev"] ** 2 / len(variant)
            se = math.sqrt(vb + vv)
            df = (vb + vv) ** 2 / ((vb ** 2 / (len(baseline) - 1) if vb else 0) + (vv ** 2 / (len(variant) - 1) if vv else 0)
                                   or 1.0)
        t_crit = student_t_quantile(1.0 - (1.0 - level) / 2.0, df) if se > 0 else 0.0
        low, high = mean_difference - t_crit * se, mean_difference + t_crit * se
        significant = (low > 0.0) or (high < 0.0)  # the t test decides; the permutation p-value is reported beside it
    else:
        significant = (low > 0.0) or (high < 0.0)

    return {
        "paired": paired,
        "method": method,
        "permutation_p_value": p_value,
        "level": level,
        "lower_is_better": lower_is_better,
        "baseline": baseline_summary,
        "variant": variant_summary,
        "mean_difference": mean_difference,
        "difference_stdev": difference_stdev,
        "interval": [low, high],
        "interval_excludes_zero": significant,
        "seed_noise_floor": noise_floor,
        "exceeds_noise_floor": abs(mean_difference) > noise_floor,
        "minimum_detectable_effect": detectable,
        "best_of_n_difference": (sign * (variant_summary["max"] - baseline_summary["max"])),
    }


def verdict(result):
    lines = []
    direction = "better" if result["mean_difference"] > 0 else "worse"
    if not result["paired"]:
        lines.append("Arms are unpaired (different lengths); pairing by seed would be "
                     "substantially more sensitive.")
    if result.get("permutation_p_value") is not None:
        lines.append(f"Fewer than {SMALL_SAMPLE} seeds: decided by a Student-t interval on the seed means (the "
                     "bootstrap undercovers here); exact permutation p-value "
                     f"{result['permutation_p_value']:.3g} (with very few seeds it cannot reach small values).")
    if result["interval_excludes_zero"]:
        lines.append(f"Supported: the {result['level'] * 100:.0f}% interval on the "
                     f"difference excludes zero, so the variant is {direction}.")
        if not result["exceeds_noise_floor"]:
            lines.append("But the mean difference is smaller than the seed spread of an "
                         "individual arm - report the distribution, not the mean alone.")
    else:
        lines.append(f"Not supported: the {result['level'] * 100:.0f}% interval on the "
                     "difference includes zero. This is consistent with seed noise.")
        lines.append(f"With this many seeds the smallest reliably detectable effect is "
                     f"{result['minimum_detectable_effect']:.4g}; observed difference is "
                     f"{result['mean_difference']:.4g}.")
    if abs(result["best_of_n_difference"]) > abs(result["mean_difference"]) * 1.5:
        lines.append("Comparing best-of-N would overstate this difference; best-of-N is "
                     "biased upward with N and is not a valid comparison.")
    return lines


def _format(result, lines):
    out = [
        f"{'Arm':<10} {'n':>3} {'mean':>12} {'stdev':>12} {'spread':>12}",
        f"{'baseline':<10} {result['baseline']['n']:>3} "
        f"{result['baseline']['mean']:>12.6g} {result['baseline']['stdev']:>12.6g} "
        f"{result['baseline']['spread']:>12.6g}",
        f"{'variant':<10} {result['variant']['n']:>3} "
        f"{result['variant']['mean']:>12.6g} {result['variant']['stdev']:>12.6g} "
        f"{result['variant']['spread']:>12.6g}",
        "",
        f"Comparison:        {'paired' if result['paired'] else 'unpaired'}",
        f"Mean difference:   {result['mean_difference']:.6g}",
        f"{result['level'] * 100:.0f}% interval:     "
        f"[{result['interval'][0]:.6g}, {result['interval'][1]:.6g}]",
        f"Seed noise floor:  {result['seed_noise_floor']:.6g}",
        f"Detectable effect: {result['minimum_detectable_effect']:.6g}  "
        f"(5% two-sided, 80% power)",
        "",
    ]
    return "\n".join(out + lines)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="?",
                        help='JSON with {"baseline": [...], "variant": [...]}')
    parser.add_argument("--baseline", type=float, nargs="+")
    parser.add_argument("--variant", type=float, nargs="+")
    parser.add_argument("--level", type=float, default=0.95)
    parser.add_argument("--lower-is-better", action=argparse.BooleanOptionalAction, default=None,
                        dest="lower_is_better",
                        help="score direction; overrides 'lower_is_better' in the runs file when given")
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--status", default="unvalidated", choices=STATUSES,
                    help="status label of the input data, echoed as status_label in the output (default unvalidated)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        if args.runs:
            with open(args.runs, encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("runs file must contain a JSON object")
            baseline = payload["baseline"]
            variant = payload["variant"]
            file_value = payload.get("lower_is_better")
            if file_value is not None and not isinstance(file_value, bool):
                raise ValueError("'lower_is_better' in the runs file must be true or false")
        elif args.baseline and args.variant:
            baseline, variant = args.baseline, args.variant
            file_value = None
        else:
            raise ValueError("supply a runs file, or both --baseline and --variant")
        if args.lower_is_better is not None:  # the command line wins when given
            lower_is_better, source = args.lower_is_better, "command line"
        elif file_value is not None:
            lower_is_better, source = file_value, "runs file"
        else:
            lower_is_better, source = False, "default (higher is better)"
        if args.resamples < 100:
            raise ValueError("resamples must be at least 100")
        result = compare(baseline, variant, args.level, lower_is_better,
                         args.resamples, args.seed)
        result["lower_is_better_source"] = source
        lines = verdict(result)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:  # JSON status, exit 2 (F-04)
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(2)

    if args.json:
        print(json.dumps({"status": "ok", **result, "verdict": lines, "status_label": args.status}, indent=2, allow_nan=False))
    else:
        print(_format(result, lines))


if __name__ == "__main__":
    main()

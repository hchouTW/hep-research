#!/usr/bin/env python3
"""Compare two model configurations across seeds, against the seed-noise floor.

Purpose: decide whether a reported improvement is real. The spread across seeds of an
unchanged configuration is the noise floor, and a large fraction of informally reported
gains are smaller than it. Reporting a single run, or the best of several, is not
evidence.

What it does: takes per-seed scores for a baseline and a variant, pairs them by seed
where possible, and reports the mean difference with a bootstrap confidence interval,
the seed spread of each arm, whether the interval excludes zero, and the minimum
effect this many seeds could reliably detect. Also flags a best-of-N comparison, which
is a biased estimator whose expectation rises with N.

Usage notes / assumptions: standard library only; PyTorch is not required. Scores are
assumed to be "higher is better" unless --lower-is-better is given. Paired mode
requires equal-length arrays whose entries correspond to the same seed and split;
unpaired mode is used automatically otherwise and is substantially less sensitive.
The bootstrap is seeded, so results are reproducible.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/compare_model_runs.py ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/assets/eval_runs.example.json
"""

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
    significant = (low > 0.0) or (high < 0.0)

    return {
        "paired": paired,
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
    parser.add_argument("--lower-is-better", action="store_true", dest="lower_is_better")
    parser.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        if args.runs:
            with open(args.runs, encoding="utf-8") as handle:
                payload = json.load(handle)
            baseline = payload["baseline"]
            variant = payload["variant"]
            lower_is_better = payload.get("lower_is_better", args.lower_is_better)
        elif args.baseline and args.variant:
            baseline, variant = args.baseline, args.variant
            lower_is_better = args.lower_is_better
        else:
            raise ValueError("supply a runs file, or both --baseline and --variant")
        if args.resamples < 100:
            raise ValueError("resamples must be at least 100")
        result = compare(baseline, variant, args.level, lower_is_better,
                         args.resamples, args.seed)
        lines = verdict(result)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"error: {exc}")

    if args.json:
        print(json.dumps({**result, "verdict": lines}, indent=2))
    else:
        print(_format(result, lines))


if __name__ == "__main__":
    main()

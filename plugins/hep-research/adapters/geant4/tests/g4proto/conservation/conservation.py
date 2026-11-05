#!/usr/bin/env python3
"""The energy-conservation checks of legacy mode (g4sim plan, Section 8.9), in their registered order: an independent trial, the derived numbers,
the calibration run with the absolute check, a second trial at the fixed q, then the relative check. No result of one stage is reused by a later one
as a sample. The negative control switches the accounting of world escape off (Section 15.1).

Usage: conservation.py run CONFIG STAGE --program PATH --baselines DIR --work DIR [--events N] [--control NAME]
       conservation.py derive-events CONFIG --work DIR       conservation.py absolute CONFIG --work DIR
       conservation.py derive-relative CONFIG --work DIR     conservation.py relative CONFIG --work DIR
From the plugin root. Prints JSON with a status key. Exit 0 ok, 1 a check failed or the design is invalid, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reacquire"))
import regress  # noqa: E402

GEV = 1000.0
EM = {"q_fraction": 1e-7, "q_constant_MeV": 0.0, "r_fraction": 1e-8}
HADRONIC = {"q_fraction": 0.60, "q_constant_MeV": 1 * GEV, "r_fraction": 0.40}
CONFIGS = {"em": {"run": "geant4-run-mirror-testem3", "limits": EM}, "hadronic-thin": {"run": "geant4-run-F937-TRK1000-nominal", "limits": HADRONIC},
           "hadronic-dense": {"run": "geant4-run-N6-TRK100-nominal", "limits": HADRONIC}}
SEEDS = {"trial": 101, "calibration": 202, "calibration-control": 212, "trial-q": 303, "trial-q-control": 313, "reference": 404, "under-test": 505, "under-test-control": 515}
MINIMUM_EVENTS, QUANTILE, CONFIDENCE, TARGET = 2995, 0.999, 0.95, 0.9
Z_TWO_SIDED, Z_ONE_SIDED, RESAMPLES, FALSE_POSITIVE = 1.959963984540054, 1.6448536269514722, 500, 0.05


def log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(Bin(n, p) <= k)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    return min(1.0, sum(math.exp(log_choose(n, i) + i * math.log(p) + (n - i) * math.log1p(-p)) for i in range(k + 1)))


def upper_bound(successes: int, n: int, confidence: float = CONFIDENCE) -> float:
    """One-sided Clopper-Pearson upper bound of a proportion, by bisection."""
    if successes >= n:
        return 1.0
    low, high = successes / n, 1.0
    for _ in range(200):
        middle = (low + high) / 2
        if binomial_cdf(successes, n, middle) > 1 - confidence:
            low = middle
        else:
            high = middle
    return high


def lower_bound(successes: int, n: int, confidence: float = CONFIDENCE) -> float:
    return 1.0 - upper_bound(n - successes, n, confidence)


def order_index(n: int) -> int | None:
    """The smallest k (1-based, ascending) with x_(k) a one-sided 95 % upper bound of the 99.9 % quantile: P(Bin(n, 0.999) < k) >= 0.95. None: n too small."""
    exceed = 1.0 - QUANTILE  # P(Bin(n, 0.999) < k) = P(Bin(n, 0.001) > n - k), summed from the small tail
    if binomial_cdf(0, n, exceed) > 1 - CONFIDENCE:
        return None
    room = 0
    while binomial_cdf(room + 1, n, exceed) <= 1 - CONFIDENCE:
        room += 1
    return n - room


def quantile_bound(absolute_sorted: list) -> float | None:
    k = order_index(len(absolute_sorted))
    return None if k is None else absolute_sorted[k - 1]


def mean_and_deviation(values: list) -> tuple:
    n = len(values)
    mean = math.fsum(values) / n
    return mean, math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (n - 1))


def absolute_passes(values: list, q_max: float, r_max: float) -> tuple:
    bound = quantile_bound(sorted(abs(value) for value in values))
    mean, deviation = mean_and_deviation(values)
    half = Z_TWO_SIDED * deviation / math.sqrt(len(values))
    return bound is not None and bound <= q_max and abs(mean) + half <= r_max, bound, mean, half


def normal_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def pass_probability(n: int, p_max: float, mean: float, deviation: float, r_max: float) -> float:
    """The lower bound P(A) + P(B) - 1 of Section 8.9: A the quantile bound holds, B the interval of the mean holds."""
    k = order_index(n)
    if k is None:
        return 0.0
    quantile = binomial_cdf(n - k, n, p_max)
    room = (r_max - abs(mean)) * math.sqrt(n) / deviation if deviation > 0 else math.inf
    interval = normal_cdf(room - Z_TWO_SIDED)
    return quantile + interval - 1


def required_events(p_max: float, mean: float, deviation: float, r_max: float, largest: int = 200000) -> int | None:
    n = MINIMUM_EVENTS
    while n <= largest:
        if pass_probability(n, p_max, mean, deviation, r_max) >= TARGET:
            return n
        n += 25
    return None


def fisher_one_sided(exceed_test: int, n_test: int, exceed_reference: int, n_reference: int) -> float:
    """P(at least exceed_test of the exceedances fall in the run under test), given the total: the hypergeometric tail."""
    total = exceed_test + exceed_reference
    denominator = log_choose(n_test + n_reference, total)
    return min(1.0, sum(math.exp(log_choose(n_test, i) + log_choose(n_reference, total - i) - denominator)
                        for i in range(exceed_test, min(total, n_test) + 1)))


def fisher_power(n: int, p0: float, p1: float) -> float:
    """The exact power at n events per run: the sum over both counts of those that reject."""
    def pmf(k, p):
        return math.exp(log_choose(n, k) + (k * math.log(p) if k else 0.0) + ((n - k) * math.log1p(-p) if n - k else 0.0)) if 0 < p < 1 else float((k == 0) if p <= 0 else (k == n))
    reference_top = min(n, int(n * p0 + 12 * math.sqrt(max(n * p0, 1.0))) + 12)
    power = 0.0
    for b in range(reference_top + 1):
        weight = pmf(b, p0)
        if weight < 1e-15:
            continue
        for a in range(n + 1):
            if fisher_one_sided(a, n, b, n) <= FALSE_POSITIVE:
                power += weight * (1.0 - binomial_cdf(a - 1, n, p1))
                break
    return power


def required_relative_events(p0: float, p1: float, largest: int = 3000, window: int = 40) -> int | None:
    """The smallest n with power >= 0.9 at n and at every larger n, the saw-tooth checked over the next window of n."""
    n = 2
    while n <= largest:
        if all(fisher_power(n + step, p0, p1) >= TARGET for step in range(window)):
            return n
        n += 1
    return None


def limits(config: dict, energy: float) -> tuple:
    rule = config["limits"]
    return rule["q_fraction"] * energy + rule["q_constant_MeV"], rule["r_fraction"] * energy


def read_stage(work: Path, config: str, stage: str) -> tuple:
    rows = json.loads((work / config / f"{stage}.json").read_text(encoding="utf-8"))
    return rows["residual_MeV"], rows["incident_MeV"], rows["accounting_errors"]


def derive_events(config: str, work: Path) -> dict:
    residuals, energy, errors = read_stage(work, config, "trial")
    q_max, r_max = limits(CONFIGS[config], energy)
    n = len(residuals)
    exceed = sum(abs(value) > q_max for value in residuals)
    mean, deviation = mean_and_deviation(residuals)
    p_max = upper_bound(exceed, n)
    mean_bound = abs(mean) + Z_ONE_SIDED * deviation / math.sqrt(n)
    deviation_bound = deviation * (1 + Z_ONE_SIDED / math.sqrt(2 * (n - 1)))
    needed = required_events(p_max, mean_bound, deviation_bound, r_max)
    return {"status": "ok" if needed else "invalid-design", "trial_events": n, "energy_MeV": energy, "q_max_MeV": q_max, "r_max_MeV": r_max, "exceedances": exceed,
            "p_max": p_max, "mu_r_MeV": mean_bound, "sigma_r_MeV": deviation_bound, "N": needed, "accounting_errors": errors}


def detection_rate(values: list, n: int, q_max: float, r_max: float) -> float:
    generator = random.Random(20261105)
    failed = sum(not absolute_passes(generator.choices(values, k=n), q_max, r_max)[0] for _ in range(RESAMPLES))
    return failed / RESAMPLES


def absolute(config: str, work: Path) -> dict:
    residuals, energy, errors = read_stage(work, config, "calibration")
    control, _, _ = read_stage(work, config, "calibration-control")
    q_max, r_max = limits(CONFIGS[config], energy)
    passed, bound, mean, half = absolute_passes(residuals, q_max, r_max)
    rate = detection_rate(control, len(residuals), q_max, r_max)
    ok = passed and errors == 0 and rate >= TARGET
    return {"status": "ok" if ok else "failed", "events": len(residuals), "q_max_MeV": q_max, "q_upper_bound_MeV": bound, "r_max_MeV": r_max, "mean_MeV": mean, "half_interval_MeV": half,
            "accounting_errors": errors, "control_detection_rate": rate, "q_hat_MeV": sorted(abs(value) for value in residuals)[int(QUANTILE * len(residuals))]}


def derive_relative(config: str, work: Path) -> dict:
    fixed = absolute(config, work)["q_hat_MeV"]
    correct, _, _ = read_stage(work, config, "trial-q")
    control, _, _ = read_stage(work, config, "trial-q-control")
    p0 = upper_bound(sum(abs(value) > fixed for value in correct), len(correct))
    p1 = lower_bound(sum(abs(value) > fixed for value in control), len(control))
    needed = required_relative_events(p0, p1)
    return {"status": "ok" if needed else "undetectable", "q_hat_MeV": fixed, "p0": p0, "p1": p1, "n": needed}


def relative(config: str, work: Path) -> dict:
    fixed = absolute(config, work)["q_hat_MeV"]
    reference, _, _ = read_stage(work, config, "reference")
    under_test, _, _ = read_stage(work, config, "under-test")
    control, _, _ = read_stage(work, config, "under-test-control")
    counts = {name: sum(abs(value) > fixed for value in values) for name, values in (("reference", reference), ("under_test", under_test), ("control", control))}
    p_correct = fisher_one_sided(counts["under_test"], len(under_test), counts["reference"], len(reference))
    generator = random.Random(20261106)
    rejected = 0
    for _ in range(RESAMPLES):
        a = sum(abs(value) > fixed for value in generator.choices(control, k=len(under_test)))
        b = sum(abs(value) > fixed for value in generator.choices(reference, k=len(reference)))
        rejected += fisher_one_sided(a, len(under_test), b, len(reference)) <= FALSE_POSITIVE
    rate = rejected / RESAMPLES
    return {"status": "ok" if p_correct > FALSE_POSITIVE and rate >= TARGET else "failed", "counts": counts, "p_value": p_correct, "control_detection_rate": rate, "events": len(under_test)}


def run_stage(args) -> dict:
    config = CONFIGS[args.config]
    rows = {row["run"]: row for row in json.loads((HERE.parent / "reacquire/recorded_runs.json").read_text(encoding="utf-8"))}
    row = rows[config["run"]]
    folder = args.work / args.config / f"{args.stage}-run"
    with gzip.open(args.baselines / "runs" / row["run"] / "probe-v2.json.gz", "rt", encoding="utf-8") as stream:
        record = json.load(stream)
    regress.write_inputs(row, record, folder)
    spec_path = folder / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    seed = SEEDS[args.stage]
    spec["run"]["events"] = args.events
    if "logical_run_seed" in spec["run"]:
        spec["run"]["logical_run_seed"] = seed
    spec["run"]["seeds"] = [seed, seed + 1]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    environment = {**__import__("os").environ}
    if args.control:
        environment["G4SIM_ACCOUNTING_CONTROL"] = args.control
    with (folder / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(args.program.resolve()), "ir.json", "spec.json"], cwd=folder, stdout=log, stderr=log, env=environment, check=False).returncode
    if code != 0:
        return {"status": "failed", "exit": code}
    residuals, incident, errors = [], 0.0, 0
    with (folder / "conservation.csv").open(encoding="utf-8") as stream:
        next(stream)
        for item in csv.DictReader(stream):
            residuals.append(float(item["residual_MeV"]))
            incident = float(item["incident_MeV"])
            errors += int(item["accounting_errors"])
    (args.work / args.config / f"{args.stage}.json").write_text(json.dumps({"residual_MeV": residuals, "incident_MeV": incident, "accounting_errors": errors}), encoding="utf-8")
    for name in ("events.csv", "events.root", "conservation.csv", "probe-v2.json", "probe.json", "ir.json"):
        (folder / name).unlink(missing_ok=True)
    return {"status": "ok", "events": len(residuals), "incident_MeV": incident, "accounting_errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "derive-events", "absolute", "derive-relative", "relative"))
    parser.add_argument("config", choices=tuple(CONFIGS))
    parser.add_argument("stage", nargs="?", choices=tuple(SEEDS))
    parser.add_argument("--program", type=Path)
    parser.add_argument("--baselines", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int)
    parser.add_argument("--control")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            (args.work / args.config).mkdir(parents=True, exist_ok=True)
            result = run_stage(args)
        else:
            result = {"derive-events": derive_events, "absolute": absolute, "derive-relative": derive_relative, "relative": relative}[args.command](args.config, args.work)
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": repr(err)}))
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

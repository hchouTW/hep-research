#!/usr/bin/env python3
"""Scoring side of T10's destriping replay: the comparator of the solver's product against the exact reference
(docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 4 and its fix round 1; K09 tolerances in
assets/t10-replay.tolerance.json (noisy, with the stopping ladder) and assets/t10-replay-noiseless.tolerance.json).

Differences are exact: each product float is read as its exact binary value and subtracted from the reference's exact Fraction;
squared 2-norms are compared exactly with the squared tolerance.

Gates: baselines and map within tau x ||a_ref||_2; the zero-sum of the product's baselines and of the reference's; with a ladder
record, the stopping ladder (each rung within safety x kappa x eps_j, and safety x G x kappa x eps_j for the map; between consecutive
rungs the baseline difference strictly smaller when the iteration count rises and equal when it does not, never fewer iterations; at
least min_informative_steps strictly smaller steps, else incomplete). Readings, not gates: whether the map difference shrinks at each
rung, ||dm|| / (G ||da||), the eps / 2 run (--halved) and the a-posteriori bound safety x max(r_n, 1e4 u) x ||b||_2 / lambda_min.

Before comparing, the record is checked against its derivation: kappa and G are recomputed from the timestream (NumPy) and must match
the record's within 0.01 and 1e-4; safety is at least 10; tau is not below safety x kappa x eps (or safety x G x kappa x eps); the
product's stopping value is the record's; kappa x eps is at least 1e3 rounding units; the reference's multiplier is exactly 0 (the
right side lies in 1-perp).

A drafted record gives DRAFT READING lines and no verdict (exit 3, incomplete); a frozen one gives PASS or FAIL lines (exit 0 passed,
1 failed, 3 incomplete when the ladder has too few informative steps or was not run). Exit 2: bad input, or a record that does not
hold its derivation.
Usage: t10_comparator.py compare --timestream T --product P --reference R --tolerance TOL [--ladder P_j ...] [--halved P2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy

ROUNDING_UNIT = 2.0 ** -53
MINIMUM_SAFETY = 10
KEYS = frozenset({"format", "state", "frozen_by", "k09", "stopping", "safety", "kappa", "map_gain", "tau_baselines", "tau_map", "norm",
                  "derivation", "zero_sum_relative", "ladder", "min_informative_steps", "ladder_rule", "readings", "expected_difference"})


class ToleranceError(ValueError):
    """The tolerance record, a product or the reference does not hold the record's derivation (exit 2)."""


def _operators(document: dict):
    pixel = numpy.array(document["pixel"])
    samples, length, pixels = pixel.size, document["baseline_length"], document["pixels"]
    P = numpy.zeros((samples, pixels))
    P[numpy.arange(samples), pixel] = 1
    F = numpy.zeros((samples, samples // length))
    F[numpy.arange(samples), numpy.arange(samples) // length] = 1
    inverse = numpy.linalg.inv(P.T @ P)
    Z = numpy.eye(samples) - P @ inverse @ P.T
    return P, F, Z, inverse


def fixture_numbers(document: dict) -> tuple[float, float]:
    """kappa of D = F^T Z F on 1-perp and G = ||M^-1 P^T F||_2, from the pointing alone."""
    P, F, Z, inverse = _operators(document)
    eigenvalues = numpy.sort(numpy.linalg.eigvalsh(F.T @ Z @ F))
    return float(eigenvalues[-1] / eigenvalues[1]), float(numpy.linalg.norm(inverse @ P.T @ F, 2))


def _right_side_and_lambda_min(document: dict) -> tuple[float, float]:
    P, F, Z, _ = _operators(document)
    b = F.T @ Z @ numpy.array(document["value"], dtype=float)
    eigenvalues = numpy.sort(numpy.linalg.eigvalsh(F.T @ Z @ F))
    return float(numpy.linalg.norm(b - b.mean())), float(eigenvalues[1])


def _check_record(document: dict, record: dict, product: dict, reference: dict) -> tuple[float, float]:
    if not isinstance(record, dict) or set(record) != KEYS or record["format"] != "t10-replay-tolerance/1" or record["state"] not in ("drafted", "frozen"):
        raise ToleranceError("not a t10-replay-tolerance/1 record with state drafted or frozen")
    kappa, gain = fixture_numbers(document)
    eps, safety = record["stopping"], record["safety"]
    if safety < MINIMUM_SAFETY:
        raise ToleranceError(f"the record's safety {safety} is below {MINIMUM_SAFETY}")
    if abs(record["kappa"] - kappa) > 0.01 or abs(record["map_gain"] - gain) > 1e-4:
        raise ToleranceError(f"the record's kappa {record['kappa']} or G {record['map_gain']} is not the timestream's ({kappa:.4f}, {gain:.5f})")
    if product["solver"]["stopping"] != eps:
        raise ToleranceError(f"the product stopped at {product['solver']['stopping']}, the record is for {eps}")
    if kappa * eps < 1e3 * ROUNDING_UNIT:
        raise ToleranceError(f"kappa x eps = {kappa * eps:.3e} is below 1e3 rounding units: the bound would compare rounding")
    if record["tau_baselines"] < safety * kappa * eps:
        raise ToleranceError(f"tau_baselines {record['tau_baselines']} is below safety x kappa x eps = {safety * kappa * eps:.4e}")
    if record["tau_map"] < safety * gain * kappa * eps:
        raise ToleranceError(f"tau_map {record['tau_map']} is below safety x G x kappa x eps = {safety * gain * kappa * eps:.4e}")
    if Fraction(reference["multiplier"]) != 0:
        raise ToleranceError(f"the reference's multiplier is {reference['multiplier']}, not exactly 0: the reference is inconsistent")
    return kappa, gain


def _exact(items) -> list[Fraction]:
    return [Fraction(item["exact"]) for item in items]


def _squared_difference(values, exact) -> Fraction:
    return sum(((Fraction(v) - x) ** 2 for v, x in zip(values, exact)), Fraction(0))


def _differences(product: dict, reference: dict) -> dict:
    if len(product["baselines"]) != len(reference["baselines"]) or len(product["map"]) != len(reference["map"]):
        raise ValueError("a product and the reference differ in size")
    return {"baselines": _squared_difference(product["baselines"], _exact(reference["baselines"])),
            "map": _squared_difference(product["map"], _exact(reference["map"])),
            "iterations": product["solver"]["iterations"], "relative_residual": product["solver"]["relative_residual"],
            "stopping": product["solver"]["stopping"]}


def _within(squared: Fraction, tau: float, size_squared: Fraction) -> bool:
    return squared <= Fraction(tau) ** 2 * size_squared


def _reading(found: dict, size: float) -> dict:
    return {"iterations": found["iterations"], "relative_residual": found["relative_residual"], "stopping": found["stopping"],
            "baselines_relative": math.sqrt(float(found["baselines"])) / size, "map_relative": math.sqrt(float(found["map"])) / size}


def _ladder(rungs: list, reference: dict, record: dict, size_squared: Fraction, size: float) -> dict:
    expected = list(record["ladder"])
    if [rung["solver"]["stopping"] for rung in rungs] != expected:
        raise ToleranceError(f"the ladder's stopping values are {[r['solver']['stopping'] for r in rungs]}, the record's {expected}")
    safety, kappa, gain = record["safety"], record["kappa"], record["map_gain"]
    found = [_differences(rung, reference) for rung in rungs]
    rows = []
    for eps_j, item in zip(expected, found):
        row = {**_reading(item, size), "baselines_within": _within(item["baselines"], safety * kappa * eps_j, size_squared),
               "map_within": _within(item["map"], safety * gain * kappa * eps_j, size_squared)}
        row["gain_ratio_reading"] = (math.sqrt(float(item["map"]) / float(item["baselines"])) / gain) if item["baselines"] else None
        rows.append(row)
    steps = []
    for before, after in zip(found, found[1:]):
        rising = after["iterations"] > before["iterations"]
        if after["iterations"] < before["iterations"]:
            rule = False
        elif rising:
            rule = after["baselines"] < before["baselines"]
        else:
            rule = after["baselines"] == before["baselines"]
        steps.append({"from": before["stopping"], "to": after["stopping"], "informative": rising, "passed": rule,
                      "map_smaller": after["map"] < before["map"]})  # a reading
    informative = sum(step["informative"] and step["passed"] for step in steps)
    passed = all(row["baselines_within"] and row["map_within"] for row in rows) and all(step["passed"] for step in steps)
    return {"rungs": rows, "steps": steps, "informative_steps": informative, "passed": passed,
            "enough": informative >= record["min_informative_steps"]}


def compare(document: dict, product: dict, reference: dict, record: dict, ladder: list | None = None, halved: dict | None = None) -> dict:
    kappa, gain = _check_record(document, record, product, reference)
    eps = record["stopping"]
    reference_baselines = _exact(reference["baselines"])
    size_squared = sum((x * x for x in reference_baselines), Fraction(0))
    size = math.sqrt(float(size_squared))
    nominal = _differences(product, reference)
    checks = {"baselines": _within(nominal["baselines"], record["tau_baselines"], size_squared),
              "map": _within(nominal["map"], record["tau_map"], size_squared)}
    total = sum((Fraction(v) for v in product["baselines"]), Fraction(0))
    magnitude = sum((abs(Fraction(v)) for v in product["baselines"]), Fraction(0))
    zero_sum = {"passed": abs(total) <= Fraction(record["zero_sum_relative"]) * magnitude, "sum": float(total), "sum_abs": float(magnitude),
                "reference_sum_exact_zero": sum(reference_baselines, Fraction(0)) == 0}
    checks["zero_sum"] = zero_sum["passed"] and zero_sum["reference_sum_exact_zero"]
    norm_b, lambda_min = _right_side_and_lambda_min(document)
    bound = record["safety"] * max(nominal["relative_residual"], 1e4 * ROUNDING_UNIT) * norm_b / lambda_min
    result = {"kappa": kappa, "map_gain": gain, "reference_baseline_norm": size, "nominal": _reading(nominal, size), "zero_sum": zero_sum,
              "a_posteriori": {"bound": bound, "bound_relative": bound / size, "baselines_relative": _reading(nominal, size)["baselines_relative"],
                               "within_reading": math.sqrt(float(nominal["baselines"])) <= bound}}
    enough = True
    if record["ladder"] is not None:
        if ladder is None:
            result["ladder"] = None
            enough = False
        else:
            result["ladder"] = _ladder(ladder, reference, record, size_squared, size)
            checks["ladder"] = result["ladder"]["passed"]
            enough = result["ladder"]["enough"]
    elif ladder is not None:
        raise ToleranceError("this record has no ladder")
    if halved is not None:
        if halved["solver"]["stopping"] != eps / 2:
            raise ToleranceError(f"the eps / 2 run stopped at {halved['solver']['stopping']}, not {eps / 2}")
        found = _differences(halved, reference)
        result["halving_reading"] = {**_reading(found, size), "more_iterations": found["iterations"] > nominal["iterations"],
                                     "bit_identical": halved["map"] == product["map"] and halved["baselines"] == product["baselines"],
                                     "within_half_tau": _within(found["baselines"], record["tau_baselines"] / 2, size_squared)
                                     and _within(found["map"], record["tau_map"] / 2, size_squared)}
    result["checks"] = checks
    if record["state"] == "drafted":
        result["status"] = "incomplete"
    elif not all(checks.values()):
        result["status"] = "failed"
    else:
        result["status"] = "passed" if enough else "incomplete"
    return result


def _load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    cmp = sub.add_parser("compare")
    cmp.add_argument("--timestream", required=True)
    cmp.add_argument("--product", required=True)
    cmp.add_argument("--reference", required=True)
    cmp.add_argument("--tolerance", required=True)
    cmp.add_argument("--ladder", action="append", help="a ladder product, in the record's order of stopping values")
    cmp.add_argument("--halved", help="the eps / 2 product (a reading)")
    args = ap.parse_args(argv)
    try:
        document, product, reference, record = (_load(p) for p in (args.timestream, args.product, args.reference, args.tolerance))
        ladder = [_load(p) for p in args.ladder] if args.ladder else None
        halved = _load(args.halved) if args.halved else None
        source = _sha256(args.timestream)
        made = [("product", product), ("halved product", halved)] + [(f"ladder product {k}", p) for k, p in enumerate(ladder or [])]
        for name, found in made:
            if found is not None and found["input"]["sha256"] != source:
                raise ValueError(f"the {name} was not made from this timestream")
        if reference.get("input_sha256") != source:
            raise ValueError("the reference was not made from this timestream")
        result = compare(document, product, reference, record, ladder, halved)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"operation": "compare", "status": "rejected", "reason": str(exc)}))
        return 2
    prefix = "DRAFT READING" if record["state"] == "drafted" else None
    for name, ok in result["checks"].items():
        lead = prefix or ("PASS" if ok else "FAIL")
        detail = result["ladder"] if name == "ladder" else result["zero_sum"] if name == "zero_sum" else result["nominal"]
        print(f"{lead} comparator {name}: {'within' if ok else 'outside'} ({json.dumps(detail, sort_keys=True)})")
    if result.get("ladder") is not None:
        print(f"READING ladder informative steps {result['ladder']['informative_steps']} (at least {record['min_informative_steps']} needed)")
    elif record["ladder"] is not None:
        print("READING ladder not run: no verdict")
    print(f"READING a-posteriori bound {result['a_posteriori']['bound_relative']:.3e} of ||a_ref||; measured {result['a_posteriori']['baselines_relative']:.3e}")
    if "halving_reading" in result:
        print(f"READING eps/2 run: {json.dumps(result['halving_reading'], sort_keys=True)}")
    print(json.dumps({"operation": "compare", "tolerance_sha256": _sha256(args.tolerance), "tolerance_state": record["state"], **result},
                     sort_keys=True))
    return {"incomplete": 3, "passed": 0, "failed": 1}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())

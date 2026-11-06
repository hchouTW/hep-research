#!/usr/bin/env python3
"""Exercise the GB15 tests at the registered size without Geant4 and without any test sample: photon counts drawn with numpy from the target behaviour itself,
on the trial's steps repeated. Every target test must pass and every control must be rejected, or the design has no power; this says nothing about Geant4.

Usage: synthetic_check.py TRIAL_FOLDER NUMBERS.json [REPEATS]   Prints JSON with a status key; exit 0 ok, 1 a test or control went wrong, 2 bad input.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

import scintillation_moments as moments
import scintillation_tests as tests
from judge import judge_sums

HERE = Path(__file__).resolve().parent
DESIGN = json.loads((HERE / "design.json").read_text(encoding="utf-8"))["gb15"]


def draw_photons(mu: np.ndarray, resolution: float, generator: np.random.Generator) -> np.ndarray:
    gaussian = mu > moments.POISSON_LIMIT
    drawn = generator.poisson(np.where(gaussian, 0.0, mu)).astype(np.int64)
    rounded = np.floor(generator.normal(mu[gaussian], resolution * np.sqrt(mu[gaussian])) + 0.5)
    drawn[gaussian] = np.maximum(rounded, 0).astype(np.int64)
    return drawn


def one_pass(item: dict, steps: np.ndarray, repeats: int, tables: dict, generator: np.random.Generator) -> dict:
    is_step = item in DESIGN["step_sets"]
    edges = DESIGN["step_bin_edges"] if is_step else DESIGN["formula_bin_edges"]
    sums = tests.Sums(edges, ["target", *item["controls"]])
    light = DESIGN["yield_per_MeV"] * (steps["visible"] if item.get("saturation", True) else steps["deposit"])
    copied = steps.copy()
    for _ in range(repeats):
        copied["photons"] = draw_photons(light, item["resolution"], generator)
        if is_step:
            tests.add_step_chunk(sums, item, copied, DESIGN["yield_per_MeV"], tables)
        else:
            tests.add_formula_chunk(sums, item, copied, DESIGN["yield_per_MeV"], tables[item["resolution"]])
    return judge_sums(sums, item, edges, DESIGN)


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(json.dumps({"status": "rejected", "message": "usage: synthetic_check.py TRIAL_FOLDER NUMBERS.json [REPEATS]"}))
        return 2
    folder = Path(sys.argv[1])
    numbers = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["gb15"]
    repetitions = int(sys.argv[3]) if len(sys.argv) == 4 else 1
    generator = np.random.default_rng(15)
    tables = {value: moments.StepMoments(value) for value in {item["resolution"] for item in DESIGN["step_sets"] + DESIGN["formula_sets"]} | {1.0}}
    report, good = {}, True
    for item in [entry for entry in DESIGN["step_sets"] + DESIGN["formula_sets"] if entry.get("must_pass", True)]:
        header, steps = tests.read_steps(folder / "gb15" / f"{item['name']}_0")
        repeats = math.ceil(numbers["events_per_set"][item["name"]] / header["events"])
        rows = []
        for _ in range(repetitions):
            result = one_pass(item, steps, repeats, tables, generator)
            rows.append(result)
        passes = sum(row["all_equivalent"] for row in rows)
        rejected = {name: sum(row["controls"][name]["rejected"] for row in rows) for name in item["controls"]}
        report[item["name"]] = {"repeats_of_trial": repeats, "all_equivalent": passes, "of": repetitions, "controls_rejected": rejected,
                                "worst_abs_residual_over_margin": max(abs(item_test["residual"]) / item_test["margin"] for row in rows for item_test in row["tests"] if item_test["records"] > 0),
                                "worst_reach_over_margin": max((abs(item_test["residual"]) + item_test["upper"] - item_test["residual"]) / item_test["margin"] for row in rows for item_test in row["tests"] if item_test["records"] > 0),
                                "failed_by_control": {name: rows[0]["controls"][name]["failed_tests"] for name in item["controls"]}}
        good = good and passes == repetitions and all(count == repetitions for count in rejected.values())
    print(json.dumps({"status": "ok" if good else "not_met", "sets": report}, indent=1, default=float))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())

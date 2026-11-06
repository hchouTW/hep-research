#!/usr/bin/env python3
"""S3 gate 4: the sensitivity test of Section 8.7. Everything that sets a charged step is halved at once, and the observables must stay within the declared tolerance; forcing every charged
deposit to the post-step point must be detected.

  sensitivity.py run LABEL --folder DIR --events N --seed S --program PATH [--halved] [--control]   one run, on prototype v2
  sensitivity.py compare A B --folder DIR                                                           the observables of two runs
  sensitivity.py judge NOMINAL HALVED CONTROL --folder DIR                                          gate 4, by the registered tolerances
Prints JSON with a status key. Exit 0 ok, 1 failed, 2 bad input. In an activated Geant4 environment, from the plugin root.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
# FTFP_BERT_EMZ's values as Geant4 reports them, and the two range factors of G4EmStandardPhysics_option4
NOMINAL_STEP_FUNCTIONS = {"step_function_electron": ["0.2", "0.01"], "step_function_muon_hadron": ["0.1", "0.05"], "step_function_light_ion": ["0.1", "0.02"], "step_function_ion": ["0.1", "0.001"]}
NOMINAL_RANGE_FACTORS = {"msc_range_factor": "0.08", "msc_muhad_range_factor": "0.2"}
NOMINAL_STEP_MM, NOMINAL_FRACTION = "2", "0.1"
DEPTH_TOLERANCE_MM, TOTAL_TOLERANCE, ONE_SIDED_Z = 0.1, math.log(1.005), 1.6448536269514722  # registered in the S3 card: f x w for 1 mm bins


def half(text: str) -> str:
    return repr(float(text) / 2)


def card_and_request(spec_folder: Path, halved: bool, events: int, seed: int) -> tuple:
    request = json.loads((spec_folder / "request.json").read_text(encoding="utf-8"))
    card = json.loads((spec_folder / "run.json").read_text(encoding="utf-8"))
    scale = half if halved else str
    request["scorers"] = [{"name": "depth", "readout": "ecal", "select": {"tags": ["crystal"]}, "quantity": "edep", "segmentation": {"along_axis": {"axis": "z", "width_mm": "1"}}, "split": "apportion",
                           "apportion_short_step_fraction": scale(NOMINAL_FRACTION)}]
    card["physics"]["user_limits"] = {"CrystalRegion": {"max_step_mm": scale(NOMINAL_STEP_MM)}}
    card["physics"]["em_parameters"] = {**{key: [scale(value[0]), scale(value[1])] for key, value in NOMINAL_STEP_FUNCTIONS.items()}, **{key: scale(value) for key, value in NOMINAL_RANGE_FACTORS.items()}}
    card["run"].update({"events": events, "logical_run_seed": seed})
    return request, card


def observables(folder: Path) -> dict:
    """Per event: the crystals' total and the deposit-weighted depth, as (total, depth x total)."""
    events: dict = {}
    with (folder / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[2] == "-1":
                continue
            total, moment = events.get(row[0], (0.0, 0.0))
            value = float(row[4])
            events[row[0]] = (total + value, moment + value * (int(row[3]) + 0.5))
    return events


def ratio_of_sums(events: dict) -> tuple:
    """Mean total, mean depth and the delta-method error of the depth."""
    totals = [value[0] for value in events.values()]
    moments = [value[1] for value in events.values()]
    count = len(totals)
    mean_total, mean_moment = math.fsum(totals) / count, math.fsum(moments) / count
    depth = mean_moment / mean_total
    residual = [moment - depth * total for total, moment in zip(totals, moments)]
    error = math.sqrt(math.fsum(value * value for value in residual) / (count - 1) / count) / mean_total
    spread = math.sqrt(math.fsum((value - mean_total) ** 2 for value in totals) / (count - 1))
    return mean_total, depth, error, spread / math.sqrt(count)


def compare(first: Path, second: Path) -> dict:
    left, right = observables(first), observables(second)
    a, b = ratio_of_sums(left), ratio_of_sums(right)
    shared = [key for key in left if key in right and left[key][0] > 0 and right[key][0] > 0]
    paired = [right[key][1] / right[key][0] - left[key][1] / left[key][0] for key in shared]
    mean = math.fsum(paired) / len(paired)
    deviation = math.sqrt(math.fsum((value - mean) ** 2 for value in paired) / (len(paired) - 1))
    return {"status": "ok", "events": [len(left), len(right)], "total_MeV": [a[0], b[0]], "log_ratio_total": math.log(b[0] / a[0]), "log_ratio_error": math.hypot(a[3] / a[0], b[3] / b[0]), "depth_mm": [a[1], b[1]],
            "depth_change_mm": b[1] - a[1], "depth_change_error_mm": math.hypot(a[2], b[2]), "paired_depth_change_mm": mean, "paired_error_mm": deviation / math.sqrt(len(paired)), "events_differing": sum(value != 0 for value in paired)}


def judge(nominal: Path, halved: Path, control: Path) -> dict:
    """TOST on both observables at alpha = 0.05; the control, whose history is the nominal run's, must move the depth beyond the tolerance."""
    change, forced = compare(nominal, halved), compare(nominal, control)
    total_bound = abs(change["log_ratio_total"]) + ONE_SIDED_Z * change["log_ratio_error"]
    depth_bound = abs(change["depth_change_mm"]) + ONE_SIDED_Z * change["depth_change_error_mm"]
    detected = abs(forced["paired_depth_change_mm"]) - ONE_SIDED_Z * forced["paired_error_mm"] > DEPTH_TOLERANCE_MM
    passed = total_bound <= TOTAL_TOLERANCE and depth_bound <= DEPTH_TOLERANCE_MM and detected
    return {"status": "ok" if passed else "failed", "total_bound": total_bound, "total_tolerance": TOTAL_TOLERANCE, "depth_bound_mm": depth_bound, "depth_tolerance_mm": DEPTH_TOLERANCE_MM,
            "control_depth_change_mm": forced["paired_depth_change_mm"], "control_detected": detected, "halved": change}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "compare", "judge"))
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--spec-folder", type=Path)
    parser.add_argument("--events", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--program", type=Path)
    parser.add_argument("--halved", action="store_true")
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    if args.command == "compare":
        print(json.dumps(compare(args.folder / args.labels[0] / "run", args.folder / args.labels[1] / "run"), indent=1))
        return 0
    if args.command == "judge":
        verdict = judge(*(args.folder / label / "run" for label in args.labels))
        print(json.dumps(verdict, indent=1))
        return 0 if verdict["status"] == "ok" else 1
    work = args.folder / args.labels[0]
    work.mkdir(parents=True, exist_ok=True)
    request, card = card_and_request(args.spec_folder, args.halved, args.events, args.seed)
    (work / "request.in.json").write_text(json.dumps(request), encoding="utf-8")
    (work / "run.in.json").write_text(json.dumps(card), encoding="utf-8")
    environment = {**os.environ, **({"G4SIM_SCORER_CONTROL": "force_post_step"} if args.control else {})}
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(args.spec_folder / "detector.json"), "--request", str(work / "request.in.json"), "--run", str(work / "run.in.json"),
                           "--program", str(args.program.resolve()), "--work", str(work / "run")], capture_output=True, text=True, check=False, env=environment)
    result = json.loads(done.stdout.strip().splitlines()[-1])
    print(json.dumps({key: result.get(key) for key in ("status", "closure", "problems", "findings", "stage", "exit_status")}))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""S5's labelled checks of the kits, not references (g4sim plan, Section 15.3): sampling-fraction, shower-containment and tof-beta, as registered in g4sim-tasks/S5.md.

Usage: labelled_checks.py --program PATH --simroot PATH --work DIR   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 every check holds, 1 otherwise.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "skills/hep-detector/scripts"))

import kit_benchmarks as kits  # noqa: E402
from geant4_benchmarks import gamma_p  # noqa: E402

SAMPLING_FRACTION, SAMPLING_WINDOW = 0.0882, 0.10
CRITICAL_ENERGY_MEV, PROFILE_B = 7.97, 0.5
TOF_LIMIT = 0.001
MUON_MEV = 105.6583755
MUON_KINETIC_MEV = 1000.0
LIGHT_MM_PER_NS = 299.792458
TOF = {"planes": 2, "bars": 8, "bar_length_mm": 1000.0, "bar_width_mm": 100.0, "bar_thickness_mm": 10.0, "plane_gap_mm": 1000.0, "bar_material": "G4_POLYSTYRENE", "world_material": "G4_Galactic"}


def scorer(name: str, tag: str, **extra) -> dict:
    return {"name": name, "readout": "none", "select": {"tags": [tag]}, "quantity": "edep", **extra}


def calorimeter(root: Path, name: str, side_mm: float, particle: str, kinetic_mev: float, events: int, program: Path) -> Path:
    folder = root / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    fields = {**kits.SCECAL, "tower_side_mm": side_mm}
    kits.derive(folder, "calorimeter", {**kits.COMMON, **fields})
    depth = fields["layers"] * (fields["absorber_mm"] + fields["active_mm"] + fields["support_mm"])
    request = {"schema": "simulation-request/1", "source": kits.beam(particle, kinetic_mev, [0, 0, -(depth / 2 + 60)], [0, 0, 1]), "scorers": [scorer("active", "active"), scorer("absorber", "absorber")]}
    return kits.simulate(folder, program, request, events)


def scorer_totals(work: Path) -> dict:
    totals: dict = {}
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[2] != "-1" and row[0].isdigit():
                totals[row[1]] = totals.get(row[1], 0.0) + float(row[4])
    return totals


def sampling_fraction(root: Path, program: Path) -> dict:
    totals = scorer_totals(calorimeter(root, "sampling", kits.SCECAL["tower_side_mm"], "mu-", MUON_KINETIC_MEV, 2000, program))
    value = totals["active"] / (totals["active"] + totals["absorber"])
    return {"value": value, "declared": SAMPLING_FRACTION, "relative_difference": value / SAMPLING_FRACTION - 1, "holds": abs(value / SAMPLING_FRACTION - 1) <= SAMPLING_WINDOW}


def depth_in_x0(work: Path) -> float:
    lengths = {item["name"]: float.fromhex(item["radiation_length_mm"]) for item in json.loads((work / "probe-v2.json").read_text(encoding="utf-8"))["materials"]}
    layer = kits.SCECAL
    return layer["layers"] * (layer["absorber_mm"] / lengths[layer["absorber_material"]] + layer["active_mm"] / lengths[kits.COMMON["active_material"]] + layer["support_mm"] / lengths[layer["support_material"]])


def containment(root: Path, program: Path) -> dict:
    energy = 10000.0
    work = calorimeter(root, "containment", 1800.0, "e-", energy, 300, program)
    with (work / "conservation.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    escaped = [sum(float(row[key]) for key in row if key.startswith("escape_")) / float(row["incident_MeV"]) for row in rows]
    depth = depth_in_x0(work)
    shape = 1 + PROFILE_B * (math.log(energy / CRITICAL_ENERGY_MEV) - 0.5)
    reference = 1 - gamma_p(shape, PROFILE_B * depth)
    window = max(0.3 * min(reference, 1 - reference), 0.02)
    value = statistics.fmean(escaped)
    return {"value": value, "standard_error": statistics.stdev(escaped) / math.sqrt(len(escaped)), "reference": reference, "depth_x0": depth, "window": window, "holds": abs(value - reference) <= window}


def flight_times(work: Path, simroot: Path) -> dict:
    target = work / "tof_hits.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", "tracker_hits", "--out", str(target)], check=True, capture_output=True, text=True, timeout=300)
    with target.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["step_track_id"] == "1"]
    entries: dict = {}
    for row in sorted(rows, key=lambda item: (int(item["event_id"]), int(item["step_index"]))):
        entries.setdefault(row["event_id"], []).append(row)
    return entries


def tof_beta(root: Path, program: Path, simroot: Path) -> dict:
    folder = root / "tof"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    kits.derive(folder, "tof", TOF)
    start = -(TOF["plane_gap_mm"] + TOF["bar_thickness_mm"]) / 2 - 50
    request = {"schema": "simulation-request/1", "source": kits.beam("mu-", MUON_KINETIC_MEV, [0, 0, start], [0, 0, 1]), "scorers": [scorer("bars", "active", level="event_file", hit_kind="tracker")]}
    work = kits.simulate(folder, program, request, 2000)
    energy = MUON_KINETIC_MEV + MUON_MEV
    beta = math.sqrt(1 - (MUON_MEV / energy) ** 2)
    ratios, doubled = [], []
    for rows in flight_times(work, simroot).values():
        first = rows[0]
        second = next((row for row in rows if float(row["z_mm"]) > 0), None)
        if float(first["z_mm"]) > 0 or second is None:
            continue
        length = math.dist([float(first[axis]) for axis in ("x_mm", "y_mm", "z_mm")], [float(second[axis]) for axis in ("x_mm", "y_mm", "z_mm")])
        flight = float(second["time_ns"]) - float(first["time_ns"])
        ratios.append(flight / (length / (beta * LIGHT_MM_PER_NS)))
        doubled.append(flight / ((length + TOF["plane_gap_mm"]) / (beta * LIGHT_MM_PER_NS)))
    mean, control = statistics.fmean(ratios), statistics.fmean(doubled)
    return {"events": len(ratios), "ratio": mean, "standard_error": statistics.stdev(ratios) / math.sqrt(len(ratios)), "control_ratio": control, "control_fails": abs(control - 1) > TOF_LIMIT, "holds": abs(mean - 1) <= TOF_LIMIT and abs(control - 1) > TOF_LIMIT}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    root, program = args.work.resolve(), args.program.resolve()
    results = {"sampling-fraction": sampling_fraction(root, program), "shower-containment": containment(root, program), "tof-beta": tof_beta(root, program, args.simroot.resolve())}
    held = all(item["holds"] for item in results.values())
    print(json.dumps({"status": "ok" if held else "failed", **results}, indent=1))
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())

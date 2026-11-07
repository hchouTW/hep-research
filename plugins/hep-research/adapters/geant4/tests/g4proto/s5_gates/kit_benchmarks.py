#!/usr/bin/env python3
"""S5 gates 5 and 6: the kit benchmarks registered in the task card, each with its negative control (g4sim plan, Section 15.3).

Every geometry comes from a kit through g4kit.py. Values and thresholds are the card's; this script only computes them.
  run NAME --program PATH --work DIR [--events N]   one benchmark: linearity, resolution, scattering, material
Prints JSON with a status key. Exit 0 the benchmark passes and its control fails, 1 otherwise.
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

PLUGIN = Path(__file__).resolve().parents[5]
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
KIT = PLUGIN / "skills/hep-detector/scripts/g4kit.py"
FACTS = "assumed"
TUNGSTEN_CARBIDE = {"composition": {"W": "0.7443", "C": "0.0486", "Co": "0.1999", "Cr": "0.0072"}, "density_g_cm3": "14.25", "facts": "arXiv:1707.07126, the balanced composition"}
STEEL = {"composition": {"Fe": "0.9834", "Mn": "0.014", "C": "0.0017", "S": "0.00045", "P": "0.00045"}, "density_g_cm3": "7.86", "facts": "arXiv:1003.2662, S235 steel"}
# 5.23 mm per layer: FR4 1.0, foil 0.23, cable 1.5, air 2.5 mm, as one mixture by mass, with FR4 as in examples/zdc-synthetic-ecal, foil as polystyrene and cable as PVC: the mixture is an assumption, its thickness the paper's
SUPPORT = {"composition": {"C": "0.4286", "H": "0.0411", "O": "0.1716", "Si": "0.1200", "Cl": "0.2387"}, "density_g_cm3": "0.76", "facts": "assumed mixture of arXiv:1003.2662's layer table"}
SCECAL = {"layers": 30, "absorber_mm": 3.49, "active_mm": 3.02, "support_mm": 2.36, "tower_side_mm": 180.0, "absorber_material": "WC", "support_material": "G4_AIR", "materials": {"WC": TUNGSTEN_CARBIDE}}
AHCAL = {"layers": 38, "absorber_mm": 21.4, "active_mm": 5.0, "support_mm": 5.23, "tower_side_mm": 900.0, "absorber_material": "S235", "support_material": "SUPPORT", "materials": {"S235": STEEL, "SUPPORT": SUPPORT}}
COMMON = {"towers_x": 1, "towers_y": 1, "active_material": "G4_POLYSTYRENE", "wrap_material": "G4_AIR", "guide_material": "G4_AIR", "world_material": "G4_Galactic"}
LINEARITY_GEV = (2, 4, 8, 12, 15, 20, 30, 32)
RESOLUTION_GEV = (10, 15, 20, 30, 40, 50)
LINEARITY_LIMIT = 0.015
STOCHASTIC, STOCHASTIC_BAND = 0.219, 0.028
LISTS = ("FTFP_BERT_EMZ", "FTFP_BERT_EMY")
BERGER = {(1, 50): (2.064, 0.078), (1, 100): (3.109, 0.052), (2, 50): (1.081, 0.040), (2, 100): (1.661, 0.024), (3, 50): (0.714, 0.024), (3, 100): (1.151, 0.018)}  # (GeV/c, um): RMS98 and its statistical error, 0.1 mrad
BERGER_SYSTEMATIC = 0.05
MATERIAL_X0_PERCENT, MATERIAL_BAND = 0.214, 0.005


def derive(folder: Path, kind: str, fields: dict) -> Path:
    geometry = folder / "design.geometry.json"
    geometry.write_text(json.dumps({"schema": "design-geometry/1", "geometry": kind, "geometry_kind": kind, "fields": fields}), encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(KIT), "derive", "--geometry", str(geometry), "--out-detector", str(folder / "spec.json"), "--out-derivation", str(folder / "derivation.json")], check=True, capture_output=True, text=True, timeout=120)
    return folder / "spec.json"


def simulate(folder: Path, program: Path, request: dict, events: int, physics_list: str = LISTS[0], threads: int = 2) -> Path:
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": physics_list, "cuts_mm": {"default": "0.7"}}, "accounting": "separated", "run": {"events": events, "first_event": 0, "logical_run_seed": 20261107, "mode": "mt", "seeding": "per-event", "threads": threads}}
    (folder / "request.json").write_text(json.dumps(request), encoding="utf-8")
    (folder / "run.json").write_text(json.dumps(card), encoding="utf-8")
    done = subprocess.run([sys.executable, "-B", str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"), "--program", str(program), "--work", str(folder / "out")], capture_output=True, text=True, check=False, timeout=20000)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        raise RuntimeError(json.dumps(summary)[:500])
    return folder / "out"


def beam(particle: str, energy_mev: float, start: list, direction: list) -> dict:
    return {"density": "analytic", "particle": particle, "energy": {"mono": {"energy_MeV": str(energy_mev)}}, "position": {"box_uniform": {"frame": "world", "centre_mm": [str(value) for value in start], "size_mm": ["1", "1", "0"]}}, "direction": {"fixed": {"frame": "world", "vector": direction}}}


def active_totals(work: Path, events: int) -> list:
    totals = [0.0] * events
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[1] == "active" and row[2] != "-1":
                totals[int(row[0])] += float(row[4])
    return totals


def calorimeter_point(root: Path, name: str, fields: dict, particle: str, energy_gev: float, events: int, program: Path, physics_list: str = LISTS[0]) -> dict:
    folder = root / name
    folder.mkdir(parents=True)
    depth = fields["layers"] * (fields["absorber_mm"] + fields["active_mm"] + fields["support_mm"])
    derive(folder, "calorimeter", {**COMMON, **fields})
    request = {"schema": "simulation-request/1", "source": beam(particle, energy_gev * 1000.0, [0, 0, -(depth / 2 + 60)], [0, 0, 1]), "scorers": [{"name": "active", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep"}]}
    totals = active_totals(simulate(folder, program, request, events, physics_list), events)
    mean, spread = statistics.fmean(totals), statistics.stdev(totals)
    return {"energy_GeV": energy_gev, "mean_MeV": mean, "mean_error": spread / math.sqrt(events), "relative_width": spread / mean, "width_error": spread / mean / math.sqrt(2 * events)}


def linear_fit(points: list) -> tuple:
    weights = [1 / point["mean_error"] ** 2 for point in points]
    x = [point["energy_GeV"] for point in points]
    y = [point["mean_MeV"] for point in points]
    total = sum(weights)
    centre_x, centre_y = sum(w * a for w, a in zip(weights, x)) / total, sum(w * b for w, b in zip(weights, y)) / total
    slope = sum(w * (a - centre_x) * (b - centre_y) for w, a, b in zip(weights, x, y)) / sum(w * (a - centre_x) ** 2 for w, a in zip(weights, x))
    return slope, centre_y - slope * centre_x


def largest_deviation(points: list) -> float:
    slope, offset = linear_fit(points)
    return max(abs(point["mean_MeV"] / (slope * point["energy_GeV"] + offset) - 1) for point in points)


def linearity(root: Path, program: Path, events: int) -> dict:
    def run(tag: str, fields: dict) -> list:
        return [calorimeter_point(root, f"{tag}-{energy}", fields, "e-", energy, events, program) for energy in LINEARITY_GEV]
    nominal = run("nominal", SCECAL)
    control = run("ten-layers", {**SCECAL, "layers": 10})
    deviation, control_deviation = largest_deviation(nominal), largest_deviation(control)
    return {"status": "ok" if deviation <= LINEARITY_LIMIT < control_deviation else "failed", "largest_deviation": deviation, "limit": LINEARITY_LIMIT, "control_deviation": control_deviation, "points": nominal, "control_points": control}


def stochastic_fit(points: list) -> tuple:
    """a and b of (sigma/E)^2 = a^2 / E + b^2, a linear fit in 1/E; a negative b^2 is taken as b = 0, as it can only mean no constant term is resolved."""
    x = [1 / point["energy_GeV"] for point in points]
    y = [point["relative_width"] ** 2 for point in points]
    weights = [1 / (2 * point["relative_width"] * point["width_error"]) ** 2 for point in points]
    total = sum(weights)
    centre_x, centre_y = sum(w * a for w, a in zip(weights, x)) / total, sum(w * b for w, b in zip(weights, y)) / total
    slope = sum(w * (a - centre_x) * (b - centre_y) for w, a, b in zip(weights, x, y)) / sum(w * (a - centre_x) ** 2 for w, a in zip(weights, x))
    constant = centre_y - slope * centre_x
    return math.sqrt(max(slope, 0.0)), math.sqrt(max(constant, 0.0))


def resolution(root: Path, program: Path, events: int) -> dict:
    results, passed = {}, True
    for physics_list in LISTS:
        points = [calorimeter_point(root, f"{physics_list}-{energy}", AHCAL, "e+", energy, events, program, physics_list) for energy in RESOLUTION_GEV]
        stochastic, constant = stochastic_fit(points)
        results[physics_list] = {"a": stochastic, "b": constant, "points": points}
        passed = passed and abs(stochastic - STOCHASTIC) <= STOCHASTIC_BAND
    doubled = [calorimeter_point(root, f"double-{energy}", {**AHCAL, "absorber_mm": 2 * AHCAL["absorber_mm"]}, "e+", energy, events, program) for energy in RESOLUTION_GEV]
    control = stochastic_fit(doubled)[0]
    caught = abs(control - STOCHASTIC) > STOCHASTIC_BAND
    return {"status": "ok" if passed and caught else "failed", "reference_a": STOCHASTIC, "band": STOCHASTIC_BAND, "lists": results, "control_a": control, "control_caught": caught}


def truncated_rms(values: list) -> float:
    ordered = sorted(values)
    cut = round(0.01 * len(ordered))
    kept = ordered[cut:len(ordered) - cut]
    centre = statistics.fmean(kept)
    return math.sqrt(statistics.fmean((value - centre) ** 2 for value in kept))


def scattering_row(root: Path, momentum_gev: int, wafers: int, events: int, program: Path) -> float:
    """RMS98 in 0.1 mrad after `wafers` wafers of 50 um: the direction at the entry of the next plane, across vacuum, of the primary."""
    folder = root / f"p{momentum_gev}-w{wafers}"
    folder.mkdir(parents=True)
    derive(folder, "planes-tracker", {"planes": wafers + 1, "plane_gap_mm": 50.0, "plane_thickness_mm": 0.05, "plane_side_mm": 2000.0, "field_tesla": 0.0, "plane_material": "G4_Si", "world_material": "G4_Galactic"})
    half = (wafers + 1) * 50.05 / 2
    request = {"schema": "simulation-request/1", "source": beam("e-", momentum_gev * 1000.0, [-(half + 20), 0, 0], [1, 0, 0]), "scorers": [{"name": "planes", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker"}]}
    work = simulate(folder, program, request, events)
    target = work / "tracker_hits.csv"
    subprocess.run([str(SIMROOT), "hits", str(work / "hits.root"), "--ntuple", "tracker_hits", "--out", str(target)], check=True, capture_output=True, text=True, timeout=300)
    with target.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["step_track_id"] == "1"]
    last = max(float(row["x_mm"]) for row in rows)
    first_in_last_plane: dict = {}
    for row in sorted(rows, key=lambda item: (int(item["event_id"]), int(item["step_index"]))):
        if float(row["x_mm"]) > last - 1.0:
            first_in_last_plane.setdefault(row["event_id"], row)
    angles = [math.atan2(float(row[axis]), float(row["px_MeV"])) * 1e4 for row in first_in_last_plane.values() for axis in ("py_MeV", "pz_MeV")]  # 0.1 mrad
    return truncated_rms(angles)


def scattering(root: Path, program: Path, events: int) -> dict:
    rows, passed = [], True
    for (momentum, thickness), (value, error) in BERGER.items():
        found = scattering_row(root, momentum, thickness // 50, events, program)
        sigma = math.hypot(error, BERGER_SYSTEMATIC * value)
        rows.append({"momentum_GeV": momentum, "thickness_um": thickness, "data": value, "simulated": found, "sigma": sigma, "pull": (found - value) / sigma})
        passed = passed and abs(found - value) <= 2 * sigma
    wrong = next(row for row in rows if row["momentum_GeV"] == 1 and row["thickness_um"] == 100)["simulated"]
    value, error = BERGER[(1, 50)]
    caught = abs(wrong - value) > 2 * math.hypot(error, BERGER_SYSTEMATIC * value)
    return {"status": "ok" if passed and caught else "failed", "rows": rows, "control_caught": caught}


def path_x0_percent(root: Path, name: str, start_y_mm: float, program: Path) -> float:
    """x/X0 of one 200 um plane: a geantino's path in it over Geant4's own radiation length, read back from the run."""
    folder = root / name
    folder.mkdir(parents=True)
    derive(folder, "planes-tracker", {"planes": 1, "plane_gap_mm": 10.0, "plane_thickness_mm": 0.2, "plane_side_mm": 100.0, "field_tesla": 0.0, "plane_material": "G4_Si", "world_material": "G4_Galactic"})
    request = {"schema": "simulation-request/1", "source": beam("geantino", 1000.0, [-60, start_y_mm, 0], [1, 0, 0]), "scorers": [{"name": "path", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "track_length"}]}
    work = simulate(folder, program, request, 10, threads=1)
    probe = json.loads((work / "probe-v2.json").read_text(encoding="utf-8"))
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        lengths = [float(row[4]) for row in csv.reader(handle) if row[1] == "path" and row[2] == "-1"]
    silicon = next(float.fromhex(item["radiation_length_mm"]) for item in probe["materials"] if item["name"] == "G4_Si")
    return 100.0 * (statistics.fmean(lengths) if lengths else 0.0) / silicon


def material(root: Path, program: Path, events: int) -> dict:
    del events
    value = path_x0_percent(root, "nominal", 0.0, program)
    missed = path_x0_percent(root, "plane-missed", 200.0, program)  # the card's control: no plane in the beam
    caught = abs(missed - MATERIAL_X0_PERCENT) > MATERIAL_BAND
    return {"status": "ok" if abs(value - MATERIAL_X0_PERCENT) <= MATERIAL_BAND and caught else "failed", "x_over_x0_percent": value, "reference": MATERIAL_X0_PERCENT, "band": MATERIAL_BAND, "control": missed, "control_caught": caught}


def main() -> int:
    global SIMROOT
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    running = commands.add_parser("run")
    running.add_argument("name", choices=("linearity", "resolution", "scattering", "material"))
    for name in ("program", "simroot", "work"):
        running.add_argument(f"--{name}", type=Path, required=True)
    running.add_argument("--events", type=int, default=2000)
    args = parser.parse_args()
    SIMROOT = args.simroot.resolve()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    result = {"linearity": linearity, "resolution": resolution, "scattering": scattering, "material": material}[args.name](root, args.program.resolve(), args.events)
    print(json.dumps({**result, "events": args.events}, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

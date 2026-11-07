#!/usr/bin/env python3
"""S4: g4sim hits through simroot and the real simreco, and an `external` text event file as their source (g4sim plan, Section 19.2 S4; a prerequisite of D0 condition 3).

Five silicon planes in a uniform field. The primaries come from a text event file, so one run exercises both. The reconstruction must recover the true rigidity and charge: a run that merely finishes proves nothing.
Usage: reco_from_hits.py --program PATH --simroot PATH --simreco PATH --simreco-strip PATH --work DIR [--events N]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.simulation import hits, response, rng  # noqa: E402

DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
PLANES_MM = (0, 100, 200, 300, 400)
THICKNESS_MM = 0.3
FIELD_TESLA = 1.0
MOMENTUM_MEV = 10000.0
PROTON_PDG, PROTON_MASS_GEV = 2212, 0.93827208816
SILICON_RADIATION_LENGTH_MM = 93.7
MINIMUM_FIT_FRACTION = 0.95
BIAS_SIGMAS = 4.0
PULL_WIDTH_RANGE = (0.7, 1.4)
WRONG_FIELD_SCALE = 1.25
MAD_TO_SIGMA = 1.4826
STRIPS = {"pitch-y-um": 50, "pitch-z-um": 100, "sharing-um": 10, "threshold": 0.2, "efficiency": 0.97}
STRIP_WIDTH_TOLERANCE = 0.05


def event_file(path: Path, events: int) -> str:
    lines = ["# g4sim-events/1"]
    for event in range(events):
        lines += [f"event {event} 1", f"{PROTON_PDG} -50 0 0 {MOMENTUM_MEV} 0 0"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ntuple(simroot: Path, work: Path, name: str) -> list:
    target = work / f"{name}.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", name, "--out", str(target)], check=True, capture_output=True, text=True, timeout=300)
    with target.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def reconstruct(root: Path, simreco: Path, label: str, field_tesla: float) -> dict:
    """Run simreco over the crossings with the field it is told, and summarise the fit against the truth."""
    geometry = {"planes": [{"id": at, "name": f"plane{at}", "role": "tracker-plane", "x_face_mm": x - THICKNESS_MM / 2, "thickness_mm": THICKNESS_MM, "centre_y_mm": 0, "centre_z_mm": 0, "half_y_mm": 200, "half_z_mm": 200,
                                "x_over_x0": THICKNESS_MM / SILICON_RADIATION_LENGTH_MM} for at, x in enumerate(PLANES_MM)],
                "field_regions": [{"lo_mm": -1000, "hi_mm": 1000, "bz_tesla": field_tesla}], "calorimeter_active_columns": []}
    table = root / f"reco-{label}.csv"
    effective = {"schema": "simreco.effective/1", "logical_run_seed": 4242, "replica": 0, "reco": {"point_resolution_um": {"bending": 10, "non_bending": 30}}, "geometry": geometry,
                 "particles": [{"pdg": PROTON_PDG, "mass_GeV": PROTON_MASS_GEV, "charge": 1}], "io": {"crossings": str(root / "crossings.csv"), "events": str(root / "events.csv"), "out_csv": str(table), "out_summary": str(root / f"reco-{label}-summary.json")}}
    card = root / f"reco-{label}.json"
    card.write_text(json.dumps(effective), encoding="utf-8")
    subprocess.run([str(simreco), str(card)], capture_output=True, text=True, check=True, timeout=600)
    with table.open(encoding="utf-8", newline="") as handle:
        next(handle)
        rows = list(csv.DictReader(handle))
    fitted = [row for row in rows if row["fit_ok"] == "1"]
    pulls = sorted(float(row["rho_pull"]) for row in fitted)
    centre = statistics.median(pulls)
    deviations = sorted(abs(pull - centre) for pull in pulls)
    return {"events": len(rows), "fitted": len(fitted), "charges_reconstructed": sorted({row["charge_reco"] for row in fitted}),
            "rigidity_true_GV": statistics.fmean(float(row["rig_true_GV"]) for row in fitted), "rigidity_reconstructed_median_GV": statistics.median(float(row["rig_reco_GV"]) for row in fitted),
            "pull_mean": statistics.fmean(pulls), "pull_median": centre, "pull_mean_error": statistics.stdev(pulls) / math.sqrt(len(pulls)), "pull_width": statistics.stdev(pulls),
            "pull_core_width": statistics.median(deviations) * MAD_TO_SIGMA, "pull_beyond_3": sum(abs(pull) > 3 for pull in pulls) / len(pulls)}


def strip_stage(root: Path, program: Path, crossings: list) -> dict:
    """Stage 5 through its hand-off file, on the real crossings: the clusters scatter by the resolution the stage reports, and the efficiency is the one asked for."""
    rows = [{"event": int(row["event_id"]), "cell": int(row["plane_id"]), "y_mm": float(row["y_mm"]), "z_mm": float(row["z_mm"])} for row in crossings]
    (root / "strip-in.json").write_text(json.dumps(response.handoff("sensor", "strips", rows)), encoding="utf-8")
    key = rng.channel_key(4242, "tracker", "strips", 0)
    arguments = {"handoff-in": root / "strip-in.json", "handoff-out": root / "strip-out.json", "stage": "strips", "next-stage": "reconstruction", "key0": key[0], "key1": key[1], **STRIPS}
    subprocess.run([str(program), *[word for name, value in arguments.items() for word in (f"--{name}", str(value))]], check=True, capture_output=True, text=True, timeout=300)
    kept = response.read_handoff(json.loads((root / "strip-out.json").read_text(encoding="utf-8")), "reconstruction")
    truth = {(row["event"], row["cell"]): row for row in rows}
    residuals = {axis: [row[axis] - truth[row["event"], row["cell"]][axis] for row in kept] for axis in ("y_mm", "z_mm")}
    ratios = {axis: math.sqrt(statistics.fmean(value * value for value in residuals[axis])) / kept[0][f"sigma_{axis}"] for axis in residuals}
    efficiency = len(kept) / len(rows)
    error = math.sqrt(STRIPS["efficiency"] * (1 - STRIPS["efficiency"]) / len(rows))
    closes = abs(efficiency - STRIPS["efficiency"]) <= BIAS_SIGMAS * error and all(abs(ratio - 1) <= STRIP_WIDTH_TOLERANCE for ratio in ratios.values())
    return {"rows_in": len(rows), "rows_out": len(kept), "efficiency": efficiency, "efficiency_error": error, "residual_over_sigma": ratios, "closes": closes}


def judged(summary: dict, events: int, planes_seen: int) -> bool:
    """Reconstruction closes: enough fits, every plane seen, the true charge, unbiased pulls of a width the errors explain."""
    return (summary["fitted"] >= MINIMUM_FIT_FRACTION * events and planes_seen == len(PLANES_MM) and summary["charges_reconstructed"] == ["1"]
            and abs(summary["pull_mean"]) <= BIAS_SIGMAS * summary["pull_mean_error"] and PULL_WIDTH_RANGE[0] <= summary["pull_width"] <= PULL_WIDTH_RANGE[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "simreco", "simreco_strip", "work"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--events", type=int, default=2000)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    digest = event_file(root / "events.txt", args.events)
    spec = {"schema": "detector-spec/1", "params": {}, "materials": {}, "fields": {"dipole": {"b_tesla": ["0", "0", str(FIELD_TESLA)]}},
            "templates": {"plane": {"solid": {"box": {"size_mm": [str(THICKNESS_MM), "400", "400"]}}, "material": "G4_Si", "tags": ["tracker"]}},
            "world": {"material": "G4_Galactic", "size_mm": ["2000", "2000", "2000"], "field": "dipole", "children": [{"template": "plane", "placement": {"explicit": {"positions_mm": [[str(x), "0", "0"] for x in PLANES_MM]}}}]}, "frames": {}}
    request = {"schema": "simulation-request/1", "source": {"density": "external", "format": "text", "path": "events.txt", "sha256": digest},
               "scorers": [{"name": "planes", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker"}], "truth": {"keep": ["primary"]}}
    card = {"schema": "g4sim-run/1", "physics": {"em_constructor": "G4EmStandardPhysics_option4", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": args.events, "first_event": 0, "logical_run_seed": 4242, "mode": "mt", "seeding": "per-event", "threads": 2}}
    for name, block in (("spec", spec), ("request", request), ("run", card)):
        (root / f"{name}.json").write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(root / "spec.json"), "--request", str(root / "request.json"), "--run", str(root / "run.json"), "--program", str(args.program.resolve()), "--work", str(root / "run")],
                          capture_output=True, text=True, check=False, timeout=1200)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        print(json.dumps({"status": "failed", "run": summary}))
        return 1
    work = root / "run"
    simroot = args.simroot.resolve()
    tracker, particles = read_ntuple(simroot, work, "tracker_hits"), read_ntuple(simroot, work, "mc_particles")
    cells = sorted({int(row["cell"]) for row in tracker})
    planes = {cell: at for at, cell in enumerate(cells)}
    crossings = hits.columns_for_simreco(tracker, particles, planes)
    with (root / "crossings.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=hits.CROSSING_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(crossings)
    (root / "events.csv").write_text("# SIMULATION\nevent,primary_pdg\n" + "".join(f"{event},{PROTON_PDG}\n" for event in range(args.events)), encoding="utf-8")
    nominal = reconstruct(root, args.simreco.resolve(), "nominal", FIELD_TESLA)
    wrong_scale = reconstruct(root, args.simreco.resolve(), "field-scaled", FIELD_TESLA * WRONG_FIELD_SCALE)
    reversed_field = reconstruct(root, args.simreco.resolve(), "field-reversed", -FIELD_TESLA)
    strips = strip_stage(root, args.simreco_strip.resolve(), crossings)
    nominal_passes = judged(nominal, args.events, len(cells))
    controls = {"field_scaled_fails": not judged(wrong_scale, args.events, len(cells)), "field_reversed_fails": not judged(reversed_field, args.events, len(cells))}
    passed = nominal_passes and all(controls.values()) and strips["closes"]
    print(json.dumps({"status": "ok" if passed else "failed", "planes_seen": len(cells), "crossings": len(crossings), "nominal": nominal, "field_scaled": wrong_scale, "field_reversed": reversed_field, "strip_stage": strips, "controls": controls}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""S4 gate 8: a hit file read back through simroot agrees with the scorers, and its truth is the truth (g4sim plan, Sections 9.2, 9.3, 19.2).

Two silicon planes and a block scored in 10 mm bins, two primaries per event, and event numbers above 2^31. Each event is run twice from one seed: with the rules under test, and with every track
kept, which gives the whole ancestry. Attribution is then judged against that ancestry, not against the file's own claims. Each control must break the check named for it, or the checks prove nothing.

Usage: hits_closure.py --program PATH --simroot PATH --work DIR [--events N]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from contracts import schema as contract_schema  # noqa: E402
from core.simulation import hits  # noqa: E402

DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
FIRST_EVENT = 2 ** 31 + 5
START_Z_MM = -300.0
PLANE_Z_MM = -150.0
REGION = "inner"
SENSOR_Z_MM = (-200.0, -180.0)
SENSOR_HALF_MM = 0.5
PIONS_MEV, PROTONS_MEV = 200.0, 500.0
PION_PDG, PROTON_PDG = 211, 2212
TOP_BIT = 2 ** 63
CONTROLS = {"ancestor_is_primary": "ancestry", "one_crossing_per_event": "crossings"}


def event_file(path: Path, events: int) -> str:
    rows = ["# g4sim-events/1"]
    for event in range(FIRST_EVENT, FIRST_EVENT + events):
        rows += [f"event {event} 2", f"{PION_PDG} 5 0 {START_Z_MM} 0 0 {PIONS_MEV}", f"{PROTON_PDG} -5 0 {START_Z_MM} 0 0 {PROTONS_MEV}"]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path, name: str, events: int, keep: list, program: Path, control: str = "") -> Path:
    folder = root / name
    folder.mkdir()
    digest = event_file(folder / "events.txt", events)
    spec = {"schema": "detector-spec/1", "params": {}, "materials": {"plastic": {"base": "G4_POLYSTYRENE", "ionisation": {"birks_mm_per_MeV": "0.126", "facts": "assumed"}, "facts": "assumed"}},
            "templates": {"sensor": {"solid": {"box": {"size_mm": ["100", "100", "1"]}}, "material": "G4_Si", "tags": ["tracker"], "region": REGION}, "block": {"solid": {"box": {"size_mm": ["100", "100", "200"]}}, "material": "plastic", "tags": ["active"]}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "sensor", "placement": {"explicit": {"positions_mm": [["0", "0", "-200"], ["0", "0", "-180"]]}}}, {"template": "block", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]}, "frames": {}}
    request = {"schema": "simulation-request/1", "source": {"density": "external", "format": "text", "path": "events.txt", "sha256": digest},
               "scorers": [{"name": "planes", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker"},
                           {"name": "cells", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep", "level": "event_file", "hit_kind": "calorimeter", "segmentation": {"along_axis": {"axis": "z", "width_mm": "10"}}, "split": "apportion"}],
               "reference_planes": [{"name": "front", "frame": "world", "z_mm": str(PLANE_Z_MM)}], "truth": {"keep": keep, "time_bin_ns": 1}}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": events, "first_event": FIRST_EVENT, "logical_run_seed": 4242, "mode": "mt", "seeding": "per-event", "threads": 2}}
    for label, block in (("spec", spec), ("request", request), ("run", card)):
        (folder / f"{label}.json").write_text(json.dumps(block), encoding="utf-8")
    environment = {**os.environ, "G4SIM_HIT_CONTROL": control} if control else None
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"), "--program", str(program), "--work", str(folder / "out")],
                          capture_output=True, text=True, check=False, timeout=1500, env=environment)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        raise RuntimeError(f"{name}: {json.dumps(summary)[:400]}")
    return folder / "out"


def ntuple(simroot: Path, work: Path, name: str) -> list:
    target = work / f"{name}.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", name, "--out", str(target)], check=True, capture_output=True, text=True, timeout=300)
    with target.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def scorer_sums(work: Path, name: str, offset: int = 0) -> dict:
    sums: dict = {}
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[1] == name and row[2] != "-1":
                sums[(int(row[0]), int(row[2]) + offset, int(row[3]))] = float(row[4])
    return sums


def nearest_kept(parents: dict, kept: set, event: int, track: int) -> int:
    """The nearest kept ancestor of a track, walking the whole ancestry; 0 above the primaries."""
    parent = parents[(event, track)]
    while parent and (event, parent) not in kept:
        parent = parents[(event, parent)]
    return parent


def judged(simroot: Path, work: Path, oracle: Path, events: int, offset: int = 0) -> dict:
    tables = {name: ntuple(simroot, work, name) for name in ("mc_particles", "tracker_hits", "calorimeter_hits", "contributions", "plane_crossings")}
    full = {name: ntuple(simroot, oracle, name) for name in ("mc_particles", "contributions")}
    particles = tables["mc_particles"]
    parents = {(int(row["event_id"]), int(row["track_id"])): int(row["parent_id"]) for row in full["mc_particles"]}
    kept = {(int(row["event_id"]), int(row["track_id"])) for row in particles}
    primaries = {key for key in kept if parents[key] == 0}

    def owner(event: int, track: int) -> int:
        return track if (event, track) in kept else nearest_kept(parents, kept, event, track)

    wrong_parent = [(row["event_id"], row["track_id"]) for row in particles
                    if int(row["parent_id"]) != nearest_kept(parents, kept, int(row["event_id"]), int(row["track_id"]))
                    or int(row["ancestor_pruned"]) != (int(row["parent_id"]) != parents[(int(row["event_id"]), int(row["track_id"]))])]
    expected: dict = {}
    for row in full["contributions"]:
        key = (*hits.cell_key(row), owner(int(row["event_id"]), int(row["track_id"])))
        expected.setdefault(key, []).append(float(row["edep_MeV"]))
    expected = {key: sum(values) for key, values in expected.items()}
    found: dict = {}
    for row in tables["contributions"]:
        key = (*hits.cell_key(row), int(row["track_id"]))
        found[key] = found.get(key, 0.0) + float(row["edep_MeV"])
    owners = hits.closure(found, expected, 1e-9) if not offset else {"ok": True}
    wrong_tracker = [row["step_index"] for row in tables["tracker_hits"] if int(row["track_id"]) != owner(int(row["event_id"]), int(row["step_track_id"]))]
    chained = sum(int(row["parent_id"]) != 0 and (int(row["event_id"]), int(row["parent_id"])) not in primaries for row in particles)
    non_primary_owners = len({key[3] for key in found if (key[0], key[3]) not in primaries})
    crossing_keys = [(int(row["event_id"]), int(row["track_id"]), int(row["plane"])) for row in tables["plane_crossings"]]
    crossed_primaries = {(event, track) for event, track, _ in crossing_keys} & primaries
    past_the_plane = {(int(row["event_id"]), int(row["track_id"])) for row in particles if (int(row["event_id"]), int(row["track_id"])) in primaries and float(row["end_z_mm"]) > PLANE_Z_MM}  # one way only: a pion can decay before the plane, or cross it and scatter back
    statuses = {int(row["simulation_status"]) for row in particles}
    calorimeter = hits.closure(hits.sums_by_cell(tables["calorimeter_hits"]), scorer_sums(work, "cells", offset))
    tracker = hits.closure(hits.sums_by_cell(tables["tracker_hits"]), scorer_sums(work, "planes", offset))
    against_parts = hits.closure(hits.sums_by_cell(tables["calorimeter_hits"]), hits.sums_by_cell(tables["contributions"]))
    index = json.loads((work / "simulation-hits.json").read_text(encoding="utf-8"))
    checks = {"calorimeter": calorimeter["ok"], "tracker": tracker["ok"], "contributions": against_parts["ok"], "ancestry": not wrong_parent and owners["ok"] and not wrong_tracker and chained > 0 and non_primary_owners > 0,
              "crossings": len(crossing_keys) == len(set(crossing_keys)) and past_the_plane <= crossed_primaries and len(past_the_plane) > 1.9 * events and {key[:2] for key in crossing_keys} <= kept, "status": 0 not in statuses and statuses == {1, 2},
              "event_numbers": min(key[0] for key in kept) == FIRST_EVENT, "segments": len({key[2] for key in hits.sums_by_cell(tables["calorimeter_hits"])}) > 5, "planes": len({key[1] for key in hits.sums_by_cell(tables["tracker_hits"])}) == 2,
              "index": contract_schema.validate(index, "simulation_hits.json").ok and len(index["request_id"]) > 0}
    return {"checks": checks, "counts": {"particles": len(particles), "kept_with_a_kept_non_primary_parent": chained, "non_primary_owners": non_primary_owners, "wrong_parents": len(wrong_parent), "wrong_tracker_owners": len(wrong_tracker), "crossings": len(crossing_keys), "cells": calorimeter["cells"], "worst_relative": calorimeter["worst_relative"]}}


def region_rule(simroot: Path, work: Path) -> dict:
    """Secondaries kept by an energy rule are born in the rule's region, and only there; the block makes far more, so a rule that ignored the region would show."""
    crossed = {(row["event_id"], row["track_id"]) for row in ntuple(simroot, work, "plane_crossings")}  # kept by the plane's rule, wherever they were born
    born = [float(row["z_mm"]) for row in ntuple(simroot, work, "mc_particles") if int(row["parent_id"]) != 0 and (row["event_id"], row["track_id"]) not in crossed]
    inside = sum(any(abs(z - centre) <= SENSOR_HALF_MM for centre in SENSOR_Z_MM) for z in born)
    return {"kept_secondaries": len(born), "born_in_the_region": inside, "ok": 0 < inside == len(born)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--events", type=int, default=300)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    program, simroot = args.program.resolve(), args.simroot.resolve()
    keep = ["primary", "decay_products"]
    oracle = run(root, "oracle", args.events, ["all"], program)
    nominal = judged(simroot, run(root, "nominal", args.events, keep, program), oracle, args.events)
    controls = {}
    for control, check in CONTROLS.items():
        controls[control] = not judged(simroot, run(root, control, args.events, keep, program, control), oracle, args.events)["checks"][check]
    high = judged(simroot, run(root, "high_cells", args.events, keep, program, "high_cells"), oracle, args.events, offset=TOP_BIT)["checks"]
    controls["cells_above_2_63_exact"] = high["calorimeter"] and high["tracker"]
    region = region_rule(simroot, run(root, "region_rule", args.events, ["primary", {"energy_above_MeV": 0.01, "region": REGION}], program))
    nominal["region_rule"] = region
    passed = all(nominal["checks"].values()) and all(controls.values()) and region["ok"]
    print(json.dumps({"status": "ok" if passed else "failed", **nominal, "controls": controls}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

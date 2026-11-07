#!/usr/bin/env python3
"""S4 gate 8: a hit file read back through simroot agrees with the scorers, and every column it holds is right (g4sim plan, Sections 9.1 to 9.3, 19.2).

Two silicon planes in 0.1 mm strips and a block in 10 mm bins; a proton tilted up and a pion tilted down in every event; event numbers above 2^31; a reference plane in vacuum, where a crossing is exact, and one past
the sensors. Each event runs twice from one seed: with the rules under test, and with every track kept, which gives the whole ancestry.

COLUMNS names, for each column written, the check that compares it with something independent of the file: the ancestry run, the geometry, or kinematics. Closure against the scorers does not count, because hits and
scorers share a code path. The gate fails if a column has no entry. CONTROLS are single faults, each of which must break the check named for it, or the checks prove nothing.

Usage: hits_closure.py --program PATH --simroot PATH --work DIR [--events N]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics
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
VACUUM_PLANE_Z_MM, PLANE_Z_MM = -250.0, -150.0
REGION = "inner"
SENSOR_Z_MM = (-200.0, -180.0)
SENSOR_HALF_MM = 0.5
STRIP_MM, BIN_MM = 0.1, 10.0
SIDE_MM, BLOCK_HALF_MM, WORLD_HALF_MM = 100.0, 100.0, 500.0
LIGHT_MM_PER_NS = 299.792458
PROTON_PDG, PION_PDG = 2212, 211
MASSES_MEV = {11: 0.51099895, 22: 0.0, 13: 105.6583755, 211: 139.57039, 2212: 938.27208816, 2112: 939.56542052}
PRIMARIES = {PROTON_PDG: {"x": -5.0, "y": -40.0, "tilt": 0.2, "pz": 500.0}, PION_PDG: {"x": 5.0, "y": 40.0, "tilt": -0.2, "pz": 200.0}}
ENERGY_RULE_MEV = 10.0
EDGE_MM = 1e-6
MASS_TABLE = 1e-5  # relative: Geant4's masses are not these values
TOP_BIT = 2 ** 63
KEEP = ["primary", "decay_products", {"energy_above_MeV": 1000, "region": REGION}, {"energy_above_MeV": ENERGY_RULE_MEV}]
NTUPLES = ("mc_particles", "tracker_hits", "calorimeter_hits", "contributions", "plane_crossings")
COLUMNS = {
    "mc_particles": {"event_id": "event_numbers", "track_id": "ancestry", "parent_id": "ancestry", "pdg": "particles", "ancestor_pruned": "ancestry", "simulation_status": "status", "born_of_decay": "energy_rule", "x_mm": "vertices", "y_mm": "vertices", "z_mm": "vertices",
                     "px_MeV": "momentum", "py_MeV": "momentum", "pz_MeV": "momentum", "ekin_MeV": "momentum", "end_x_mm": "vertices", "end_y_mm": "vertices", "end_z_mm": "vertices"},
    "tracker_hits": {"event_id": "event_numbers", "step_index": "path_order", "track_id": "ancestry", "step_track_id": "ancestry", "step_number": "apportion", "cell": "tracker_cells", "segment": "pieces", "scorer": "no_readout", "cell_id": "no_readout", "x_mm": "tracker_points", "y_mm": "pieces", "z_mm": "tracker_points",
                     "px_MeV": "tracker_kinematics", "py_MeV": "tracker_kinematics", "pz_MeV": "tracker_kinematics", "ekin_MeV": "tracker_kinematics", "edep_MeV": "apportion", "time_ns": "times", "path_mm": "apportion"},
    "calorimeter_hits": {"event_id": "event_numbers", "cell": "contributions", "segment": "pieces", "scorer": "no_readout", "cell_id": "no_readout", "edep_MeV": "contributions", "x_mm": "block_points", "y_mm": "block_points", "z_mm": "pieces"},
    "contributions": {"event_id": "event_numbers", "cell": "contributions", "segment": "pieces", "track_id": "ancestry", "time_bin": "times", "edep_MeV": "ancestry", "time_ns": "contribution_times", "x_mm": "block_points", "y_mm": "block_points", "z_mm": "pieces"},
    "plane_crossings": {"event_id": "event_numbers", "plane": "crossing_values", "track_id": "crossings", "x_mm": "crossing_values", "y_mm": "crossing_values", "z_mm": "crossing_values", "dx": "crossing_values", "dy": "crossing_values", "dz": "crossing_values", "energy_MeV": "crossing_values", "time_ns": "crossing_values"}}
CONTROLS = {"ancestor_is_primary": "ancestry", "one_crossing_per_event": "crossings", "pieces_repeat_the_step": "pieces", "crossing_at_pre_step": "crossing_values", "crossing_offset": "crossing_values", "crossing_energy_zero": "crossing_values", "crossing_time_zero": "crossing_values",
            "status_swapped": "status", "threshold_ignored": "energy_rule", "decay_rule_off": "energy_rule", "momentum_zero": "momentum", "secondary_energy_doubled": "momentum", "tracker_kinematics_zero": "tracker_kinematics", "kinematics_across_the_kink": "tracker_kinematics",
            "time_zero": "times", "time_not_interpolated": "times", "contribution_time_not_interpolated": "contribution_times", "equal_split": "apportion"}


def event_file(path: Path, events: int) -> str:
    rows = ["# g4sim-events/1"]
    for event in range(FIRST_EVENT, FIRST_EVENT + events):
        rows.append(f"event {event} {len(PRIMARIES)}")
        rows += [f"{pdg} {item['x']} {item['y']} {START_Z_MM} 0 {item['tilt'] * item['pz']} {item['pz']}" for pdg, item in PRIMARIES.items()]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path, name: str, events: int, keep: list, program: Path, control: str = "", threads: int = 2) -> Path:
    folder = root / name
    folder.mkdir()
    digest = event_file(folder / "events.txt", events)
    spec = {"schema": "detector-spec/1", "params": {}, "materials": {"plastic": {"base": "G4_POLYSTYRENE", "ionisation": {"birks_mm_per_MeV": "0.126", "facts": "assumed"}, "facts": "assumed"}},
            "templates": {"sensor": {"solid": {"box": {"size_mm": [str(SIDE_MM), str(SIDE_MM), str(2 * SENSOR_HALF_MM)]}}, "material": "G4_Si", "tags": ["tracker"], "region": REGION}, "block": {"solid": {"box": {"size_mm": [str(SIDE_MM), str(SIDE_MM), str(2 * BLOCK_HALF_MM)]}}, "material": "plastic", "tags": ["active"]}},
            "world": {"material": "G4_Galactic", "size_mm": [str(2 * WORLD_HALF_MM)] * 3, "children": [{"template": "sensor", "placement": {"explicit": {"positions_mm": [["0", "0", str(z)] for z in SENSOR_Z_MM]}}}, {"template": "block", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]}, "frames": {}}
    request = {"schema": "simulation-request/1", "source": {"density": "external", "format": "text", "path": "events.txt", "sha256": digest},
               "scorers": [{"name": "planes", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker", "segmentation": {"along_axis": {"axis": "y", "width_mm": str(STRIP_MM)}}, "split": "apportion"},
                           {"name": "cells", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep", "level": "event_file", "hit_kind": "calorimeter", "segmentation": {"along_axis": {"axis": "z", "width_mm": str(BIN_MM)}}, "split": "apportion"},
                           {"name": "by_event", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep"}, {"name": "summed", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep", "level": "moments"}],
               "reference_planes": [{"name": "vacuum", "frame": "world", "z_mm": str(VACUUM_PLANE_Z_MM)}, {"name": "front", "frame": "world", "z_mm": str(PLANE_Z_MM)}], "truth": {"keep": keep, "time_bin_ns": 1}}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": events, "first_event": FIRST_EVENT, "logical_run_seed": 4242, "mode": "mt", "seeding": "per-event", "threads": threads}}
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


def middle(values) -> float:
    """A median that a fault can empty: nothing to judge is a failed check, not a crash."""
    found = list(values)
    return statistics.median(found) if found else math.inf


def key_of(row: dict, track: str = "track_id") -> tuple:
    return int(row["event_id"]), int(row[track])


def nearest_kept(parents: dict, kept: set, event: int, track: int) -> int:
    """The nearest kept ancestor of a track, walking the whole ancestry; 0 above the primaries."""
    parent = parents[(event, track)]
    while parent and (event, parent) not in kept:
        parent = parents[(event, parent)]
    return parent


def inside(position: float, start: float, width: float, index: int) -> bool:
    return start + index * width - EDGE_MM <= position <= start + (index + 1) * width + EDGE_MM


def moments_agree(work: Path, events: int) -> bool:
    """A cell's sum and sum of squares at level `moments` are the same doubles as those of the per-event rows of level `column`, and the events run are recorded apart from those with a deposit."""
    values: dict = {}
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[1] == "by_event" and row[2] != "-1":
                values.setdefault((int(row[2]), int(row[3])), []).append(float(row[4]))
    with (work / "moments.csv").open(encoding="utf-8", newline="") as handle:
        rows = {(int(row[1]), int(row[2])): row for row in csv.reader(handle) if row[0] == "summed" and row[2] != "-1"}
    return len(rows) > 0 and set(rows) == set(values) and all(int(rows[key][3]) == events and int(rows[key][4]) == len(found) and float(rows[key][5]) == math.fsum(found) and float(rows[key][6]) == math.fsum(value * value for value in found) for key, found in values.items())


def speed_mm_per_ns(momentum: float, mass: float) -> float:
    return LIGHT_MM_PER_NS * momentum / math.hypot(momentum, mass)


def flight_ns(item: dict, mass: float, z: float) -> float:
    """From the start to a plane at z, in a straight line through vacuum."""
    return (z - START_Z_MM) * math.hypot(1.0, item["tilt"]) / speed_mm_per_ns(item["pz"] * math.hypot(1.0, item["tilt"]), mass)


def crossing_values(rows: list, primaries: dict, particles: dict) -> bool:
    """In vacuum a primary's crossing is fixed: position, direction, time and its energy at birth. Past the sensors it is on the plane, near the line. Every row is on its plane."""
    planes = (VACUUM_PLANE_Z_MM, PLANE_Z_MM)
    if not all(abs(float(row["z_mm"]) - planes[int(row["plane"])]) < 1e-9 for row in rows):
        return False
    upstream, far = 0, []
    for row in rows:
        key = key_of(row)
        if key not in primaries:
            continue
        pdg = primaries[key]
        item = PRIMARIES[pdg]
        z = planes[int(row["plane"])]
        line = item["y"] + item["tilt"] * (z - START_Z_MM)
        if int(row["plane"]) == 1:
            far.append(abs(float(row["y_mm"]) - line))
            continue
        upstream += 1
        size = math.hypot(1.0, item["tilt"])
        exact = (abs(float(row["x_mm"]) - item["x"]) < 1e-9 and abs(float(row["y_mm"]) - line) < 1e-9 and abs(float(row["dy"]) - item["tilt"] / size) < 1e-9 and abs(float(row["dz"]) - 1 / size) < 1e-9 and abs(float(row["dx"])) < 1e-9
                 and abs(float(row["energy_MeV"]) - float(particles[key]["ekin_MeV"])) < 1e-9 and abs(float(row["time_ns"]) / flight_ns(item, MASSES_MEV[pdg], z) - 1) < MASS_TABLE)
        if not exact:
            return False
    return upstream > 0 and middle(far) < 1.0


def apportion(rows: list, primaries: dict) -> dict:
    """A split step, against geometry computed here: an interior piece crosses a whole strip, so its path is the strip over the slope of the step's chord, and a deposit is shared as the path is."""
    groups: dict = {}
    for row in rows:
        if key_of(row, "step_track_id") in primaries:
            groups.setdefault((row["event_id"], row["step_track_id"], row["cell"], row["step_number"]), []).append(row)
    worst_path = worst_rate = 0.0
    interior = 0
    for pieces in groups.values():
        pieces.sort(key=lambda row: int(row["step_index"]))
        rates = [float(row["edep_MeV"]) / float(row["path_mm"]) for row in pieces if float(row["path_mm"]) > 0]
        if len(pieces) >= 2 and max(rates) > 0:
            worst_rate = max(worst_rate, (max(rates) - min(rates)) / max(rates))
        if len(pieces) < 3:
            continue
        ends = [[float(row[f"{axis}_mm"]) for axis in "xyz"] for row in (pieces[0], pieces[-1])]
        span = math.dist(*ends)
        slope = abs(ends[1][1] - ends[0][1]) / span if span else 0.0  # apportioning cuts the step's chord, so the chord's slope is the reference
        for row in pieces[1:-1]:
            worst_path = max(worst_path, abs(float(row["path_mm"]) * slope / STRIP_MM - 1))
            interior += 1
    return {"interior_pieces": interior, "worst_path": worst_path, "worst_rate": worst_rate, "ok": interior > 20 and worst_path < 0.02 and worst_rate < 1e-9}


def judged(simroot: Path, work: Path, oracle: Path, events: int, offset: int = 0) -> dict:
    tables = {name: ntuple(simroot, work, name) for name in NTUPLES}
    full = {name: ntuple(simroot, oracle, name) for name in ("mc_particles", "contributions")}
    written = {name: set(rows[0]) for name, rows in tables.items()}
    particles = tables["mc_particles"]
    rows_by_key = {key_of(row): row for row in particles}
    every = {key_of(row): row for row in full["mc_particles"]}
    parents = {key: int(row["parent_id"]) for key, row in every.items()}
    kept = set(rows_by_key)
    primaries = {key: int(every[key]["pdg"]) for key in kept if parents[key] == 0}
    tracker, calorimeter_rows, parts, plane_rows = tables["tracker_hits"], tables["calorimeter_hits"], tables["contributions"], tables["plane_crossings"]

    def owner(event: int, track: int) -> int:
        return track if (event, track) in kept else nearest_kept(parents, kept, event, track)

    wrong_parent = [key_of(row) for row in particles if int(row["parent_id"]) != nearest_kept(parents, kept, *key_of(row)) or int(row["ancestor_pruned"]) != (int(row["parent_id"]) != parents[key_of(row)])]
    expected: dict = {}
    for row in full["contributions"]:
        key = (*hits.cell_key(row), owner(*key_of(row)))
        expected[key] = expected.get(key, 0.0) + float(row["edep_MeV"])
    found: dict = {}
    for row in parts:
        key = (*hits.cell_key(row), int(row["track_id"]))
        found[key] = found.get(key, 0.0) + float(row["edep_MeV"])
    owners = hits.closure(found, expected, 1e-9) if not offset else {"ok": True}
    wrong_tracker = [row["step_index"] for row in tracker if int(row["track_id"]) != owner(int(row["event_id"]), int(row["step_track_id"]))]
    chained = sum(int(row["parent_id"]) != 0 and (int(row["event_id"]), int(row["parent_id"])) not in primaries for row in particles)
    non_primary_owners = len({key[3] for key in found if (key[0], key[3]) not in primaries})
    crossing_keys = [(*key_of(row), int(row["plane"])) for row in plane_rows]
    crossed = {key[:2] for key in crossing_keys}
    past_the_plane = {key for key in primaries if float(rows_by_key[key]["end_z_mm"]) > PLANE_Z_MM}  # one way only: a pion can decay before the plane, or cross it and scatter back

    def energy_of(row: dict) -> bool:
        pdg = abs(int(row["pdg"]))
        if pdg not in MASSES_MEV:
            return True
        momentum = math.sqrt(math.fsum(float(row[f"p{axis}_MeV"]) ** 2 for axis in "xyz"))
        kinetic = float(row["ekin_MeV"])
        return abs(math.sqrt(kinetic * (kinetic + 2 * MASSES_MEV[pdg])) - momentum) <= MASS_TABLE * max(momentum, 1.0)

    births_right = all(abs(float(rows_by_key[key][f"p{axis}_MeV"]) - value) < 1e-9 for key, pdg in primaries.items() for axis, value in (("x", 0.0), ("y", PRIMARIES[pdg]["tilt"] * PRIMARIES[pdg]["pz"]), ("z", PRIMARIES[pdg]["pz"])))
    starts_right = all(abs(float(rows_by_key[key][f"{axis}_mm"]) - value) < 1e-9 for key, pdg in primaries.items() for axis, value in (("x", PRIMARIES[pdg]["x"]), ("y", PRIMARIES[pdg]["y"]), ("z", START_Z_MM)))
    decays = {key for key, row in every.items() if int(row["born_of_decay"])}
    from_the_parent = all(max(abs(float(row[f"{axis}_mm"]) - float(every[(key[0], parents[key])][f"end_{axis}_mm"])) for axis in "xyz") < 1e-6 for key, row in every.items() if key in decays)
    above = {key for key, row in every.items() if float(row["ekin_MeV"]) > ENERGY_RULE_MEV}

    sensors = {}
    for row in tracker:
        sensors.setdefault(min(range(2), key=lambda at: abs(float(row["z_mm"]) - SENSOR_Z_MM[at])), set()).add(int(row["cell"]))
    primary_hits = [row for row in tracker if key_of(row, "step_track_id") in primaries]
    ordered: dict = {}
    for row in sorted(tracker, key=lambda item: (int(item["event_id"]), int(item["step_index"]))):
        ordered.setdefault(key_of(row, "step_track_id"), []).append(float(row["time_ns"]))
    path_order = all(left <= right for key, times in ordered.items() if key in primaries for left, right in zip(times, times[1:]))
    index_keys = [(row["event_id"], row["step_index"]) for row in tracker]
    speeds = []
    groups: dict = {}
    for row in primary_hits:
        groups.setdefault((row["event_id"], row["step_track_id"], row["cell"], row["step_number"]), []).append(row)
    for pieces in groups.values():
        pieces.sort(key=lambda row: int(row["step_index"]))
        for left, right in zip(pieces, pieces[1:]):
            distance = math.dist([float(left[f"{axis}_mm"]) for axis in "xyz"], [float(right[f"{axis}_mm"]) for axis in "xyz"])
            lapse = float(right["time_ns"]) - float(left["time_ns"])
            momentum = math.sqrt(math.fsum(float(left[f"p{axis}_MeV"]) ** 2 for axis in "xyz"))
            if distance > 0 and momentum > 0:
                speeds.append(lapse * speed_mm_per_ns(momentum, MASSES_MEV[primaries[key_of(left, "step_track_id")]]) / distance)
    first_hits = {}
    for row in sorted(primary_hits, key=lambda item: int(item["step_index"])):
        first_hits.setdefault((*key_of(row, "step_track_id"), row["cell"]), row)
    flight_error = middle(abs(float(row["time_ns"]) / flight_ns(PRIMARIES[primaries[key[:2]]], MASSES_MEV[primaries[key[:2]]], float(row["z_mm"])) - 1) for key, row in first_hits.items())
    steady = all(float(row["ekin_MeV"]) > 0 for row in primary_hits) and all(energy_of({**row, "pdg": primaries[key_of(row, "step_track_id")]}) for row in primary_hits)
    slopes = middle(abs(float(row["py_MeV"]) / float(row["pz_MeV"]) - PRIMARIES[primaries[key_of(row, "step_track_id")]]["tilt"]) for row in primary_hits if float(row["pz_MeV"]) != 0)
    no_kinks = True
    for pieces in groups.values():
        energies = [float(row["ekin_MeV"]) for row in pieces]
        no_kinks = no_kinks and max(energies) - min(energies) <= math.fsum(float(row["edep_MeV"]) for row in pieces) * (1 + 1e-9) + 1e-9
    protons = {key for key, pdg in primaries.items() if pdg == PROTON_PDG}
    front = []
    for row in parts:
        key = key_of(row)
        if key in protons and int(row["segment"]) == 0:
            item = PRIMARIES[PROTON_PDG]
            front.append(abs(float(row["time_ns"]) - flight_ns(item, MASSES_MEV[PROTON_PDG], float(row["z_mm"]))))
    front_error = middle(front)
    time_bins_right = all(int(row["time_bin"]) == math.floor(float(row["time_ns"])) for row in parts)

    calorimeter = hits.closure(hits.sums_by_cell(calorimeter_rows), scorer_sums(work, "cells", offset))
    tracker_closure = hits.closure(hits.sums_by_cell(tracker), scorer_sums(work, "planes", offset))
    against_parts = hits.closure(hits.sums_by_cell(calorimeter_rows), hits.sums_by_cell(parts))
    shares = apportion(tracker, primaries)
    index = json.loads((work / "simulation-hits.json").read_text(encoding="utf-8"))
    left_the_world = {key for key, row in rows_by_key.items() if max(abs(float(row[f"end_{axis}_mm"])) for axis in "xyz") >= WORLD_HALF_MM - EDGE_MM}
    statuses = {int(row["simulation_status"]) for row in particles}
    paths: dict = {}
    for row in primary_hits:
        key = (*key_of(row, "step_track_id"), row["cell"])
        paths[key] = paths.get(key, 0.0) + float(row["path_mm"])
    path_ratio = middle(value / (2 * SENSOR_HALF_MM * math.hypot(1.0, PRIMARIES[primaries[key[:2]]]["tilt"])) for key, value in paths.items())
    checks = {"no_readout": all(row["cell_id"] == "0" for row in [*calorimeter_rows, *tracker]) and {row["scorer"] for row in tracker} == {"0"} and {row["scorer"] for row in calorimeter_rows} == {"1"}, "calorimeter": calorimeter["ok"], "tracker": tracker_closure["ok"], "contributions": against_parts["ok"] and {row["cell"] for row in calorimeter_rows} == {row["cell"] for row in parts} and len({row["cell"] for row in calorimeter_rows}) == 1,
              "ancestry": not wrong_parent and owners["ok"] and not wrong_tracker and chained > 0 and non_primary_owners > 0 and {key: row["pdg"] for key, row in rows_by_key.items()} == {key: every[key]["pdg"] for key in kept},
              "particles": sorted(set(primaries.values())) == sorted(PRIMARIES) and len(primaries) == len(PRIMARIES) * events,
              "crossings": len(crossing_keys) == len(set(crossing_keys)) and past_the_plane <= crossed and len(past_the_plane) > 1.9 * events and crossed <= kept,
              "crossing_values": crossing_values(plane_rows, primaries, rows_by_key), "status": statuses == {1, 2} and all((int(row["simulation_status"]) == 2) == (key in left_the_world) for key, row in rows_by_key.items()),
              "energy_rule": kept == set(primaries) | crossed | above | decays and len(above - set(primaries)) > 0 and len(decays - above - crossed) > 0,
              "momentum": births_right and all(energy_of(row) for row in particles), "vertices": starts_right and from_the_parent and len(decays) > 0,
              "pieces": all(inside(float(row["y_mm"]), -SIDE_MM / 2, STRIP_MM, int(row["segment"])) for row in tracker) and all(inside(float(row["z_mm"]), -BLOCK_HALF_MM, BIN_MM, int(row["segment"])) for name in ("calorimeter_hits", "contributions") for row in tables[name]) and abs(path_ratio - 1) < 0.02,
              "apportion": shares["ok"], "path_order": path_order and len(index_keys) == len(set(index_keys)), "tracker_cells": len(sensors) == 2 and all(len(cells) == 1 for cells in sensors.values()) and sensors[0] != sensors[1],
              "tracker_points": all(abs(float(row["x_mm"])) <= SIDE_MM / 2 and min(abs(float(row["z_mm"]) - z) for z in SENSOR_Z_MM) <= SENSOR_HALF_MM + EDGE_MM for row in tracker),
              "tracker_kinematics": steady and slopes < 0.02 and no_kinks, "times": flight_error < 0.02 and abs(middle(speeds) - 1) < 0.02 and time_bins_right, "contribution_times": front_error < 0.01 and min(float(row["time_ns"]) for row in parts) > 0,
              "block_points": all(max(abs(float(row["x_mm"])), abs(float(row["y_mm"]))) <= SIDE_MM / 2 + EDGE_MM for name in ("calorimeter_hits", "contributions") for row in tables[name]),
              "event_numbers": all(FIRST_EVENT <= int(row["event_id"]) < FIRST_EVENT + events for rows in tables.values() for row in rows), "segments": len({key[2] for key in hits.sums_by_cell(calorimeter_rows)}) > 5, "moments": moments_agree(work, events),
              "index": contract_schema.validate(index, "simulation_hits.json").ok and len(index["request_id"]) == 64}
    unlisted = sorted(f"{name}.{column}" for name, columns in written.items() for column in columns if column not in COLUMNS[name]) + sorted(f"{name}.{column}" for name, columns in COLUMNS.items() for column in columns if column not in written[name])
    checks["every_column_listed"] = not unlisted and all(check in checks for columns in COLUMNS.values() for check in columns.values())
    return {"checks": checks, "unlisted": unlisted, "counts": {"particles": len(particles), "kept_with_a_kept_non_primary_parent": chained, "non_primary_owners": non_primary_owners, "wrong_parents": len(wrong_parent), "wrong_tracker_owners": len(wrong_tracker), "crossings": len(crossing_keys), "cells": calorimeter["cells"],
                                                     "worst_relative": calorimeter["worst_relative"], "path_ratio": path_ratio, "apportion": shares, "decay_products": len(decays), "flight_error": flight_error, "front_time_error_ns": front_error, "speed_ratio": middle(speeds), "slope_error": slopes, "kept_by_energy": len(above - set(primaries))}}


def region_rule(simroot: Path, work: Path) -> dict:
    """Secondaries kept by an energy rule are born in the rule's region, and only there; the block makes far more, so a rule that ignored the region would show."""
    crossed = {(row["event_id"], row["track_id"]) for row in ntuple(simroot, work, "plane_crossings")}  # kept by the plane's rule, wherever they were born
    born = [float(row["z_mm"]) for row in ntuple(simroot, work, "mc_particles") if int(row["parent_id"]) != 0 and (row["event_id"], row["track_id"]) not in crossed]
    found = sum(any(abs(z - centre) <= SENSOR_HALF_MM for centre in SENSOR_Z_MM) for z in born)
    return {"kept_secondaries": len(born), "born_in_the_region": found, "ok": 0 < found == len(born)}


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
    oracle = run(root, "oracle", args.events, ["all"], program)
    work = run(root, "nominal", args.events, KEEP, program)
    nominal = judged(simroot, work, oracle, args.events)
    controls = {}
    for control, check in CONTROLS.items():
        faulty = judged(simroot, run(root, control, args.events, KEEP, program, control), oracle, args.events)["checks"]
        controls[control] = {"seen": not faulty[check], "other_checks_failing": sorted(name for name, value in faulty.items() if not value and name != check)}
    high = judged(simroot, run(root, "high_cells", args.events, KEEP, program, "high_cells"), oracle, args.events, offset=TOP_BIT)["checks"]
    cells_exact = high["calorimeter"] and high["tracker"]
    single = run(root, "one_thread", args.events, KEEP, program, threads=1)
    for name in NTUPLES:
        ntuple(simroot, single, name)
    nominal["checks"]["threads"] = all((work / f"{name}.csv").read_bytes() == (single / f"{name}.csv").read_bytes() for name in (*NTUPLES, "moments"))
    region = region_rule(simroot, run(root, "region_rule", args.events, ["primary", {"energy_above_MeV": 0.01, "region": REGION}], program))
    passed = all(nominal["checks"].values()) and all(item["seen"] for item in controls.values()) and region["ok"] and cells_exact
    print(json.dumps({"status": "ok" if passed else "failed", **nominal, "controls": controls, "cells_above_2_63_exact": cells_exact, "region_rule": region, "column_checks": COLUMNS}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

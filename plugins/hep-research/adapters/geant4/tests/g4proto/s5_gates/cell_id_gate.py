#!/usr/bin/env python3
"""Encoded cellID in hit files (g4sim plan, Sections 6.2.6, 9.2; registered in g4sim-tasks/S5.md): every hit's decoded fields against the indices found from its position.

Two modules along z, each a grid of crystals, with every segmentation kind. The readout's fields sort apart from a grid's packing and a bin's axes, so a cellID built by multiplying copy numbers would decode wrongly. Also two readouts in one file, a fault in the producer, a value one past its field, and a file of the earlier layout.

Usage: cell_id_gate.py --program PATH --simroot PATH --work DIR --old-hits FILE   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kit_benchmarks as kits  # noqa: E402

from core.simulation import hits  # noqa: E402

COLUMNS, ROWS, MODULES = 3, 2, 2
PITCH_MM, CRYSTAL_MM, DEPTH_MM, MODULE_PITCH_MM = 25.0, 20.0, 40.0, 150.0
PAD_START_MM, PAD_PITCH_MM = -260.0, 20.0
EVENTS = 300
COPIES = {"col": 2, "m": 1, "row": 1}
# A name that sorts against its axis, so that a bitfield's order differs from a bin's: x is zx and y is ay.
CASES = {"along_z": ({"along_axis": {"axis": "z", "width_mm": "10"}}, {"mz": 2}), "along_x": ({"along_axis": {"axis": "x", "width_mm": "5"}}, {"zx": 2}), "along_y": ({"along_axis": {"axis": "y", "width_mm": "5"}}, {"ay": 2}),
         "cartesian_xy": ({"cartesian_xy": {"width_mm": ["5", "10"]}}, {"zx": 2, "ay": 1}), "cartesian_xyz": ({"cartesian_xyz": {"width_mm": ["5", "10", "10"]}}, {"zx": 2, "ay": 1, "mz": 2}), "polar": ({"polar": {"width_r_mm": "5", "phi_bins": 4}}, {"rr": 2, "aphi": 2})}


def specification(fields: dict) -> dict:
    crystal = {"solid": {"box": {"size_mm": [str(CRYSTAL_MM), str(CRYSTAL_MM), str(DEPTH_MM)]}}, "material": "G4_PbWO4", "tags": ["crystal"]}
    module = {"solid": {"box": {"size_mm": ["100", "70", "60"]}}, "material": "G4_Galactic", "tags": ["module"],
              "children": [{"template": "crystal", "placement": {"grid": {"n": [COLUMNS, ROWS], "pitch_mm": [str(PITCH_MM), str(PITCH_MM)], "centre_mm": ["0", "0", "0"], "index": ["col", "row"]}}}]}
    pad = {"solid": {"box": {"size_mm": ["200", "200", "1"]}}, "material": "G4_Si", "tags": ["pad"]}
    pads = {"solid": {"box": {"size_mm": ["200", "200", "40"]}}, "material": "G4_Galactic", "tags": ["pads"], "children": [{"template": "pad", "placement": {"linear": {"count": 2, "pitch_mm": ["0", "0", str(PAD_PITCH_MM)], "start_mm": ["0", "0", str(-PAD_PITCH_MM / 2)], "index": "p"}}}]}
    children = [{"template": "module", "placement": {"linear": {"count": MODULES, "pitch_mm": ["0", "0", str(MODULE_PITCH_MM)], "start_mm": ["0", "0", str(-MODULE_PITCH_MM / 2)], "index": "m"}}},
                {"template": "pads", "placement": {"single": {"centre_mm": ["0", "0", str(PAD_START_MM + PAD_PITCH_MM / 2)]}}}]
    return {"schema": "detector-spec/1", "params": {}, "materials": {}, "templates": {"crystal": crystal, "module": module, "pad": pad, "pads": pads}, "readout": {"cal": {"fields": fields}, "pads": {"fields": {"p": 1}}, "flat": {"fields": {"m": 1}}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": children}}


def request(kind: str, particle: str, segmentation: dict, segment_fields: list, pads: bool = False) -> dict:
    source = kits.beam(particle, 2000.0, [0, 0, -300], [0, 0, 1])
    source["position"]["box_uniform"]["size_mm"] = ["70", "45", "0"]
    scorers = [{"name": "crystals", "readout": "cal", "select": {"tags": ["crystal"]}, "quantity": "edep", "level": "event_file", "hit_kind": kind, "segmentation": segmentation, "split": "apportion", "segment_fields": segment_fields}]
    if pads:
        scorers.append({"name": "pads", "readout": "pads", "select": {"tags": ["pad"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker"})
    return {"schema": "simulation-request/1", "source": source, "scorers": scorers}


def run(folder: Path, program: Path, fields: dict, document: dict) -> Path:
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "spec.json").write_text(json.dumps(specification({**COPIES, **fields})), encoding="utf-8")
    return kits.simulate(folder, program, document, EVENTS)


def binned(value: float, half: float, width: float) -> int:
    return min(math.ceil(2 * half / width) - 1, max(0, math.floor((value + half) / width)))


def segment_values(case: str, local: tuple) -> dict:
    x, y, z = local
    half = CRYSTAL_MM / 2
    if case == "polar":
        rings = math.ceil(math.hypot(half, half) / 5.0)
        phi = math.atan2(y, x) % (2 * math.pi)
        return {"rr": min(rings - 1, int(math.hypot(x, y) / 5.0)), "aphi": min(3, int(phi / (2 * math.pi) * 4))}
    every = {"along_z": {"mz": (z, DEPTH_MM / 2, 10.0)}, "along_x": {"zx": (x, half, 5.0)}, "along_y": {"ay": (y, half, 5.0)}, "cartesian_xy": {"zx": (x, half, 5.0), "ay": (y, half, 10.0)}, "cartesian_xyz": {"zx": (x, half, 5.0), "ay": (y, half, 10.0), "mz": (z, DEPTH_MM / 2, 10.0)}}
    return {name: binned(*item) for name, item in every[case].items()}


def indices(row: dict, case: str) -> dict:
    """The cell a position lies in, from the geometry alone: the position never passes through the encoding."""
    x, y, z = (float(row[name]) for name in ("x_mm", "y_mm", "z_mm"))
    module = 0 if z < 0 else 1
    column, line = round(x / PITCH_MM + (COLUMNS - 1) / 2), round(y / PITCH_MM + (ROWS - 1) / 2)
    local = (x - (column - (COLUMNS - 1) / 2) * PITCH_MM, y - (line - (ROWS - 1) / 2) * PITCH_MM, z - (module - 0.5) * MODULE_PITCH_MM)
    return {"col": column, "row": line, "m": module, **segment_values(case, local)}


def read(work: Path, simroot: Path, ntuple: str) -> list:
    target = work / f"{ntuple}.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", ntuple, "--out", str(target)], check=True, capture_output=True, text=True, timeout=600)
    with target.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def judged(work: Path, simroot: Path, ntuple: str, case: str) -> dict:
    rows = read(work, simroot, ntuple)
    fields = json.loads((work / "ir.json").read_text(encoding="utf-8"))["physical"]["readout"]["cal"]["fields"]
    wrong = [row for row in rows if hits.cell_fields(int(row["cell_id"]), fields) != indices(row, case)]
    swapped = [{**field, "stride": fields[(at + 1) % len(fields)]["stride"]} for at, field in enumerate(fields)]  # another bitfield must not decode these cells
    control = sum(hits.cell_fields(int(row["cell_id"]), swapped) != indices(row, case) for row in rows)
    forward: dict = {}
    backward: dict = {}
    for row in rows:
        forward.setdefault(row["cell_id"], set()).add((row["cell"], row["segment"]))
        backward.setdefault((row["cell"], row["segment"]), set()).add(row["cell_id"])
    one_to_one = all(len(value) == 1 for value in forward.values()) and all(len(value) == 1 for value in backward.values())
    return {"rows": len(rows), "cells": len(forward), "wrong": len(wrong), "one_to_one": one_to_one, "wrong_with_another_bitfield": control, "first_wrong": wrong[0] if wrong else None}


def good(item: dict) -> bool:
    return item["rows"] > 0 and item["cells"] > 1 and item["wrong"] == 0 and item["one_to_one"] and item["wrong_with_another_bitfield"] > 0


def two_readouts(root: Path, program: Path, simroot: Path) -> dict:
    """Two readouts in one file: a row's scorer names its bitfield, and the integers alone cannot."""
    segmentation, fields = CASES["along_z"]
    work = run(root / "two", program, fields, request("tracker", "mu-", segmentation, list(fields), pads=True))
    index = json.loads((work / "simulation-hits.json").read_text(encoding="utf-8"))
    bitfields = json.loads((work / "ir.json").read_text(encoding="utf-8"))["physical"]["readout"]
    rows = read(work, simroot, "tracker_hits")
    wrong = counts = 0
    seen: dict = {}
    for row in rows:
        name = index["scorers"][int(row["scorer"])]
        seen[name] = seen.get(name, 0) + 1
        decoded = hits.cell_fields(int(row["cell_id"]), bitfields[index["readouts"][name]]["fields"])
        expected = {"p": round((float(row["z_mm"]) - PAD_START_MM) / PAD_PITCH_MM)} if name == "pads" else indices(row, "along_z")
        wrong += decoded != expected
        counts += 1
    return {"rows": counts, "by_scorer": seen, "wrong": wrong, "holds": wrong == 0 and len(seen) == 2}


def stops(root: Path, name: str, program: Path, fields: dict, document: dict) -> bool:
    try:
        run(root / name, program, fields, document)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        return "g4sim-cellid" in (root / name / "out/log.txt").read_text(encoding="utf-8", errors="replace") or "g4sim-cellid" in str(error)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "work", "old-hits"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    root, program, simroot = args.work.resolve(), args.program.resolve(), args.simroot.resolve()
    results = {}
    for case, (segmentation, fields) in CASES.items():
        results[f"tracker {case}"] = judged(run(root / f"t-{case}", program, fields, request("tracker", "mu-", segmentation, list(fields))), simroot, "tracker_hits", case)
    for case in ("along_z", "polar"):
        segmentation, fields = CASES[case]
        results[f"calorimeter {case}"] = judged(run(root / f"c-{case}", program, fields, request("calorimeter", "e-", segmentation, list(fields))), simroot, "calorimeter_hits", case)
    segmentation, fields = CASES["along_z"]
    pair = two_readouts(root, program, simroot)
    os.environ["G4SIM_HIT_CONTROL"] = "cell_id_no_segment"
    fault = judged(run(root / "fault", program, fields, request("tracker", "mu-", segmentation, list(fields))), simroot, "tracker_hits", "along_z")
    del os.environ["G4SIM_HIT_CONTROL"]
    five_bins = {"along_axis": {"axis": "z", "width_mm": "8"}}  # value 4 against a limit of 4: the first value that does not fit
    narrow = stops(root, "narrow", program, fields, request("tracker", "mu-", five_bins, list(fields)))
    narrow_calorimeter = stops(root, "narrow-c", program, fields, request("calorimeter", "e-", five_bins, list(fields)))
    old = subprocess.run([str(simroot), "hits", str(args.old_hits), "--ntuple", "tracker_hits", "--out", str(root / "old.csv")], capture_output=True, text=True, timeout=300, check=False)
    old_refused = old.returncode != 0 and "were read" in old.stdout + old.stderr
    try:
        run(root / "collision", program, {key: value for key, value in fields.items()}, {**request("tracker", "mu-", segmentation, list(fields)), "scorers": [{**request("tracker", "mu-", segmentation, list(fields))["scorers"][0], "readout": "flat", "segment_fields": []}]})
        collision_refused = False
    except RuntimeError as error:
        collision_refused = "hit-readout" in str(error)
    held = all(good(item) for item in results.values()) and pair["holds"] and fault["wrong"] > 0 and narrow and narrow_calorimeter and old_refused and collision_refused
    print(json.dumps({"status": "ok" if held else "failed", **results, "two_readouts": pair, "producer_fault_wrong_rows": fault["wrong"], "narrow_field_stops_the_run": [narrow, narrow_calorimeter], "old_file_refused": old_refused, "collision_refused": collision_refused}, indent=1))
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())

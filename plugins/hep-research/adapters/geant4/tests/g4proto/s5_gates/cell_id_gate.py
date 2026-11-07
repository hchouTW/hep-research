#!/usr/bin/env python3
"""Encoded cellID in hit files (g4sim plan, Sections 6.2.6, 9.2; registered in g4sim-tasks/S5.md): every hit's decoded fields against the indices found from its position.

Two modules along z, each a grid of crystals, in bins along z. The readout's fields sort as col, iz, m, row, so they do not follow the packing of a grid's copy number, and a cellID built by multiplying copy numbers would decode wrongly. The position of a hit never passes through the encoding, so the comparison is independent of it.

Usage: cell_id_gate.py --program PATH --simroot PATH --work DIR   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
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
PITCH_MM, CRYSTAL_MM, DEPTH_MM, BIN_MM, MODULE_PITCH_MM = 25.0, 20.0, 40.0, 10.0, 150.0
BINS = int(DEPTH_MM / BIN_MM)
EVENTS = 300
READOUT = {"col": 2, "iz": 2, "m": 1, "row": 1}


def specification(fields: dict) -> dict:
    crystal = {"solid": {"box": {"size_mm": [str(CRYSTAL_MM), str(CRYSTAL_MM), str(DEPTH_MM)]}}, "material": "G4_PbWO4", "tags": ["crystal"]}
    module = {"solid": {"box": {"size_mm": ["100", "70", "60"]}}, "material": "G4_Galactic", "tags": ["module"],
              "children": [{"template": "crystal", "placement": {"grid": {"n": [COLUMNS, ROWS], "pitch_mm": [str(PITCH_MM), str(PITCH_MM)], "centre_mm": ["0", "0", "0"], "index": ["col", "row"]}}}]}
    return {"schema": "detector-spec/1", "params": {}, "materials": {}, "templates": {"crystal": crystal, "module": module}, "readout": {"cal": {"fields": fields}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "module", "placement": {"linear": {"count": MODULES, "pitch_mm": ["0", "0", str(MODULE_PITCH_MM)], "start_mm": ["0", "0", str(-MODULE_PITCH_MM / 2)], "index": "m"}}}]}}


def request(kind: str, particle: str) -> dict:
    source = kits.beam(particle, 2000.0, [0, 0, -300], [0, 0, 1])
    source["position"]["box_uniform"]["size_mm"] = ["70", "45", "0"]
    scorer = {"name": "crystals", "readout": "cal", "select": {"tags": ["crystal"]}, "quantity": "edep", "level": "event_file", "hit_kind": kind, "segmentation": {"along_axis": {"axis": "z", "width_mm": str(BIN_MM)}}, "split": "apportion", "segment_fields": ["iz"]}
    return {"schema": "simulation-request/1", "source": source, "scorers": [scorer]}


def run(folder: Path, program: Path, fields: dict, kind: str, particle: str) -> Path:
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "spec.json").write_text(json.dumps(specification(fields)), encoding="utf-8")
    return kits.simulate(folder, program, request(kind, particle), EVENTS)


def indices(row: dict) -> dict:
    """The cell a position lies in, from the geometry alone."""
    x, y, z = (float(row[name]) for name in ("x_mm", "y_mm", "z_mm"))
    module = 0 if z < 0 else 1
    front = (module - 0.5) * MODULE_PITCH_MM - DEPTH_MM / 2
    return {"col": round(x / PITCH_MM + (COLUMNS - 1) / 2), "row": round(y / PITCH_MM + (ROWS - 1) / 2), "m": module, "iz": min(BINS - 1, max(0, math.floor((z - front) / BIN_MM)))}


def judged(work: Path, simroot: Path, ntuple: str) -> dict:
    target = work / f"{ntuple}.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", ntuple, "--out", str(target)], check=True, capture_output=True, text=True, timeout=600)
    with target.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = json.loads((work / "ir.json").read_text(encoding="utf-8"))["physical"]["readout"]["cal"]["fields"]
    wrong = [row for row in rows if hits.cell_fields(int(row["cell_id"]), fields) != indices(row)]
    forward: dict = {}
    backward: dict = {}
    for row in rows:
        forward.setdefault(row["cell_id"], set()).add((row["cell"], row["segment"]))
        backward.setdefault((row["cell"], row["segment"]), set()).add(row["cell_id"])
    one_to_one = all(len(value) == 1 for value in forward.values()) and all(len(value) == 1 for value in backward.values())
    return {"rows": len(rows), "cells": len(forward), "wrong": len(wrong), "one_to_one": one_to_one, "first_wrong": wrong[0] if wrong else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    root, program, simroot = args.work.resolve(), args.program.resolve(), args.simroot.resolve()
    results = {"tracker": judged(run(root / "tracker", program, READOUT, "tracker", "mu-"), simroot, "tracker_hits"), "calorimeter": judged(run(root / "calorimeter", program, READOUT, "calorimeter", "e-"), simroot, "calorimeter_hits")}
    try:
        run(root / "narrow", program, {**READOUT, "iz": 1}, "calorimeter", "e-")
        refused = False
    except (RuntimeError, subprocess.CalledProcessError) as error:
        refused = "g4sim-cellid" in (root / "narrow/out/log.txt").read_text(encoding="utf-8", errors="replace") or "g4sim-cellid" in str(error)
    held = refused and all(item["rows"] > 0 and item["cells"] > 1 and item["wrong"] == 0 and item["one_to_one"] for item in results.values())
    print(json.dumps({"status": "ok" if held else "failed", **results, "narrow_field_stops_the_run": refused}, indent=1))
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())

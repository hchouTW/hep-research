#!/usr/bin/env python3
"""What simreco needs from a g4sim run (g4sim plan, Sections 9.2, 19.2): the planes and the field as simreco_spec.py reads them, and the crossings and events it reads, from the IR and the hit file.

A library of geant4_run.py reco: simreco reads a telescope along x, so the planes are the volumes of the tagged templates, in order of x. Nothing here runs Geant4.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))

from core.simulation import hits  # noqa: E402

TRACKER_TAG = "tracker"


def world_positions(ir: dict) -> list:
    """(template, position in the world) of every placed volume: the placements hold positions in their mother."""
    placements = ir["physical"]["placements"]
    found = []

    def walk(mother: str, origin: tuple) -> None:
        for item in placements:
            if item["mother"] == mother:
                position = tuple(origin[i] + float(item["centre_mm"][i]) for i in range(3))
                found.append((item["template"], position))
                walk(item["template"], position)

    walk("world", (0.0, 0.0, 0.0))
    return found


def half_lengths(template: dict) -> list:
    return [float(value) for value in template["half_mm"]]


def element_view(ir: dict, request: dict, card: dict, field_tesla: list) -> dict:
    """The telescope as simreco_spec.py reads an element_sim spec: tracker planes in order of x, and one field region over the world."""
    templates, tags = ir["physical"]["templates"], ir["marker"]["tags"]
    placed = sorted((position, name) for name, position in world_positions(ir) if TRACKER_TAG in tags.get(name, []))
    if not placed:
        raise ValueError("the specification has no volume tagged tracker")
    elements = [{"name": f"plane{at}", "role": "tracker-plane", "material": templates[name]["material"], "centre_mm": list(position), "half_mm": half_lengths(templates[name])} for at, (position, name) in enumerate(placed)]
    elements.append({"name": "field", "role": "passive", "material": templates["world"]["material"], "centre_mm": [0.0, 0.0, 0.0], "half_mm": half_lengths(templates["world"])})
    return {"schema": "g4sim.element-view/1", "elements": elements, "field": {"regions": [{"element": "field", "b_tesla": field_tesla}]}, "run": {"logical_run_seed": card["run"]["logical_run_seed"]}, "source": {"particle": request["source"]["particle"]}}


def read_ntuple(simroot: Path, hit_file: Path, name: str, target: Path) -> list:
    subprocess.run([str(simroot), "hits", str(hit_file), "--ntuple", name, "--out", str(target)], check=True, capture_output=True, text=True, timeout=3600)
    with target.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    target.unlink()
    return rows


def write_columns(simroot: Path, run_folder: Path, view: dict, crossings: Path, events: Path) -> int:
    """simreco's crossings and events files of a run; returns the rows written. A cell is matched to the plane nearest its hits in x."""
    tracker = read_ntuple(simroot, run_folder / "hits.root", "tracker_hits", crossings.with_suffix(".tracker.csv"))
    particles = read_ntuple(simroot, run_folder / "hits.root", "mc_particles", crossings.with_suffix(".particles.csv"))
    faces = [element["centre_mm"][0] for element in view["elements"] if element["role"] == "tracker-plane"]
    first_x: dict = {}
    for row in tracker:
        first_x.setdefault(int(row["cell"]), float(row["x_mm"]))
    planes = {cell: min(range(len(faces)), key=lambda at, x=x: abs(faces[at] - x)) for cell, x in first_x.items()}
    rows = hits.columns_for_simreco(tracker, particles, planes)
    with crossings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=hits.CROSSING_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    primaries = {int(row["event_id"]): int(row["pdg"]) for row in particles if int(row["parent_id"]) == 0}
    events.write_text("# SIMULATION\nevent,primary_pdg\n" + "".join(f"{event},{pdg}\n" for event, pdg in sorted(primaries.items())), encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    print(json.dumps({"status": "rejected", "message": "a library: run geant4_run.py reco"}))
    sys.exit(2)

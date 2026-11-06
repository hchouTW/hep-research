#!/usr/bin/env python3
"""S3 gate 2: x/X0 along declared rays, analytic in Python against a Geant4 geantino scan, relative difference at most 1e-3 (g4sim plan, Section 19.2).

The rays are the geantinos' own: positions and directions are drawn by a declared source and written by g4sim_run as doubles, so both sides trace the same line.
Usage: ray_budget.py --detector SPEC --program PATH --work DIR [--rays N] [--seed S]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from contracts import geometry  # noqa: E402
from core.geometry import material  # noqa: E402

DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
RELATIVE_LIMIT = 1e-3
FACE_SIZE_MM = ["130", "130", "0"]
HALF_ANGLE_DEG = "3"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--detector", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--rays", type=int, default=500)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    checked = geometry.check_file(args.detector)
    if checked["status"] != "ok":
        print(json.dumps({"status": "rejected", "findings": checked["findings"]}))
        return 2
    ir = checked["ir"]
    templates = sorted(ir["physical"]["templates"])
    request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "geantino", "energy": {"mono": {"energy_MeV": "1000"}},
                                                            "position": {"box_uniform": {"frame": "gun", "centre_mm": ["0", "0", "0"], "size_mm": FACE_SIZE_MM}},
                                                            "direction": {"cone": {"frame": "gun", "axis": [0, 0, 1], "half_angle_deg": HALF_ANGLE_DEG}}},
               "scorers": [{"name": f"path_{name}", "readout": "none", "select": {"templates": [name]}, "quantity": "track_length"} for name in templates]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": args.rays, "first_event": 0, "logical_run_seed": args.seed, "mode": "mt", "seeding": "per-event", "threads": 2}}
    (args.work / "request.in.json").write_text(json.dumps(request), encoding="utf-8")
    (args.work / "run.in.json").write_text(json.dumps(card), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(args.detector), "--request", str(args.work / "request.in.json"), "--run", str(args.work / "run.in.json"),
                           "--program", str(args.program.resolve()), "--work", str(args.work / "run")], capture_output=True, text=True, check=False)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        print(json.dumps({"status": "failed", "run": summary}))
        return 1
    work = args.work / "run"
    probe = json.loads((work / "probe-v2.json").read_text(encoding="utf-8"))
    lengths = {item["name"]: float.fromhex(item["radiation_length_mm"]) for item in probe["materials"]}
    of_template = {name: node["material"] for name, node in ir["physical"]["templates"].items()}
    geant4: dict = {}
    for line in (work / "cells.csv").read_text(encoding="utf-8").splitlines():
        event, scorer, volume, _, value = line.split(",")[:5]
        if volume != "-1":
            geant4[int(event)] = geant4.get(int(event), 0.0) + float(value) / lengths[of_template[scorer[len("path_"):]]]
    table = {name: Decimal(repr(value)) for name, value in lengths.items()}
    worst, worst_ray, compared = 0.0, None, 0
    for line in (work / "primaries.csv").read_text(encoding="utf-8").splitlines():
        cells = line.split(",")
        event = int(cells[0])
        origin = tuple(Decimal(value) for value in cells[2:5])
        heading = tuple(Decimal(value) for value in cells[5:8])
        analytic = float(material.budget(ir, origin, heading, table))
        difference = abs(geant4.get(event, 0.0) / analytic - 1) if analytic else math.inf
        compared += 1
        if difference > worst:
            worst, worst_ray = difference, {"event": event, "analytic": analytic, "geant4": geant4.get(event, 0.0)}
    budgets = sorted(geant4.values())
    passed = compared == args.rays and worst <= RELATIVE_LIMIT
    print(json.dumps({"status": "ok" if passed else "failed", "rays": compared, "worst_relative": worst, "worst_ray": worst_ray, "limit": RELATIVE_LIMIT, "budget_range": [budgets[0], budgets[-1]]}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

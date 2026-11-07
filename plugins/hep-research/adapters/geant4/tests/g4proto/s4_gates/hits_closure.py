#!/usr/bin/env python3
"""S4 gate 8: a hit file read back through simroot agrees with the scorer sums, and truth keeping is consistent (g4sim plan, Sections 9.2, 9.3, 19.2).

Usage: hits_closure.py --program PATH --simroot PATH --work DIR [--events N]   In an activated Geant4 environment, from the plugin root. Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.simulation import hits  # noqa: E402

FIXTURES = PLUGIN / "tests/adapters/data"
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"g4sim_block.{name}.json").read_text(encoding="utf-8"))


def read_ntuple(simroot: Path, work: Path, name: str) -> list:
    target = work / f"{name}.csv"
    subprocess.run([str(simroot), "hits", str(work / "hits.root"), "--ntuple", name, "--out", str(target)], check=True, capture_output=True, text=True, timeout=300)
    with target.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--simroot", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int, default=300)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    spec, request, card = fixture("spec"), fixture("request"), fixture("run")
    card["run"]["events"] = args.events
    request["scorers"] = [{"name": "calorimeter", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep", "level": "event_file", "hit_kind": "calorimeter"}]
    request["reference_planes"] = [{"name": "front", "frame": "world", "z_mm": "-150"}]
    request["truth"] = {"keep": ["primary", "decay_products"], "time_bin_ns": 1}
    request["source"]["particle"] = "proton"  # its pions are not kept and their decay muons are, so pruning happens
    request["source"]["energy"] = {"uniform": {"min_MeV": "1000", "max_MeV": "2000"}}
    for name, block in (("spec", spec), ("request", request), ("run", card)):
        (root / f"{name}.json").write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(root / "spec.json"), "--request", str(root / "request.json"), "--run", str(root / "run.json"), "--program", str(args.program.resolve()), "--work", str(root / "run")],
                          capture_output=True, text=True, check=False, timeout=900)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        print(json.dumps({"status": "failed", "run": summary}))
        return 1
    work = root / "run"
    simroot = args.simroot.resolve()
    calorimeter, parts, particles, planes = (read_ntuple(simroot, work, name) for name in ("calorimeter_hits", "contributions", "mc_particles", "plane_crossings"))
    scorer = {}
    with (work / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[1] == "calorimeter" and row[2] != "-1":
                scorer[(int(row[0]), float(row[2]))] = float(row[4])
    from_hits, from_parts = hits.sums_by_cell(calorimeter), hits.sums_by_cell(parts)
    against_scorer, against_parts = hits.closure(from_hits, scorer), hits.closure(from_hits, from_parts)
    orphans = hits.owners_are_kept(particles, parts)
    pruned = sum(int(row["ancestor_pruned"]) for row in particles)
    primaries = sum(int(row["parent_id"]) == 0 for row in particles)
    crossed = {int(row["event_id"]) for row in planes}
    index = json.loads((work / "simulation-hits.json").read_text(encoding="utf-8"))
    passed = against_scorer["ok"] and against_parts["ok"] and not orphans and primaries >= args.events and len(crossed) == args.events and pruned > 0 and index["schema"] == hits.SCHEMA
    print(json.dumps({"status": "ok" if passed else "failed", "against_scorer": against_scorer, "against_contributions": against_parts, "orphans": orphans, "particles": len(particles), "pruned": pruned, "primaries": primaries,
                      "events_crossing_the_plane": len(crossed), "hit_rows": len(calorimeter), "contribution_rows": len(parts)}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

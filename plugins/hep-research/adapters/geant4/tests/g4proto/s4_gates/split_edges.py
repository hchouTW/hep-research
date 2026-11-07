#!/usr/bin/env python3
"""S4: split steps at the edges of a segmentation, live (g4sim plan, Sections 9.2, 10.2).

A track on the exact diagonal of a grid crosses two bin edges at one point, which once made a piece of no width and rows of NaN. A track through the rings of a polar segmentation leaves a ring and comes back to it, and
the mean of the two arcs once lay outside the ring. A segmentation above 2^16 bins stops the run before any event, even if nothing reaches it.

Usage: split_edges.py --program PATH --simroot PATH --work DIR   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
EVENTS = 60
GRID_MM, RING_MM, SECTORS = 1.0, 0.05, 1  # one sector: a track across the axis comes back to the same bin
RINGS = 1000
PROTON_PDG = 2212


def run(folder: Path, segmentation: dict, line: str, hit_kind: str, extra_scorers: tuple = ()) -> dict:
    folder.mkdir(parents=True)
    rows = ["# g4sim-events/1"]
    for event in range(EVENTS):
        rows += [f"event {event} 1", line]
    (folder / "events.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    digest = hashlib.sha256((folder / "events.txt").read_bytes()).hexdigest()
    spec = {"schema": "detector-spec/1", "params": {}, "materials": {}, "templates": {"block": {"solid": {"box": {"size_mm": ["100", "100", "40"]}}, "material": "G4_Si", "tags": ["active"]}, "far": {"solid": {"box": {"size_mm": ["100", "100", "1"]}}, "material": "G4_Si", "tags": ["far"]}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "block", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}, {"template": "far", "placement": {"single": {"centre_mm": ["0", "0", "400"]}}}]}, "frames": {}}
    request = {"schema": "simulation-request/1", "source": {"density": "external", "format": "text", "path": "events.txt", "sha256": digest},
               "scorers": [{"name": "hits", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep", "level": "event_file", "hit_kind": hit_kind, "segmentation": segmentation, "split": "apportion", "apportion_short_step_fraction": "0"}, *extra_scorers]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated", "run": {"events": EVENTS, "first_event": 0, "logical_run_seed": 77, "mode": "mt", "seeding": "per-event", "threads": 1}}
    for label, block in (("spec", spec), ("request", request), ("run", card)):
        (folder / f"{label}.json").write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"), "--program", str(PROGRAM), "--work", str(folder / "out")],
                          capture_output=True, text=True, check=False, timeout=600)
    return json.loads(done.stdout.strip().splitlines()[-1])


def rows_of(folder: Path, name: str) -> list:
    target = folder / "out" / f"{name}.csv"
    subprocess.run([str(SIMROOT), "hits", str(folder / "out/hits.root"), "--ntuple", name, "--out", str(target)], check=True, capture_output=True, text=True, timeout=120)
    with target.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def finite(rows: list) -> bool:
    return all(math.isfinite(float(value)) for row in rows for value in row.values())


def main() -> int:
    global PROGRAM, SIMROOT
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    PROGRAM, SIMROOT = args.program.resolve(), args.simroot.resolve()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    grid = {"cartesian_xy": {"width_mm": [str(GRID_MM), str(GRID_MM)]}}
    diagonal = f"{PROTON_PDG} -40 -40 -300 300 300 1000"  # at the block's face x = y = 50 mm from the corner of a bin, moving equally in both
    results = {}
    for kind in ("tracker", "calorimeter"):
        summary = run(root / f"diagonal-{kind}", grid, diagonal, kind)
        tables = {"tracker_hits"} if kind == "tracker" else {"calorimeter_hits", "contributions"}
        results[f"diagonal_{kind}"] = {"status": summary["status"], "rows": {name: len(rows_of(root / f"diagonal-{kind}", name)) for name in tables}, "finite": all(finite(rows_of(root / f"diagonal-{kind}", name)) for name in tables)}
    summary = run(root / "polar", {"polar": {"width_r_mm": str(RING_MM), "phi_bins": SECTORS}}, f"{PROTON_PDG} -100 0.02 0 500 0 0", "tracker")  # across the axis within one step, so that it leaves each ring and comes back
    rows = rows_of(root / "polar", "tracker_hits")
    wrong = [row for row in rows if int(row["segment"]) // SECTORS != min(int(math.hypot(float(row["x_mm"]), float(row["y_mm"])) / RING_MM), RINGS - 1)]  # the outer ring takes the corners of the square
    results["polar"] = {"status": summary["status"], "rows": len(rows), "out_of_their_ring": len(wrong)}
    fine = {"cartesian_xy": {"width_mm": ["0.01", "0.01"]}}
    results["over_the_limit"] = run(root / "too-fine", fine, diagonal, "tracker")
    far = {"name": "unreached", "readout": "none", "select": {"tags": ["far"]}, "quantity": "edep", "segmentation": {"cartesian_xy": {"width_mm": ["1e-8", "1e-8"]}}}
    results["over_the_limit_and_unreached"] = run(root / "unreached", grid, f"{PROTON_PDG} 0 0 -300 0 500 0", "tracker", (far,))
    refused = [results[name] for name in ("over_the_limit", "over_the_limit_and_unreached")]
    passed = (all(results[f"diagonal_{kind}"]["status"] == "ok" and results[f"diagonal_{kind}"]["finite"] and min(results[f"diagonal_{kind}"]["rows"].values()) > 0 for kind in ("tracker", "calorimeter")) and results["polar"]["status"] == "ok" and results["polar"]["rows"] > 0
              and results["polar"]["out_of_their_ring"] == 0 and all(item["status"] == "failed" and item["stage"].startswith("preflight") and "a segmentation of" in item["reason"] for item in refused))
    print(json.dumps({"status": "ok" if passed else "failed", **results}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

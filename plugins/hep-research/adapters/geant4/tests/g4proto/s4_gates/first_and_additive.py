#!/usr/bin/env python3
"""S4: first-type scorers and the remaining additive quantities, live, on values physics fixes (g4sim plan, Section 19.2 S4).

A 200 mm block 200 mm downstream of the source, in vacuum. Events from a text file:
  two events holding a slow proton and a fast electron, in both orders: `time_first` and `first_entry_kinematics` must be the electron's whichever is tracked first;
  10 GeV muons: `track_length` covers the block, and `edep_charged` holds nearly all of `edep`;
  1 MeV photons: `edep_charged` falls below `edep`, so it is not `edep` under another name; `edep_nonionizing` stays within `edep`.
Usage: first_and_additive.py --program PATH --work DIR   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
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
FIXTURES = PLUGIN / "tests/adapters/data"
LIGHT_MM_PER_NS = 299.792458
FLIGHT_MM = 200.0
BLOCK_MM = 200.0
START_Z_MM = -300.0
ELECTRON_PDG, ELECTRON_MASS, PROTON_PDG, PROTON_MASS = 11, 0.51099895, 2212, 938.27208816
MUON_PDG, PHOTON_PDG = 13, 22
ELECTRON_MOMENTUM, PROTON_MOMENTUM = 1000.0, 400.0
GROUP_EVENTS = 200
TIME_TOLERANCE_NS, ENERGY_TOLERANCE_MEV = 1e-6, 1e-3
QUANTITIES = ("edep", "edep_charged", "edep_nonionizing", "track_length")


def flight_ns(momentum: float, mass: float) -> float:
    return FLIGHT_MM * math.hypot(momentum, mass) / momentum / LIGHT_MM_PER_NS


def line(pdg: int, momentum: float) -> str:
    return f"{pdg} 0 0 {START_Z_MM} 0 0 {momentum}"


def write_events(path: Path) -> tuple:
    rows = ["# g4sim-events/1", "event 0 2", line(PROTON_PDG, PROTON_MOMENTUM), line(ELECTRON_PDG, ELECTRON_MOMENTUM), "event 1 2", line(ELECTRON_PDG, ELECTRON_MOMENTUM), line(PROTON_PDG, PROTON_MOMENTUM)]
    event = 2
    for pdg, momentum in ((MUON_PDG, 10000.0), (PHOTON_PDG, 1.0)):
        for _ in range(GROUP_EVENTS):
            rows += [f"event {event} 1", line(pdg, momentum)]
            event += 1
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return event, hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    events, digest = write_events(root / "events.txt")
    spec, card = (json.loads((FIXTURES / f"g4sim_block.{name}.json").read_text(encoding="utf-8")) for name in ("spec", "run"))
    select = {"tags": ["active"]}
    request = {"schema": "simulation-request/1", "source": {"density": "external", "format": "text", "path": "events.txt", "sha256": digest},
               "scorers": [{"name": name, "readout": "none", "select": select, "quantity": name} for name in (*QUANTITIES, "time_first", "first_entry_kinematics")]}
    card["run"].update(events=events, threads=1)
    for name, block in (("spec", spec), ("request", request), ("run", card)):
        (root / f"{name}.json").write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(root / "spec.json"), "--request", str(root / "request.json"), "--run", str(root / "run.json"), "--program", str(args.program.resolve()), "--work", str(root / "run")],
                          capture_output=True, text=True, check=False, timeout=900)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        print(json.dumps({"status": "failed", "run": summary}))
        return 1
    table: dict = {}
    with (root / "run/cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[2] != "-1":
                table.setdefault(int(row[0]), {}).setdefault(row[1], []).append(row[3:])
    sums = {event: {name: math.fsum(float(cell[1]) for cell in table[event].get(name, [])) for name in QUANTITIES} for event in table}
    electron_time = flight_ns(ELECTRON_MOMENTUM, ELECTRON_MASS)
    first = {event: {"time_ns": float(table[event]["time_first"][0][1]), "pdg": int(float(table[event]["first_entry_kinematics"][0][2])), "ekin_MeV": float(table[event]["first_entry_kinematics"][0][3])} for event in (0, 1)}
    electron_kinetic = math.hypot(ELECTRON_MOMENTUM, ELECTRON_MASS) - ELECTRON_MASS
    earliest = all(abs(row["time_ns"] - electron_time) <= TIME_TOLERANCE_NS and row["pdg"] == ELECTRON_PDG and abs(row["ekin_MeV"] - electron_kinetic) <= ENERGY_TOLERANCE_MEV for row in first.values())
    muons = [sums[event] for event in range(2, 2 + GROUP_EVENTS) if event in sums]
    photons = [sums[event] for event in range(2 + GROUP_EVENTS, events) if event in sums]
    within = all(row["edep_charged"] <= row["edep"] * (1 + 1e-12) and 0 <= row["edep_nonionizing"] <= row["edep"] * (1 + 1e-12) for row in muons + photons)
    track_covers = min(row["track_length"] for row in muons) >= BLOCK_MM * (1 - 1e-9)
    muon_share = math.fsum(row["edep_charged"] for row in muons) / math.fsum(row["edep"] for row in muons)
    photon_share = math.fsum(row["edep_charged"] for row in photons) / math.fsum(row["edep"] for row in photons)
    passed = earliest and within and track_covers and muon_share > 0.9 and photon_share < 1.0 and len(muons) == GROUP_EVENTS and photons
    print(json.dumps({"status": "ok" if passed else "failed", "expected_time_ns": electron_time, "expected_ekin_MeV": electron_kinetic, "proton_time_ns": flight_ns(PROTON_MOMENTUM, PROTON_MASS), "first": first, "earliest_is_the_electron": earliest,
                      "muons": len(muons), "photons": len(photons), "shortest_muon_track_mm": min(row["track_length"] for row in muons), "charged_share_muons": muon_share, "charged_share_photons": photon_share, "largest_nonionizing_MeV": max(row["edep_nonionizing"] for row in muons + photons), "within_edep": within}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

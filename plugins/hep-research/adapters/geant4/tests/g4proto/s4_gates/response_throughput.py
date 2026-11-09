#!/usr/bin/env python3
"""S4: the Python response pipeline against the transport of the same events, on one core (g4sim performance budget, Section 16).

With --photon-times every detected photon of every channel also gets a time (`response.photon_times`, decay 2.1 ns, exponential transit 1 ns),
the per-photon cost the budget's first measurements left out (S8 settles `g4sim_digi` with it).
Usage: response_throughput.py FOLDER --program PATH --events N [--photon-times]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 within the limit, 1 over it.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(PLUGIN), str(HERE)]

import json  # noqa: E402

import scintillation_equivalence as run_source  # noqa: E402
from core.simulation import response, rng  # noqa: E402

LIMIT = 0.25  # g4sim-performance-budget.md
CHANNELS = ("left", "right", "top", "bottom")
STAGE = {"name": "scintillation", "kind": "scintillation", "parameters": {"light_yield_per_MeV": {"value": run_source.LIGHT_YIELD, "source_of_facts": "assumed"}, "resolution_scale": {"value": 1.0, "source_of_facts": "assumed"}}}
PIPELINE = {"schema": response.SCHEMA, "run_seed": 7, "replica": 0, "stages": [STAGE]}
LIGHT_MAP = {"schema": "efficiency-map/1", "channels": list(CHANNELS), "form": {"kind": "uniform", "value": [0.1, 0.1, 0.1, 0.1]}}


def transport_seconds(folder: Path) -> float:
    stamps = {}
    for line in (folder / "out/log.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        words = line.split()
        if len(words) == 2 and words[0] in ("G4SIM_INITIALIZED", "G4SIM_DONE"):
            stamps[words[0]] = float(words[1])
    return stamps["G4SIM_DONE"] - stamps["G4SIM_INITIALIZED"]


def respond(bins: list, timing: bool = False) -> int:
    """Every bin of every event through photon numbers, channels, sensor and electronics; returns the channels read out."""
    events: dict = {}
    for event, volume, bin_index, large, small, steps in bins:
        events.setdefault((event, volume), {})[bin_index] = (large, small, steps)
    sensor_key, electronics_key = (rng.channel_key(7, "tracker", stage, 0) for stage in ("sensor", "electronics"))
    fired = 0
    for (event, volume), rows in events.items():
        for at, photons in enumerate(response.scintillation_event(PIPELINE, STAGE, event, volume, rows, LIGHT_MAP).values()):
            cell = volume * len(CHANNELS) + at
            if timing:
                response.photon_times(PIPELINE, STAGE["name"], event, cell, 0, photons, 2.1, 1.0)
            charge = response.sensor_response(rng.SubStream(sensor_key, event, cell), photons, 1.0, 0.1, 1e-4, 100.0)
            fired += response.electronics_response(rng.SubStream(electronics_key, event, cell), charge, 0.5, 2.0, 0.25, 12) is not None
    return fired


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--events", type=int, default=2000)
    parser.add_argument("--photon-times", action="store_true")
    args = parser.parse_args()
    folder = args.folder.resolve()
    shutil.rmtree(folder, ignore_errors=True)
    if run_source.run(folder, args.program.resolve(), args.events, threads=1):
        print(json.dumps({"status": "failed", "error": "the run failed"}))
        return 1
    bins = run_source.read_bins(folder)
    start = time.perf_counter()
    fired = respond(bins, args.photon_times)
    responding = time.perf_counter() - start
    transporting = transport_seconds(folder)
    ratio = responding / transporting
    print(json.dumps({"status": "ok" if ratio <= LIMIT else "failed", "events": args.events, "photon_times": args.photon_times, "bins": len(bins), "channels_fired": fired, "transport_s": transporting, "response_s": responding, "ratio": ratio, "limit": LIMIT, "bins_per_s": len(bins) / responding}, indent=1))
    return 0 if ratio <= LIMIT else 1


if __name__ == "__main__":
    sys.exit(main())

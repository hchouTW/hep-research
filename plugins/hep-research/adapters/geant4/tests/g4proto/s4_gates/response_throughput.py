#!/usr/bin/env python3
"""S4: the Python response pipeline against the transport of the same events, on one core (g4sim performance budget, Section 16).

With --photon-times every detected photon of every channel also gets a time (`response.photon_times`, decay 2.1 ns, exponential transit 1 ns),
the per-photon cost the budget's first measurements left out (S8 settles `g4sim_digi` with it). With --digi PATH the response of the same
bins is g4sim_digi's instead (S8): its wall time, reading the job and bins and writing every channel row (and time), against the transport.
Usage: response_throughput.py FOLDER --program PATH --events N [--photon-times] [--digi PATH]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 within the limit, 1 over it.
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
import subprocess  # noqa: E402

import scintillation_equivalence as run_source  # noqa: E402
from core.simulation import digitize, response, rng  # noqa: E402

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


def respond_digi(folder: Path, bins: list, program: Path, timing: bool) -> float:
    """g4sim_digi on the same bins, with the stage, sensor and electronics settings of respond(); its wall time in seconds."""
    job = {"schema": digitize.SCHEMA, "run_seed": 7, "replica": 0, "readout": "tracker", "channels": list(CHANNELS),
           "stage": {"name": STAGE["name"], "light_yield_per_MeV": run_source.LIGHT_YIELD, "resolution_scale": 1.0},
           "efficiencies": {str(b): list(LIGHT_MAP["form"]["value"]) for b in sorted({row[2] for row in bins})},
           "timing": {"decay_ns": 2.1, "transit": {"kind": "exponential", "transit_ns": 1.0}} if timing else None,
           "sensor": {"name": "sensor", "gain": 1.0, "excess_noise": 0.1, "dark_rate_per_ns": 1e-4, "gate_ns": 100.0},
           "electronics": {"name": "electronics", "noise_sigma": 0.5, "threshold": 2.0, "lsb": 0.25, "bits": 12}}
    (folder / "digi-job.json").write_text(json.dumps(digitize.job_with_keys(job)), encoding="utf-8")
    (folder / "digi-bins.csv").write_text("".join(f"{e},{v},{b},{float(large).hex()},{float(small).hex()},{n}\n" for e, v, b, large, small, n in bins), encoding="ascii")
    command = [str(program), str(folder / "digi-job.json"), str(folder / "digi-bins.csv"), str(folder / "digi-channels.csv")] + ([str(folder / "digi-times.csv")] if timing else [])
    start = time.perf_counter()
    subprocess.run(command, check=True, timeout=3000)
    return time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--events", type=int, default=2000)
    parser.add_argument("--photon-times", action="store_true")
    parser.add_argument("--digi", type=Path, help="time g4sim_digi on the same bins instead of the Python response")
    args = parser.parse_args()
    folder = args.folder.resolve()
    shutil.rmtree(folder, ignore_errors=True)
    if run_source.run(folder, args.program.resolve(), args.events, threads=1):
        print(json.dumps({"status": "failed", "error": "the run failed"}))
        return 1
    bins = run_source.read_bins(folder)
    if args.digi:
        fired, responding = None, respond_digi(folder, bins, args.digi.resolve(), args.photon_times)
    else:
        start = time.perf_counter()
        fired = respond(bins, args.photon_times)
        responding = time.perf_counter() - start
    transporting = transport_seconds(folder)
    ratio = responding / transporting
    print(json.dumps({"status": "ok" if ratio <= LIMIT else "failed", "events": args.events, "photon_times": args.photon_times, "response": "g4sim_digi" if args.digi else "python", "bins": len(bins), "channels_fired": fired, "transport_s": transporting, "response_s": responding, "ratio": ratio, "limit": LIMIT, "bins_per_s": len(bins) / responding}, indent=1))
    return 0 if ratio <= LIMIT else 1


if __name__ == "__main__":
    sys.exit(main())

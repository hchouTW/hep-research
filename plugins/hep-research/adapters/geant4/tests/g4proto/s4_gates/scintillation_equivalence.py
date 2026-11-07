#!/usr/bin/env python3
"""S4 gates 3 and 7, from a real g4sim_run output (`edep_visible_ly_split`), never a hand-written fixture (g4sim plan, Section 19.2).

  run FOLDER --program PATH --events N                 the run that supplies E^L, E^S and n^L
  determinism FOLDER                                   gate 3: bit-identical after shuffling, and with any number of chunks
  trial FOLDER --out TRIAL.json                        gate 7's independent trial: K and the draws needed
  equivalence FOLDER --design TRIAL.json               gate 7: TOST of the mean and variance at r = 1 and r = 0.5, on other replicas

Statistics per (r, regime, moment): d1 = N - mu and d2 = (N - mu)^2 - v, averaged over draws, so a spread of mu among bins does not enter the variance; margins are relative to the mean of mu and of v.
Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.simulation import response, rng  # noqa: E402

DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
FIXTURES = PLUGIN / "tests/adapters/data"
LIGHT_YIELD = 100.0
SCALES = (1.0, 0.5)
MEAN_MARGIN, VARIANCE_MARGIN = 0.005, 0.03
ALPHA_Z = 1.6448536269514722
JOINT_POWER = 0.9
TRIAL_REPLICAS = range(1000, 1012)
TEST_FIRST_REPLICA = 2000


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"g4sim_block.{name}.json").read_text(encoding="utf-8"))


def run(folder: Path, program: Path, events: int) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    spec, request, card = fixture("spec"), fixture("request"), fixture("run")
    spec["materials"]["scintillator"]["scintillation"] = {"yield_per_MeV": str(LIGHT_YIELD), "resolution_scale": "1", "facts": "assumed"}
    request["source"]["energy"] = {"uniform": {"min_MeV": "1", "max_MeV": "60"}}
    request["scorers"] = [{"name": "split", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep_visible_ly_split", "segmentation": {"along_axis": {"axis": "z", "width_mm": "1"}}, "split": "midpoint"}]
    card["run"]["events"] = events
    for name, block in (("spec", spec), ("request", request), ("run", card)):
        (folder / f"{name}.json").write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"), "--program", str(program.resolve()), "--work", str(folder / "out")],
                          capture_output=True, text=True, check=False, timeout=3000)
    print(done.stdout.strip().splitlines()[-1][:300])
    return done.returncode


def read_bins(folder: Path) -> list:
    """[(event, volume, bin, E^L, E^S, n^L)] from the run's rows: even bins hold E^L and n^L, odd bins E^S."""
    table: dict = {}
    with (folder / "out/cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[2] == "-1":
                continue
            key = (int(row[0]), int(row[2]), int(row[3]) // 2)
            cell = table.setdefault(key, [0.0, 0.0, 0])
            if int(row[3]) % 2 == 0:
                cell[0] += float(row[4])
                cell[2] += int(row[5])
            else:
                cell[1] += float(row[4])
    return [(*key, *value) for key, value in sorted(table.items())]


def draw(bins_row: tuple, scale: float, replica: int) -> int:
    event, volume, bin_index, large, small, steps = bins_row
    stream = rng.SubStream(rng.volume_key(20261107, f"gate7-{scale}", replica), event, volume, bin_index)
    return response.bin_photons(stream, LIGHT_YIELD, scale, large, small, steps)


def regime(bins_row: tuple) -> str:
    return "poisson" if LIGHT_YIELD * (bins_row[3] + bins_row[4]) <= response.POISSON_LIMIT else "gaussian"


def statistics_of(bins: list, scale: float, replicas) -> dict:
    """Per regime: mean and variance of d1 and d2 over draws, and the mean of mu and of v."""
    sums: dict = {}
    for row in bins:
        mean, variance = response.photon_moments(LIGHT_YIELD, scale, row[3], row[4], row[5])
        cell = sums.setdefault(regime(row), {"count": 0, "d1": [], "d2": [], "mu": [], "v": []})
        for replica in replicas:
            number = draw(row, scale, replica)
            cell["count"] += 1
            cell["d1"].append(number - mean)
            cell["d2"].append((number - mean) ** 2 - variance)
            cell["mu"].append(mean)
            cell["v"].append(variance)
    out = {}
    for name, cell in sums.items():
        count = cell["count"]
        means = {key: math.fsum(cell[key]) / count for key in ("d1", "d2", "mu", "v")}
        spreads = {key: math.sqrt(math.fsum((value - means[key]) ** 2 for value in cell[key]) / (count - 1)) for key in ("d1", "d2")}
        out[name] = {"count": count, **means, "sd_d1": spreads["d1"], "sd_d2": spreads["d2"]}
    return out


def normal_quantile(probability: float) -> float:
    low, high = -10.0, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        if 0.5 * math.erfc(-middle / math.sqrt(2)) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def trial(folder: Path, target: Path) -> dict:
    bins = read_bins(folder)
    rows = {}
    for scale in SCALES:
        for name, cell in statistics_of(bins, scale, TRIAL_REPLICAS).items():
            rows[f"r={scale}/{name}"] = cell
    count = 2 * len(rows)
    power = JOINT_POWER ** (1 / count)
    z = ALPHA_Z + normal_quantile((1 + power) / 2)
    needed = {}
    for key, cell in rows.items():
        needed[f"{key}/mean"] = (z * cell["sd_d1"] / (MEAN_MARGIN * cell["mu"])) ** 2
        needed[f"{key}/variance"] = (z * cell["sd_d2"] / (VARIANCE_MARGIN * cell["v"])) ** 2
    per_bin = {name: sum(regime(row) == name for row in bins) for name in ("poisson", "gaussian")}
    replicas = max(math.ceil(value / per_bin[key.split("/")[1]]) for key, value in needed.items())
    design = {"K": count, "power_each": power, "z": z, "bins": per_bin, "draws_needed": {key: math.ceil(value) for key, value in needed.items()}, "replicas_needed": replicas, "trial_replicas": len(TRIAL_REPLICAS)}
    target.write_text(json.dumps(design, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", **design}


def equivalence(folder: Path, design: dict, replicas: int) -> dict:
    bins = read_bins(folder)
    chosen = range(TEST_FIRST_REPLICA, TEST_FIRST_REPLICA + replicas)
    rows = []
    for scale in SCALES:
        for name, cell in statistics_of(bins, scale, chosen).items():
            for moment, center, spread, reference, margin in (("mean", cell["d1"], cell["sd_d1"], cell["mu"], MEAN_MARGIN), ("variance", cell["d2"], cell["sd_d2"], cell["v"], VARIANCE_MARGIN)):
                relative, error = center / reference, spread / math.sqrt(cell["count"]) / reference
                rows.append({"test": f"r={scale}/{name}/{moment}", "relative": relative, "error": error, "margin": margin, "equivalent": abs(relative) + ALPHA_Z * error <= margin, "draws": cell["count"]})
    passed = len(rows) == design["K"] and all(row["equivalent"] for row in rows)
    return {"status": "ok" if passed else "failed", "K": len(rows), "replicas": replicas, "rows": rows}


def determinism(folder: Path) -> dict:
    bins = read_bins(folder)
    whole = {row[:3]: draw(row, 1.0, 5) for row in bins}
    shuffled = list(bins)
    random.Random(1).shuffle(shuffled)
    again = {row[:3]: draw(row, 1.0, 5) for row in shuffled}
    results = {"shuffled_equal": whole == again}
    for chunks in (3, 7, 16):
        merged: dict = {}
        for at in range(chunks):
            merged.update({row[:3]: draw(row, 1.0, 5) for row in bins[at::chunks]})
        results[f"chunks_{chunks}_equal"] = merged == whole
    partial = [rng.partial_sums([float(value) for value in list(whole.values())[at::5]]) for at in range(5)]
    results["merged_sum_equal"] = rng.merge_partial_sums(partial) == math.fsum(float(value) for value in whole.values())
    wrong = {row[:3]: response.bin_photons(rng.SubStream(rng.volume_key(20261107, "gate7-1.0", 5), row[0], row[1], at), LIGHT_YIELD, 1.0, row[3], row[4], row[5]) for at, row in enumerate(shuffled)}
    results["control_position_in_the_counter_detected"] = wrong != whole
    return {"status": "ok" if all(results.values()) else "failed", "bins": len(bins), **results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "determinism", "trial", "equivalence"))
    parser.add_argument("folder", type=Path)
    parser.add_argument("--program", type=Path)
    parser.add_argument("--events", type=int, default=2000)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--design", type=Path)
    parser.add_argument("--replicas", type=int)
    args = parser.parse_args()
    if args.command == "run":
        return run(args.folder, args.program, args.events)
    if args.command == "determinism":
        result = determinism(args.folder)
    elif args.command == "trial":
        result = trial(args.folder, args.out)
    else:
        result = equivalence(args.folder, json.loads(args.design.read_text(encoding="utf-8")), args.replicas)
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

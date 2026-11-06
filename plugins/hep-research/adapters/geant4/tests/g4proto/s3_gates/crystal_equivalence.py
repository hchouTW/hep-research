#!/usr/bin/env python3
"""S3 gate 3: equivalence of the mean deposit per crystal between g4sim and zdcsim (g4sim plan, Section 19.2).

  reduce-zdcsim EVENTS.root N_CRYSTALS OUT.npy    per-event deposits per crystal; needs uproot
  reduce-g4sim RUN_FOLDER N_CRYSTALS OUT.npy      the same from a g4sim run
  derive REFERENCE.npy... --other OTHER.npy... --beam MEV --out TRIAL.json   the trial: grouping, K and the events needed
  test TRIAL.json --reference ... --other ...     the TOST of each observable, from independent samples

Each crystal whose reference mean is at least 1% of the beam energy is an observable; the rest are summed into one. Log ratio of means, delta-method variance, |log ratio| <= ln 1.005,
TOST at alpha = 0.05, passing only if all K pass; power 0.9^(1/K) per test at a true difference of 0. Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

MARGIN = math.log(1.005)
ALPHA = 0.05
JOINT_POWER = 0.9
OWN_FRACTION = 0.01
PACKED_WIDTH = 3


def normal_quantile(probability: float) -> float:
    low, high = -10.0, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        if 0.5 * math.erfc(-middle / math.sqrt(2)) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def reduce_zdcsim(path: Path, count: int) -> np.ndarray:
    import uproot
    with uproot.open(path) as handle:
        tree = handle["events"]
        cells, deposits = tree["cell"].array(library="np"), tree["edep"].array(library="np")
    out = np.zeros((len(cells), count * count))
    for row, (cell, deposit) in enumerate(zip(cells, deposits)):
        keep = cell < count * count
        np.add.at(out[row], cell[keep], deposit[keep])
    return out


def crystal_of(volume: int, stride: int, count: int) -> int:
    """The crystal's id iy * n + ix from a volume ID: the wrapper's packed copy number sits at the first level."""
    copy = (volume // stride) - 1 if stride > 1 else volume - 1
    return (copy >> PACKED_WIDTH) * count + (copy & ((1 << PACKED_WIDTH) - 1))


def reduce_g4sim(folder: Path, count: int) -> np.ndarray:
    strides = json.loads((folder / "column_map.json").read_text(encoding="utf-8"))["volume_id"]["strides"]
    events = sum(1 for _ in (folder / "primaries.csv").open(encoding="utf-8"))
    out = np.zeros((events, count * count))
    first = None
    with (folder / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row[2] == "-1":
                continue
            event = int(row[0])
            first = event if first is None else min(first, event)
            volume = int(row[2])
            # level 0 is the wrapper, level 1 the crystal inside it, with copy 0: its term is one stride of that level
            out[event % events, crystal_of(volume - strides[1], strides[0], count)] += float(row[4])
    return out


def observables(matrix: np.ndarray, own: list) -> np.ndarray:
    rest = [at for at in range(matrix.shape[1]) if at not in own]
    return np.column_stack([matrix[:, own], matrix[:, rest].sum(axis=1)])


def load(paths: list) -> np.ndarray:
    return np.concatenate([np.load(path) for path in paths])


def derive(reference: np.ndarray, other: np.ndarray, beam: float) -> dict:
    means = reference.mean(axis=0)
    own = [int(at) for at in np.nonzero(means >= OWN_FRACTION * beam)[0]]
    columns = [observables(sample, own) for sample in (reference, other)]
    count = len(own) + 1
    power = JOINT_POWER ** (1 / count)
    z = normal_quantile(1 - ALPHA) + normal_quantile((1 + power) / 2)  # two one-sided tests at a true difference of 0
    variation = [column.std(axis=0, ddof=1) / column.mean(axis=0) for column in columns]
    relative_variance = variation[0] ** 2 + variation[1] ** 2
    needed = z ** 2 * relative_variance / MARGIN ** 2  # each sample, n events: Var(log ratio) = (cv1^2 + cv2^2) / n
    return {"own_crystals": own, "K": count, "power_each": power, "z": z, "events_needed_each": int(math.ceil(needed.max())), "by_observable": needed.tolist(),
            "reference_means_MeV": columns[0].mean(axis=0).tolist(), "other_means_MeV": columns[1].mean(axis=0).tolist(), "relative_sd": variation[0].tolist(), "trial_events": [len(reference), len(other)]}


def equivalence(trial: dict, reference: np.ndarray, other: np.ndarray) -> dict:
    a, b = observables(reference, trial["own_crystals"]), observables(other, trial["own_crystals"])
    critical = normal_quantile(1 - ALPHA)
    rows = []
    for at in range(a.shape[1]):
        mean_a, mean_b = a[:, at].mean(), b[:, at].mean()
        error = math.sqrt(a[:, at].var(ddof=1) / (len(a) * mean_a ** 2) + b[:, at].var(ddof=1) / (len(b) * mean_b ** 2))
        ratio = math.log(mean_b / mean_a)
        rows.append({"observable": trial["own_crystals"][at] if at < len(trial["own_crystals"]) else "peripheral", "log_ratio": ratio, "error": error, "equivalent": abs(ratio) + critical * error <= MARGIN})
    return {"status": "ok" if all(row["equivalent"] for row in rows) else "failed", "margin": MARGIN, "events": [len(a), len(b)], "K": len(rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("reduce-zdcsim", "reduce-g4sim"):
        item = commands.add_parser(name)
        item.add_argument("source", type=Path)
        item.add_argument("count", type=int)
        item.add_argument("out", type=Path)
    item = commands.add_parser("derive")
    item.add_argument("reference", type=Path, nargs="+")
    item.add_argument("--other", type=Path, nargs="+", required=True)
    item.add_argument("--beam", type=float, required=True)
    item.add_argument("--out", type=Path, required=True)
    item = commands.add_parser("test")
    item.add_argument("trial", type=Path)
    item.add_argument("--reference", type=Path, nargs="+", required=True)
    item.add_argument("--other", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    if args.command.startswith("reduce"):
        matrix = reduce_zdcsim(args.source, args.count) if args.command == "reduce-zdcsim" else reduce_g4sim(args.source, args.count)
        np.save(args.out, matrix)
        print(json.dumps({"status": "ok", "events": len(matrix), "mean_total_MeV": float(matrix.sum(axis=1).mean())}))
        return 0
    if args.command == "derive":
        result = derive(load(args.reference), load(args.other), args.beam)
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", **{key: result[key] for key in ("K", "own_crystals", "events_needed_each", "trial_events")}}))
        return 0
    result = equivalence(json.loads(args.trial.read_text(encoding="utf-8")), load(args.reference), load(args.other))
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

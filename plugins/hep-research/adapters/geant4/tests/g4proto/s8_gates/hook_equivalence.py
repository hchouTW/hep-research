#!/usr/bin/env python3
"""S8 gate 3: the fast-simulation hook (g4sim plan, Section 19.2 S8, addendum 11.1).

Part 1, the idle hook: on S3 gate 3's ZDC prototype v2, its crystal template as the fast_sim_envelope, the same seeds with no hook and with
the idle model on e-, e+ and gamma. Observables grouped as in S3 gate 3: each crystal whose no-hook mean is at least 1% of the beam is its
own, the rest are summed into one. Paired TOST of each log ratio of means, |ln(mean_hook / mean_none)| <= ln 1.005, at alpha = 0.05, with
the delta-method variance of the per-event differences w_i = y_i / mean_y - x_i / mean_x, which keeps the pairing; passing only if all K
pass. Power at a true difference of 0, each test 0.9^(1/K) (Sidak), joint 0.9: events n = (z_0.95 + z_((1+p)/2))^2 Var(w) / margin^2 from an
independent trial (Section 18), with a floor (FLOOR_EVENTS) registered with it.

Part 2, the closure: an envelope of PbWO4 alone in vacuum, the absorb model on e-, e+, gamma and proton beams: every event's deposit inside the
envelope equals the incident kinetic energy within the closure tolerance of Section 9.1, n 2^-52 sum|x_i| with n = 1 (the model books one
deposit), and the conservation identity holds.

  specs ZDC_SPEC_FOLDER OUT          the detector, request and run cards: none, idle, and the closure set
  derive NONE_RUN IDLE_RUN --beam MEV --out TRIAL.json        the trial: grouping, K, Var(w), events needed
  test TRIAL.json NONE_RUN IDLE_RUN                           the registered test
  closure RUN [RUN...]                                         the closure of each absorb run
Prints JSON with a status key. Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import sys
from pathlib import Path

MARGIN = math.log(1.005)
ALPHA = 0.05
JOINT_POWER = 0.9
OWN_FRACTION = 0.01
FLOOR_EVENTS = 2000  # at least the histories GB19 saw change (about 1%) many times over
HOOK_PARTICLES = ["e-", "e+", "gamma"]
CLOSURE_BEAMS = (("e-", "1000"), ("e+", "1000"), ("gamma", "1000"), ("proton", "5000"))


def normal_quantile(probability: float) -> float:
    """The standard normal quantile by bisection of the error function: exact enough for a design, and no library."""
    low, high = -12.0, 12.0
    for _ in range(200):
        middle = (low + high) / 2
        if 0.5 * math.erfc(-middle / math.sqrt(2)) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def specs(source: Path, out: Path) -> dict:
    detector = json.loads((source / "detector.json").read_text(encoding="utf-8"))
    request = json.loads((source / "request.json").read_text(encoding="utf-8"))
    run = json.loads((source / "run.json").read_text(encoding="utf-8"))
    hooked = copy.deepcopy(detector)
    hooked["physics_requirements"] = [*detector.get("physics_requirements", []), {"need": "fast_sim_envelope", "select": {"tags": ["crystal"]}}]
    out.mkdir(parents=True, exist_ok=True)
    idle = copy.deepcopy(run)
    idle["physics"]["fast_sim"] = {"model": "idle", "particles": HOOK_PARTICLES}
    files = {"detector-none.json": detector, "detector-hook.json": hooked, "request.json": request, "run-none.json": run, "run-idle.json": idle}
    closure = {"schema": "detector-spec/1", "params": {},
               "templates": {"block": {"solid": {"box": {"size_mm": ["400", "400", "400"]}}, "material": "G4_PbWO4", "region": "block", "tags": ["block"]}},
               "world": {"material": "G4_Galactic", "size_mm": ["2000", "2000", "2000"], "children": [{"template": "block", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
               "physics_requirements": [{"need": "fast_sim_envelope", "select": {"tags": ["block"]}}]}
    files["closure-detector.json"] = closure
    files["closure-run.json"] = {**copy.deepcopy(run), "physics": {**run["physics"], "fast_sim": {"model": "absorb", "particles": ["e-", "e+", "gamma", "proton"]}}}
    for particle, energy in CLOSURE_BEAMS:
        files[f"closure-request-{particle}.json"] = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": particle, "energy": {"mono": {"energy_MeV": energy}},
                                                     "position": {"box_uniform": {"frame": "world", "centre_mm": ["0", "0", "-600"], "size_mm": ["20", "20", "0.1"]}},
                                                     "direction": {"fixed": {"frame": "world", "vector": ["0", "0", "1"]}}},
                                                     "scorers": [{"name": "block", "readout": "none", "select": {"tags": ["block"]}, "quantity": "edep"}]}
    for name, document in files.items():
        (out / name).write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", "written": sorted(files)}


def per_event(folder: Path) -> tuple[list, dict]:
    """[(event)] in order and {volume: [deposit per event]} of the crystal scorer, from cells.csv (volume -1 is the scorer's total)."""
    events = [int(row[0]) for row in csv.reader((folder / "primaries.csv").open(encoding="utf-8", newline=""))]
    index = {event: at for at, event in enumerate(sorted(set(events)))}
    table: dict = {}
    for row in csv.reader((folder / "cells.csv").open(encoding="utf-8", newline="")):
        if row[2] == "-1":
            continue
        column = table.setdefault(int(row[2]), [0.0] * len(index))
        column[index[int(row[0])]] += float(row[4])
    return sorted(index), table


def observables(table: dict, own: list, count: int) -> list:
    rest = [0.0] * count
    for volume, column in table.items():
        if volume not in own:
            rest = [a + b for a, b in zip(rest, column)]
    return [table.get(volume, [0.0] * count) for volume in own] + [rest]


def paired(x: list, y: list) -> tuple[float, float, float]:
    """(log ratio, its standard error, Var(w) per event) of mean y over mean x, paired by event."""
    n = len(x)
    mean_x, mean_y = sum(x) / n, sum(y) / n
    w = [b / mean_y - a / mean_x for a, b in zip(x, y)]
    mean_w = sum(w) / n
    variance = sum((value - mean_w) ** 2 for value in w) / (n - 1)
    return math.log(mean_y / mean_x), math.sqrt(variance / n), variance


def load_pair(none_run: Path, idle_run: Path) -> tuple:
    events_x, x = per_event(none_run)
    events_y, y = per_event(idle_run)
    if events_x != events_y:
        raise ValueError("the two runs do not hold the same events: the test is paired by event")
    return len(events_x), x, y


def derive(none_run: Path, idle_run: Path, beam: float) -> dict:
    count, x, y = load_pair(none_run, idle_run)
    means = {volume: sum(column) / count for volume, column in x.items()}
    own = sorted(volume for volume, mean in means.items() if mean >= OWN_FRACTION * beam)
    k = len(own) + 1
    power = JOINT_POWER ** (1 / k)
    z = normal_quantile(1 - ALPHA) + normal_quantile((1 + power) / 2)
    rows = []
    for at, (a, b) in enumerate(zip(observables(x, own, count), observables(y, own, count))):
        ratio, error, variance = paired(a, b)
        rows.append({"observable": own[at] if at < len(own) else "peripheral", "mean_none_MeV": sum(a) / count, "log_ratio": ratio, "var_w": variance,
                     "events_needed": z ** 2 * variance / MARGIN ** 2, "changed_events": sum(p != q for p, q in zip(a, b))})
    needed = max(row["events_needed"] for row in rows)
    return {"status": "ok", "trial_events": count, "beam_MeV": beam, "own_volumes": own, "K": k, "power_each": power, "z": z, "margin": MARGIN,
            "events_needed": math.ceil(needed), "floor_events": FLOOR_EVENTS, "events_to_register": max(math.ceil(needed), FLOOR_EVENTS), "rows": rows}


def test(trial: dict, none_run: Path, idle_run: Path) -> dict:
    count, x, y = load_pair(none_run, idle_run)
    critical = normal_quantile(1 - ALPHA)
    rows = []
    for at, (a, b) in enumerate(zip(observables(x, trial["own_volumes"], count), observables(y, trial["own_volumes"], count))):
        ratio, error, _ = paired(a, b)
        rows.append({"observable": trial["own_volumes"][at] if at < len(trial["own_volumes"]) else "peripheral", "log_ratio": ratio, "error": error,
                     "bound": abs(ratio) + critical * error, "equivalent": abs(ratio) + critical * error <= MARGIN, "changed_events": sum(p != q for p, q in zip(a, b))})
    holds = all(row["equivalent"] for row in rows) and count >= trial["events_to_register"]
    return {"status": "ok" if holds else "failed", "events": count, "registered_events": trial["events_to_register"], "K": len(rows), "margin": MARGIN, "rows": rows}


def closure(runs: list) -> dict:
    rows = []
    for folder in runs:
        request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        energy = float(request["source"]["energy"]["mono"]["energy_MeV"])
        _, table = per_event(folder)
        deposits = [sum(values) for values in zip(*table.values())] if table else []
        events = sum(1 for _ in (folder / "primaries.csv").open(encoding="utf-8"))
        tolerance = 2.0 ** -52 * energy  # Section 9.1 with n = 1: the model books one deposit
        worst = max((abs(value - energy) for value in deposits), default=math.inf)
        conservation = list(csv.DictReader((folder / "conservation.csv").open(encoding="utf-8", newline="")))
        residual = max(abs(float(row["residual_MeV"])) for row in conservation)
        holds = len(deposits) == events and worst <= tolerance and residual <= 1e-6
        rows.append({"run": folder.name, "particle": request["source"]["particle"], "energy_MeV": energy, "events": events, "scored_events": len(deposits),
                     "largest_deviation_MeV": worst, "tolerance_MeV": tolerance, "largest_conservation_residual_MeV": residual, "holds": holds})
    return {"status": "ok" if rows and all(row["holds"] for row in rows) else "failed", "rows": rows}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("specs")
    one.add_argument("source", type=Path)
    one.add_argument("out", type=Path)
    two = sub.add_parser("derive")
    two.add_argument("none_run", type=Path)
    two.add_argument("idle_run", type=Path)
    two.add_argument("--beam", type=float, required=True)
    two.add_argument("--out", type=Path, required=True)
    three = sub.add_parser("test")
    three.add_argument("trial", type=Path)
    three.add_argument("none_run", type=Path)
    three.add_argument("idle_run", type=Path)
    four = sub.add_parser("closure")
    four.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args(argv)
    try:
        if args.command == "specs":
            result = specs(args.source, args.out)
        elif args.command == "derive":
            result = derive(args.none_run, args.idle_run, args.beam)
            args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        elif args.command == "test":
            result = test(json.loads(args.trial.read_text(encoding="utf-8")), args.none_run, args.idle_run)
        else:
            result = closure(args.runs)
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

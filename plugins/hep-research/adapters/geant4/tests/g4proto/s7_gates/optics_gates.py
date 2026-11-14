#!/usr/bin/env python3
"""S7 gates 1 and 2 (g4sim plan, Section 19.2): the optical escape fraction of a simple block, and the Cherenkov angle.

  setup FOLDER                         the specifications, requests and trial run cards of both gates
  escape RUN_FOLDER --index N          gate 1: the escape fraction against 3 (1 - sqrt(1 - 1/n^2)), TOST at +-1% relative
  cherenkov RUN_FOLDER --index N --kinetic-mev T   gate 2: the mean Cherenkov angle against arccos(1/(n beta)), TOST at +-0.5 mrad
  derive escape|cherenkov RUN_FOLDER ...   the events a judged run needs at power 0.9, from the analytic or the trial variance

Gate 1. Isotropic photons born uniformly in a polished cube of index n > sqrt(2), with no absorption, in an optical vacuum: a photon
whose direction lies within the escape cone of a face (half angle arcsin(1/n)) leaves through it, after Fresnel reflections, which
keep it within the cone of the opposite face; any other photon is trapped by total internal reflection forever, because reflection
in a cube only permutes the signs of its direction cosines. For n > sqrt(2) the six cones do not overlap, so the escape fraction is
6 (1 - cos theta_c) / 2. A time cut ends trapped photons (KillProcess); escaping ones reach the world's boundary, where Geant4
absorbs them (no refractive index there). The estimate is binomial.

Gate 2. A muon through a radiator of constant index n, the sensor inside the same medium, so a detected photon keeps the direction it
was emitted in; photons the muon itself emitted (parent track 1) are compared with arccos(1/(n beta)), beta from the kinetic energy and
core/constants' muon mass. Photons of one event share the muon's scattering, so the mean is taken per event and the standard error over
events. TOST at alpha = 0.05; power 0.9 at a true difference of 0 needs margin / se >= z_0.95 + z_0.95. Prints JSON with a status key.
Exit 0 pass, 1 fail, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.constants import physical  # noqa: E402

ALPHA = 0.05
POWER = 0.9
ESCAPE_MARGIN_RELATIVE = 0.01
ANGLE_MARGIN_RAD = 0.5e-3
BLOCK_INDEX = "1.5"
RADIATOR_INDEX = "1.05"
MUON_KINETIC_MEV = "3000"
TIME_CUT_NS = "50"
E2 = ["2.5", "3.5"]


def z(probability: float) -> float:
    return statistics.NormalDist().inv_cdf(probability)


def needed_ratio() -> float:
    """margin / se at which TOST has power POWER at a true difference of 0 (K = 1)."""
    return z(1 - ALPHA) + z(1 - (1 - POWER) / 2)


def tost(estimate: float, reference: float, se: float, margin: float) -> dict:
    difference = estimate - reference
    lower = (difference + margin) / se
    upper = (margin - difference) / se
    p_value = max(1 - statistics.NormalDist().cdf(lower), 1 - statistics.NormalDist().cdf(upper))
    return {"estimate": estimate, "reference": reference, "difference": difference, "se": se, "margin": margin, "p_value": p_value,
            "equivalent": p_value < ALPHA, "margin_over_se": margin / se, "needed_margin_over_se": needed_ratio()}


def escape_reference(index: float) -> float:
    if index <= math.sqrt(2):
        raise ValueError("the closed form needs n > sqrt(2), where the escape cones do not overlap")
    return 3 * (1 - math.sqrt(1 - 1 / index ** 2))


def cherenkov_reference(index: float, kinetic_mev: float) -> float:
    mass = float(physical.constant("muon_mass_energy", "MeV").value)
    gamma = 1 + kinetic_mev / mass
    beta = math.sqrt(1 - 1 / gamma ** 2)
    return math.acos(1 / (index * beta))


def _optical(base: str, index: str) -> dict:
    return {"base": base, "optical": {"rindex": {"energy_eV": E2, "value": [index, index]}}}


def _card(events: int, threads: int = 4, time_cut: str | None = None) -> dict:
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}, "extra_constructors": ["G4OpticalPhysics"]},
            "accounting": "separated", "run": {"events": events, "first_event": 0, "logical_run_seed": 20261108, "mode": "mt", "seeding": "per-event", "threads": threads}}
    if time_cut:
        card["kill_policy"] = {"time_cut_ns": time_cut}
    return card


def setup(folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    escape = {"schema": "detector-spec/1", "params": {},
              "materials": {"glass_optical": _optical("G4_GLASS_PLATE", BLOCK_INDEX), "vacuum_optical": _optical("G4_Galactic", "1.0")},
              "templates": {"block": {"solid": {"box": {"size_mm": ["20", "20", "20"]}}, "material": "glass_optical", "tags": ["optical"]},
                            "envelope": {"solid": {"box": {"size_mm": ["200", "200", "200"]}}, "material": "vacuum_optical", "tags": ["optical"],
                                         "children": [{"template": "block", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]}},
              "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "envelope", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
              "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}]}
    escape_request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "opticalphoton", "energy": {"mono": {"energy_MeV": "3e-6"}},
                      "position": {"box_uniform": {"frame": "world", "centre_mm": ["0", "0", "0"], "size_mm": ["20", "20", "20"]}}, "direction": {"isotropic": {}}},
                      "scorers": [{"name": "block_edep", "readout": "none", "select": {"tags": ["optical"]}, "quantity": "edep"}]}
    angle = {"schema": "detector-spec/1", "params": {},
             "materials": {"radiator_optical": _optical("G4_SILICON_DIOXIDE", RADIATOR_INDEX)},
             "templates": {"sensor": {"solid": {"box": {"size_mm": ["400", "400", "1"]}}, "material": "G4_Si", "tags": ["optical", "sensor"]},
                           "radiator": {"solid": {"box": {"size_mm": ["400", "400", "110"]}}, "material": "radiator_optical", "tags": ["optical"],
                                        "children": [{"template": "sensor", "placement": {"single": {"centre_mm": ["0", "0", "54.5"]}}}]}},
             "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "radiator", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
             "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}],
             "optical_surfaces": {"sensor_surface": {"skin": "sensor", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                                                     "reflectivity": {"energy_eV": E2, "value": ["0", "0"]}, "efficiency": {"energy_eV": E2, "value": ["1", "1"]}}}}
    angle_request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "mu-", "energy": {"mono": {"energy_MeV": MUON_KINETIC_MEV}},
                     "position": {"box_uniform": {"frame": "world", "centre_mm": ["0", "0", "-300"], "size_mm": ["0.1", "0.1", "0"]}},
                     "direction": {"fixed": {"frame": "world", "vector": ["0", "0", "1"]}}},
                     "scorers": [{"name": "detected", "readout": "none", "select": {"tags": ["sensor"]}, "quantity": "photon_detected"}]}
    files = {"escape/spec.json": escape, "escape/request.json": escape_request, "escape/trial.json": _card(4000, time_cut=TIME_CUT_NS),
             "cherenkov/spec.json": angle, "cherenkov/request.json": angle_request, "cherenkov/trial.json": _card(20)}
    for name, document in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", "written": sorted(files)}


def _rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def escape_counts(folder: Path) -> tuple[int, int, dict]:
    rows = _rows(folder / "conservation.csv")
    fates = {key: sum(int(row[key]) for row in rows) for key in ("optical_produced", "optical_boundary_absorbed", "optical_killed_scope", "optical_absorbed",
                                                                 "optical_escaped", "optical_other", "optical_detected", "optical_wls")}
    # the time cut's kills have their own column since build 26 (optical_killed_time); before, they were in optical_killed_scope
    fates["optical_killed_time"] = sum(int(row.get("optical_killed_time", 0)) for row in rows)
    return fates["optical_produced"], fates["optical_boundary_absorbed"], fates


def escape(args) -> dict:
    produced, escaped, fates = escape_counts(args.run)
    if fates["optical_absorbed"] or fates["optical_other"] or fates["optical_wls"] or produced != escaped + fates["optical_killed_scope"] + fates["optical_killed_time"]:
        return {"status": "rejected", "message": "a photon ended other than by escaping or by the time cut", "fates": fates}
    reference = escape_reference(args.index)
    fraction = escaped / produced
    result = tost(fraction, reference, math.sqrt(fraction * (1 - fraction) / produced), ESCAPE_MARGIN_RELATIVE * reference)
    return {"status": "ok" if result["equivalent"] else "failed", "photons": produced, "fates": fates, **result}


def event_angles(folder: Path) -> dict:
    by_event: dict = {}
    with (folder / "photons.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if not row or row[0] == "event" or int(row[12]) != 1:
                continue
            by_event.setdefault(int(row[0]), []).append(math.acos(max(-1.0, min(1.0, float(row[11])))))
    return by_event


def cherenkov(args) -> dict:
    by_event = event_angles(args.run)
    means = [statistics.fmean(values) for values in by_event.values()]
    if len(means) < 2:
        return {"status": "rejected", "message": f"{len(means)} event(s) with photons of the muon"}
    reference = cherenkov_reference(args.index, args.kinetic_mev)
    result = tost(statistics.fmean(means), reference, statistics.stdev(means) / math.sqrt(len(means)), ANGLE_MARGIN_RAD)
    return {"status": "ok" if result["equivalent"] else "failed", "events": len(means), "photons": sum(len(v) for v in by_event.values()), **result}


def derive(args) -> dict:
    ratio = needed_ratio()
    if args.gate == "escape":
        p = escape_reference(args.index)
        events = math.ceil(p * (1 - p) * (ratio / (ESCAPE_MARGIN_RELATIVE * p)) ** 2)
        return {"status": "ok", "gate": 1, "reference": p, "photons_needed": events, "basis": "binomial variance at the analytic fraction"}
    means = [statistics.fmean(values) for values in event_angles(args.run).values()]
    sd = statistics.stdev(means)
    return {"status": "ok", "gate": 2, "trial_events": len(means), "sd_of_event_means_rad": sd, "events_needed": math.ceil((ratio * sd / ANGLE_MARGIN_RAD) ** 2),
            "basis": "the trial's spread of event means"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup").add_argument("folder", type=Path)
    for name in ("escape", "cherenkov"):
        command = commands.add_parser(name)
        command.add_argument("run", type=Path)
        command.add_argument("--index", type=float, required=True)
        if name == "cherenkov":
            command.add_argument("--kinetic-mev", type=float, required=True)
    deriving = commands.add_parser("derive")
    deriving.add_argument("gate", choices=("escape", "cherenkov"))
    deriving.add_argument("run", type=Path, nargs="?")
    deriving.add_argument("--index", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        result = {"setup": lambda: setup(args.folder), "escape": lambda: escape(args), "cherenkov": lambda: cherenkov(args), "derive": lambda: derive(args)}[args.command]()
    except (OSError, ValueError, KeyError, IndexError) as err:
        result = {"status": "rejected", "message": str(err)}
    print(json.dumps(result, indent=1))
    return {"ok": 0, "failed": 1}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())

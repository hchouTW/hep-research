#!/usr/bin/env python3
"""S7 gate 4 (g4sim plan, Sections 10.4, 19.2): the efficiency-map validation run, full optical tracking against the map's digitization.

  setup FOLDER                                   specification, the mapping and validation requests and run cards
  compare VALIDATION_RUN MAP.json [--replicas R]  the joint TOST of the mean and width of the photoelectron number
  derive VALIDATION_RUN MAP.json [--replicas R]   the validation events a judged run needs, or the mapping photons first

A scintillator bar with a photodetector on one end, one scintillation component (the validation run's condition of Section 10.4), Birks
declared. The validation run tracks every photon (photon_detected gives N_full per event) and scores edep_visible_ly_split in the map's
cartesian bins; the digitization of the same events' bins through the map gives N_map, so the two samples are paired. Statistics: the
relative difference of the means and of the standard deviations, margins +-1% and +-5% (Section 19.2 defaults), alpha = 0.05; joint power
0.9 over K = 2 tests, so 0.9^(1/2) each at a true difference of 0. The standard error adds, to a paired bootstrap over events, the variance
between Dirichlet replicas of the map, which does not shrink with events; if that alone keeps the power below 0.9, the mapping run needs more
photons (the margins are never relaxed). The validation conditions are checked first: physics_check.validation_findings on the run's
effective config, efficiency_map.validation_response_findings and component_findings. Prints JSON with a status key. Exit 0 pass, 1 fail,
2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "adapters/geant4/assets"))

import g4sim_physics_check as physics_check  # noqa: E402
from core.simulation import efficiency_map, response  # noqa: E402

ALPHA = 0.05
JOINT_POWER = 0.9
K = 2
MEAN_MARGIN, WIDTH_MARGIN = 0.01, 0.05
BOOTSTRAP = 200
SEGMENTATION = {"kind": "cartesian_xyz", "width_mm": ["10", "10", "20"]}
E2 = ["2.5", "3.5"]
MATERIAL = "scint_optical"
RUN_SEED = 20261108


def z(probability: float) -> float:
    return statistics.NormalDist().inv_cdf(probability)


def needed_ratio() -> float:
    return z(1 - ALPHA) + z(1 - (1 - JOINT_POWER ** (1 / K)) / 2)


def setup(folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    flat = {"energy_eV": E2, "value": ["1", "1"]}
    spec = {"schema": "detector-spec/1", "params": {},
            "materials": {MATERIAL: {"base": "G4_PLASTIC_SC_VINYLTOLUENE", "ionisation": {"birks_mm_per_MeV": "0.126"},
                                     "optical": {"rindex": {"energy_eV": E2, "value": ["1.58", "1.58"]}, "absorption_length_mm": {"energy_eV": E2, "value": ["2000", "2000"]}},
                                     "scintillation": {"yield_per_MeV": "2000", "resolution_scale": "1", "components": [{"fraction": "1", "spectrum": flat, "rise_ns": "0", "decay_ns": "2.1"}]}},
                          "vacuum_optical": {"base": "G4_Galactic", "optical": {"rindex": {"energy_eV": E2, "value": ["1.0", "1.0"]}}}},
            "templates": {"bar": {"solid": {"box": {"size_mm": ["20", "20", "200"]}}, "material": MATERIAL, "tags": ["optical", "scint"]},
                          "sensor": {"solid": {"box": {"size_mm": ["20", "20", "1"]}}, "material": "G4_Si", "tags": ["optical", "sensor"]},
                          "envelope": {"solid": {"box": {"size_mm": ["400", "400", "400"]}}, "material": "vacuum_optical", "tags": ["optical"],
                                       "children": [{"template": "bar", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}},
                                                    {"template": "sensor", "placement": {"single": {"centre_mm": ["0", "0", "100.5"]}}}]}},
            "world": {"material": "G4_Galactic", "size_mm": ["1000", "1000", "1000"], "children": [{"template": "envelope", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
            "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}],
            "optical_surfaces": {"photocathode": {"skin": "sensor", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                                                  "reflectivity": {"energy_eV": E2, "value": ["0", "0"]}, "efficiency": {"energy_eV": E2, "value": ["0.3", "0.3"]}}}}
    validation = {"schema": "simulation-request/1", "birks_active": True,
                  "source": {"density": "analytic", "particle": "mu-", "energy": {"mono": {"energy_MeV": "1000"}},
                             "position": {"box_uniform": {"frame": "world", "centre_mm": ["-150", "0", "0"], "size_mm": ["0", "16", "180"]}},
                             "direction": {"fixed": {"frame": "world", "vector": ["1", "0", "0"]}}},
                  "scorers": [{"name": "pe", "readout": "none", "select": {"tags": ["sensor"]}, "quantity": "photon_detected"},
                              {"name": "split", "readout": "none", "select": {"tags": ["scint"]}, "quantity": "edep_visible_ly_split",
                               "segmentation": {"cartesian_xyz": {"width_mm": SEGMENTATION["width_mm"]}}, "split": "midpoint"}]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}, "extra_constructors": ["G4OpticalPhysics"]},
            "accounting": "separated", "run": {"events": 200, "first_event": 0, "logical_run_seed": RUN_SEED, "mode": "mt", "seeding": "per-event", "threads": 8}}
    mapping = json.loads(json.dumps(card))
    mapping["run"]["events"] = 400000
    for name, document in (("spec.json", spec), ("validation-request.json", validation), ("validation-trial.json", card), ("mapping-trial.json", mapping),
                           ("segmentation.json", SEGMENTATION)):
        (folder / name).write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", "folder": str(folder), "next": "g4sim_efficiency_map.py plan --template bar --material scint_optical --scorer pe --select '{\"tags\": [\"sensor\"]}'"}


def read_run(folder: Path) -> tuple[dict, dict]:
    """N_full per event, and the split scorer's bins per event and volume: {bin: (E^L, E^S, n^L)}."""
    full: dict = {}
    bins: dict = {}
    with (folder / "cells.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if not row or row[0] == "event" or row[2] == "-1":
                continue
            event = int(row[0])
            if row[1] == "pe":
                full[event] = full.get(event, 0) + round(float(row[4]))
            elif row[1] == "split":
                cell = bins.setdefault(event, {}).setdefault(int(row[2]), {}).setdefault(int(row[3]) // 2, [0.0, 0.0, 0])
                if int(row[3]) % 2 == 0:
                    cell[0] += float(row[4])
                    cell[2] += int(row[5])
                else:
                    cell[1] += float(row[4])
    primaries = [int(row[0]) for row in csv.reader((folder / "primaries.csv").open(encoding="utf-8")) if row and row[0] != "event"]
    return {event: full.get(event, 0) for event in primaries}, bins


def digitize(bins: dict, events: list, document: dict, replica: int, material: dict) -> list:
    pipeline = {"schema": "response-pipeline/1", "run_seed": RUN_SEED, "replica": replica, "stages": []}
    stage = {"name": "scintillation", "kind": "scintillation", "parameters": {
        "light_yield_per_MeV": {"value": float(material["scintillation"]["yield_per_MeV"]), "source_of_facts": "the material"},
        "resolution_scale": {"value": float(material["scintillation"]["resolution_scale"]), "source_of_facts": "the material"}}}
    out = []
    for event in events:
        total = 0
        for volume, rows in bins.get(event, {}).items():
            channels = response.scintillation_event(pipeline, stage, event, volume, {b: tuple(v) for b, v in rows.items()}, document)
            total += sum(channels.values())
        out.append(total)
    return out


def relative(full: list, mapped: list) -> tuple[float, float]:
    return statistics.fmean(mapped) / statistics.fmean(full) - 1, statistics.stdev(mapped) / statistics.stdev(full) - 1


def tost(difference: float, se: float, margin: float) -> dict:
    p_value = max(1 - statistics.NormalDist().cdf((difference + margin) / se), 1 - statistics.NormalDist().cdf((margin - difference) / se))
    return {"difference": difference, "se": se, "margin": margin, "p_value": p_value, "equivalent": p_value < ALPHA, "margin_over_se": margin / se}


def analysis(run: Path, map_path: Path, replicas: int) -> dict:
    document = json.loads(map_path.read_text(encoding="utf-8"))
    ir = json.loads((run / "ir.json").read_text(encoding="utf-8"))
    material = ir["physical"]["materials"][MATERIAL]
    effective = json.loads((run / "effective-em.json").read_text(encoding="utf-8"))
    card = json.loads((run / "run.json").read_text(encoding="utf-8"))
    stage = {"parameters": {"light_yield_per_MeV": {"value": float(material["scintillation"]["yield_per_MeV"])}}}
    findings = physics_check.validation_findings(card, ir["physical"]["materials"], MATERIAL, effective, float(material["scintillation"]["resolution_scale"]))
    findings += efficiency_map.validation_response_findings(stage, material) + efficiency_map.component_findings(material, {1: document})
    if findings:
        return {"status": "rejected", "findings": findings}
    full, bins = read_run(run)
    events = sorted(full)
    n_full = [full[event] for event in events]
    nominal = digitize(bins, events, document, 0, material)
    mean_rel, width_rel = relative(n_full, nominal)
    draw = random.Random(RUN_SEED)
    boot = []
    for _ in range(BOOTSTRAP):
        picks = [draw.randrange(len(events)) for _ in events]
        boot.append(relative([n_full[i] for i in picks], [nominal[i] for i in picks]))
    se_stat = [statistics.stdev(item[k] for item in boot) for k in (0, 1)]
    by_replica = [relative(n_full, digitize(bins, events, document, replica, material)) for replica in efficiency_map.replicas(document, replicas)]
    se_map = [statistics.stdev(item[k] for item in by_replica) for k in (0, 1)]
    return {"events": len(events), "mean_full": statistics.fmean(n_full), "mean_map": statistics.fmean(nominal), "sd_full": statistics.stdev(n_full),
            "sd_map": statistics.stdev(nominal), "relative": [mean_rel, width_rel], "se_stat": se_stat, "se_map": se_map}


def compare(args) -> dict:
    found = analysis(args.run, args.map, args.replicas)
    if "status" in found:
        return found
    tests = [tost(found["relative"][k], math.hypot(found["se_stat"][k], found["se_map"][k]), margin) for k, margin in enumerate((MEAN_MARGIN, WIDTH_MARGIN))]
    passed = all(item["equivalent"] for item in tests)
    return {"status": "ok" if passed else "failed", **found, "mean_test": tests[0], "width_test": tests[1], "needed_margin_over_se": needed_ratio()}


def derive(args) -> dict:
    found = analysis(args.run, args.map, args.replicas)
    if "status" in found:
        return found
    ratio = needed_ratio()
    plan = {}
    for k, (name, margin) in enumerate((("mean", MEAN_MARGIN), ("width", WIDTH_MARGIN))):
        allowed = (margin / ratio) ** 2 - found["se_map"][k] ** 2
        if allowed <= 0:
            plan[name] = {"map_limited": True, "se_map": found["se_map"][k], "note": "the map's own error keeps the power below 0.9: raise the mapping photons"}
        else:
            plan[name] = {"map_limited": False, "events_needed": math.ceil(found["events"] * found["se_stat"][k] ** 2 / allowed)}
    return {"status": "ok", **found, "plan": plan, "needed_margin_over_se": ratio}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup").add_argument("folder", type=Path)
    for name in ("compare", "derive"):
        command = commands.add_parser(name)
        command.add_argument("run", type=Path)
        command.add_argument("map", type=Path)
        command.add_argument("--replicas", type=int, default=efficiency_map.MINIMUM_REPLICAS)
    args = parser.parse_args(argv)
    try:
        result = setup(args.folder) if args.command == "setup" else compare(args) if args.command == "compare" else derive(args)
    except (OSError, ValueError, KeyError, efficiency_map.MapError, response.ResponseError) as err:
        result = {"status": "rejected", "message": str(err)}
    print(json.dumps(result, indent=1))
    return {"ok": 0, "failed": 1}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Energy conservation in `separated` mode (g4sim plan, Section 8.9): S2's checks, statistics and order on new-specification runs, with killed energy as the term switched off.

Usage: separated_conservation.py run CONFIG STAGE --spec-folder DIR --program PATH --work DIR --events N [--control NAME] [--threads T]
       separated_conservation.py derive-events|absolute|derive-relative|relative|neutron CONFIG --work DIR
From the plugin root, in an activated Geant4 environment. Prints JSON with a status key. Exit 0 ok, 1 a check failed or the design is invalid, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "conservation"))
sys.path.insert(0, str(HERE.parent / "reacquire"))

import conservation as base  # noqa: E402

DRIVER = HERE.parents[2] / "assets/g4sim_run.py"
EM_LIST = {"em_constructor": "G4EmStandardPhysics_option4", "cuts_mm": {"default": "0.7"}}
HADRONIC_LIST = {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}
CONFIGS = {"em": {"particle": "e-", "energy_MeV": "1000", "physics": EM_LIST, "kill_MeV": "1", "limits": base.EM},
           "hadronic-99": {"particle": "proton", "energy_MeV": "99000", "physics": HADRONIC_LIST, "kill_MeV": "1000", "limits": base.HADRONIC},
           "hadronic-1000": {"particle": "proton", "energy_MeV": "1000000", "physics": HADRONIC_LIST, "kill_MeV": "1000", "limits": base.HADRONIC}}
SEED_OFFSET = 940000
base.CONFIGS = CONFIGS
base.SEEDS["neutron-control"] = 616


def run_stage(args) -> dict:
    config = CONFIGS[args.config]
    request = json.loads((args.spec_folder / "request.json").read_text(encoding="utf-8"))
    request["source"]["particle"] = config["particle"]
    request["source"]["energy"] = {"mono": {"energy_MeV": config["energy_MeV"]}}
    request["scorers"] = []
    card = json.loads((args.spec_folder / "run.json").read_text(encoding="utf-8"))
    card["physics"] = config["physics"]
    card["kill_policy"] = {"min_kinetic_energy_MeV": config["kill_MeV"]}
    card["run"].update({"events": args.events, "threads": args.threads, "logical_run_seed": SEED_OFFSET + base.SEEDS[args.stage]})
    folder = args.work / args.config
    work = folder / f"{args.stage}-run"
    shutil.rmtree(work, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{args.stage}.request.json").write_text(json.dumps(request), encoding="utf-8")
    (folder / f"{args.stage}.run.json").write_text(json.dumps(card), encoding="utf-8")
    environment = {**os.environ, **({"G4SIM_ACCOUNTING_CONTROL": args.control} if args.control else {})}
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(args.spec_folder / "detector.json"), "--request", str(folder / f"{args.stage}.request.json"), "--run", str(folder / f"{args.stage}.run.json"),
                           "--program", str(args.program.resolve()), "--work", str(work)], capture_output=True, text=True, check=False, env=environment)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        return {"status": "failed", "run": summary}
    residuals, incident, errors, killed = [], 0.0, 0, 0.0
    with (work / "conservation.csv").open(encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            residuals.append(float(item["residual_MeV"]))
            incident = float(item["incident_MeV"])
            errors += int(item["accounting_errors"])
            killed += float(item["killed_kinetic_process_MeV"])
    (folder / f"{args.stage}.json").write_text(json.dumps({"residual_MeV": residuals, "incident_MeV": incident, "accounting_errors": errors}), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    return {"status": "ok", "events": len(residuals), "incident_MeV": incident, "accounting_errors": errors, "mean_killed_MeV": killed / max(len(residuals), 1)}


def neutron(config: str, work: Path) -> dict:
    """Section 15.1: the neutron's unreleased energy changed to its rest energy must make the residual check of a hadronic run fail."""
    residuals, energy, _ = base.read_stage(work, config, "calibration")
    wrong, _, _ = base.read_stage(work, config, "neutron-control")
    q_max, r_max = base.limits(CONFIGS[config], energy)
    rate = base.detection_rate(wrong, len(residuals), q_max, r_max)
    mean, _ = base.mean_and_deviation(wrong)
    return {"status": "ok" if rate >= base.TARGET else "failed", "detection_rate": rate, "mean_MeV": mean, "r_max_MeV": r_max, "q_max_MeV": q_max}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "derive-events", "absolute", "derive-relative", "relative", "neutron"))
    parser.add_argument("config", choices=tuple(CONFIGS))
    parser.add_argument("stage", nargs="?", choices=tuple(base.SEEDS))
    parser.add_argument("--spec-folder", type=Path)
    parser.add_argument("--program", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int)
    parser.add_argument("--control")
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    actions = {"derive-events": base.derive_events, "absolute": base.absolute, "derive-relative": base.derive_relative, "relative": base.relative, "neutron": neutron}
    result = run_stage(args) if args.command == "run" else actions[args.command](args.config, args.work)
    print(json.dumps(result, indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

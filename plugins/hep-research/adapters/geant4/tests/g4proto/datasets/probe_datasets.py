#!/usr/bin/env python3
"""Which Geant4 datasets a physics list really needs: run a short job with each dataset pointed at an empty folder, and see which runs fail
(Section 22, content of the physics-list table; contracts/rules/geant4_datasets.json).

An empty folder, not an unset variable: an unset one falls back to the installation's own path. A dataset whose absence changes nothing is
"not needed by this run", which is weaker than "not needed": the table adds the sources it was read from.

Usage: probe_datasets.py --baselines DIR --specs FILE --out FILE [--cores N]
From the plugin root, in an activated Geant4 environment. DIR is a baseline.py folder, whose builds are used. Prints JSON with a status key.
Exit 0 ok, 1 the unchanged run failed, 2 bad input.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DATASETS = ("G4NEUTRONHPDATA", "G4LEDATA", "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA", "G4PARTICLEXSDATA", "G4PIIDATA", "G4REALSURFACEDATA",
            "G4SAIDXSDATA", "G4ABLADATA", "G4INCLDATA", "G4ENSDFSTATEDATA", "G4CHANNELINGDATA")
TIME_LIMIT_S = 900
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
CASES = {"FTFP_BERT_EMZ": ("element_sim", "FTFP_BERT_EMZ"), "QGSP_BIC_EMZ": ("element_sim", "QGSP_BIC_EMZ"),
         "FTFP_BERT_EMY": ("element_sim", "FTFP_BERT_EMY"), "FTFP_BERT__SS": ("element_sim", "FTFP_BERT__SS"),
         "G4EmStandardPhysics_option4": ("layered_sim", "G4EmStandardPhysics_option4"),
         "G4EmStandardPhysics_option3": ("layered_sim", "G4EmStandardPhysics_option3"), "G4EmStandardPhysics": ("layered_sim", "G4EmStandardPhysics")}


def failed(text: str) -> bool:
    return "G4Exception-START" in text and "*** Fatal Exception ***" in text


def run_case(executable: Path, spec: dict, folder: Path, missing: str | None, empty: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    document = json.loads(json.dumps(spec))
    document.setdefault("output", {}).update({"csv": str(folder / "events.csv"), "materials": str(folder / "materials.json"),
                                              "datapaths": str(folder / "datapaths.json")})
    (folder / "spec.json").write_text(json.dumps(document), encoding="utf-8")
    environment = dict(os.environ)
    if missing:
        environment[missing] = str(empty)
    try:
        done = subprocess.run([str(executable), "spec.json"], cwd=folder, capture_output=True, text=True, env=environment, check=False,
                              timeout=TIME_LIMIT_S)
    except subprocess.TimeoutExpired:
        return {"exit": None, "fatal": False, "events_sha256": None, "timed_out": True}
    text = done.stdout + done.stderr
    csv = folder / "events.csv"
    return {"exit": done.returncode, "fatal": failed(text), "events_sha256": hashlib.sha256(csv.read_bytes()).hexdigest() if csv.is_file() else None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--specs", type=Path, required=True, help="JSON: {element_sim: spec, layered_sim: spec}, each a proton run")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=24)
    args = parser.parse_args(argv)
    try:
        specs = json.loads(args.specs.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    builds = {"element_sim": args.baselines / "build/d9db638c-element_sim/element_sim", "layered_sim": args.baselines / "build/636213ae-layered_sim/layered_sim"}
    results: dict = {}
    with tempfile.TemporaryDirectory() as scratch, concurrent.futures.ThreadPoolExecutor(max_workers=args.cores) as pool:
        empty = Path(scratch) / "empty"
        empty.mkdir()
        jobs = {}
        for name, (program, value) in CASES.items():
            spec = json.loads(json.dumps(specs[program]))
            spec["physics"]["reference_list" if program == "element_sim" else "em_constructor"] = value
            for missing in (None, *DATASETS):
                folder = Path(scratch) / name / (missing or "unchanged")
                jobs[pool.submit(run_case, builds[program], spec, folder, missing, empty)] = (name, missing or "unchanged")
        for job, (name, missing) in jobs.items():
            results.setdefault(name, {})[missing] = job.result()
    table = {}
    broken = []
    for name, cases in results.items():
        base = cases["unchanged"]
        if base["exit"] != 0 or base["fatal"]:
            broken.append(name)
        table[name] = {"needed": sorted(k for k, v in cases.items() if k != "unchanged" and (v["exit"] not in (0, None) or v["fatal"])),
                       "output_changed": sorted(k for k, v in cases.items() if k != "unchanged" and v["exit"] == 0
                                                and v["events_sha256"] != base["events_sha256"]),
                       "timed_out": sorted(k for k, v in cases.items() if v.get("timed_out"))}
    args.out.write_text(json.dumps({"table": table, "cases": results}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "failed" if broken else "ok", "broken": broken, "table": table}, indent=1))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

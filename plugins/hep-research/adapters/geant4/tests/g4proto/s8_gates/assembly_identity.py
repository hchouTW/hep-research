#!/usr/bin/env python3
"""S8, recorded with the gates (not a registered gate): placement_impl assembly against ordinary placements where the cells themselves are
rotated, a ring of 12 radial cells tilted 11 degrees and one cell at an arbitrary zyx rotation, in a mother rotated about all three axes. The
volume write-back (probe-v2.json), the scorer cells and the conservation rows must be byte-identical, the same seeds on both sides. S8's
independent read found MakeImprint's rotation up to 2 ulp from the IR's matrix; the builder puts the IR's matrix back (NewBuild.hh).
Usage: assembly_identity.py --program PATH --work DIR [--events N]   In an activated Geant4 environment. Prints JSON with a status key.
Exit 0 identical, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
COMPARED = ("probe-v2.json", "cells.csv", "conservation.csv", "primaries.csv")


def inputs(folder: Path, events: int) -> None:
    cell = {"solid": {"box": {"size_mm": ["20", "40", "30"]}}, "material": "G4_PLASTIC_SC_VINYLTOLUENE", "tags": ["cell"]}
    spec = {"schema": "detector-spec/1", "params": {},
            "templates": {"ring": {"solid": {"box": {"size_mm": ["400", "400", "200"]}}, "material": "G4_AIR", "children": [
                {"template": "cell", "placement": {"ring": {"n": 12, "radius_mm": "150", "phi0_deg": "7.5", "orientation": "radial", "tilt_deg": "11"}}},
                {"template": "cell", "placement": {"single": {"centre_mm": ["0", "0", "60"], "rotation": {"zyx_deg": ["31.7", "-17.3", "53.1"]}}}}]},
                "cell": cell},
            "world": {"material": "G4_Galactic", "size_mm": ["2000", "2000", "2000"],
                      "children": [{"template": "ring", "placement": {"single": {"centre_mm": ["0", "0", "0"], "rotation": {"zyx_deg": ["5", "3", "1"]}}}}]}}
    request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "e-", "energy": {"mono": {"energy_MeV": "300"}},
                                                          "position": {"box_uniform": {"frame": "world", "centre_mm": ["0", "0", "-500"], "size_mm": ["360", "360", "0.1"]}},
                                                          "direction": {"fixed": {"frame": "world", "vector": ["0", "0", "1"]}}},
               "scorers": [{"name": "e", "readout": "none", "select": {"tags": ["cell"]}, "quantity": "edep"}]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": events, "first_event": 0, "logical_run_seed": 83, "mode": "mt", "seeding": "per-event", "threads": 4}}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    (folder / "request.json").write_text(json.dumps(request, indent=1), encoding="utf-8")
    (folder / "run-ordinary.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
    card["placement_impl"] = [{"mother": "ring", "template": "cell", "kind": "assembly"}]
    (folder / "run-assembly.json").write_text(json.dumps(card, indent=1), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int, default=3000)
    args = parser.parse_args(argv)
    inputs(args.work, args.events)
    runs = {}
    for kind in ("ordinary", "assembly"):
        out = args.work / kind
        done = subprocess.run([sys.executable, str(PLUGIN / "adapters/geant4/assets/g4sim_run.py"), "simulate", "--detector", str(args.work / "spec.json"),
                               "--request", str(args.work / "request.json"), "--run", str(args.work / f"run-{kind}.json"), "--program", str(args.program.resolve()),
                               "--work", str(out)], capture_output=True, text=True, timeout=3000, check=False)
        runs[kind] = json.loads(done.stdout) if done.stdout.strip().startswith("{") else {"status": "error"}
        if runs[kind].get("status") != "ok":
            print(json.dumps({"status": "rejected", "message": f"the {kind} run failed", "stderr": done.stderr[-400:]}))
            return 2
    assembled = "G4SIM_ASSEMBLED" in (args.work / "assembly/log.txt").read_text(encoding="utf-8", errors="replace")
    identical = {name: (args.work / "ordinary" / name).read_bytes() == (args.work / "assembly" / name).read_bytes() for name in COMPARED}
    cells = runs["assembly"]["rows"]["cells"]
    holds = assembled and all(identical.values()) and cells > 100
    print(json.dumps({"status": "ok" if holds else "failed", "events": args.events, "assembly_built": assembled, "scorer_rows": cells, "identical": identical}, indent=1))
    return 0 if holds else 1


if __name__ == "__main__":
    sys.exit(main())

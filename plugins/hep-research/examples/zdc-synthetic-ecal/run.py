#!/usr/bin/env python3
"""A synthetic ZDC ECAL prototype as detector-spec/1 (g4sim plan, Section 19.2 S3). Checks the three specifications and writes what they fix, with no Geant4.

The geometry is a 6 x 6 array of wrapped PbWO4 crystals with SiPMs, a board and beam monitors; every number is assumed, and the example is labelled synthetic.
To simulate it: python3 adapters/geant4/assets/g4sim_run.py simulate --detector specs/detector.json --request specs/request.json --run specs/run.json --program PATH --work DIR

Usage: run.py --out FOLDER   Prints JSON with a status key. Exit 0 ok, 1 a specification is refused.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "adapters/geant4/assets"))

import g4sim_physics_check as physics_check  # noqa: E402
import g4sim_simulate as simulate  # noqa: E402

from contracts import geometry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    checked = geometry.check_file(HERE / "specs/detector.json")
    if checked["status"] != "ok":
        print(json.dumps({"status": "rejected", "findings": checked["findings"]}))
        return 1
    request = json.loads((HERE / "specs/request.json").read_text(encoding="utf-8"))
    card = json.loads((HERE / "specs/run.json").read_text(encoding="utf-8"))
    ir = checked["ir"]
    resolved = simulate.resolved_request(request, ir)
    findings = physics_check.card_findings(card, request, materials=ir["physical"]["materials"], selected_materials=simulate.selected_materials(resolved, ir))
    summary = {"status": "rejected" if findings else "ok", "label": "synthetic", "findings": findings, "geometry_id": checked["geometry_id"], "provenance_id": checked["provenance_id"],
               "placements": dict(sorted(Counter(row["template"] for row in ir["physical"]["placements"]).items())), "scorers": [item["name"] for item in resolved["scorers"]], "source_schema": resolved["source"]["schema"]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "geometry_id": summary["geometry_id"]}))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

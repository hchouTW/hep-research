#!/usr/bin/env python3
"""S9 gates 1 and 2: alignment overlays on S7's CMS Phase-1 barrel pixel case (g4sim plan, Section 19.2 S9, Section 17).

Overlays of layer 4, each applied alone to the case's IR: (A) shifts of three modules along their ladder by 1 um and of one ladder by
10 to 20 um; (B) a rotation of one ladder about its centre by 0.001 degree; (C) a shift of zero of one module; (D) A and B together. A
module shift moves that module in every layer-4 ladder: an IR placement belongs to a logical (core/geometry/alignment.py). Gate 1: each overlaid IR's geometry_id differs from the nominal IR's, and
from every other overlay's (two IRs differing only by an overlay have different geometry_id). Gate 2: the diff tool (`g4sim_run.py diff`)
lists as moved exactly the placements an overlay shifts or turns by a non-zero amount, as overlaid exactly the placements it names, and no
placement that only one IR holds. Every overlaid IR passes check-spec, the gap rule and the error bounds included.
Usage: alignment_gate.py --work DIR   Prints JSON with a status key. Exit 0 both gates hold, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
CASE = PLUGIN / "profiles/reference/geometry-cases/cases/cms-phase1-bpix/detector-spec.json"
DEPENDS = ("reference/detector-atlas", "experiments/ams-02", "experiments/eic")
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
CHECK = PLUGIN / "contracts/geometry.py"


def shift(mother: str, template: str, copy_number: int, delta: list, turn: list | None = None) -> dict:
    out = {"mother": mother, "template": template, "copy_number": copy_number, "delta_mm": delta}
    if turn:
        out["rotation"] = {"zyx_deg": turn}
    return out


A = [shift("ladder_l4", "module_l4", 0, ["0.001", "0", "0"]), shift("ladder_l4", "module_l4", 2, ["-0.001", "0", "0"]), shift("ladder_l4", "module_l4", 5, ["0.001", "0", "0"]),
     shift("world", "ladder_l4", 84, ["0.01", "-0.01", "0.02"])]
B = [shift("world", "ladder_l4", 90, ["0", "0", "0"], ["0.001", "0", "0"])]
C = [shift("ladder_l4", "module_l4", 1, ["0", "0", "0"])]
OVERLAYS = {"A": A, "B": B, "C": C, "D": A + B}


def nonzero(item: dict) -> bool:
    return any(value != "0" for value in item["delta_mm"]) or any(value != "0" for value in item.get("rotation", {}).get("zyx_deg", []))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)
    claims = [c["id"] for p in DEPENDS for c in json.loads((PLUGIN / "profiles" / p / "evidence/claims.json").read_text(encoding="utf-8"))]
    (args.work / "claims.json").write_text(json.dumps(claims), encoding="utf-8")

    def checked(overlay: Path | None) -> dict:
        command = [sys.executable, "-B", str(CHECK), str(CASE), "--claims", str(args.work / "claims.json")] + (["--overlay", str(overlay)] if overlay else [])
        done = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
        return json.loads(done.stdout)

    nominal = checked(None)
    if nominal["status"] != "ok":
        print(json.dumps({"status": "rejected", "message": "the nominal case does not pass check-spec", "findings": nominal["findings"][:3]}))
        return 2
    rows, ids = [], {"nominal": nominal["geometry_id"]}
    for name, shifts in OVERLAYS.items():
        path = args.work / f"overlay-{name}.json"
        path.write_text(json.dumps({"schema": "alignment-overlay/1", "description": f"S9 gate overlay {name}", "shifts": shifts}, indent=1), encoding="utf-8")
        result = checked(path)
        done = subprocess.run([sys.executable, "-B", str(DRIVER), "diff", "--detector", str(CASE), "--against", str(CASE), "--against-overlay", str(path), "--claims", str(args.work / "claims.json")],
                              capture_output=True, text=True, timeout=600, check=False)
        listed = json.loads(done.stdout) if done.stdout.strip().startswith("{") else {"status": "error", "stderr": done.stderr[-300:]}
        if listed.get("status") == "rejected" and "claim" in json.dumps(listed):
            listed = {"status": "error", "message": "the diff tool needs the claims"}
        ids[name] = result.get("geometry_id")
        expected_moved = sorted([item["mother"], item["template"], item["copy_number"]] for item in shifts if nonzero(item))
        expected_named = sorted([item["mother"], item["template"], item["copy_number"]] for item in shifts)
        rows.append({"overlay": name, "check_spec": result["status"], "findings": [item["code"] for item in result.get("findings", [])][:3], "geometry_id": ids[name],
                     "diff_status": listed.get("status"), "moved": listed.get("moved"), "expected_moved": expected_moved,
                     "overlaid": (listed.get("overlaid") or {}).get("second"), "expected_overlaid": expected_named,
                     "only_one": (listed.get("only_first"), listed.get("only_second"))})
    distinct = len(set(ids.values())) == len(ids) and None not in ids.values()
    gate1 = distinct and all(row["check_spec"] == "ok" for row in rows)
    gate2 = all(row["diff_status"] == "ok" and row["moved"] == row["expected_moved"] and row["overlaid"] == row["expected_overlaid"] and row["only_one"] == ([], []) for row in rows)
    status = "ok" if gate1 and gate2 else "failed"
    print(json.dumps({"status": status, "gate_1": gate1, "gate_2": gate2, "geometry_ids": ids, "rows": rows}, indent=1))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

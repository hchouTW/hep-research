#!/usr/bin/env python3
"""S6 gates 1 to 3: the reference cases of profiles/reference/geometry-cases against their cited values (g4sim plan, Sections 13, 19.2).

For each case: its tolerances equal the task card's (gate 1 fails if they differ), its detector-spec resolves every value to a claim of a
profile it depends on, each quantity is measured (a geantino's path in each material over the radiation length Geant4 reports, or a count
from the expanded IR) and compared with its reference, and each negative control must fail the same tolerance. A case is marked
validated-in-scope only when its reference is verified independent and its controls are caught (Section 13.3); the comparison is
validation with cited values, never confirmation.

Usage: cases_gate.py --program PATH --work DIR [--write]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
--write records each case's result in its case.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))
CASES = PLUGIN / "profiles/reference/geometry-cases/cases"
CARD = PLUGIN / "docs/dev/geant4-architecture/g4sim-tasks/S6.md"
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
CHECK = PLUGIN / "contracts/geometry.py"
CLAIMS: list = []
DEPENDS = ("reference/detector-atlas", "experiments/ams-02", "experiments/eic")


def card_rows() -> list:
    """The registered rows of the task card's case table: (case, quantity text, reference, tolerance)."""
    text = CARD.read_text(encoding="utf-8")
    start = text.index("| Case | Level | Quantity |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        reference = float(re.match(r"[\d,.]+", cells[3]).group(0).replace(",", ""))
        tolerance = 0.0 if cells[4] == "exact" else float(cells[4].split("%")[0]) / 100
        rows.append({"case": cells[0], "level": cells[1], "reference": reference, "tolerance": tolerance})
    return rows


def claims_file(work: Path) -> Path:
    ids = [c["id"] for p in DEPENDS for c in json.loads((PLUGIN / "profiles" / p / "evidence/claims.json").read_text(encoding="utf-8"))]
    path = work / "claims.json"
    path.write_text(json.dumps(ids), encoding="utf-8")
    return path


def expanded(spec: Path, claims: Path, out: Path) -> dict:
    done = subprocess.run([sys.executable, "-B", str(CHECK), str(spec), "--claims", str(claims), "--out", str(out)], capture_output=True, text=True, timeout=600, check=False)
    report = json.loads(done.stdout)
    if report["status"] != "ok":
        raise RuntimeError(f"{spec}: {report.get('findings')}")
    return json.loads(out.read_text(encoding="utf-8"))


def multiplicity(ir: dict) -> dict:
    """How many volumes of each template the expanded tree holds."""
    placements = ir["physical"]["placements"]
    count = {"world": 1}

    def of(template: str) -> int:
        if template not in count:
            count[template] = sum(of(item["mother"]) for item in placements if item["template"] == template)
        return count[template]
    for item in placements:
        of(item["template"])
    return count


def path_x0(folder: Path, spec: dict, request: dict, program: Path) -> float:
    """sum over materials of the geantino's path / the radiation length Geant4 reports (one event, the path scorer)."""
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated", "run": {"events": 1, "first_event": 0, "logical_run_seed": 20261108, "mode": "mt", "seeding": "per-event", "threads": 1}}
    for name, document in (("spec.json", spec), ("request.json", request), ("run.json", card)):
        (folder / name).write_text(json.dumps(document), encoding="utf-8")
    done = subprocess.run([sys.executable, "-B", str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"), "--program", str(program), "--work", str(folder / "out"), "--claims", str(CLAIMS[0])], capture_output=True, text=True, timeout=1800, check=False)
    summary = json.loads(done.stdout.strip().splitlines()[-1])
    if summary["status"] != "ok":
        raise RuntimeError(json.dumps(summary)[:600])
    out = folder / "out"
    lengths = {item["name"]: float.fromhex(item["radiation_length_mm"]) for item in json.loads((out / "probe-v2.json").read_text(encoding="utf-8"))["materials"]}
    ir = json.loads((out / "ir.json").read_text(encoding="utf-8"))
    material = {name: node["material"] for name, node in ir["physical"]["templates"].items()}
    selected = request["scorers"][0]["select"]["tags"]
    tags = ir["marker"]["tags"]
    names = [name for name in material if set(tags.get(name, [])) & set(selected)]
    if len({material[name] for name in names}) != 1:
        raise RuntimeError(f"the path scorer selects templates of several materials: {names}")
    with (out / "cells.csv").open(encoding="utf-8", newline="") as handle:
        path = sum(float(row[4]) for row in csv.reader(handle) if row[1] == "path" and row[2] != "-1")
    return path / lengths[material[names[0]]]


def cells(ir: dict, request: dict) -> int:
    """Readout cells of the segmented templates: volumes times bins (ceil of each side over its width)."""
    count = multiplicity(ir)
    scorer = next(item for item in request["scorers"] if "segmentation" in item)
    width = [float(value) for value in scorer["segmentation"]["cartesian_xy"]["width_mm"]]
    tags = ir["marker"]["tags"]
    total = 0
    for name, node in ir["physical"]["templates"].items():
        if set(tags.get(name, [])) & set(scorer["select"]["tags"]):
            half = [float(value) for value in node["half_mm"]]
            total += count.get(name, 0) * math.prod(max(1, math.ceil(2 * half[axis] / width[axis] - 1e-9)) for axis in (0, 1))
    return total


def counters(ir: dict) -> int:
    count = multiplicity(ir)
    tags = ir["marker"]["tags"]
    return sum(count.get(name, 0) for name in ir["physical"]["templates"] if "counter" in tags.get(name, []))


def measure(name: str, quantity: str, spec: dict, request: dict, work: Path, claims: Path, program: Path):
    folder = work / f"{name}-{quantity}"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    (folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    if quantity in ("cells", "counters"):
        ir = expanded(folder / "spec.json", claims, folder / "ir.json")
        return cells(ir, request) if quantity == "cells" else counters(ir)
    expanded(folder / "spec.json", claims, folder / "ir.json")  # the claims resolve before anything runs
    return path_x0(folder, spec, request, program)


def control_spec(name: str, quantity: str, spec: dict) -> dict:
    """The case's negative control, as a change of its own specification."""
    spec = json.loads(json.dumps(spec))
    if name == "cms-ecal-barrel-crystal":
        spec["params"]["crystal_length_mm"] = "220"
    elif name == "ams02-tof" and quantity == "half_x0":
        spec["params"]["thickness_mm"] = "9"
    elif name == "ams02-tof":
        spec["templates"]["even2"]["children"][0]["placement"]["linear"]["count"] -= 1
    elif quantity == "steel_x0":
        spec["params"]["layers"] = "60"
        spec["templates"]["section"]["children"][0]["placement"]["stack"]["repeat"] = 30
    else:
        spec["templates"]["tiles_even"]["solid"]["box"]["size_mm"][1] = "11 * cell_mm"
    return spec


def judge(value: float, reference: float, tolerance: float) -> bool:
    return value == reference if tolerance == 0 else abs(value / reference - 1) <= tolerance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    claims = claims_file(work)
    CLAIMS.append(claims)
    rows = card_rows()
    results, held = {}, True
    for folder in sorted(CASES.iterdir()):
        case = json.loads((folder / "case.json").read_text(encoding="utf-8"))
        spec = json.loads((folder / "detector-spec.json").read_text(encoding="utf-8"))
        request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        registered = [row for row in rows if row["case"].startswith(case["card_case"])]
        copied = [(q["reference"], q["tolerance_relative"]) for q in case["quantities"]]
        agrees = sorted(copied) == sorted((row["reference"], row["tolerance"]) for row in registered) and all(row["level"] == case["level"] for row in registered)
        out = {"copies_the_card": agrees, "quantities": []}
        for q in case["quantities"]:
            value = measure(folder.name, q["name"], spec, request, work, claims, args.program.resolve())
            control = measure(folder.name, q["name"] + "-control", control_spec(folder.name, q["name"], spec), request, work, claims, args.program.resolve()) if q["name"] not in ("cells", "counters") else None
            if control is None:
                cspec = control_spec(folder.name, q["name"], spec)
                cfolder = work / f"{folder.name}-{q['name']}-control"
                shutil.rmtree(cfolder, ignore_errors=True)
                cfolder.mkdir(parents=True)
                (cfolder / "spec.json").write_text(json.dumps(cspec), encoding="utf-8")
                ir = expanded(cfolder / "spec.json", claims, cfolder / "ir.json")
                control = cells(ir, request) if q["name"] == "cells" else counters(ir)
            within = judge(value, q["reference"], q["tolerance_relative"])
            caught = not judge(control, q["reference"], q["tolerance_relative"])
            out["quantities"].append({"name": q["name"], "measured": value, "reference": q["reference"], "residual_relative": value / q["reference"] - 1, "tolerance_relative": q["tolerance_relative"], "within": within, "control": control, "control_caught": caught})
        independent = all(q["independence"]["verified"] for q in case["quantities"])
        passed = agrees and all(item["within"] for item in out["quantities"])
        validated = passed and independent and all(item["control_caught"] for item in out["quantities"])
        out.update(passed=passed, independent=independent, status="validated-in-scope (comparison with cited values, not confirmation)" if validated else "comparison with cited values: not validated")
        held = held and passed and validated
        results[folder.name] = out
        if args.write:
            case["result"] = {key: out[key] for key in ("quantities", "copies_the_card", "independent")}
            case["status"] = out["status"]
            (folder / "case.json").write_text(json.dumps(case, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok" if held else "failed", "cases": results}, indent=1))
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""S7's reference cases against their cited values (g4sim plan, Sections 13, 19.2), the generic form of S6's cases_gate.py.

A case of phase S7 states, for each quantity, how it is measured ("measure") and its negative control ("negative_control": a JSON pointer
into its detector-spec, or into a request with "file", and the value it takes). Measures:
  path_x0           a geantino's path in the selected material over the radiation length Geant4 reports (S6's measure); request named
  count             how many volumes of the templates carrying a tag the expanded IR holds
  cherenkov_angle   the mean angle of the photons the primary itself emitted, detected inside the radiator's own medium (gate 2's method);
                    request and run card named
  field_integral    the integral of |B|, or of B times the distance from the centre, along a line, from the field map Geant4 reads, after a
                    geometry check has shown Geant4's field equal to this reading at the sample points
Each case's tolerances must equal the task card's rows (| Case | Level | Quantity | Reference | Tolerance |); a quantity within tolerance
whose control falls outside it, with its reference verified independent of Geant4, is validated-in-scope; a case labelled synthetic never is.
Usage: cases_gate.py --program PATH --work DIR [--case NAME] [--write]   In an activated Geant4 environment. Prints JSON with a status key.
Exit 0 every case passes, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))
CASES = PLUGIN / "profiles/reference/geometry-cases/cases"
CARD = PLUGIN / "docs/dev/geant4-architecture/g4sim-tasks/S7.md"
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
VALIDATED = "validated-in-scope (comparison with cited values, not confirmation)"
NOT_VALIDATED = "comparison with cited values: not validated"
SYNTHETIC = "synthetic: a comparison with another simulation, not a validation"


def _s6():
    spec = importlib.util.spec_from_file_location("s6_cases_gate", PLUGIN / "adapters/geant4/tests/g4proto/s6_gates/cases_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S6 = _s6()


def card_rows() -> list:
    text = CARD.read_text(encoding="utf-8")
    start = text.index("| Case | Level | Quantity | Reference | Tolerance |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        reference = float(re.match(r"-?[\d,.]+(?:e-?\d+)?", cells[3]).group(0).replace(",", ""))
        tolerance = 0.0 if cells[4] == "exact" else float(cells[4].split("%")[0]) / 100
        rows.append({"case": cells[0], "level": cells[1], "quantity": cells[2], "reference": reference, "tolerance": tolerance})
    return rows


def claims_file(work: Path) -> Path:
    profiles = ("reference/detector-atlas", "experiments/ams-02", "experiments/eic")
    ids = [c["id"] for p in profiles for c in json.loads((PLUGIN / "profiles" / p / "evidence/claims.json").read_text(encoding="utf-8"))]
    path = work / "claims.json"
    path.write_text(json.dumps(ids), encoding="utf-8")
    return path


def set_pointer(document: dict, pointer: str, value) -> dict:
    document = json.loads(json.dumps(document))
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.strip("/").split("/")]
    node = document
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    if isinstance(node, list):
        node[int(parts[-1])] = value
    else:
        node[parts[-1]] = value
    return document


def simulate(folder: Path, spec: dict, request: dict, card: dict, claims: Path, program: Path, case_folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, document in (("spec.json", spec), ("request.json", request), ("run.json", card)):
        (folder / name).write_text(json.dumps(document), encoding="utf-8")
    for extra in case_folder.glob("*.txt"):  # field maps and position files beside the specification
        shutil.copy2(extra, folder / extra.name)
    done = subprocess.run([sys.executable, "-B", str(DRIVER), "simulate", "--detector", str(folder / "spec.json"), "--request", str(folder / "request.json"), "--run", str(folder / "run.json"),
                           "--program", str(program), "--work", str(folder / "out"), "--claims", str(claims)], capture_output=True, text=True, timeout=7200, check=False)
    summary = json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {"status": "error", "stderr": done.stderr[-500:]}
    if summary["status"] != "ok":
        raise RuntimeError(json.dumps(summary)[:800])
    return folder / "out"


def cherenkov_angle(out: Path) -> float:
    by_event: dict = {}
    with (out / "photons.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row and row[0] != "event" and int(row[12]) == 1:
                by_event.setdefault(int(row[0]), []).append(math.acos(max(-1.0, min(1.0, float(row[11])))))
    if not by_event:
        raise RuntimeError("no photon of the primary was detected")
    return statistics.fmean(statistics.fmean(values) for values in by_event.values())


def field_integral(folder: Path, spec: dict, measure: dict, claims: Path, program: Path, case_folder: Path) -> float:
    """After a geometry check passes (Geant4's field equals this reading at the sample points), the integral along the measure's line."""
    from core.geometry import fieldmap
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    for extra in case_folder.glob("*.txt"):
        shutil.copy2(extra, folder / extra.name)
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated",
            "run": {"events": 1, "first_event": 0, "logical_run_seed": 20261108, "mode": "geometry-check", "seeding": "per-event", "threads": 1}}
    (folder / "run.json").write_text(json.dumps(card), encoding="utf-8")
    done = subprocess.run([sys.executable, "-B", str(DRIVER), "geometry-check", "--detector", str(folder / "spec.json"), "--run", str(folder / "run.json"), "--program", str(program),
                           "--work", str(folder / "out")], capture_output=True, text=True, timeout=3600, check=False)
    report = json.loads(done.stdout.strip().splitlines()[-1])
    if report["status"] != "ok":
        raise RuntimeError(json.dumps(report)[:800])
    parsed = fieldmap.parse((folder / "out" / f"field-map.{measure['field']}.txt").read_text(encoding="utf-8"))
    start, end, steps = [float(v) for v in measure["from_mm"]], [float(v) for v in measure["to_mm"]], int(measure.get("steps", 2000))
    length = math.dist(start, end)
    total = 0.0
    for i in range(steps):
        t = (i + 0.5) / steps
        point = [a + (b - a) * t for a, b in zip(start, end)]
        b = fieldmap.interpolate(parsed["grid"], parsed["values"], point)
        value = math.hypot(*b) if measure.get("component", "magnitude") == "magnitude" else b["xyz".index(measure["component"])]
        weight = abs(t * length - length / 2) if measure.get("weight") == "distance_from_centre" else 1.0
        total += value * weight * length / steps / 1000.0  # tesla times metres (and metres again with the distance weight)
    return total


def measure(name: str, q: dict, spec: dict, case_folder: Path, work: Path, claims: Path, program: Path) -> float:
    folder = work / name
    shutil.rmtree(folder, ignore_errors=True)
    m = q["measure"]
    if m["kind"] == "count":
        folder.mkdir(parents=True)
        (folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        for extra in case_folder.glob("*.txt"):
            shutil.copy2(extra, folder / extra.name)
        ir = S6.expanded(folder / "spec.json", claims, folder / "ir.json")
        count = S6.multiplicity(ir)
        tags = ir["marker"]["tags"]
        return float(sum(count.get(t, 0) for t in ir["physical"]["templates"] if m["tag"] in tags.get(t, [])))
    if m["kind"] == "field_integral":
        return field_integral(folder, spec, m, claims, program, case_folder)
    request = json.loads((case_folder / m["request"]).read_text(encoding="utf-8"))
    if q.get("_request_override"):
        request = q["_request_override"]
    if m["kind"] == "path_x0":
        folder.mkdir(parents=True)
        S6.CLAIMS[:] = [claims]
        return S6.path_x0(folder, spec, request, program)
    if m["kind"] == "cherenkov_angle":
        card = json.loads((case_folder / m["run"]).read_text(encoding="utf-8"))
        return cherenkov_angle(simulate(folder, spec, request, card, claims, program, case_folder))
    raise ValueError(f"unknown measure {m['kind']}")


def judge(value: float, reference: float, tolerance: float) -> bool:
    return value == reference if tolerance == 0 else abs(value / reference - 1) <= tolerance


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--case", action="append")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    claims = claims_file(work)
    rows = card_rows()
    results, held = {}, True
    for folder in sorted(CASES.iterdir()):
        case = json.loads((folder / "case.json").read_text(encoding="utf-8"))
        if case.get("phase") != "S7" or (args.case and folder.name not in args.case):
            continue
        spec = json.loads((folder / "detector-spec.json").read_text(encoding="utf-8"))
        registered = [row for row in rows if row["case"] == case["card_case"]]
        agrees = sorted((q["reference"], q["tolerance_relative"]) for q in case["quantities"]) == sorted((r["reference"], r["tolerance"]) for r in registered) \
            and all(r["level"] == case["level"] for r in registered)
        out = {"copies_the_card": agrees, "quantities": []}
        try:
            for q in case["quantities"]:
                value = measure(f"{folder.name}-{q['name']}", q, spec, folder, work, claims, args.program.resolve())
                control_q, control_spec = dict(q), spec
                change = q["negative_control"]
                if change.get("file"):
                    control_q["_request_override"] = set_pointer(json.loads((folder / change["file"]).read_text(encoding="utf-8")), change["pointer"], change["value"])
                else:
                    control_spec = set_pointer(spec, change["pointer"], change["value"])
                control = measure(f"{folder.name}-{q['name']}-control", control_q, control_spec, folder, work, claims, args.program.resolve())
                out["quantities"].append({"name": q["name"], "measured": value, "reference": q["reference"], "residual_relative": value / q["reference"] - 1,
                                          "tolerance_relative": q["tolerance_relative"], "within": judge(value, q["reference"], q["tolerance_relative"]),
                                          "control": control, "control_caught": not judge(control, q["reference"], q["tolerance_relative"])})
        except (RuntimeError, OSError, KeyError, ValueError) as err:
            out["error"] = str(err)[:800]
        passed = "error" not in out and agrees and all(item["within"] for item in out["quantities"])
        independent = all(q["independence"]["verified"] for q in case["quantities"])
        synthetic = case.get("label_status") == "synthetic"
        validated = passed and independent and not synthetic and all(item["control_caught"] for item in out["quantities"])
        out.update(passed=passed, independent=independent, status=SYNTHETIC if synthetic and passed else VALIDATED if validated else NOT_VALIDATED)
        held = held and passed and (validated or synthetic)
        results[folder.name] = out
        if args.write and "error" not in out:
            case["result"] = {key: out[key] for key in ("quantities", "copies_the_card", "independent")}
            case["status"] = out["status"]
            (folder / "case.json").write_text(json.dumps(case, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok" if held and results else "failed", "cases": results}, indent=1))
    return 0 if held and results else 1


if __name__ == "__main__":
    sys.exit(main())

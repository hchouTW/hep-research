#!/usr/bin/env python3
"""S5 gate 8: a search of a new geometry kind, through evaluate_design.py search, g4kit.py and geant4_run.py (g4sim plan, Sections 18 and 19.2).

A synthetic calorimeter candidate on a copy of the J15 project. Every design the search runs must leave a derivation record, the hashes of its specification files and a computational-run, and one changed byte of a
specification written by g4kit.py must make geant4_run.py refuse it.

Usage: kit_search.py --program PATH --work DIR   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from contracts.schema import validate  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

EVALUATE = PLUGIN / "skills/hep-detector/scripts/evaluate_design.py"
RUN = PLUGIN / "adapters/geant4/assets/geant4_run.py"
PROJECT = PLUGIN / "examples/design-minimal-spectrometer/output/artifacts"
NAMESPACE = "j15-v1"
CANDIDATE = f"{NAMESPACE}:cand-KIT"
FIGURE = "calorimeter-energy-resolution"
SYNTHETIC = {"source": "gate 8 (SYNTHETIC)", "status": "proposal"}


def parameter(value, unit: str) -> dict:
    return {"value": value, "unit": unit, **SYNTHETIC}


def candidate(base: dict) -> dict:
    values = {"stochastic_term": (0.1, "GeV^0.5"), "constant_term": (0.01, "1"), "noise_term_GeV": (0.0, "GeV"), "depth_x0": (10.0, "1"), "front_position_m": (1.0, "m"), "passive_material": ("G4_Pb", "n/a"), "absorber_x0_mm": (5.612, "mm"),
              "layers": (10, "1"), "towers_x": (1, "1"), "towers_y": (1, "1"), "active_mm": (3.0, "mm"), "support_mm": (1.0, "mm"), "support_material": ("G4_AIR", "n/a"), "tower_side_mm": (150.0, "mm"), "absorber_material": ("G4_Pb", "n/a"), "active_material": ("G4_PLASTIC_SC_VINYLTOLUENE", "n/a"),
              "wrap_material": ("G4_MYLAR", "n/a"), "guide_material": ("G4_PLEXIGLASS", "n/a"), "world_material": ("G4_AIR", "n/a")}
    document = json.loads(json.dumps(base))
    document["artifact_id"] = "cand-KIT"
    document["extension"] = {"candidate_id": CANDIDATE, "design_id": NAMESPACE, "description": "a synthetic calorimeter of the kit", "geometry_kind": "calorimeter",
                             "subsystems": {"DES-CAL-001": {**base["extension"]["subsystems"]["DES-CAL-001"], "technology": "synthetic sampling calorimeter", "parameters": {name: parameter(*item) for name, item in values.items()}}}}
    return document


def go(arguments: list, environment: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *map(str, arguments)], capture_output=True, text=True, check=False, timeout=3000, env=environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    art = root / "artifacts"
    shutil.copytree(PROJECT, art, ignore=shutil.ignore_patterns("reports", "studies", "evaluations", "outputs"))
    (art / "studies").mkdir()
    base = json.loads((art / "candidates/cand-N6.json").read_text(encoding="utf-8"))
    for extra in (art / "candidates").glob("*.json"):
        extra.unlink()
    (art / "candidates/cand-KIT.json").write_text(json.dumps(candidate(base), indent=1) + "\n", encoding="utf-8")
    (art / "search").mkdir()
    request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "e-", "energy": {"mono": {"energy_MeV": "1000"}}, "position": {"box_uniform": {"frame": "world", "centre_mm": ["0", "0", "-200"], "size_mm": ["1", "1", "0"]}}, "direction": {"fixed": {"frame": "world", "vector": [0, 0, 1]}}},
               "scorers": [{"name": "active", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep"}]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": "0.7"}}, "accounting": "separated", "run": {"events": 1, "first_event": 0, "logical_run_seed": 1, "mode": "mt", "seeding": "per-event", "threads": 2}}
    (art / "search/request.json").write_text(json.dumps(request), encoding="utf-8")
    (art / "search/run.json").write_text(json.dumps(card), encoding="utf-8")
    label = FIGURE
    spec = {"search_spec_version": 1, "design_spec": {"path": "design-spec.v1.json", "sha256": hashlib.sha256((art / "design-spec.v1.json").read_bytes()).hexdigest()}, "base_candidate": CANDIDATE,
            "objectives": [{"figure_of_merit": FIGURE, "denominator": {"energy_GeV": 1.0, "species": "electron"}, "reference_point": 0.5}],
            "free_parameters": [{"ref": "DES-CAL-001.parameters.depth_x0", "range": [6.0, 14.0]}, {"ref": "DES-CAL-001.parameters.stochastic_term", "range": [0.05, 0.2]}], "rules_version": "1.1.0", "materials_version": "1.0.0",
            "budget": {"evaluations": 16, "geant4": 6}, "optimizer": {"name": "nsga2", "population": 8, "generations": 2, "seed": 7}, "finalists": {"max": 2, "distinct_topologies": False},
            "geant4": {"kit": {"request": "search/request.json", "run": "search/run.json"}, "events": 64, "blocks": 8, "top_k": 1, "generations": 1, "offspring": 2, "targets": {label: {"particle": "e-", "energy_MeV": 1000, "scorer": "active", "measure": "relative_width"}}}}
    (art / "search/SEARCH-KIT.spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
    config = root / "config.json"
    config.write_text(json.dumps({"g4sim_run": str(args.program.resolve())}), encoding="utf-8")
    environment = {**os.environ, "HEP_GEANT4_CONFIG": str(config), "PYTHONDONTWRITEBYTECODE": "1"}
    done = go([EVALUATE, "search", "--artifacts", art, "--spec", "search/SEARCH-KIT.spec.json", "--id", "SEARCH-KIT", "--status", "synthetic", "--geant4-work", root / "g4work"], environment)
    if done.returncode != 0:
        print(json.dumps({"status": "failed", "search": done.stdout[-1200:], "error": done.stderr[-600:]}))
        return 1
    summary = json.loads((art / "runs/SEARCH-KIT.computational-run.json").read_text(encoding="utf-8"))["extension"]["search_summary"]
    evidence = summary["geant4"]["evidence"]
    scratch = root / "g4work/SEARCH-KIT/artifacts"
    problems = []
    for row in evidence:
        record = json.loads((scratch / row["derivation"]).read_text(encoding="utf-8"))
        run = json.loads(Path(row["record"]).read_text(encoding="utf-8"))
        detector = scratch / row["derivation"].replace(".derivation.json", ".detector.json")
        if not validate(record, "geometry_derivation.json").ok:
            problems.append(f"{row['run']}: the derivation record is not valid")
        if record["detector_spec_sha256"] != row["detector_sha256"] or hashlib.sha256(detector.read_bytes()).hexdigest() != row["detector_sha256"]:
            problems.append(f"{row['run']}: the detector-spec is not the one recorded")
        if record["geometry_id"] != run["extension"]["geometry"]["geometry_id"]:
            problems.append(f"{row['run']}: the run has another geometry_id")
        if {row["detector_sha256"], row["request_sha256"], row["run_card_sha256"]} - {item["sha256"] for item in run["extension"]["input_manifest"]}:
            problems.append(f"{row['run']}: a specification is not in input_manifest")
        report = validate_artifact(run)
        if not report.ok:
            problems.append(f"{row['run']}: the computational-run fails: {[item.message[:90] for item in report.errors][:2]}")
    first = evidence[0]
    detector = scratch / first["derivation"].replace(".derivation.json", ".detector.json")
    original = detector.read_bytes()
    detector.write_bytes(original[:-2] + b" " + original[-1:])
    folder = scratch / "specs/search"
    refused = go([RUN, "run-spec", "--detector", detector, "--detector-sha256", first["detector_sha256"], "--request", folder / f"{first['run']}.request.json", "--request-sha256", first["request_sha256"], "--run", folder / f"{first['run']}.run.json", "--run-sha256", first["run_card_sha256"],
                  "--exe", args.program.resolve(), "--work", root / "tampered", "--run-id", "tampered", "--record", root / "tampered.json"], environment)
    detector.write_bytes(original)
    rejected = refused.returncode != 0 and "sha256" in refused.stdout and not (root / "tampered.json").exists()
    distinct = len({row["detector_sha256"] for row in evidence})
    passed = len(evidence) >= 2 and distinct >= 2 and not problems and rejected
    print(json.dumps({"status": "ok" if passed else "failed", "runs": len(evidence), "distinct_designs": distinct, "problems": problems[:6], "one_byte_refused": rejected, "refusal": refused.stdout[-260:], "values": [point.get("geant4", [{}])[0].get("values", {}).get(label, {}).get("value") for point in json.loads((art / "runs/SEARCH-KIT.points.json").read_text(encoding="utf-8")).get("points", []) if point.get("geant4")] if (art / "runs/SEARCH-KIT.points.json").is_file() else None}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

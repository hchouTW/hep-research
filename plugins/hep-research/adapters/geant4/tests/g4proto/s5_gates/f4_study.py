#!/usr/bin/env python3
"""S5 gate 7: a synthetic study made by a kit and run through g4sim_run reaches an F4 evaluation, with D0's four conditions judged from the records, and a corrupted condition makes design.py refuse (g4sim plan, Section 19.2).

On a copy of the J15 project: a planes_tracker candidate, its design geometry and detector-spec, the study runs, the four conditions (material-definition, field-propagation, reco-closure, multiple-scattering-reference), check_geant4_study.py
label and evaluate_design.py f4.

Usage: f4_study.py --program PATH --simroot PATH --simreco PATH --work DIR [--events N]   In an activated Geant4 environment. Prints JSON with a status key. Exit 0 pass, 1 fail.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
SCRIPTS = PLUGIN / "skills/hep-detector/scripts"
EVALUATE, KIT, BENCH, CHECK = (SCRIPTS / name for name in ("evaluate_design.py", "g4kit.py", "geant4_benchmarks.py", "check_geant4_study.py"))
RUN = PLUGIN / "adapters/geant4/assets/geant4_run.py"
DESIGN = PLUGIN / "contracts/design.py"
PROJECT = PLUGIN / "examples/design-minimal-spectrometer/output/artifacts"
NAMESPACE = "j15-v1"
CANDIDATE = f"{NAMESPACE}:cand-TRK"
FIGURE = "momentum-resolution-core"
RIGIDITY_GV = 1.0  # the rigidity of the requirement this evaluation must decide
PROTON_MASS_GEV = 0.93827208943
X0_SILICON_MM = 93.7
PLANE_MM = 0.3
BLOCKS = 16
EVALUATION = "SIM-TRK"
BELOW_SCREENING = 8  # the row of design.py's verdict table
SCATTERING_EVENTS = 8000  # the J15 sample: blocks of a few events bias the core width upward (22% at 320 events)
SELECTED = [{"column": "selected", "op": "==", "value": 1}]
SYNTHETIC = {"source": "gate 7 (SYNTHETIC)", "status": "proposal"}
MATERIAL = {"name": "G4_Si", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329, "radiation_length_mm": X0_SILICON_MM, "reference_origin": "independent", "reference_source": "PDG Atomic and Nuclear Properties 2024 (https://pdg.lbl.gov/2024/AtomicNuclearProperties/), read 2026-10-24"}


def go(arguments: list, allowed: tuple = (0,), environment=None) -> dict:
    done = subprocess.run([sys.executable, "-B", *map(str, arguments)], capture_output=True, text=True, check=False, timeout=7000, env=environment)
    if done.returncode not in allowed:
        raise RuntimeError(f"{Path(str(arguments[0])).name} {arguments[1]} exited {done.returncode}: {done.stdout[-700:]} {done.stderr[-300:]}")
    text = done.stdout.strip()
    try:
        return json.loads(text[text.rindex("\n{") + 1 if "\n{" in text and not text.startswith("{") else 0:])
    except ValueError:
        return {"raw": text[-500:]}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate(base: dict) -> dict:
    values = {"planes": (6, "1"), "plane_gap_mm": (100.0, "mm"), "plane_thickness_mm": (PLANE_MM, "mm"), "plane_side_mm": (400.0, "mm"), "field_tesla": (1.0, "T"), "plane_material": ("G4_Si", "n/a"), "world_material": ("G4_Galactic", "n/a"),
              "point_resolution_um": (10.0, "um"), "layer_x_over_x0": (PLANE_MM / X0_SILICON_MM, "1")}
    document = json.loads(json.dumps(base))
    document["artifact_id"] = "cand-TRK"
    subsystem = base["extension"]["subsystems"]["DES-TRK-001"]
    document["extension"] = {"candidate_id": CANDIDATE, "design_id": NAMESPACE, "description": "a synthetic telescope of the kit", "geometry_kind": "planes-tracker",
                             "subsystems": {"DES-TRK-001": {**subsystem, "parameters": {name: {"value": value, "unit": unit, **SYNTHETIC} for name, (value, unit) in values.items()}}}}
    return document


def request(particle: str, energy_mev: float, scorers: list, start_x: float = -400.0, direction=None, planes=None) -> dict:
    block = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": particle, "energy": {"mono": {"energy_MeV": str(energy_mev)}}, "position": {"box_uniform": {"frame": "world", "centre_mm": [str(start_x), "0", "0"], "size_mm": ["0", "1", "1"]}}, "direction": {"fixed": {"frame": "world", "vector": direction or [1, 0, 0]}}}, "scorers": scorers}
    if planes:
        block["reference_planes"] = [{"name": f"plane{at}", "frame": "world", "z_mm": str(z)} for at, z in enumerate(planes)]
    return block


HITS = [{"name": "planes", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "edep", "level": "event_file", "hit_kind": "tracker"}]
PATH = [{"name": "path", "readout": "none", "select": {"tags": ["tracker"]}, "quantity": "track_length"}]


class Study:
    def __init__(self, root: Path, program: Path, simroot: Path, simreco: Path, events: int):
        self.root, self.program, self.simroot, self.simreco, self.events = root, program, simroot, simreco, events
        self.art = root / "artifacts"
        self.runs: dict = {}

    def card(self, events: int, seed: int, cut: str = "0.7", physics_list: str = "FTFP_BERT_EMZ") -> dict:
        return {"schema": "g4sim-run/1", "physics": {"reference_list": physics_list, "cuts_mm": {"default": cut}}, "accounting": "separated", "run": {"events": events, "first_event": 0, "logical_run_seed": seed, "mode": "mt", "seeding": "per-event", "threads": 2}}

    def run(self, name: str, detector: Path, source: dict, card: dict, role: str, extra_inputs=()) -> Path:
        folder = self.art / "specs"
        folder.mkdir(exist_ok=True)
        files = {"request": folder / f"{name}.request.json", "run": folder / f"{name}.run.json"}
        files["request"].write_text(json.dumps(source, indent=1) + "\n", encoding="utf-8")
        files["run"].write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8")
        record = self.art / "runs" / f"{name}.computational-run.json"
        record.parent.mkdir(exist_ok=True)
        go([RUN, "run-spec", "--detector", detector, "--detector-sha256", sha(detector), "--request", files["request"], "--request-sha256", sha(files["request"]), "--run", files["run"], "--run-sha256", sha(files["run"]), "--exe", self.program,
            "--work", self.root / "sim" / name, "--run-id", name, "--record", record, "--created", "2026-11-07", "--evidence-role", role, "--point-id", name, *[word for path in extra_inputs for word in ("--input", path)]])
        self.runs[name] = record
        return self.root / "sim" / name

    def reco(self, name: str, events: int, width: float, geometry=None) -> tuple:
        observables = [{"name": "core", "source_column": "inv_rig_res", "estimator": "gaussian-core", "bins": {"lo": -2.0, "hi": 2.0, "width": width}, "selection": SELECTED}, {"name": "pull", "source_column": "rho_pull", "bins": {"lo": -10, "hi": 10, "width": 0.05}, "selection": SELECTED},
                       {"name": "residual", "source_column": "inv_rig_res", "bins": {"lo": -2.0, "hi": 2.0, "width": width}, "selection": SELECTED}]
        spec = {"schema": "simreco.spec/1", "point_resolution_um": {"bending": 10.0, "non_bending": 30.0}, "radiation_length_mm": {"G4_Si": X0_SILICON_MM}, "output": {"observables": observables, "blocks": {"blocks": BLOCKS, "block_size": events // BLOCKS}}}
        path = self.art / "specs" / f"{name}.reco.json"
        path.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        record = self.art / "runs" / f"{name}-reco.computational-run.json"
        go([RUN, "reco", "--run-record", self.runs[name], "--reco-spec", path, "--simreco", self.simreco, "--simroot", self.simroot, "--work-out", self.root / "reco", "--reco-id", f"{name}-reco", "--record", record, "--project-root", self.art, "--created", "2026-11-07",
            *(["--geometry", geometry] if geometry else [])])
        self.runs[f"{name}-reco"] = record
        return record, self.root / "reco" / f"{name}-reco" / "summary_r000.json", path

    def scattering_files(self, name: str, density_factor: float, momentum_mev: float, folder: Path) -> tuple:
        """A slab and a plane of the kit, and the crossing file the reference benchmark reads: the direction at the entry of the plane, across vacuum."""
        tag = folder / name
        tag.mkdir(parents=True)
        geometry = tag / "design.geometry.json"
        fields = {"planes": 2, "plane_gap_mm": 100.0, "plane_thickness_mm": PLANE_MM, "plane_side_mm": 400.0, "field_tesla": 0.0, "plane_material": "Si_slab", "world_material": "G4_Galactic",
                  "materials": {"Si_slab": {"composition": {"Si": "1"}, "density_g_cm3": str(MATERIAL["density_g_cm3"] * density_factor), "facts": "PDG, the control's factor applied"}}}
        geometry.write_text(json.dumps({"schema": "design-geometry/1", "geometry": "planes-tracker", "geometry_kind": "planes-tracker", "fields": fields}), encoding="utf-8")
        detector = tag / "detector.json"
        go([KIT, "derive", "--geometry", geometry, "--out-detector", detector, "--out-derivation", tag / "derivation.json"])
        kinetic = (math.hypot(RIGIDITY_GV, PROTON_MASS_GEV) - PROTON_MASS_GEV) * 1000
        work = self.run(f"ms-{name}", detector, request("proton", kinetic, HITS, -250.0), self.card(max(self.events, SCATTERING_EVENTS), 9000 + int(density_factor * 100)), "calibration")
        target = tag / "hits.csv"
        subprocess.run([str(self.simroot), "hits", str(work / "hits.root"), "--ntuple", "tracker_hits", "--out", str(target)], check=True, capture_output=True, text=True, timeout=600)
        with target.open(encoding="utf-8", newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row["step_track_id"] == "1"]
        last = max(float(row["x_mm"]) for row in rows)
        first: dict = {}
        for row in sorted(rows, key=lambda item: (int(item["event_id"]), int(item["step_index"]))):
            if float(row["x_mm"]) > last - 1.0:
                first.setdefault(row["event_id"], row)
        crossings = tag / "crossings.csv"
        with crossings.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["event_id", "track_id", "plane_id", "dx", "dy", "dz"])
            for event, row in first.items():
                vector = [float(row[f"p{axis}_MeV"]) for axis in "xyz"]
                size = math.sqrt(sum(value * value for value in vector))
                writer.writerow([event, 1, 1, *(value / size for value in vector)])
        return detector, crossings


def design_view(art: Path) -> dict:
    """What design.py does with the evaluation: its errors, and whether the requirement's verdict rests on it."""
    done = subprocess.run([sys.executable, "-B", str(DESIGN), "check", "--artifacts", str(art)], capture_output=True, text=True, timeout=280, check=False)
    report = json.loads(done.stdout)
    wanted = f"{NAMESPACE}:{EVALUATION}"
    item = next((entry for entry in report.get("evaluations", []) if entry["evaluation"] == wanted), {})
    rows = [row for requirement in report.get("requirements", []) for row in requirement.get("matrix", []) if CANDIDATE in row.get("candidates", [])]
    deciding = [entry for row in rows for entry in row.get("used", []) if entry.get("evaluation") == wanted]
    return {"exit": done.returncode, "status": report.get("status"), "fidelity": item.get("fidelity"), "verdict_rows": [{"row": entry.get("row"), "verdict": entry.get("verdict"), "code": entry.get("code")} for entry in deciding],
            "errors": sorted({error.get("code", str(error)) if isinstance(error, dict) else str(error) for error in item.get("errors", []) + report.get("errors", [])})}


def accepted(view: dict) -> bool:
    """F4 evidence that counts: no error, and a verdict that does not rest on row 8, below screening (ART-31)."""
    return view["status"] == "ok" and view["exit"] == 0 and not view["errors"] and bool(view["verdict_rows"]) and all(item["row"] != BELOW_SCREENING for item in view["verdict_rows"])


def rebound(art: Path, document: dict) -> None:
    """The record rewritten, with the hash the evaluation binds rewritten too: a forgery a hash comparison alone does not see."""
    path = art / "studies/TRK/study.computational-run.json"
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    evaluation = art / f"evaluations/{EVALUATION}.json"
    bound = json.loads(evaluation.read_text(encoding="utf-8"))
    for item in bound["inputs"]:
        if item["ref"].endswith("study.computational-run.json"):
            item["sha256"] = sha(path)
    evaluation.write_text(json.dumps(bound, indent=1) + "\n", encoding="utf-8")


def study_record(art: Path) -> tuple:
    document = json.loads((art / "studies/TRK/study.computational-run.json").read_text(encoding="utf-8"))
    return document, next(item for item in document["extension"]["study"]["benchmarks"] if item["benchmark"] == "field-propagation")


def forged_field_hash(art: Path) -> None:
    document, entry = study_record(art)
    entry["scope"]["field_configuration_sha256"] = "0" * 64
    rebound(art, document)


def forged_everywhere(art: Path) -> None:
    """The field hash changed wherever the record holds it, so the record agrees with itself; only the study's own files can show it."""
    document, entry = study_record(art)
    entry["scope"]["field_configuration_sha256"] = "0" * 64
    document["extension"]["study"]["declared_scope"]["field_configuration_sha256"] = "0" * 64
    rebound(art, document)


def failed_beside_a_clean_entry(art: Path) -> None:
    document, entry = study_record(art)
    document["extension"]["study"]["benchmarks"].append(json.loads(json.dumps(entry)))
    entry["verdict"] = "fail"
    rebound(art, document)


def changed_derivation(art: Path) -> None:
    path = art / "studies/TRK.derivation.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["design_geometry_sha256"] = "0" * 64
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")


def changed_kind(art: Path) -> None:
    path = art / "studies/G-TRK.geometry.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["geometry_kind"] = "tof"
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")


CORRUPTIONS = {"field-hash": forged_field_hash, "field-hash-everywhere": forged_everywhere, "failed-beside-clean": failed_beside_a_clean_entry, "derivation": changed_derivation, "geometry-kind": changed_kind}


def corrupted(root: Path, art: Path, change) -> dict:
    copy = root / f"corrupted-{change.__name__}"
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(art, copy)
    change(copy)
    return design_view(copy)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("program", "simroot", "simreco", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--events", type=int, default=3200)
    args = parser.parse_args()
    root = args.work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    art = root / "artifacts"
    shutil.copytree(PROJECT, art, ignore=shutil.ignore_patterns("reports", "studies", "evaluations", "outputs"))
    (art / "studies").mkdir()
    base = json.loads((art / "candidates/cand-N6.json").read_text(encoding="utf-8"))
    for extra in (art / "candidates").glob("*.json"):
        extra.unlink()
    path = art / "candidates/cand-TRK.json"
    path.write_text(json.dumps(candidate(base), indent=1) + "\n", encoding="utf-8")
    study = Study(root, args.program.resolve(), args.simroot.resolve(), args.simreco.resolve(), args.events)
    denominator = ["--denominator", f"rigidity_GV={RIGIDITY_GV:g}", "--denominator", "species=proton"]
    go([EVALUATE, "geometry", "--artifacts", art, "--candidate", CANDIDATE, "--figure-of-merit", FIGURE, *denominator, "--id", "G-TRK"])
    geometry = art / "studies/G-TRK.geometry.json"
    detector, derivation = art / "studies/TRK.detector.json", art / "studies/TRK.derivation.json"
    record = go([KIT, "derive", "--geometry", geometry, "--out-detector", detector, "--out-derivation", derivation])
    bound = json.loads(path.read_text(encoding="utf-8"))
    bound["extension"].update(geometry_id=record["geometry_id"], geometry_derivation_ref="studies/TRK.derivation.json")
    path.write_text(json.dumps(bound, indent=1) + "\n", encoding="utf-8")
    kinetic = (math.hypot(RIGIDITY_GV, PROTON_MASS_GEV) - PROTON_MASS_GEV) * 1000
    nominal = study.run("nominal", detector, request("proton", kinetic, HITS), study.card(args.events, 1), "nominal", [geometry])
    reco_record, summary, reco_spec = study.reco("nominal", args.events, 0.002, geometry)
    # the variation runs and the cut scan of the convergence gate
    variations = {"emy": "reference list FTFP_BERT_EMY: Urban multiple scattering for protons instead of WentzelVI", "qgsp-bic": "reference list QGSP_BIC_EMZ: Binary cascade for nucleons below 1.5 GeV"}
    lists = {"emy": "FTFP_BERT_EMY", "qgsp-bic": "QGSP_BIC_EMZ"}
    study.run("scan", detector, request("proton", kinetic, HITS), study.card(args.events, 2, cut="0.35"), "scan", [geometry])
    scan_summary = study.reco("scan", args.events, 0.002, geometry)[1]
    variation_summaries, variation_records = {}, {}
    for name, physics_list in lists.items():
        study.run(name, detector, request("proton", kinetic, HITS), study.card(args.events, 3, physics_list=physics_list), "variation", [geometry])
        variation_records[name], variation_summaries[name], _ = study.reco(name, args.events, 0.002, geometry)
    # condition 1: a geantino scan
    geantino = study.run("geantino", detector, request("geantino", 1000.0, PATH), study.card(50, 4), "calibration", [geometry])
    # condition 2: charged geantinos at an angle to the field, through planes that lie in it
    planes_z = [50.0, 100.0, 150.0]
    charged = study.run("charged", detector, request("chargedgeantino", 1000.0, [], -400.0, [0.6, 0, 0.8], planes_z), study.card(200, 5), "calibration", [geometry])
    crossing_file = root / "charged.crossings.csv"
    subprocess.run([str(study.simroot), "hits", str(charged / "hits.root"), "--ntuple", "plane_crossings", "--out", str(crossing_file)], check=True, capture_output=True, text=True, timeout=300)
    # condition 3: closure, at a rigidity where scattering is negligible
    study.run("closure", detector, request("mu-", 1.0e6, HITS), study.card(args.events, 6), "calibration", [geometry])
    closure_record, closure_summary, _ = study.reco("closure", args.events, 0.002)
    # condition 4: the tracking reference
    scatter = root / "scatter"
    references = {"nominal": study.scattering_files("nominal", 1.0, RIGIDITY_GV * 1000, scatter)}
    shim = root / "scatter.elements.json"
    shim.write_text(json.dumps({"elements": [{"name": "Slab"}, {"name": "Plane"}]}), encoding="utf-8")
    keys = go([BENCH, "scope-keys", "--ir", nominal / "ir.json", "--reco-spec", reco_spec, "--geometry", geometry, "--realization", detector])["scope_keys"]
    identity = json.loads((nominal / "summary.json").read_text(encoding="utf-8"))
    studies = art / "studies/TRK"
    studies.mkdir()
    relative = lambda target: os.path.relpath(target, studies)  # noqa: E731
    entry = lambda target: {"path": relative(target), "sha256": sha(target)}  # noqa: E731
    observables = json.loads(reco_spec.read_text(encoding="utf-8"))["output"]["observables"]
    spec = {"schema": "geant4-study-spec/1", "study_id": "s5-gate7-TRK", "label": "SYNTHETIC S5 gate 7 study (names no experiment)", "geant4": {"version": "11.4.3", "documentation": [{"name": "Geant4 upstream source, tag v11.4.3", "version": "11.4.3", "relied_on": True}]},
            "geometry_source": {"kind": "design", "description": "made by g4kit.py from the design geometry", "uses_replicas": False}, "materials": [MATERIAL], "reproducibility": {"data_paths_recorded": True, "build_record": "none: a conda-forge installation"},
            "downstream_use": {"kind": "other", "note": "F4 evaluation of momentum-resolution-core, S5 gate 7"}, "observable": {"name": FIGURE, "kind": "tracking-resolution", "domain": "em", "definition": "Gaussian core width of (1/R_reco - 1/R_true) R_true of selected tracks", "unit": "1"},
            "particle": {"name": "proton", "energy_MeV": kinetic},
            "physics": {"g4sim": {"detector_spec": entry(detector), "simulation_request": entry(art / "specs/nominal.request.json"), "run_card": entry(art / "specs/nominal.run.json"), "geometry_id": record["geometry_id"], "request_id": identity["request_id"]},
                        "justification": [{"choice": "FTFP_BERT_EMZ", "reason": "EM option 4 for multiple scattering", "source": "geant4:source/physics_lists/lists (reference list factory)"}, {"choice": "production cut", "reason": "converged in this study's cut scan", "source": "convergence gate of this study"}]},
            "convergence_plan": {"parameters": [{"name": "physics.default_cut_mm", "values": [0.35, 0.7]}], "observables": ["core"], "tolerance_relative": {"core": 0.1}}, "observables": observables, "blocks": {"K": BLOCKS}, "statistical_target": {"observable": "core", "relative_se": 0.05},
            "validation_plan": {"benchmarks": [{"name": name, "grade": "verification" if name != "multiple-scattering-reference" else "reference"} for name in ("material-definition", "field-propagation", "reco-closure", "multiple-scattering-reference")],
                                "scope": {"particle": "proton", "energy_MeV": [kinetic, kinetic], "observable": FIGURE, "material": "G4_Si", "thickness_x0": [PLANE_MM / X0_SILICON_MM] * 2, "rigidity_GV": [RIGIDITY_GV, RIGIDITY_GV], **keys}},
            "variation_plan": {"observable": "core", "model_assignment_checked": True, "variations": [{"name": name, "change": change} for name, change in variations.items()]}}
    spec_path = studies / "study.json"
    spec_path.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    go([CHECK, "run", "--spec", spec_path, "--summary", f"nominal={summary}", "--summary", f"scan={scan_summary}", "--out", studies / "convergence.json"], (0, 1, 3))
    go([CHECK, "variations", "--spec", spec_path, "--nominal", summary, *[word for name, value in variation_summaries.items() for word in ("--variation", f"{name}={value}")], "--out", studies / "variations.json"], (0, 1, 3))
    configuration = studies / "bench.config.json"
    conditions = [{"benchmark": "material-definition", "g4sim": True, "geometry": relative(geometry), "detector": relative(detector), "probe": relative(geantino / "probe-v2.json"), "cells": relative(geantino / "cells.csv"), "tolerance_relative": 0.01},
                  {"benchmark": "field-propagation", "g4sim": True, "ir": relative(charged / "ir.json"), "primaries": relative(charged / "primaries.csv"), "crossings": relative(crossing_file), "field_tesla": 1.0},
                  {"benchmark": "reco-closure", "reco_record": relative(closure_record), "summary": relative(closure_summary), "pull_observable": "pull", "residual_observable": "residual", "rigidity_GV": 1000.0, "particle": "mu-"},
                  {"benchmark": "multiple-scattering-reference", "g4sim": True, "element_spec": relative(shim), "crossings": relative(references["nominal"][1]), "measuring_plane": "Plane", "material": "G4_Si", "particle": "proton", "momentum_MeV": RIGIDITY_GV * 1000.0, "thickness_mm": PLANE_MM, "slab": "sensor", "target_slabs": ["telescope"], "control_rule": "declared-size/1", "run_record": relative(study.runs["ms-nominal"]),
                   "tolerance": {"reference_accuracy_relative": 0.02, "k_sigma": 3.0, "reference_source": "Lynch and Dahl, NIM B 58 (1991) 6, '2% or better' against Moliere (abstract; PDG 1998 section 23.3, page read 2026-10-24)"},
                   "negative_controls": []}]
    configuration.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json", "benchmarks": conditions}, indent=1) + "\n", encoding="utf-8")
    # declared-size/1: the controls are sized from the nominal run alone, before they run
    plan = go([BENCH, "plan-controls", "--config", configuration, "--benchmark", "multiple-scattering-reference"])
    controls = {"plus" if item["sign"] == "+" else "minus": item["injected_relative"] for item in plan["controls"]}
    references.update({name: study.scattering_files(name, 1 + injected, RIGIDITY_GV * 1000, scatter) for name, injected in controls.items()})
    conditions[-1]["negative_controls"] = [{"crossings": relative(references[name][1]), "run_record": relative(study.runs[f"ms-{name}"]), "injected": f"slab density x {1 + injected:.6f}", "injected_relative": injected} for name, injected in controls.items()]
    configuration.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json", "benchmarks": conditions}, indent=1) + "\n", encoding="utf-8")
    bench = studies / "bench.results.json"
    go([BENCH, "run", "--config", configuration, "--out", bench], (0, 1, 3))
    go([RUN, "table", "--reco-record", reco_record, "--figure-of-merit", FIGURE, "--observable", "core", *denominator, "--out", studies / "table.dataset-record.json", "--id", "TRK", "--f4-results", studies / "f4-results.json", "--geometry", geometry, "--project-root", art, "--created", "2026-11-07",
        *[word for name, value in variation_records.items() for word in ("--variation", f"{name}={value}")]])
    record_path = studies / "study.computational-run.json"
    label = go([CHECK, "label", "--spec", spec_path, "--benchmarks", bench, "--convergence", studies / "convergence.json", "--variations", studies / "variations.json", *[word for value in study.runs.values() for word in ("--run-record", value)], "--project-root", art, "--results", studies / "f4-results.json", "--geometry", geometry, "--upgrade", "--write", record_path, "--created", "2026-11-07"], (0, 1, 3))
    go([EVALUATE, "f4", "--artifacts", art, "--candidate", CANDIDATE, "--figure-of-merit", FIGURE, *denominator, "--study", record_path.relative_to(art), "--id", EVALUATION])
    verdicts = {"faithful": design_view(art), **{name: corrupted(root, art, change) for name, change in CORRUPTIONS.items()}}
    results = {"evaluation": verdicts, "benchmarks": {item["benchmark"]: item["verdict"] for item in json.loads(bench.read_text(encoding="utf-8"))["benchmarks"]}, "label": label.get("highest_usable_label"), "gaps": label.get("gaps"), "upgrade": label.get("upgrade")}
    held = results["label"] == "validated-in-scope" and accepted(verdicts["faithful"]) and not any(accepted(verdicts[name]) for name in CORRUPTIONS)
    print(json.dumps({"status": "ok" if held else "failed", **results}, indent=1))
    return 0 if held else 1


if __name__ == "__main__":
    sys.exit(main())

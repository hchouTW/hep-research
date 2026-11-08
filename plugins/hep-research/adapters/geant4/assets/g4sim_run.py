#!/usr/bin/env python3
"""The driver of g4sim_run (g4sim plan, Section 8): check-spec, dataset control, the identities, and one run of the program with its record.

Usage: g4sim_run.py check-spec --run RUN.json [--detector DETECTOR.json]
       g4sim_run.py run --detector D.json --request R.json --run RUN.json --record PROBE.json --program PATH --work DIR
       g4sim_run.py geometry-check --detector D.json --run RUN.json --program PATH --work DIR
check-spec holds the checks of Geant4 behavior (Appendix B); S2 has three: nothing may call SetSurfaceTolerance, the run card's seeding must
equal the legacy block's, and optical physics (S7) comes only through G4OpticalPhysics with separated accounting. run needs a re-acquisition record for the legacy block (T1 class).
A project with agent_policy, or --protected, runs this in protected mode. Prints JSON with a status key. Exit 0 ok, 1 the run failed,
2 refused or bad input, 3 a missing dataset.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import g4sim_physics_check as physics_check  # noqa: E402
import g4sim_simulate as simulate_new  # noqa: E402
import g4sim_translate as translate  # noqa: E402
from contracts import KNOWN_CAPABILITIES, geometry  # noqa: E402
from core import constants  # noqa: E402
from core.canonical import canonical_sha256, require_hash_scope  # noqa: E402
from core.geometry import identity  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

DATASETS = ROOT / "contracts/rules/geant4_datasets.json"
SURFACE_TOLERANCE = re.compile(r"surface.?tolerance|world.?maximum.?extent", re.IGNORECASE)
OPTICAL = re.compile(r"optical", re.IGNORECASE)
OPTICAL_CONSTRUCTOR = "G4OpticalPhysics"
TIMING_FIELDS = ("wall_seconds", "cpu_seconds", "startup_seconds", "threads", "load_at_start")
BEAM_ON_MARK = "G4SIM_BEAM_ON "
MERGE_MARK = "G4SIM_MERGE_SECONDS "
OVERLAP_MARK = "GeomVol1002"
ATOMIC_MASS_TOLERANCE = 1e-3  # natural mixtures and table editions differ below this; a swapped element differs by far more
KEPT = ("events.csv", "summary.json", "column_map.json", "materials.json", "conservation.csv", "probe-v2.json")


def check_card(card: dict, legacy: dict | None = None) -> list[dict]:
    """The findings of check-spec: an empty list passes."""
    findings = []
    physics = card.get("physics", {})
    commands = card.get("ui_commands") or []
    for command in commands:
        if SURFACE_TOLERANCE.search(command):
            findings.append({"code": "surface-tolerance", "path": "ui_commands", "message": f"would call SetSurfaceTolerance: {command}"})
        if OPTICAL.search(command):  # optical settings come through the run card, where check-spec sees them
            findings.append({"code": "optical-ui-command", "path": "ui_commands", "message": f"optical settings belong in physics.optical, not a UI command: {command}"})
    for key, value in physics.items():
        if SURFACE_TOLERANCE.search(key):
            findings.append({"code": "surface-tolerance", "path": f"physics.{key}", "message": "would call SetSurfaceTolerance"})
    for name in (*physics.get("extra_constructors", ()), physics.get("reference_list") or "", physics.get("em_constructor") or ""):
        if OPTICAL.search(name) and name != OPTICAL_CONSTRUCTOR:
            findings.append({"code": "optical-constructor", "path": "physics", "message": f"optical physics comes only through {OPTICAL_CONSTRUCTOR}: {name}"})
    if OPTICAL_CONSTRUCTOR in physics.get("extra_constructors", ()):
        # the optical-photon class of Section 8.4 exists only in separated accounting; legacy accounting would book photons as ordinary tracks
        if card.get("accounting") != "separated":
            findings.append({"code": "optical-class-missing", "path": "accounting", "message": "optical physics needs separated accounting, which holds the optical-photon class"})
        if legacy is not None:
            findings.append({"code": "optical-legacy", "path": "physics", "message": "legacy mode keeps the old programs, which have no optical physics"})
    elif "optical" in physics:
        findings.append({"code": "optical-without-constructor", "path": "physics.optical", "message": f"physics.optical needs {OPTICAL_CONSTRUCTOR} in extra_constructors"})
    if legacy is not None and card.get("run", {}).get("seeding") != legacy.get("seeding"):
        findings.append({"code": "seeding-differs", "path": "run.seeding",
                         "message": f"the run card says {card.get('run', {}).get('seeding')!r}, the legacy block {legacy.get('seeding')!r}"})
    return findings + physics_check.card_findings(card)


def physics_list(card: dict) -> str:
    physics = card["physics"]
    return physics.get("reference_list") or physics.get("em_constructor") or ""


def missing_datasets(card: dict, environment: dict | None = None) -> list[str]:
    """Datasets the physics list requires and the environment does not hold (Section 8.10). Unknown list: refused by the caller."""
    environment = os.environ if environment is None else environment
    table = json.loads(DATASETS.read_text(encoding="utf-8"))["physics_lists"]
    name = physics_list(card)
    if name not in table:
        raise ValueError(f"physics list {name!r} is not in contracts/rules/geant4_datasets.json")
    return [variable for variable in table[name] if not (variable in environment and Path(environment[variable]).is_dir()
                                                         and any(Path(environment[variable]).iterdir()))]


def run_id(geometry_identity: str, request_identity: str, card: dict, build_hash: str) -> str:
    document = identity.in_decimals({"geometry_id": geometry_identity, "request_id": request_identity, "run_card": card, "build_hash": build_hash})
    require_hash_scope(document)
    return canonical_sha256(document)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def record_problems(record: dict) -> list[str]:
    """A run record without its times is refused: the cost of a job is the sum of recorded times (g4sim-execution-plan.md, Section 2)."""
    return [f"run record lacks {field}" for field in TIMING_FIELDS if not isinstance(record.get(field), (int, float))]


def startup_seconds(log: Path, started_epoch: float) -> float:
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith(BEAM_ON_MARK):
                return round(float(line[len(BEAM_ON_MARK):]) - started_epoch, 3)
    return 0.0


def merge_seconds(log: Path) -> float:
    with log.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith(MERGE_MARK):
                return float(line[len(MERGE_MARK):])
    return 0.0


def read_record(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def run(args) -> dict:
    detector_text = args.detector.read_bytes()
    detector, request, card = (json.loads(path.read_text(encoding="utf-8")) for path in (args.detector, args.request, args.run))
    checked = geometry.check_spec(detector_text, folder=args.detector.parent)
    if checked["status"] != "ok":
        return {"status": "rejected", "findings": checked["findings"]}
    if checked.get("field_map_files"):  # legacy mode keeps the old programs' fields (Section 6.2.8)
        return {"status": "rejected", "findings": [{"code": "field-map-legacy", "path": "/fields", "message": "a field map is not available in legacy mode"}]}
    old = translate.merge(detector, request, card)
    block = translate.legacy_block(read_record(args.record), old, card["run"]["seeding"], args.observer_revision)
    findings = check_card(card, block)
    if findings:
        return {"status": "rejected", "findings": findings}
    missing = missing_datasets(card)
    if missing:
        return {"status": "missing-dataset", "missing": missing}
    ir = checked["ir"]
    ir["physical"]["legacy"] = block
    geometry_identity = identity.geometry_id(ir)
    request_identity = identity.request_id(identity.identified_request(request, ir), geometry_identity)
    build_hash = _sha256(args.program)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    (work / "ir.json").write_text(json.dumps(ir), encoding="utf-8")
    old.setdefault("output", {}).update({"csv": str(work / "events.csv"), "materials": str(work / "materials.json"),
                                         "datapaths": str(work / "datapaths.json")})
    (work / "spec.json").write_text(json.dumps(old), encoding="utf-8")
    load, started, begun = os.getloadavg()[0], time.time(), time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (work / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(args.program.resolve()), "ir.json", "spec.json"], cwd=work, stdout=log, stderr=log, check=False).returncode
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = {"status": "ok" if code == 0 else "failed", "exit_status": code, "wall_seconds": round(time.perf_counter() - begun, 3),
              "cpu_seconds": round(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, 3),
              "startup_seconds": startup_seconds(work / "log.txt", started), "merge_seconds": merge_seconds(work / "log.txt"), "threads": card["run"].get("threads", 1), "load_at_start": round(load, 2),
              "extension": {"geometry": {"geometry_id": geometry_identity, "provenance_id": identity.provenance_id(ir), "request_id": request_identity,
                                         "run_id": run_id(geometry_identity, request_identity, card, build_hash), "build_hash": build_hash,
                                         "installed_features": {"datasets": sorted(json.loads(DATASETS.read_text(encoding="utf-8"))["physics_lists"][physics_list(card)])}}},
              "output_hashes": {name: _sha256(work / name) for name in KEPT if (work / name).is_file()}}
    if code == 0 and (work / "column_map.json").is_file():
        record["missing_columns"] = missing_columns(json.loads((work / "column_map.json").read_text(encoding="utf-8")), event_header(work / "events.csv"))
        if record["missing_columns"]:
            record["status"] = "failed"
    problems = record_problems(record)
    if problems:
        return {"status": "failed", "problems": problems}
    (work / "run-record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


SOLID_FIELDS = {"G4Trd": (("half_x1_mm", "dx1_mm"), ("half_x2_mm", "dx2_mm"), ("half_y1_mm", "dy1_mm"), ("half_y2_mm", "dy2_mm"), ("half_z_mm", "dz_mm")),
                "G4Tubs": (("rmin_mm", "rmin_mm"), ("rmax_mm", "rmax_mm"), ("half_z_mm", "dz_mm"))}
PRISM_RADIUS_TOLERANCE_MM = 1e-9
TUBE_ANGLE_TOLERANCE_RAD = 1e-12  # the IR holds degrees, Geant4 radians: the conversion is not exact


def _angle_problems(name: str, held: dict, solid: dict, pairs: tuple) -> list[str]:
    """Angles Geant4 holds in radians against the IR's degrees; a start may sit a whole turn away."""
    problems = []
    for key, source in pairs:
        turn = (float.fromhex(held[key]) - math.radians(float(solid[source]))) / math.tau
        if abs(turn - (round(turn) if key.startswith("start") else 0)) * math.tau > TUBE_ANGLE_TOLERANCE_RAD:
            problems.append(f"logical {name}: {key} differs")
    return problems


def s7_solid_problems(name: str, shape: str, solid: dict, curved: dict | None, polyhedron: dict | None) -> list[str]:
    """S7's shapes as Geant4 built them (ProbeV2's curved_solids and polyhedra): lengths bit for bit, angles to 1e-12 rad, and a
    polyhedra's corners at the circumradii, which proves the apothem conversion (GB23)."""
    if shape == "polyhedra":
        if polyhedron is None or polyhedron["sides"] != solid["sides"]:
            return [f"logical {name}: the polyhedra was not written back with {solid['sides']} sides"]
        got = sorted(float.fromhex(value) for value in polyhedron["corners_r_mm"])
        want = sorted(float(value) for value in solid["circumradius_rmin_mm"] + solid["circumradius_rmax_mm"])
        if len(got) != len(want) or any(abs(a - b) > PRISM_RADIUS_TOLERANCE_MM for a, b in zip(got, want)):
            return [f"logical {name}: its corners are at {got} mm, the circumradii are {want}"]
        return []
    wanted = {"cone": "G4Cons", "sphere_section": "G4Sphere", "polycone": "G4Polycone"}[shape]
    if curved is None or curved["type"] != wanted:
        return [f"logical {name}: no {wanted} was written back"]
    if shape == "cone":
        problems = [f"logical {name}: {key} differs" for key, source in (("rmin1_mm", "rmin1_mm"), ("rmax1_mm", "rmax1_mm"), ("rmin2_mm", "rmin2_mm"), ("rmax2_mm", "rmax2_mm"), ("half_z_mm", "dz_mm")) if float.fromhex(curved[key]) != float(solid[source])]
        return problems + _angle_problems(name, curved, solid, (("start_phi_rad", "phi_start_deg"), ("delta_phi_rad", "phi_span_deg")))
    if shape == "sphere_section":
        problems = [f"logical {name}: {key} differs" for key in ("rmin_mm", "rmax_mm") if float.fromhex(curved[key]) != float(solid[key])]
        return problems + _angle_problems(name, curved, solid, (("start_phi_rad", "phi_start_deg"), ("delta_phi_rad", "phi_span_deg"), ("start_theta_rad", "theta_start_deg"), ("delta_theta_rad", "theta_span_deg")))
    got = sorted((float.fromhex(r), float.fromhex(z)) for r, z in curved["corners"])
    want = sorted([(float(r), float(z)) for r, z in zip(solid["rmax_mm"], solid["z_mm"])] + [(float(r), float(z)) for r, z in zip(solid["rmin_mm"], solid["z_mm"])])
    if got != want:
        return [f"logical {name}: its (r, z) corners {got} are not the planes' {want}"]
    return []


def solid_problems(item: dict, node: dict, polyhedron: dict | None, curved: dict | None = None) -> list[str]:
    """The solid Geant4 built against the IR: bit for bit in lengths; a prism's corners at its circumradius, which proves the apothem conversion."""
    shape, solid, name = node["shape"], node.get("solid"), item["name"]
    if shape in ("cone", "sphere_section", "polycone", "polyhedra"):
        return s7_solid_problems(name, shape, solid, curved, polyhedron)
    if shape == "polygon_prism":
        if polyhedron is None or polyhedron["sides"] != solid["sides"]:
            return [f"logical {name}: the prism was not written back with {solid['sides']} sides"]
        wanted = float(solid["circumradius_mm"])
        reach = max(float.fromhex(value) for value in polyhedron["corners_r_mm"])  # a solid prism also has corners on its axis
        return [] if abs(reach - wanted) <= PRISM_RADIUS_TOLERANCE_MM else [f"logical {name}: its outer corners are at {reach} mm, the circumradius is {wanted}"]
    parameters = item["solid"]["parameters"]
    if shape == "box":
        return [f"logical {name}: {key} differs" for key, half in zip(("half_x_mm", "half_y_mm", "half_z_mm"), node["half_mm"]) if float.fromhex(parameters[key]) != float(half)]
    problems = [f"logical {name}: {key} differs" for key, source in SOLID_FIELDS[item["solid"]["type"]] if float.fromhex(parameters[key]) != float(solid[source])]
    if shape == "tube":
        for key, source in (("start_phi_rad", "phi_start_deg"), ("delta_phi_rad", "phi_span_deg")):
            turn = (float.fromhex(parameters[key]) - math.radians(float(solid[source]))) / math.tau  # G4Tubs may hold the start a whole turn away
            if abs(turn - (round(turn) if key == "start_phi_rad" else 0)) * math.tau > TUBE_ANGLE_TOLERANCE_RAD:
                problems.append(f"logical {name}: {key} differs")
    return problems


OPTICAL_RELATIVE_TOLERANCE = 1e-12  # energies pass through Geant4's eV: x * eV / eV need not return x exactly
SURFACE_ENUMS = {"model": {"glisur": 0, "unified": 1},
                 "finish": {"polished": 0, "polishedfrontpainted": 1, "polishedbackpainted": 2, "ground": 3, "groundfrontpainted": 4, "groundbackpainted": 5},
                 "type": {"dielectric_metal": 0, "dielectric_dielectric": 1}}


def expected_optical_table(material: dict) -> dict:
    """What OpticalTable (Optics.hh) builds from an IR material: {property: spectrum or number}, in the units of the write-back."""
    table = {}
    optical = material.get("optical", {})
    for key, source in (("RINDEX", "rindex"), ("ABSLENGTH", "absorption_length_mm"), ("RAYLEIGH", "rayleigh_length_mm")):
        if source in optical:
            table[key] = optical[source]
    if "mie" in optical:
        table.update({"MIEHG": optical["mie"]["length_mm"], "MIEHG_FORWARD": optical["mie"]["forward_g"],
                      "MIEHG_BACKWARD": optical["mie"]["backward_g"], "MIEHG_FORWARD_RATIO": optical["mie"]["forward_ratio"]})
    if "wls" in optical:
        table.update({"WLSABSLENGTH": optical["wls"]["absorption_length_mm"], "WLSCOMPONENT": optical["wls"]["emission"],
                      "WLSTIMECONSTANT": optical["wls"]["time_constant_ns"]})
    components = material.get("scintillation", {}).get("components")
    if components:
        table.update({"SCINTILLATIONYIELD": material["scintillation"]["yield_per_MeV"], "RESOLUTIONSCALE": material["scintillation"]["resolution_scale"]})
        for number, component in enumerate(components, start=1):
            table.update({f"SCINTILLATIONCOMPONENT{number}": component["spectrum"], f"SCINTILLATIONTIMECONSTANT{number}": component["decay_ns"],
                          f"SCINTILLATIONRISETIME{number}": component["rise_ns"], f"SCINTILLATIONYIELD{number}": component["fraction"]})
    return table


def _close(held: str, wanted) -> bool:
    got, value = float.fromhex(held), float(wanted)
    return abs(got - value) <= OPTICAL_RELATIVE_TOLERANCE * max(abs(value), 1e-300)


def _table_problems(where: str, held: dict, wanted: dict) -> list[str]:
    problems = [f"{where}: {key} is {'missing' if key in wanted else 'not in the IR'}" for key in sorted(set(wanted) ^ set(held))]
    for key in sorted(set(wanted) & set(held)):
        if isinstance(wanted[key], dict):
            pairs = list(zip(held[key]["energy_eV"], wanted[key]["energy_eV"])) + list(zip(held[key]["value"], wanted[key]["value"]))
            if len(held[key]["value"]) != len(wanted[key]["value"]) or not all(_close(a, b) for a, b in pairs):
                problems.append(f"{where}: {key} differs")
        elif not _close(held[key], wanted[key]):
            problems.append(f"{where}: {key} differs")
    return problems


def optical_problems(ir: dict, record: dict) -> list[str]:
    """S7: each material's optical table and each optical surface as Geant4 holds them, against the IR (a wrong refractive index is the
    negative test of Section 15.1)."""
    physical = ir["physical"]
    held = record.get("optical", {"materials": {}, "surfaces": {}})
    problems = []
    used = {node["material"] for node in physical["templates"].values()}
    wanted = {name: expected_optical_table(material) for name, material in physical["materials"].items() if name in used}
    wanted = {name: table for name, table in wanted.items() if table}
    for name in sorted(set(wanted) | set(held["materials"])):
        if name not in held["materials"] or name not in wanted:
            problems.append(f"material {name}: an optical table {'was not built' if name in wanted else 'is not in the IR'}")
            continue
        problems += _table_problems(f"material {name}", held["materials"][name], wanted[name])
    surfaces = physical.get("optical_surfaces", {})
    for name in sorted(set(surfaces) | set(held["surfaces"])):
        if name not in held["surfaces"] or name not in surfaces:
            problems.append(f"surface {name}: {'not built' if name in surfaces else 'not in the IR'}")
            continue
        got, entry = held["surfaces"][name], surfaces[name]
        if ("skin" in entry) != ("skin" in got) or got.get("skin", got.get("border")) != entry.get("skin", entry.get("border")):
            problems.append(f"surface {name}: placed on {got.get('skin', got.get('border'))}, the IR says {entry.get('skin', entry.get('border'))}")
        problems += [f"surface {name}: {key} differs" for key, names in SURFACE_ENUMS.items() if got[key] != names[entry[key]]]
        alpha = math.radians(float(entry.get("sigma_alpha_deg", 0)))
        if abs(float.fromhex(got["sigma_alpha_rad"]) - alpha) > TUBE_ANGLE_TOLERANCE_RAD:
            problems.append(f"surface {name}: sigma_alpha differs")
        problems += _table_problems(f"surface {name}", got["table"], {key.upper(): entry[key] for key in ("reflectivity", "efficiency") if key in entry})
    return problems


def tree_problems(ir: dict, record: dict, field_records: dict) -> list[str]:
    """What the write-back says that the IR does not: placements bit for bit, regions, and each thread's fields (Sections 6.2.8, 6.2.10)."""
    physical = ir["physical"]
    geometry = record["base"]["geometry"]
    problems = []
    logical_names = {item["id"]: item["name"] for item in geometry["logical_volumes"]}
    written = {(logical_names[item["mother_logical"]], item["name"], item["copy_number"]): item
               for item in geometry["placements"] if item["mother_logical"] is not None}
    for placement in physical["placements"]:
        key = (placement["mother"], placement["template"], placement["copy_number"])
        item = written.pop(key, None)
        if item is None:
            problems.append(f"placement {key} was not written back")
            continue
        if [float.fromhex(text) for text in item["translation_mm"]] != [float(text) for text in placement["centre_mm"]]:
            problems.append(f"placement {key}: translation differs")
        wanted = placement["rotation"]
        found = item["rotation"]
        if (wanted is None) != (found is None):
            problems.append(f"placement {key}: rotation differs")
        # the IR holds the passive matrix G4PVPlacement takes; the probe writes the object's rotation, which is its transpose
        elif wanted is not None and [float.fromhex(text) for text in found] != [float(row[column]) for column in range(3) for row in wanted]:
            problems.append(f"placement {key}: rotation differs")
    problems += [f"placement {key} is not in the IR" for key in written]
    polyhedra = {item["logical"]: item for item in record.get("polyhedra", [])}
    curved = {item["logical"]: item for item in record.get("curved_solids", [])}
    for item in geometry["logical_volumes"]:
        node = physical["templates"].get(item["name"])
        if node is None:
            problems.append(f"logical {item['name']} is not in the IR")
            continue
        problems += solid_problems(item, node, polyhedra.get(item["name"]), curved.get(item["name"]))
        if node["region"] != "default" and item["region"] != node["region"]:
            problems.append(f"logical {item['name']}: region {item['region']}, the IR says {node['region']}")
    for thread, rows in field_records.items():
        for name, node in physical["templates"].items():
            wanted = "none" if node["field"] == "none" else "field"
            if rows.get(name) != wanted:
                problems.append(f"thread {thread}, logical {name}: field {rows.get(name)}, the IR says {wanted}")
    return problems


def missing_columns(column_map: dict, header: str) -> list[str]:
    """Columns the column map declares for the event file that the file's header does not have (S2 gate 2)."""
    present = set(header.strip().split(","))
    return [item["column"] for item in column_map["columns"] if item.get("file") == "csv" and item["column"] not in present]


def event_header(path: Path) -> str:
    with path.open(encoding="utf-8") as stream:
        next(stream)
        return next(stream)


def material_problems(record: dict, table=None) -> list[str]:
    """The material table Geant4 used against core/constants (Section 8.10): each element's Z and atomic mass."""
    table = constants.element if table is None else table
    problems = []
    for material in record["base"]["geometry"]["materials"]:
        for item in material["elements"]:
            z = round(float.fromhex(item["z"]))
            mass = float.fromhex(item["a_g_mole"])
            entry = table(item["symbol"])
            wanted = float(entry["pdg_atomic_mass"].split("(")[0])
            if z != entry["Z"] or abs(mass - wanted) > ATOMIC_MASS_TOLERANCE * wanted:
                problems.append(f"material {material['name']}: element {item['symbol']} has Z={z}, A {mass}; core/constants says Z={entry['Z']}, A {wanted}")
    return problems


def overlaps_in_log(log: Path) -> int:
    return log.read_text(encoding="utf-8", errors="replace").count(OVERLAP_MARK)


def read_field_records(folder: Path) -> dict:
    records = {}
    for path in sorted(folder.glob("field-managers.thread*.txt")):
        records[path.name] = {line.split()[0]: line.split()[1] for line in path.read_text(encoding="utf-8").splitlines()}
    return records


def geometry_check(args) -> dict:
    card = json.loads(args.run.read_text(encoding="utf-8"))
    checked = geometry.check_spec(args.detector.read_bytes(), folder=args.detector.parent)
    if checked["status"] != "ok":
        return {"status": "rejected", "findings": checked["findings"]}
    findings = check_card(card)
    if findings:
        return {"status": "rejected", "findings": findings}
    missing = missing_datasets(card)
    if missing:
        return {"status": "missing-dataset", "missing": missing}
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    (work / "ir.json").write_text(json.dumps(checked["ir"]), encoding="utf-8")
    (work / "run.json").write_text(json.dumps(card), encoding="utf-8")
    staged = simulate_new.stage_field_maps(checked, work)
    with (work / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(args.program.resolve()), "--geometry-check", "ir.json", "run.json"], cwd=work, stdout=log, stderr=log, check=False).returncode
    if code != 0:
        return {"status": "failed", "exit_status": code}
    record = read_record(work / "probe-v2.json")
    problems = tree_problems(checked["ir"], record, read_field_records(work)) + material_problems(record) + optical_problems(checked["ir"], record) + simulate_new.field_sample_problems(staged, work)
    overlaps = overlaps_in_log(work / "log.txt")
    if overlaps:
        problems.append(f"Geant4's overlap test reported {overlaps} overlap(s)")
    effective = {"geometry_id": checked["geometry_id"], "provenance_id": checked["provenance_id"], "run_card_sha256": _sha256(args.run),
                 "surface_tolerance_mm": (work / "tolerance.txt").read_text(encoding="utf-8").strip()}
    (work / "effective-config.json").write_text(json.dumps(effective, indent=1) + "\n", encoding="utf-8")
    return {"status": "failed" if problems else "ok", "problems": problems[:20], **effective}


def simulate(args) -> dict:
    """A run of a new specification: `separated` accounting, sources and scorers (Section 8)."""
    card = json.loads(args.run.read_text(encoding="utf-8"))
    request = json.loads(args.request.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8")) if getattr(args, "claims", None) else []
    checked = geometry.check_file(args.detector, claims, protected=args.protected)
    if checked["status"] != "ok":
        return {"status": "rejected", "findings": checked["findings"]}
    findings = check_card(card)
    if findings:
        return {"status": "rejected", "findings": findings}
    missing = missing_datasets(card)
    if missing:
        return {"status": "missing-dataset", "missing": missing}
    return simulate_new.simulate(card, request, checked, args.program.resolve(), args.work.resolve(), folder=args.request.resolve().parent)


@protected_main("adapters.geant4.g4sim_run", capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check-spec")
    check.add_argument("--run", type=Path, required=True)
    check.add_argument("--legacy-seeding")
    check.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    execute = commands.add_parser("run")
    for name in ("detector", "request", "run", "record", "program", "work"):
        execute.add_argument(f"--{name}", type=Path, required=True)
    execute.add_argument("--observer-revision", default="current")
    execute.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    shape = commands.add_parser("geometry-check")
    for name in ("detector", "run", "program", "work"):
        shape.add_argument(f"--{name}", type=Path, required=True)
    shape.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    simulating = commands.add_parser("simulate")
    for name in ("detector", "request", "run", "program", "work"):
        simulating.add_argument(f"--{name}", type=Path, required=True)
    simulating.add_argument("--claims", type=Path, help="a JSON list of the claim ids of the profiles the specification depends on, as contracts/geometry.py --claims")
    simulating.add_argument("--protected", action="store_true", help="protected mode (a project with agent_policy needs no flag)")
    args = parser.parse_args(argv)
    guard(f"adapters.geant4.g4sim_run.{args.command}", paths=[str(args.run)], flag=args.protected, capabilities=KNOWN_CAPABILITIES)
    try:
        if args.command == "check-spec":
            card = json.loads(args.run.read_text(encoding="utf-8"))
            findings = check_card(card, {"seeding": args.legacy_seeding} if args.legacy_seeding else None)
            print(json.dumps({"status": "rejected" if findings else "ok", "findings": findings}))
            return 2 if findings else 0
        result = {"geometry-check": geometry_check, "simulate": simulate, "run": run}[args.command](args)
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    print(json.dumps(result))
    return {"ok": 0, "failed": 1, "missing-dataset": 3}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())

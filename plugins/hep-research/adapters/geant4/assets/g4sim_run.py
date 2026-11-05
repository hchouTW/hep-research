#!/usr/bin/env python3
"""The driver of g4sim_run (g4sim plan, Section 8): check-spec, dataset control, the identities, and one run of the program with its record.

Usage: g4sim_run.py check-spec --run RUN.json [--detector DETECTOR.json]
       g4sim_run.py run --detector D.json --request R.json --run RUN.json --record PROBE.json --program PATH --work DIR
       g4sim_run.py geometry-check --detector D.json --run RUN.json --program PATH --work DIR
check-spec holds the checks of Geant4 behavior (Appendix B); S2 has three: nothing may call SetSurfaceTolerance, the run card's seeding must
equal the legacy block's, and optical physics is refused before S7. run needs a re-acquisition record for the legacy block (T1 class).
A project with agent_policy, or --protected, runs this in protected mode. Prints JSON with a status key. Exit 0 ok, 1 the run failed,
2 refused or bad input, 3 a missing dataset.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
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

import g4sim_translate as translate  # noqa: E402
from contracts import KNOWN_CAPABILITIES, geometry  # noqa: E402
from core.canonical import canonical_sha256, require_hash_scope  # noqa: E402
from core.geometry import identity  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

DATASETS = ROOT / "contracts/rules/geant4_datasets.json"
SURFACE_TOLERANCE = re.compile(r"surface.?tolerance|world.?maximum.?extent", re.IGNORECASE)
OPTICAL = re.compile(r"optical", re.IGNORECASE)
TIMING_FIELDS = ("wall_seconds", "cpu_seconds", "startup_seconds", "threads", "load_at_start")
BEAM_ON_MARK = "G4SIM_BEAM_ON "
KEPT = ("events.csv", "summary.json", "column_map.json", "materials.json", "conservation.csv", "probe-v2.json")


def check_card(card: dict, legacy: dict | None = None) -> list[dict]:
    """The findings of check-spec: an empty list passes."""
    findings = []
    physics = card.get("physics", {})
    commands = card.get("ui_commands") or []
    for command in commands:
        if SURFACE_TOLERANCE.search(command):
            findings.append({"code": "surface-tolerance", "path": "ui_commands", "message": f"would call SetSurfaceTolerance: {command}"})
        if OPTICAL.search(command):
            findings.append({"code": "optical-before-s7", "path": "ui_commands", "message": f"optical physics is refused before S7: {command}"})
    for key, value in physics.items():
        if SURFACE_TOLERANCE.search(key):
            findings.append({"code": "surface-tolerance", "path": f"physics.{key}", "message": "would call SetSurfaceTolerance"})
    for name in (*physics.get("extra_constructors", ()), physics.get("reference_list") or "", physics.get("em_constructor") or ""):
        if OPTICAL.search(name):
            findings.append({"code": "optical-before-s7", "path": "physics", "message": f"optical physics is refused before S7: {name}"})
    if legacy is not None and card.get("run", {}).get("seeding") != legacy.get("seeding"):
        findings.append({"code": "seeding-differs", "path": "run.seeding",
                         "message": f"the run card says {card.get('run', {}).get('seeding')!r}, the legacy block {legacy.get('seeding')!r}"})
    return findings


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


def in_decimals(value):
    """A translated document for hashing: a float becomes its repr, the decimal string the translator writes (no binary float in the hash scope)."""
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, dict):
        return {key: in_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [in_decimals(item) for item in value]
    return value


def request_id(request: dict, geometry_identity: str) -> str:
    document = in_decimals({"request": request, "geometry_id": geometry_identity})
    require_hash_scope(document)
    return canonical_sha256(document)


def run_id(geometry_identity: str, request_identity: str, card: dict, build_hash: str) -> str:
    document = in_decimals({"geometry_id": geometry_identity, "request_id": request_identity, "run_card": card, "build_hash": build_hash})
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


def read_record(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def run(args) -> dict:
    detector_text = args.detector.read_bytes()
    detector, request, card = (json.loads(path.read_text(encoding="utf-8")) for path in (args.detector, args.request, args.run))
    checked = geometry.check_spec(detector_text)
    if checked["status"] != "ok":
        return {"status": "rejected", "findings": checked["findings"]}
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
    request_identity = request_id(request, geometry_identity)
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
              "startup_seconds": startup_seconds(work / "log.txt", started), "threads": card["run"].get("threads", 1), "load_at_start": round(load, 2),
              "extension": {"geometry": {"geometry_id": geometry_identity, "provenance_id": identity.provenance_id(ir), "request_id": request_identity,
                                         "run_id": run_id(geometry_identity, request_identity, card, build_hash), "build_hash": build_hash,
                                         "installed_features": {"datasets": sorted(json.loads(DATASETS.read_text(encoding="utf-8"))["physics_lists"][physics_list(card)])}}},
              "output_hashes": {name: _sha256(work / name) for name in KEPT if (work / name).is_file()}}
    problems = record_problems(record)
    if problems:
        return {"status": "failed", "problems": problems}
    (work / "run-record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


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
    for item in geometry["logical_volumes"]:
        node = physical["templates"].get(item["name"])
        if node is None:
            problems.append(f"logical {item['name']} is not in the IR")
        elif node["region"] != "default" and item["region"] != node["region"]:
            problems.append(f"logical {item['name']}: region {item['region']}, the IR says {node['region']}")
    for thread, rows in field_records.items():
        for name, node in physical["templates"].items():
            wanted = "none" if node["field"] == "none" else "field"
            if rows.get(name) != wanted:
                problems.append(f"thread {thread}, logical {name}: field {rows.get(name)}, the IR says {wanted}")
    return problems


def read_field_records(folder: Path) -> dict:
    records = {}
    for path in sorted(folder.glob("field-managers.thread*.txt")):
        records[path.name] = {line.split()[0]: line.split()[1] for line in path.read_text(encoding="utf-8").splitlines()}
    return records


def geometry_check(args) -> dict:
    card = json.loads(args.run.read_text(encoding="utf-8"))
    checked = geometry.check_spec(args.detector.read_bytes())
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
    with (work / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(args.program.resolve()), "--geometry-check", "ir.json", "run.json"], cwd=work, stdout=log, stderr=log, check=False).returncode
    if code != 0:
        return {"status": "failed", "exit_status": code}
    record = read_record(work / "probe-v2.json")
    problems = tree_problems(checked["ir"], record, read_field_records(work))
    effective = {"geometry_id": checked["geometry_id"], "provenance_id": checked["provenance_id"], "run_card_sha256": _sha256(args.run),
                 "surface_tolerance_mm": (work / "tolerance.txt").read_text(encoding="utf-8").strip()}
    (work / "effective-config.json").write_text(json.dumps(effective, indent=1) + "\n", encoding="utf-8")
    return {"status": "failed" if problems else "ok", "problems": problems[:20], **effective}


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
    args = parser.parse_args(argv)
    guard(f"adapters.geant4.g4sim_run.{args.command}", paths=[str(args.run)], flag=args.protected, capabilities=KNOWN_CAPABILITIES)
    try:
        if args.command == "check-spec":
            card = json.loads(args.run.read_text(encoding="utf-8"))
            findings = check_card(card, {"seeding": args.legacy_seeding} if args.legacy_seeding else None)
            print(json.dumps({"status": "rejected" if findings else "ok", "findings": findings}))
            return 2 if findings else 0
        result = geometry_check(args) if args.command == "geometry-check" else run(args)
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    print(json.dumps(result))
    return {"ok": 0, "failed": 1, "missing-dataset": 3}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())

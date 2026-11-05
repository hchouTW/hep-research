#!/usr/bin/env python3
"""The driver of g4sim_run (g4sim plan, Section 8): check-spec, dataset control, the identities, and one run of the program with its record.

Usage: g4sim_run.py check-spec --run RUN.json [--detector DETECTOR.json]
       g4sim_run.py run --detector D.json --request R.json --run RUN.json --record PROBE.json --program PATH --work DIR
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
    args = parser.parse_args(argv)
    guard(f"adapters.geant4.g4sim_run.{args.command}", paths=[str(args.run)], flag=args.protected, capabilities=KNOWN_CAPABILITIES)
    try:
        if args.command == "check-spec":
            card = json.loads(args.run.read_text(encoding="utf-8"))
            findings = check_card(card, {"seeding": args.legacy_seeding} if args.legacy_seeding else None)
            print(json.dumps({"status": "rejected" if findings else "ok", "findings": findings}))
            return 2 if findings else 0
        result = run(args)
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    print(json.dumps(result))
    return {"ok": 0, "failed": 1, "missing-dataset": 3}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())

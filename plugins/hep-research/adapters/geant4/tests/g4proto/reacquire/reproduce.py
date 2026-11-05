#!/usr/bin/env python3
"""The reproduction check of every recorded run (g4sim plan, Section 7.4; GB2): rebuild each recorded source with the probe,
rerun with the recorded seed and number of events, and compare the outputs with the recorded hashes.

Every output path is redirected below --work, so a reference output cannot be touched. A finished run is kept in results.json and
skipped on the next start; bulky outputs are deleted once hashed, and the probe record is kept compressed. status.json says how far
the job is, what it is running, and the wall time of each finished run, so a job's real cost is on record.

Usage: reproduce.py --facts FACTS.json --states WORK.json --work-root DIR --work DIR [--only TEXT] [--extra-random]
                    [--keep-outputs] [--redo TEXT] [--geant4-config PATH]
From the plugin root. --states is the output of g4sim_inventory.py check-work; --work-root holds the recorded probe records.
--only runs those whose name holds TEXT. --extra-random is the negative test: one extra random number, so reproduction must fail;
its results go to negative.json and never into the table. --keep-outputs keeps the bulky outputs, for looking into a difference.
--redo reruns finished runs whose name holds TEXT. With --only the table is not written, because it would be partial.
A build of a commit is reused on a later start; a partial one is cleared and redone. A build failure is never saved as a run's
result, so a later start tries it again. Prints JSON with a status key. Exit 0 ok, 1 a problem in the table or a build failure.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
COMPARED = ("events.csv", "summary.json", "column_map.json")
REQUIRED = ("events.csv", "summary.json")
# geant4_run.py completes summary.json after the program ends (complete_summary at d9db638c, lines 657-663): these keys of its "run"
# block are not program output, and the recorded hash is the completed file's. Nothing else may differ.
COMPLETED_KEYS = ("completed_by", "data_path_problems", "datasets_content_match", "evidence_role", "run_id", "run_record", "seed_scheme",
                  "settings", "spec_sha256")
SAME_BEFORE_COMPLETION = "same-before-completion"
BULK = ("events.csv", "events.root", "column_map.json", "summary.json", "materials.json", "datapaths.json")


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sampler = _module("g4proto_cost_sample", HERE / "cost_sample.py")
inventory = sampler.inventory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def same_before_completion(rerun: dict, recorded: dict) -> bool:
    """The recorded summary equals the rerun's once the keys the wrapper added are taken out: exactly those, and nothing else."""
    stripped = json.loads(json.dumps(recorded))
    run = stripped.get("run", {})
    if not all(key in run for key in COMPLETED_KEYS) or any(key in rerun.get("run", {}) for key in COMPLETED_KEYS):
        return False
    for key in COMPLETED_KEYS:
        del run[key]
    return stripped == rerun


def output_states(row: dict, folder: Path, work_root: Path | None = None) -> dict:
    """Each compared output of a rerun against its recorded hash: "same", "different", "missing", or, for a summary whose program
    output is equal to the recorded one, "same-before-completion"."""
    states = {}
    for name, expected in row["outputs"].items():
        base = name.rsplit("/", 1)[-1]
        if base in COMPARED:
            path = folder / base
            states[base] = "missing" if not path.is_file() else ("same" if _sha256(path) == expected else "different")
            if base == "summary.json" and states[base] == "different" and work_root is not None:
                reference = work_root / (row["work"] or "").removeprefix(inventory.HOME_PREFIX) / name
                if reference.is_file() and same_before_completion(json.loads(path.read_text(encoding="utf-8")),
                                                                  json.loads(reference.read_text(encoding="utf-8"))):
                    states[base] = SAME_BEFORE_COMPLETION
    return states


def reproduced(states: dict) -> bool:
    """The reference outputs are bit-identical: the column file and the summary wherever they were recorded."""
    checked = [states[name] for name in REQUIRED if name in states]
    return bool(checked) and all(state in ("same", SAME_BEFORE_COMPLETION) for state in checked)


def probe_agrees(existing: dict | None, record: dict):
    """None without an existing probe record; otherwise whether its geometry, materials and user limits equal the new record's."""
    if existing is None:
        return None
    return existing.get("geometry") == record["base"].get("geometry")


def field_visible(record: dict) -> bool:
    return record.get("recorded") is True and not [row for row in record.get("logical_fields", []) if row["source"] == "declared"]


def declared_fields(spec: dict) -> str:
    return ",".join(region["element"] for region in (spec.get("field") or {}).get("regions", []))


def built_executable(folder: Path, program: str) -> Path | None:
    for path in (folder / program, folder / "build" / program):
        if path.is_file():
            return path
    return None


def prepare(row: dict, folder: Path, config: str | None) -> Path:
    """The executable of a run's source: an earlier build if there is one, otherwise a clean one."""
    existing = built_executable(folder, row["program"])
    if existing is not None:
        return existing
    shutil.rmtree(folder, ignore_errors=True)
    assets = sampler.extract(row["source_commit"], folder / "archive")
    source = sampler.apply_probe.apply(row["program"], assets, folder / "src")
    return sampler.build(source, row["program"], folder, config)


def run_one(row: dict, executable: Path, folder: Path, work_root: Path, extra_random: bool, keep_outputs: bool = False) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    spec = sampler.spec_of(row)
    seed_as_recorded = spec["run"]["seeds"] == next(iter(row["seeds"].values()), None) if row.get("seeds") else True
    spec.setdefault("output", {}).update({"csv": str(folder / "events.csv"), "materials": str(folder / "materials.json"),
                                          "datapaths": str(folder / "datapaths.json")})
    (folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    environment = {**os.environ, "G4PROTO_OUT": str(folder), "G4PROTO_DECLARED": declared_fields(spec)}
    if extra_random:
        environment["G4PROTO_EXTRA_RANDOM"] = "1"
    with (folder / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(executable), "spec.json"], cwd=folder, stdout=log, stderr=log, env=environment, check=False).returncode
    states = output_states(row, folder, work_root)
    result = {"exit": code, "built": True, "outputs": states, "reproduced": code == 0 and reproduced(states),
              "seed_as_recorded": seed_as_recorded, "probe_agrees": None, "field_visible": False, "random_state_unchanged": False}
    record_path = folder / "probe-v2.json"
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        existing_name = next((name for name in row["outputs"] if name.endswith("probe.json")), None)
        existing = None
        if existing_name:
            path = work_root / (row["work"] or "").removeprefix(inventory.HOME_PREFIX) / existing_name
            existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        result.update({"probe_agrees": probe_agrees(existing, record), "field_visible": field_visible(record),
                       "random_state_unchanged": record.get("random_state_unchanged") is True})
        with gzip.open(folder / "probe-v2.json.gz", "wt", encoding="utf-8") as stream:
            stream.write(record_path.read_text(encoding="utf-8"))
        record_path.unlink()
    if not keep_outputs:
        for name in BULK:
            (folder / name).unlink(missing_ok=True)
    return result


def write_status(path: Path, total: int, results: dict, current: str | None, started: str) -> None:
    """How far the job is, written atomically, so a reader never sees half a file."""
    wall = sum(item.get("wall_seconds", 0.0) for item in results.values())
    document = {"total": total, "done": len(results), "reproduced": sum(1 for item in results.values() if item.get("reproduced")),
                "current": current, "started": started, "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "wall_seconds": round(wall, 1)}
    scratch = path.with_suffix(".part")
    scratch.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    scratch.replace(path)


def table(rows: list[dict], states: dict, results: dict) -> list[dict]:
    out = []
    for row in rows:
        run_states = states.get(row["run"], {})
        classified = inventory.classify(run_states, results.get(row["run"]))
        out.append({"run": row["run"], "journey": row["journey"], "states": run_states, **classified})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("facts", "states", "work-root", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--extra-random", action="store_true")
    parser.add_argument("--keep-outputs", action="store_true")
    parser.add_argument("--redo", default="")
    parser.add_argument("--geant4-config")
    args = parser.parse_args(argv)
    try:
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        states = json.loads(args.states.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    results_path = work / ("negative.json" if args.extra_random else "results.json")
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.is_file() else {}
    if args.redo:
        results = {run: result for run, result in results.items() if args.redo not in run}
    executables: dict = {}
    build_failures: list = []
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    wanted = sum(1 for row in facts if args.only in row["run"])
    for row in facts:
        if args.only not in row["run"] or row["run"] in results:
            continue
        write_status(work / "status.json", wanted, results, row["run"], started)
        commit = row["source_commit"]
        if commit not in executables:
            try:
                executables[commit] = prepare(row, work / "build" / commit, args.geant4_config)
            except (OSError, ValueError, subprocess.CalledProcessError) as err:
                executables[commit] = None
                build_failures.append(commit)
                print(json.dumps({"build_failed": commit, "error": str(err)[:300]}), flush=True)
        if executables[commit] is None:
            continue
        begun = time.perf_counter()
        results[row["run"]] = run_one(row, executables[commit], work / "runs" / row["run"], args.work_root.expanduser(),
                                      args.extra_random, args.keep_outputs)
        results[row["run"]]["wall_seconds"] = round(time.perf_counter() - begun, 1)
        results_path.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"run": row["run"], "reproduced": results[row["run"]]["reproduced"]}), flush=True)
    write_status(work / "status.json", wanted, results, None, started)
    if args.extra_random:
        print(json.dumps({"status": "ok", "negative": {run: result["reproduced"] for run, result in results.items()}}, indent=1))
        return 0
    if args.only:
        print(json.dumps({"status": "ok" if not build_failures else "failed", "partial": True, "runs_done": len(results),
                          "reproduced": {run: result["reproduced"] for run, result in results.items() if args.only in run}}, indent=1))
        return 1 if build_failures else 0
    rows = table(facts, states, results)
    (work / "inventory.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    tally: dict = {}
    for row in rows:
        tally[str(row["class"])] = tally.get(str(row["class"]), 0) + 1
    problems = inventory.table_problems(rows, facts)
    failed = bool(problems or build_failures)
    print(json.dumps({"status": "failed" if failed else "ok", "runs_done": len(results), "classes": tally, "problems": problems[:10],
                      "build_failures": build_failures}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

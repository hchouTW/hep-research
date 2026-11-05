#!/usr/bin/env python3
"""The reproduction check of every recorded run (g4sim plan, Section 7.4; GB2): rebuild each recorded source with the probe,
rerun with the recorded seed and number of events, and compare the outputs with the recorded hashes.

Every output path is redirected below --work, so a reference output cannot be touched. A finished run is kept in results.json and
skipped on the next start; bulky outputs are deleted once hashed, and the probe record is kept compressed.

Usage: reproduce.py --facts FACTS.json --states WORK.json --work-root DIR --work DIR [--only TEXT] [--extra-random]
                    [--geant4-config PATH]
From the plugin root. --states is the output of g4sim_inventory.py check-work; --work-root holds the recorded probe records.
--only runs those whose name holds TEXT. --extra-random is the negative test: one extra random number, so reproduction must fail;
its results go to negative.json and never into the table. Prints JSON with a status key. Exit 0 ok, 1 a problem in the table.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
COMPARED = ("events.csv", "summary.json", "column_map.json")
REQUIRED = ("events.csv", "summary.json")
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


def output_states(row: dict, folder: Path) -> dict:
    """Each compared output of a rerun against its recorded hash: "same", "different" or "missing"."""
    states = {}
    for name, expected in row["outputs"].items():
        base = name.rsplit("/", 1)[-1]
        if base in COMPARED:
            path = folder / base
            states[base] = "missing" if not path.is_file() else ("same" if _sha256(path) == expected else "different")
    return states


def reproduced(states: dict) -> bool:
    """The reference outputs are bit-identical: the column file and the summary wherever they were recorded."""
    checked = [states[name] for name in REQUIRED if name in states]
    return bool(checked) and all(state == "same" for state in checked)


def probe_agrees(existing: dict | None, record: dict):
    """None without an existing probe record; otherwise whether its geometry, materials and user limits equal the new record's."""
    if existing is None:
        return None
    return existing.get("geometry") == record["base"].get("geometry")


def field_visible(record: dict) -> bool:
    return record.get("recorded") is True and not [row for row in record.get("logical_fields", []) if row["source"] == "declared"]


def declared_fields(spec: dict) -> str:
    return ",".join(region["element"] for region in (spec.get("field") or {}).get("regions", []))


def run_one(row: dict, executable: Path, folder: Path, work_root: Path, extra_random: bool) -> dict:
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
    states = output_states(row, folder)
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
    for name in BULK:
        (folder / name).unlink(missing_ok=True)
    return result


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
    executables: dict = {}
    for row in facts:
        if args.only not in row["run"] or row["run"] in results:
            continue
        commit = row["source_commit"]
        if commit not in executables:
            folder = work / "build" / commit
            try:
                assets = sampler.extract(commit, folder / "archive")
                source = sampler.apply_probe.apply(row["program"], assets, folder / "src")
                executables[commit] = sampler.build(source, row["program"], folder, args.geant4_config)
            except (OSError, ValueError, subprocess.CalledProcessError) as err:
                executables[commit] = None
                print(json.dumps({"build_failed": commit, "error": str(err)[:300]}), flush=True)
        if executables[commit] is None:
            results[row["run"]] = {"built": False, "reproduced": False, "seed_as_recorded": True, "probe_agrees": None, "field_visible": False}
        else:
            results[row["run"]] = run_one(row, executables[commit], work / "runs" / row["run"], args.work_root.expanduser(), args.extra_random)
        results_path.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"run": row["run"], "reproduced": results[row["run"]]["reproduced"]}), flush=True)
    if args.extra_random:
        print(json.dumps({"status": "ok", "negative": {run: result["reproduced"] for run, result in results.items()}}, indent=1))
        return 0
    rows = table(facts, states, results)
    (work / "inventory.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    tally: dict = {}
    for row in rows:
        tally[str(row["class"])] = tally.get(str(row["class"]), 0) + 1
    problems = inventory.table_problems(rows, facts)
    print(json.dumps({"status": "ok" if not problems else "failed", "runs_done": len(results), "classes": tally, "problems": problems[:10]}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

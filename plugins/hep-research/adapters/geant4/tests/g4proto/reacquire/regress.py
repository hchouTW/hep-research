#!/usr/bin/env python3
"""T1 regression of g4sim_run against working baselines of the same platform (g4sim plan, Section 18): each run's legacy block comes from
the baseline's probe record, the run is repeated with g4sim_run, and the output hashes and the volume-tree write-back are compared.

Usage: regress.py --facts FACTS.json --baselines DIR --program PATH --work DIR [--cores N] [--only TEXT] [--keep-outputs]
From the plugin root, in an activated Geant4 environment. Prints JSON with a status key. Exit 0 every run identical, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import baseline
import reproduce

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[4]
sampler = reproduce.sampler
spec_of_module = importlib.util.spec_from_file_location("g4sim_translate", PLUGIN / "adapters/geant4/assets/g4sim_translate.py")
translate = importlib.util.module_from_spec(spec_of_module)
sys.modules["g4sim_translate"] = translate
spec_of_module.loader.exec_module(translate)
EARLY_OBSERVER, EARLY_SOURCES = "layered-early", ("3f4f9985",)  # layered_sim before its leakage-by-face columns
TREE_KEYS = ("positions", "logical_volumes", "materials", "regions", "fields", "processes")


def write_inputs(row: dict, record: dict, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    old = sampler.spec_of(row)
    revision = EARLY_OBSERVER if row["source_commit"] in EARLY_SOURCES else "current"
    block = translate.legacy_block(record, old, translate.split(old)[2]["run"]["seeding"], revision)
    (folder / "ir.json").write_text(json.dumps({"schema": "geometry-ir/1", "physical": {"legacy": block}}), encoding="utf-8")
    old.setdefault("output", {}).update({"csv": str(folder / "events.csv"), "materials": str(folder / "materials.json"),
                                         "datapaths": str(folder / "datapaths.json")})
    (folder / "spec.json").write_text(json.dumps(old), encoding="utf-8")


def tree_differences(expected: dict, record: dict) -> list[str]:
    seeding = "per-event"
    wanted = translate.legacy_block(expected, {"elements": []}, seeding)
    found = translate.legacy_block(record, {"elements": []}, seeding)
    return [key for key in TREE_KEYS if wanted[key] != found[key]]


def run_one(row: dict, reference: dict, record: dict, program: Path, folder: Path, keep: bool = False) -> dict:
    write_inputs(row, record, folder)
    begun = time.perf_counter()
    with (folder / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(program), "ir.json", "spec.json"], cwd=folder, stdout=log, stderr=log, check=False).returncode
    wall = round(time.perf_counter() - begun, 1)
    hashes = {name: reproduce._sha256(folder / name) for name in baseline.HASHED if (folder / name).is_file()}
    same = {name: hashes.get(name) == value for name, value in reference["hashes"].items()}
    written = folder / "probe-v2.json"
    tree = tree_differences(record, json.loads(written.read_text(encoding="utf-8"))) if written.is_file() else ["no write-back"]
    for name in (*reproduce.BULK, "probe-v2.json") if not keep else ():
        (folder / name).unlink(missing_ok=True)
    return {"exit": code, "same": same, "tree_differences": tree, "wall_seconds": wall, "identical": code == 0 and all(same.values()) and not tree}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("facts", "baselines", "program", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--only", default="")
    parser.add_argument("--keep-outputs", action="store_true")
    args = parser.parse_args(argv)
    try:
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        references = json.loads((args.baselines / "baselines.json").read_text(encoding="utf-8"))["runs"]
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    args.work.mkdir(parents=True, exist_ok=True)
    path = args.work / "regression.json"
    results = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    rows = baseline.order([row for row in facts if args.only in row["run"] and row["run"] not in results])
    cores = baseline.Cores(args.cores)

    def work_on(row: dict) -> None:
        with gzip.open(args.baselines / "runs" / row["run"] / "probe-v2.json.gz", "rt", encoding="utf-8") as stream:
            record = json.load(stream)
        taken = cores.take(row.get("threads") or 1)
        try:
            result = run_one(row, references[row["run"]], record, args.program.resolve(), args.work / "runs" / row["run"], args.keep_outputs)
        finally:
            cores.give(taken)
        results[row["run"]] = result
        path.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"run": row["run"], **{k: result[k] for k in ("identical", "exit", "wall_seconds")}}), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.cores) as pool:
        for finished in [pool.submit(work_on, row) for row in rows]:
            finished.result()
    different = sorted(run for run, item in results.items() if not item["identical"])
    print(json.dumps({"status": "failed" if different else "ok", "done": len(results), "different": different[:20]}, indent=1))
    return 1 if different else 0


if __name__ == "__main__":
    sys.exit(main())

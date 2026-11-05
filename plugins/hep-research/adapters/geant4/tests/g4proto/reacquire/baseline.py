#!/usr/bin/env python3
"""Working baselines of the recorded runs on this platform (g4sim-execution-plan.md, Section 1): rebuild each recorded source with the
probe, rerun with the recorded seed and number of events, and record the output hashes, the environment and the time.

A baseline belongs to its platform, so nothing here is compared with the E2 references: that is reproduce.py's work, and S2 gate 4 is
judged against those references. Development regression compares g4sim_run with these records on the same platform.

Usage: baseline.py --facts FACTS.json --work DIR --geant4-config PATH [--cores N] [--only TEXT] [--redo TEXT]
From the plugin root. Runs share --cores (default all), each taking as many as it has threads, longest first. A finished run is kept in
baselines.json and skipped on the next start; bulky outputs are deleted once hashed, and the probe record is kept compressed.
status.json says how far the job is. Prints JSON with a status key. Exit 0 ok, 1 a failed run or build, 2 bad input.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import os
import platform
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path

import reproduce

HASHED = ("events.csv", "summary.json", "column_map.json", "materials.json")
sampler = reproduce.sampler


class Cores:
    """A count of free cores: a run waits until as many as it needs are free."""

    def __init__(self, total: int):
        self.total, self.free, self.changed = total, total, threading.Condition()

    def take(self, count: int) -> int:
        count = min(count, self.total)
        with self.changed:
            self.changed.wait_for(lambda: self.free >= count)
            self.free -= count
        return count

    def give(self, count: int) -> None:
        with self.changed:
            self.free += count
            self.changed.notify_all()


def environment_record(config: str) -> dict:
    """What a baseline belongs to; a comparison across two of these is not a T1 comparison."""
    def printed_by(*command: str) -> str:
        return subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()
    return {"platform": platform.platform(), "machine": platform.machine(), "compiler": printed_by("g++", "--version").splitlines()[0],
            "flags": "-O2 -std=c++17 " + printed_by(config, "--cflags"), "geant4": printed_by(config, "--version"),
            "geant4_prefix": printed_by(config, "--prefix")}


def run_one(row: dict, executable: Path, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    spec = sampler.spec_of(row)
    spec.setdefault("output", {}).update({"csv": str(folder / "events.csv"), "materials": str(folder / "materials.json"),
                                          "datapaths": str(folder / "datapaths.json")})
    (folder / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    environment = {**os.environ, "G4PROTO_OUT": str(folder), "G4PROTO_DECLARED": reproduce.declared_fields(spec)}
    load = os.getloadavg()[0]
    begun, before = time.perf_counter(), resource.getrusage(resource.RUSAGE_CHILDREN)
    with (folder / "log.txt").open("w", encoding="utf-8") as log:
        code = subprocess.run([str(executable), "spec.json"], cwd=folder, stdout=log, stderr=log, env=environment, check=False).returncode
    wall = time.perf_counter() - begun
    hashes = {name: reproduce._sha256(folder / name) for name in HASHED if (folder / name).is_file()}
    record_path = folder / "probe-v2.json"
    if record_path.is_file():
        with gzip.open(folder / "probe-v2.json.gz", "wt", encoding="utf-8") as stream:
            stream.write(record_path.read_text(encoding="utf-8"))
        record_path.unlink()
    for name in reproduce.BULK:
        (folder / name).unlink(missing_ok=True)
    return {"exit": code, "source_commit": row["source_commit"], "seeds": row.get("seeds"), "events": row.get("events"),
            "threads": row.get("threads"), "hashes": hashes, "wall_seconds": round(wall, 1), "load_at_start": round(load, 2),
            "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def order(rows: list[dict]) -> list[dict]:
    """Longest first, by work per core, so the long runs do not end up alone at the end."""
    return sorted(rows, key=lambda row: -(row.get("events") or 0) / max(row.get("threads") or 1, 1))


def write_status(path: Path, total: int, results: dict, running: set, started: str) -> None:
    done_ok = sum(1 for item in results.values() if item["exit"] == 0)
    document = {"total": total, "done": len(results), "ok": done_ok, "current": sorted(running), "started": started,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "wall_seconds": round(sum(i["wall_seconds"] for i in results.values()), 1)}
    scratch = path.with_suffix(".part")
    scratch.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    scratch.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--geant4-config", required=True)
    parser.add_argument("--cores", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--only", default="")
    parser.add_argument("--redo", default="")
    args = parser.parse_args(argv)
    try:
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        environment = environment_record(args.geant4_config)
    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        print(json.dumps({"status": "error", "message": str(err)[:300]}))
        return 2
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    path = work / "baselines.json"
    document = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"environment": environment, "runs": {}}
    if document["environment"] != environment:
        print(json.dumps({"status": "error", "message": "this folder holds baselines of another environment"}))
        return 2
    results = {run: item for run, item in document["runs"].items() if not (args.redo and args.redo in run)}
    wanted = [row for row in facts if args.only in row["run"]]
    pending = order([row for row in wanted if row["run"] not in results])
    executables, failed_builds = {}, []
    for commit in sorted({row["source_commit"] for row in pending}):
        row = next(item for item in pending if item["source_commit"] == commit)
        try:
            executables[commit, row["program"]] = reproduce.prepare(row, work / "build" / f"{commit}-{row['program']}", args.geant4_config)
        except (OSError, ValueError, subprocess.CalledProcessError) as err:
            failed_builds.append(commit)
            print(json.dumps({"build_failed": commit, "error": str(err)[:300]}), flush=True)
    cores, lock, running = Cores(args.cores), threading.Lock(), set()
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    def work_on(row: dict) -> None:
        key = row["source_commit"], row["program"]
        if key not in executables:
            return
        taken = cores.take(row.get("threads") or 1)
        with lock:
            running.add(row["run"])
            write_status(work / "status.json", len(wanted), results, running, started)
        try:
            result = run_one(row, executables[key], work / "runs" / row["run"])
        finally:
            cores.give(taken)
        with lock:
            running.discard(row["run"])
            results[row["run"]] = result
            scratch = path.with_suffix(".part")
            scratch.write_text(json.dumps({"environment": environment, "runs": results}, indent=1) + "\n", encoding="utf-8")
            scratch.replace(path)
            write_status(work / "status.json", len(wanted), results, running, started)
        print(json.dumps({"run": row["run"], "exit": result["exit"], "wall_seconds": result["wall_seconds"]}), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.cores) as pool:
        for finished in [pool.submit(work_on, row) for row in pending]:
            finished.result()
    failed = sorted(run for run, item in results.items() if item["exit"] != 0)
    print(json.dumps({"status": "failed" if failed or failed_builds else "ok", "done": len(results), "failed": failed[:10],
                      "build_failures": failed_builds}, indent=1))
    return 1 if failed or failed_builds else 0


if __name__ == "__main__":
    sys.exit(main())

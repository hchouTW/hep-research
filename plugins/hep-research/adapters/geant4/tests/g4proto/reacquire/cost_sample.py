#!/usr/bin/env python3
"""Timed sample for the rerun cost of the task card (g4sim plan, Section 7.4), before the first re-acquisition build is judged.

For each recorded executable: extract the source at its commit, add the probe, build, and time three of its runs (most events,
median, fewest) at N and at 2N events. The difference gives seconds per event with start-up removed; the slowest of the three
prices every run of that executable, so the estimate is an upper bound, because cost per event differs between run types. N doubles until the difference is at least MINIMUM_DIFFERENCE_S, because a smaller one is start-up
noise; a sample that never gets there is reported as unreliable, never as a small cost. Nothing it writes is a reference output.

Usage: cost_sample.py --facts FACTS.json --work DIR [--events N] [--geant4-config PATH]
From the plugin root. --geant4-config compiles with geant4-config; without it, CMake finds Geant4 from the environment.
Prints JSON with a status key. Exit 0 ok, 1 a sample failed, 2 bad input.
"""
from __future__ import annotations

import argparse
import glob
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
MINIMUM_DIFFERENCE_S = 5.0
MAXIMUM_DOUBLINGS = 12


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_probe = _module("g4proto_apply_probe", HERE / "apply_probe.py")
inventory = _module("g4sim_inventory", PLUGIN / "adapters/geant4/assets/g4sim_inventory.py")


def extract(commit: str, folder: Path) -> Path:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=PLUGIN, capture_output=True, text=True, check=True).stdout.strip()
    folder.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "-C", top, "archive", commit, "plugins/hep-research/adapters/geant4/assets"], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(folder)], input=archive.stdout, check=True)
    return folder / "plugins/hep-research/adapters/geant4/assets"


def build(source: Path, program: str, work: Path, config: str | None) -> Path:
    log = (work / "build.log").open("w", encoding="utf-8")
    if config:
        prefix = subprocess.run([config, "--prefix"], capture_output=True, text=True, check=True).stdout.strip()
        flags = subprocess.run([config, "--cflags"], capture_output=True, text=True, check=True).stdout.split()
        libraries = subprocess.run([config, "--libs"], capture_output=True, text=True, check=True).stdout.split()
        files = sorted(glob.glob(str(source / "*.cc")))
        executable = work / program
        subprocess.run(["g++", "-O2", "-std=c++17", *flags, f"-I{source}", f"-I{source.parent / 'g4sim'}", *files, "-o", str(executable),
                        *libraries, f"-Wl,-rpath,{prefix}/lib", f"-Wl,-rpath-link,{prefix}/lib"], stdout=log, stderr=log, check=True)
        return executable
    subprocess.run(["cmake", "-S", str(source), "-B", str(work / "build"), "-DCMAKE_BUILD_TYPE=Release"], stdout=log, stderr=log, check=True)
    subprocess.run(["cmake", "--build", str(work / "build"), "-j8", "--target", program], stdout=log, stderr=log, check=True)
    return work / "build" / program


def timed_run(executable: Path, spec: dict, events: int, folder: Path) -> float:
    folder.mkdir(parents=True, exist_ok=True)
    document = json.loads(json.dumps(spec))
    document["run"]["events"] = events
    document.setdefault("output", {}).update({"csv": str(folder / "events.csv"), "materials": str(folder / "materials.json"),
                                              "datapaths": str(folder / "datapaths.json")})
    (folder / "spec.json").write_text(json.dumps(document), encoding="utf-8")
    start = time.perf_counter()
    with (folder / "log.txt").open("w", encoding="utf-8") as log:
        subprocess.run([str(executable), "spec.json"], cwd=folder, stdout=log, stderr=log, check=True,
                       env={**os.environ, "G4PROTO_OUT": str(folder)})
    return time.perf_counter() - start


def spec_of(row: dict) -> dict:
    """The spec file of a run, by its recorded hash: other recorded files can share its name."""
    folder = PLUGIN / inventory.EXAMPLES[row["journey"]] / "recorded"
    for path in folder.rglob(row["spec_name"]):
        if hashlib.sha256(path.read_bytes()).hexdigest() == row["spec_file_sha256"]:
            return json.loads(path.read_text(encoding="utf-8"))
    raise ValueError(f"{row['run']}: no file with the recorded hash")


def per_event(measure, events: int) -> dict:
    """Seconds per event from measure(n), doubling n until the difference between n and 2n is large enough to mean something."""
    for _ in range(MAXIMUM_DOUBLINGS):
        short, long = measure(events), measure(2 * events)
        if long - short >= MINIMUM_DIFFERENCE_S:
            return {"sample_events": events, "seconds_short": round(short, 2), "seconds_long": round(long, 2),
                    "seconds_per_event": (long - short) / events, "reliable": True}
        events *= 2
    return {"sample_events": events // 2, "seconds_short": round(short, 2), "seconds_long": round(long, 2),
            "seconds_per_event": None, "reliable": False}


def chosen(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (row["events"], row["run"]))
    return list({row["run"]: row for row in (ordered[-1], ordered[len(ordered) // 2], ordered[0])}.values())


def priced(timings: list[dict], total_events: int) -> dict:
    """The hours for an executable from its timed runs: the slowest reliable rate; none reliable gives no estimate."""
    rates = [item["seconds_per_event"] for item in timings if item["reliable"]]
    if not rates:
        return {"reliable": False, "seconds_per_event": None, "estimated_hours": None}
    return {"reliable": True, "seconds_per_event": max(rates), "estimated_hours": round(max(rates) * total_events / 3600, 2)}


def sample(rows: list[dict], work: Path, events: int, config: str | None) -> dict:
    first = rows[0]
    program, commit = first["program"], first["source_commit"]
    folder = work / commit
    shutil.rmtree(folder, ignore_errors=True)
    assets = extract(commit, folder / "archive")
    source = apply_probe.apply(program, assets, folder / "src")
    executable = build(source, program, folder, config)
    timings = []
    for at, row in enumerate(chosen(rows)):
        spec = spec_of(row)
        timing = per_event(lambda n, spec=spec, at=at: timed_run(executable, spec, n, folder / f"run-{at}-{n}"), events)
        timings.append({"run": row["run"], "recorded_events": row["events"], **timing})
    total = sum(row["events"] for row in rows)
    return {"executable": first["executable"], "commit": commit, "program": program, "runs": len(rows), "events": total,
            "timed": timings, **priced(timings, total)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int, default=2000)
    parser.add_argument("--geant4-config")
    args = parser.parse_args(argv)
    try:
        rows = json.loads(args.facts.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    groups: dict = {}
    for row in rows:
        groups.setdefault(row["executable"], []).append(row)
    work = args.work.resolve()
    results, failed = [], []
    for executable, members in groups.items():
        try:
            results.append(sample(members, work, args.events, args.geant4_config))
        except (OSError, subprocess.CalledProcessError, StopIteration, ValueError) as err:
            failed.append({"executable": executable, "error": str(err)[:300]})
    complete = not failed and all(item["reliable"] for item in results)
    total = round(sum(item["estimated_hours"] for item in results), 2) if complete else None
    print(json.dumps({"status": "ok" if complete else "failed", "samples": results, "failed": failed, "estimated_hours": total}, indent=1))
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())

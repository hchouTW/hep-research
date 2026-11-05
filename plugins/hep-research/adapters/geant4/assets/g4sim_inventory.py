#!/usr/bin/env python3
"""The inventory table of recorded Geant4 runs (g4sim plan, Section 7.4): every run listed in GL2, in exactly one of four classes.

  collect                 facts the repository holds: program, executable, events, seeds, outputs and their hashes
  check-work WORK_ROOT    on the machine that made the runs: which reference outputs still exist with their recorded hash
  classify                the class of each run, from those facts and the results of its re-acquisition

Usage: g4sim_inventory.py collect --out FACTS.json
       g4sim_inventory.py check-work --facts FACTS.json --work-root DIR --out WORK.json
Only hashes and file sizes are read from WORK_ROOT; nothing is written there. Prints JSON with a status key.
Exit 0 ok, 1 refused with findings, 2 bad input.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SOURCES = {"J14": "examples/geant4-thin-silicon/output/artifacts/runs/*.json",
           "J15": "examples/design-minimal-spectrometer/recorded/runs/*",
           "J16": "examples/design-search-j16/recorded/runs/*"}
PROGRAMS = ("layered_sim", "element_sim")
CLASSES = ("T1-recorded", "T1-regenerated", "T2", "not-regressable")
COLUMN_FILE, SUMMARY_FILE = "events.csv", "summary.json"
# The commit whose files match sources_sha256 of each recorded executable, found by walking the history (S1 task card).
SOURCE_COMMITS = {"d39225ea24707abf": "636213ae", "a69ffad7c003aad9": "3f4f9985", "193c678cb9e97fad": "d9db638c",
                  "db090f9ea07ec303": "2a0b9f29"}
EXAMPLES = {"J14": "examples/geant4-thin-silicon", "J15": "examples/design-minimal-spectrometer", "J16": "examples/design-search-j16"}
HOME_PREFIX = "~/Workspace/geant4-work/"


def _load(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _row(journey: str, document: dict) -> dict | None:
    extension = document["extension"]
    tools = {tool["name"]: tool["version"] for tool in extension.get("tools", [])}
    program = next((name for name in PROGRAMS if name in tools), None)
    if program is None or "Geant4" not in tools:
        return None
    simulation = extension.get("simulation") or {}
    spec = extension["input_manifest"][0]
    return {"run": document["artifact_id"], "journey": journey, "program": program, "executable": tools[program],
            "source_commit": SOURCE_COMMITS.get(tools[program]), "spec_name": spec["path"].rsplit("/", 1)[1],
            "spec_file_sha256": spec["sha256"],
            "geant4": tools["Geant4"], "plugin_version": document["versions"]["plugin"], "command": extension["commands"][0],
            "work": extension["environment"].get("work"), "seeds": extension.get("seeds"), "events": simulation.get("events"),
            "run_manager": simulation.get("run_manager"), "threads": simulation.get("threads"),
            "spec_sha256": simulation.get("spec_sha256"), "outputs": extension["output_hashes"]}


def collect(root: Path = PLUGIN) -> list[dict]:
    rows = []
    for journey, pattern in SOURCES.items():
        for path in sorted(glob.glob(str(root / pattern))):
            if path.endswith((".json", ".json.gz")):
                document = _load(Path(path))
                row = _row(journey, document) if document.get("artifact_type") == "computational-run" else None
                if row:
                    rows.append(row)
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_work(rows: list[dict], work_root: Path) -> dict:
    """{run: {output: "match" | "different" | "missing"}}; a run's outputs lie below the work folder it recorded."""
    found = {}
    for row in rows:
        relative = (row["work"] or "").removeprefix(HOME_PREFIX)
        states = {}
        for name, expected in row["outputs"].items():
            path = work_root / relative / name
            states[name] = "missing" if not path.is_file() else ("match" if _sha256(path) == expected else "different")
        found[row["run"]] = states
    return found


def scope(states: dict) -> list[str]:
    """What an existing reference output covers: the column file, the summary, or both."""
    usable = [name.rsplit("/", 1)[-1] for name, state in states.items() if state == "match"]
    return sorted({"columns" if name == COLUMN_FILE else "summary" for name in usable if name in (COLUMN_FILE, SUMMARY_FILE)})


def classify(states: dict, result: dict | None) -> dict:
    """The class of one run. result is its re-acquisition: built, reproduced, probe_agrees (None without an existing probe
    record), field_visible (GB22), regenerated (a baseline of the unmodified program), and seed_as_recorded."""
    covers = scope(states)
    result = result or {}
    if result.get("seed_as_recorded") is False:
        return {"class": None, "reason": "the reproduction check used a different seed, so it proves nothing", "scope": covers}
    reference = bool(covers) or bool(result.get("regenerated"))
    if not reference:
        return {"class": "not-regressable", "reason": "no usable reference output and no regenerated baseline", "scope": covers}
    failures = [text for key, text in (("built", "the re-acquisition build cannot be built"),
                                       ("reproduced", "the reproduction check failed"),
                                       ("field_visible", "GB22 does not hold for this run")) if not result.get(key)]
    if result.get("probe_agrees") is False:
        failures.append("an existing probe record disagrees with the re-acquisition record")
    if failures:
        return {"class": "T2", "reason": "; ".join(failures), "scope": covers or ["regenerated"]}
    if covers:
        return {"class": "T1-recorded", "reason": "existing output reproduced", "scope": covers}
    return {"class": "T1-regenerated", "reason": "reproduced against a regenerated baseline", "scope": ["regenerated"]}


def table_problems(table: list[dict], facts: list[dict]) -> list[str]:
    """Every recorded run in exactly one class; a summary-only run must not claim the column file."""
    problems = []
    runs = [row["run"] for row in table]
    for row in facts:
        if runs.count(row["run"]) != 1:
            problems.append(f"{row['run']}: listed {runs.count(row['run'])} times")
    for row in table:
        if row.get("class") not in CLASSES:
            problems.append(f"{row['run']}: not classified")
        has_columns = any(name.endswith(COLUMN_FILE) and state == "match" for name, state in row.get("states", {}).items())
        if "columns" in row.get("scope", []) and not has_columns:
            problems.append(f"{row['run']}: claims the column file, which it does not have")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    gather = commands.add_parser("collect")
    gather.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("check-work")
    check.add_argument("--facts", type=Path, required=True)
    check.add_argument("--work-root", type=Path, required=True)
    check.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            rows = collect()
            args.out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
            print(json.dumps({"status": "ok", "runs": len(rows), "events": sum(row["events"] or 0 for row in rows)}))
        else:
            rows = json.loads(args.facts.read_text(encoding="utf-8"))
            found = check_work(rows, args.work_root)
            args.out.write_text(json.dumps(found, indent=1) + "\n", encoding="utf-8")
            tally: dict = {}
            for states in found.values():
                for state in states.values():
                    tally[state] = tally.get(state, 0) + 1
            print(json.dumps({"status": "ok", "runs": len(found), "files": tally,
                              "with_a_reference": sum(bool(scope(states)) for states in found.values())}))
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""T08 calorimetry (adapters/calo-cluster): generate a few synthetic t08-grid/1 events, reconstruct them, check the product.

ILLUSTRATIVE and SYNTHETIC. Two events of the frozen fixture t08-grid/1 (block 1, the tuning block; variant main, stratum 7: energy bin
E3, 1 to 4 GeV, separation far, two showers of equal energy 3 to 8 shower widths apart) on the 40 x 40 analog grid, reconstructed by
reco.calo.cell-cluster/1, a development binding in Python (not a native backend). Names no experiment. Makes no calorimetry quality
claim: the counts below are what the programs wrote, not an efficiency or a resolution, and T08's quality verdict waits for K09 at
Freeze B.
- The scoring harness (fixture_tools/t08_fixture_files.py) calls the frozen generator, checked by its SHA-256, and writes the data
  file (calo-cells/1, role reconstruction-input: raw values, live and saturated flags only), the pedestal and gain payloads, and
  the truth file (role truth), apart.
- reconstruct (calo_cluster.py, data side, its own process) reads the data file and the payloads alone: the cell chain, then
  section 7.1's clustering, written as calo-cluster-product/1; check-product reads it back and runs the double-count check.
- The truth file is not used: only its SHA-256 is recorded.

Modes:
  offline replay (default): reads --recorded (default recorded/: the cells file, both payloads, the product, and runs.json with the
    reports and commands, the folders replaced by <work>, <plugin> and <python>), checks the identities and labels below, and writes
    summary.json and report.md to --out (default output/); the result is byte-identical to the committed output/
    (tests/examples/test_reconstruction_calorimetry.py). Needs NumPy and SciPy (the recipe and its reader).
  live (--live --generator GEN, or HEP_T08_GENERATOR): runs the harness, reconstruct and check-product in --work (a temporary folder
    by default, outside the plugin), rewrites --recorded and replays. The frozen generator is outside the repository, so the committed
    recorded/ comes from the T08 job (D2 stage 4), whose recording the coordinator copies after a PASS.

Checks, every one must pass (exit 0, else 1): each operation ok with exit 0; the recipe's commands name no truth file; the product
names the recorded cells file and payloads (SHA-256); it was made with the t08-grid/1 configuration file beside the recipe; it reads
back whole as calo-cluster-product/1 of recipe reco.calo.cell-cluster/1 with energy kind clustered deposited energy, never incident
energy; no cell is counted twice; its kept cells are exactly section 7.1's selection of the recorded cells, and kept, unclustered and
dead cells and their sums account for the input (fixture_tools/t08_scenarios.py, scenario A38); the recipe run again on the recorded
cells writes the recorded product byte for byte.

Expected readings, stated before the first live run and checked by nobody: 2 events, 2 objects in each (two two-peak objects of one
component, or two one-peak objects of two components), no component without objects, no dead cell, no saturated cell.
A different count is a reading to explain, not a failed check.

Usage (from the plugin root): python3 examples/reconstruction-calorimetry/run.py [--out DIR] [--recorded DIR]
       python3 examples/reconstruction-calorimetry/run.py --live --generator GEN [--work DIR] [--recorded DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
ASSETS = PLUGIN / "adapters" / "calo-cluster" / "assets"
RECIPE_CLI = ASSETS / "calo_cluster.py"
CONFIGURATION = ASSETS / "t08-grid-1.configuration.json"
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

VARIANT, BLOCK, STRATUM, EVENTS = "main", 1, 7, 2
STEM = "events"
PRODUCT_ID = "example-reconstruction-calorimetry"
RECORDED_FILES = ("runs.json", "events.cells", "events.pedestal.json", "events.gain.json", "events.product")
FROZEN_GENERATOR_SHA256 = "d901362c62431282ce37eeaac88efb864339aec9eb6915aa9e7d69808f7946f9"   # freeze-a.md; the harness checks it
DROPPED_FIELDS = ("seconds",)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def placeholders(text: str, work: Path) -> str:
    for real, name in ((str(work.resolve()), "<work>"), (str(work), "<work>"), (str(PLUGIN), "<plugin>"), (sys.executable, "<python>")):
        text = text.replace(real, name)
    return text


def recipe_run(arguments: list, work: Path) -> dict:
    command = [sys.executable, "-I", "-B", str(RECIPE_CLI), *arguments]
    finished = subprocess.run(command, capture_output=True, text=True, timeout=600)
    try:
        report = json.loads(finished.stdout)
    except ValueError:
        report = {"operation": arguments[0], "status": "failed", "exit_code": finished.returncode,
                  "reason": f"the recipe wrote no report: {finished.stderr[-500:]}"}
    kept = {key: value for key, value in report.items() if key not in DROPPED_FIELDS}
    kept = json.loads(placeholders(json.dumps(kept, sort_keys=True), work))
    kept["exit_code"] = finished.returncode
    kept["command"] = [placeholders(str(token), work) for token in command]
    return kept


# ---- live: harness, reconstruct, check-product.

def live(generator, generator_sha256, work: Path, recorded: Path) -> int:
    """generator: the frozen module (loaded by the harness, hash checked) or a stand-in with its interface (tests)."""
    import t08_fixture_files as fixture_files  # noqa: E402  NumPy: the scoring harness

    work.mkdir(parents=True, exist_ok=True)
    files = fixture_files.stratum_files(generator, VARIANT, BLOCK, STRATUM, EVENTS, work, STEM)
    runs = [{"operation": "generate", "status": "ok", "exit_code": 0, "harness": "fixture_tools/t08_fixture_files.py",
             "data_side_files": sorted(f"{STEM}.{suffix}" for suffix in ("cells", "pedestal.json", "gain.json"))}]
    product_path = work / f"{STEM}.product"
    runs.append(recipe_run(["reconstruct", "--cells", str(work / f"{STEM}.cells"), "--pedestal-payload", str(work / f"{STEM}.pedestal.json"),
                            "--gain-payload", str(work / f"{STEM}.gain.json"), "--product", str(product_path), "--product-id", PRODUCT_ID], work))
    if runs[-1]["exit_code"] != 0:
        print(json.dumps(runs[-1], indent=1))
        return runs[-1]["exit_code"] or 1
    runs.append(recipe_run(["check-product", "--product", str(product_path)], work))
    if runs[-1]["exit_code"] != 0:
        print(json.dumps(runs[-1], indent=1))
        return runs[-1]["exit_code"]
    recorded.mkdir(parents=True, exist_ok=True)
    for name in RECORDED_FILES[1:]:
        shutil.copyfile(work / name, recorded / name)
    write_json(recorded / "runs.json", {"generator": generator.GENERATOR, "generator_sha256": generator_sha256, "variant": VARIANT,
                                        "block": BLOCK, "stratum": STRATUM, "events": EVENTS,
                                        "files_sha256": {name: entry["sha256"] for name, entry in sorted(files.items())}, "runs": runs})
    return 0


# ---- offline replay.

def rerun_product(recorded: Path) -> bytes | None:
    """The recipe run again on the recorded cells and payloads, in a temporary folder: the product's bytes, None on failure."""
    with tempfile.TemporaryDirectory() as name:
        out = Path(name) / "again.product"
        finished = subprocess.run([sys.executable, "-I", "-B", str(RECIPE_CLI), "reconstruct", "--cells", str(recorded / f"{STEM}.cells"),
                                   "--pedestal-payload", str(recorded / f"{STEM}.pedestal.json"), "--gain-payload", str(recorded / f"{STEM}.gain.json"),
                                   "--product", str(out), "--product-id", PRODUCT_ID], capture_output=True, text=True, timeout=600)
        return out.read_bytes() if finished.returncode == 0 and out.is_file() else None


def replay(recorded: Path) -> tuple:
    from calo_recipe import ENERGY_KIND, RECIPE, cell_input, configuration, gain_payload, product  # noqa: E402
    import t08_scenarios as scenarios  # noqa: E402

    runs = json.loads((recorded / "runs.json").read_text(encoding="utf-8"))
    content = {name: (recorded / name).read_bytes() for name in RECORDED_FILES}
    by_operation = {run["operation"]: run for run in runs["runs"]}
    readout = cell_input.read_cells(content[f"{STEM}.cells"], "cells")
    pedestal = cell_input.read_payload(content[f"{STEM}.pedestal.json"], "pedestal payload")
    gain = gain_payload.read_gain(content[f"{STEM}.gain.json"], "gain payload")
    cfg = configuration.load(CONFIGURATION)
    try:
        read, refusal = product.read_text(content[f"{STEM}.product"].decode("utf-8")), None
    except product.ProductError as exc:
        read, refusal = None, str(exc)
    header = read.header if read else {}
    double = [d for doc in read.events for d in product.double_count_defects(doc)] if read else ["product refused"]
    selection = []
    if read:
        for i, doc in enumerate(read.events):
            energy = scenarios.cell_energies(readout.raw[i], readout.live[i], pedestal.values, gain.values, gain.operation)
            selection.extend(scenarios.selection_defects(doc, readout.raw[i], readout.live[i], energy, cfg))
    recipe_commands = [token for operation in ("reconstruct", "check-product") for token in by_operation.get(operation, {}).get("command", [])]
    checks = [
        ("every operation is ok with exit 0", [run["operation"] for run in runs["runs"]] == ["generate", "reconstruct", "check-product"]
         and all(run["status"] == "ok" and run["exit_code"] == 0 for run in runs["runs"])),
        ("the recipe's commands name no truth file", not any("truth" in token for token in recipe_commands)),
        ("the product names the recorded cells file and payloads", bool(read) and header["input"]["sha256"] == sha256_bytes(content[f"{STEM}.cells"])
         == runs["files_sha256"]["cells"] and [step["payload_id"] for step in header["chain"]] == [pedestal.identity, gain.identity]),
        ("the product was made with the t08-grid/1 configuration", bool(read) and header["configuration"]["sha256"] == cfg.sha256),
        ("the product reads back whole, clustered deposited energy, never incident energy", bool(read) and (header["format"], header["recipe"],
         header["energy_kind"]) == (product.FORMAT, RECIPE, ENERGY_KIND)),
        ("no cell is counted twice", double == [] and by_operation.get("check-product", {}).get("double_count_defects") == 0),
        ("the kept cells are section 7.1's selection and hit and unhit cells account for the input (A38)", bool(read) and selection == []),
        ("the recipe run again on the recorded cells writes the recorded product", rerun_product(recorded) == content[f"{STEM}.product"]),
    ]
    events = []
    for doc in (read.events if read else []):
        kinds = {}
        for cluster in doc["objects"]:
            kinds[cluster["kind"]] = kinds.get(cluster["kind"], 0) + 1
        events.append({"event": doc["event"], "objects": len(doc["objects"]), "kinds": kinds, "components": len(doc["components"]),
                       "components_without_objects": sum(c["failure"] is not None for c in doc["components"]),
                       "kept_cells": len(doc["cells"]), "unclustered_cells": doc["unclustered_cells"], "dead_cells": len(doc["dead_channels"]),
                       "saturated_cells": sum(row[6] for row in doc["cells"])})
    summary = {
        "example": "reconstruction-calorimetry", "data": "synthetic",
        "quality_claim": "none: counts the programs wrote, not an efficiency or a resolution (K09 at Freeze B)",
        "generator": runs["generator"], "generator_sha256": runs["generator_sha256"], "variant": runs["variant"], "block": runs["block"],
        "stratum": runs["stratum"], "events_generated": runs["events"], "files_sha256": runs["files_sha256"],
        "recipe": header.get("recipe"), "product_format": header.get("format"), "energy_kind": header.get("energy_kind"),
        "configuration_sha256": header.get("configuration", {}).get("sha256"), "product_refused": refusal,
        "events": events,
        "recorded_sha256": {name: sha256_bytes(body) for name, body in content.items()},
        "checks": [{"check": name, "passed": bool(passed)} for name, passed in checks],
    }
    return summary, all(passed for _, passed in checks)


def report_text(summary: dict) -> str:
    lines = ["# T08 calorimetry example: generate, reconstruct, check (synthetic)", "",
             f"Generator {summary['generator']}, block {summary['block']} (tuning), variant {summary['variant']}, stratum {summary['stratum']}, "
             f"{summary['events_generated']} events, recipe {summary['recipe']} (a development binding), product {summary['product_format']}, "
             f"energy kind {summary['energy_kind']}. Synthetic data only. No calorimetry quality claim: the counts are what the programs "
             "wrote, not an efficiency or a resolution; T08's quality verdict waits for K09 at Freeze B.", "",
             "| Event | Objects | Kinds | Components | Without objects | Kept cells | Unclustered cells | Dead | Saturated |",
             "|---|---|---|---|---|---|---|---|---|"]
    for event in summary["events"]:
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(event["kinds"].items())) or "none"
        lines.append(f"| {event['event']} | {event['objects']} | {kinds} | {event['components']} | {event['components_without_objects']} | "
                     f"{event['kept_cells']} | {event['unclustered_cells']} | {event['dead_cells']} | {event['saturated_cells']} |")
    lines += ["", "| Check | Result |", "|---|---|"]
    lines += [f"| {item['check']} | {'pass' if item['passed'] else 'FAIL'} |" for item in summary["checks"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--out", default=str(HERE / "output"))
    parser.add_argument("--recorded", default=str(HERE / "recorded"))
    parser.add_argument("--live", action="store_true", help="run the harness, reconstruct and check-product, and rewrite --recorded")
    parser.add_argument("--generator", default=os.environ.get("HEP_T08_GENERATOR", ""), help="the frozen gen_t08_grid.py (live)")
    parser.add_argument("--work", help="work folder of the live run (default: a temporary folder)")
    arguments = parser.parse_args(argv)
    recorded, out = Path(arguments.recorded), Path(arguments.out)
    if arguments.live:
        if not arguments.generator:
            print("the live mode needs the frozen generator: --generator or HEP_T08_GENERATOR", file=sys.stderr)
            return 3
        import t08_fixture_files as fixture_files  # noqa: E402
        try:
            generator = fixture_files.load_generator(arguments.generator)
        except fixture_files.FixtureError as exc:
            print(f"the generator is refused: {exc}", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory() as temporary:
            code = live(generator, FROZEN_GENERATOR_SHA256, Path(arguments.work) if arguments.work else Path(temporary), recorded)
        if code != 0:
            return code
    missing = [name for name in RECORDED_FILES if not (recorded / name).is_file()]
    if missing:
        print(f"no recorded run in {recorded}: missing {', '.join(missing)}; the live mode (--live) writes it", file=sys.stderr)
        return 1
    summary, passed = replay(recorded)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    (out / "report.md").write_text(report_text(summary), encoding="utf-8")
    print(f"{sum(item['passed'] for item in summary['checks'])} of {len(summary['checks'])} checks pass; {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

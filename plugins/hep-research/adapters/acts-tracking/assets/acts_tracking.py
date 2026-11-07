#!/usr/bin/env python3
"""Thin wrapper over the T07 native programs (contract-map.md, tool_contract.json row): it forwards and reports. No fixture value,
no physics and no fit lives here. The programs are built from assets/native by CMake against ACTS 48.2.0.

The folder of the built programs comes from --build-dir or HEP_ACTS_TRACKING_BUILD. A missing program is a failed result with
its reason, never a fallback (docs/adapter-authoring.md, Honesty rules). Output: one JSON object on stdout, with the status, the
reason and the exact command run. Exit 0 ok, 1 program failed, 2 invalid input, 3 program missing (core/status.py).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DRIVER = "acts_tracking_driver"
GENERATOR = "t07_fixture_generator"
FINDER = "acts_tracking_finder"
RUN_TIMEOUT_SECONDS = 3600
EXIT_FAILED, EXIT_INVALID, EXIT_MISSING = 1, 2, 3
PROGRAM_INVALID_INPUT = 2


def program_path(build_dir: str | None, program: str) -> Path | None:
    folder = build_dir or os.environ.get("HEP_ACTS_TRACKING_BUILD")
    if not folder:
        return None
    candidate = Path(folder) / program
    return candidate if candidate.is_file() and os.access(candidate, os.X_OK) else None


def report(operation: str, status: str, reason: str, exit_code: int, **fields) -> int:
    print(json.dumps({"operation": operation, "status": status, "reason": reason, "exit_code": exit_code, **fields}, sort_keys=True))
    return exit_code


def report_finished(operation: str, fields: dict) -> int:
    """A refit or a search stays ok with some failed tracks, which it counts; with no track fitted the operation failed."""
    try:
        summary = json.loads(fields["program_stdout"])
    except ValueError:
        summary = {}
    tracks, failed = (summary.get("tracks"), summary.get("failed")) if isinstance(summary, dict) else (None, None)
    if failed is None:
        return report(operation, "ok", "", 0, **fields)
    fields = dict(fields, tracks=tracks, failed_tracks=failed)
    if tracks and failed == tracks:
        return report(operation, "failed", "every fit failed", EXIT_FAILED, **fields)
    return report(operation, "ok", "", 0, **fields)


def run_program(operation: str, build_dir: str | None, program: str, arguments: list) -> int:
    executable = program_path(build_dir, program)
    if executable is None:
        return report(operation, "missing-dependency", f"{program} not found: set --build-dir or HEP_ACTS_TRACKING_BUILD to its build folder", EXIT_MISSING, program=program)
    command = [str(executable), *arguments]
    try:
        finished = subprocess.run(command, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as error:
        return report(operation, "failed", f"{program} did not finish: {error}", EXIT_FAILED, command=command)
    fields = {"command": command, "program_exit": finished.returncode, "program_stdout": finished.stdout, "program_stderr": finished.stderr}
    if finished.returncode == 0:
        return report_finished(operation, fields)
    if finished.returncode == PROGRAM_INVALID_INPUT:
        return report(operation, "rejected", finished.stderr.strip(), EXIT_INVALID, **fields)
    return report(operation, "failed", finished.stderr.strip() or "the program failed", EXIT_FAILED, **fields)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="operation", required=True)
    self_test = commands.add_parser("self-test", help="geometry, propagation, file and product checks of the driver")
    self_test.add_argument("--work-dir", required=True, help="writable folder for its small files")
    self_test.add_argument("--build-dir", help="folder of the built programs")
    generate = commands.add_parser("generate-fixture", help="events of t07-telescope-clean/1 or t07-telescope-noise/1")
    generate.add_argument("--fixture", required=True, choices=("clean", "noise"))
    generate.add_argument("--block", required=True, type=int, help="seed block of t04-values-v4.md section 3.2")
    generate.add_argument("--stratum", required=True, type=int, help="3 x momentum bin + occupancy level, 0 to 11")
    generate.add_argument("--first-event", required=True, type=int)
    generate.add_argument("--count", required=True, type=int)
    generate.add_argument("--data-file", required=True, help="measurements, role reconstruction-input")
    generate.add_argument("--truth-file", required=True, help="truth, role truth, suffix .t07truth")
    generate.add_argument("--build-dir", help="folder of the built programs")
    refit = commands.add_parser("refit", help="ACTS Kalman refit of known hit sets: truth-assisted, never finding. At zero field or the fixture's 1 T")
    refit.add_argument("--data-file", required=True, help="measurements")
    refit.add_argument("--hit-sets", required=True, help="acts-tracking-hit-sets/1 bound to the data file")
    refit.add_argument("--field-tesla", required=True, type=float)
    refit.add_argument("--product-id", required=True)
    refit.add_argument("--product-file", required=True, help="acts-tracking-product/1 to write")
    refit.add_argument("--build-dir", help="folder of the built programs")
    find = commands.add_parser("find", help="ACTS pattern recognition on hits alone: seeds from hits, CKF, ambiguity resolution, fit. Recipe reco.track.acts-ckf-planar/1, data side")
    find.add_argument("--data-file", required=True, help="measurements")
    find.add_argument("--product-id", required=True)
    find.add_argument("--product-file", required=True, help="acts-tracking-product/1 to write, with the states of the selected tracks")
    find.add_argument("--record-file", required=True, help="acts-tracking-finding-record/1 to write: every event and candidate")
    find.add_argument("--product-events", required=True, type=int, help="how many events, from the first, keep their states in the product")
    find.add_argument("--build-dir", help="folder of the built programs")
    return parser


def main(argv=None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
    except SystemExit as stop:
        return EXIT_INVALID if stop.code else 0
    if arguments.operation == "self-test":
        return run_program("self-test", arguments.build_dir, DRIVER, ["self-test", "--work-dir", arguments.work_dir])
    if arguments.operation == "generate-fixture":
        forwarded = ["generate", "--fixture", arguments.fixture, "--block", str(arguments.block), "--stratum", str(arguments.stratum),
                     "--first-event", str(arguments.first_event), "--count", str(arguments.count), "--data-file", arguments.data_file,
                     "--truth-file", arguments.truth_file]
        return run_program("generate-fixture", arguments.build_dir, GENERATOR, forwarded)
    if arguments.operation == "find":
        if not Path(arguments.data_file).is_file():
            return report("find", "rejected", f"no such input file: {arguments.data_file}", EXIT_INVALID)
        forwarded = ["--data-file", arguments.data_file, "--product-id", arguments.product_id, "--product-file", arguments.product_file, "--record-file", arguments.record_file,
                     "--product-events", str(arguments.product_events)]
        return run_program("find", arguments.build_dir, FINDER, forwarded)
    for input_file in (arguments.data_file, arguments.hit_sets):
        if not Path(input_file).is_file():
            return report("refit", "rejected", f"no such input file: {input_file}", EXIT_INVALID)
    forwarded = ["refit", "--data-file", arguments.data_file, "--hit-sets", arguments.hit_sets, "--field-tesla", repr(arguments.field_tesla),
                 "--product-id", arguments.product_id, "--product-file", arguments.product_file]
    return run_program("refit", arguments.build_dir, DRIVER, forwarded)


if __name__ == "__main__":
    sys.exit(main())

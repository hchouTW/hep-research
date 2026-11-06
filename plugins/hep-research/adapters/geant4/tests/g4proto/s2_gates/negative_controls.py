#!/usr/bin/env python3
"""The live negative tests of the accounting (Section 15.1), run with s2_gates: each control must be caught, and the same run without it must not be.

Usage: negative_controls.py PROGRAM FOLDER   Prints JSON with a status key. Exit 0 every control caught, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

EM_LIMIT = 1e-7


def run(program: Path, folder: Path, mode: str, control: str) -> dict:
    out = folder / f"{mode}-{control or 'plain'}.json"
    environment = {**os.environ, **({"G4SIM_ACCOUNTING_CONTROL": control} if control else {})}
    subprocess.run([str(program), mode, str(out)], cwd=folder, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=environment, check=True)
    return json.loads(out.read_text(encoding="utf-8"))


def main(argv) -> int:
    if len(argv) != 3:
        print(json.dumps({"status": "rejected", "message": __doc__.splitlines()[-2]}))
        return 2
    program, folder = Path(argv[1]).resolve(), Path(argv[2]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    plain = run(program, folder, "gb8em", "")
    killed = run(program, folder, "gb8em", "stop_status_is_killed")
    special = run(program, folder, "gb7", "")
    special_control = run(program, folder, "gb7", "class_d_kinetic")
    table = run(program, folder, "gb9", "")
    neutron = run(program, folder, "gb9", "neutron_rest_energy")
    nuclei = run(program, folder, "gb9", "nuclei_unreleased")
    relative = float.fromhex(killed["worst_relative_residual"])
    results = {
        "plain_run_clean": plain["accounting_errors"] == 0 and float.fromhex(plain["worst_relative_residual"]) <= EM_LIMIT,
        "every_stop_as_killed_counts_errors": killed["accounting_errors"] > 0,
        "every_stop_as_killed_fails_conservation": relative > EM_LIMIT,
        "class_d_kinetic_moves_the_residual": float.fromhex(special_control["worst_residual_MeV"]) > float.fromhex(special["worst_residual_MeV"]),
        "neutron_at_rest_energy_differs": float.fromhex(neutron["particles"]["neutron"]["unreleased_MeV"]) > 100 * float.fromhex(table["particles"]["neutron"]["unreleased_MeV"]),
        "nuclei_nonzero_is_seen": float.fromhex(nuclei["nucleus_unreleased_MeV"]) != 0.0 and float.fromhex(table["nucleus_unreleased_MeV"]) == 0.0}
    ok = all(results.values())
    print(json.dumps({"status": "ok" if ok else "failed", "results": results, "killed_relative_residual": relative}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

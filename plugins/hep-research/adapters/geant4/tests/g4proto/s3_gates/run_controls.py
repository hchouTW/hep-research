#!/usr/bin/env python3
"""The output negatives of Section 15.1 for S3, on real runs of g4sim_run: each passes when correct and each injected defect must be caught.

Usage: run_controls.py --program PATH --work DIR [--events N]   In an activated Geant4 environment, from the plugin root.
Prints JSON with a status key. Exit 0 every check as expected, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "adapters/geant4/assets"))

import g4sim_simulate as simulate  # noqa: E402

from core.simulation import source_density  # noqa: E402

FIXTURES = PLUGIN / "tests/adapters/data"
DRIVER = PLUGIN / "adapters/geant4/assets/g4sim_run.py"
BALANCE_TOLERANCE_MEV = 1e-6
KOLMOGOROV_LIMIT = 1.63  # sqrt(n) D at about the 1% level
FIELD_TOLERANCE = 1e-3


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"g4sim_block.{name}.json").read_text(encoding="utf-8"))


def run_case(label: str, folder: Path, program: Path, spec: dict, request: dict, card: dict, environment: dict | None = None) -> tuple:
    work = folder / label
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    paths = {}
    for name, block in (("spec", spec), ("request", request), ("run", card)):
        paths[name] = work / f"input-{name}.json"
        paths[name].write_text(json.dumps(block), encoding="utf-8")
    done = subprocess.run([sys.executable, str(DRIVER), "simulate", "--detector", str(paths["spec"]), "--request", str(paths["request"]), "--run", str(paths["run"]), "--program", str(program), "--work", str(work / "run")],
                          capture_output=True, text=True, check=False, env={**os.environ, **(environment or {})})
    return json.loads(done.stdout.strip().splitlines()[-1]), work / "run"


def rows_of(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def events_sum(cells: list, scorer: str) -> dict:
    out: dict = {}
    for row in cells:
        if row[1] == scorer and row[2] != "-1":
            out[row[0]] = out.get(row[0], 0.0) + float(row[4])
    return out


def nonionizing_mismatch(work: Path) -> int:
    """Events where the classes' non-ionizing energy differs from the `edep_nonionizing` scorer."""
    cells = rows_of(work / "cells.csv")
    classes: dict = {}
    for row in cells:
        if row[1] == "classes" and row[2] != "-1" and simulate.class_x(int(row[3]))[0] == "nonionizing":
            classes[row[0]] = classes.get(row[0], 0.0) + float(row[4])
    direct = events_sum(cells, "nonionizing")
    return sum(abs(classes.get(event, 0.0) - value) > 1e-9 * max(value, 1e-12) for event, value in direct.items())


def reweighting_failures(work: Path, birks: float) -> int:
    cells = rows_of(work / "cells.csv")
    classes: dict = {}
    for row in cells:
        if row[1] == "classes" and row[2] != "-1":
            classes.setdefault(row[0], []).append((int(row[3]), float(row[4])))
    visible = events_sum(cells, "visible")
    return sum(abs(simulate.reweighted(rows, birks) - visible.get(event, 0.0)) > simulate.reweighting_bound(rows, birks) for event, rows in classes.items())


def kolmogorov_statistic(work: Path, record: dict) -> float:
    energies = sorted(float(row[1]) for row in rows_of(work / "primaries.csv"))
    low, high = record["energy"]["min_MeV"], record["energy"]["max_MeV"]
    count = len(energies)
    return math.sqrt(count) * max(abs((at + 1) / count - (value - low) / (high - low)) for at, value in enumerate(energies))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--events", type=int, default=300)
    args = parser.parse_args()
    spec, request, card = fixture("spec"), fixture("request"), fixture("run")
    card["run"]["events"] = args.events
    request["scorers"].append({"name": "nonionizing", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep_nonionizing"})
    work = args.work.resolve()
    program = args.program.resolve()

    def case(label, spec_in=spec, request_in=request, card_in=card, environment=None):
        return run_case(label, work, program, spec_in, request_in, card_in, environment)
    checks = {}
    good, good_work = case("nominal")
    checks["nominal_passes"] = good["status"] == "ok" and good["closure"]["failing"] == 0 and good["balance"]["largest_MeV"] < BALANCE_TOLERANCE_MEV and good["conservation"]["accounting_errors"] == 0
    dropped, _ = case("drop_bin", environment={"G4SIM_SCORER_CONTROL": "drop_bin"})
    checks["dropped_bin_caught"] = dropped["closure"]["failing"] > 0

    proton = copy.deepcopy(request)
    proton["source"]["particle"] = "proton"
    proton["source"]["energy"] = {"uniform": {"min_MeV": "5", "max_MeV": "60"}}
    plain, plain_work = case("proton", request_in=proton)
    mixed, mixed_work = case("nonionizing_as_ionizing", request_in=proton, environment={"G4SIM_DEDX_CONTROL": "nonionizing_as_ionizing"})
    checks["classes_hold_the_nonionizing_part"] = plain["status"] == "ok" and nonionizing_mismatch(plain_work) == 0 and sum(float(row[4]) for row in rows_of(plain_work / "cells.csv") if row[1] == "nonionizing" and row[2] != "-1") > 0
    checks["nonionizing_in_an_ionizing_class_caught"] = nonionizing_mismatch(mixed_work) > 0
    checks["reweighting_within_its_bound_electrons"] = reweighting_failures(good_work, 0.126) == 0
    checks["reweighting_within_its_bound_protons"] = reweighting_failures(plain_work, 0.126) == 0

    silent = copy.deepcopy(spec)
    silent["materials"] = {"crystal": {"base": "G4_PbWO4", "ionisation": {"birks_mm_per_MeV": "0", "facts": "assumed"}, "facts": "assumed"}}
    silent["templates"]["block"]["material"] = "G4_PbWO4"
    undeclared, _ = case("birks_undeclared", spec_in=silent)
    checks["undeclared_birks_refused"] = undeclared["status"] == "rejected" and any(item["code"] == "birks-undeclared" for item in undeclared.get("findings", []))

    for label, control in (("no_backflow", "backflow_needed"), ("outflow_minus_incidence", "any"), ("kinetic_only_incidence", "any")):
        if control == "backflow_needed":
            continue
        broken, _ = case(label, environment={"G4SIM_SCORER_CONTROL": label})
        checks[f"{label}_caught"] = broken["balance"]["largest_MeV"] > BALANCE_TOLERANCE_MEV
    # backflow needs particles that leave and come back: a field bends them round
    bent = copy.deepcopy(spec)
    bent["fields"] = {"solenoid": {"b_tesla": ["0", "4", "0"]}}
    bent["world"]["field"] = "solenoid"
    returning = copy.deepcopy(request)
    returning["source"]["particle"] = "e-"
    returning["source"]["energy"] = {"uniform": {"min_MeV": "20", "max_MeV": "60"}}
    returning["source"]["position"]["box_uniform"]["centre_mm"] = ["0", "0", "190"]  # 10 mm before the block, or the field turns them away first
    bounded = copy.deepcopy(card)  # in vacuum they would circle for ever: KillProcess ends them, and books what it takes
    bounded["kill_policy"] = {"time_cut_ns": "100"}
    with_field, field_work = case("backflow_nominal", spec_in=bent, request_in=returning, card_in=bounded)
    without, _ = case("no_backflow", spec_in=bent, request_in=returning, card_in=bounded, environment={"G4SIM_SCORER_CONTROL": "no_backflow"})
    killing = copy.deepcopy(card)
    killing["kill_policy"] = {"min_kinetic_energy_MeV": "1"}
    killing["physics"] = {"em_constructor": "G4EmStandardPhysics_option4", "cuts_mm": {"default": "0.7"}}  # pure EM: a photonuclear event breaks this closure by a binding energy
    booked, booked_work = case("kill_booked", card_in=killing)
    unbooked, _ = case("kill_unbooked", card_in=killing, environment={"G4SIM_ACCOUNTING_CONTROL": "no_killed_process"})
    with (field_work / "boundary.csv").open(encoding="utf-8", newline="") as handle:
        backflows = sum(int(row[5]) for row in csv.reader(handle) if row[2] != "balance")
    checks["backflow_was_exercised"] = backflows > 0
    with (booked_work / "conservation.csv").open(encoding="utf-8", newline="") as handle:
        killed_mev = sum(float(row["killed_kinetic_process_MeV"]) for row in csv.DictReader(handle))
    checks["kill_process_fired"] = killed_mev > 0
    checks["conservation_holds_with_kills"] = booked["conservation"]["largest_residual_MeV"] < BALANCE_TOLERANCE_MEV and booked["conservation"]["accounting_errors"] == 0
    checks["balance_holds_with_kills"] = booked["balance"]["largest_MeV"] < BALANCE_TOLERANCE_MEV
    checks["unbooked_kill_caught"] = unbooked["conservation"]["largest_residual_MeV"] > BALANCE_TOLERANCE_MEV
    checks["balance_holds_with_backflow"] = with_field["status"] == "ok" and with_field["balance"]["mean_incident_MeV"] > 0 and with_field["balance"]["largest_MeV"] < BALANCE_TOLERANCE_MEV
    checks["no_backflow_caught"] = without["balance"]["largest_MeV"] > BALANCE_TOLERANCE_MEV

    early = copy.deepcopy(card)
    early["physics"]["em_parameters"] = {"step_function_electron": ["0.1", "0.005"], "msc_range_factor": "0.02"}
    set_right, _ = case("em_after_constructor", card_in=early)
    too_soon, _ = case("em_before_constructor", card_in=early, environment={"G4SIM_EM_TOO_EARLY": "1"})
    checks["em_parameters_read_back"] = set_right["status"] == "ok"
    checks["em_parameters_too_early_refused"] = too_soon["status"] == "rejected" and bool(too_soon.get("problems"))

    regional = copy.deepcopy(spec)
    regional["templates"]["block"]["region"] = "tracker"
    pai_card = copy.deepcopy(card)
    pai_card["physics"]["pai"] = [{"region": "tracker", "particle": "e-", "model": "PAI"}]
    pai_card["run"]["events"] = 20
    pai_run, _ = case("pai", spec_in=regional, card_in=pai_card)
    pai_broken, _ = case("pai_world_changed", spec_in=regional, card_in=pai_card, environment={"G4SIM_PAI_CONTROL": "1"})
    in_tracker = pai_run.get("effective", {}).get("models", {}).get("tracker", {}).get("eIoni/e-", [])
    checks["pai_read_back_in_its_region"] = pai_run["status"] == "ok" and any(row[0] == "PAIModel" for row in in_tracker)
    checks["pai_changing_models_outside_refused"] = pai_broken["status"] == "rejected" and bool(pai_broken.get("problems"))

    # S4, Section 10.3: E^L + E^S equals edep_visible bin by bin; n^L counts the steps with mu_s > 10
    scintillating = copy.deepcopy(spec)
    scintillating["materials"]["scintillator"]["scintillation"] = {"yield_per_MeV": "100", "resolution_scale": "1", "facts": "assumed"}
    splitting = copy.deepcopy(request)
    segments = {"along_axis": {"axis": "z", "width_mm": "20"}}
    splitting["scorers"] = [{"name": "visible", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep_visible", "segmentation": segments, "split": "midpoint"},
                            {"name": "split", "readout": "none", "select": {"tags": ["active"]}, "quantity": "edep_visible_ly_split", "segmentation": segments, "split": "midpoint"}]
    split_run, split_work = case("split", spec_in=scintillating, request_in=splitting)
    refused, _ = case("split_no_yield", request_in=splitting)
    whole: dict = {}
    parts: dict = {}
    large_steps = 0
    for row in rows_of(split_work / "cells.csv"):
        if row[2] == "-1":
            continue
        if row[1] == "visible":
            whole[(row[0], row[2], int(row[3]))] = float(row[4])
        else:
            key = (row[0], row[2], int(row[3]) // 2)
            parts[key] = parts.get(key, 0.0) + float(row[4])
            large_steps += int(row[5]) if int(row[3]) % 2 == 0 else 0
    worst = max((abs(parts.get(key, 0.0) - value) for key, value in whole.items()), default=math.inf)
    checks["split_closes_on_edep_visible"] = split_run["status"] == "ok" and set(whole) == set(parts) and worst < 1e-9 and large_steps > 0
    checks["split_without_a_yield_refused"] = refused["status"] == "rejected" and any(item["code"] == "scintillation-undeclared" for item in refused.get("findings", []))

    record = source_density.density(request["source"])
    source_card = copy.deepcopy(card)
    source_card["run"]["events"] = 2000
    plain_source = copy.deepcopy(request)
    plain_source["scorers"] = []
    fine, fine_work = case("source", request_in=plain_source, card_in=source_card)
    wide, wide_work = case("source_wide", request_in=plain_source, card_in=source_card, environment={"G4SIM_SOURCE_CONTROL": "wide_energy"})
    good_distance, bad_distance = kolmogorov_statistic(fine_work, record), kolmogorov_statistic(wide_work, record)
    checks["source_matches_its_density"] = fine["status"] == "ok" and good_distance < KOLMOGOROV_LIMIT
    checks["wrong_source_parameters_caught"] = bad_distance > KOLMOGOROV_LIMIT

    field_spec = copy.deepcopy(spec)
    field_spec["templates"]["block"]["material"] = "G4_Galactic"
    field_spec["materials"] = {}
    field_spec["fields"] = {"dipole": {"b_tesla": ["0", "1", "0"]}}
    field_spec["world"]["field"] = "dipole"
    muon = copy.deepcopy(request)
    muon["source"]["particle"] = "mu-"
    muon["source"]["energy"] = {"mono": {"energy_MeV": "1000"}}
    muon["source"]["position"] = {"point": {"frame": "beam", "centre_mm": ["0", "0", "0"]}}
    muon["scorers"] = [{"name": "exit", "readout": "none", "select": {"tags": ["active"]}, "quantity": "crossing_kinematics"}]
    field_card = copy.deepcopy(card)
    field_card["run"]["events"] = 3
    bend, bend_work = case("field", spec_in=field_spec, request_in=muon, card_in=field_card)
    flipped, flip_work = case("field_flipped", spec_in=field_spec, request_in=muon, card_in=field_card, environment={"G4SIM_BUILDER_CONTROL": "flip_field"})
    mass = 105.6583755
    momentum = math.sqrt((1000 + mass) ** 2 - mass ** 2)
    radius = momentum / (0.299792458 * 1.0)  # mm, for p in MeV/c and B in T
    path = 300 + 100  # the point of exit lies 400 mm downstream of the source
    # dp/dt = q v x B with q < 0 and B along +y: the muon, moving along +z, turns towards +x... by F = q (z x y) = -q x
    wanted = radius - math.sqrt(radius ** 2 - path ** 2)
    found = [float(row[5]) for row in rows_of(bend_work / "crossings.csv")]
    opposite = [float(row[5]) for row in rows_of(flip_work / "crossings.csv")]
    checks["field_bends_as_the_helix"] = bend["status"] == "ok" and bool(found) and all(abs(value - wanted) < FIELD_TOLERANCE * wanted for value in found)
    checks["flipped_field_caught"] = bool(opposite) and all(abs(value - wanted) > FIELD_TOLERANCE * wanted for value in opposite)

    report = {"status": "ok" if all(checks.values()) else "failed", "checks": checks, "numbers": {"nominal": {key: good.get(key) for key in ("closure", "balance", "conservation")}, "kolmogorov": [good_distance, bad_distance],
              "backflow": {"nominal": with_field.get("balance"), "without": without.get("balance")}, "field_x_mm": {"wanted": wanted, "found": found, "flipped": opposite}}}
    print(json.dumps(report, indent=1))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

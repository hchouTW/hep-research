#!/usr/bin/env python3
"""Judge GB15, GB16 and GB17 (g4sim plan, Section 23) from the files s3_optics writes, by the criteria in the S3 task card.

GB16 needs no registered number. GB15 and GB17 refuse to run without NUMBERS.json, whose content must stand in the S3 card before the judged runs; a sample of
any other size is rejected. A verdict here is an E5 result, never a confirmed GB.

Usage: judge.py gb15|gb17 FOLDER NUMBERS.json  |  judge.py gb16 FOLDER
Prints JSON with a status key; exit 0 every criterion met, 1 a criterion not met, 2 bad input.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2

import scintillation_moments as moments
import scintillation_tests as tests

HERE = Path(__file__).resolve().parent
DESIGN = json.loads((HERE / "design.json").read_text(encoding="utf-8"))
SCOPE_VOLUME = "inside_scintillator"
STRUCTURES = {"G4RegularXTRadiator": "regular", "G4TransparentRegXTRadiator": "regular", "G4XTRRegularRadModel": "regular", "G4XTRTransparentRegRadModel": "regular",
              "G4GammaXTRadiator": "irregular", "G4GaussXTRadiator": "irregular", "G4XTRGammaRadModel": "irregular", "G4XTRGaussRadModel": "irregular",
              "G4StrawTubeXTRadiator": None}  # regular: fixed thicknesses, no distribution input; irregular: alpha inputs; the straw has one wall and a third medium, so neither fits


class BadInput(Exception):
    pass


def load(path: Path) -> dict:
    if not path.is_file():
        raise BadInput(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# --- GB15 -----------------------------------------------------------------------------------------------------------


def chunks_of(folder: Path, name: str) -> list:
    found = sorted((folder / "gb15").glob(f"{name}_[0-9]*.json"))
    if not found:
        raise BadInput(f"no chunks of {name} in {folder}")
    return [path.with_suffix("") for path in found]


def check_header(header: dict, item: dict, design: dict) -> None:
    wanted = {"yield_per_MeV": design["yield_per_MeV"], "resolution_scale": item.get("resolution", 1.0), "birks_mm_per_MeV": design["birks_mm_per_MeV"]}
    for key, value in wanted.items():
        if tests.hexed(header[key]) != value:
            raise BadInput(f"{key} differs from the design in a chunk of {item['name']}")
    if header["saturation_attached"] != item.get("saturation", True) or header["scintillation_by_particle_type"]:
        raise BadInput(f"saturation or particle-type setting differs from the design in {item['name']}")


def judge_sums(sums: tests.Sums, item: dict, edges: list, design: dict) -> dict:
    rows = tests.tests_of(sums, "target", design, edges)
    controls = {}
    for name in item["controls"]:
        control_rows = tests.tests_of(sums, name, design, edges)
        controls[name] = {"rejected": not all(row["equivalent"] for row in control_rows), "failed_tests": [f"{row['moment']} {row['bin']}" for row in control_rows if not row["equivalent"]]}
    return {"all_equivalent": all(row["equivalent"] for row in rows), "tests": rows, "controls": controls}


def component_split(folder: Path, item: dict, design: dict) -> dict:
    """Geant4's truncating split against the plan's multinomial, at the level of the plan's segmentation bin, by mu_b bin."""
    (prefix,) = chunks_of(folder, item["name"])
    header, steps = tests.read_steps(prefix)
    yields = [tests.hexed(text) for text in header["component_yields"]]
    total = sum(yields)
    fraction = [value / total for value in yields]
    photons = steps["photons"].astype(np.int64)
    parts = [steps["fast"], steps["medium"], steps["slow"]][:len(yields)]
    wanted = [np.floor(value / total * photons.astype(float)).astype(np.int64) for value in yields]  # numPhot = yield / sum * N, truncated by the assignment to size_t
    if len(yields) == 2:
        wanted[1] = photons - wanted[0]
    differ = int(sum(np.count_nonzero(got != want) for got, want in zip(parts, wanted)))
    mu = design["yield_per_MeV"] * steps["visible"]
    small = (mu > 3.0) & (mu <= moments.POISSON_LIMIT)
    key = steps["event"].astype(np.int64) * tests.KEY_SLICES + steps["slice"]
    order = np.argsort(key, kind="stable")
    starts = np.flatnonzero(np.r_[True, key[order][1:] != key[order][:-1]])
    light = np.add.reduceat(mu[order], starts)
    total_photons = np.add.reduceat(photons[order].astype(float), starts)
    per_part = [np.add.reduceat(part[order].astype(float), starts) for part in parts]
    edges = np.asarray(design["formula_bin_edges"], dtype=float)
    index = np.searchsorted(edges, light, side="left") - 1
    rows = []
    for number, label in enumerate(tests.bin_labels(design["formula_bin_edges"])):
        chosen = index == number
        if not chosen.any():
            continue
        mean_total, variance_total = total_photons[chosen].mean(), total_photons[chosen].var()
        row = {"bin": label, "cells": int(chosen.sum()), "mean_photons": mean_total, "lost_fraction": 1.0 - sum(part[chosen].mean() for part in per_part) / mean_total, "components": []}
        for share, part in zip(fraction, per_part):
            multinomial_mean = share * mean_total
            multinomial_variance = share * share * variance_total + share * (1.0 - share) * mean_total
            row["components"].append({"share": share, "geant4_mean": part[chosen].mean(), "multinomial_mean": multinomial_mean, "mean_difference_relative": part[chosen].mean() / multinomial_mean - 1.0,
                                      "geant4_variance": part[chosen].var(), "multinomial_variance": multinomial_variance, "variance_difference_relative": part[chosen].var() / multinomial_variance - 1.0})
        rows.append(row)
    split_sum = sum(part[small].astype(float).sum() for part in parts)
    return {"components": len(yields), "steps": int(steps.size), "steps_with_split_differing_from_truncation": differ, "per_step_lost_fraction_mu_3_to_10": 1.0 - split_sum / max(float(photons[small].sum()), 1.0), "bins": rows}


def judge_scintillation(folder: Path, numbers: dict) -> dict:
    design = DESIGN["gb15"]
    registered = numbers["gb15"]
    all_sets = design["step_sets"] + design["formula_sets"]
    tables = {value: moments.StepMoments(value) for value in {item["resolution"] for item in all_sets} | {1.0}}
    report, passed = {}, True
    for item in all_sets:
        is_step = item in design["step_sets"]
        edges = design["step_bin_edges"] if is_step else design["formula_bin_edges"]
        sums = tests.Sums(edges, ["target", *item["controls"]])
        events = zero_photons = 0
        for prefix in chunks_of(folder, item["name"]):
            header, steps = tests.read_steps(prefix)
            check_header(header, item, design)
            events += header["events"]
            zero_photons += header["zero_deposit_photons"]
            if is_step:
                tests.add_step_chunk(sums, item, steps, design["yield_per_MeV"], tables)
            else:
                tests.add_formula_chunk(sums, item, steps, design["yield_per_MeV"], tables[item["resolution"]])
        if events != registered["events_per_set"][item["name"]]:
            raise BadInput(f"{item['name']}: {events} events, registered {registered['events_per_set'][item['name']]}")
        result = judge_sums(sums, item, edges, design)
        result["events"] = events
        result["photons_on_zero_deposit_steps"] = zero_photons
        report[item["name"]] = result
        if item.get("must_pass", True):
            passed = passed and result["all_equivalent"] and zero_photons == 0
        passed = passed and all(control["rejected"] for control in result["controls"].values())
    check, _ = (load(chunks_of(folder, design["stack_check"]["name"])[0].with_suffix(".json")), None)
    report["secondaries_equal_get_num_photons"] = {"steps": check["steps_compared_with_secondaries"], "differing": check["steps_secondaries_differ"]}
    passed = passed and check["steps_secondaries_differ"] == 0 and check["steps_compared_with_secondaries"] > 0
    report["component_property_names"] = check["component_property_names"]
    passed = passed and len(check["component_property_names"]) == 3
    report["components"] = {item["name"]: component_split(folder, item, design) for item in design["component_sets"]}
    passed = passed and all(item["steps_with_split_differing_from_truncation"] == 0 for item in report["components"].values())
    return {"criteria_met_on_E5": passed, **report}


# --- GB16 -----------------------------------------------------------------------------------------------------------


def judge_scope(folder: Path) -> dict:
    design = DESIGN["gb16"]
    runs, exits = {}, {}
    for name in design["runs"]:
        exits[name] = int((folder / "gb16" / f"{name}.exit").read_text(encoding="utf-8"))
        if exits[name] == 0:
            runs[name] = load(folder / "gb16" / f"{name}.json")

    def volumes(run: dict, field: str) -> set:
        return {key.split("|")[0] for key in run[field]} if field == "produced" else set(run[field])

    scope, both = runs["scope"], runs["both_tables"]
    production = {"produced_in": sorted(volumes(scope, "produced")), "control_with_table_produced_in": sorted(volumes(both, "produced")), "produced": scope["produced"]}
    production["met"] = volumes(scope, "produced") == {SCOPE_VOLUME} and "outside_scintillator" in volumes(both, "produced")
    outside_steps = {name: sum(count for volume, count in runs[name]["optical_steps"].items() if volume != SCOPE_VOLUME) for name in ("scope", "leak_killed", "leak_open", "leak_entry")}
    kill = {"steps_outside_scope": outside_steps, "killed_by_scope_process": {name: runs[name]["killed_by_scope"] for name in ("scope", "leak_killed", "leak_entry")},
            "ends_in_scope_run": scope["optical_end"], "zero_length_steps_entry_kill": runs["leak_entry"]["optical_zero_length_steps"]}
    kill["met"] = outside_steps["scope"] == 0 and outside_steps["leak_killed"] == 0 and runs["leak_killed"]["killed_by_scope"] > 0 and outside_steps["leak_open"] > 0
    closure_runs = [name for name in ("scope", "both_tables", "leak_killed") if runs[name]["steps_checked"] > 0]
    worst = max(tests.hexed(runs[name]["worst_relative"]) for name in closure_runs)
    with_photons = min(tests.hexed(runs[name]["smallest_relative_with_photon_energy"]) for name in closure_runs)
    energy = {"steps_checked": sum(runs[name]["steps_checked"] for name in closure_runs), "worst_relative": worst, "tolerance": design["relative_tolerance"], "control_smallest_relative_if_photon_energy_were_subtracted": with_photons,
              "parents": {name: runs[name]["parents"] for name in closure_runs}, "excluded": {name: runs[name]["excluded_parents"] for name in closure_runs},
              "photon_energy_over_deposit": sum(tests.hexed(runs[name]["photon_energy_MeV"]) for name in closure_runs) / sum(tests.hexed(runs[name]["deposit_in_producing_steps_MeV"]) for name in closure_runs)}
    energy["met"] = worst <= design["relative_tolerance"] and with_photons > design["relative_tolerance"]
    active = {"unchanged_with_scintillation_type": runs["active_scintillation"]["produced"] == both["produced"], "unchanged_with_cerenkov_type": runs["active_cerenkov"]["produced"] == both["produced"],
              "exit_codes": {name: exits[name] for name in exits if name.startswith(("general", "plain"))},
              "general_produced": {name: run["produced"] for name, run in runs.items() if name.startswith("general")}, "plain_worker_produced": runs["plain_worker"]["produced"]}
    active["can_restrict_by_volume"] = False if active["unchanged_with_scintillation_type"] and active["unchanged_with_cerenkov_type"] else None
    return {"criteria_met_on_E5": production["met"] and kill["met"] and energy["met"], "production": production, "scope_kill": kill, "parent_energy": energy, "set_active_volume": active}


# --- GB17 -----------------------------------------------------------------------------------------------------------


def upper_limit(count: int, events: int, level: float) -> float:
    return float(chi2.ppf(level, 2 * (count + 1)) / 2.0) / events


def lower_limit(count: int, events: int, level: float) -> float:
    return float(chi2.ppf(1.0 - level, 2 * count) / 2.0) / events if count else 0.0


def judge_radiators(folder: Path, numbers: dict) -> dict:
    design = DESIGN["gb17"]
    registered = numbers["gb17"]
    report, table = {}, {}
    for name in design["classes"]:
        high, below, control = (load(folder / "gb17" / f"{kind}_{name}.json") for kind in ("high", "below", "control"))
        if high["events"] != registered["high_events"] or control["events"] != registered["high_events"] or below["events"] != registered["below_events"]:
            raise BadInput(f"{name}: events differ from the registered numbers")
        yield_high = high["photons"] / high["events"]
        limit = upper_limit(below["photons"], below["events"], design["upper_limit_level"])
        inside_strict = high["strictly_inside"] == high["photons"] and control["strictly_inside"] == control["photons"]
        inside_closed = high["outside_envelope"] == 0 and control["outside_envelope"] == 0
        only_envelope = set(high["vertex_volume"]) <= {"radiator_envelope"} and set(control["vertex_volume"]) <= {"radiator_envelope"}
        control_rejected = lower_limit(control["photons"], control["events"], design["upper_limit_level"]) >= design["yield_fraction"] * yield_high
        report[name] = {"yield_high": yield_high, "photons_high": high["photons"], "strictly_inside": high["strictly_inside"], "on_surface": high["on_surface"], "outside_envelope": high["outside_envelope"], "vertex_volume": high["vertex_volume"],
                        "below_events": below["events"], "below_photons": below["photons"], "below_from_primary": below["photons_from_primary"], "below_upper_limit": limit, "limit_required": design["yield_fraction"] * yield_high,
                        "control_yield": control["photons"] / control["events"], "control_rejected": control_rejected, "inside_strict": inside_strict, "inside_closed": inside_closed,
                        "criteria_met_on_E5": yield_high > 0 and inside_strict and only_envelope and limit < design["yield_fraction"] * yield_high and control_rejected}
        table[name] = {"structure": STRUCTURES[name], "photon_vertex": "on_envelope_surface" if high["on_surface"] == high["photons"] else "along_track_inside_envelope",
                       "alpha_read_back": [tests.hexed(high["alpha_foil_read_back"]), tests.hexed(high["alpha_gas_read_back"])]}
    return {"criteria_met_on_E5": all(item["criteria_met_on_E5"] for item in report.values()), "classes": report, "xtr_radiators_draft": table}


def main() -> int:
    arguments = sys.argv[1:]
    try:
        if len(arguments) == 2 and arguments[0] == "gb16":
            verdict = judge_scope(Path(arguments[1]))
        elif len(arguments) == 3 and arguments[0] in ("gb15", "gb17"):
            numbers = load(Path(arguments[2]))
            verdict = (judge_scintillation if arguments[0] == "gb15" else judge_radiators)(Path(arguments[1]), numbers)
        else:
            raise BadInput("usage: judge.py gb15|gb17 FOLDER NUMBERS.json | judge.py gb16 FOLDER")
    except BadInput as problem:
        print(json.dumps({"status": "rejected", "message": str(problem)}))
        return 2
    met = verdict["criteria_met_on_E5"]
    print(json.dumps({"status": "ok" if met else "not_met", arguments[0]: verdict}, indent=1, default=float))
    return 0 if met else 1


if __name__ == "__main__":
    sys.exit(main())

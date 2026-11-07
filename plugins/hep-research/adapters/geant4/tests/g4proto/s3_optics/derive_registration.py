#!/usr/bin/env python3
"""GB15 and GB17 (g4sim plan, Section 23): turn a trial run into the numbers the S3 task card registers, before any judged run.

A trial run only estimates variances, the mu_s distribution and yields; judged runs use other seeds and never reuse it. Nothing here tests equivalence.

Usage: derive_registration.py commands trial|judged [NUMBERS.json]   one run per line: NAME<TAB>MODE<TAB>options, for run_all.sh
       derive_registration.py gb16-commands
       derive_registration.py register FOLDER NUMBERS.json           derive from the trial runs in FOLDER, write NUMBERS.json
Prints JSON with a status key; exit 0 ok, 1 a required set is infeasible, 2 bad input.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2, poisson

import scintillation_moments as moments
import scintillation_tests as tests

HERE = Path(__file__).resolve().parent
DESIGN = json.loads((HERE / "design.json").read_text(encoding="utf-8"))
ALLOWED_BELOW_PHOTONS = 1  # the class with the smallest yield must pass even with this many photons below threshold, so the size does not rest on seeing exactly none
FOIL_DENSITY_G_CM3, FOIL_Z_OVER_A = 0.94, 0.57  # G4_POLYETHYLENE
XI_MEV_CM2_G = 0.1535  # 2 pi N_A r_e^2 m_e c^2, PDG: the delta-ray rate is xi / T above T for beta = 1
ELECTRON_TABLE_FLOOR_MEV = 100e3 * 0.51099895 / 938.27209  # G4VXTRenergyLoss: no TR below a proton-scaled kinetic energy of 100 GeV


def scintillation_options(design: dict, resolution: float, saturation: bool, events: int, seed: int, extra: tuple = ()) -> str:
    beam = design["beam"]
    words = [f"resolution={resolution!r}", f"yield={design['yield_per_MeV']!r}", f"birks={design['birks_mm_per_MeV']!r}", f"slice_mm={design['slice_mm']!r}",
             f"low_MeV={beam['low_MeV']!r}", f"high_MeV={beam['high_MeV']!r}", f"particle={beam['particle']}", f"saturation={int(saturation)}", f"events={events}", f"seed={seed}", *extra]
    return " ".join(words)


def scintillation_commands(stage: str, numbers: dict) -> list:
    design = DESIGN["gb15"]
    base = design["trial_seed"] if stage == "trial" else design["judged_seed"]
    rows = []
    for number, item in enumerate(design["step_sets"] + design["formula_sets"]):
        saturation = item.get("saturation", True)
        total = design["trial_events"] if stage == "trial" else numbers["gb15"]["events_per_set"][item["name"]]
        chunks = 1 if stage == "trial" else math.ceil(total / design["events_per_process"])
        for chunk in range(chunks):
            events = total // chunks + (1 if chunk < total % chunks else 0)
            rows.append((f"gb15/{item['name']}_{chunk}", "gb15", scintillation_options(design, item["resolution"], saturation, events, base + 100 * number + chunk)))
    scale = 0.1 if stage == "trial" else 1.0
    for number, item in enumerate(design["component_sets"]):
        extra = (f"components={item['components']}", *(f"yield{i + 1}={value!r}" for i, value in enumerate(item["yields"])))
        rows.append((f"gb15/{item['name']}_0", "gb15", scintillation_options(design, 1.0, True, int(item["events"] * scale), base + 50 + number, extra)))
    check = design["stack_check"]
    rows.append((f"gb15/{check['name']}_0", "gb15", scintillation_options(design, 1.0, True, int(check["events"] * scale), base + 60, ("stack=1",))))
    return rows


def radiator_options(design: dict, name: str, beam: dict, events: int, seed: int, attach_electrons: bool = True) -> str:
    geometry = design["straw"] if name == "G4StrawTubeXTRadiator" else design["stack"]
    words = [f"class={name}", f"particle={beam['particle']}", f"energy_MeV={beam['energy_MeV']!r}", f"events={events}", f"seed={seed}", f"attach_electrons={int(attach_electrons)}"]
    return " ".join(words + [f"{key}={value!r}" for key, value in geometry.items()])


def radiator_commands(stage: str, numbers: dict) -> list:
    design = DESIGN["gb17"]
    base = design["trial_seed"] if stage == "trial" else design["judged_seed"]
    rows = []
    for number, name in enumerate(design["classes"]):
        for kind_number, kind in enumerate(("high", "below", "control")):
            events = design["trial_events"]
            if stage == "trial" and name == "G4StrawTubeXTRadiator":
                events *= 10
            if stage == "judged":
                events = numbers["gb17"]["high_events"] if kind != "below" else numbers["gb17"]["below_events"]
            attach_electrons = stage == "judged" or name not in design["slow_tables"]  # a trial keeps each run short: one table build only
            rows.append((f"gb17/{kind}_{name}", "gb17", radiator_options(design, name, design[kind], events, base + 10 * number + kind_number, attach_electrons)))
    return rows


def scope_commands() -> list:
    design = DESIGN["gb16"]
    return [(f"gb16/{name}", "gb16", " ".join([f"events={design['events']}", f"seed={design['seed']}", *words])) for name, words in design["runs"].items()]


def trial_sums(folder: Path) -> tuple:
    """Per set: the sums of every hypothesis, the events and the CPU time of the trial chunk."""
    design = DESIGN["gb15"]
    tables = {value: moments.StepMoments(value) for value in {item["resolution"] for item in design["step_sets"] + design["formula_sets"]} | {1.0}}
    found = {}
    for item in design["step_sets"]:
        header, steps = tests.read_steps(folder / "gb15" / f"{item['name']}_0")
        sums = tests.Sums(design["step_bin_edges"], ["target", *item["controls"]])
        tests.add_step_chunk(sums, item, steps, design["yield_per_MeV"], tables)
        found[item["name"]] = (sums, header, steps.size)
    for item in design["formula_sets"]:
        header, steps = tests.read_steps(folder / "gb15" / f"{item['name']}_0")
        sums = tests.Sums(design["formula_bin_edges"], ["target", *item["controls"]])
        tests.add_formula_chunk(sums, item, steps, design["yield_per_MeV"], tables[item["resolution"]])
        found[item["name"]] = (sums, header, steps.size)
    return found, tables


def scintillation_numbers(folder: Path) -> dict:
    design = DESIGN["gb15"]
    found, _ = trial_sums(folder)
    step_tests = len(design["step_sets"]) * (len(design["step_bin_edges"]) - 1) * 2
    formula_required = [item for item in design["formula_sets"] if item["must_pass"]]
    formula_tests = len(formula_required) * (len(design["formula_bin_edges"]) - 1) * 2
    total_tests = step_tests + formula_tests
    power = 1.0 - (1.0 - design["joint_power"]) / total_tests  # Bonferroni over all tests: at or above 0.9^(1/K) too, so both rules of Section 18 hold
    events_per_set, rows, feasibility = {}, [], {}
    for item in design["step_sets"] + design["formula_sets"]:
        sums, header, steps = found[item["name"]]
        edges = design["step_bin_edges"] if item in design["step_sets"] else design["formula_bin_edges"]
        needed_events, worst_ratio = 0.0, 0.0
        for index, label in enumerate(tests.bin_labels(edges)):
            for moment in tests.MOMENTS:
                row = tests.summarize(sums.table["target"], index, moment, design)
                records_per_event = row["records"] / header["events"]
                ratio = abs(row["expected_difference"]) / row["margin"]
                worst_ratio = max(worst_ratio, ratio)
                needed = tests.required_records(row["residual_variance"], row["margin"], abs(row["expected_difference"]), design["alpha"], power)
                needed_events = max(needed_events, needed / records_per_event) if item.get("must_pass", True) else needed_events
                rows.append({"set": item["name"], "regime": tests.regime(edges, index), "moment": moment, "bin": label, "trial_records": row["records"], "records_per_event": records_per_event,
                             "bin_average": row["margin"] / (design["mean_margin"] if moment == "mean" else design["variance_margin"]), "absolute_margin": row["margin"],
                             "residual_variance": row["residual_variance"], "assumed_true_difference": row["expected_difference"], "difference_over_margin": ratio, "required_records": needed})
        events_per_set[item["name"]] = int(math.ceil(needed_events * design["sample_size_safety"]))
        if item in design["formula_sets"]:
            feasibility[item["name"]] = {"resolution": item["resolution"], "must_pass": item["must_pass"], "worst_difference_over_margin": worst_ratio,
                                         "close_to_margin": bool(worst_ratio > design["close_to_margin_fraction"])}
    reference = max(events_per_set[item["name"]] for item in formula_required)
    for item in design["formula_sets"]:
        events_per_set[item["name"]] = max(events_per_set[item["name"]], reference)  # all formula sets share one size; r = 3 is only recorded
    cpu = {name: tests.hexed(header["cpu_seconds"]) / header["events"] for name, (_, header, _) in found.items()}
    return {"K_step": step_tests, "K_formula": formula_tests, "K": total_tests, "per_test_power": power, "sidak_reference": design["joint_power"] ** (1.0 / total_tests),
            "events_per_set": events_per_set, "feasibility": feasibility, "tests": rows, "trial_cpu_seconds_per_event": cpu,
            "estimated_cpu_seconds": sum(cpu[name] * events for name, events in events_per_set.items()),
            "estimated_record_bytes": sum(found[name][2] / found[name][1]["events"] * events * 28 for name, events in events_per_set.items())}


def poisson_upper(count: int, level: float) -> float:
    return float(chi2.ppf(level, 2 * (count + 1)) / 2.0)


def delta_ray_rate(design: dict, name: str, yield_per_particle: float) -> float:
    """An upper estimate of the TR photons per below-threshold particle: delta rays above the electrons' table floor, each giving at most the full high-gamma yield."""
    geometry = design["straw"] if name == "G4StrawTubeXTRadiator" else design["stack"]
    thickness = geometry["foils"] * geometry["foil_mm"] * 0.1 * FOIL_DENSITY_G_CM3
    return XI_MEV_CM2_G * FOIL_Z_OVER_A * thickness / ELECTRON_TABLE_FLOOR_MEV * yield_per_particle


def radiator_event_numbers(rows: dict, design: dict) -> dict:
    """The size at the class with the smallest yield, and each class's chance of passing it, given the delta-ray estimate."""
    level, fraction = design["upper_limit_level"], design["yield_fraction"]
    lowest = min(item["yield_lower_95"] for item in rows.values())
    events = math.ceil(poisson_upper(ALLOWED_BELOW_PHOTONS, level) / (fraction * lowest))
    chances = {}
    for name, item in rows.items():
        allowed = ALLOWED_BELOW_PHOTONS
        while poisson_upper(allowed + 1, level) / events < fraction * item["yield_lower_95"]:
            allowed += 1
        rate = delta_ray_rate(design, name, item["yield"])
        chances[name] = {"allowed_photons": allowed, "delta_ray_photons_expected": rate * events, "chance_of_passing": float(poisson.cdf(allowed, rate * events))}
    return {"below_events": events, "upper_limit_with_no_photon": poisson_upper(0, level) / events, "required_limit_at_lowest_yield": fraction * lowest, "power_by_class": chances,
            "joint_chance_of_passing": float(np.prod([item["chance_of_passing"] for item in chances.values()]))}


def radiator_numbers(folder: Path) -> dict:
    design = DESIGN["gb17"]
    rows, cpu = {}, 0.0
    for name in design["classes"]:
        high, below, control = (json.loads((folder / "gb17" / f"{kind}_{name}.json").read_text(encoding="utf-8")) for kind in ("high", "below", "control"))
        count, events = high["photons"], high["events"]
        rows[name] = {"events": events, "photons": count, "yield": count / events, "yield_lower_95": float(chi2.ppf(0.05, 2 * count) / 2.0) / events, "below_events": below["events"], "below_photons": below["photons"],
                      "below_photons_from_primary": below["photons_from_primary"], "control_yield": control["photons"] / control["events"], "strictly_inside": high["strictly_inside"], "on_surface": high["on_surface"],
                      "outside_envelope": high["outside_envelope"], "cpu_seconds": {kind: tests.hexed(item["run_cpu_seconds"]) + tests.hexed(item["initialize_cpu_seconds"]) for kind, item in zip(("high", "below", "control"), (high, below, control))}}
        cpu += sum(rows[name]["cpu_seconds"].values())
    # The yield itself should be known to about 5% in the judged run, at the class with the smallest yield.
    high_events = math.ceil(1.0 / (0.05 ** 2 * min(item["yield"] for item in rows.values())))
    return {"classes": rows, "high_events": high_events, **radiator_event_numbers(rows, design), "trial_cpu_seconds": cpu}


def main() -> int:
    arguments = sys.argv[1:]
    if not arguments:
        print(json.dumps({"status": "rejected", "message": __doc__.splitlines()[4]}))
        return 2
    if arguments[0] == "gb16-commands":
        print("\n".join("\t".join(row) for row in scope_commands()))
        return 0
    if arguments[0] == "commands":
        stage = arguments[1]
        numbers = json.loads(Path(arguments[2]).read_text(encoding="utf-8")) if stage == "judged" else {}
        print("\n".join("\t".join(row) for row in scintillation_commands(stage, numbers) + radiator_commands(stage, numbers)))
        return 0
    if arguments[0] == "register":
        folder, target = Path(arguments[1]), Path(arguments[2])
        numbers = {"moments_check": moments.self_check(), "gb15": scintillation_numbers(folder), "gb17": radiator_numbers(folder)}
        target.write_text(json.dumps(numbers, indent=1) + "\n", encoding="utf-8")
        required = [item for item in numbers["gb15"]["feasibility"].values() if item["must_pass"]]
        infeasible = [item for item in required if item["close_to_margin"]]
        summary = {key: numbers["gb15"][key] for key in ("K_step", "K_formula", "K", "per_test_power", "sidak_reference", "events_per_set", "feasibility", "estimated_cpu_seconds", "estimated_record_bytes")}
        print(json.dumps({"status": "infeasible" if infeasible else "ok", "numbers": str(target), "gb15": summary, "gb17": numbers["gb17"], "moments_check": numbers["moments_check"]}, indent=1))
        return 1 if infeasible else 0
    print(json.dumps({"status": "rejected", "message": f"unknown command {arguments[0]}"}))
    return 2


if __name__ == "__main__":
    sys.exit(main())

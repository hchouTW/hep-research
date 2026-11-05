#!/usr/bin/env python3
"""Judge GB3, GB5, GB7, GB8 and GB9 (g4sim plan, Section 23) from the files s2_gates writes, by the criteria in the S2 task card.

GB9 as re-registered on 2026-11-05: the limit judges the chain logic, recomputed here with Geant4's own masses and decay channels; the difference
from PDG masses (core/constants) is reported per particle as a stated limitation, because Geant4's mass table is older. A confirmed GB needs every criterion.

Usage: judge.py FOLDER   Prints JSON with a status key; exit 0 all confirmed, 1 a GB not confirmed, 2 bad input.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
PDG = ROOT / "core/constants/data/pdg-2026.json"
NAMES = {"e-": 11, "e+": -11, "mu-": 13, "mu+": -13, "pi-": -211, "pi+": 211, "pi0": 111, "kaon-": -321, "kaon+": 321, "neutron": 2112,
         "proton": 2212, "lambda": 3122, "gamma": 22}
FIXED_LIST = ("neutron", "mu-", "mu+", "pi-", "pi+", "kaon-", "kaon+", "lambda")  # Section 23
NEUTRINOS = ("nu_e", "nu_mu", "anti_nu_e", "anti_nu_mu")
SPECIAL_CUTS_TOLERANCE, MAX_STEP_RATIO = 1e-12, 10
UNRELEASED_TOLERANCE, CURVATURE_TOLERANCE, STRAIGHT_TOLERANCE_MM = 1e-6, 1e-3, 1e-9
EM_RELATIVE_LIMIT = 1e-7  # the pure-EM q_max of the S2 task card
TESLA_RADIUS_MM_PER_MEV = 1e3 / (0.299792458 * 1e3)  # R[mm] = p[MeV/c] / (0.2998 B[T])


def hexed(text: str) -> float:
    return float.fromhex(text)


def pdg_masses() -> dict:
    table = json.loads(PDG.read_text(encoding="utf-8"))["particles"]
    by_code = {item["mcid"]: item for item in table.values() if "mcid" in item}
    out = {}
    for name, code in NAMES.items():
        item = by_code.get(abs(code)) or by_code.get(code)
        if item is not None:
            out[name] = item["mass"]["value"]
    out["gamma"] = 0.0
    for name in NEUTRINOS:
        out[name] = 0.0
    return out


def reference(name: str, particles: dict, masses: dict) -> float:
    """The expected Q of the whole chain, plus 2 m_e for each e+, from PDG masses; a particle without channels here ends the chain."""
    if name not in particles or not particles[name]["channels"]:
        return 0.0
    weighted = total = 0.0
    for channel in particles[name]["channels"]:
        branch = hexed(channel["branch"])
        released = masses[name]
        for daughter in channel["daughters"]:
            released -= masses[daughter]
            released += 2 * masses["e-"] if daughter == "e+" else reference(daughter, particles, masses)
        weighted += branch * released
        total += branch
    return weighted / total


def judge_unreleased_energy(document: dict, masses: dict) -> dict:
    particles = document["particles"]
    worst, against_pdg, rows = 0.0, 0.0, {}
    own = {**masses, **{name: hexed(item["mass_MeV"]) for name, item in particles.items()}}
    for name, item in particles.items():
        if name not in FIXED_LIST:
            continue
        wanted, logic = reference(name, particles, masses), reference(name, particles, own)
        got = hexed(item["unreleased_MeV"])
        rows[name] = {"geant4_MeV": got, "pdg_MeV": wanted, "relative": abs(got - wanted) / wanted, "with_geant4_masses_relative": abs(got - logic) / logic,
                      "geant4_mass_MeV": own[name], "pdg_mass_MeV": masses[name]}
        worst = max(worst, rows[name]["with_geant4_masses_relative"])
        against_pdg = max(against_pdg, rows[name]["relative"])
    nucleus = hexed(document["nucleus_unreleased_MeV"])
    return {"confirmed": worst <= UNRELEASED_TOLERANCE and nucleus == 0.0, "worst_relative": worst, "worst_against_pdg_masses": against_pdg, "nucleus_MeV": nucleus, "rows": rows}


def judge_special_cuts(first: dict, second: dict) -> dict:
    killed, deposit = hexed(first["killed_kinetic_MeV"]), hexed(first["killed_deposit_MeV"])
    relative = abs(killed - deposit) / killed if killed else math.inf
    limit = hexed(first["median_electron_step_mm"]) / MAX_STEP_RATIO
    every_particle = first["with_user_special_cuts"] == first["particles_with_a_process_manager"]
    return {"confirmed": every_particle and first["kills"] > 0 and relative <= SPECIAL_CUTS_TOLERANCE and hexed(second["max_electron_step_mm"]) <= hexed(second["limit_mm"]),
            "particles": first["particles_with_a_process_manager"], "with_cuts": first["with_user_special_cuts"], "short_lived": first["short_lived"], "empty": first["empty_process_list"], "lacking": first["lacking"][:300], "kills": first["kills"], "relative": relative,
            "limit_mm": hexed(second["limit_mm"]), "planned_limit_mm": limit, "longest_step_mm": hexed(second["max_electron_step_mm"])}


def judge_termination_classes(hadronic: dict, electromagnetic: dict) -> dict:
    looper = hexed(hadronic["looper_kinetic_MeV"])
    relative = hexed(electromagnetic["worst_relative_residual"])
    return {"confirmed": hadronic["accounting_errors"] == 0 and electromagnetic["accounting_errors"] == 0 and looper > 0 and relative <= EM_RELATIVE_LIMIT,
            "accounting_errors": hadronic["accounting_errors"] + electromagnetic["accounting_errors"], "looper_kinetic_MeV": looper,
            "events_with_a_looper": hadronic["events_with_a_looper"], "tracks": hadronic["tracks"], "em_worst_relative": relative, "em_limit": EM_RELATIVE_LIMIT}


def judge_sensitive_detectors(document: dict) -> dict:
    return {"confirmed": document["events_with_a_difference"] == 0 and document["steps_action"] > 0 and document["steps_first_sd"] == document["steps_second_sd"] == document["steps_action"],
            "steps_action": document["steps_action"], "first": document["steps_first_sd"], "second": document["steps_second_sd"],
            "events_with_a_difference": document["events_with_a_difference"]}


def fitted_radius(points: list) -> float:
    """Least-squares circle through the points (Kasa fit)."""
    n = len(points)
    mean_x, mean_y = sum(p[0] for p in points) / n, sum(p[1] for p in points) / n
    u, v = [p[0] - mean_x for p in points], [p[1] - mean_y for p in points]
    suu, svv, suv = sum(a * a for a in u), sum(b * b for b in v), sum(a * b for a, b in zip(u, v))
    suuu, svvv = sum(a ** 3 for a in u), sum(b ** 3 for b in v)
    suvv, svuu = sum(a * b * b for a, b in zip(u, v)), sum(b * a * a for a, b in zip(u, v))
    determinant = suu * svv - suv * suv
    centre_u = (svv * (suuu + suvv) - suv * (svvv + svuu)) / (2 * determinant)
    centre_v = (suu * (svvv + svuu) - suv * (suuu + suvv)) / (2 * determinant)
    return math.sqrt(centre_u ** 2 + centre_v ** 2 + (suu + svv) / n)


def straightness(points: list) -> float:
    first = points[0]
    last = max(points, key=lambda point: sum((a - b) ** 2 for a, b in zip(point, first)))  # two events write the same path: take the far end
    axis = [b - a for a, b in zip(first, last)]
    length = math.sqrt(sum(a * a for a in axis))
    worst = 0.0
    for point in points:
        offset = [b - a for a, b in zip(first, point)]
        along = sum(a * b for a, b in zip(offset, axis)) / length
        worst = max(worst, math.sqrt(max(sum(a * a for a in offset) - along * along, 0.0)))
    return worst


def judge_field_assignment(forward: dict, reverse: dict, mother_only: dict, none_manager: dict, no_manager: dict) -> dict:
    wanted = {"WithField": "field", "Free": "none", "Shared": "none"}
    both = all(row == wanted for document in (forward, reverse) for row in document["managers"].values())
    workers_equal_master = all(len({json.dumps(row, sort_keys=True) for row in document["managers"].values()}) == 1 for document in (forward, reverse))
    propagation_real = any(row != wanted for row in mother_only["managers"].values())
    path = [[hexed(a) for a in point] for point in forward["field_path_mm"]]
    expected = 1000.0 * TESLA_RADIUS_MM_PER_MEV
    radius = fitted_radius(path) if len(path) >= 3 else math.inf
    relative = abs(radius - expected) / expected
    free = [[hexed(a) for a in point] for point in none_manager["free_path_mm"]]
    deviation = straightness(free) if len(free) >= 2 else math.inf
    same_steps = none_manager["step_sequence"] == no_manager["step_sequence"] and bool(none_manager["step_sequence"])
    return {"confirmed": both and workers_equal_master and propagation_real and relative <= CURVATURE_TOLERANCE and deviation <= STRAIGHT_TOLERANCE_MM and same_steps,
            "orders_equal_the_ir": both, "workers_equal_master": workers_equal_master, "mother_only_differs": propagation_real, "radius_mm": radius, "expected_mm": expected,
            "relative": relative, "points": len(path), "straight_deviation_mm": deviation, "none_and_absent_manager_same_steps": same_steps}


def main(argv) -> int:
    if len(argv) != 2:
        print(json.dumps({"status": "rejected", "message": __doc__.splitlines()[-2]}))
        return 2
    folder = Path(argv[1])
    try:
        read = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in folder.glob("*.json")}
        second = dict(read["gb7-limited"], limit_mm=read["gb7-limit"]["limit_mm"])
        verdicts = {"GB3": judge_field_assignment(read["gb3-forward"], read["gb3-reverse"], read["gb3-mother_only"], read["gb3-none_manager"], read["gb3-no_manager"]),
                    "GB5": judge_sensitive_detectors(read["gb5"]), "GB7": judge_special_cuts(read["gb7"], second), "GB8": judge_termination_classes(read["gb8"], read["gb8em"]), "GB9": judge_unreleased_energy(read["gb9"], pdg_masses())}
    except (OSError, ValueError, KeyError) as err:
        print(json.dumps({"status": "error", "message": repr(err)}))
        return 2
    confirmed = all(item["confirmed"] for item in verdicts.values())
    print(json.dumps({"status": "ok" if confirmed else "failed", "verdicts": verdicts}, indent=1))
    return 0 if confirmed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

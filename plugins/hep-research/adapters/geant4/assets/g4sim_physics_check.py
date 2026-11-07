#!/usr/bin/env python3
"""check-spec rules of S3 (g4sim plan, Sections 6.2.9, 8.4, 8.6, 9.1): PAI semantics, the G4UserLimits restriction, time cuts and scorer combinations.

A particle's ionization process name comes from the effective config after initialization (`ionisation`), never from an assumption here.
Every function returns findings, each {code, path, message}; an empty list passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

PAI_MODELS = ("PAI", "PAIphoton")
ALL_PARTICLES = "all"
IONISATION_PROCESSES = ("eIoni", "muIoni", "ionIoni", "hIoni")
WORLD_REGION_NAMES = ("", "world", "World")
MAPPED_PROCESS = {"e-": "eIoni", "e+": "eIoni", "mu+": "muIoni", "mu-": "muIoni", "GenericIon": "ionIoni"}
ALLOWED_USER_LIMITS = {"max_step_mm"}

ADDITIVE = ("edep", "edep_visible", "edep_charged", "edep_nonionizing", "track_length", "edep_by_dedx_class")
BOUNDARY = ("n_crossings", "crossing_kinematics", "energy_out_by_face")
FIRST = ("time_first", "first_entry_kinematics")
LATER_QUANTITIES = {"edep_visible_ly_split": "S4", "photon_detected": "S7"}
SEGMENTATIONS = ("none", "along_axis", "cartesian_xy", "cartesian_xyz", "polar")
ALLOWED_SEGMENTATION = {**{name: SEGMENTATIONS for name in ADDITIVE}, **{name: ("none", "cartesian_xy") for name in BOUNDARY}, **{name: ("none",) for name in FIRST}}
BIRKS_QUANTITIES = ("edep_visible", "edep_by_dedx_class")


def _finding(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def mapped_process(particle: str) -> str:
    """The process a PAI request selects, by the requested particle's identity and not by the process that particle uses (GB11)."""
    return MAPPED_PROCESS.get(particle, "hIoni")


def actual_particles(ionisation_name: str, ionisation: dict) -> list:
    """Every particle carrying this process name: the set the request really acts on."""
    return sorted(name for name, own in ionisation.items() if own == ionisation_name)


def pai_findings(requests: list, regions, ionisation: dict, requirements=()) -> list:
    """Section 6.2.9. `ionisation` maps each particle of the table to its ionization process name, or None if it has none of the four."""
    findings = []
    by_region: dict = {}
    for at, request in enumerate(requests):
        where = f"physics.pai/{at}"
        region, particle, model = request.get("region"), request.get("particle"), request.get("model")
        if model not in PAI_MODELS:
            findings.append(_finding("pai-model", where, f"model {model!r} is not one of {PAI_MODELS}"))
        if region in WORLD_REGION_NAMES:
            findings.append(_finding("pai-region", where, f"region {region!r} means the world's default region to Geant4: name the region explicitly"))
        elif region not in regions:
            findings.append(_finding("pai-region", where, f"region {region!r} is not in the IR, and the PAI constructor has no guard of its own"))
        by_region.setdefault(region, []).append((at, particle))
        if particle == ALL_PARTICLES:
            continue
        if particle not in ionisation:
            findings.append(_finding("pai-particle", where, f"particle {particle!r} is not in the particle table, and the PAI constructor has no guard of its own"))
        elif ionisation[particle] not in IONISATION_PROCESSES:
            findings.append(_finding("pai-no-ionisation", where, f"{particle} has none of the four ionization processes"))
        elif ionisation[particle] != mapped_process(particle):
            findings.append(_finding("pai-mapping", where, f"{particle} maps to {mapped_process(particle)} but uses {ionisation[particle]}: it would get no PAI itself"))
    for region, rows in by_region.items():
        names = [particle for _, particle in rows]
        if ALL_PARTICLES in names and len(names) > 1:
            findings.append(_finding("pai-mixed", f"physics.pai/{rows[0][0]}", f"region {region}: `all` already covers the four processes, so another request would add a second set of models"))
            continue
        mapped = [mapped_process(particle) for particle in names if particle != ALL_PARTICLES]
        for repeated in sorted({name for name in mapped if mapped.count(name) > 1}):
            findings.append(_finding("pai-duplicate", f"physics.pai/{rows[0][0]}", f"region {region}: more than one request maps to {repeated}"))
    for at, requirement in enumerate(requirements):
        if requirement.get("need") != "thin_layer_ionisation":
            continue
        covered = _covered(requests, requirement.get("region"))
        for particle in requirement.get("particles", ()):
            if ionisation.get(particle) not in covered:
                findings.append(_finding("pai-requirement", f"physics_requirements/{at}", f"{particle} in region {requirement.get('region')} has no PAI request for its process"))
    return findings


def _covered(requests: list, region: str) -> set:
    names = [request.get("particle") for request in requests if request.get("region") == region]
    return set(IONISATION_PROCESSES) if ALL_PARTICLES in names else {mapped_process(name) for name in names}


def effective_pai(requests: list, ionisation: dict) -> list:
    """What Geant4 ends up doing, for the effective config: (region, process, model, actual particle set)."""
    rows = []
    for request in requests:
        names = IONISATION_PROCESSES if request["particle"] == ALL_PARTICLES else (mapped_process(request["particle"]),)
        rows += [{"region": request["region"], "process": name, "model": request["model"], "particles": actual_particles(name, ionisation)} for name in names]
    return rows


def limit_findings(card: dict) -> list:
    """Section 8.4: in `separated` mode G4UserLimits sets only the maximum step, because G4UserSpecialCuts would book the rest as deposit (GB7)."""
    if card.get("accounting") != "separated":
        return []
    return [_finding("separated-user-limits", f"physics.user_limits/{region}", f"{key} would be booked as deposit: use kill_policy")
            for region, limits in card.get("physics", {}).get("user_limits", {}).items() for key in sorted(set(limits) - ALLOWED_USER_LIMITS)]


def time_cut_findings(card: dict, scorers: list) -> list:
    """Section 8.6: the time cut is no earlier than the latest end of any scorer's time window."""
    cut = card.get("kill_policy", {}).get("time_cut_ns")
    if cut is None:
        return []
    return [_finding("time-cut", f"scorers/{at}", f"the time cut {cut} ns is earlier than the window's end {scorer['time_window_ns'][1]} ns")
            for at, scorer in enumerate(scorers) if "time_window_ns" in scorer and Decimal(str(cut)) < Decimal(str(scorer["time_window_ns"][1]))]


def _segmentation_name(scorer: dict) -> str:
    segmentation = scorer.get("segmentation", "none")
    return segmentation if isinstance(segmentation, str) else next(iter(segmentation))


def scorer_findings(scorers: list, materials: dict | None = None, selected_materials=None) -> list:
    """Section 9.1: which quantity takes which segmentation, split and level. `selected_materials` maps a scorer's name to its materials."""
    findings = []
    names: set = set()
    for at, scorer in enumerate(scorers):
        where, quantity = f"scorers/{at}", scorer.get("quantity")
        if scorer.get("name") in names:
            findings.append(_finding("scorer-name", where, f"{scorer.get('name')} appears twice"))
        names.add(scorer.get("name"))
        if quantity in LATER_QUANTITIES:
            findings.append(_finding("scorer-phase", where, f"{quantity} arrives in {LATER_QUANTITIES[quantity]}"))
            continue
        if quantity not in ALLOWED_SEGMENTATION:
            findings.append(_finding("scorer-quantity", where, f"unknown quantity {quantity!r}"))
            continue
        segmentation = _segmentation_name(scorer)
        if segmentation not in SEGMENTATIONS:
            findings.append(_finding("scorer-segmentation", where, f"unknown segmentation {segmentation!r}"))
        elif segmentation not in ALLOWED_SEGMENTATION[quantity]:
            findings.append(_finding("scorer-combination", where, f"{quantity} takes {ALLOWED_SEGMENTATION[quantity]}, not {segmentation}"))
        split = scorer.get("split")
        if split is not None and (quantity not in ADDITIVE or segmentation == "none"):
            findings.append(_finding("scorer-combination", where, "`split` needs an additive quantity with a segmentation"))
        if split not in (None, "apportion", "midpoint"):
            findings.append(_finding("scorer-combination", where, f"split {split!r} is not apportion or midpoint"))
        if split != "apportion" and ({"apportion_short_step_fraction", "chord_min_rigidity_GV"} & set(scorer)):
            findings.append(_finding("scorer-combination", where, "the short-step fraction and rigidity threshold belong to `apportion`"))
        if scorer.get("level", "column") != "column":
            findings.append(_finding("scorer-phase", where, f"level {scorer['level']} arrives in S4"))
        if quantity in BIRKS_QUANTITIES and materials is not None:
            for name in (selected_materials or {}).get(scorer.get("name"), ()):
                if "birks_mm_per_MeV" not in materials.get(name, {}).get("ionisation", {}):
                    findings.append(_finding("birks-undeclared", where, f"{name} declares no Birks constant, and Geant4 may set one silently (GB13)"))
    return findings


def source_findings(source: dict) -> list:
    """Section 6.3: the density type is declared, and `external` arrives in S4."""
    density = source.get("density")
    if density == "analytic":
        return []
    return [_finding("source-density", "source/density", "an external source arrives in S4" if density == "external" else f"density {density!r} is not declared")]


def card_findings(card: dict, request: dict | None = None, regions=(), ionisation: dict | None = None, requirements=(), materials=None, selected_materials=None) -> list:
    """All of the above that the inputs at hand can judge. Without `ionisation` the PAI semantics wait for the effective config."""
    findings = limit_findings(card)
    requests = card.get("physics", {}).get("pai", [])
    if requests and ionisation is not None:
        findings += pai_findings(requests, regions, ionisation, requirements)
    if request is not None:
        scorers = request.get("scorers", [])
        findings += time_cut_findings(card, scorers) + scorer_findings(scorers, materials, selected_materials) + source_findings(request.get("source", {}))
    return findings


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    print(json.dumps({"status": "rejected", "message": "a library: run g4sim_run.py check-spec or simulate"}))
    sys.exit(2)

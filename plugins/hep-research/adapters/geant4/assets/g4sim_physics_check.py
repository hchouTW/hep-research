#!/usr/bin/env python3
"""check-spec rules of S3 (g4sim plan, Sections 6.2.9, 8.4, 8.6, 9.1): PAI semantics, the G4UserLimits restriction, time cuts and scorer combinations.

A particle's ionization process name comes from the effective config after initialization (`ionisation`), never from an assumption here.
Every function returns findings, each {code, path, message}; an empty list passes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from decimal import Decimal
from pathlib import Path

PAI_MODELS = ("PAI", "PAIphoton")
ALL_PARTICLES = "all"
IONISATION_PROCESSES = ("eIoni", "muIoni", "ionIoni", "hIoni")
WORLD_REGION_NAMES = ("", "world", "World")
MAPPED_PROCESS = {"e-": "eIoni", "e+": "eIoni", "mu+": "muIoni", "mu-": "muIoni", "GenericIon": "ionIoni"}
ALLOWED_USER_LIMITS = {"max_step_mm"}

ADDITIVE = ("edep", "edep_visible", "edep_charged", "edep_nonionizing", "track_length", "edep_by_dedx_class", "edep_visible_ly_split")
BOUNDARY = ("n_crossings", "crossing_kinematics", "energy_out_by_face")
FIRST = ("time_first", "first_entry_kinematics")
PHOTON = ("photon_detected",)  # S7: a count per detecting volume, with optical physics on
LATER_QUANTITIES: dict = {}  # empty since photon_detected opened in S7
SEGMENTATIONS = ("none", "along_axis", "cartesian_xy", "cartesian_xyz", "polar")
ALLOWED_SEGMENTATION = {**{name: SEGMENTATIONS for name in ADDITIVE}, **{name: ("none", "cartesian_xy") for name in BOUNDARY}, **{name: ("none",) for name in FIRST + PHOTON}}
BIRKS_QUANTITIES = ("edep_visible", "edep_by_dedx_class", "edep_visible_ly_split")
SPLIT_QUANTITY = "edep_visible_ly_split"


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
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(scorer.get("name"))) or scorer.get("name") == "event":
            findings.append(_finding("scorer-name", where, f"name {scorer.get('name')!r}: a name is a word, and `event` heads a file's columns"))
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
        level = scorer.get("level", "column")
        if level == "event_file":
            if quantity != "edep" or scorer.get("hit_kind") not in ("tracker", "calorimeter"):
                findings.append(_finding("scorer-combination", where, "an event_file scorer is `edep` with hit_kind tracker or calorimeter"))
        elif level == "moments":
            if quantity not in ADDITIVE:
                findings.append(_finding("scorer-combination", where, "`moments` is for linear quantities"))
        elif level != "column":
            findings.append(_finding("scorer-quantity", where, f"unknown level {level!r}"))
        if quantity in BIRKS_QUANTITIES and materials is not None:
            for name in (selected_materials or {}).get(scorer.get("name"), ()):
                if "birks_mm_per_MeV" not in materials.get(name, {}).get("ionisation", {}):
                    findings.append(_finding("birks-undeclared", where, f"{name} declares no Birks constant, and Geant4 may set one silently (GB13)"))
                if quantity == SPLIT_QUANTITY and "scintillation" not in materials.get(name, {}):
                    findings.append(_finding("scintillation-undeclared", where, f"{name} declares no scintillation yield or RESOLUTIONSCALE (Section 10.3)"))
    return findings


def source_findings(source: dict) -> list:
    """Section 6.3: the density type is declared; an external source names a text event file, or HepMC3 if the installation record has it."""
    density = source.get("density")
    if density == "analytic":
        return []
    if density != "external":
        return [_finding("source-density", "source/density", f"density {density!r} is not declared")]
    if source.get("format") == "hepmc3":
        return [_finding("source-hepmc3", "source/format", "HepMC3 is not in the installation record of this host: use a text event file, or install it and record it")]
    if source.get("format") != "text":
        return [_finding("source-format", "source/format", f"format {source.get('format')!r} is not text or hepmc3")]
    return []


def plane_findings(request: dict) -> list:
    """Section 6.3: a reference plane states its frame."""
    return [_finding("plane-frame", f"reference_planes/{at}", f"plane {plane.get('name')!r} states no frame") for at, plane in enumerate(request.get("reference_planes", [])) if not plane.get("frame")]


def truth_findings(request: dict) -> list:
    """Section 9.3: the keeping rules are known ones, and a time bin has a width."""
    truth = request.get("truth", {})
    findings = []
    width = float(truth.get("time_bin_ns", 1))
    if not math.isfinite(width) or width <= 0:
        findings.append(_finding("truth-rule", "truth/time_bin_ns", "a time bin has a positive, finite width"))
    for at, rule in enumerate(truth.get("keep", [])):
        known = rule in ("primary", "decay_products", "all") or (isinstance(rule, dict) and "energy_above_MeV" in rule and set(rule) <= {"energy_above_MeV", "region"} and 0 <= float(rule["energy_above_MeV"]) < math.inf)
        if not known:
            findings.append(_finding("truth-rule", f"truth/keep/{at}", f"unknown keeping rule {rule!r}"))
    return findings


def hit_findings(scorers: list, regions: set, truth: dict) -> list:
    """On resolved scorers: a step is written once, a named readout can encode its cells, and a rule's region exists."""
    findings = []
    claimed: dict = {}
    for scorer in scorers:
        if "hit_kind" not in scorer:
            continue
        if "problem" in scorer.get("cell_id", {}):
            findings.append(_finding("hit-readout", f"scorers/{scorer['name']}", scorer["cell_id"]["problem"]))
        for template in scorer["templates"]:
            if template in claimed:
                findings.append(_finding("hit-overlap", f"scorers/{scorer['name']}", f"template {template} is also written by {claimed[template]}: each step would be written twice"))
            claimed[template] = scorer["name"]
    for at, rule in enumerate(truth.get("keep", [])):
        if isinstance(rule, dict) and "region" in rule and rule["region"] not in regions:
            findings.append(_finding("truth-rule", f"truth/keep/{at}", f"region {rule['region']!r} is not a named region of this specification"))
    return findings


def calibration_findings(request: dict) -> list:
    """Section 3, principle 7: a calibration workflow needs an analytic density, so an external source is refused there."""
    if request.get("source", {}).get("density") == "external":
        return [_finding("calibration-source", "source/density", "the calibration workflow refuses an external source: it has no analytic density")]
    return []


def event_range_findings(card: dict) -> list:
    """Section 10.2: first_event + number of events fits in the counter's word 0."""
    run = card.get("run", {})
    if run.get("first_event", 0) + run.get("events", 0) > 2 ** 32:
        return [_finding("event-range", "run", "first_event + events exceeds 2^32")]
    return []


BUILT_CONSTRUCTORS = {"G4OpticalPhysics", "g4sim_xtr"}
RADIATOR_CONSTRUCTOR = "g4sim_xtr"
RADIATOR_TABLE = Path(__file__).resolve().parent / "xtr_radiators.json"


def radiator_findings(card: dict, requirements, table: dict | None = None) -> list:
    """XTR rules 4 and 5 (Section 6.2.9, S7): the g4sim_xtr constructor attaches one radiator per transition_radiation requirement, named by
    its envelope; the run card's class must be in the adapter's table with the requirement's structure. G4StrawTubeXTRadiator has no foil
    count and no structure, so it is refused (addendum 11.1)."""
    table = table if table is not None else json.loads(RADIATOR_TABLE.read_text(encoding="utf-8"))["classes"]
    physics = card.get("physics", {})
    radiators = {item.get("envelope"): item for item in physics.get("xtr", [])}
    wanted = {requirement["templates"][0]: requirement for requirement in requirements if requirement.get("need") == "transition_radiation" and requirement.get("templates")}
    findings = []
    if (wanted or radiators) and RADIATOR_CONSTRUCTOR not in physics.get("extra_constructors", ()):
        findings.append({"code": "xtr-constructor", "path": "physics.extra_constructors", "message": f"XTR is attached by {RADIATOR_CONSTRUCTOR} in extra_constructors (rule 4)"})
    for envelope in sorted(set(wanted) - set(radiators)):
        findings.append({"code": "xtr-class-missing", "path": "physics.xtr", "message": f"the radiator of envelope {envelope} has no class in the run card"})
    for envelope in sorted(set(radiators) - set(wanted)):
        findings.append({"code": "xtr-requirement-missing", "path": "physics.xtr", "message": f"{envelope} is no transition_radiation envelope of the specification"})
    for envelope in sorted(set(wanted) & set(radiators)):
        name = radiators[envelope].get("radiator_class")
        entry = table.get(name)
        if entry is None:
            findings.append({"code": "xtr-class-unknown", "path": "physics.xtr", "message": f"{name} is not in xtr_radiators.json"})
        elif entry["structure"] is None:
            findings.append({"code": "xtr-class-structureless", "path": "physics.xtr", "message": f"{name} has no foil count and no structure, so g4sim cannot check it (addendum 11.1)"})
        elif entry["structure"] != wanted[envelope]["structure"]:
            findings.append({"code": "xtr-incompatible", "path": "physics.xtr", "message": f"{name} builds the structure {entry['structure']}, the specification's radiator is {wanted[envelope]['structure']} (rule 5)"})
    return findings


def optical_findings(card: dict, requirements, scorers=()) -> list:
    """A new-mode run (S7): G4OpticalPhysics is the one extra constructor g4sim_run builds, and it runs only with a specification that declares
    optical_scope, the templates KillProcess keeps photons in (GB16). Any other name would be ignored by the program, so it is refused here."""
    extra = card.get("physics", {}).get("extra_constructors", ())
    findings = [{"code": "extra-constructor-unknown", "path": "physics.extra_constructors", "message": f"g4sim_run builds only {sorted(BUILT_CONSTRUCTORS)}, not {name}"}
                for name in extra if name not in BUILT_CONSTRUCTORS]
    if "G4OpticalPhysics" in extra and not any(requirement.get("need") == "optical_scope" for requirement in requirements):
        findings.append({"code": "optical-no-scope", "path": "physics.extra_constructors", "message": "optical physics needs an optical_scope requirement in the specification"})
    if "G4OpticalPhysics" not in extra:
        findings += [{"code": "photon-detected-without-optics", "path": f"scorers/{at}", "message": "photon_detected counts optical photons, which need G4OpticalPhysics"}
                     for at, scorer in enumerate(scorers) if scorer.get("quantity") in PHOTON]
    return findings


def validation_findings(card: dict, materials: dict, material: str, effective: dict, resolution_scale: float) -> list:
    """check-spec of a validation run with full optical tracking (Section 10.4, S7): optical physics on; the material's RESOLUTIONSCALE equals
    the digitization's r; and, read back from Geant4, G4Scintillation holds G4EmSaturation and ScintillationByParticleType is off. The
    material declares its Birks constant, without which the saturation would use one Geant4 may set silently (GB13)."""
    findings = []
    if "G4OpticalPhysics" not in card.get("physics", {}).get("extra_constructors", ()):
        findings.append({"code": "validation-not-optical", "path": "physics.extra_constructors", "message": "a validation run tracks the light: it needs G4OpticalPhysics"})
    declared = materials.get(material, {})
    scale = declared.get("scintillation", {}).get("resolution_scale")
    if scale is None or float(scale) != float(resolution_scale):
        findings.append({"code": "validation-resolution-scale", "path": f"materials.{material}", "message": f"RESOLUTIONSCALE {scale} in the full optical run, r = {resolution_scale} in the digitization"})
    if "birks_mm_per_MeV" not in declared.get("ionisation", {}):
        findings.append({"code": "birks-undeclared", "path": f"materials.{material}", "message": f"{material} declares no Birks constant (GB13)"})
    optical = effective.get("optical", {})
    if optical.get("scintillation_saturation") is not True:
        findings.append({"code": "validation-saturation", "path": "effective-em.optical", "message": "G4Scintillation holds no G4EmSaturation"})
    if optical.get("scintillation_by_particle_type") is not False:
        findings.append({"code": "validation-by-particle-type", "path": "effective-em.optical", "message": "ScintillationByParticleType is not off"})
    return findings


def card_findings(card: dict, request: dict | None = None, regions=(), ionisation: dict | None = None, requirements=(), materials=None, selected_materials=None) -> list:
    """All of the above that the inputs at hand can judge. Without `ionisation` the PAI semantics wait for the effective config."""
    findings = limit_findings(card)
    requests = card.get("physics", {}).get("pai", [])
    if requests and ionisation is not None:
        findings += pai_findings(requests, regions, ionisation, requirements)
    if request is not None:
        scorers = request.get("scorers", [])
        findings += optical_findings(card, requirements, scorers) + radiator_findings(card, requirements)
        findings += time_cut_findings(card, scorers) + scorer_findings(scorers, materials, selected_materials) + source_findings(request.get("source", {})) + plane_findings(request) + truth_findings(request) + event_range_findings(card)
    return findings


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    print(json.dumps({"status": "rejected", "message": "a library: run g4sim_run.py check-spec or simulate"}))
    sys.exit(2)

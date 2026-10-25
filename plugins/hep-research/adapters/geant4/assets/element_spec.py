#!/usr/bin/env python3
"""element_sim specs and realization profiles of the geant4 adapter (Geant4 program B1.1, B1.6, B1.8).

Imported by geant4_run.py (subcommands check-spec and from-geometry, and runs of element_sim). It checks an
element_sim.spec/1 against element_sim/spec.schema.json and then the cross-field rules (unique names, mothers placed
once in the world, daughters inside their mother and every element inside the world, no overlapping siblings, roles
compatible with materials, at most one calorimeter mother, field regions on distinct elements that neither nest nor
overlap, cut regions on known elements, a gun source, the per-event seeds of the logical run, the hits-level event
limit, observables on CSV columns), and derives an element_sim.spec/1 from a design-geometry/1 file and an
element_sim.realization/1 profile (mappings 1.0.0 and 1.1.0, layered-spectrometer): deterministic, so the same two
files give a byte-identical spec. Run directly it only prints this help.
Exit codes: 0 (--help). Standard library only.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import ASSETS, JsonArgumentParser, SpecError, sha256_file, tilde  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.simulation.seeds import job_seeds  # noqa: E402

SPEC_SCHEMA = ASSETS / "element_sim" / "spec.schema.json"
REALIZATION_SCHEMA = ASSETS / "element_sim" / "realization.schema.json"
ADAPTER_VERSION = "0.5.0"
VACUUM_DENSITY_G_CM3 = 1e-20  # as contracts/validate.py: G4_Galactic and anything thinner is vacuum
MATTER_ROLES = ("tracker-plane", "tof-layer", "calorimeter-active", "calorimeter-passive")
CALO_DAUGHTER_ROLES = ("calorimeter-active", "calorimeter-passive")
LEVELS = ("none", "summary", "crossings", "hits")
TOL_MM = 1e-9  # containment and overlap tolerance (Geant4's surface tolerance is 1e-9 mm)
ROUND_MM = 1e-6  # from-geometry rounds derived lengths to 1 nm, so a float rounding of x/X0 cannot reach the spec
MAPPINGS = ("1.0.0", "1.1.0")
FIELDS_1_1 = ("layer_material", "layer_transverse_half_m", "field_extent_m", "tof_layer_positions_m",
              "tof_layer_thickness_m", "tof_time_resolution_ps", "calo_front_m", "calo_depth_x0",
              "calo_sampling_layers", "calo_passive_material", "calo_passive_thickness_mm", "calo_active_material",
              "calo_active_thickness_mm")
SAMPLING = FIELDS_1_1[-5:]  # the calorimeter's sampling structure: all five fields or none
DEPTH_TOLERANCE = 0.01  # relative: calo_depth_x0 against the sampling structure realized with the profile's X0
NUCLEONS = {"proton": 1, "deuteron": 2, "triton": 3, "He3": 3, "alpha": 4}
MAX_EVENT = 2 ** 31 - 1  # event numbers are I (32-bit) columns of the event file


def _problems_of(report) -> list[str]:
    return [f"{f.path}: {f.message}" for f in report.errors]


def copies(e: dict) -> list[list[float]]:
    """World centres of an element's copies (repeat and shift_mm applied)."""
    n = (e.get("repeat") or {}).get("count", 1)
    pitch = (e.get("repeat") or {}).get("pitch_mm", [0.0, 0.0, 0.0])
    shift = e.get("shift_mm", [0.0, 0.0, 0.0])
    return [[e["centre_mm"][i] + k * pitch[i] + shift[i] for i in range(3)] for k in range(n)]


def _box(centre, half) -> list[tuple[float, float]]:
    return [(centre[i] - half[i], centre[i] + half[i]) for i in range(3)]


def _inside(inner, outer) -> bool:
    return all(lo >= olo - TOL_MM and hi <= ohi + TOL_MM for (lo, hi), (olo, ohi) in zip(inner, outer))


def _overlap(a, b) -> bool:
    return all(min(ahi, bhi) - max(alo, blo) > TOL_MM for (alo, ahi), (blo, bhi) in zip(a, b))


def _vacuum(name: str, materials: dict) -> bool:
    if name == "G4_Galactic":
        return True
    m = materials.get(name)
    return bool(m) and m.get("density_g_cm3", 1.0) < VACUUM_DENSITY_G_CM3


def csv_columns(spec: dict) -> list[str]:
    """The per-event CSV columns of an element_sim spec (Actions.cc CsvColumns)."""
    cols = ["event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm", "primary_y_mm",
            "primary_z_mm", "primary_dx", "primary_dy", "primary_dz"]
    cols += [f"edep_{e['name']}_MeV" for e in spec["elements"]]
    cols += [f"plen_{e['name']}_mm" for e in spec["elements"]]
    cols += ["edep_world_MeV", "escape_world_MeV"]
    if any(e["role"] == "calorimeter" for e in spec["elements"]):
        cols += ["leak_rear_MeV", "leak_front_MeV", "leak_lateral_MeV"]
    return cols


def check_spec(spec) -> list[str]:
    """Every problem of an element_sim.spec/1 (schema first; the cross-field rules only when the schema passes)."""
    if not isinstance(spec, dict):
        return ["the spec must be a JSON object"]
    rep = validate(spec, str(SPEC_SCHEMA))
    if not rep.ok:
        return _problems_of(rep)
    problems: list[str] = []
    mats = {}
    for i, m in enumerate(spec.get("materials", [])):
        if m["name"].startswith("G4_"):
            problems.append(f"materials[{i}].name: G4_ names are NIST materials; give a user material another name")
        if ("components" in m) == ("z" in m or "a_g_mole" in m):
            problems.append(f"materials[{i}] needs either z and a_g_mole (one element) or components (a mixture)")
        if "z" in m and "a_g_mole" not in m:
            problems.append(f"materials[{i}] needs a_g_mole with z")
        if "components" in m:
            if abs(math.fsum(c["mass_fraction"] for c in m["components"]) - 1) > 1e-6:
                problems.append(f"materials[{i}].components: mass fractions must sum to 1")
            for c in m["components"]:
                if not (c["material"].startswith("G4_") or c["material"] in mats):
                    problems.append(f"materials[{i}]: component {c['material']} must be a NIST G4_ name or a material "
                                    "defined above")
        if m["name"] in mats:
            problems.append(f"materials[{i}]: {m['name']} is defined twice")
        mats[m["name"]] = m
    for name in [spec["world"]["material"]] + [e["material"] for e in spec["elements"]]:
        if not (name.startswith("G4_") or name in mats):
            problems.append(f"material {name} is neither a NIST G4_ name nor defined in materials")
    world = _box([0.0, 0.0, 0.0], spec["world"]["half_mm"])
    els = {}
    for e in spec["elements"]:
        if e["name"] in els or e["name"] in ("world", "World"):
            problems.append(f"element name {e['name']} is not unique")
        els[e["name"]] = e
    calos = [e["name"] for e in spec["elements"] if e["role"] == "calorimeter"]
    if len(calos) > 1:
        problems.append(f"at most one element has role calorimeter (found {calos})")
    for e in spec["elements"]:
        name, mother = e["name"], e.get("mother", "world")
        boxes = [_box(c, e["half_mm"]) for c in copies(e)]
        if mother != "world":
            m = els.get(mother)
            if m is None:
                problems.append(f"element {name}: unknown mother {mother}")
                continue
            if m.get("mother", "world") != "world" or (m.get("repeat") or {}).get("count", 1) != 1:
                problems.append(f"element {name}: its mother {mother} must be placed once in the world (one level of "
                                "nesting)")
                continue
            mbox = _box(copies(m)[0], m["half_mm"])
            for k, b in enumerate(boxes):
                if not _inside(b, mbox):
                    problems.append(f"element {name} copy {k} is not inside its mother {mother}")
        for k, b in enumerate(boxes):
            if not _inside(b, world):
                problems.append(f"element {name} copy {k} is not inside the world")
        if e["role"] in MATTER_ROLES and _vacuum(e["material"], mats):
            problems.append(f"element {name}: role {e['role']} needs a material that is not vacuum ({e['material']})")
        if e["role"] in CALO_DAUGHTER_ROLES and (mother == "world" or els.get(mother, {}).get("role") != "calorimeter"):
            problems.append(f"element {name}: role {e['role']} needs a mother with role calorimeter")
    by_mother: dict = {}
    for e in spec["elements"]:
        for k, c in enumerate(copies(e)):
            by_mother.setdefault(e.get("mother", "world"), []).append((e["name"], k, _box(c, e["half_mm"])))
    for mother, items in by_mother.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if _overlap(items[i][2], items[j][2]):
                    problems.append(f"elements {items[i][0]} copy {items[i][1]} and {items[j][0]} copy {items[j][1]} "
                                    f"overlap (mother {mother})")
                    break
    field = spec.get("field")
    if field:
        names = [r["element"] for r in field["regions"]]
        for r in field["regions"]:
            if r["element"] not in els:
                problems.append(f"field region names unknown element {r['element']}")
            elif (els[r["element"]].get("repeat") or {}).get("count", 1) != 1:
                problems.append(f"field region {r['element']}: a field element is placed once (no repeat)")
            elif any(not math.isfinite(b) for b in r["b_tesla"]):
                problems.append(f"field region {r['element']}: b_tesla must be finite")
        if len(set(names)) != len(names):
            problems.append("field regions: an element carries at most one field region")
        for a in names:
            for b in names:
                if a != b and a in els and b in els and els[a].get("mother", "world") == b:
                    problems.append(f"field regions {a} and {b} nest (field regions may not nest)")
        if field.get("min_epsilon_step", 5e-5) > field.get("max_epsilon_step", 1e-3):
            problems.append("field: min_epsilon_step exceeds max_epsilon_step")
    p = spec["physics"]
    if ("reference_list" in p) == ("em_constructor" in p):
        problems.append("physics needs exactly one of reference_list and em_constructor")
    seen = set()
    for r in p.get("regions", []):
        for n in r["elements"]:
            if n not in els:
                problems.append(f"physics region {r['name']} names unknown element {n}")
            if n in seen:
                problems.append(f"element {n} is in two physics regions")
            seen.add(n)
    for c in spec.get("ui_commands", []):
        if c.split()[0] in ("/run/initialize", "/run/beamOn", "/control/execute", "/control/shell"):
            problems.append(f"ui_commands may not contain {c.split()[0]}: the program initializes and runs itself")
    src = spec["source"]
    if src["type"] != "gun":
        problems.append(f"source.type {src['type']} is defined as an interface only (Geant4 program R.10.2)")
    else:
        energies = [k for k in ("energy_MeV", "ekin_per_nucleon_MeV") if k in src]
        if "particle" not in src:
            problems.append("source.particle is required for a gun")
        if "cycle" in src and energies:
            problems.append("source: cycle gives the energies; energy_MeV and ekin_per_nucleon_MeV go without it")
        if "cycle" not in src and len(energies) != 1:
            problems.append("source needs exactly one of energy_MeV, ekin_per_nucleon_MeV (or a cycle)")
        if "ekin_per_nucleon_MeV" in src and src.get("particle") not in NUCLEONS:
            problems.append(f"source.ekin_per_nucleon_MeV needs a light ion ({sorted(NUCLEONS)})")
        dirs = [src.get("direction", [1.0, 0.0, 0.0])] + [c["direction"] for c in src.get("cycle", [])]
        if any(math.fsum(x * x for x in d) == 0 for d in dirs):
            problems.append("source: a direction must not be the zero vector")
        pos = src.get("position_mm", [0.0, 0.0, 0.0])
        if not _inside(_box(pos, [0.0, 0.0, 0.0]), world):
            problems.append("source.position_mm is outside the world")
    run = spec["run"]
    first = run.get("first_event", 0)
    if list(run["seeds"]) != list(job_seeds(run["logical_run_seed"], first)):
        problems.append(f"run.seeds {run['seeds']} are not the job seeds {list(job_seeds(run['logical_run_seed'], first))}"
                        f" of logical run seed {run['logical_run_seed']} at event {first} (core/simulation/seeds.py)")
    if first + run["events"] - 1 > MAX_EVENT:
        problems.append(f"run.first_event + run.events - 1 = {first + run['events'] - 1} exceeds {MAX_EVENT}: event "
                        "numbers are 32-bit integers in the event file")
    if run.get("threads", 1) > 1 and run.get("run_manager", "serial") != "mt":
        problems.append("run.threads above 1 needs run_manager mt")
    out = spec.get("output", {})
    ef = out.get("event_file", {})
    if ef.get("level", "none") == "hits" and run["events"] > ef.get("max_events_hits", 100):
        problems.append(f"output.event_file: level hits allows at most max_events_hits = {ef.get('max_events_hits', 100)}"
                        f" events, the run has {run['events']}")
    if ("observables" in out) != ("blocks" in out):
        problems.append("output.observables and output.blocks go together")
    if "observables" in out:
        rep = validate(out["observables"], "simulation_observables.json")
        if not rep.ok:
            problems.append("output.observables is not a simulation-observables/1 declaration: "
                            + "; ".join(_problems_of(rep))[:400])
        else:
            names = [o["name"] for o in out["observables"]]
            if len(set(names)) != len(names):
                problems.append(f"output.observables: names must be unique ({names})")
            cols = set(csv_columns(spec))
            for o in out["observables"]:
                needed = {o["source_column"], *(c["column"] for c in o.get("selection") or [])}
                if needed - cols:
                    problems.append(f"output.observables {o['name']}: columns {sorted(needed - cols)} are not CSV columns")
                for c in o.get("selection") or []:
                    if c["op"] in ("contains", "!contains"):
                        problems.append(f"output.observables {o['name']}: element_sim has no string column for {c['op']}")
                n = (o["bins"]["hi"] - o["bins"]["lo"]) / o["bins"]["width"]
                if round(n) < 1 or abs(n - round(n)) > 1e-9 * max(1.0, n):
                    problems.append(f"output.observables {o['name']}: (hi - lo) / width must be a positive integer")
        if out.get("blocks", {}).get("first_event", 0) > first:
            problems.append("output.blocks.first_event (the logical run's first event) is after run.first_event")
    if out.get("debug_observable_dump") and "observables" not in out:
        problems.append("output.debug_observable_dump needs output.observables")
    return problems


def validate_spec(spec: dict) -> None:
    """Refuse (SpecError) an element_sim spec with any problem."""
    problems = check_spec(spec)
    if problems:
        raise SpecError("; ".join(problems)[:2000])


# --- from-geometry (B1.8) -----------------------------------------------------------------------------------------

def _r(x: float) -> float:
    """A derived length rounded to 1 nm (ROUND_MM), +0.0 for -0.0."""
    return round(x / ROUND_MM) * ROUND_MM + 0.0


def _axis(name: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[name]


def check_realization(prof) -> list[str]:
    """Every problem of an element_sim.realization/1 profile."""
    if not isinstance(prof, dict):
        return ["the realization profile must be a JSON object"]
    rep = validate(prof, str(REALIZATION_SCHEMA))
    return _problems_of(rep)


def _seq(value, n: int, what: str) -> list[float]:
    if isinstance(value, list):
        if len(value) != n:
            raise SpecError(f"geometry field {what} has {len(value)} values for {n} layers")
        return [float(v) for v in value]
    return [float(value)] * n


def from_geometry(geometry: dict, geometry_ref: dict, profile: dict, profile_ref: dict) -> dict:
    """The element_sim.spec/1 of a design-geometry/1 file and a realization profile (mapping 1.0.0): tracker planes
    at origin + layer_positions_m along the stack axis (thickness layer_x_over_x0 times the template's radiation
    length), one passive slab when passive_x_over_x0 > 0, a field-region element from the first to the last plane
    plus the profile's margin with B = field_T along the profile's field direction, then the profile's other elements,
    world, physics, source, run and output defaults; the provenance block names both inputs by sha256. Raises
    SpecError on an unknown geometry kind or mapping version, a missing template, or a derived spec that fails
    check_spec."""
    problems = check_realization(profile)
    if problems:
        raise SpecError("the realization profile does not validate: " + "; ".join(problems)[:600])
    if not isinstance(geometry, dict) or geometry.get("schema") != "design-geometry/1":
        raise SpecError("the geometry file is not design-geometry/1 (evaluate_design.py geometry writes it)")
    kind, version = geometry.get("geometry"), geometry.get("mapping_version")
    if kind != profile["geometry_kind"]:
        raise SpecError(f"geometry kind {kind!r} is not the profile's {profile['geometry_kind']!r}")
    if kind != "layered-spectrometer":
        raise SpecError(f"unknown geometry kind {kind!r} (from-geometry realizes layered-spectrometer)")
    fields = geometry.get("fields") or {}
    # mapping 1.1.0 only adds optional fields: a geometry file that uses none of them is realized as 1.0.0 (a 1.0.0
    # profile realizes it); one that uses any needs a profile that declares 1.1.0
    needed = "1.1.0" if any(f in fields for f in FIELDS_1_1) else "1.0.0"
    if version not in MAPPINGS or needed not in profile["mapping_versions"] or (needed == "1.1.0" and version != "1.1.0"):
        raise SpecError(f"mapping version {version!r} (fields of {needed}) is not one this adapter ({list(MAPPINGS)}) "
                        f"and the profile ({profile['mapping_versions']}) both realize")
    for f in ("layer_positions_m", "layer_x_over_x0", "passive_x_over_x0", "field_T"):
        if f not in fields:
            raise SpecError(f"the geometry file has no field {f}")
    tmpl = profile["templates"]
    for role in ("tracking", "bending"):
        if role not in tmpl:
            raise SpecError(f"the realization profile has no template for role {role}")
    passive = float(fields["passive_x_over_x0"])
    if passive > 0 and "passive" not in tmpl:
        raise SpecError("passive_x_over_x0 > 0 but the realization profile has no passive template")
    ax = _axis(profile["stack_axis"])
    origin = profile["origin_mm"]
    pos = [float(p) for p in fields["layer_positions_m"]]
    if not pos:
        raise SpecError("layer_positions_m is empty")
    n = len(pos)
    xx0 = _seq(fields["layer_x_over_x0"], n, "layer_x_over_x0")
    t_trk = tmpl["tracking"]
    trans = t_trk["transverse_half_mm"]
    if "layer_material" in fields and fields["layer_material"] != t_trk["material"]:
        raise SpecError(f"layer_material {fields['layer_material']!r} is not the tracking template's "
                        f"{t_trk['material']!r}: its radiation length belongs to the template (add a profile for it)")
    if "layer_transverse_half_m" in fields:
        lt = fields["layer_transverse_half_m"]
        if not (isinstance(lt, list) and len(lt) == 2 and all(isinstance(v, (int, float)) and v > 0 for v in lt)):
            raise SpecError("layer_transverse_half_m is two positive numbers (m)")
        trans = [_r(float(v) * 1000.0) for v in lt]

    def at(stack_mm: float, half_stack: float, transverse: list) -> tuple[list, list]:
        centre, half = list(origin), [0.0, 0.0, 0.0]
        centre[ax] = _r(origin[ax] + stack_mm)
        others = [i for i in range(3) if i != ax]
        half[ax] = _r(half_stack)
        for i, h in zip(others, transverse):
            half[i] = h
        return [_r(c) for c in centre], half

    elements = []
    b = tmpl["bending"]
    lo, hi = min(pos) * 1000.0, max(pos) * 1000.0
    region_lo, region_hi = lo - b["margin_mm"], hi + b["margin_mm"]
    if "field_extent_m" in fields:  # mapping 1.1.0: the field region's extent along the stack axis
        fe = fields["field_extent_m"]
        if not (isinstance(fe, list) and len(fe) == 2 and all(isinstance(v, (int, float)) for v in fe) and fe[0] < fe[1]):
            raise SpecError("field_extent_m is [lo, hi] (m, along the stack axis from the origin) with lo < hi")
        region_lo, region_hi = float(fe[0]) * 1000.0, float(fe[1]) * 1000.0
    rc, rh = at((region_lo + region_hi) / 2, (region_hi - region_lo) / 2, b["transverse_half_mm"])
    elements.append({"name": b["element"], "material": b["material"], "centre_mm": rc, "half_mm": rh,
                     "role": "passive"})
    for k, (p, x) in enumerate(zip(pos, xx0)):
        c, h = at(p * 1000.0, x * t_trk["radiation_length_mm"] / 2, trans)
        elements.append({"name": f"{t_trk['name_prefix']}{k + 1}", "material": t_trk["material"], "centre_mm": c,
                         "half_mm": h, "mother": b["element"], "role": "tracker-plane"})
    if passive > 0:
        t_p = tmpl["passive"]
        c, h = at(t_p["position_m"] * 1000.0, passive * t_p["radiation_length_mm"] / 2, t_p["transverse_half_mm"])
        el = {"name": t_p["element"], "material": t_p["material"], "centre_mm": c, "half_mm": h, "role": "passive"}
        rbox = _box(rc, rh)
        if _inside(_box(c, h), rbox):
            el["mother"] = b["element"]
        elements.append(el)
    elements += _profile_elements(profile, fields, ax, origin)
    spec = {"schema": "element_sim.spec/1",
            "note": f"derived by geant4_run.py from-geometry from candidate {geometry.get('candidate')} "
                    f"(figure of merit {geometry.get('figure_of_merit')}); never edited by hand (Geant4 program B1.8)",
            "world": profile["world"], "elements": elements}
    if profile.get("materials"):
        spec["materials"] = profile["materials"]
    field_t = float(fields["field_T"])
    if field_t != 0.0:
        d = profile["field_direction"]
        norm = math.sqrt(math.fsum(v * v for v in d))
        spec["field"] = {"regions": [{"element": b["element"], "b_tesla": [field_t * v / norm + 0.0 for v in d]}],
                         **profile.get("field", {})}
    for key in ("physics", "ui_commands", "source", "run", "output"):
        if key in profile:
            spec[key] = json.loads(json.dumps(profile[key]))
    run = spec.get("run", {})
    if "logical_run_seed" in run:
        run["seeds"] = list(job_seeds(run["logical_run_seed"], run.get("first_event", 0)))
    spec["provenance"] = {"generator": f"geant4_run.py from-geometry (adapter {ADAPTER_VERSION})",
                          "geometry": geometry_ref, "realization": profile_ref,
                          "candidate": str(geometry.get("candidate")),
                          "parameter_digest": str(geometry.get("parameter_digest")), "mapping_version": version}
    problems = check_spec(spec)
    if problems:
        raise SpecError("the derived spec fails check-spec: " + "; ".join(problems)[:1500])
    return spec


def _profile_elements(profile: dict, fields: dict, ax: int, origin: list) -> list[dict]:
    """The profile's other elements, with the mapping 1.1.0 fields applied: TOF layers at tof_layer_positions_m (stack
    axis from the origin, layer centres; thickness tof_layer_thickness_m; names and transverse sizes the profile's, in
    order), the calorimeter moved so its front face is at calo_front_m and its sampling structure rebuilt from the five
    calo sampling fields (layers; passive and active material and thickness: passive then active from the front face,
    pitch their sum), and calo_depth_x0 checked against that structure with the profile's calorimetry-em radiation
    lengths (relative DEPTH_TOLERANCE)."""
    els = json.loads(json.dumps(profile.get("elements", [])))
    tofs = [e for e in els if e["role"] == "tof-layer"]
    if "tof_layer_positions_m" in fields:
        pos = fields["tof_layer_positions_m"]
        if not isinstance(pos, list) or len(pos) != len(tofs):
            raise SpecError(f"tof_layer_positions_m has {len(pos) if isinstance(pos, list) else 'no'} values for the "
                            f"profile's {len(tofs)} TOF layers")
        for e, p in zip(tofs, pos):
            e["centre_mm"][ax] = _r(origin[ax] + float(p) * 1000.0)
    if "tof_layer_thickness_m" in fields:
        t = fields["tof_layer_thickness_m"]
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t <= 0:
            raise SpecError("tof_layer_thickness_m is one positive number (m)")
        for e in tofs:
            e["half_mm"][ax] = _r(float(t) * 1000.0 / 2)
    calo = [e for e in els if e["role"] == "calorimeter"]
    wants = [f for f in ("calo_front_m", "calo_depth_x0", *SAMPLING) if f in fields]
    if not wants:
        return els
    if len(calo) != 1:
        raise SpecError(f"{', '.join(wants)} need exactly one calorimeter element in the profile")
    mother = calo[0]
    daughters = [e for e in els if e.get("mother") == mother["name"]]
    front = mother["centre_mm"][ax] - mother["half_mm"][ax]
    if "calo_front_m" in fields:
        front = _r(origin[ax] + float(fields["calo_front_m"]) * 1000.0)
    samp = None
    if any(f in fields for f in SAMPLING):
        if not all(f in fields for f in SAMPLING):
            raise SpecError(f"the calorimeter sampling fields go together: {', '.join(SAMPLING)}")
        layers = fields["calo_sampling_layers"]
        samp = {"layers": layers, "passive": {"material": fields["calo_passive_material"],
                                              "thickness_mm": fields["calo_passive_thickness_mm"]},
                "active": {"material": fields["calo_active_material"],
                           "thickness_mm": fields["calo_active_thickness_mm"]}}
        ok = (isinstance(layers, (int, float)) and not isinstance(layers, bool) and layers == int(layers) and layers > 0
              and all(isinstance(samp[k]["material"], str) and isinstance(samp[k]["thickness_mm"], (int, float))
                      and samp[k]["thickness_mm"] > 0 for k in ("passive", "active")))
        if not ok:
            raise SpecError("calo_sampling_layers is a positive whole number; the materials are names and the "
                            "thicknesses positive numbers (mm)")
        samp["layers"] = int(layers)
        roles = {"calorimeter-passive": samp["passive"], "calorimeter-active": samp["active"]}
        if sorted(d["role"] for d in daughters) != sorted(roles):
            raise SpecError("the calorimeter sampling fields need the profile's calorimeter to have one passive and "
                            "one active daughter")
        tp, ta = float(samp["passive"]["thickness_mm"]), float(samp["active"]["thickness_mm"])
        pitch = tp + ta
        mother["half_mm"][ax] = _r(samp["layers"] * pitch / 2)
        for d in daughters:
            s = roles[d["role"]]
            d["material"] = s["material"]
            d["half_mm"][ax] = _r(float(s["thickness_mm"]) / 2)
            p = [0.0, 0.0, 0.0]
            p[ax] = _r(pitch)
            d["repeat"] = {"count": samp["layers"], "pitch_mm": p}
    shift = front - (mother["centre_mm"][ax] - mother["half_mm"][ax])
    mother["centre_mm"][ax] = _r(front + mother["half_mm"][ax])
    offset = 0.0
    for d in sorted(daughters, key=lambda d: d["role"] != "calorimeter-passive"):
        if samp is not None:  # passive then active from the front face
            d["centre_mm"][ax] = _r(front + offset + d["half_mm"][ax])
            offset += 2 * d["half_mm"][ax]
        else:
            d["centre_mm"][ax] = _r(d["centre_mm"][ax] + shift)
    if "calo_depth_x0" in fields:
        x0 = ((profile.get("templates") or {}).get("calorimetry-em") or {}).get("radiation_lengths_mm") or {}
        depth = 0.0
        for d in daughters:
            if d["material"] not in x0:
                raise SpecError(f"calo_depth_x0: the profile's calorimetry-em template has no radiation length for "
                                f"{d['material']}")
            depth += (d.get("repeat") or {}).get("count", 1) * 2 * d["half_mm"][ax] / x0[d["material"]]
        want = float(fields["calo_depth_x0"])
        if abs(depth / want - 1) > DEPTH_TOLERANCE:
            raise SpecError(f"calo_depth_x0 {want} differs from the realized sampling structure's {depth:.4g} X0 by "
                            f"more than {DEPTH_TOLERANCE:.0%}")
    return els


def file_ref(path: Path) -> dict:
    return {"path": tilde(path), "sha256": sha256_file(path)}


def canonical(doc: dict) -> str:
    """The JSON text of a derived spec: sorted keys, one space indent, newline at the end (byte-identical reruns;
    float values round-trip through repr)."""
    for v in _floats(doc):
        if float.fromhex(v.hex()) != v:
            raise SpecError("a derived number does not round-trip through float.hex")
    return json.dumps(doc, indent=1, sort_keys=True) + "\n"


def _floats(x):
    if isinstance(x, float):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _floats(v)
    elif isinstance(x, list):
        for v in x:
            yield from _floats(v)


if __name__ == "__main__":
    JsonArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    sys.exit(0)

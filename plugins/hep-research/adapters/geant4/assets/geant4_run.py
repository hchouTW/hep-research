#!/usr/bin/env python3
"""Run the layered_sim and element_sim Geant4 programs from a JSON spec and record each run (WP1 M2, Geant4 program B1).

Purpose: one recorded Geant4 run per spec: per-event CSV, log, material dump and data-path record in a work folder,
and a computational-run record with a `simulation` block (Geant4 version and commit, datasets with the paths
resolved at run time and their content hashes, physics settings and UI commands verbatim, cuts and step limits,
spec and material-dump hashes, random engine and seeds, event count, run manager and threads). Every record is
`unvalidated` (or also `failed`): a run that completes is not physical validity, which hep-detector decides.

Tool and licence boundary: Geant4 (Geant4 Software License, Version 1.0, 28 June 2006) is built by geant4_build.py
in the user's work folder; layered_sim (assets/layered_sim/, this plugin's code) links against that installation and
runs as a separate executable that exchanges JSON and CSV. Nothing of Geant4 is bundled.

Method: the spec is validated here first (spec.schema.json; exit 2 on any problem), the output paths are set inside
<work>/<run-id>/, and layered_sim runs with every Geant4 dataset variable unset except those of the build record (so
Geant4's automatic data search cannot silently pick another copy). After the run the data-path record is compared
with the build record: a resolved path or content hash that differs makes the run `failed`.
From adapter 0.3.0 (Geant4 program B1) a spec whose schema is element_sim.spec/1 runs element_sim (box elements, one
level of nesting, uniform field regions, plane crossings of every charged track, calorimeter leakage, per-event
seeding only) with the same boundary artifacts, plus the per-event ROOT file events.root at event-file level summary
or above, recorded by path, file sha256 and simroot's content_sha256 (the files are never committed); a run that is
killed or times out is incomplete (exit 3).
Subcommands:
  build-sim  configure and build layered_sim (default) or, with --program element_sim, element_sim and simroot
  check-spec validate an element_sim.spec/1 (element_sim/spec.schema.json and the cross-field rules of
             element_spec.py): {ok, problems}, exit 0 or 2; no Geant4 needed
  from-geometry  a design-geometry/1 file (evaluate_design.py geometry) and an element_sim.realization/1 profile ->
             an element_sim.spec/1 (mapping 1.0.0 or 1.1.0; deterministic: the same inputs give a byte-identical spec whose
             provenance names both by sha256); exit 2 on an unknown kind or version, a missing template or a derived
             spec that fails check-spec
  run        one spec -> <work>/<run-id>/ (events.csv, materials.json, datapaths.json, log.txt, spec.json) and --record
  scan       base spec + parameter grid -> specs and a workflow.json for skills/hep-computing/scripts/run_workflow.py
             (point k gets seeds [s0, s1 + k] unless the grid scans run.seeds; from adapter 0.2.0 a base spec without
             run.seeding, and every point of a base spec that declares per-event seeding, gets per-event seeding with
             its own run.logical_run_seed S = H(study_id, role, point id), study_id from --study-id (default the grid
             name) and role from --role (default scan), unless the grid scans run.logical_run_seed; --seeding stream
             keeps the stream for a base without run.seeding);
             a step whose estimated time (events / --events-per-second) exceeds 3600 s is refused: partition it
  chunk      a local_partition.py worker: events [start, stop) with the chunk's seed (with --logical-run-seed S the
             job seeds H(S, start, 0), H(S, start, 1), core/simulation/seeds.py); writes additive sums only
             (n_events, sum_*, sumsq_*) plus {"csv": [{path, sha256}], "records": [...]} for --rule csv=concat
  summarize  from adapter 0.2.0 (chunks with output.observables carry their summaries; merge with
             --rule summaries=concat): the summaries merged block by block and each observable's batch-means mean and
             SE, reading no CSV (A2.6); for older partitions, means and standard errors from the additive sums
             (non-additive quantities after the merge); with --work, the chunk CSVs are checked against the merged
             hashes and for duplicate event numbers; with --single-record, each mean is compared with one
             unpartitioned run (|z| <= --z-max, default 3)
  reduce     a gzip-compressed copy (mtime 0, byte-reproducible) of chosen columns of a run's CSV, for replay
  oracle     run hep-detector's geant4_benchmarks.py on a recorded run through a subprocess (never imported)
Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_run.py build-sim --build-record BUILD.json --work DIR [--program element_sim]
  python3 adapters/geant4/assets/geant4_run.py check-spec --spec SPEC.json
  python3 adapters/geant4/assets/geant4_run.py from-geometry --geometry studies/G.geometry.json --profile PROFILE.json --out SPEC.json
  python3 adapters/geant4/assets/geant4_run.py run --spec SPEC.json --exe EXE --build-record BUILD.json --work DIR --run-id ID --record OUT.json
      [--evidence-role ROLE --point-id ID [--logical-run-seed S] [--seed-group NAME]] [--simroot SIMROOT]
  python3 adapters/geant4/assets/geant4_run.py scan --base SPEC.json --grid GRID.json --exe EXE --build-record BUILD.json --out-dir DIR --events-per-second R [--seeding per-event|stream]
  python3 adapters/geant4/assets/geant4_run.py chunk --spec SPEC.json --exe EXE --build-record BUILD.json --work DIR --start A --stop B --seed S --id ID --out OUT.json
  python3 adapters/geant4/assets/geant4_run.py summarize --merged MERGED.json [--work DIR] [--single-record RUN.json]
  python3 adapters/geant4/assets/geant4_run.py reduce --csv EVENTS.csv --columns C1 C2 ... --out OUT.csv.gz
  python3 adapters/geant4/assets/geant4_run.py oracle --benchmark-config CONFIG.json [--out OUT.json]
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status, status_label, inputs, defaults_used, and the subcommand's result.
Exit codes: 0 ok; 1 the run failed (program error, data-path mismatch, benchmark failed); 2 bad input; 3 Geant4,
cmake or the program missing, or an element_sim run interrupted (incomplete). Standard library only.
"""
from __future__ import annotations

import datetime
import gzip
import hashlib
import itertools
import json
import math
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import (ASSETS, DATA_VARS, PLUGIN, JsonArgumentParser, SpecError, build_record_ok, data_env,  # noqa: E402
                      expand, install_prefix, record_skeleton, run_settings, sha256_file, sha256_json, tilde,
                      write_json)
from contracts.identity import plugin_release  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.validate import geant4_spec_v1, geant4_tree_v1  # noqa: E402
from core.simulation import estimates as ESTIMATES, summary as SUMMARY  # noqa: E402
from core.simulation.seeds import job_seeds, logical_run_seed  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402
import element_spec as ES  # noqa: E402
import simreco_spec as RS  # noqa: E402

# every source file of each program's build, as paths under assets/, per program (adapter 0.2.0: the g4sim/ group was
# added and MiniJson.hh moved there, so the keys of sources_sha256 changed once, from bare names to these paths;
# adapter 0.3.0: a map per program instead of one flat tuple, the keys of a layered_sim record are unchanged)
ADAPTER_VERSION = "0.5.0"
SCHEMAS = ASSETS / "schemas"
STRING_COLUMNS = ("primary_end_process",)  # the only non-numeric CSV column (output.schema.json)
A2_OUTPUTS = ("summary.json", "column_map.json", "probe.json", "observables_dump.csv")  # adapter 0.2.0
SIM_SOURCES = {
    "layered_sim": tuple(f"layered_sim/{s}" for s in (
        "CMakeLists.txt", "Spec.hh", "Spec.cc", "Detector.hh", "Detector.cc", "Physics.hh", "Physics.cc", "Actions.hh",
        "Actions.cc", "layered_sim.cc")),
    "element_sim": tuple(f"element_sim/{s}" for s in (
        "CMakeLists.txt", "Spec.hh", "Spec.cc", "Detector.hh", "Detector.cc", "Field.hh", "Field.cc", "Actions.hh",
        "Actions.cc", "EventFile.hh", "EventFile.cc", "element_sim.cc")),
    "simroot": ("simroot/simroot.cc",),
    "simreco": ("simreco/CMakeLists.txt", "simreco/Fit.hh", "simreco/simreco.cc"),
    "g4sim": tuple(f"g4sim/{s}" for s in (
        "MiniJson.hh", "SimHash.hh", "SimSeed.hh", "SimSummary.hh", "SimObservables.hh", "SimProbe.hh", "SimCsv.hh",
        "SimMaterials.hh", "SimPhysics.hh")),
}
PROGRAM_GROUPS = {"layered_sim": ("layered_sim", "g4sim"), "element_sim": ("element_sim", "simroot", "g4sim"),
                  "simreco": ("simreco", "g4sim")}
PROGRAMS = {"layered_sim.spec/1": "layered_sim", "element_sim.spec/1": "element_sim"}


def program_sources(program: str) -> dict[str, str]:
    """{path under assets/: sha256} of every source file a program's build compiles (with the g4sim headers)."""
    return {s: sha256_file(ASSETS / s) for g in PROGRAM_GROUPS[program] for s in SIM_SOURCES[g]}


def program_of(spec) -> str:
    """layered_sim or element_sim, by the spec's schema (SpecError for anything else)."""
    name = PROGRAMS.get(spec.get("schema")) if isinstance(spec, dict) else None
    if not name:
        raise SpecError(f"schema must be one of {sorted(PROGRAMS)}")
    return name


def validate_any(spec: dict) -> str:
    """Validate a spec of either program; returns the program."""
    name = program_of(spec)
    if name == "element_sim":
        ES.validate_spec(spec)
    else:
        validate_spec(spec)
    return name
BENCHMARKS = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"
STEP_LIMIT_S = 3600  # skills/hep-computing/scripts/run_workflow.py STEP_TIMEOUT_S
STATES = ("solid", "liquid", "gas")
EM_CONSTRUCTORS = ("G4EmStandardPhysics", "G4EmStandardPhysics_option1", "G4EmStandardPhysics_option2",
                   "G4EmStandardPhysics_option3", "G4EmStandardPhysics_option4", "G4EmLivermorePhysics",
                   "G4EmPenelopePhysics", "G4EmLowEPPhysics", "G4EmStandardPhysicsGS", "G4EmStandardPhysicsSS",
                   "G4EmStandardPhysicsWVI")


def _num(x, where, positive=False, nonneg=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise SpecError(f"{where} must be a finite number")
    if positive and x <= 0:
        raise SpecError(f"{where} must be positive")
    if nonneg and x < 0:
        raise SpecError(f"{where} must not be negative")
    return x


def _int(x, where, minimum=None):
    if isinstance(x, bool) or not isinstance(x, int):
        raise SpecError(f"{where} must be an integer")
    if minimum is not None and x < minimum:
        raise SpecError(f"{where} must be at least {minimum}")
    return x


def _keys(d, where, allowed, required=()):
    if not isinstance(d, dict):
        raise SpecError(f"{where} must be an object")
    extra = sorted(set(d) - set(allowed))
    if extra:
        raise SpecError(f"{where}: unknown key(s) {extra}")
    for k in required:
        if k not in d:
            raise SpecError(f"{where}.{k} is required")


def validate_spec(spec: dict) -> None:
    """Refuse (SpecError) anything assets/layered_sim/spec.schema.json does not allow, plus the cross-field rules."""
    _keys(spec, "spec", ("schema", "note", "source", "geometry", "materials", "physics", "ui_commands", "gun", "run",
                         "output"), ("schema", "geometry", "physics", "gun", "run"))
    if spec["schema"] != "layered_sim.spec/1":
        raise SpecError("schema must be layered_sim.spec/1")
    g = spec["geometry"]
    _keys(g, "geometry", ("lateral_mm", "layers", "world"), ("lateral_mm", "layers", "world"))
    _num(g["lateral_mm"], "geometry.lateral_mm", positive=True)
    if not isinstance(g["layers"], list) or not g["layers"]:
        raise SpecError("geometry.layers must be a non-empty list")
    slabs = {}
    for i, layer in enumerate(g["layers"]):
        _keys(layer, f"geometry.layers[{i}]", ("repeat", "slabs"), ("slabs",))
        _int(layer.get("repeat", 1), f"geometry.layers[{i}].repeat", 1)
        if not isinstance(layer["slabs"], list) or not layer["slabs"]:
            raise SpecError(f"geometry.layers[{i}].slabs must be a non-empty list")
        for j, s in enumerate(layer["slabs"]):
            w = f"geometry.layers[{i}].slabs[{j}]"
            _keys(s, w, ("name", "material", "thickness_mm", "sensitive", "shift_mm"), ("name", "material", "thickness_mm"))
            _num(s.get("shift_mm", 0), f"{w}.shift_mm")
            if not isinstance(s["name"], str) or not s["name"].replace("_", "").isalnum():
                raise SpecError(f"{w}.name must be letters, digits and underscores")
            if not isinstance(s["material"], str) or not s["material"]:
                raise SpecError(f"{w}.material is required")
            _num(s["thickness_mm"], f"{w}.thickness_mm", positive=True)
            if not isinstance(s.get("sensitive", False), bool):
                raise SpecError(f"{w}.sensitive must be true or false")
            prev = slabs.setdefault(s["name"], s)
            if (prev["material"], prev["thickness_mm"]) != (s["material"], s["thickness_mm"]):
                raise SpecError(f"slab name {s['name']} is reused with another material or thickness")
    world = g["world"]
    _keys(world, "geometry.world", ("material", "scale", "size_mm"), ("material",))
    if ("scale" in world) == ("size_mm" in world):
        raise SpecError("geometry.world needs exactly one of scale and size_mm")
    if "scale" in world and _num(world["scale"], "geometry.world.scale") <= 1:
        raise SpecError("geometry.world.scale must exceed 1")
    if "size_mm" in world:
        if not isinstance(world["size_mm"], list) or len(world["size_mm"]) != 3:
            raise SpecError("geometry.world.size_mm must have three numbers")
        for x in world["size_mm"]:
            _num(x, "geometry.world.size_mm", positive=True)
    defined = set()
    for i, m in enumerate(spec.get("materials", [])):
        w = f"materials[{i}]"
        _keys(m, w, ("name", "z", "a_g_mole", "components", "density_g_cm3", "state", "temperature_K", "pressure_Pa",
                     "source"), ("name", "density_g_cm3"))
        if ("components" in m) == ("z" in m or "a_g_mole" in m):
            raise SpecError(f"{w} needs either z and a_g_mole (one element) or components (a mixture), not both")
        if "components" in m:
            comps = m["components"]
            if not isinstance(comps, list) or len(comps) < 2:
                raise SpecError(f"{w}.components must list at least two {{material, mass_fraction}} entries")
            for j, c in enumerate(comps):
                _keys(c, f"{w}.components[{j}]", ("material", "mass_fraction"), ("material", "mass_fraction"))
                if not isinstance(c["material"], str) or not (c["material"].startswith("G4_") or c["material"] in defined):
                    raise SpecError(f"{w}.components[{j}].material must be a NIST G4_ name or a material defined above")
                _num(c["mass_fraction"], f"{w}.components[{j}].mass_fraction", positive=True)
            if abs(math.fsum(c["mass_fraction"] for c in comps) - 1) > 1e-6:
                raise SpecError(f"{w}.components: mass fractions must sum to 1")
        else:
            _keys(m, w, ("name", "z", "a_g_mole", "density_g_cm3", "state", "temperature_K", "pressure_Pa", "source"),
                  ("name", "z", "a_g_mole", "density_g_cm3"))
            _int(m["z"], f"{w}.z", 1)
            _num(m["a_g_mole"], f"{w}.a_g_mole", positive=True)
        _num(m["density_g_cm3"], f"{w}.density_g_cm3", positive=True)
        if m.get("state", "solid") not in STATES:
            raise SpecError(f"{w}.state must be one of {STATES}")
        if m["name"].startswith("G4_"):
            raise SpecError(f"{w}.name: G4_ names are NIST materials; give a user material another name")
        defined.add(m["name"])
    p = spec["physics"]
    _keys(p, "physics", ("reference_list", "em_constructor", "decay", "default_cut_mm", "regions", "step_limit_mm",
                         "min_ekin_MeV", "kill_secondaries", "justification"), ("default_cut_mm",))
    if ("reference_list" in p) == ("em_constructor" in p):
        raise SpecError("physics needs exactly one of reference_list and em_constructor")
    if "em_constructor" in p and p["em_constructor"] not in EM_CONSTRUCTORS:
        raise SpecError(f"physics.em_constructor must be one of {EM_CONSTRUCTORS}")
    _num(p["default_cut_mm"], "physics.default_cut_mm", positive=True)
    for k in ("step_limit_mm", "min_ekin_MeV"):
        if k in p:
            _num(p[k], f"physics.{k}", nonneg=True)
    for i, r in enumerate(p.get("regions", [])):
        _keys(r, f"physics.regions[{i}]", ("name", "slabs", "cut_mm"), ("name", "slabs", "cut_mm"))
        _num(r["cut_mm"], f"physics.regions[{i}].cut_mm", positive=True)
        unknown = [s for s in r["slabs"] if s not in slabs]
        if unknown:
            raise SpecError(f"physics.regions[{i}] names unknown slab(s) {unknown}")
    ui = spec.get("ui_commands", [])
    if not isinstance(ui, list) or not all(isinstance(c, str) and c.startswith("/") for c in ui):
        raise SpecError("ui_commands must be a list of Geant4 UI commands (each starting with '/')")
    for c in ui:
        if c.split()[0] in ("/run/initialize", "/run/beamOn", "/control/execute", "/control/shell"):
            raise SpecError(f"ui_commands may not contain {c.split()[0]}: the program initializes and runs itself")
    gun = spec["gun"]
    _keys(gun, "gun", ("particle", "energy_MeV", "world_fraction", "direction"), ("particle", "energy_MeV"))
    _num(gun["energy_MeV"], "gun.energy_MeV", positive=True)
    f = _num(gun.get("world_fraction", -0.5), "gun.world_fraction")
    if not -0.5 <= f < 0:
        raise SpecError("gun.world_fraction must be in [-0.5, 0): the gun starts upstream, inside the world")
    run = spec["run"]
    _keys(run, "run", ("events", "first_event", "chunk", "seeds", "run_manager", "threads", "seeding",
                       "logical_run_seed"), ("events", "seeds"))
    if run.get("seeding", "stream") not in ("stream", "per-event"):
        raise SpecError("run.seeding must be stream or per-event")
    if "logical_run_seed" in run:
        _int(run["logical_run_seed"], "run.logical_run_seed", 1)
    if run.get("seeding") == "per-event" and "logical_run_seed" not in run:
        raise SpecError("run.seeding per-event needs run.logical_run_seed (S, core/simulation/seeds.py)")
    _int(run["events"], "run.events", 1)
    _int(run.get("first_event", 0), "run.first_event", 0)
    if not isinstance(run["seeds"], list) or len(run["seeds"]) != 2:
        raise SpecError("run.seeds must be two positive integers")
    for s in run["seeds"]:
        _int(s, "run.seeds", 1)
    if run.get("run_manager", "serial") not in ("serial", "mt"):
        raise SpecError("run.run_manager must be serial or mt")
    _int(run.get("threads", 1), "run.threads", 1)
    out = spec.get("output", {})
    _keys(out, "output", ("overlap_test_points", "per_instance", "observables", "blocks", "debug_observable_dump"))
    if ("observables" in out) != ("blocks" in out):
        raise SpecError("output.observables and output.blocks go together")
    if "observables" in out:
        rep = validate(out["observables"], "simulation_observables.json")
        if not rep.ok:
            raise SpecError("output.observables is not a simulation-observables/1 declaration: "
                            + "; ".join(f"{f.path} {f.message}" for f in rep.errors)[:400])
        names = [o["name"] for o in out["observables"]]
        if len(set(names)) != len(names):
            raise SpecError(f"output.observables: names must be unique ({names})")
        cols = set(csv_columns(spec))
        for o in out["observables"]:
            needed = {o["source_column"], *(c["column"] for c in o.get("selection") or [])}
            if needed - cols:
                raise SpecError(f"output.observables {o['name']}: columns {sorted(needed - cols)} are not CSV columns")
            if o["source_column"] in STRING_COLUMNS:
                raise SpecError(f"output.observables {o['name']}: source_column {o['source_column']} is not numeric")
            for c in o.get("selection") or []:
                if c["op"] in ("contains", "!contains") and (c["column"] not in STRING_COLUMNS
                                                             or not isinstance(c["value"], str)):
                    raise SpecError(f"output.observables {o['name']}: {c['op']} needs a string column and a string "
                                    "value (the C++ and Python summaries agree only there)")
            n = (o["bins"]["hi"] - o["bins"]["lo"]) / o["bins"]["width"]
            if round(n) < 1 or abs(n - round(n)) > 1e-9 * max(1.0, n):
                raise SpecError(f"output.observables {o['name']}: (hi - lo) / width must be a positive integer")
        b = out["blocks"]
        _keys(b, "output.blocks", ("blocks", "block_size", "first_event"), ("blocks", "block_size"))
        _int(b["blocks"], "output.blocks.blocks", 2)  # batch means need at least two blocks
        _int(b["block_size"], "output.blocks.block_size", 1)
        _int(b.get("first_event", 0), "output.blocks.first_event", 0)
        if b.get("first_event", 0) > run.get("first_event", 0):
            raise SpecError("output.blocks.first_event (the logical run's first event) is after run.first_event")
    if not isinstance(out.get("debug_observable_dump", False), bool):
        raise SpecError("output.debug_observable_dump must be true or false")
    if out.get("debug_observable_dump") and "observables" not in out:
        raise SpecError("output.debug_observable_dump needs output.observables")


def csv_columns(spec: dict) -> list[str]:
    """The per-event CSV columns of a spec (layered_sim Actions.cc CsvColumns; output.schema.json)."""
    names, placements = [], 0
    for layer in spec["geometry"]["layers"]:
        placements += layer.get("repeat", 1) * len(layer["slabs"])
        for s in layer["slabs"]:
            if s["name"] not in names:
                names.append(s["name"])
    cols = ["event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm", "primary_y_mm",
            "primary_z_mm", "primary_dx", "primary_dy", "primary_dz"]
    for n in names:
        cols += [f"edep_{n}_MeV", f"chlen_{n}_mm", f"plen_{n}_mm"]
    if (spec.get("output") or {}).get("per_instance"):
        cols += [f"edep_copy{i}_MeV" for i in range(placements)]
    return cols + ["edep_world_MeV", "leak_gamma_MeV", "leak_e_MeV", "leak_nu_MeV", "leak_other_MeV", "leak_rear_MeV",
                   "leak_front_MeV", "leak_lateral_MeV", "killed_booked_MeV", "killed_unbooked_MeV", "killed_eplus",
                   "exit_ekin_MeV", "primary_eloss_MeV", "exit_dx", "exit_dy", "exit_dz", "primary_fate",
                   "primary_end_x_mm", "primary_end_process", "n_sec_gamma", "n_sec_electron", "n_sec_positron",
                   "n_sec_other"]


def effective_spec(spec: dict) -> dict:
    """The spec layered_sim reads: output files named inside the run folder (its working directory)."""
    s = json.loads(json.dumps(spec))
    out = dict(s.get("output", {}))
    out.update(csv="events.csv", materials="materials.json", datapaths="datapaths.json")
    s["output"] = out
    return s


def tree_signature(root: Path) -> tuple[int, int, float]:
    n = size = 0
    latest = 0.0
    for p in root.rglob("*"):
        if p.is_file():
            st = p.stat()
            n, size, latest = n + 1, size + st.st_size, max(latest, st.st_mtime)
    return n, size, latest


def content_hash(root: Path, cache_file: Path) -> str | None:
    """The geant4_build.py content hash of a dataset directory, cached by (file count, bytes, newest mtime)."""
    if not root.is_dir():
        return None
    from geant4_build import tree_hash  # sibling script, same hashing as the build record
    sig = list(tree_signature(root))
    cache = {}
    if cache_file.is_file():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}
    hit = cache.get(str(root))
    if hit and hit["signature"] == sig:
        return hit["sha256"]
    digest = tree_hash(root)[0]
    cache[str(root)] = {"signature": sig, "sha256": digest}
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return digest


def compare_datapaths(datapaths: dict, build: dict, cache_file: Path) -> tuple[list[dict], list[str]]:
    resolved = datapaths.get("after_run", {})
    rows, problems = [], []
    for d in build["extension"]["build"]["datasets"]:
        got = resolved.get(d["envvar"])
        same_path = got is not None and Path(got).resolve() == expand(d["path"]).resolve()
        digest = content_hash(Path(got), cache_file) if got else None
        row = {"name": d["name"], "version": d["version"], "envvar": d["envvar"], "path_recorded": d["path"],
               "path_resolved": tilde(got) if got else None, "content_sha256": digest,
               "path_match": same_path, "content_match": digest == d.get("content_sha256")}
        rows.append(row)
        if not same_path:
            problems.append(f"{d['envvar']} resolved to {row['path_resolved']}, recorded {d['path']}")
        elif not row["content_match"]:
            problems.append(f"{d['name']} at {d['path']}: content hash differs from the build record")
    extra = sorted(set(resolved) - {d["envvar"] for d in build["extension"]["build"]["datasets"]})
    for var in extra:
        problems.append(f"{var} resolved to {tilde(resolved[var])}, which the build record does not list")
    return rows, problems


def _load_build(path) -> dict:
    rec = json.loads(expand(str(path)).read_text(encoding="utf-8"))
    why = build_record_ok(rec)
    if why:
        raise SpecError(f"--build-record: {why}")
    return rec


def event_file_block(run_dir: Path, run_id: str, level: str, simroot: Path | None, problems: list) -> dict | None:
    """B1.4: what the run record keeps of element_sim's events.root (never committed): its path, file sha256 (the
    bytes include the write time), simroot's content_sha256 and the rows and hash of each ntuple, the file size."""
    if level == "none":
        return None
    f = run_dir / "events.root"
    if not f.is_file():
        problems.append(f"output.event_file.level is {level} but element_sim wrote no events.root")
        return None
    block = {"path": tilde(f), "ref": f"{run_id}/events.root", "sha256": sha256_file(f), "size_bytes": f.stat().st_size,
             "level": level, "event_file_version": "element_sim.events/1", "committed": False}
    if simroot is None or not simroot.is_file():
        problems.append("simroot not found: the event file's content_sha256 cannot be computed (--simroot)")
        return block
    p = subprocess.run([str(simroot), "hash", str(f)], capture_output=True, text=True, timeout=3600)
    try:
        doc = json.loads(p.stdout)
    except ValueError:
        doc = {}
    if p.returncode != 0 or doc.get("status") != "ok":
        problems.append(f"simroot hash failed on events.root (exit {p.returncode}): {doc.get('error')}")
        return block
    block.update(content_sha256=doc["content_sha256"], ntuples=doc["ntuples"],
                 simroot={"path": tilde(simroot), "sha256": sha256_file(simroot)})
    return block


def run_one(spec: dict, exe: Path, build: dict, build_path: Path, work: Path, run_id: str, timeout: float,
            overrides: dict[str, str], simroot: Path | None = None) -> tuple[str, dict, dict]:
    """Run layered_sim or element_sim (by the spec's schema); returns (status, summary, record). An element_sim run
    that is killed or exceeds the timeout is incomplete: its event file is not closed."""
    program = program_of(spec)
    element = program == "element_sim"
    run_dir = work / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    eff = json.loads(json.dumps(spec)) if element else effective_spec(spec)  # element_sim names its own outputs
    (run_dir / "spec.json").write_text(json.dumps(eff, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    env = data_env(build)
    env.update(overrides)
    sources = program_sources(program)
    if element:
        env["ELEMENT_SIM_SOURCES_SHA256"] = sha256_json(sources)
    log = run_dir / "log.txt"
    interrupted = None
    with log.open("w", encoding="utf-8") as fh:
        try:
            p = subprocess.run([str(exe), str(run_dir / "spec.json")], cwd=run_dir, stdout=fh, stderr=subprocess.STDOUT,
                               env=env, timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            if not element:
                raise
            code, interrupted = -1, f"element_sim exceeded the timeout of {timeout} s"
    if element and code in (-signal.SIGKILL, -signal.SIGTERM, -signal.SIGINT) and not interrupted:
        interrupted = f"element_sim was stopped (signal {-code})"  # a crash (SIGABRT, SIGSEGV) is a failed run
    if interrupted:
        return "incomplete", {"error": interrupted + ": the run and its event file are incomplete",
                              "run_dir": tilde(run_dir)}, {}
    text = log.read_text(encoding="utf-8", errors="replace")
    tag = "ELEMENT_SIM_STATUS " if element else "LAYERED_SIM_STATUS "
    status_line = next((ln for ln in reversed(text.splitlines()) if ln.startswith(tag)), None)
    sim_status = json.loads(status_line.split(" ", 1)[1]) if status_line else {"status": "failed",
                                                                                "error": f"no status line (exit {code})"}
    if code == 2 or sim_status.get("status") == "rejected":
        return "rejected", {"error": sim_status.get("error"), "log": tilde(log)}, {}
    problems = [] if code == 0 and sim_status.get("status") == "ok" else [
        f"{program} exit {code}: {sim_status.get('error')}"]
    datapaths = json.loads((run_dir / "datapaths.json").read_text(encoding="utf-8")) \
        if (run_dir / "datapaths.json").is_file() else {}
    rows, dp_problems = compare_datapaths(datapaths, build, work / ".dataset-hash-cache.json") if datapaths else ([], [])
    problems += dp_problems
    overlaps = text.count("GeomVol1002")
    outputs = {}
    for name in ("spec.json", "events.csv", "materials.json", "datapaths.json", "log.txt") + A2_OUTPUTS:
        if (run_dir / name).is_file():
            outputs[f"{run_id}/{name}"] = sha256_file(run_dir / name)
    if "events.csv" not in " ".join(outputs) and not problems:
        problems.append(f"{program} wrote no events.csv")
    b = build["extension"]["build"]
    run = spec["run"]
    a2 = boundary_artifacts(spec, run_dir, work, build_path, sources, problems)
    if a2.get("inconsistent"):
        return "rejected", {"error": a2["inconsistent"], "run_dir": tilde(run_dir)}, {}
    sim = {
        "geant4": {"version": datapaths.get("geant4_version"), "tag": b["tag"], "commit": b["commit"],
                   "build_record_sha256": sha256_file(build_path)},
        "program": {"name": program, "path": tilde(exe), "sha256": sha256_file(exe), "adapter": ADAPTER_VERSION,
                    "sources_sha256": sources},
        "datasets": rows, "data_path_problems": dp_problems,
        "physics": spec["physics"], "ui_commands": spec.get("ui_commands", []),
        "cuts": {"default_mm": spec["physics"]["default_cut_mm"], "regions": spec["physics"].get("regions", [])},
        "materials": spec.get("materials", []),
        "spec_sha256": sha256_json(spec),
        "material_dump_sha256": outputs.get(f"{run_id}/materials.json"),
        "random": {"engine": "MixMaxRng", "seeds": run["seeds"]},
        "events": run["events"], "first_event": run.get("first_event", 0), "chunk": run.get("chunk", 0),
        "run_manager": run.get("run_manager", "serial"), "threads": run.get("threads", 1),
        "overlap_reports": overlaps,
        "data_overrides": {k: tilde(v) for k, v in overrides.items()},
        "seeding": run.get("seeding", "stream"),
        **{k: v for k, v in a2.items() if k != "inconsistent"},
    }
    if element:  # the bytes element_sim read and hashed into the event file's run row
        sim["spec_sha256"] = sha256_file(run_dir / "spec.json")
        sim.update(source=spec["source"], world=spec["world"], elements=spec["elements"],
                   field=spec.get("field"), logical_run_seed=run["logical_run_seed"],
                   step_limits={"field_max_step_mm": (spec.get("field") or {}).get("max_step_mm", 10.0)}
                   if spec.get("field") else {})
        if spec.get("provenance"):
            sim["spec_provenance"] = spec["provenance"]
        level = ((spec.get("output") or {}).get("event_file") or {}).get("level", "none")
        ef = event_file_block(run_dir, run_id, level, simroot or exe.parent / "simroot", problems)
        if ef:
            sim["event_file"] = ef
    else:
        sim.update(gun=spec["gun"], geometry=spec["geometry"],
                   step_limits={k: spec["physics"][k] for k in ("step_limit_mm", "min_ekin_MeV") if k in spec["physics"]})
    ok = not problems
    return ("ok" if ok else "failed"), {"run_dir": tilde(run_dir), "problems": problems, "outputs": outputs}, \
        {"simulation": sim, "outputs": outputs, "exit": code, "ok": ok}


def build_effective_config(probe: dict, spec: dict, build_path: Path, sources: dict) -> dict:
    """The effective config of a run (A2.4; schemas/effective_config.schema.json) from the program's probe.json:
    the probe's geometry with its tree-v1 hashes (contracts.validate.geant4_tree_v1), its other sections, the seeding,
    the backend and the build record it ran against; config_sha256 over everything else."""
    run = spec["run"]
    recorded = bool(probe.get("recorded"))
    tree = probe.get("geometry") if recorded else None
    hashes = geant4_tree_v1({"geometry": {"tree": tree}}, None) if tree else {}
    sections = {k: v for k, v in probe.items() if k not in ("geometry", "probe_version", "engine", "engine_version",
                                                            "recorded")}
    ec = {"engine": "geant4", "engine_version": probe.get("engine_version", ""),
          "probe_version": probe.get("probe_version", ""),
          "backend": {"name": program_of(spec), "version": ADAPTER_VERSION, "sources_sha256": sha256_json(sources)},
          "source": "probe" if recorded else "declared", "recorded": recorded,
          "seeding": {"mode": run.get("seeding", "stream"), "logical_run_seed": run.get("logical_run_seed")},
          "geometry": {"tree": tree, "tree_sha256": hashes.get("tree_sha256"),
                       "naming_sha256": hashes.get("naming_sha256"), "hash_scheme": "tree-v1", "gdml_sha256": None,
                       **({"canonical_ties": hashes["canonical_ties"]} if hashes else {})},
          "environment_ref": sha256_file(build_path), "sections": {"geant4": sections}}
    ec["config_sha256"] = hashlib.sha256(json.dumps(ec, sort_keys=True, separators=(",", ":"))
                                         .encode("utf-8")).hexdigest()  # sorted keys, no whitespace (the schema)
    return ec


def store_effective_config(ec: dict, work: Path) -> Path:
    """effective_configs/<config_sha256>.json under the work folder, written once per content hash; an existing file
    with other content under that name is an error."""
    path = work / "effective_configs" / f"{ec['config_sha256']}.json"
    body = json.dumps(ec, indent=1, sort_keys=True) + "\n"
    if path.is_file():
        if json.loads(path.read_text(encoding="utf-8")) != ec:
            raise SpecError(f"{tilde(path)} exists with other content")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def consistency(spec: dict, ec: dict) -> str | None:
    """A2.6: the configuration decision (isolated or embedded) via spec-v1 (from spec/1) and via tree-v1 (from the
    effective config) must agree for every slab alone and for all slabs together; None, or what disagrees."""
    if not ec.get("recorded") or program_of(spec) != "layered_sim":  # spec-v1 describes layered_sim geometry only
        return None
    names = []
    for layer in spec["geometry"]["layers"]:
        names += [s["name"] for s in layer["slabs"] if s["name"] not in names]
    sim = {"geometry": spec["geometry"], "materials": spec.get("materials", [])}
    for target in [[n] for n in names] + ([names] if len(names) > 1 else []):
        a, b = geant4_spec_v1(sim, target), geant4_tree_v1(ec, target)
        if a["configuration"] != b["configuration"]:
            return (f"target {target}: spec-v1 gives {a['configuration']}, tree-v1 gives {b['configuration']}; "
                    "the effective config and spec/1 disagree")
    return None


def boundary_artifacts(spec: dict, run_dir: Path, work: Path, build_path: Path, sources: dict,
                       problems: list) -> dict:
    """A2.3-A2.5: the summary, column map and effective config of a finished run, checked and hashed for the run
    record's extension.simulation; problems (a file that does not validate, a probe that changed the random state)
    are appended to `problems`; {"inconsistent": why} when spec-v1 and tree-v1 disagree (the caller rejects)."""
    out: dict = {}
    summary = run_dir / "summary.json"
    if (spec.get("output") or {}).get("observables"):
        if not summary.is_file():
            problems.append(f"output.observables is declared but {program_of(spec)} wrote no summary.json")
        else:
            rep = validate(json.loads(summary.read_text(encoding="utf-8")), "simulation_summary.json")
            if not rep.ok:
                problems.append("summary.json does not validate: " + "; ".join(f.message for f in rep.errors)[:300])
            out["summary"] = {"ref": f"{run_dir.name}/summary.json", "sha256": sha256_file(summary)}
    cmap = run_dir / "column_map.json"
    if cmap.is_file():
        rep = validate(json.loads(cmap.read_text(encoding="utf-8")), str(SCHEMAS / "column_map.schema.json"))
        if not rep.ok:
            problems.append("column_map.json does not validate: " + "; ".join(f.message for f in rep.errors)[:300])
        out["column_map"] = {"ref": f"{run_dir.name}/column_map.json", "sha256": sha256_file(cmap)}
    probe_path = run_dir / "probe.json"
    if not probe_path.is_file():
        problems.append(f"{program_of(spec)} wrote no probe.json")
        return out
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("random_state_unchanged") is not True:
        problems.append("the probe changed the random-engine state")
    ec = build_effective_config(probe, spec, build_path, sources)
    rep = validate(ec, str(SCHEMAS / "effective_config.schema.json"))
    if not rep.ok:
        problems.append("the effective config does not validate: " + "; ".join(f.message for f in rep.errors)[:300])
    why = consistency(spec, ec)
    if why:
        return {"inconsistent": why}
    stored = store_effective_config(ec, work)
    out["effective_config"] = {"config_sha256": ec["config_sha256"], "ref": str(stored.relative_to(work)),
                               "recorded": ec["recorded"], "source": ec["source"], "geometry": ec["geometry"]}
    return out


def complete_summary(run_dir: Path, run_id: str, sim: dict, outputs: dict) -> None:
    """The run fields of layered_sim's summary.json that only the run record knows (A2.3): run_id, evidence role,
    logical-run seed and scheme, spec hash, settings, data-path problems, dataset content match and the run record's
    id, as summary_from_csv.py writes them, so that hep-detector's study check reads this summary like any other.
    The producer stays layered_sim; the summary's hash in the record and outputs is the completed file's."""
    if "summary" not in sim:
        return
    path = run_dir / "summary.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    run = doc["run"]
    run.update({k: v for k, v in {
        "run_id": f"geant4-run-{run_id}", "evidence_role": sim.get("evidence_role"),
        "logical_run_seed": sim.get("logical_run_seed", run.get("logical_run_seed")),
        "seed_scheme": sim.get("seed_scheme"), "spec_sha256": sim.get("spec_sha256"), "settings": run_settings(sim),
        "data_path_problems": sim.get("data_path_problems", []),
        "datasets_content_match": all(d.get("content_match") for d in sim.get("datasets", [])),
        "run_record": {"artifact_id": f"geant4-run-{run_id}"}}.items() if v is not None})
    run["completed_by"] = {"name": "geant4_run.py", "adapter": ADAPTER_VERSION}
    write_json(path, doc)
    digest = sha256_file(path)
    sim["summary"]["sha256"] = digest
    outputs[f"{run_id}/summary.json"] = digest


def write_run_record(path: Path, run_id: str, spec_path: Path, spec: dict, exe: Path, result: dict, work: Path,
                     created: str, argv: list[str] | None = None) -> dict:
    """The computational-run record of one layered_sim or element_sim run; from adapter 0.2.0 also argv (the
    command actually run, interpreter first), script_sha256 (this script, keyed as it appears in argv) and
    versions.plugin_release (contracts/identity.py), as run_workflow.py writes them."""
    sim = result["simulation"]
    if isinstance((spec.get("output") or {}).get("blocks"), dict):  # 0.5.0: K and B, for the seed_group rule (C2.1)
        sim["blocks"] = {k: spec["output"]["blocks"][k] for k in ("blocks", "block_size")}
    complete_summary(work / run_id, run_id, sim, result["outputs"])
    program = sim["program"]["name"]
    src = spec.get("gun") or spec.get("source") or {}
    energy = f"{src['energy_MeV']} MeV" if "energy_MeV" in src else (
        f"{src['ekin_per_nucleon_MeV']} MeV/nucleon" if "ekin_per_nucleon_MeV" in src else
        f"{len(src.get('cycle', []))} cycled energies")
    rec = record_skeleton(f"geant4-run-{run_id}",
                          f"Geant4 {program} run {run_id}: {src.get('particle')} {energy}, "
                          f"{sim['events']} events (a completed run, not a validated result)", created,
                          ["unvalidated"] if result["ok"] else ["unvalidated", "failed"])
    rec["extension"] = {
        "input_manifest": [{"path": tilde(spec_path), "sha256": sha256_file(spec_path)}],
        "tools": [{"name": "Geant4", "version": f"{sim['geant4']['tag']} ({sim['geant4']['commit']})"},
                  {"name": program, "version": sim["program"]["sha256"][:16]}],
        "commands": [f"{tilde(exe)} {run_id}/spec.json"],
        "environment": {"work": tilde(work), "dataset_variables": "all unset except the build record's",
                        "G4FORCE_RUN_MANAGER_TYPE": "unset"},
        "seeds": {program: sim["random"]["seeds"]}, "tolerances": {},
        "exit_status": 0 if result["ok"] else 1, "output_hashes": result["outputs"], "simulation": sim}
    if argv:
        rec["extension"]["argv"] = list(argv)
        rec["extension"]["script_sha256"] = {a: sha256_file(Path(a)) for a in argv if a.endswith(".py") and Path(a).is_file()}
    rec["versions"]["plugin_release"] = plugin_release()
    write_json(path, rec)
    return rec


def _evidence_fields(sim: dict, args) -> None:
    """A1.4: what the run is for in a study (extension.simulation.evidence_role, point_id) and its seed scheme
    (hash-v1 with the logical-run seed S, or legacy)."""
    for key in ("evidence_role", "point_id", "logical_run_seed", "seed_group"):
        if getattr(args, key, None) is not None:
            sim[key] = getattr(args, key)
    if getattr(args, "logical_run_seed", None) is not None or sim.get("program", {}).get("name") == "element_sim":
        sim["seed_scheme"] = "hash-v1"  # element_sim: always per-event with the spec's logical-run seed
    elif getattr(args, "evidence_role", None) is not None:
        sim["seed_scheme"] = "legacy"


def cmd_build_sim(args) -> tuple[str, dict]:
    program = args.program
    if not shutil.which("cmake"):
        return "missing-dependency", {"error": "cmake not found on PATH"}
    g4opt = []
    if program != "simreco":  # simreco links no Geant4 (B2.1)
        if not args.build_record:
            raise SpecError(f"--build-record is required to build {program}")
        build = _load_build(args.build_record)
        g4dir = install_prefix(build) / "lib" / "cmake" / "Geant4"
        if not g4dir.is_dir():
            return "missing-dependency", {"error": f"no Geant4 CMake configuration at {tilde(g4dir)}"}
        g4opt = [f"-DGeant4_DIR={g4dir}"]
    bld = expand(str(args.work)) / f"{program}-build"
    log = bld / "build.log"
    bld.mkdir(parents=True, exist_ok=True)
    codes = []
    with log.open("w", encoding="utf-8") as fh:
        for cmd in (["cmake", "-S", str(ASSETS / program), "-B", str(bld), *g4opt,
                     "-DCMAKE_BUILD_TYPE=Release"], ["cmake", "--build", str(bld), "--parallel", str(args.jobs)]):
            codes.append(subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode)
            if codes[-1]:
                break
    exe = bld / program
    built = [exe] + ([bld / "simroot"] if program == "element_sim" else [])
    if any(codes) or not all(f.is_file() for f in built):
        return "failed", {"error": f"{program} did not build", "log": tilde(log), "exit_codes": codes}
    out = {"exe": tilde(exe), "sha256": sha256_file(exe), "sources_sha256": program_sources(program)}
    if program == "element_sim":
        out["simroot"] = {"path": tilde(bld / "simroot"), "sha256": sha256_file(bld / "simroot")}
    return "ok", out


def _exe(path: str) -> Path:
    exe = expand(path)
    if not exe.is_file():
        raise FileNotFoundError(f"executable {tilde(exe)} not found (build it with build-sim)")
    return exe


def _overrides(items) -> dict[str, str]:
    out = {}
    for item in items or []:
        var, _, val = item.partition("=")
        if var not in DATA_VARS or not val:
            raise SpecError(f"--data-override takes VAR=PATH with VAR one of {DATA_VARS}")
        out[var] = str(expand(val))
    return out


def cmd_run(args) -> tuple[str, dict]:
    spec_path = expand(str(args.spec))
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    program = validate_any(spec)
    build_path = expand(str(args.build_record))
    build = _load_build(build_path)
    try:
        exe = _exe(args.exe)
    except FileNotFoundError as exc:
        return "missing-dependency", {"error": str(exc)}
    work = expand(str(args.work)).resolve()
    if program == "element_sim" and args.logical_run_seed is not None \
            and args.logical_run_seed != spec["run"]["logical_run_seed"]:
        raise SpecError(f"--logical-run-seed {args.logical_run_seed} is not the spec's run.logical_run_seed "
                        f"{spec['run']['logical_run_seed']}")
    if getattr(args, "seed_group", None) is not None and args.logical_run_seed is None:
        raise SpecError("--seed-group needs --logical-run-seed (the S its runs share)")
    if args.logical_run_seed is not None:  # A1.4: a single job of logical run S has the seed pair (H(S,0,0), H(S,0,1))
        first = int(spec["run"].get("first_event", 0))
        want = list(job_seeds(args.logical_run_seed, first))
        if list(spec["run"].get("seeds") or []) != want:
            raise SpecError(f"run.seeds {spec['run'].get('seeds')} are not the job seeds {want} of logical run seed "
                            f"{args.logical_run_seed} starting at event {first} (core/simulation/seeds.py)")
    simroot = expand(args.simroot) if args.simroot else None
    status, summary, result = run_one(spec, exe, build, build_path, work, args.run_id, args.timeout,
                                      _overrides(args.data_override), simroot)
    if status in ("rejected", "incomplete"):  # no record of a refused or interrupted run
        return status, summary
    _evidence_fields(result["simulation"], args)
    created = args.created or datetime.date.today().isoformat()
    record_path = expand(str(args.record))
    write_run_record(record_path, args.run_id, spec_path, spec, exe, result, work, created, args.argv_run)
    summary["record"] = tilde(record_path)
    return status, summary


def cmd_check_spec(args) -> tuple[str, dict]:
    """B1.6: an element_sim.spec/1 against the schema and the cross-field rules; no Geant4 needed."""
    path = expand(str(args.spec))
    spec = json.loads(path.read_text(encoding="utf-8"))
    problems = ES.check_spec(spec)
    return ("ok" if not problems else "rejected"), {"ok": not problems, "problems": problems,
                                                    "spec": {"path": tilde(path), "sha256": sha256_file(path)}}


def cmd_from_geometry(args) -> tuple[str, dict]:
    """B1.8: the element_sim.spec/1 of a design-geometry/1 file and a realization profile (deterministic)."""
    gpath, ppath = expand(str(args.geometry)), expand(str(args.profile))
    geometry = json.loads(gpath.read_text(encoding="utf-8"))
    profile = json.loads(ppath.read_text(encoding="utf-8"))
    spec = ES.from_geometry(geometry, ES.file_ref(gpath), profile, ES.file_ref(ppath))
    out = expand(str(args.out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ES.canonical(spec), encoding="utf-8")
    return "ok", {"spec": tilde(out), "sha256": sha256_file(out), "elements": len(spec["elements"]),
                  "provenance": spec["provenance"],
                  "note": "derived from the candidate's geometry file; never edit it by hand (regenerate instead)"}


def _set(doc: dict, dotted: str, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        doc = doc.setdefault(k, {})
    doc[keys[-1]] = value


def cmd_scan(args) -> tuple[str, dict]:
    base = json.loads(expand(str(args.base)).read_text(encoding="utf-8"))
    validate_any(base)
    grid = json.loads(expand(str(args.grid)).read_text(encoding="utf-8"))
    params = grid.get("parameters")
    if not isinstance(params, dict) or not params or not all(isinstance(v, list) and v for v in params.values()):
        raise SpecError("the grid needs 'parameters': {dotted.spec.key: [values, ...]}")
    if args.events_per_second <= 0:
        raise SpecError("--events-per-second must be positive (measure it with a trial run)")
    out = expand(str(args.out_dir))
    (out / "specs").mkdir(parents=True, exist_ok=True)
    names = sorted(params)
    steps, refused = [], []
    for k, combo in enumerate(itertools.product(*(params[n] for n in names))):
        spec = json.loads(json.dumps(base))
        for n, v in zip(names, combo):
            _set(spec, n, v)
        if "run.seeds" not in params:  # independent samples per point: the convergence gate's SE assumes them
            spec["run"]["seeds"] = [spec["run"]["seeds"][0], spec["run"]["seeds"][1] + k]
        sid = f"{grid.get('name', 'scan')}-{k:03d}"
        per_event = base["run"].get("seeding") == "per-event" or (args.seeding == "per-event"
                                                                  and "seeding" not in base["run"])
        if per_event and "run.logical_run_seed" not in params:  # A2.2: every point its own S, also when the base
            spec["run"].update(seeding="per-event",  # declares per-event; S = H(study_id, role, point_id)
                               logical_run_seed=logical_run_seed(args.study_id or grid.get("name", "scan"),
                                                                 args.role, sid))
        evidence = []
        if spec["run"].get("seeding") == "per-event" and "logical_run_seed" in spec["run"]:
            # the run record carries the point's S, role and id (seed_scheme hash-v1), and run.seeds are its job seeds
            s_point = spec["run"]["logical_run_seed"]
            spec["run"]["seeds"] = list(job_seeds(s_point, spec["run"].get("first_event", 0)))
            evidence = ["--evidence-role", args.role, "--point-id", sid, "--logical-run-seed", str(s_point)]
        validate_any(spec)
        est = spec["run"]["events"] / args.events_per_second
        if est > STEP_LIMIT_S:
            refused.append({"id": sid, "estimated_s": est})
            continue
        (out / "specs" / f"{sid}.json").write_text(json.dumps(spec, indent=1, sort_keys=True) + "\n",
                                                  encoding="utf-8")
        steps.append({"id": sid, "needs": [], "inputs": [f"specs/{sid}.json"],
                      "outputs": [f"records/{sid}.computational-run.json"],
                      "parameters": dict(zip(names, combo)), "estimated_s": round(est, 1),
                      "argv": ["{python}", "{plugin}/adapters/geant4/assets/geant4_run.py", "run", "--spec",
                               f"specs/{sid}.json", "--exe", tilde(expand(args.exe)), "--build-record",
                               tilde(expand(str(args.build_record))), "--work", "runs", "--run-id", sid, "--record",
                               f"records/{sid}.computational-run.json", "--created", args.created or
                               datetime.date.today().isoformat(), "--timeout", str(STEP_LIMIT_S - 60), *evidence]})
    if refused:
        return "rejected", {"error": f"{len(refused)} step(s) would exceed {STEP_LIMIT_S} s: partition them with "
                                     "local_partition.py and the chunk subcommand", "refused": refused}
    wf = {"workflow": grid.get("name", "scan"),
          "note": "Geant4 scan written by adapters/geant4/assets/geant4_run.py scan; run with "
                  "skills/hep-computing/scripts/run_workflow.py --work <this folder>", "steps": steps}
    write_json(out / "workflow.json", wf)
    return "ok", {"workflow": tilde(out / "workflow.json"), "steps": len(steps)}


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "# SIMULATION":
        raise SpecError(f"{tilde(path)} is not a layered_sim CSV (first line must be '# SIMULATION')")
    cols = lines[1].split(",")
    return cols, [ln.split(",") for ln in lines[2:] if ln]


SUMMED = ("edep_", "chlen_", "plen_", "leak_", "killed_", "exit_ekin_MeV", "primary_eloss_MeV", "escape_world_MeV")


def cmd_chunk(args) -> tuple[str, dict]:
    spec = json.loads(expand(str(args.spec)).read_text(encoding="utf-8"))
    program = validate_any(spec)
    if program == "element_sim" and args.logical_run_seed != spec["run"]["logical_run_seed"]:
        raise SpecError("an element_sim chunk needs --logical-run-seed equal to the spec's run.logical_run_seed")
    if not 0 <= args.start < args.stop:
        raise SpecError("--start/--stop must give a non-empty range")
    build_path = expand(str(args.build_record))
    build = _load_build(build_path)
    try:
        exe = _exe(args.exe)
    except FileNotFoundError as exc:
        return "missing-dependency", {"error": str(exc)}
    chunk_no = int(args.id.lstrip("c")) if args.id.lstrip("c").isdigit() else 0
    seeds = list(job_seeds(args.logical_run_seed, args.start)) if args.logical_run_seed is not None else \
        [max(1, args.seed), args.start + 1]  # A1.4: the job starting at event e has (H(S, e, 0), H(S, e, 1))
    spec["run"].update(events=args.stop - args.start, first_event=args.start, chunk=chunk_no, seeds=seeds)
    if program == "element_sim":
        ES.validate_spec(spec)
    work = expand(str(args.work)).resolve()
    status, summary, result = run_one(spec, exe, build, build_path, work, args.id, args.timeout, {})
    if status != "ok":
        return status, summary
    created = args.created or datetime.date.today().isoformat()
    rec_path = work / "records" / f"{args.id}.computational-run.json"
    write_run_record(rec_path, args.id, expand(str(args.spec)), spec, exe, result, work, created, args.argv_run)
    cols, rows = read_csv(work / args.id / "events.csv")
    sums = {"n_events": len(rows)}
    for i, c in enumerate(cols):
        if c.startswith(SUMMED):
            vals = [float(r[i]) for r in rows]
            sums[f"sum_{c}"] = math.fsum(vals)
            sums[f"sumsq_{c}"] = math.fsum(v * v for v in vals)
    sums["csv"] = [{"path": f"{args.id}/events.csv", "sha256": sha256_file(work / args.id / "events.csv")}]
    if (work / args.id / "summary.json").is_file():  # adapter 0.2.0: merge with --rule summaries=concat
        sums["summaries"] = [{"path": f"{args.id}/summary.json", "sha256": sha256_file(work / args.id / "summary.json")}]
    sums["records"] = [{"path": f"records/{args.id}.computational-run.json", "sha256": sha256_file(rec_path)}]
    write_json(expand(str(args.out)), sums)
    return "ok", {"chunk": args.id, "n_events": len(rows)}


def summarize_summaries(res: dict, work: Path) -> tuple[str, dict]:
    """A2.6: the chunks' run summaries (simulation-summary/1) merged block by block (core/simulation/summary.py) and
    each declared observable estimated from the merged summary (core/simulation/estimates.py, mean unless the
    summary was declared otherwise); no CSV is read. Every summary must match its merged hash."""
    docs, problems = [], []
    for c in res["summaries"]:
        f = work / c["path"]
        if not f.is_file() or sha256_file(f) != c["sha256"]:
            problems.append(f"{c['path']}: missing or changed since the merge")
            continue
        docs.append(json.loads(f.read_text(encoding="utf-8")))
    if not docs:
        return "failed", {"source": "summaries", "problems": problems or ["no summary to merge"]}
    try:
        merged = SUMMARY.merge(docs)
    except (ValueError, IndexError, KeyError) as exc:
        return "rejected", {"source": "summaries", "error": f"the chunk summaries do not merge: {exc}"}
    out = {}
    for o in merged["observables"]:
        try:
            r = ESTIMATES.estimate(merged, {"name": o["name"], "estimator": "mean"})
            out[o["name"]] = {"mean": r["value"], "se": r["se"], "dof": r["dof"], "n": r["n"]}
        except ValueError as exc:  # SummaryError, BatchMeansError (fewer than 2 usable blocks)
            out[o["name"]] = {"error": str(exc)}
    run = merged["run"]
    if run["events_in_blocks"] + run["events_ignored"] != res.get("n_events", run["events_in_blocks"]
                                                                  + run["events_ignored"]):
        problems.append(f"the summaries hold {run['events_in_blocks'] + run['events_ignored']} events, "
                        f"the merge {res.get('n_events')}")
    return ("ok" if not problems else "failed"), {
        "source": "summaries", "summaries": len(docs), "events_in_blocks": run["events_in_blocks"],
        "events_ignored": run["events_ignored"], "observables": out, "problems": problems}


def cmd_summarize(args) -> tuple[str, dict]:
    merged = json.loads(expand(str(args.merged)).read_text(encoding="utf-8"))
    res = merged.get("merged", merged)
    if res.get("summaries"):
        if not args.work:
            raise SpecError("--work (the chunk work folder) is needed to read the chunks' summaries")
        return summarize_summaries(res, expand(str(args.work)))
    n = res.get("n_events")
    if not isinstance(n, (int, float)) or n < 2:
        raise SpecError("the merged result needs n_events >= 2")
    out = {}
    for k, s in res.items():
        if k.startswith("sum_") and f"sumsq_{k[4:]}" in res:
            q = k[4:]
            mean = s / n
            var = max(res[f"sumsq_{q}"] / n - mean * mean, 0.0) * n / (n - 1)
            out[q] = {"mean": mean, "sd": math.sqrt(var), "se": math.sqrt(var / n)}
    doc = {"n_events": n, "quantities": out, "csv_files": len(res.get("csv", []))}
    problems = []
    if args.work:  # the chunk CSVs: hashes as merged, and no event number twice
        work, seen, dup = expand(str(args.work)), set(), 0
        for c in res.get("csv", []):
            f = work / c["path"]
            if not f.is_file() or sha256_file(f) != c["sha256"]:
                problems.append(f"{c['path']}: missing or changed since the merge")
                continue
            for row in read_csv(f)[1]:
                dup += row[0] in seen
                seen.add(row[0])
        doc.update(events_in_csv=len(seen), duplicate_events=dup)
        if dup or len(seen) != n:
            problems.append(f"{dup} duplicate event number(s); {len(seen)} events in the CSVs, {n} merged")
    if args.single_record:  # agreement with one unpartitioned run (other seeds): |z| <= --z-max per quantity
        single = json.loads(expand(str(args.single_record)).read_text(encoding="utf-8"))
        run_dir = expand(single["extension"]["environment"]["work"]) / single["artifact_id"].removeprefix("geant4-run-")
        cols, rows = read_csv(run_dir / "events.csv")
        table = []
        for q, m in out.items():
            vals = [float(r[cols.index(q)]) for r in rows]
            mean = math.fsum(vals) / len(vals)
            se = math.sqrt(max(math.fsum((v - mean) ** 2 for v in vals) / (len(vals) - 1), 0) / len(vals))
            se_tot = math.hypot(se, m["se"])
            z = (m["mean"] - mean) / se_tot if se_tot > 0 else (0.0 if m["mean"] == mean else math.inf)
            table.append({"quantity": q, "partitioned": m["mean"], "single": mean, "z": z,
                          "verdict": "pass" if abs(z) <= args.z_max else "fail"})
        doc.update(single_run=tilde(run_dir), z_max=args.z_max, comparison=table)
        problems += [f"{t['quantity']}: |z| = {abs(t['z']):.2f} > {args.z_max}" for t in table if t["verdict"] == "fail"]
    doc["problems"] = problems
    return ("ok" if not problems else "failed"), doc


def cmd_reduce(args) -> tuple[str, dict]:
    src = expand(str(args.csv))
    cols, rows = read_csv(src)
    keep = args.columns
    missing = [c for c in keep if c not in cols]
    if missing:
        raise SpecError(f"columns {missing} not in {tilde(src)}")
    idx = [cols.index(c) for c in keep]
    body = "# SIMULATION\n" + ",".join(keep) + "\n" + "".join(",".join(r[i] for i in idx) + "\n" for r in rows)
    out = expand(str(args.out))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(gzip.compress(body.encode(), compresslevel=9, mtime=0))  # mtime 0: byte-identical reruns
    return "ok", {"out": tilde(out), "sha256": sha256_file(out), "rows": len(rows), "columns": keep,
                  "source": {"csv": tilde(src), "sha256": sha256_file(src)}}


def _run_dir(rec: dict, work_arg) -> Path:
    work = expand(str(work_arg)) if work_arg else expand(rec["extension"]["environment"]["work"])
    return work / rec["artifact_id"].removeprefix("geant4-run-")


def cmd_reco(args) -> tuple[str, dict]:
    """B2.4: simroot dump of an element_sim run's crossings, then simreco once per reconstruction replica; one
    computational-run record (extension.reconstruction) with the input run record and event-file hashes."""
    rec_path = expand(str(args.run_record))
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    sim = (rec.get("extension") or {}).get("simulation") or {}
    if (sim.get("program") or {}).get("name") != "element_sim":
        raise SpecError("--run-record is not an element_sim run record")
    ef = sim.get("event_file") or {}
    if ef.get("level") not in ("crossings", "hits"):
        raise SpecError("the run has no event file at level crossings or hits (simreco reads the crossings)")
    run_dir = _run_dir(rec, args.work)
    spec = json.loads((run_dir / "spec.json").read_text(encoding="utf-8"))
    reco_path = expand(str(args.reco_spec))
    reco = json.loads(reco_path.read_text(encoding="utf-8"))
    problems = RS.check(reco, spec)
    if problems:
        raise SpecError("; ".join(problems)[:1500])
    exe = expand(args.simreco)
    if not exe.is_file():
        return "missing-dependency", {"error": f"simreco {tilde(exe)} not found (build-sim --program simreco)"}
    simroot = expand(args.simroot) if args.simroot else expand((ef.get("simroot") or {}).get("path", "simroot"))
    if not simroot.is_file():
        return "missing-dependency", {"error": f"simroot {tilde(simroot)} not found (--simroot)"}
    root = run_dir / "events.root"
    h = subprocess.run([str(simroot), "hash", str(root)], capture_output=True, text=True, timeout=3600)
    try:
        content = json.loads(h.stdout).get("content_sha256")
    except ValueError:
        content = None
    if content is None or content != ef.get("content_sha256"):
        raise SpecError(f"{tilde(root)} does not match the run record's content_sha256 (changed or missing)")
    bending, bending_source, tof_ps, tof_source = None, "reco spec", None, "reco spec"
    if args.geometry:
        gpath = expand(str(args.geometry))
        geo = json.loads(gpath.read_text(encoding="utf-8"))
        pr = (geo.get("fields") or {}).get("point_resolution_um")
        if not isinstance(pr, (int, float)) or isinstance(pr, bool):
            raise SpecError("the geometry file's point_resolution_um is not one number")
        bending, bending_source = float(pr), f"design geometry {tilde(gpath)}"
        tr = (geo.get("fields") or {}).get("tof_time_resolution_ps")  # mapping 1.1.0 (optional field)
        if tr is not None:
            if not isinstance(tr, (int, float)) or isinstance(tr, bool) or tr <= 0:
                raise SpecError("the geometry file's tof_time_resolution_ps is not one positive number")
            tof_ps, tof_source = float(tr), f"design geometry {tilde(gpath)}"
    work = expand(str(args.work_out)).resolve()
    out_dir = work / args.reco_id
    out_dir.mkdir(parents=True, exist_ok=True)
    cross = out_dir / "crossings.csv"  # a temporary dump: removed after the replicas (never kept, B2.1)
    with cross.open("w", encoding="utf-8") as fh:
        d = subprocess.run([str(simroot), "dump", str(root), "--ntuple", "crossings"], stdout=fh,
                           stderr=subprocess.PIPE, text=True, timeout=3600)
    if d.returncode != 0:
        raise SpecError(f"simroot dump failed: {d.stderr[-300:]}")
    dump_sha = sha256_file(cross)
    replicas = reco.get("replicas", 1)
    outputs, rows, tails = {}, [], RS.tails_on(reco)
    for m in range(replicas):
        csv, summ = out_dir / f"results_r{m:03d}.csv", out_dir / f"summary_r{m:03d}.json"
        eff = RS.effective(reco, spec, m, {"crossings": str(cross), "events": str(run_dir / "events.csv"),
                                           "out_csv": str(csv), "out_summary": str(summ)}, bending, tof_ps)
        effp = out_dir / f"effective_r{m:03d}.json"
        write_json(effp, eff)
        log = out_dir / f"log_r{m:03d}.txt"
        with log.open("w", encoding="utf-8") as fh:
            p = subprocess.run([str(exe), str(effp)], stdout=fh, stderr=subprocess.STDOUT, timeout=args.timeout)
        text = log.read_text(encoding="utf-8", errors="replace")
        line = next((ln for ln in reversed(text.splitlines()) if ln.startswith("SIMRECO_STATUS ")), None)
        st = json.loads(line.split(" ", 1)[1]) if line else {"status": "failed", "error": f"exit {p.returncode}"}
        if p.returncode == 2 or st.get("status") == "rejected":
            return "rejected", {"error": f"simreco replica {m}: {st.get('error')}", "log": tilde(log)}
        if p.returncode != 0 or st.get("status") != "ok":
            return "failed", {"error": f"simreco replica {m} exit {p.returncode}: {st.get('error')}", "log": tilde(log)}
        row = {"replica": m, "results": {"ref": f"{args.reco_id}/{csv.name}", "sha256": sha256_file(csv)},
               "effective_spec": {"ref": f"{args.reco_id}/{effp.name}", "sha256": sha256_file(effp)}}
        outputs[row["results"]["ref"]] = row["results"]["sha256"]
        if summ.is_file():  # the run fields the study layer reads, from the simulation run record (as complete_summary)
            sdoc = json.loads(summ.read_text(encoding="utf-8"))
            sdoc["run"].update({k: v for k, v in {
                "run_id": f"geant4-reco-{args.reco_id}-r{m:03d}", "evidence_role": sim.get("evidence_role"),
                "seed_scheme": sim.get("seed_scheme"), "spec_sha256": sim.get("spec_sha256"),
                "settings": run_settings(sim), "data_path_problems": sim.get("data_path_problems", []),
                "datasets_content_match": all(d.get("content_match") for d in sim.get("datasets", [])),
                "run_record": {"artifact_id": f"geant4-reco-{args.reco_id}"},
                "simulation_run_record": {"artifact_id": rec["artifact_id"]}}.items() if v is not None})
            sdoc["run"]["completed_by"] = {"name": "geant4_run.py reco", "adapter": ADAPTER_VERSION}
            write_json(summ, sdoc)
            row["summary"] = {"ref": f"{args.reco_id}/{summ.name}", "sha256": sha256_file(summ)}
            outputs[row["summary"]["ref"]] = row["summary"]["sha256"]
        rows.append(row)
    cross.unlink()
    sources = program_sources("simreco")
    created = args.created or datetime.date.today().isoformat()
    labels = list(dict.fromkeys(["unvalidated"] + [s for s in rec.get("status", []) if s in ("failed", "synthetic")]))
    record = record_skeleton(f"geant4-reco-{args.reco_id}",
                             f"simreco reconstruction {args.reco_id} of {rec['artifact_id']} ({replicas} replica(s); "
                             "a reconstructed simulation, not a validated result)", created, labels)
    base = expand(str(args.project_root)).resolve() if args.project_root else expand(str(args.record)).resolve().parent
    try:  # refs relative to the project root (contracts/dependencies.py resolves them there)
        ref = rec_path.resolve().relative_to(base).as_posix()
    except ValueError:
        ref = tilde(rec_path)
    record["inputs"] = [{"ref": ref, "artifact_type": "computational-run", "artifact_id": rec["artifact_id"],
                         "sha256": sha256_file(rec_path), "status": rec.get("status", [])}]
    manifest = [{"path": tilde(reco_path), "sha256": sha256_file(reco_path)},
                {"path": tilde(rec_path), "sha256": sha256_file(rec_path)}]
    if args.geometry:
        manifest.append({"path": tilde(expand(str(args.geometry))), "sha256": sha256_file(expand(str(args.geometry)))})
    record["extension"] = {
        "input_manifest": manifest,
        "tools": [{"name": "simreco", "version": sha256_file(exe)[:16]}, {"name": "simroot", "version": sha256_file(simroot)[:16]}],
        "commands": [f"simroot dump events.root --ntuple crossings | simreco (x{replicas})"],
        "environment": {"work": tilde(work)}, "seeds": {"simreco": spec["run"]["logical_run_seed"]},
        "tolerances": {}, "exit_status": 0, "output_hashes": outputs,
        "argv": list(args.argv_run),
        "script_sha256": {a: sha256_file(Path(a)) for a in args.argv_run if a.endswith(".py") and Path(a).is_file()},
        "reconstruction": {
            "program": {"name": "simreco", "path": tilde(exe), "sha256": sha256_file(exe), "adapter": ADAPTER_VERSION,
                        "sources_sha256": sources},
            "reco_spec": reco, "reco_spec_sha256": sha256_file(reco_path),
            "run_record": {"artifact_id": rec["artifact_id"], "sha256": sha256_file(rec_path)},
            "event_file_content_sha256": content, "dumped": {"ntuple": "crossings", "columns": "all",
                                                              "dump_sha256": dump_sha, "kept": False},
            "events_csv_sha256": sha256_file(run_dir / "events.csv"),
            "point_resolution_bending_um": bending if bending is not None else reco["point_resolution_um"]["bending"],
            "point_resolution_source": bending_source,
            "tof_sigma_t_ps": tof_ps if tof_ps is not None else (reco.get("tof") or {}).get("sigma_t_ps"),
            "tof_sigma_t_source": tof_source, "replicas": replicas, "tail_sources_simulated": tails,
            "logical_run_seed": spec["run"]["logical_run_seed"], "outputs": rows}}
    record["versions"]["plugin_release"] = plugin_release()
    write_json(expand(str(args.record)), record)
    return "ok", {"record": tilde(expand(str(args.record))), "replicas": replicas, "tail_sources_simulated": tails,
                  "outputs": rows}


def _reco_summaries(rec: dict, work_arg) -> list[dict]:
    rx = (rec.get("extension") or {}).get("reconstruction")
    if not rx:
        raise SpecError(f"{rec.get('artifact_id')} is not a reco record (no extension.reconstruction)")
    work = expand(str(work_arg)) if work_arg else expand(rec["extension"]["environment"]["work"])
    out = []
    for row in rx["outputs"]:
        if "summary" not in row:
            raise SpecError(f"{rec['artifact_id']}: replica {row['replica']} has no summary (declare output.observables)")
        f = work / row["summary"]["ref"]
        if not f.is_file() or sha256_file(f) != row["summary"]["sha256"]:
            raise SpecError(f"{tilde(f)} is missing or changed since the reco record")
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def cmd_table(args) -> tuple[str, dict]:
    """B2.4, B2.6: a figure of merit from a reco record's replica summaries, as a simulated dataset-record and, with
    --f4-results, an f4-results/1 file (value, statistical uncertainty, the coverage-0.90 uncertainty object, model
    envelope from --variation reco records, tail sources, the geometry file)."""
    rec_path = expand(str(args.reco_record))
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    summaries = _reco_summaries(rec, args.work)
    rx = rec["extension"]["reconstruction"]
    decls = {o["name"]: o for o in (rx["reco_spec"].get("output") or {}).get("observables", [])}
    if args.observable not in decls:
        raise SpecError(f"--observable {args.observable} is not declared in the reco spec ({sorted(decls)})")
    if args.figure_of_merit not in RS.FOM:
        raise SpecError(f"--figure-of-merit must be one of {sorted(RS.FOM)}")
    den = {}
    for kv in args.denominator or []:
        k, _, v = kv.partition("=")
        try:
            den[k] = float(v)
        except ValueError:
            den[k] = v
    for s in summaries:  # the summaries say which stages ran; the record must agree
        if list(s["run"].get("tail_sources_simulated") or []) != list(rx.get("tail_sources_simulated") or []):
            raise SpecError(f"a replica summary lists tail sources {s['run'].get('tail_sources_simulated')}, the reco "
                            f"record {rx.get('tail_sources_simulated')}")
    problems = RS.check_denominator(den, summaries[0]["run"].get("settings") or {})
    if problems:
        raise SpecError("; ".join(problems))
    res = RS.fom_result(args.figure_of_merit, summaries, decls[args.observable], den)
    envelope = None
    if args.variation:
        var = {"nominal": summaries}
        for item in args.variation:
            name, _, path = item.partition("=")
            vrec = json.loads(expand(path).read_text(encoding="utf-8"))
            var[name] = _reco_summaries(vrec, args.work)
        envelope = RS.model_envelope(args.figure_of_merit, var, decls[args.observable])
        res["model_envelope"] = envelope["envelope"]
        res["model_envelope_annotation"] = {k: v for k, v in envelope.items() if k != "envelope"}
    created = args.created or datetime.date.today().isoformat()
    out = expand(str(args.out))
    base = expand(str(args.project_root)).resolve() if args.project_root else out.resolve().parent
    try:  # refs relative to the project root (contracts/dependencies.py resolves them there)
        ref = rec_path.resolve().relative_to(base).as_posix()
    except ValueError:
        ref = tilde(rec_path)
    labels = list(dict.fromkeys(["unvalidated"] + [s for s in rec.get("status", []) if s in ("failed", "synthetic")]))
    x = next(iter(den.values()), 0.0)
    xv = float(x) if isinstance(x, (int, float)) else 0.0
    edges = [xv * (1 - 1e-9) - 1e-12, xv * (1 + 1e-9) + 1e-12]
    rule = RS.FOM[args.figure_of_merit]
    half = (res["uncertainty"]["minus"] + res["uncertainty"]["plus"]) / 2
    doc = record_skeleton(f"geant4-table-{args.id}", f"Simulated {args.figure_of_merit} from {rec['artifact_id']} "
                          "(detector level; unvalidated unless an input study record is validated in scope)", created,
                          labels)
    doc["artifact_type"] = "dataset-record"
    doc["inputs"] = [{"ref": ref, "artifact_type": "computational-run", "artifact_id": rec["artifact_id"],
                      "sha256": sha256_file(rec_path), "status": rec.get("status", [])}]
    for k in ("extension",):
        doc.pop(k, None)
    doc["extension"] = {
        "dataset_id": f"simulation:{args.id}", "source_evidence_ids": [],
        "observable": {"quantity": rule["quantity"], "process": f"simulation of {args.figure_of_merit}",
                       "variables": [{"name": next(iter(den), "point"), "unit": "", "points": [xv]}],
                       "phase_space": {"definition": json.dumps(den, sort_keys=True)}, "level": "detector",
                       "normalization": {"kind": "shape-only"}, "bin_semantics": "point", "unit": "1"},
        "data": {"edges": edges, "values": [res["value"]], "unit": "1",
                 "uncertainties": [{"name": "statistical (+) replica spread, coverage 0.90", "kind": "statistical",
                                    "values": [half], "correlation": "uncorrelated", "gaussian": False}]},
        "covariance": {"status": "absent"}, "status": "simulated",
        "conditions": f"tail sources simulated: {rx['tail_sources_simulated']}; replicas {rx['replicas']}"}
    write_json(out, doc)
    result = {"dataset": tilde(out), "figure_of_merit": args.figure_of_merit, "result": res}
    if args.f4_results:
        f4 = {"schema": "f4-results/1", "results": {args.figure_of_merit: res},
              "tail_sources_simulated": rx["tail_sources_simulated"],
              "reco_record": {"artifact_id": rec["artifact_id"], "sha256": sha256_file(rec_path)}}
        if args.geometry:
            g = expand(str(args.geometry))
            f4["geometry"] = {"path": tilde(g), "sha256": sha256_file(g)}
        fp = expand(str(args.f4_results))
        rep = validate(f4, str(ASSETS / "simreco" / "f4_results.schema.json"))
        if not rep.ok:
            raise SpecError("the f4-results file does not validate: " + "; ".join(f.message for f in rep.errors)[:400])
        write_json(fp, f4)
        result["f4_results"] = tilde(fp)
    return "ok", result


def cmd_oracle(args) -> tuple[str, dict]:
    cfg = expand(str(args.benchmark_config))
    if not cfg.is_file():
        raise FileNotFoundError(f"{tilde(cfg)} not found")
    if not BENCHMARKS.is_file():
        return "missing-dependency", {"error": "skills/hep-detector/scripts/geant4_benchmarks.py not found"}
    cmd = [sys.executable, "-B", str(BENCHMARKS), "run", "--config", str(cfg)]
    if args.out:
        cmd += ["--out", str(expand(str(args.out)))]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    try:
        res = json.loads(p.stdout)
    except ValueError:
        return "failed", {"error": f"geant4_benchmarks.py printed no JSON (exit {p.returncode})",
                          "stderr": p.stderr[-400:]}
    verdicts = {b["benchmark"]: b.get("verdict") for b in res.get("benchmarks", [])}
    failed = sorted(k for k, v in verdicts.items() if v == "fail")
    status = "failed" if p.returncode == 1 or failed else ("ok" if p.returncode == 0 else
                                                            {2: "rejected", 3: "incomplete"}.get(p.returncode, "failed"))
    return status, {"benchmarks": verdicts, "failed": failed, "benchmark_status": res.get("status"),
                    "rule": "every reference benchmark passes and its negative control fails"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build-sim", help="build layered_sim against a recorded Geant4 installation")
    p.add_argument("--build-record", help="the Geant4 build record (not needed for simreco)")
    p.add_argument("--work", required=True)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--program", choices=("layered_sim", "element_sim", "simreco"), default="layered_sim",
                   help="which program to build (element_sim also builds simroot; simreco needs no Geant4)")
    p = sub.add_parser("check-spec", help="validate an element_sim.spec/1 (schema and cross-field rules)")
    p.add_argument("--spec", required=True)
    p = sub.add_parser("from-geometry", help="design-geometry/1 + realization profile -> element_sim.spec/1")
    for name in ("--geometry", "--profile", "--out"):
        p.add_argument(name, required=True)
    p = sub.add_parser("run", help="run one spec and write its record")
    for name, req in (("--spec", True), ("--exe", True), ("--build-record", True), ("--work", True),
                      ("--run-id", True), ("--record", True), ("--created", False)):
        p.add_argument(name, required=req)
    p.add_argument("--timeout", type=float, default=86400.0)
    p.add_argument("--data-override", action="append",
                   help="VAR=PATH: point a dataset variable elsewhere (negative control of the data-path check)")
    p.add_argument("--evidence-role", help="what the run is for in a study: trial, nominal, scan, control, variation, "
                                           "calibration (extension.simulation.evidence_role)")
    p.add_argument("--point-id", help="the evidence point of the study this run is")
    p.add_argument("--seed-group", help="adapter 0.5.0 (Geant4 program C2.1): the declared seed_group whose runs share "
                   "S (Geant4 search values: S = H(search_id, 'search', seed_group)); needs --logical-run-seed")
    p.add_argument("--logical-run-seed", type=int, help="S = H(study_id, role, point_id); run.seeds must be its job "
                                                        "seeds (seed_scheme hash-v1)")
    p.add_argument("--simroot", help="the simroot executable for an element_sim event file (default: next to --exe)")
    p = sub.add_parser("scan", help="spec grid -> workflow.json for run_workflow.py")
    for name in ("--base", "--grid", "--exe", "--build-record", "--out-dir"):
        p.add_argument(name, required=True)
    p.add_argument("--events-per-second", type=float, required=True)
    p.add_argument("--created")
    p.add_argument("--seeding", choices=("per-event", "stream"), default="per-event",
                   help="seeding of the written specs when the base spec states none (default per-event: point k gets "
                        "run.logical_run_seed S = H(study_id, role, point id))")
    p.add_argument("--study-id", help="the study's study_id for S (default: the grid name)")
    p.add_argument("--role", default="scan", help="the evidence role of the points for S (default scan)")
    p = sub.add_parser("chunk", help="local_partition.py worker")
    for name in ("--spec", "--exe", "--build-record", "--work", "--id", "--out"):
        p.add_argument(name, required=True)
    for name in ("--start", "--stop", "--seed"):
        p.add_argument(name, type=int, required=True)
    p.add_argument("--logical-run-seed", type=int, help="the job's seeds become (H(S, start, 0), H(S, start, 1))")
    p.add_argument("--created")
    p.add_argument("--timeout", type=float, default=86400.0)
    p = sub.add_parser("summarize", help="means after a partition merge")
    p.add_argument("--merged", required=True)
    p.add_argument("--work", help="the chunk work folder: check CSV hashes and duplicate event numbers")
    p.add_argument("--single-record", help="a single-run record to compare the merged means with")
    p.add_argument("--z-max", type=float, default=3.0, help="declared |z| limit against the single run (default 3)")
    p = sub.add_parser("reduce", help="a gzip-compressed copy of chosen CSV columns (recorded replay inputs)")
    p.add_argument("--csv", required=True)
    p.add_argument("--columns", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("reco", help="simroot dump + simreco per replica of an element_sim run, with its record")
    for name in ("--run-record", "--reco-spec", "--simreco", "--work-out", "--reco-id", "--record"):
        p.add_argument(name, required=True)
    p.add_argument("--work", help="the run record's work folder (default: its extension.environment.work)")
    p.add_argument("--simroot", help="the simroot executable (default: the run record's)")
    p.add_argument("--geometry", help="the design-geometry/1 file: its point_resolution_um replaces the spec's bending")
    p.add_argument("--project-root", help="refs of the record's inputs are relative to it (default: the record's folder)")
    p.add_argument("--created")
    p.add_argument("--timeout", type=float, default=86400.0)
    p = sub.add_parser("table", help="a figure of merit from a reco record: simulated dataset-record, f4-results/1")
    for name in ("--reco-record", "--figure-of-merit", "--observable", "--out", "--id"):
        p.add_argument(name, required=True)
    p.add_argument("--denominator", action="append", help="K=V of the figure of merit's denominator")
    p.add_argument("--variation", action="append", help="NAME=RECO_RECORD of a physics-list variation (model envelope)")
    p.add_argument("--f4-results", help="also write the f4-results/1 file here")
    p.add_argument("--geometry", help="the design-geometry/1 file the study used (named by sha256 in f4-results)")
    p.add_argument("--work", help="the reco records' work folder (default: each record's)")
    p.add_argument("--project-root", help="refs of the dataset's inputs are relative to it (default: its folder)")
    p.add_argument("--created")
    p = sub.add_parser("oracle", help="geant4_benchmarks.py on recorded output, through a subprocess")
    p.add_argument("--benchmark-config", required=True)
    p.add_argument("--out")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    args.argv_run = [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)]
    inputs = {k: v for k, v in vars(args).items() if k not in ("status", "argv_run")}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("jobs", "timeout", "created", "z_max", "seeding", "role", "program", "status")
                if hasattr(args, k) and f"--{k}" not in given]
    handlers = {"build-sim": cmd_build_sim, "check-spec": cmd_check_spec, "from-geometry": cmd_from_geometry,
                "run": cmd_run, "scan": cmd_scan, "chunk": cmd_chunk, "summarize": cmd_summarize, "reduce": cmd_reduce,
                "reco": cmd_reco, "table": cmd_table, "oracle": cmd_oracle}
    try:
        status, doc = handlers[args.command](args)
    except (SpecError, FileNotFoundError, KeyError, json.JSONDecodeError, IsADirectoryError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        status, doc = "failed", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())

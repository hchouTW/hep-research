#!/usr/bin/env python3
"""Run the layered_sim Geant4 program from a JSON spec and record each run (WP1 M2).

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
Subcommands:
  build-sim  configure and build layered_sim against the installation of a build record
  run        one spec -> <work>/<run-id>/ (events.csv, materials.json, datapaths.json, log.txt, spec.json) and --record
  scan       base spec + parameter grid -> specs and a workflow.json for skills/hep-computing/scripts/run_workflow.py
             (point k gets seeds [s0, s1 + k] unless the grid scans run.seeds);
             a step whose estimated time (events / --events-per-second) exceeds 3600 s is refused: partition it
  chunk      a local_partition.py worker: events [start, stop) with the chunk's seed (with --logical-run-seed S the
             job seeds H(S, start, 0), H(S, start, 1), core/simulation/seeds.py); writes additive sums only
             (n_events, sum_*, sumsq_*) plus {"csv": [{path, sha256}], "records": [...]} for --rule csv=concat
  summarize  means and standard errors from a merged partition result (non-additive quantities after the merge);
             with --work, the chunk CSVs are checked against the merged hashes and for duplicate event numbers;
             with --single-record, each mean is compared with one unpartitioned run (|z| <= --z-max, default 3)
  reduce     a gzip-compressed copy (mtime 0, byte-reproducible) of chosen columns of a run's CSV, for replay
  oracle     run hep-detector's geant4_benchmarks.py on a recorded run through a subprocess (never imported)
Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_run.py build-sim --build-record BUILD.json --work DIR
  python3 adapters/geant4/assets/geant4_run.py run --spec SPEC.json --exe EXE --build-record BUILD.json --work DIR --run-id ID --record OUT.json
      [--evidence-role ROLE --point-id ID [--logical-run-seed S]]
  python3 adapters/geant4/assets/geant4_run.py scan --base SPEC.json --grid GRID.json --exe EXE --build-record BUILD.json --out-dir DIR --events-per-second R
  python3 adapters/geant4/assets/geant4_run.py chunk --spec SPEC.json --exe EXE --build-record BUILD.json --work DIR --start A --stop B --seed S --id ID --out OUT.json
  python3 adapters/geant4/assets/geant4_run.py summarize --merged MERGED.json [--work DIR] [--single-record RUN.json]
  python3 adapters/geant4/assets/geant4_run.py reduce --csv EVENTS.csv --columns C1 C2 ... --out OUT.csv.gz
  python3 adapters/geant4/assets/geant4_run.py oracle --benchmark-config CONFIG.json [--out OUT.json]
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status, status_label, inputs, defaults_used, and the subcommand's result.
Exit codes: 0 ok; 1 the run failed (layered_sim error, data-path mismatch, benchmark failed); 2 bad input; 3 Geant4,
cmake or layered_sim missing. Standard library only.
"""
from __future__ import annotations

import datetime
import gzip
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import (ASSETS, DATA_VARS, PLUGIN, JsonArgumentParser, SpecError, build_record_ok, data_env,  # noqa: E402
                      expand, install_prefix, record_skeleton, sha256_file, sha256_json, tilde, write_json)
from core.simulation.seeds import job_seeds  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

SIM_SOURCES = ("CMakeLists.txt", "MiniJson.hh", "Spec.hh", "Spec.cc", "Detector.hh", "Detector.cc", "Physics.hh",
               "Physics.cc", "Actions.hh", "Actions.cc", "layered_sim.cc")
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
    _keys(run, "run", ("events", "first_event", "chunk", "seeds", "run_manager", "threads"), ("events", "seeds"))
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
    _keys(out, "output", ("overlap_test_points", "per_instance"))


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


def run_one(spec: dict, exe: Path, build: dict, build_path: Path, work: Path, run_id: str, timeout: float,
            overrides: dict[str, str]) -> tuple[str, dict, dict]:
    """Run layered_sim; returns (status, summary, record)."""
    run_dir = work / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    eff = effective_spec(spec)
    (run_dir / "spec.json").write_text(json.dumps(eff, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    env = data_env(build)
    env.update(overrides)
    log = run_dir / "log.txt"
    with log.open("w", encoding="utf-8") as fh:
        p = subprocess.run([str(exe), str(run_dir / "spec.json")], cwd=run_dir, stdout=fh, stderr=subprocess.STDOUT,
                           env=env, timeout=timeout)
    text = log.read_text(encoding="utf-8", errors="replace")
    status_line = next((ln for ln in reversed(text.splitlines()) if ln.startswith("LAYERED_SIM_STATUS ")), None)
    sim_status = json.loads(status_line.split(" ", 1)[1]) if status_line else {"status": "failed",
                                                                                "error": f"no status line (exit {p.returncode})"}
    if p.returncode == 2 or sim_status.get("status") == "rejected":
        return "rejected", {"error": sim_status.get("error"), "log": tilde(log)}, {}
    problems = [] if p.returncode == 0 and sim_status.get("status") == "ok" else [
        f"layered_sim exit {p.returncode}: {sim_status.get('error')}"]
    datapaths = json.loads((run_dir / "datapaths.json").read_text(encoding="utf-8")) \
        if (run_dir / "datapaths.json").is_file() else {}
    rows, dp_problems = compare_datapaths(datapaths, build, work / ".dataset-hash-cache.json") if datapaths else ([], [])
    problems += dp_problems
    overlaps = text.count("GeomVol1002")
    outputs = {}
    for name in ("spec.json", "events.csv", "materials.json", "datapaths.json", "log.txt"):
        if (run_dir / name).is_file():
            outputs[f"{run_id}/{name}"] = sha256_file(run_dir / name)
    if "events.csv" not in " ".join(outputs) and not problems:
        problems.append("layered_sim wrote no events.csv")
    ok = not problems
    b = build["extension"]["build"]
    run = spec["run"]
    sim = {
        "geant4": {"version": datapaths.get("geant4_version"), "tag": b["tag"], "commit": b["commit"],
                   "build_record_sha256": sha256_file(build_path)},
        "program": {"name": "layered_sim", "path": tilde(exe), "sha256": sha256_file(exe),
                    "sources_sha256": {s: sha256_file(ASSETS / "layered_sim" / s) for s in SIM_SOURCES}},
        "datasets": rows, "data_path_problems": dp_problems,
        "physics": spec["physics"], "ui_commands": spec.get("ui_commands", []),
        "cuts": {"default_mm": spec["physics"]["default_cut_mm"], "regions": spec["physics"].get("regions", [])},
        "step_limits": {k: spec["physics"][k] for k in ("step_limit_mm", "min_ekin_MeV") if k in spec["physics"]},
        "gun": spec["gun"], "geometry": spec["geometry"], "materials": spec.get("materials", []),
        "spec_sha256": sha256_json(spec),
        "material_dump_sha256": outputs.get(f"{run_id}/materials.json"),
        "random": {"engine": "MixMaxRng", "seeds": run["seeds"]},
        "events": run["events"], "first_event": run.get("first_event", 0), "chunk": run.get("chunk", 0),
        "run_manager": run.get("run_manager", "serial"), "threads": run.get("threads", 1),
        "overlap_reports": overlaps,
        "data_overrides": {k: tilde(v) for k, v in overrides.items()},
    }
    return ("ok" if ok else "failed"), {"run_dir": tilde(run_dir), "problems": problems, "outputs": outputs}, \
        {"simulation": sim, "outputs": outputs, "exit": p.returncode, "ok": ok}


def write_run_record(path: Path, run_id: str, spec_path: Path, spec: dict, exe: Path, result: dict, work: Path,
                     created: str) -> dict:
    sim = result["simulation"]
    rec = record_skeleton(f"geant4-run-{run_id}",
                          f"Geant4 layered_sim run {run_id}: {spec['gun']['particle']} {spec['gun']['energy_MeV']} MeV, "
                          f"{sim['events']} events (a completed run, not a validated result)", created,
                          ["unvalidated"] if result["ok"] else ["unvalidated", "failed"])
    rec["extension"] = {
        "input_manifest": [{"path": tilde(spec_path), "sha256": sha256_file(spec_path)}],
        "tools": [{"name": "Geant4", "version": f"{sim['geant4']['tag']} ({sim['geant4']['commit']})"},
                  {"name": "layered_sim", "version": sim["program"]["sha256"][:16]}],
        "commands": [f"{tilde(exe)} {run_id}/spec.json"],
        "environment": {"work": tilde(work), "dataset_variables": "all unset except the build record's",
                        "G4FORCE_RUN_MANAGER_TYPE": "unset"},
        "seeds": {"layered_sim": sim["random"]["seeds"]}, "tolerances": {},
        "exit_status": 0 if result["ok"] else 1, "output_hashes": result["outputs"], "simulation": sim}
    write_json(path, rec)
    return rec


def _evidence_fields(sim: dict, args) -> None:
    """A1.4: what the run is for in a study (extension.simulation.evidence_role, point_id) and its seed scheme
    (hash-v1 with the logical-run seed S, or legacy)."""
    for key in ("evidence_role", "point_id", "logical_run_seed"):
        if getattr(args, key, None) is not None:
            sim[key] = getattr(args, key)
    if getattr(args, "logical_run_seed", None) is not None:
        sim["seed_scheme"] = "hash-v1"
    elif getattr(args, "evidence_role", None) is not None:
        sim["seed_scheme"] = "legacy"


def cmd_build_sim(args) -> tuple[str, dict]:
    build = _load_build(args.build_record)
    if not shutil.which("cmake"):
        return "missing-dependency", {"error": "cmake not found on PATH"}
    g4dir = install_prefix(build) / "lib" / "cmake" / "Geant4"
    if not g4dir.is_dir():
        return "missing-dependency", {"error": f"no Geant4 CMake configuration at {tilde(g4dir)}"}
    bld = expand(str(args.work)) / "layered_sim-build"
    log = bld / "build.log"
    bld.mkdir(parents=True, exist_ok=True)
    codes = []
    with log.open("w", encoding="utf-8") as fh:
        for cmd in (["cmake", "-S", str(ASSETS / "layered_sim"), "-B", str(bld), f"-DGeant4_DIR={g4dir}",
                     "-DCMAKE_BUILD_TYPE=Release"], ["cmake", "--build", str(bld), "--parallel", str(args.jobs)]):
            codes.append(subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, timeout=3600).returncode)
            if codes[-1]:
                break
    exe = bld / "layered_sim"
    if any(codes) or not exe.is_file():
        return "failed", {"error": "layered_sim did not build", "log": tilde(log), "exit_codes": codes}
    return "ok", {"exe": tilde(exe), "sha256": sha256_file(exe),
                  "sources_sha256": {s: sha256_file(ASSETS / "layered_sim" / s) for s in SIM_SOURCES}}


def _exe(path: str) -> Path:
    exe = expand(path)
    if not exe.is_file():
        raise FileNotFoundError(f"layered_sim executable {tilde(exe)} not found (build it with build-sim)")
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
    validate_spec(spec)
    build_path = expand(str(args.build_record))
    build = _load_build(build_path)
    try:
        exe = _exe(args.exe)
    except FileNotFoundError as exc:
        return "missing-dependency", {"error": str(exc)}
    work = expand(str(args.work)).resolve()
    if args.logical_run_seed is not None:  # A1.4: a single job of logical run S has the seed pair (H(S,0,0), H(S,0,1))
        first = int(spec["run"].get("first_event", 0))
        want = list(job_seeds(args.logical_run_seed, first))
        if list(spec["run"].get("seeds") or []) != want:
            raise SpecError(f"run.seeds {spec['run'].get('seeds')} are not the job seeds {want} of logical run seed "
                            f"{args.logical_run_seed} starting at event {first} (core/simulation/seeds.py)")
    status, summary, result = run_one(spec, exe, build, build_path, work, args.run_id, args.timeout,
                                      _overrides(args.data_override))
    if status == "rejected":
        return status, summary
    _evidence_fields(result["simulation"], args)
    created = args.created or datetime.date.today().isoformat()
    record_path = expand(str(args.record))
    write_run_record(record_path, args.run_id, spec_path, spec, exe, result, work, created)
    summary["record"] = tilde(record_path)
    return status, summary


def _set(doc: dict, dotted: str, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        doc = doc.setdefault(k, {})
    doc[keys[-1]] = value


def cmd_scan(args) -> tuple[str, dict]:
    base = json.loads(expand(str(args.base)).read_text(encoding="utf-8"))
    validate_spec(base)
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
        validate_spec(spec)
        sid = f"{grid.get('name', 'scan')}-{k:03d}"
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
                               datetime.date.today().isoformat(), "--timeout", str(STEP_LIMIT_S - 60)]})
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


SUMMED = ("edep_", "chlen_", "plen_", "leak_", "killed_", "exit_ekin_MeV", "primary_eloss_MeV")


def cmd_chunk(args) -> tuple[str, dict]:
    spec = json.loads(expand(str(args.spec)).read_text(encoding="utf-8"))
    validate_spec(spec)
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
    work = expand(str(args.work)).resolve()
    status, summary, result = run_one(spec, exe, build, build_path, work, args.id, args.timeout, {})
    if status != "ok":
        return status, summary
    created = args.created or datetime.date.today().isoformat()
    rec_path = work / "records" / f"{args.id}.computational-run.json"
    write_run_record(rec_path, args.id, expand(str(args.spec)), spec, exe, result, work, created)
    cols, rows = read_csv(work / args.id / "events.csv")
    sums = {"n_events": len(rows)}
    for i, c in enumerate(cols):
        if c.startswith(SUMMED):
            vals = [float(r[i]) for r in rows]
            sums[f"sum_{c}"] = math.fsum(vals)
            sums[f"sumsq_{c}"] = math.fsum(v * v for v in vals)
    sums["csv"] = [{"path": f"{args.id}/events.csv", "sha256": sha256_file(work / args.id / "events.csv")}]
    sums["records"] = [{"path": f"records/{args.id}.computational-run.json", "sha256": sha256_file(rec_path)}]
    write_json(expand(str(args.out)), sums)
    return "ok", {"chunk": args.id, "n_events": len(rows)}


def cmd_summarize(args) -> tuple[str, dict]:
    merged = json.loads(expand(str(args.merged)).read_text(encoding="utf-8"))
    res = merged.get("merged", merged)
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
    p.add_argument("--build-record", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
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
    p.add_argument("--logical-run-seed", type=int, help="S = H(study_id, role, point_id); run.seeds must be its job "
                                                        "seeds (seed_scheme hash-v1)")
    p = sub.add_parser("scan", help="spec grid -> workflow.json for run_workflow.py")
    for name in ("--base", "--grid", "--exe", "--build-record", "--out-dir"):
        p.add_argument(name, required=True)
    p.add_argument("--events-per-second", type=float, required=True)
    p.add_argument("--created")
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
    p = sub.add_parser("oracle", help="geant4_benchmarks.py on recorded output, through a subprocess")
    p.add_argument("--benchmark-config", required=True)
    p.add_argument("--out")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("jobs", "timeout", "created", "z_max", "status") if hasattr(args, k) and f"--{k}" not in given]
    handlers = {"build-sim": cmd_build_sim, "run": cmd_run, "scan": cmd_scan, "chunk": cmd_chunk,
                "summarize": cmd_summarize, "reduce": cmd_reduce, "oracle": cmd_oracle}
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

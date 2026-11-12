"""The Geant4 PRODUCTION runs of simcal phase 3 (wave 3, WP-I) and the drivers that turn their products into the section
15.2 / P0 / P3 / P6 evidence and the section 8.7 note 6 RICH calibration. Not a unit test module; no Slurm here (the main
session registers the configuration in the card and submits the arrays).

  python3 calibration_phase3_g4.py --cards ROOT                 the run cards, the ask states and the manifest; check-spec
  python3 calibration_phase3_g4.py --list                       the Geant4 array (one task per g4sim_run)
  python3 calibration_phase3_g4.py --task K --out ROOT          one Geant4 array task (conda env `geant4` active)
  python3 calibration_phase3_g4.py --tell ROOT                  products -> G4simEvaluator.tell; the section 6.6 check
  python3 calibration_phase3_g4.py --evidence-list              the evidence array (after --tell)
  python3 calibration_phase3_g4.py --evidence K --root ROOT --out DIR    one evidence task
  python3 calibration_phase3_g4.py --merge DIR --out FILE       merge and decide (exit 0 all passed, 1 a failure/missing)
  python3 calibration_phase3_g4.py --local --out DIR            the whole path on STAND-IN products at tiny sizes

Campaigns under ROOT (default /ceph/sharedfs/work/AMS/hsinyichou/simcal-p3): `zdc-fixture` (section 15.2 synthetic ZDC,
P0 (k_B), P0 of the response, the Birks rerun) and `rich-replica` (section 15.2 RICH replica, P3, P6, note 6). Layout per
campaign: cards/<run>/{detector,request,run}.json (+ claims.json), state/<run>.json (the evaluator's ask/tell state of
that run), runs/<run>/ (g4sim_run's work folder and task.json), manifest.json (every card's SHA-256), tell.json.

Seeds (section 6.6, 14.1): the ZDC runs share S_0 = H(simcal-p3, zdc, fit, nominal, 0, t) and the events [0, N) (common
random numbers: k_B and the scintillation yield draw no random number in transport without optical photons), the
reference run S_1 = H(simcal-p3, zdc, reference, nominal, 0, t) (independent events); the RICH runs one block per beta
sample (calibration_rich_fixture.ask: S_b = H(simcal-p3, rich, design, surrogate, b, t)), shared by its 32 design
points. Everything is `synthetic` (the ZDC example and the RICH replica are synthetic geometries)."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import resource
import shutil
import socket
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "adapters" / "geant4" / "assets"
for _p in (str(ROOT), str(HERE), str(ASSETS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibration_rich_fixture as R  # noqa: E402
import calibration_zdc_fixture as Z  # noqa: E402
import g4sim_calib_eval as E  # noqa: E402
import g4sim_simulate as simulate  # noqa: E402

from core.calibration import cherenkov_standin as C  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import emulator, identify, io, kernel_check, linear  # noqa: E402
from core.calibration import evaluator as engine  # noqa: E402
from core.calibration import evaluator_problem as EP  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402

SERIES = "simcal-p3"
OUT_ROOT = Path("/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3")
PROGRAM = Path("/ceph/sharedfs/work/AMS/hsinyichou/g4sim-references/g4sim_run-build28/g4sim_run")
PROGRAM_SHA256 = "8b6230c150c0f21d6e76ffe7ab50a08b11838d7bfaf072f2176b51ea0826cffc"
BUILD = ("g4sim_run-build28: the S8 judged build (job 7531421), source 70af0c20; the g4sim_run C++ differs from this "
         "commit's only by a comment (e98cd989, NewRun.cc)")
CALO, RICH = "zdc-fixture", "rich-replica"
CALO_EVENTS, RICH_EVENTS = 20_000, 2000
CALO_CPU_S = Z.CALORIMETER_MS_PER_EVENT * Z.SCORER_FACTOR / 1000.0      # 9.2 ms x 1.5 (job 7477544)
RICH_CPU_S = R.CPU_S_PER_EVENT                                           # 0.084 s (job 7523520)
VISIBLE = "zdc_visible"
READOUT = "ecal"                         # the ZDC example's readout (6 x 6 crystals, fields ix, iy)
BIRKS_CENTRE = 0.5 * (Z.BIRKS_PRIOR[0] + Z.BIRKS_PRIOR[1])
LABEL = "synthetic"
RICH_SAMPLES = [dict(s, beta=C.beta_of(s["kinetic_per_nucleon_GeV"])) for s in R.SAMPLES]
TRUTH = {"height_mm": 465.0, "index_scale": 1.0005}    # the note-6 toys' truth (as the stand-in's registered test)
NOTE6_TOYS, NOTE6_RESEED, NOTE6_PER_TASK = 1000, 10, 100
PROVISIONAL = "provisional-thresholds"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
                                timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                                    timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "host": socket.gethostname(), "python": sys.version.split()[0],
            "numpy": np.__version__}


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    io.write_json(str(path), io.jsonable(value))


# ------------------------------------------------------------------ the ZDC production documents
def calo_documents(events: int = CALO_EVENTS) -> dict:
    """The CALO example's specifications as the fixture's production: the crystals in `PbWO4_scint` (G4_PbWO4 with the
    fixture's Birks constant and scintillation yield, r = 0.5; all `assumed`), the split, dE/dx-class and edep_visible
    scorers on the crystals, one thread per task; the fixture's response pipeline and map."""
    det = json.loads((Z.EXAMPLE / "detector.json").read_text())
    det["materials"][Z.MATERIAL] = {
        "base": "G4_PbWO4", "facts": "assumed",
        "ionisation": {"birks_mm_per_MeV": repr(Z.BIRKS0), "facts": "assumed"},
        "scintillation": {"yield_per_MeV": repr(Z.LIGHT_YIELD0), "resolution_scale": repr(Z.R0), "facts": "assumed"}}
    det["templates"]["crystal"]["material"] = Z.MATERIAL
    req = json.loads((Z.EXAMPLE / "request.json").read_text())
    sel = {"tags": ["crystal"]}
    req["scorers"] = [{"name": Z.SPLIT, "readout": READOUT, "select": sel, "quantity": "edep_visible_ly_split"},
                      {"name": Z.DEDX, "readout": READOUT, "select": sel, "quantity": "edep_by_dedx_class"},
                      {"name": VISIBLE, "readout": READOUT, "select": sel, "quantity": "edep_visible"}]
    run = json.loads((Z.EXAMPLE / "run.json").read_text())
    run["run"].update(events=int(events), first_event=0, mode="mt", threads=1)
    fx = Z.documents()
    return {"detector": det, "request": req, "run": run, "pipeline": fx["pipeline"], "maps": fx["maps"]}


def calo_plan(batches: dict, observables=None, coupling: str | None = None) -> dict:
    """The fixture's plan (Z.plan) over the production documents."""
    p = Z.plan(batches, observables=observables)
    d = calo_documents()
    p["evaluator"]["documents"].update(detector=d["detector"], request=d["request"], run=d["run"])
    p["evaluator"]["scorers"] = {"split": Z.SPLIT, "dedx": Z.DEDX}
    if coupling:
        p["evaluator"]["coupling"] = coupling
    return p


def calo_runs(events: int = CALO_EVENTS) -> list:
    """Z.production_runs plus `kB-centre` (k_B at the prior centre, the same events): P0 (k_B) needs >= 3 points with a
    full g4sim_run each (k_B is a rerun parameter, kernel_check._reference), the two extremes and the centre."""
    out = []
    for r in Z.production_runs(events):
        theta = ({"birks": r["birks"]} if r["name"].startswith("kB") else
                 {"light_yield": r["light_yield"]} if r["name"].startswith("LY") else {})
        out.append({"name": r["name"], "theta": theta, "block": "reference" if r["name"] == "reference" else "nominal",
                    "use": r["use"]})
    out.insert(3, {"name": "kB-centre", "theta": {"birks": BIRKS_CENTRE}, "block": "nominal",
                   "use": "P0 (k_B): the third point (the prior centre) with a full g4sim_run at the nominal events"})
    return out


def calo_seeds() -> dict:
    s0, t0 = DG.block_seed(SERIES, "zdc", "fit", "nominal", 0)
    s1, t1 = DG.block_seed(SERIES, "zdc", "reference", "nominal", 0, registered=[s0])
    return {"nominal": (s0, t0), "reference": (s1, t1)}


def _repoint(state_path: Path, req: dict, seed: int, first: int, n: int) -> None:
    """The evaluator's ask puts every point on its design block; a paired run is re-pointed at the nominal block (as
    Z.production_cards does for the request), and the state record with it, so that tell checks the right interval."""
    st = io.load(str(state_path))
    rec = st["points"][req["point_id"]]
    rec.update(logical_run_seed=seed, first_event=first, events=n, run_sha256=req["run_sha256"],
               detector_sha256=req["detector_sha256"])
    io.write_json(str(state_path), st)


def calo_cards(out: Path, events: int = CALO_EVENTS) -> list:
    seeds = calo_seeds()
    nominal = {"logical_run_seed": seeds["nominal"][0], "first_event": 0, "events": int(events), "cells": [],
               "primaries": []}
    contract = Z.contract(thetas=("birks", "light_yield"))
    ev = engine.make(calo_plan({"nominal": nominal}), contract)
    rows = []
    for r in calo_runs(events):
        st = out / CALO / "state" / f"{r['name']}.json"
        st.parent.mkdir(parents=True, exist_ok=True)
        if st.exists():
            st.unlink()
        req = ev.ask([r["theta"]], str(st), series=SERIES, study="zdc", events=int(events))[0]
        seed, t = seeds[r["block"]]
        req["run"]["run"].update(logical_run_seed=seed, first_event=0, events=int(events))
        if "light_yield" in r["theta"]:      # the full run at that yield: the split of the detector-spec moves with it
            req["detector"] = DG.pointer_set(req["detector"], f"/materials/{Z.MATERIAL}/scintillation/yield_per_MeV",
                                             repr(float(r["theta"]["light_yield"])))
        req["run_sha256"], req["detector_sha256"] = canonical_sha256(req["run"]), canonical_sha256(req["detector"])
        _repoint(st, req, seed, 0, int(events))
        rows.append({"campaign": CALO, "name": r["name"], "theta": r["theta"], "use": "fit" if r["block"] == "nominal"
                     else "reference", "set": f"zdc-{r['block']}", "logical_run_seed": seed, "seed_t": t,
                     "first_event": 0, "events": int(events), "purpose": r["use"],
                     "documents": {"detector": req["detector"], "request": req["request"], "run": req["run"]},
                     "state": str(st.relative_to(out)), "cpu_seconds_estimate": round(events * CALO_CPU_S, 1)})
    return rows


# ------------------------------------------------------------------ the RICH production documents
def rich_contract(samples=None) -> dict:
    return C.contract(samples or RICH_SAMPLES, exposure=RICH_EVENTS)


def rich_plan() -> dict:
    return {"design": {"surrogate": {"parameters": ["height_mm", "index_scale"], "n_design": 24, "held_back": 8}}}


def rich_points() -> dict:
    cfg = emulator.settings(rich_contract(), rich_plan())
    return {"settings": cfg, **emulator.design(cfg)}


def rich_cards(out: Path, events: int = RICH_EVENTS) -> list:
    pts = rich_points()
    points = pts["training"] + pts["held_back"]
    role = ["training"] * len(pts["training"]) + ["held-back"] * len(pts["held_back"])
    rows = []
    for req in R.ask(points, SERIES, "rich", events=int(events)):
        req["run"]["run"].update(threads=1)
        req["run_sha256"] = canonical_sha256(req["run"])
        name = f"{req['sample']}-{int(req['point_id']):02d}"
        st = out / RICH / "state" / f"{name}.json"
        _write(st, {"schema": E.STATE_SCHEMA, "points": {"0": {
            "theta": req["theta"], "status": "asked", "run_id": None, "run_sha256": req["run_sha256"],
            "detector_sha256": req["detector_sha256"], "logical_run_seed": req["logical_run_seed"],
            "first_event": req["first_event"], "events": req["events"]}}})
        rows.append({"campaign": RICH, "name": name, "theta": req["theta"], "sample": req["sample"],
                     "role": role[int(req["point_id"])], "use": "design", "set": f"rich-{req['sample']}",
                     "logical_run_seed": req["logical_run_seed"], "seed_t": req["seed_t"],
                     "first_event": req["first_event"], "events": req["events"],
                     "documents": {"detector": req["detector"], "request": req["request"], "run": req["run"]},
                     "claims": list(R.CLAIMS), "state": str(st.relative_to(out)),
                     "cpu_seconds_estimate": round(req["events"] * RICH_CPU_S, 1)})
    return rows


# ------------------------------------------------------------------ cards, check-spec, manifest
def preflight(row: dict, folder: Path) -> list:
    """The checks a card passes before Slurm, without Geant4: g4sim_run.py check-spec on the run card (subprocess, as
    the job runs it), the detector-spec check (with the profile's claims for the RICH case) and g4sim's physics and
    scorer checks of the simulate preflight (g4sim_physics_check, as examples/zdc-synthetic-ecal/run.py)."""
    import g4sim_physics_check as physics_check
    from contracts import geometry
    out = []
    cp = subprocess.run([sys.executable, "-I", str(ASSETS / "g4sim_run.py"), "check-spec", "--run",
                         str(folder / "run.json")], capture_output=True, text=True, timeout=300)
    try:
        if json.loads(cp.stdout)["status"] != "ok":
            out.append(f"check-spec: {cp.stdout.strip()}")
    except (json.JSONDecodeError, KeyError):
        out.append(f"check-spec exit {cp.returncode}: {cp.stdout[-400:]} {cp.stderr[-400:]}")
    checked = geometry.check_file(folder / "detector.json", row.get("claims") or [])
    if checked["status"] != "ok":
        return out + [f"detector-spec: {checked['findings'][:3]}"]
    ir = checked["ir"]
    request = row["documents"]["request"]
    resolved = simulate.resolved_request(request, ir, folder)
    f = physics_check.card_findings(row["documents"]["run"], request,
                                    requirements=ir["physical"]["physics_requirements"],
                                    materials=ir["physical"]["materials"],
                                    selected_materials=simulate.selected_materials(resolved, ir),
                                    physical=ir["physical"])
    regions = {rec["region"] for rec in ir["physical"]["templates"].values()} - {"default"}
    f += physics_check.hit_findings(resolved["scorers"], regions, request.get("truth", {}))
    return out + [f"physics: {x.get('code')}: {x.get('message')}" for x in f]


def write_cards(out: Path, calo_events: int = CALO_EVENTS, rich_events: int = RICH_EVENTS, check: bool = True,
                rich: bool | None = None) -> dict:
    rows = calo_cards(out, calo_events) + (rich_cards(out, rich_events) if (R.AVAILABLE if rich is None else rich)
                                         else [])
    problems = {}
    for r in rows:
        folder = out / r["campaign"] / "cards" / r["name"]
        folder.mkdir(parents=True, exist_ok=True)
        for k, doc in r["documents"].items():
            (folder / f"{k}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        if r.get("claims"):
            (folder / "claims.json").write_text(json.dumps(r["claims"]) + "\n", encoding="utf-8")
        r["sha256"] = {f.name: _sha(f) for f in sorted(folder.glob("*.json"))}
        if check:
            bad = preflight(r, folder)
            if bad:
                problems[f"{r['campaign']}/{r['name']}"] = bad
    man = {"schema": "simcal-p3-g4-manifest/1", "program": str(PROGRAM), "program_sha256": PROGRAM_SHA256,
           "build": BUILD, "series": SERIES, "label": LABEL, "provenance": provenance(),
           "runs": [{k: v for k, v in r.items() if k != "documents"} for r in rows],
           "checked": bool(check), "problems": problems}
    _write(out / "manifest.json", man)
    man["manifest_sha256"] = _sha(out / "manifest.json")
    return man


def load_manifest(root: Path) -> dict:
    return json.loads((root / "manifest.json").read_text())


# ------------------------------------------------------------------ the Geant4 array
def geant4_tasks(root: Path | None = None) -> list:
    """One task per g4sim_run: ZDC (7 runs) then RICH (64 runs), in manifest order (or the default configuration)."""
    if root is not None and (root / "manifest.json").exists():
        runs = load_manifest(root)["runs"]
    else:
        runs = [{"campaign": CALO, "name": r["name"], "events": CALO_EVENTS,
                 "cpu_seconds_estimate": round(CALO_EVENTS * CALO_CPU_S, 1)} for r in calo_runs()]
        runs += [{"campaign": RICH, "name": f"{s['name']}-{i:02d}", "events": RICH_EVENTS,
                  "cpu_seconds_estimate": round(RICH_EVENTS * RICH_CPU_S, 1)} for s in R.SAMPLES for i in range(32)]
    return [{"task": k, "campaign": r["campaign"], "name": r["name"], "events": r["events"],
             "cpu_seconds_estimate": r["cpu_seconds_estimate"]} for k, r in enumerate(runs)]


def run_geant4_task(k: int, root: Path, program: Path = PROGRAM, program_sha256: str = PROGRAM_SHA256,
                    runner=None) -> dict:
    """One g4sim_run.py simulate from the registered cards (their SHA-256 checked against the manifest, the program's
    against the build record); outputs in ROOT/<campaign>/runs/<run>/, a task record beside them."""
    man = load_manifest(root)
    row = man["runs"][k]
    cards = root / row["campaign"] / "cards" / row["name"]
    work = root / row["campaign"] / "runs" / row["name"]
    problems = [f"{n}: sha256 differs from the manifest" for n, h in row["sha256"].items() if _sha(cards / n) != h]
    if _sha(program) != program_sha256:
        problems.append(f"{program}: sha256 is not the build's {program_sha256[:16]}")
    rec = {"task": k, "campaign": row["campaign"], "name": row["name"], "program": str(program),
           "provenance": provenance(), "started": time.time()}
    if problems:
        rec.update(status="refused", problems=problems)
        _write(root / row["campaign"] / "runs" / f"{row['name']}.task.json", rec)
        return rec
    if work.exists():
        shutil.rmtree(work)                 # a task is rerun whole (g4sim_run's work folder is not resumable)
    cmd = [sys.executable, "-I", str(ASSETS / "g4sim_run.py"), "simulate", "--detector", str(cards / "detector.json"),
           "--request", str(cards / "request.json"), "--run", str(cards / "run.json"), "--program", str(program),
           "--work", str(work)]
    if (cards / "claims.json").exists():
        cmd += ["--claims", str(cards / "claims.json")]
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    cp = (runner or subprocess.run)(cmd, capture_output=True, text=True, check=False)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        result = json.loads(cp.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        result = {"status": "error", "stdout": cp.stdout[-2000:], "stderr": cp.stderr[-2000:]}
    rec.update(status=result.get("status"), exit=cp.returncode, wall_seconds=round(time.perf_counter() - t0, 1),
               cpu_seconds=round(after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, 1),
               max_rss_kb=after.ru_maxrss, result={k2: result.get(k2) for k2 in ("status", "rows", "closure",
                                                                                    "geometry_id", "request_id",
                                                                                    "findings", "problems", "reason")})
    _write(root / row["campaign"] / "runs" / f"{row['name']}.task.json", rec)
    return rec


# ------------------------------------------------------------------ tell (section 7.1) and the section 6.6 check
def _rows(path: Path) -> list:
    return E.read_csv_rows(path) if path.exists() else []


def read_products(work: Path, campaign: str) -> dict:
    """One g4sim_run's products as an evaluator part: cells (the ZDC scorers, bins >= 0; all rows for the RICH case),
    primaries, photons; with the run's summary."""
    cells = _rows(work / "cells.csv")
    if campaign == CALO:
        keep = {Z.SPLIT, Z.DEDX, VISIBLE}
        cells = [r for r in cells if r[1] in keep and int(r[3]) >= 0]
    out = {"cells": cells, "primaries": _rows(work / "primaries.csv")}
    if campaign == RICH:
        out["photons"] = _rows(work / "photons.csv")
    return out


def tell_all(root: Path, build_hash: str = PROGRAM_SHA256) -> dict:
    """Every finished run told into its state (G4simEvaluator.tell: the products must be the asked seed and interval),
    then DG.interval_findings on the told records and the seed blocks (section 6.6). Exit-style status: passed, failed
    (a finding or a refused tell), incomplete (a run without products)."""
    import g4sim_run
    man = load_manifest(root)
    told, missing, refused = [], [], {}
    for row in man["runs"]:
        work = root / row["campaign"] / "runs" / row["name"]
        summ = work / "summary.json"
        if not summ.exists():
            missing.append(f"{row['campaign']}/{row['name']}")
            continue
        s = json.loads(summ.read_text())
        if s.get("status") != "ok":
            refused[f"{row['campaign']}/{row['name']}"] = f"g4sim_run status {s.get('status')}"
            continue
        part = read_products(work, row["campaign"])
        firsts = sorted(int(p[0]) for p in part["primaries"])
        if firsts != list(range(row["first_event"], row["first_event"] + row["events"])):
            refused[f"{row['campaign']}/{row['name']}"] = "primaries.csv does not hold exactly the asked events"
            continue
        part.update(logical_run_seed=row["logical_run_seed"], first_event=row["first_event"], events=row["events"])
        card = json.loads((root / row["campaign"] / "cards" / row["name"] / "run.json").read_text())
        rid = g4sim_run.run_id(s["geometry_id"], s["request_id"], card, build_hash)
        try:
            E.G4simEvaluator.tell(str(root / row["state"]), "0", rid, [part])
        except DG.CheckError as exc:
            refused[f"{row['campaign']}/{row['name']}"] = str(exc)
            continue
        told.append({"run_id": rid, "use": row["use"], "set": row["set"], "logical_run_seed": row["logical_run_seed"],
                     "first_event": row["first_event"], "events": row["events"], "run_seed": row["logical_run_seed"],
                     "replica": 0, "name": f"{row['campaign']}/{row['name']}",
                     "products_sha256": {n: _sha(work / n) for n in ("cells.csv", "primaries.csv", "photons.csv")
                                         if (work / n).exists()}})
    chk = told_interval_check(root, man)
    status = "failed" if refused or chk["findings"] else ("incomplete" if missing else "passed")
    rep = {"status": status, "told": told, "missing": missing, "refused": refused, "interval_check": chk,
           "provenance": provenance(), "label": LABEL}
    _write(root / "tell.json", rep)
    return rep


def told_interval_check(root: Path, man: dict | None = None) -> dict:
    """DG.interval_findings on the TOLD records (seed and interval as the states hold them after tell) and the seed
    blocks of the manifest (m_blk = 1, N_ev = the run's events)."""
    man = man or load_manifest(root)
    evs, blocks = [], {}
    for row in man["runs"]:
        st = io.load(str(root / row["state"]))
        rec = st["points"]["0"]
        if rec.get("status") != "told":
            continue
        evs.append({"run_id": f"{row['campaign']}/{row['name']}", "use": row["use"], "set": row["set"],
                    "logical_run_seed": rec["batch"]["logical_run_seed"], "first_event": rec["batch"]["first_event"],
                    "events": rec["batch"]["events"], "run_seed": rec["batch"]["logical_run_seed"], "replica": 0})
        blocks[(row["campaign"], row["set"])] = {"block": f"{row['campaign']}/{row['set']}",
                                                 "logical_run_seed": row["logical_run_seed"], "t": row["seed_t"],
                                                 "m_blk": 1, "N_ev": row["events"]}
    return DG.interval_findings({"evaluations": evs, "seed_blocks": list(blocks.values())})


def _compact(row) -> tuple:
    """A CSV row as a tuple of numbers (the scorer name interned): a 20,000-event ZDC run has ~2 M cell rows, whose
    string lists would take several GB (the evaluator reads rows by index and converts with int()/float())."""
    def num(i, x):
        if i == 1 or not isinstance(x, str):
            return sys.intern(x) if isinstance(x, str) else x
        try:
            return int(x) if i in (0, 2, 3) else float(x)
        except ValueError:
            return x
    return tuple(num(i, x) for i, x in enumerate(row))


def told_batch(root: Path, campaign: str, name: str) -> dict:
    rec = io.load(str(root / campaign / "state" / f"{name}.json"))["points"]["0"]
    if rec.get("status") != "told":
        raise LookupError(f"{campaign}/{name} is not told")
    b = rec["batch"]
    b["cells"] = [_compact(r) for r in b.get("cells", [])]
    return b


# ------------------------------------------------------------------ evidence: the ZDC items
def calo_evaluator(root: Path, names: list, thetas, observables, coupling: str | None = None, reference: bool = False):
    """The g4sim evaluator over told ZDC products: `nominal` (and `reference`) plus the told points, the runs at the
    nominal events declaring one set (paired, section 6.6)."""
    bs = {}
    for nm in ["nominal"] + (["reference"] if reference else []) + list(names):
        b = dict(told_batch(root, CALO, nm))
        if nm in ("nominal", "reference"):
            b.pop("point", None)
        b.update(use="reference" if nm == "reference" else "fit", **({} if nm == "reference" else {"set": "s"}))
        bs[nm] = b
    p = calo_plan(bs, observables=observables, coupling=coupling)
    if reference:
        p["evaluator"]["reference"] = "reference"
    c = Z.contract(thetas=thetas, observables=[o for o in observables if o != "vis_mean"] or ("vis_mean",))
    return c, p, engine.make(p, c)


def ev_calo_p0_response(root: Path) -> dict:
    """Section 15.2 synthetic ZDC item 1 (test_with_geant4 of ResponseParametersP0, test_p0_against_full_simulation):
    P0 of the light yield by re-digitization against a full g4sim_run plus response at the section 5.4 light-yield
    extremes (LY-low, LY-high) and the independent `reference` events. Rule: P0 (section 8.2 note 1, D53)."""
    c, p, ev = calo_evaluator(root, ["LY-low", "LY-high"], ("light_yield",), ("pe_mean", "pe_std"), reference=True)
    req = kernel_check.required_spot_checks(c, p)
    r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"light_yield": Z.LIGHT_YIELD0}, {"light_yield": 195.0}],
                        5, spot_checks=req[0]["points"], required=req)
    return {"item": "zdc-p0-response", "result": r, "passed": r["status"] == "passed", "flags": [PROVISIONAL]}


def ev_calo_birks_rerun(root: Path) -> dict:
    """Section 15.2 synthetic ZDC item 2 (BirksRerunAgainstResimulation.test_with_geant4, Birks.test_rerun_agrees_
    with_resimulation_at_the_new_birks): edep_visible from the nominal run's edep_by_dedx_class at k_B' against the
    edep_visible scorer of the run at k_B' (the same events), per (event, volume) within g4sim_simulate.
    reweighting_bound at k_B'; and through the evaluator, |vis_mean(rerun) - vis_mean(run)| within the mean bound.
    Rule: every comparison within its bound (D75: a deterministic rerun)."""
    nom = told_batch(root, CALO, "nominal")
    dedx: dict = {}
    for r in nom["cells"]:
        if r[1] == Z.DEDX:
            dedx.setdefault((int(r[0]), int(r[2])), []).append((int(r[3]), float(r[4])))
    _, _, ev = calo_evaluator(root, [], ("birks",), ("vis_mean",))
    rows = []
    for nm, kb in (("kB-low", Z.BIRKS_PRIOR[0]), ("kB-centre", BIRKS_CENTRE), ("kB-high", Z.BIRKS_PRIOR[1])):
        b = told_batch(root, CALO, nm)
        vis: dict = {}
        for r in b["cells"]:
            if r[1] == VISIBLE:
                key = (int(r[0]), int(r[2]))
                vis[key] = vis.get(key, 0.0) + float(r[4])
        keys = sorted(set(dedx) | set(vis))
        diff = np.array([abs(simulate.reweighted(dedx.get(k, []), kb) - vis.get(k, 0.0)) for k in keys])
        bound = np.array([simulate.reweighting_bound(dedx.get(k, []), kb) for k in keys])
        within = diff <= bound + 1e-9 * np.maximum(1.0, bound)
        per_event = {}
        for (e, _v), x in vis.items():
            per_event[e] = per_event.get(e, 0.0) + x
        truth = float(np.mean([per_event.get(e, 0.0) for e in range(b["first_event"], b["first_event"] + b["events"])]))
        res = ev.evaluate({"birks": kb})
        k = res["names"].index("vis_mean")
        dmean = abs(float(res["pred"][k]) - truth)
        mb = float(res["birks_bound_MeV"]["vis_mean"])
        rows.append({"run": nm, "birks": kb, "pairs": len(keys), "within": int(within.sum()),
                     "max_ratio": float(np.max(diff / np.where(bound > 0, bound, np.inf))) if keys else None,
                     "unmatched": len(set(dedx) ^ set(vis)), "mean_rerun": float(res["pred"][k]), "mean_run": truth,
                     "mean_bound": mb, "mean_within": dmean <= mb,
                     "passed": bool(within.all()) and dmean <= mb})
    return {"item": "zdc-birks-rerun", "rows": rows, "passed": all(r["passed"] for r in rows)}


def ev_calo_p0_birks(root: Path) -> dict:
    """Section 15.3.1 P0 (k_B) with the section 5.4 spot checks (BirksSpotChecks.test_with_geant4_products): k_B by the
    deterministic rerun with scintillation downstream (r = 0.5) against full g4sim_runs at k_B = 0.21 (centre) and at
    both extremes; the evaluator's default (quantile) coupling. Rule: P0. On the stand-in this P0 FAILS at both
    extremes (the nominal-split bias, a recorded phase-3 finding); the Geant4 result is recorded as it comes."""
    c, p, ev = calo_evaluator(root, ["kB-low", "kB-centre", "kB-high"], ("birks",), ("pe_std",))
    req = kernel_check.required_spot_checks(c, p)
    r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"birks": BIRKS_CENTRE}], 3, spot_checks=req[0]["points"],
                        required=req)
    return {"item": "zdc-p0-birks", "result": r, "passed": r["status"] == "passed", "flags": [PROVISIONAL]}


# ------------------------------------------------------------------ evidence: the RICH items
def _rindex(doc: dict, material: str):
    t = doc["materials"][material]["optical"]["rindex"]
    return np.array([float(x) for x in t["energy_eV"]]), np.array([float(x) for x in t["value"]])


def plane_radius(batch: dict, detector: dict) -> np.ndarray:
    """Per event, the median over the primary's aerogel photons (parent 1, emission in the aerogel layer) of their
    radius on the detection plane about the primary's crossing: the emission point carried down the planar layers
    (aerogel, foil, the expansion gap) along the recorded arrival direction refracted back by Snell's law with the
    run's own n(E) (the run's detector card: a theta on the index or the height moves the radius). photons.csv holds
    no arrival position; for an unscattered photon this IS its hit position. NaN for an event without such photons.
    (calib_eval's `ring_radius`, expansion x tan(angle) at a fixed expansion, does not see the height.)"""
    prm = detector["params"]
    h, f, t = (float(prm[k]) for k in ("height_mm", "foil_mm", "aero_mm"))
    ea, na = _rindex(detector, "aerogel")
    ef, nf = _rindex(detector, "foil_pmma")
    z0, z1 = h + f, h + f + t
    first, n = int(batch["first_event"]), int(batch["events"])
    prim = {int(r[0]): (np.array([float(x) for x in r[2:5]]), np.array([float(x) for x in r[5:8]]))
            for r in batch.get("primaries", [])}
    per: dict = {}
    for r in batch.get("photons", []):
        e, z, parent = int(r[0]), float(r[8]), int(r[12])
        if parent != 1 or not z0 <= z <= z1 or e not in prim:
            continue
        d = np.array([float(x) for x in r[9:12]])
        d = d / np.linalg.norm(d)
        if d[2] >= 0:
            continue
        en = float(r[5])
        s_out = math.hypot(d[0], d[1])
        sa, sf = s_out / float(np.interp(en, ea, na)), s_out / float(np.interp(en, ef, nf))
        if not (sa < 1 and sf < 1):
            continue
        u = d[:2] / s_out if s_out > 0 else np.zeros(2)
        lateral = (z - z0) * sa / math.sqrt(1 - sa * sa) + f * sf / math.sqrt(1 - sf * sf) + h * s_out / abs(d[2])
        hit = np.array([float(r[6]), float(r[7])]) + lateral * u
        p0, pd = prim[e]
        cross = p0[:2] + (0.0 - p0[2]) * pd[:2] / pd[2] if abs(pd[2]) > 0 else p0[:2]
        per.setdefault(e, []).append(float(np.linalg.norm(hit - cross)))
    return np.array([np.median(per[e]) if e in per else np.nan for e in range(first, first + n)])


def rich_reduce(root: Path) -> dict:
    """Per RICH run (told), the per-event plane radii -> {name: {theta, sample, role, mean, s2, n, influence}}."""
    man = load_manifest(root)
    out = {}
    for row in man["runs"]:
        if row["campaign"] != RICH:
            continue
        b = told_batch(root, RICH, row["name"])
        det = json.loads((root / RICH / "cards" / row["name"] / "detector.json").read_text())
        x = plane_radius(b, det)
        ok = np.isfinite(x)
        m = float(np.mean(x[ok])) if ok.any() else float("nan")
        s2 = float(np.var(x[ok], ddof=1)) if ok.sum() > 1 else float("nan")
        infl = np.where(ok, (np.nan_to_num(x) - m) / max(int(ok.sum()), 1), 0.0)
        out[row["name"]] = {"theta": row["theta"], "sample": row["sample"], "role": row["role"], "mean": m, "s2": s2,
                            "n": int(ok.sum()), "events": int(row["events"]), "influence": infl.tolist()}
    return out


class RichRunsEvaluator:
    """Section 7.1 over the reduced RICH products: at a told design point, per sample the mean plane radius, V_MC =
    s2 / n, s2, the per-event influence (for P6's paired sigma_Delta); ask/tell as toy.ChainEvaluator."""

    def __init__(self, reduced: dict, samples):
        self.samples = [s["name"] for s in samples]
        self.parameters = ["height_mm", "index_scale"]
        self.by: dict = {}
        for rec in reduced.values():
            if rec["sample"] in self.samples:
                self.by.setdefault(self._key(rec["theta"]), {})[rec["sample"]] = rec
        self._asked: dict = {}

    @staticmethod
    def _key(theta):
        return (round(float(theta["height_mm"]), 9), round(float(theta["index_scale"]), 12))

    def default_method(self, par: str) -> str:
        return "resimulation"

    def evaluate(self, theta: dict, phi=None, psi=None, model: str = "nominal", effects_off=(), seeds=None,
                 names=None) -> dict:
        recs = self.by.get(self._key(theta))
        if recs is None or any(s not in recs for s in self.samples):
            raise E.ResimulationRequired(f"no told RICH run at {theta}")
        nm = [s for s in self.samples if names is None or s in names]
        pred = np.array([recs[s]["mean"] for s in nm])
        s2 = np.array([recs[s]["s2"] for s in nm])
        n = np.array([recs[s]["n"] for s in nm], float)
        infl = {s: {j: (np.asarray(recs[s]["influence"]), 1.0)} for j, s in enumerate(nm)}
        return {"names": nm, "pred": pred, "V_MC": np.diag(s2 / n), "s2": np.diag(s2), "runs": nm,
                "n_eff": n, "missing_support_runs": [], "flags": [LABEL], "V_emu": None, "V_learn": None,
                "theta": dict(theta), "influence": infl}

    def ask(self, requests: list) -> list:
        for q in requests:
            self._asked[q["run_id"]] = self.evaluate(q["theta"], names=q.get("names"))
        return [q["run_id"] for q in requests]

    def tell(self, run_ids=None) -> dict:
        ids = list(self._asked) if run_ids is None else list(run_ids)
        return {r: self._asked.pop(r) for r in ids if r in self._asked}


class SurrogateEvaluator:
    """The surrogate trained on the 24 design points as a section 7.1 evaluator over the design box: pred, V_MC + V_emu,
    s2 interpolated with the same weights; OutsideDomain outside the box."""

    def __init__(self, sur, s2_design):
        self.sur, self.s2 = sur, np.asarray(s2_design, float)
        self.parameters = list(sur.parameters)
        self.samples = list(sur.names)

    def default_method(self, par: str) -> str:
        return "surrogate-model"

    def evaluate(self, theta: dict, phi=None, psi=None, model: str = "nominal", effects_off=(), seeds=None,
                 names=None) -> dict:
        pr = self.sur.predict({p: float(theta[p]) for p in self.parameters})
        idx = [j for j, s in enumerate(self.samples) if names is None or s in names]
        s2 = np.maximum(pr["weights"] @ self.s2, 0.0)[idx]
        V = (pr["V_MC"] + pr["V_emu"])[np.ix_(idx, idx)]
        nm = [self.samples[j] for j in idx]
        return {"names": nm, "pred": pr["pred"][idx], "V_MC": V, "s2": np.diag(s2), "runs": nm,
                "n_eff": np.full(len(idx), np.inf), "missing_support_runs": [], "flags": [LABEL, "surrogate"],
                "V_emu": pr["V_emu"][np.ix_(idx, idx)], "V_learn": None, "theta": dict(theta)}


def train(reduced: dict, samples) -> dict:
    """The surrogate on the training points (emulator.training_set through ask/tell) and P6 on the held-back points."""
    contract, plan = rich_contract(samples), rich_plan()
    ev = RichRunsEvaluator(reduced, samples)
    tr = emulator.training_set(ev, contract, plan, names=[s["name"] for s in samples])
    if tr["status"] != "ok":
        return {"status": "incomplete", "outstanding": tr.get("outstanding")}
    s2 = np.array([[np.diag(e["_raw"]["s2"])[j] for j in range(len(samples))] for e in tr["state"]["entries"]])
    p6 = emulator.p6_from_evaluator(ev, contract, plan, names=[s["name"] for s in samples], trained=tr)
    return {"status": "ok", "surrogate": tr["surrogate"], "s2": s2, "p6": p6, "contract": contract}


class SurrogateProblem(EP.EvaluatorProblem):
    """EvaluatorProblem over the surrogate with the analytic Jacobian of the kriging weights (H, read by fit.jacobian):
    no finite-difference probe leaves the design box, outside which the surrogate is never queried (section 6.4); the
    fits are bounded by the box (physical bounds = sampling bounds, `surrogate_contract`)."""

    def H(self, tp) -> np.ndarray:
        sev = self.evaluator
        theta = {n: float(v) for n, v in zip(self.theta_names, np.asarray(tp, float))}
        pred = np.asarray(self._evaluate(tp)["pred"], float)
        g = linear.to_link_delta(pred, self.links)
        idx = [sev.samples.index(n) for n in self.names]
        cols = [g * (sev.sur.weight_derivatives(theta, p)[0] @ sev.sur.values)[idx] for p in self.theta_names]
        return np.stack(cols, axis=1)

    def with_data(self, observed: L.Observations):
        p = SurrogateProblem(self.evaluator, self.contract, self.plan, self.seeds, self.degeneracy_modes,
                             self._fd_fraction)
        p.observed, p.truth = observed, self.truth
        return p


FD_FRACTION = 0.005      # the problem's finite-difference step, in units of the prior width


def surrogate_contract(contract: dict) -> dict:
    """The fit bounds inside the design box by one finite-difference step (fit.minimize differences h centrally, and
    the surrogate is never queried outside its domain); the prior (sampling bounds) stays the design box."""
    c = copy.deepcopy(contract)
    for q in c["parameters"]:
        lo, hi = map(float, q["sampling_bounds"])
        s = 1.001 * FD_FRACTION * (hi - lo)
        q["physical_bounds"] = [lo + s, hi - s]
    return c


def _problem(sev, contract, truth=None, seed=None):
    contract = surrogate_contract(contract)
    p = SurrogateProblem(sev, contract, degeneracy_modes=[C.MODE], fd_fraction=FD_FRACTION)
    centre = {q["name"]: 0.5 * sum(q["sampling_bounds"]) for q in contract["parameters"]}
    if seed is None:
        p.observed = L.Observations(y_gauss=p.h(p.beta(centre if truth is None else truth)))
    else:
        p.observed = p.simulate(p.beta(truth), np.random.default_rng(seed))
    return p, centre


def _nominal_beta(p, centre):
    lk = L.Likelihood(p.layout, p.observed, p.reference(p.beta(centre), None))
    return lk.initial_beta(centre)


def surrogates(reduced: dict) -> dict:
    """The two-beta and the single-beta (R_p100) surrogates."""
    return {"two-beta": train(reduced, RICH_SAMPLES), "single-beta": train(reduced, RICH_SAMPLES[:1])}


def ev_rich_p3_p6(root: Path, reduced: dict | None = None) -> dict:
    """Section 15.2 RICH replica (test_with_geant4 of P3MultipleBeta): P3 at the prior centre (Asimov) on the surrogate
    of the 64 runs: with R_p100 alone the index and the height are not identifiable (p3.not_identifiable with the
    `multiple beta` hint), with R_p100 and R_p2.4 P3 passes. P6 of each surrogate on its 8 held-back points.
    Rule: single-beta P3 fails with the hint, two-beta P3 passes (section 15.2); P6 (section 8.2 note 4)."""
    reduced = reduced if reduced is not None else rich_reduce(root)
    tr = surrogates(reduced)
    out = {"item": "rich-p3-p6", "flags": [PROVISIONAL, LABEL]}
    for k, t in tr.items():
        if t["status"] != "ok":
            out[k] = {"status": "incomplete", "outstanding": t.get("outstanding")}
            continue
        sev = SurrogateEvaluator(t["surrogate"], t["s2"])
        p, centre = _problem(sev, t["contract"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = identify.p3(p, _nominal_beta(p, centre))
        out[k] = {"p3": r, "p6": t["p6"], "surrogate": t["surrogate"].record()}
    ok = all(isinstance(out.get(k), dict) and "p3" in out[k] for k in tr)
    single_hint = ok and out["single-beta"]["p3"]["status"] == "failed" and \
        out["single-beta"]["p3"].get("finding") == "p3.not_identifiable" and \
        any("multiple beta" in h.get("signal", "") for h in out["single-beta"]["p3"].get("hints", []))
    out["p3_passed"] = bool(ok and single_hint and out["two-beta"]["p3"]["status"] == "passed")
    out["p6_passed"] = bool(ok and all(out[k]["p6"].get("status") == "passed" for k in tr))
    out["passed"] = out["p3_passed"] and out["p6_passed"]
    return out


def ev_rich_note6(root: Path, config: str, chunk: int, per: int = NOTE6_PER_TASK, n_reseed: int = NOTE6_RESEED,
                  reduced: dict | None = None) -> dict:
    """Section 8.7 note 6 for the RICH replica (test_note_6_calibration): toys j in [chunk per, (chunk + 1) per) of
    pseudo-data at TRUTH from the surrogate (`gaussian-summary`), each classified under n_reseed reseedings of the
    section 7.4 starts (cherenkov_standin.reseeding_stability on the surrogate problem)."""
    reduced = reduced if reduced is not None else _cached_reduce(root)
    t = train(reduced, RICH_SAMPLES if config == "two-beta" else RICH_SAMPLES[:1])
    if t["status"] != "ok":
        return {"item": "rich-note6", "config": config, "chunk": chunk, "status": "incomplete"}
    sev = SurrogateEvaluator(t["surrogate"], t["s2"])
    j0 = chunk * per

    def toy(j):
        return _problem(sev, t["contract"], TRUTH, seed=(9, j0 + j))[0]

    def beta0(p):
        return _nominal_beta(p, {q["name"]: 0.5 * sum(q["sampling_bounds"]) for q in t["contract"]["parameters"]})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = C.reseeding_stability(toy, per, n_reseed, beta0, seed=1_100_000 + chunk)
    r["label"] = LABEL
    return {"item": "rich-note6", "config": config, "chunk": chunk, "first_toy": j0, "result": r}


def _cached_reduce(root: Path) -> dict:
    """The reduction written by the rich-p3-p6 task (rich-reduced.json beside tell.json), else computed here."""
    f = root / RICH / "rich-reduced.json"
    if f.exists():
        return json.loads(f.read_text())
    red = rich_reduce(root)
    return red


# ------------------------------------------------------------------ the evidence array, merge and decisions
def evidence_tasks(toys: int = NOTE6_TOYS, per: int = NOTE6_PER_TASK) -> list:
    t = [{"item": "zdc-p0-response"}, {"item": "zdc-birks-rerun"}, {"item": "zdc-p0-birks"}, {"item": "rich-p3-p6"}]
    for cfg in ("two-beta", "single-beta"):
        t += [{"item": "rich-note6", "config": cfg, "chunk": c, "per": per, "after": "rich-p3-p6"}
              for c in range(toys // per)]
    return [dict(x, task=k) for k, x in enumerate(t)]


def run_evidence(k: int, root: Path, out: Path, tasks=None, n_reseed: int = NOTE6_RESEED) -> dict:
    task = (tasks or evidence_tasks())[k]
    t0 = time.process_time()
    it = task["item"]
    if it == "zdc-p0-response":
        r = ev_calo_p0_response(root)
    elif it == "zdc-birks-rerun":
        r = ev_calo_birks_rerun(root)
    elif it == "zdc-p0-birks":
        r = ev_calo_p0_birks(root)
    elif it == "rich-p3-p6":
        red = rich_reduce(root)
        _write(root / RICH / "rich-reduced.json", red)
        r = ev_rich_p3_p6(root, red)
    else:
        r = ev_rich_note6(root, task["config"], task["chunk"], task["per"], n_reseed)
    rec = {"task": k, **task, "record": r, "cpu_seconds": round(time.process_time() - t0, 1),
           "provenance": provenance(), "tell_sha256": _sha(root / "tell.json") if (root / "tell.json").exists()
           else None, "label": LABEL}
    _write(out / f"evidence_{k:04d}.json", rec)
    return rec


def judge_note6(chunks: list, toys: int = NOTE6_TOYS, reseed: int = NOTE6_RESEED) -> dict:
    """Section 8.7 note 6 (phase 3, RICH replica): the classification unchanged under 10 reseedings in >= 99% of
    >= 10^3 toys."""
    n = sum(c["result"]["toys"] for c in chunks if "result" in c)
    same = sum(c["result"]["unchanged"] for c in chunks if "result" in c)
    rs = {c["result"]["reseedings"] for c in chunks if "result" in c}
    kinds: dict = {}
    for c in chunks:
        for kk, v in (c.get("result") or {}).get("kinds", {}).items():
            kinds[kk] = kinds.get(kk, 0) + v
    frac = same / n if n else None
    complete = n >= toys and rs == {reseed}
    return {"toys": n, "unchanged": same, "fraction": frac, "reseedings": sorted(rs), "kinds": kinds,
            "complete": complete, "passed": bool(complete and frac is not None and frac >= 0.99),
            "rule": ">= 0.99 of >= 1000 toys unchanged under 10 reseedings (section 8.7 note 6)", "flags": [PROVISIONAL]}


def merge(out_dir: Path, out: Path, tasks=None, toys: int = NOTE6_TOYS, reseed: int = NOTE6_RESEED) -> dict:
    tasks = tasks or evidence_tasks()
    recs = {}
    for t in tasks:
        f = out_dir / f"evidence_{t['task']:04d}.json"
        recs[t["task"]] = json.loads(f.read_text()) if f.exists() else None
    missing = [k for k, v in recs.items() if v is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    tells = {r.get("tell_sha256") for r in recs.values() if r}
    results, n6 = {}, {}
    for r in recs.values():
        if not r:
            continue
        if r["item"] == "rich-note6":
            n6.setdefault(r["config"], []).append(r["record"])
        else:
            results[r["item"]] = r["record"]
    for cfg, chunks in n6.items():
        results[f"rich-note6/{cfg}"] = judge_note6(chunks, toys, reseed)
    passed = {k: bool(v.get("passed")) for k, v in results.items()}
    complete = not missing and len(commits) == 1 and not dirty and len(tells) == 1
    rep = {"array": "simcal phase 3 Geant4 evidence (WP-I): section 15.2 synthetic ZDC and RICH replica, P0 (k_B), "
           "P3, P6, section 8.7 note 6", "complete": complete, "missing_tasks": missing, "commits": sorted(
               c for c in commits if c), "dirty": dirty, "tell_sha256": sorted(t for t in tells if t),
           "results": results, "passed": passed, "failed": sorted(k for k, v in passed.items() if not v),
           "provenance": provenance(), "label": LABEL, "flags": [PROVISIONAL]}
    _write(out, rep)
    return rep


# ------------------------------------------------------------------ --local: the path on STAND-IN products
def _write_csv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)


def standin_calo_products(work: Path, row: dict, wrong_birks: float | None = None) -> None:
    """g4sim-layout products of the ZDC fixture's synthetic transport stand-in (calibration_zdc_fixture.products) at the
    run's k_B and yield, with the edep_visible scorer's rows; `wrong_birks` makes a mislabelled run (a control)."""
    th = row["theta"]
    kb = wrong_birks if wrong_birks is not None else th.get("birks", Z.BIRKS0)
    p = Z.products(int(row["logical_run_seed"]) % 100000, row["first_event"], row["events"], birks=kb,
                   light_yield=th.get("light_yield", Z.LIGHT_YIELD0))
    cells = [list(r) for r in p["cells"]] + [[e, VISIBLE, v, 0, s, 1, s] for (e, v), s in sorted(p["edep_visible"].items())]
    _write_csv(work / "cells.csv", cells)
    _write_csv(work / "primaries.csv", p["primaries"])
    _write(work / "summary.json", {"status": "ok", "geometry_id": "standin", "request_id": "standin",
                                   "label": Z.LABEL})


def standin_rich_products(work: Path, row: dict, detector: dict, photons_per_event: float = 12.0) -> None:
    """g4sim-layout products of an analytic Cherenkov emission through the run's planar layers (photons.csv rows with the
    emission point and the arrival direction), labelled `analytic-stand-in`: tests plane_radius and the RICH path."""
    smp = next(s for s in RICH_SAMPLES if s["name"] == row["sample"])
    beta = smp["beta"]
    prm = detector["params"]
    h, f, t = (float(prm[k]) for k in ("height_mm", "foil_mm", "aero_mm"))
    ea, na = _rindex(detector, "aerogel")
    ef, nf = _rindex(detector, "foil_pmma")
    prim, ph = [], []
    for e in range(row["first_event"], row["first_event"] + row["events"]):
        g = np.random.default_rng([int(row["logical_run_seed"]), e])
        prim.append([e, 1000.0 * smp["kinetic_per_nucleon_GeV"], 226.0, 0.0, 530.0, 0.0, 0.0, -1.0])
        for _ in range(g.poisson(photons_per_event)):
            en = g.uniform(2.0, 4.0)
            n_a = float(np.interp(en, ea, na))
            c = 1.0 / (n_a * beta)
            if c >= 1:
                continue
            s_out = n_a * math.sqrt(1 - c * c)
            if s_out >= 1 or s_out / float(np.interp(en, ef, nf)) >= 1:
                continue
            z = g.uniform(h + f, h + f + t)
            phi = g.uniform(0, 2 * math.pi)
            d = [s_out * math.cos(phi), s_out * math.sin(phi), -math.sqrt(1 - s_out * s_out)]
            ph.append([e, "plane", 3, 0.0, 0.0, en, 226.0, 0.0, z, *d, 1])
    _write_csv(work / "primaries.csv", prim)
    _write_csv(work / "photons.csv", ph)
    _write_csv(work / "cells.csv", [])
    _write(work / "summary.json", {"status": "ok", "geometry_id": "standin", "request_id": "standin",
                                   "label": C.LABEL})


def smoke(out: Path, wrong: tuple | None = None, toys: int = 2, reseed: int = 2, rich: bool | None = None,
          calo_events: int = 120, rich_events: int = 40) -> dict:
    """The production path at tiny sizes on stand-in products (never evidence): cards (check-spec on two cards),
    products, tell, the section 6.6 check, every evidence item (note 6 at `toys` x `reseed`), merge. `wrong` = (run,
    k_B): that run's products are made at another k_B than its card's (a mislabelled run, a control)."""
    root = out / "root"
    if root.exists():
        shutil.rmtree(root)
    rich = R.AVAILABLE if rich is None else rich
    man = write_cards(root, calo_events, rich_events, check=False, rich=rich)
    checked = {}
    for row in [man["runs"][0]] + ([man["runs"][-1]] if rich else []):   # the full preflight on one card per campaign
        docs = {k: json.loads((root / row["campaign"] / "cards" / row["name"] / f"{k}.json").read_text())
                for k in ("detector", "request", "run")}
        checked[row["name"]] = preflight({**row, "documents": docs}, root / row["campaign"] / "cards" / row["name"])
    for row in man["runs"]:
        work = root / row["campaign"] / "runs" / row["name"]
        if row["campaign"] == CALO:
            standin_calo_products(work, row, wrong[1] if wrong and row["name"] == wrong[0] else None)
        else:
            det = json.loads((root / RICH / "cards" / row["name"] / "detector.json").read_text())
            standin_rich_products(work, row, det)
    told = tell_all(root, build_hash="standin")
    tasks = evidence_tasks(toys, 1) if rich else evidence_tasks(0, 1)[:3]
    if not rich:
        tasks = tasks[:3]
    t0 = time.process_time()
    for t in tasks:
        run_evidence(t["task"], root, out / "evidence", tasks, n_reseed=reseed)
    rep = merge(out / "evidence", out / "merged.json", tasks, toys, reseed)
    return {"tell": told["status"], "interval_findings": told["interval_check"]["findings"], "preflight": checked,
            "merged": rep, "evidence_cpu_seconds": round(time.process_time() - t0, 1)}


# ------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cards")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--tell")
    ap.add_argument("--evidence-list", action="store_true")
    ap.add_argument("--evidence", type=int)
    ap.add_argument("--root")
    ap.add_argument("--merge")
    ap.add_argument("--local", dest="smoke", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cards:
        m = write_cards(Path(a.cards))
        print(json.dumps({"runs": len(m["runs"]), "problems": m["problems"], "manifest_sha256": m["manifest_sha256"]}))
        return 1 if m["problems"] else 0
    if a.list:
        print(json.dumps(geant4_tasks(Path(a.root) if a.root else None), indent=0))
        return 0
    if a.task is not None:
        r = run_geant4_task(a.task, Path(a.out or OUT_ROOT))
        print(json.dumps({k: r.get(k) for k in ("task", "name", "status", "exit", "cpu_seconds", "problems")}))
        return 0 if r["status"] == "ok" else 1
    if a.tell:
        r = tell_all(Path(a.tell))
        print(json.dumps({"status": r["status"], "told": len(r["told"]), "missing": len(r["missing"]),
                          "refused": r["refused"], "findings": r["interval_check"]["findings"]}))
        return {"passed": 0, "failed": 1}.get(r["status"], 3)
    if a.evidence_list:
        print(json.dumps(evidence_tasks(), indent=0))
        return 0
    if a.evidence is not None:
        r = run_evidence(a.evidence, Path(a.root or OUT_ROOT), Path(a.out))
        print(json.dumps({"task": r["task"], "item": r["item"], "cpu_seconds": r["cpu_seconds"]}))
        return 0
    if a.merge:
        r = merge(Path(a.merge), Path(a.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if a.smoke:
        r = smoke(Path(a.out))
        print(json.dumps({"tell": r["tell"], "passed": r["merged"]["passed"], "cpu": r["evidence_cpu_seconds"]}))
        return 0
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())

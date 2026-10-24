#!/usr/bin/env python3
"""Journey J14 (detector simulation study with independent-reference benchmarks): energy loss in 300 um of silicon.

ILLUSTRATIVE. Two studies with Geant4 11.4.3 through adapters/geant4 and hep-detector's Geant4 study tools; names no
experiment. Every Geant4 run record is `unvalidated`; the final products are the two study records, each written
`unvalidated` and re-issued as `validated-in-scope` for its benchmarked scope (phase 2, contracts 3.1.0: the run
records become evidence records referenced by hash; the coarse-cut scenario's upgrade is refused).
- study-mpv.json: most probable energy loss of 10 GeV mu- (thin-layer-mpv reference benchmark against the PDG
  Landau-Vavilov Delta_p, thin-layer-width sanity), cut scan 0.1/0.03/0.01 mm, variations EM option 0 and 3, PAI, and
  FTFP_BERT_EMZ (same EM model: must be excluded from the systematic list).
- study-sp.json: mean stopping power of 100 MeV protons (stopping-power reference benchmark against Bethe), cut scan,
  variations EM option 0 and 3.
Reference inputs (density, Z/A, I, Sternheimer parameters) come from the PDG silicon tables (refdata/), never from the
Geant4 material dump. Negative controls (A1.10): each reference benchmark reruns on Geant4 runs whose silicon density
is raised and lowered by the claimed detection limit (the reference keeps 2.329 g/cm3); each must fail, and its
shift of the observable must sit at the detection limit.
Statistics (contracts CV-A1, Geant4 program A1.5-A1.9): every run is one logical run with seed S = H(study_id, role,
point_id) (core/simulation/seeds.py) and is summarised in K = 16 blocks (simulation-summary/1, recorded/blocks/,
written by adapters/geant4/assets/summary_from_csv.py with the study spec's observables); each point with an se target
(the scan points, the nominal) first gets a trial run of N_TRIAL events, and its event count is N = N_trial
(SE_trial / target)^2 F_0.95(15, 15), rounded up to a multiple of K; a point that then misses its target is incomplete
and is never topped up. Three stopping-power runs (sp-nominal, sp-control, sp-density-10) were not re-recorded: their
blocks are cut from the recorded per-event CSVs, and they keep their legacy seed pairs.
Negative-control scenarios, each written as a study record that lists its gaps:
  coarse-cut      the MPV study with a scan of 1.0 and 0.3 mm only: stopped by the convergence gate;
  density-10      the stopping-power benchmark on a run with the silicon density 10 % too high: caught;
  dump-reference  reference inputs taken from the Geant4 material dump: flagged as a gap.

Modes:
  offline replay (default): recomputes the spec checks, convergence gate, benchmarks, variations, study records,
    literature record, report and checks from recorded/ and writes them to --out (default output/); the result is
    byte-identical to the committed output/ (tests/examples/test_geant4_thin_silicon.py).
  live (--live, needs HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG naming a JSON {"build_record", "layered_sim"}):
    runs every Geant4 run in --work (outside the plugin): trial runs first, then the evidence runs with the planned
    event counts, then the controls at the planned detection limits; rewrites --recorded (default recorded/: run
    records with ~ paths, block summaries, effective specs, the build record, plan.json) and replays. Per-event CSVs
    are not committed, except the first 5000 events of mpv-nominal (the response check) and the three legacy runs.
Usage (from the plugin root): python3 examples/geant4-thin-silicon/run.py [--out DIR] [--recorded DIR]
       HEP_GEANT4_LIVE_TEST=1 HEP_GEANT4_CONFIG=cfg.json python3 examples/geant4-thin-silicon/run.py --live --work DIR [--recorded DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))
from core.simulation.seeds import H, job_seeds  # noqa: E402
from core.stats.distributions import f_ppf  # noqa: E402

RUN = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_run.py"
SUMMARY = PLUGIN / "adapters" / "geant4" / "assets" / "summary_from_csv.py"
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
BENCH = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"
LIT = PLUGIN / "skills" / "hep-citations" / "scripts" / "manage_literature.py"
CITES = PLUGIN / "skills" / "hep-authoring" / "scripts" / "check_citations.py"
VALIDATE = PLUGIN / "contracts" / "validate.py"
DEPS = PLUGIN / "contracts" / "dependencies.py"
DETR = PLUGIN / "skills" / "hep-detector" / "scripts" / "build_response.py"
RESP = PLUGIN / "contracts" / "response_adapter.py"
CREATED = "2026-10-24"
REDUCED = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process"]
LABEL = "ILLUSTRATIVE (journey J14): Geant4 outputs are unvalidated; names no experiment"
K = 16
F_TWO_STAGE = f_ppf(0.95, K - 1, K - 1)  # A1.9 with the maintainer's choice F_0.95 (about 2.40)
N_TRIAL = {"mpv": 64000, "sp": 16000}
# A1.7 design (bias toys, Moyal with 1.5 xi checked against the recorded 60k-event histogram; VALIDATION
# GEANT4-CORRECTNESS): with 2 keV bins the mean of block modes has a 95 % upper bias bound <= tol/10 = 0.002 only from
# B = 30000 events per block, so every point of the MPV study has at least K x 30000 events
MIN_BLOCK_EVENTS = {"mpv": 30000, "sp": 1}
CUTS = (0.1, 0.03)
COARSE = (1.0, 0.3)
BASE = {"mpv": "mpv-mu10GeV.json", "sp": "sp-p100MeV.json"}
STUDY_ID = {"mpv": "j14-mpv-mu10gev-si300um", "sp": "j14-sp-p100mev-si300um"}
LEGACY = {"sp-nominal": [1402, 1], "sp-control": [1402, 50], "sp-density-10": [1402, 40]}  # not re-recorded
RESPONSE_EVENTS = 5000


def run_table() -> dict[str, dict]:
    """run id -> study, evidence role, point id, spec changes (dotted keys), whether it gets a trial run."""
    t = {}
    for study in ("mpv", "sp"):
        t[f"{study}-nominal"] = {"study": study, "role": "nominal", "point": "cut-0.01", "set": {}, "trial": True}
        for cut in CUTS + (COARSE if study == "mpv" else ()):
            t[f"{study}-cut-{cut}"] = {"study": study, "role": "scan", "point": f"cut-{cut}", "trial": True,
                                       "set": {"physics.default_cut_mm": cut, "physics.regions.0.cut_mm": cut}}
        for name, em in (("em-option0", "G4EmStandardPhysics"), ("em-option3", "G4EmStandardPhysics_option3")):
            t[f"{study}-{name}"] = {"study": study, "role": "variation", "point": name, "trial": False,
                                    "set": {"physics.em_constructor": em}}
    t["sp-density-10"] = {"study": "sp", "role": "control", "point": "density-10", "trial": False,
                          "set": {"materials.0.density_g_cm3": round(2.329 * 1.10, 6)}}
    t["mpv-pai"] = {"study": "mpv", "role": "variation", "point": "pai", "trial": False,
                    "set": {"ui_commands": ["/process/em/AddPAIRegion all SiRegion PAI"]}}
    t["mpv-ftfp-bert-emz"] = {"study": "mpv", "role": "variation", "point": "ftfp-bert-emz", "trial": False,
                              "set": {"physics.reference_list": "FTFP_BERT_EMZ", "physics.em_constructor": None}}
    for rid in LEGACY:
        t.setdefault(rid, {"study": "sp", "role": "control", "point": rid[3:], "set": {}, "trial": False})
        t[rid].update(legacy=True, trial=False)
    t["sp-nominal"]["role"] = "nominal"
    return t


def set_key(doc: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    for k in keys[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    last = keys[-1]
    if value is None:
        doc.pop(last, None)
    elif isinstance(doc, list):
        doc[int(last)] = value
    else:
        doc[last] = value


CWD = [HERE]  # working folder of the tool calls: the example, or the replay's staging copy


def call(script: Path, *args, cwd: Path | None = None, ok=(0,)) -> tuple[int, dict]:
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       cwd=cwd or CWD[0], timeout=7200)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"raw": p.stdout[-800:], "stderr": p.stderr[-800:]}
    if p.returncode not in ok:
        raise RuntimeError(f"{script.name} {' '.join(map(str, args))} exited {p.returncode}: {json.dumps(out)[:800]}")
    return p.returncode, out


def write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def study_spec(study: str) -> dict:
    return json.loads((HERE / f"study-{study}.json").read_text(encoding="utf-8"))


def se_targets(study: str, role: str) -> dict:
    """The relative se targets of a point (A1.8, A1.9): tol / (4 sqrt 2) for each convergence observable on scan and
    nominal points, and the statistical target on the nominal."""
    s = study_spec(study)
    tol = s["convergence_plan"]["tolerance_relative"]
    out = {o: tol[o] / (4 * math.sqrt(2)) for o in s["convergence_plan"]["observables"]}
    if role == "nominal":
        st = s["statistical_target"]
        out[st["observable"]] = min(out.get(st["observable"], math.inf), st["relative_se"])
    return out


def planned_events(trial: dict, study: str, role: str, n_trial: int) -> dict:
    """A1.9: N = N_trial (SE_trial / target)^2 F_0.95(K - 1, K_trial - 1), the largest over the point's targets,
    rounded up to a multiple of K (never below N_trial)."""
    need = {}
    for o, target in se_targets(study, role).items():
        e = trial["observables"][o]
        rel = e["se"] / abs(e["value"])
        need[o] = n_trial * (rel / target) ** 2 * F_TWO_STAGE
    n = max(n_trial, K * MIN_BLOCK_EVENTS[study], math.ceil(max(need.values()) / K) * K)
    return {"events": n, "per_observable": need, "factor": F_TWO_STAGE, "trial_events": n_trial,
            "min_block_events": MIN_BLOCK_EVENTS[study]}


# --------------------------------------------------------------------------------------------------------- live
def live(work: Path, rec_dir: Path) -> None:
    if os.environ.get("HEP_GEANT4_LIVE_TEST") != "1" or not os.environ.get("HEP_GEANT4_CONFIG"):
        raise SystemExit("--live needs HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG")
    cfg = json.loads(Path(os.path.expanduser(os.environ["HEP_GEANT4_CONFIG"])).read_text(encoding="utf-8"))
    build, exe = os.path.expanduser(cfg["build_record"]), os.path.expanduser(cfg["layered_sim"])
    keep = {name: (rec_dir / "runs" / f"{name}.computational-run.json").read_bytes() for name in LEGACY}
    keep_csv = {name: (rec_dir / "events" / f"{name}.csv.gz").read_bytes() for name in LEGACY}
    keep_specs = {name: (rec_dir / "specs" / f"{name}.json").read_bytes() for name in LEGACY}
    old_control = json.loads((rec_dir / "control-sp.json").read_text(encoding="utf-8"))
    legacy_control = {"injected_relative": old_control.get("injected_relative"),
                      "injected": old_control.get("injected")}
    if rec_dir.exists():
        shutil.rmtree(rec_dir)
    (rec_dir / "build").mkdir(parents=True)
    shutil.copyfile(build, rec_dir / "build" / "geant4-build.computational-run.json")
    for name in LEGACY:
        for sub, data, ext in (("runs", keep, ".computational-run.json"), ("events", keep_csv, ".csv.gz"),
                               ("specs", keep_specs, ".json")):
            (rec_dir / sub).mkdir(parents=True, exist_ok=True)
            (rec_dir / sub / f"{name}{ext}").write_bytes(data[name])
    table = run_table()
    plan: dict = {"factor": F_TWO_STAGE, "K": K, "runs": {}}

    def nominal_events(study: str) -> int:
        row = table[f"{study}-nominal"]
        if row.get("legacy"):
            return json.loads(keep[f"{study}-nominal"])["extension"]["simulation"]["events"]
        return row["events"]["events"]

    def spec_for(row: dict, events: int, s: int) -> dict:
        spec = json.loads((HERE / "specs" / BASE[row["study"]]).read_text(encoding="utf-8"))
        spec["run"]["events"], spec["run"]["seeds"] = events, list(job_seeds(s, 0))
        for k, v in row["set"].items():
            set_key(spec, k, v)
        return spec

    def summarise(rid: str, csv: Path, rec: Path, study: str, role: str, events: int, s: int | None) -> dict:
        out = rec_dir / "blocks" / f"{rid}.json"
        args = ["--csv", csv, "--observables", HERE / f"study-{study}.json", "--block-size", events // K,
                "--blocks", K, "--run-record", rec, "--out", out, "--evidence-role", role]
        args += ["--logical-run-seed", s, "--seed-scheme", "hash-v1"] if s else ["--seed-scheme", "legacy"]
        call(SUMMARY, *args, cwd=PLUGIN)
        return json.loads(out.read_text(encoding="utf-8"))

    def one(rid: str, row: dict, role: str, point: str, events: int, keep_events: int = 0) -> Path:
        s = H(STUDY_ID[row["study"]], role, point)
        sp = rec_dir / "specs" / f"{rid}.json"
        write(sp, spec_for(row, events, s))
        rec = rec_dir / "runs" / f"{rid}.computational-run.json"
        call(RUN, "run", "--spec", sp, "--exe", exe, "--build-record", build, "--work", work, "--run-id", rid,
             "--record", rec, "--created", CREATED, "--evidence-role", role, "--point-id", point,
             "--logical-run-seed", s, cwd=PLUGIN)
        csv = work / rid / "events.csv"
        summarise(rid, csv, rec, row["study"], role, events, s)
        if keep_events:
            lines = csv.read_text(encoding="utf-8").splitlines()
            cols = lines[1].split(",")
            idx = [cols.index(c) for c in REDUCED]
            body = [",".join(ln.split(",")[i] for i in idx) for ln in lines[2:2 + keep_events]]
            (rec_dir / "events").mkdir(parents=True, exist_ok=True)
            (rec_dir / "events" / f"{rid}.csv.gz").write_bytes(gzip.compress(
                ("\n".join([lines[0], ",".join(REDUCED), *body]) + "\n").encode(), mtime=0))
        plan["runs"][rid] = {"role": role, "point_id": point, "logical_run_seed": s, "events": events}
        return rec

    # 1. trial runs, then the planned event counts (A1.9)
    for rid, row in table.items():
        if row.get("trial"):
            trial_rid = f"{rid}-trial"
            one(trial_rid, row, "trial", row["point"], N_TRIAL[row["study"]])
            _, tr = call(CHECK, "run", "--spec", HERE / f"study-{row['study']}.json", "--summary",
                         f"trial={rec_dir / 'blocks' / f'{trial_rid}.json'}", ok=(0, 1, 3), cwd=HERE)
            row["events"] = planned_events(tr["summaries"][0], row["study"], row["role"], N_TRIAL[row["study"]])
            plan["runs"][trial_rid]["plan_for"] = rid
            plan["runs"][trial_rid]["planned"] = row["events"]
    # 2. evidence runs (variations take the nominal's event count; legacy runs are only summarised)
    for rid, row in table.items():
        study = row["study"]
        if row.get("legacy"):
            n = json.loads(keep[rid])["extension"]["simulation"]["events"]
            csv = work / f"{rid}.csv"
            csv.parent.mkdir(parents=True, exist_ok=True)
            csv.write_bytes(gzip.decompress(keep_csv[rid]))
            summarise(rid, csv, rec_dir / "runs" / f"{rid}.computational-run.json", study, row["role"],
                      n - n % K, None)
            plan["runs"][rid] = {"role": row["role"], "point_id": row["point"], "legacy_seeds": LEGACY[rid],
                                 "events": n}
            continue
        n = nominal_events(study) if row["role"] == "variation" else row["events"]["events"]
        one(rid, row, row["role"], row["point"], n, RESPONSE_EVENTS if rid == "mpv-nominal" else 0)
    # 3. negative controls at the planned detection limit, both directions (A1.10)
    for study, bench in (("mpv", "thin-layer-mpv"), ("sp", "stopping-power")):
        cfg_path = rec_dir / f"dl-{study}.config.json"
        write(cfg_path, bench_config(study, rec_dir, nominal_only=True, root=rec_dir, study_dir=HERE))
        _, res = call(BENCH, "run", "--config", cfg_path, ok=(0, 1, 3))
        cfg_path.unlink()
        b = next(x for x in res["benchmarks"] if x["benchmark"] == bench)
        dl = b["negative_control"]["planned_detection_limit_relative"]
        inj = math.ceil(dl * 1000) / 1000
        n = nominal_events(study)
        controls = {}
        for sign, rid in ((+1, f"{study}-control"), (-1, f"{study}-control-minus")):
            if rid in LEGACY:  # recorded before CV-A1 at the then-claimed detection limit; kept, not re-recorded
                controls[rid] = dict(legacy_control)
                continue
            row = {"study": study, "set": {"materials.0.density_g_cm3": round(2.329 * (1 + sign * inj), 6)}}
            one(rid, row, "control", f"density-{'plus' if sign > 0 else 'minus'}", n)
            controls[rid] = {"injected_relative": sign * inj,
                             "injected": f"silicon density x {1 + sign * inj:.3f} on the Geant4 side (reference keeps "
                                         "2.329 g/cm3)"}
        write(rec_dir / f"control-{study}.json", {"planned_detection_limit_relative": dl, "controls": controls})
    write(rec_dir / "plan.json", plan)
    write(rec_dir / "live.json", {"created": CREATED, "runs": sorted(plan["runs"]), "work": str(work).replace(
        str(Path.home()), "~"), "hosts_contacted": [], "note": "Geant4 runs need no network; the build record lists "
                                                               "the hosts its build contacted"})


# ------------------------------------------------------------------------------------------------------- replay
def bench_config(study: str, rec_dir: Path, nominal_only=False, main="nominal", root: Path | None = None,
                 study_dir: Path | None = None) -> dict:
    root = root or HERE
    rel = os.path.relpath(rec_dir, root)
    spec_rel = os.path.relpath((study_dir or rec_dir.parent) / f"study-{study}.json", root)
    common = {"material": "Si_study", "slab": "Si", "thickness_mm": 0.3}
    out = []
    ctrl = None if nominal_only else json.loads((rec_dir / f"control-{study}.json").read_text(encoding="utf-8"))
    if study == "mpv":
        width = next(o for o in study_spec("mpv")["observables"] if o["name"] == "loss_transmitted_MeV")["bins"]["width"]
        b = {"benchmark": "thin-layer-mpv", "particle": "mu-", "energy_MeV": 10000.0, "observable": "loss_transmitted_MeV",
             "binning": {"bin_width_MeV": width}, "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3},
             **common}
        w = {"benchmark": "thin-layer-width", "particle": "mu-", "energy_MeV": 10000.0,
             "observable": "deposit_transmitted_MeV", **common}
        main_rows = [b, w]
    else:
        b = {"benchmark": "stopping-power", "particle": "proton", "energy_MeV": 100.0,
             "observable": "loss_transmitted_MeV", "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3},
             **common}
        main_rows = [b]
    for r in main_rows:
        r["summary"] = f"{rel}/blocks/{study}-{main}.json"
        r["run_record"] = f"{rel}/runs/{study}-{main}.computational-run.json"
        if ctrl and r["benchmark"] != "thin-layer-width":
            r["negative_controls"] = [{"summary": f"{rel}/blocks/{rid}.json",
                                       "run_record": f"{rel}/runs/{rid}.computational-run.json", **c}
                                      for rid, c in sorted(ctrl["controls"].items())]
        out.append(r)
    return {"schema": "geant4-benchmarks/1", "study_spec": spec_rel, "benchmarks": out}


def summaries(study: str, cuts) -> list[str]:
    args = ["--summary", f"nominal=recorded/blocks/{study}-nominal.json"]
    for c in cuts:
        args += ["--summary", f"scan=recorded/blocks/{study}-cut-{c}.json"]
    return args


INPUTS = ("study-mpv.json", "study-sp.json", "literature-input.json", "specs", "refdata", "recorded")


def replay(dest: Path, recorded: Path = HERE / "recorded") -> dict:
    """Replay in a staging copy of the example inputs, so every path written into the outputs is the same wherever
    --out is; the staged output/ is then copied to dest."""
    if not (recorded / "runs").is_dir():
        raise SystemExit("recorded/ is missing: run once with --live")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / HERE.name
        stage.mkdir()
        for name in INPUTS:
            src = recorded if name == "recorded" else HERE / name
            (shutil.copytree if src.is_dir() else shutil.copyfile)(src, stage / name)
        CWD[0] = stage
        try:
            results = _replay(stage)
        finally:
            CWD[0] = HERE
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(stage / "output", dest)
    return results


def _replay(here: Path) -> dict:
    rec = here / "recorded"
    out = here / "output"
    art = out / "artifacts"
    (art / "runs").mkdir(parents=True)
    for f in sorted((rec / "runs").glob("*.json")):
        shutil.copyfile(f, art / "runs" / f.name)
    o = "output"
    results, crit = {"label": LABEL, "studies": {}}, {}
    # the literature record first: the study specs name it (rule G4R-CITATION)
    call(LIT, "import", "literature-input.json", "--project-root", ".", "--out",
         f"{o}/artifacts/geant4.literature-record.json", "--today", CREATED, "--artifact-id", "j14-geant4-literature")
    variations = {"mpv": ["em-option0", "em-option3", "pai", "ftfp-bert-emz"], "sp": ["em-option0", "em-option3"]}
    for study in ("mpv", "sp"):
        _, spec = call(CHECK, "spec", "--spec", f"study-{study}.json")
        write(out / f"spec-check-{study}.json", spec)
        code, conv = call(CHECK, "run", "--spec", f"study-{study}.json", *summaries(study, CUTS), "--out",
                          f"{o}/convergence-{study}.json", ok=(0, 1))
        write(out / f"benchmarks-{study}.config.json", bench_config(study, rec, root=out))
        bcode, bench = call(BENCH, "run", "--config", f"{o}/benchmarks-{study}.config.json", "--out",
                            f"{o}/benchmarks-{study}.json", ok=(0, 1, 3))
        var_args = [a for v in variations[study] for a in ("--variation",
                                                         f"{v}=recorded/blocks/{study}-{v}.json")]
        call(CHECK, "variations", "--spec", f"study-{study}.json", "--nominal",
             f"recorded/blocks/{study}-nominal.json", *var_args, "--out", f"{o}/variations-{study}.json")
        runs = [f"{o}/artifacts/runs/{study}-{r}.computational-run.json"
                for r in ["nominal", "control", "control-minus", *[f"cut-{c}" for c in CUTS], *variations[study]]]
        _, lab = call(CHECK, "label", "--spec", f"study-{study}.json", "--benchmarks", f"{o}/benchmarks-{study}.json",
                      "--convergence", f"{o}/convergence-{study}.json", "--variations", f"{o}/variations-{study}.json",
                      *[a for r in runs for a in ("--run-record", r)], "--project-root", ".",
                      "--write", f"{o}/artifacts/{study}.study.computational-run.json", "--created", CREATED)
        _, up = call(CHECK, "label", "--spec", f"study-{study}.json", "--benchmarks", f"{o}/benchmarks-{study}.json",
                     "--convergence", f"{o}/convergence-{study}.json", "--variations", f"{o}/variations-{study}.json",
                     *[a for r in runs for a in ("--run-record", r)], "--project-root", ".", "--upgrade",
                     "--write", f"{o}/artifacts/{study}.study-validated.computational-run.json", "--created", CREATED)
        crit[f"{study}_reissued_validated_in_scope"] = up["labels"] == ["validated-in-scope"]
        results["studies"][study] = {"spec": spec["status"], "upgrade": up["upgrade"], "convergence_gate": conv["convergence"]["gate"],
                                     "statistical_target": conv["statistical_target"]["verdict"],
                                     "benchmarks": {b["benchmark"]: {"verdict": b["verdict"],
                                                                     "relative_difference": b.get("relative_difference"),
                                                                     "detection_limit": b.get("detection_limit_relative"),
                                                                     "negative_control": b.get("negative_control", {}).get("status"),
                                                                     "validation_evidence": b.get("validation_evidence")}
                                                    for b in bench["benchmarks"]},
                                     "labels": lab["labels"], "gaps": lab["gaps"],
                                     "phase2_eligible": [e["benchmark"] for e in lab["phase2_upgrade_eligible_scopes"]]}
        ref = "thin-layer-mpv" if study == "mpv" else "stopping-power"
        crit[f"{study}_spec_ok"] = spec["status"] == "ok"
        crit[f"{study}_convergence_gate_passes"] = conv["convergence"]["gate"] == "pass"
        crit[f"{study}_statistical_target_met"] = conv["statistical_target"]["verdict"] == "pass"
        crit[f"{study}_{ref}_passes"] = results["studies"][study]["benchmarks"][ref]["verdict"] == "pass"
        crit[f"{study}_{ref}_negative_control_caught"] = results["studies"][study]["benchmarks"][ref]["negative_control"] == "caught"
        crit[f"{study}_record_unvalidated"] = lab["labels"] == ["unvalidated"]
    vmpv = json.loads((out / "variations-mpv.json").read_text(encoding="utf-8"))
    crit["same_model_variation_excluded"] = [v["variation"] for v in vmpv["variations"] if not v["listed"]] == \
        ["ftfp-bert-emz"]
    # scenarios
    scen = out / "scenarios"
    coarse = json.loads((here / "study-mpv.json").read_text(encoding="utf-8"))
    coarse["study_id"] = "j14-scenario-coarse-cut"
    coarse["convergence_plan"]["parameters"][0]["values"] = list(COARSE)
    coarse["physics"]["layered_sim_spec"] = os.path.relpath(here / "recorded" / "specs" / "mpv-nominal.json", scen)
    coarse["citations"]["literature_record"] = "../artifacts/geant4.literature-record.json"
    write(scen / "coarse-cut.study.json", coarse)
    _, cc = call(CHECK, "run", "--spec", f"{o}/scenarios/coarse-cut.study.json", "--summary",
                 "scan=recorded/blocks/mpv-cut-1.0.json", "--summary", "scan=recorded/blocks/mpv-cut-0.3.json",
                 "--out", f"{o}/scenarios/coarse-cut.convergence.json", ok=(1,))
    _, lc = call(CHECK, "label", "--spec", f"{o}/scenarios/coarse-cut.study.json", "--benchmarks",
                 f"{o}/benchmarks-mpv.json", "--convergence", f"{o}/scenarios/coarse-cut.convergence.json",
                 "--variations", f"{o}/variations-mpv.json", "--project-root", ".", "--write",
                 f"{o}/artifacts/scenario-coarse-cut.study.computational-run.json", "--created", CREATED)
    crit["coarse_cut_stopped_by_gate"] = cc["convergence"]["gate"] == "fail" and any(
        "convergence gate not passed" in g for g in lc["gaps"])
    _, uc = call(CHECK, "label", "--spec", f"{o}/scenarios/coarse-cut.study.json", "--benchmarks",
                 f"{o}/benchmarks-mpv.json", "--convergence", f"{o}/scenarios/coarse-cut.convergence.json",
                 "--variations", f"{o}/variations-mpv.json", "--project-root", ".", "--upgrade")
    crit["coarse_cut_upgrade_refused"] = isinstance(uc["upgrade"], dict) and uc["labels"] == ["unvalidated"]
    d10 = bench_config("sp", rec, root=scen, main="density-10")
    write(scen / "density-10.config.json", d10)
    _, b10 = call(BENCH, "run", "--config", f"{o}/scenarios/density-10.config.json", "--out",
                  f"{o}/scenarios/density-10.benchmarks.json", ok=(1,))
    _, l10 = call(CHECK, "label", "--spec", "study-sp.json", "--benchmarks", f"{o}/scenarios/density-10.benchmarks.json",
                  "--convergence", f"{o}/convergence-sp.json", "--variations", f"{o}/variations-sp.json",
                  "--project-root", ".", "--write", f"{o}/artifacts/scenario-density-10.study.computational-run.json",
                  "--created", CREATED)
    crit["density_10_caught"] = b10["benchmarks"][0]["verdict"] == "fail" and "stopping-power" in b10["failed"] and \
        any(g.startswith("stopping-power failed") for g in l10["gaps"])
    dump = json.loads((here / "study-sp.json").read_text(encoding="utf-8"))
    dump["study_id"] = "j14-scenario-dump-reference"
    dump["materials"][0]["reference_source"] = "Geant4 material dump (materials.json of the nominal run)"
    dump["materials"][0]["reference_origin"] = "geant4-material-dump"
    dump["physics"]["layered_sim_spec"] = os.path.relpath(here / "specs" / "sp-p100MeV.json", scen)
    dump["citations"]["literature_record"] = "../artifacts/geant4.literature-record.json"
    write(scen / "dump-reference.study.json", dump)
    _, ld = call(CHECK, "label", "--spec", f"{o}/scenarios/dump-reference.study.json", "--benchmarks",
                 f"{o}/benchmarks-sp.json", "--convergence", f"{o}/convergence-sp.json", "--variations",
                 f"{o}/variations-sp.json", "--project-root", ".", "--write",
                 f"{o}/artifacts/scenario-dump-reference.study.computational-run.json", "--created", CREATED)
    crit["dump_reference_flagged"] = any("taken from the Geant4 material dump" in g for g in ld["gaps"])
    results["scenarios"] = {"coarse-cut": lc["gaps"], "density-10": l10["gaps"], "dump-reference": ld["gaps"]}
    # a response from the WP1 output (format compatibility of the layered_sim CSV with build_response.py; the
    # response carries unvalidated and, since build_response.py writes empty inputs, cannot link the run records)
    rows = gzip.decompress((rec / "events" / "mpv-nominal.csv.gz").read_bytes()).decode().splitlines()
    cols = rows[1].split(",")
    li, di = cols.index("primary_eloss_MeV"), cols.index("edep_Si_MeV")
    tr = ["# SIMULATION (first 5000 events of mpv-nominal; energy loss and deposit in keV)", "truth,reco"]
    tr += [f"{float(r.split(',')[li]) * 1e3:.6g},{float(r.split(',')[di]) * 1e3:.6g}" for r in rows[2:5002]]
    (out / "response").mkdir(parents=True)
    (out / "response" / "truth-reco.csv").write_text("\n".join(tr) + "\n", encoding="utf-8")
    call(DETR, "build", f"{o}/response/truth-reco.csv", "--truth-col", "truth", "--reco-col", "reco", "--unweighted",
         "--all-selected", "--truth-edges", 40, 70, 80, 90, 100, 150, 400, "--reco-edges", 40, 70, 80, 90, 100, 150,
         400, "--variable", "primary_energy_loss", "--unit", "keV", "--reco-variable", "deposit", "--reco-unit", "keV",
         "--variable-conversion", "deposit = energy loss minus the energy carried out of the slab by secondaries",
         "--normalization", "conditional_on_generated", "--acceptance", "outside_matrix", "--residual", "difference",
         "--intended-use", "forward_folding", "--artifact-id", "j14-response-mpv",
         "--objective", "deposit response to the primary energy loss, 10 GeV mu- in 300 um Si (Geant4, unvalidated)",
         "--created", CREATED, "--status", "unvalidated", "--out", f"{o}/artifacts/response.json",
         "--input-record", f"{o}/artifacts/runs/mpv-nominal.computational-run.json", "--project-root", ".")
    rcode, _ = call(VALIDATE, f"{o}/artifacts/response.json", "--strict", ok=(0, 1))
    acode, _ = call(RESP, f"{o}/artifacts/response.json", "--validate", ok=(0, 1, 2, 3))
    crit["response_validates_and_is_unvalidated"] = rcode == 0 and acode == 0 and "unvalidated" in json.loads(
        (art / "response.json").read_text(encoding="utf-8"))["status"]
    # literature record and report
    report = render_report(results)
    (out / "report.md").write_text(report, encoding="utf-8")
    ccode, cite = call(CITES, f"{o}/report.md", "--record", f"{o}/artifacts/geant4.literature-record.json",
                       ok=(0, 1, 3))
    crit["report_citations_verified"] = ccode == 0
    vcode, val = call(VALIDATE, f"{o}/artifacts", ok=(0, 1))
    crit["artifacts_validate"] = vcode == 0 and not any(
        f.get("code") == "artifacts_dir.non_json" for f in val.get("findings", []))
    for study in ("mpv", "sp"):
        for kind in ("study", "study-validated"):
            dcode, dep = call(DEPS, f"{o}/artifacts/{study}.{kind}.computational-run.json", "--root", ".",
                              ok=(0, 1, 3))
            crit[f"{study}_{kind}_dependencies_ok"] = dcode == 0 and dep.get("dependency_consistency_ok") is True
    dcode, _ = call(DEPS, f"{o}/artifacts/response.json", "--root", ".", ok=(0, 1, 3))
    crit["response_linked_to_its_run"] = dcode == 0
    results["pass"] = crit
    write(out / "results.json", results)
    return results


def render_report(r: dict) -> str:
    m, s = r["studies"]["mpv"], r["studies"]["sp"]
    mb, sb = m["benchmarks"]["thin-layer-mpv"], s["benchmarks"]["stopping-power"]
    return f"""# Energy loss in 300 um of silicon with Geant4 11.4.3 (journey J14)

{LABEL}. Simulation only: every figure or table made from these runs is labelled "Simulation".

Geant4 11.4.3 [@Agostinelli:2002hh; @Allison:2006ve; @Allison:2016lfl] was built from the v11.4.3 tag and run with an EM-only modular list
(G4EmStandardPhysics_option4 with G4DecayPhysics), production cut 0.01 mm, through adapters/geant4.

References: the Bethe mean rate (Eq. 34.5) and the Landau-Vavilov most probable loss (Eq. 34.12) of the Review of
Particle Physics [@ParticleDataGroup:2024cfk], with silicon inputs from the PDG atomic and nuclear
properties tables, never from the Geant4 material dump.

- Most probable energy loss of 10 GeV mu- (thin-layer-mpv, reference grade): relative difference to the PDG
  Landau-Vavilov value {mb['relative_difference']:+.4f}, detection limit {mb['detection_limit']:.4f}; negative control
  {mb['negative_control']}; convergence gate {m['convergence_gate']}.
- Mean stopping power of 100 MeV protons (stopping-power, reference grade): relative difference to Bethe
  {sb['relative_difference']:+.4f}, detection limit {sb['detection_limit']:.4f}; negative control {sb['negative_control']};
  convergence gate {s['convergence_gate']}.

Label of both study records: {', '.join(m['labels'])}; each is re-issued as validated-in-scope for its benchmarked scope
only ({', '.join(m['phase2_eligible'] + s['phase2_eligible']) or 'none'}: one particle, energy, material and thickness),
with the run records referenced as evidence by hash (contracts 3.1.0). Nothing outside that scope is validated.
Gaps of the MPV study: {len(m['gaps'])}; of the stopping-power study: {len(s['gaps'])} (listed in the study records).
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--recorded", type=Path, default=HERE / "recorded",
                    help="the recorded inputs: read by the replay, rewritten by --live (default recorded/)")
    args = ap.parse_args(argv)
    rec = args.recorded.expanduser().resolve()
    if args.live:
        if not args.work:
            ap.error("--live needs --work")
        live(args.work.expanduser().resolve(), rec)
    res = replay(args.out.resolve(), rec)
    print(json.dumps({"pass": res["pass"]}, indent=1))
    return 0 if all(res["pass"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

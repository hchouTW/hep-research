#!/usr/bin/env python3
"""Journey J14 (detector simulation study with independent-reference benchmarks): energy loss in 300 um of silicon.

ILLUSTRATIVE. Two studies with Geant4 11.4.3 through adapters/geant4 and hep-detector's Geant4 study tools; names no
experiment. Every Geant4 output is `unvalidated`; the final products are the two study records.
- study-mpv.json: most probable energy loss of 10 GeV mu- (thin-layer-mpv reference benchmark against the PDG
  Landau-Vavilov Delta_p, thin-layer-width sanity), cut scan 0.1/0.03/0.01 mm, variations EM option 0 and 3, PAI, and
  FTFP_BERT_EMZ (same EM model: must be excluded from the systematic list).
- study-sp.json: mean stopping power of 100 MeV protons (stopping-power reference benchmark against Bethe), cut scan,
  variations EM option 0 and 3.
Reference inputs (density, Z/A, I, Sternheimer parameters) come from the PDG silicon tables (refdata/), never from the
Geant4 material dump. Negative controls: each reference benchmark reruns on a Geant4 run whose silicon density is
raised by the claimed detection limit (the reference keeps 2.329 g/cm3), and must fail.
Negative-control scenarios, each written as a study record that lists its gaps:
  coarse-cut      the MPV study with a scan of 1.0 and 0.3 mm only: stopped by the convergence gate;
  density-10      the stopping-power benchmark on a run with the silicon density 10 % too high: caught;
  dump-reference  reference inputs taken from the Geant4 material dump: flagged as a gap.

Modes:
  offline replay (default): recomputes the spec checks, convergence gate, benchmarks, variations, study records,
    literature record, report and checks from recorded/ and writes them to --out (default output/); the result is
    byte-identical to the committed output/ (tests/examples/test_geant4_thin_silicon.py).
  live (--live, needs HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG naming a JSON {"build_record", "layered_sim"}):
    runs every Geant4 run in --work (outside the plugin), then rewrites --recorded (default recorded/: run records with
    ~ paths, reduced gzip CSVs of the benchmark runs, run summaries, effective specs, the build record) and replays.
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
RUN = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_run.py"
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
BENCH = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"
LIT = PLUGIN / "skills" / "hep-citations" / "scripts" / "manage_literature.py"
CITES = PLUGIN / "skills" / "hep-authoring" / "scripts" / "check_citations.py"
VALIDATE = PLUGIN / "contracts" / "validate.py"
DEPS = PLUGIN / "contracts" / "dependencies.py"
DETR = PLUGIN / "skills" / "hep-detector" / "scripts" / "build_response.py"
RESP = PLUGIN / "contracts" / "response_adapter.py"
CREATED = "2026-10-21"
REDUCED = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process"]
LABEL = "ILLUSTRATIVE (journey J14): Geant4 outputs are unvalidated; names no experiment"
# run id: (base spec, events, seeds, changes as dotted spec keys, role, keep the reduced CSV)
CUTS = (0.1, 0.03)
COARSE = (1.0, 0.3)


def run_table() -> dict[str, dict]:
    t = {}
    for study, base, n, seed in (("mpv", "mpv-mu10GeV.json", 60000, 1401), ("sp", "sp-p100MeV.json", 30000, 1402)):
        t[f"{study}-nominal"] = {"base": base, "events": n, "seeds": [seed, 1], "set": {}, "csv": True}
        for k, cut in enumerate(CUTS + (COARSE if study == "mpv" else ())):
            t[f"{study}-cut-{cut}"] = {"base": base, "events": n, "seeds": [seed, 10 + k], "csv": False,
                                       "set": {"physics.default_cut_mm": cut, "physics.regions.0.cut_mm": cut}}
        for name, em in (("em-option0", "G4EmStandardPhysics"), ("em-option3", "G4EmStandardPhysics_option3")):
            t[f"{study}-{name}"] = {"base": base, "events": n, "seeds": [seed, 20 + len(name)], "csv": False,
                                    "set": {"physics.em_constructor": em}}
        t[f"{study}-density-10"] = {"base": base, "events": n, "seeds": [seed, 40], "csv": study == "sp",
                                    "set": {"materials.0.density_g_cm3": round(2.329 * 1.10, 6)}}
    t["mpv-pai"] = {"base": "mpv-mu10GeV.json", "events": 60000, "seeds": [1401, 30], "csv": False,
                    "set": {"ui_commands": ["/process/em/AddPAIRegion all SiRegion PAI"]}}
    t["mpv-ftfp-bert-emz"] = {"base": "mpv-mu10GeV.json", "events": 60000, "seeds": [1401, 31], "csv": False,
                              "set": {"physics.reference_list": "FTFP_BERT_EMZ", "physics.em_constructor": None}}
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


# --------------------------------------------------------------------------------------------------------- live
def live(work: Path, rec_dir: Path) -> None:
    if os.environ.get("HEP_GEANT4_LIVE_TEST") != "1" or not os.environ.get("HEP_GEANT4_CONFIG"):
        raise SystemExit("--live needs HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG")
    cfg = json.loads(Path(os.path.expanduser(os.environ["HEP_GEANT4_CONFIG"])).read_text(encoding="utf-8"))
    build, exe = os.path.expanduser(cfg["build_record"]), os.path.expanduser(cfg["layered_sim"])
    if rec_dir.exists():
        shutil.rmtree(rec_dir)
    (rec_dir / "build").mkdir(parents=True)
    shutil.copyfile(build, rec_dir / "build" / "geant4-build.computational-run.json")
    table = run_table()
    plan = {}

    def one(rid: str, spec: dict) -> None:
        sp = rec_dir / "specs" / f"{rid}.json"
        write(sp, spec)
        rec = rec_dir / "runs" / f"{rid}.computational-run.json"
        call(RUN, "run", "--spec", sp, "--exe", exe, "--build-record", build, "--work", work, "--run-id", rid,
             "--record", rec, "--created", CREATED, cwd=PLUGIN)
        csv = work / rid / "events.csv"
        call(CHECK, "summarize", "--record", rec, "--csv", csv, "--slab", "Si", "--out",
             rec_dir / "summaries" / f"{rid}.json", cwd=PLUGIN)
        if table.get(rid, {}).get("csv", True):
            call(RUN, "reduce", "--csv", csv, "--columns", *REDUCED, "--out", rec_dir / "events" / f"{rid}.csv.gz",
                 cwd=PLUGIN)
        plan[rid] = spec.get("_plan", {})

    def spec_for(row: dict) -> dict:
        spec = json.loads((HERE / "specs" / row["base"]).read_text(encoding="utf-8"))
        spec["run"]["events"], spec["run"]["seeds"] = row["events"], row["seeds"]
        for k, v in row["set"].items():
            set_key(spec, k, v)
        return spec
    for rid, row in table.items():
        one(rid, spec_for(row))
    # negative controls at the claimed detection limit, from the nominal benchmark of each study
    for study, bench in (("mpv", "thin-layer-mpv"), ("sp", "stopping-power")):
        cfg_path = rec_dir / f"dl-{study}.config.json"
        write(cfg_path, bench_config(study, rec_dir, nominal_only=True, root=rec_dir, study_dir=HERE))
        _, res = call(BENCH, "run", "--config", cfg_path, ok=(0, 1, 3))
        dl = next(b for b in res["benchmarks"] if b["benchmark"] == bench)["detection_limit_relative"]
        inj = math.ceil(dl * 1000) / 1000
        row = dict(table[f"{study}-nominal"], seeds=[table[f"{study}-nominal"]["seeds"][0], 50], csv=True,
                   set={"materials.0.density_g_cm3": round(2.329 * (1 + inj), 6)})
        table[f"{study}-control"] = row
        one(f"{study}-control", spec_for(row))
        write(rec_dir / f"control-{study}.json", {"detection_limit_relative": dl, "injected_relative": inj,
                                                  "injected": f"silicon density x {1 + inj:.3f} on the Geant4 side "
                                                              "(reference keeps 2.329 g/cm3)"})
        cfg_path.unlink()
    write(rec_dir / "live.json", {"created": CREATED, "runs": sorted(table), "work": str(work).replace(
        str(Path.home()), "~"), "hosts_contacted": [], "note": "Geant4 runs need no network; the build record lists "
                                                               "the hosts its build contacted"})


# ------------------------------------------------------------------------------------------------------- replay
def bench_config(study: str, rec_dir: Path, nominal_only=False, main="nominal", root: Path | None = None,
                 study_dir: Path | None = None) -> dict:
    root = root or HERE
    rel = os.path.relpath(rec_dir, root)
    spec_rel = os.path.relpath((study_dir or rec_dir.parent) / f"study-{study}.json", root)
    common = {"material": "Si_study", "slab": "Si", "thickness_mm": 0.3, "bootstrap": {"resamples": 200, "seed": 1}}
    out = []
    ctrl = None if nominal_only else json.loads((rec_dir / f"control-{study}.json").read_text(encoding="utf-8"))
    if study == "mpv":
        b = {"benchmark": "thin-layer-mpv", "particle": "mu-", "energy_MeV": 10000.0,
             "binning": {"bin_width_MeV": 0.002}, "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3},
             **common}
        w = {"benchmark": "thin-layer-width", "particle": "mu-", "energy_MeV": 10000.0,
             "binning": {"bin_width_MeV": 0.002}, **common}
        main_rows = [b, w]
    else:
        b = {"benchmark": "stopping-power", "particle": "proton", "energy_MeV": 100.0,
             "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3}, **common}
        main_rows = [b]
    for r in main_rows:
        r["csv"] = f"{rel}/events/{study}-{main}.csv.gz"
        r["run_record"] = f"{rel}/runs/{study}-{main}.computational-run.json"
        if ctrl and r["benchmark"] != "thin-layer-width":
            r["negative_control"] = {"csv": f"{rel}/events/{study}-control.csv.gz",
                                     "run_record": f"{rel}/runs/{study}-control.computational-run.json",
                                     "injected": ctrl["injected"], "injected_relative": ctrl["injected_relative"]}
        out.append(r)
    return {"schema": "geant4-benchmarks/1", "study_spec": spec_rel, "benchmarks": out}


def summaries(study: str, cuts) -> list[str]:
    args = ["--summary", f"nominal=recorded/summaries/{study}-nominal.json"]
    for c in cuts:
        args += ["--summary", f"scan=recorded/summaries/{study}-cut-{c}.json"]
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
                                                         f"{v}=recorded/summaries/{study}-{v}.json")]
        call(CHECK, "variations", "--spec", f"study-{study}.json", "--nominal",
             f"recorded/summaries/{study}-nominal.json", *var_args, "--out", f"{o}/variations-{study}.json")
        runs = [f"{o}/artifacts/runs/{study}-{r}.computational-run.json"
                for r in ["nominal", "control", *[f"cut-{c}" for c in CUTS], *variations[study]]]
        _, lab = call(CHECK, "label", "--spec", f"study-{study}.json", "--benchmarks", f"{o}/benchmarks-{study}.json",
                      "--convergence", f"{o}/convergence-{study}.json", "--variations", f"{o}/variations-{study}.json",
                      *[a for r in runs for a in ("--run-record", r)], "--project-root", ".",
                      "--write", f"{o}/artifacts/{study}.study.computational-run.json", "--created", CREATED)
        results["studies"][study] = {"spec": spec["status"], "convergence_gate": conv["convergence"]["gate"],
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
    coarse["physics"]["layered_sim_spec"] = os.path.relpath(here / "specs" / "mpv-mu10GeV.json", scen)
    write(scen / "coarse-cut.study.json", coarse)
    _, cc = call(CHECK, "run", "--spec", f"{o}/scenarios/coarse-cut.study.json", "--summary",
                 "scan=recorded/summaries/mpv-cut-1.0.json", "--summary", "scan=recorded/summaries/mpv-cut-0.3.json",
                 "--out", f"{o}/scenarios/coarse-cut.convergence.json", ok=(1,))
    _, lc = call(CHECK, "label", "--spec", f"{o}/scenarios/coarse-cut.study.json", "--benchmarks",
                 f"{o}/benchmarks-mpv.json", "--convergence", f"{o}/scenarios/coarse-cut.convergence.json",
                 "--variations", f"{o}/variations-mpv.json", "--project-root", ".", "--write",
                 f"{o}/artifacts/scenario-coarse-cut.study.computational-run.json", "--created", CREATED)
    crit["coarse_cut_stopped_by_gate"] = cc["convergence"]["gate"] == "fail" and any(
        "convergence gate not passed" in g for g in lc["gaps"])
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
         "--created", CREATED, "--status", "unvalidated", "--out", f"{o}/artifacts/response.json")
    rcode, _ = call(VALIDATE, f"{o}/artifacts/response.json", "--strict", ok=(0, 1))
    acode, _ = call(RESP, f"{o}/artifacts/response.json", "--validate", ok=(0, 1, 2, 3))
    crit["response_validates_and_is_unvalidated"] = rcode == 0 and acode == 0 and "unvalidated" in json.loads(
        (art / "response.json").read_text(encoding="utf-8"))["status"]
    # literature record and report
    call(LIT, "import", "literature-input.json", "--project-root", ".", "--out",
         f"{o}/artifacts/geant4.literature-record.json", "--today", CREATED, "--artifact-id", "j14-geant4-literature")
    report = render_report(results)
    (out / "report.md").write_text(report, encoding="utf-8")
    ccode, cite = call(CITES, f"{o}/report.md", "--record", f"{o}/artifacts/geant4.literature-record.json",
                       ok=(0, 1, 3))
    crit["report_citations_verified"] = ccode == 0
    vcode, val = call(VALIDATE, f"{o}/artifacts", ok=(0, 1))
    crit["artifacts_validate"] = vcode == 0 and not any(
        f.get("code") == "artifacts_dir.non_json" for f in val.get("findings", []))
    for study in ("mpv", "sp"):
        dcode, dep = call(DEPS, f"{o}/artifacts/{study}.study.computational-run.json", "--root", ".", ok=(0, 1, 3))
        crit[f"{study}_dependencies_ok"] = dcode == 0 and dep.get("dependency_consistency_ok") is True
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

Label of both study records: {', '.join(m['labels'])} (phase 1: no Geant4-derived artifact is upgraded). Scopes phase 2
could re-issue: {', '.join(m['phase2_eligible'] + s['phase2_eligible']) or 'none'}.
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

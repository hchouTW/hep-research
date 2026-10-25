#!/usr/bin/env python3
"""Journey J15 (take a spectrometer design from F1 to F4): the minimal spectrometer of Geant4 program section B.4.

SYNTHETIC design study; the geometry is invented and represents no experiment (README). A 0.5 T uniform-field
spectrometer with six 0.3 mm silicon planes over a 0.80 m lever arm, two two-layer TOF stations and a 50-layer Pb/PVT
sampling calorimeter (18.4 X0), and two variants with four and eight planes over the same lever arm:
  cand-N6  nominal (six planes, section B.4.1);
  cand-N4  four planes, same lever arm (derived from cand-N6, overrides only the tracker layers);
  cand-N8  eight planes, same lever arm.
Requirements (illustrative numbers): REQ-TRK-001 momentum-resolution-core <= 0.03 for 1 GV protons; REQ-TRK-002 the
same <= 0.12 at 100 GV; REQ-CC-001 charge-confusion-rate <= 0.02 for 500 GV protons with a declared curvature offset
(0 +- 2e-5 per GV); REQ-CAL-001 shower-containment >= 0.95 for 10 GeV electrons; hard mass and channel-count
constraints; equal-mass comparison basis with expected-precision among the Pareto axes.

Chain (skills/hep-detector/scripts/evaluate_design.py; verdicts only from contracts/design.py):
1. the design-spec, the three candidates and the realization profile (j15.realization.json, mapping 1.1.0);
2. F1 per candidate: tracker_resolution momentum and multiple_scattering resolution at 1 and 100 GV, the
   Gaussian-core charge confusion at 500 GV fed by an F1 resolution there, the mass and channel-count budgets;
   F2: toy_spectrometer resolution at 1 and 100 GV, design_estimates infield-acceptance at 1 and 10 GV against the
   straight-line acceptance (F1);
3. the plan (missing evidence) and the design report (compliance matrix, screening, comparison basis).
The F4 studies (Geant4, stage B3.6) are added from recorded/ by the same script (see the README).

Usage (from the plugin root): python3 examples/design-minimal-spectrometer/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.design import derive  # noqa: E402

PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
RECORDED = HERE / "recorded"
NS = "j15-v1"
CREATED = "2026-10-24"
EPOCH = "1792800000"  # 2026-10-24T00:00:00Z: SOURCE_DATE_EPOCH for reproducible envelopes
LABEL = "SYNTHETIC design study (journey J15, minimal spectrometer; names no experiment)"
X0_SI_MM, X0_PB_MM, X0_PVT_MM = 93.7, 5.612, 425.4  # PDG 2024 Atomic and Nuclear Properties (silicon, lead, PVT)
LEVER_M = 0.80


def param(value, unit, source="example proposal (SYNTHETIC)", status="proposal"):
    return {"value": value, "unit": unit, "source": source, "status": status}


def calib(method, samples):
    return {"method": method, "control_samples": samples}


def positions(n: int) -> list[float]:
    return [round(i * LEVER_M / (n - 1), 6) for i in range(n)]


def tracker(n: int) -> dict:
    return {"role": "tracking", "technology": "single-sided silicon strip planes (0.3 mm)",
            "parameters": {"layer_positions_m": param(positions(n), "m"),
                           "point_resolution_um": param(10.0, "um"),
                           "layer_x_over_x0": param([0.3 / X0_SI_MM] * n, "1"),
                           "passive_x_over_x0": param(0.0, "1"),
                           "layer_material": param("G4_Si", "n/a"),
                           "layer_transverse_half_m": param([0.1, 0.1], "m"),
                           "layer_aperture_radius_m": param([0.1] * n, "m"),
                           "layer_lateral_offset_m": param([0.0] * n, "m"),
                           "aperture_radius_tolerance_m": param(0.001, "m")},
            "interfaces": ["DES-MAG-001", "DES-TOF-001"],
            "calibration": calib("track-based alignment", ["cosmic-ray muons", "high-rigidity protons"])}


def magnet() -> dict:
    return {"role": "bending", "technology": "uniform-field dipole (field only; no magnet material, README)",
            "parameters": {"field_T": param(0.5, "T"), "field_extent_m": param([-0.02, 0.82], "m")},
            "interfaces": ["DES-TRK-001"], "calibration": calib("field map before integration", ["field map"])}


def tof() -> dict:
    return {"role": "tof", "technology": "two unsegmented plastic-scintillator layers per station",
            "parameters": {"layer_positions_m": param([-0.305, -0.285, 0.995, 1.015], "m"),
                           "layer_thickness_m": param(0.010, "m"), "time_resolution_ps": param(100.0, "ps")},
            "interfaces": ["DES-TRK-001"],
            "calibration": calib("time offsets and walk from through-going muons", ["cosmic-ray muons"])}


def calorimeter() -> dict:
    layers = 50
    depth = layers * (2.0 / X0_PB_MM + 5.0 / X0_PVT_MM)
    return {"role": "calorimetry-em", "technology": "Pb / plastic-scintillator sampling calorimeter",
            "parameters": {"front_position_m": param(1.05, "m"), "depth_x0": param(round(depth, 6), "1"),
                           "sampling_layers": param(layers, "1"),
                           "passive_material": param("G4_Pb", "n/a"), "passive_thickness_mm": param(2.0, "mm"),
                           "active_material": param("G4_PLASTIC_SC_VINYLTOLUENE", "n/a"),
                           "active_thickness_mm": param(5.0, "mm")},
            "interfaces": ["DES-TOF-001"],
            "calibration": calib("energy scale from minimum-ionizing muons", ["cosmic-ray muons", "test-beam electrons"])}


def row(estimate, sigma, unit, basis="estimate", source="SYNTHETIC example estimate"):
    return {"allocation": round(estimate * 1.1, 6), "estimate": estimate, "uncertainty": sigma, "unit": unit,
            "basis": basis, "source": source, "fidelity": "F1"}


def budgets(n: int) -> dict:
    # estimates carry at least the adequacy table's 20 %, catalog rows 5 % (budget_min_relative_uncertainty)
    cat = "SYNTHETIC example: catalog values of comparable components"
    return {"mass": {"DES-TRK-001": row(3.0 * n, 0.6 * n, "kg"), "DES-MAG-001": row(400.0, 80.0, "kg"),
                     "DES-TOF-001": row(20.0, 4.0, "kg"), "DES-CAL-001": row(1500.0, 75.0, "kg", "catalog", cat)},
            "channel_count": {"DES-TRK-001": row(2000.0 * n, 100.0 * n, "1", "catalog", cat),
                              "DES-MAG-001": row(0.0, 0.0, "1", "catalog", cat),
                              "DES-TOF-001": row(16.0, 0.8, "1", "catalog", cat),
                              "DES-CAL-001": row(100.0, 5.0, "1", "catalog", cat)}}


def den(v, tol=0.0):
    return {"value": v, "tolerance": tol}


def envelope(atype, aid, ext):
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": aid, "artifact_type": atype, "objective": LABEL,
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION},
            "bindings": {"experiments": [], "theory": []},
            "provenance": {"producer_skill": "hep-detector", "created": CREATED, "evidence_ids": []},
            "inputs": [], "outputs": [], "status": ["synthetic"], "unresolved_inputs": [], "extension": ext}


SUBSYSTEMS = ["DES-TRK-001", "DES-MAG-001", "DES-TOF-001", "DES-CAL-001"]


def spec() -> dict:
    trk = lambda rid, r, target: {  # noqa: E731
        "id": f"{NS}:{rid}", "parents": [f"{NS}:PHY-001"], "quantity": "momentum-resolution-core", "comparator": "<=",
        "target": target, "unit": "1", "kind": "driving", "denominator": {"rigidity_GV": den(r), "species": den("proton")},
        "allocation": f"{NS}:ALC-{rid[4:]}",
        "verification": {"method": "analysis, then Geant4 simulation through the F4 qualification path"}}
    return {"design_id": NS, "spec_version": 1,
            "objectives": [{"id": f"{NS}:PHY-001", "description": "SYNTHETIC: charge-separated proton spectrum",
                            "observable": "proton flux versus rigidity", "range": "1 GV to 500 GV",
                            "precision_goal": "illustrative (journey J15)"}],
            "requirements": [
                trk("REQ-TRK-001", 1.0, 0.03), trk("REQ-TRK-002", 100.0, 0.12),
                {"id": f"{NS}:REQ-CC-001", "parents": [f"{NS}:PHY-001"], "quantity": "charge-confusion-rate",
                 "comparator": "<=", "target": 0.02, "unit": "1", "kind": "driving",
                 "denominator": {"rigidity_GV": den(500.0), "species": den("proton"), "charge_sign": den("positive"),
                                 "curvature_offset_per_GV": den(0.0, 2e-5)},
                 "allocation": f"{NS}:ALC-CC-001", "verification": {"method": "simulation validated with data"}},
                {"id": f"{NS}:REQ-CAL-001", "parents": [f"{NS}:PHY-001"], "quantity": "shower-containment",
                 "comparator": ">=", "target": 0.95, "unit": "1", "kind": "driving",
                 "denominator": {"energy_GeV": den(10.0), "species": den("e-")},
                 "allocation": f"{NS}:ALC-CAL-001", "verification": {"method": "Geant4 simulation"}}],
            "allocations": [
                {"id": f"{NS}:ALC-TRK-001", "requirement": f"{NS}:REQ-TRK-001", "rule": "quadrature", "independent": True,
                 "items": [{"name": "multiple scattering", "value": 0.025}, {"name": "intrinsic", "value": 0.005},
                           {"name": "alignment", "value": 0.008}], "margin": 0.003},
                {"id": f"{NS}:ALC-TRK-002", "requirement": f"{NS}:REQ-TRK-002", "rule": "quadrature", "independent": True,
                 "items": [{"name": "intrinsic", "value": 0.09}, {"name": "multiple scattering", "value": 0.02},
                           {"name": "alignment", "value": 0.05}], "margin": 0.01},
                {"id": f"{NS}:ALC-CC-001", "requirement": f"{NS}:REQ-CC-001", "rule": "linear",
                 "items": [{"name": "Gaussian core", "value": 0.01}, {"name": "non-Gaussian tails", "value": 0.008}],
                 "margin": 0.002},
                {"id": f"{NS}:ALC-CAL-001", "requirement": f"{NS}:REQ-CAL-001", "rule": "linear",
                 "items": [{"name": "rear leakage", "value": 0.03}, {"name": "lateral and albedo", "value": 0.015}],
                 "margin": 0.005}],
            "constraints": [
                {"id": f"{NS}:CON-MASS-001", "type": "mass", "hardness": "hard", "quantity": "mass-budget",
                 "comparator": "<=", "target": 2500.0, "unit": "kg", "denominator": {}, "subsystems": SUBSYSTEMS},
                {"id": f"{NS}:CON-CHAN-001", "type": "channel-count", "hardness": "soft",
                 "quantity": "channel-count-budget", "comparator": "<=", "target": 20000.0, "unit": "1",
                 "denominator": {}, "subsystems": SUBSYSTEMS}],
            "comparison_basis": {"quantity": "mass-budget", "tolerance_relative": 0.05,
                                 "pareto_axes": ["expected-precision", "mass-budget"],
                                 "note": "candidates are compared at equal mass: they differ only in the number of "
                                         "0.3 mm silicon planes (3 kg each, SYNTHETIC), so magnet, TOF and calorimeter "
                                         "items are shared and cancel"}}


CANDIDATES = {"cand-N6": ("nominal: six planes over 0.80 m (section B.4.1)", 6),
              "cand-N4": ("four planes over the same 0.80 m", 4),
              "cand-N8": ("eight planes over the same 0.80 m", 8)}


def candidate(name: str) -> dict:
    desc, n = CANDIDATES[name]
    ext = {"candidate_id": f"{NS}:{name}", "design_id": NS, "description": desc}
    if name == "cand-N6":
        ext["subsystems"] = {"DES-TRK-001": tracker(6), "DES-MAG-001": magnet(), "DES-TOF-001": tof(),
                             "DES-CAL-001": calorimeter()}
    else:  # a variant records only its differences (ART-20)
        t = tracker(n)["parameters"]
        ext["derived_from"] = f"{NS}:cand-N6"
        ext["overrides"] = {"DES-TRK-001": {"parameters": {k: t[k] for k in (
            "layer_positions_m", "layer_x_over_x0", "layer_aperture_radius_m", "layer_lateral_offset_m")}}}
    ext["budgets"] = budgets(n)
    return envelope("design-candidate", f"{NS}-{name}", ext)


def evaluate(art: Path, *args: str, ok: tuple = (0,)) -> dict:
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)
    p = subprocess.run([sys.executable, "-B", str(EVAL), *args, "--artifacts", str(art)], capture_output=True,
                       text=True, env=env, timeout=600)
    out = json.loads(p.stdout)
    if p.returncode not in ok:
        raise RuntimeError(f"evaluate_design.py {args}: {out}")
    return out


# the F4 studies of B3.6: one per (candidate, figure of merit, denominator); the geometry file of each is generated
# before any F1 evaluation (a geometry call sets the candidate's geometry_ref, which would make earlier evaluations of
# that candidate stale)
STUDIES = {
    "N6-TRK1": ("cand-N6", "momentum-resolution-core", {"rigidity_GV": 1, "species": "proton"}, "REQ-TRK-001"),
    "N6-TRK100": ("cand-N6", "momentum-resolution-core", {"rigidity_GV": 100, "species": "proton"}, "REQ-TRK-002"),
    "N4-TRK1": ("cand-N4", "momentum-resolution-core", {"rigidity_GV": 1, "species": "proton"}, "REQ-TRK-001"),
    "N4-TRK100": ("cand-N4", "momentum-resolution-core", {"rigidity_GV": 100, "species": "proton"}, "REQ-TRK-002"),
    "N8-TRK1": ("cand-N8", "momentum-resolution-core", {"rigidity_GV": 1, "species": "proton"}, "REQ-TRK-001"),
    "N8-TRK100": ("cand-N8", "momentum-resolution-core", {"rigidity_GV": 100, "species": "proton"}, "REQ-TRK-002"),
    "N6-CC500": ("cand-N6", "charge-confusion-rate", {"rigidity_GV": 500, "species": "proton",
                                                     "charge_sign": "positive", "curvature_offset_per_GV": 0.0},
                 "REQ-CC-001"),
    "N6-CAL10": ("cand-N6", "shower-containment", {"energy_GeV": 10, "species": "e-"}, "REQ-CAL-001"),
}


def write_design(out: Path) -> Path:
    """The design-spec, the H1 and H2 drafts, the candidates and every F4 study's geometry file; returns the
    artifacts_dir."""
    art, dec = out / "artifacts", out / "decisions"
    for d in (art, dec):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    (art / "design-spec.v1.json").write_text(json.dumps(envelope("design-spec", f"{NS}-spec-v1", spec()), indent=1)
                                             + "\n")
    for cat, text in (("design-scope", "the goal and its observable and range are the scope of J15"),
                      ("requirements-baseline", "the four driving requirements, their allocations and the equal-mass "
                                                "comparison basis are the baseline")):
        rec = {"record_version": "1.1.0", "decision_id": f"{NS}-{cat}", "analysis": NS, "decision": text,
               "category": cat, "actor": {"kind": "agent", "id": "prepared by an agent: NEEDS A HUMAN SIGNATURE"},
               "time": f"{CREATED}T12:00:00Z", "seen": {"state": "not-applicable"},
               "artifacts": [{"ref": "design-spec.v1.json",
                              "sha256": hashlib.sha256((art / "design-spec.v1.json").read_bytes()).hexdigest()}]}
        (dec / f"{cat}.draft.json").write_text(json.dumps(rec, indent=1) + "\n")
    (art / "candidates").mkdir()
    for name in CANDIDATES:
        (art / "candidates" / f"{name}.json").write_text(json.dumps(candidate(name), indent=1) + "\n")
    for sid, (cand, fom, den_, _) in STUDIES.items():
        evaluate(art, "geometry", "--candidate", f"{NS}:{cand}", "--figure-of-merit", fom,
                 *[a for k, v in den_.items() for a in ("--denominator", f"{k}={v}")], "--id", f"G-{sid}")
    return art


def f12(art: Path) -> dict:
    """The F1 and F2 evaluations of every candidate (B3.1)."""
    evals: dict = {}
    for name in CANDIDATES:
        c, cid = name.split("-")[1], f"{NS}:{name}"
        e = evals[name] = {}
        for req, tag in (("REQ-TRK-001", "1"), ("REQ-TRK-002", "100")):
            r = evaluate(art, "run", "--candidate", cid, "--requirement", req, "--tool", "tracker-resolution:momentum",
                         "--id", f"CALC-TR{tag}-{c}", "--status", "synthetic")
            e[f"F1 resolution {tag} GV"] = {"value": r["value"], "bound": r["bound"]}
            r = evaluate(art, "run", "--candidate", cid, "--requirement", req, "--fidelity", "F2",
                         "--tool", "toy-spectrometer:resolution", "--id", f"CALC-TOY{tag}-{c}", "--status", "synthetic")
            e[f"F2 toy_spectrometer {tag} GV"] = {"value": r["value"], "bound": r["bound"]}
        up = evaluate(art, "run", "--candidate", cid, "--figure-of-merit", "momentum-resolution-core",
                      "--denominator", "rigidity_GV=500", "--denominator", "species=proton",
                      "--tool", "tracker-resolution:momentum", "--id", f"CALC-TR500-{c}", "--status", "synthetic")
        cc = evaluate(art, "run", "--candidate", cid, "--requirement", "REQ-CC-001", "--upstream", up["evaluation"],
                      "--id", f"CALC-CC-{c}", "--status", "synthetic")
        e["F1 resolution 500 GV"] = {"value": up["value"], "bound": up["bound"]}
        for mdr in ("intrinsic", "total"):
            m = evaluate(art, "run", "--candidate", cid, "--figure-of-merit", "maximum-detectable-rigidity",
                         "--denominator", "species=proton", "--denominator", f"mdr_definition={mdr}",
                         "--tool", "multiple-scattering:resolution", "--id", f"CALC-MDR-{mdr}-{c}",
                         "--status", "synthetic")
            e[f"F1 MDR {mdr}"] = {"value": m["value"], "bound": m["bound"]}
        e["F1 charge confusion 500 GV"] = {"value": cc["value"], "bound": cc["bound"]}
        for r_gv in ("1", "10"):
            for fid, tool, short in (("F1", "design-estimates:straight-line-acceptance", "SLA"),
                                     ("F2", "design-estimates:infield-acceptance", "IFA")):
                a = evaluate(art, "run", "--candidate", cid, "--figure-of-merit", "geometric-acceptance",
                             "--denominator", f"rigidity_GV={r_gv}", "--denominator", "species=proton",
                             "--denominator", "charge_sign=positive", "--fidelity", fid, "--tool", tool,
                             "--id", f"CALC-{short}{r_gv}-{c}", "--status", "synthetic")
                e[f"{fid} acceptance {r_gv} GV"] = {"value": a["value"], "bound": a["bound"]}
        for q, short in (("mass", "MASS"), ("channel_count", "CHAN")):
            m = evaluate(art, "budget", "--candidate", cid, "--quantity", q, "--id", f"CALC-{short}-{c}",
                         "--status", "synthetic")
            e[f"F1 {q}"] = {"value": m["value"]}
    return evals


def label(art: Path, sid: str, results: str, write: str) -> dict:
    """check_geant4_study.py label --upgrade on the recorded inputs of one study (the run records the live record
    named as evidence or inputs), offline."""
    sdir = art / "studies" / sid
    live = json.loads((sdir / write).read_text(encoding="utf-8"))
    refs = [r["ref"] for r in (live.get("extension") or {}).get("evidence_records") or []]
    refs += [i["ref"] for i in live.get("inputs") or [] if i.get("artifact_type") == "computational-run"]
    var = ["--variations", str(sdir / "variations.json")] if (sdir / "variations.json").is_file() else []
    p = subprocess.run([sys.executable, "-B", str(CHECK), "label", "--spec", str(sdir / "study.json"), "--benchmarks",
                        str(sdir / "bench.results.json"), "--convergence", str(sdir / "convergence.json"), *var,
                        *[a for r in dict.fromkeys(refs) for a in ("--run-record", str(art / r))],
                        "--project-root", str(art), "--results", str(sdir / results), "--geometry",
                        str(art / "studies" / f"G-{sid}.geometry.json"), "--upgrade", "--write", str(sdir / write),
                        "--created", CREATED], capture_output=True, text=True, timeout=600,
                       env=dict(os.environ, SOURCE_DATE_EPOCH=EPOCH))
    out = json.loads(p.stdout)
    if p.returncode not in (0, 1, 3):
        raise RuntimeError(f"label {sid}: {out}")
    return out


def replay_f4(art: Path) -> dict:
    """The F4 studies (B3.6) from recorded/ (written by live.py): run records unpacked, every study re-labelled
    offline (qualification path, D0-c uncertainty) and its F4 evaluation written; a study whose upgrade is refused
    gets none (f4 is incomplete, exit 3: it would decide nothing); nothing is simulated here."""
    if not (RECORDED / "runs").is_dir():
        return {}
    (art / "runs").mkdir(exist_ok=True)
    for gz in sorted((RECORDED / "runs").glob("*.json.gz")):
        (art / "runs" / gz.name.removesuffix(".gz")).write_bytes(gzip.decompress(gz.read_bytes()))
    for sub_ in ("specs", "studies", "checks"):
        if (RECORDED / "artifacts" / sub_).is_dir():
            shutil.copytree(RECORDED / "artifacts" / sub_, art / sub_, dirs_exist_ok=True)
    shutil.copy(HERE / "j15.realization.json", art / "j15.realization.json")
    out = {}
    for sid, (cand, fom, _den, req) in STUDIES.items():
        records = [("study.computational-run.json", "f4-results.json", f"SIM-{sid}")]
        if (art / "studies" / sid / "study-notails.computational-run.json").is_file():
            records.append(("study-notails.computational-run.json", "f4-results-notails.json", f"SIM-{sid}-notails"))
        for write, results, eid in records:
            if not (art / "studies" / sid / write).is_file():
                continue
            lab = label(art, sid, results, write)
            res = json.loads((art / "studies" / sid / results).read_text(encoding="utf-8"))["results"][fom]
            f4 = evaluate(art, "f4", "--candidate", f"{NS}:{cand}", "--requirement", req, "--study",
                          f"studies/{sid}/{write}", "--id", eid, ok=(0, 3))
            if f4.get("status") == "incomplete" and f4.get("reason") != "upgrade-refused":
                raise RuntimeError(f"f4 {eid}: {f4}")
            out[eid] = {"upgrade": lab.get("upgrade"), "gaps": lab.get("gaps"), "value": res["value"],
                        "f4_written": f4.get("status") != "incomplete",
                        "uncertainty": res.get("uncertainty"), "model_envelope": res.get("model_envelope"),
                        "tail_sources_simulated": json.loads((art / "studies" / sid / results).read_text())[
                            "tail_sources_simulated"], "bound": f4.get("bound")}
    return out


def build(out: Path) -> dict:
    art = write_design(out)
    evals = f12(art)
    f4 = replay_f4(art)
    dec = out / "decisions"
    plan = evaluate(art, "plan", "--decisions", str(dec))
    rep = evaluate(art, "report", "--decisions", str(dec))
    return {"evaluations": evals, "f4": f4, "plan": plan, "report": rep["report"]}


def summarize(full: dict) -> dict:
    rows = {}
    for item in full["requirements"] + full["constraints"]:
        for m in item["matrix"]:
            for c in m["candidates"]:
                rows[f"{item['id'].split(':')[1]} {c.split(':')[1]}"] = {
                    "result": m["result"], "codes": m["codes"], "missing_evidence": m["missing_evidence"]}
    return rows


def f4_criteria(f4: dict, rows: dict) -> dict:
    """B3.9, from the recorded F4 studies (B3.6)."""
    up = lambda e: f4[e]["upgrade"] == "re-issued as validated-in-scope"  # noqa: E731
    gap = lambda e, text: any(text in g for g in f4[e]["gaps"] or [])  # noqa: E731
    return {
        # the 1 GV resolution studies qualify (B2.8: material definition, field, closure, the multiple-scattering
        # reference) and the core falls in section B.4.2's 1.8-2.6 % row (the core may sit slightly below)
        "trk1_upgraded": all(up(f"SIM-{c}-TRK1") for c in ("N4", "N6", "N8")),
        "n6_core_in_b42_band": 0.0175 <= f4["SIM-N6-TRK1"]["value"] <= 0.026,
        "tails_off_optimistic_on_estimate": (f4["SIM-N6-TRK1-notails"]["bound"], f4["SIM-N6-TRK1"]["bound"])
        == ("optimistic", "estimate"),
        "trk1_decides": all(rows[f"REQ-TRK-001 {c}"]["result"] == "pass" for c in ("cand-N4", "cand-N8")),
        # 100 GV: the reference's minus control shifted beyond 1.1 DL (recorded, never rerun): not upgraded
        "trk100_refused_on_the_control": all(not up(f"SIM-{c}-TRK100") and gap(f"SIM-{c}-TRK100", "detection limit")
                                             for c in ("N4", "N6", "N8")),
        "trk100_more_planes_better": f4["SIM-N8-TRK100"]["value"] < f4["SIM-N6-TRK100"]["value"]
        < f4["SIM-N4-TRK100"]["value"],
        "cc_not_qualifiable_before_d0b": not up("SIM-N6-CC500") and gap("SIM-N6-CC500", "D0-b"),
        "shower_not_upgraded": not up("SIM-N6-CAL10") and 0.9 <= f4["SIM-N6-CAL10"]["value"] <= 1.0,
    }


def criteria(evals: dict, rows: dict, full: dict) -> dict:
    n6 = evals["cand-N6"]
    return {
        "no_design_errors": full["status"] == "ok" and not full["errors"],
        # section B.4.2: 1 GV protons, multiple-scattering term 1.8-2.6 % (the F1 PDG coefficient omits the Highland
        # log term and the discrete-plane factor, so it may sit below the band)
        "f1_1gv_in_b42_band": 0.012 <= n6["F1 resolution 1 GV"]["value"] <= 0.026,
        # MDR about 1172 GV (exact least squares): the 100 GV measurement term is about 100/1172 = 8.5 %
        # section B.4.2: MDR about 1172 GV (exact least squares), about 1131 GV with Gluckstern (multiple_scattering)
        "f1_mdr_near_b42": 1000 <= n6["F1 MDR intrinsic"]["value"] <= 1250,
        "f1_100gv_measurement_term": 0.075 <= n6["F1 resolution 100 GV"]["value"] <= 0.10,
        "f2_toy_close_to_f1": all(abs(e["F2 toy_spectrometer 100 GV"]["value"] /
                                      e["F1 resolution 100 GV"]["value"] - 1) < 0.25
                                  for e in evals.values()),
        "more_planes_better_at_100gv": (evals["cand-N8"]["F1 resolution 100 GV"]["value"]
                                        < n6["F1 resolution 100 GV"]["value"]
                                        < evals["cand-N4"]["F1 resolution 100 GV"]["value"]),
        # at 10 GV the tracks are nearly straight over 0.8 m: the in-field acceptance (F2) approaches the
        # straight-line acceptance (F1) of the same circular apertures
        "acceptance_f2_near_f1_at_10gv": all(abs(e["F2 acceptance 10 GV"]["value"] / e["F1 acceptance 10 GV"]["value"]
                                                 - 1) < 0.1 for e in evals.values()),
        "shower_needs_f4": all("F4" in " ".join(rows[f"REQ-CAL-001 {c}"]["missing_evidence"]) for c in CANDIDATES),
        "gate_flags_shown": full["gate_flags"] == ["gate.H1_missing", "gate.H2_missing", "gate.H3_missing"],
        # H1 and H2 are prepared by the agent and listed, but only a human record clears a gate (DEC-05)
        "drafts_listed_not_valid": all(g["records"] and not any(r["valid"] for r in g["records"])
                                       for g in full["gates"] if g["category"] in ("design-scope",
                                                                                     "requirements-baseline")),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    built = build(args.out)
    full = derive(args.out / "artifacts", args.out / "decisions")
    rows = summarize(full)
    passed = criteria(built["evaluations"], rows, full)
    if built["f4"]:
        passed.update(f4_criteria(built["f4"], rows))
    results = {"label": LABEL, "design_id": NS, "evaluations": built["evaluations"], "f4": built["f4"],
               "verdicts": rows,
               "comparison_basis": {k: full["comparison_basis"].get(k) for k in ("declared", "holds", "reason")},
               "ranking": full["ranking"]["status"], "gate_flags": full["gate_flags"], "pass": passed,
               "note": "verdicts derived by contracts/design.py"}
    (args.out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"pass": passed, "out": str(args.out)}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

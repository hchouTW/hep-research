#!/usr/bin/env python3
"""Example B (detector system design spec, M3): a collider tracking and electromagnetic-calorimetry design study.

SYNTHETIC design study bound to the illustrative experiment:synthetic-collider profile; it does not reproduce CMS or
any real detector (EXB-01). Every number is a proposal of this example. Three candidates:
  cand-A  13 layers over 1.0 m in 3.8 T, a fine-sampling ECAL;
  cand-B  10 layers over 1.0 m in 2.0 T, a coarser ECAL;
  cand-P  a probe with 6 layers over 0.4 m (too short a lever arm).
Only tracking (momentum resolution at 100 GeV for muons) and ECAL energy resolution (50 GeV electrons) have
evaluators; the hadronic calorimeter resolution, the trigger efficiency, the pileup robustness and the shower
containment have none at any fidelity up to F3 and are recorded as capability.unavailable, listed in the report and in
the H3 decision record (EXB-02). The H3 record is prepared by the agent (actor agent): it lists what a human would
approve, and the H3 gate flag stays until a human signs it (DEC-05).

Chain: design-spec and candidates -> evaluate_design.py run (resolution, ECAL, the four unavailable records) and
budget (mass) -> the prepared H3 record -> evaluate_design.py report. Verdicts only from contracts/design.py.
Acceptance criteria: the probe fails resolution (bound.excludes); the two reasonable candidates are inconclusive on
resolution and ECAL resolution (bound.direction); the four unavailable quantities are inconclusive with
capability.unavailable and listed; the equal-mass basis is checked between the two that survive screening (the 2.0 T
solenoid and the coarser ECAL are lighter, no item is shared, so it does not hold; the report refuses to rank for that and
for lack of expected-precision evaluations).

Usage (from the plugin root): python3 examples/design-collider-tracker/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.design import derive  # noqa: E402

PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
PROFILE_VERSION = json.loads((PLUGIN / "profiles/experiments/synthetic-collider/profile.json").read_text())["version"]
EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
NS = "collider-tracker-v1"
CREATED = "2026-10-24"
EPOCH = "1792800000"
LABEL = "SYNTHETIC design study (illustrative collider; not CMS or any real detector)"
UNAVAILABLE = {"REQ-HCAL-001": "hadronic-energy-resolution", "REQ-TRG-001": "trigger-efficiency",
               "REQ-PU-001": "pileup-robustness", "REQ-CONT-001": "shower-containment"}


def param(value, unit):
    return {"value": value, "unit": unit, "source": "example proposal", "status": "proposal"}


def calib(method, samples):
    return {"method": method, "control_samples": samples}


def row(estimate, sigma, unit, basis="estimate", source="example engineering estimate"):
    return {"allocation": round(estimate * 1.1, 6), "estimate": estimate, "uncertainty": sigma, "unit": unit,
            "basis": basis, "source": source, "fidelity": "F1"}


def candidate(n_layers, lever, field, ecal, trk_mass, mag_mass, ecal_mass):
    pos = [round(0.1 + i * lever / (n_layers - 1), 6) for i in range(n_layers)]
    catalog = "SYNTHETIC example: catalog masses of comparable components (not weighed)"
    subs = {
        "DES-TRK-001": {"role": "tracking", "technology": "silicon pixel and strip barrel",
                        "parameters": {"layer_positions_m": param(pos, "m"), "point_resolution_um": param(20.0, "um"),
                                       "layer_x_over_x0": param([0.02] * n_layers, "1"),
                                       "passive_x_over_x0": param(0.1, "1")},
                        "interfaces": ["DES-MAG-001"], "calibration": calib("track-based alignment",
                                                                              ["Z -> mu mu", "cosmic-ray muons"])},
        "DES-MAG-001": {"role": "bending", "technology": "superconducting solenoid",
                        "parameters": {"field_T": param(field, "T")}, "interfaces": ["DES-TRK-001"],
                        "calibration": calib("field map with Hall and NMR probes", ["field map"])},
        "DES-ECAL-001": {"role": "calorimetry-em", "technology": "lead-tungstate crystals",
                         "parameters": {"stochastic_term": param(ecal[0], "GeV^0.5"),
                                        "noise_term_GeV": param(ecal[1], "GeV"),
                                        "constant_term": param(ecal[2], "1")},
                         "interfaces": ["DES-TRK-001"], "calibration": calib("intercalibration with isolated electrons",
                                                                              ["Z -> e e", "W -> e nu"])}}
    budgets = {"mass": {"DES-TRK-001": row(trk_mass, 0.05 * trk_mass, "kg", "catalog", catalog),
                        "DES-MAG-001": row(mag_mass, 0.05 * mag_mass, "kg", "catalog", catalog),
                        "DES-ECAL-001": row(ecal_mass, 0.05 * ecal_mass, "kg", "catalog", catalog)}}
    for q, unit in (("power", "W"), ("channel_count", "1"), ("data_rate", "Mbit/s")):
        budgets[q] = {sid: row(100.0, 20.0, unit) for sid in subs}
    return subs, budgets


# the 2.0 T solenoid and the coarser ECAL are lighter catalog items than the 3.8 T solenoid and the fine ECAL
CANDIDATES = {"cand-A": ("13 layers over 1.0 m in 3.8 T, fine-sampling ECAL", 13, 1.0, 3.8, (0.03, 0.12, 0.003), 1500.0,
                         12000.0, 9000.0),
              "cand-B": ("10 layers over 1.0 m in 2.0 T, coarser ECAL", 10, 1.0, 2.0, (0.05, 0.20, 0.005), 1480.0,
                         9000.0, 7000.0),
              "cand-P": ("probe: 6 layers over 0.4 m in 3.8 T", 6, 0.4, 3.8, (0.05, 0.20, 0.005), 700.0,
                         12000.0, 7000.0)}


def den(v, tol=0.0):
    return {"value": v, "tolerance": tol}


def spec() -> dict:
    req = lambda rid, q, cmp, tgt, unit, d, kind: {"id": f"{NS}:{rid}", "parents": [f"{NS}:PHY-001"], "quantity": q,  # noqa: E731
                                                   "comparator": cmp, "target": tgt, "unit": unit, "denominator": d,
                                                   "kind": kind}
    reqs = [dict(req("REQ-TRK-001", "momentum-resolution-core", "<=", 0.03, "1",
                     {"rigidity_GV": den(100.0), "species": den("muon")}, "driving"), allocation=f"{NS}:ALC-TRK-001"),
            dict(req("REQ-ECAL-001", "calorimeter-energy-resolution", "<=", 0.02, "1",
                     {"energy_GeV": den(50.0), "species": den("electron")}, "driving"), allocation=f"{NS}:ALC-ECAL-001"),
            req("REQ-HCAL-001", "hadronic-energy-resolution", "<=", 0.15, "1",
                {"energy_GeV": den(100.0), "species": den("pion")}, "derived"),
            req("REQ-TRG-001", "trigger-efficiency", ">=", 0.95, "1",
                {"species": den("muon"), "transverse_momentum_GeV": den(25.0)}, "derived"),
            req("REQ-PU-001", "pileup-robustness", "<=", 0.05, "1", {"mean_pileup": den(50.0)}, "derived"),
            req("REQ-CONT-001", "shower-containment", ">=", 0.95, "1",
                {"energy_GeV": den(50.0), "species": den("electron")}, "derived")]
    return {"design_id": NS, "spec_version": 1,
            "objectives": [{"id": f"{NS}:PHY-001", "description": "SYNTHETIC: dilepton resonance search at a collider",
                            "observable": "dimuon and dielectron invariant mass", "range": "100 GeV to 1 TeV",
                            "precision_goal": "dimuon mass resolution below 2.5% at 200 GeV (legs near 100 GeV: "
                                              "sigma_m/m ~ (sigma_p/p)/sqrt(2) for equal legs)"}],
            "requirements": reqs,
            "allocations": [
                {"id": f"{NS}:ALC-TRK-001", "requirement": f"{NS}:REQ-TRK-001", "rule": "quadrature", "independent": True,
                 "items": [{"name": "intrinsic", "value": 0.02}, {"name": "scattering", "value": 0.015},
                           {"name": "alignment", "value": 0.01}], "margin": 0.003},
                {"id": f"{NS}:ALC-ECAL-001", "requirement": f"{NS}:REQ-ECAL-001", "rule": "quadrature", "independent": True,
                 "items": [{"name": "stochastic", "value": 0.012}, {"name": "constant", "value": 0.01},
                           {"name": "leakage", "value": 0.008}], "margin": 0.002}],
            "constraints": [{"id": f"{NS}:CON-MASS-001", "type": "mass", "hardness": "hard", "quantity": "mass-budget",
                             "comparator": "<=", "target": 25000.0, "unit": "kg", "denominator": {}}],
            "comparison_basis": {"quantity": "mass-budget", "tolerance_relative": 0.05,
                                 "note": "candidates are compared at equal mass"}}


def envelope(atype, aid, ext):
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": aid, "artifact_type": atype, "objective": LABEL,
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION,
                         "profiles": {"experiment:synthetic-collider": PROFILE_VERSION}},
            "bindings": {"experiments": [{"profile": "experiment:synthetic-collider", "version": PROFILE_VERSION}],
                         "theory": []},
            "provenance": {"producer_skill": "hep-detector", "created": CREATED},
            "inputs": [], "outputs": [], "status": ["synthetic"], "unresolved_inputs": [], "extension": ext}


def evaluate(art: Path, *args: str) -> dict:
    p = subprocess.run([sys.executable, "-B", str(EVAL), *args, "--artifacts", str(art)], capture_output=True, text=True,
                       env=dict(os.environ, SOURCE_DATE_EPOCH=EPOCH), timeout=600)
    out = json.loads(p.stdout)
    if p.returncode != 0:
        raise RuntimeError(f"evaluate_design.py {args}: {out}")
    return out


def build(out: Path) -> dict:
    art, dec = out / "artifacts", out / "decisions"
    for d in (art, dec):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    (art / "design-spec.v1.json").write_text(json.dumps(envelope("design-spec", f"{NS}-spec-v1", spec()), indent=1) + "\n")
    (art / "candidates").mkdir()
    for name, (desc, n, lever, field, ecal, mass, mag_mass, ecal_mass) in CANDIDATES.items():
        subs, budgets = candidate(n, lever, field, ecal, mass, mag_mass, ecal_mass)
        ext = {"candidate_id": f"{NS}:{name}", "design_id": NS, "description": desc, "subsystems": subs, "budgets": budgets}
        (art / "candidates" / f"{name}.json").write_text(json.dumps(envelope("design-candidate", f"{NS}-{name}", ext),
                                                                    indent=1) + "\n")
    values, unavailable = {}, {}
    for name in CANDIDATES:
        c, cid = name.split("-")[1], f"{NS}:{name}"
        r = evaluate(art, "run", "--candidate", cid, "--requirement", "REQ-TRK-001", "--id", f"CALC-TRK-{c}",
                     "--status", "synthetic")
        e = evaluate(art, "run", "--candidate", cid, "--requirement", "REQ-ECAL-001", "--id", f"CALC-ECAL-{c}",
                     "--status", "synthetic")
        evaluate(art, "budget", "--candidate", cid, "--quantity", "mass", "--id", f"CALC-MASS-{c}", "--status",
                 "synthetic")
        for rid in UNAVAILABLE:
            u = evaluate(art, "run", "--candidate", cid, "--requirement", rid, "--id", f"EST-{rid[4:-4]}-{c}",
                         "--status", "synthetic")
            unavailable.setdefault(name, []).append(u["evaluation"])
        values[name] = {"resolution": r["value"], "ecal": e["value"]}
    # the H3 record the agent prepares for a human (EXB-02): candidates entering convergence and every unavailable record
    arts = [f"candidates/{n}.json" for n in ("cand-A", "cand-B")] + unavailable["cand-A"] + unavailable["cand-B"]
    rec = {"record_version": "1.1.0", "decision_id": f"{NS}-h3-prepared", "analysis": NS,
           "decision": "PREPARED by the agent for human approval: cand-A and cand-B enter convergence; cand-P is "
                       "screened out; hadronic resolution, trigger efficiency, pileup robustness and shower containment "
                       "have no evaluator (capability.unavailable) and need F4 studies",
           "category": "architecture-selection", "actor": {"kind": "agent", "id": "example-run"},
           "time": "2026-10-24T00:00:00Z", "seen": {"state": "not-applicable"},
           "artifacts": [{"ref": a, "sha256": hashlib.sha256((art / a).read_bytes()).hexdigest()} for a in arts]}
    (dec / "h3-prepared.json").write_text(json.dumps(rec, indent=1) + "\n")
    evaluate(art, "report", "--decisions", str(dec))
    return values


def criteria(full: dict) -> dict:
    rows = {(item["id"].split(":")[1], c.split(":")[1]): m for item in full["requirements"] for m in item["matrix"]
            for c in m["candidates"]}
    pair = lambda r, c: (rows[(r, c)]["result"], rows[(r, c)]["codes"])  # noqa: E731
    return {
        "no_design_errors": full["status"] == "ok" and not full["errors"],
        "probe_fails_resolution": pair("REQ-TRK-001", "cand-P") == ("fail", ["bound.excludes"]),
        "reasonable_inconclusive": all(pair(r, c) == ("inconclusive", ["bound.direction"])
                                       for r in ("REQ-TRK-001", "REQ-ECAL-001") for c in ("cand-A", "cand-B")),
        "unavailable_listed": all(pair(r, c) == ("inconclusive", ["capability.unavailable"])
                                  for r in UNAVAILABLE for c in ("cand-A", "cand-B", "cand-P"))
        and len(full["unavailable"]) == 12,
        "unavailable_in_h3_record": any(r["category"] == "architecture-selection" for r in full["gates"])
        and "gate.H3_missing" in full["gate_flags"],
        "equal_mass_basis_checked": full["comparison_basis"]["declared"] and len(full["comparison_basis"]["pairs"]) == 1
        and not full["comparison_basis"]["holds"] and full["comparison_basis"]["pairs"][0]["shared_items"] == [],
        "no_ranking_claimed": full["ranking"]["status"] == "refused" and len(full["ranking"]["reasons"]) == 2,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    values = build(args.out)
    full = derive(args.out / "artifacts", args.out / "decisions")
    passed = criteria(full)
    verdicts = {f"{item['id'].split(':')[1]} {c.split(':')[1]}": {"result": m["result"], "codes": m["codes"],
                                                                     "missing_evidence": m["missing_evidence"]}
                for item in full["requirements"] + full["constraints"] for m in item["matrix"] for c in m["candidates"]}
    results = {"label": LABEL, "design_id": NS, "evaluations": values, "verdicts": verdicts,
               "unavailable": full["unavailable"], "gate_flags": full["gate_flags"],
               "comparison_basis": {k: full["comparison_basis"].get(k) for k in ("declared", "holds", "reason")},
               "ranking": full["ranking"]["status"], "pass": passed,
               "note": "verdicts derived by contracts/design.py; F1 analysis can exclude but not approve; quantities "
                       "without an evaluator are recorded, never estimated"}
    (args.out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"pass": passed, "out": str(args.out)}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

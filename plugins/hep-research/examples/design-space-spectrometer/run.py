#!/usr/bin/env python3
"""Example A (detector system design spec, M1): an AMS-like space spectrometer designed through the F1 loop.

SYNTHETIC design study. Three candidates of a magnetic spectrometer are compared on a momentum-resolution
requirement and a charge-confusion requirement at 1000 GV, with an equal-mass comparison basis:
  cand-S  short lever arm (2.0 m), many layers (9);
  cand-L  long lever arm (3.0 m), few layers (5);
  cand-P  a probe with a deliberately too-short lever arm (0.6 m, 5 layers).
Public facts are cited through the evidence ledger of the public experiment:ams-02 profile (the 1.4 kG central field,
ams02:C93 and ams02:C112; 10 um per-layer resolution in the bending direction, ams02:C175; the 3.0 m L1-L9 lever arm,
ams02:C94); every other number is a proposal of this example and describes no real detector. The private
ams02-research profile is not used (OQ-20).

Chain (all through skills/hep-detector/scripts/evaluate_design.py, verdicts only from contracts/design.py):
1. design-spec (goal, two driving requirements with denominators and allocations, a hard mass constraint, the
   comparison basis) and the three candidates;
2. per candidate: F1 momentum resolution (tracker_resolution momentum), F1 Gaussian-core charge confusion fed by it
   (charge_confusion_rate gaussian-core), F1 mass budget (design_estimates budget-sum);
3. the design report (communication) with the compliance matrix.
Acceptance (M1): the same verdicts as the M0 fixtures (the probe fails resolution with bound.excludes; the two
reasonable candidates are inconclusive on resolution and charge confusion with bound.direction, with the missing F3,
F4 and data-validation evidence listed); the equal-mass basis is checked (it holds for the two candidates that survive
screening; the probe is screened out); no verdict is hand-written.

Usage (from the plugin root): python3 examples/design-space-spectrometer/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
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
EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
NS = "ams-like-v1"
CREATED = "2026-10-24"
EPOCH = "1792800000"  # 2026-10-24T00:00:00Z: SOURCE_DATE_EPOCH for reproducible envelopes
LABEL = "SYNTHETIC design study (AMS-like; not the AMS-02 detector)"
PUBLIC = "public-fact"


def param(value, unit, source="example proposal", status="proposal"):
    return {"value": value, "unit": unit, "source": source, "status": status}


def calib(method, samples):
    return {"method": method, "control_samples": samples}


def tracker(n_layers: int, lever_arm_m: float, lever_source: str = "example proposal") -> dict:
    pos = [round(i * lever_arm_m / (n_layers - 1), 6) for i in range(n_layers)]
    lever_status = PUBLIC if lever_source.startswith("ams02:") else "proposal"
    return {"role": "tracking", "technology": "double-sided silicon microstrip ladders",
            "parameters": {"layer_positions_m": param(pos, "m", lever_source, lever_status),
                           "point_resolution_um": param(10.0, "um", "ams02:C175", PUBLIC),
                           "layer_x_over_x0": param([0.01] * n_layers, "1"),
                           "passive_x_over_x0": param(0.03, "1")},
            "interfaces": ["DES-MAG-001"],
            "calibration": calib("track-based alignment with an infrared laser monitor", ["cosmic-ray protons",
                                                                                       "high-rigidity tracks"])}


def magnet() -> dict:
    return {"role": "bending", "technology": "permanent magnet (Nd-Fe-B)",
            "parameters": {"field_T": param(0.14, "T", "ams02:C93; ams02:C112", PUBLIC)},
            "interfaces": ["DES-TRK-001"], "calibration": calib("pre-flight field map, temperature correction",
                                                                  ["field map"])}


def row(estimate, sigma, unit, basis="estimate", source="example engineering estimate"):
    return {"allocation": round(estimate * 1.1, 6), "estimate": estimate, "uncertainty": sigma, "unit": unit,
            "basis": basis, "source": source, "fidelity": "F1"}


def budgets(trk_mass: float, n_layers: int) -> dict:
    weighed = "SYNTHETIC example: assumed weighed prototype components"
    return {"mass": {"DES-TRK-001": row(trk_mass, 0.02 * trk_mass, "kg", "measurement", weighed),
                     "DES-MAG-001": row(2000.0, 40.0, "kg", "measurement", weighed)},
            "power": {"DES-TRK-001": row(25.0 * n_layers, 5.0 * n_layers, "W"), "DES-MAG-001": row(0.0, 0.0, "W")},
            "channel_count": {"DES-TRK-001": row(20000.0 * n_layers, 4000.0 * n_layers, "1"),
                              "DES-MAG-001": row(0.0, 0.0, "1")},
            "data_rate": {"DES-TRK-001": row(0.5 * n_layers, 0.1 * n_layers, "Mbit/s"),
                          "DES-MAG-001": row(0.0, 0.0, "Mbit/s")}}


def den(v, tol=0.0):
    return {"value": v, "tolerance": tol}


def envelope(atype, aid, ext):
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": aid, "artifact_type": atype, "objective": LABEL,
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION}, "bindings": {"experiments": [], "theory": []},
            "provenance": {"producer_skill": "hep-detector", "created": CREATED,
                           "evidence_ids": ["ams02:C93", "ams02:C94", "ams02:C112", "ams02:C175"]},
            "inputs": [], "outputs": [], "status": ["synthetic"], "unresolved_inputs": [], "extension": ext}


def spec() -> dict:
    return {"design_id": NS, "spec_version": 1,
            "objectives": [{"id": f"{NS}:PHY-001", "description": "charge-separated proton and antiproton spectra",
                            "observable": "antiproton-to-proton flux ratio versus rigidity", "range": "1 GV to 1 TV",
                            "precision_goal": "statistics-limited at 1 TV"}],
            "requirements": [
                {"id": f"{NS}:REQ-TRK-001", "parents": [f"{NS}:PHY-001"], "quantity": "momentum-resolution-core",
                 "comparator": "<=", "target": 0.5, "unit": "1", "kind": "driving",
                 "denominator": {"rigidity_GV": den(1000.0), "species": den("proton")},
                 "allocation": f"{NS}:ALC-TRK-001", "verification": {"method": "analysis, then simulation with tails"}},
                {"id": f"{NS}:REQ-CC-001", "parents": [f"{NS}:PHY-001", f"{NS}:REQ-TRK-001"],
                 "quantity": "charge-confusion-rate", "comparator": "<=", "target": 0.05, "unit": "1", "kind": "driving",
                 "denominator": {"rigidity_GV": den(1000.0), "species": den("proton"), "charge_sign": den("positive"),
                                 "curvature_offset_per_GV": den(0.0)},
                 "allocation": f"{NS}:ALC-CC-001", "verification": {"method": "simulation validated with data"}}],
            "allocations": [
                {"id": f"{NS}:ALC-TRK-001", "requirement": f"{NS}:REQ-TRK-001", "rule": "quadrature", "independent": True,
                 "items": [{"name": "intrinsic", "value": 0.4}, {"name": "scattering", "value": 0.1},
                           {"name": "alignment", "value": 0.25}], "margin": 0.05},
                {"id": f"{NS}:ALC-CC-001", "requirement": f"{NS}:REQ-CC-001", "rule": "linear",
                 "items": [{"name": "Gaussian core", "value": 0.02}, {"name": "non-Gaussian tails", "value": 0.025}],
                 "margin": 0.005}],
            "constraints": [{"id": f"{NS}:CON-MASS-001", "type": "mass", "hardness": "hard", "quantity": "mass-budget",
                             "comparator": "<=", "target": 3000.0, "unit": "kg", "denominator": {}}],
            "comparison_basis": {"quantity": "mass-budget", "tolerance_relative": 0.05,
                                 "note": "candidates are compared at equal mass"}}


CANDIDATES = {"cand-S": ("short lever arm (2.0 m), many layers", 9, 2.0, "example proposal", 400.0),
              "cand-L": ("long lever arm (3.0 m), few layers", 5, 3.0, "ams02:C94", 395.0),
              "cand-P": ("probe: deliberately too-short lever arm (0.6 m)", 5, 0.6, "example proposal", 150.0)}


def evaluate(art: Path, *args: str) -> dict:
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)
    p = subprocess.run([sys.executable, "-B", str(EVAL), *args, "--artifacts", str(art)], capture_output=True,
                       text=True, env=env, timeout=600)
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
    for name, (desc, n, lever, lever_src, trk_mass) in CANDIDATES.items():
        ext = {"candidate_id": f"{NS}:{name}", "design_id": NS, "description": desc,
               "subsystems": {"DES-TRK-001": tracker(n, lever, lever_src), "DES-MAG-001": magnet()},
               "budgets": budgets(trk_mass, n)}
        (art / "candidates").mkdir(exist_ok=True)
        (art / "candidates" / f"{name}.json").write_text(json.dumps(envelope("design-candidate", f"{NS}-{name}", ext),
                                                                    indent=1) + "\n")
    runs = {}
    for name in CANDIDATES:
        c = name.split("-")[1]
        cid = f"{NS}:{name}"
        r = evaluate(art, "run", "--candidate", cid, "--requirement", "REQ-TRK-001", "--id", f"CALC-TRK-{c}",
                     "--status", "synthetic")
        cc = evaluate(art, "run", "--candidate", cid, "--requirement", "REQ-CC-001", "--id", f"CALC-CC-{c}",
                      "--upstream", r["evaluation"], "--status", "synthetic")
        m = evaluate(art, "budget", "--candidate", cid, "--quantity", "mass", "--id", f"CALC-MASS-{c}",
                     "--status", "synthetic")
        runs[name] = {"resolution": r["value"], "resolution_bound": r["bound"], "charge_confusion": cc["value"],
                      "charge_confusion_bound": cc["bound"], "mass_kg": m["value"]}
    rep = evaluate(art, "report", "--decisions", str(dec))
    return {"evaluations": runs, "report": rep["report"]}


def summarize(full: dict) -> dict:
    rows = {}
    for item in full["requirements"] + full["constraints"]:
        for m in item["matrix"]:
            for c in m["candidates"]:
                rows[f"{item['id'].split(':')[1]} {c.split(':')[1]}"] = {
                    "result": m["result"], "codes": m["codes"], "provisional": m["provisional"],
                    "missing_evidence": m["missing_evidence"], "status_axis": m["maturity"]["status_axis"]}
    return rows


def criteria(rows: dict, full: dict) -> dict:
    trk = lambda c: rows[f"REQ-TRK-001 {c}"]  # noqa: E731
    cc = lambda c: rows[f"REQ-CC-001 {c}"]  # noqa: E731
    return {
        "no_design_errors": full["status"] == "ok" and not full["errors"],
        "probe_fails_resolution": (trk("cand-P")["result"], trk("cand-P")["codes"]) == ("fail", ["bound.excludes"]),
        "reasonable_inconclusive": all((x(c)["result"], x(c)["codes"]) == ("inconclusive", ["bound.direction"])
                                       for c in ("cand-S", "cand-L") for x in (trk, cc)),
        "missing_evidence_listed": all(any("F3" in e for e in trk(c)["missing_evidence"])
                                       and any("at F4" in e for e in cc(c)["missing_evidence"])
                                       and any("data-validation" in e for e in cc(c)["missing_evidence"])
                                       for c in ("cand-S", "cand-L")),
        "probe_screened_out": [c["candidates"] for c in full["candidates"] if c["screened_out"]] == [[f"{NS}:cand-P"]],
        "equal_mass_basis_checked": full["comparison_basis"]["declared"] and full["comparison_basis"]["holds"]
        and len(full["comparison_basis"]["pairs"]) == 1,
        "no_ranking_claimed": full["ranking"]["status"] in ("not-provided", "refused"),
        "gate_flags_shown": full["gate_flags"] == ["gate.H1_missing", "gate.H2_missing", "gate.H3_missing"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    built = build(args.out)
    full = derive(args.out / "artifacts", args.out / "decisions")
    rows = summarize(full)
    passed = criteria(rows, full)
    results = {"label": LABEL, "design_id": NS, "evaluations": built["evaluations"], "verdicts": rows,
               "comparison_basis": {k: full["comparison_basis"].get(k) for k in ("declared", "holds", "reason")},
               "ranking": full["ranking"]["status"], "gate_flags": full["gate_flags"], "pass": passed,
               "note": "verdicts derived by contracts/design.py; F1 analysis can exclude but not approve a candidate"}
    (args.out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"pass": passed, "out": str(args.out)}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

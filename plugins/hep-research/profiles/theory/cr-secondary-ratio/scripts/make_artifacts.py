#!/usr/bin/env python3
"""Write the envelope artifacts of theory:cr-secondary-ratio: the theory-spec (derivations/theory-spec.json) and the
benchmark prediction (predictions/bc-benchmark.prediction.json), both checked with contracts/validate.py by the tests.

The prediction is the 1D thin-disc ratio at the benchmark parameter point, averaged in ln(E/n) over the benchmark
bins, with the alternative ILLUSTRATIVE cross-section set as a model-alternative uncertainty object. To produce a
prediction at another parameter point, pass --set KEY=VALUE (same keys as predict.py) and --out-dir.

Usage: python3 make_artifacts.py [--check] [--set D0_cm2_s=2e28 ...] [--out-dir DIR]
  --check: exit 1 if the stored artifacts differ from what would be written (no file written).
Exit 0 ok, 1 stored artifacts are stale (--check), 2 bad input, 3 numpy/scipy missing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
sys.path.insert(0, str(HERE))

PROFILE_ID, PROFILE_VERSION = "theory:cr-secondary-ratio", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.21.0", "3.3.0"
CREATED = "2026-10-15"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
PRED_PATH = PROFILE / "predictions" / "bc-benchmark.prediction.json"
CORE_KEYS = ("unit_system", "hbar_c_one", "metric_signature", "coupling_normalization", "renormalization_scheme",
             "scales", "energy_variable", "frame", "angle_definition", "spin_treatment", "mass_approximation")


def _envelope(artifact_id: str, artifact_type: str, objective: str, status: list[str], ext: dict,
              inputs: list | None = None) -> dict:
    return {"contract_version": CONTRACTS, "artifact_id": artifact_id, "artifact_type": artifact_type,
            "objective": objective, "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                                 "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED,
                           "evidence_ids": ["crsr:C01", "crsr:C02", "crsr:C04", "crsr:C05"]},
            "inputs": inputs or [], "outputs": [], "status": status, "unresolved_inputs": [], "extension": ext}


def theory_spec(cfg: dict, conventions: dict) -> dict:
    t = cfg["transport"]
    ext = {
        "model": {"id": "crsr-thin-disc-1d-diffusion",
                  "description": "1D diffusion halo of half-height L with a thin gas and source disc of half-thickness h, "
                                 "D(R) = D0 beta (R/R0)^delta, no convection, reacceleration, energy losses or decay; "
                                 "equivalent to a weighted slab with lambda_esc = n_H m_H h v L / D",
                  "family": "cosmic-ray-propagation"},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "steady state; free escape at |z| = L; observer at the mid-plane z = 0",
            "thin disc (h << L): gas and sources in 2 h delta(z); hydrogen target only",
            "kinetic energy per nucleon conserved in fragmentation (straight-ahead)",
            "parents (C, O) are pure primaries with observed ratios given as input; one effective stable secondary",
            "cross sections are inputs: effective cumulative, energy independent, ILLUSTRATIVE values",
            "local interstellar ratio: no solar modulation"],
        "conventions": {k: conventions[k] for k in CORE_KEYS} | {k: v for k, v in conventions.items() if ":" in k},
        "order": "not-applicable (classical transport model, no perturbative expansion)",
        "parameters": {k: t[k] for k in ("D0_cm2_s", "L_kpc", "h_kpc", "n_H_cm3", "delta", "R0_GV")}
                      | {"cross_section_set": cfg["cross_section_set"]},
        "scales": {"R0_GV": t["R0_GV"], "meaning": "reference rigidity of the diffusion coefficient"},
        "derivation_status": "analytic-derivation",
        "validity_domain": {"kinetic_energy_per_nucleon_gev": [cfg["energy_bin_edges_gev_per_n"][0],
                                                                cfg["energy_bin_edges_gev_per_n"][-1]],
                            "geometry": "h << L (thin disc); corrections O(h/L) quantified in the benchmark",
                            "physics": "energies where convection, reacceleration and energy losses are negligible; "
                                       "the model is not claimed to describe low energies"},
        "checks_run": [
            {"name": "slab path-length average equals the closed form (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "thin-disc jump solution and linear halo profile (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "thin disc equals weighted slab with lambda_esc = n_H m_H h v L / D (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "ratio invariant under D0 and L scaled together, not under D0 alone (SymPy and numerical)",
             "result": "pass", "tolerance": "exact; 1e-12 relative numerically"},
            {"name": "finite-disc closed form solves both regions and matches at z = h (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "slab ODE integration averaged over the path-length distribution vs closed form",
             "result": "pass", "tolerance": 1e-7},
            {"name": "finite-volume solution vs finite-disc closed form", "result": "pass", "tolerance": 1e-6},
            {"name": "finite-disc ratio tends to the thin-disc closed form as h/L -> 0", "result": "pass",
             "tolerance": "monotonic; < 1e-3 at h = 1.6 pc"},
            {"name": "units and dimensions (grammage in g/cm^2, ratio dimensionless)", "result": "pass",
             "tolerance": "exact"}],
        "checks_not_run": ["comparison with a published numerical B/C benchmark (open question B1)",
                           "comparison with any propagation code (none run)",
                           "comparison with measured data"],
        "references_read": [],
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "coupling_normalization", "renormalization_scheme", "angle_definition",
                         "spin_treatment"],
        "neglected": ["convection (Galactic wind)", "reacceleration", "ionization and Coulomb losses",
                      "radioactive decay and unstable secondaries", "parent-to-parent spallation and tertiaries",
                      "energy dependence of the cross sections", "helium in the interstellar gas",
                      "radial (2D) structure of the Galaxy", "solar modulation"],
        "degenerate_directions": ["D0/L"],
    }
    return _envelope("crsr-theory-spec-thin-disc-1d", "theory-spec",
                     "Theory spec of the B/C ratio in the 1D thin-disc diffusion model of theory:cr-secondary-ratio "
                     "(equivalent weighted slab), with its degenerate direction D0/L", ["synthetic", "unvalidated"], ext)


def prediction(cfg: dict, conventions: dict, overrides: dict | None = None) -> dict:
    import predict
    edges = cfg["energy_bin_edges_gev_per_n"]
    nominal = predict.bin_averaged(cfg, edges, overrides)
    point = predict.evaluate(dict(cfg, energies_gev_per_n=[edges[0]]), overrides)["parameter_point"]
    alts = []
    for alt in cfg.get("alternative_cross_section_sets", []):
        vals = predict.bin_averaged(cfg, edges, overrides, alt)
        alts.append({"name": f"cross-section set {Path(alt).stem}", "kind": "model-alternative",
                     "correlation": "fully-correlated", "gaussian": False,
                     "values": [a - b for a, b in zip(vals, nominal)]})
    obs_conv = {k: conventions[k] for k in ("unit_system", "energy_variable", "frame", "mass_approximation")}
    obs_conv |= {k: v for k, v in conventions.items() if ":" in k}
    ext = {
        "observable": {
            "quantity": "ratio",
            "process": "secondary-to-primary ratio B/C from spallation of C and O on interstellar hydrogen",
            "species": [{"name": "boron"}, {"name": "carbon"}],
            "variables": [{"name": "kinetic_energy_per_nucleon", "unit": "GeV/n", "edges": edges}],
            "phase_space": {"definition": "local interstellar ratio at the Galactic mid-plane (z = 0), before solar "
                                          "modulation", "fiducial": False},
            "level": "crsr:local-interstellar",
            "frame": "Galactic rest frame (interstellar gas at rest)",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "ratio of two fluxes at the same E/n; the normalization cancels"},
            "bin_semantics": "bin-averaged",
            "unit": "1",
            "conventions": obs_conv,
            "validity_range": {"variable": "kinetic_energy_per_nucleon", "min": edges[0], "max": edges[-1],
                               "unit": "GeV/n"}},
        "theory_spec_ref": "derivations/theory-spec.json",
        "derivation_status": "analytic-derivation",
        "parameter_point": point | {"cross_section_set": cfg["cross_section_set"]},
        "representation": "numerical",
        "values": {"edges": edges, "values": nominal, "unit": "1"},
        "uncertainties": alts,
        "allowed_transformations": ["solar modulation (outside this profile; force field in hep-measurement)",
                                    "rebin (recompute the ln(E/n) average; never merge averaged values)"],
    }
    spec_ref = "derivations/theory-spec.json"
    return _envelope("crsr-prediction-bc-benchmark", "prediction",
                     "B/C in the 1D thin-disc diffusion model at the ILLUSTRATIVE benchmark parameter point "
                     "(synthetic cross sections; not a statement about the Galaxy)", ["synthetic", "unvalidated"],
                     ext, inputs=[{"ref": spec_ref, "artifact_type": "theory-spec",
                                   "artifact_id": "crsr-theory-spec-thin-disc-1d", "status": ["synthetic", "unvalidated"]}])


def same(a, b, rel: float = 1e-9) -> bool:
    """Structural equality with a relative tolerance on floats (recomputation may differ in the last bits)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= rel * max(abs(a), abs(b))
    return a == b


def build(overrides: dict | None = None) -> dict[Path, dict]:
    import predict
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    conventions = predict.load_json(PROFILE / "conventions.json")
    return {SPEC_PATH: theory_spec(cfg, conventions), PRED_PATH: prediction(cfg, conventions, overrides)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--out-dir", type=Path)
    opts = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}"}))
        return 3
    import predict
    try:
        arts = build(predict._parse_assign(opts.set, many=False))
    except (predict.InputError, KeyError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    stale = []
    for path, doc in arts.items():
        text = json.dumps(doc, indent=1) + "\n"
        target = (opts.out_dir / path.name) if opts.out_dir else path
        if opts.check:
            if not target.exists() or not same(json.loads(target.read_text(encoding="utf-8")), json.loads(text)):
                stale.append(str(target))
        else:
            target.write_text(text, encoding="utf-8")
    print(json.dumps({"status": "stale" if stale else "ok", "stale": stale,
                      "written": [] if opts.check else [str(p) for p in arts]}))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())

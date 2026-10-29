#!/usr/bin/env python3
"""Write the envelope artifacts of theory:cr-secondary-antiprotons: the theory-spec (derivations/theory-spec.json) and
the benchmark prediction (predictions/source-term-benchmark.prediction.json), both checked with contracts/validate.py
by the tests.

The prediction is the total source term (all four channels, antineutrons and hyperons included) averaged linearly in
T_pbar over the benchmark bins, with two model-alternative uncertainty objects: the alternative ILLUSTRATIVE toy
cross-section set, and the antineutron treatment without isospin enhancement (Delta_IS = 0, the traditional factor 2).
Its model.family is a source term, not a propagation family, so no degenerate_directions are required.

Usage: python3 make_artifacts.py [--check]
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

PROFILE_ID, PROFILE_VERSION = "theory:cr-secondary-antiprotons", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.46.0", "3.17.0"
CREATED = "2026-10-15"
MODEL_FAMILY = "cosmic-ray-secondary-source-term"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
PRED_PATH = PROFILE / "predictions" / "source-term-benchmark.prediction.json"
CORE_KEYS = ("unit_system", "hbar_c_one", "metric_signature", "coupling_normalization", "renormalization_scheme",
             "scales", "energy_variable", "frame", "angle_definition", "spin_treatment", "mass_approximation")
EVIDENCE = ["crpb:C01", "crpb:C02", "crpb:C04", "crpb:C05", "crpb:C06"]


def _envelope(artifact_id: str, artifact_type: str, objective: str, ext: dict, inputs: list | None = None) -> dict:
    return {"contract_version": CONTRACTS, "artifact_id": artifact_id, "artifact_type": artifact_type,
            "objective": objective, "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                                 "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED, "evidence_ids": EVIDENCE},
            "inputs": inputs or [], "outputs": [], "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
            "extension": ext}


def theory_spec(cfg: dict, conventions: dict) -> dict:
    import predict
    xs = predict.load_cross_sections(cfg)
    ext = {
        "model": {"id": "crpb-source-term-toy-xscaling",
                  "description": "secondary antiproton source term q(T) = sum_ij 4 pi n_j int phi_i dsigma_ij/dT dT_i "
                                 "for p and He projectiles on H and He gas, prompt antiprotons times the antineutron and "
                                 "hyperon factor; toy x-scaling pp cross section with constant channel rescaling",
                  "family": MODEL_FAMILY},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "steady, spatially uniform gas and primary fluxes (a local source term, before propagation)",
            "projectiles p and He, targets H and He; heavier nuclei neglected",
            "nuclear channels obtained from pp by constant factors at the same energy per nucleon (ILLUSTRATIVE)",
            "antineutrons and hyperon feed-down as multiplicative factors on the prompt antiproton cross section",
            "cross sections are inputs: a toy x-scaling form with ILLUSTRATIVE parameters, not a published parametrization",
            "primary fluxes are inputs: ILLUSTRATIVE power laws in kinetic energy per nucleon"],
        "conventions": {k: conventions[k] for k in CORE_KEYS} | {k: v for k, v in conventions.items() if ":" in k},
        "order": "not-applicable (source integral over a parametrized cross section, no perturbative expansion)",
        "parameters": {"n_H_cm3": cfg["ism"]["n_H_cm3"], "He_to_H": cfg["ism"]["He_to_H"],
                       "primaries": cfg["primaries"], "antineutrons": cfg["antineutrons"],
                       "hyperons": cfg["hyperons"], "cross_section_set": cfg["cross_section_set"],
                       "threshold_gev_per_n": predict.threshold(xs)},
        "scales": {"T0_gev": 1.0, "meaning": "reference energy per nucleon of the primary power laws"},
        "derivation_status": "analytic-derivation",
        "validity_domain": {"antiproton_kinetic_energy_gev": [cfg["energy_bin_edges_gev"][0],
                                                              cfg["energy_bin_edges_gev"][-1]],
                            "physics": "the toy cross section is a placeholder: the result tests the source-integral "
                                       "machinery and its bookkeeping, it is not a physical antiproton source term"},
        "checks_run": [
            {"name": "substitution x = T/T_i maps the source integral to an incomplete beta function (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "above threshold: beta function B(gamma, n + 1) for symbolic gamma, n = 0, 1, 2, 3, 7 (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "below threshold: incomplete beta B(T/T_th; gamma, n + 1), n = 2 (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "antineutron and hyperon bookkeeping equals 2 + Delta_IS + 2 Delta_Lambda (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "numerical quadrature vs closed form, four channels, power-law and broken power-law primaries, "
                     "energies on both sides of the threshold", "result": "pass", "tolerance": 1e-8},
            {"name": "hand-computed point (n = 0, pure power law)", "result": "pass", "tolerance": 1e-10},
            {"name": "units and dimensions (q in cm^-3 s^-1 GeV^-1)", "result": "pass", "tolerance": "exact"}],
        "checks_not_run": ["comparison with published source-term values (open question B2: which table or figure, "
                           "and whether digitizing a figure is acceptable)",
                           "any published cross-section parametrization (none is reproduced; the toy sets are "
                           "ILLUSTRATIVE)",
                           "propagation of the source term and comparison with measured antiproton fluxes",
                           "degenerate-direction analysis: not applicable, model.family is a source term, not "
                           "cosmic-ray-propagation, so contracts/validate.py does not require degenerate_directions"],
        "references_read": [],
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "coupling_normalization", "renormalization_scheme", "angle_definition",
                         "spin_treatment"],
        "neglected": ["energy dependence of the channel rescaling", "nuclear threshold lowering (Fermi motion)",
                      "projectiles and targets heavier than helium", "tertiary antiprotons",
                      "energy dependence of Delta_IS and Lambda-bar/pbar", "kinematic dependence of the threshold on "
                                                                           "T_pbar"],
    }
    return _envelope("crpb-theory-spec-source-term", "theory-spec",
                     "Theory spec of the secondary antiproton source term of theory:cr-secondary-antiprotons (pp, pHe, "
                     "Hep, HeHe; antineutrons and hyperons) with an ILLUSTRATIVE toy cross section", ext)


def prediction(cfg: dict, conventions: dict) -> dict:
    import predict
    edges = cfg["energy_bin_edges_gev"]
    nominal = predict.bin_averaged(cfg, edges)
    alts = []
    for alt in cfg.get("alternative_cross_section_sets", []):
        vals = predict.bin_averaged(cfg, edges, alt)
        alts.append({"name": f"cross-section set {Path(alt).stem}", "kind": "model-alternative",
                     "correlation": "fully-correlated", "gaussian": False,
                     "values": [a - b for a, b in zip(vals, nominal)]})
    xs = predict.load_cross_sections(cfg)
    no_is = dict(xs, antineutron={"Delta_IS": 0.0})
    scale = predict.factor_parts(cfg, no_is)["factor"] / predict.factor_parts(cfg, xs)["factor"]
    alts.append({"name": "antineutrons without isospin enhancement (Delta_IS = 0, traditional factor 2)",
                 "kind": "model-alternative", "correlation": "fully-correlated", "gaussian": False,
                 "values": [v * scale - v for v in nominal]})
    obs_conv = {k: conventions[k] for k in ("unit_system", "energy_variable", "frame", "mass_approximation")}
    obs_conv |= {k: v for k, v in conventions.items() if ":" in k}
    ext = {
        "observable": {
            "quantity": "rate",
            "process": "secondary antiproton production (prompt, from antineutrons and from hyperons) by cosmic-ray p "
                       "and He on interstellar H and He",
            "species": [{"name": "antiproton"}],
            "variables": [{"name": "antiproton_kinetic_energy", "unit": "GeV", "edges": edges}],
            "phase_space": {"definition": "local interstellar source term per unit volume, before propagation",
                            "fiducial": False},
            "level": "crpb:interstellar-source",
            "frame": "Galactic rest frame (interstellar gas at rest)",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "absolute production rate per unit volume and energy; no instrument "
                                            "normalization applies"},
            "bin_semantics": "bin-averaged",
            "unit": "cm^-3 s^-1 GeV^-1",
            "conventions": obs_conv,
            "validity_range": {"antiproton_kinetic_energy": [edges[0], edges[-1]]}},
        "theory_spec_ref": "derivations/theory-spec.json",
        "derivation_status": "analytic-derivation",
        "parameter_point": {"n_H_cm3": cfg["ism"]["n_H_cm3"], "He_to_H": cfg["ism"]["He_to_H"],
                            "primaries": cfg["primaries"], "antineutrons": cfg["antineutrons"],
                            "hyperons": cfg["hyperons"], "cross_section_set": cfg["cross_section_set"]},
        "representation": "numerical",
        "values": {"edges": edges, "values": nominal, "unit": "cm^-3 s^-1 GeV^-1"},
        "uncertainties": alts,
        "allowed_transformations": ["propagation (outside this profile)",
                                    "rebin (recompute the linear average; never merge averaged values without widths)"],
    }
    return _envelope("crpb-prediction-source-term-benchmark", "prediction",
                     "Secondary antiproton source term at the ILLUSTRATIVE benchmark point (toy cross sections; not a "
                     "statement about the Galaxy)", ext,
                     inputs=[{"ref": "derivations/theory-spec.json", "artifact_type": "theory-spec",
                              "artifact_id": "crpb-theory-spec-source-term", "status": ["synthetic", "unvalidated"]}])


def same(a, b, rel: float = 1e-9) -> bool:
    """Structural equality with a relative tolerance on floats (recomputation may differ in the last bits)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= rel * max(abs(a), abs(b))
    return a == b


def build() -> dict[Path, dict]:
    import predict
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    conventions = predict.load_json(PROFILE / "conventions.json")
    return {SPEC_PATH: theory_spec(cfg, conventions), PRED_PATH: prediction(cfg, conventions)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    opts = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}"}))
        return 3
    import predict
    try:
        arts = build()
    except (predict.InputError, KeyError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    stale = []
    for path, doc in arts.items():
        text = json.dumps(doc, indent=1) + "\n"
        if opts.check:
            if not path.exists() or not same(json.loads(path.read_text(encoding="utf-8")), json.loads(text)):
                stale.append(str(path))
        else:
            path.write_text(text, encoding="utf-8")
    print(json.dumps({"status": "stale" if stale else "ok", "stale": stale,
                      "written": [] if opts.check else [str(p) for p in arts]}))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Write the theory-spec of theory:heliospheric-modulation (derivations/theory-spec.json), checked with
contracts/validate.py by the tests. Standard library only.

Usage: python3 make_artifacts.py [--check]
  --check: exit 1 if the stored theory-spec differs from what would be written (no file written).
Exit 0 ok, 1 stale (--check).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
PROFILE_ID, PROFILE_VERSION = "theory:heliospheric-modulation", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.15.0", "2.12.0"
CREATED = "2026-10-15"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
CORE_KEYS = ("unit_system", "hbar_c_one", "metric_signature", "coupling_normalization", "renormalization_scheme",
             "scales", "energy_variable", "frame", "angle_definition", "spin_treatment", "mass_approximation")


def theory_spec(conventions: dict, cfg: dict) -> dict:
    ext = {
        "model": {"id": "helmod-force-field",
                  "description": "Force-field approximation of solar modulation: zero radial streaming, spherical "
                                 "symmetry, steady state, diffusion coefficient kappa_1(r) beta R; "
                                 "J_TOA(T) = p(T)^2 / p(T + |Z| phi)^2 J_LIS(T + |Z| phi). Numbers come from the "
                                 "hep-measurement force-field script; the closed forms for a power-law LIS are the "
                                 "benchmark",
                  "family": "heliospheric-modulation"},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "zero radial streaming (force-field equation); spherical symmetry; steady state within a period",
            "diffusion coefficient separable and proportional to rigidity: kappa = kappa_1(r) beta R",
            "phi(r) = int_r^r_b V / (3 kappa_1) dr', zero at the modulation boundary r_b",
            "one modulation potential phi per period; no charge-sign, drift, latitude or transient effects",
            "LIS given as input (power law in the benchmark, synthetic normalization and index)"],
        "conventions": {k: conventions[k] for k in CORE_KEYS} | {k: v for k, v in conventions.items() if ":" in k},
        "order": "not-applicable (closed-form solution of the force-field equation, no perturbative expansion)",
        "parameters": {"phi_gv": cfg["phi_gv"], "lis_normalization": cfg["lis"]["normalization"],
                       "lis_index": cfg["lis"]["index"], "species": [s["name"] for s in cfg["species"]]},
        "scales": "not-applicable",
        "derivation_status": "analytic-derivation",
        "validity_domain": {
            "kinetic_energy_per_nucleon_gev": "above about 0.30 (protons) and 0.25 (alpha particles) [helmod:C03]; "
                                              "other species not stated",
            "physics": "steady modulation within a period; charge-sign, drift and transient effects absent "
                       "[helmod:C05]"},
        "checks_run": [
            {"name": "f = F(T + Z phi) solves the force-field equation; F(T - Z phi) does not (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "T + Z phi constant along the characteristic (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "p^2 = T (T + 2m) = E^2 - m^2, the Gleeson-Axford invariant (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "per-nucleon and rigidity closed forms equal the total-energy relation times the Jacobians "
                     "(SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "limits: phi -> 0 returns the LIS; ratio 1 - (gamma + 2) Z phi / T at large T; flux linear "
                     "in T as T -> 0 (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "hep-measurement force-field script vs closed form, 90 synthetic points (2 species, 3 phi, "
                     "3 energy kinds)", "result": "pass", "tolerance": cfg["relative_tolerance"]},
            {"name": "script demodulate inverts its own modulate (round trip)", "result": "pass",
             "tolerance": cfg["relative_tolerance"]},
            {"name": "units: phi in GV, |Z| phi in GeV with e = 1; flux ratio dimensionless", "result": "pass",
             "tolerance": "exact"}],
        "checks_not_run": [
            "comparison with a numerical transport solution (with streaming) or a drift model",
            "comparison with a published modulated spectrum or phi series",
            "comparison with measured fluxes"],
        "references_read": [],
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "coupling_normalization", "renormalization_scheme", "scales",
                         "angle_definition", "spin_treatment", "order"],
        "neglected": ["radial streaming (adiabatic and convective terms beyond the force-field limit)",
                      "gradient, curvature and current-sheet drifts (charge-sign dependence)",
                      "latitude dependence and non-spherical heliosphere", "time dependence within a period",
                      "Forbush decreases and solar energetic particle events"],
        "degenerate_directions": ["phi vs LIS spectral shape (injection and transport parameters)"],
    }
    return {"contract_version": CONTRACTS, "artifact_id": "helmod-theory-spec-force-field",
            "artifact_type": "theory-spec",
            "objective": "Theory spec of force-field solar modulation in theory:heliospheric-modulation, with its "
                         "validity range, its limits and the power-law closed-form benchmark",
            "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID, "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED,
                           "evidence_ids": ["helmod:C01", "helmod:C03", "helmod:C04", "helmod:C05"]},
            "inputs": [], "outputs": [], "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
            "extension": ext}


def build() -> dict:
    conventions = json.loads((PROFILE / "conventions.json").read_text(encoding="utf-8"))
    cfg = json.loads((PROFILE / "benchmarks" / "power-law-benchmark.json").read_text(encoding="utf-8"))
    return theory_spec(conventions, cfg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    opts = ap.parse_args(argv)
    text = json.dumps(build(), indent=1) + "\n"
    if opts.check:
        stale = not SPEC_PATH.exists() or json.loads(SPEC_PATH.read_text(encoding="utf-8")) != json.loads(text)
        print(json.dumps({"status": "stale" if stale else "ok", "path": str(SPEC_PATH)}))
        return 1 if stale else 0
    SPEC_PATH.write_text(text, encoding="utf-8")
    print(json.dumps({"status": "ok", "written": [str(SPEC_PATH)]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

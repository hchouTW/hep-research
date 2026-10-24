#!/usr/bin/env python3
"""Write the envelope artifacts of theory:dis-parton-model: the theory-spec (derivations/theory-spec.json) and the
toy-grid prediction (predictions/fl-toy-grid.prediction.json), both checked with contracts/validate.py by the tests.

The prediction is SYNTHETIC: F_2 at O(alpha_s^0) and F_L at O(alpha_s^1) on invented Beta-form densities and invented
alpha_s values (benchmarks/toy-closed-form.json). It is a symbolic prediction (the Altarelli-Martinelli expression)
with its evaluation at the toy points in 'point_values'; no published F_L number was read, so nothing here is a
published benchmark.

Usage: python3 make_artifacts.py [--check]
  --check: exit 1 if the stored artifacts differ from what would be written (no file written).
Exit 0 ok, 1 stored artifacts are stale (--check), 2 bad input, 3 numpy/scipy missing.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True  # importing siblings or core leaves no __pycache__ (F-10)
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
sys.path.insert(0, str(HERE))

PROFILE_ID, PROFILE_VERSION = "theory:dis-parton-model", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.38.0", "3.12.0"
CREATED = "2026-10-23"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
PRED_PATH = PROFILE / "predictions" / "fl-toy-grid.prediction.json"
SPEC_ID = "dispm-theory-spec-fl-alpha-s"
EVIDENCE = ["dispm:C01", "dispm:C02", "dispm:C03", "dispm:C04"]
AM_FORM = ("F_L(x, Q^2) = (alpha_s(Q^2)/(4 pi)) x^2 int_x^1 dz/z^3 [ 4 C_F F_2(z) + 8 sum_q e_q^2 (1 - x/z) z g(z) ], "
           "C_F = 4/3; F_2(z) = z sum_q e_q^2 (q(z) + qbar(z))")
REFERENCES = [
    {"citation": "E.C. Aschenauer, R.S. Thorne and R. Yoshida, 'Structure Functions', in F. Takahashi et al. (Particle "
                 "Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026)",
     "location": "Eq. (18.17) p. 4; Sec. 18.2.1 Eq. (18.18) p. 5; Sec. 18.2.2 Eqs. (18.21)-(18.22) p. 7",
     "date_read": "2026-10-23"},
    {"citation": "S. Moch, J.A.M. Vermaseren and A. Vogt, 'The Longitudinal Structure Function at the Third Order', "
                 "arXiv:hep-ph/0411112v2, Phys. Lett. B 606 (2005) 123",
     "location": "Eqs. (1)-(3) and surrounding text (printed pp. 1-2); <e^k> definition below Eq. (11) (p. 3)",
     "date_read": "2026-10-23"}]


def _envelope(artifact_id: str, artifact_type: str, objective: str, ext: dict, inputs: list | None = None) -> dict:
    return {"contract_version": CONTRACTS, "artifact_id": artifact_id, "artifact_type": artifact_type,
            "objective": objective, "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                                 "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED, "evidence_ids": EVIDENCE},
            "inputs": inputs or [], "outputs": [], "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
            "extension": ext}


def theory_spec(cfg: dict, conventions: dict) -> dict:
    ext = {
        "model": {"id": "dispm-lo-parton-model-fl-alpha-s",
                  "description": "LO quark-parton-model F_2 (photon exchange) and the O(alpha_s) longitudinal "
                                 "structure function from the LO coefficient functions, in the Altarelli-Martinelli "
                                 "form: " + AM_FORM,
                  "family": "dis-structure-functions"},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "photon exchange only; massless quarks, n_f effectively massless flavours (zero-mass scheme)",
            "leading twist: power corrections and target-mass corrections O(M^2/Q^2) dropped (PDG Eq. 18.21)",
            "x^-1 F_L = C_L,ns (x) q_ns + <e^2> (C_L,q (x) q_s + C_L,g (x) g) with the O(alpha_s) coefficients of "
            "Moch, Vermaseren and Vogt (c_ns = 4 C_F x, c_ps = 0, c_g = 8 n_f x (1 - x)), mu_R = mu_F = Q",
            "q_ns = sum (e_i^2 - <e^2>)(q_i + qbar_i): the non-singlet combination that reproduces LO F_2 (identified "
            "by this profile; the paper does not write it out)",
            "parton densities and alpha_s are inputs; in this profile they are SYNTHETIC toys, not evolved in Q^2"],
        "conventions": dict(conventions),
        "order": "F_L at O(alpha_s^1) (its leading order, absolute order alpha_s^1); F_2 at O(alpha_s^0)",
        "parameters": {"C_F": cfg["C_F"], "n_f": len(cfg["flavours"]),
                       "charges": {fl["name"]: fl["charge"] for fl in cfg["flavours"]},
                       "toy_densities": "benchmarks/toy-closed-form.json (SYNTHETIC)"},
        "scales": {"mu_R": "Q", "mu_F": "Q", "source": "dispm:C04"},
        "derivation_status": "perturbative-argument",
        "validity_domain": {
            "kinematics": "Q^2 >> M^2 (leading twist), W^2 well above the resonance region; x not so small that "
                          "small-x resummation matters, not so large that target-mass and higher-twist terms do "
                          "(no numerical bound is derived here)",
            "order": "F_L at its leading order only: NLO and NNLO coefficient functions (Moch, Vermaseren and Vogt "
                     "Eqs. 4-10) are not included",
            "inputs": "synthetic toy densities and toy alpha_s values; the numbers say nothing about a real nucleon"},
        "checks_run": [
            {"name": "change of variables z = x/y in int_x^1 dy/y C(y) f(x/y) gives int_x^1 dz/z C(x/z) f(z) "
                     "(SymPy, generic C and f; manual substitution and Integral.transform)",
             "result": "pass", "tolerance": "exact"},
            {"name": "flavour algebra: q_ns + <e^2> q_s = sum e^2 (q + qbar), q_ns flavour-traceless, n_f = 3..6; "
                     "<e^2> = 5/18 for n_f = 4, 6 (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "coefficient-function route equals the Altarelli-Martinelli integrand identically (SymPy, "
                     "generic F_2 and g)", "result": "pass", "tolerance": "exact"},
            {"name": "known limit: F_L linear in alpha_s, F_L = 0 at alpha_s = 0 (SymPy and numerical)",
             "result": "pass", "tolerance": "exact"},
            {"name": "positivity: integrand non-negative on x <= z <= 1 for non-negative densities, so F_L >= 0 "
                     "(SymPy); F_L >= 0 on every toy point", "result": "pass", "tolerance": "exact"},
            {"name": "F_L <= F_2 on every toy point (numerical; a property of the toy, not proven in general)",
             "result": "pass", "tolerance": "exact"},
            {"name": "adaptive quadrature against the exact SymPy closed form, 6 x points on SYNTHETIC Beta-form "
                     "densities", "result": "pass", "tolerance": cfg["relative_tolerance"]},
            {"name": "convergence study: Gauss-Legendre rule in ln z with 4..128 nodes converges to the closed form "
                     "(error at 128 nodes below tolerance; stored in derivations/derivation.json)",
             "result": "pass", "tolerance": cfg["relative_tolerance"]},
            {"name": "convolution route in the original variable y (no change of variables) equals the "
                     "Altarelli-Martinelli form numerically", "result": "pass",
             "tolerance": cfg["relative_tolerance"]},
            {"name": "units: x, Q^2-independent toy densities, F_2, F_L and alpha_s dimensionless",
             "result": "pass", "tolerance": "exact"}],
        "checks_not_run": [
            "comparison with any published F_L value or table (none was read; the profile is synthetic-only)",
            "comparison with measured F_L or F_2",
            "NLO/NNLO coefficient functions, DGLAP evolution of the densities, heavy-quark mass effects, "
            "target-mass and higher-twist corrections",
            "formal proof of the factorization formula (cited, not derived)"],
        "references_read": REFERENCES,
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "frame", "angle_definition", "em_coupling", "structure_function_signs",
                         "log_accuracy"],
        "neglected": ["O(alpha_s^2) and higher coefficient functions", "power corrections O(M^2/Q^2)",
                      "heavy-quark masses", "Z exchange and gamma-Z interference", "Q^2 evolution of the toy "
                                                                                  "densities"],
    }
    return _envelope(SPEC_ID, "theory-spec",
                     "Theory spec of LO F_2 and the O(alpha_s) longitudinal structure function F_L in "
                     "theory:dis-parton-model (synthetic-only profile)", ext)


def prediction(cfg: dict, conventions: dict) -> dict:
    import predict
    out = predict.predict(cfg)
    obs_conv = {k: conventions[k] for k in ("unit_system", "energy_variable", "scales", "mass_approximation",
                                            "exchanged_bosons", "heavy_quark_scheme", "target_normalization")}
    obs_conv |= {k: v for k, v in conventions.items() if ":" in k}
    ext = {
        "observable": {
            "quantity": "dispm:structure-function",
            "process": "neutral-current deep-inelastic lepton-nucleon scattering, photon exchange: F_L (O(alpha_s)) "
                       "and F_2 (O(alpha_s^0))",
            "variables": [{"name": "x", "unit": "1", "points": cfg["x_points"]},
                          {"name": "Q2", "unit": "GeV^2", "points": cfg["q2_points_gev2"]}],
            "phase_space": {"definition": "inclusive structure functions at the stated (x, Q^2) points; no final-state "
                                          "selection", "fiducial": False},
            "level": "dispm:inclusive",
            "frame": "not-applicable (invariant structure functions)",
            "normalization": {"kind": "integrated-luminosity", "value": "not-applicable",
                              "convention": "absolute, dimensionless structure functions: no luminosity, exposure "
                                            "or unit-area normalization enters (the vocabulary has no 'none' kind)"},
            "bin_semantics": "point",
            "unit": "1",
            "conventions": obs_conv,
            "validity_range": {"x": [min(cfg["x_points"]), max(cfg["x_points"])],
                               "Q2": [min(cfg["q2_points_gev2"]), max(cfg["q2_points_gev2"])]}},
        "theory_spec_ref": "derivations/theory-spec.json",
        "derivation_status": "perturbative-argument",
        "parameter_point": {"toy_inputs": "benchmarks/toy-closed-form.json (SYNTHETIC)",
                            "alpha_s_at_Q2": dict(zip([str(q) for q in cfg["q2_points_gev2"]], cfg["alpha_s_at_q2"])),
                            "n_f": out["n_f"], "sum_e2": out["sum_e2"], "mu_R": "Q", "mu_F": "Q"},
        "representation": "symbolic",
        "expression": AM_FORM,
        "point_values": {"about": "the expression evaluated at the toy points (SYNTHETIC); one row per (x, Q^2)",
                         "rows": [{k: r[k] for k in ("x", "q2_gev2", "alpha_s", "F2", "FL", "FL_quadrature_error")}
                                  for r in out["rows"]],
                         "checks": out["checks"]},
        "uncertainties": [{"name": "quadrature error estimate of F_L (adaptive, relative tolerance 1e-13)",
                           "kind": "numerical", "correlation": "unknown", "gaussian": False,
                           "values": [r["FL_quadrature_error"] for r in out["rows"]]}],
        "allowed_transformations": ["re-evaluation with other densities and alpha_s values (predict.py --config)",
                                    "never compare with data: the inputs are synthetic"],
    }
    return _envelope("dispm-prediction-fl-toy-grid", "prediction",
                     "F_L at O(alpha_s) and LO F_2 on SYNTHETIC toy densities (demonstration of the machinery, not a "
                     "statement about any nucleon)", ext,
                     inputs=[{"ref": "derivations/theory-spec.json", "artifact_type": "theory-spec",
                              "artifact_id": SPEC_ID, "status": ["synthetic", "unvalidated"]}])


def same(a, b, rel: float = 1e-9) -> bool:
    """Structural equality with a relative tolerance on floats (recomputation may differ in the last bits)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            return False
        return abs(a - b) <= rel * max(abs(a), abs(b)) or abs(a - b) <= 1e-16
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

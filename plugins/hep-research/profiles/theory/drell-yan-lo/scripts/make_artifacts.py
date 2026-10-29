#!/usr/bin/env python3
"""Write the envelope artifacts of theory:drell-yan-lo: the theory-spec (derivations/theory-spec.json) and the
angular-coefficient prediction (predictions/angular-coefficients.prediction.json), both checked with
contracts/validate.py by the tests.

The prediction is lambda, nu and 1 - lambda - 2 nu versus qT/Q at O(alpha_s) for the q qbar and q g channels and for
channel mixtures with q g fraction f (a parameter, not fitted to data). It is a symbolic prediction (the closed forms)
with its evaluation at the grid points in 'point_values'. Channels mix exactly by averaging A0 and A2 with the
angle-integrated cross-section fractions (derived in derive.py), so no mixing-rule uncertainty is stored.

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

PROFILE_ID, PROFILE_VERSION = "theory:drell-yan-lo", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.46.0", "3.16.0"
CREATED = "2026-10-23"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
PRED_PATH = PROFILE / "predictions" / "angular-coefficients.prediction.json"
SPEC_ID = "dylo-theory-spec-lo-and-lam-tung"
EVIDENCE = ["dylo:C01", "dylo:C02", "dylo:C03", "dylo:C04", "dylo:C05", "dylo:C06", "dylo:C07"]
EXPRESSION = ("r = qT/Q; A0(qqbar) = r^2/(1 + r^2), A0(qg) = 5 r^2/(1 + 5 r^2); A0(f) = f A0(qg) + (1 - f) A0(qqbar); "
              "A2 = A0 (phi1 = 0 at O(alpha_s)); lambda = (2 - 3 A0)/(2 + A0); nu = 2 A2/(2 + A0); "
              "1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0) = 0. Per channel: lambda = (2 - r^2)/(2 + 3 r^2), "
              "nu = 2 r^2/(2 + 3 r^2) (q qbar); lambda = (2 - 5 r^2)/(2 + 15 r^2), nu = 10 r^2/(2 + 15 r^2) (q g)")
REFERENCES = [
    {"citation": "H. Baer and R.N. Cahn, 'Cross-Section Formulae for Specific Processes', in F. Takahashi et al. "
                 "(Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026)",
     "location": "Sec. 51.2 Eq. (51.3) p. 1; Sec. 51.6 Eq. (51.40) and Eqs. (51.41)-(51.42) p. 7",
     "date_read": "2026-10-23"},
    {"citation": "J.-C. Peng, W.-C. Chang, R.E. McClellan and O. Teryaev, 'Interpretation of Angular Distributions of "
                 "Z-boson Production at Colliders', arXiv:1511.08932v3 (2016)",
     "location": "Eq. (1) p. 1; Eqs. (2)-(7) p. 2; remarks after Eq. (7) and Eqs. (8)-(10) p. 3; coplanarity at "
                 "leading order alpha_s, p. 4",
     "date_read": "2026-10-23"}]


def _envelope(artifact_id: str, artifact_type: str, objective: str, ext: dict, status: list,
              inputs: list | None = None) -> dict:
    return {"contract_version": CONTRACTS, "artifact_id": artifact_id, "artifact_type": artifact_type,
            "objective": objective, "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                                 "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED, "evidence_ids": EVIDENCE},
            "inputs": inputs or [], "outputs": [], "status": status, "unresolved_inputs": [], "extension": ext}


def theory_spec(conventions: dict, bench: dict, xs_cfg: dict) -> dict:
    ext = {
        "model": {"id": "dylo-lo-drell-yan-and-alpha-s-angular-coefficients",
                  "description": "LO Drell-Yan d2sigma/dM dy = (8 pi alpha^2/(9 M s)) sum e_q^2 [q1 qbar2 + qbar1 q2] "
                                 "(photon exchange) from PDG Eqs. 51.3 and 51.40, and the lepton angular coefficients "
                                 "lambda, nu at O(alpha_s) from the quark-axis picture of Peng et al. (Eqs. 2-10), "
                                 "with the Lam-Tung relation 1 - lambda - 2 nu = 0 for a coplanar quark axis",
                  "family": "drell-yan"},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "photon exchange only (a = 0); massless quarks and leptons; unpolarized hadrons; N_c = 3",
            "LO parton-model factorization (PDG Eq. 51.40); time reversal relates q qbar -> l+ l- to Eq. 51.3",
            "angular coefficients at O(alpha_s): one emitted parton, no intrinsic transverse momentum",
            "phi1 = 0 at O(alpha_s) (quark axis in the hadron plane): cited from Peng et al., not derived here",
            "<sin^2 theta1> = r^2/(1 + r^2) for q qbar (exact) and 5 r^2/(1 + 5 r^2) for q g (approximate, Peng "
            "et al.)",
            "channel mixture: A_i averaged with the angle-integrated cross-section fractions f_c of the channels in "
            "the same (qT, Q) bin (exact; equal to event fractions only with full angular acceptance)"],
        "conventions": dict(conventions),
        "order": "d2sigma/dM dy at O(alpha^2 alpha_s^0) (LO); lambda, nu and the Lam-Tung relation at O(alpha_s^1)",
        "parameters": {"N_c": 3, "toy_cross_section_check": "benchmarks/toy-lo-cross-section.json (SYNTHETIC)",
                       "published_benchmark": "benchmarks/peng-eq10.json"},
        "scales": "not-applicable",
        "derivation_status": "perturbative-argument",
        "validity_domain": {
            "cross_section": "photon exchange, M well below the Z mass and above resonance regions; LO only",
            "angular_coefficients": "O(alpha_s), qT > 0 generated by one hard emission; at small qT intrinsic "
                                    "transverse momentum and resummation (not included) matter; beyond O(alpha_s) "
                                    "non-coplanar emissions violate Lam-Tung (1 - lambda - 2 nu >= 0)",
            "qg_channel": "Eq. 9 is an approximation whose accuracy depends on the parton distributions (Peng et al.)"},
        "checks_run": [
            {"name": "colour average: sigma(q qbar -> l+ l-) = e_q^2 4 pi alpha^2/(9 s_hat) from PDG Eq. 51.3 (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "Jacobian |d(x1, x2)/d(tau, y)| = 1 and the map inverts (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "delta-function integration gives d2sigma/dM dy = (8 pi alpha^2/(9 M s)) e_q^2 L(M^2/s, y) "
                     "(SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "numerical: the formula integrated over an (M, y) box equals the parton integral over the "
                     "matching (x1, x2) region, SYNTHETIC toy densities", "result": "pass",
             "tolerance": xs_cfg["relative_tolerance"]},
            {"name": "Peng Eq. 4 substituted into Eq. 2 reproduces Eq. 5 identically (SymPy normal form modulo "
                     "sin^2 + cos^2 = 1)", "result": "pass", "tolerance": "exact"},
            {"name": "matching Eq. 3 to Eq. 5 gives A_0..A_7 of Eq. 6; Eq. 3 against Eq. 1 gives Eq. 7 (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0); phi1 = 0 gives A0 = A2 and Lam-Tung; A0 - A2 = "
                     "2 sin^2 theta1 sin^2 phi1 >= 0 (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "Eqs. 8 and 9 in Eq. 7 reproduce Peng Eq. 10 for both channels (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "channel mixture: A_i terms of Eq. 3 integrate to zero over the sphere, 1 + cos^2 to 16 pi/3; "
                     "the cross-section-weighted sum of channel distributions is Eq. 3 with the weighted A_i, i.e. "
                     "lambda_mix = sum f lambda/(3 + lambda) / sum f/(3 + lambda) (SymPy)", "result": "pass",
             "tolerance": "exact"},
            {"name": "limits: qT -> 0 gives lambda = 1, nu = 0; qT -> infinity gives lambda = -1/3 (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "published closed form (Peng Eq. 10) against the profile's numbers, 2 channels x 7 qT/Q "
                     "values", "result": "pass", "tolerance": bench["relative_tolerance"]},
            {"name": "units: lambda, mu, nu dimensionless; cross section in (4 pi alpha^2/3) GeV^-3",
             "result": "pass", "tolerance": "exact"}],
        "checks_not_run": [
            "independent check of Peng Eq. 9 (q g channel): cited approximation, not recomputed from the matrix "
            "element",
            "derivation of phi1 = 0 at O(alpha_s): cited, not derived",
            "comparison with measured lambda, nu or cross sections (no data in this profile)",
            "Z exchange, NLO cross section, qT resummation, intrinsic transverse momentum"],
        "references_read": REFERENCES,
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "renormalization_scheme", "scales", "factorization_scheme",
                         "xF_definition", "log_accuracy"],
        "neglected": ["Z exchange and gamma-Z interference (a = 0)", "O(alpha_s) corrections to the cross section",
                      "O(alpha_s^2) non-coplanar emissions (Lam-Tung violation)", "intrinsic transverse momentum",
                      "qT resummation"],
    }
    return _envelope(SPEC_ID, "theory-spec",
                     "Theory spec of the LO Drell-Yan cross section and the O(alpha_s) angular coefficients with the "
                     "Lam-Tung relation in theory:drell-yan-lo", ext, ["unvalidated"])


def prediction(conventions: dict, cfg: dict) -> dict:
    import predict
    out = predict.predict(cfg)
    rs = cfg["qT_over_Q"]
    obs_conv = {k: conventions[k] for k in ("frame", "angle_definition", "exchanged_bosons", "azimuth_convention",
                                            "mass_approximation", "spin_treatment")}
    obs_conv |= {k: v for k, v in conventions.items() if ":" in k}
    ext = {
        "observable": {
            "quantity": "dylo:angular-coefficient",
            "process": "lepton-pair production in hadron-hadron collisions via a virtual photon, O(alpha_s) channels "
                       "q qbar -> gamma* g and q g -> gamma* q",
            "species": [{"name": "negative lepton"}],
            "variables": [{"name": "qT_over_Q", "unit": "1", "points": rs}],
            "phase_space": {"definition": "lepton angular distribution in the Collins-Soper frame, integrated over "
                                          "the dilepton rapidity and mass at fixed qT/Q; no lepton cuts",
                            "fiducial": False},
            "level": "parton",
            "frame": "Collins-Soper",
            "normalization": {"kind": "shape-only", "value": "not-applicable",
                              "convention": "lambda, mu, nu are coefficients of the normalized angular distribution "
                                            "(Peng et al. Eq. 1)"},
            "bin_semantics": "point",
            "unit": "1",
            "conventions": obs_conv,
            "validity_range": {"qT_over_Q": [min(rs), max(rs)]}},
        "theory_spec_ref": "derivations/theory-spec.json",
        "derivation_status": "perturbative-argument",
        "parameter_point": {"qg_fractions": cfg["qg_fractions"], "mixing_rule": "A0, A2 averaged with angle-integrated cross-section fractions (exact)",
                            "note": "the q g fraction f is a free parameter of the prediction, not fitted to data"},
        "representation": "symbolic",
        "expression": EXPRESSION,
        "point_values": {"about": "the expression evaluated at the grid points; channels and mixtures (q g fraction)",
                         "channels": out["channels"], "mixtures_by_qg_fraction": out["mixtures_average_A"],
                         "checks": out["checks"]},
        "uncertainties": [],
        "allowed_transformations": ["re-evaluation at other qT/Q values or q g fractions (predict.py --config)",
                                    "a comparison with data needs a stated q g fraction (or a fit of it, in "
                                    "hep-statistics) and must allow Lam-Tung violation beyond O(alpha_s)"],
    }
    return _envelope("dylo-prediction-angular-coefficients", "prediction",
                     "lambda, nu and 1 - lambda - 2 nu versus qT/Q at O(alpha_s) for the q qbar and q g channels and "
                     "their mixtures (no data)", ext, ["unvalidated"],
                     inputs=[{"ref": "derivations/theory-spec.json", "artifact_type": "theory-spec",
                              "artifact_id": SPEC_ID, "status": ["unvalidated"]}])


def same(a, b, rel: float = 1e-9) -> bool:
    """Structural equality with a relative tolerance on floats (recomputation may differ in the last bits)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            return False
        return abs(a - b) <= rel * max(abs(a), abs(b)) or abs(a - b) <= 1e-14
    return a == b


def build() -> dict[Path, dict]:
    import predict
    conventions = predict.load_json(PROFILE / "conventions.json")
    bench, xs_cfg = predict.load_json(predict.BENCHMARK), predict.load_json(predict.TOY_XS)
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    return {SPEC_PATH: theory_spec(conventions, bench, xs_cfg), PRED_PATH: prediction(conventions, cfg)}


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

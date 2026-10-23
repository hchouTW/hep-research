#!/usr/bin/env python3
"""Write the envelope artifacts of theory:tmd-gaussian-lo: the theory-spec (derivations/theory-spec.json) and three
predictions (predictions/*.prediction.json): the SIDIS F_UU,T shape, the SIDIS Sivers asymmetry (with the Sivers
function in SIDIS and Drell-Yan), and the Drell-Yan q_T shape. All are checked with contracts/validate.py by the tests.

The predictions are symbolic (the closed forms) with their evaluation in 'point_values'. Their inputs are SYNTHETIC
collinear values and Sivers normalizations, and the paper's fitted widths used as ILLUSTRATIVE settings; status
heuristic-argument (Gaussian ansatz, no evolution).

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

PROFILE_ID, PROFILE_VERSION = "theory:tmd-gaussian-lo", "0.1.0"
PLUGIN_VERSION, CONTRACTS = "0.35.0", "3.10.0"
CREATED = "2026-10-23"
SPEC_PATH = PROFILE / "derivations" / "theory-spec.json"
PRED_DIR = PROFILE / "predictions"
SPEC_ID = "tmdg-theory-spec-gaussian-tmd-lo"
STATUS = ["synthetic", "unvalidated"]
EVIDENCE = ["tmdg:C01", "tmdg:C02", "tmdg:C03", "tmdg:C04", "tmdg:C05", "tmdg:C06", "tmdg:C07", "tmdg:C08"]
REFERENCES = [
    {"citation": "M. Anselmino, M. Boglione, U. D'Alesio, A. Kotzinian, F. Murgia, A. Prokudin, 'The role of Cahn "
                 "and Sivers effects in deep inelastic scattering', arXiv:hep-ph/0501196v2",
     "location": "Eqs. (29), (32)-(39) pp. 6-7; Eq. (47) p. 9; Eqs. (48)-(58) pp. 10-12; Eqs. (63)-(68), Table I "
                 "pp. 12-14", "date_read": "2026-10-23"},
    {"citation": "A. Bacchetta, M. Diehl, K. Goeke, A. Metz, P.J. Mulders, M. Schlegel, 'Semi-inclusive deep "
                 "inelastic scattering at small transverse momentum', arXiv:hep-ph/0611265v2",
     "location": "Eqs. (2.3), (2.7)-(2.15) PDF pp. 4-6; Eq. (3.41) PDF p. 14; Eqs. (4.1), (4.2), (4.11) PDF "
                 "pp. 18-19; Eq. (4.20) PDF p. 20; Eq. (4.21) PDF p. 21", "date_read": "2026-10-23"},
    {"citation": "A. Bacchetta, U. D'Alesio, M. Diehl, C.A. Miller, 'Single-spin asymmetries: the Trento "
                 "conventions', arXiv:hep-ph/0410050v2",
     "location": "Eqs. (2)-(4) pp. 1-2; Eq. (14) p. 3", "date_read": "2026-10-23"}]
LEVEL = "tmdg:leading-power-tmd"


def _envelope(artifact_id: str, artifact_type: str, objective: str, ext: dict, inputs: list | None = None) -> dict:
    return {"contract_version": CONTRACTS, "artifact_id": artifact_id, "artifact_type": artifact_type,
            "objective": objective, "bindings": {"experiments": [], "theory": [{"profile": PROFILE_ID,
                                                                                 "version": PROFILE_VERSION}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS, "profiles": {PROFILE_ID: PROFILE_VERSION}},
            "provenance": {"producer_skill": "hep-theory", "created": CREATED, "evidence_ids": EVIDENCE},
            "inputs": inputs or [], "outputs": [], "status": list(STATUS), "unresolved_inputs": [], "extension": ext}


def theory_spec(cfg: dict, conventions: dict, bench: dict) -> dict:
    tol = cfg["relative_tolerance"]
    ext = {
        "model": {"id": "tmdg-gaussian-tmd-lo",
                  "description": "Gaussian-ansatz TMD distribution and fragmentation functions with constant, "
                                 "flavour-independent widths, at leading order in alpha_s and without evolution: "
                                 "SIDIS F_UU,T with <P_T^2> = <p_perp^2> + z^2 <k_perp^2>, the Cahn cos(phi_h) term "
                                 "at O(k/Q), the Sivers asymmetry in the Gaussian Sivers model, the Drell-Yan q_T "
                                 "shape with <q_T^2> = <k1^2> + <k2^2>, and the SIDIS -> Drell-Yan Sivers sign change",
                  "family": "tmd-phenomenology"},
        "domain_profile": PROFILE_ID,
        "assumptions": [
            "Gaussian k_perp and p_perp dependence, constant flavour-independent widths (Anselmino et al. Eqs. 34-35): "
            "a model, so the physics status is heuristic-argument",
            "P_hT = z k_perp + p_perp, x = x_B, z = z_h at O(k_perp/Q) (Eq. 29); Cahn term kept at O(k_perp/Q)",
            "one-photon exchange; massless partons; gamma = 2Mx/Q -> 0",
            "Sivers function 2 N_q(x) h'(k) f(x, k), h' = sqrt(2e)(k/M') exp(-k^2/M'^2) (Eqs. 63, 68)",
            "f_1T^perp,DY = -f_1T^perp,SIDIS (Trento Eq. 14): cited, not derived",
            "Drell-Yan q_T: tree-level convolution of two Gaussian TMD PDFs, no soft factor"],
        "conventions": dict(conventions),
        "order": "leading order in alpha_s; leading power in k_perp/Q for F_UU,T, the Sivers term and Drell-Yan, "
                 "O(k_perp/Q) for the Cahn term; no TMD evolution",
        "parameters": {"kperp2_gev2": cfg["kperp2_gev2"], "pperp2_gev2": cfg["pperp2_gev2"],
                       "Mprime2_gev2": cfg["sivers"]["Mprime2_gev2"],
                       "widths_note": "fitted values of Anselmino et al. (Eq. 47, Table I) used as ILLUSTRATIVE "
                                      "settings; collinear values, N_q and Drell-Yan widths SYNTHETIC",
                       "inputs": "benchmarks/toy-inputs.json"},
        "scales": "not-applicable",
        "derivation_status": "heuristic-argument",
        "validity_domain": {
            "kinematics": "P_hT ~ k_perp << Q (the paper's validity statement: corrections O(k_perp^2/Q^2) small); "
                          "no matching to the large-P_hT collinear region",
            "model": "constant Gaussian widths independent of x, z, Q^2 and flavour; no evolution; the derivations "
                     "are exact within this model (analytic-derivation per step in derivations/derivation.json)",
            "sivers_sign": "applies to TMDs with the SIDIS and Drell-Yan Wilson lines (Trento Eq. 14)"},
        "checks_run": [
            {"name": "Gaussian normalizations, including D_1(z) = z^2 int d^2k_T D_1(z, k_T^2) (SymPy)",
             "result": "pass", "tolerance": "exact"},
            {"name": "SIDIS convolution gives the Gaussian in P_hT with <P_T^2> = <p_perp^2> + z^2 <k_perp^2> "
                     "(Anselmino form) and the same F_UU,T from the Bacchetta convolution with <p_perp^2> = "
                     "z^2 <k_T^2> (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "d^2P_hT integral of F_UU,T = x sum e^2 f D (Bacchetta Eq. 4.21) (SymPy and numerical)",
             "result": "pass", "tolerance": "exact"},
            {"name": "Eq. 32 with Eq. 33 reproduces the Cahn term of Eq. 38; Bacchetta Eq. 4.20 with Eqs. 2.9 and "
                     "2.11 at gamma = 0 gives the same bracket (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "Eq. 58 with Eqs. 63, 68 reproduces Eqs. 64-67; Bacchetta Eq. 4.11 with Trento Eq. 4 gives the "
                     "same asymmetry (SymPy)", "result": "pass", "tolerance": "exact"},
            {"name": "Drell-Yan: two Gaussians convolve to width <k1^2> + <k2^2>, unit normalization (SymPy and "
                     "numerical)", "result": "pass", "tolerance": "exact"},
            {"name": "Trento Eq. 4 round trip between Delta^N f and f_1T^perp (SymPy); the Drell-Yan sign (Trento "
                     "Eq. 14) is applied as a cited rule, not checked", "result": "pass", "tolerance": "exact"},
            {"name": "closed forms against 2D adaptive quadrature of the defining integrals (toy inputs)",
             "result": "pass", "tolerance": tol},
            {"name": "published closed forms (Anselmino et al. Eqs. 38-39 and 64-67) against the profile's quadrature "
                     "of its transcription of the same integrands at 4 (z, P_T) points (same route as the paper: "
                     "checks algebra and transcription, not physics)", "result": "pass",
             "tolerance": bench["relative_tolerance"]},
            {"name": "frame map: Anselmino et al. (q along +z, P along -z, l_x > 0; pp. 2, 6, 11) inserted in Trento "
                     "Eq. 16 gives the same phi_h and phi_S (by hand, recorded in derivation-record.md)",
             "result": "pass", "tolerance": "exact"},
            {"name": "limits: Cahn ratio 1 and Sivers asymmetry 0 at P_hT = 0", "result": "pass",
             "tolerance": "exact"}],
        "checks_not_run": [
            "TMD evolution, the soft factor and the matching to collinear factorization at large P_hT",
            "an independent derivation of the Sivers sign change (cited from the Trento conventions)",
            "a Drell-Yan Sivers asymmetry formula: no source read gives one, so only the sign of the Sivers function "
            "is propagated",
            "comparison with measured multiplicities, asymmetries or q_T spectra"],
        "references_read": REFERENCES,
        "derivation_record": "derivations/derivation-record.md",
        "inapplicable": ["metric_signature", "coupling_normalization", "renormalization_scheme", "scales",
                         "factorization_scheme", "log_accuracy", "xF_definition", "rapidity_frame"],
        "neglected": ["TMD evolution", "flavour, x and z dependence of the widths", "O(k_perp^2/Q^2) kinematic terms",
                      "Boer-Mulders and Collins contributions", "target and hadron masses"],
    }
    return _envelope(SPEC_ID, "theory-spec",
                     "Theory spec of Gaussian-ansatz TMDs at leading order without evolution (SIDIS F_UU,T, Cahn, "
                     "Sivers, Drell-Yan q_T, Sivers sign change) in theory:tmd-gaussian-lo", ext)


def _obs(quantity, process, var, points, unit, norm_kind, norm_conv, conventions, level=LEVEL):
    keys = ("unit_system", "frame", "angle_definition", "azimuth_convention", "exchanged_bosons", "mass_approximation")
    conv = {k: conventions[k] for k in keys} | {k: v for k, v in conventions.items() if ":" in k}
    return {"quantity": quantity, "process": process, "variables": [{"name": var, "unit": "GeV", "points": points}],
            "phase_space": {"definition": "leading-power TMD region, no cuts", "fiducial": False}, "level": level,
            "normalization": {"kind": norm_kind, "value": "not-applicable", "convention": norm_conv},
            "bin_semantics": "point", "unit": unit, "conventions": conv,
            "validity_range": {var: [min(points), max(points)]}}


def predictions(cfg: dict, conventions: dict) -> dict[Path, dict]:
    import predict
    out = predict.predict(cfg)
    spec_in = [{"ref": "derivations/theory-spec.json", "artifact_type": "theory-spec", "artifact_id": SPEC_ID,
                "status": list(STATUS)}]
    common = {"theory_spec_ref": "derivations/theory-spec.json", "derivation_status": "heuristic-argument",
              "representation": "symbolic"}
    ppts = cfg["PhT_gev"]
    fuu = {"observable": _obs("tmdg:structure-function", "SIDIS l N -> l h X, one-photon exchange: F_UU,T",
                              "PhT", ppts, "GeV^-2", "integrated-luminosity",
                              "absolute structure function per GeV^2 of P_hT; no luminosity enters", conventions),
           **common,
           "parameter_point": {"x": cfg["x"], "z": cfg["z"], "kperp2_gev2": cfg["kperp2_gev2"],
                               "pperp2_gev2": cfg["pperp2_gev2"], "flavours": cfg["flavours"], "cahn": cfg["cahn"]},
           "expression": "F_UU,T = x sum e_q^2 f_q(x) D_q(z) exp(-P_hT^2/<P_T^2>)/(pi <P_T^2>), <P_T^2> = <p_perp^2> "
                         "+ z^2 <k_perp^2>; Cahn ratio [1 + (1-y)^2 - 4 (2-y) sqrt(1-y) <k_perp^2> z P_hT "
                         "cos(phi_h)/(<P_T^2> Q)]/[1 + (1-y)^2]",
           "point_values": {"PT2_width_gev2": out["PT2_width_gev2"], "collinear_F_UU_T": out["collinear_F_UU_T"],
                            "rows": out["F_UU_T"], "checks": {k: out["checks"][k] for k in (
                                "F_UU_T_closed_form_equals_quadrature", "F_UU_T_integrates_to_collinear",
                                "cahn_ratio_one_at_PhT_0")}},
           "uncertainties": [],
           "allowed_transformations": ["re-evaluation with other inputs (predict.py --config)",
                                       "never compare with data: collinear inputs are synthetic"]}
    siv = {"observable": _obs("asymmetry", "SIDIS l p(transversely polarized) -> l h X: A_UT^sin(phi_h - phi_S) from "
                                           "the Sivers function", "PhT", ppts, "1", "shape-only",
                              "ratio of cross sections; no absolute normalization", conventions),
           **common,
           "parameter_point": {"x": cfg["x"], "z": cfg["z"], "kperp2_gev2": cfg["kperp2_gev2"],
                               "pperp2_gev2": cfg["pperp2_gev2"], "sivers": cfg["sivers"], "flavours": cfg["flavours"]},
           "expression": "A = sum_q e_q^2 f_q D_q 2 N_q z P_hT sqrt(2e) <k^2>hat^2/(M' <P_T^2>hat^2 <k_perp^2>) "
                         "exp(-P_hT^2/<P_T^2>hat) / [2 sum_q e_q^2 f_q D_q exp(-P_hT^2/<P_T^2>)/<P_T^2>] (Anselmino "
                         "et al. Eqs. 64-67). Sivers function: Delta^N f(SIDIS) = 2 N_q h'(k) f(x, k); "
                         "Delta^N f(DY) = -Delta^N f(SIDIS) (Trento Eqs. 4, 14)",
           "point_values": {"sidis_asymmetry": out["sivers_asymmetry_sidis"], "sivers_function": out["sivers_function"],
                            "declarations": out["declarations"],
                            "checks": {k: out["checks"][k] for k in ("sivers_asymmetry_zero_at_PhT_0",
                                                                     "published_closed_forms_reproduced_by_quadrature")}},
           "uncertainties": [],
           "allowed_transformations": ["re-evaluation with other inputs (predict.py --config)",
                                       "Drell-Yan: only the sign of the Sivers function is propagated (no Drell-Yan "
                                       "asymmetry formula in the sources read)"]}
    d = cfg["drell_yan"]
    dy = {"observable": _obs("differential-cross-section", "Drell-Yan h1 h2 -> l+ l- X: normalized q_T shape "
                                                           "(1/sigma) d sigma/d^2q_T", "qT", d["qT_gev"], "GeV^-2",
                             "shape-only", "normalized to unit integral over d^2q_T", conventions, level="parton"),
          **common,
          "parameter_point": {"k1perp2_gev2": d["k1perp2_gev2"], "k2perp2_gev2": d["k2perp2_gev2"]},
          "expression": "exp(-q_T^2/<q_T^2>)/(pi <q_T^2>), <q_T^2> = <k1perp^2> + <k2perp^2> (derived here)",
          "point_values": {"qT2_width_gev2": out["qT2_width_gev2"], "rows": out["drell_yan_qT_shape"],
                           "checks": {k: out["checks"][k] for k in ("dy_shape_closed_form_equals_quadrature",
                                                                    "dy_shape_unit_normalized")}},
          "uncertainties": [],
          "allowed_transformations": ["multiply by the LO collinear cross section for an absolute q_T spectrum",
                                      "never compare with data: widths are synthetic"]}
    return {PRED_DIR / "sidis-fuut.prediction.json":
            _envelope("tmdg-prediction-sidis-fuut", "prediction", "SIDIS F_UU,T and Cahn ratio versus P_hT in the "
                      "Gaussian ansatz (synthetic collinear inputs)", fuu, spec_in),
            PRED_DIR / "sivers-asymmetry.prediction.json":
            _envelope("tmdg-prediction-sivers-asymmetry", "prediction", "SIDIS Sivers asymmetry versus P_hT and the "
                      "Sivers function in SIDIS and Drell-Yan (opposite sign), Gaussian model, synthetic N_q", siv,
                      spec_in),
            PRED_DIR / "dy-qt-shape.prediction.json":
            _envelope("tmdg-prediction-dy-qt-shape", "prediction", "Normalized Drell-Yan q_T shape from two Gaussian "
                      "TMD PDFs (synthetic widths)", dy, spec_in)}


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
    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    conventions = predict.load_json(PROFILE / "conventions.json")
    bench = predict.load_json(predict.BENCHMARK)
    return {SPEC_PATH: theory_spec(cfg, conventions, bench), **predictions(cfg, conventions)}


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

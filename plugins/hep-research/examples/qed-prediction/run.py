#!/usr/bin/env python3
"""Path C (journey J4): standalone theory with theory:qed-benchmark, no experiment resource.

Runs the SymPy derivation (profiles/theory/qed-benchmark/scripts/derive.py) and the numerical prediction
(scripts/predict.py) at the benchmark point, then writes a theory-spec artifact (assumptions, conventions,
derivation status, validity domain, reference read, checks run and not run, inapplicable fields), a prediction
artifact (bin-averaged d sigma / d cos theta and integrated cross sections with units and uncertainty
components), a figure and a short report. Every data file opened and every profile module imported during the run
is recorded; the run fails if any experiment-profile file is read.

Usage (from the plugin root): python3 examples/qed-prediction/run.py [--out DIR]
Requires numpy, scipy, sympy and matplotlib (D5 environment). No GPU and no commercial CAS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
PROFILE_DIR = PLUGIN / "profiles" / "theory" / "qed-benchmark"
OPENED: set[str] = set()


def _audit(event, args):
    # Code is left to _imported_profile_code: an import opens the .py on a cold bytecode cache and the .pyc on a warm one,
    # and on a cold in-tree cache it also writes __pycache__/<name>.pyc.<id> (a temporary file renamed into place).
    if event == "open" and isinstance(args[0], (str, Path)) and not str(args[0]).endswith(".py") and ".pyc" not in Path(args[0]).name:
        try:
            OPENED.add(str(Path(args[0]).resolve().relative_to(PLUGIN)))
        except ValueError:
            pass


def _imported_profile_code() -> set[str]:
    """Source files of the modules imported from profiles/, whatever the state of the bytecode cache."""
    found = set()
    for mod in list(sys.modules.values()):
        try:
            rel = Path(getattr(mod, "__file__", None) or "").resolve().relative_to(PLUGIN)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == "profiles":
            found.add(str(rel))
    return found


sys.addaudithook(_audit)
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PROFILE_DIR / "scripts"))
import numpy as np  # noqa: E402

import derive  # noqa: E402
import predict  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
CONVENTIONS = json.loads((PROFILE_DIR / "conventions.json").read_text(encoding="utf-8"))
CFG = json.loads((PROFILE_DIR / "benchmarks" / "path-c.json").read_text(encoding="utf-8"))
CLAIMS = json.loads((PROFILE_DIR / "evidence" / "claims.json").read_text(encoding="utf-8"))
SOURCES = json.loads((PROFILE_DIR / "evidence" / "sources.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def artifacts(der: dict, pred: dict, created: str):
    vocab = Vocabulary.with_profiles([PROFILE])
    base = {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [], "theory": [{"profile": PROFILE["id"], "version": PROFILE["version"]}]},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "profiles": {PROFILE["id"]: PROFILE["version"]}},
            "inputs": [], "outputs": [], "unresolved_inputs": []}
    src = SOURCES[0]
    spec = dict(base, artifact_id="qedbench-path-c-theory-spec", artifact_type="theory-spec",
                objective="Tree-level e+e- -> mu+mu- via one photon: differential and integrated cross section",
                provenance={"producer_skill": "hep-theory", "created": created, "evidence_ids": [c["id"] for c in CLAIMS]},
                status=["validated-in-scope"],
                extension={
                    "model": {"id": "qed-tree-level-photon-exchange", "description": "e+e- -> mu+mu- through one s-channel photon, lowest order"},
                    "domain_profile": PROFILE["id"],
                    "assumptions": der["assumptions"],
                    "conventions": {k: v for k, v in CONVENTIONS.items()},
                    "order": "tree level, O(alpha^2) in the cross section",
                    "parameters": {"sqrt_s_gev": pred["sqrt_s_gev"], "reference_constant_nb_gev2": pred["reference_constant_nb_gev2"],
                                   "muon_mass": "symbolic m in the derivation; 0 in the numerical prediction"},
                    "scales": "not-applicable",
                    "derivation_status": der["derivation_status"],
                    "validity_domain": {"sqrt_s": "well above 2 m_mu and well below m_Z [Proposal: benchmark point 10 GeV]",
                                        "excluded_effects": ["Z exchange", "radiative corrections", "running alpha", "beam polarization"],
                                        "quantified": False},
                    "checks_run": [{"name": k, "result": "pass" if v else "fail"} for k, v in {**der["checks"], **pred["checks"]}.items()],
                    "checks_not_run": [
                        "independent value of 4 pi alpha^2 / 3 in nb GeV^2 from separately read alpha and (hbar c)^2",
                        "quantitative Z-exchange and gamma-Z interference size at the benchmark point",
                        "QED radiative corrections and running of alpha",
                        "numerical muon-mass correction (no cited muon mass)",
                        "formal proof (SymPy steps trusted, not verified)"],
                    "references_read": [{"citation": f"{src['title']}; {src['authors']}", "location": "section 51.2, eqs. (51.2), (51.3); "
                                         f"{src['identifiers']['url']}; read {src['verification_date']} at level '{src['verification_level']}'"}],
                    "derivation_record": "profiles/theory/qed-benchmark/derivations/derivation-record.md",
                    "inapplicable": ["detector", "data", "blinding", "luminosity", "experiment bindings", "PDFs", "factorization scale", "parton shower"]})
    edges = pred["edges"]
    rel = pred["relative_uncertainty_reference_rounding"]
    vals = pred["dsigma_dcos_bin_averaged_pb"]
    obs = {"quantity": "differential-cross-section", "process": "e+e- -> mu+mu- (one photon, tree level)",
           "variables": [{"name": "cos_theta", "unit": "1", "edges": edges}],
           "phase_space": {"definition": f"full angular range at sqrt(s) = {pred['sqrt_s_gev']} GeV; no cuts", "fiducial": False},
           "level": "parton", "frame": "center-of-mass",
           "normalization": {"kind": "integrated-luminosity", "value": "not-applicable",
                             "convention": "absolute cross section; a comparison multiplies by the measurement's integrated luminosity"},
           "bin_semantics": "bin-averaged", "unit": "pb", "validity_range": {"cos_theta": [-1.0, 1.0]},
           "conventions": {"energy_variable": "sqrt_s", "angle_definition": CONVENTIONS["angle_definition"],
                           "spin_treatment": CONVENTIONS["spin_treatment"], "mass_approximation": "massless final state (beta -> 1)"}}
    prediction = dict(base, artifact_id="qedbench-path-c-prediction", artifact_type="prediction",
                      objective=f"d sigma / d cos theta at sqrt(s) = {pred['sqrt_s_gev']} GeV, tree-level QED",
                      provenance={"producer_skill": "hep-theory", "created": created, "evidence_ids": ["qedbench:C02"]},
                      status=["validated-in-scope"],
                      inputs=[{"ref": "artifacts/theory_spec.json", "artifact_type": "theory-spec", "status": ["validated-in-scope"]}],
                      unresolved_inputs=["higher-order (truncation) and Z-exchange uncertainties are not quantified; see the theory spec"],
                      extension={"observable": obs, "theory_spec_ref": "artifacts/theory_spec.json",
                                 "parameter_point": {"sqrt_s_gev": pred["sqrt_s_gev"]}, "representation": "numerical",
                                 "expression": "d sigma / d cos theta = (3/8) (86.8 nb GeV^2 / s) (1 + cos^2 theta)",
                                 "values": {"edges": edges, "values": vals, "unit": "pb",
                                            "uncertainties": [
                                                {"name": "reference rounding of 86.8 nb GeV^2", "kind": "parametric",
                                                 "values": [v * rel for v in vals], "correlation": "fully-correlated"},
                                                {"name": "numerical integration", "kind": "numerical",
                                                 "values": [pred["convergence"]["quad_abs_error"] / 2.0] * len(vals), "correlation": "unknown"}]},
                                 "uncertainties": [{"name": "missing higher orders and Z exchange", "kind": "truncation", "correlation": "unknown"}],
                                 "allowed_transformations": ["bin-integrate", "rebin", "fiducial-restriction", "unit-conversion",
                                                             "multiply-by-normalization", "level-identification", "forward-fold"]})
    docs = {"theory_spec": spec, "prediction": prediction}
    return docs, {k: {"ok": (r := validate_artifact(v, vocab)).ok, "errors": [f.message for f in r.errors]} for k, v in docs.items()}


def figure(pred, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = np.linspace(-1, 1, 201)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.plot(c, predict.dsigma_dcos(c, pred["sqrt_s_gev"], pred["reference_constant_nb_gev2"]), label="(3/8) sigma (1 + cos^2 theta)")
    ax.stairs(pred["dsigma_dcos_bin_averaged_pb"], pred["edges"], baseline=None, label="bin-averaged")
    ax.set_xlabel("cos theta"); ax.set_ylabel("d sigma / d cos theta [pb]"); ax.set_ylim(bottom=0)
    ax.set_title(f"Tree-level QED, sqrt(s) = {pred['sqrt_s_gev']:g} GeV"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "dsigma_dcos_prediction.png", dpi=110); plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--created", default="2026-10-02")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    (args.out / "artifacts").mkdir(parents=True, exist_ok=True)
    der = derive.derive()
    pred = predict.predict(CFG)
    docs, contract = artifacts(der, pred, args.created)
    for name, doc in docs.items():
        (args.out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
    figure(pred, args.out)
    read = sorted(p for p in OPENED | _imported_profile_code() if p.startswith("profiles/"))
    passes = {"derivation_checks": all(der["checks"].values()), "prediction_checks": all(pred["checks"].values()),
              "contracts": all(c["ok"] for c in contract.values()),
              "no_experiment_resources": not any(p.startswith("profiles/experiments/") for p in read)}
    results = {"label": "theory only; no experiment resource; no synthetic data", "profiles_loaded": [PROFILE["id"]],
               "profile_files_read": read, "pass": passes, "derivation": der, "prediction": pred, "contract_validation": contract}
    (args.out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    write_report(args.out, results)
    print(json.dumps({"pass": passes}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    p, d = r["prediction"], r["derivation"]
    yes = lambda b: "pass" if b else "FAIL"  # noqa: E731
    lines = [
        "# Path C report: standalone tree-level QED benchmark",
        "",
        "Theory only: profile `theory:qed-benchmark`, no experiment profile, no detector, data or blinding fields, "
        f"no GPU and no commercial CAS. Profile files read: {', '.join('`' + x + '`' for x in r['profile_files_read'])}.",
        "",
        "Reproduce: `python3 examples/qed-prediction/run.py` (from the plugin root, D5 environment).",
        "",
        "## Result",
        "",
        f"At sqrt(s) = {p['sqrt_s_gev']:g} GeV (s = {p['s_gev2']:g} GeV^2): sigma = {p['sigma_total_pb']:.1f} pb, and "
        f"sigma(|cos theta| < {p['fiducial_abs_cos_max']}) = {p['sigma_fiducial_pb']:.1f} pb. d sigma / d cos theta = (3/8) sigma (1 + cos^2 theta). "
        f"The reference constant 86.8 nb GeV^2 is rounded to three significant figures, a relative uncertainty of {p['relative_uncertainty_reference_rounding']:.1e}. "
        "Missing higher orders and Z exchange are not quantified.",
        "",
        "## Status",
        "",
        f"Derivation status: `{d['derivation_status']}`. {d['status_note']} The result agrees symbolically with PDG eqs. 51.2 and 51.3 "
        "(section 51.2, read 2026-10-02 at page level). Numerical agreement below is corroboration, not proof.",
        "",
        "| Check | Result |", "|---|---|",
    ]
    lines += [f"| {k} | {yes(v)} |" for k, v in {**d["checks"], **p["checks"]}.items()]
    lines += [f"| contract artifacts | {yes(r['pass']['contracts'])} |", f"| no experiment resource read | {yes(r['pass']['no_experiment_resources'])} |",
              "", "Trapezoid observed order on [-1, 1]: " + ", ".join(f"{o:.2f}" for o in p["convergence"]["trapezoid_observed_order"]) + ".",
              "", "Checks not run: see `artifacts/theory_spec.json` (`checks_not_run`) and the derivation record.",
              "", "Figure: `dsigma_dcos_prediction.png`. Artifacts: `artifacts/theory_spec.json`, `artifacts/prediction.json`.", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())

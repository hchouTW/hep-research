#!/usr/bin/env python3
"""T24 (journey J6): compare the tree-level QED prediction with a SYNTHETIC dataset record shaped like a published
table, using only the record and its covariance. No detector module, response or experiment-profile file is read;
every opened file is recorded and the run fails if one under profiles/experiments/ appears.

Chain: Path C prediction artifact + standalone dataset record -> comparison gate (level identification parton ->
particle-fiducial and fiducial restriction to |cos theta| < 0.9, both justified) -> Gaussian likelihood with the
record's full covariance -> normalization scale mu (analytic GLS) and chi2 -> independent check of mu by whitened
least squares -> contract artifacts and a short report.

Usage (from the plugin root): python3 examples/published-comparison/run.py [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy (D5 environment).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OPENED: set[str] = set()


def _audit(event, args):
    if event == "open" and isinstance(args[0], (str, Path)):
        try:
            OPENED.add(str(Path(args[0]).resolve().relative_to(PLUGIN)))
        except ValueError:
            pass


sys.addaudithook(_audit)
sys.path.insert(0, str(PLUGIN))
import numpy as np  # noqa: E402

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.comparison.gate import gate, side_from_artifact  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

PRED_PATH = PLUGIN / "examples" / "qed-prediction" / "output" / "artifacts" / "prediction.json"
RECORD_PATH = HERE / "synthetic-published-record.json"
TRANSFORMS = [
    {"kind": "level-identification", "owner": "hep-theory", "from": "parton", "to": "particle-fiducial",
     "justification": "tree-level prediction without radiation: the outgoing muon is the stable final-state particle"},
    {"kind": "fiducial-restriction", "owner": "hep-theory", "variable": "cos_theta", "range": [-0.9, 0.9]}]
MAPPINGS = [
    {"key": "angle_definition", "action": "equivalent",
     "justification": "both define theta between the incoming e- (beam) and the outgoing mu- in the c.m. frame"},
    {"key": "synthcol:fiducial_definition", "action": "transform", "transformation": "fiducial-restriction to |cos theta| < 0.9",
     "justification": "the record's fiducial cut is on the binned variable; prediction edges align at +-0.9"}]
PEELLE = ("the record's luminosity block is built from the measured values (fully correlated, proportional to the data); "
          "a Gaussian GLS normalization fit with such a matrix is known to be biased low for multiplicative uncertainties "
          "(Peelle's pertinent puzzle), so mu here can differ from the ratio of fiducial cross sections")
CRITERIA = {"mu_vs_whitened_lstsq_rel": 1e-12, "chi2_p_min": 0.001}


def restrict(pred_doc, lo, hi):
    v = pred_doc["extension"]["values"]
    keep = [i for i, (a, b) in enumerate(zip(v["edges"][:-1], v["edges"][1:])) if a >= lo - 1e-12 and b <= hi + 1e-12]
    return [v["edges"][i] for i in keep] + [v["edges"][keep[-1] + 1]], np.array([v["values"][i] for i in keep])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    args = ap.parse_args(argv)
    out = args.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    pred_doc = json.loads(PRED_PATH.read_text(encoding="utf-8"))
    rec = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    cov_doc = json.loads((HERE / rec["extension"]["covariance"]["ref"]).read_text(encoding="utf-8"))
    cond = dict(kv.split(" = ") for kv in [rec["extension"]["conditions"]])
    cond = {k: float(v) for k, v in cond.items()}
    g = gate(side_from_artifact(pred_doc), side_from_artifact(rec), TRANSFORMS, MAPPINGS, cond)
    if not g["comparable"]:
        (out / "gate_failure.json").write_text(json.dumps(g, indent=1) + "\n")
        print(json.dumps({"gate": "not comparable; inference stopped", "mismatches": g["mismatches"]}, indent=1))
        return 1

    edges, p = restrict(pred_doc, -0.9, 0.9)
    d = np.array(rec["extension"]["data"]["values"])
    c = np.array(cov_doc["matrix"])
    ci = np.linalg.inv(c)
    mu = float(p @ ci @ d / (p @ ci @ p))
    sigma_mu = float(1.0 / np.sqrt(p @ ci @ p))
    r = d - mu * p
    chi2 = float(r @ ci @ r)
    ndf = len(d) - 1
    from scipy.stats import chi2 as chi2_dist
    pval = float(chi2_dist.sf(chi2, ndf))
    L = np.linalg.cholesky(c)
    ref = float(np.linalg.lstsq(np.linalg.solve(L, p)[:, None], np.linalg.solve(L, d), rcond=None)[0][0])
    width = np.diff(edges)
    fid_pred = float(np.sum(p * width))
    detector_reads = sorted(f for f in OPENED if f.startswith("profiles/experiments/"))

    base = {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [], "theory": pred_doc["bindings"]["theory"]},
            "versions": {"plugin": pred_doc["versions"]["plugin"], "contracts": CONTRACTS_VERSION, "profiles": pred_doc["versions"]["profiles"]},
            "outputs": [], "unresolved_inputs": ["truncation (higher orders, Z exchange) not quantified in the prediction"]}
    ins = [{"ref": "../qed-prediction/output/artifacts/prediction.json", "artifact_type": "prediction", "status": pred_doc["status"]},
           {"ref": "synthetic-published-record.json", "artifact_type": "dataset-record", "status": ["synthetic"]}]
    comp = dict(base, artifact_id="synthetic-t24-comparison", artifact_type="comparison-spec", inputs=ins, status=["synthetic"],
                objective="QED prediction vs SYNTHETIC published-style record", provenance={"producer_skill": "hep-statistics", "created": "2026-10-02"},
                extension={"dataset_bindings": [rec["extension"]["dataset_id"]], "prediction_bindings": [pred_doc["artifact_id"]],
                           "gate_result": {"comparable": True, "mismatches": [], "notes": g["notes"]},
                           "transformations": [{k: v for k, v in t.items() if k not in ("before", "after")} for t in g["transformations"]],
                           "correlations": [{"source": "record covariance", "kind": "full matrix as published (synthetic)"}],
                           "inference_assumptions": ["Gaussian likelihood with the record's full covariance",
                                                     "luminosity part of the covariance used as given (fully correlated)"],
                           "limits": ["synthetic record", "no detector information used or needed",
                                      PEELLE]})
    stat = dict(base, artifact_id="synthetic-t24-mu", artifact_type="statistical-result", status=["synthetic"],
                inputs=[{"ref": "artifacts/comparison_spec.json", "artifact_type": "comparison-spec", "status": ["synthetic"]}],
                objective="Normalization scale of the QED prediction on a SYNTHETIC published-style record",
                provenance={"producer_skill": "hep-statistics", "created": "2026-10-02"},
                extension={"paradigm": "frequentist", "likelihood": {"form": "multivariate Gaussian with the record covariance"},
                           "parameters_of_interest": ["mu"], "nuisances": [],
                           "test_statistic": "chi2(mu) = (d - mu p)^T C^-1 (d - mu p)", "construction": "asymptotic",
                           "coverage": {"method": "not studied here; Gaussian, linear in mu, so exact if the covariance is right"},
                           "fit_status": "converged", "results": {"mu_hat": mu, "sigma_mu": sigma_mu, "chi2": chi2, "ndf": ndf, "p_value": pval}})
    docs = {"comparison_spec": comp, "result": stat}
    contract = {k: {"ok": (rp := validate_artifact(v, Vocabulary())).ok, "errors": [f.message for f in rp.errors]} for k, v in docs.items()}
    for k, v in docs.items():
        (out / "artifacts" / f"{k}.json").write_text(json.dumps(v, indent=1) + "\n")
    passes = {"gate_comparable": g["comparable"],
              "mu_matches_whitened_lstsq": abs(mu / ref - 1) < CRITERIA["mu_vs_whitened_lstsq_rel"],
              "chi2_reasonable": pval > CRITERIA["chi2_p_min"],
              "no_detector_files_read": not detector_reads,
              "contracts": all(v["ok"] for v in contract.values())}
    res = {"label": "SYNTHETIC record shaped like a published table; not a physics result", "criteria": CRITERIA, "pass": passes,
           "mu_hat": mu, "sigma_mu": sigma_mu, "mu_whitened_lstsq": ref, "chi2": chi2, "ndf": ndf, "p_value": pval,
           "prediction_restricted_pb": p.tolist(), "fiducial_prediction_pb": fid_pred, "edges": edges,
           "gate_transformations": [t["kind"] for t in g["transformations"]], "gate_notes": g["notes"],
           "files_read": sorted(f for f in OPENED if "__pycache__" not in f and not f.startswith("examples/published-comparison/output")), "detector_files_read": detector_reads,
           "contract_validation": contract}
    (out / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    lines = ["# T24 report: prediction vs a synthetic published-style record (SYNTHETIC)", "",
             "The record (`synthetic-published-record.json`) is synthetic: its values and covariance are copied from the Path B output. "
             "Only the record and its covariance file are used; no detector module, response or experiment-profile file is read.", "",
             "Reproduce: `python3 examples/published-comparison/run.py` (from the plugin root).", "",
             f"Gate: comparable after {', '.join(res['gate_transformations'])} (both justified), with declared convention mappings.", "",
             f"mu = {mu:.4f} ± {sigma_mu:.4f}; chi2 = {chi2:.2f} / {ndf} (p = {pval:.2f}). Whitened least squares gives the same mu "
             f"to {abs(mu / ref - 1):.1e}. Fiducial prediction {fid_pred:.2f} pb.", "",
             f"Limitation: {PEELLE}.", "",
             "| Check | Result |", "|---|---|"] + [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in passes.items()] + [
             "", "Files read: " + ", ".join(f"`{f}`" for f in res["files_read"] if not f.endswith(".pyc")), ""]
    (out / "report.md").write_text("\n".join(lines))
    print(json.dumps({"pass": passes, "mu_hat": mu, "sigma_mu": sigma_mu}, indent=1))
    return 0 if all(passes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

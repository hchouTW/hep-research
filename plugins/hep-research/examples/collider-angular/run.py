#!/usr/bin/env python3
"""Path B (journey J3): SYNTHETIC corrected e+e- -> mu+mu- angular distribution with the illustrative
experiment:synthetic-collider profile.

SYNTHETIC and ILLUSTRATIVE. The generator, efficiency, resolution and luminosity are invented
(profiles/experiments/synthetic-collider/benchmarks/path-b.json) and describe no real experiment. Only that
profile is loaded; no AMS or theory resource is read.

Chain: seeded synthetic signal and background events (profile generator) -> reconstructed cos theta histograms of
selected events in the signal region (x_vis >= 0.9), the control sideband (0.5 <= x_vis < 0.8) and the validation
band (0.8 <= x_vis < 0.9) -> blinding: the signal-region bin cos theta >= 0.9 is masked by the custodian step
(skills/hep-measurement/scripts/mask_blinded_bins.py) before the analysis reads the counts, and the analysis fills it
with its simulated expectation -> background = transfer factor x control-sideband counts, subtracted per reco bin,
with a closure test in the validation band -> full-rank unfolding with an analytic response that includes the
efficiency (core.stats linear_matrix) -> d sigma / d cos theta = unfolded truth counts / (integrated luminosity x
bin width) in the fiducial region |cos theta| < 0.9 -> covariance (statistical, a 10% transfer-factor term and a
2% luminosity term, both fully correlated) -> fiducial cross section -> comparison with independent expected values
(analytic bin integrals of the generator shape) -> Asimov closure and seeded toy closure (counts, transfer factor
and luminosity fluctuated, the same blinded procedure) -> contract artifacts, figures, report.

Blinding (synthetic policy): the forward signal region cos theta >= 0.9, outside the reported fiducial range, is
reserved for a separate synthetic forward analysis. Its signal-region count never reaches results, report, figure
or artifacts; the sidebands stay open, as the background estimate needs them. Unblinding is not done here.

Usage (from the plugin root): python3 examples/collider-angular/run.py [--toys 400] [--seed 20261003] [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy and matplotlib (D5 environment).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
PROFILE_DIR = PLUGIN / "profiles" / "experiments" / "synthetic-collider"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PROFILE_DIR / "scripts"))
import detector  # noqa: E402
import generate_events  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.blinding.blinding import blinded_mask, check_figure  # noqa: E402
from core.stats.unfolding_diagnostics import linear_matrix  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from contracts.response_adapter import to_validator_input  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
CFG = json.loads((PROFILE_DIR / "benchmarks" / "path-b.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
CRITERIA = {"asimov_max_rel_dev": 1e-9, "toy_mean_pull_abs": 0.2, "toy_pull_width": (0.85, 1.15),
            "fiducial_toy_mean_pull_abs": 0.2, "fiducial_toy_pull_width": (0.85, 1.15),
            "background_asimov_max_rel_dev": 1e-12, "validation_band_abs_pull": 3.0, "validation_band_chi2_p_min": 1e-3}

TE = np.array(CFG["truth_edges"])
RE = np.array(CFG["reco_edges"])
WIDTH = np.diff(TE)
REP = slice(*CFG["reported_truth_bins"])
LUMI = CFG["integrated_luminosity_pb"]
LUMI_REL = CFG["luminosity_rel_uncertainty"]

# SYNTHETIC analysis choices (not profile numbers): x_vis regions, transfer-factor uncertainty, blinding policy
SIGNAL_REGION = (0.9, math.inf)
CONTROL_REGION = (0.5, 0.8)
VALIDATION_REGION = (0.8, 0.9)
TF_SR = generate_events.xvis_fraction(CFG, *SIGNAL_REGION, "background") / generate_events.xvis_fraction(CFG, *CONTROL_REGION, "background")
TF_VR = generate_events.xvis_fraction(CFG, *VALIDATION_REGION, "background") / generate_events.xvis_fraction(CFG, *CONTROL_REGION, "background")
TF_REL = 0.10  # synthetic: modelling of the background x_vis shape, fully correlated across bins
BLIND = {"variable": "cos_theta", "low": 0.9, "high": 1.0}
BLINDED = np.array(blinded_mask(RE, BLIND))  # reco bins (same edges as truth) whose signal-region count is masked
MASK_SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "mask_blinded_bins.py"


def expected_dsigma(sigma, a, b):
    """Independent expected values: analytic integral of f(c) = 1 + a c^2 + b c over each truth bin."""
    prim = lambda c: c + a * c ** 3 / 3 + b * c ** 2 / 2  # noqa: E731
    norm = prim(1.0) - prim(-1.0)
    return sigma * (prim(TE[1:]) - prim(TE[:-1])) / norm / WIDTH  # pb per unit cos theta, bin-averaged


def reco_histogram(ev, region=None):
    """Selected events per reco cos theta bin, optionally inside an x_vis region [lo, hi)."""
    sel = ev["selected"] & (ev["reco_cos"] >= RE[0]) & (ev["reco_cos"] < RE[-1])
    if region is not None:
        sel &= (ev["x_vis"] >= region[0]) & (ev["x_vis"] < region[1])
    return np.histogram(ev["reco_cos"][sel], bins=RE)[0].astype(float)


def truth_counts(sigma, a, b):
    """Expected generated events per truth bin for a 1 + a c^2 + b c shape with cross section sigma."""
    prim = lambda c: c + a * c ** 3 / 3 + b * c ** 2 / 2  # noqa: E731
    return LUMI * sigma * (prim(TE[1:]) - prim(TE[:-1])) / (prim(1.0) - prim(-1.0))


def expected_background():
    """Simulated background per reco bin in each x_vis region (analytic: detector response x x_vis fractions)."""
    bg = CFG["background"]
    mb = detector.response(CFG, bg["shape_a"], bg["shape_b"])["matrix"]
    reco = mb @ truth_counts(bg["sigma_pb"], bg["shape_a"], bg["shape_b"])
    return {name: reco * generate_events.xvis_fraction(CFG, *rg, "background")
            for name, rg in (("sr", SIGNAL_REGION), ("cr", CONTROL_REGION), ("vr", VALIDATION_REGION))}


def analyse(sr, cr, m, lumi_used, tf_used, fill):
    """Background-subtracted unfolding. sr: signal-region counts with None in blinded bins (as released by the
    custodian step); a blinded bin takes the simulated signal expectation fill[k] with no variance, so no published
    number depends on its count. cr: control-sideband counts; background = tf_used x cr."""
    blind = np.array([v is None for v in sr])
    n = np.array([0.0 if v is None else float(v) for v in sr])
    bkg = np.where(blind, 0.0, tf_used * cr)
    s = np.where(blind, fill, n - bkg)
    var = np.where(blind, 0.0, n + tf_used ** 2 * cr)
    a = np.array(linear_matrix("tsvd", len(TE) - 1, m.tolist(), np.maximum(var, 1.0).tolist()))
    u = a @ s
    cov_u = a @ np.diag(var) @ a.T
    cov_b = a @ (np.outer(bkg, bkg) * TF_REL ** 2) @ a.T
    scale = 1.0 / (lumi_used * WIDTH)
    x = u * scale
    stat = cov_u * np.outer(scale, scale)
    bkg_cov = cov_b * np.outer(scale, scale)
    lumi = np.outer(x, x) * LUMI_REL ** 2
    fid = float(np.sum(x[REP] * WIDTH[REP]))
    w = WIDTH[REP]
    fid_var = {"stat": float(w @ stat[REP, REP] @ w), "background": float(w @ bkg_cov[REP, REP] @ w),
               "lumi": float(w @ lumi[REP, REP] @ w)}
    return {"dsigma": x, "stat": stat, "background": bkg_cov, "lumi": lumi, "total": stat + bkg_cov + lumi, "unfolded": u,
            "fiducial_pb": fid, "fiducial_var": fid_var, "background_estimate": tf_used * cr, "subtracted": s}


def pseudo_data(seed):
    """SYNTHETIC pseudo-data per reco bin in the three x_vis bands: the signal sample of the profile generator
    (unchanged), its x_vis from its own stream, and the background sample. 'sr' is unmasked: only the custodian step
    (and a test acting as custodian) may read it."""
    ev = generate_events.generate(CFG, seed)
    ev["x_vis"] = generate_events.signal_xvis(CFG, ev["meta"]["n_generated"], seed + 3)
    bk = generate_events.generate_background(CFG, seed + 2)
    data = {k: np.concatenate([ev[k], bk[k]]) for k in ("selected", "reco_cos", "x_vis")}
    return {"sr": reco_histogram(data, SIGNAL_REGION), "cr": reco_histogram(data, CONTROL_REGION),
            "vr": reco_histogram(data, VALIDATION_REGION)}


def blind_counts(values):
    """The analysis-side view of a signal-region histogram: blinded bins are None."""
    return [None if b else float(v) for v, b in zip(values, BLINDED)]


def custodian_mask(sr_counts, expected_sr, out):
    """SYNTHETIC stand-in for the data custodian's preparation step: the unmasked histogram exists only in a temporary
    directory outside the outputs; mask_blinded_bins.py writes the released masked histogram (and the masked
    data/expectation ratio) into the outputs, and the analysis reads only that file."""
    import tempfile
    sys.path.insert(0, str(MASK_SCRIPT.parent))
    import mask_blinded_bins
    target = out / "blinded" / "signal_region_counts.masked.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hist, ref = Path(tmp) / "hist.json", Path(tmp) / "expected.json"
        hist.write_text(json.dumps({"edges": RE.tolist(), "values": sr_counts.tolist()}))
        ref.write_text(json.dumps({"edges": RE.tolist(), "values": expected_sr.tolist()}))
        code = mask_blinded_bins.main(["--hist", str(hist), "--low", str(BLIND["low"]), "--high", str(BLIND["high"]),
                                       "--reference", str(ref), "--status", "synthetic", "--out", str(target)])
    if code != 0:
        raise RuntimeError("the masking step failed: nothing may be analysed")
    released = json.loads(target.read_text(encoding="utf-8"))
    return released["values"], target


def validation_closure(vr, cr, tf):
    """Closure of the sideband method in the validation band (signal-free by construction): predicted tf x cr against
    the observed counts, per bin and in total, statistical uncertainties only (the strict form of the test)."""
    pred = tf * cr
    var = pred + tf ** 2 * cr
    ok = var > 0
    chi2_val = float(np.sum((vr - pred)[ok] ** 2 / var[ok]))
    ndf = int(ok.sum())
    pull = float((vr.sum() - pred.sum()) / math.sqrt(var.sum()))
    return {"observed": vr.tolist(), "predicted": pred.tolist(), "total_observed": float(vr.sum()),
            "total_predicted": float(pred.sum()), "total_pull": pull, "chi2": chi2_val, "ndf": ndf,
            "p_value": _chi2_sf(chi2_val, ndf)}


def chi2(x, ref, cov):
    d = (x - ref)[REP]
    c = cov[REP, REP]
    val = float(d @ np.linalg.solve(c, d))
    ndf = len(d)
    return val, ndf, _chi2_sf(val, ndf)


def _chi2_sf(x, k):
    from core.stats.statistical_toys import chi2_sf
    return chi2_sf(x, k)


def toy_closure(m, mu_reco, bkg_exp, expected, fid_expected, toys, seed):
    """Toys of the published (blinded) procedure: signal, background and sideband counts, the transfer factor and the
    luminosity fluctuate; the blinded bin is filled with the expectation as for the data."""
    rng = np.random.default_rng(seed)
    pulls, fid_pulls = [], []
    for _ in range(toys):
        sr = rng.poisson(mu_reco).astype(float) + rng.poisson(bkg_exp["sr"]).astype(float)
        cr = rng.poisson(bkg_exp["cr"]).astype(float)
        lumi_hat = LUMI * (1.0 + LUMI_REL * rng.normal())  # the luminosity measurement fluctuates around the true value
        tf_hat = TF_SR * (1.0 + TF_REL * rng.normal())  # so does the transfer factor taken from the simulation
        r = analyse(blind_counts(sr), cr, m, lumi_hat, tf_hat, mu_reco)
        pulls.append(((r["dsigma"] - expected) / np.sqrt(np.diag(r["total"])))[REP])
        fid_pulls.append((r["fiducial_pb"] - fid_expected) / math.sqrt(sum(r["fiducial_var"].values())))
    p = np.array(pulls)
    return {"mean_per_bin": p.mean(axis=0).round(4).tolist(), "width_per_bin": p.std(axis=0, ddof=1).round(4).tolist(),
            "fiducial_mean_pull": round(float(np.mean(fid_pulls)), 4), "fiducial_pull_width": round(float(np.std(fid_pulls, ddof=1)), 4)}


def artifacts(res, resp, created):
    vocab = Vocabulary.with_profiles([PROFILE])
    edges = TE[REP.start:REP.stop + 1].tolist()
    base = {"contract_version": CONTRACTS_VERSION,
            "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {PROFILE["id"]: PROFILE["version"]}},
            "inputs": [], "outputs": [], "unresolved_inputs": []}
    obs = {"quantity": "differential-cross-section", "process": "e+e- -> mu+mu- (synthetic generator)",
           "variables": [{"name": "cos_theta", "unit": "1", "edges": edges}],
           "phase_space": {"definition": "SYNTHETIC: |cos theta| < 0.9 at particle level, fixed sqrt(s) = 10 GeV", "fiducial": True},
           "level": "particle-fiducial", "frame": "center-of-mass",
           "normalization": {"kind": "integrated-luminosity", "value": LUMI, "unit": "pb^-1",
                             "convention": "unfolded truth counts / (integrated luminosity x bin width)"},
           "bin_semantics": "bin-averaged", "unit": "pb",
           "conventions": {"energy_variable": "sqrt_s", "angle_definition": "theta between the incoming e- beam and the outgoing mu-",
                           "synthcol:fiducial_definition": "|cos theta| < 0.9 at particle level"}}
    spec = dict(base, artifact_id="synthetic-path-b-measurement-spec", artifact_type="measurement-spec",
                objective="SYNTHETIC Path B: corrected d sigma / d cos theta in the fiducial region (illustrative profile)",
                provenance={"producer_skill": "hep-measurement", "created": created}, status=["synthetic"],
                extension={"estimand": ("SYNTHETIC: the differential cross section d sigma / d cos theta of e+e- -> mu+mu- at "
                                        "fixed sqrt(s) = 10 GeV, at particle level in the fiducial region |cos theta| < 0.9, "
                                        "center-of-mass frame"),
                           "observable": obs, "species_or_process": "e+e- -> mu+mu- (synthetic)", "period": "not-applicable",
                           "selections": [{"name": "synthetic event selection", "definition": "efficiency e0 - e1 cos^4 theta (invented)",
                                           "conditional_denominator": "generated events in the truth bin"},
                                          {"name": "signal region", "definition": "SYNTHETIC: visible-energy fraction x_vis >= 0.9",
                                           "conditional_denominator": "selected events (signal x_vis = 1 + N(0, 0.01): inside by construction)"}],
                           "backgrounds": [{"name": "synthetic tau-pair-like background",
                                            "estimator": "sideband extrapolation in x_vis: B_k = TF x N_CR,k per reco cos theta bin, "
                                                         "TF = f(SR) / f(CR) from the simulated background x_vis shape",
                                            "control_region": "SYNTHETIC: 0.5 <= x_vis < 0.8 (signal-free by construction)",
                                            "closure": "SYNTHETIC: validation band 0.8 <= x_vis < 0.9 predicted from the control "
                                                       "sideband (results.json#background/validation_closure); Asimov closure exact",
                                            "transfer_factor": TF_SR,
                                            "uncertainty": "10% on TF, fully correlated (synthetic x_vis shape modelling); "
                                                           "control-sideband counts in the statistical block"}],
                           "corrections": [
                               {"effect_id": "efficiency_and_migration", "category": "migration", "applied_in": "response_matrix"}],
                           "systematics": [{"name": "luminosity", "source": "synthetic 2% assumption", "effect": "normalization",
                                            "applied_via": "covariance (fully correlated across bins)"},
                                           {"name": "background_transfer_factor", "source": "synthetic 10% on the x_vis transfer factor",
                                            "effect": "mixed", "applied_via": "covariance (TF x control counts, fully correlated, unfolded)"}],
                           "blinding": {"blinded": True,
                                        "mask": {"regions": ["signal region x_vis >= 0.9 in the forward bin cos theta >= 0.9"],
                                                 "intervals": [dict(BLIND)]},
                                        "unblinding_record_ref": None},
                           "notes": ("SYNTHETIC blinding policy: the forward signal-region bin, outside the reported fiducial "
                                     "range, is masked by the custodian step and filled with the simulated expectation in "
                                     "the unfolding; the sidebands stay open"),
                           "experiment_fields": {"synthcol:note": "ILLUSTRATIVE and SYNTHETIC; every number is invented"}})
    response_doc = dict(base, artifact_id="synthetic-path-b-response", artifact_type="response",
                        objective="SYNTHETIC cos theta response including the efficiency", status=["synthetic"],
                        provenance={"producer_skill": "hep-detector", "created": created},
                        extension={"truth_axis": {"name": "cos_theta", "unit": "1", "edges": TE.tolist()},
                                   "reco_axis": {"name": "cos_theta", "unit": "1", "edges": RE.tolist()},
                                   "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
                                   "inefficiency": "inside_matrix", "acceptance": "inside_matrix", "includes": ["migration", "efficiency"],
                                   "applied_separately": ["luminosity"],
                                   "underflow_overflow": "explicit_bins", "intended_use": "unfolding",
                                   "conditions": "single synthetic run",
                                   "provenance": "analytic integration of the synthetic detector model; reco outside [-1, 1] is "
                                                 "kept in explicit underflow/overflow vectors; outer truth bins are buffers",
                                   "matrix_ref": "matrices/response.json", "form": "matrix"})
    stat = dict(base, artifact_id="synthetic-path-b-result", artifact_type="statistical-result", required_capabilities=["stats:result-semantics"],
                objective="SYNTHETIC corrected angular distribution and fiducial cross section with covariance",
                provenance={"producer_skill": "hep-statistics", "created": created}, status=["synthetic"],
                inputs=[{"ref": "artifacts/measurement_spec.json", "artifact_type": "measurement-spec", "status": ["synthetic"]}],
                extension={"paradigm": "frequentist",
                           "likelihood": {"form": "Poisson counts per reco bin; unfolding by full-rank weighted least squares (no regularization)"},
                           "parameters_of_interest": ["d sigma / d cos theta per fiducial bin", "fiducial cross section"],
                           "nuisances": ["integrated luminosity", "background transfer factor"],
                           "test_statistic": "not-applicable (point estimates with linear covariance)", "construction": "other",
                           "coverage": {"check": "not-checked", "method": "seeded toys of counts and luminosity (closure and pulls, not interval coverage)", "result_ref": "results.json#toy_closure"},
                           "fit_status": "converged", "results": {"ref": "results.json#dsigma"}})
    data = dict(base, artifact_id="synthetic-path-b-dsigma", artifact_type="dataset-record",
                objective="SYNTHETIC corrected d sigma / d cos theta (illustrative)", status=["synthetic"],
                provenance={"producer_skill": "hep-measurement", "created": created},
                extension={"dataset_id": "synthcol:synthetic-path-b-dsigma", "source_evidence_ids": [], "observable": obs,
                           "data": {"edges": edges, "values": res["dsigma"][REP].tolist(), "unit": "pb",
                                    "uncertainties": [{"name": "total", "kind": "statistical", "correlation": "covariance",
                                                       "covariance_ref": "results.json#dsigma/covariance"}]},
                           "covariance": {"status": "present", "ref": "results.json#dsigma/covariance"},
                           "period": "not-applicable", "status": "synthetic", "experiment_profile": PROFILE["id"]})
    docs = {"measurement_spec": spec, "response": response_doc, "result": stat, "dataset_record": data}
    return docs, {k: {"ok": (r := validate_artifact(v, vocab)).ok, "errors": [f.message for f in r.errors]} for k, v in docs.items()}


def figures(res, expected, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = 0.5 * (TE[1:] + TE[:-1])
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.errorbar(c[REP], res["dsigma"][REP], yerr=np.sqrt(np.diag(res["total"]))[REP], fmt="o", ms=4,  # no x bars: they would touch the blinded edge
                label="SYNTHETIC corrected data")
    ax.stairs(expected[REP], TE[REP.start:REP.stop + 1], baseline=None, label="expected (generator shape, analytic)")
    ax.set_xlabel("cos theta"); ax.set_ylabel("d sigma / d cos theta [pb]"); ax.set_ylim(bottom=0); ax.set_title("SYNTHETIC Path B (illustrative)")
    ax.legend(fontsize=7); fig.tight_layout()
    found = check_figure(fig, BLIND)  # nothing may be drawn inside the blinded cos theta range
    if not found:
        fig.savefig(out / "dsigma_dcos.png", dpi=110)
    plt.close(fig)
    return {"status": "pass" if not found else "fail", "artists_in_blinded_range": len(found)}


def review_spec(spec, vocab, out):
    """Verdict-first review draft of the spec with the hep-measurement review script (references/review-and-artifacts.md)."""
    sys.path.insert(0, str(PLUGIN / "skills" / "hep-measurement" / "scripts"))
    import review_measurement_spec
    review = review_measurement_spec.draft(spec, vocab)
    (out / "review.md").write_text(review_measurement_spec.markdown(review, spec["artifact_id"], "synthetic"))
    return {"verdict": review["verdict"], "defects": len(review["defects"]), "unresolved": len(review["unresolved"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--toys", type=int, default=CFG["toys"])
    ap.add_argument("--seed", type=int, default=CFG["seed"])
    ap.add_argument("--created", default="2026-10-02")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    out = args.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    g = CFG["generator"]
    resp = detector.response(CFG, g["shape_a"], g["shape_b"])
    m = resp["matrix"]
    expected = expected_dsigma(g["sigma_pb"], g["shape_a"], g["shape_b"])
    fid_expected = float(np.sum(expected[REP] * WIDTH[REP]))
    mu_truth = LUMI * expected * WIDTH
    mu_reco = m @ mu_truth
    bkg_exp = expected_background()

    asimov = analyse(blind_counts(mu_reco + bkg_exp["sr"]), bkg_exp["cr"], m, LUMI, TF_SR, mu_reco)
    asimov_dev = float(np.max(np.abs(asimov["dsigma"][REP] / expected[REP] - 1)))
    asimov_fid_dev = abs(asimov["fiducial_pb"] / fid_expected - 1)
    bkg_asimov_dev = float(np.max(np.abs(TF_SR * bkg_exp["cr"] / bkg_exp["sr"] - 1)))

    data = pseudo_data(args.seed)
    cr, vr = data["cr"], data["vr"]
    # custodian step: the signal-region histogram is masked before the analysis sees it
    sr_released, masked_file = custodian_mask(data["sr"], mu_reco + bkg_exp["sr"], out)
    del data["sr"]
    res = analyse(sr_released, cr, m, LUMI, TF_SR, mu_reco)
    c2 = chi2(res["dsigma"], expected, res["total"])
    vclos = validation_closure(vr, cr, TF_VR)
    toys = toy_closure(m, mu_reco, bkg_exp, expected, fid_expected, args.toys, args.seed + 1)

    docs, contract = artifacts(res, resp, args.created)
    # the validator input comes from the response artifact itself (contracts.response_adapter), not a second declaration
    rv = validate_response(to_validator_input(docs["response"]["extension"], matrix=m.tolist(),
                                              underflow=resp["underflow"].tolist(), overflow=resp["overflow"].tolist())["input"])
    labels = [f"b{j}" for j in range(REP.start, REP.stop)]
    cv = validate_covariance({"labels": labels, "kind": "absolute", "units": "pb^2", "matrix": res["total"][REP, REP].tolist(),
                              "blocks": {"stat": res["stat"][REP, REP].tolist(), "background": res["background"][REP, REP].tolist(),
                                         "lumi": res["lumi"][REP, REP].tolist()}})
    for name, doc in docs.items():
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
    # the matrix_ref target: the matrix with its underflow/overflow vectors, inside the artifact folder
    (out / "artifacts" / "matrices").mkdir(exist_ok=True)
    (out / "artifacts" / "matrices" / "response.json").write_text(json.dumps(
        {"matrix": m.tolist(), "underflow": resp["underflow"].tolist(), "overflow": resp["overflow"].tolist()}, indent=1) + "\n")
    fig_check = figures(res, expected, out)

    passes = {
        "asimov_closure": max(asimov_dev, asimov_fid_dev) < CRITERIA["asimov_max_rel_dev"],
        "toy_mean_pull": all(abs(v) < CRITERIA["toy_mean_pull_abs"] for v in toys["mean_per_bin"]),
        "toy_pull_width": all(CRITERIA["toy_pull_width"][0] < v < CRITERIA["toy_pull_width"][1] for v in toys["width_per_bin"]),
        "fiducial_toy_pull": abs(toys["fiducial_mean_pull"]) < CRITERIA["fiducial_toy_mean_pull_abs"]
                             and CRITERIA["fiducial_toy_pull_width"][0] < toys["fiducial_pull_width"] < CRITERIA["fiducial_toy_pull_width"][1],
        "background_asimov_closure": bkg_asimov_dev < CRITERIA["background_asimov_max_rel_dev"],
        "background_validation_closure": abs(vclos["total_pull"]) < CRITERIA["validation_band_abs_pull"]
                                         and vclos["p_value"] > CRITERIA["validation_band_chi2_p_min"],
        "blinded_figure": fig_check["status"] == "pass",
        "response_validation": rv["status"] != "fail",
        "covariance_validation": cv["status"] != "fail",
        "contracts": all(c["ok"] for c in contract.values()),
    }
    review = review_spec(docs["measurement_spec"], Vocabulary.with_profiles([PROFILE]), out)
    passes["review_verdict"] = review["verdict"] == "acceptable-with-open-inputs"
    pub = lambda v: [None if b else x for x, b in zip(np.asarray(v).tolist(), BLINDED)]  # noqa: E731
    pub_cov = lambda c: [pub(row) if not b else [None] * len(row) for row, b in zip(np.asarray(c).tolist(), BLINDED)]  # noqa: E731
    results = {
        "label": "SYNTHETIC and ILLUSTRATIVE: invented inputs; describes no experiment",
        "review": review,
        "profiles_loaded": [PROFILE["id"]],
        "seed": args.seed, "toys": args.toys, "criteria": CRITERIA, "pass": passes,
        "config": CFG, "truth_edges": TE.tolist(), "reported_truth_bins": [REP.start, REP.stop],
        "blinding": {"region": BLIND, "blinded_reco_bins": [int(j) for j in np.flatnonzero(BLINDED)],
                     "released_signal_region_histogram": masked_file.relative_to(out).as_posix(),
                     "procedure": "custodian masks the signal-region count (mask_blinded_bins.py); the analysis fills the "
                                  "blinded bin with the simulated signal expectation and zero variance; values in blinded "
                                  "bins are null in every output; sidebands are open",
                     "figure_check": fig_check, "unblinded": False},
        "n_selected_signal_region_unblinded_bins": float(sum(v for v in sr_released if v is not None)),
        "reco_counts": sr_released,
        "response": {"matrix": m.tolist(), "efficiency": resp["efficiency"].tolist(),
                     "underflow": resp["underflow"].tolist(), "overflow": resp["overflow"].tolist()},
        "background": {"regions_x_vis": {"signal": [SIGNAL_REGION[0], "inf"], "control": list(CONTROL_REGION),
                                         "validation": list(VALIDATION_REGION)},
                       "transfer_factor_signal_region": TF_SR, "transfer_factor_validation_band": TF_VR,
                       "transfer_factor_rel_uncertainty": TF_REL,
                       "control_region_counts": cr.tolist(), "estimate_signal_region": pub(res["background_estimate"]),
                       "expected_signal_region": bkg_exp["sr"].tolist(),
                       "asimov_closure_max_rel_dev": bkg_asimov_dev, "validation_closure": vclos},
        "dsigma": {"values": pub(res["dsigma"]), "expected": expected.tolist(),
                   "covariance": {k: pub_cov(res[k]) for k in ("stat", "background", "lumi", "total")}},
        "fiducial_cross_section_pb": {"value": res["fiducial_pb"], "stat": math.sqrt(res["fiducial_var"]["stat"]),
                                      "background": math.sqrt(res["fiducial_var"]["background"]),
                                      "lumi": math.sqrt(res["fiducial_var"]["lumi"]), "expected": fid_expected},
        "chi2_vs_expected": {"chi2": c2[0], "ndf": c2[1], "p_value": c2[2],
                             "note": "consistency of one synthetic sample with its own generator; not a physics test"},
        "asimov_closure": {"max_rel_dev_dsigma": asimov_dev, "rel_dev_fiducial": asimov_fid_dev},
        "toy_closure": toys, "response_validation": rv["status"], "covariance_validation": cv["status"],
        "contract_validation": contract,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    write_report(out, results)
    digest = hashlib.sha256((out / "results.json").read_bytes()).hexdigest()
    print(json.dumps({"pass": passes, "results_sha256": digest}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    fmt = lambda v: ", ".join(f"{x:.4g}" for x in v)  # noqa: E731
    rep = slice(*r["reported_truth_bins"])
    f = r["fiducial_cross_section_pb"]
    b = r["background"]
    v = b["validation_closure"]
    yes = lambda k: "pass" if r["pass"][k] else "FAIL"  # noqa: E731
    lines = [
        "# Path B report: synthetic corrected angular distribution (SYNTHETIC, ILLUSTRATIVE)",
        "",
        "**Status: synthetic.** Profile `experiment:synthetic-collider` is illustrative: its generator, efficiency, resolution and "
        "luminosity are invented (`profiles/experiments/synthetic-collider/benchmarks/path-b.json`). Nothing here describes a real "
        "detector or measurement, and the generator's shape and cross section are inputs, not predictions. Only this profile is loaded.",
        "",
        f"Reproduce: `python3 examples/collider-angular/run.py --toys {r['toys']} --seed {r['seed']}` (from the plugin root, D5 environment).",
        "",
        "## Pre-declared criteria and outcome",
        "",
        "| Check | Criterion | Result |",
        "|---|---|---|",
        f"| Asimov closure (d sigma / d cos theta and fiducial sigma) | relative deviation < {r['criteria']['asimov_max_rel_dev']} | {yes('asimov_closure')} (max {max(r['asimov_closure'].values()):.1e}) |",
        f"| Toy closure, mean pull per bin | abs < {r['criteria']['toy_mean_pull_abs']} | {yes('toy_mean_pull')} |",
        f"| Toy closure, pull width per bin | in {tuple(r['criteria']['toy_pull_width'])} | {yes('toy_pull_width')} |",
        f"| Toy closure, fiducial cross section | mean abs < 0.2, width in (0.85, 1.15) | {yes('fiducial_toy_pull')} (mean {r['toy_closure']['fiducial_mean_pull']}, width {r['toy_closure']['fiducial_pull_width']}) |",
        f"| Background estimate, Asimov closure | TF x expected control = expected signal-region background, relative < {r['criteria']['background_asimov_max_rel_dev']} | {yes('background_asimov_closure')} (max {b['asimov_closure_max_rel_dev']:.1e}) |",
        f"| Background estimate, validation band 0.8 <= x_vis < 0.9 | abs total pull < {r['criteria']['validation_band_abs_pull']} and chi2 p > {r['criteria']['validation_band_chi2_p_min']} | {yes('background_validation_closure')} (observed {v['total_observed']:.0f}, predicted {v['total_predicted']:.1f}, pull {v['total_pull']:.2f}; chi2 {v['chi2']:.1f} / {v['ndf']}, p = {v['p_value']:.2f}) |",
        f"| Figure drawn outside the blinded range (core.blinding.check_figure) | no artist inside | {yes('blinded_figure')} |",
        f"| Response and covariance validators (core.stats) | no failure | {'pass' if r['pass']['response_validation'] and r['pass']['covariance_validation'] else 'FAIL'} |",
        f"| Contract artifacts (profile vocabulary) | all valid | {yes('contracts')} |",
        "",
        "The covariance validator warns that the luminosity and background blocks have rank 1. That is expected: one luminosity "
        "and one transfer factor scale every bin together.",
        "",
        "## Blinding (synthetic policy)",
        "",
        "The forward signal-region bin cos theta >= 0.9 (x_vis >= 0.9), outside the reported fiducial range, is blinded for a "
        "separate synthetic forward analysis. A custodian step (`skills/hep-measurement/scripts/mask_blinded_bins.py`) masks its count "
        f"before the analysis reads the histogram; the released file is `{r['blinding']['released_signal_region_histogram']}`. The "
        "unfolding fills the blinded bin with the simulated signal expectation and zero variance, so no published number depends "
        "on its count, and every value in that bin is null in `results.json`. The control and validation sidebands stay open: the "
        "background estimate needs them. Nothing here unblinds; that is done by an authorized person outside the agent session.",
        "",
        "## Result on the synthetic sample",
        "",
        f"{r['n_selected_signal_region_unblinded_bins']:.0f} selected signal-region events in the unblinded bins; estimated "
        f"background there {sum(x for x in b['estimate_signal_region'] if x is not None):.1f} events (TF = {b['transfer_factor_signal_region']:.4f} "
        f"x {sum(b['control_region_counts']):.0f} control-sideband events in all bins). Fiducial cross section (|cos theta| < 0.9): "
        f"{f['value']:.2f} ± {f['stat']:.2f} (stat) ± {f['background']:.2f} (background) ± {f['lumi']:.2f} (lumi) pb; expected "
        f"from the generator inputs {f['expected']:.2f} pb.",
        "",
        f"d sigma / d cos theta per bin (pb): {fmt(r['dsigma']['values'][rep.start:rep.stop])}",
        f"Expected (analytic bin integrals of the generator shape): {fmt(r['dsigma']['expected'][rep.start:rep.stop])}",
        f"chi2 against expected with the full covariance: {r['chi2_vs_expected']['chi2']:.2f} / {r['chi2_vs_expected']['ndf']} "
        f"(p = {r['chi2_vs_expected']['p_value']:.2f}). This only checks the chain on its own synthetic input.",
        "",
        "## What the chain does",
        "",
        "Synthetic signal and background events are generated with the profile's generator, kept with the invented efficiency and "
        "smeared in cos theta. Selected events are histogrammed in reconstructed cos theta in three bands of the visible-energy "
        "fraction x_vis: the signal region (>= 0.9), the control sideband (0.5-0.8, signal-free) and the validation band (0.8-0.9). "
        "The background in the signal region is the control count times a transfer factor from the simulated background x_vis "
        "shape, subtracted bin by bin (10% fully correlated transfer-factor uncertainty). A full-rank unfolding with an analytic response that includes "
        "the efficiency (normalized per generated truth event, so column sums are the bin efficiencies) returns generated truth counts per bin. Dividing by the integrated "
        "luminosity and the bin width gives the bin-averaged d sigma / d cos theta. The outer truth bins (|cos theta| > 0.9) "
        "absorb migration and are not reported. The covariance has a statistical block (signal-region and control counts), a "
        "background block (transfer factor) and a fully correlated 2% luminosity block.",
        "",
        f"Toys: {r['toys']} pseudo-experiments (seed {r['seed'] + 1}) fluctuate the signal-region and control counts (Poisson), the transfer factor and the luminosity estimate, "
        "and apply the same blinded procedure.",
        "",
        "| Bin | mean pull | pull width |", "|---|---|---|",
    ]
    for j, (mu, w) in enumerate(zip(r["toy_closure"]["mean_per_bin"], r["toy_closure"]["width_per_bin"])):
        lo, hi = r["truth_edges"][rep.start + j], r["truth_edges"][rep.start + j + 1]
        lines.append(f"| [{lo:g}, {hi:g}) | {mu} | {w} |")
    lines += ["", "## Limitations (by construction)", "",
              "- The response uses the generated shape inside each bin; model dependence of the unfolding is not studied.",
              "- The background's x_vis shape factorizes from cos theta by construction, so one transfer factor serves every bin.",
              "- No radiative corrections, charge confusion or beam-energy spread are modeled.",
              "- Efficiency and resolution are assumed exactly known; only the luminosity and the transfer factor carry a systematic.",
              "- Passing these checks shows internal consistency on synthetic data, nothing about a real detector.",
              "", "Figure: `dsigma_dcos.png`. Artifacts: `artifacts/*.json` (status `synthetic`).", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Path B (journey J3): SYNTHETIC corrected e+e- -> mu+mu- angular distribution with the illustrative
experiment:synthetic-collider profile.

SYNTHETIC and ILLUSTRATIVE. The generator, efficiency, resolution and luminosity are invented
(profiles/experiments/synthetic-collider/benchmarks/path-b.json) and describe no real experiment. Only that
profile is loaded; no AMS or theory resource is read.

Chain: seeded synthetic events (profile generator) -> reconstructed cos theta histogram of selected events ->
full-rank unfolding with an analytic response that includes the efficiency (core.stats linear_matrix) ->
d sigma / d cos theta = unfolded truth counts / (integrated luminosity x bin width) in the fiducial region
|cos theta| < 0.9 -> covariance (statistical, plus a 2% fully correlated luminosity term) -> fiducial cross
section -> comparison with independent expected values (analytic bin integrals of the generator shape) ->
Asimov closure and seeded toy closure (counts and luminosity fluctuated) -> contract artifacts, figures, report.

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
from core.stats.unfolding_diagnostics import linear_matrix  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
CFG = json.loads((PROFILE_DIR / "benchmarks" / "path-b.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
CRITERIA = {"asimov_max_rel_dev": 1e-9, "toy_mean_pull_abs": 0.2, "toy_pull_width": (0.85, 1.15),
            "fiducial_toy_mean_pull_abs": 0.2, "fiducial_toy_pull_width": (0.85, 1.15)}

TE = np.array(CFG["truth_edges"])
RE = np.array(CFG["reco_edges"])
WIDTH = np.diff(TE)
REP = slice(*CFG["reported_truth_bins"])
LUMI = CFG["integrated_luminosity_pb"]
LUMI_REL = CFG["luminosity_rel_uncertainty"]


def expected_dsigma(sigma, a, b):
    """Independent expected values: analytic integral of f(c) = 1 + a c^2 + b c over each truth bin."""
    prim = lambda c: c + a * c ** 3 / 3 + b * c ** 2 / 2  # noqa: E731
    norm = prim(1.0) - prim(-1.0)
    return sigma * (prim(TE[1:]) - prim(TE[:-1])) / norm / WIDTH  # pb per unit cos theta, bin-averaged


def reco_histogram(ev):
    sel = ev["selected"] & (ev["reco_cos"] >= RE[0]) & (ev["reco_cos"] < RE[-1])
    return np.histogram(ev["reco_cos"][sel], bins=RE)[0].astype(float)


def analyse(counts, m, lumi_used):
    a = np.array(linear_matrix("tsvd", len(TE) - 1, m.tolist(), np.maximum(counts, 1.0).tolist()))
    u = a @ counts
    cov_u = a @ np.diag(counts) @ a.T
    scale = 1.0 / (lumi_used * WIDTH)
    x = u * scale
    stat = cov_u * np.outer(scale, scale)
    lumi = np.outer(x, x) * LUMI_REL ** 2
    fid = float(np.sum(x[REP] * WIDTH[REP]))
    w = WIDTH[REP]
    fid_var = {"stat": float(w @ stat[REP, REP] @ w), "lumi": float(w @ lumi[REP, REP] @ w)}
    return {"dsigma": x, "stat": stat, "lumi": lumi, "total": stat + lumi, "unfolded": u, "fiducial_pb": fid,
            "fiducial_var": fid_var}


def chi2(x, ref, cov):
    d = (x - ref)[REP]
    c = cov[REP, REP]
    val = float(d @ np.linalg.solve(c, d))
    ndf = len(d)
    return val, ndf, _chi2_sf(val, ndf)


def _chi2_sf(x, k):
    from core.stats.statistical_toys import chi2_sf
    return chi2_sf(x, k)


def toy_closure(m, mu_reco, expected, fid_expected, toys, seed):
    rng = np.random.default_rng(seed)
    pulls, fid_pulls = [], []
    for _ in range(toys):
        counts = rng.poisson(mu_reco).astype(float)
        lumi_hat = LUMI * (1.0 + LUMI_REL * rng.normal())  # the luminosity measurement fluctuates around the true value
        r = analyse(counts, m, lumi_hat)
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
                provenance={"producer_skill": "hep-analysis", "created": created}, status=["synthetic"],
                extension={"observable": obs, "species_or_process": "e+e- -> mu+mu- (synthetic)", "period": "not-applicable",
                           "selections": [{"name": "synthetic event selection", "definition": "efficiency e0 - e1 cos^4 theta (invented)",
                                           "conditional_denominator": "generated events in the truth bin"}],
                           "backgrounds": [], "corrections": [
                               {"effect_id": "efficiency_and_migration", "category": "response", "applied_in": "response_matrix"},
                               {"effect_id": "luminosity", "category": "normalization", "applied_in": "estimator"}],
                           "systematics": [{"name": "luminosity", "source": "synthetic 2% assumption", "effect": "normalization",
                                            "applied_via": "covariance (fully correlated across bins)"}],
                           "blinding": {"blinded": False},
                           "experiment_fields": {"synthcol:note": "ILLUSTRATIVE and SYNTHETIC; every number is invented"}})
    response_doc = dict(base, artifact_id="synthetic-path-b-response", artifact_type="response",
                        objective="SYNTHETIC cos theta response including the efficiency", status=["synthetic"],
                        provenance={"producer_skill": "detector-response", "created": created},
                        extension={"truth_axis": {"name": "cos_theta", "unit": "1", "edges": TE.tolist()},
                                   "reco_axis": {"name": "cos_theta", "unit": "1", "edges": RE.tolist()},
                                   "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
                                   "inefficiency": "inside_matrix", "acceptance": "inside_matrix", "includes": ["migration", "efficiency"],
                                   "applied_separately": ["luminosity"],
                                   "underflow_overflow": "reco outside [-1, 1] is lost; outer truth bins are buffers",
                                   "conditions": "single synthetic run", "provenance": "analytic integration of the synthetic detector model",
                                   "matrix_ref": "results.json#response", "form": "matrix"})
    stat = dict(base, artifact_id="synthetic-path-b-result", artifact_type="statistical-result",
                objective="SYNTHETIC corrected angular distribution and fiducial cross section with covariance",
                provenance={"producer_skill": "hep-statistics", "created": created}, status=["synthetic"],
                inputs=[{"ref": "artifacts/measurement_spec.json", "artifact_type": "measurement-spec", "status": ["synthetic"]}],
                extension={"paradigm": "frequentist",
                           "likelihood": {"form": "Poisson counts per reco bin; unfolding by full-rank weighted least squares (no regularization)"},
                           "parameters_of_interest": ["d sigma / d cos theta per fiducial bin", "fiducial cross section"],
                           "nuisances": ["integrated luminosity"],
                           "test_statistic": "not-applicable (point estimates with linear covariance)", "construction": "other",
                           "coverage": {"method": "seeded toys of counts and luminosity", "result_ref": "results.json#toy_closure"},
                           "fit_status": "converged", "results": {"ref": "results.json#dsigma"}})
    data = dict(base, artifact_id="synthetic-path-b-dsigma", artifact_type="dataset-record",
                objective="SYNTHETIC corrected d sigma / d cos theta (illustrative)", status=["synthetic"],
                provenance={"producer_skill": "hep-analysis", "created": created},
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
    ax.errorbar(c[REP], res["dsigma"][REP], yerr=np.sqrt(np.diag(res["total"]))[REP], xerr=WIDTH[REP] / 2, fmt="o", ms=4,
                label="SYNTHETIC corrected data")
    ax.stairs(expected[REP], TE[REP.start:REP.stop + 1], baseline=None, label="expected (generator shape, analytic)")
    ax.set_xlabel("cos theta"); ax.set_ylabel("d sigma / d cos theta [pb]"); ax.set_ylim(bottom=0); ax.set_title("SYNTHETIC Path B (illustrative)")
    ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(out / "dsigma_dcos.png", dpi=110); plt.close(fig)


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

    asimov = analyse(mu_reco.copy(), m, LUMI)
    asimov_dev = float(np.max(np.abs(asimov["dsigma"][REP] / expected[REP] - 1)))
    asimov_fid_dev = abs(asimov["fiducial_pb"] / fid_expected - 1)

    ev = generate_events.generate(CFG, args.seed)
    counts = reco_histogram(ev)
    res = analyse(counts, m, LUMI)
    c2 = chi2(res["dsigma"], expected, res["total"])
    toys = toy_closure(m, mu_reco, expected, fid_expected, args.toys, args.seed + 1)

    rv = validate_response({"metadata": {"truth_axis": {"variable": "cos_theta", "unit": "1", "edges": TE.tolist()},
                                         "reco_axis": {"variable": "cos_theta", "unit": "1", "edges": RE.tolist()},
                                         "orientation": "rows_reco_cols_truth", "normalization": "includes_efficiency",
                                         "inefficiency": "inside_matrix", "acceptance": "inside_matrix",
                                         "underflow_overflow": "explicit_bins", "efficiency_applied_separately": False,
                                         "acceptance_applied_separately": False},
                            "matrix": m.tolist(), "underflow": resp["underflow"].tolist(), "overflow": resp["overflow"].tolist()})
    labels = [f"b{j}" for j in range(REP.start, REP.stop)]
    cv = validate_covariance({"labels": labels, "kind": "absolute", "units": "pb^2", "matrix": res["total"][REP, REP].tolist(),
                              "blocks": {"stat": res["stat"][REP, REP].tolist(), "lumi": res["lumi"][REP, REP].tolist()}})
    docs, contract = artifacts(res, resp, args.created)
    for name, doc in docs.items():
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")

    passes = {
        "asimov_closure": max(asimov_dev, asimov_fid_dev) < CRITERIA["asimov_max_rel_dev"],
        "toy_mean_pull": all(abs(v) < CRITERIA["toy_mean_pull_abs"] for v in toys["mean_per_bin"]),
        "toy_pull_width": all(CRITERIA["toy_pull_width"][0] < v < CRITERIA["toy_pull_width"][1] for v in toys["width_per_bin"]),
        "fiducial_toy_pull": abs(toys["fiducial_mean_pull"]) < CRITERIA["fiducial_toy_mean_pull_abs"]
                             and CRITERIA["fiducial_toy_pull_width"][0] < toys["fiducial_pull_width"] < CRITERIA["fiducial_toy_pull_width"][1],
        "response_validation": rv["status"] != "fail",
        "covariance_validation": cv["status"] != "fail",
        "contracts": all(c["ok"] for c in contract.values()),
    }
    results = {
        "label": "SYNTHETIC and ILLUSTRATIVE: invented inputs; describes no experiment",
        "profiles_loaded": [PROFILE["id"]],
        "seed": args.seed, "toys": args.toys, "criteria": CRITERIA, "pass": passes,
        "config": CFG, "truth_edges": TE.tolist(), "reported_truth_bins": [REP.start, REP.stop],
        "n_generated": ev["meta"]["n_generated"], "n_selected": int(ev["selected"].sum()), "reco_counts": counts.tolist(),
        "response": {"matrix": m.tolist(), "efficiency": resp["efficiency"].tolist(),
                     "underflow": resp["underflow"].tolist(), "overflow": resp["overflow"].tolist()},
        "dsigma": {"values": res["dsigma"].tolist(), "expected": expected.tolist(),
                   "covariance": {"stat": res["stat"].tolist(), "lumi": res["lumi"].tolist(), "total": res["total"].tolist()}},
        "fiducial_cross_section_pb": {"value": res["fiducial_pb"], "stat": math.sqrt(res["fiducial_var"]["stat"]),
                                      "lumi": math.sqrt(res["fiducial_var"]["lumi"]), "expected": fid_expected},
        "chi2_vs_expected": {"chi2": c2[0], "ndf": c2[1], "p_value": c2[2],
                             "note": "consistency of one synthetic sample with its own generator; not a physics test"},
        "asimov_closure": {"max_rel_dev_dsigma": asimov_dev, "rel_dev_fiducial": asimov_fid_dev},
        "toy_closure": toys, "response_validation": rv["status"], "covariance_validation": cv["status"],
        "contract_validation": contract,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    figures(res, expected, out)
    write_report(out, results)
    digest = hashlib.sha256((out / "results.json").read_bytes()).hexdigest()
    print(json.dumps({"pass": passes, "results_sha256": digest}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    fmt = lambda v: ", ".join(f"{x:.4g}" for x in v)  # noqa: E731
    rep = slice(*r["reported_truth_bins"])
    f = r["fiducial_cross_section_pb"]
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
        f"| Response and covariance validators (core.stats) | no failure | {'pass' if r['pass']['response_validation'] and r['pass']['covariance_validation'] else 'FAIL'} |",
        f"| Contract artifacts (profile vocabulary) | all valid | {yes('contracts')} |",
        "",
        "The covariance validator warns that the luminosity block has rank 1. That is expected: one luminosity scales every bin together.",
        "",
        "## Result on the synthetic sample",
        "",
        f"{r['n_generated']} events generated, {r['n_selected']} selected. Fiducial cross section (|cos theta| < 0.9): "
        f"{f['value']:.2f} ± {f['stat']:.2f} (stat) ± {f['lumi']:.2f} (lumi) pb; expected from the generator inputs {f['expected']:.2f} pb.",
        "",
        f"d sigma / d cos theta per bin (pb): {fmt(r['dsigma']['values'][rep.start:rep.stop])}",
        f"Expected (analytic bin integrals of the generator shape): {fmt(r['dsigma']['expected'][rep.start:rep.stop])}",
        f"chi2 against expected with the full covariance: {r['chi2_vs_expected']['chi2']:.2f} / {r['chi2_vs_expected']['ndf']} "
        f"(p = {r['chi2_vs_expected']['p_value']:.2f}). This only checks the chain on its own synthetic input.",
        "",
        "## What the chain does",
        "",
        "Synthetic events are generated with the profile's generator, kept with the invented efficiency and smeared in cos theta. "
        "Selected events are histogrammed in reconstructed cos theta. A full-rank unfolding with an analytic response that includes "
        "the efficiency (normalized per generated truth event, so column sums are the bin efficiencies) returns generated truth counts per bin. Dividing by the integrated "
        "luminosity and the bin width gives the bin-averaged d sigma / d cos theta. The outer truth bins (|cos theta| > 0.9) "
        "absorb migration and are not reported. The covariance has a statistical block and a fully correlated 2% luminosity block.",
        "",
        f"Toys: {r['toys']} pseudo-experiments (seed {r['seed'] + 1}) fluctuate the reconstructed counts (Poisson) and the luminosity estimate.",
        "",
        "| Bin | mean pull | pull width |", "|---|---|---|",
    ]
    for j, (mu, w) in enumerate(zip(r["toy_closure"]["mean_per_bin"], r["toy_closure"]["width_per_bin"])):
        lo, hi = r["truth_edges"][rep.start + j], r["truth_edges"][rep.start + j + 1]
        lines.append(f"| [{lo:g}, {hi:g}) | {mu} | {w} |")
    lines += ["", "## Limitations (by construction)", "",
              "- The response uses the generated shape inside each bin; model dependence of the unfolding is not studied.",
              "- No background, radiative corrections, charge confusion or beam-energy spread are modeled.",
              "- Efficiency and resolution are assumed exactly known; only the luminosity carries a systematic.",
              "- Passing these checks shows internal consistency on synthetic data, nothing about a real detector.",
              "", "Figure: `dsigma_dcos.png`. Artifacts: `artifacts/*.json` (status `synthetic`).", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())

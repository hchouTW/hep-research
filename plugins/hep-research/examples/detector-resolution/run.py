#!/usr/bin/env python3
"""Journey J2 (detector physicist): SYNTHETIC angular resolution and efficiency study with the illustrative
experiment:synthetic-collider profile, handed to hep-statistics for a constant-resolution fit.

SYNTHETIC and ILLUSTRATIVE. The detector model (efficiency e0 - e1 c^4, Gaussian cos theta smearing) and every
number come from profiles/experiments/synthetic-collider/benchmarks/path-b.json and describe no real experiment.
Only that profile is loaded; no AMS or theory resource is read.

Chain (detector-response -> hep-statistics):
1. Seeded synthetic events from the profile generator and detector.
2. Per truth bin of |cos theta| in [0, 0.9] (away from the acceptance edge, so smearing is not truncated):
   resolution = maximum-likelihood Gaussian width of (reco - truth) for selected events, with its large-sample
   uncertainty sigma / sqrt(2 n); efficiency = selected / generated with a binomial uncertainty.
3. Independent expected values: the configured width, and the efficiency model averaged over each bin with the
   generator shape (Simpson integration), computed without the event sample.
4. hep-statistics: weighted constant-width fit (chi2, p-value); efficiency chi2 against the model.
5. Seeded replicate samples: pulls of the fitted width (mean and spread), to check the stated uncertainty.
6. Contract artifacts (two dataset records at detector level, one statistical result), figure, report.

Usage (from the plugin root): python3 examples/detector-resolution/run.py [--replicates 200] [--seed 20261005] [--out DIR]
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
from core.stats.statistical_toys import chi2_sf  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
CFG = json.loads((PROFILE_DIR / "benchmarks" / "path-b.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
EDGES = np.array([0.0, 0.18, 0.36, 0.54, 0.72, 0.9])  # |cos theta| truth bins
CRITERIA = {"width_fit_pull_abs": 3.0, "width_chi2_p_min": 0.001, "efficiency_chi2_p_min": 0.001,
            "replicate_mean_pull_abs": 0.25, "replicate_pull_width": (0.8, 1.2)}
LABEL = "SYNTHETIC and ILLUSTRATIVE: invented detector model; describes no experiment"


def measure(ev) -> dict:
    t, r, sel = np.abs(ev["truth_cos"]), ev["reco_cos"] - ev["truth_cos"], ev["selected"]
    width, width_err, eff, eff_err, n_sel, n_gen = [], [], [], [], [], []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        inb = (t >= lo) & (t < hi)
        res = r[inb & sel]
        s = float(np.sqrt(np.mean((res - res.mean()) ** 2)))  # Gaussian MLE width
        width.append(s)
        width_err.append(s / math.sqrt(2 * res.size))
        n, k = int(inb.sum()), int((inb & sel).sum())
        e = k / n
        eff.append(e)
        eff_err.append(math.sqrt(e * (1 - e) / n))
        n_sel.append(k)
        n_gen.append(n)
    return {"width": np.array(width), "width_err": np.array(width_err), "eff": np.array(eff), "eff_err": np.array(eff_err),
            "n_selected": n_sel, "n_generated": n_gen}


def expected_efficiency() -> np.ndarray:
    """Bin average of the efficiency model weighted by the generator shape (|c| bins; the shape is even when b = 0)."""
    g = CFG["generator"]
    out = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        c = np.linspace(lo, hi, 2001)
        w = 1 + g["shape_a"] * c ** 2 + g["shape_b"] * c + (1 + g["shape_a"] * c ** 2 - g["shape_b"] * c)  # +c and -c
        h = (hi - lo) / 2000
        simpson = lambda y: h / 3 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum())
        out.append(simpson(w * detector.efficiency(c, CFG)) / simpson(w))
    return np.array(out)


def fit_constant(x, err):
    w = 1 / err ** 2
    mean = float(np.sum(w * x) / np.sum(w))
    chi2 = float(np.sum(w * (x - mean) ** 2))
    ndf = len(x) - 1
    return {"value": mean, "error": float(1 / math.sqrt(np.sum(w))), "chi2": chi2, "ndf": ndf, "p_value": float(chi2_sf(chi2, ndf))}


def replicates(n, seed):
    true = CFG["resolution"]["sigma_cos"]
    pulls = []
    for k in range(n):
        f = fit_constant(*(lambda m: (m["width"], m["width_err"]))(measure(generate_events.generate(CFG, seed + k))))
        pulls.append((f["value"] - true) / f["error"])
    p = np.array(pulls)
    return {"n": n, "seed_first": seed, "mean_pull": float(p.mean()), "pull_width": float(p.std(ddof=1))}


def artifacts(m, fit, exp_eff, created):
    vocab = Vocabulary.with_profiles([PROFILE])
    base = {"contract_version": CONTRACTS_VERSION,
            "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {PROFILE["id"]: PROFILE["version"]}},
            "inputs": [], "outputs": [], "unresolved_inputs": [], "status": ["synthetic"]}
    var = [{"name": "abs_cos_theta_truth", "unit": "1", "edges": EDGES.tolist()}]
    ps = {"definition": "SYNTHETIC: selected events, |cos theta| < 0.9 at truth level, fixed sqrt(s) = 10 GeV", "fiducial": True}

    def record(aid, quantity, values, errors, unit, conv, objective, key):
        return dict(base, artifact_id=aid, artifact_type="dataset-record", objective=objective,
                    provenance={"producer_skill": "detector-response", "created": created},
                    extension={"dataset_id": f"synthcol:{aid}", "source_evidence_ids": [],
                               "observable": {"quantity": quantity, "process": "e+e- -> mu+mu- (synthetic generator)", "variables": var,
                                              "phase_space": ps, "level": "detector", "frame": "center-of-mass",
                                              "normalization": {"kind": "shape-only", "convention": conv},
                                              "bin_semantics": "bin-averaged", "unit": unit,
                                              "conventions": {"angle_definition": "theta between the incoming e- beam and the outgoing mu-"}},
                               "data": {"edges": EDGES.tolist(), "values": [float(v) for v in values], "unit": unit,
                                        "uncertainties": [{"name": "statistical", "kind": "statistical", "correlation": "uncorrelated",
                                                           "values": [float(v) for v in errors]}]},
                               "covariance": {"status": "present", "ref": f"results.json#per_bin/{key}",
                                              "note": "diagonal: bins hold disjoint events, so the per-bin errors are the whole covariance"},
                               "period": "not-applicable", "status": "synthetic", "experiment_profile": PROFILE["id"]})

    width = record("synthetic-j2-resolution", "resolution", m["width"], m["width_err"], "1",
                   "Gaussian width of reco - truth cos theta for selected events; not a rate",
                   "SYNTHETIC J2: cos theta resolution per |cos theta| bin (illustrative detector)", "width_err")
    eff = record("synthetic-j2-efficiency", "efficiency", m["eff"], m["eff_err"], "1",
                 "selected / generated in the truth bin; acceptance and selection together",
                 "SYNTHETIC J2: selection efficiency per |cos theta| bin (illustrative detector)", "eff_err")
    stat = dict(base, artifact_id="synthetic-j2-width-fit", artifact_type="statistical-result",
                objective="SYNTHETIC J2: constant-width fit of the per-bin resolution",
                provenance={"producer_skill": "hep-statistics", "created": created},
                inputs=[{"ref": "artifacts/resolution.json", "artifact_type": "dataset-record", "status": ["synthetic"]}],
                extension={"paradigm": "frequentist",
                           "likelihood": {"form": "Gaussian per bin with the large-sample width uncertainty (weighted least squares)"},
                           "parameters_of_interest": ["constant cos theta resolution"], "nuisances": [],
                           "test_statistic": "chi2 of the constant model", "construction": "other",
                           "coverage": {"method": "seeded replicate samples; pull mean and width", "result_ref": "results.json#replicates"},
                           "fit_status": "converged", "results": {"ref": "results.json#width_fit"}})
    docs = {"resolution": width, "efficiency": eff, "width_fit": stat}
    return docs, {k: {"ok": (r := validate_artifact(v, vocab)).ok, "errors": [f.message for f in r.errors]} for k, v in docs.items()}


def figure(m, fit, exp_eff, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = 0.5 * (EDGES[:-1] + EDGES[1:])
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    ax[0].errorbar(x, m["width"], m["width_err"], fmt="o", label="measured (synthetic)")
    ax[0].axhline(fit["value"], label="constant fit")
    ax[0].axhline(CFG["resolution"]["sigma_cos"], ls="--", color="k", label="configured")
    ax[0].set(xlabel="|cos theta| (truth)", ylabel="cos theta resolution")
    ax[1].errorbar(x, m["eff"], m["eff_err"], fmt="o", label="measured (synthetic)")
    ax[1].plot(x, exp_eff, "k_", ms=20, label="model, bin average")
    ax[1].set(xlabel="|cos theta| (truth)", ylabel="efficiency")
    for a in ax:
        a.legend(fontsize=7)
    fig.suptitle("SYNTHETIC J2 detector study (illustrative profile)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "resolution_efficiency.png", dpi=110, metadata={"Software": None})
    plt.close(fig)


def write_report(out: Path, r: dict) -> None:
    f, e = r["width_fit"], r["efficiency_check"]
    lines = [
        "# J2 detector study (SYNTHETIC, illustrative profile)", "",
        f"{r['label']}. Profile loaded: `{r['profiles_loaded'][0]}` only. Seed {r['seed']}, {r['replicates']['n']} replicate samples.", "",
        "| Quantity | Result | Expected (independent) |", "|---|---|---|",
        f"| Constant cos theta resolution | {f['value']:.5f} ± {f['error']:.5f} (chi2 {f['chi2']:.2f}/{f['ndf']}, p = {f['p_value']:.3f}) | {r['configured_width']} (configured) |",
        f"| Efficiency vs bin-averaged model | chi2 {e['chi2']:.2f}/{e['ndf']}, p = {e['p_value']:.3f} | model e0 - e1 c^4 |",
        f"| Replicate pulls of the fitted width | mean {r['replicates']['mean_pull']:.3f}, width {r['replicates']['pull_width']:.3f} | 0 and 1 |", "",
        "Criteria: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in r["pass"].items()) + ".", "",
        "Limits: the detector is invented and Gaussian; the large-sample width uncertainty is checked by replicates only for "
        "this sample size; bins stop at |cos theta| = 0.9 so the acceptance edge does not truncate the residuals. "
        "This shows the J2 chain and its contracts, not any detector's performance.",
        "", f"Reproduce: `python3 examples/detector-resolution/run.py --replicates {r['replicates']['n']} --seed {r['seed']}`",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--replicates", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261005)
    ap.add_argument("--created", default="2026-10-02")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    out = a.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    m = measure(generate_events.generate(CFG, a.seed))
    fit = fit_constant(m["width"], m["width_err"])
    exp_eff = expected_efficiency()
    ec2 = float(np.sum(((m["eff"] - exp_eff) / m["eff_err"]) ** 2))
    eff_check = {"chi2": ec2, "ndf": len(exp_eff), "p_value": float(chi2_sf(ec2, len(exp_eff)))}
    rep = replicates(a.replicates, a.seed + 1)
    true = CFG["resolution"]["sigma_cos"]
    docs, contract = artifacts(m, fit, exp_eff, a.created)
    for name, doc in docs.items():
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
    passes = {
        "width_closure": abs(fit["value"] - true) / fit["error"] < CRITERIA["width_fit_pull_abs"],
        "width_constant_model": fit["p_value"] > CRITERIA["width_chi2_p_min"],
        "efficiency_vs_model": eff_check["p_value"] > CRITERIA["efficiency_chi2_p_min"],
        "replicate_mean_pull": abs(rep["mean_pull"]) < CRITERIA["replicate_mean_pull_abs"],
        "replicate_pull_width": CRITERIA["replicate_pull_width"][0] < rep["pull_width"] < CRITERIA["replicate_pull_width"][1],
        "contracts": all(c["ok"] for c in contract.values()),
    }
    results = {"label": LABEL, "profiles_loaded": [PROFILE["id"]], "seed": a.seed, "criteria": CRITERIA, "pass": passes,
               "abs_cos_edges": EDGES.tolist(), "configured_width": true,
               "per_bin": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in m.items()},
               "expected_efficiency": exp_eff.tolist(), "width_fit": fit, "efficiency_check": eff_check,
               "replicates": rep, "contract_validation": contract}
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    figure(m, fit, exp_eff, out)
    write_report(out, results)
    print(json.dumps({"pass": passes, "results_sha256": hashlib.sha256((out / "results.json").read_bytes()).hexdigest()}, indent=1))
    return 0 if all(passes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

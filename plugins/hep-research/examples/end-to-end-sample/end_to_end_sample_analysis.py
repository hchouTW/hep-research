#!/usr/bin/env python3
"""End-to-end synthetic analysis: ntuple -> cutflow -> histograms -> pyhf fit -> yield table.

Purpose: one small, runnable chain that exercises the conventions in SKILL.md together
(signed generator weights normalized to the full production, sumw/sumw2 at every cut,
orthogonal signal and control regions, MC-stat nuisances from sumw2, a labelled
pseudo-data set, and a yield table), so it doubles as a smoke test and a template.

What it does:
1. Generates a synthetic background ("ttbar-like", ~10% negative NLO-style weights) and
   signal sample: njet (Poisson) and a mass observable in GeV, fixed seed.
2. Normalizes each sample by lumi * xsec / sum(generator weights of the full sample).
3. Builds a weighted cutflow (sumw, sumw2 per cut) and mass histograms in two
   orthogonal regions: CR (njet == 3) and SR (njet >= 4).
4. Draws Poisson pseudo-data from background + injected signal (mu_injected), labelled
   as pseudo-data, never as observed data.
5. Builds a pyhf model (signal normfactor mu, background normfactor mu_bkg shared across
   regions, per-bin MC-stat staterror from sumw2, 2.5% lumi normsys), fits it, and
   computes the observed and expected 95% CLs upper limit on mu.
6. Writes cutflow.csv, yields.csv, workspace.json, summary.json into --outdir and
   prints the yield table via scripts/make_yield_table.py.

Usage:
    python3 assets/end_to_end_sample_analysis.py --outdir demo_out [--seed 1] [--mu-injected 1.0]
Requires: numpy, pyhf (and scipy, which pyhf uses); iminuit optional, for fit uncertainties. All numbers are synthetic and
illustrative; nothing here is an experimental input.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyhf

LUMI_PB = 100e3  # 100 fb^-1 in pb^-1
SAMPLES = {
    # name: (cross section [pb], generated events, negative-weight fraction, mass model)
    "ttbar": (0.06, 200_000, 0.10, "falling"),
    "signal": (0.002, 50_000, 0.0, "peak"),
}
MASS_EDGES = np.linspace(100.0, 300.0, 11)  # GeV, 10 bins
SKILL_DIR = Path(__file__).resolve().parents[1]


def generate(name: str, rng: np.random.Generator) -> dict[str, np.ndarray]:
    xsec, n_gen, neg_frac, shape = SAMPLES[name]
    gen_weight = np.where(rng.random(n_gen) < neg_frac, -1.0, 1.0)
    njet = rng.poisson(3.0 if name == "ttbar" else 4.5, n_gen)
    if shape == "falling":
        mass = 100.0 + rng.exponential(60.0, n_gen)
    else:
        mass = rng.normal(200.0, 12.0, n_gen)
    # Normalize to the FULL generated sample's signed weight sum, before any cut.
    norm = LUMI_PB * xsec / gen_weight.sum()
    return {"njet": njet, "mass": mass, "weight": gen_weight * norm}


def weighted_hist(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sumw, _ = np.histogram(values, bins=MASS_EDGES, weights=weights)
    sumw2, _ = np.histogram(values, bins=MASS_EDGES, weights=weights**2)
    return sumw, sumw2


def cutflow_rows(name: str, ev: dict[str, np.ndarray]) -> list[dict[str, object]]:
    in_range = (ev["mass"] >= MASS_EDGES[0]) & (ev["mass"] < MASS_EDGES[-1])
    cuts = [
        ("all", np.ones_like(in_range)),
        ("mass in [100, 300) GeV", in_range),
        ("njet >= 3", in_range & (ev["njet"] >= 3)),
        ("CR: njet == 3", in_range & (ev["njet"] == 3)),
        ("SR: njet >= 4", in_range & (ev["njet"] >= 4)),
    ]
    rows = []
    for cut, mask in cuts:
        w = ev["weight"][mask]
        rows.append({"sample": name, "cut": cut, "entries": int(mask.sum()),
                     "sumw": float(w.sum()), "sumw2": float((w**2).sum())})
    return rows


def region_masks(ev: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    masks = {"CR": ev["njet"] == 3, "SR": ev["njet"] >= 4}
    assert not np.any(masks["CR"] & masks["SR"]), "regions must be orthogonal"
    return masks


def build_workspace(hists: dict, data: dict) -> dict:
    channels = []
    for region in ("SR", "CR"):
        sig_w, _ = hists[("signal", region)]
        bkg_w, bkg_w2 = hists[("ttbar", region)]
        channels.append({
            "name": region,
            "samples": [
                {"name": "signal", "data": sig_w.tolist(), "modifiers": [
                    {"name": "mu", "type": "normfactor", "data": None},
                    {"name": "lumi", "type": "normsys", "data": {"hi": 1.025, "lo": 0.975}},
                ]},
                {"name": "ttbar", "data": bkg_w.tolist(), "modifiers": [
                    {"name": "mu_bkg", "type": "normfactor", "data": None},
                    {"name": f"staterror_{region}", "type": "staterror", "data": np.sqrt(bkg_w2).tolist()},
                ]},
            ],
        })
    return {
        "channels": channels,
        "observations": [{"name": r, "data": data[r].tolist()} for r in ("SR", "CR")],
        "measurements": [{"name": "demo", "config": {"poi": "mu", "parameters": [
            {"name": "mu", "bounds": [[0.0, 10.0]]},
            {"name": "mu_bkg", "bounds": [[0.1, 5.0]]},
        ]}}],
        "version": "1.0.0",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mu-injected", type=float, default=1.0)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    events = {name: generate(name, rng) for name in SAMPLES}
    cutflow, hists = [], {}
    for name, ev in events.items():
        cutflow += cutflow_rows(name, ev)
        for region, mask in region_masks(ev).items():
            hists[(name, region)] = weighted_hist(ev["mass"][mask], ev["weight"][mask])

    # Pseudo-data (NOT observed data): Poisson draw from background + mu_injected * signal.
    data = {}
    for region in ("SR", "CR"):
        expected = hists[("ttbar", region)][0] + args.mu_injected * hists[("signal", region)][0]
        if np.any(expected < 0):
            raise ValueError(f"negative expected yield in {region}; check signed weights/binning")
        data[region] = rng.poisson(expected)

    spec = build_workspace(hists, data)
    workspace = pyhf.Workspace(spec)
    model = workspace.model()
    obs = workspace.data(model)
    try:  # Minuit gives parameter uncertainties; scipy alone returns best-fit values only.
        pyhf.set_backend("numpy", pyhf.optimize.minuit_optimizer(tolerance=1e-3))
        has_errors = True
    except Exception:  # iminuit not installed
        pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer())
        has_errors = False
    result, twice_nll = pyhf.infer.mle.fit(obs, model, return_uncertainties=has_errors,
                                           return_fitted_val=True)
    fitted = {}
    for name in ("mu", "mu_bkg", "lumi"):
        entry = result[model.config.par_slice(name)][0]
        value, error = (entry[0], entry[1]) if has_errors else (entry, float("nan"))
        fitted[name] = {"value": float(value), "error": float(error) if has_errors else None}
    obs_limit, exp_limits = pyhf.infer.intervals.upper_limits.upper_limit(
        obs, model, scan=np.linspace(0.0, 5.0, 51))

    with (args.outdir / "cutflow.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "cut", "entries", "sumw", "sumw2"])
        writer.writeheader()
        writer.writerows(cutflow)
    with (args.outdir / "yields.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["region", "sample", "yield", "uncertainty"])
        for (name, region), (sumw, sumw2) in sorted(hists.items()):
            writer.writerow([region, name, sumw.sum(), np.sqrt(sumw2.sum())])
        for region in ("SR", "CR"):
            writer.writerow([region, "pseudo-data (not observed)", data[region].sum(), ""])
    (args.outdir / "workspace.json").write_text(json.dumps(spec, indent=1))
    summary = {
        "mu_injected": args.mu_injected,
        "fitted": fitted,
        "twice_nll": float(twice_nll),
        "cls_upper_limit_mu": {"observed": float(obs_limit),
                               "expected_-2s..+2s": [float(x) for x in exp_limits]},
        "data_label": "Poisson pseudo-data from bkg + mu_injected * signal (synthetic)",
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=1))

    subprocess.run([sys.executable, str(SKILL_DIR / "scripts/make_yield_table.py"),
                    "--input", str(args.outdir / "yields.csv"), "--precision", "1"], check=True)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

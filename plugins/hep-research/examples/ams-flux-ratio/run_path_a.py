#!/usr/bin/env python3
"""Path A (journey J1): synthetic charged-particle flux and correlated ratio with the AMS-02 profile.

SYNTHETIC. Every number generated here (spectra, acceptance, livetime, cutoff distribution,
efficiencies, resolution, control-sample sizes) is invented for this example and describes no
experiment. Only conventions and one documented practice come from the experiment:ams-02 profile:
rigidity R = pc/(Ze) in GV, the flux definition at the top of the instrument, exposure as the
normalization kind, and the geomagnetic selection "R > 1.2 x maximum cutoff", documented for the
proton flux analysis (ams02:C31) and used here for helium as a [Proposal].

Chain (per species, per period): truth flux -> selected events (trigger and selection efficiency,
acceptance, livetime, cutoff fraction) -> rigidity migration (core resolution plus a non-Gaussian
tail) -> Poisson counts -> unfolding (core.stats.unfolding_diagnostics.linear_matrix, full-rank
truncated SVD, no regularization) -> flux with exposure normalization -> covariance (statistical,
trigger efficiency fully correlated across bins and shared by the species, selection efficiency per
bin and species) -> He/p ratio per period (the trigger term cancels) -> exposure-weighted average
over periods -> Asimov closure and seeded toy closure -> contract artifacts, figures and a report.

Usage (from the plugin root): python3 examples/ams-flux-ratio/run_path_a.py [--toys 400] [--seed 20261002] [--out DIR]
Default output: examples/ams-flux-ratio/output/. Exit 0 when every pre-declared closure criterion passes,
1 otherwise. Requires numpy and matplotlib (the D5 environment).
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
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.stats.statistical_toys import ratio_measured  # noqa: E402
from core.stats.unfolding_diagnostics import linear_matrix  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

PROFILE_DIR = PLUGIN / "profiles" / "experiments" / "ams-02"
PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

# ----------------------------------------------------------------------------- synthetic world
EDGES = np.array([1.5, 2.0, 3.0, 4.5, 7.0, 10.0, 15.0, 25.0, 40.0, 60.0, 100.0, 150.0])  # GV; first and last bins are migration buffers
REPORTED = slice(1, len(EDGES) - 2)  # bins 2-3 ... 60-100 GV are reported
SPECIES = {  # power law K (R / 10 GV)^-gamma in m^-2 sr^-1 s^-1 GV^-1, synthetic
    "proton": {"abs_Z": 1, "A": 1, "K": 0.05, "gamma": 2.7, "acc_max": 0.045, "sel": (0.80, 0.05)},
    "helium": {"abs_Z": 2, "A": 4, "K": 0.01, "gamma": 2.6, "acc_max": 0.040, "sel": (0.70, 0.08)},
}
PERIODS = {  # synthetic: livetime (s), modulation depth, trigger efficiency, livetime fraction by maximum cutoff (GV)
    "synthetic-period-1": {"livetime": 1.5e6, "mod": 0.35, "trigger": 0.93,
                           "cutoff_hist": {1.0: 0.20, 1.5: 0.15, 3.0: 0.25, 6.0: 0.25, 10.0: 0.10, 14.0: 0.05}},
    "synthetic-period-2": {"livetime": 2.6e6, "mod": 0.15, "trigger": 0.90,
                           "cutoff_hist": {1.0: 0.10, 1.5: 0.10, 3.0: 0.30, 6.0: 0.30, 10.0: 0.15, 14.0: 0.05}},
}
CUTOFF_FACTOR = 1.2  # documented for the proton analysis (ams02:C31); a proposal for helium
RESOLUTION = {"core_rel": 0.02, "mdr_gv": 2000.0, "tail_fraction": 0.02, "tail_scale": 5.0}  # in curvature 1/R
N_CTRL_TRIGGER = 1000  # synthetic unbiased-trigger control sample per period
N_CTRL_SELECTION = 5000  # synthetic control sample per bin and species (shared by the periods)
CRITERIA = {"asimov_max_rel_dev": 1e-9, "toy_mean_pull_abs": 0.2, "toy_pull_width": (0.85, 1.15),
            "reference_rel_agreement": 1e-9}

NB = len(EDGES) - 1
WIDTH = np.diff(EDGES)
CENTER = np.sqrt(EDGES[:-1] * EDGES[1:])


def truth_flux(sp: dict, period: dict, r):
    return sp["K"] * (r / 10.0) ** (-sp["gamma"]) * (1.0 - period["mod"] * np.exp(-r / 5.0))


def bin_integrals(sp, period, n=801):
    """Integral of the truth flux over each bin (trapezoid on a fine log grid)."""
    out = np.empty(NB)
    for j in range(NB):
        x = np.geomspace(EDGES[j], EDGES[j + 1], n)
        y = truth_flux(sp, period, x)
        out[j] = float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))
    return out


def acceptance(sp):
    """Piecewise constant per bin by construction of the synthetic detector (m^2 sr)."""
    return sp["acc_max"] * (1.0 - np.exp(-CENTER / 3.0))


def selection_eff(sp):
    a, b = sp["sel"]
    return a - b * np.exp(-CENTER / 5.0)


def cutoff_fraction(period):
    """Livetime fraction with R_low_edge > CUTOFF_FACTOR x maximum cutoff (bin-level criterion)."""
    return np.array([sum(w for rc, w in period["cutoff_hist"].items() if CUTOFF_FACTOR * rc < EDGES[j]) for j in range(NB)])


def exposure(sp, period):
    return acceptance(sp) * period["livetime"] * cutoff_fraction(period)  # m^2 sr s


def response(sp, period, n=200):
    """P(reco bin k | truth bin j), rows reco, cols truth; curvature smearing with a core and a wide tail.
    Probability outside [EDGES[0], EDGES[-1]] (including negative curvature) is lost (overflow/underflow)."""
    from math import erf
    m = np.zeros((NB, NB))
    under = np.zeros(NB)
    over = np.zeros(NB)

    def cdf(x, mu, s):
        return 0.5 * (1.0 + erf((x - mu) / (s * math.sqrt(2.0))))
    for j in range(NB):
        r = np.geomspace(EDGES[j], EDGES[j + 1], n)
        w = truth_flux(sp, period, r) * np.gradient(r)
        w = w / w.sum()
        for rt, wt in zip(r, w):
            x0 = 1.0 / rt
            s_core = x0 * math.hypot(RESOLUTION["core_rel"], rt / RESOLUTION["mdr_gv"])
            for frac, s in ((1 - RESOLUTION["tail_fraction"], s_core), (RESOLUTION["tail_fraction"], s_core * RESOLUTION["tail_scale"])):
                for k in range(NB):  # reco bin k in R <-> curvature in [1/EDGES[k+1], 1/EDGES[k]]
                    m[k, j] += wt * frac * (cdf(1.0 / EDGES[k], x0, s) - cdf(1.0 / EDGES[k + 1], x0, s))
                over[j] += wt * frac * cdf(1.0 / EDGES[-1], x0, s)  # R above range, or wrong sign of curvature
                under[j] += wt * frac * (1.0 - cdf(1.0 / EDGES[0], x0, s))  # R below range
    return m, under, over


# ----------------------------------------------------------------------------- analysis
def unfold(m, counts):
    a = np.array(linear_matrix("tsvd", NB, m.tolist(), np.maximum(counts, 1.0).tolist()))
    u = a @ counts
    cov = a @ np.diag(counts) @ a.T
    return u, cov


def analyse(counts, eff_trig_hat, eff_sel_hat, sigma_trig, sigma_sel, expo, m):
    """Flux and covariance blocks for one species and period."""
    u, cov_u = unfold(m, counts)
    denom = eff_trig_hat * eff_sel_hat * expo * WIDTH
    flux = u / denom
    jac = np.diag(1.0 / denom)
    stat = jac @ cov_u @ jac.T
    trig = np.outer(flux, flux) * (sigma_trig / eff_trig_hat) ** 2  # fully correlated across bins
    sel = np.diag((flux * sigma_sel / eff_sel_hat) ** 2)  # independent per bin
    return {"flux": flux, "unfolded": u, "stat": stat, "trigger": trig, "selection": sel, "total": stat + trig + sel}


def ratio_block(num, den):
    """He/p ratio and covariance; the trigger efficiency is the same estimate in both, so it cancels exactly."""
    r = num["flux"] / den["flux"]
    rel = (num["stat"] + num["selection"]) / np.outer(num["flux"], num["flux"]) + \
          (den["stat"] + den["selection"]) / np.outer(den["flux"], den["flux"])
    return r, rel * np.outer(r, r)


def simulate(rng, world, asimov=False):
    """One pseudo-experiment: reco counts per species and period, and the efficiency control samples."""
    out = {"counts": {}, "trig_hat": {}, "sel_hat": {}}
    for pname, per in PERIODS.items():
        out["trig_hat"][pname] = per["trigger"] if asimov else rng.binomial(N_CTRL_TRIGGER, per["trigger"]) / N_CTRL_TRIGGER
    for sname, sp in SPECIES.items():
        eps = selection_eff(sp)
        out["sel_hat"][sname] = eps if asimov else rng.binomial(N_CTRL_SELECTION, eps) / N_CTRL_SELECTION
        for pname in PERIODS:
            mu = world[sname][pname]["expected_reco"]
            out["counts"][(sname, pname)] = mu.copy() if asimov else rng.poisson(mu).astype(float)
    return out


def run_analysis(sim, world):
    res = {}
    for pname, per in PERIODS.items():
        st = math.sqrt(per["trigger"] * (1 - per["trigger"]) / N_CTRL_TRIGGER)
        for sname, sp in SPECIES.items():
            ss = np.sqrt(selection_eff(sp) * (1 - selection_eff(sp)) / N_CTRL_SELECTION)
            w = world[sname][pname]
            res[(sname, pname)] = analyse(sim["counts"][(sname, pname)], sim["trig_hat"][pname], sim["sel_hat"][sname],
                                          st, ss, w["exposure"], w["response"])
        res[("ratio", pname)] = ratio_block(res[("helium", pname)], res[("proton", pname)])
    for sname in SPECIES:  # exposure-weighted average over periods: sum of corrected counts / sum of exposures
        num = sum(res[(sname, p)]["unfolded"] / (sim["trig_hat"][p] * sim["sel_hat"][sname]) for p in PERIODS)
        den = sum(world[sname][p]["exposure"] for p in PERIODS) * WIDTH
        res[(sname, "average")] = num / den
    return res


def build_world():
    world = {}
    for sname, sp in SPECIES.items():
        world[sname] = {}
        for pname, per in PERIODS.items():
            integ = bin_integrals(sp, per)
            expo = exposure(sp, per)
            eff = per["trigger"] * selection_eff(sp)
            selected = integ * expo * eff
            m, under, over = response(sp, per)
            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": expo, "selected_truth": selected,
                                   "response": m, "underflow": under, "overflow": over, "expected_reco": m @ selected}
        tot_expo = sum(world[sname][p]["exposure"] for p in PERIODS)
        world[sname]["average_truth"] = sum(world[sname][p]["exposure"] * world[sname][p]["truth_flux"] for p in PERIODS) / tot_expo
        livetime_total = sum(per["livetime"] for per in PERIODS.values())
        equal_split = sum(acceptance(sp) * 0.5 * livetime_total * cutoff_fraction(per) for per in PERIODS.values())
        world[sname]["equal_split_exposure"] = equal_split
    for pname in PERIODS:
        world.setdefault("ratio_truth", {})[pname] = world["helium"][pname]["truth_flux"] / world["proton"][pname]["truth_flux"]
    return world


# ----------------------------------------------------------------------------- checks
def asimov_closure(world):
    res = run_analysis(simulate(None, world, asimov=True), world)
    devs = {}
    for sname in SPECIES:
        for pname in PERIODS:
            devs[f"{sname}/{pname}"] = float(np.max(np.abs(res[(sname, pname)]["flux"][REPORTED] / world[sname][pname]["truth_flux"][REPORTED] - 1)))
        devs[f"{sname}/average"] = float(np.max(np.abs(res[(sname, "average")][REPORTED] / world[sname]["average_truth"][REPORTED] - 1)))
    for pname in PERIODS:
        devs[f"ratio/{pname}"] = float(np.max(np.abs(res[("ratio", pname)][0][REPORTED] / world["ratio_truth"][pname][REPORTED] - 1)))
    return res, devs


def toy_closure(world, toys, seed):
    rng = np.random.default_rng(seed)
    pulls = {}
    for _ in range(toys):
        res = run_analysis(simulate(rng, world), world)
        for sname in SPECIES:
            for pname in PERIODS:
                b = res[(sname, pname)]
                p = (b["flux"] - world[sname][pname]["truth_flux"]) / np.sqrt(np.diag(b["total"]))
                pulls.setdefault(f"{sname}/{pname}", []).append(p[REPORTED])
        for pname in PERIODS:
            r, c = res[("ratio", pname)]
            pulls.setdefault(f"ratio/{pname}", []).append(((r - world["ratio_truth"][pname]) / np.sqrt(np.diag(c)))[REPORTED])
    summary = {}
    for key, rows in pulls.items():
        a = np.array(rows)
        summary[key] = {"mean_per_bin": a.mean(axis=0).round(4).tolist(), "width_per_bin": a.std(axis=0, ddof=1).round(4).tolist()}
    return summary


def ratio_reference(res, pname):
    """Independent linear propagation (core.stats ratio_measured) from the joint He, p covariance in which the
    trigger term is a shared, fully correlated component. Must equal the cancellation used in ratio_block."""
    he, p = res[("helium", pname)], res[("proton", pname)]
    sl = REPORTED
    x, y = he["flux"][sl], p["flux"][sl]
    cxx, cyy = he["total"][sl, sl], p["total"][sl, sl]
    rel_trig = he["trigger"][sl, sl] / np.outer(x, x)  # same relative trigger variance for both species
    cxy = rel_trig * np.outer(x, y)
    joint = np.block([[cxx, cxy], [cxy.T, cyy]])
    ref = ratio_measured({"numerator": x.tolist(), "denominator": y.tolist(), "covariance": joint.tolist()}, toys=200, seed=1)
    mine = np.sqrt(np.diag(res[("ratio", pname)][1]))[sl]
    indep = np.block([[cxx, np.zeros_like(cxy)], [np.zeros_like(cxy), cyy]])
    naive = np.array(ratio_measured({"numerator": x.tolist(), "denominator": y.tolist(), "covariance": indep.tolist()},
                                    toys=200, seed=1)["linear_sigma"])
    return {"reference_linear_sigma": ref["linear_sigma"], "this_analysis_sigma": mine.tolist(),
            "max_rel_difference": float(np.max(np.abs(np.array(ref["linear_sigma"]) / mine - 1))),
            "sigma_if_trigger_treated_as_independent": naive.tolist(),
            "overestimate_factor_if_independent": (naive / mine).round(4).tolist()}


# ----------------------------------------------------------------------------- outputs
def artifacts(world, res, created):
    vocab = Vocabulary.with_profiles([PROFILE])
    edges = EDGES[1:-1].tolist()
    base = {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "profiles": {PROFILE["id"]: PROFILE["version"]}},
            "inputs": [], "outputs": [], "unresolved_inputs": []}
    periods = [{"start": p, "end": p} for p in PERIODS]
    obs = {"quantity": "ratio", "species": [{"name": "helium", "abs_Z": 2, "A": 4}, {"name": "proton", "abs_Z": 1, "A": 1}],
           "variables": [{"name": "rigidity", "unit": "GV", "edges": edges}],
           "phase_space": {"definition": "synthetic: downward-going particles inside the synthetic acceptance, R > 1.2 x maximum cutoff per bin lower edge", "fiducial": True},
           "level": "crflux:top-of-instrument", "frame": "detector location",
           "normalization": {"kind": "exposure", "value": "not-applicable", "convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime x cutoff fraction per period"},
           "bin_semantics": "bin-averaged", "unit": "1",
           "conventions": {"energy_variable": "rigidity", "ams02:rigidity_definition": "R = pc/(Ze) in GV; p = |Z|R/c; rigidity is not momentum"}}
    spec = dict(base, artifact_id="synthetic-path-a-measurement-spec", artifact_type="measurement-spec",
                objective="SYNTHETIC Path A: He/p flux ratio per rigidity bin in two synthetic periods",
                provenance={"producer_skill": "hep-analysis", "created": created, "evidence_ids": ["ams02:C31"]},
                status=["synthetic"],
                extension={"observable": obs, "species_or_process": "helium, proton (synthetic)", "period": periods,
                           "selections": [{"name": "geomagnetic", "definition": "bin lower edge > 1.2 x maximum cutoff", "conditional_denominator": "livetime"},
                                          {"name": "species selection", "definition": "synthetic per-species selection", "conditional_denominator": "triggered events in acceptance"}],
                           "backgrounds": [], "corrections": [
                               {"effect_id": "trigger_efficiency", "category": "efficiency", "applied_in": "estimator"},
                               {"effect_id": "selection_efficiency", "category": "efficiency", "applied_in": "estimator"},
                               {"effect_id": "acceptance", "category": "acceptance", "applied_in": "estimator"},
                               {"effect_id": "livetime_and_cutoff", "category": "exposure", "applied_in": "estimator"},
                               {"effect_id": "rigidity_migration", "category": "response", "applied_in": "response_matrix"}],
                           "systematics": [{"name": "trigger_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, shared by species)"},
                                           {"name": "selection_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (per bin, per species)"}],
                           "blinding": {"blinded": False},
                           "ratio": {"numerator": "helium flux", "denominator": "proton flux", "cancellations": [
                               {"effect": "trigger_efficiency", "treatment": "cancels", "correlation_model": "the same per-period estimate divides both species", "verification": "independent linear propagation with the shared component (core.stats ratio_measured) agrees"},
                               {"effect": "livetime_and_cutoff", "treatment": "cancels", "correlation_model": "identical livetime and cutoff fraction per period and bin", "verification": "by construction of the exposure"},
                               {"effect": "acceptance", "treatment": "independent", "correlation_model": "species-specific acceptance (assumed exactly known here)"},
                               {"effect": "selection_efficiency", "treatment": "independent", "correlation_model": "separate control samples per species"}]},
                           "experiment_fields": {"ams02:parameters": [
                               {"name": "geomagnetic cutoff safety factor", "value": CUTOFF_FACTOR, "provenance": "documented", "claim_ids": ["C31"], "applies_to": {"species": ["proton"]}},
                               {"name": "geomagnetic cutoff safety factor", "value": CUTOFF_FACTOR, "provenance": "proposal", "claim_ids": [], "applies_to": {"species": ["helium"]}}],
                               "ams02:note": "SYNTHETIC: every number except the documented cutoff factor is invented"}})
    resp = {}
    for sname in SPECIES:
        resp[sname] = dict(base, artifact_id=f"synthetic-path-a-response-{sname}", artifact_type="response",
                           objective=f"SYNTHETIC rigidity migration for {sname}", status=["synthetic"],
                           provenance={"producer_skill": "detector-response", "created": created},
                           extension={"truth_axis": {"name": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                      "reco_axis": {"name": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                      "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_selected",
                                      "inefficiency": "outside_matrix", "acceptance": "outside_matrix", "includes": ["migration"],
                                      "applied_separately": ["trigger_efficiency", "selection_efficiency", "acceptance", "exposure"],
                                      "underflow_overflow": "lost outside [1.5, 150] GV; first and last bins are buffers",
                                      "conditions": "per synthetic period (spectral shape inside bins differs slightly)",
                                      "provenance": "computed analytically from the synthetic resolution model", "matrix_ref": "results.json",
                                      "form": "matrix"})
    stat = dict(base, artifact_id="synthetic-path-a-ratio-result", artifact_type="statistical-result",
                objective="SYNTHETIC He/p ratio per bin and period with covariance",
                provenance={"producer_skill": "hep-statistics", "created": created}, status=["synthetic"],
                inputs=[{"ref": "artifacts/measurement_spec.json", "artifact_type": "measurement-spec", "status": ["synthetic"]}],
                extension={"paradigm": "frequentist", "likelihood": {"form": "Poisson counts per reco bin; unfolding by full-rank weighted least squares (no regularization)"},
                           "parameters_of_interest": ["He/p ratio per rigidity bin and period"],
                           "nuisances": ["trigger efficiency per period", "selection efficiency per bin and species"],
                           "test_statistic": "not-applicable (point estimates with linear covariance)", "construction": "other",
                           "coverage": {"method": "seeded toys of the full chain", "result_ref": "results.json#toy_closure"},
                           "fit_status": "converged", "results": {"ref": "results.json#ratio"}})
    data = {}
    for pname in PERIODS:
        r, c = res[("ratio", pname)]
        data[pname] = dict(base, artifact_id=f"synthetic-path-a-ratio-{pname}", artifact_type="dataset-record",
                           objective=f"SYNTHETIC He/p ratio, {pname}", status=["synthetic"],
                           provenance={"producer_skill": "hep-analysis", "created": created},
                           extension={"dataset_id": f"ams02:synthetic-path-a-ratio-{pname}", "source_evidence_ids": [],
                                      "observable": obs, "data": {"edges": edges, "values": r[REPORTED].tolist(), "unit": "1",
                                                                  "uncertainties": [{"name": "total", "kind": "statistical", "correlation": "covariance", "covariance_ref": f"results.json#ratio/{pname}/covariance"}]},
                                      "covariance": {"status": "present", "ref": f"results.json#ratio/{pname}/covariance"},
                                      "period": {"start": pname, "end": pname}, "status": "synthetic", "experiment_profile": PROFILE["id"]})
    docs = {"measurement_spec": spec, "response_proton": resp["proton"], "response_helium": resp["helium"], "ratio_result": stat,
            **{f"dataset_{p}": d for p, d in data.items()}}
    reports = {k: validate_artifact(v, vocab) for k, v in docs.items()}
    return docs, {k: {"ok": r.ok, "errors": [f.message for f in r.errors]} for k, r in reports.items()}


def figures(world, res, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    x = CENTER[REPORTED]
    shift = {p: f for p, f in zip(PERIODS, (0.97, 1.03))}  # offset the periods horizontally for legibility
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, sname in zip(axes, SPECIES):
        for pname, mk in zip(PERIODS, ("o", "s")):
            b = res[(sname, pname)]
            y, e = b["flux"][REPORTED], np.sqrt(np.diag(b["total"]))[REPORTED]
            ax.errorbar(x * shift[pname], y * x ** 2.7, yerr=e * x ** 2.7, fmt=mk, ms=4, label=f"{pname} (synthetic data)")
            ax.plot(x, world[sname][pname]["truth_flux"][REPORTED] * x ** 2.7, "--" if pname.endswith("1") else "-", lw=1, label=f"{pname} truth")
        ax.set_xscale("log"); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlabel("rigidity R [GV]"); ax.set_ylabel("flux x R^2.7 [m^-2 sr^-1 s^-1 GV^1.7]")
        ax.set_title(f"SYNTHETIC {sname} flux"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "flux_per_period.png", dpi=110); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for pname, mk in zip(PERIODS, ("o", "s")):
        r, c = res[("ratio", pname)]
        ax.errorbar(x * shift[pname], r[REPORTED], yerr=np.sqrt(np.diag(c))[REPORTED], fmt=mk, ms=4, label=f"{pname} (synthetic data)")
        ax.plot(x, world["ratio_truth"][pname][REPORTED], "--" if pname.endswith("1") else "-", lw=1, label=f"{pname} truth")
    ax.set_xscale("log"); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlabel("rigidity R [GV]"); ax.set_ylabel("He / p"); ax.set_title("SYNTHETIC He/p ratio"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out / "ratio_per_period.png", dpi=110); plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--toys", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261002)
    ap.add_argument("--created", default="2026-10-02", help="date recorded in artifact provenance (fixed for reproducibility)")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    args = ap.parse_args(argv)
    out = args.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    world = build_world()
    asimov_res, asimov_dev = asimov_closure(world)
    sim = simulate(np.random.default_rng(args.seed), world)
    res = run_analysis(sim, world)
    toys = toy_closure(world, args.toys, args.seed + 1)
    refs = {p: ratio_reference(res, p) for p in PERIODS}
    resp_checks = {s: validate_response({"metadata": {"truth_axis": {"variable": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                                      "reco_axis": {"variable": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                                      "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_selected",
                                                      "inefficiency": "outside_matrix", "acceptance": "outside_matrix",
                                                      "underflow_overflow": "explicit_bins", "efficiency_applied_separately": True,
                                                      "acceptance_applied_separately": True},
                                         "matrix": world[s][p]["response"].tolist(), "underflow": world[s][p]["underflow"].tolist(),
                                         "overflow": world[s][p]["overflow"].tolist()})["status"]
                   for s in SPECIES for p in list(PERIODS)[:1]}
    cov_checks = {}
    for (k, p), b in res.items():
        if k in SPECIES and p in PERIODS:
            sl = REPORTED
            cov_checks[f"{k}/{p}"] = validate_covariance({"labels": [f"b{j}" for j in range(sl.start, sl.stop)], "kind": "absolute",
                                                          "units": "(m^-2 sr^-1 s^-1 GV^-1)^2", "matrix": b["total"][sl, sl].tolist(),
                                                          "blocks": {"stat": b["stat"][sl, sl].tolist(), "trigger": b["trigger"][sl, sl].tolist(),
                                                                     "selection": b["selection"][sl, sl].tolist()}})["status"]
    docs, contract = artifacts(world, res, args.created)
    for name, doc in docs.items():
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")

    t11 = {s: {"exposure_per_period": {p: world[s][p]["exposure"][REPORTED].tolist() for p in PERIODS},
               "average_flux": res[(s, "average")][REPORTED].tolist(), "average_truth": world[s]["average_truth"][REPORTED].tolist(),
               "equal_split_exposure_rel_error": [round(float(v), 4) + 0.0 for v in world[s]["equal_split_exposure"][REPORTED] / sum(world[s][p]["exposure"] for p in PERIODS)[REPORTED] - 1]}
           for s in SPECIES}
    passes = {
        "asimov_closure": max(asimov_dev.values()) < CRITERIA["asimov_max_rel_dev"],
        "toy_mean_pull": all(abs(v) < CRITERIA["toy_mean_pull_abs"] for s in toys.values() for v in s["mean_per_bin"]),
        "toy_pull_width": all(CRITERIA["toy_pull_width"][0] < v < CRITERIA["toy_pull_width"][1] for s in toys.values() for v in s["width_per_bin"]),
        "ratio_reference_agreement": all(r["max_rel_difference"] < CRITERIA["reference_rel_agreement"] for r in refs.values()),
        "response_checks": all(v != "fail" for v in resp_checks.values()),
        "covariance_checks": all(v != "fail" for v in cov_checks.values()),
        "contracts": all(c["ok"] for c in contract.values()),
    }
    results = {
        "label": "SYNTHETIC: invented inputs; describes no experiment",
        "seed": args.seed, "toys": args.toys, "criteria": CRITERIA, "pass": passes,
        "edges_gv": EDGES.tolist(), "reported_bins": [REPORTED.start, REPORTED.stop],
        "synthetic_inputs": {"species": SPECIES, "periods": PERIODS, "cutoff_factor": CUTOFF_FACTOR, "resolution": RESOLUTION,
                             "n_ctrl_trigger": N_CTRL_TRIGGER, "n_ctrl_selection": N_CTRL_SELECTION},
        "observed_counts": {f"{s}/{p}": sim["counts"][(s, p)].tolist() for s in SPECIES for p in PERIODS},
        "flux": {f"{s}/{p}": {"values": res[(s, p)]["flux"].tolist(), "truth": world[s][p]["truth_flux"].tolist(),
                              "covariance": {k: res[(s, p)][k].tolist() for k in ("stat", "trigger", "selection", "total")}}
                 for s in SPECIES for p in PERIODS},
        "ratio": {p: {"values": res[("ratio", p)][0].tolist(), "truth": world["ratio_truth"][p].tolist(),
                      "covariance": res[("ratio", p)][1].tolist()} for p in PERIODS},
        "time_average_T11": t11,
        "asimov_closure_max_rel_dev": asimov_dev, "toy_closure": toys, "ratio_reference_T10": refs,
        "response_validation": resp_checks, "covariance_validation": cov_checks, "contract_validation": contract,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    figures(world, res, out)
    write_report(out, results)
    digest = hashlib.sha256((out / "results.json").read_bytes()).hexdigest()
    print(json.dumps({"pass": passes, "results_sha256": digest}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    def fmt(v):
        return ", ".join(f"{x:.4g}" for x in v)
    lines = [
        "# Path A report: synthetic flux and correlated He/p ratio (SYNTHETIC)",
        "",
        "**Status: synthetic.** All inputs are invented (see `results.json` → `synthetic_inputs`). Nothing here is an AMS-02 "
        "measurement, performance figure or result. The profile supplies conventions (rigidity R = pc/(Ze) in GV, flux at the "
        "top of the instrument, exposure normalization) and one documented practice: R > 1.2 × maximum cutoff, documented for "
        "the proton flux analysis [Documented, ams02:C31] and applied to helium here as a [Proposal].",
        "",
        f"Reproduce: `python3 examples/ams-flux-ratio/run_path_a.py --toys {r['toys']} --seed {r['seed']}` (from the plugin root, D5 environment).",
        "",
        "## Pre-declared criteria and outcome",
        "",
        "| Check | Criterion | Result |",
        "|---|---|---|",
        f"| Asimov closure (flux, ratio, period average) | max relative deviation < {r['criteria']['asimov_max_rel_dev']} | {'pass' if r['pass']['asimov_closure'] else 'FAIL'} (max {max(r['asimov_closure_max_rel_dev'].values()):.2e}) |",
        f"| Toy closure, mean pull per bin | abs < {r['criteria']['toy_mean_pull_abs']} | {'pass' if r['pass']['toy_mean_pull'] else 'FAIL'} |",
        f"| Toy closure, pull width per bin | in {tuple(r['criteria']['toy_pull_width'])} | {'pass' if r['pass']['toy_pull_width'] else 'FAIL'} |",
        f"| Ratio sigma vs independent propagation (T10) | relative difference < {r['criteria']['reference_rel_agreement']} | {'pass' if r['pass']['ratio_reference_agreement'] else 'FAIL'} |",
        f"| Response and covariance validators (core.stats) | no failure | {'pass' if r['pass']['response_checks'] and r['pass']['covariance_checks'] else 'FAIL'} |",
        f"| Contract artifacts (profile vocabulary) | all valid | {'pass' if r['pass']['contracts'] else 'FAIL'} |",
        "",
        "The covariance validator warns that the trigger block has rank 1. That is expected: a single per-period trigger "
        "efficiency scales every bin together, so its block is fully correlated by construction.",
        "",
        "## What the chain does",
        "",
        "Per species and synthetic period: selected truth counts = ∫Φ dR × acceptance × livetime × cutoff fraction × trigger "
        "efficiency × selection efficiency; rigidity migration (2% core resolution in curvature, a 2% tail five times wider) "
        "gives Poisson reco counts; a full-rank weighted least-squares unfolding (`core.stats.unfolding_diagnostics.linear_matrix`, "
        "no regularization) returns selected truth counts; dividing by the efficiencies, the exposure and the bin width gives the "
        "bin-averaged flux. The first and last bins (1.5-2 and 100-150 GV) absorb migration and are not reported.",
        "",
        "Efficiencies are estimated from synthetic control samples. The trigger efficiency is one estimate per period shared by "
        "both species (fully correlated across bins); the selection efficiency is measured per bin and species and shared by the "
        "two periods. In the He/p ratio the trigger term cancels exactly and the livetime and cutoff fraction cancel by "
        "construction; acceptance and selection efficiency do not cancel.",
        "",
        "## Correlated ratio (T10)",
        "",
    ]
    for p, ref in r["ratio_reference_T10"].items():
        lines.append(f"- {p}: ratio sigma per bin {fmt(ref['this_analysis_sigma'])}; independent linear propagation with the shared "
                     f"trigger component agrees to {ref['max_rel_difference']:.1e}. Treating the trigger term as independent "
                     f"would overstate the sigma by factors {fmt(ref['overestimate_factor_if_independent'])}.")
    lines += ["", "## Time-dependent exposure (T11)", ""]
    livetimes = ", ".join(f"{v['livetime']:.2g} s" for v in r["synthetic_inputs"]["periods"].values())
    for s, t in r["time_average_T11"].items():
        lines.append(f"- {s}: the period average is the sum of efficiency-corrected counts over the sum of per-period exposures "
                     f"(livetimes {livetimes}; "
                     f"different cutoff fractions). Splitting the total livetime equally between periods would mis-state the "
                     f"exposure per bin by {fmt(t['equal_split_exposure_rel_error'])} (relative).")
    lines += ["", "## Toy closure", "", f"{r['toys']} pseudo-experiments (seed {r['seed'] + 1}) regenerate the counts and the control samples.", "",
              "| Quantity | mean pull per bin | pull width per bin |", "|---|---|---|"]
    for k, v in r["toy_closure"].items():
        lines.append(f"| {k} | {fmt(v['mean_per_bin'])} | {fmt(v['width_per_bin'])} |")
    lines += ["", "## Limitations (by construction of this example)", "",
              "- Acceptance and the response are assumed exactly known; no finite-MC or acceptance systematic is modeled.",
              "- No background, charge confusion or fragmentation is modeled; the synthetic truth exists only in 1.5-150 GV.",
              "- The response uses the generated spectral shape inside each bin, so model dependence of the unfolding is not studied.",
              "- Acceptance, efficiencies and cutoff fractions are constant within a bin by construction.",
              "- Passing these checks shows the chain is internally consistent on synthetic data; it says nothing about any real detector.",
              "", "Figures: `flux_per_period.png`, `ratio_per_period.png`. Artifacts: `artifacts/*.json` (all status `synthetic`).", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())

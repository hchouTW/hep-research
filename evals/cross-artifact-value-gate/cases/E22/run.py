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

Background (SYNTHETIC): a tail of Z=1 events in the charge estimator Q leaks into the helium window 1.7 <= Q < 2.5.
It is estimated per reco rigidity bin and period from the helium-free sideband 1.3 <= Q < 1.6 times a transfer
factor from the synthetic tail shape (10% fully correlated uncertainty), subtracted before the helium unfolding, and
checked in the validation band 1.6 <= Q < 1.7 and by Asimov closure.

Blinding (SYNTHETIC policy): the helium signal-region count in the bin 60-100 GV is blinded in both periods. A
custodian step (skills/hep-measurement/scripts/mask_blinded_bins.py) masks it before the analysis reads the counts; the
unfolding fills it with the simulated helium expectation and zero variance, so no published number depends on it,
and the helium flux, the He/p ratio and the period average are null in that bin in every output. The charge sidebands
and the proton counts stay open. Unblinding is not done here.

Usage (from the plugin root): python3 examples/ams-flux-ratio/run.py [--toys 400] [--seed 20261002] [--out DIR]
Default output: examples/ams-flux-ratio/output/. Exit 0 when every pre-declared closure criterion passes,
1 otherwise. Requires numpy and matplotlib (the D5 environment).
Validating the spec by hand: its level `crflux:top-of-instrument` is a profile term, so plain validation reports
vocab.unknown_term; bind experiment:ams-02 in a project config outside the plugin (with an artifacts_dir outside it)
and run python3 "<plugin root>/contracts/validate.py" examples/ams-flux-ratio/output/artifacts/measurement_spec.json --profiles-from <your project>/hep-research.project.json.
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
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.blinding.blinding import blinded_mask, check_figure  # noqa: E402
from core.stats.statistical_toys import chi2_sf, ratio_measured  # noqa: E402
from core.stats.unfolding_diagnostics import linear_matrix  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from contracts.response_adapter import to_validator_input  # noqa: E402

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
CHARGE_TAIL = {"fraction": 0.05, "start": 1.3, "slope": 0.2}  # synthetic: fraction of selected Z=1 events with Q > start
HE_WINDOW = (1.7, 2.5)  # helium signal region in the charge estimator Q (synthetic)
SIDEBAND = (1.3, 1.6)  # helium-free control sideband (synthetic)
VALIDATION_BAND = (1.6, 1.7)  # helium-free validation band (synthetic)
TF_REL = 0.10  # synthetic transfer-factor uncertainty (tail-shape modelling), fully correlated
BLIND = {"variable": "rigidity", "low": 60.0, "high": 100.0}  # synthetic blinding policy, helium signal region only
CRITERIA = {"asimov_max_rel_dev": 1e-9, "toy_mean_pull_abs": 0.2, "toy_pull_width": (0.85, 1.15),
            "reference_rel_agreement": 1e-9, "background_asimov_max_rel_dev": 1e-12, "validation_band_abs_pull": 3.0,
            "validation_band_chi2_p_min": 1e-3, "validation_band_min_predicted": 5.0}
MASK_SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "mask_blinded_bins.py"

NB = len(EDGES) - 1
WIDTH = np.diff(EDGES)
CENTER = np.sqrt(EDGES[:-1] * EDGES[1:])
BLINDED = np.array(blinded_mask(EDGES, BLIND))
PUBLISHED = slice(REPORTED.start, int(np.flatnonzero(BLINDED)[0]))  # reported helium and ratio bins below the blinded one


def tail_fraction(lo, hi):
    """Fraction of the synthetic Z=1 charge tail (exponential above CHARGE_TAIL['start']) with lo <= Q < hi."""
    t = CHARGE_TAIL
    return math.exp(-(lo - t["start"]) / t["slope"]) - math.exp(-(hi - t["start"]) / t["slope"])


TF_SR = tail_fraction(*HE_WINDOW) / tail_fraction(*SIDEBAND)
TF_VR = tail_fraction(*VALIDATION_BAND) / tail_fraction(*SIDEBAND)


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
def unfold(m, counts, var, weights):
    a = np.array(linear_matrix("tsvd", NB, m.tolist(), np.maximum(weights, 1.0).tolist()))
    u = a @ counts
    cov = a @ np.diag(var) @ a.T
    return u, cov, a


def blind_counts(values):
    """The analysis-side view of a helium signal-region histogram: the blinded bin is None."""
    return [None if (b or v is None) else float(v) for v, b in zip(values, BLINDED)]


def analyse(counts, eff_trig_hat, eff_sel_hat, sigma_trig, sigma_sel, expo, m, sideband=None, tf=0.0, fill=None):
    """Flux and covariance blocks for one species and period. counts may hold None (a blinded bin, as released by the
    custodian step): that bin takes the simulated expectation fill[k] with no variance. With a sideband, the
    background tf x sideband is subtracted per reco bin; its statistical variance joins the statistical block and the
    transfer-factor uncertainty forms the background block."""
    blind = np.array([v is None for v in counts])
    n = np.array([0.0 if v is None else float(v) for v in counts])
    cr = np.zeros(NB) if sideband is None else np.asarray(sideband, float)
    bkg = np.where(blind, 0.0, tf * cr)
    s = np.where(blind, 0.0 if fill is None else fill, n - bkg)
    var = np.where(blind, 0.0, n + tf ** 2 * cr)
    u, cov_u, a = unfold(m, s, var, np.where(blind, s, var))  # the weights only condition the full-rank inverse
    denom = eff_trig_hat * eff_sel_hat * expo * WIDTH
    flux = u / denom
    jac = np.diag(1.0 / denom)
    stat = jac @ cov_u @ jac.T
    bkg_cov = jac @ a @ (np.outer(bkg, bkg) * TF_REL ** 2) @ a.T @ jac.T
    trig = np.outer(flux, flux) * (sigma_trig / eff_trig_hat) ** 2  # fully correlated across bins
    sel = np.diag((flux * sigma_sel / eff_sel_hat) ** 2)  # independent per bin
    return {"flux": flux, "unfolded": u, "stat": stat, "trigger": trig, "selection": sel, "background": bkg_cov,
            "total": stat + trig + sel + bkg_cov, "background_estimate": tf * cr}


def ratio_block(num, den):
    """He/p ratio and covariance; the trigger efficiency is the same estimate in both, so it cancels exactly."""
    r = num["flux"] / den["flux"]
    rel = (num["stat"] + num["selection"] + num["background"]) / np.outer(num["flux"], num["flux"]) + \
          (den["stat"] + den["selection"] + den["background"]) / np.outer(den["flux"], den["flux"])
    return r, rel * np.outer(r, r)


def simulate(rng, world, asimov=False):
    """One pseudo-experiment: reco counts per species and period, the efficiency control samples, and the Z=1 charge
    tail in the helium window, the sideband and the validation band. The tail is drawn after the signal, so the signal
    counts of a seed are those of the signal-only chain. The helium counts are the full signal region (unmasked)."""
    out = {"counts": {}, "trig_hat": {}, "sel_hat": {}, "sideband": {}, "validation": {}}
    for pname, per in PERIODS.items():
        out["trig_hat"][pname] = per["trigger"] if asimov else rng.binomial(N_CTRL_TRIGGER, per["trigger"]) / N_CTRL_TRIGGER
    for sname, sp in SPECIES.items():
        eps = selection_eff(sp)
        out["sel_hat"][sname] = eps if asimov else rng.binomial(N_CTRL_SELECTION, eps) / N_CTRL_SELECTION
        for pname in PERIODS:
            mu = world[sname][pname]["expected_reco"]
            out["counts"][(sname, pname)] = mu.copy() if asimov else rng.poisson(mu).astype(float)
    for pname in PERIODS:
        leak = world["helium"][pname]["leak"]
        draw = (lambda mu: mu.copy()) if asimov else (lambda mu: rng.poisson(mu).astype(float))  # noqa: E731
        out["counts"][("helium", pname)] = out["counts"][("helium", pname)] + draw(leak["window"])
        out["sideband"][pname] = draw(leak["sideband"])
        out["validation"][pname] = draw(leak["validation"])
    out["tf_hat"] = TF_SR if asimov else TF_SR * (1.0 + TF_REL * rng.normal())
    return out


def run_analysis(sim, world):
    """The published (blinded) procedure: the helium signal-region bin in BLIND is masked if it is not already."""
    res = {}
    for pname, per in PERIODS.items():
        st = math.sqrt(per["trigger"] * (1 - per["trigger"]) / N_CTRL_TRIGGER)
        for sname, sp in SPECIES.items():
            ss = np.sqrt(selection_eff(sp) * (1 - selection_eff(sp)) / N_CTRL_SELECTION)
            w = world[sname][pname]
            if sname == "helium":
                extra = {"sideband": sim["sideband"][pname], "tf": sim["tf_hat"], "fill": w["expected_reco"]}
                counts = blind_counts(sim["counts"][(sname, pname)])
            else:
                extra, counts = {}, sim["counts"][(sname, pname)]
            sel = sim["sel_hat"][sname] if sname == "proton" else 1.0  # helium: inside the acceptance model
            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sel,
                                          st, ss, w["exposure"], w["response"], **extra)
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
        # synthetic background: the Z=1 charge tail, binned like the proton reco counts, in each charge band
        tail = CHARGE_TAIL["fraction"] * world["proton"][pname]["expected_reco"]
        world["helium"][pname]["leak"] = {"window": tail * tail_fraction(*HE_WINDOW), "sideband": tail * tail_fraction(*SIDEBAND),
                                          "validation": tail * tail_fraction(*VALIDATION_BAND)}
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
    """Toys of the published procedure (helium blinded bin filled): pulls over the reported proton bins and over the
    published helium and ratio bins (the blinded bin carries the expectation, not a measurement)."""
    rng = np.random.default_rng(seed)
    pulls = {}
    for _ in range(toys):
        res = run_analysis(simulate(rng, world), world)
        for sname in SPECIES:
            for pname in PERIODS:
                b = res[(sname, pname)]
                p = (b["flux"] - world[sname][pname]["truth_flux"]) / np.sqrt(np.diag(b["total"]))
                pulls.setdefault(f"{sname}/{pname}", []).append(p[REPORTED if sname == "proton" else PUBLISHED])
        for pname in PERIODS:
            r, c = res[("ratio", pname)]
            pulls.setdefault(f"ratio/{pname}", []).append(((r - world["ratio_truth"][pname]) / np.sqrt(np.diag(c)))[PUBLISHED])
    summary = {}
    for key, rows in pulls.items():
        a = np.array(rows)
        summary[key] = {"mean_per_bin": a.mean(axis=0).round(4).tolist(), "width_per_bin": a.std(axis=0, ddof=1).round(4).tolist()}
    return summary


def ratio_reference(res, pname):
    """Independent linear propagation (core.stats ratio_measured) from the joint He, p covariance in which the
    trigger term is a shared, fully correlated component. Must equal the cancellation used in ratio_block."""
    he, p = res[("helium", pname)], res[("proton", pname)]
    sl = PUBLISHED
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


def validation_closure(sim):
    """Closure of the charge-sideband method in the helium-free validation band, per period: predicted TF_VR x sideband
    against the observed counts; total pull with statistical uncertainties only, and chi2 over the bins with at least
    CRITERIA['validation_band_min_predicted'] predicted events."""
    out = {}
    for pname in PERIODS:
        cr, vr = sim["sideband"][pname], sim["validation"][pname]
        pred = TF_VR * cr
        var = pred + TF_VR ** 2 * cr
        ok = pred >= CRITERIA["validation_band_min_predicted"]
        chi2 = float(np.sum((vr - pred)[ok] ** 2 / var[ok]))
        ndf = int(ok.sum())
        out[pname] = {"observed": vr.tolist(), "predicted": pred.tolist(), "total_observed": float(vr.sum()),
                      "total_predicted": float(pred.sum()), "total_pull": float((vr.sum() - pred.sum()) / math.sqrt(var.sum())),
                      "chi2": chi2, "ndf": ndf, "p_value": chi2_sf(chi2, ndf)}
    return out


def custodian_mask(counts, expected, pname, out):
    """SYNTHETIC stand-in for the data custodian's preparation step: the unmasked helium signal-region histogram exists
    only in a temporary directory outside the outputs; mask_blinded_bins.py writes the released masked histogram (and
    the masked data/expectation ratio) into the outputs, and the analysis reads only that file."""
    import tempfile
    sys.path.insert(0, str(MASK_SCRIPT.parent))
    import mask_blinded_bins
    target = out / "blinded" / f"helium_signal_region_{pname}.masked.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        hist, ref = Path(tmp) / "hist.json", Path(tmp) / "expected.json"
        hist.write_text(json.dumps({"edges": EDGES.tolist(), "values": np.asarray(counts).tolist()}))
        ref.write_text(json.dumps({"edges": EDGES.tolist(), "values": np.asarray(expected).tolist()}))
        code = mask_blinded_bins.main(["--hist", str(hist), "--low", str(BLIND["low"]), "--high", str(BLIND["high"]),
                                       "--reference", str(ref), "--status", "synthetic", "--out", str(target)])
    if code != 0:
        raise RuntimeError("the masking step failed: nothing may be analysed")
    return json.loads(target.read_text(encoding="utf-8"))["values"], target


def pseudo_data(seed, world):
    """The SYNTHETIC pseudo-data of a seed, unmasked: only the custodian step (and a test acting as custodian) reads
    the helium signal-region counts from it. The data analysis uses the nominal transfer factor; only toys vary it."""
    sim = simulate(np.random.default_rng(seed), world)
    sim["tf_hat"] = TF_SR
    return sim


# ----------------------------------------------------------------------------- outputs
def artifacts(world, res, created):
    vocab = Vocabulary.with_profiles([PROFILE])
    edges = EDGES[1:-1].tolist()
    base = {"contract_version": CONTRACTS_VERSION, "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
            "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {PROFILE["id"]: PROFILE["version"]}},
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
                provenance={"producer_skill": "hep-measurement", "created": created, "evidence_ids": ["ams02:C31"]},
                status=["synthetic"],
                extension={"estimand": ("SYNTHETIC: the helium-to-proton flux ratio per rigidity bin (edges above, GV) at top "
                                        "of instrument, separately in each of two synthetic periods, for particles above the "
                                        "geomagnetic cutoff selection"),
                           "observable": obs, "species_or_process": "helium, proton (synthetic)", "period": periods,
                           "selections": [{"name": "geomagnetic", "definition": "bin lower edge > 1.2 x maximum cutoff", "conditional_denominator": "livetime"},
                                          {"name": "species selection", "definition": "synthetic per-species selection", "conditional_denominator": "triggered events in acceptance"},
                                          {"name": "helium charge window", "definition": "SYNTHETIC: charge estimator 1.7 <= Q < 2.5",
                                           "conditional_denominator": "helium events passing the species selection (inside by construction)"}],
                           "backgrounds": [{"name": "Z=1 charge tail in the helium window (synthetic)",
                                            "estimator": "charge-sideband extrapolation: B_k = TF x N_sideband,k per reco rigidity bin and "
                                                         "period, TF = tail fraction in the window / in the sideband from the synthetic tail shape",
                                            "control_region": "SYNTHETIC: charge estimator 1.3 <= Q < 1.6 (helium-free by construction)",
                                            "closure": "SYNTHETIC: validation band 1.6 <= Q < 1.7 predicted from the sideband per period "
                                                       "(results.json#background/validation_closure); Asimov closure exact",
                                            "transfer_factor": TF_SR, "processes": ["proton (Z=1)"],
                                            "uncertainty": "10% on TF, fully correlated (synthetic tail-shape modelling); sideband "
                                                           "counts in the statistical block"}],
                           "corrections": [
                               {"effect_id": "trigger_efficiency", "category": "trigger_efficiency", "applied_in": "estimator"},
                               {"effect_id": "selection_efficiency", "category": "selection_efficiency", "applied_in": "estimator"},
                               {"effect_id": "acceptance", "category": "acceptance", "applied_in": "normalization", "factor_of": "exposure",
                                "notes": "acceptance enters once, inside the exposure normalization (acceptance x livetime x cutoff fraction)"},
                               {"effect_id": "rigidity_migration", "category": "migration", "applied_in": "response_matrix"}],
                           "systematics": [{"name": "trigger_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, shared by species)"},
                                           {"name": "selection_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (per bin, per species)"},
                                           {"name": "background_transfer_factor", "source": "synthetic 10% on the charge-tail transfer factor", "effect": "mixed",
                                            "applied_via": "covariance (TF x sideband counts, fully correlated across bins, helium only, unfolded)"}],
                           "blinding": {"blinded": True,
                                        "mask": {"regions": ["helium signal region (1.7 <= Q < 2.5) in the bin 60-100 GV, both periods"],
                                                 "intervals": [dict(BLIND)]},
                                        "unblinding_record_ref": None},
                           "notes": ("SYNTHETIC blinding policy: the custodian step masks the helium signal-region count in the "
                                     "blinded bin; the unfolding fills it with the simulated expectation; helium flux, ratio and "
                                     "period average are null there; proton counts and the charge sidebands stay open"),
                           "ratio": {"numerator": "helium flux", "denominator": "proton flux", "cancellations": [
                               {"effect": "trigger_efficiency", "treatment": "cancels", "correlation_model": "the same per-period estimate divides both species", "verification": "independent linear propagation with the shared component (core.stats ratio_measured) agrees"},
                               {"effect": "livetime_and_cutoff", "treatment": "cancels", "correlation_model": "identical livetime and cutoff fraction per period and bin", "verification": "by construction of the exposure"},
                               {"effect": "acceptance", "treatment": "independent", "correlation_model": "species-specific acceptance (assumed exactly known here)"},
                               {"effect": "selection_efficiency", "treatment": "independent", "correlation_model": "separate control samples per species"},
                               {"effect": "background_subtraction", "treatment": "independent", "correlation_model": "helium (numerator) only; the proton sample has no subtracted background here"}]},
                           "experiment_fields": {"ams02:parameters": [
                               {"name": "geomagnetic cutoff safety factor", "value": CUTOFF_FACTOR, "provenance": "documented", "claim_ids": ["C31"], "applies_to": {"species": ["proton"]}},
                               {"name": "geomagnetic cutoff safety factor", "value": CUTOFF_FACTOR, "provenance": "proposal", "claim_ids": [], "applies_to": {"species": ["helium"]}}],
                               "ams02:note": "SYNTHETIC: every number except the documented cutoff factor is invented"}})
    resp = {}
    for sname, pname in ((s, p) for s in SPECIES for p in PERIODS):
        resp[(sname, pname)] = dict(base, artifact_id=f"synthetic-path-a-response-{sname}-{pname}", artifact_type="response",
                           objective=f"SYNTHETIC rigidity migration for {sname}, {pname}", status=["synthetic"],
                           provenance={"producer_skill": "hep-detector", "created": created},
                           extension={"truth_axis": {"name": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                      "reco_axis": {"name": "rigidity", "unit": "GV", "edges": EDGES.tolist()},
                                      "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_selected",
                                      "inefficiency": "outside_matrix", "acceptance": "outside_matrix", "includes": ["migration"],
                                      "applied_separately": ["trigger_efficiency", "selection_efficiency", "exposure"],
                                      # analyse() divides the unfolded (truth-space) counts by the efficiencies and by
                                      # the exposure per rigidity bin (acceptance x livetime x cutoff fraction)
                                      "correction_space": {"trigger_efficiency": {"space": "truth"},
                                                           "selection_efficiency": {"space": "truth", "binned_in": "rigidity"},
                                                           "exposure": {"space": "truth", "binned_in": "rigidity"}},
                                      "underflow_overflow": "explicit_bins", "intended_use": "unfolding",
                                      "conditions": f"{pname} (the spectral shape inside bins differs slightly between periods)",
                                      "provenance": "computed analytically from the synthetic resolution model; migration outside "
                                                    "[1.5, 150] GV is kept in explicit underflow/overflow vectors; first and last "
                                                    "bins are buffers", "matrix_ref": f"matrices/response_{sname}_{pname}.json",
                                      "form": "matrix"})
    stat = dict(base, artifact_id="synthetic-path-a-ratio-result", artifact_type="statistical-result", required_capabilities=["stats:result-semantics"],
                objective="SYNTHETIC He/p ratio per bin and period with covariance",
                provenance={"producer_skill": "hep-statistics", "created": created}, status=["synthetic"],
                inputs=[{"ref": "artifacts/measurement_spec.json", "artifact_type": "measurement-spec", "status": ["synthetic"]}],
                extension={"paradigm": "frequentist", "likelihood": {"form": "Poisson counts per reco bin; unfolding by full-rank weighted least squares (no regularization)"},
                           "parameters_of_interest": ["He/p ratio per rigidity bin and period"],
                           "nuisances": ["trigger efficiency per period", "selection efficiency per bin and species",
                                         "background transfer factor (helium)"],
                           "test_statistic": "not-applicable (point estimates with linear covariance)", "construction": "other",
                           "coverage": {"check": "not-checked", "method": "seeded toys of the full chain (closure and pulls, not interval coverage)", "result_ref": "results.json#toy_closure"},
                           "fit_status": "converged", "results": {"ref": "results.json#ratio"}})
    data = {}
    pub_edges = EDGES[PUBLISHED.start:PUBLISHED.stop + 1].tolist()  # the blinded bin is not released
    pub_obs = dict(obs, variables=[{"name": "rigidity", "unit": "GV", "edges": pub_edges}])
    for pname in PERIODS:
        r, c = res[("ratio", pname)]
        data[pname] = dict(base, artifact_id=f"synthetic-path-a-ratio-{pname}", artifact_type="dataset-record",
                           objective=f"SYNTHETIC He/p ratio, {pname}, unblinded bins", status=["synthetic"],
                           provenance={"producer_skill": "hep-measurement", "created": created},
                           extension={"dataset_id": f"ams02:synthetic-path-a-ratio-{pname}", "source_evidence_ids": [],
                                      "observable": pub_obs, "data": {"edges": pub_edges, "values": r[PUBLISHED].tolist(), "unit": "1",
                                                                  "uncertainties": [{"name": "total", "kind": "statistical", "correlation": "covariance", "covariance_ref": f"results.json#ratio/{pname}/covariance"}]},
                                      "covariance": {"status": "present", "ref": f"results.json#ratio/{pname}/covariance"},
                                      "period": {"start": pname, "end": pname}, "status": "synthetic", "experiment_profile": PROFILE["id"]})
    docs = {"measurement_spec": spec, **{f"response_{s}_{p}": d for (s, p), d in resp.items()}, "ratio_result": stat,
            **{f"dataset_{p}": d for p, d in data.items()}}
    reports = {k: validate_artifact(v, vocab) for k, v in docs.items()}
    return docs, {k: {"ok": r.ok, "errors": [f.message for f in r.errors]} for k, r in reports.items()}


def review_spec(spec, vocab, out):
    """Verdict-first review draft of the spec with the hep-measurement review script (references/review-and-artifacts.md)."""
    sys.path.insert(0, str(PLUGIN / "skills" / "hep-measurement" / "scripts"))
    import review_measurement_spec
    review = review_measurement_spec.draft(spec, vocab)
    (out / "review.md").write_text(review_measurement_spec.markdown(review, spec["artifact_id"], "synthetic"))
    return {"verdict": review["verdict"], "defects": len(review["defects"]), "unresolved": len(review["unresolved"])}


def figures(world, res, out):
    """Both figures show the bins below the blinded one only (every species, data and truth alike), and are saved only
    when core.blinding.check_figure finds nothing drawn inside the blinded rigidity range."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    sl = PUBLISHED
    x = CENTER[sl]
    shift = {p: f for p, f in zip(PERIODS, (0.97, 1.03))}  # offset the periods horizontally for legibility
    checks = {}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, sname in zip(axes, SPECIES):
        for pname, mk in zip(PERIODS, ("o", "s")):
            b = res[(sname, pname)]
            y, e = b["flux"][sl], np.sqrt(np.diag(b["total"]))[sl]
            ax.errorbar(x * shift[pname], y * x ** 2.7, yerr=e * x ** 2.7, fmt=mk, ms=4, label=f"{pname} (synthetic data)")
            ax.plot(x, world[sname][pname]["truth_flux"][sl] * x ** 2.7, "--" if pname.endswith("1") else "-", lw=1, label=f"{pname} truth")
        ax.set_xscale("log"); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlabel("rigidity R [GV]"); ax.set_ylabel("flux x R^2.7 [m^-2 sr^-1 s^-1 GV^1.7]")
        ax.set_title(f"SYNTHETIC {sname} flux (60-100 GV blinded)"); ax.legend(fontsize=7)
    fig.tight_layout()
    checks["flux_per_period.png"] = len(check_figure(fig, BLIND))
    if not checks["flux_per_period.png"]:
        fig.savefig(out / "flux_per_period.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for pname, mk in zip(PERIODS, ("o", "s")):
        r, c = res[("ratio", pname)]
        ax.errorbar(x * shift[pname], r[sl], yerr=np.sqrt(np.diag(c))[sl], fmt=mk, ms=4, label=f"{pname} (synthetic data)")
        ax.plot(x, world["ratio_truth"][pname][sl], "--" if pname.endswith("1") else "-", lw=1, label=f"{pname} truth")
    ax.set_xscale("log"); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlabel("rigidity R [GV]"); ax.set_ylabel("He / p"); ax.set_title("SYNTHETIC He/p ratio (60-100 GV blinded)"); ax.legend(fontsize=7)
    fig.tight_layout()
    checks["ratio_per_period.png"] = len(check_figure(fig, BLIND))
    if not checks["ratio_per_period.png"]:
        fig.savefig(out / "ratio_per_period.png", dpi=110)
    plt.close(fig)
    return {"status": "pass" if not any(checks.values()) else "fail", "artists_in_blinded_range": checks}


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
    bkg_asimov_dev = max(float(np.max(np.abs(TF_SR * world["helium"][p]["leak"]["sideband"] / world["helium"][p]["leak"]["window"] - 1)))
                         for p in PERIODS)
    sim = pseudo_data(args.seed, world)
    # custodian step: the helium signal-region histograms are masked before the analysis reads them
    released = {}
    for p in PERIODS:
        expected = world["helium"][p]["expected_reco"] + world["helium"][p]["leak"]["window"]
        sim["counts"][("helium", p)], released[p] = custodian_mask(sim["counts"][("helium", p)], expected, p, out)
    res = run_analysis(sim, world)
    vclos = validation_closure(sim)
    toys = toy_closure(world, args.toys, args.seed + 1)
    refs = {p: ratio_reference(res, p) for p in PERIODS}
    docs, contract = artifacts(world, res, args.created)
    # the validator input comes from each response artifact (contracts.response_adapter), not a second declaration
    # each response artifact points at its own matrix file (matrix, underflow, overflow); every period is checked
    matrices = {(s, p): {"matrix": world[s][p]["response"].tolist(), "underflow": world[s][p]["underflow"].tolist(),
                         "overflow": world[s][p]["overflow"].tolist()} for s in SPECIES for p in PERIODS}
    resp_checks = {f"{s}/{p}": validate_response(to_validator_input(docs[f"response_{s}_{p}"]["extension"], **m)["input"])["status"]
                   for (s, p), m in matrices.items()}
    cov_checks = {}
    for (k, p), b in res.items():
        if k in SPECIES and p in PERIODS:
            sl = REPORTED if k == "proton" else PUBLISHED
            blocks = {"stat": b["stat"][sl, sl].tolist(), "trigger": b["trigger"][sl, sl].tolist(), "selection": b["selection"][sl, sl].tolist()}
            if k == "helium":
                blocks["background"] = b["background"][sl, sl].tolist()
            cov_checks[f"{k}/{p}"] = validate_covariance({"labels": [f"b{j}" for j in range(sl.start, sl.stop)], "kind": "absolute",
                                                          "units": "(m^-2 sr^-1 s^-1 GV^-1)^2", "matrix": b["total"][sl, sl].tolist(),
                                                          "blocks": blocks})["status"]
    for name, doc in docs.items():
        (out / "artifacts" / f"{name}.json").write_text(json.dumps(doc, indent=1) + "\n")
    (out / "artifacts" / "matrices").mkdir(exist_ok=True)
    for (s, p), m in matrices.items():
        (out / "artifacts" / "matrices" / f"response_{s}_{p}.json").write_text(json.dumps(m, indent=1) + "\n")
    fig_check = figures(world, res, out)

    def pub(v, species="helium"):
        """Values with the blinded bin null (helium and the ratio; proton values are open)."""
        v = np.asarray(v).tolist()
        return v if species == "proton" else [None if b else x for x, b in zip(v, BLINDED)]

    def pub_cov(c, species="helium"):
        c = np.asarray(c).tolist()
        return c if species == "proton" else [pub(row) if not b else [None] * len(row) for row, b in zip(c, BLINDED)]

    blinded_rep = BLINDED[REPORTED]
    t11 = {s: {"exposure_per_period": {p: world[s][p]["exposure"][REPORTED].tolist() for p in PERIODS},
               "average_flux": [None if (b and s == "helium") else x for x, b in zip(res[(s, "average")][REPORTED].tolist(), blinded_rep)],
               "average_truth": world[s]["average_truth"][REPORTED].tolist(),
               "equal_split_exposure_rel_error": [round(float(v), 4) + 0.0 for v in world[s]["equal_split_exposure"][REPORTED] / sum(world[s][p]["exposure"] for p in PERIODS)[REPORTED] - 1]}
           for s in SPECIES}
    passes = {
        "asimov_closure": max(asimov_dev.values()) < CRITERIA["asimov_max_rel_dev"],
        "toy_mean_pull": all(abs(v) < CRITERIA["toy_mean_pull_abs"] for s in toys.values() for v in s["mean_per_bin"]),
        "toy_pull_width": all(CRITERIA["toy_pull_width"][0] < v < CRITERIA["toy_pull_width"][1] for s in toys.values() for v in s["width_per_bin"]),
        "ratio_reference_agreement": all(r["max_rel_difference"] < CRITERIA["reference_rel_agreement"] for r in refs.values()),
        "background_asimov_closure": bkg_asimov_dev < CRITERIA["background_asimov_max_rel_dev"],
        "background_validation_closure": all(abs(v["total_pull"]) < CRITERIA["validation_band_abs_pull"]
                                             and v["p_value"] > CRITERIA["validation_band_chi2_p_min"] for v in vclos.values()),
        "blinded_figures": fig_check["status"] == "pass",
        "response_checks": all(v != "fail" for v in resp_checks.values()),
        "covariance_checks": all(v != "fail" for v in cov_checks.values()),
        "contracts": all(c["ok"] for c in contract.values()),
    }
    review = review_spec(docs["measurement_spec"], Vocabulary.with_profiles([PROFILE]), out)
    passes["review_verdict"] = review["verdict"] == "acceptable-with-open-inputs"
    results = {
        "label": "SYNTHETIC: invented inputs; describes no experiment",
        "review": review,
        "seed": args.seed, "toys": args.toys, "criteria": CRITERIA, "pass": passes,
        "edges_gv": EDGES.tolist(), "reported_bins": [REPORTED.start, REPORTED.stop],
        "published_helium_and_ratio_bins": [PUBLISHED.start, PUBLISHED.stop],
        "synthetic_inputs": {"species": SPECIES, "periods": PERIODS, "cutoff_factor": CUTOFF_FACTOR, "resolution": RESOLUTION,
                             "n_ctrl_trigger": N_CTRL_TRIGGER, "n_ctrl_selection": N_CTRL_SELECTION,
                             "charge_tail": CHARGE_TAIL, "charge_bands": {"helium_window": HE_WINDOW, "sideband": SIDEBAND,
                                                                          "validation_band": VALIDATION_BAND},
                             "transfer_factor_rel_uncertainty": TF_REL},
        "blinding": {"region": BLIND, "blinded_bins": [int(j) for j in np.flatnonzero(BLINDED)], "applies_to": "helium signal region, both periods",
                     "released_helium_histograms": {p: f.relative_to(out).as_posix() for p, f in released.items()},
                     "procedure": "custodian masks the helium signal-region count (mask_blinded_bins.py); the analysis fills the "
                                  "blinded bin with the simulated helium expectation and zero variance; helium and ratio values "
                                  "in that bin are null in every output; proton counts and charge sidebands are open",
                     "figure_check": fig_check, "unblinded": False},
        "observed_counts": {f"{s}/{p}": (sim["counts"][(s, p)] if s == "helium" else sim["counts"][(s, p)].tolist())
                            for s in SPECIES for p in PERIODS},
        "background": {"transfer_factor_window": TF_SR, "transfer_factor_validation_band": TF_VR,
                       "sideband_counts": {p: sim["sideband"][p].tolist() for p in PERIODS},
                       "estimate_window": {p: pub(res[("helium", p)]["background_estimate"]) for p in PERIODS},
                       "expected_window": {p: world["helium"][p]["leak"]["window"].tolist() for p in PERIODS},
                       "asimov_closure_max_rel_dev": bkg_asimov_dev, "validation_closure": vclos},
        "flux": {f"{s}/{p}": {"values": pub(res[(s, p)]["flux"], s), "truth": world[s][p]["truth_flux"].tolist(),
                              "covariance": {k: pub_cov(res[(s, p)][k], s) for k in ("stat", "trigger", "selection", "background", "total")}}
                 for s in SPECIES for p in PERIODS},
        "ratio": {p: {"values": pub(res[("ratio", p)][0]), "truth": world["ratio_truth"][p].tolist(),
                      "covariance": pub_cov(res[("ratio", p)][1])} for p in PERIODS},
        "time_average_T11": t11,
        "asimov_closure_max_rel_dev": asimov_dev, "toy_closure": toys, "ratio_reference_T10": refs,
        "response_validation": resp_checks, "covariance_validation": cov_checks, "contract_validation": contract,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    write_report(out, results)
    digest = hashlib.sha256((out / "results.json").read_bytes()).hexdigest()
    print(json.dumps({"pass": passes, "results_sha256": digest}, indent=1))
    return 0 if all(passes.values()) else 1


def write_report(out: Path, r: dict) -> None:
    def fmt(v):
        return ", ".join(f"{x:.4g}" for x in v)
    vband = "; ".join(f"{p}: observed {v['total_observed']:.0f}, predicted {v['total_predicted']:.1f}, pull {v['total_pull']:.2f}, "
                      f"chi2 {v['chi2']:.1f} / {v['ndf']}" for p, v in r["background"]["validation_closure"].items())
    lines = [
        "# Path A report: synthetic flux and correlated He/p ratio (SYNTHETIC)",
        "",
        "**Status: synthetic.** All inputs are invented (see `results.json` → `synthetic_inputs`). Nothing here is an AMS-02 "
        "measurement, performance figure or result. The profile supplies conventions (rigidity R = pc/(Ze) in GV, flux at the "
        "top of the instrument, exposure normalization) and one documented practice: R > 1.2 × maximum cutoff, documented for "
        "the proton flux analysis [Documented, ams02:C31] and applied to helium here as a [Proposal].",
        "",
        f"Reproduce: `python3 examples/ams-flux-ratio/run.py --toys {r['toys']} --seed {r['seed']}` (from the plugin root, D5 environment).",
        "",
        "Validate the spec (its level is a profile term, so the profile vocabulary is needed): bind `experiment:ams-02` in a "
        "`hep-research.project.json` outside the plugin and run "
        "`python3 \"<plugin root>/contracts/validate.py\" examples/ams-flux-ratio/output/artifacts/measurement_spec.json "
        "--profiles-from <your project>/hep-research.project.json`.",
        "",
        "## Pre-declared criteria and outcome",
        "",
        "| Check | Criterion | Result |",
        "|---|---|---|",
        f"| Asimov closure (flux, ratio, period average) | max relative deviation < {r['criteria']['asimov_max_rel_dev']} | {'pass' if r['pass']['asimov_closure'] else 'FAIL'} (max {max(r['asimov_closure_max_rel_dev'].values()):.2e}) |",
        f"| Toy closure, mean pull per bin | abs < {r['criteria']['toy_mean_pull_abs']} | {'pass' if r['pass']['toy_mean_pull'] else 'FAIL'} |",
        f"| Toy closure, pull width per bin | in {tuple(r['criteria']['toy_pull_width'])} | {'pass' if r['pass']['toy_pull_width'] else 'FAIL'} |",
        f"| Ratio sigma vs independent propagation (T10) | relative difference < {r['criteria']['reference_rel_agreement']} | {'pass' if r['pass']['ratio_reference_agreement'] else 'FAIL'} |",
        f"| Background estimate, Asimov closure | TF x expected sideband = expected window background, relative < {r['criteria']['background_asimov_max_rel_dev']} | {'pass' if r['pass']['background_asimov_closure'] else 'FAIL'} (max {r['background']['asimov_closure_max_rel_dev']:.1e}) |",
        f"| Background estimate, validation band 1.6 <= Q < 1.7, per period | abs total pull < {r['criteria']['validation_band_abs_pull']} and chi2 p > {r['criteria']['validation_band_chi2_p_min']} (bins with >= {r['criteria']['validation_band_min_predicted']:g} predicted) | {'pass' if r['pass']['background_validation_closure'] else 'FAIL'} ({vband}) |",
        f"| Figures drawn outside the blinded range (core.blinding.check_figure) | no artist inside | {'pass' if r['pass']['blinded_figures'] else 'FAIL'} |",
        f"| Response and covariance validators (core.stats) | no failure | {'pass' if r['pass']['response_checks'] and r['pass']['covariance_checks'] else 'FAIL'} |",
        f"| Contract artifacts (profile vocabulary) | all valid | {'pass' if r['pass']['contracts'] else 'FAIL'} |",
        "",
        "The covariance validator warns that the trigger and background blocks have rank 1. That is expected: a single "
        "per-period trigger efficiency, and a single transfer factor, scale every bin together, so these blocks are fully "
        "correlated by construction.",
        "",
        "## Background: Z=1 charge tail in the helium window (synthetic)",
        "",
        f"A synthetic {r['synthetic_inputs']['charge_tail']['fraction']:.0%} of the selected Z=1 events has a charge estimator Q above "
        f"{r['synthetic_inputs']['charge_tail']['start']} with an exponential tail (slope {r['synthetic_inputs']['charge_tail']['slope']}); "
        "the part inside the helium window 1.7 <= Q < 2.5 is a background to helium. Per reco rigidity bin and period it is "
        f"estimated as TF x the counts of the helium-free sideband 1.3 <= Q < 1.6, TF = {r['background']['transfer_factor_window']:.4f} "
        "from the synthetic tail shape (10% fully correlated uncertainty), and subtracted before the helium unfolding. The "
        "validation band 1.6 <= Q < 1.7 (TF = "
        f"{r['background']['transfer_factor_validation_band']:.4f}) checks the extrapolation on data. The proton flux is not affected.",
        "",
        "## Blinding (synthetic policy)",
        "",
        "The helium signal-region count in the bin 60-100 GV is blinded in both periods. A custodian step "
        "(`skills/hep-measurement/scripts/mask_blinded_bins.py`) masks it before the analysis reads the histograms; the released "
        f"files are {', '.join('`' + f + '`' for f in r['blinding']['released_helium_histograms'].values())}. The unfolding fills the "
        "blinded bin with the simulated helium expectation and zero variance, so no published number depends on its count. "
        "The helium flux, the He/p ratio and the period average are null in that bin in `results.json`, the dataset records stop "
        "at 60 GV, and the figures show 2-60 GV. Proton counts and the charge sidebands stay open. Nothing here unblinds; that "
        "is done by an authorized person outside the agent session.",
        "",
        "## What the chain does",
        "",
        "Per species and synthetic period: selected truth counts = ∫Φ dR × acceptance × livetime × cutoff fraction × trigger "
        "efficiency × selection efficiency; rigidity migration (2% core resolution in curvature, a 2% tail five times wider) "
        "gives Poisson reco counts; a full-rank weighted least-squares unfolding (`core.stats.unfolding_diagnostics.linear_matrix`, "
        "no regularization) returns selected truth counts; dividing by the efficiencies, the exposure and the bin width gives the "
        "bin-averaged flux. The first and last bins (1.5-2 and 100-150 GV) absorb migration and are not reported. For helium "
        "the charge-tail background is subtracted from the reco counts first.",
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
    lines += ["", "## Toy closure", "", f"{r['toys']} pseudo-experiments (seed {r['seed'] + 1}) regenerate the counts, the control samples, the charge-tail "
              "counts and the transfer factor, and apply the same blinded procedure; helium and ratio pulls cover 2-60 GV.", "",
              "| Quantity | mean pull per bin | pull width per bin |", "|---|---|---|"]
    for k, v in r["toy_closure"].items():
        lines.append(f"| {k} | {fmt(v['mean_per_bin'])} | {fmt(v['width_per_bin'])} |")
    lines += ["", "## Limitations (by construction of this example)", "",
              "- Acceptance and the response are assumed exactly known; no finite-MC or acceptance systematic is modeled.",
              "- The only background is the synthetic Z=1 charge tail; its charge shape factorizes from rigidity by construction, so "
              "one transfer factor serves every bin. No charge confusion or fragmentation is modeled; the synthetic truth exists "
              "only in 1.5-150 GV.",
              "- The response uses the generated spectral shape inside each bin, so model dependence of the unfolding is not studied.",
              "- Acceptance, efficiencies and cutoff fractions are constant within a bin by construction.",
              "- Passing these checks shows the chain is internally consistent on synthetic data; it says nothing about any real detector.",
              "", "Figures: `flux_per_period.png`, `ratio_per_period.png`. Artifacts: `artifacts/*.json` (all status `synthetic`).", ""]
    (out / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())

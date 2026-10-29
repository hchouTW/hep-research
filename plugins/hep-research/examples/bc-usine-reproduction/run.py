#!/usr/bin/env python3
"""Reproduction of Genolini et al. 2019 (arXiv:1904.08917, PRD 99 123028) Table II with USINE through the plugin's
USINE provider and skills/hep-statistics/scripts/propagation_fit.py (cr-propagation work package F1).

OBSERVED data: the AMS-02 B/C ratio (PRL 117, 231102, 2016; 67 rigidity bins 1.92-2600 GV, data period 2011-05 to
2016-05; profile experiment:ams-02 dataset record boron-to-carbon-2016), read in place from the table with the
per-source uncertainty breakdown that USINE V3.5 ships (HEP_USINE_DATA/CRDATA_COVARIANCE/ERRORS/
AMS02_BC_R__PRL117_231102_2016.txt: rigidity bin, value, stat, background, acceptance, unfolding, scale, total
systematic). USINE is GPL-2.0: no USINE file and no copy of one is committed; this script reads them where they lie
and writes everything it makes to --out (outside the repository).

Covariance (model-supplied; none is published): built with build_covariance.py from that breakdown, one block per
source, with the correlation structure of the covariance USINE ships for these data (CRDATA_COVARIANCE/
cov_AMS02_201105201605__BC_R.dat, "a toy-model for the covariance of AMS02 B/C(R) data ... courtesy of L. Derome",
USINE doc/input_cr_data_cov.rst; the covariance the initialisation files of Genolini et al. 2019 name): statistical
uncorrelated; background, acceptance and rigidity scale fully correlated; unfolding with the correlation length
UNF_LENGTH in ln R (the 'length' model exp(-|ln R_i - ln R_j| / length), fitted here to the unfolding block of that
file). Correlation-length alternatives (r3 P9) and that file's exact unfolding correlation ('matrix' model) are model
alternatives, fitted separately, never combined.

Model families (from the paper's initialisation files and fit outputs shipped with USINE V3.5,
doc/DocFiles/2019-Genolini-benchmarks-BC.tar.gz; numbers only): Model1DKisoVc, L = 10 kpc, h = 100 pc, no local
bubble, K = beta^eta K0 R^delta x low break x high break, Kpp of USINE's files, gas HI 0.867, HII 0.033, He 0.1 cm^-3,
ionization, Coulomb and adiabatic losses, BETA decay on, electron capture off, GALPROP opt12 production and
Tripathi99+Coste12 inelastic cross sections (USINE's files), source spectrum q beta^-1 R^-alpha with alpha fixed per
family at the paper's value, sources normalised to data, 13C, 15N, 17O, 18O pure secondaries, network 1H-58Fe.
  BIG     D0_cm2_s, delta, V_A_kms, V_c_kms, R_break_gv, delta_below free (eta = 1, low break s = 0.05)
  SLIM    D0_cm2_s, delta, R_break_gv, delta_below free (eta = 1, V_A = V_c = 0, low break s = 0.05)
  QUAINT  D0_cm2_s, delta, V_A_kms, V_c_kms, eta free (no low break)
Nuisances of the paper, as provider parameters with Gaussian priors (the 'initial setting' of the fit outputs):
phi_2011_2016_gv 0.73 +- 0.10 GV (force field, applied by USINE per isotope), xs_norm_12C_H_11B 1.10 +- 0.12,
xs_slope_12C_H_11B 0.03 +- 0.15 (threshold 8 GeV/n fixed). The high break (Rbreak, Deltabreak, sbreak; nuisances in
the paper with priors that the shipped files do not determine) is fixed at each family's published best fit, with
Deltabreak kept when delta moves (usine_provider.py). Start points: the published best fits.

Stages (--stages): data (dataset-record, covariance, CRDB cross-check marked secondary), start (chi2 of the published
best fits with this covariance and with USINE's own covariance file), fit (one propagation_fit run per family),
compare (the D9 table of VALIDATION.md CRPROP-F1), attribution (linear response of delta and K10 to configuration
differences from the paper that one provider run shows, with the Jacobian from the cached Fisher points). Criteria: VALIDATION.md, section CRPROP-F1 (written before any fit).

Usage (from the plugin root, with HEP_USINE_BIN and HEP_USINE_DATA set):
  python3 examples/bc-usine-reproduction/run.py --out DIR [--stages data,start,fit,compare] [--families BIG,SLIM,QUAINT]
      [--cache-dir DIR] [--max-evaluations 600] [--jobs 3]
Exit 0 when the stages run (compare: every family within D9), 1 a failed stage or a D9 miss, 3 USINE or numpy missing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN))

FIT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "propagation_fit.py"
BUILD_COV = PLUGIN / "skills" / "hep-statistics" / "scripts" / "build_covariance.py"
VALIDATE = PLUGIN / "contracts" / "validate.py"
PROVIDER = "usine"
# the provider's current version, read from its declaration (a run asks the registered version); the committed F1
# record keeps the version that produced it (usine 0.2.0) as history (cache-key migration, VALIDATION CRPROP-L2)
PROVIDER_VERSION = next(d.get("version") for d in json.loads((PLUGIN / "adapters" / "cr-propagation" / "adapter.json")
                                                             .read_text(encoding="utf-8"))["provider"]
                        if d["id"] == PROVIDER)
PERIOD = "2011_2016"
PHI = f"phi_{PERIOD}_gv"
ERRORS_FILE = "CRDATA_COVARIANCE/ERRORS/AMS02_BC_R__PRL117_231102_2016.txt"
COV_FILE = "CRDATA_COVARIANCE/cov_AMS02_201105201605__BC_R.dat"
DATABASE_EXPORT_FILE = "crdata_crdb20170523.dat"
SOURCES = ("stat", "back", "acc", "unf", "scale")
KPC_CM = 648000.0 / math.pi * 1.495978707e13 * 1e3          # IAU parsec (r3 P1)
KPC2_PER_MYR_CM2_S = KPC_CM ** 2 / (1e6 * 365.25 * 86400.0)  # Julian year

# Published values (r3 card F1; VALIDATION.md CRPROP-F1): delta (central, -sigma, +sigma), K10 (central) and the
# 1-sigma of log10 K10 from the authors' fit covariance
PUBLISHED = {"BIG": {"delta": (0.48, 0.03, 0.04), "K10": 0.30, "s_log10_K10": 0.0520},
             "SLIM": {"delta": (0.51, 0.02, 0.02), "K10": 0.28, "s_log10_K10": 0.0352},
             "QUAINT": {"delta": (0.45, 0.02, 0.05), "K10": 0.33, "s_log10_K10": 0.0463}}
# The paper's best fits (fit_result.out of each family; log10 K0 in kpc^2/Myr) and fixed inputs
PAPER_FITS = {
    "BIG": {"delta": 0.4823171, "log10_K0": -1.000069, "V_A_kms": 66.78604, "V_c_kms": 0.01168883,
            "R_break_gv": 3.452812, "deltalow": 0.6911, "eta": 1.0, "alpha": 2.348466,
            "high": (2.392106, 0.1848917, 0.04073533), "phi": 0.7310421, "norm": 1.1162, "slope": 0.1240419,
            "chi2": 61.71249, "dof": 61},
    "SLIM": {"delta": 0.5089642, "log10_K0": -1.059793, "V_A_kms": 0.0, "V_c_kms": 0.0,
             "R_break_gv": 4.40674, "deltalow": 0.8701146, "eta": 1.0, "alpha": 2.33381,
             "high": (2.37548, 0.1896237, 0.04043187), "phi": 0.7341483, "norm": 1.132545, "slope": 0.003710011,
             "chi2": 61.79595, "dof": 63},
    "QUAINT": {"delta": 0.4503136, "log10_K0": -0.9282009, "V_A_kms": 101.294, "V_c_kms": 0.1034788,
               "R_break_gv": None, "deltalow": None, "eta": -0.09120126, "alpha": 2.360299,
               "high": (2.431985, 0.1708353, 0.03604498), "phi": 0.7248042, "norm": 1.108318, "slope": 0.1561423,
               "chi2": 62.09285, "dof": 62},
}
FREE = {"BIG": ["D0_cm2_s", "delta", "V_A_kms", "V_c_kms", "R_break_gv", "delta_below"],
        "SLIM": ["D0_cm2_s", "delta", "R_break_gv", "delta_below"],
        "QUAINT": ["D0_cm2_s", "delta", "V_A_kms", "V_c_kms", "eta"]}
# declared variants (VALIDATION CRPROP-F1, dispatch 2): name -> (paper family, parameters fixed in addition)
VARIANTS = {"QUAINT-Vc0": ("QUAINT", {"V_c_kms": 0.0})}
# 0.3 x the conditional sigma (1/sqrt of the precision matrix diagonal) of the paper's BIG fit covariance
# (fit_covmatrix.out), in this fit's coordinates (ln D0, delta_below = -deltalow): restart steps for BIG, which has no
# Fisher matrix of its own (its first pass stopped on the budget)
BIG_RESTART_STEPS = {"delta": 0.00143, "D0_cm2_s": 0.00595, "V_A_kms": 1.88, "V_c_kms": 0.0485, "R_break_gv": 0.0854,
                     "delta_below": 0.108, "phi_2011_2016_gv": 0.0239, "xs_norm_12C_H_11B": 0.0122,
                     "xs_slope_12C_H_11B": 0.0112}
NUISANCES = {PHI: (0.73, 0.10), "xs_norm_12C_H_11B": (1.10, 0.12), "xs_slope_12C_H_11B": (0.03, 0.15)}
XS_THRESHOLD = 8.0
# difference steps in the fit coordinate: about a quarter of each published sigma, far above USINE's 6-digit noise
# (the verdict's Hessian is a second difference of -ln L, whose noise with chi2 ~ 60 is about 1e-3)
STEPS = {"D0_cm2_s": 0.03, "delta": 0.006, "V_A_kms": 3.0, "V_c_kms": 0.5, "R_break_gv": 0.1, "delta_below": 0.05,
         "eta": 0.05, PHI: 0.01, "xs_norm_12C_H_11B": 0.02, "xs_slope_12C_H_11B": 0.01}
SCALES = {"D0_cm2_s": "log"}
UNF_LENGTH = None   # set by stage data from the shipped unfolding correlation (recorded in data/covariance-model.json)


def usine_data() -> Path:
    path = os.environ.get("HEP_USINE_DATA")
    if not path or not Path(path).is_dir():
        raise SystemExit(json.dumps({"status": "missing-dependency", "error": "set HEP_USINE_DATA (USINE's inputs "
                                     "folder); the data and the covariance structure are read from it in place"}))
    return Path(path)


def read_breakdown(data_dir: Path):
    rows = [ln.split() for ln in (data_dir / ERRORS_FILE).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]
    rows = [[float(x) for x in r] for r in rows]
    edges = [rows[0][0]] + [r[1] for r in rows]
    if any(abs(a[1] - b[0]) > 1e-9 for a, b in zip(rows, rows[1:])):
        raise SystemExit("the rigidity bins of the breakdown table are not contiguous")
    cols = {name: [r[3 + k] for r in rows] for k, name in enumerate(SOURCES)}
    return edges, [r[2] for r in rows], cols, [r[8] for r in rows]


def read_usine_covariance(data_dir: Path) -> dict:
    """USINE's relative covariance per error type (name -> matrix)."""
    blocks, cur, rows = {}, None, []
    for ln in (data_dir / COV_FILE).read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("ErrorType:"):
            if cur and rows:
                blocks[cur] = rows
            cur, rows = s.split(":", 1)[1].strip(), []
            continue
        rows.append([float(x) for x in s.split()])
    if cur and rows:
        blocks[cur] = rows
    return blocks


def fit_unf_length(np, rel_unf, centers) -> tuple[float, float]:
    """Least-squares length of exp(-|ln R_i - ln R_j| / length) against the shipped unfolding correlation."""
    from scipy.optimize import minimize_scalar
    m = np.asarray(rel_unf)
    sig = np.sqrt(np.diag(m))
    corr = m / np.outer(sig, sig)
    d = np.abs(np.log(centers)[:, None] - np.log(centers)[None, :])
    res = minimize_scalar(lambda ell: float(np.sum((np.exp(-d / ell) - corr) ** 2)), bounds=(1e-3, 1e2),
                          method="bounded")
    rms = math.sqrt(res.fun / (len(centers) * (len(centers) - 1)))
    return float(res.x), rms


def covariance_sources(values, cols, unf_model: dict) -> list[dict]:
    return [{"name": "stat", "model": "none", "sigma": cols["stat"]},
            {"name": "back", "model": "full", "sigma": cols["back"]},
            {"name": "acc", "model": "full", "sigma": cols["acc"]},
            {"name": "scale", "model": "full", "sigma": cols["scale"]},
            dict({"name": "unf", "sigma": cols["unf"]}, **unf_model)]


def build_cov(work: Path, tag: str, values, centers, sources) -> Path:
    inp = work / f"covariance-{tag}.input.json"
    inp.write_text(json.dumps({"values": values, "x": centers, "sources": sources, "units": "1"}) + "\n")
    out = work / f"covariance-{tag}.json"
    res = subprocess.run([sys.executable, str(BUILD_COV), "build", "--input", str(inp), "--out", str(out)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"build_covariance failed ({tag}): {res.stdout[-600:]}")
    doc = json.loads(out.read_text())
    doc["origin"] = ("model-supplied: built by build_covariance.py from the published per-source uncertainties with "
                     "stated correlation models (no covariance is published for these data)")
    out.write_text(json.dumps(doc) + "\n")
    return out


def stage_data(out: Path) -> dict:
    import numpy as np
    from contracts import CONTRACTS_VERSION
    global UNF_LENGTH
    data_dir = usine_data()
    work = out / "data"
    work.mkdir(parents=True, exist_ok=True)
    edges, values, cols, syst_total = read_breakdown(data_dir)
    centers = [math.sqrt(a * b) for a, b in zip(edges, edges[1:])]
    shipped = read_usine_covariance(data_dir)
    rel = {k: np.asarray(shipped[k]) for k in SOURCES}
    # the shipped blocks are relative covariances of the same table: check the diagonal against the breakdown
    diag_check = {k: float(np.max(np.abs(np.sqrt(np.diag(rel[k])) - np.asarray(cols[k]) / np.asarray(values))))
                  for k in SOURCES}
    UNF_LENGTH, rms = fit_unf_length(np, rel["unf"], np.asarray(centers))
    nominal = build_cov(work, "nominal", values, centers,
                        covariance_sources(values, cols, {"model": "length", "length": round(UNF_LENGTH, 4)}))
    # USINE's own correlation of the unfolding block, scaled with the data (the paper scales with the model)
    sig = np.sqrt(np.diag(rel["unf"]))
    unf_corr = (rel["unf"] / np.outer(sig, sig)).tolist()
    build_cov(work, "usine-unf-matrix", values, centers, covariance_sources(values, cols, {"model": "matrix",
                                                                                          "correlation": unf_corr}))
    cov_model = {"unf_length_ln_r": round(UNF_LENGTH, 4), "unf_length_fit_rms": rms,
                 "shipped_diagonal_vs_breakdown_max_abs": diag_check,
                 "shipped_correlation": {k: ("none" if k == "stat" else "full" if k != "unf" else "partial")
                                         for k in SOURCES},
                 "total_systematic_vs_quadrature_max_rel": float(np.max(np.abs(
                     np.asarray(syst_total) / np.sqrt(sum(np.asarray(cols[k]) ** 2 for k in SOURCES[1:])) - 1)))}
    (work / "covariance-model.json").write_text(json.dumps(cov_model, indent=1) + "\n")
    comps = [{"name": "statistical", "kind": "statistical", "correlation": "uncorrelated", "values": cols["stat"]},
             {"name": "systematic: background, acceptance, scale (fully correlated) and unfolding (correlation length "
                      f"{UNF_LENGTH:.4f} in ln R); model-supplied", "kind": "systematic", "correlation": "covariance",
              "covariance_ref": "covariance-systematic.json"}]
    # the systematic block alone (the nominal total minus the statistical diagonal)
    tot = np.asarray(json.loads(nominal.read_text())["matrix"])
    syst = tot - np.diag(np.asarray(cols["stat"]) ** 2)
    (work / "covariance-systematic.json").write_text(json.dumps({
        "labels": [f"bin {i}" for i in range(len(values))], "matrix": syst.tolist(), "kind": "absolute", "units": "1",
        "origin": "model-supplied: background, acceptance and rigidity scale fully correlated, unfolding with "
                  f"exp(-|ln R_i - ln R_j| / {UNF_LENGTH:.4f}), following the correlation structure of the covariance "
                  "USINE V3.5 ships for these data (Derome et al. 2019); build_covariance.py"}) + "\n")
    observable = {
        "quantity": "ratio", "process": "boron to carbon flux ratio of primary and secondary cosmic rays near Earth",
        "species": [{"name": "boron"}, {"name": "carbon"}],
        "variables": [{"name": "rigidity", "unit": "GV", "edges": edges}],
        "phase_space": {"definition": "cosmic rays at the instrument in low Earth orbit; the published fluxes are "
                                      "corrected for acceptance and for the geomagnetic cutoff, so no fiducial "
                                      "restriction remains (the flux near Earth outside the magnetosphere)",
                        "fiducial": False},
        "level": "top-of-instrument",
        "normalization": {"kind": "exposure", "value": "not-applicable",
                          "convention": "ratio of exposure-normalized fluxes; the normalization cancels"},
        "bin_semantics": "bin-integrated", "unit": "1",
        "conventions": {"energy_variable": "rigidity R = pc/(Ze) in GV; the ratio of the boron and carbon fluxes "
                                           "integrated over each rigidity bin (event counts per bin corrected bin by bin)"},
        "validity_range": {"variable": "rigidity", "min": edges[0], "max": edges[-1], "unit": "GV"}}
    record = {
        "contract_version": CONTRACTS_VERSION, "artifact_id": "f1-ams02-boron-to-carbon-2016-observed",
        "artifact_type": "dataset-record",
        "objective": "AMS-02 B/C (PRL 117, 231102, 2016), 67 rigidity bins, read from the per-source breakdown table "
                     "shipped with USINE V3.5 (a transcription of the paper's table), for the F1 reproduction",
        "bindings": {"experiments": [{"profile": "experiment:ams-02", "version": "2.0.0"}], "theory": []},
        "versions": {"plugin": "0.44.0", "contracts": CONTRACTS_VERSION, "profiles": {"experiment:ams-02": "2.0.0"}},
        "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-28", "evidence_ids": ["ams02:S10"]},
        "inputs": [], "outputs": [], "status": ["observed"],
        "unresolved_inputs": ["values transcribed by USINE's authors (GPL-2.0 file, read in place): compared with the "
                              "CRDB export shipped with USINE (secondary), not with the paper's table itself"],
        "extension": {"dataset_id": "ams02:boron-to-carbon-2016", "source_evidence_ids": ["ams02:S10"],
                      "observable": observable,
                      "data": {"edges": edges, "values": values, "unit": "1", "uncertainties": comps},
                      "covariance": {"status": "present", "ref": "covariance-nominal.json",
                                     "note": "model-supplied (no covariance is published): build_covariance.py, see "
                                             "covariance-model.json; correlation-length alternatives are model "
                                             "alternatives (r3 P9)"},
                      "period": {"start": "2011-05-19", "end": "2016-05-26", "evidence": "ams02:S10 (profile "
                                 "dataset record boron-to-carbon-2016, claim C32)"},
                      "status": "published", "experiment_profile": "experiment:ams-02",
                      "conditions": "data period 2011-05/2016-05 (one force-field potential)"}}
    (work / "bc-observed.json").write_text(json.dumps(record, indent=1) + "\n")
    val = subprocess.run([sys.executable, str(VALIDATE), str(work / "bc-observed.json")], capture_output=True, text=True)
    crdb = database_crosscheck(data_dir, edges, values, cols, syst_total)
    (work / "crdb-crosscheck.json").write_text(json.dumps(crdb, indent=1) + "\n")
    return {"record": str(work / "bc-observed.json"), "validate_exit": val.returncode, "validate": val.stdout[-400:],
            "covariance_model": cov_model, "crdb": {k: crdb[k] for k in ("rows", "matched", "max_rel_value",
                                                                          "max_rel_stat", "max_rel_syst")}}


def database_crosscheck(data_dir: Path, edges, values, cols, syst_total) -> dict:
    """The AMS02 B/C rows of the CRDB export shipped with USINE (CRDB 2017/05/23), each marked secondary, against the
    table used here."""
    rows = []
    for ln in (data_dir / DATABASE_EXPORT_FILE).read_text(encoding="utf-8", errors="replace").splitlines():
        p = ln.split()
        if len(p) > 11 and p[0] == "B/C" and p[1].startswith("AMS02(2011/05-2016/05)") and p[2] == "R":
            rows.append({"role": "secondary", "source": f"CRDB export {DATABASE_EXPORT_FILE} (USINE V3.5 inputs), {p[1]}",
                         "e_low": float(p[4]), "e_high": float(p[5]), "value": float(p[6]), "stat": float(p[8]),
                         "syst": float(p[10])})
    matched, dv, ds, dy = 0, 0.0, 0.0, 0.0
    for r in rows:
        k = next((i for i in range(len(values)) if abs(edges[i] - r["e_low"]) < 1e-6 * edges[i]
                  and abs(edges[i + 1] - r["e_high"]) < 1e-6 * edges[i + 1]), None)
        r["matched_bin"] = k
        if k is None:
            continue
        matched += 1
        dv = max(dv, abs(r["value"] / values[k] - 1))
        ds = max(ds, abs(r["stat"] / cols["stat"][k] - 1))
        dy = max(dy, abs(r["syst"] / syst_total[k] - 1))
    return {"label": "secondary: a cross-check only, never fitted", "rows": len(rows), "matched": matched,
            "max_rel_value": dv, "max_rel_stat": ds, "max_rel_syst": dy, "table": rows}


def base_family(family: str) -> str:
    """The paper family of a family, a declared variant or a tagged fit folder name ('QUAINT-Vc0-papercov')."""
    hits = [v for v in VARIANTS if family == v or family.startswith(v + "-")]
    return VARIANTS[max(hits, key=len)][0] if hits else family.split("-")[0]


def free_of(family: str) -> list:
    return [n for n in FREE[base_family(family)] if n not in VARIANTS.get(family, ("", {}))[1]]


def transport(family: str) -> dict:
    family = base_family(family)
    f = PAPER_FITS[family]
    log10_rb, d_break, s_break = f["high"]
    breaks = []
    if f["R_break_gv"] is not None:
        breaks.append({"kind": "low", "R_break_gv": f["R_break_gv"], "delta_below": -f["deltalow"], "s": 0.05,
                       "s_convention": "usine"})
    breaks.append({"kind": "high", "R_break_gv": 10 ** log10_rb, "delta_above": f["delta"] - d_break, "s": s_break,
                   "s_convention": "usine"})
    return {
        "geometry": {"kind": "slab-1d", "L_kpc": 10.0, "disc_halfwidth_pc": 100.0, "local_bubble_radius_kpc": 0.0},
        "diffusion": {"form": "beta^eta (R/R0)^delta with smooth breaks", "D0_cm2_s": 10 ** f["log10_K0"]
                      * KPC2_PER_MYR_CM2_S, "R0_gv": 1.0, "eta": f["eta"], "delta": f["delta"], "breaks": breaks},
        "reacceleration": {"V_A_kms": f["V_A_kms"], "zone": "thin-disc", "relation": "Seo-Ptuskin 1994", "w": 1.0},
        "convection": {"V_c_kms": f["V_c_kms"], "dVc_dz_kms_per_kpc": 0.0},
        "losses": ["ionization", "coulomb", "adiabatic"],
        "decay": {"enabled": True, "lorentz_dilation": True, "ec_treatment": "fully-stripped"},
        "gas": {"model": "uniform in the thin disc, n_HI = 0.867 cm^-3, n_HII = 0.033 cm^-3, n_H2 = 0 cm^-3",
                "He_to_H_number": 0.1 / 0.9},
        "sources": {"spatial": "thin disc (1D model)",
                    "injection": [{"species_group": "all primaries", "gamma": f["alpha"], "eta": -1.0, "breaks": []}],
                    "abundances": "data-normalised usine:crdata_crdb20170523.dat H,He:PAMELA@20;C,N,O,F,Ne,Na,Mg,Al,"
                                  "Si,P,S,Cl,Ar,K,Ca,Sc,Ti,V,Cr,Mn,Fe:HEAO@10.6 pure:13C,15N,17O,18O"},
        "cross_sections": {"production_set": "usine:XS_NUCLEI/sigProdGALPROP17_OPT12.dat",
                           "inelastic_set": "usine:XS_NUCLEI/sigInelTripathi99+Coste12.dat"},
        "species": {"network_top": "Fe-58", "isotopic": True},
        "family": f"{family} (Genolini et al. 2019)",
        "free": FREE[family],
    }


def paper_point(family: str) -> dict:
    extra = VARIANTS.get(family, ("", {}))[1]
    family = base_family(family)
    f = PAPER_FITS[family]
    pt = {"D0_cm2_s": 10 ** f["log10_K0"] * KPC2_PER_MYR_CM2_S, "delta": f["delta"], "L_kpc": 10.0,
          PHI: f["phi"], "xs_norm_12C_H_11B": f["norm"], "xs_slope_12C_H_11B": f["slope"],
          "xs_threshold_12C_H_11B_gev": XS_THRESHOLD}
    if family in ("BIG", "QUAINT"):
        pt.update(V_A_kms=f["V_A_kms"], V_c_kms=f["V_c_kms"])
    else:
        pt.update(V_A_kms=0.0, V_c_kms=0.0)
    if family == "QUAINT":
        pt["eta"] = f["eta"]
    else:
        pt.update(eta=1.0, R_break_gv=f["R_break_gv"], delta_below=-f["deltalow"])
    return dict(pt, **extra)


def restart_from(path: Path, fraction: float) -> tuple[dict, dict]:
    """(start values, difference steps) from an earlier fit of the same family: its best fit, and steps of
    fraction / sqrt(F_ii) in the fit coordinates (a fraction of the conditional sigma, so that the verdict's second
    differences stay in the quadratic region; F the earlier fit's Fisher matrix with priors)."""
    fit = json.loads(path.read_text())["fits"][0]
    names = [q["name"] for q in fit["parameters"]]
    fisher = fit["fisher_full"]["matrix"]
    starts = {q["name"]: q["best_fit"] for q in fit["parameters"]}
    steps = {n: float(f"{fraction / math.sqrt(fisher[i][i]):.3g}") for i, n in enumerate(names)}
    return starts, steps


def config(family: str, record: dict, conditions: dict, cov_alt: bool, restart: tuple | None = None) -> dict:
    pt = paper_point(family)
    free = free_of(family) + list(NUISANCES)
    starts, steps = restart if restart else ({}, {})
    params = {}
    for n in free:
        params[n] = {"start": starts.get(n, pt[n]), "scale": SCALES.get(n, "linear"), "step": steps.get(n, STEPS[n])}
        if n in NUISANCES:
            params[n]["prior"] = {"mean": NUISANCES[n][0], "sigma": NUISANCES[n][1]}
    fixed = {k: v for k, v in pt.items() if k not in free}
    cfg = {"provider": {"id": PROVIDER, "version": PROVIDER_VERSION},
           "datasets": [{"name": "bc", "measurement": record, "observable": "B/C", "period": PERIOD}],
           "gate_plan": {"measurement_conditions": conditions,
                         "mappings": [{"key": "energy_variable", "action": "equivalent",
                                       "justification": "both are rigidity bins in GV with the ratio of the "
                                                        "bin-integrated boron and carbon fluxes (r3 P2); the provider "
                                                        "sums isotopes at equal rigidity (P3)"},
                                      {"field": "process", "action": "equivalent",
                                       "justification": "both are the boron to carbon flux ratio near Earth: the "
                                                        "prediction is USINE's force-field modulated B/C, the data "
                                                        "the measured B/C"},
                                      {"field": "phase_space", "action": "equivalent",
                                       "justification": "the published ratio is corrected for acceptance and "
                                                        "geomagnetic cutoff, i.e. the flux near Earth outside the "
                                                        "magnetosphere, which the force-field flux describes"}],
                         "transformations": [{"kind": "level-identification", "owner": "hep-statistics (F1)",
                                              "from": "top-of-atmosphere", "to": "top-of-instrument",
                                              "justification": "a space instrument has no atmosphere above it: the "
                                                               "force-field flux near Earth is the flux at the "
                                                               "instrument (geomagnetic effects are corrected in the "
                                                               "published ratio)"}]},
           "parameters": params, "fixed": fixed,
           "families": [{"name": family, "free": free, "fixed": {}}],
           "optimizer": {"max_iterations": 60, "max_restarts": 0, "seed": 0, "polish_steps": 0},
           "transport": transport(family), "run_record_keys": ["usine_run"]}
    if cov_alt:
        data_dir = usine_data()
        edges, values, cols, _ = read_breakdown(data_dir)
        cfg["covariance_alternatives"] = {"family": family, "dataset": "bc", "source": "unf",
                                          "model": {"sources": covariance_sources(values, cols, {
                                              "model": "length", "length": UNF_LENGTH})},
                                          "lengths": [round(UNF_LENGTH / 2, 4), round(2 * UNF_LENGTH, 4)]}
    return cfg


def registry(out: Path) -> Path:
    reg = out / "registry.json"
    res = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write", str(reg)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"provider registry: {res.stdout[-400:]}")
    return reg


def evaluate(reg: Path, cache: Path, family: str, point: dict, edges) -> dict:
    from core.provider.runner import ProviderRunner
    req = {"protocol": "cr-provider/1", "provider": PROVIDER, "provider_version": PROVIDER_VERSION,
           "points": [point], "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV",
                                               "bins": [[a, b] for a, b in zip(edges, edges[1:])]}],
           "want": ["lis"], "seed": None, "transport": transport(family)}
    with ProviderRunner(str(reg), cache_dir=str(cache), session="serve") as runner:
        resp = runner.evaluate(req)
        stats = dict(runner.stats)
    res = resp["results"][0]
    if res["status"] != "ok":
        raise SystemExit(f"provider failed at the published {family} point: {res.get('reason')} {res.get('detail')}")
    return {"prediction": res["predictions"][0], "labels": res["labels"], "evaluation": res["evaluation"],
            "points_sent": stats.get("points_sent", 0)}


def chi2_of(np, y, mu, cov) -> float:
    r = np.asarray(y) - np.asarray(mu)
    return float(r @ np.linalg.solve(cov, r))


def stage_start(out: Path, families, reg: Path, cache: Path) -> dict:
    import numpy as np
    data_dir = out / "data"
    rec = json.loads((data_dir / "bc-observed.json").read_text())
    y, edges = rec["extension"]["data"]["values"], rec["extension"]["data"]["edges"]
    stat = np.diag(np.asarray(rec["extension"]["data"]["uncertainties"][0]["values"]) ** 2)
    cov_nom = stat + np.asarray(json.loads((data_dir / "covariance-systematic.json").read_text())["matrix"])
    cov_usine_data = np.asarray(json.loads((data_dir / "covariance-usine-unf-matrix.json").read_text())["matrix"])
    shipped = read_usine_covariance(usine_data())
    rel_total = sum(np.asarray(shipped[k]) for k in SOURCES)
    rows, sent = {}, 0
    for fam in families:
        ev = evaluate(reg, cache, fam, paper_point(fam), edges)
        sent += ev["points_sent"]
        mu = np.asarray(ev["prediction"]["values"]["values"])
        pf = PAPER_FITS[fam]
        prior = sum(((paper_point(fam)[n] - m) / s) ** 2 for n, (m, s) in NUISANCES.items())
        rows[fam] = {"chi2_nominal": chi2_of(np, y, mu, cov_nom),
                     "chi2_usine_unf_correlation_data_scaled": chi2_of(np, y, mu, cov_usine_data),
                     "chi2_usine_covariance_model_scaled": chi2_of(np, y, mu, rel_total * np.outer(mu, mu)),
                     "chi2_priors": prior, "paper_chi2_min_including_nuisances": pf["chi2"], "paper_dof": pf["dof"],
                     "prediction_over_data": {"min": float(np.min(mu / np.asarray(y))),
                                              "max": float(np.max(mu / np.asarray(y)))},
                     "substitutes": ev["prediction"]["parameter_point"]["transport_substitutes"],
                     "computational_run_ref": ev["evaluation"]["computational_run_ref"],
                     "values": mu.tolist()}
    (out / "start.json").write_text(json.dumps(rows, indent=1) + "\n")
    return {"families": {f: {k: v for k, v in r.items() if k not in ("substitutes", "values")} for f, r in rows.items()},
            "points_sent": sent}


def run_fit(out: Path, family: str, reg: Path, cache: Path, max_eval: int, cov_alt: bool,
            restart: tuple | None = None, covariance: str = "nominal", tag: str = "") -> subprocess.Popen:
    start = json.loads((out / "start.json").read_text())
    work = out / f"fit-{family}{tag}"
    work.mkdir(parents=True, exist_ok=True)
    conditions = {"transport_substitutes": start.get(family, start[base_family(family)])["substitutes"]}
    if restart:   # the gate sees the start point, whose substitutes name its own values: take them from that point
        point = dict(paper_point(family), **restart[0])
        edges = json.loads((out / "data" / "bc-observed.json").read_text())["extension"]["data"]["edges"]
        conditions = {"transport_substitutes": evaluate(reg, cache, family, point, edges)["prediction"][
            "parameter_point"]["transport_substitutes"]}
    # the dataset-record with its covariance file named by absolute path (references resolve from the config folder)
    record = json.loads((out / "data" / "bc-observed.json").read_text())
    for comp in record["extension"]["data"]["uncertainties"]:
        if comp.get("covariance_ref"):
            comp["covariance_ref"] = str(out / "data" / comp["covariance_ref"])
    record["extension"]["covariance"]["ref"] = str(out / "data" / record["extension"]["covariance"]["ref"])
    if covariance.startswith("model-scaled:"):
        record = model_scaled_record(out, record, covariance.split(":", 1)[1], reg, cache, work)
    cfg = config(family, record, conditions, cov_alt, restart)
    (work / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
    cmd = [sys.executable, str(FIT), "fit", "--input", str(work / "config.json"), "--provider-registry", str(reg),
           "--cache-dir", str(cache), "--out", str(work / "out"), "--max-evaluations", str(max_eval)]
    log = open(work / "fit.log", "w")
    return subprocess.Popen(cmd, stdout=open(work / "result.stdout.json", "w"), stderr=log)


def run_rejudge(out: Path, family: str, reg: Path, cache: Path, max_eval: int, earlier: Path, noise_budget: int,
                polish: int, tag: str = "") -> subprocess.Popen:
    """K1 re-judging (VALIDATION.md CRPROP-K1): the earlier pass's own configuration of the family (start, stated
    steps, priors, no restart), so its least-squares path replays from the cached runs, with the noise-aware verdict
    (optimizer.noise measured within noise_budget evaluations) and polish_steps."""
    cfg = json.loads((earlier / f"fit-{family}" / "config.json").read_text())
    cfg["optimizer"] = dict(cfg["optimizer"], noise={"mode": "measure", "max_evaluations": noise_budget},
                            polish_steps=polish)
    work = out / f"fit-{family}{tag}"
    work.mkdir(parents=True, exist_ok=True)
    (work / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
    cmd = [sys.executable, str(FIT), "fit", "--input", str(work / "config.json"), "--provider-registry", str(reg),
           "--cache-dir", str(cache), "--out", str(work / "out"), "--max-evaluations", str(max_eval)]
    return subprocess.Popen(cmd, stdout=open(work / "result.stdout.json", "w"), stderr=open(work / "fit.log", "w"))


def model_scaled_record(out: Path, record: dict, ref_family: str, reg: Path, cache: Path, work: Path) -> dict:
    """The paper's covariance choice as a declared model alternative: USINE's shipped relative covariance (all five
    error types) times the prediction of ref_family's best fit (USINE's IsModelOrDataForRelCov true), held fixed
    during the fit (one step of the paper's model-dependent scaling)."""
    import numpy as np
    shipped = read_usine_covariance(usine_data())
    rel = sum(np.asarray(shipped[k]) for k in SOURCES)
    edges = record["extension"]["data"]["edges"]
    fit = json.loads((out / f"fit-{ref_family}" / "out" / "result.json").read_text())["fits"][0]
    point = dict(fit["fixed"], **{q["name"]: q["best_fit"] for q in fit["parameters"]})
    mu = np.asarray(evaluate(reg, cache, ref_family, point, edges)["prediction"]["values"]["values"])
    path = work / "covariance-model-scaled.json"
    path.write_text(json.dumps({"labels": [f"bin {i}" for i in range(len(mu))], "matrix": (rel * np.outer(mu, mu)).tolist(),
                                "kind": "absolute", "units": "1",
                                "origin": f"model-supplied: USINE's shipped relative covariance scaled with the {ref_family} "
                                          "best-fit prediction (the paper's choice), a model alternative (P9)"}) + "\n")
    rec = json.loads(json.dumps(record))
    rec["extension"]["data"]["uncertainties"] = [{"name": "total, USINE relative covariance x model (model-supplied)",
                                                  "kind": "systematic", "correlation": "covariance",
                                                  "covariance_ref": str(path)}]
    rec["extension"]["covariance"] = {"status": "present", "ref": str(path),
                                      "note": "model-supplied: USINE's relative covariance scaled with the model "
                                              f"({ref_family} best fit); a model alternative (P9)"}
    return rec


def restart_cached(out: Path, family: str, pass1: Path | None, fraction: float) -> tuple[dict, dict]:
    """(start, steps) for a restart from the lowest cached point of the family (variant parameters set to their
    fixed values), with steps of fraction x the conditional sigma from the earlier pass's Fisher matrix, or for BIG
    (no reported first pass) BIG_RESTART_STEPS."""
    best = best_cached(out, base_family(family))["point"]
    free = free_of(family) + list(NUISANCES)
    starts = {n: best[n] for n in free}
    earlier = (pass1 / f"fit-{base_family(family)}" / "out" / "result.json") if pass1 else None
    steps = restart_from(earlier, fraction)[1] if earlier and earlier.is_file() else dict(BIG_RESTART_STEPS)
    return starts, {n: steps[n] for n in free}


def k10(d0_cm2_s: float, delta: float) -> float:
    return d0_cm2_s / KPC2_PER_MYR_CM2_S * 10 ** delta


def provider_domain() -> dict:
    adapter = json.loads((PLUGIN / "adapters" / "cr-propagation" / "adapter.json").read_text())
    decls = adapter["provider"] if isinstance(adapter["provider"], list) else [adapter["provider"]]
    return next(d for d in decls if d["id"] == PROVIDER)["domain"]


def _evaluate_many(reg: Path, cache: Path, family: str, points, edges, transport_block=None) -> list:
    from core.provider.runner import ProviderRunner
    out = []
    with ProviderRunner(str(reg), cache_dir=str(cache), session="serve") as runner:
        for pt in points:
            req = {"protocol": "cr-provider/1", "provider": PROVIDER, "provider_version": PROVIDER_VERSION,
                   "points": [pt], "observables": [{"id": "B/C", "axis": "rigidity", "unit": "GV",
                                                    "bins": [[a, b] for a, b in zip(edges, edges[1:])]}],
                   "want": ["lis"], "seed": None, "transport": transport_block or transport(family)}
            res = runner.evaluate(req)["results"][0]
            if res["status"] != "ok":
                raise SystemExit(f"provider failed ({family}): {res.get('reason')} {res.get('detail')}")
            out.append(res["predictions"][0]["values"]["values"])
        sent = int(runner.stats.get("points_sent", 0))
    return out, sent


def variants(family: str, best: dict) -> dict:
    """Configuration differences from the paper that one provider run can show: name -> (point, transport)."""
    out = {}
    t = transport(family)
    si = json.loads(json.dumps(t))
    si["species"]["network_top"] = "Si-30"
    si["sources"]["abundances"] = ("data-normalised usine:crdata_crdb20170523.dat H,He:PAMELA@20;"
                                   "C,N,O,F,Ne,Na,Mg,Al,Si:HEAO@10.6 pure:13C,15N,17O,18O")
    out["network to Si-30 (the SLIM and QUAINT initialisation files)"] = (best, si)
    if family == "SLIM":
        out["V_A 6 km/s, V_c 0.1 km/s (the SLIM initialisation file's fixed values)"] = (
            dict(best, V_A_kms=6.0, V_c_kms=0.1), t)
    return out


def covariance_variants(out: Path, mu0) -> dict:
    """Alternative data covariances (label -> matrix): USINE's shipped unfolding correlation scaled with the data,
    USINE's shipped relative covariance scaled with the model (the paper's IsModelOrDataForRelCov true), and the
    unfolding correlation length halved and doubled (r3 P9)."""
    import numpy as np
    data_dir = out / "data"
    shipped = read_usine_covariance(usine_data())
    edges, values, cols, _ = read_breakdown(usine_data())
    centers = [math.sqrt(a * b) for a, b in zip(edges, edges[1:])]
    length = json.loads((data_dir / "covariance-model.json").read_text())["unf_length_ln_r"]
    alts = {"USINE unfolding correlation, data-scaled":
            np.asarray(json.loads((data_dir / "covariance-usine-unf-matrix.json").read_text())["matrix"]),
            "USINE relative covariance, model-scaled (the paper's choice)":
            sum(np.asarray(shipped[k]) for k in SOURCES) * np.outer(mu0, mu0)}
    for factor in (0.5, 2.0):
        path = build_cov(data_dir, f"unf-length-x{factor:g}", values, centers,
                         covariance_sources(values, cols, {"model": "length", "length": round(length * factor, 4)}))
        alts[f"unfolding correlation length x{factor:g} ({length * factor:.3f} in ln R)"] = np.asarray(
            json.loads(path.read_text())["matrix"])
    return alts


def stage_attribution(out: Path, families, reg: Path, cache: Path) -> dict:
    """Linear response of the best fit to each configuration difference: dtheta = (J^T W J + P)^-1 J^T W dmu, with J
    from the cached evaluations at the best fit +- the stated steps (the Fisher matrix's points: no new run), W the
    inverse data covariance and P the prior Fisher term; dmu = the variant's prediction minus the best fit's."""
    import numpy as np
    rec = json.loads((out / "data" / "bc-observed.json").read_text())
    edges = rec["extension"]["data"]["edges"]
    stat = np.diag(np.asarray(rec["extension"]["data"]["uncertainties"][0]["values"]) ** 2)
    cov = stat + np.asarray(json.loads((out / "data" / "covariance-systematic.json").read_text())["matrix"])
    w = np.linalg.inv(cov)
    rows, sent = {}, 0
    for fam in families:
        path = out / f"fit-{fam}" / "out" / "result.json"
        if not path.is_file():
            continue
        fit = json.loads(path.read_text())["fits"][0]
        names = [q["name"] for q in fit["parameters"]]
        scales = [q["scale"] for q in fit["parameters"]]
        t_hat = [q["best_fit_coordinate"] for q in fit["parameters"]]
        nat = lambda t, sc: math.exp(t) if sc == "log" else float(t)   # noqa: E731
        best = dict(fit["fixed"], **{n: nat(x, sc) for n, x, sc in zip(names, t_hat, scales)})
        domain = provider_domain()
        pts, spans = [best], []
        for i, n in enumerate(names):   # the Fisher matrix's points: t +- step, one-sided at a domain bound
            lo, hi = (math.log(domain[n][e]) if scales[i] == "log" else domain[n][e] for e in ("min", "max"))
            tp, tm = min(t_hat[i] + STEPS[n], hi), max(t_hat[i] - STEPS[n], lo)
            pts += [dict(best, **{n: nat(tp, scales[i])}), dict(best, **{n: nat(tm, scales[i])})]
            spans.append(tp - tm)
        mus, k = _evaluate_many(reg, cache, fam, pts, edges)
        sent += k
        mu0 = np.asarray(mus[0])
        jac = np.array([(np.asarray(mus[1 + 2 * i]) - np.asarray(mus[2 + 2 * i])) / spans[i]
                        for i in range(len(names))]).T
        prior = np.diag([(1.0 / NUISANCES[n][1]) ** 2 if n in NUISANCES else 0.0 for n in names])
        fisher = jac.T @ w @ jac + prior
        gain = np.linalg.solve(fisher, jac.T @ w)
        i_d, i_k = names.index("delta"), names.index("D0_cm2_s")
        fam_rows = {}
        for label, (pt, tr) in variants(fam, best).items():
            (mu_v,), k = _evaluate_many(reg, cache, fam, [pt], edges, tr)
            sent += k
            dtheta = gain @ (np.asarray(mu_v) - mu0)
            # K10 = D0 10^delta: d log10 K10 = d ln D0 / ln 10 + d delta
            fam_rows[label] = {"max_rel_change_of_BC": float(np.max(np.abs(np.asarray(mu_v) / mu0 - 1))),
                               "d_delta": float(dtheta[i_d]),
                               "d_log10_K10": float(dtheta[i_k] / math.log(10) + dtheta[i_d])}
        # covariance alternatives (P9 and the paper's choice): chi2 at this best fit and one Gauss-Newton step under
        # each covariance, with the same Jacobian (no run)
        cov_rows = {}
        for label, cov_alt in covariance_variants(out, mu0).items():
            w_alt = np.linalg.inv(cov_alt)
            r0 = np.asarray(rec["extension"]["data"]["values"]) - mu0
            f_alt = jac.T @ w_alt @ jac + prior
            prior_grad = np.array([-(best[n] - NUISANCES[n][0]) / NUISANCES[n][1] ** 2 if n in NUISANCES else 0.0
                                   for n in names])
            step = np.linalg.solve(f_alt, jac.T @ w_alt @ r0 + prior_grad)
            cov_rows[label] = {"chi2_at_this_best_fit": float(r0 @ w_alt @ r0), "d_delta": float(step[i_d]),
                               "d_log10_K10": float(step[i_k] / math.log(10) + step[i_d])}
        rows[fam] = {"jacobian_points": len(pts), "variants": fam_rows, "covariance_alternatives": cov_rows,
                     "linear_sigma": {"delta": float(math.sqrt(np.linalg.inv(fisher)[i_d, i_d]))}}
    (out / "attribution.json").write_text(json.dumps(rows, indent=1) + "\n")
    return {"families": rows, "points_sent": sent}


def stage_compare(out: Path, families) -> dict:
    table, ok = {}, True
    for fam in families:
        path = out / f"fit-{fam}" / "out" / "result.json"
        if not path.is_file():
            table[fam] = {"status": "not-run"}
            ok = False
            continue
        res = json.loads(path.read_text())
        fit = res["fits"][0]
        p = {q["name"]: q for q in fit["parameters"]}
        delta, d0 = p["delta"]["best_fit"], p["D0_cm2_s"]["best_fit"]
        kk = k10(d0, delta)
        pub = PUBLISHED[base_family(fam)]
        c, lo, hi = pub["delta"]
        d_win = (round(c - lo, 6), round(c + hi, 6))
        k_win = (pub["K10"] * 10 ** -pub["s_log10_K10"], pub["K10"] * 10 ** pub["s_log10_K10"])
        passed = (fit["status"] == "converged" and d_win[0] <= delta <= d_win[1] and k_win[0] <= kk <= k_win[1])
        ok &= passed
        table[fam] = {"status": fit["status"], "delta": delta, "delta_window": d_win, "K10": kk, "K10_window": k_win,
                      "delta_in_window": d_win[0] <= delta <= d_win[1], "K10_in_window": k_win[0] <= kk <= k_win[1],
                      "convergence": {k: fit["convergence"].get(k) for k in ("status", "reasons", "edm")},
                      "points_sent": res["provider_evaluations"]["points_sent"],
                      "chi2": fit["chi2"], "dof": fit["dof"], "D9": "passed" if passed else "missed",
                      "best_fit": {n: q["best_fit"] for n, q in p.items()},
                      "sigma_coordinate": {n: q["sigma_coordinate"] for n, q in p.items()},
                      "paper": PAPER_FITS[base_family(fam)]}
        if "noise" in fit:   # K1 re-judging: the noise-aware verdict (VALIDATION.md CRPROP-K1)
            n = fit["noise"]
            table[fam]["convergence"].update({k: fit["convergence"][k] for k in ("edm_threshold", "polish")
                                              if k in fit["convergence"]})
            table[fam]["noise"] = {k: n.get(k) for k in ("mode", "sigma_m2lnl", "dof", "evaluations", "max_evaluations",
                                                         "k", "edm_threshold", "step_factor", "variance_inflation_sum")}
            table[fam]["polish_steps"] = fit["attempts"][-1].get("polish_steps", 0)
    (out / "compare.json").write_text(json.dumps(table, indent=1) + "\n")
    return {"families": table, "D9_all": ok}


def best_cached(out: Path, family: str) -> dict | None:
    """The lowest -2 ln L (data + priors) among the cached provider results of a family (for a fit that stopped
    before reporting, e.g. on the evaluation budget): its point, chi2 and computational-run reference."""
    import numpy as np
    rec = json.loads((out / "data" / "bc-observed.json").read_text())
    y = np.asarray(rec["extension"]["data"]["values"])
    cov = (np.diag(np.asarray(rec["extension"]["data"]["uncertainties"][0]["values"]) ** 2)
           + np.asarray(json.loads((out / "data" / "covariance-systematic.json").read_text())["matrix"]))
    w = np.linalg.inv(cov)
    best = None
    for path in (out / "cache").glob("*/*.json"):
        res = json.loads(path.read_text()).get("result") or {}
        pt = res.get("point") or {}
        if res.get("status") != "ok" or not pt:
            continue
        fam = "QUAINT" if "R_break_gv" not in pt else ("SLIM" if pt.get("V_A_kms", 0.0) == 0.0 else "BIG")
        if fam != family:
            continue
        r = y - np.asarray(res["predictions"][0]["values"]["values"])
        chi2 = float(r @ w @ r) + sum(((pt[n] - m) / sd) ** 2 for n, (m, sd) in NUISANCES.items() if n in pt)
        if best is None or chi2 < best["chi2"]:
            best = {"chi2": chi2, "point": pt, "computational_run_ref": res["evaluation"]["computational_run_ref"]}
    return best


def stage_record(out: Path, families, record_path: Path, usine_runs: int, rejudge_runs: int | None = None) -> dict:
    """The committed record of the reproduction: numbers only (no data value, no USINE file content)."""
    start = json.loads((out / "start.json").read_text())
    compare = json.loads((out / "compare.json").read_text()) if (out / "compare.json").is_file() else {}
    observed = json.loads((out / "data" / "bc-observed.json").read_text())
    crdb = json.loads((out / "data" / "crdb-crosscheck.json").read_text())
    fams = {}
    for fam in families:
        row = dict(compare.get(fam) or {})
        row.pop("paper", None)
        if row.get("status") in (None, "not-run"):
            cached = best_cached(out, base_family(fam))
            if cached:
                pt = cached["point"]
                kk = k10(pt["D0_cm2_s"], pt["delta"])
                pub = PUBLISHED[base_family(fam)]
                c, lo, hi = pub["delta"]
                row = {"status": "not-reported", "note": "the fit stopped on its evaluation budget before reporting; "
                       "the lowest -2 ln L among its cached provider results", "delta": pt["delta"], "K10": kk,
                       "delta_window": (round(c - lo, 6), round(c + hi, 6)),
                       "K10_window": (pub["K10"] * 10 ** -pub["s_log10_K10"], pub["K10"] * 10 ** pub["s_log10_K10"]),
                       "delta_in_window": c - lo <= pt["delta"] <= c + hi,
                       "K10_in_window": (pub["K10"] * 10 ** -pub["s_log10_K10"] <= kk
                                         <= pub["K10"] * 10 ** pub["s_log10_K10"]),
                       "chi2": cached["chi2"], "best_fit": pt, "computational_run_ref": cached["computational_run_ref"],
                       "D9": "missed (not converged)"}
        attr = out / f"attribution-{fam}.json"
        if attr.is_file():
            row["attribution"] = json.loads(attr.read_text()).get(fam)
        row["published_point_chi2"] = {k: start[base_family(fam)][k] for k in ("chi2_nominal",
                                                                  "chi2_usine_unf_correlation_data_scaled",
                                                                  "chi2_usine_covariance_model_scaled",
                                                                  "paper_chi2_min_including_nuisances", "paper_dof")}
        fams[fam] = row
    doc = {"work_package": "F1", "target": "Genolini et al. 2019 (arXiv:1904.08917) Table II, BIG/SLIM/QUAINT",
           "criteria": "VALIDATION.md CRPROP-F1 (D9)", "provider": {"id": PROVIDER, "version": PROVIDER_VERSION},
           "data": {"artifact_id": observed["artifact_id"], "status": observed["status"], "bins": len(observed["extension"]["data"]
                                                                                              ["values"]),
                    "covariance_note": observed["extension"]["covariance"]["note"],
                    "covariance_model": json.loads((out / "data" / "covariance-model.json").read_text())},
           "crdb_crosscheck": {k: crdb[k] for k in ("label", "rows", "matched", "max_rel_value", "max_rel_stat",
                                                     "max_rel_syst")} | {"row_roles": sorted({r["role"] for r in
                                                                                             crdb["table"]})},
           "families": fams, "usine_runs": usine_runs}
    if rejudge_runs is not None:   # K1: BIG, SLIM, QUAINT-Vc0 re-judged under the noise-aware rule
        doc["rejudge"] = {"work_package": "K1", "rule": "VALIDATION.md CRPROP-K1 (EDM <= max(1e-5, k sigma_noise))",
                          "families": sorted(f for f, r in fams.items() if "noise" in r), "usine_runs": rejudge_runs,
                          "usine_cap": 600}
    # D9 is judged on BIG, SLIM and QUAINT, or the declared variant QUAINT-Vc0 when boundary_kkt accepts V_c = 0
    # (VALIDATION CRPROP-F1, dispatch 2); model alternatives (tagged folders) are reported, never judged
    kkt_path = out / "quaint-vc-kkt.json"
    kkt = json.loads(kkt_path.read_text()) if kkt_path.is_file() else None
    quaint = "QUAINT-Vc0" if kkt and kkt["kkt_ok"] and "QUAINT-Vc0" in fams else "QUAINT"
    if kkt:
        doc["quaint_vc_boundary_kkt"] = kkt
    alt_path = out / "quaint-vc0-papercov-best.json"
    if alt_path.is_file():   # model alternative (P9): the paper's covariance choice, reported next to D9
        alt = json.loads(alt_path.read_text())
        pub = PUBLISHED["QUAINT"]
        c, lo, hi = pub["delta"]
        doc["model_alternatives"] = {"QUAINT-Vc0, USINE relative covariance x model (the paper's choice)": {
            "status": "not-reported", "note": alt["note"], "chi2": alt["chi2"], "delta": alt["delta"], "K10": alt["K10"],
            "delta_in_window": c - lo <= alt["delta"] <= c + hi,
            "K10_in_window": pub["K10"] * 10 ** -pub["s_log10_K10"] <= alt["K10"] <= pub["K10"] * 10 ** pub["s_log10_K10"],
            "computational_run_ref": alt["computational_run_ref"]}}
    doc["judged_for_D9"] = [f for f in ("BIG", "SLIM", quaint) if f in fams]
    doc["D9_all"] = all(fams[f].get("D9") == "passed" for f in doc["judged_for_D9"])
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(doc, indent=1, default=list) + "\n")
    return {"record": str(record_path), "D9_all": doc["D9_all"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--stages", default="data,start,fit,compare")
    ap.add_argument("--families", default="BIG,SLIM,QUAINT")
    ap.add_argument("--cache-dir", type=Path)
    ap.add_argument("--max-evaluations", type=int, default=600)
    ap.add_argument("--covariance-alternatives", default="", help="families that also fit the P9 alternatives")
    ap.add_argument("--restart-from", type=Path, help="folder holding fit-<family>/out/result.json of an earlier pass: "
                    "start at its best fits with steps of --step-fraction of each conditional sigma")
    ap.add_argument("--step-fraction", type=float, default=0.3)
    ap.add_argument("--restart-cached", action="store_true", help="start each family at its lowest cached point "
                    "(steps from --restart-from's Fisher matrices, or BIG_RESTART_STEPS)")
    ap.add_argument("--covariance", default="nominal", help="nominal, or model-scaled:<family> (the paper's choice)")
    ap.add_argument("--tag", default="", help="suffix of the fit folders (fit-<family><tag>)")
    ap.add_argument("--record", type=Path, help="stage record: the JSON record to write (numbers only)")
    ap.add_argument("--usine-runs", type=int, default=0, help="stage record: the USINE run tally to record")
    ap.add_argument("--rejudge-from", type=Path, help="stage fit (K1): refit each family from <dir>/fit-<family>/"
                    "config.json with the noise-aware verdict (VALIDATION.md CRPROP-K1)")
    ap.add_argument("--noise-budget", type=int, default=40, help="K1: evaluations of the noise measurement per fit")
    ap.add_argument("--polish-steps", type=int, default=0, help="K1: Newton steps of the verdict (optimizer.polish_steps)")
    ap.add_argument("--rejudge-usine-runs", type=int, help="stage record: the K1 USINE run tally to record")
    a = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "missing-dependency", "error": "numpy and scipy are needed"}))
        return 3
    global UNF_LENGTH
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache = (a.cache_dir or out / "cache").resolve()
    families = [f for f in a.families.split(",") if f]
    stages = a.stages.split(",")
    summary = {}
    if "data" in stages:
        summary["data"] = stage_data(out)
    model_file = out / "data" / "covariance-model.json"
    if model_file.is_file():
        UNF_LENGTH = json.loads(model_file.read_text())["unf_length_ln_r"]
    reg = registry(out) if {"start", "fit"} & set(stages) else None
    if "start" in stages:
        summary["start"] = stage_start(out, families, reg, cache)
    if "fit" in stages:
        alts = set(a.covariance_alternatives.split(",")) - {""}
        if a.rejudge_from:
            procs = {f: run_rejudge(out, f, reg, cache, a.max_evaluations, a.rejudge_from, a.noise_budget,
                                    a.polish_steps, a.tag) for f in families}
        else:
            procs = {f: run_fit(out, f, reg, cache, a.max_evaluations, f in alts,
                                restart_cached(out, f, a.restart_from, a.step_fraction) if a.restart_cached else
                                restart_from(a.restart_from / f"fit-{f}" / "out" / "result.json", a.step_fraction)
                                if a.restart_from else None, a.covariance, a.tag) for f in families}
        summary["fit"] = {f: p.wait() for f, p in procs.items()}
    if "compare" in stages:
        summary["compare"] = stage_compare(out, families)
    if "record" in stages:
        summary["record"] = stage_record(out, families, a.record or out / "f1-reproduction.json", a.usine_runs,
                                         a.rejudge_usine_runs)
    if "attribution" in stages:
        summary["attribution"] = stage_attribution(out, families, reg or registry(out), cache)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str)[:4000])
    failed = any(v for v in summary.get("fit", {}).values()) or ("compare" in summary
                                                                 and not summary["compare"]["D9_all"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

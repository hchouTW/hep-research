#!/usr/bin/env python3
"""External benchmark of theory:cr-secondary-antiprotons (open question B2): the pp-induced secondary antiproton source
term of di Mauro, Donato, Goudelis and Serpico, Phys. Rev. D 90 (2014) 085017, arXiv:1408.0288v3, Table VI, against
this profile's implementation of the same paper's closed-form parametrizations.

PUBLISHED inputs, labelled with their source (crpb:S02, crpb:S05; claims crpb:C07-C09):
  q_pp(T) = int dE_p dsigma/dE_pbar(E_p, E_pbar) n_H 4 pi Phi_p(E_p)                        (1408.0288 Eq. (1))
  dsigma/dE_pbar = 2 pi p_pbar int_{cos theta_max}^{1} E d3sigma/dp3 d(cos theta)            (Eq. (2), (A15))
  E d3sigma/dp3 = sigma_in(s) (1 - x_R)^C1 exp(-C2 x_R) [...]                                (Eqs. (11)-(13))
  sigma_in = sigma_tot - sigma_el, PDG-type form                                            (Eqs. (B1)-(B2))
  Phi_p = A beta^P1 R^-P2                                                                   (1402.0321v2 Sec. 2.3)
Parameters: models/xs-dimauro2014-pp.json (Tables III, IV, V, VII); reference values and tolerance:
benchmarks/published-source-term-dimauro2014.json. The toy cross sections of predict.py are not used here.

Numerics: the angular integral runs over u = 1 - cos(theta) on a log scale (the integrand is confined to
u ~ (p_T / p_pbar)^2 / 2 at high energy); the projectile integral over ln T_p from just below the kinematic threshold
to the profile's upper limit (not stated in the paper; recorded in the benchmark file).

Usage:
  python3 published_benchmark.py [--out result.json]   # exit 0 when every entry expected to be reproduced is
                                                        # within tolerance and every other one is documented
Exit codes: 0 ok, 1 a check failed, 2 bad input, 3 numpy/scipy missing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
BENCHMARK = PROFILE / "benchmarks" / "published-source-term-dimauro2014.json"

M_P_GEV = 0.93827208816       # CODATA 2018 (crpb:C06)
HBARC2_GEV2_MB = 0.389379372  # (hbar c)^2 in GeV^2 mb, CODATA 2018 hbar c = 0.197326980 GeV fm (crpb:C10)
MB_CM2 = 1e-27
FORMS = ("eq11", "eq12", "eq13")


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sigma_pdg(s: float, p: dict) -> float:
    """Eq. (B2) of 1408.0288: Z + B log^2(s/s_M) + Y1 (s_M/s)^eta1 - Y2 (s_M/s)^eta2 in mb (s in GeV^2)."""
    s_m = (2.0 * M_P_GEV + p["M"]) ** 2
    b = math.pi * HBARC2_GEV2_MB / p["M"] ** 2
    return p["Z"] + b * math.log(s / s_m) ** 2 + p["Y1"] * (s_m / s) ** p["eta1"] - p["Y2"] * (s_m / s) ** p["eta2"]


def sigma_in(xs: dict, s: float) -> float:
    """Eq. (B1): inelastic = total - elastic, both from Eq. (B2) with Table VII, in mb."""
    return sigma_pdg(s, xs["sigma_in"]["total"]) - sigma_pdg(s, xs["sigma_in"]["elastic"])


def invariant(xs: dict, form: str, s: float, x_r: float, p_t: float) -> float:
    """E d3sigma/dp3 in mb GeV^-2 for Eq. (11), (12) or (13) of 1408.0288."""
    c = xs["parametrizations"][form]["C"]
    rs = math.sqrt(s)
    pre = sigma_in(xs, s) * (1.0 - x_r) ** c[0] * math.exp(-c[1] * x_r)
    if form == "eq11":
        br = c[2] * math.exp(-c[3] * p_t) + c[4] * math.exp(-c[5] * p_t ** 2)
    elif form == "eq12":
        br = c[2] * rs ** c[3] * math.exp(-c[4] * p_t) + c[5] * rs ** c[6] * math.exp(-c[7] * p_t ** 2)
    elif form == "eq13":
        br = abs(c[2] * rs ** c[3] * math.exp(-c[4] * p_t) + c[5] * rs ** c[6] * math.exp(-c[7] * p_t ** 2)
                 + c[8] * rs ** c[9] * math.exp(-c[10] * p_t ** 3))
    else:
        raise ValueError(f"unknown parametrization {form!r}")
    return pre * br


def dsigma_de(xs: dict, form: str, e_p: float, e_b: float) -> float:
    """dsigma/dE_pbar (E_p, E_pbar) in mb/GeV, Eq. (2) with the lab-frame angular limit of Eq. (A15)."""
    from scipy.integrate import quad
    s = 2.0 * M_P_GEV * (e_p + M_P_GEV)
    rs = math.sqrt(s)
    e_max = (s - 8.0 * M_P_GEV ** 2) / (2.0 * rs)
    if e_max <= M_P_GEV or e_b <= M_P_GEV:
        return 0.0
    p_p, p_b = math.sqrt(e_p ** 2 - M_P_GEV ** 2), math.sqrt(e_b ** 2 - M_P_GEV ** 2)
    c_max = (e_b * (e_p + M_P_GEV) - M_P_GEV * (e_p - 3.0 * M_P_GEV)) / (p_b * p_p)
    if c_max >= 1.0:
        return 0.0
    u_max = 1.0 - max(c_max, -1.0)
    v, g = p_p / (e_p + M_P_GEV), (e_p + M_P_GEV) / rs

    def integrand(lu: float) -> float:
        u = math.exp(lu)
        cos_t = 1.0 - u
        x_r = g * (e_b - v * p_b * cos_t) / e_max
        if not 0.0 <= x_r < 1.0:
            return 0.0
        p_t = p_b * math.sqrt(max(0.0, u * (2.0 - u)))
        return invariant(xs, form, s, x_r, p_t) * u

    val, _ = quad(integrand, math.log(u_max * 1e-12), math.log(u_max), epsabs=0.0, epsrel=1e-8, limit=400)
    return 2.0 * math.pi * p_b * val


def proton_flux(spec: dict, t_p: float) -> float:
    """Phi_p = A beta^P1 R^-P2 (1402.0321v2 Sec. 2.3), converted to cm^-2 s^-1 sr^-1 GeV^-1 (R = p for protons)."""
    e = t_p + M_P_GEV
    p = math.sqrt(e * e - M_P_GEV ** 2)
    return spec["A_m2_s_sr_GeV"] * 1e-4 * (p / e) ** spec["P1"] * p ** (-spec["P2"])


def source_term_pp(xs: dict, inputs: dict, form: str, t: float, t_p_max: float | None = None) -> float:
    """q_pp(T) in GeV^-1 cm^-3 s^-1 (Eq. (1) of 1408.0288) for antiproton kinetic energy T in GeV."""
    from scipy.integrate import quad
    e_b = t + M_P_GEV
    t_max = float(t_p_max or inputs["projectile_kinetic_energy_max_gev"])
    flux = inputs["proton_flux"]

    def integrand(lt: float) -> float:
        t_p = math.exp(lt)
        return dsigma_de(xs, form, t_p + M_P_GEV, e_b) * proton_flux(flux, t_p) * t_p

    lo = math.log(5.9 * M_P_GEV)  # just below the threshold T_p = 6 m_p; zero integrand there
    val, _ = quad(integrand, lo, math.log(t_max), epsabs=0.0, epsrel=1e-7, limit=1000)
    return 4.0 * math.pi * float(inputs["n_H_cm3"]) * val * MB_CM2


def benchmark(bench: dict | None = None) -> dict:
    bench = bench or load_json(BENCHMARK)
    xs = load_json(PROFILE / bench["inputs"]["cross_sections"])
    rows, checks = [], {}
    expected = bench["expected_status"]["reproduced"]
    tol_ok_where_expected = True
    for form in FORMS:
        ref = bench["table_vi"][form]
        for k, t in enumerate(bench["energies_gev"]):
            q = source_term_pp(xs, bench["inputs"], form, t)
            dev = q / ref["q"][k] - 1.0
            tol = ref["rel_error_percent"][k] / 100.0
            within = abs(dev) <= tol
            exp_rep = t in expected.get(form, [])
            status = "reproduced" if exp_rep and within else "documented-not-reproduced"
            if exp_rep and not within:
                tol_ok_where_expected = False
            rows.append({"form": form, "T_gev": t, "q_profile": q, "q_table": ref["q"][k], "rel_dev": dev,
                         "tolerance": tol, "within_tolerance": within, "status": status})
    checks["expected_entries_within_paper_error"] = tol_ok_where_expected
    documented = set(bench["expected_status"]["documented_not_reproduced"])
    checks["every_other_entry_documented"] = all(
        f"{r['form']}@{r['T_gev']:g}" in documented for r in rows if r["status"] != "reproduced")
    # unit guard, not a published number: this code gives sigma_in = 31.7 mb at sqrt(s) = 17.3 GeV; a wrong (hbar c)^2
    # or s convention moves it far outside this window
    s_na49 = 17.3 ** 2
    checks["sigma_in_at_na49_between_30_and_33_mb"] = 30.0 < sigma_in(xs, s_na49) < 33.0
    n_rep = sum(r["status"] == "reproduced" for r in rows)
    max_dev = max((abs(r["rel_dev"]) for r in rows if r["status"] == "reproduced"), default=None)
    return {"source": bench["source"], "unit": bench["unit"], "rows": rows, "reproduced_entries": n_rep,
            "entries": len(rows), "max_abs_rel_dev_reproduced": max_dev,
            "checks": {k: bool(v) for k, v in checks.items()}, "illustrative": False}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--benchmark-file", type=Path, default=BENCHMARK)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}"}))
        return 3
    try:
        out = benchmark(load_json(opts.benchmark_file))
    except (KeyError, ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

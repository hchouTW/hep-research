#!/usr/bin/env python3
"""Numerical predictions of theory:higgs-bb-width: Gamma(H -> b bbar) with the MS-bar running b mass, n_f = 5.

Gamma(mu) = 3 G_F M_H / (4 sqrt(2) pi) mbar_b(mu)^2 sum_(n<=N) r_n(L) a(mu)^n, a = alpha_s / pi, L = ln(mu^2 / M_H^2),
r_n(0) = s_n (hbb:C02, C03). The r_n(L) follow from the renormalization-group invariance of Gamma: with
d a / dL = -sum_i B_i a^(i+2) and d ln m / dL = -sum_i gamma_i a^(i+1),
    d r_n / dL = 2 sum_(k<n) gamma_k r_(n-1-k) + sum_(i<=n-2) B_i (n-1-i) r_(n-1-i);
the tests check these polynomials against the SymPy derivation in derive.py. alpha_s(mu) is run from alpha_s(m_Z) and
mbar_b(mu) from mbar_b(mbar_b) with the four-loop beta function and mass anomalous dimension at fixed n_f = 5 (no
threshold matching; hbb:C04, C05), for every order N.

Three uncertainty objects are reported separately and never combined into a Gaussian: the scale envelope (min and max
over mu in [M_H/2, 2 M_H], a prescription, not a confidence interval), the truncation estimate (size of the last
included term at mu = M_H, a heuristic) and the parametric variations of alpha_s(m_Z) and mbar_b(mbar_b) (the PDG
uncertainties, propagated by re-evaluation one at a time).

Usage: python3 predict.py [--config ../benchmarks/hbb-125.json] [--out prediction.json]
Exit 0 all checks pass, 1 a check fails or the configuration is outside the validity domain (JSON reason).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE.parent / "benchmarks" / "hbb-125.json"
MAX_ORDER = 4
ZETA3, ZETA5, ZETA4, PI2 = 1.2020569031595942, 1.0369277551433699, math.pi ** 4 / 90, math.pi ** 2


def s_coefficients(nf: int, s4: float) -> list[float]:
    """s_0..s_4 at mu = M_H (hep-ph/9608318 eq. (21) / 3, hbb:C02; s_4 at n_f = 5 from hep-ph/0511063, hbb:C03)."""
    s2 = 10801 / 144 - 19 / 12 * PI2 - 39 / 2 * ZETA3 + nf * (-65 / 24 + PI2 / 18 + 2 / 3 * ZETA3)
    s3 = (6163613 / 5184 - 3535 / 72 * PI2 - 109735 / 216 * ZETA3 + 815 / 12 * ZETA5
          + nf * (-46147 / 486 + 277 / 72 * PI2 + 262 / 9 * ZETA3 - 5 / 6 * ZETA4 - 25 / 9 * ZETA5)
          + nf ** 2 * (15511 / 11664 - 11 / 162 * PI2 - ZETA3 / 3))
    return [1.0, 17 / 3, s2, s3, s4]


def gammas(nf: int) -> list[float]:
    """gamma_0..gamma_3 for a = alpha_s / pi (hep-ph/9703278 eqs. (7)-(9), hbb:C04)."""
    return [1.0, (202 / 3 - 20 / 9 * nf) / 16, (1249 + nf * (-2216 / 27 - 160 / 3 * ZETA3) - 140 / 81 * nf ** 2) / 64,
            (4603055 / 162 + 135680 / 27 * ZETA3 - 8800 * ZETA5
             + nf * (-91723 / 27 - 34192 / 9 * ZETA3 + 880 * ZETA4 + 18400 / 9 * ZETA5)
             + nf ** 2 * (5242 / 243 + 800 / 9 * ZETA3 - 160 / 3 * ZETA4) + nf ** 3 * (-332 / 243 + 64 / 27 * ZETA3)) / 256]


def betas(nf: int) -> list[float]:
    """B_0..B_3 for a = alpha_s / pi: beta_i (alpha_s/(4 pi), hep-ph/9701390 eq. (11), hbb:C05) / 4^(i+1)."""
    b = [11 - 2 / 3 * nf, 102 - 38 / 3 * nf, 2857 / 2 - 5033 / 18 * nf + 325 / 54 * nf ** 2,
         149753 / 6 + 3564 * ZETA3 - (1078361 / 162 + 6508 / 27 * ZETA3) * nf + (50065 / 162 + 6472 / 81 * ZETA3) * nf ** 2
         + 1093 / 729 * nf ** 3]
    return [x / 4 ** (i + 1) for i, x in enumerate(b)]


def r_polynomials(nf: int, s4: float) -> list[list[float]]:
    """r_0..r_4 as coefficient lists in L (lowest power first), from the RG recursion with r_n(0) = s_n."""
    s, g, bb = s_coefficients(nf, s4), gammas(nf), betas(nf)
    r: list[list[float]] = [[1.0]]
    for n in range(1, MAX_ORDER + 1):
        deriv: list[float] = [0.0] * n
        for k in range(n):  # 2 gamma_k r_(n-1-k)
            for p, c in enumerate(r[n - 1 - k]):
                deriv[p] += 2 * g[k] * c
        for i in range(n - 1):  # B_i (n-1-i) r_(n-1-i)
            for p, c in enumerate(r[n - 1 - i]):
                deriv[p] += bb[i] * (n - 1 - i) * c
        r.append([s[n]] + [c / (p + 1) for p, c in enumerate(deriv)])
    return r


def r_values(nf: int, s4: float, lg: float) -> list[float]:
    return [sum(c * lg ** p for p, c in enumerate(poly)) for poly in r_polynomials(nf, s4)]


def _rge(nf: int):
    bb, g = betas(nf), gammas(nf)

    def f(t, y):  # y = [a, ln m], t = ln mu^2
        a = y[0]
        return [-sum(b * a ** (i + 2) for i, b in enumerate(bb)), -sum(c * a ** (i + 1) for i, c in enumerate(g))]
    return f


def run(cfg: dict, mu: float, alpha_s_mz: float, mb_mb: float) -> tuple[float, float]:
    """(alpha_s(mu), mbar_b(mu)): alpha_s from m_Z down to mbar_b, then (a, ln m) from mbar_b to mu, fixed n_f."""
    from scipy.integrate import solve_ivp
    f = _rge(cfg["n_f"])
    tol = {"rtol": 1e-12, "atol": 1e-15}
    a_mb = solve_ivp(lambda t, y: [f(t, [y[0], 0.0])[0]], (2 * math.log(cfg["m_z_gev"]), 2 * math.log(mb_mb)),
                     [alpha_s_mz / math.pi], **tol).y[0, -1]
    sol = solve_ivp(f, (2 * math.log(mb_mb), 2 * math.log(mu)), [a_mb, math.log(mb_mb)], **tol)
    return float(sol.y[0, -1] * math.pi), float(math.exp(sol.y[1, -1]))


def width(cfg: dict, order: int, mu: float, alpha_s_mz: float | None = None, mb_mb: float | None = None) -> float:
    m_h = cfg["m_h_gev"]
    alpha, mb = run(cfg, mu, cfg["alpha_s_mz"] if alpha_s_mz is None else alpha_s_mz,
                    cfg["mb_mb_gev"] if mb_mb is None else mb_mb)
    a = alpha / math.pi
    r = r_values(cfg["n_f"], cfg["s4_nf5"], math.log(mu ** 2 / m_h ** 2))
    pref = 3 * cfg["g_f_gev_minus2"] * m_h / (4 * math.sqrt(2) * math.pi)
    return pref * mb ** 2 * sum(r[n] * a ** n for n in range(order + 1))


def check_domain(cfg: dict) -> None:
    if cfg["n_f"] != 5:
        raise ValueError("this profile covers n_f = 5 only (s_4 is known numerically at n_f = 5)")
    if not 2 * cfg["mb_mb_gev"] < min(cfg["scale_factors"]) * cfg["m_h_gev"]:
        raise ValueError("outside the validity domain: the lowest scale must stay well above m_b")
    if not 0.05 < cfg["alpha_s_mz"] < 0.2 or cfg["mb_mb_gev"] <= 0 or cfg["m_h_gev"] <= 0:
        raise ValueError("inputs outside the range this profile was checked for")


def predict(cfg: dict) -> dict:
    check_domain(cfg)
    m_h = cfg["m_h_gev"]
    n = cfg["scale_scan_points"]
    lo, hi = min(cfg["scale_factors"]), max(cfg["scale_factors"])
    scan = [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]
    alpha_mh, mb_mh = run(cfg, m_h, cfg["alpha_s_mz"], cfg["mb_mb_gev"])
    orders = []
    for order in range(MAX_ORDER + 1):
        central = width(cfg, order, m_h)
        values = [width(cfg, order, f * m_h) for f in scan]
        last = 0.0 if order == 0 else central - width(cfg, order - 1, m_h)
        da, dm = cfg["alpha_s_mz_uncertainty"], cfg["mb_mb_uncertainty_gev"]
        orders.append({
            "order_in_alpha_s": order, "Gamma_GeV_mu_eq_MH": central,
            "scale_envelope": {"prescription": "scan-min-max over mu in [M_H/2, 2 M_H] (log scan, running mass and coupling)",
                               "min": min(values), "max": max(values),
                               "three_point": {str(f): width(cfg, order, f * m_h) for f in cfg["scale_factors"]},
                               "gaussian": False},
            "truncation_estimate": {"method": "last-term", "value": abs(last), "gaussian": False},
            "parametric_alpha_s": {"up": width(cfg, order, m_h, cfg["alpha_s_mz"] + da) - central,
                                   "down": width(cfg, order, m_h, cfg["alpha_s_mz"] - da) - central,
                                   "source": "alpha_s(m_Z) +- PDG uncertainty"},
            "parametric_mb": {"up": width(cfg, order, m_h, mb_mb=cfg["mb_mb_gev"] + dm) - central,
                              "down": width(cfg, order, m_h, mb_mb=cfg["mb_mb_gev"] - dm) - central,
                              "source": "mbar_b(mbar_b) +- PDG summary-table uncertainty (printed at CL = 90%)"}})
    widths = [o["scale_envelope"]["max"] - o["scale_envelope"]["min"] for o in orders]
    s = s_coefficients(cfg["n_f"], cfg["s4_nf5"])
    checks = {
        "mb_runs_down_toward_MH": mb_mh < cfg["mb_mb_gev"],
        "alpha_s_falls_toward_MH": alpha_mh < cfg["alpha_s_mz"],
        "leading_correction_is_s1_a": abs(orders[1]["Gamma_GeV_mu_eq_MH"] / orders[0]["Gamma_GeV_mu_eq_MH"] - 1
                                          - s[1] * alpha_mh / math.pi) < 1e-12,
        "scale_envelope_shrinks_from_LO_to_N4LO": widths[4] < widths[0],
        "central_inside_its_envelope": all(o["scale_envelope"]["min"] <= o["Gamma_GeV_mu_eq_MH"] <= o["scale_envelope"]["max"]
                                           for o in orders),
    }
    return {"m_h_gev": m_h, "n_f": cfg["n_f"], "alpha_s_at_MH": alpha_mh, "mb_at_MH_gev": mb_mh,
            "running": "four-loop beta and gamma_m, fixed n_f = 5, from alpha_s(m_Z) and mbar_b(mbar_b)",
            "orders": orders, "scale_envelope_widths_GeV": widths, "checks": checks,
            "status": "perturbative-argument; prediction, not a measurement; massless b at leading power, no "
                      "electroweak or top-induced corrections"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    try:
        out = predict(json.loads(opts.config.read_text(encoding="utf-8")))
    except ValueError as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 1
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Numerical predictions of theory:qcd-r-ratio: R(Q) = R_EW (1 + delta_QCD) for massless quarks, photon exchange only.

delta_QCD = sum_n d_n(L) a(mu)^n with a = alpha_s/pi, L = ln(mu^2/Q^2) and d_n(0) = c_n (PDG eq. 9.9, qcdr:C02); the
d_n(L) closed forms below are checked against the SymPy derivation in derive.py by the tests. alpha_s(mu) is run from
alpha_s(m_Z) (qcdr:C04) with the three-loop beta function (PDG eq. 9.3, qcdr:C03) at fixed n_f.

Three uncertainty objects are reported separately and never combined into a Gaussian: the scale envelope (min and max
over mu in [Q/2, 2Q], a prescription, not a confidence interval), the truncation estimate (size of the last included
term, a heuristic) and the parametric alpha_s(m_Z) variation (the PDG uncertainty, propagated by re-evaluation).

Usage: python3 predict.py [--config ../benchmarks/r-ratio-15gev.json] [--out prediction.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE.parent / "benchmarks" / "r-ratio-15gev.json"
MAX_ORDER = 4


def c_coefficients(nf: int, eta: float) -> list[float]:
    """c_1..c_4 at mu = Q, MS-bar (PDG eq. 9.9, qcdr:C02)."""
    return [1.0, 1.9857 - 0.1152 * nf,
            -6.63694 - 1.20013 * nf - 0.00518 * nf ** 2 - 1.240 * eta,
            -156.61 + 18.775 * nf - 0.7974 * nf ** 2 + 0.0215 * nf ** 3 - (17.828 - 0.575 * nf) * eta]


def beta_coefficients(nf: int) -> list[float]:
    """beta_k = pi^(k+1) b_k for a = alpha_s/pi (PDG eq. 9.3, qcdr:C03)."""
    return [(33 - 2 * nf) / 12.0, (153 - 19 * nf) / 24.0, (2857 - 5033 / 9 * nf + 325 / 27 * nf ** 2) / 128.0]


def d_coefficients(nf: int, eta: float, lg: float) -> list[float]:
    """d_1..d_4 at L = ln(mu^2/Q^2): the RGE consequence of the c_n (derived in derive.py)."""
    c1, c2, c3, c4 = c_coefficients(nf, eta)
    b0, b1, b2 = beta_coefficients(nf)
    return [c1,
            c2 + b0 * c1 * lg,
            c3 + (2 * b0 * c2 + b1 * c1) * lg + b0 ** 2 * c1 * lg ** 2,
            c4 + (3 * b0 * c3 + 2 * b1 * c2 + b2 * c1) * lg + (3 * b0 ** 2 * c2 + 2.5 * b0 * b1 * c1) * lg ** 2
            + b0 ** 3 * c1 * lg ** 3]


def run_alpha_s(alpha_s_mz: float, m_z: float, mu: float, nf: int) -> float:
    """alpha_s(mu) from alpha_s(m_Z), three-loop RGE at fixed n_f, integrated in t = ln(mu^2)."""
    from scipy.integrate import solve_ivp
    b0, b1, b2 = beta_coefficients(nf)
    sol = solve_ivp(lambda t, y: [-(b0 * y[0] ** 2 + b1 * y[0] ** 3 + b2 * y[0] ** 4)],
                    (2 * math.log(m_z), 2 * math.log(mu)), [alpha_s_mz / math.pi], rtol=1e-12, atol=1e-15)
    return float(sol.y[0, -1] * math.pi)


def r_value(cfg: dict, order: int, mu: float, alpha_s_mz: float | None = None) -> float:
    q, nf = cfg["q_gev"], cfg["n_f"]
    r_ew, eta = electroweak_factor(cfg)
    a_mu = run_alpha_s(cfg["alpha_s_mz"] if alpha_s_mz is None else alpha_s_mz, cfg["m_z_gev"], mu, nf) / math.pi
    d = d_coefficients(nf, eta, math.log(mu ** 2 / q ** 2))
    return r_ew * (1.0 + sum(d[n] * a_mu ** (n + 1) for n in range(order)))


def electroweak_factor(cfg: dict) -> tuple[float, float]:
    e = cfg["quark_charges"]
    if len(e) != cfg["n_f"]:
        raise ValueError(f"{len(e)} quark charges for n_f = {cfg['n_f']}")
    sum_e2 = sum(x * x for x in e)
    return cfg["n_c"] * sum_e2, sum(e) ** 2 / (cfg["n_c"] * sum_e2)


def predict(cfg: dict) -> dict:
    q = cfg["q_gev"]
    if min(cfg["scale_factors"]) * q < cfg["lowest_scale_gev"] or q > cfg["m_z_gev"] / 3:
        raise ValueError("outside the validity domain: scales below lowest_scale_gev or Q too close to m_Z")
    r_ew, eta = electroweak_factor(cfg)
    alpha_q = run_alpha_s(cfg["alpha_s_mz"], cfg["m_z_gev"], q, cfg["n_f"])
    n = cfg["scale_scan_points"]
    lo, hi = min(cfg["scale_factors"]), max(cfg["scale_factors"])
    scan = [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]
    orders = []
    for order in range(MAX_ORDER + 1):
        central = r_value(cfg, order, q)
        values = [r_value(cfg, order, f * q) for f in scan]
        three = [r_value(cfg, order, f * q) for f in cfg["scale_factors"]]
        last = 0.0 if order == 0 else central - r_value(cfg, order - 1, q)
        up = r_value(cfg, order, q, cfg["alpha_s_mz"] + cfg["alpha_s_mz_uncertainty"]) - central
        down = r_value(cfg, order, q, cfg["alpha_s_mz"] - cfg["alpha_s_mz_uncertainty"]) - central
        orders.append({"order_in_alpha_s": order, "R_central_mu_eq_Q": central,
                       "scale_envelope": {"prescription": "min and max over mu in [Q/2, 2Q] (log scan)",
                                          "min": min(values), "max": max(values),
                                          "three_point": dict(zip([str(f) for f in cfg["scale_factors"]], three)),
                                          "gaussian": False},
                       "truncation_estimate": {"prescription": "absolute size of the last included term at mu = Q",
                                               "value": abs(last), "gaussian": False},
                       "parametric_alpha_s": {"up": up, "down": down, "source": "alpha_s(m_Z) +- PDG uncertainty"}})
    widths = [o["scale_envelope"]["max"] - o["scale_envelope"]["min"] for o in orders]
    checks = {
        "R_EW_is_11_over_3_for_udscb": abs(r_ew - 11 / 3) < 1e-12 if cfg["n_f"] == 5 else True,
        "eta_is_1_over_33_for_udscb": abs(eta - 1 / 33) < 1e-12 if cfg["n_f"] == 5 else True,
        "alpha_s_grows_toward_low_scale": alpha_q > cfg["alpha_s_mz"],
        "leading_correction_is_alpha_s_over_pi": abs(orders[1]["R_central_mu_eq_Q"] / r_ew - 1 - alpha_q / math.pi) < 1e-12,
        "order_0_has_no_scale_dependence": widths[0] == 0.0,
        "scale_envelope_shrinks_from_NLO_to_N3LO": widths[4] < widths[1],
        "central_inside_its_envelope": all(o["scale_envelope"]["min"] <= o["R_central_mu_eq_Q"] <= o["scale_envelope"]["max"] for o in orders),
    }
    return {"q_gev": q, "n_f": cfg["n_f"], "R_EW": r_ew, "eta": eta, "alpha_s_at_Q": alpha_q,
            "alpha_s_running": "three-loop, fixed n_f, from alpha_s(m_Z)", "orders": orders,
            "scale_envelope_widths": widths, "checks": checks,
            "status": "perturbative-argument; prediction, not a measurement; no Z exchange, no quark masses"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    out = predict(json.loads(opts.config.read_text(encoding="utf-8")))
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

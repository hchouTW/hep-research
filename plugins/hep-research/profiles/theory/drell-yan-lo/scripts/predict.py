#!/usr/bin/env python3
"""Numerical predictions of theory:drell-yan-lo.

Angular coefficients at O(alpha_s) (photon exchange, Collins-Soper frame), r = qT/Q:
  A0 = <sin^2 theta1>: r^2/(1 + r^2) for q qbar -> gamma* g (Peng et al. Eq. 8), 5 r^2/(1 + 5 r^2) for
  q g -> gamma* q (Eq. 9, an approximation); A2 = A0 because phi1 = 0 at this order (cited, dylo:C06);
  lambda = (2 - 3 A0)/(2 + A0), nu = 2 A2/(2 + A0) (Eq. 7); 1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0) = 0.
A channel mixture with q g fraction f has A_i = f A_i(qg) + (1 - f) A_i(qqbar), exactly (derive.py): every A_i term of
Peng Eq. 3 integrates to zero over the sphere and the (1 + cos^2 theta) term to 16 pi/3, so f is the angle-integrated
cross-section fraction of the channel in the same (qT, Q) bin (an event fraction only with full angular acceptance).
Equivalently lambda = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c); a linear average of lambda is wrong.

LO cross section (dylo:C01, C02): d^2 sigma/dM dy = (8 pi alpha^2/(9 M s)) sum e_q^2 [q1(x1) qbar2(x2) + qbar1(x1)
q2(x2)], x1,2 = (M/sqrt(s)) e^(+-y). Computed in units of 4 pi alpha^2/3 (= 86.8 nb GeV^2, PDG Eq. 51.3), so no value
of alpha is used. The Jacobian is checked numerically: the formula integrated over an (M, y) box against the parton
integral over the matching region of (x1, x2), on SYNTHETIC toy densities.

Usage: python3 predict.py [--config ../benchmarks/angular-grid.json] [--out prediction.json]
Exit 0 all checks pass, 1 a check fails, 2 bad input, 3 numpy/scipy missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import math
import sys

sys.dont_write_bytecode = True  # importing siblings or core leaves no __pycache__ (F-10)
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
DEFAULT_CONFIG = PROFILE / "benchmarks" / "angular-grid.json"
BENCHMARK = PROFILE / "benchmarks" / "peng-eq10.json"
TOY_XS = PROFILE / "benchmarks" / "toy-lo-cross-section.json"
NB_GEV2 = 86.8  # 4 pi alpha^2 / 3 in nb GeV^2, PDG Eq. 51.3 (dylo:C01)
CHANNELS = ("qqbar", "qg")


class InputError(ValueError):
    """A config that cannot describe a valid input."""


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------ angular coefficients
def sin2_theta1(channel: str, r: float) -> float:
    """<sin^2 theta1> at O(alpha_s): Peng Eq. 8 (q qbar, exact) or Eq. 9 (q g, approximate); r = qT/Q >= 0."""
    if r < 0:
        raise InputError(f"qT/Q must be >= 0, got {r}")
    k = {"qqbar": 1.0, "qg": 5.0}.get(channel)
    if k is None:
        raise InputError(f"unknown channel {channel!r}; one of {CHANNELS}")
    return k * r * r / (1.0 + k * r * r)


def lambda_nu(a0: float, a2: float) -> tuple[float, float]:
    """Peng Eq. 7."""
    return (2.0 - 3.0 * a0) / (2.0 + a0), 2.0 * a2 / (2.0 + a0)


def channel_coefficients(channel: str, r: float) -> dict:
    a0 = sin2_theta1(channel, r)
    lam, nu = lambda_nu(a0, a0)  # phi1 = 0: A2 = A0
    return {"A0": a0, "A2": a0, "lambda": lam, "nu": nu, "lam_tung": 1.0 - lam - 2.0 * nu}


def mixture_coefficients(f_qg: float, r: float, rule: str = "average-A") -> dict:
    """Channel mixture with q g cross-section fraction f_qg: A0, A2 averaged with the angle-integrated cross-section
    fractions (exact, derived in derive.py). 'average-A' is the only rule; anything else is refused."""
    if not 0.0 <= f_qg <= 1.0:
        raise InputError(f"q g fraction must lie in [0, 1], got {f_qg}")
    qq, qg = channel_coefficients("qqbar", r), channel_coefficients("qg", r)
    if rule == "average-A":
        a0 = f_qg * qg["A0"] + (1.0 - f_qg) * qq["A0"]
        a2 = f_qg * qg["A2"] + (1.0 - f_qg) * qq["A2"]
        lam, nu = lambda_nu(a0, a2)
    else:
        raise InputError(f"unknown mixing rule {rule!r}")
    return {"lambda": lam, "nu": nu, "lam_tung": 1.0 - lam - 2.0 * nu}


def peng_eq10(bench: dict, channel: str, quantity: str, r: float) -> float:
    n0, n1, d0, d1 = bench["rational_form"][channel][quantity]
    return (n0 + n1 * r * r) / (d0 + d1 * r * r)


def benchmark_comparison(bench: dict | None = None) -> dict:
    """The profile's lambda, nu (Eqs. 7-9) against the published closed form (Eq. 10) at the benchmark qT/Q values."""
    bench = bench or load_json(BENCHMARK)
    rel, absol = bench["relative_tolerance"], bench["absolute_tolerance"]
    rows, ok = [], True
    for ch in CHANNELS:
        for r in bench["qT_over_Q"]:
            c = channel_coefficients(ch, r)
            for q in ("lambda", "nu"):
                ref = peng_eq10(bench, ch, q, r)
                diff = abs(c[q] - ref)
                passed = diff <= max(absol, rel * abs(ref))
                ok &= passed
                rows.append({"channel": ch, "qT_over_Q": r, "quantity": q, "profile": c[q], "published": ref,
                             "abs_difference": diff, "pass": passed})
    return {"rows": rows, "all_pass": ok, "tolerance": {"relative": rel, "absolute": absol}}


# ------------------------------------------------------------------------------------------ LO cross section
def _density(components, x: float) -> float:
    return sum(float(Fraction(str(n))) * x ** float(Fraction(str(a))) * (1.0 - x) ** b for n, a, b in components)


def parton_luminosity(cfg: dict, x1: float, x2: float) -> float:
    """sum_q e_q^2 [q1(x1) qbar2(x2) + qbar1(x1) q2(x2)], both hadrons with the same toy set."""
    if not (0.0 < x1 < 1.0 and 0.0 < x2 < 1.0):
        return 0.0
    tot = 0.0
    for fl in cfg["flavours"]:
        e2 = float(Fraction(fl["charge"])) ** 2
        tot += e2 * (_density(fl["quark"], x1) * _density(fl["antiquark"], x2)
                     + _density(fl["antiquark"], x1) * _density(fl["quark"], x2))
    return tot


def d2sigma_dm_dy(cfg: dict, m: float, y: float) -> float:
    """LO d^2 sigma/dM dy in units of (4 pi alpha^2/3) GeV^-3: (2/3)/(M s) times the parton luminosity."""
    s = cfg["sqrt_s_gev"] ** 2
    x1, x2 = m / math.sqrt(s) * math.exp(y), m / math.sqrt(s) * math.exp(-y)
    return 2.0 / 3.0 / (m * s) * parton_luminosity(cfg, x1, x2)


def box_from_formula(cfg: dict) -> float:
    from scipy.integrate import dblquad
    (m1, m2), (y1, y2) = cfg["mass_window_gev"], cfg["rapidity_window"]
    val, _ = dblquad(lambda y, m: d2sigma_dm_dy(cfg, m, y), m1, m2, y1, y2, epsabs=0.0, epsrel=1e-11)
    return val


def box_from_partons(cfg: dict) -> float:
    """The same box from the parton integral in (x1, x2): sigma = int dx1 dx2 L(x1, x2) sigma_hat(x1 x2 s) over the
    region M1^2 <= x1 x2 s <= M2^2, y1 <= ln(x1/x2)/2 <= y2, sigma_hat = (1/3)(4 pi alpha^2/3)/s_hat (colour average)."""
    from scipy.integrate import quad
    s = cfg["sqrt_s_gev"] ** 2
    (m1, m2), (y1, y2) = cfg["mass_window_gev"], cfg["rapidity_window"]
    rs = math.sqrt(s)

    def inner(x1):
        lo = max(m1 * m1 / (x1 * s), x1 * math.exp(-2.0 * y2))
        hi = min(m2 * m2 / (x1 * s), x1 * math.exp(-2.0 * y1))
        if hi <= lo:
            return 0.0
        v, _ = quad(lambda x2: parton_luminosity(cfg, x1, x2) / (3.0 * x1 * x2 * s), lo, hi,
                    epsabs=0.0, epsrel=1e-12, limit=200)
        return v
    kinks = sorted({m * math.exp(yy) / rs for m in (m1, m2) for yy in (y1, y2)})
    total = 0.0
    for a_, b_ in zip(kinks, kinks[1:]):
        v, _ = quad(inner, a_, b_, epsabs=0.0, epsrel=1e-11, limit=200)
        total += v
    return total


def cross_section_check(cfg: dict | None = None) -> dict:
    cfg = cfg or load_json(TOY_XS)
    a, b = box_from_formula(cfg), box_from_partons(cfg)
    rel = abs(a / b - 1.0)
    return {"box_from_formula": a, "box_from_partons": b, "unit": "(4 pi alpha^2/3) GeV^-2; times 86.8 nb GeV^2 gives nb",
            "box_from_formula_nb": a * NB_GEV2, "relative_difference": rel,
            "pass": rel <= cfg["relative_tolerance"], "label": "SYNTHETIC toy densities"}


# ------------------------------------------------------------------------------------------ prediction
def predict(cfg: dict) -> dict:
    rs, fs = cfg["qT_over_Q"], cfg["qg_fractions"]
    if any(r < 0 for r in rs) or any(not 0.0 <= f <= 1.0 for f in fs):
        raise InputError("qT/Q must be >= 0 and q g fractions in [0, 1]")
    chans = {ch: [dict(qT_over_Q=r, **channel_coefficients(ch, r)) for r in rs] for ch in CHANNELS}
    mix = {str(f): [dict(qT_over_Q=r, **mixture_coefficients(f, r)) for r in rs] for f in fs}
    bench = benchmark_comparison()
    xs = cross_section_check()
    every = [row for rows in list(chans.values()) + list(mix.values()) for row in rows]
    checks = {
        "lam_tung_zero_in_each_channel_and_mixture": all(abs(row["lam_tung"]) <= 1e-14 for row in every),
        "lambda_1_nu_0_at_qT_0": all(abs(rows[0]["lambda"] - 1.0) <= 1e-15 and rows[0]["nu"] == 0.0
                                     for rows in chans.values()) if rs and rs[0] == 0.0 else True,
        "lambda_within_minus_one_third_and_one": all(-1.0 / 3.0 - 1e-15 <= row["lambda"] <= 1.0 + 1e-15 for row in every),
        "qg_lambda_falls_faster_than_qqbar": all(g["lambda"] <= q["lambda"] + 1e-15
                                                  for q, g in zip(chans["qqbar"], chans["qg"])),
        "published_eq10_reproduced": bench["all_pass"],
        "lo_cross_section_jacobian_numerical": xs["pass"],
    }
    return {"channels": chans, "mixtures_average_A": mix,
            "declarations": {"units": "lambda, nu, A_n are dimensionless coefficients of a normalized angular "
                                      "distribution (a statement, not a computed check)"},
            "benchmark": bench, "lo_cross_section_check": xs, "checks": checks,
            "status": "perturbative-argument at O(alpha_s); photon exchange; prediction, not a measurement"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}"}))
        return 3
    try:
        out = predict(load_json(opts.config))
    except (InputError, KeyError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

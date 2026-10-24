#!/usr/bin/env python3
"""Numerical predictions of theory:dis-parton-model: LO quark-parton-model F_2 (photon exchange) and the O(alpha_s)
longitudinal structure function F_L, on SYNTHETIC toy densities.

F_2(x) = x sum_q e_q^2 (q(x) + qbar(x))                                   (PDG Eq. 18.18, dispm:C01)
F_L(x) = (alpha_s / 4 pi) x^2 int_x^1 dz/z^3 [ 4 C_F F_2(z) + 8 sum_q e_q^2 (1 - x/z) z g(z) ]
The F_L form follows from x^-1 F_L = C_L,ns (x) q_ns + <e^2> (C_L,q (x) q_s + C_L,g (x) g) with the O(alpha_s)
coefficients c_L,ns = 4 C_F x, c_L,ps = 0, c_L,g = 8 n_f x (1 - x) (Moch, Vermaseren and Vogt, Eqs. 1-3, dispm:C03,
C04) and the convolution of PDG Eq. 18.22 (dispm:C02); the change of variables is done in SymPy in derive.py.
mu_R = mu_F = Q; target mass and quark masses neglected; photon exchange only.

The densities and the alpha_s values come from the config and are SYNTHETIC (benchmarks/toy-closed-form.json); the
output is not a statement about any nucleon. Integrals are computed by adaptive quadrature in t = ln z; F_L is also
computed by the convolution route in the original variable y (independent of the change of variables) and by a
Gauss-Legendre rule for a convergence study.

Usage: python3 predict.py [--config ../benchmarks/toy-closed-form.json] [--out prediction.json]
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
DEFAULT_CONFIG = HERE.parent / "benchmarks" / "toy-closed-form.json"


class InputError(ValueError):
    """A config that cannot describe a valid toy input."""


def rational(v) -> Fraction:
    return Fraction(str(v))


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_config(cfg: dict) -> None:
    if not cfg.get("flavours"):
        raise InputError("no quark flavours given")
    for fl in cfg["flavours"]:
        for part in ("quark", "antiquark"):
            for comp in fl.get(part, []):
                if rational(comp[0]) < 0 or not isinstance(comp[2], int) or comp[2] < 0:
                    raise InputError(f"{fl['name']} {part}: need N >= 0 and an integer b >= 0, got {comp}")
    for comp in cfg.get("gluon", []):
        if rational(comp[0]) < 0 or not isinstance(comp[2], int) or comp[2] < 0:
            raise InputError(f"gluon: need N >= 0 and an integer b >= 0, got {comp}")
    if len(cfg["q2_points_gev2"]) != len(cfg["alpha_s_at_q2"]):
        raise InputError("one alpha_s value per Q^2 point")
    if any(not 0.0 < x < 1.0 for x in cfg["x_points"]):
        raise InputError("x points must lie in (0, 1)")
    if any(a < 0 for a in cfg["alpha_s_at_q2"]):
        raise InputError("alpha_s must be non-negative")


def density(components, x: float) -> float:
    """Number density sum_k N_k x^a_k (1 - x)^b_k."""
    return sum(float(rational(n)) * x ** float(rational(a)) * (1.0 - x) ** b for n, a, b in components)


def sum_e2(cfg: dict) -> float:
    return sum(float(rational(fl["charge"])) ** 2 for fl in cfg["flavours"])


def f2(cfg: dict, x: float) -> float:
    """LO quark-parton-model F_2, photon exchange (PDG Eq. 18.18)."""
    return x * sum(float(rational(fl["charge"])) ** 2 * (density(fl["quark"], x) + density(fl["antiquark"], x))
                   for fl in cfg["flavours"])


def gluon(cfg: dict, x: float) -> float:
    return density(cfg.get("gluon", []), x)


def fl_integrand(cfg: dict, x: float, z: float) -> float:
    """Integrand of the Altarelli-Martinelli form, without the alpha_s/(4 pi) x^2 prefactor."""
    cf = float(rational(cfg["C_F"]))
    return (4.0 * cf * f2(cfg, z) + 8.0 * sum_e2(cfg) * (1.0 - x / z) * z * gluon(cfg, z)) / z ** 3


def fl_over_as(cfg: dict, x: float) -> tuple[float, float]:
    """F_L / alpha_s by adaptive quadrature in t = ln z; returns (value, quadrature error estimate)."""
    from scipy.integrate import quad
    val, err = quad(lambda t: fl_integrand(cfg, x, math.exp(t)) * math.exp(t), math.log(x), 0.0,
                    epsabs=0.0, epsrel=1e-13, limit=200)
    pref = x * x / (4.0 * math.pi)
    return pref * val, pref * err


def fl(cfg: dict, x: float, alpha_s: float) -> float:
    return alpha_s * fl_over_as(cfg, x)[0]


def fl_convolution_route(cfg: dict, x: float, alpha_s: float) -> float:
    """F_L from x^-1 F_L = a_s [c_L,ns (x) sum e^2 (q + qbar) + <e^2> c_L,g (x) g] directly in the convolution variable y
    (PDG Eq. 18.22: C (x) f = int_x^1 dy/y C(y) f(x/y)), with c_L,ns = 4 C_F y and c_L,g = 8 n_f y (1 - y). No change of
    variables: an independent numerical route to the same number."""
    from scipy.integrate import quad
    cf = float(rational(cfg["C_F"]))
    nf = len(cfg["flavours"])
    e2_avg = sum_e2(cfg) / nf

    def integrand(u):  # y = exp(u), dy/y = du
        y = math.exp(u)
        xi = x / y
        return 4.0 * cf * y * f2(cfg, xi) / xi + e2_avg * 8.0 * nf * y * (1.0 - y) * gluon(cfg, xi)
    val, _ = quad(integrand, math.log(x), 0.0, epsabs=0.0, epsrel=1e-13, limit=200)
    return x * alpha_s / (4.0 * math.pi) * val


def fl_gauss_legendre(cfg: dict, x: float, alpha_s: float, nodes: int) -> float:
    """F_L by an n-point Gauss-Legendre rule in t = ln z on [ln x, 0] (convergence study)."""
    import numpy as np
    t, w = np.polynomial.legendre.leggauss(nodes)
    lo, hi = math.log(x), 0.0
    ts = 0.5 * (hi - lo) * t + 0.5 * (hi + lo)
    s = sum(wi * fl_integrand(cfg, x, math.exp(ti)) * math.exp(ti) for ti, wi in zip(ts, w))
    return alpha_s * x * x / (4.0 * math.pi) * 0.5 * (hi - lo) * s


def predict(cfg: dict) -> dict:
    check_config(cfg)
    xs, q2s, alphas = cfg["x_points"], cfg["q2_points_gev2"], cfg["alpha_s_at_q2"]
    rows = []
    for q2, a_s in zip(q2s, alphas):
        for x in xs:
            per_as, err = fl_over_as(cfg, x)
            rows.append({"x": x, "q2_gev2": q2, "alpha_s": a_s, "F2": f2(cfg, x), "FL": a_s * per_as,
                         "FL_quadrature_error": a_s * err,
                         "FL_convolution_route": fl_convolution_route(cfg, x, a_s)})
    tol = cfg["relative_tolerance"]
    checks = {
        "FL_non_negative": all(r["FL"] >= 0.0 for r in rows),
        "FL_not_above_F2": all(r["FL"] <= r["F2"] for r in rows),
        "FL_vanishes_as_alpha_s_to_0": all(fl(cfg, x, 0.0) == 0.0 for x in xs)
        and all(abs(fl(cfg, x, 1e-6) / 1e-6 - fl_over_as(cfg, x)[0]) <= tol * fl_over_as(cfg, x)[0] for x in xs),
        "convolution_route_equals_AM_form": all(abs(r["FL_convolution_route"] - r["FL"]) <= tol * abs(r["FL"])
                                                for r in rows),
        "quadrature_error_below_tolerance": all(r["FL_quadrature_error"] <= tol * r["FL"] for r in rows),
    }
    return {"label": "SYNTHETIC toy densities; F_2 at O(alpha_s^0), F_L at O(alpha_s^1); not a statement about any "
                     "nucleon", "n_f": len(cfg["flavours"]), "sum_e2": sum_e2(cfg), "rows": rows, "checks": checks,
            "declarations": {"units": "x, F_2, F_L and alpha_s are dimensionless; Q^2 (GeV^2) only labels alpha_s "
                                      "(a statement, not a computed check)"},
            "status": "perturbative-argument at O(alpha_s); synthetic inputs; prediction, not a measurement"}


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

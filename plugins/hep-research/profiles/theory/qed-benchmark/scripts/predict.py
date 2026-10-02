#!/usr/bin/env python3
"""Numerical predictions of theory:qed-benchmark (tree-level e+e- -> mu+mu-, one photon, massless limit).

sigma(s) = K / s with K = 4 pi alpha^2 / 3 = 86.8 nb GeV^2 (PDG eq. 51.3, qedbench:C02);
d sigma / d cos theta = (3/8) sigma (1 + cos^2 theta) (derived in scripts/derive.py). Computes bin-averaged
values from analytic bin integrals, the integrated and fiducial cross sections, and an integration study:
trapezoid and Simpson rules on 3...257 points and scipy.integrate.quad against the analytic integrals, with the
observed convergence order. Numerical agreement is corroboration on a finite set of checks, not proof.

Usage: python3 predict.py [--config ../benchmarks/path-c.json] [--sqrt-s 10] [--out prediction.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE.parent / "benchmarks" / "path-c.json"
NB_TO_PB = 1000.0


def sigma_pb(sqrt_s: float, k_nb_gev2: float) -> float:
    return k_nb_gev2 / sqrt_s ** 2 * NB_TO_PB


def dsigma_dcos(c, sqrt_s: float, k_nb_gev2: float):
    return 3.0 / 8.0 * sigma_pb(sqrt_s, k_nb_gev2) * (1.0 + np.asarray(c, dtype=float) ** 2)


def bin_integral(lo, hi, sqrt_s, k):
    prim = lambda c: c + c ** 3 / 3.0  # noqa: E731
    return 3.0 / 8.0 * sigma_pb(sqrt_s, k) * (prim(hi) - prim(lo))


def _trapezoid(f, lo, hi, n):
    x = np.linspace(lo, hi, n)
    y = f(x)
    return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))


def _simpson(f, lo, hi, n):
    if n % 2 == 0:
        raise ValueError("Simpson needs an odd number of points")
    x = np.linspace(lo, hi, n)
    h = (hi - lo) / (n - 1)
    y = f(x)
    return float(h / 3.0 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum()))


def convergence(sqrt_s, k, lo, hi, points):
    """Integration study on [lo, hi]: absolute errors per rule and the observed order log2(e_n / e_2n)."""
    from scipy.integrate import quad
    f = lambda c: dsigma_dcos(c, sqrt_s, k)  # noqa: E731
    exact = bin_integral(lo, hi, sqrt_s, k)
    trap = [abs(_trapezoid(f, lo, hi, n) - exact) for n in points]
    simp = [abs(_simpson(f, lo, hi, n) - exact) for n in points]
    q, qerr = quad(f, lo, hi, epsabs=0, epsrel=1e-13)
    orders = [math.log2(trap[i] / trap[i + 1]) for i in range(len(points) - 1) if trap[i + 1] > 0]
    return {"interval": [lo, hi], "exact_pb": exact, "points": list(points), "trapezoid_abs_error": trap,
            "simpson_abs_error": simp, "trapezoid_observed_order": orders, "quad_value_pb": q,
            "quad_reported_error": qerr, "quad_abs_error": abs(q - exact)}


def predict(cfg: dict, sqrt_s: float | None = None) -> dict:
    rs = cfg["sqrt_s_gev"] if sqrt_s is None else sqrt_s
    k = cfg["reference_constant_nb_gev2"]
    edges = np.asarray(cfg["edges"], dtype=float)
    width = np.diff(edges)
    integ = np.array([bin_integral(a, b, rs, k) for a, b in zip(edges[:-1], edges[1:])])
    cut = cfg["fiducial_abs_cos_max"]
    total = sigma_pb(rs, k)
    fid = bin_integral(-cut, cut, rs, k)
    rel_param = cfg["reference_constant_rounding_nb_gev2"] / k
    conv = convergence(rs, k, -1.0, 1.0, cfg["convergence_points"])
    return {
        "sqrt_s_gev": rs, "s_gev2": rs ** 2, "reference_constant_nb_gev2": k,
        "sigma_total_pb": total, "sigma_fiducial_pb": fid, "fiducial_abs_cos_max": cut,
        "edges": edges.tolist(), "dsigma_dcos_bin_averaged_pb": (integ / width).tolist(),
        "relative_uncertainty_reference_rounding": rel_param,
        "convergence": conv,
    } | {"checks": {k: bool(v) for k, v in {
        "integral_over_full_range_equals_sigma": abs(bin_integral(-1, 1, rs, k) / total - 1) < 1e-14,
        "bins_sum_to_sigma": abs(integ.sum() / total - 1) < 1e-12,
        "even_in_cos_theta": np.allclose(integ, integ[::-1], rtol=1e-14),
        "positive": np.all(integ > 0),
        "forward_to_central_ratio_is_2": abs(dsigma_dcos(1.0, rs, k) / dsigma_dcos(0.0, rs, k) - 2.0) < 1e-14,
        "scales_as_1_over_s": abs(sigma_pb(2 * rs, k) * 4 / total - 1) < 1e-14,
        "trapezoid_second_order": all(abs(o - 2.0) < 0.05 for o in conv["trapezoid_observed_order"][2:]),
        "simpson_exact_for_quadratic": max(conv["simpson_abs_error"]) < 1e-9 * total,
        "quad_agrees": conv["quad_abs_error"] < 1e-10 * total,
    }.items()}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--sqrt-s", type=float)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    res = predict(json.loads(args.config.read_text(encoding="utf-8")), args.sqrt_s)
    text = json.dumps(res, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(res["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

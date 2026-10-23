#!/usr/bin/env python3
"""Numerical predictions of theory:tmd-gaussian-lo: Gaussian-ansatz TMDs at leading order, no evolution.

Closed forms (derived in derive.py, or published and re-derived there):
  F_UU,T(x, z, P) = x sum e_q^2 f_q(x) D_q(z) exp(-P^2/<P_T^2>)/(pi <P_T^2>), <P_T^2> = <p^2> + z^2 <k^2>
      (Anselmino et al. Eqs. 34-39; Bacchetta et al. Eqs. 4.1-4.2, 4.21)
  Cahn term: [1 + (1-y)^2 - 4 (2-y) sqrt(1-y) <k^2> z P cos(phi_h)/(<P_T^2> Q)] (Anselmino et al. Eq. 38)
  Sivers asymmetry A_UT^sin(phi_h - phi_S) = Delta sigma_Siv / sigma_0 (Anselmino et al. Eqs. 64-67)
  Drell-Yan q_T shape exp(-q_T^2/<q_T^2>)/(pi <q_T^2>), <q_T^2> = <k1^2> + <k2^2> (derived here)
  Sivers function in Drell-Yan = - Sivers function in SIDIS (Trento conventions Eq. 14, cited)
Second numerical route: every closed form is also computed by 2D adaptive quadrature of the profile's transcription
of its defining k_perp integral (same route as the paper: a check of algebra and transcription, not physics) (Eq. 32 with Eqs. 33-35; Eq. 58 with Eqs. 63 and 68; the Drell-Yan convolution).

Inputs (benchmarks/toy-inputs.json): collinear values, Sivers normalizations and Drell-Yan widths are SYNTHETIC; the
SIDIS widths and M'^2 are the paper's fitted values used as ILLUSTRATIVE settings.

Usage: python3 predict.py [--config ../benchmarks/toy-inputs.json] [--out prediction.json]
Exit 0 all checks pass, 1 a check fails, 2 bad input, 3 numpy/scipy missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
DEFAULT_CONFIG = PROFILE / "benchmarks" / "toy-inputs.json"
BENCHMARK = PROFILE / "benchmarks" / "anselmino-closed-forms.json"
PROCESSES = ("SIDIS", "DY")


class InputError(ValueError):
    """Input the profile cannot use."""


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _positive(name: str, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
        raise InputError(f"{name} must be a finite number > 0, got {v!r}")
    return float(v)


def gauss2(v2: float, w: float) -> float:
    """Normalized 2D Gaussian exp(-v^2/w)/(pi w) at |v|^2 = v2."""
    return math.exp(-v2 / w) / (math.pi * w)


def pt2_width(z: float, kperp2: float, pperp2: float) -> float:
    """Eq. 39."""
    return pperp2 + z * z * kperp2


def collinear(cfg: dict) -> float:
    """x sum e_q^2 f_q(x) D_q(z) (Bacchetta et al. Eq. 4.21)."""
    return cfg["x"] * sum(float(Fraction(fl["charge"])) ** 2 * fl["f"] * fl["D"] for fl in cfg["flavours"])


def fuu_closed(cfg: dict, pht: float) -> float:
    z = cfg["z"]
    return collinear(cfg) * gauss2(pht * pht, pt2_width(z, cfg["kperp2_gev2"], cfg["pperp2_gev2"]))


def _box(*widths: float) -> float:
    return 12.0 * math.sqrt(max(widths))


def _int2(fun, half: float) -> float:
    from scipy.integrate import dblquad
    val, _ = dblquad(lambda b, a: fun(a, b), -half, half, -half, half, epsabs=0.0, epsrel=1e-11)
    return val


def fuu_numeric(cfg: dict, pht: float, phi_h: float = 0.0) -> float:
    """x sum e^2 int d^2k f(x, k) D(z, P - z k), Gaussian k and p dependence (Eqs. 32, 34-35)."""
    z, k2, p2 = cfg["z"], cfg["kperp2_gev2"], cfg["pperp2_gev2"]
    px, py = pht * math.cos(phi_h), pht * math.sin(phi_h)
    core = _int2(lambda kx, ky: gauss2(kx * kx + ky * ky, k2) * gauss2((px - z * kx) ** 2 + (py - z * ky) ** 2, p2),
                 _box(k2, p2))
    return collinear(cfg) * core


def cahn_ratio_closed(z, pht, y, q, phi_h, kperp2, pperp2) -> float:
    """[1 + (1-y)^2 - 4 (2-y) sqrt(1-y) <k^2> z P cos(phi_h)/(<P_T^2> Q)] / [1 + (1-y)^2] (Eq. 38)."""
    w = pt2_width(z, kperp2, pperp2)
    unpol = 1 + (1 - y) ** 2
    return (unpol - 4 * (2 - y) * math.sqrt(1 - y) * kperp2 * z * pht * math.cos(phi_h) / (w * q)) / unpol


def cahn_ratio_numeric(z, pht, y, q, phi_h, kperp2, pperp2) -> float:
    """The same ratio from Eq. 32 with hat-s^2 + hat-u^2 of Eq. 33 (lepton plane along x), integrated numerically."""
    px, py = pht * math.cos(phi_h), pht * math.sin(phi_h)
    unpol = 1 + (1 - y) ** 2
    half = _box(kperp2, pperp2)

    def weight(kx, ky):
        return gauss2(kx * kx + ky * ky, kperp2) * gauss2((px - z * kx) ** 2 + (py - z * ky) ** 2, pperp2)
    num = _int2(lambda kx, ky: (unpol - 4 * (2 - y) * math.sqrt(1 - y) * kx / q) * weight(kx, ky), half)
    return num / (unpol * _int2(weight, half))


def k_hat2(kperp2: float, mprime2: float) -> float:
    """Eq. 67."""
    return mprime2 * kperp2 / (mprime2 + kperp2)


def sivers_asymmetry_closed(z, pht, n, kperp2, pperp2, mprime2) -> float:
    """Single flavour Delta sigma_Siv / sigma_0 of Eqs. 64-67 (common factors and f, D, e_q^2 cancel)."""
    kh = k_hat2(kperp2, mprime2)
    ph = pperp2 + z * z * kh
    w = pt2_width(z, kperp2, pperp2)
    dsig = 2 * n * z * pht * math.sqrt(2 * math.e) * kh ** 2 / (math.sqrt(mprime2) * ph ** 2 * kperp2) \
        * math.exp(-pht ** 2 / ph)
    sig0 = 2 * math.pi * math.exp(-pht ** 2 / w) / (math.pi * w)
    return dsig / sig0


def sivers_function(k: float, n: float, f: float, kperp2: float, mprime2: float, process: str = "SIDIS") -> float:
    """Delta^N f(x, k) = 2 N h'(k) f(x, k) (Eqs. 63, 68) in the SIDIS convention; the Drell-Yan function is its
    negative (f_1T^perp,DY = -f_1T^perp,SIDIS, Trento Eq. 14; Delta^N f is proportional to f_1T^perp, Trento Eq. 4)."""
    if process not in PROCESSES:
        raise InputError(f"process must be one of {PROCESSES}, got {process!r}")
    sidis = 2 * n * math.sqrt(2 * math.e) * k / math.sqrt(mprime2) * math.exp(-k * k / mprime2) * f * gauss2(k * k,
                                                                                                         kperp2)
    out = sidis if process == "SIDIS" else -sidis
    return out + 0.0  # -0.0 -> 0.0 for a zero Sivers normalization


def sivers_asymmetry_numeric(z, pht, n, kperp2, pperp2, mprime2) -> float:
    """Eq. 58 at leading power with Eq. 68: the phi_S integral gives pi cos(phi - phi_h) (derive.py); with P_T along x
    the numerator is (1/2pi) pi 2pi int d^2k Delta^N f (k_x/k) D(z, P - z k), the denominator (1/2pi)(2pi)^2 int f D."""
    half = _box(kperp2, pperp2)

    def dfrag(kx, ky):
        return gauss2((pht - z * kx) ** 2 + (z * ky) ** 2, pperp2)

    def num_int(kx, ky):
        k = math.hypot(kx, ky)
        return 0.0 if k == 0 else sivers_function(k, n, 1.0, kperp2, mprime2) * (kx / k) * dfrag(kx, ky)
    num = math.pi * _int2(num_int, half)
    den = 2 * math.pi * _int2(lambda kx, ky: gauss2(kx * kx + ky * ky, kperp2) * dfrag(kx, ky), half)
    return num / den


def dy_shape_closed(qt: float, k1: float, k2: float) -> float:
    return gauss2(qt * qt, k1 + k2)


def dy_shape_numeric(qt: float, k1: float, k2: float) -> float:
    return _int2(lambda kx, ky: gauss2(kx * kx + ky * ky, k1) * gauss2((qt - kx) ** 2 + ky ** 2, k2), _box(k1, k2))


def benchmark_comparison(bench: dict | None = None) -> dict:
    bench = bench or load_json(BENCHMARK)
    s = bench["settings"]
    tol = bench["relative_tolerance"]
    rows, ok = [], True
    for pt in bench["points"]:
        z, p = pt["z"], pt["PhT_gev"]
        for name, closed, num in (
                ("cahn_ratio_eq38", cahn_ratio_closed(z, p, s["y"], s["Q_gev"], 0.0, s["kperp2_gev2"], s["pperp2_gev2"]),
                 cahn_ratio_numeric(z, p, s["y"], s["Q_gev"], 0.0, s["kperp2_gev2"], s["pperp2_gev2"])),
                ("sivers_asymmetry_eqs64_67",
                 sivers_asymmetry_closed(z, p, s["N_single_flavour"], s["kperp2_gev2"], s["pperp2_gev2"],
                                         s["Mprime2_gev2"]),
                 sivers_asymmetry_numeric(z, p, s["N_single_flavour"], s["kperp2_gev2"], s["pperp2_gev2"],
                                          s["Mprime2_gev2"]))):
            rel = abs(num / closed - 1.0)
            ok &= rel <= tol
            rows.append({"quantity": name, "z": z, "PhT_gev": p, "published_closed_form": closed,
                         "profile_quadrature": num, "relative_difference": rel, "pass": rel <= tol})
    return {"rows": rows, "all_pass": ok, "relative_tolerance": tol}


def check_config(cfg: dict) -> None:
    for key in ("x", "z"):
        if not 0.0 < cfg[key] <= 1.0:
            raise InputError(f"{key} must lie in (0, 1], got {cfg[key]}")
    for key in ("kperp2_gev2", "pperp2_gev2"):
        _positive(key, cfg[key])
    _positive("Mprime2_gev2", cfg["sivers"]["Mprime2_gev2"])
    for key in ("k1perp2_gev2", "k2perp2_gev2"):
        _positive(key, cfg["drell_yan"][key])
    for fl in cfg["flavours"]:
        if fl["f"] < 0 or fl["D"] < 0:
            raise InputError(f"collinear values must be >= 0 ({fl['name']})")
    if any(p < 0 for p in cfg["PhT_gev"]) or any(q < 0 for q in cfg["drell_yan"]["qT_gev"]):
        raise InputError("P_hT and q_T must be >= 0")


def predict(cfg: dict) -> dict:
    check_config(cfg)
    z, k2, p2 = cfg["z"], cfg["kperp2_gev2"], cfg["pperp2_gev2"]
    tol = cfg["relative_tolerance"]
    c = cfg["cahn"]
    fuu = [{"PhT_gev": p, "F_UU_T": fuu_closed(cfg, p), "F_UU_T_quadrature": fuu_numeric(cfg, p, 0.7),
            "cahn_ratio": cahn_ratio_closed(z, p, c["y"], c["Q_gev"], c["phi_h"], k2, p2)} for p in cfg["PhT_gev"]]
    sv = cfg["sivers"]
    by_flavour = {fl["name"]: fl for fl in cfg["flavours"]}
    # several flavours: A = sum_q e^2 f D N_q (single-flavour shape) / sum_q e^2 f D (Eqs. 65-66)
    w = [(float(Fraction(fl["charge"])) ** 2 * fl["f"] * fl["D"], sv["N"].get(fl["name"], 0.0)) for fl in cfg["flavours"]]
    wsum = sum(a for a, _ in w)
    asym = [{"PhT_gev": p, "A_UT_sin_phih_minus_phiS":
             sum(a * sivers_asymmetry_closed(z, p, n_, k2, p2, sv["Mprime2_gev2"]) for a, n_ in w) / wsum}
            for p in cfg["PhT_gev"]]
    sivers_fn = [{"flavour": name, "k_gev": k,
                  **{f"Delta_N_f_{proc}": sivers_function(k, sv["N"].get(name, 0.0), by_flavour[name]["f"], k2,
                                                          sv["Mprime2_gev2"], proc) for proc in PROCESSES}}
                 for name in sv["N"] for k in sv["k_gev"]]
    d = cfg["drell_yan"]
    dy = [{"qT_gev": q, "shape_per_gev2": dy_shape_closed(q, d["k1perp2_gev2"], d["k2perp2_gev2"]),
           "shape_quadrature": dy_shape_numeric(q, d["k1perp2_gev2"], d["k2perp2_gev2"])} for q in d["qT_gev"]]
    bench = benchmark_comparison()
    from scipy.integrate import quad
    norm_fuu = 2 * math.pi * quad(lambda p: p * fuu_closed(cfg, p), 0, math.inf, epsabs=0, epsrel=1e-12)[0]
    norm_dy = 2 * math.pi * quad(lambda q: q * dy_shape_closed(q, d["k1perp2_gev2"], d["k2perp2_gev2"]), 0, math.inf,
                                 epsabs=0, epsrel=1e-12)[0]
    checks = {
        "F_UU_T_closed_form_equals_quadrature": all(abs(r["F_UU_T_quadrature"] / r["F_UU_T"] - 1) <= tol for r in fuu),
        "F_UU_T_integrates_to_collinear": abs(norm_fuu / collinear(cfg) - 1) <= tol,
        "dy_shape_closed_form_equals_quadrature": all(abs(r["shape_quadrature"] / r["shape_per_gev2"] - 1) <= tol
                                                      for r in dy),
        "dy_shape_unit_normalized": abs(norm_dy - 1) <= tol,
        "sivers_asymmetry_zero_at_PhT_0": all(r["A_UT_sin_phih_minus_phiS"] == 0.0 for r in asym if r["PhT_gev"] == 0),
        "cahn_ratio_one_at_PhT_0": all(r["cahn_ratio"] == 1.0 for r in fuu if r["PhT_gev"] == 0),
        "published_closed_forms_reproduced_by_quadrature": bench["all_pass"],
    }
    return {"PT2_width_gev2": pt2_width(z, k2, p2), "collinear_F_UU_T": collinear(cfg), "F_UU_T": fuu,
            "sivers_asymmetry_sidis": asym, "sivers_function": sivers_fn, "drell_yan_qT_shape": dy,
            "qT2_width_gev2": d["k1perp2_gev2"] + d["k2perp2_gev2"], "benchmark": bench, "checks": checks,
            "declarations": {"sivers_sign_rule": "Delta^N f(DY) = -Delta^N f(SIDIS): the cited Trento Eq. 14 "
                                                 "rule applied by construction (a declaration, not a check)",
                             "units": "widths in GeV^2, P_hT and q_T in GeV; F_UU,T and the q_T shape per GeV^2; "
                                      "asymmetries dimensionless (a statement, not a computed check)"},
            "status": "heuristic-argument (Gaussian ansatz, no evolution); prediction, not a measurement"}


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

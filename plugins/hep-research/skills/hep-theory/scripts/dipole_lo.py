#!/usr/bin/env python3
"""Dipole picture of small-x DIS at leading order: photon wave functions, the GBW dipole cross section, sigma_T,
sigma_L, F_2 and F_L, with a convergence report (Th19).

Purpose: a checkable dipole-model calculation with every model input explicit. See
<plugin root>/skills/hep-theory/references/small-x-and-saturation.md.
Formulas (Golec-Biernat and Wusthoff, arXiv:hep-ph/9807513v2, Phys. Rev. D 59 (1998) 014017, read 2026-10-23):
  sigma_T,L(x, Q^2) = int d^2r int_0^1 dz |Psi_T,L(z, r)|^2 sigma_hat(x, r^2)                                (Eq. 1)
  |Psi_T|^2 = (6 alpha_em / 4 pi^2) sum_f e_f^2 { [z^2 + (1 - z)^2] eps^2 K_1^2(eps r) + m_f^2 K_0^2(eps r) }   (Eq. 2)
  |Psi_L|^2 = (6 alpha_em / 4 pi^2) sum_f e_f^2 4 Q^2 z^2 (1 - z)^2 K_0^2(eps r),  eps^2 = z(1 - z) Q^2 + m_f^2 (Eqs. 3-4)
  F_2 = F_T + F_L,  F_T,L = Q^2 / (4 pi^2 alpha_em) sigma_T,L                                                (Eqs. 5-6)
  GBW: sigma_hat = sigma_0 [1 - exp(-r_hat^2)], r_hat = r / (2 R_0), R_0 = (1/Q_0)(x/x_0)^(lambda/2), Q_0 = 1 GeV
       (Eqs. 7-10); i.e. sigma_hat = sigma_0 [1 - exp(-r^2 Q_s^2 / 4)] with Q_s^2 = Q_0^2 (x_0/x)^lambda
  x variable: Bjorken x, or the mass-modified x~ = x (Q^2 + 4 m_f^2) / Q^2 per flavour (Eq. 21)
sigma_0, x_0, lambda and the quark masses are model parameters from one fit, supplied by the user with their source;
the x variable must be the one the parameters were fitted with. alpha_em cancels in F_T,L and enters sigma_T,L.
Integration: r on a logarithmic grid in [r_min, r_max] (trapezoid in ln r), z by Gauss-Legendre; the convergence report
reruns with doubled nodes, then (at those nodes) with r_max doubled and r_min divided by 10.
Qs2_GeV2_at_input_x uses the input x (with the mass-modified variable each flavour uses its own x~). K_0, K_1 from scipy.special (core stack).
Derivation status: heuristic-argument (dipole model); the wave functions are LO QED.
Exit codes (core/status.py): 0 ok; 1 refused (x variable different from the fit's, x above the user's --x-max);
2 rejected (unknown model, missing or non-positive parameters, unreadable flavours, non-finite values); 3
missing-dependency (SciPy absent).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

MODELS = ("gbw",)
Q0_GEV = 1.0  # GBW Eq. 7 sets the dimension with Q_0 = 1 GeV (a definition of the model, not a fit value)


class DipoleError(ValueError):
    def __init__(self, msg: str, status: str = "rejected"):
        super().__init__(msg)
        self.status = status


def parse_flavours(text: str) -> list[tuple[str, float, float]]:
    """name:charge:mass_GeV,... e.g. u:2/3:0.14,d:-1/3:0.14"""
    out = []
    for item in text.split(","):
        try:
            name, charge, mass = item.split(":")
            num, _, den = charge.partition("/")
            e = float(num) / (float(den) if den else 1.0)
            m = float(mass)
        except (ValueError, ZeroDivisionError) as exc:
            raise DipoleError(f"--flavours items are name:charge:mass, got {item!r}") from exc
        if name in [f[0] for f in out]:
            raise DipoleError(f"flavour {name} is listed twice")
        if not (math.isfinite(e) and math.isfinite(m) and m >= 0 and e != 0):
            raise DipoleError(f"flavour {name}: need a non-zero charge and a mass >= 0")
        out.append((name, e, m))
    if not out:
        raise DipoleError("--flavours is empty")
    return out


def gbw_sigma_hat(r: float, x: float, sigma0: float, x0: float, lam: float) -> float:
    qs2 = Q0_GEV ** 2 * (x0 / x) ** lam
    return sigma0 * (-math.expm1(-r * r * qs2 / 4.0))


def cross_sections(x, q2, flavours, sigma0_gev2, x0, lam, xvar, alpha, n_r, n_z, r_min, r_max):
    import numpy as np
    from scipy.special import k0, k1

    zs, wz = np.polynomial.legendre.leggauss(n_z)
    zs, wz = 0.5 * (zs + 1.0), 0.5 * wz
    lnr = np.linspace(math.log(r_min), math.log(r_max), n_r)
    rs = np.exp(lnr)
    sig_t = sig_l = 0.0
    pref = 6.0 * alpha / (4.0 * math.pi ** 2)
    for _, e, m in flavours:
        xf = x * (q2 + 4 * m * m) / q2 if xvar == "mass-modified" else x
        R, Z = np.meshgrid(rs, zs, indexing="ij")
        eps = np.sqrt(Z * (1 - Z) * q2 + m * m)
        er = eps * R
        kk0, kk1 = k0(er), k1(er)
        psi_t = pref * e * e * ((Z ** 2 + (1 - Z) ** 2) * eps ** 2 * kk1 ** 2 + m * m * kk0 ** 2)
        psi_l = pref * e * e * 4.0 * q2 * Z ** 2 * (1 - Z) ** 2 * kk0 ** 2
        qs2 = Q0_GEV ** 2 * (x0 / xf) ** lam
        sh = sigma0_gev2 * (-np.expm1(-R * R * qs2 / 4.0))
        # d^2r = 2 pi r dr = 2 pi r^2 d ln r
        jac = 2.0 * math.pi * R * R
        it = (psi_t * sh * jac) @ wz
        il = (psi_l * sh * jac) @ wz
        sig_t += float(np.trapezoid(it, lnr))
        sig_l += float(np.trapezoid(il, lnr))
    return sig_t, sig_l


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--x", type=float, required=True)
    ap.add_argument("--Q2", type=float, required=True, help="GeV^2")
    ap.add_argument("--flavours", required=True, help="name:charge:mass_GeV,... (masses are model parameters)")
    ap.add_argument("--model", required=True, help="dipole model; implemented: gbw")
    ap.add_argument("--sigma0-mb", type=float)
    ap.add_argument("--x0", type=float)
    ap.add_argument("--lambda", dest="lam", type=float)
    ap.add_argument("--parameter-source", required=True, help="the fit the parameters come from (one fit only)")
    ap.add_argument("--x-variable", choices=("bjorken", "mass-modified"), required=True)
    ap.add_argument("--fit-x-variable", choices=("bjorken", "mass-modified"), required=True,
                    help="the x variable the parameters were fitted with")
    ap.add_argument("--x-max", type=float, required=True, help="the user's upper validity limit in x")
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--alpha-label", required=True)
    ap.add_argument("--n-r", type=int, default=400)
    ap.add_argument("--n-z", type=int, default=64)
    ap.add_argument("--r-min", type=float, default=1e-4, help="GeV^-1")
    ap.add_argument("--r-max", type=float, default=50.0, help="GeV^-1")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    defaults = [k for k in ("n-r", "n-z", "r-min", "r-max", "status") if f"--{k}" not in given]
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": defaults}
    try:
        if a.model not in MODELS:
            raise DipoleError(f"unknown dipole model {a.model!r}; implemented: {MODELS} (others are plug-ins to add)")
        for name, v in (("--sigma0-mb", a.sigma0_mb), ("--x0", a.x0), ("--lambda", a.lam)):
            if v is None or not math.isfinite(v) or v <= 0:
                raise DipoleError(f"{name} is required for gbw and must be > 0")
        for name, v in (("--x", a.x), ("--Q2", a.Q2), ("--alpha", a.alpha), ("--x-max", a.x_max),
                        ("--r-min", a.r_min), ("--r-max", a.r_max)):
            if not math.isfinite(v) or v <= 0:
                raise DipoleError(f"{name} must be > 0")
        if a.r_min >= a.r_max or a.n_r < 20 or a.n_z < 8:
            raise DipoleError("need r_min < r_max, n_r >= 20, n_z >= 8")
        if a.x > 1:
            raise DipoleError("x must be in (0, 1]")
        flavours = parse_flavours(a.flavours)
        if a.x_variable != a.fit_x_variable:
            raise DipoleError(f"the parameters were fitted with x = {a.fit_x_variable}; using {a.x_variable} mixes "
                              "conventions", status="refused")
        if a.x > a.x_max:
            raise DipoleError(f"x = {a.x} is above the declared validity limit {a.x_max}", status="refused")
        try:
            import numpy  # noqa: F401
            import scipy.special  # noqa: F401
        except ImportError as exc:
            raise DipoleError(f"SciPy and NumPy are needed: {exc}", status="missing-dependency") from exc
        mb_per_gev2 = constants.hbar_c_squared("GeV^2 mb").value
        s0 = a.sigma0_mb / mb_per_gev2
        args = (a.x, a.Q2, flavours, s0, a.x0, a.lam, a.x_variable, a.alpha)
        st, sl = cross_sections(*args, a.n_r, a.n_z, a.r_min, a.r_max)
        st2, sl2 = cross_sections(*args, 2 * a.n_r, 2 * a.n_z, a.r_min, a.r_max)
        st3, sl3 = cross_sections(*args, 2 * a.n_r, 2 * a.n_z, a.r_min, 2 * a.r_max)
        st4, sl4 = cross_sections(*args, 2 * a.n_r, 2 * a.n_z, a.r_min / 10, a.r_max)
    except DipoleError as exc:
        print(json.dumps({"status": exc.status, **base, "reason": str(exc)}, indent=1))
        return exit_code(exc.status)
    f_norm = a.Q2 / (4.0 * math.pi ** 2 * a.alpha)
    ft, fl = f_norm * st, f_norm * sl
    rel = lambda u, v: abs(u - v) / max(abs(u), 1e-300)  # noqa: E731
    out = {"sigma_T_GeV-2": st, "sigma_L_GeV-2": sl, "sigma_T_mb": st * mb_per_gev2, "sigma_L_mb": sl * mb_per_gev2,
           "F_T": ft, "F_L": fl, "F_2": ft + fl,
           "Qs2_GeV2_at_input_x": Q0_GEV ** 2 * (a.x0 / a.x) ** a.lam,
           "convergence": {"rel_change_doubling_nodes": {"T": rel(st, st2), "L": rel(sl, sl2)},
                           "rel_change_doubling_rmax": {"T": rel(st2, st3), "L": rel(sl2, sl3)},
                           "rel_change_rmin_divided_by_10": {"T": rel(st2, st4), "L": rel(sl2, sl4)},
                           "method": "rerun with 2x (n_r, n_z); then, at those nodes, 2x r_max and r_min / 10"}}
    checks = [{"name": "sigma_T_and_sigma_L_non_negative", "result": "pass" if st >= 0 and sl >= 0 else "fail"}]
    conventions = {"model": f"GBW (Golec-Biernat and Wusthoff, Eqs. 1-10); parameters from {a.parameter_source}",
                   "x_variable": a.x_variable, "em_coupling": f"alpha = {a.alpha} ({a.alpha_label})",
                   "units": "r in GeV^-1, sigma in GeV^-2 and mb ((hbar c)^2, CODATA 2022)",
                   "Q0": "1 GeV (definition of the GBW model, Eq. 7)"}
    status = "ok" if all(c["result"] == "pass" for c in checks) else "failed"
    print(json.dumps({"status": status, **base, "conventions": conventions, "derivation_status": "heuristic-argument",
                      "outputs": out, "checks": checks}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Exclusive and diffractive DIS kinematics: t_min and the skewness xi for DVCS-type processes, the azimuthal angle in
the BMK and Trento conventions from four-vectors, and x_P, beta, M_X for diffractive DIS (Th20).

Purpose: put an exclusive or diffractive prediction and a measurement in the same variables with the conventions
explicit. See <plugin root>/skills/hep-theory/references/exclusive-and-gpd.md.
Subcommands:
  dvcs        --xB --Q2 --t --M (GeV^2, GeV): epsilon = 2 xB M / Q; -t_min = Q^2 [2(1 - xB)(1 - sqrt(1 + eps^2)) +
              eps^2] / [4 xB (1 - xB) + eps^2]; xi = xB (1 + t/2Q^2) / (2 - xB + xB t/Q^2) (Belitsky, Mueller,
              Kirchner, arXiv:hep-ph/0112108v2, Eqs. 3-4 (Sec. 2), Eq. 31 and epsilon after Eq. 22 (Sec. 4); read
              2026-10-23); also the leading-power xi_0 = xB / (2 - xB), labelled.
  angles      --l --P --lp --q2 --azimuth-convention bmk|trento|both (four-vectors E,px,py,pz in any frame; q2 the
              produced real photon or meson): the recoil P' = P + l - lp - q2, t = (P' - P)^2, and in the target rest
              frame phi_BMK (azimuth of the recoiled nucleon about z' = -q^, x' along the incoming lepton's transverse
              momentum; BMK Sec. 4, text after Eq. 22, Fig. 1) and phi_Trento (azimuth of the produced particle about q^ from the lepton
              plane; Trento conventions, arXiv:hep-ph/0410050v2, Eq. 16). Their relation is computed, not assumed.
  diffractive --x --Q2 --t --MX2 --M: x_P = (Q^2 + M_X^2 - t) / (Q^2 + W^2 - M^2) and beta = Q^2 / (Q^2 + M_X^2 - t)
              with W^2 = M^2 + Q^2 (1 - x)/x (derived here from x_P = q.(P - P')/q.P and beta = Q^2/(2 q.(P - P'))),
              so beta x_P = x; PDG 2026 Structure Functions Sec. 18.5 (Eq. 18.33: z in [x/x_P, 1]).
Exit codes (core/status.py): 0 ok; 2 rejected (|t| < |t_min|, t > 0, x or xB outside (0, 1), M_X^2 < 0, unreadable
vectors, undeclared convention, a recoil along q with the angle undefined). Standard library only. Derivation status:
analytic-derivation (kinematics).
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
from core.status import add_status_argument, exit_code  # noqa: E402


class ExclError(ValueError):
    """Input the tool cannot use (rejected, exit 2)."""


def _num(name, v, positive=False):
    if v is None or not math.isfinite(v) or (positive and v <= 0):
        raise ExclError(f"{name} must be a finite number{' > 0' if positive else ''}")
    return float(v)


def tmin(xb: float, q2: float, m: float) -> float:
    """t_min (negative) from BMK Eq. 31."""
    eps2 = 4 * xb * xb * m * m / q2
    return -q2 * (2 * (1 - xb) * (1 - math.sqrt(1 + eps2)) + eps2) / (4 * xb * (1 - xb) + eps2)


def xi_bmk(xb: float, q2: float, t: float) -> float:
    return xb * (1 + t / (2 * q2)) / (2 - xb + xb * t / q2)


def _vec(name, text):
    try:
        v = [float(c) for c in text.split(",")]
    except ValueError as exc:
        raise ExclError(f"{name} must be E,px,py,pz") from exc
    if len(v) != 4 or not all(math.isfinite(c) for c in v):
        raise ExclError(f"{name} must be 4 finite numbers")
    return v


def dot(a, b):
    return a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot3(a, b):
    return sum(a[i] * b[i] for i in range(3))


def norm3(a):
    return math.sqrt(dot3(a, a))


def boost_to_rest(v, p):
    m = math.sqrt(dot(p, p))
    b = [p[1] / p[0], p[2] / p[0], p[3] / p[0]]
    b2 = dot3(b, b)
    if b2 == 0:
        return list(v)
    g = p[0] / m
    bp = dot3(b, v[1:])
    k = (g - 1) * bp / b2 - g * v[0]
    return [g * (v[0] - bp), v[1] + k * b[0], v[2] + k * b[1], v[3] + k * b[2]]


def angles(l, P, lp, q2v) -> dict:
    if P[0] <= 0 or dot(P, P) <= 0:
        raise ExclError("--P must be a timelike target four-momentum with positive energy")
    q = [l[i] - lp[i] for i in range(4)]
    pp = [P[i] + q[i] - q2v[i] for i in range(4)]
    if abs(dot(pp, pp) - dot(P, P)) > 1e-6 * max(dot(P, P), 1.0):
        raise ExclError(f"the recoil P' = P + l - l' - q2 has mass^2 {dot(pp, pp):.6g}, not the target's {dot(P, P):.6g}: "
                        "an exclusive event needs an on-shell recoil of the same mass")
    t = dot([pp[i] - P[i] for i in range(4)], [pp[i] - P[i] for i in range(4)])
    lr, qr, ppr, gr = (boost_to_rest(v, P)[1:] for v in (l, q, pp, q2v))
    qhat = [c / norm3(qr) for c in qr]

    def perp(v):
        return [v[i] - dot3(v, qhat) * qhat[i] for i in range(3)]

    lt, nt, gt = perp(lr), perp(ppr), perp(gr)
    if norm3(lt) <= 1e-12 * norm3(lr) or norm3(nt) <= 1e-12 * max(norm3(ppr), 1e-300) or \
            norm3(gt) <= 1e-12 * norm3(gr):
        raise ExclError("a momentum along q: the azimuth is undefined")
    # BMK: z' = -q^, x' along the lepton's transverse momentum, y' = z' x x'; phi = azimuth of the recoiled nucleon
    zp = [-c for c in qhat]
    xp = [c / norm3(lt) for c in lt]
    yp = cross(zp, xp)
    phi_bmk = math.atan2(dot3(nt, yp), dot3(nt, xp))
    # Trento Eq. 16 for the produced particle around q^ from the lepton plane
    ql, qg = cross(qhat, lr), cross(qhat, gr)
    c = dot3(ql, qg) / (norm3(ql) * norm3(qg))
    s = dot3(cross(lr, gr), qhat) / (norm3(ql) * norm3(qg))
    phi_tr = math.atan2(s, c)
    return {"t_GeV2": t, "phi_BMK_rad": phi_bmk, "phi_Trento_rad": phi_tr,
            "pi_minus_phi_BMK_minus_phi_Trento_mod_2pi": (math.pi - phi_bmk - phi_tr) % (2 * math.pi)}


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    pd = sub.add_parser("dvcs")
    pa = sub.add_parser("angles")
    pf = sub.add_parser("diffractive")
    for n in ("xB", "Q2", "t", "M"):
        pd.add_argument(f"--{n}", type=float, required=True)
    for n in ("l", "P", "lp", "q2"):
        pa.add_argument(f"--{n}", required=True, help="E,px,py,pz in GeV")
    pa.add_argument("--azimuth-convention", choices=("bmk", "trento", "both"), required=True)
    for n in ("x", "Q2", "t", "MX2", "M"):
        pf.add_argument(f"--{n}", type=float, required=True)
    for p in (pd, pa, pf):
        add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    try:
        if a.cmd == "dvcs":
            xb, q2, t, m = _num("--xB", a.xB), _num("--Q2", a.Q2, True), _num("--t", a.t), _num("--M", a.M, True)
            if not 0 < xb < 1 or t > 0:
                raise ExclError("need 0 < xB < 1 and t <= 0")
            tm = tmin(xb, q2, m)
            if t > tm:
                raise ExclError(f"|t| = {-t} is below |t_min| = {-tm}")
            out = {"t_min_GeV2": tm, "epsilon": 2 * xb * m / math.sqrt(q2), "xi_BMK_Eq4": xi_bmk(xb, q2, t),
                   "xi_leading_power": xb / (2 - xb)}
            conv = {"skewness": "xi from BMK Eq. 4 (with t/Q^2 terms); xi_leading_power = xB/(2 - xB)",
                    "source": "Belitsky, Mueller, Kirchner, hep-ph/0112108v2, Eqs. 3-4, 31"}
        elif a.cmd == "angles":
            out = angles(_vec("--l", a.l), _vec("--P", a.P), _vec("--lp", a.lp), _vec("--q2", a.q2))
            if a.azimuth_convention == "bmk":
                out.pop("phi_Trento_rad")
            elif a.azimuth_convention == "trento":
                out.pop("phi_BMK_rad")
            conv = {"azimuth_convention": a.azimuth_convention,
                    "bmk": "recoiled-nucleon azimuth about -q^ with x' along the lepton (BMK Sec. 4, text after Eq. 22, Fig. 1)",
                    "trento": "produced-particle azimuth about q^ from the lepton plane (Trento Eq. 16)"}
        else:
            x, q2, t, mx2, m = (_num("--x", a.x), _num("--Q2", a.Q2, True), _num("--t", a.t), _num("--MX2", a.MX2),
                                _num("--M", a.M, True))
            if not 0 < x < 1 or t > 0 or mx2 < 0:
                raise ExclError("need 0 < x < 1, t <= 0, M_X^2 >= 0")
            w2 = m * m + q2 * (1 - x) / x
            xp = (q2 + mx2 - t) / (q2 + w2 - m * m)
            beta = q2 / (q2 + mx2 - t)
            if not 0 < xp <= 1:
                raise ExclError(f"x_P = {xp:.6g} outside (0, 1]")
            out = {"W2_GeV2": w2, "x_P": xp, "beta": beta, "beta_times_x_P": beta * xp}
            conv = {"definitions": "x_P = q.(P - P')/q.P, beta = Q^2/(2 q.(P - P')) (derived here); PDG 2026 Sec. 18.5"}
    except ExclError as exc:
        print(json.dumps({"status": "rejected", **base, "reason": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "conventions": conv, "derivation_status": "analytic-derivation",
                      "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())

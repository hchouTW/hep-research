#!/usr/bin/env python3
"""Semi-inclusive DIS kinematics: x, y, Q^2, z, P_h_perp, the Trento azimuthal angles phi_h and phi_S, the photon-flux
ratio epsilon, the leading-power q_T, and the classification of a point into TMD, matching or collinear regions
against thresholds the user supplies (Th18).

Purpose: put a SIDIS prediction, a selection and a measurement in the same variables with the azimuthal convention
explicit. See <plugin root>/skills/hep-theory/references/sidis-and-tmd.md.
Subcommands:
  vectors   --l --P --lp --ph E,px,py,pz (beam lepton, target, scattered lepton, hadron; any frame, GeV) and optional
            --S sx,sy,sz (target spin direction in the target rest frame), --azimuth-convention trento:
            x = Q^2/(2 P.q), y = P.q/P.l, z = P.P_h/P.q, gamma = 2 M x / Q (Bacchetta et al., hep-ph/0611265v2,
            Eq. 2.2); epsilon = (1 - y - gamma^2 y^2/4)/(1 - y + y^2/2 + gamma^2 y^2/4) (their Eq. 2.8); in the target rest
            frame cos phi_h = (q^ x l).(q^ x P_h)/(|q^ x l||q^ x P_h|), sin phi_h = (l x P_h).q^/(|q^ x l||q^ x P_h|)
            and phi_S likewise with the spin (Trento conventions, Bacchetta, D'Alesio, Diehl, Miller, hep-ph/0410050v2,
            Eq. 16); P_h_perp is the hadron momentum transverse to q in that frame; q_T = P_h_perp / z is the
            leading-power relation (q_T = -P_h_perp/z in the frame of Bacchetta et al. Sec. 3.2, their Eqs. 3.9 and
            4.1), labelled as such.
  classify  --Q2 --z --PhT, and the user's thresholds --tmd-max (q_T/Q below it: TMD region) and --collinear-min (q_T/Q
            above it: collinear region; between: matching region). No default threshold is shipped.
Exit codes (core/status.py): 0 ok; 2 rejected (unreadable vectors, undeclared azimuth convention, z outside (0, 1],
P_h_perp < 0, a hadron along q with phi_h undefined, non-finite values, thresholds not ordered). Standard library only.
Derivation status: analytic-derivation (definitions); the q_T relation is a leading-power statement.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

SOURCES = ("Trento conventions, hep-ph/0410050v2 Eq. 16; Bacchetta et al., hep-ph/0611265v2 Eqs. 2.2, 2.8, 3.9, 4.1 "
           "(read 2026-10-23)")


class KinError(ValueError):
    """Input the tool cannot use (rejected, exit 2)."""


def _vec(name: str, text: str, n: int) -> list[float]:
    try:
        v = [float(t) for t in text.split(",")]
    except ValueError as exc:
        raise KinError(f"{name} must be {n} comma-separated numbers") from exc
    if len(v) != n or not all(math.isfinite(t) for t in v):
        raise KinError(f"{name} must be {n} finite numbers")
    return v


def dot(a, b):
    return a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm3(a):
    return math.sqrt(dot3(a, a))


def boost_to_rest(v, p):
    """v seen in the rest frame of p (p timelike)."""
    m = math.sqrt(dot(p, p))
    b = [p[1] / p[0], p[2] / p[0], p[3] / p[0]]
    b2 = dot3(b, b)
    if b2 == 0:
        return list(v)
    g = p[0] / m
    bp = dot3(b, v[1:])
    e = g * (v[0] - bp)
    k = (g - 1) * bp / b2 - g * v[0]
    return [e, v[1] + k * b[0], v[2] + k * b[1], v[3] + k * b[2]]


def azimuth(qhat, lvec, avec) -> float:
    """Trento Eq. 16: angle of avec around q^ measured from the lepton plane."""
    ql, qa = cross(qhat, lvec), cross(qhat, avec)
    nl, na = norm3(ql), norm3(qa)
    if nl <= 1e-9 * norm3(lvec) or na <= 1e-9 * norm3(avec):  # relative: rounding leaves a tiny transverse part
        raise KinError("a vector along q: its azimuth is undefined")
    c = dot3(ql, qa) / (nl * na)
    s = dot3(cross(lvec, avec), qhat) / (nl * na)
    return math.atan2(s, c)


def from_vectors(l, P, lp, ph, spin=None) -> dict:
    m2 = dot(P, P)
    for name, v in (("--P", P), ("--ph", ph), ("--l", l), ("--lp", lp)):
        if v[0] <= 0 or dot(v, v) < -1e-9 * v[0] ** 2:
            raise KinError(f"{name} must have positive energy and not be spacelike")
    if m2 <= 0:
        raise KinError("the target four-momentum must be timelike")
    M = math.sqrt(m2)
    q = [l[i] - lp[i] for i in range(4)]
    Q2 = -dot(q, q)
    if Q2 <= 0:
        raise KinError("Q^2 must be > 0")
    pq, pl, pph = dot(P, q), dot(P, l), dot(P, ph)
    x, y, z = Q2 / (2 * pq), pq / pl, pph / pq
    if not (0 < x <= 1 and 0 < y <= 1 and 0 < z <= 1):
        raise KinError(f"x = {x:.6g}, y = {y:.6g}, z = {z:.6g} must lie in (0, 1]")
    gamma = 2 * M * x / math.sqrt(Q2)
    eps = (1 - y - gamma ** 2 * y ** 2 / 4) / (1 - y + y ** 2 / 2 + gamma ** 2 * y ** 2 / 4)
    lr, qr, hr = boost_to_rest(l, P), boost_to_rest(q, P), boost_to_rest(ph, P)
    qhat = [c / norm3(qr[1:]) for c in qr[1:]]
    h3 = hr[1:]
    hperp = norm3([h3[i] - dot3(h3, qhat) * qhat[i] for i in range(3)])
    out = {"x": x, "y": y, "Q2_GeV2": Q2, "z": z, "gamma": gamma, "epsilon": eps, "PhT_GeV": hperp,
           "phi_h_rad": azimuth(qhat, lr[1:], h3), "abs_qT_GeV_leading_power": hperp / z,
           "abs_qT_over_Q_leading_power": hperp / z / math.sqrt(Q2), "W2_GeV2": m2 + 2 * pq - Q2}
    if spin is not None:
        if norm3(spin) == 0:
            raise KinError("--S must be a non-zero direction")
        out["phi_S_rad"] = azimuth(qhat, lr[1:], spin)
    return out


def classify(qt_over_q: float, tmd_max: float, coll_min: float) -> str:
    if qt_over_q < tmd_max:
        return "TMD"
    if qt_over_q > coll_min:
        return "collinear"
    return "matching"


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    pv = sub.add_parser("vectors")
    for n in ("l", "P", "lp", "ph"):
        pv.add_argument(f"--{n}", required=True, help="E,px,py,pz in GeV")
    pv.add_argument("--S", help="sx,sy,sz: target spin direction in the target rest frame reached from the input frame by a pure boost")
    pv.add_argument("--azimuth-convention", choices=("trento",), required=True)
    pv.add_argument("--tmd-max", type=float)
    pv.add_argument("--collinear-min", type=float)
    pc = sub.add_parser("classify")
    pc.add_argument("--Q2", type=float, required=True)
    pc.add_argument("--z", type=float, required=True)
    pc.add_argument("--PhT", type=float, required=True)
    pc.add_argument("--tmd-max", type=float, required=True)
    pc.add_argument("--collinear-min", type=float, required=True)
    for p in (pv, pc):
        add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    try:
        thresholds = None
        if a.tmd_max is not None or a.collinear_min is not None:
            if a.tmd_max is None or a.collinear_min is None:
                raise KinError("give both --tmd-max and --collinear-min")
            if not (math.isfinite(a.tmd_max) and math.isfinite(a.collinear_min) and 0 < a.tmd_max <= a.collinear_min):
                raise KinError("need 0 < --tmd-max <= --collinear-min")
            thresholds = (a.tmd_max, a.collinear_min)
        if a.cmd == "vectors":
            out = from_vectors(_vec("--l", a.l, 4), _vec("--P", a.P, 4), _vec("--lp", a.lp, 4), _vec("--ph", a.ph, 4),
                               _vec("--S", a.S, 3) if a.S else None)
            qtq = out["abs_qT_over_Q_leading_power"]
        else:
            for name in ("Q2", "z", "PhT"):
                if not math.isfinite(getattr(a, name)):
                    raise KinError(f"--{name} must be finite")
            if a.Q2 <= 0 or not 0 < a.z <= 1 or a.PhT < 0:
                raise KinError("need Q^2 > 0, z in (0, 1], P_hT >= 0")
            qtq = a.PhT / a.z / math.sqrt(a.Q2)
            out = {"abs_qT_over_Q_leading_power": qtq}
        out["region"] = classify(qtq, *thresholds) if thresholds else "not classified (no thresholds given)"
    except KinError as exc:
        print(json.dumps({"status": "rejected", **base, "reason": str(exc)}, indent=1))
        return exit_code("rejected")
    conventions = {"azimuth_convention": "Trento (hep-ph/0410050v2 Eq. 16), angles in the target rest frame",
                   "frame": "target rest frame for P_h_perp and the angles", "source": SOURCES,
                   "qT": "|q_T| = P_h_perp / z at leading power (q_T = -P_h_perp/z in the hadron frame; not an exact four-vector identity)"}
    print(json.dumps({"status": "ok", **base, "conventions": conventions, "derivation_status": "analytic-derivation",
                      "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())

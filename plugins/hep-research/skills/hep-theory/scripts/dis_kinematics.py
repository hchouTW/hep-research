#!/usr/bin/env python3
"""Lepton-nucleon deep-inelastic-scattering kinematics from beam energies and two of (x, y, Q^2).

Purpose: give the frame-independent invariants of l N -> l' X with every convention explicit, so that a
theory prediction, a selection or a response can be stated in the same variables. Definitions follow the
PDG review "Structure Functions", section 18.1 (see
<plugin root>/skills/hep-theory/references/dis-kinematics.md for the citation and the derivation status).

What it does: builds s = (k + P)^2 exactly from the two beam four-momenta (a crossing angle is allowed),
then from two of x, y, Q^2 computes the third with the exact identity Q^2 = x y (s - M^2 - m_l^2), and
nu = Q^2 / (2 M x), W^2 = M^2 + 2 M nu - Q^2, k.P = (s - M^2 - m_l^2) / 2. Refuses x or y outside (0, 1],
Q^2 <= 0 or W^2 < M^2 with exit 1 and a JSON reason. from_four_vectors() computes the same invariants
directly from k, k', P and is the independent check used by the tests.

Usage notes / assumptions: standard library only. Energies in GeV; the hadron energy is PER NUCLEON and M is
the mass the caller supplies (a nucleon mass for a per-nucleon convention; this script ships no constant).
The lepton mass defaults to 0 (the PDG neglects it after the definitions). The crossing angle is the angle
between the lepton momentum and the reversed hadron momentum, 0 for head-on beams. No polarization, no
structure functions, no cross sections: see the reference for what belongs to other skills.
Run: python3 <plugin root>/skills/hep-theory/scripts/dis_kinematics.py --E-lepton 10 --E-hadron 275 --M 0.938 --x 0.1 --y 0.5
Exit 0 ok, 1 unphysical kinematics (status "failed"), 2 bad arguments.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _dot(a, b) -> float:
    return a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]


def beam_s(E_lepton: float, E_hadron: float, M: float, m_lepton: float = 0.0, crossing_angle_rad: float = 0.0) -> float:
    """s = (k + P)^2 with k = (E_l, |k| sin th_c, 0, -|k| cos th_c) and P = (E_h, 0, 0, |P|)."""
    pl = math.sqrt(E_lepton**2 - m_lepton**2)
    ph = math.sqrt(E_hadron**2 - M**2)
    k = (E_lepton, pl * math.sin(crossing_angle_rad), 0.0, -pl * math.cos(crossing_angle_rad))
    P = (E_hadron, 0.0, 0.0, ph)
    tot = tuple(k[i] + P[i] for i in range(4))
    return _dot(tot, tot)


def from_four_vectors(k, kp, P) -> dict:
    """Invariants directly from the lepton in (k), lepton out (kp) and nucleon (P) four-momenta (E, px, py, pz)."""
    q = tuple(k[i] - kp[i] for i in range(4))
    M = math.sqrt(_dot(P, P))
    Q2 = -_dot(q, q)
    nu = _dot(q, P) / M
    x = Q2 / (2 * M * nu)
    y = _dot(q, P) / _dot(k, P)
    W2 = _dot(tuple(P[i] + q[i] for i in range(4)), tuple(P[i] + q[i] for i in range(4)))
    tot = tuple(k[i] + P[i] for i in range(4))
    s = _dot(tot, tot)
    return {"x": x, "y": y, "Q2": Q2, "nu": nu, "W2": W2, "W": math.sqrt(W2) if W2 >= 0 else float("nan"),
            "s": s, "sqrt_s": math.sqrt(s), "kP": _dot(k, P)}


def invariants(s: float, M: float, m_lepton: float = 0.0, x: float | None = None, y: float | None = None,
               Q2: float | None = None) -> dict:
    """Closed forms from exactly two of x, y, Q^2. Raises ValueError when the kinematics are unphysical."""
    given = {n: v for n, v in (("x", x), ("y", y), ("Q2", Q2)) if v is not None}
    if len(given) != 2:
        raise ValueError("give exactly two of x, y, Q2")
    for name, value in (("s", s), ("M", M), ("m_lepton", m_lepton), *given.items()):
        if not math.isfinite(value):
            raise ValueError(f"{name} = {value} is not finite")
    kP = (s - M**2 - m_lepton**2) / 2.0
    if kP <= 0:
        raise ValueError("s must exceed M^2 + m_l^2")
    if x is None:
        x = Q2 / (2.0 * kP * y)
    elif y is None:
        y = Q2 / (2.0 * kP * x)
    else:
        Q2 = 2.0 * kP * x * y
    if not 0 < x <= 1:
        raise ValueError(f"x = {x} outside (0, 1]")
    if not 0 < y <= 1:
        raise ValueError(f"y = {y} outside (0, 1]")
    if Q2 <= 0:
        raise ValueError(f"Q^2 = {Q2} must be positive")
    nu = Q2 / (2.0 * M * x)
    W2 = M**2 + 2.0 * M * nu - Q2
    if W2 < M**2 * (1 - 1e-12):
        raise ValueError(f"W^2 = {W2} below M^2")
    return {"x": x, "y": y, "Q2": Q2, "nu": nu, "W2": W2, "W": math.sqrt(W2), "s": s, "sqrt_s": math.sqrt(s), "kP": kP}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n", 1)[1])
    p.add_argument("--E-lepton", type=float, required=True, help="lepton beam energy, GeV")
    p.add_argument("--E-hadron", type=float, required=True, help="hadron beam energy per nucleon, GeV")
    p.add_argument("--M", type=float, required=True, help="target mass used in the invariants, GeV (no default shipped)")
    p.add_argument("--m-lepton", type=float, default=0.0, help="lepton mass, GeV (default 0)")
    p.add_argument("--crossing-angle-mrad", type=float, default=0.0, help="beam crossing angle, mrad (default 0, head-on)")
    p.add_argument("--x", type=float)
    p.add_argument("--y", type=float)
    p.add_argument("--Q2", type=float, help="GeV^2")
    return p


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    a = p.parse_args(argv)
    given = [n for n in ("x", "y", "Q2") if getattr(a, n) is not None]
    for name in ("E_lepton", "E_hadron", "M", "m_lepton", "crossing_angle_mrad", "x", "y", "Q2"):
        value = getattr(a, name)
        if value is not None and not math.isfinite(value):
            p.error(f"--{name.replace('_', '-')} must be finite, got {value}")        # argparse exits 2
    if len(given) != 2:
        p.error("give exactly two of --x, --y, --Q2")                       # argparse exits 2
    if a.E_lepton <= 0 or a.E_hadron <= 0 or a.M <= 0 or a.m_lepton < 0 or a.E_lepton <= a.m_lepton or a.E_hadron <= a.M:
        p.error("beam energies must be positive and exceed the respective masses; M must be positive")
    conventions = {"units": "GeV, GeV^2", "lepton_mass_GeV": a.m_lepton,
                   "hadron_energy": "per nucleon; M is the mass the user supplied",
                   "crossing_angle_mrad": a.crossing_angle_mrad,
                   "frame": "invariants are frame-independent; E, E', theta and nu as an energy loss refer to the nucleon rest frame",
                   "definitions": "PDG Structure Functions review, section 18.1; Q^2 = x y (s - M^2 - m_l^2) exact",
                   "derivation_status": "analytic-derivation (closed forms from the definitions; checked numerically against four-vector arithmetic in the tests)"}
    s = beam_s(a.E_lepton, a.E_hadron, a.M, a.m_lepton, a.crossing_angle_mrad * 1e-3)
    inputs = {"E_lepton_GeV": a.E_lepton, "E_hadron_per_nucleon_GeV": a.E_hadron, "M_GeV": a.M, "given": {n: getattr(a, n) for n in given}}
    try:
        out = invariants(s, a.M, a.m_lepton, a.x, a.y, a.Q2)
    except ValueError as exc:
        print(json.dumps({"status": "failed", "reason": str(exc), "inputs": inputs, "conventions": conventions, "outputs": {}}, indent=1))
        return 1
    print(json.dumps({"status": "ok", "inputs": inputs, "conventions": conventions, "outputs": out,
                      "checks": {"x_in_(0,1]": True, "y_in_(0,1]": True, "Q2_positive": True, "W2_at_least_M2": True}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

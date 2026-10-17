#!/usr/bin/env python3
"""Four-vector kinematics: two-body decays, Lorentz boosts, invariant masses, Mandelstam variables, reaction
thresholds, Dalitz boundaries, rapidity and pseudorapidity, and width, lifetime and c tau (Th7).

Conventions: a four-vector is (E, px, py, pz) in GeV with c = 1; metric (+, -, -, -); masses in GeV. boost(v, beta)
gives v in the frame that moves with velocity beta (|beta| < 1) relative to the current one, so boost(v, beta_of(v))
is the rest frame of v and boost(w, -beta) undoes it. Mandelstam variables for 1 + 2 -> 3 + 4: s = (p1 + p2)^2,
t = (p1 - p3)^2, u = (p1 - p4)^2. Dalitz variables for M -> 1 2 3: m12^2 = (p1 + p2)^2, m23^2 = (p2 + p3)^2
(PDG Review, Kinematics). Width, lifetime and c tau are related by tau = hbar / Gamma with the exact hbar and c of
core/constants. No masses are embedded: the caller supplies them (skills/hep-theory/scripts/kinematics.py can take
them from core/constants by name). Every result is [General method] arithmetic.

Usage: from core.kinematics import fourvector as fv; fv.two_body_decay(M, m1, m2); fv.boost(v, beta);
fv.mandelstam(p1, p2, p3, p4); fv.fixed_target_threshold(m_beam, m_target, final_masses);
fv.dalitz_m23_range(M, m1, m2, m3, m12sq); fv.rapidity(v); fv.lifetime_relations(width_gev=...)
Standard library only.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from core.kinematics.relativistic import KinematicsError

Vec = tuple[float, float, float, float]
LABEL = "[General method]"


def _finite(x, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise KinematicsError(f"{name} must be a finite number")
    return float(x)


def _mass(m, name: str) -> float:
    m = _finite(m, name)
    if m < 0:
        raise KinematicsError(f"{name} must be >= 0")
    return m


def _vec(v, name: str = "four-vector") -> Vec:
    if len(v) != 4:
        raise KinematicsError(f"{name} must have four components (E, px, py, pz)")
    e, px, py, pz = (_finite(x, name) for x in v)
    return (e, px, py, pz)


def kallen(x: float, y: float, z: float) -> float:
    """Kallen triangle function lambda(x, y, z) = x^2 + y^2 + z^2 - 2xy - 2xz - 2yz."""
    return x * x + y * y + z * z - 2 * x * y - 2 * x * z - 2 * y * z


def two_body_momentum(M: float, m1: float, m2: float) -> float:
    """Daughter momentum in the parent rest frame, p* = sqrt(lambda(M^2, m1^2, m2^2)) / 2M."""
    M, m1, m2 = _mass(M, "M"), _mass(m1, "m1"), _mass(m2, "m2")
    if M <= 0:
        raise KinematicsError("the parent mass M must be > 0")
    if M < m1 + m2:
        raise KinematicsError(f"closed channel: M = {M} < m1 + m2 = {m1 + m2}")
    lam = kallen(M * M, m1 * m1, m2 * m2)
    return math.sqrt(max(lam, 0.0)) / (2 * M)


def two_body_decay(M: float, m1: float, m2: float) -> dict:
    """p*, the daughter energies E1 = (M^2 + m1^2 - m2^2) / 2M, E2, and the daughter velocities in the rest frame."""
    p = two_body_momentum(M, m1, m2)
    e1 = (M * M + m1 * m1 - m2 * m2) / (2 * M)
    e2 = (M * M + m2 * m2 - m1 * m1) / (2 * M)
    return {"p": p, "E1": e1, "E2": e2, "beta1": p / e1 if e1 else 1.0, "beta2": p / e2 if e2 else 1.0,
            "label": LABEL}


def mass_squared(v) -> float:
    e, px, py, pz = _vec(v)
    return e * e - px * px - py * py - pz * pz


def invariant_mass(*vectors) -> float:
    """sqrt((sum of the four-vectors)^2); refuses a spacelike sum beyond rounding."""
    if not vectors:
        raise KinematicsError("give at least one four-vector")
    tot = [0.0, 0.0, 0.0, 0.0]
    for v in vectors:
        for i, x in enumerate(_vec(v)):
            tot[i] += x
    m2 = tot[0] ** 2 - tot[1] ** 2 - tot[2] ** 2 - tot[3] ** 2
    scale = max(tot[0] ** 2, 1e-300)
    if m2 < -1e-9 * scale:
        raise KinematicsError(f"the summed four-vector is spacelike (m^2 = {m2})")
    return math.sqrt(max(m2, 0.0))


def beta_of(v) -> tuple[float, float, float]:
    """Velocity of the rest frame of v."""
    e, px, py, pz = _vec(v)
    if e <= 0:
        raise KinematicsError("energy must be > 0")
    beta = (px / e, py / e, pz / e)
    if math.fsum(b * b for b in beta) >= 1.0:
        raise KinematicsError("v is lightlike or spacelike: no rest frame")
    return beta


def boost(v, beta: Sequence[float]) -> Vec:
    """v seen from a frame moving with velocity beta (general direction)."""
    e, px, py, pz = _vec(v)
    if len(beta) != 3:
        raise KinematicsError("beta must have three components")
    bx, by, bz = (_finite(b, "beta") for b in beta)
    b2 = bx * bx + by * by + bz * bz
    if b2 >= 1.0:
        raise KinematicsError(f"|beta| must be < 1 (got {math.sqrt(b2)})")
    if b2 == 0.0:
        return (e, px, py, pz)
    gamma = 1.0 / math.sqrt(1.0 - b2)
    bp = bx * px + by * py + bz * pz
    k = (gamma - 1.0) * bp / b2 - gamma * e
    return (gamma * (e - bp), px + k * bx, py + k * by, pz + k * bz)


def mandelstam(p1, p2, p3, p4) -> tuple[float, float, float]:
    """(s, t, u) of 1 + 2 -> 3 + 4."""
    a, b, c, d = (_vec(v) for v in (p1, p2, p3, p4))
    s = mass_squared(tuple(x + y for x, y in zip(a, b)))
    t = mass_squared(tuple(x - y for x, y in zip(a, c)))
    u = mass_squared(tuple(x - y for x, y in zip(a, d)))
    return s, t, u


def fixed_target_threshold(m_beam: float, m_target: float, final_masses: Sequence[float]) -> dict:
    """Threshold of beam + target (at rest) -> final state: sqrt(s)_th = sum of final masses and
    E_beam,th = (sqrt(s)_th^2 - m_beam^2 - m_target^2) / 2 m_target."""
    mb, mt = _mass(m_beam, "m_beam"), _mass(m_target, "m_target")
    if mt <= 0:
        raise KinematicsError("the target mass must be > 0 (a target at rest)")
    if not final_masses:
        raise KinematicsError("give the final-state masses")
    root_s = math.fsum(_mass(m, "final mass") for m in final_masses)
    e_th = (root_s * root_s - mb * mb - mt * mt) / (2 * mt)
    open_at_rest = e_th <= mb
    e_th = max(e_th, mb)
    return {"sqrt_s": root_s, "beam_energy": e_th, "beam_kinetic_energy": e_th - mb,
            "beam_momentum": math.sqrt(max(e_th * e_th - mb * mb, 0.0)), "open_at_rest": open_at_rest, "label": LABEL}


def dalitz_m12_range(M: float, m1: float, m2: float, m3: float) -> tuple[float, float]:
    M, m1, m2, m3 = (_mass(x, n) for x, n in ((M, "M"), (m1, "m1"), (m2, "m2"), (m3, "m3")))
    if M < m1 + m2 + m3:
        raise KinematicsError("closed channel: M < m1 + m2 + m3")
    return (m1 + m2) ** 2, (M - m3) ** 2


def dalitz_m23_range(M: float, m1: float, m2: float, m3: float, m12sq: float) -> tuple[float, float]:
    """(m23^2 min, max) at fixed m12^2: E2* = (m12^2 - m1^2 + m2^2) / 2 m12, E3* = (M^2 - m12^2 - m3^2) / 2 m12
    in the (12) rest frame; m23^2 = (E2* + E3*)^2 - (p2* +- p3*)^2."""
    lo, hi = dalitz_m12_range(M, m1, m2, m3)
    m12sq = _finite(m12sq, "m12^2")
    if not lo - 1e-12 * hi <= m12sq <= hi * (1 + 1e-12):
        raise KinematicsError(f"m12^2 = {m12sq} is outside [{lo}, {hi}]")
    m12 = math.sqrt(m12sq)
    e2 = (m12sq - m1 * m1 + m2 * m2) / (2 * m12)
    e3 = (M * M - m12sq - m3 * m3) / (2 * m12)
    p2 = math.sqrt(max(e2 * e2 - m2 * m2, 0.0))
    p3 = math.sqrt(max(e3 * e3 - m3 * m3, 0.0))
    return (e2 + e3) ** 2 - (p2 + p3) ** 2, (e2 + e3) ** 2 - (p2 - p3) ** 2


def rapidity(v) -> float:
    """y = (1/2) ln((E + pz) / (E - pz))."""
    e, _, _, pz = _vec(v)
    if e <= abs(pz):
        raise KinematicsError("rapidity needs E > |pz|")
    return 0.5 * math.log((e + pz) / (e - pz))


def pseudorapidity(v) -> float:
    """eta = -ln tan(theta / 2) = atanh(pz / |p|)."""
    _, px, py, pz = _vec(v)
    p = math.sqrt(px * px + py * py + pz * pz)
    if p == 0 or abs(pz) >= p:
        raise KinematicsError("pseudorapidity is infinite along the axis (or undefined at p = 0)")
    return math.atanh(pz / p)


def lifetime_relations(width_gev: float | None = None, lifetime_s: float | None = None,
                       ctau_m: float | None = None) -> dict:
    """Exactly one of width (GeV), mean lifetime (s) or c tau (m) -> all three, with tau = hbar / Gamma (exact
    hbar and c, CODATA 2022 / SI 2019)."""
    given = {k: v for k, v in (("width_gev", width_gev), ("lifetime_s", lifetime_s), ("ctau_m", ctau_m)) if v is not None}
    if len(given) != 1:
        raise KinematicsError("give exactly one of width_gev, lifetime_s, ctau_m")
    (key, value), = given.items()
    value = _finite(value, key)
    if value <= 0:
        raise KinematicsError(f"{key} must be > 0")
    from core import constants  # imported here: relativistic.py users need no data files
    hbar = constants.hbar("GeV s").value
    c = constants.constant("speed_of_light").value
    tau = {"width_gev": lambda: hbar / value, "lifetime_s": lambda: value, "ctau_m": lambda: value / c}[key]()
    return {"width_gev": hbar / tau, "lifetime_s": tau, "ctau_m": c * tau,
            "hbar_gev_s": hbar, "source": "hbar and c exact (CODATA 2022, SI 2019) from core/constants", "label": LABEL}

#!/usr/bin/env python3
"""Leading-order Drell-Yan (photon exchange): cross sections, variable conversions, angular frames and the Lam-Tung
combination (Th15).

Purpose: d2sigma/dM dy and d2sigma/dM dx_F at LO from parton values the user supplies, with the rapidity frame and the
x_F definition explicit; the conversions between (M, y), (M, x_F), (x_1, x_2) and (tau, y); the rotation of the angular
coefficients (lambda, mu, nu) between the Collins-Soper and helicity frames with their frame-invariant combinations;
the Lam-Tung combination 1 - lambda - 2 nu. See <plugin root>/skills/hep-theory/references/drell-yan.md.
Subcommands:
  xsec     --M, --y or --xF (with --xF-definition), --rapidity-frame, beams (--sqrt-s, or --E1 --m1 --E2 --m2: beam 1
           along +z, beam 2 along -z, a fixed target has E2 = m2), --alpha, --alpha-label, --bosons gamma,
           --partons FILE = {"representation": "xf", "x1": x_1, "x2": x_2, "beam1": {flavour: x f(x_1, M^2)},
           "beam2": {flavour: x f(x_2, M^2)}} for d u s c b dbar ubar sbar cbar bbar; the x_1, x_2 in the file must be
           those of this point (run `convert` first). Optional --resonance-window LO:HI (GeV, repeatable).
  convert  one of (--M --y), (--M --xF --xF-definition), (--x1 --x2), (--tau --y), with the beams; prints all forms and
           the Jacobians (LO kinematics, q_T = 0).
  frames   --M --qT --y (dilepton in the hadronic centre-of-mass frame), --from CS|HX --to CS|HX, --lambda --mu --nu.
  lam-tung --lambda --nu [--sigma-lambda --sigma-nu --rho]: 1 - lambda - 2 nu and its linear uncertainty.
  coefficients  --A0 --A1 --A2 -> (lambda, mu, nu), or --lambda --mu --nu -> (A0, A1, A2).
Physics and sources:
- d2sigma/dM dy = (8 pi alpha^2 / (9 M s)) sum_q e_q^2 [q_1(x_1) qbar_2(x_2) + qbar_1(x_1) q_2(x_2)],
  x_{1,2} = (M / sqrt(s)) e^{+/- y}, y in the hadronic centre-of-mass frame. Derived here (analytic-derivation, LO) from
  sigma(e+e- -> f fbar) = N_c Q_f^2 4 pi alpha^2 / (3 s) (PDG 2026 "Cross-Section Formulae", Eq. 51.3) with the colour
  average 1/N_c^2 x N_c for q qbar -> l+ l-, N_c = 3, the parton factorization of Eq. (51.40), and dx_1 dx_2 = dtau dy.
- x_F at LO and q_T = 0: x_1 - x_2 = 2 p_L* / sqrt(s) exactly; p_L* / p_L,max = (x_1 - x_2) / (1 - tau) with
  p_L,max = (s - M^2) / (2 sqrt(s)) (derived here). y_lab = y_cm + y_shift, y_shift the rapidity of the beam system.
- Angular distribution dsigma/dOmega ~ 1 + lambda cos^2 theta + mu sin 2theta cos phi + (nu/2) sin^2 theta cos 2phi
  (Peng et al., arXiv:1511.08932v3, Eq. 1); lambda = (2 - 3 A0)/(2 + A0), mu = 2 A1/(2 + A0), nu = 2 A2/(2 + A0) from
  the A_i expansion of Aad et al., arXiv:1606.00689v1, Eq. 1 (derived here). Frames: CS and HX axes and the rotation about the
  normal to the production plane, lambda' = (lambda - 3 L)/(1 + L), lambda_phi' = (lambda_phi + L)/(1 + L),
  lambda_thetaphi' = (lambda_thetaphi cos 2d - (lambda - lambda_phi) sin 2d / 2)/(1 + L),
  L = (lambda - lambda_phi) sin^2 d / 2 - lambda_thetaphi sin 2d / 2, with lambda_phi = nu/2, lambda_thetaphi = mu,
  d_HX->CS = -d_CS->HX = arccos(m p_L / (m_T p)) (Faccioli, Lourenco, Seixas, Woehri, arXiv:1006.2738v1, Eqs. 21, 25-28,
  beam 1 along +z, y axis along P1' x P2'); invariants lambda~ = (lambda + 3 lambda_phi)/(1 - lambda_phi) (their
  Eq. 31) and F = (1 + lambda + 2 lambda_phi)/(3 + lambda) (Faccioli, Lourenco, Seixas, arXiv:1005.2601v1, Eq. 8).
  Positivity: the distribution is >= 0 on the sphere, i.e. I + M >= 0 with M = [[nu/2, 0, mu], [0, -nu/2, 0],
  [mu, 0, lambda]] (derived here), and the bounds of 1006.2738 Eq. 22 (|lambda| <= 1 in every frame) hold; neither
  implies the other.
- The lepton whose angles are given is a convention (Peng et al. and Aad et al. use l-); swapping it leaves lambda, mu, nu
  unchanged (derived here). Z exchange (A_3, A_4 terms) is not implemented: a request is refused.
Inputs read 2026-10-23. Derivation status: analytic-derivation (LO kinematics and cross section); the frame
transformation is geometry.
Output JSON: status, status_label, inputs, conventions, outputs, checks. Exit codes (core/status.py): 0 ok; 1 refused
(Z exchange requested; M inside a declared resonance window without --allow-in-window; angular parameters outside the
positivity domain); 2 rejected (missing or unreadable input, undeclared frame or x_F definition, M^2 >= s, x outside
(0, 1], x_1 or x_2 of the parton file not those of this point, non-finite values). Standard library only; (hbar c)^2 from
core/constants (CODATA 2022).
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

QUARKS = ("d", "u", "s", "c", "b")
FLAVOURS = QUARKS + tuple(q + "bar" for q in QUARKS)
CHARGE = {"d": -1.0 / 3.0, "u": 2.0 / 3.0, "s": -1.0 / 3.0, "c": 2.0 / 3.0, "b": -1.0 / 3.0}
XF_DEFS = ("x1-x2", "2pL/sqrts", "pL/pLmax")


class DYError(ValueError):
    def __init__(self, msg: str, status: str = "rejected"):
        super().__init__(msg)
        self.status = status


def _num(name, v, positive=False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise DYError(f"{name} must be a finite number, got {v!r}")
    if positive and v <= 0:
        raise DYError(f"{name} must be > 0")
    return float(v)


def beams(a) -> dict:
    """s and the rapidity shift of the beam system (beam 1 along +z, beam 2 along -z)."""
    if a.sqrt_s is not None:
        if any(v is not None for v in (a.E1, a.E2)):
            raise DYError("give --sqrt-s or the beam energies, not both")
        rs = _num("--sqrt-s", a.sqrt_s, positive=True)
        return {"s": rs * rs, "y_shift": None, "source": "--sqrt-s (centre-of-mass frame only)"}
    if None in (a.E1, a.m1, a.E2, a.m2):
        raise DYError("give --sqrt-s, or --E1 --m1 --E2 --m2")
    e1, m1, e2, m2 = (_num(n, v) for n, v in (("--E1", a.E1), ("--m1", a.m1), ("--E2", a.E2), ("--m2", a.m2)))
    if m1 < 0 or m2 < 0 or e1 < m1 or e2 < m2 or e1 + e2 <= 0:
        raise DYError("need E >= m >= 0 for each beam")
    p1, p2 = math.sqrt(e1 * e1 - m1 * m1), math.sqrt(e2 * e2 - m2 * m2)
    e, pz = e1 + e2, p1 - p2
    s = e * e - pz * pz
    if s <= 0 or e - abs(pz) <= 0:
        raise DYError("the beams have no centre-of-mass frame (massless beams moving the same way, or a beam at rest "
                      "with zero mass)")
    return {"s": s, "y_shift": 0.5 * math.log((e + pz) / (e - pz)), "source": "beam four-momenta (lab frame)"}


def kinematics(m: float, y: float, s: float) -> dict:
    rs = math.sqrt(s)
    tau = m * m / s
    x1, x2 = m / rs * math.exp(y), m / rs * math.exp(-y)
    xf = {"x1-x2": x1 - x2, "2pL/sqrts": x1 - x2, "pL/pLmax": (x1 - x2) / (1.0 - tau)}
    # d x_F / d y at fixed M: x_1 - x_2 = 2 sqrt(tau) sinh y
    dxf_dy = {"x1-x2": x1 + x2, "2pL/sqrts": x1 + x2, "pL/pLmax": (x1 + x2) / (1.0 - tau)}
    return {"M": m, "y_cm": y, "x1": x1, "x2": x2, "tau": tau, "xF": xf, "dxF_dy": dxf_dy,
            "jacobian_x1x2_tau_y": 1.0, "dtau_dM": 2.0 * m / s}


def y_from(a, s: float) -> tuple[float, float]:
    """(M, y_cm) from the given pair."""
    if a.x1 is not None or a.x2 is not None:
        if any(v is not None for v in (a.M, a.y, a.xF, a.tau)):
            raise DYError("give one point: (--M --y), (--M --xF), (--x1 --x2) or (--tau --y)")
        x1, x2 = _num("--x1", a.x1, True), _num("--x2", a.x2, True)
        return math.sqrt(x1 * x2 * s), 0.5 * math.log(x1 / x2)
    if a.tau is not None:
        if a.M is not None or a.xF is not None:
            raise DYError("give one point: (--M --y), (--M --xF), (--x1 --x2) or (--tau --y)")
        tau = _num("--tau", a.tau, True)
        return math.sqrt(tau * s), _num("--y", a.y)
    m = _num("--M", a.M, True)
    if a.y is not None and a.xF is not None:
        raise DYError("give --y or --xF, not both")
    if a.y is not None:
        return m, _num("--y", a.y)
    if a.xF is None:
        raise DYError("give --y or --xF")
    if a.xF_definition is None:
        raise DYError("--xF needs --xF-definition (x1-x2, 2pL/sqrts or pL/pLmax)")
    tau = m * m / s
    diff = _num("--xF", a.xF) * ((1.0 - tau) if a.xF_definition == "pL/pLmax" else 1.0)
    x1 = 0.5 * (diff + math.sqrt(diff * diff + 4.0 * tau))
    return m, math.log(x1 / math.sqrt(tau))


def resolve_point(a) -> tuple[dict, dict]:
    b = beams(a)
    m, y = y_from(a, b["s"])
    if a.rapidity_frame == "lab" and a.y is not None and a.x1 is None:
        if b["y_shift"] is None:
            raise DYError("--rapidity-frame lab needs the beam four-momenta (--E1 --m1 --E2 --m2)")
        y = y - b["y_shift"]
    if m * m >= b["s"]:
        raise DYError("M^2 must be below s")
    k = kinematics(m, y, b["s"])
    if not (0 < k["x1"] <= 1 and 0 < k["x2"] <= 1):
        raise DYError(f"x_1 = {k['x1']:.6g}, x_2 = {k['x2']:.6g}: both must be in (0, 1]")
    if b["y_shift"] is not None:
        k["y_lab"] = y + b["y_shift"]
        k["y_shift"] = b["y_shift"]
    k["s"] = b["s"]
    return k, b


def load_partons(path: str, k: dict) -> tuple[dict, dict]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DYError(f"cannot read --partons {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("representation") != "xf":
        raise DYError('--partons must be {"representation": "xf", "x1": .., "x2": .., "beam1": {..}, "beam2": {..}}')
    for key in ("x1", "x2"):
        given = _num(f"partons {key}", doc.get(key), True)
        if abs(given - k[key]) > 1e-9 * k[key]:
            raise DYError(f"the parton file was evaluated at {key} = {given}, this point has {key} = {k[key]:.12g}")
    out = []
    for beam in ("beam1", "beam2"):
        vals = doc.get(beam)
        if not isinstance(vals, dict) or any(f not in vals for f in FLAVOURS):
            raise DYError(f"{beam} needs x f for {list(FLAVOURS)} (0 for an absent flavour)")
        out.append({f: _num(f"{beam}.{f}", vals[f]) for f in FLAVOURS})
    return out[0], out[1]


def xsec(a) -> dict:
    if a.bosons != "gamma":
        raise DYError("Z exchange (A_3, A_4 terms, gamma*/Z couplings and the Breit-Wigner) is not implemented; "
                      "only --bosons gamma", status="refused")
    alpha = _num("--alpha", a.alpha, True)
    k, b = resolve_point(a)
    for w in a.resonance_window or []:
        try:
            lo, hi = (float(v) for v in w.split(":"))
        except ValueError as exc:
            raise DYError(f"--resonance-window is LO:HI in GeV, got {w!r}") from exc
        if not (math.isfinite(lo) and math.isfinite(hi) and 0 <= lo < hi):
            raise DYError(f"--resonance-window needs 0 <= LO < HI, got {w!r}")
        if lo <= k["M"] <= hi and not a.allow_in_window:
            raise DYError(f"M = {k['M']} GeV is inside the declared window {w}; pass --allow-in-window to override",
                          status="refused")
    b1, b2 = load_partons(a.partons, k)
    x1, x2, m, s = k["x1"], k["x2"], k["M"], k["s"]
    lum = sum(CHARGE[q] ** 2 * (b1[q] * b2[q + "bar"] + b1[q + "bar"] * b2[q]) for q in QUARKS) / (x1 * x2)
    d2_dmdy = 8.0 * math.pi * alpha ** 2 / (9.0 * m * s) * lum
    gev2_pb = constants.hbar_c_squared("GeV^2 mb").value * 1e9
    out = dict(k, d2sigma_dM_dy_GeV3=d2_dmdy, d2sigma_dM_dy_pb_per_GeV=d2_dmdy * gev2_pb,
               luminosity_sum_eq2_q1_qbar2=lum)
    if a.xF_definition:
        out["xF_definition"] = a.xF_definition
        out["d2sigma_dM_dxF_GeV3"] = d2_dmdy / k["dxF_dy"][a.xF_definition]
        out["d2sigma_dM_dxF_pb_per_GeV"] = out["d2sigma_dM_dxF_GeV3"] * gev2_pb
    out["M3_dsigma_dM_dy_GeV0"] = m ** 3 * d2_dmdy  # depends on tau and y only at LO (scaling check)
    return out


def rotate(lam: float, mu: float, nu: float, d: float) -> dict:
    """Faccioli et al. 2010, Eq. (21), with lambda_phi = nu / 2, lambda_thetaphi = mu."""
    lph = nu / 2.0
    big = 0.5 * (lam - lph) * math.sin(d) ** 2 - 0.5 * mu * math.sin(2 * d)
    lam_n = (lam - 3.0 * big) / (1.0 + big)
    lph_n = (lph + big) / (1.0 + big)
    mu_n = (mu * math.cos(2 * d) - 0.5 * (lam - lph) * math.sin(2 * d)) / (1.0 + big)
    return {"lambda": lam_n, "mu": mu_n, "nu": 2.0 * lph_n}


def invariants(lam: float, mu: float, nu: float) -> dict:
    lph = nu / 2.0
    return {"lambda_tilde": (lam + 3.0 * lph) / (1.0 - lph), "F": (1.0 + lam + 2.0 * lph) / (3.0 + lam),
            "lam_tung_1_minus_lambda_minus_2nu": 1.0 - lam - 2.0 * nu}


def positivity(lam: float, mu: float, nu: float) -> list[str]:
    """The distribution must be >= 0 on the whole sphere. With r the lepton direction, W = r^T (I + M) r,
    M = [[nu/2, 0, mu], [0, -nu/2, 0], [mu, 0, lambda]] (derived here), so W >= 0 exactly when the eigenvalues of
    I + M are >= 0. Faccioli et al. 2010, Eq. 22 (from |lambda| <= 1 in every frame) is a separate condition: neither
    implies the other, and both are required."""
    lph, bad = nu / 2.0, []
    if abs(lam) > 1 + 1e-12:
        bad.append("|lambda| <= 1")
    if abs(lph) > 0.5 * (1 + lam) + 1e-12:
        bad.append("|nu/2| <= (1 + lambda)/2 (Eq. 22)")
    if abs(mu) > 0.5 * (1 - lph) + 1e-12:
        bad.append("|mu| <= (1 - nu/2)/2 (Eq. 22)")
    a, c = 1.0 + lph, 1.0 + lam
    xz_min = 0.5 * (a + c) - math.sqrt(0.25 * (a - c) ** 2 + mu * mu)
    if min(1.0 - lph, xz_min) < -1e-12:
        bad.append("W >= 0 on the sphere (eigenvalues of I + M)")
    return bad


def hx_to_cs_angle(m: float, qt: float, y: float) -> float:
    """d_HX->CS = arccos(m p_L / (m_T p)) (Faccioli et al. 2010, Eq. 28), dilepton in the hadronic c.m. frame."""
    mt = math.sqrt(m * m + qt * qt)
    pl = mt * math.sinh(y)
    p = math.hypot(pl, qt)
    if p == 0:
        return 0.0
    return math.acos(max(-1.0, min(1.0, m * pl / (mt * p))))


def frames(a) -> dict:
    m, qt, y = _num("--M", a.M, True), _num("--qT", a.qT), _num("--y", a.y)
    if qt < 0:
        raise DYError("--qT must be >= 0")
    lam, mu, nu = (_num(n, v) for n, v in (("--lambda", a.lam), ("--mu", a.mu), ("--nu", a.nu)))
    bad = positivity(lam, mu, nu)
    if bad:
        raise DYError(f"angular parameters outside the positivity domain: {bad}", status="refused")
    d = hx_to_cs_angle(m, qt, y)
    if a.from_frame == a.to_frame:
        d = 0.0
    elif a.from_frame == "CS":
        d = -d
    new = rotate(lam, mu, nu, d)
    inv_old, inv_new = invariants(lam, mu, nu), invariants(new["lambda"], new["mu"], new["nu"])
    return {"from": a.from_frame, "to": a.to_frame, "rotation_angle_rad": d, "input": {"lambda": lam, "mu": mu, "nu": nu},
            "output": new, "invariants_before": inv_old, "invariants_after": inv_new}


def lam_tung(a) -> dict:
    lam, nu = _num("--lambda", a.lam), _num("--nu", a.nu)
    out = {"one_minus_lambda_minus_2nu": 1.0 - lam - 2.0 * nu}
    if a.sigma_lambda is not None or a.sigma_nu is not None:
        sl, sn = _num("--sigma-lambda", a.sigma_lambda or 0.0), _num("--sigma-nu", a.sigma_nu or 0.0)
        rho = _num("--rho", a.rho if a.rho is not None else 0.0)
        if not -1 <= rho <= 1 or sl < 0 or sn < 0:
            raise DYError("need sigma >= 0 and -1 <= rho <= 1")
        out["sigma"] = math.sqrt(sl * sl + 4.0 * sn * sn + 4.0 * rho * sl * sn)
        out["propagation"] = "linear, var = s_l^2 + 4 s_n^2 + 4 rho s_l s_n (rho is the user's)"
    return out


def coefficients(a) -> dict:
    if a.A0 is not None:
        a0, a1, a2 = _num("--A0", a.A0), _num("--A1", a.A1), _num("--A2", a.A2)
        if a0 <= -2:
            raise DYError("A0 must exceed -2")
        return {"lambda": (2 - 3 * a0) / (2 + a0), "mu": 2 * a1 / (2 + a0), "nu": 2 * a2 / (2 + a0),
                "A0_minus_A2": a0 - a2}
    lam, mu, nu = _num("--lambda", a.lam), _num("--mu", a.mu), _num("--nu", a.nu)
    if lam <= -3:
        raise DYError("lambda must exceed -3")
    a0 = 2 * (1 - lam) / (3 + lam)
    return {"A0": a0, "A1": mu * (2 + a0) / 2, "A2": nu * (2 + a0) / 2}


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _beam_args(p):
    p.add_argument("--sqrt-s", type=float, help="GeV, hadron-hadron centre-of-mass energy")
    for n in ("E1", "m1", "E2", "m2"):
        p.add_argument(f"--{n}", type=float, help="GeV; beam 1 along +z, beam 2 along -z (lab frame)")
    p.add_argument("--rapidity-frame", choices=("cm", "lab"), required=True)


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    px = sub.add_parser("xsec")
    pc = sub.add_parser("convert")
    for p in (px, pc):
        _beam_args(p)
        p.add_argument("--M", type=float)
        p.add_argument("--y", type=float)
        p.add_argument("--xF", type=float)
        p.add_argument("--xF-definition", choices=XF_DEFS)
        p.add_argument("--x1", type=float)
        p.add_argument("--x2", type=float)
        p.add_argument("--tau", type=float)
        add_status_argument(p)
    px.add_argument("--alpha", type=float, required=True)
    px.add_argument("--alpha-label", required=True)
    px.add_argument("--bosons", choices=("gamma", "gammaZ"), required=True)
    px.add_argument("--partons", required=True)
    px.add_argument("--resonance-window", action="append")
    px.add_argument("--allow-in-window", action="store_true")
    pf = sub.add_parser("frames")
    pf.add_argument("--M", type=float, required=True)
    pf.add_argument("--qT", type=float, required=True)
    pf.add_argument("--y", type=float, required=True, help="dilepton rapidity in the hadronic c.m. frame")
    pf.add_argument("--from", dest="from_frame", choices=("CS", "HX"), required=True)
    pf.add_argument("--to", dest="to_frame", choices=("CS", "HX"), required=True)
    for p in (pf,):
        p.add_argument("--lambda", dest="lam", type=float, required=True)
        p.add_argument("--mu", type=float, required=True)
        p.add_argument("--nu", type=float, required=True)
        add_status_argument(p)
    pl = sub.add_parser("lam-tung")
    pl.add_argument("--lambda", dest="lam", type=float, required=True)
    pl.add_argument("--nu", type=float, required=True)
    pl.add_argument("--sigma-lambda", type=float)
    pl.add_argument("--sigma-nu", type=float)
    pl.add_argument("--rho", type=float)
    add_status_argument(pl)
    pk = sub.add_parser("coefficients")
    for n in ("A0", "A1", "A2"):
        pk.add_argument(f"--{n}", type=float)
    pk.add_argument("--lambda", dest="lam", type=float)
    pk.add_argument("--mu", type=float)
    pk.add_argument("--nu", type=float)
    add_status_argument(pk)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    conventions = {"unit_system": "natural-HEP (GeV, hbar = c = 1); pb via (hbar c)^2 (CODATA 2022)",
                   "exchanged_bosons": "photon only", "order": "LO (q qbar -> gamma* -> l+ l-, N_c = 3)",
                   "angular_parametrization": "1 + lambda cos^2 + mu sin 2theta cos phi + (nu/2) sin^2 cos 2phi"}
    try:
        if a.cmd == "xsec":
            out = xsec(a)
            conventions.update(rapidity_frame=a.rapidity_frame, xF_definition=a.xF_definition or "not-applicable",
                               em_coupling=f"alpha = {a.alpha} ({a.alpha_label})")
        elif a.cmd == "convert":
            out, _ = resolve_point(a)
            conventions.update(rapidity_frame=a.rapidity_frame, kinematics="LO, q_T = 0")
        elif a.cmd == "frames":
            out = frames(a)
            conventions.update(frame=f"{a.from_frame} -> {a.to_frame}; beam 1 along +z, y axis along P1' x P2' "
                                     "(Faccioli et al. 2010, Eqs. 25, 27)")
        elif a.cmd == "lam-tung":
            out = lam_tung(a)
        else:
            if (a.A0 is None) == (a.lam is None) or (a.A0 is not None and None in (a.A1, a.A2)) or \
                    (a.lam is not None and None in (a.mu, a.nu)):
                raise DYError("give --A0 --A1 --A2, or --lambda --mu --nu")
            out = coefficients(a)
    except DYError as exc:
        print(json.dumps({"status": exc.status, **base, "reason": str(exc)}, indent=1))
        return exit_code(exc.status)
    print(json.dumps({"status": "ok", **base, "conventions": conventions, "derivation_status": "analytic-derivation",
                      "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())

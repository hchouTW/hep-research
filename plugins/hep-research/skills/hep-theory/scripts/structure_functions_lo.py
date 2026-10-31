#!/usr/bin/env python3
"""Leading-order (quark-parton model) DIS structure functions and neutral- and charged-current cross sections (Th14).

Purpose: F_2, 2xF_1, F_L, xF_3, the NC reduced cross section and d2sigma/dx dy, d2sigma/dx dQ^2 from parton values the
user supplies, with every convention explicit. See <plugin root>/skills/hep-theory/references/dis-structure-functions.md.
Source: PDG 2026 review "Structure Functions" (Aschenauer, Thorne, Yoshida, revised August 2025), read in full text
2026-10-23: cross section Eq. (18.16) with Y_+/- = 1 +/- (1 - y)^2 and F_L = F_2 - 2xF_1 (18.17); in its last term the
minus sign is for an incoming e+ or antineutrino and the plus sign for e- or neutrino (text after Eq. 18.8); propagator
and coupling ratios eta_gammaZ, eta_Z, eta_W (18.4); NC combinations F_2^NC, xF_3^NC for e+-N with lepton helicity
lambda (18.11, 18.12), g_V^e = -1/2 + 2 sin^2 theta_W, g_A^e = -1/2 (after 18.3); eta^CC = (1 +/- lambda)^2 eta_W for
l+- and 4 eta_W for neutrinos (18.9); quark-parton model F_2^gamma, F_2^gammaZ, F_2^Z, F_3^gammaZ, F_3^Z with
g_V^q = +/-1/2 - 2 e_q sin^2 theta_W, g_A^q = +/-1/2 (18.18); F^{W-} = 2x(u + dbar + sbar + c), F_3^{W-} =
2(u - dbar - sbar + c) and F^{W+} by d <-> u, s <-> c (18.19, CKM mixing neglected); 2xF_1 = F_2 (Callan-Gross).
Derived here: a beam of longitudinal polarization P_e enters NC through lambda -> P_e (Eqs. 18.11-18.12 are linear in
lambda) and CC through eta^CC = 2 (1 +/- P_e) eta_W (the helicity average of (1 +/- lambda)^2); d2sigma/dx dQ^2 =
(y / Q^2) d2sigma/dx dy from Eq. (18.1) with Q^2 = x y (s - M^2).
Derivation status: analytic-derivation (LO parton model, massless partons, target mass neglected in the y dependence:
Eq. 18.16 is the M^2/Q^2 -> 0 limit of Eq. 18.8). F_L = 0 at this order; it starts at O(alpha_s).
Inputs: --x, --Q2 (GeV^2), and --s (GeV^2) or head-on beams --E-lepton --E-hadron (GeV, massless lepton) with --M
(target mass per nucleon, GeV, supplied by the caller); --lepton {e-,e+,mu-,mu+,nu,nubar}; --polarization P_e
(charged leptons); --bosons {gamma,gammaZ,CC}; --sf-signs pdg (the only supported sign convention, PDG 2026 Eq. 18.8);
--alpha and --alpha-label; for gammaZ: --sin2w, --mz, --gf, --ew-scheme; for CC: --mw, --gf, --ew-scheme, --ckm
diagonal; --target {p,n} or --Z --A (per-nucleon isospin combination of bound-proton values, no nuclear model);
--target-normalization {per-nucleon,per-nucleus}; --target-mass-treatment neglected; --heavy-quark-scheme LABEL;
--partons FILE: {"representation": "xf", "values": {"d": .., "u": .., "s": .., "c": .., "b": .., "dbar": .., "ubar": ..,
"sbar": .., "cbar": .., "bbar": ..}} = x f_i(x, Q^2) of the proton (or bound proton) at this x and Q^2. Optional
--q2-min / --w2-min classify the point against the user's validity bounds; no default threshold is shipped.
Output JSON: status, status_label, inputs, conventions, derivation_status, outputs (structure functions, their gamma,
gammaZ and Z or W parts, eta factors, y, W^2, the bracket Y_+ F_2 -/+ Y_- xF_3 - y^2 F_L, sigma_r (NC), d2sigma/dx dy in
GeV^-2 and pb, d2sigma/dx dQ^2 in GeV^-4 and pb/GeV^2), checks, checks_not_run.
Exit codes (core/status.py): 0 ok; 2 rejected (missing or unreadable input, missing flavour, non-finite value, x outside
(0, 1] without --allow-nuclear-x, y > 1, G_F, M_Z or M_W <= 0, sin^2 theta_W outside (0, 1), a convention the
script does not implement); no negative verdict is issued.
Standard library only; (hbar c)^2 from core/constants (CODATA 2022).
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

FLAVOURS = ("d", "u", "s", "c", "b", "dbar", "ubar", "sbar", "cbar", "bbar")
QUARKS = ("d", "u", "s", "c", "b")
CHARGE = {"d": -1.0 / 3.0, "u": 2.0 / 3.0, "s": -1.0 / 3.0, "c": 2.0 / 3.0, "b": -1.0 / 3.0}
T3 = {"d": -0.5, "u": 0.5, "s": -0.5, "c": 0.5, "b": -0.5}  # sign of g_A^q = +/- 1/2 (u-type +, d-type -)
LEPTONS = {"e-": -1, "e+": 1, "mu-": -1, "mu+": 1, "nu": 0, "nubar": 0}
SOURCE = "PDG 2026 review 'Structure Functions', Eqs. (18.1), (18.4), (18.8)-(18.12), (18.16)-(18.19), read 2026-10-23"


class SFError(ValueError):
    """Input the calculation cannot use (run status rejected, exit 2)."""


def _finite(name, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SFError(f"{name} must be a number, got {v!r}")
    v = float(v)
    if not math.isfinite(v):
        raise SFError(f"{name} is not finite")
    return v


def load_partons(path: str) -> dict:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SFError(f"cannot read --partons {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("representation") != "xf" or not isinstance(doc.get("values"), dict):
        raise SFError('--partons must be {"representation": "xf", "values": {flavour: x f(x, Q^2)}}')
    vals = doc["values"]
    missing = [f for f in FLAVOURS if f not in vals]
    if missing:
        raise SFError(f"missing flavours in --partons: {missing} (give 0 for a flavour that is absent)")
    return {f: _finite(f"x{f}", vals[f]) for f in FLAVOURS}


def isospin_target(proton: dict, z: float, a: float) -> dict:
    """Per-nucleon combination (Z/A) f^p + ((A-Z)/A) f^n with f^n from f^p by u <-> d, ubar <-> dbar (isospin)."""
    neutron = dict(proton, u=proton["d"], d=proton["u"], ubar=proton["dbar"], dbar=proton["ubar"])
    wp, wn = z / a, (a - z) / a
    return {f: wp * proton[f] + wn * neutron[f] for f in FLAVOURS}


def nc_parts(xf: dict, sin2w: float) -> dict:
    """PDG Eq. (18.18) with x f inputs: F_2^gamma, F_2^gammaZ, F_2^Z, xF_3^gammaZ, xF_3^Z (F_3^gamma = 0)."""
    out = dict.fromkeys(("F2_gamma", "F2_gammaZ", "F2_Z", "xF3_gammaZ", "xF3_Z"), 0.0)
    for q in QUARKS:
        e, ga = CHARGE[q], T3[q]
        gv = ga - 2.0 * e * sin2w
        plus, minus = xf[q] + xf[q + "bar"], xf[q] - xf[q + "bar"]
        out["F2_gamma"] += e * e * plus
        out["F2_gammaZ"] += 2.0 * e * gv * plus
        out["F2_Z"] += (gv * gv + ga * ga) * plus
        out["xF3_gammaZ"] += 2.0 * e * ga * minus
        out["xF3_Z"] += 2.0 * gv * ga * minus
    return out


def cc_parts(xf: dict, w_charge: int) -> dict:
    """PDG Eq. (18.19): F_2^{W-} = 2x(u + dbar + sbar + c), xF_3^{W-} = 2x(u - dbar - sbar + c); W+ by d<->u, s<->c.
    The b quark is left out, as in Eq. (18.19) (its CKM partner t is not active)."""
    if w_charge < 0:
        up, down = ("u", "c"), ("dbar", "sbar")
    else:
        up, down = ("d", "s"), ("ubar", "cbar")
    return {"F2_W": 2.0 * (sum(xf[q] for q in up) + sum(xf[q] for q in down)),
            "xF3_W": 2.0 * (sum(xf[q] for q in up) - sum(xf[q] for q in down))}


def compute(a) -> dict:
    x, q2 = _finite("--x", a.x), _finite("--Q2", a.Q2)
    if q2 <= 0:
        raise SFError("--Q2 must be > 0")
    nucleus = a.A is not None
    if nucleus:
        z, mass_a = _finite("--Z", a.Z), _finite("--A", a.A)
        if mass_a < 1 or z < 0 or z > mass_a:
            raise SFError("need 0 <= Z <= A and A >= 1")
    if not (x > 0 and (x <= 1 or (a.allow_nuclear_x and nucleus and x <= a.A))):
        raise SFError("x must be in (0, 1] (per-nucleon x up to A only for a nucleus with --allow-nuclear-x)")
    m = _finite("--M", a.M)
    if m < 0:
        raise SFError("--M must be >= 0")
    if a.s is not None:
        s = _finite("--s", a.s)
    elif a.E_lepton is not None and a.E_hadron is not None:
        el, eh = _finite("--E-lepton", a.E_lepton), _finite("--E-hadron", a.E_hadron)
        if el <= 0 or eh < m:
            raise SFError("need E_lepton > 0 and E_hadron >= M")
        s = m * m + 2.0 * el * (eh + math.sqrt(max(eh * eh - m * m, 0.0)))
    else:
        raise SFError("give --s, or --E-lepton and --E-hadron (head-on, massless lepton)")
    if s <= m * m:
        raise SFError("s must exceed M^2")
    y = q2 / (x * (s - m * m))
    if not 0 < y <= 1:
        raise SFError(f"y = Q^2 / (x (s - M^2)) = {y:.6g} is outside (0, 1] at this s")
    alpha = _finite("--alpha", a.alpha)
    if not 0 < alpha < 1:
        raise SFError("--alpha must be in (0, 1)")

    charge = LEPTONS[a.lepton]
    neutrino = charge == 0
    if neutrino and a.bosons != "CC":
        raise SFError("neutrino NC scattering is not implemented (PDG Eq. 18.8 NC covers charged leptons); use --bosons CC")
    if neutrino and a.polarization is not None:
        raise SFError("--polarization applies to charged leptons; neutrino helicity is fixed")
    if not neutrino and a.polarization is None:
        raise SFError("--polarization P_e is required for a charged lepton (0 for an unpolarized beam)")
    pol = 0.0 if neutrino else _finite("--polarization", a.polarization)
    if abs(pol) > 1:
        raise SFError("--polarization must be in [-1, 1]")
    if a.bosons in ("gammaZ", "CC"):
        for name in (("gf", "ew_scheme") + (("sin2w", "mz") if a.bosons == "gammaZ" else ("mw",))):
            if getattr(a, name) is None:
                raise SFError(f"--{name.replace('_', '-')} is required with --bosons {a.bosons}")
    for name in ("gf", "mz", "mw"):
        if getattr(a, name) is not None and not _finite(f"--{name}", getattr(a, name)) > 0:
            raise SFError(f"--{name} must be > 0")
    if a.sin2w is not None and not 0 < _finite("--sin2w", a.sin2w) < 1:
        raise SFError("--sin2w must be in (0, 1)")
    for name in ("q2_min", "w2_min"):
        if getattr(a, name) is not None:
            _finite(f"--{name.replace('_', '-')}", getattr(a, name))
    if a.bosons == "CC" and a.ckm is None:
        raise SFError("--ckm diagonal is required with --bosons CC (full CKM mixing is not implemented)")

    proton = load_partons(a.partons)
    if nucleus:
        xf = isospin_target(proton, z, mass_a)
        target_desc = f"nucleus Z={a.Z:g}, A={a.A:g}: per-nucleon isospin combination of bound-proton values"
    elif a.target == "n":
        xf = isospin_target(proton, 0.0, 1.0)
        target_desc = "neutron from proton values by u <-> d, ubar <-> dbar (isospin)"
    else:
        xf = proton
        target_desc = "proton"

    yp, ym = 1.0 + (1.0 - y) ** 2, 1.0 - (1.0 - y) ** 2
    outputs = {"x": x, "Q2_GeV2": q2, "s_GeV2": s, "y": y, "W2_GeV2": m * m + q2 * (1.0 / x - 1.0),
               "Y_plus": yp, "Y_minus": ym}
    if a.bosons == "CC":
        gf, mw = _finite("--gf", a.gf), _finite("--mw", a.mw)
        w_charge = -1 if a.lepton in ("e-", "mu-", "nubar") else 1
        parts = cc_parts(xf, w_charge)
        eta_w = 0.5 * (gf * mw * mw / (4.0 * math.pi * alpha) * q2 / (q2 + mw * mw)) ** 2
        eta = 4.0 * eta_w if neutrino else 2.0 * (1.0 + charge * pol) * eta_w
        f2, xf3 = parts["F2_W"], parts["xF3_W"]
        outputs.update(boson=f"W{'+' if w_charge > 0 else '-'}", eta_W=eta_w, eta=eta, parts=parts)
        sign = -1.0 if a.lepton in ("e+", "mu+", "nubar") else 1.0
    else:
        sin2w = _finite("--sin2w", a.sin2w) if a.bosons == "gammaZ" else 0.0
        parts = nc_parts(xf, sin2w)
        if a.bosons == "gamma":
            f2, xf3 = parts["F2_gamma"], 0.0
            parts = {"F2_gamma": parts["F2_gamma"]}
            outputs.update(eta_gammaZ=0.0, eta_Z=0.0)
        else:
            gf, mz = _finite("--gf", a.gf), _finite("--mz", a.mz)
            eta_gz = gf * mz * mz / (2.0 * math.sqrt(2.0) * math.pi * alpha) * q2 / (q2 + mz * mz)
            eta_z = eta_gz * eta_gz
            gve, gae = -0.5 + 2.0 * sin2w, -0.5
            lam = charge * pol  # Eqs. (18.11)-(18.12): the +/- is the lepton charge, lambda its helicity
            f2 = (parts["F2_gamma"] - (gve + lam * gae) * eta_gz * parts["F2_gammaZ"]
                  + (gve * gve + gae * gae + 2.0 * lam * gve * gae) * eta_z * parts["F2_Z"])
            xf3 = (-(gae + lam * gve) * eta_gz * parts["xF3_gammaZ"]
                   + (2.0 * gve * gae + lam * (gve * gve + gae * gae)) * eta_z * parts["xF3_Z"])
            outputs.update(eta_gammaZ=eta_gz, eta_Z=eta_z, g_V_e=gve, g_A_e=gae)
        eta = 1.0
        outputs.update(boson=a.bosons, eta=eta, parts=parts)
        sign = -1.0 if charge > 0 else 1.0
    fl = 0.0
    bracket = yp * f2 + sign * ym * xf3 - y * y * fl
    d2_dxdy = 2.0 * math.pi * alpha ** 2 / (x * y * q2) * eta * bracket
    d2_dxdq2 = y / q2 * d2_dxdy
    norm = 1.0 if a.target_normalization == "per-nucleon" or not nucleus else a.A
    gev2_pb = constants.hbar_c_squared("GeV^2 mb").value * 1e9  # GeV^2 mb -> GeV^2 pb
    outputs.update(F2=f2 * norm, two_x_F1=f2 * norm, FL=fl, xF3=xf3 * norm, xF3_sign_in_bracket=sign,
                   bracket=bracket * norm, normalization_factor=norm,
                   d2sigma_dx_dy_GeV2=d2_dxdy * norm, d2sigma_dx_dy_pb=d2_dxdy * norm * gev2_pb,
                   d2sigma_dx_dQ2_GeV4=d2_dxdq2 * norm, d2sigma_dx_dQ2_pb_per_GeV2=d2_dxdq2 * norm * gev2_pb)
    if a.bosons != "CC":
        outputs["sigma_r_NC"] = f2 * norm - y * y / yp * fl + sign * ym / yp * xf3 * norm
    validity = {}
    if a.q2_min is not None:
        validity["Q2_min"] = {"bound": a.q2_min, "inside": q2 >= a.q2_min}
    if a.w2_min is not None:
        validity["W2_min"] = {"bound": a.w2_min, "inside": outputs["W2_GeV2"] >= a.w2_min}
    outputs["validity"] = validity or "no bounds given (the validity domain is the user's to state)"
    conventions = {
        "unit_system": "natural-HEP (GeV, hbar = c = 1); cross sections also in pb via (hbar c)^2 (CODATA 2022)",
        "exchanged_bosons": {"gamma": "photon only", "gammaZ": "photon + Z with interference",
                             "CC": f"{outputs['boson']} exchange"}[a.bosons],
        "electroweak_scheme": a.ew_scheme or "not-applicable (photon exchange only)",
        "em_coupling": f"alpha = {alpha} ({a.alpha_label})",
        "structure_function_signs": "PDG 2026 Eq. (18.8): -xF_3 term for e+ and antineutrino, + for e- and neutrino; "
                                    "xF_3^NC per Eq. (18.12)",
        "heavy_quark_scheme": a.heavy_quark_scheme,
        "target_mass_treatment": "neglected in the y dependence (Eq. 18.16, M^2/Q^2 -> 0); M enters y and W^2 only",
        "target_normalization": f"{a.target_normalization} ({target_desc})",
        "factorization_scheme": "not-applicable (LO parton model)",
        "ckm": a.ckm or "not-applicable",
        "lepton": f"{a.lepton}, P_e = {pol}" if not neutrino else a.lepton,
        "source": SOURCE,
    }
    checks = [
        {"name": "callan_gross_2xF1_equals_F2", "result": "pass (LO parton model, by construction)"},
        {"name": "FL_zero_at_LO", "result": "pass (F_L starts at O(alpha_s))"},
        {"name": "y_in_unit_interval", "result": "pass"},
    ]
    return {"outputs": outputs, "conventions": conventions, "checks": checks}


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
    ap.add_argument("--s", type=float, help="lepton-nucleon s in GeV^2")
    ap.add_argument("--E-lepton", type=float)
    ap.add_argument("--E-hadron", type=float, help="per nucleon, GeV")
    ap.add_argument("--M", type=float, required=True, help="target mass per nucleon in GeV (caller's convention)")
    ap.add_argument("--lepton", choices=tuple(LEPTONS), required=True)
    ap.add_argument("--polarization", type=float, help="longitudinal lepton polarization P_e in [-1, 1]")
    ap.add_argument("--bosons", choices=("gamma", "gammaZ", "CC"), required=True)
    ap.add_argument("--sf-signs", choices=("pdg",), required=True, help="xF_3 sign convention (PDG 2026 Eq. 18.8)")
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--alpha-label", required=True, help="e.g. 'alpha(0), CODATA 2022' or 'alpha(M_Z) from <source>'")
    ap.add_argument("--sin2w", type=float)
    ap.add_argument("--mz", type=float)
    ap.add_argument("--mw", type=float)
    ap.add_argument("--gf", type=float, help="G_F in GeV^-2")
    ap.add_argument("--ew-scheme", help="label of the electroweak scheme the inputs belong to")
    ap.add_argument("--ckm", choices=("diagonal",))
    ap.add_argument("--target", choices=("p", "n"))
    ap.add_argument("--Z", type=float)
    ap.add_argument("--A", type=float)
    ap.add_argument("--allow-nuclear-x", action="store_true")
    ap.add_argument("--target-normalization", choices=("per-nucleon", "per-nucleus"), required=True)
    ap.add_argument("--target-mass-treatment", choices=("neglected",), required=True)
    ap.add_argument("--heavy-quark-scheme", required=True, help="label, e.g. 'ZM-VFNS, n_f = 5'")
    ap.add_argument("--partons", required=True, help="JSON file of x f_i(x, Q^2)")
    ap.add_argument("--q2-min", type=float)
    ap.add_argument("--w2-min", type=float)
    add_status_argument(ap)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    try:
        if (a.target is None) == (a.A is None) or (a.A is None) != (a.Z is None):
            raise SFError("give exactly one target: --target p|n, or --Z and --A")
        res = compute(a)
    except SFError as exc:
        print(json.dumps({"status": "rejected", **base, "reason": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "conventions": res["conventions"],
                      "derivation_status": "analytic-derivation", "order": "LO (quark-parton model)",
                      "outputs": res["outputs"], "checks": res["checks"],
                      "checks_not_run": ["higher orders (coefficient functions beyond LO)", "target-mass corrections",
                                         "heavy-quark mass effects", "higher twist", "QED radiative corrections"]},
                     indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Derivation checks for theory:heliospheric-modulation (SymPy): the force-field solution of the zero-streaming
transport condition, the flux relation it implies, and the closed forms of a power-law local interstellar spectrum
(LIS) modulated in total kinetic energy, kinetic energy per nucleon and rigidity.

Notation (c = 1, e = 1): p momentum (GeV), m rest mass of the nucleus (GeV), |Z| = Z charge number, T = sqrt(p^2 + m^2)
- m kinetic energy (GeV), R = p / Z rigidity (GV), beta = p / E. f(r, p) is the phase-space density, the flux per unit
kinetic energy is J_T = p^2 f.

1. Force-field equation (zero radial streaming, spherical symmetry, steady state; helmod:C01):
       kappa(r, p) df/dr + (V(r) p / 3) df/dp = 0,   kappa = kappa_1(r) beta R   (separable, proportional to rigidity).
   With phi(r) = int_r^r_b V / (3 kappa_1) dr' (so dphi/dr = -V / (3 kappa_1)), f = F(T + Z phi(r)) solves it for
   any F: the solution is constant along T + Z phi (the characteristic). The opposite sign F(T - Z phi) does not.
2. At the boundary r_b, phi = 0 and f = f_LIS. So J_TOA(T) = (p(T)^2 / p(T')^2) J_LIS(T'), T' = T + Z phi, and
   p^2 = T (T + 2 m) = E^2 - m^2: the Gleeson-Axford form J / (E^2 - E_0^2) = invariant (helmod:C01).
3. Closed forms for J_LIS = A x^-gamma in the variable x of each kind (same A, gamma, x in its own unit):
       Ek_total:        J = A T (T + 2m) / (T' (T' + 2m)) T'^-gamma,                      T' = T + Z phi
       Ek_per_nucleon:  J = A t (t + 2 m_n) / (t' (t' + 2 m_n)) t'^-gamma, m_n = m / A_n,  t' = t + (Z / A_n) phi
       rigidity:        J = A (p^3 E') / (p'^3 E) R'^-gamma, p = Z R, E' = E + Z phi, p' = sqrt(E'^2 - m^2), R' = p'/Z
   Each is checked to equal the total-energy relation times the Jacobian dT/dx at the two points.
4. Limits: phi -> 0 returns the LIS; J_TOA / J_LIS(x) -> 1 - (gamma + 2) Z phi / T at large T (Ek_total);
   J_TOA ~ 2 m A T / (Z phi (Z phi + 2 m)) (Z phi)^-gamma, linear in T, as T -> 0.
Status: analytic derivation under the force-field assumptions (not a formal proof; SymPy checks the algebra). The
force field itself is an approximation to the transport equation; its validity range is in the model file.

Usage: python3 derive.py [--out ../derivations/derivation.json]
Exit 0 all checks pass, 1 a check fails, 2 SymPy is missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import sympy as sp
except ImportError as exc:  # run as a script: explain the missing package; imported: the caller sees the error
    if __name__ != "__main__":
        raise
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        sys.exit(0)
    print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name or 'sympy'}",
                      "hint": "run with a Python that has SymPy (skills/hep-computing/scripts/find_python.py "
                              "finds one), or install requirements-core.txt"}))
    sys.exit(2)

HERE = Path(__file__).resolve().parent
pos = {"positive": True}
r, p, m, Z, T, A, gamma, phi0, An, t, R = sp.symbols("r p m Z T A gamma phi A_n t R", **pos)
kappa1, V, phi_r, F = sp.Function("kappa_1"), sp.Function("V"), sp.Function("phi"), sp.Function("F")


def kinetic(p_):
    return sp.sqrt(p_ ** 2 + m ** 2) - m


def force_field_pde(sign: int = 1):
    """Residual of the force-field equation for f = F(T(p) + sign Z phi(r)), with dphi/dr = -V/(3 kappa_1)."""
    f = F(kinetic(p) + sign * Z * phi_r(r))
    beta = p / sp.sqrt(p ** 2 + m ** 2)
    kappa = kappa1(r) * beta * p / Z
    res = kappa * sp.diff(f, r) + V(r) * p / 3 * sp.diff(f, p)
    res = res.subs(sp.Derivative(phi_r(r), r), -V(r) / (3 * kappa1(r))).doit()
    return sp.simplify(res)


def characteristic_invariant():
    """d(T + Z phi)/dr along dp/dr = V p / (3 kappa): zero."""
    beta = p / sp.sqrt(p ** 2 + m ** 2)
    dp_dr = V(r) * p / (3 * kappa1(r) * beta * p / Z)
    return sp.simplify(sp.diff(kinetic(p), p) * dp_dr + Z * (-V(r) / (3 * kappa1(r))))


def flux_ratio(t_toa, t_lis, mass):
    """p(T)^2 / p(T')^2 with p^2 = T (T + 2 m)."""
    return t_toa * (t_toa + 2 * mass) / (t_lis * (t_lis + 2 * mass))


def closed_forms():
    """The three closed forms of step 3, as SymPy expressions."""
    tp = T + Z * phi0
    ek_total = A * flux_ratio(T, tp, m) * tp ** (-gamma)
    mn = m / An
    tn_p = t + Z / An * phi0
    per_nucleon = A * flux_ratio(t, tn_p, mn) * tn_p ** (-gamma)
    p_r = Z * R
    e = sp.sqrt(p_r ** 2 + m ** 2)
    e_p = e + Z * phi0
    p_p = sp.sqrt(e_p ** 2 - m ** 2)
    rigidity = A * p_r ** 3 * e_p / (p_p ** 3 * e) * (p_p / Z) ** (-gamma)
    return {"Ek_total": ek_total, "Ek_per_nucleon": per_nucleon, "rigidity": rigidity}


def derive() -> dict:
    cf = closed_forms()
    checks = {}
    checks["force_field_solution_F_of_T_plus_Z_phi"] = force_field_pde(+1) == 0
    checks["wrong_sign_F_of_T_minus_Z_phi_fails"] = force_field_pde(-1) != 0
    checks["T_plus_Z_phi_constant_on_characteristic"] = characteristic_invariant() == 0
    checks["p2_equals_T_T_plus_2m_equals_E2_minus_m2"] = (
        sp.simplify(kinetic(p) * (kinetic(p) + 2 * m) - p ** 2) == 0
        and sp.simplify((T + m) ** 2 - m ** 2 - T * (T + 2 * m)) == 0)
    # per nucleon: J_n(t) = A_n J_T(T) at T = A_n t, with the LIS power law in t (same A, gamma in t)
    j_lis_t = lambda tt: A * (tt / An) ** (-gamma) / An  # noqa: E731  J_LIS per GeV of T for a power law in t
    tp = An * t + Z * phi0
    via_total = An * flux_ratio(An * t, tp, m) * j_lis_t(tp)
    checks["per_nucleon_form_equals_total_energy_relation"] = sp.simplify(via_total - cf["Ek_per_nucleon"]) == 0
    # rigidity: J_R = J_T dT/dR = J_T Z beta; LIS power law in R'
    p_r = Z * R
    e = sp.sqrt(p_r ** 2 + m ** 2)
    e_p = e + Z * phi0
    p_p = sp.sqrt(e_p ** 2 - m ** 2)
    beta, beta_p = p_r / e, p_p / e_p
    via_total_r = beta / beta_p * (p_r ** 2 / p_p ** 2) * A * (p_p / Z) ** (-gamma)
    checks["rigidity_form_equals_total_energy_relation"] = sp.simplify(via_total_r - cf["rigidity"]) == 0
    checks["rigidity_shift_is_Z_phi_in_kinetic_energy"] = sp.simplify(kinetic(p_p) - kinetic(p_r) - Z * phi0) == 0
    lis = {"Ek_total": A * T ** (-gamma), "Ek_per_nucleon": A * t ** (-gamma), "rigidity": A * R ** (-gamma)}
    checks["phi_zero_returns_the_lis"] = all(sp.simplify(cf[k].subs(phi0, 0) - lis[k]) == 0 for k in cf)
    # high-energy limit: ratio -> 1 - (gamma + 2) Z phi / T + O(T^-2)
    u = sp.symbols("u", positive=True)  # u = 1/T
    ratio = sp.simplify((cf["Ek_total"] / lis["Ek_total"]).subs(T, 1 / u))
    hi = sp.series(ratio, u, 0, 2).removeO()
    checks["high_energy_ratio_1_minus_gamma_plus_2_Z_phi_over_T"] = sp.simplify(hi - (1 - (gamma + 2) * Z * phi0 * u)) == 0
    lo = sp.limit(cf["Ek_total"] / T, T, 0)
    checks["low_energy_flux_linear_in_T"] = sp.simplify(
        lo - 2 * m * A / (Z * phi0 * (Z * phi0 + 2 * m)) * (Z * phi0) ** (-gamma)) == 0
    return {
        "label": f"theory:heliospheric-modulation force field and power-law closed forms (SymPy {sp.__version__})",
        "status": "analytic-derivation",
        "assumptions": [
            "zero radial streaming (force-field equation), spherical symmetry, steady state",
            "diffusion coefficient separable and proportional to rigidity: kappa = kappa_1(r) beta R",
            "phi(r) = int_r^r_b V / (3 kappa_1) dr', phi(r_b) = 0 at the modulation boundary",
            "J per unit kinetic energy = p^2 f; c = 1, e = 1; phi in GV, Z phi in GeV",
            "the LIS power law is written in the variable of each energy kind (Ek_total, Ek_per_nucleon, rigidity)"],
        "results": {"solution": "f(r, T) = F(T + Z phi(r)); J_TOA(T) = p(T)^2 / p(T + Z phi)^2 J_LIS(T + Z phi)",
                    "closed_forms": {k: sp.sstr(v) for k, v in cf.items()},
                    "high_energy_ratio": sp.sstr(hi),
                    "low_energy_slope": sp.sstr(sp.simplify(lo))},
        "checks": {k: bool(v) for k, v in checks.items()},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None, help="write the derivation JSON here")
    opts = ap.parse_args(argv)
    out = derive()
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

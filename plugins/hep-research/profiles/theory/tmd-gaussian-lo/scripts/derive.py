#!/usr/bin/env python3
"""Derivations for theory:tmd-gaussian-lo: Gaussian-ansatz TMDs at leading order, no evolution (SymPy, exact).

Inputs (cited): the Gaussian ansatz f_q(x, k) = f_q(x) exp(-k^2/<k^2>)/(pi <k^2>), D(z, p) = D(z) exp(-p^2/<p^2>)/
(pi <p^2>) and p = P_T - z k at O(k/Q) (Anselmino et al., Eqs. 29, 32-37, tmdg:C01-C03); the convolution
C[w f D] = x sum e^2 int d^2p_T d^2k_T delta(p_T - k_T - P_h/z) w f(x, p_T^2) D(z, k_T^2) with
D_1(z) = z^2 int d^2k_T D_1(z, k_T^2) (Bacchetta et al., Eqs. 3.41, 4.1-4.2, 4.11, 4.20, 4.21, tmdg:C05-C07); the
Sivers parametrization of Anselmino et al. Eqs. 48-50, 58, 63, 68 (tmdg:C04); f_1T^perp,DY = -f_1T^perp,SIDIS and
Delta^N f = -(2 |k_T|/M) f_1T^perp (Trento conventions Eqs. 4, 14, tmdg:C08).

Steps:
 1. Normalization of the Gaussians (Eqs. 36-37) and of the D_1(z, k_T^2) Gaussian with the z^2 of Eq. 3.41.
 2. SIDIS, Anselmino form: x sum e^2 int d^2k f(x, k) D(z, P - z k) = x sum e^2 f D exp(-P^2/<P_T^2>)/(pi <P_T^2>),
    <P_T^2> = <p^2> + z^2 <k^2> (Eq. 39); its d^2P integral is x sum e^2 f D (Bacchetta Eq. 4.21).
 3. SIDIS, Bacchetta form (Eqs. 4.1-4.2) with k_T the quark momentum relative to the hadron: the same F_UU,T once
    <p^2> = z^2 <k_T^2> (hadron relative to quark = -z k_T).
 4. Cahn term: int d^2k f [1 + (1-y)^2 - 4 (2-y) sqrt(1-y) (k_x/Q)] D(z, P - z k) reproduces Eq. 38; the same
    cos(phi_h) coefficient follows from Bacchetta Eq. 4.20 with the depolarization factors of Eqs. 2.9 and 2.11 at
    gamma = 0.
 5. Sivers: the phi_S, phi_h and d^2k integrals of Eq. 58 with Eqs. 63 and 68, at O(k/Q), reproduce Eqs. 64-67; the
    same asymmetry follows from Bacchetta Eq. 4.11 with f_1T^perp = -(M/(2|k_T|)) Delta^N f (Trento Eq. 4). The two
    papers' phi_h, phi_S coincide: Anselmino et al. (p. 2) use q along +z, P along -z, l = E(1, sin theta, 0, cos theta)
    with l_x > 0, P_T = P_T(cos phi_h, sin phi_h, 0), S_T = |S_T|(cos phi_S, sin phi_S, 0), and Trento Eq. 16 returns
    the same angles (q-hat x l = sin theta y-hat).
 6. Drell-Yan: int d^2k1 d^2k2 delta(k1 + k2 - q_T) G(k1; <k1^2>) G(k2; <k2^2>) = G(q_T; <k1^2> + <k2^2>), unit
    normalization (derived here; no source gives this line).
 7. Sivers sign change: with f_1T^perp,DY = -f_1T^perp,SIDIS (cited, time reversal) the Gaussian Sivers function and
    every quantity linear in it change sign between SIDIS and Drell-Yan.
Status: each step is an analytic derivation within the Gaussian ansatz and the O(k/Q) kinematics; the ansatz is a
model, so the profile's results carry heuristic-argument as their physics status. Not a formal proof.

Usage: python3 derive.py [--out ../derivations/derivation.json]
Exit 0 all checks pass, 1 a check fails, 2 SymPy is missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import platform
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

kx, ky, qx, qy, Px, Py = sp.symbols("k_x k_y q_x q_y P_x P_y", real=True)
kperp2, pperp2, kT2, k12, k22, Mp2 = sp.symbols("kperp2 pperp2 kT2 k1perp2 k2perp2 Mprime2", positive=True)
z, x, y, Q, P = sp.symbols("z x y Q P", positive=True)
phi, phih, phiS = sp.symbols("phi phi_h phi_S", real=True)
f0, D0, N = sp.symbols("f D N", real=True)  # collinear f_q(x), D_q(z), Sivers N_q(x)
OO = sp.oo


def G(vx, vy, w):
    """Normalized 2D Gaussian exp(-v^2/w)/(pi w)."""
    return sp.exp(-(vx ** 2 + vy ** 2) / w) / (sp.pi * w)


def int2(expr, u=kx, v=ky):
    return sp.integrate(sp.integrate(expr, (u, -OO, OO), conds="none"), (v, -OO, OO), conds="none")


def clean(expr):
    """Combine exponentials and cancel their (rational) exponents, so Gaussian results compare reliably."""
    e = sp.powsimp(sp.expand_power_exp(sp.sympify(expr)), force=True, combine="exp")
    return e.replace(lambda u: isinstance(u, sp.exp), lambda u: sp.exp(sp.factor(sp.cancel(sp.together(u.args[0])))))


def same(a, b) -> bool:
    """a == b for the Gaussian expressions here: the ratio, with exponents cancelled, simplifies to 1."""
    r = clean(sp.simplify(clean(a) / clean(b)))
    return sp.simplify(sp.cancel(sp.together(r)) - 1) == 0


def normalizations() -> dict:
    n_f = sp.simplify(int2(G(kx, ky, kperp2)) - 1) == 0
    d_bacchetta = D0 / z ** 2 * G(kx, ky, kT2)  # D_1(z, k_T^2) Gaussian with D_1(z) = z^2 int d^2k_T D_1(z, k_T^2)
    n_d = sp.simplify(z ** 2 * int2(d_bacchetta) - D0) == 0
    return {"gaussian_unit_normalization": bool(n_f), "bacchetta_D1_z2_normalization": bool(n_d)}


PT2 = pperp2 + z ** 2 * kperp2  # Eq. 39


def sidis_anselmino():
    """x int d^2k f(x, k) D(z, P - z k) per unit e^2 (Eq. 32 at leading power, Eqs. 34-35)."""
    return x * int2(f0 * G(kx, ky, kperp2) * D0 * G(Px - z * kx, Py - z * ky, pperp2))


def sidis_bacchetta():
    """C[f1 D1] of Eqs. 4.1-4.2 per unit e^2: delta(p_T - k_T - P/z) fixes k_T = p_T - P/z (p_T -> k_x, k_y)."""
    d1 = D0 / z ** 2 * G(kx - Px / z, ky - Py / z, kT2)
    return x * int2(f0 * G(kx, ky, kperp2) * d1)


def sidis_checks() -> dict:
    target = x * f0 * D0 * G(Px, Py, PT2)
    a_form = sidis_anselmino()
    b_form = sidis_bacchetta().subs(kT2, pperp2 / z ** 2)
    total = int2(target, Px, Py)
    return {"anselmino_form_gives_gaussian_with_PT2_eq39": same(a_form, target),
            "bacchetta_form_equals_anselmino_with_pperp2_z2_kT2": same(b_form, target),
            "integral_over_PhT_is_collinear_x_f_D": sp.simplify(total - x * f0 * D0) == 0}


def cahn_checks() -> dict:
    """Eq. 32-33 at O(k/Q) with lepton plane along x: hat-s^2 + hat-u^2 propto 1 + (1-y)^2 - 4 (k_x/Q)(2-y) sqrt(1-y)."""
    pxh, pyh = Px, Py  # P_T = P (cos phi_h, sin phi_h): P_x = P cos(phi_h), substituted after the integrals
    unpol = 1 + (1 - y) ** 2
    cahn = int2(G(kx, ky, kperp2) * kx * G(pxh - z * kx, pyh - z * ky, pperp2))
    gauss = int2(G(kx, ky, kperp2) * G(pxh - z * kx, pyh - z * ky, pperp2))
    mean_kx = clean(sp.simplify(cahn / gauss))
    eq38_ratio = -4 * (2 - y) * sp.sqrt(1 - y) * kperp2 * z * P / (PT2 * Q) * sp.cos(phih)
    from_eq32 = sp.simplify(-4 * (2 - y) * sp.sqrt(1 - y) * mean_kx / Q)
    on_shell = {Px: P * sp.cos(phih), Py: P * sp.sin(phih)}
    ok38 = (sp.simplify(from_eq32.subs(on_shell) - eq38_ratio) == 0
            and same(gauss.subs(on_shell), G(P * sp.cos(phih), P * sp.sin(phih), PT2)))
    # Bacchetta: sigma propto y^2/(2(1-eps)) [F_UU,T + sqrt(2 eps (1+eps)) cos(phi_h) F_UU^cos], gamma = 0
    eps = (1 - y) / (1 - y + y ** 2 / 2)  # Eq. 2.8 at gamma = 0
    depol = y ** 2 / (2 * (1 - eps))
    eq29 = sp.simplify(depol - (1 - y + y ** 2 / 2)) == 0
    # compare squares (both sides positive for 0 < y < 1)
    eq211 = sp.simplify(depol ** 2 * 2 * eps * (1 + eps) - (2 - y) ** 2 * (1 - y)) == 0
    # <h . p_T> with h = P_T/|P_T|: the mean quark k along the hadron direction
    mean_along = clean(sp.simplify(int2(G(kx, ky, kperp2) * kx * G(P - z * kx, -z * ky, pperp2))
                             / int2(G(kx, ky, kperp2) * G(P - z * kx, -z * ky, pperp2))))
    f_cos_over_fuu = -2 / Q * mean_along  # Eq. 4.20: F^cos = (2M/Q) C[-(h.p_T/M) f1 D1]
    bracket = (depol * 1 + (2 - y) * sp.sqrt(1 - y) * sp.cos(phih) * f_cos_over_fuu) / (unpol / 2)
    ok420 = sp.simplify(clean(bracket) - clean(1 + eq38_ratio / unpol)) == 0
    return {"cahn_eq32_reproduces_eq38_cos_phi_h_term": bool(ok38), "depolarization_eq2_9_at_gamma_0": bool(eq29),
            "depolarization_eq2_11_at_gamma_0": bool(eq211), "bacchetta_eq4_20_reproduces_eq38_bracket": bool(ok420),
            "mean_k_along_hadron": sp.sstr(mean_along)}


def sivers_checks() -> dict:
    """Eq. 58 with Eqs. 63, 68 at leading power: numerator / denominator vs Eqs. 64-67."""
    sqrt2e = sp.sqrt(2 * sp.E)
    k_hat2 = Mp2 * kperp2 / (Mp2 + kperp2)  # Eq. 67
    pt_hat2 = pperp2 + z ** 2 * k_hat2
    # phi_S integral of sin(phi - phi_S) sin(phi_h - phi_S) = pi cos(phi - phi_h)
    phis = sp.simplify(sp.integrate(sp.sin(phi - phiS) * sp.sin(phih - phiS), (phiS, 0, 2 * sp.pi)))
    ok_phis = sp.simplify(sp.expand_trig(phis - sp.pi * sp.cos(phi - phih))) == 0
    # with P_T along x (phi_h = 0 after the rotation-invariant phi_h integral): k h'(k) cos(phi - phi_h)/k = k_x/M'
    gk = G(kx, ky, kperp2)
    num_k = int2(2 * N * f0 * sqrt2e * kx / sp.sqrt(Mp2) * sp.exp(-(kx ** 2 + ky ** 2) / Mp2) * gk
                 * D0 * G(P - z * kx, -z * ky, pperp2))
    den_k = int2(f0 * gk * D0 * G(P - z * kx, -z * ky, pperp2))
    # numerator: (1/2pi) int dphi_S dphi_h ... = (1/2pi) * pi * 2pi * num_k; denominator: (1/2pi) (2pi)(2pi) den_k
    asym = sp.simplify((sp.pi * num_k) / (2 * sp.pi * den_k))
    eq65_over_eq66 = (2 * N * f0 * D0 * z * P * sqrt2e * k_hat2 ** 2 / (sp.sqrt(Mp2) * pt_hat2 ** 2 * kperp2)
                      * sp.exp(-P ** 2 / pt_hat2)) / (2 * sp.pi * f0 * D0 * sp.exp(-P ** 2 / PT2) / (sp.pi * PT2))
    ok64 = same(asym, eq65_over_eq66)
    # Bacchetta Eq. 4.11 with Trento Eq. 4: f_1T^perp = -(M/(2|k|)) Delta^N f, w = -(h . p_T)/M (M cancels)
    m = sp.Symbol("M", positive=True)
    kk = sp.sqrt(kx ** 2 + ky ** 2)
    delta_n = 2 * N * sqrt2e * kk / sp.sqrt(Mp2) * sp.exp(-kk ** 2 / Mp2) * f0 * gk
    f1t = -m / (2 * kk) * delta_n
    fut = int2(-(kx / m) * f1t * D0 * G(P - z * kx, -z * ky, pperp2))
    fuu = den_k
    ok411 = same(sp.simplify(fut / fuu), eq65_over_eq66)
    return {"phi_S_integral_is_pi_cos_phi_minus_phi_h": bool(ok_phis),
            "eq58_with_eq63_reproduces_eqs64_to_67": bool(ok64),
            "bacchetta_eq4_11_with_trento_eq4_gives_same_asymmetry": bool(ok411),
            "asymmetry": sp.sstr(clean(sp.simplify(eq65_over_eq66)))}


def drell_yan_checks() -> dict:
    shape = int2(G(kx, ky, k12) * G(qx - kx, qy - ky, k22))
    ok = same(shape, G(qx, qy, k12 + k22))
    norm = sp.simplify(int2(G(qx, qy, k12 + k22), qx, qy) - 1) == 0
    return {"two_gaussians_convolve_to_width_sum": bool(ok), "qT_shape_unit_normalized": bool(norm)}


def sivers_sign_checks() -> dict:
    """The Gaussian Sivers function (Eqs. 63, 68) and the SIDIS asymmetry are linear in it: flipping f_1T^perp flips
    every such quantity (Trento Eq. 14 applied, not derived)."""
    k = sp.Symbol("k", positive=True)
    delta_sidis = 2 * N * sp.sqrt(2 * sp.E) * k / sp.sqrt(Mp2) * sp.exp(-k ** 2 / Mp2) * f0 * sp.exp(-k ** 2 / kperp2) \
        / (sp.pi * kperp2)
    m = sp.Symbol("M", positive=True)
    f1t_sidis = -m / (2 * k) * delta_sidis  # Trento Eq. 4
    f1t_dy = -f1t_sidis  # Trento Eq. 14
    delta_dy = -(2 * k / m) * f1t_dy
    return {"dy_sivers_function_is_minus_sidis": sp.simplify(f1t_dy + f1t_sidis) == 0,
            "dy_delta_N_is_minus_sidis": sp.simplify(delta_dy + delta_sidis) == 0,
            "trento_eq4_round_trip": sp.simplify(-(2 * k / m) * f1t_sidis - delta_sidis) == 0}


def derive() -> dict:
    parts = {"normalization": normalizations(), "sidis": sidis_checks(), "cahn": cahn_checks(),
             "sivers": sivers_checks(), "drell_yan": drell_yan_checks(), "sivers_sign": sivers_sign_checks()}
    checks, results = {}, {}
    for name, d in parts.items():
        for k_, v in d.items():
            (checks if isinstance(v, bool) else results)[f"{name}:{k_}"] = v
    return {
        "label": f"theory:tmd-gaussian-lo Gaussian TMD convolutions, Cahn and Sivers terms (SymPy {sp.__version__})",
        "status": {"steps": "analytic-derivation within the Gaussian ansatz and O(k/Q) kinematics",
                   "physics": "heuristic-argument (the Gaussian ansatz with constant widths is a model)",
                   "sivers_sign_change": "cited (time reversal, Trento Eq. 14), applied here"},
        "order": "leading order in alpha_s, leading power in k/Q for F_UU,T and the Sivers term, O(k/Q) for the Cahn "
                 "cos(phi_h) term; no TMD evolution",
        "environment": {"python": platform.python_version(), "sympy": sp.__version__,
                        "interpreter": "from skills/hep-computing/scripts/find_python.py"},
        "assumptions": [
            "Gaussian k_perp and p_perp dependence with flavour-independent constant widths (Eqs. 34-35)",
            "p_perp = P_T - z k_perp at O(k/Q) (Eq. 29), x = x_B, z = z_h",
            "Sivers function Delta^N f = 2 N_q(x) h'(k) f(x, k), h' = sqrt(2e) (k/M') exp(-k^2/M'^2) (Eqs. 63, 68)",
            "one-photon exchange; massless partons; target mass and gamma = 2Mx/Q neglected",
            "Drell-Yan q_T shape: convolution of two Gaussian TMD PDFs, no soft factor, no evolution"],
        "results": {**results, "F_UU_T": "x sum e_q^2 f_q(x) D_q(z) exp(-P^2/<P_T^2>)/(pi <P_T^2>), "
                                         "<P_T^2> = <p^2> + z^2 <k^2>",
                    "dy_shape": "exp(-q_T^2/<q_T^2>)/(pi <q_T^2>), <q_T^2> = <k1^2> + <k2^2>"},
        "checks": checks,
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

#!/usr/bin/env python3
"""Derivations for theory:drell-yan-lo (SymPy, exact arithmetic).

 1. LO cross section (analytic derivation). From sigma(e+e- -> f fbar) = N_c Q_f^2 4 pi alpha^2 / (3 s) (PDG Eq. 51.3,
    dylo:C01), the colour-averaged partonic sigma(q qbar -> l+ l-) = e_q^2 4 pi alpha^2 / (3 N_c s_hat) (same spin- and
    colour-summed |M|^2 by time reversal; average over N_c^2 initial colours instead of summing N_c final ones). With
    the parton-model factorization of PDG Eq. 51.40 (dylo:C02), d sigma_hat / dM^2 = sigma_hat delta(s_hat - M^2),
    s_hat = x1 x2 s, tau = x1 x2, y = (1/2) ln(x1/x2) and dx1 dx2 = dtau dy (Jacobian 1):
      d^2 sigma / dM dy = (8 pi alpha^2 / (9 M s)) sum_q e_q^2 [q(x1) qbar(x2) + qbar(x1) q(x2)],
    x1,2 = (M / sqrt(s)) e^(+-y), N_c = 3.
 2. Angular structure (analytic derivation). Substituting cos theta0 = cos theta cos theta1 + sin theta sin theta1
    cos(phi - phi1) (Peng et al. Eq. 4, dylo:C04) into 1 + a cos theta0 + cos^2 theta0 (Eq. 2, dylo:C03) reproduces
    Eq. 5; matching Eq. 3 gives A_0..A_7 of Eq. 6 (per event; Peng et al. average them over the event sample);
    comparing Eq. 3 with Eq. 1 gives lambda = (2 - 3 A0)/(2 + A0), mu = 2 A1/(2 + A0), nu = 2 A2/(2 + A0) (Eq. 7), and
    1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0). With phi1 = 0 (quark axis in the hadron plane, which Peng et al. state
    holds at O(alpha_s) where a single parton is emitted, dylo:C06) A0 = A2, hence 1 - lambda - 2 nu = 0 (Lam-Tung).
    The Lam-Tung step is a perturbative argument at O(alpha_s): the coplanarity input is cited, not derived.
 3. O(alpha_s) channels (perturbative argument). Inserting <sin^2 theta1> = r^2/(1 + r^2) (q qbar -> gamma* g, Eq. 8)
    and 5 r^2/(1 + 5 r^2) (q g -> gamma* q, Eq. 9, an approximation per Peng et al.), r = q_T/Q, into Eq. 7 reproduces
    Eq. 10 for both channels; limits r -> 0 (lambda = 1, nu = 0) and r -> oo (lambda = -1/3).
 4. Channel mixture (analytic derivation). The A_i terms of Eq. 3 integrate to zero over the sphere and 1 + cos^2 theta
    to 16 pi/3, so a sum of channel distributions is Eq. 3 with A_i = sum_c (sigma_c/sigma) A_i^c (sigma_c
    angle-integrated); equivalently lambda_mix = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c).

Usage: python3 derive.py [--out ../derivations/derivation.json]
Exit 0 all checks pass, 1 a check fails, 2 SymPy is missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import platform
import sys

sys.dont_write_bytecode = True  # importing siblings or core leaves no __pycache__ (F-10)
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

alpha, s, s_hat, M, e_q, N_c = sp.symbols("alpha s s_hat M e_q N_c", positive=True)
x1, x2, tau = sp.symbols("x1 x2 tau", positive=True)
y = sp.Symbol("y", real=True)
th, ph, th1, ph1, a = sp.symbols("theta phi theta1 phi1 a", real=True)
A = sp.symbols("A0:8", real=True)
r = sp.Symbol("r", nonnegative=True)  # q_T / Q


# ---------------------------------------------------------------- 1. LO cross section
def lo_cross_section() -> dict:
    sigma_ee_ff = N_c * e_q ** 2 * 4 * sp.pi * alpha ** 2 / (3 * s_hat)  # PDG Eq. 51.3 (final colours summed)
    sigma_qq_ll = sigma_ee_ff / N_c ** 2  # time reversal: same summed |M|^2; 1/N_c^2 initial-colour average, no sum
    sig = sigma_qq_ll.subs(N_c, 3)
    # (x1, x2) -> (tau, y): x1 = sqrt(tau) e^y, x2 = sqrt(tau) e^-y
    x1_t, x2_t = sp.sqrt(tau) * sp.exp(y), sp.sqrt(tau) * sp.exp(-y)
    jac = sp.simplify(sp.Matrix([[sp.diff(x1_t, tau), sp.diff(x1_t, y)], [sp.diff(x2_t, tau), sp.diff(x2_t, y)]]).det())
    inverse_ok = sp.simplify(x1_t * x2_t - tau) == 0 and sp.simplify(sp.log(x1_t / x2_t) / 2 - y) == 0
    # integrate the delta function over tau; L(tau, y) stands for the parton luminosity q(x1) qbar(x2) + qbar(x1) q(x2)
    lum = sp.Function("L")
    d_sigma_dM2_dy = sp.integrate(lum(tau, y) * sig.subs(s_hat, tau * s) * sp.DiracDelta(tau * s - M ** 2) * abs(jac),
                                  (tau, 0, 1))
    d_sigma_dM2_dy = d_sigma_dM2_dy.subs(sp.Heaviside(1 - M ** 2 / s), 1)  # M^2 < s: kinematically allowed
    d_sigma_dM_dy = sp.simplify(2 * M * d_sigma_dM2_dy)  # dM^2 = 2 M dM
    target = 8 * sp.pi * alpha ** 2 / (9 * M * s) * e_q ** 2 * lum(M ** 2 / s, y)
    nb_form = sp.Rational(2, 3)  # 8 pi alpha^2 / 9 = (2/3) (4 pi alpha^2 / 3); PDG Eq. 51.3 gives 4 pi alpha^2/3 = 86.8 nb GeV^2
    return {"sigma_hat_qqbar_to_ll": sp.sstr(sig), "jacobian": sp.sstr(jac),
            "d2sigma_dM_dy": sp.sstr(d_sigma_dM_dy),
            "checks": {"colour_average_gives_one_ninth_of_e_q2_4pi_alpha2_over_3s":
                       sp.simplify(sig - e_q ** 2 * 4 * sp.pi * alpha ** 2 / (9 * s_hat)) == 0,
                       "jacobian_dx1dx2_equals_dtau_dy": sp.simplify(abs(jac) - 1) == 0,
                       "tau_y_map_inverts": bool(inverse_ok),
                       "d2sigma_dM_dy_matches_8_pi_alpha2_over_9Ms": sp.simplify(d_sigma_dM_dy - target) == 0,
                       "nb_factor_8pi_alpha2_over_9_is_two_thirds_of_4pi_alpha2_over_3":
                       sp.simplify(8 * sp.pi * alpha ** 2 / 9 - nb_form * 4 * sp.pi * alpha ** 2 / 3) == 0}}


# ---------------------------------------------------------------- 2. angular structure
def eq2_with_eq4():
    cos_th0 = sp.cos(th) * sp.cos(th1) + sp.sin(th) * sp.sin(th1) * sp.cos(ph - ph1)  # Peng Eq. 4
    return 1 + a * cos_th0 + cos_th0 ** 2  # Peng Eq. 2


def eq5():
    return ((1 + sp.cos(th) ** 2) + sp.sin(th1) ** 2 / 2 * (1 - 3 * sp.cos(th) ** 2)
            + (sp.sin(2 * th1) * sp.cos(ph1) / 2) * sp.sin(2 * th) * sp.cos(ph)
            + (sp.sin(th1) ** 2 * sp.cos(2 * ph1) / 2) * sp.sin(th) ** 2 * sp.cos(2 * ph)
            + (a * sp.sin(th1) * sp.cos(ph1)) * sp.sin(th) * sp.cos(ph) + (a * sp.cos(th1)) * sp.cos(th)
            + (sp.sin(th1) ** 2 * sp.sin(2 * ph1) / 2) * sp.sin(th) ** 2 * sp.sin(2 * ph)
            + (sp.sin(2 * th1) * sp.sin(ph1) / 2) * sp.sin(2 * th) * sp.sin(ph)
            + (a * sp.sin(th1) * sp.sin(ph1)) * sp.sin(th) * sp.sin(ph))


def eq3(coeffs=A):
    A0, A1, A2, A3, A4, A5, A6, A7 = coeffs
    return ((1 + sp.cos(th) ** 2) + A0 / 2 * (1 - 3 * sp.cos(th) ** 2) + A1 * sp.sin(2 * th) * sp.cos(ph)
            + A2 / 2 * sp.sin(th) ** 2 * sp.cos(2 * ph) + A3 * sp.sin(th) * sp.cos(ph) + A4 * sp.cos(th)
            + A5 * sp.sin(th) ** 2 * sp.sin(2 * ph) + A6 * sp.sin(2 * th) * sp.sin(ph) + A7 * sp.sin(th) * sp.sin(ph))


def eq6():
    """A_0..A_7 per event (Peng Eq. 6 without the event-sample average)."""
    return [sp.sin(th1) ** 2, sp.sin(2 * th1) * sp.cos(ph1) / 2, sp.sin(th1) ** 2 * sp.cos(2 * ph1),
            a * sp.sin(th1) * sp.cos(ph1), a * sp.cos(th1), sp.sin(th1) ** 2 * sp.sin(2 * ph1) / 2,
            sp.sin(2 * th1) * sp.sin(ph1) / 2, a * sp.sin(th1) * sp.sin(ph1)]


ANGLES = (th, ph, th1, ph1)
COS = sp.symbols("c0:4", real=True)
SIN = sp.symbols("s0:4", real=True)


def _reduce(expr):
    """Polynomial normal form in the cosines and sines of theta, phi, theta1, phi1, modulo sin^2 + cos^2 = 1 for each
    angle (canonical: zero iff the trigonometric expression vanishes identically)."""
    e = sp.expand(sp.expand_trig(expr))
    e = e.subs({f(ang): v for ang, c_, s_ in zip(ANGLES, COS, SIN) for f, v in ((sp.cos, c_), (sp.sin, s_))})
    _, rem = sp.reduced(sp.expand(e), [s_ ** 2 + c_ ** 2 - 1 for c_, s_ in zip(COS, SIN)], *SIN, *COS)
    return rem


def _normal_form(expr):
    """_reduce as a polynomial in the lepton-angle functions; its coefficients carry the quark-axis angles."""
    return sp.Poly(_reduce(expr), *SIN[:2], *COS[:2])


def _to_trig(expr):
    return expr.subs({v: f(ang) for ang, c_, s_ in zip(ANGLES, COS, SIN) for f, v in ((sp.cos, c_), (sp.sin, s_))})


def angular_structure() -> dict:
    eq5_ok = _normal_form(eq2_with_eq4() - eq5()).is_zero
    # read A_0..A_7 off by matching Eq. 3 to Eq. 5 coefficient by coefficient (the angular functions are independent)
    diff = _normal_form(eq3() - eq5())
    sol = sp.solve(diff.coeffs(), A, dict=True)
    read_off = sol[0] if len(sol) == 1 and set(sol[0]) == set(A) else {}
    eq6_ok = bool(read_off) and all(_reduce(read_off[Ai] - v) == 0 for Ai, v in zip(A, eq6()))
    # Eq. 3 against Eq. 1: dsigma/dOmega propto 1 + lambda cos^2 + mu sin2 cos + (nu/2) sin^2 cos 2phi
    lam, mu, nu, k = sp.symbols("lambda mu nu k")
    A0, A1, A2 = A[:3]
    eq3_even = eq3((A0, A1, A2, 0, 0, 0, 0, 0))
    eq1 = 1 + lam * sp.cos(th) ** 2 + mu * sp.sin(2 * th) * sp.cos(ph) + nu / 2 * sp.sin(th) ** 2 * sp.cos(2 * ph)
    sol1 = sp.solve(_normal_form(eq3_even - k * eq1).coeffs(), [lam, mu, nu, k], dict=True)
    s1 = sol1[0] if len(sol1) == 1 else {}
    lam_e, mu_e, nu_e = (2 - 3 * A0) / (2 + A0), 2 * A1 / (2 + A0), 2 * A2 / (2 + A0)
    eq7_ok = bool(s1) and all(sp.simplify(s1[v] - w) == 0 for v, w in ((lam, lam_e), (mu, mu_e), (nu, nu_e)))
    lt = sp.simplify(1 - lam_e - 2 * nu_e)
    lt_ok = sp.simplify(lt - 4 * (A0 - A2) / (2 + A0)) == 0
    a6 = eq6()
    coplanar_A0_eq_A2 = sp.simplify((a6[0] - a6[2]).subs(ph1, 0)) == 0
    lam_tung_coplanar = sp.simplify(lt.subs({A0: a6[0], A2: a6[2]}).subs(ph1, 0)) == 0
    # A0 - A2 = sin^2 theta1 (1 - cos 2 phi1) >= 0: 1 - lambda - 2 nu >= 0 for any phi1 (Peng remark b)
    nonneg = sp.simplify(a6[0] - a6[2] - 2 * sp.sin(th1) ** 2 * sp.sin(ph1) ** 2) == 0
    # the parity-violating parameter a drops out of A0, A1, A2, A5, A6 (remark c)
    a_free = all(not v.has(a) for i, v in enumerate(a6) if i in (0, 1, 2, 5, 6))
    return {"read_off_A": {str(k_): sp.sstr(sp.simplify(_to_trig(v))) for k_, v in read_off.items()},
            "lambda_mu_nu": {"lambda": sp.sstr(lam_e), "mu": sp.sstr(mu_e), "nu": sp.sstr(nu_e)},
            "one_minus_lambda_minus_2nu": sp.sstr(lt),
            "checks": {"eq4_into_eq2_reproduces_eq5": bool(eq5_ok), "eq3_vs_eq5_gives_eq6": bool(eq6_ok),
                       "eq3_vs_eq1_gives_eq7": bool(eq7_ok), "lam_tung_violation_is_4_A0_minus_A2_over_2_plus_A0":
                       bool(lt_ok), "phi1_zero_gives_A0_equals_A2": bool(coplanar_A0_eq_A2),
                       "lam_tung_holds_for_coplanar_quark_axis": bool(lam_tung_coplanar),
                       "A0_minus_A2_is_2_sin2theta1_sin2phi1_nonnegative": bool(nonneg),
                       "parity_parameter_a_absent_from_A0_A1_A2_A5_A6": bool(a_free)}}


# ---------------------------------------------------------------- 3. O(alpha_s) channels
SIN2_THETA1 = {"qqbar": r ** 2 / (1 + r ** 2),  # Peng Eq. 8 (exact at O(alpha_s), Collins-Soper frame)
               "qg": 5 * r ** 2 / (1 + 5 * r ** 2)}  # Peng Eq. 9 (approximation)
PENG_EQ10 = {"qqbar": ((2 - r ** 2) / (2 + 3 * r ** 2), 2 * r ** 2 / (2 + 3 * r ** 2)),
             "qg": ((2 - 5 * r ** 2) / (2 + 15 * r ** 2), 10 * r ** 2 / (2 + 15 * r ** 2))}  # Q = 1 units of Eq. 10


def channels() -> dict:
    out, checks = {}, {}
    for ch, a0 in SIN2_THETA1.items():
        lam_c = sp.simplify((2 - 3 * a0) / (2 + a0))
        nu_c = sp.simplify(2 * a0 / (2 + a0))  # A2 = A0 at phi1 = 0
        lam_p, nu_p = PENG_EQ10[ch]
        checks[f"{ch}_lambda_matches_peng_eq10"] = sp.simplify(lam_c - lam_p) == 0
        checks[f"{ch}_nu_matches_peng_eq10"] = sp.simplify(nu_c - nu_p) == 0
        checks[f"{ch}_lam_tung_zero"] = sp.simplify(1 - lam_c - 2 * nu_c) == 0
        checks[f"{ch}_limit_qT_to_0_lambda_1_nu_0"] = lam_c.subs(r, 0) == 1 and nu_c.subs(r, 0) == 0
        checks[f"{ch}_limit_qT_to_oo_lambda_minus_one_third"] = sp.limit(lam_c, r, sp.oo) == sp.Rational(-1, 3)
        out[ch] = {"sin2_theta1": sp.sstr(a0), "lambda": sp.sstr(lam_c), "nu": sp.sstr(nu_c),
                   "nu_limit_qT_to_oo": sp.sstr(sp.limit(nu_c, r, sp.oo))}
    return {"channels": out, "checks": checks}


# ---------------------------------------------------------------- 4. channel mixture
def _sphere(expr):
    return sp.integrate(sp.integrate(expr * sp.sin(th), (th, 0, sp.pi)), (ph, 0, 2 * sp.pi))


def channel_mixture() -> dict:
    """Mixing channels is an exact cross-section-weighted average of the A_i (analytic derivation):
    each A_i term of Eq. 3 integrates to zero over the sphere and (1 + cos^2 theta) to 16 pi/3, so
    d sigma_c/d Omega = sigma_c (3/(16 pi)) Eq3(A^c) with sigma_c the angle-integrated cross section of channel c, and
    sum_c d sigma_c/d Omega = sigma (3/(16 pi)) Eq3(sum_c (sigma_c/sigma) A^c). In lambda, nu: 2 + A0 = 8/(3 + lambda),
    so lambda_mix = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c), and nu likewise."""
    zero = [eq3(tuple(1 if j == i else 0 for j in range(8))) - eq3((0,) * 8) for i in range(8)]
    a_terms_zero = all(sp.simplify(_sphere(z)) == 0 for z in zero)
    unpol = sp.simplify(_sphere(1 + sp.cos(th) ** 2) - sp.Rational(16, 3) * sp.pi) == 0
    sa, sb = sp.symbols("sigma_a sigma_b", positive=True)
    Aa, Ab = sp.symbols("Aa0:8", real=True), sp.symbols("Ab0:8", real=True)
    dist = lambda sig, coeffs: sig * 3 / (16 * sp.pi) * eq3(coeffs)  # noqa: E731
    normalized = all(sp.simplify(_sphere(dist(sg, c)) - sg) == 0 for sg, c in ((sa, Aa), (sb, Ab)))
    amix = tuple((sa * x + sb * y_) / (sa + sb) for x, y_ in zip(Aa, Ab))
    weighted = sp.simplify(sp.expand(dist(sa, Aa) + dist(sb, Ab) - dist(sa + sb, amix))) == 0
    f = sp.Symbol("f", nonnegative=True)
    lam_c = [(2 - 3 * a[0]) / (2 + a[0]) for a in (Aa, Ab)]
    nu_c = [2 * a[2] / (2 + a[0]) for a in (Aa, Ab)]
    fs = (1 - f, f)
    a0m, a2m = fs[0] * Aa[0] + fs[1] * Ab[0], fs[0] * Aa[2] + fs[1] * Ab[2]
    w = sum(fc / (3 + lc) for fc, lc in zip(fs, lam_c))
    lam_form = sum(fc * lc / (3 + lc) for fc, lc in zip(fs, lam_c)) / w
    nu_form = sum(fc * nc / (3 + lc) for fc, lc, nc in zip(fs, lam_c, nu_c)) / w
    lam_ok = sp.simplify((2 - 3 * a0m) / (2 + a0m) - lam_form) == 0 and sp.simplify(2 * a2m / (2 + a0m) - nu_form) == 0
    linear_differs = sp.simplify((2 - 3 * a0m) / (2 + a0m) - sum(fc * lc for fc, lc in zip(fs, lam_c))) != 0
    return {"checks": {"A_terms_integrate_to_zero": bool(a_terms_zero),
                       "unpolarized_term_integrates_to_16pi_over_3": bool(unpol),
                       "distribution_normalized_to_sigma_c": bool(normalized),
                       "sigma_weighted_sum_equals_A_average": bool(weighted),
                       "lambda_form_with_3_plus_lambda_weights": bool(lam_ok),
                       "linear_lambda_average_differs": bool(linear_differs)},
            "results": {"A_mix": "A_i = sum_c (sigma_c/sigma) A_i^c, sigma_c angle-integrated in the same (qT, Q) bin",
                        "lambda_mix": "sum_c f_c lambda_c/(3 + lambda_c) / sum_c f_c/(3 + lambda_c)",
                        "nu_mix": "sum_c f_c nu_c/(3 + lambda_c) / sum_c f_c/(3 + lambda_c)"}}


def derive() -> dict:
    lo, ang, chs, mix = lo_cross_section(), angular_structure(), channels(), channel_mixture()
    checks = {**{f"lo:{k}": v for k, v in lo["checks"].items()}, **{f"angular:{k}": v for k, v in ang["checks"].items()},
              **{f"alpha_s:{k}": v for k, v in chs["checks"].items()},
              **{f"mixture:{k}": v for k, v in mix["checks"].items()}}
    return {
        "label": f"theory:drell-yan-lo LO cross section, angular coefficients and Lam-Tung at O(alpha_s) (SymPy "
                 f"{sp.__version__})",
        "status": {"lo_cross_section": "analytic-derivation", "angular_structure_eqs_5_to_7": "analytic-derivation",
                   "lam_tung_and_eq10": "perturbative-argument", "channel_mixture": "analytic-derivation"},
        "order": "cross section at O(alpha^2 alpha_s^0); lambda, nu at O(alpha_s) (single emission, phi1 = 0 cited)",
        "environment": {"python": platform.python_version(), "sympy": sp.__version__,
                        "interpreter": "from skills/hep-computing/scripts/find_python.py"},
        "assumptions": [
            "photon exchange only (a = 0 in Peng Eq. 2 for the numbers; a kept symbolic in the algebra)",
            "massless quarks and leptons; unpolarized hadrons; N_c = 3; LO parton model (PDG Eq. 51.40)",
            "time reversal: q qbar -> l+ l- and l+ l- -> q qbar share the spin- and colour-summed |M|^2",
            "phi1 = 0 at O(alpha_s): cited from Peng et al., not derived here",
            "<sin^2 theta1> of the q g channel (Peng Eq. 9) is an approximation per Peng et al.; Eq. 8 exact",
            "no intrinsic transverse momentum; no resummation; channels mixed by angle-integrated cross-section fraction"],
        "results": {"lo": {k: v for k, v in lo.items() if k != "checks"},
                    "angular": {k: v for k, v in ang.items() if k != "checks"},
                    "alpha_s_channels": chs["channels"], "channel_mixture": mix["results"]},
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

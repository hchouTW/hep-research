#!/usr/bin/env python3
"""Derivation for theory:higgs-bb-width: scale dependence of Gamma(H -> b bbar) with the MS-bar running mass.

Gamma = 3 G_F M_H / (4 sqrt(2) pi) mbar_b(mu)^2 R(a(mu), L), a = alpha_s / pi, L = ln(mu^2 / M_H^2), massless b at
leading power (m_b^2 / M_H^2 terms neglected). At mu = M_H, R = 1 + s_1 a + s_2 a^2 + s_3 a^3 + s_4 a^4 with s_1..s_3
exact for general n_f (Chetyrkin, hep-ph/9608318, eq. (21), hbb:C02) and s_4 = -825.7 at n_f = 5 only (Baikov,
Chetyrkin, Kuhn, hep-ph/0511063, Table I, hbb:C03; kept as a symbol s_4 in the general derivation). The mass runs with
mu^2 d m / d mu^2 = -m sum_i gamma_i a^(i+1) (Chetyrkin, hep-ph/9703278, eqs. (1), (7)-(9), hbb:C04) and the coupling
with d a / d ln mu^2 = -sum_i B_i a^(i+2), B_i = beta_i / 4^(i+1) from van Ritbergen, Vermaseren, Larin,
hep-ph/9701390, eq. (11) (hbb:C05). a(M_H) and mbar(M_H) are expanded in a(mu) by Picard iteration; the result is
R = sum_n r_n(L) a(mu)^n with r_n(0) = s_n.

The scale-dependent r_n are derived at n_f = 5 (the profile's domain); the s_n and the normalizations are checked for
general n_f. Checks: r_n(0) = s_n; the mu dependence of m(mu)^2 times the truncated series is of higher order than the truncation,
N = 1..4 (exact arithmetic, zeta values symbolic), and a wrong sign of gamma_0 breaks it; r_1 = s_1 + 2 gamma_0 L; the n_f = 5 numbers of s_1..s_3 against
hep-ph/0511063 eq. (3) and the n_f forms against hep-ph/9608318 eq. (22); the anomalous-dimension normalization
against the PDG Quark Masses review eq. (60.3) and the beta coefficients against PDG QCD eq. (9.3) (hbb:C04, C05).
Status: perturbative argument at fixed order (N4LO in R), SymPy algebra; not a formal proof.

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
a, L, nf, s4 = sp.symbols("a L n_f s_4")
Q = sp.Rational
# zeta(3), zeta(5) and pi^2 are kept as independent symbols (zeta(4) = pi^4/90): every identity checked below is then a
# polynomial identity with rational coefficients, exact and fast; NUMERIC substitutes their values for the n_f checks.
Z3, Z5, PI2 = sp.symbols("zeta3 zeta5 pi2")
Z4 = PI2 ** 2 / 90
NUMERIC = {Z3: sp.zeta(3), Z5: sp.zeta(5), PI2: sp.pi ** 2}
ORDER = 4


def s_coefficients(nf_=nf, s4_=s4):
    """s_1..s_4 of R at mu^2 = s = M_H^2 (hep-ph/9608318 eq. (21) divided by 3; s_4 from hep-ph/0511063 Table I)."""
    s1 = Q(17, 3)
    s2 = Q(10801, 144) - Q(19, 12) * PI2 - Q(39, 2) * Z3 + nf_ * (-Q(65, 24) + Q(1, 18) * PI2 + Q(2, 3) * Z3)
    s3 = (Q(6163613, 5184) - Q(3535, 72) * PI2 - Q(109735, 216) * Z3 + Q(815, 12) * Z5
          + nf_ * (-Q(46147, 486) + Q(277, 72) * PI2 + Q(262, 9) * Z3 - Q(5, 6) * Z4 - Q(25, 9) * Z5)
          + nf_ ** 2 * (Q(15511, 11664) - Q(11, 162) * PI2 - Q(1, 3) * Z3))
    return [s1, s2, s3, s4_]


def gammas(nf_=nf):
    """gamma_0..gamma_3 of the mass anomalous dimension for a = alpha_s / pi (hep-ph/9703278 eqs. (7)-(9))."""
    return [sp.Integer(1),
            (Q(202, 3) - Q(20, 9) * nf_) / 16,
            (1249 + nf_ * (-Q(2216, 27) - Q(160, 3) * Z3) - Q(140, 81) * nf_ ** 2) / 64,
            (Q(4603055, 162) + Q(135680, 27) * Z3 - 8800 * Z5
             + nf_ * (-Q(91723, 27) - Q(34192, 9) * Z3 + 880 * Z4 + Q(18400, 9) * Z5)
             + nf_ ** 2 * (Q(5242, 243) + Q(800, 9) * Z3 - Q(160, 3) * Z4)
             + nf_ ** 3 * (-Q(332, 243) + Q(64, 27) * Z3)) / 256]


def betas_4pi(nf_=nf):
    """beta_0..beta_3 for a_s = alpha_s / (4 pi) (hep-ph/9701390 eq. (11))."""
    return [11 - Q(2, 3) * nf_, 102 - Q(38, 3) * nf_, Q(2857, 2) - Q(5033, 18) * nf_ + Q(325, 54) * nf_ ** 2,
            Q(149753, 6) + 3564 * Z3 - (Q(1078361, 162) + Q(6508, 27) * Z3) * nf_
            + (Q(50065, 162) + Q(6472, 81) * Z3) * nf_ ** 2 + Q(1093, 729) * nf_ ** 3]


def betas(nf_=nf):
    """B_i for a = alpha_s / pi: d a / d ln mu^2 = -sum_i B_i a^(i+2), B_i = beta_i / 4^(i+1)."""
    return [b / 4 ** (i + 1) for i, b in enumerate(betas_4pi(nf_))]


def _trunc(expr, order=ORDER):
    """The polynomial part of expr in a through a^order (expr is a polynomial in a)."""
    e = sp.expand(expr)
    return sp.Add(*[e.coeff(a, k) * a ** k for k in range(order + 1)])


def running_to_mh(bs, gs, order=ORDER):
    """a(M_H) and mbar(M_H)/mbar(mu) as series in a = a(mu) through a^order (t = ln(scale^2/mu^2) from 0 to -L)."""
    t = sp.symbols("t")
    series = a
    for _ in range(order):
        rhs = -sum(b * series ** (i + 2) for i, b in enumerate(bs))
        series = _trunc(a + sp.integrate(_trunc(rhs, order), (t, 0, t)), order)
    gamma_t = _trunc(sum(g * series ** (i + 1) for i, g in enumerate(gs)), order)
    log_ratio = -sp.integrate(gamma_t, (t, 0, t))  # ln(mbar(scale) / mbar(mu))
    x = _trunc(log_ratio, order)  # x = O(a), so exp(x) = sum_k x^k / k! through k = order
    mass_ratio, term = sp.Integer(1), sp.Integer(1)
    for k in range(1, order + 1):
        term = _trunc(term * x / k, order)
        mass_ratio += term
    return sp.expand(series.subs(t, -L)), sp.expand(mass_ratio.subs(t, -L))


def scale_dependent_coefficients(nf_=nf, s4_=s4, order=ORDER, bs=None, gs=None):
    """r_0..r_order with Gamma proportional to mbar(mu)^2 sum_n r_n(L) a(mu)^n."""
    bs = betas(nf_) if bs is None else bs
    gs = gammas(nf_) if gs is None else gs
    a_mh, m_ratio = running_to_mh(bs, gs, order)
    s = [sp.Integer(1)] + s_coefficients(nf_, s4_)
    r_mh = sum(c * a_mh ** n for n, c in enumerate(s[:order + 1]))
    total = _trunc(m_ratio ** 2 * r_mh, order)
    return [sp.expand(total.coeff(a, n)) for n in range(order + 1)]


def mu_independent(r, bs, gs, order=ORDER) -> bool:
    """d/dL [m^2 sum_(n<=N) r_n a^n] / m^2 = sum (dr_n/dL a^n) + (-2 gamma(a)) sum r_n a^n + beta(a) d/da (...),
    with da/dL = -sum B_i a^(i+2); it must vanish through a^N for each truncation N = 1..order."""
    beta_a = -sum(b * a ** (i + 2) for i, b in enumerate(bs))
    gamma_a = sum(g * a ** (i + 1) for i, g in enumerate(gs))
    for n_trunc in range(1, order + 1):
        series = sum(r[k] * a ** k for k in range(n_trunc + 1))
        total = sp.diff(series, L) - 2 * gamma_a * series + beta_a * sp.diff(series, a)
        if sp.expand(_trunc(total, n_trunc)) != 0:
            return False
    return True


NF = 5  # the profile's flavour number; the s_n and the normalization checks below are also done for general n_f


def derive() -> dict:
    bs, gs = betas(NF), gammas(NF)
    r = scale_dependent_coefficients(NF)
    s = [sp.Integer(1)] + s_coefficients(NF)
    checks = {"r_n_at_L0_equal_s_n": all(sp.expand(rn.subs(L, 0) - sn) == 0 for rn, sn in zip(r, s))}
    checks["truncated_series_mu_independent_to_its_order"] = mu_independent(r, bs, gs)
    checks["r1_equals_s1_plus_2_gamma0_L"] = sp.expand(r[1] - (s[1] + 2 * gs[0] * L)) == 0
    checks["wrong_gamma0_sign_breaks_mu_independence"] = not mu_independent(r, bs, [-gs[0]] + gs[1:])
    five = {nf: 5}
    num = [float(x.subs(five).subs(NUMERIC)) for x in s_coefficients(5, Q(-8257, 10))]
    # hep-ph/0511063 eq. (3): R = 1 + 5.66667 a + 29.1467 a^2 + 41.7576 a^3 (n_f = 5)
    checks["nf5_s1_s2_s3_match_hep_ph_0511063_eq3"] = (abs(num[0] - 5.66667) < 5e-6 and abs(num[1] - 29.1467) < 5e-5
                                                       and abs(num[2] - 41.7576) < 5e-5)
    # hep-ph/9608318 eq. (22): (35.93996 - 1.35865 n_f) a^2 + (164.13921 - 25.77119 n_f + 0.258974 n_f^2) a^3
    s2p, s3p = (sp.Poly(sp.expand(x), nf) for x in s_coefficients()[1:3])
    c2, c3 = ([float(sp.sympify(c).subs(NUMERIC)) for c in reversed(p.all_coeffs())] for p in (s2p, s3p))
    checks["nf_forms_match_hep_ph_9608318_eq22"] = (abs(c2[0] - 35.93996) < 5e-6 and abs(c2[1] + 1.35865) < 5e-5
                                                   and abs(c3[0] - 164.13921) < 5e-6 and abs(c3[1] + 25.77119) < 5e-6
                                                   and abs(c3[2] - 0.258974) < 5e-7)
    # PDG Quark Masses eq. (60.3): gamma_r(PDG, alpha_s/(4 pi), r >= 1) = 4^r gamma_(r-1)(alpha_s/pi)
    pdg_gamma = [sp.Integer(4), Q(202, 3) - Q(20, 9) * nf,
                 1249 + (-Q(2216, 27) - Q(160, 3) * Z3) * nf - Q(140, 81) * nf ** 2]
    checks["gamma_normalization_matches_pdg_eq_60_3"] = all(
        sp.expand(pg - 4 ** (k + 1) * gammas()[k]) == 0 for k, pg in enumerate(pdg_gamma))
    # PDG QCD eq. (9.3): b_k alpha_s^(k+2) expansion; B_k = pi^(k+1) b_k
    pdg_b = [(33 - 2 * nf) / (12 * sp.pi), (153 - 19 * nf) / (24 * sp.pi ** 2),
             (2857 - Q(5033, 9) * nf + Q(325, 27) * nf ** 2) / (128 * sp.pi ** 3)]
    checks["beta_normalization_matches_pdg_eq_9_3"] = all(
        sp.simplify(sp.pi ** (k + 1) * pb - betas()[k]) == 0 for k, pb in enumerate(pdg_b))
    return {
        "label": f"theory:higgs-bb-width scale-dependent coefficients (SymPy {sp.__version__})",
        "status": "perturbative-argument",
        "order": "R through a^4 (alpha_s^4) with a = alpha_s/pi, MS-bar mass and coupling, massless b at leading power",
        "assumptions": ["a = alpha_s/pi and mbar_b(mu) in the MS-bar scheme with n_f = 5 active flavours (top decoupled)",
                        "Gamma = 3 G_F M_H / (4 sqrt 2 pi) mbar_b(mu)^2 R; m_b^2/M_H^2 power corrections neglected",
                        "s_1..s_3 exact (hep-ph/9608318 eq. 21), s_4 = -825.7 at n_f = 5 only (hep-ph/0511063 Table I)",
                        "no electroweak corrections and no top-induced (singlet) terms; n_f fixed between m_b and 2 M_H"],
        "results": {"r_n(L), L = ln(mu^2/M_H^2), n_f = 5, s_4 symbolic": [sp.sstr(x) for x in r],
                    "s_n(n_f = 5), s_4 = -825.7": num},
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

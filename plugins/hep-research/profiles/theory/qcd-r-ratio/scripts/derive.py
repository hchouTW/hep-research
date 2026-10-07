#!/usr/bin/env python3
"""Derivation for theory:qcd-r-ratio: the massless QCD correction to R(e+e- -> hadrons) at a renormalization scale
mu different from Q, from the coefficients c_1..c_4 at mu = Q (PDG eqs. 9.8-9.9, qcdr:C02) and the renormalization
group equation (PDG eq. 9.3, qcdr:C03).

With a = alpha_s / pi and L = ln(mu^2 / Q^2): delta_QCD(Q) = sum_n c_n a(Q)^n. a(Q) is expanded in a(mu) by solving
d a / d ln mu^2 = -(beta0 a^2 + beta1 a^3 + beta2 a^4) order by order, with beta_k = pi^(k+1) b_k. The result is
delta_QCD = sum_n d_n(L) a(mu)^n with d_n(0) = c_n. Checks: d_n(0) = c_n; the mu dependence of the truncated series
is of higher order than the truncation (symbolic); the nf = 5 numbers of c_2, c_3, c_4. Status: perturbative
argument at fixed order (N3LO in delta_QCD), SymPy algebra; not a formal proof.

Usage: python3 derive.py [--out ../derivations/derivation.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
a, L, nf, eta = sp.symbols("a L n_f eta")
R = sp.Rational  # decimal strings of the reference, kept exact so cancellations are exact
ORDER = 4  # c_1 .. c_4


def coefficients(nf_=nf, eta_=eta):
    """c_1..c_4 of PDG eq. (9.9) in the MS-bar scheme at mu_R = Q (qcdr:C02)."""
    return [sp.Integer(1),
            R("1.9857") - R("0.1152") * nf_,
            R("-6.63694") - R("1.20013") * nf_ - R("0.00518") * nf_ ** 2 - R("1.240") * eta_,
            (R("-156.61") + R("18.775") * nf_ - R("0.7974") * nf_ ** 2 + R("0.0215") * nf_ ** 3
             - (R("17.828") - R("0.575") * nf_) * eta_)]


def betas(nf_=nf):
    """beta_k = pi^(k+1) b_k for a = alpha_s/pi, from b_0, b_1, b_2 of PDG eq. (9.3) (qcdr:C03)."""
    return [(33 - 2 * nf_) / sp.Integer(12), (153 - 19 * nf_) / sp.Integer(24),
            (2857 - sp.Rational(5033, 9) * nf_ + sp.Rational(325, 27) * nf_ ** 2) / sp.Integer(128)]


def a_of_q_in_a_of_mu(nf_=nf, order=ORDER):
    """a(Q) as a power series in a = a(mu) through a^order, from integrating the RGE from mu to Q (ln Q^2/mu^2 = -L)."""
    b0, b1, b2 = betas(nf_)
    t = sp.symbols("t")  # t runs from 0 (scale mu) to -L (scale Q) in ln(scale^2/mu^2)
    # Picard iteration of da/dt = -(b0 a^2 + b1 a^3 + b2 a^4), truncated at a^(order)
    series = a
    for _ in range(order):
        rhs = -(b0 * series ** 2 + b1 * series ** 3 + b2 * series ** 4)
        rhs = sp.series(sp.expand(rhs), a, 0, order + 1).removeO()
        series = a + sp.integrate(rhs, (t, 0, t))
        series = sp.series(sp.expand(series), a, 0, order + 1).removeO()
    return sp.expand(series.subs(t, -L))


def scale_dependent_coefficients(nf_=nf, eta_=eta, order=ORDER):
    aq = a_of_q_in_a_of_mu(nf_, order)
    delta = sum(c * aq ** (n + 1) for n, c in enumerate(coefficients(nf_, eta_)))
    delta = sp.series(sp.expand(delta), a, 0, order + 1).removeO()
    return [sp.expand(delta.coeff(a, n)) for n in range(1, order + 1)]


def mu_independent(d, bs, order=ORDER) -> bool:
    """d/dL of each truncated series, with da/dL = -(b0 a^2 + b1 a^3 + b2 a^4), vanishes through its own order."""
    b0, b1, b2 = bs
    for n_trunc in range(1, order + 1):
        series = sum(d[k] * a ** (k + 1) for k in range(n_trunc))
        total = sp.diff(series, L) + sp.diff(series, a) * (-(b0 * a ** 2 + b1 * a ** 3 + b2 * a ** 4))
        if sp.expand(sp.series(sp.expand(total), a, 0, n_trunc + 1).removeO()) != 0:
            return False
    return True


def derive() -> dict:
    d = scale_dependent_coefficients()
    c = coefficients()
    b0, b1, b2 = betas()
    checks = {"d_n_at_L0_equal_c_n": all(sp.simplify(dn.subs(L, 0) - cn) == 0 for dn, cn in zip(d, c))}
    checks["truncated_series_mu_independent_to_its_order"] = mu_independent(d, (b0, b1, b2))
    # expected structure of the first log terms (textbook RGE consequence)
    checks["d2_equals_c2_plus_beta0_L"] = sp.simplify(d[1] - (c[1] + b0 * L)) == 0
    five = {nf: 5, eta: sp.Rational(1, 33)}
    num = [float(x.subs(five)) for x in c]
    checks["nf5_c2_is_1_409"] = abs(num[1] - 1.4097) < 5e-4
    checks["nf5_c3_nonsinglet_is_minus_12_77"] = abs(float(c[2].subs({nf: 5, eta: 0})) + 12.767) < 1e-3
    checks["nf5_c4_nonsinglet_is_minus_79_98"] = abs(float(c[3].subs({nf: 5, eta: 0})) + 79.98) < 0.01
    return {
        "label": f"theory:qcd-r-ratio scale-dependent coefficients (SymPy {sp.__version__})",
        "status": "perturbative-argument",
        "order": "delta_QCD through a^4 (alpha_s^4), MS-bar, massless quarks, photon exchange only",
        "assumptions": ["a = alpha_s/pi in the MS-bar scheme with n_f active massless flavours",
                        "R(Q) = R_EW (1 + delta_QCD(Q)), R_EW = N_c sum e_q^2 (photon exchange only)",
                        "c_1..c_4 at mu_R = Q from PDG eq. (9.9); beta function through b_2 (PDG eq. 9.3)",
                        "no quark-mass, Z-exchange or QED corrections; n_f fixed (no threshold crossed)"],
        "results": {"d_n(L), L = ln(mu^2/Q^2)": [sp.sstr(x) for x in d],
                    "c_n(n_f = 5, eta = 1/33)": num},
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

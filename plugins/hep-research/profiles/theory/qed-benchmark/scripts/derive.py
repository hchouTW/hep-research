#!/usr/bin/env python3
"""Tree-level e+e- -> mu+mu- via one s-channel photon: symbolic derivation with SymPy (theory:qed-benchmark).

Derives, from explicit Dirac matrices and CM-frame four-momenta (no trace identities assumed):
  1. the spin-averaged squared amplitude (1/4) sum |M|^2 with a massive muon and massless electrons,
  2. d sigma / d Omega = beta / (64 pi^2 s) x (1/4) sum |M|^2, written with alpha = e^2 / (4 pi),
  3. the total cross section by integrating over the solid angle, for any beta, and its beta -> 1 limit,
  4. d sigma / d cos theta and the forward-backward asymmetry,
and compares each with the reference forms (PDG review "Cross-Section Formulae for Specific Processes", eqs. 51.2
and 51.3; see evidence/). Status of what this shows: an analytic derivation under the stated assumptions, not a
formal proof; SymPy simplification is trusted as a tool.

Usage: python3 derive.py [--out derivation.json]
"""
from __future__ import annotations

import argparse
import json
import sys

import sympy as sp
from sympy.physics.matrices import mgamma

s, m, alpha = sp.symbols("s m alpha", positive=True)
c = sp.symbols("c", real=True)  # cos theta
beta = sp.symbols("beta", positive=True)
e = sp.sqrt(4 * sp.pi * alpha)  # coupling convention alpha = e^2 / (4 pi) (Heaviside-Lorentz, hbar = c = 1)

G = [mgamma(mu) for mu in range(4)]  # gamma^mu, Dirac representation
METRIC = sp.diag(1, -1, -1, -1)
ONE = sp.eye(4)


def slash(p):
    """p-slash = gamma^mu p_mu = gamma^0 p^0 - gamma^i p^i."""
    return G[0] * p[0] - G[1] * p[1] - G[2] * p[2] - G[3] * p[3]


def kinematics():
    E = sp.sqrt(s) / 2
    pmu = sp.sqrt(E ** 2 - m ** 2)
    sn = sp.sqrt(1 - c ** 2)
    p1 = (E, 0, 0, E)          # incoming e-
    p2 = (E, 0, 0, -E)         # incoming e+
    p3 = (E, pmu * sn, 0, pmu * c)    # outgoing mu-; theta between incoming e- and outgoing mu-
    p4 = (E, -pmu * sn, 0, -pmu * c)  # outgoing mu+
    return p1, p2, p3, p4


def squared_amplitude():
    p1, p2, p3, p4 = kinematics()
    le = [[(slash(p2) * G[a] * slash(p1) * G[b]).trace() for b in range(4)] for a in range(4)]            # Tr[p2 g^a p1 g^b]
    lm = [[((slash(p3) + m * ONE) * G[a] * (slash(p4) - m * ONE) * G[b]).trace() for b in range(4)] for a in range(4)]
    contraction = sum(le[a][b] * lm[a][b] * METRIC[a, a] * METRIC[b, b] for a in range(4) for b in range(4))
    return sp.simplify(sp.Rational(1, 4) * e ** 4 / s ** 2 * contraction)


def derive() -> dict:
    msq = squared_amplitude()
    beta_of_m = sp.sqrt(1 - 4 * m ** 2 / s)
    dsdo = sp.simplify(beta_of_m / (64 * sp.pi ** 2 * s) * msq)
    # reference eq. 51.2 with N_c = 1, Q_f^2 = 1, written in terms of m through beta
    ref_512 = alpha ** 2 / (4 * s) * beta_of_m * (1 + c ** 2 + (1 - beta_of_m ** 2) * (1 - c ** 2))
    dsdc = sp.simplify(2 * sp.pi * dsdo)  # azimuthal symmetry
    sigma = sp.simplify(sp.integrate(dsdc, (c, -1, 1)))
    sigma_beta = sp.simplify(sigma.subs(m, sp.sqrt(s * (1 - beta ** 2)) / 2))
    sigma_limit = sp.limit(sigma_beta, beta, 1)
    ref_513 = 4 * sp.pi * alpha ** 2 / (3 * s)
    massless_dsdc = sp.simplify(dsdc.subs(m, 0))
    shape = sp.simplify(massless_dsdc / sigma_limit)
    afb = sp.simplify((sp.integrate(massless_dsdc, (c, 0, 1)) - sp.integrate(massless_dsdc, (c, -1, 0))) / sigma_limit)
    checks = {
        "squared_amplitude_massless_equals_e4_1_plus_c2": sp.simplify(msq.subs(m, 0) - e ** 4 * (1 + c ** 2)) == 0,
        "dsigma_domega_equals_ref_eq_51_2": sp.simplify(dsdo - ref_512) == 0,
        "sigma_beta_to_1_equals_ref_eq_51_3": sp.simplify(sigma_limit - ref_513) == 0,
        "sigma_general_beta_equals_beta_3_minus_beta2_over_2": sp.simplify(sigma_beta - ref_513 * beta * (3 - beta ** 2) / 2) == 0,
        "shape_normalized_equals_3_8_1_plus_c2": sp.simplify(shape - sp.Rational(3, 8) * (1 + c ** 2)) == 0,
        "forward_backward_asymmetry_zero": afb == 0,
        "dsigma_dcos_even_in_c": sp.simplify(dsdc - dsdc.subs(c, -c)) == 0,
        "threshold_sigma_vanishes_linearly_in_beta": sp.limit(sigma_beta / beta, beta, 0) == sp.simplify(ref_513 * sp.Rational(3, 2)),
    }
    return {
        "label": "theory:qed-benchmark tree-level derivation (SymPy " + sp.__version__ + ")",
        "assumptions": ["one s-channel photon, tree level (order alpha^2 in the cross section)", "massless electrons, muon mass m kept",
                        "unpolarized beams: average over the 4 initial spin states, sum over final spins",
                        "alpha = e^2 / (4 pi), hbar = c = 1", "point-like fermions, no Z exchange, no radiative corrections"],
        "results": {
            "spin_averaged_squared_amplitude": str(msq),
            "dsigma_domega": str(dsdo),
            "dsigma_dcos_theta": str(dsdc),
            "sigma_total": str(sigma_beta),
            "sigma_total_massless": str(sigma_limit),
            "dsigma_dcos_theta_massless": str(massless_dsdc),
            "normalized_shape_massless": str(shape),
            "forward_backward_asymmetry_massless": str(afb),
        },
        "checks": {k: bool(v) for k, v in checks.items()},
        "derivation_status": "analytic-derivation",
        "status_note": "Exact at tree level under the listed assumptions; SymPy steps are trusted, not formally verified. Not a formal proof.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rec = derive()
    text = json.dumps(rec, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0 if all(rec["checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())

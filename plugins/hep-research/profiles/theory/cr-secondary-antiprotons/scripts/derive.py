#!/usr/bin/env python3
"""Derivation checks for theory:cr-secondary-antiprotons (SymPy): the closed form of the source integral for a
power-law primary and the toy x-scaling cross section, its threshold branch, and the antineutron/hyperon bookkeeping.

Source integral for one channel (projectile flux phi = C T_i^-gamma, toy dsigma/dT = (s0 / T_i) (1 - T/T_i)^n above
the threshold T_th and for T < T_i):

  I(T) = int_{max(T_th, T)}^{oo} C T_i^-gamma (s0 / T_i) (1 - T/T_i)^n dT_i.

1. Substitution x = T / T_i maps it to C s0 T^-gamma int_0^{x_max} x^(gamma-1) (1 - x)^n dx with
   x_max = min(1, T / T_th), the incomplete beta function B(x_max; gamma, n + 1).
2. Above threshold (T >= T_th): I = C s0 T^-gamma B(gamma, n + 1) = C s0 T^-gamma Gamma(gamma) Gamma(n+1) / Gamma(gamma+n+1),
   checked for symbolic gamma > 0 at n = 0, 1, 2, 3, 7.
3. Below threshold (T < T_th): the original integral and the incomplete-beta form agree (checked for n = 2 with
   symbolic gamma, T, T_th).
4. A sharp break at T_b splits the integral into two such pieces (x between T/T_b and the upper end); the pieces add.
5. Antineutrons and hyperons: (1 + Delta_Lambda) + (1 + Delta_IS + Delta_Lambda) = 2 + Delta_IS + 2 Delta_Lambda,
   the total factor of the hep-theory reference (Winkler Eq. (5); Korsmeier et al. Eq. (4)); the split into an
   antiproton and an antineutron part is this profile's bookkeeping.
Status: analytic derivation for the toy cross section; SymPy checks the algebra (not a formal proof).

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

pos = {"positive": True}
g, T, Ti, Tth, C, s0, x, Tb = sp.symbols("gamma T T_i T_th C sigma0 x T_b", **pos)
d_is, d_lam = sp.symbols("Delta_IS Delta_Lambda", nonnegative=True)


def zero(expr) -> bool:
    return sp.simplify(expr) == 0


def substitution() -> bool:
    """The integrand transforms exactly under T_i = T / x, dT_i = -T / x^2 dx."""
    n = sp.Symbol("n", nonnegative=True)
    integrand = C * Ti ** (-g) * s0 / Ti * (1 - T / Ti) ** n
    mapped = integrand.subs(Ti, T / x) * T / x ** 2
    target = C * s0 * T ** (-g) * x ** (g - 1) * (1 - x) ** n
    return zero(sp.powsimp(sp.expand_power_base(mapped / target, force=True), force=True) - 1)


def above_threshold(n: int) -> bool:
    """int_0^1 x^(gamma-1) (1-x)^n dx = Gamma(gamma) Gamma(n+1) / Gamma(gamma+n+1) for symbolic gamma > 0."""
    lhs = sp.integrate(x ** (g - 1) * (1 - x) ** n, (x, 0, 1), conds="none")
    rhs = sp.gamma(g) * sp.gamma(n + 1) / sp.gamma(g + n + 1)
    return zero(sp.gammasimp(lhs - rhs))


def direct_vs_beta(n: int, lo, hi_x) -> bool:
    """The direct integral over T_i from `lo` to oo equals the x form from 0 to hi_x = T / lo (symbolic gamma)."""
    direct = sp.integrate(Ti ** (-g - 1) * (1 - T / Ti) ** n, (Ti, lo, sp.oo), conds="none")
    via_x = T ** (-g) * sp.integrate(x ** (g - 1) * (1 - x) ** n, (x, 0, hi_x), conds="none")
    return zero(sp.expand(sp.powsimp(sp.expand_power_base(direct - via_x, force=True), force=True)))


def broken_split(n: int) -> bool:
    """Split at T_b > T_th > T: the pieces [T_th, T_b] and [T_b, oo) add to the whole for one index."""
    f = Ti ** (-g - 1) * (1 - T / Ti) ** n
    whole = sp.integrate(f, (Ti, Tth, sp.oo), conds="none")
    pieces = sp.integrate(f, (Ti, Tth, Tb), conds="none") + sp.integrate(f, (Ti, Tb, sp.oo), conds="none")
    return zero(sp.expand(sp.powsimp(sp.expand_power_base(whole - pieces, force=True), force=True)))


def bookkeeping() -> bool:
    return zero((1 + d_lam) + (1 + d_is + d_lam) - (2 + d_is + 2 * d_lam))


def derive() -> dict:
    checks = {"substitution_x_equals_T_over_Ti": substitution(),
              **{f"above_threshold_beta_function_n{n}": above_threshold(n) for n in (0, 1, 2, 3, 7)},
              "below_threshold_incomplete_beta_n2": direct_vs_beta(2, Tth, T / Tth),
              "above_threshold_direct_equals_beta_n2": direct_vs_beta(2, T, 1),
              "broken_power_law_pieces_add_n2": broken_split(2),
              "antineutron_hyperon_bookkeeping": bookkeeping()}
    return {
        "label": f"theory:cr-secondary-antiprotons source integral for the toy cross section (SymPy {sp.__version__})",
        "status": "analytic-derivation",
        "assumptions": ["projectile flux a power law (or sharp broken power law) in kinetic energy per nucleon",
                        "toy prompt cross section (sigma0 / T_i) (1 - T/T_i)^n above a threshold T_th, zero for T >= T_i",
                        "nuclear channels: constant rescaling of pp at the same energy per nucleon",
                        "antineutron and hyperon contributions as multiplicative factors on the prompt cross section"],
        "results": {"above_threshold": "4 pi n_j f_ij sigma0 C T^-gamma B(gamma, n + 1)",
                    "general": "4 pi n_j f_ij sigma0 C T^-gamma B(min(1, T/T_th); gamma, n + 1)",
                    "factor": "(1 + Delta_Lambda) + (1 + Delta_IS + Delta_Lambda) = 2 + Delta_IS + 2 Delta_Lambda"},
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

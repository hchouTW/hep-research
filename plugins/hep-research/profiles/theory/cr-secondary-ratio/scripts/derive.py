#!/usr/bin/env python3
"""Derivation checks for theory:cr-secondary-ratio (SymPy): the weighted-slab ratio, the 1D thin-disc ratio, their
equivalence through lambda_esc = n_H m_H h v L / D, and the finite-thickness disc solution used as a benchmark.

One parent P (production cross section sigma_Ps, inelastic sigma_P) and one stable secondary s (inelastic sigma_s);
several parents add linearly. Kinetic energy per nucleon is conserved in fragmentation (straight-ahead), so every
species is evaluated at the same E/n and the same velocity v.

1. Weighted slab: dN_P/dx = -N_P/lambda_P, dN_s/dx = N_P/lambda_Ps - N_s/lambda_s, N_s(0) = 0, observed
   <N> = int_0^oo G(x) N(x) dx with G = exp(-x/lambda)/lambda. Result: <N_s>/<N_P> = (1/lambda_Ps) / (1/lambda + 1/lambda_s).
2. 1D thin disc: -D_i N_i'' + 2 h delta(z) n v sigma_i N_i = 2 h delta(z) S_i in |z| < L, N_i(+-L) = 0.
   N_i = N_i(0) (1 - |z|/L); the jump at z = 0 gives N_s(0)/N_P(0) = sigma_Ps / (sigma_s + D_s / (h n v L)).
3. The two agree for lambda = n m_H h v L / D_s (with 1/lambda_i = sigma_i / m_H): the grammage depends on D and L
   only through D/L, which is the D0/L degeneracy.
4. Finite disc (gas and sources uniform in |z| < h): the closed form in predict.halo_finite_disc_exact solves the
   equations in both regions and is continuous with a continuous derivative at z = h.
Status: analytic derivation under the stated model assumptions; SymPy checks the algebra (not a formal proof).

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
x, z = sp.symbols("x z", nonnegative=True)
lam, lam_p, lam_s, lam_ps = sp.symbols("lambda lambda_P lambda_s lambda_Ps", **pos)
D_p, D_s, h, L, n, v, m = sp.symbols("D_P D_s h L n v m_H", **pos)
sig_p, sig_s, sig_ps, q = sp.symbols("sigma_P sigma_s sigma_Ps q", **pos)


def slab() -> dict:
    """Solve the slab ODEs symbolically and average over the exponential path-length distribution."""
    n_p = sp.exp(-x / lam_p)
    f = sp.Function("N_s")
    sol = sp.dsolve(sp.Eq(f(x).diff(x), n_p / lam_ps - f(x) / lam_s), f(x), ics={f(0): 0}).rhs
    avg = lambda expr: sp.integrate(sp.exp(-x / lam) / lam * expr, (x, 0, sp.oo), conds="none")  # noqa: E731
    ratio = sp.simplify(avg(sol) / avg(n_p))
    closed = (1 / lam_ps) / (1 / lam + 1 / lam_s)
    return {"ratio": ratio, "closed": closed, "ok": sp.simplify(ratio - closed) == 0}


def thin_disc() -> dict:
    """Linear profiles in the halo; the jump condition at the disc fixes N(0)."""
    n_p0, n_s0 = sp.symbols("N_P0 N_s0", **pos)
    prof = lambda n0: n0 * (1 - z / L)  # noqa: E731  (z >= 0 side; symmetric)
    halo_ok = all(sp.diff(prof(n0), z, 2) == 0 for n0 in (n_p0, n_s0)) and prof(n_s0).subs(z, L) == 0
    # integrate the equation over [-eps, eps]: -2 D N'(0+) + 2 h n v sigma N(0) = 2 h S
    jump_p = sp.Eq(-2 * D_p * sp.diff(prof(n_p0), z) + 2 * h * n * v * sig_p * n_p0, 2 * h * q)
    jump_s = sp.Eq(-2 * D_s * sp.diff(prof(n_s0), z) + 2 * h * n * v * sig_s * n_s0, 2 * h * n * v * sig_ps * n_p0)
    sol = sp.solve([jump_p, jump_s], [n_p0, n_s0], dict=True)[0]
    ratio = sp.simplify(sol[n_s0] / sol[n_p0])
    closed = sig_ps / (sig_s + D_s / (h * n * v * L))
    grammage = n * m * h * v * L / D_s
    slab_mapped = (sig_ps / m) / (1 / grammage + sig_s / m)
    scale = sp.symbols("c", positive=True)
    return {"ratio": ratio, "closed": closed, "grammage": grammage, "halo_profile_ok": bool(halo_ok),
            "ok": sp.simplify(ratio - closed) == 0,
            "equals_slab": sp.simplify(ratio - slab_mapped) == 0,
            "invariant_D_L_scaling": sp.simplify(ratio.subs({D_s: scale * D_s, L: scale * L}) - ratio) == 0,
            "not_invariant_D_alone": sp.simplify(ratio.subs(D_s, scale * D_s) - ratio) != 0}


def finite_disc() -> dict:
    """The finite-disc closed form satisfies the ODEs in both regions and the matching at z = h.

    The rates are written as Gamma_i = D_i k_i^2, so every check is a rational identity in cosh and sinh of k_i h and
    k_i z (treated as independent atoms; no hyperbolic identity is needed) and sp.cancel decides it exactly."""
    k_p, k_s, g_ps = sp.symbols("k_P k_s Gamma_Ps", **pos)
    g_p, g_s = D_p * k_p ** 2, D_s * k_s ** 2
    delta = lambda k: sp.cosh(k * h) + (L - h) * k * sp.sinh(k * h)  # noqa: E731
    a = q / g_p
    big_a = -a / delta(k_p)
    np_in = a + big_a * sp.cosh(k_p * z)
    np_out = -big_a * k_p * sp.sinh(k_p * h) * (L - z)
    c = g_ps * a / g_s
    e = g_ps * big_a / (g_s - D_s * k_p ** 2)
    f = -(c + e * delta(k_p)) / delta(k_s)
    ns_in = c + e * sp.cosh(k_p * z) + f * sp.cosh(k_s * z)
    ns_out = -(e * k_p * sp.sinh(k_p * h) + f * k_s * sp.sinh(k_s * h)) * (L - z)
    zero = lambda expr: sp.cancel(sp.together(sp.expand(expr))) == 0  # noqa: E731
    checks = {
        "parent_disc_equation": zero(D_p * sp.diff(np_in, z, 2) - g_p * np_in + q),
        "parent_value_continuous_at_h": zero((np_in - np_out).subs(z, h)),
        "parent_derivative_continuous_at_h": zero(sp.diff(np_in - np_out, z).subs(z, h)),
        "parent_symmetric_at_0": sp.diff(np_in, z).subs(z, 0) == 0,
        "secondary_disc_equation": zero(D_s * sp.diff(ns_in, z, 2) - g_s * ns_in + g_ps * np_in),
        "secondary_value_continuous_at_h": zero((ns_in - ns_out).subs(z, h)),
        "secondary_derivative_continuous_at_h": zero(sp.diff(ns_in - ns_out, z).subs(z, h)),
        "halo_vanishes_at_L": np_out.subs(z, L) == 0 and ns_out.subs(z, L) == 0,
        "halo_profiles_linear": sp.diff(np_out, z, 2) == 0 and sp.diff(ns_out, z, 2) == 0,
    }
    return {"checks": checks, "parent_mid_plane": sp.simplify(np_in.subs(z, 0))}


def derive() -> dict:
    s, t, fd = slab(), thin_disc(), finite_disc()
    checks = {"slab_average_equals_closed_form": s["ok"], "thin_disc_jump_solution": t["ok"],
              "thin_disc_halo_profile_linear_and_zero_at_L": t["halo_profile_ok"],
              "thin_disc_equals_slab_with_grammage_nmhvL_over_D": t["equals_slab"],
              "ratio_invariant_under_D_and_L_scaled_together": t["invariant_D_L_scaling"],
              "ratio_changes_with_D_alone": t["not_invariant_D_alone"],
              **{f"finite_disc_{k}": v for k, v in fd["checks"].items()}}
    return {
        "label": f"theory:cr-secondary-ratio slab and 1D thin-disc ratios (SymPy {sp.__version__})",
        "status": "analytic-derivation",
        "assumptions": ["steady state; one stable secondary; parents are pure primaries (no parent-to-parent feeding)",
                        "kinetic energy per nucleon conserved in fragmentation (straight-ahead); same v for all species",
                        "no convection, reacceleration, energy losses or radioactive decay; free escape at |z| = L",
                        "thin disc: gas and sources in 2 h delta(z); finite disc: uniform in |z| < h",
                        "cross sections are inputs (effective, cumulative); hydrogen target only"],
        "results": {"slab_ratio": sp.sstr(s["closed"]), "thin_disc_ratio": sp.sstr(t["closed"]),
                    "escape_grammage": sp.sstr(t["grammage"]),
                    "finite_disc_parent_mid_plane": sp.sstr(fd["parent_mid_plane"])},
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

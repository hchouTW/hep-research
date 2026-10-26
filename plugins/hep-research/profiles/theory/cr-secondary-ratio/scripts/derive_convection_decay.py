#!/usr/bin/env python3
"""Derivation checks for the 1D thin-disc model with constant convection and radioactive decay (SymPy), work package
B2 of theory:cr-secondary-ratio. Recorded in ../derivations/convection-decay-record.md.

Model (one species i, halo |z| < L, thin disc 2 h delta(z), free escape N_i(+-L) = 0, steady state):

    -D_i N_i'' + d/dz (V_c sign(z) N_i) + Gamma_i N_i + 2 h delta(z) n v sigma_i N_i = 2 h delta(z) q_i + G_i(z)

with constant convective speed V_c away from the disc (conservative form: the derivative of sign(z) gives the
2 V_c delta(z) N_i sweeping term at the disc; the adiabatic energy change that goes with div V is neglected, as are
all other energy changes), decay rate Gamma_i = 1/(gamma tau_0) of an unstable species (0 for a stable one), disc
source q_i = n v sum_j sigma_ji N_j(0), and the halo source G_i(z) = Gamma_R N_R(z) of the daughter of a radioactive
species R (10Be -> 10B).

1. Stable species, V_c > 0: N = N(0) (e^{V_c L/D} - e^{V_c z/D}) / (e^{V_c L/D} - 1); the jump at z = 0 gives
   N(0) = 2 h q / (K + 2 h n v sigma) with K = V_c (1 + coth(V_c L / 2D)).
2. Radioactive species: N = N(0) e^{V_c z/2D} sinh(S (L - z)/2) / sinh(S L/2), S = sqrt(V_c^2/D^2 + 4 Gamma/D);
   K = V_c + D S coth(S L/2). Step 1 is the case Gamma = 0 (S = V_c/D).
3. Limits (B2-1): K -> 2 D / L for V_c -> 0 and Gamma -> 0 in either order, so the ratio reduces to the pure-diffusion
   closed form sigma_Ps r / (sigma_s + D_s / (h n v L)) of derive.py.
4. Daughter of a radioactive species: particular solution sum_pm c_pm e^{k_pm z}, k_pm = V_c/(2 D_R) +- S_R/2,
   plus the homogeneous a + b g(z), g(z) = (e^{V_c z/D} - 1) D / V_c; N(L) = 0 and the jump at z = 0 fix a and b.
   Checked: the ODE, the boundary conditions, the gain vanishing as Gamma -> 0, and number conservation (decay moves
   particles from R to the daughter: with equal D and sigma the sum R + daughter does not depend on Gamma).
5. Dimensions (B2-2): each symbol is given its dimension in length, time and mass; [K] = velocity, [S L] = [V_c L/D]
   = [Gamma t] = 1, K/(2 h n v) is an area (a cross section) and the ratio is dimensionless.
Status: analytic derivation under the stated model assumptions; SymPy checks the algebra (not a formal proof).

Usage: python3 derive_convection_decay.py [--out ../derivations/convection-decay-derivation.json]
Exit 0 all checks pass, 1 a check fails, 2 SymPy is missing (JSON failed status on stdout).
"""
from __future__ import annotations

import argparse
import json
import math
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
z = sp.symbols("z", nonnegative=True)
D, D_R, D_d, V, L, h, n, v = sp.symbols("D D_R D_d V_c L h n v", **pos)
sigma, sigma_R, sigma_d, sigma_Ps, q, q_d, N0, N_R0 = sp.symbols(
    "sigma sigma_R sigma_d sigma_Ps q q_d N_0 N_R0", **pos)
Gam = sp.symbols("Gamma", **pos)
ratio_r = sp.symbols("r", **pos)


def is_zero(expr) -> bool:
    """Exact zero test for rational functions of exponentials (and hyperbolic functions) of symbolic arguments.

    Each exp(sum_k c_k m_k) (c_k rational, m_k a monomial) is replaced by prod_k Y_k^(c_k d_k) with Y_k =
    exp(m_k / d_k) a new symbol, d_k the common denominator of the c_k of m_k. The expression becomes a rational
    function of independent symbols and sp.cancel decides it exactly."""
    expr = sp.sympify(expr).rewrite(sp.exp)
    pieces: dict = {}
    for atom in expr.atoms(sp.exp):
        for term in sp.Add.make_args(sp.expand(atom.args[0])):
            coeff, mono = term.as_coeff_Mul()
            pieces.setdefault(mono, []).append(sp.Rational(coeff))
    denom = {m: math.lcm(*[int(c.q) for c in cs]) for m, cs in pieces.items()}
    subs_y = {m: sp.Symbol(f"Y{i}", positive=True) for i, m in enumerate(pieces)}
    swap = {}
    for atom in expr.atoms(sp.exp):
        val = sp.Integer(1)
        for term in sp.Add.make_args(sp.expand(atom.args[0])):
            coeff, mono = term.as_coeff_Mul()
            val *= subs_y[mono] ** (sp.Rational(coeff) * denom[mono])
        swap[atom] = val
    return sp.cancel(sp.together(expr.xreplace(swap))) == 0


def jump(dens, deriv0, diff, sigma_i):
    """Left side of the integrated equation over the thin disc: -2 D N'(0+) + 2 V_c N(0) + 2 h n v sigma N(0)."""
    return -2 * diff * deriv0 + 2 * V * dens + 2 * h * n * v * sigma_i * dens


def escape_term(diff, decay):
    """K = V_c + D S coth(S L/2), S = sqrt(V_c^2/D^2 + 4 Gamma/D)."""
    s_root = sp.sqrt(V ** 2 / diff ** 2 + 4 * decay / diff)
    return V + diff * s_root * sp.coth(s_root * L / 2)


def stable_species() -> dict:
    """Step 1: the stable species with convection."""
    prof = N0 * (sp.exp(V * L / D) - sp.exp(V * z / D)) / (sp.exp(V * L / D) - 1)
    ode = -D * sp.diff(prof, z, 2) + V * sp.diff(prof, z)
    n0 = sp.solve(sp.Eq(jump(N0, sp.diff(prof, z).subs(z, 0), D, sigma), 2 * h * q), N0)[0]
    big_k = V * (1 + sp.coth(V * L / (2 * D)))
    closed = 2 * h * q / (big_k + 2 * h * n * v * sigma)
    return {"checks": {"stable_halo_equation": is_zero(ode), "stable_value_at_0": is_zero(prof.subs(z, 0) - N0),
                       "stable_vanishes_at_L": is_zero(prof.subs(z, L)),
                       "stable_jump_gives_closed_form": is_zero(n0 - closed),
                       "stable_escape_term_is_decay_form_at_zero_decay": is_zero(
                           escape_term(D, 0) - big_k)},
            "escape_term": big_k, "mid_plane": closed}


def radioactive_species() -> dict:
    """Step 2: a radioactive species (decay rate Gamma) with convection. S is kept as its own symbol with
    Gamma = (D S^2 - V_c^2/D)/4 (its definition solved for Gamma) so the zero tests are exact; the escape term is
    then written back with S = sqrt(V_c^2/D^2 + 4 Gamma/D)."""
    s_sym = sp.symbols("S", positive=True)
    gam = (D * s_sym ** 2 - V ** 2 / D) / 4
    prof = N0 * sp.exp(V * z / (2 * D)) * sp.sinh(s_sym * (L - z) / 2) / sp.sinh(s_sym * L / 2)
    ode = -D * sp.diff(prof, z, 2) + V * sp.diff(prof, z) + gam * prof
    n0 = sp.solve(sp.Eq(jump(N0, sp.diff(prof, z).subs(z, 0), D, sigma), 2 * h * q), N0)[0]
    k_sym = V + D * s_sym * sp.coth(s_sym * L / 2)
    big_k = escape_term(D, Gam)
    closed = 2 * h * q / (big_k + 2 * h * n * v * sigma)
    return {"checks": {"radioactive_halo_equation": is_zero(ode),
                       "radioactive_value_at_0": is_zero(prof.subs(z, 0) - N0),
                       "radioactive_vanishes_at_L": is_zero(prof.subs(z, L)),
                       "radioactive_jump_gives_closed_form": is_zero(
                           n0 - 2 * h * q / (k_sym + 2 * h * n * v * sigma)),
                       "radioactive_S_definition_consistent": sp.simplify(
                           big_k.subs(Gam, gam) - k_sym) == 0},
            "escape_term": big_k, "mid_plane": closed}


def limits() -> dict:
    """Step 3 (B2-1): V_c -> 0 and Gamma -> 0 reduce K to 2 D / L, and the ratio to the pure-diffusion form."""
    big_k = escape_term(D, Gam)
    pure = 2 * D / L
    k_no_decay = sp.simplify(big_k.subs(Gam, 0))  # S -> V_c/D (V_c > 0)
    v_then_g = sp.limit(sp.limit(big_k, V, 0), Gam, 0)
    g_then_v = sp.limit(k_no_decay, V, 0)
    # the secondary-to-parent ratio: N_s(0)/N_P(0) with q_s = n v sigma_Ps N_P(0)
    ratio = sigma_Ps * ratio_r / (sigma + big_k / (2 * h * n * v))
    pure_ratio = sigma_Ps * ratio_r / (sigma + D / (h * n * v * L))
    ratio_limit = sp.limit(sp.limit(ratio, V, 0), Gam, 0)
    # independent of sp.limit: Taylor series. At Gamma = 0, K = 2D/L + V_c + V_c^2 L/(6D) + O(V_c^3);
    # at V_c = 0, K = 2D/L + (2/3) Gamma L + O(Gamma^2) (with S = 2 sqrt(Gamma/D)).
    ser_v = sp.series(k_no_decay, V, 0, 3).removeO()
    first_order = ser_v.coeff(V, 1)
    k_static = sp.simplify(big_k.subs(V, 0))
    ser_g = sp.series(k_static, Gam, 0, 2).removeO()
    return {"checks": {"limit_V_c_then_Gamma_gives_2D_over_L": is_zero(v_then_g - pure),
                       "limit_Gamma_then_V_c_gives_2D_over_L": is_zero(g_then_v - pure),
                       "limit_ratio_equals_pure_diffusion_ratio": is_zero(ratio_limit - pure_ratio),
                       "series_in_V_c_constant_term_is_2D_over_L": sp.simplify(ser_v.coeff(V, 0) - pure) == 0,
                       "escape_term_first_order_in_V_c_is_V_c": sp.simplify(first_order - 1) == 0,
                       "series_in_Gamma_constant_term_is_2D_over_L": sp.simplify(ser_g.coeff(Gam, 0) - pure) == 0,
                       "escape_term_first_order_in_Gamma_is_2L_over_3": sp.simplify(
                           ser_g.coeff(Gam, 1) - 2 * L / 3) == 0},
            "escape_term_no_decay": k_no_decay, "first_order_coefficient_in_V_c": first_order}


def daughter_species() -> dict:
    """Step 4: the daughter (stable) of a radioactive parent R, with the halo gain Gamma N_R(z) and a direct disc
    source q_d; the closed form used by convection_decay.decay_daughter_mid_plane.

    The parent's S_R is kept as its own symbol with Gamma = (D_R S_R^2 - V_c^2/D_R)/4 (the definition of S_R
    solved for Gamma), so every expression is a rational function of exponentials of linear forms and the zero tests
    are exact and fast."""
    s_r = sp.symbols("S_R", positive=True)
    gam = (D_R * s_r ** 2 - V ** 2 / D_R) / 4
    k_m, k_p = V / (2 * D_R) - s_r / 2, V / (2 * D_R) + s_r / 2
    e_sl = sp.exp(-s_r * L)
    amp_m, amp_p = N_R0 / (1 - e_sl), -N_R0 * e_sl / (1 - e_sl)
    parent_prof = amp_m * sp.exp(k_m * z) + amp_p * sp.exp(k_p * z)
    radioactive = N_R0 * sp.exp(V * z / (2 * D_R)) * sp.sinh(s_r * (L - z) / 2) / sp.sinh(s_r * L / 2)
    c_m = gam * amp_m / (V * k_m - D_d * k_m ** 2)
    c_p = gam * amp_p / (V * k_p - D_d * k_p ** 2)
    part = c_m * sp.exp(k_m * z) + c_p * sp.exp(k_p * z)
    g_fun = (sp.exp(V * z / D_d) - 1) * D_d / V
    wall = 2 * V + 2 * h * n * v * sigma_d
    p0, pl, dp0 = part.subs(z, 0), part.subs(z, L), sp.diff(part, z).subs(z, 0)
    g_l = g_fun.subs(z, L)
    big_b = (wall * (p0 - pl) - 2 * D_d * dp0 - 2 * h * q_d) / (2 * D_d + wall * g_l)
    big_a = -big_b * g_l - pl
    prof = big_a + big_b * g_fun + part
    dens0 = prof.subs(z, 0)
    checks = {
        "daughter_parent_profile_is_radioactive_solution": is_zero(parent_prof - radioactive),
        "daughter_parent_profile_solves_decay_equation": is_zero(
            -D_R * sp.diff(parent_prof, z, 2) + V * sp.diff(parent_prof, z) + gam * parent_prof),
        # each particular term c e^{kz} solves -D_d N'' + V_c N' = Gamma a e^{kz}; the homogeneous part solves it
        # with zero source
        "daughter_particular_terms_solve_halo_equation": all(
            is_zero(c * (V * k - D_d * k ** 2) - gam * a) for c, k, a in ((c_m, k_m, amp_m), (c_p, k_p, amp_p))),
        "daughter_homogeneous_part_solves_halo_equation": is_zero(
            -D_d * sp.diff(g_fun, z, 2) + V * sp.diff(g_fun, z)),
        "daughter_vanishes_at_L": is_zero(prof.subs(z, L)),
        "daughter_jump_condition": is_zero(jump(dens0, sp.diff(prof, z).subs(z, 0), D_d, sigma_d) - 2 * h * q_d),
    }
    gain = dens0.subs(q_d, 0)
    # Gamma -> 0 is S_R -> V_c/D_R, where single terms have poles (k_- -> 0) that cancel. Checked at 50 digits
    # (mpmath) at a rational point with D_d != D_R: gain/N_R0 falls linearly with Gamma, gain/Gamma converges.
    point = {V: sp.Rational(1, 3), D_R: sp.Rational(7, 5), D_d: sp.Rational(9, 10), L: sp.Integer(4),
             h: sp.Rational(1, 40), n: sp.Integer(1), v: sp.Integer(1), sigma_d: sp.Rational(3, 2), N_R0: 1}
    at_point = gain.subs(point)
    slopes = []
    for eps_exp in (20, 21, 22):
        eps = sp.Rational(1, 10 ** eps_exp)
        s_val = point[V] / point[D_R] + eps
        g_val = sp.N(at_point.subs(s_r, s_val), 50)
        slopes.append(g_val / sp.N(gam.subs(point).subs(s_r, s_val), 50))
    checks["daughter_gain_vanishes_without_decay"] = bool(
        abs(slopes[0] - slopes[2]) < 1e-15 * abs(slopes[2]) and abs(slopes[2]) < 1e3)
    # the direct part is the stable closed form of step 1 (it does not depend on the decay)
    direct = dens0 - gain
    stable = 2 * h * q_d / (V * (1 + sp.coth(V * L / (2 * D_d))) + 2 * h * n * v * sigma_d)
    checks["daughter_direct_part_is_stable_closed_form"] = is_zero(direct - stable)
    # number conservation: equal D and sigma; the parent fed by the disc source q, the daughter by decay only:
    # N_R(0) + N_d(0) equals the stable species with source q, whatever the decay rate
    equal = {D_R: D, D_d: D, sigma_d: sigma}
    n_r0 = 2 * h * q / (V + D * s_r * sp.coth(s_r * L / 2) + 2 * h * n * v * sigma)
    total = gain.subs(equal).subs(N_R0, n_r0) + n_r0
    checks["decay_conserves_number_equal_transport"] = is_zero(
        total - 2 * h * q / (V * (1 + sp.coth(V * L / (2 * D))) + 2 * h * n * v * sigma))
    return {"checks": checks, "mid_plane_gain": gain}


# dimensions: length, time, mass as positive symbols; each model symbol maps to its dimension
LEN, TIME, MASS = sp.symbols("length time mass", positive=True)
DIMENSIONS = {D: LEN ** 2 / TIME, D_R: LEN ** 2 / TIME, D_d: LEN ** 2 / TIME, V: LEN / TIME, L: LEN, h: LEN,
              n: LEN ** -3, v: LEN / TIME, sigma: LEN ** 2, sigma_R: LEN ** 2, sigma_d: LEN ** 2, sigma_Ps: LEN ** 2,
              Gam: 1 / TIME, z: LEN, ratio_r: sp.Integer(1)}


def dimension(expr):
    """Dimension of a monomial or of a sum of terms of equal dimension (each term checked separately)."""
    terms = sp.Add.make_args(sp.expand(expr))
    dims = {sp.powsimp(t.subs(DIMENSIONS, simultaneous=True), force=True).as_coeff_Mul()[1] for t in terms}
    if len(dims) != 1:
        raise ValueError(f"terms of different dimension in {expr}: {dims}")
    return dims.pop()


def dimension_checks() -> dict:
    """Step 5 (B2-2): dimensions of every quantity that enters a closed form."""
    s_sq = V ** 2 / D ** 2 + 4 * Gam / D
    return {
        "dim_S_squared_is_inverse_length_squared": dimension(s_sq) == LEN ** -2,
        "dim_S_L_dimensionless": dimension(s_sq * L ** 2) == 1,
        "dim_peclet_V_c_L_over_D_dimensionless": dimension(V * L / D) == 1,
        "dim_decay_rate_times_time_dimensionless": dimension(Gam * TIME) == 1,
        "dim_escape_term_V_c_is_velocity": dimension(V) == LEN / TIME,
        "dim_escape_term_D_S_is_velocity": dimension(D ** 2 * s_sq) == (LEN / TIME) ** 2,
        "dim_pure_diffusion_2D_over_L_is_velocity": dimension(2 * D / L) == LEN / TIME,
        "dim_disc_loss_2hnv_sigma_is_velocity": dimension(2 * h * n * v * sigma) == LEN / TIME,
        "dim_escape_over_2hnv_is_cross_section": dimension(V / (2 * h * n * v)) == LEN ** 2,
        "dim_ratio_dimensionless": dimension(sigma_Ps * ratio_r / sigma) == 1,
        "dim_daughter_g_of_L_is_length": dimension(L) == LEN and dimension(D / V) == LEN,
        "dim_daughter_k_is_inverse_length": dimension(V / D_R) == 1 / LEN,
        "dim_daughter_particular_coefficient_is_density": dimension(Gam / (V * V / D_R)) == 1,
    }


def derive() -> dict:
    st, ra, li, da = stable_species(), radioactive_species(), limits(), daughter_species()
    checks = {**st["checks"], **ra["checks"], **li["checks"], **da["checks"], **dimension_checks()}
    return {
        "label": f"theory:cr-secondary-ratio 1D thin disc with convection and decay (SymPy {sp.__version__})",
        "status": "analytic-derivation",
        "assumptions": [
            "steady state; parents are pure primaries with given mid-plane ratios; secondaries fed by parents only, "
            "plus the decay gain of a radioactive secondary's daughter (10Be -> 10B)",
            "kinetic energy per nucleon conserved in fragmentation and in decay (straight-ahead); same v for all species",
            "constant convective speed V_c sign(z) in the whole halo, conservative form d/dz(V N); adiabatic energy "
            "change, reacceleration and all other energy changes neglected",
            "decay rate 1/(gamma tau_0) in the whole halo; decay inside the thin disc neglected (measure zero)",
            "fully stripped 7Be cannot decay by electron capture and is treated as stable",
            "thin disc: gas and sources in 2 h delta(z); free escape at |z| = L; cross sections are inputs "
            "(effective, cumulative), hydrogen target only",
        ],
        "conventions": {"unit_system": "symbols in any consistent unit system; the code uses CGS (cm, s, g)",
                        "hbar_c_one": False, "energy_variable": "kinetic energy per nucleon E/n",
                        "frame": "Galactic rest frame; observer at the disc mid-plane z = 0",
                        "convection": "V_c(z) = V_c sign(z), conservative form d/dz(V_c(z) N)"},
        "results": {"stable_escape_term": sp.sstr(st["escape_term"]),
                    "radioactive_escape_term": sp.sstr(ra["escape_term"]),
                    "mid_plane_density": sp.sstr(ra["mid_plane"]),
                    "escape_term_no_decay_limit": sp.sstr(li["escape_term_no_decay"]),
                    "pure_diffusion_limit_of_escape_term": "2*D/L",
                    "first_order_coefficient_in_V_c": sp.sstr(li["first_order_coefficient_in_V_c"])},
        "checks": {k: bool(val) for k, val in checks.items()},
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

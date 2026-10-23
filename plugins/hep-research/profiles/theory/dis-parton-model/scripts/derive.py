#!/usr/bin/env python3
"""Derivation for theory:dis-parton-model: the O(alpha_s) longitudinal structure function in the Altarelli-Martinelli
form, from the coefficient functions of Moch, Vermaseren and Vogt (Eqs. 1-3, dispm:C03, C04) and the convolution of
PDG Eq. 18.22 (dispm:C02), with LO F_2 = x sum e_q^2 (q + qbar) (PDG Eq. 18.18, dispm:C01).

Steps (SymPy, exact arithmetic):
 1. Flavour algebra: with q_s = sum (q_i + qbar_i), <e^2> = n_f^-1 sum e_i^2 and q_ns = sum (e_i^2 - <e^2>)(q_i + qbar_i)
    (the non-singlet combination that reproduces LO F_2; identified here, the paper calls it 'the corresponding
    non-singlet combination'), q_ns + <e^2> q_s = sum e_i^2 (q_i + qbar_i) = F_2/x, for n_f = 3..6. Since
    c_L,ps^(1) = 0, c_L,q^(1) = c_L,ns^(1), so x^-1 F_L = a_s [c_ns (x) (F_2/x) + <e^2> c_g (x) g], a_s = alpha_s/(4 pi).
 2. Change of variables z = x/y in C (x) f = int_x^1 dy/y C(y) f(x/y) gives int_x^1 dz/z C(x/z) f(z) (generic C, f).
 3. With c_ns = 4 C_F y, c_g = 8 n_f y (1 - y), <e^2> n_f = sum e^2 and C_F = 4/3 the integrand equals
    a_s x^2 z^-3 [16/3 F_2(z) + 8 sum e^2 (1 - x/z) z g(z)] identically (generic functions F_2, g).
 4. Analytic checks: F_L >= 0 for non-negative densities (integrand non-negative on x <= z <= 1); F_L linear in alpha_s.
 5. Toy closed form: for the SYNTHETIC Beta-form densities of benchmarks/toy-closed-form.json, F_L(x) is integrated
    exactly; predict.py's adaptive quadrature must agree to the stated relative tolerance, and a Gauss-Legendre
    convergence study must converge to the closed form.
Status: perturbative argument at O(alpha_s) (the leading order of F_L), mu_R = mu_F = Q; not a formal proof.

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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import predict  # noqa: E402

x, y, z = sp.symbols("x y z", positive=True)
a_s, n_f = sp.symbols("a_s n_f", positive=True)
F2, g = sp.Function("F2"), sp.Function("g")
C_F = sp.Rational(4, 3)  # MVV below Eq. 3: C_F = 4/3 in QCD


def flavour_algebra(nfs=(3, 4, 5, 6)) -> dict:
    """q_ns + <e^2> q_s = sum e^2 (q + qbar), q_ns flavour-traceless, and <e^2> = 5/18 for even n_f."""
    charges = [sp.Rational(2, 3), sp.Rational(-1, 3), sp.Rational(-1, 3), sp.Rational(2, 3), sp.Rational(-1, 3),
               sp.Rational(2, 3)]  # u, d, s, c, b, t
    ok_sum, ok_traceless, e2avg = True, True, {}
    for nf_ in nfs:
        e = charges[:nf_]
        q = sp.symbols(f"q1:{nf_ + 1}")
        qb = sp.symbols(f"qb1:{nf_ + 1}")
        avg = sum(ei ** 2 for ei in e) / nf_
        qs = sum(qi + qbi for qi, qbi in zip(q, qb))
        qns = sum((ei ** 2 - avg) * (qi + qbi) for ei, qi, qbi in zip(e, q, qb))
        target = sum(ei ** 2 * (qi + qbi) for ei, qi, qbi in zip(e, q, qb))
        ok_sum &= sp.expand(qns + avg * qs - target) == 0
        ok_traceless &= sum(ei ** 2 - avg for ei in e) == 0
        e2avg[nf_] = avg
    return {"ns_plus_singlet_equals_charge_weighted_sum": bool(ok_sum), "q_ns_flavour_traceless": bool(ok_traceless),
            "e2_average_is_5_over_18_for_even_nf": all(e2avg[n] == sp.Rational(5, 18) for n in nfs if n % 2 == 0),
            "e2_average": {str(k): str(v) for k, v in e2avg.items()}}


def change_of_variables() -> bool:
    """int_x^1 dy/y C(y) f(x/y) = int_x^1 dz/z C(x/z) f(z): substitute y = x/z, |dy/dz| = x/z^2, limits swap."""
    C, f = sp.Function("C"), sp.Function("f")
    integrand_y = C(y) * f(x / y) / y
    y_of_z = x / z
    integrand_z = integrand_y.subs(y, y_of_z) * (-sp.diff(y_of_z, z))  # minus: y = x -> z = 1, y = 1 -> z = x
    manual = sp.simplify(integrand_z - C(x / z) * f(z) / z) == 0
    via_transform = sp.Integral(integrand_y, (y, x, 1)).transform(y, (x / z, z))
    (var, lo, hi), = via_transform.limits
    oriented = via_transform.function if (lo, hi) == (x, 1) else -via_transform.function
    if (lo, hi) not in ((x, 1), (1, x)):
        return False
    return manual and sp.simplify(oriented.subs(var, z) - C(x / z) * f(z) / z) == 0


def altarelli_martinelli_integrand(cf=C_F, gluon_has_e2=True) -> tuple[bool, sp.Expr]:
    """x * a_s [c_ns (x) (F_2/x) + <e^2> c_g (x) g] after z = x/y, against the Altarelli-Martinelli integrand.
    cf and gluon_has_e2 exist for negative tests (a wrong colour factor, <e^2> dropped from the gluon term)."""
    sum_e2 = sp.Symbol("Sigma_e2", positive=True)
    e2_avg = sum_e2 / n_f if gluon_has_e2 else 1
    c_ns = lambda v: 4 * cf * v  # noqa: E731  MVV Eq. 3
    c_g = lambda v: 8 * n_f * v * (1 - v)  # noqa: E731  MVV Eq. 3
    # after the change of variables the convolution integrand is C(x/z) f(z) / z
    ns = c_ns(x / z) * (F2(z) / z) / z
    gl = e2_avg * c_g(x / z) * g(z) / z
    from_coefficients = x * a_s * (ns + gl)
    am = a_s * x ** 2 / z ** 3 * (sp.Rational(16, 3) * F2(z) + 8 * sum_e2 * (1 - x / z) * z * g(z))
    return sp.simplify(from_coefficients - am) == 0, am


def toy_closed_form(cfg: dict):
    """Exact F_L(x)/alpha_s and F_2(x) for the toy Beta-form densities (expand (1 - z)^b, integrate term by term)."""
    def dens(components, v):
        return sum(sp.Rational(str(n)) * v ** sp.Rational(str(a)) * (1 - v) ** b for n, a, b in components)
    e2 = [sp.Rational(fl["charge"]) ** 2 for fl in cfg["flavours"]]
    f2z = z * sum(ei * (dens(fl["quark"], z) + dens(fl["antiquark"], z)) for ei, fl in zip(e2, cfg["flavours"]))
    gz = dens(cfg.get("gluon", []), z)
    cf = sp.Rational(cfg["C_F"])
    integrand = sp.expand((4 * cf * f2z + 8 * sum(e2) * (1 - x / z) * z * gz) / z ** 3)
    integral = sum(sp.integrate(term, (z, x, 1)) for term in sp.Add.make_args(integrand))
    fl_over_as = sp.expand(x ** 2 / (4 * sp.pi) * integral)
    return fl_over_as, f2z.subs(z, x)


def numerical_checks(cfg: dict) -> dict:
    fl_exact, f2_exact = toy_closed_form(cfg)
    tol = cfg["relative_tolerance"]
    rows, ok_quad, conv = [], True, {}
    for xv in cfg["x_points"]:
        exact = float(fl_exact.subs(x, sp.Rational(str(xv))).evalf(30))
        num = predict.fl_over_as(cfg, xv)[0]
        rel = abs(num / exact - 1.0)
        ok_quad &= rel <= tol and abs(float(f2_exact.subs(x, sp.Rational(str(xv)))) - predict.f2(cfg, xv)) <= tol
        rows.append({"x": xv, "FL_over_alpha_s_closed_form": exact, "FL_over_alpha_s_quadrature": num,
                     "relative_difference": rel})
        conv[str(xv)] = [abs(predict.fl_gauss_legendre(cfg, xv, 1.0, n) / exact - 1.0) for n in cfg["gauss_legendre_nodes"]]
    # convergence: the error at the largest rule is below tolerance and no worse than at the second largest
    converged = all(errs[-1] <= tol and errs[-1] <= max(errs[-2], 1e-14) for errs in conv.values())
    decreasing = all(errs[-1] < errs[0] for errs in conv.values())
    return {"rows": rows, "gauss_legendre_relative_error": {"nodes": cfg["gauss_legendre_nodes"], "by_x": conv},
            "quadrature_matches_closed_form": bool(ok_quad), "gauss_legendre_converges": bool(converged and decreasing),
            "closed_form_FL_over_alpha_s_nonnegative": all(r["FL_over_alpha_s_closed_form"] >= 0 for r in rows)}


def derive(cfg: dict | None = None) -> dict:
    cfg = cfg or predict.load_json(predict.DEFAULT_CONFIG)
    flav = flavour_algebra()
    am_ok, am = altarelli_martinelli_integrand()
    # positivity: with F_2, g >= 0 every term of the integrand is >= 0 on x <= z <= 1 (1 - x/z >= 0 there)
    t = sp.Symbol("t", nonnegative=True)  # z = x + t with t >= 0 covers x <= z
    bracket_nonneg = sp.factor(sp.together(1 - x / (x + t))).is_nonnegative is True
    linear_in_as = sp.simplify(sp.diff(am, a_s, 2)) == 0 and am.subs(a_s, 0) == 0
    num = numerical_checks(cfg)
    checks = {
        "change_of_variables_z_equals_x_over_y": change_of_variables(),
        "ns_plus_singlet_equals_charge_weighted_sum": flav["ns_plus_singlet_equals_charge_weighted_sum"],
        "q_ns_flavour_traceless": flav["q_ns_flavour_traceless"],
        "e2_average_is_5_over_18_for_even_nf": flav["e2_average_is_5_over_18_for_even_nf"],
        "coefficient_route_equals_altarelli_martinelli_integrand": am_ok,
        "FL_nonnegative_for_nonnegative_densities": bracket_nonneg,
        "FL_linear_in_alpha_s_and_zero_at_alpha_s_0": bool(linear_in_as),
        "toy_quadrature_matches_closed_form": num["quadrature_matches_closed_form"],
        "toy_gauss_legendre_converges": num["gauss_legendre_converges"],
    }
    return {
        "label": f"theory:dis-parton-model O(alpha_s) F_L (SymPy {sp.__version__})",
        "status": "perturbative-argument",
        "order": "F_L at O(alpha_s^1) (its leading order), F_2 at O(alpha_s^0); mu_R = mu_F = Q",
        "environment": {"python": platform.python_version(), "sympy": sp.__version__,
                        "interpreter": "from skills/hep-computing/scripts/find_python.py"},
        "assumptions": [
            "photon exchange only; massless quarks, n_f active flavours; target mass neglected (O(M^2/Q^2))",
            "x^-1 F_L = C_L,ns (x) q_ns + <e^2> (C_L,q (x) q_s + C_L,g (x) g), MVV Eq. 1, power corrections dropped",
            "c_L,ns^(1) = 4 C_F x, c_L,ps^(1) = 0, c_L,g^(1) = 8 n_f x (1 - x), expansion in alpha_s/(4 pi), MVV Eqs. 2-3",
            "q_ns = sum (e_i^2 - <e^2>)(q_i + qbar_i): identified so that LO F_2 is PDG Eq. 18.18 (not spelled out in MVV)",
            "toy densities and alpha_s values SYNTHETIC; densities not evolved in Q^2"],
        "results": {
            "altarelli_martinelli": "F_L(x) = (alpha_s/(4 pi)) x^2 int_x^1 dz/z^3 [ (16/3) F_2(z) + 8 sum_q e_q^2 "
                                    "(1 - x/z) z g(z) ]",
            "integrand_sympy": sp.sstr(am),
            "e2_average_by_nf": flav["e2_average"],
            "toy_closed_form_vs_quadrature": num["rows"],
            "toy_gauss_legendre_relative_error": num["gauss_legendre_relative_error"]},
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

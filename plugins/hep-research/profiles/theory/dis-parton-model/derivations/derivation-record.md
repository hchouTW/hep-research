# Derivation record: O(alpha_s) longitudinal structure function (theory:dis-parton-model)

**Status: `perturbative-argument`, F_L at O(alpha_s^1)** (the leading order of F_L, absolute order alpha_s^1; F_2 at
O(alpha_s^0)), mu_R = mu_F = Q. SymPy did the algebra with exact arithmetic (`scripts/derive.py`, output
`derivations/derivation.json`), and SymPy is trusted as a tool. The factorization formula and the coefficient
functions are cited, not derived. This is not a formal proof. **Numbers are synthetic only.**

**Environment.** The interpreter came from `skills/hep-computing/scripts/find_python.py` (status `found`): Python
3.13.2, SymPy 1.14.0 (also SciPy 1.17.1 and NumPy 2.4.4 for the quadrature). `derivation.json` records the Python and SymPy versions of the run that wrote it.

**References read (2026-10-23).**
- PDG review "Structure Functions" (E.C. Aschenauer, R.S. Thorne, R. Yoshida, revised August 2025), in F. Takahashi
  et al. (Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026): Eq. (18.17) p. 4, Eq. (18.18) p. 5,
  Eqs. (18.21)-(18.22) p. 7 (dispm:S01, C01, C02).
- S. Moch, J.A.M. Vermaseren, A. Vogt, arXiv:hep-ph/0411112v2, Phys. Lett. B 606 (2005) 123: Eqs. (1)-(3), printed
  pp. 1-2, and the definition of <e^k> below Eq. (11) (dispm:S02, C03, C04). Eq. (1) was checked on the rendered page.
  The bracket is <e^2> (C_L,q (x) q_s + C_L,g (x) g), so <e^2> also multiplies the gluon term.

## Steps

1. **Flavour algebra.** q_s = sum (q_i + qbar_i), <e^2> = n_f^-1 sum e_i^2, q_ns = sum (e_i^2 - <e^2>)(q_i + qbar_i).
   Then q_ns + <e^2> q_s = sum e_i^2 (q_i + qbar_i) = F_2/x by PDG Eq. (18.18). This is checked for n_f = 3..6, along
   with <e^2> = 5/18 for even n_f (as the paper states). c_L,ps^(1) = 0 gives c_L,q^(1) = c_L,ns^(1), so
   x^-1 F_L = a_s [c_ns (x) (F_2/x) + <e^2> c_g (x) g], with a_s = alpha_s/(4 pi).
2. **Change of variables.** z = x/y with |dy/dz| = x/z^2 swaps the limits and gives
   int_x^1 dy/y C(y) f(x/y) = int_x^1 dz/z C(x/z) f(z). This is checked for generic C and f, by hand substitution
   and by `Integral.transform`.
3. **Altarelli-Martinelli form.** Inserting c_ns(x/z) = 4 C_F x/z, c_g(x/z) = 8 n_f (x/z)(1 - x/z),
   <e^2> n_f = sum e^2 and C_F = 4/3 makes the integrand identical, for generic functions F_2 and g, to
   a_s x^2 z^-3 [ (16/3) F_2(z) + 8 sum e^2 (1 - x/z) z g(z) ].
4. **Limits and signs.** The integrand is linear in alpha_s and vanishes at alpha_s = 0. Because 1 - x/z >= 0 on
   x <= z <= 1, F_L >= 0 for non-negative F_2 and g.
5. **Numerical check (synthetic).** For the Beta-form toys with integer powers of (1 - x), F_L(x) is integrated exactly
   in SymPy (binomial expansion, term by term). At x = 0.001, 0.01, 0.05, 0.1, 0.3 and 0.6, adaptive quadrature in
   ln z (`predict.py`) agrees with this closed form within relative 1e-10 (observed <= 7e-16). Gauss-Legendre rules
   with 4, 8, 16, 32, 64 and 128 nodes converge to the closed form: the error falls from 0.18 at 4 nodes (x = 0.001)
   to round-off (< 1e-14) from 16 nodes on. A second numerical route, the convolution in the original variable y with
   no change of variables, agrees with the AM form within 1e-10.

## Checks run

| Check | Result |
|---|---|
| Change of variables z = x/y (generic C, f) | pass |
| Non-singlet + singlet = charge-weighted sum; q_ns flavour-traceless; <e^2> = 5/18 for even n_f | pass |
| Coefficient route = Altarelli-Martinelli integrand (generic F_2, g) | pass |
| F_L linear in alpha_s, zero at alpha_s = 0 | pass |
| F_L >= 0 for non-negative densities (analytic); F_L <= F_2 on the toy points (numerical) | pass |
| Quadrature vs exact closed form on the toy, tolerance 1e-10; Gauss-Legendre convergence study | pass |
| Units: all quantities dimensionless | pass |
| A wrong colour factor or a missing <e^2> on the gluon term breaks the identity (negative tests) | pass (`tests/test_derivation.py`) |

## Checks not run

Comparison with any published F_L (none was read, so the profile stays synthetic-only), comparison with
measurements, and all higher orders, evolution, heavy-quark, target-mass and higher-twist effects.

# Derivation record: LO Drell-Yan and O(alpha_s) angular coefficients (theory:drell-yan-lo)

**Status by part.**
- LO cross section: `analytic-derivation`.
- Angular structure (Peng Eqs. 5-7) and channel mixing: `analytic-derivation`.
- Lam-Tung relation and the per-channel lambda, nu (Eq. 10): `perturbative-argument` at O(alpha_s^1). The coplanarity
  phi1 = 0 at that order is cited from Peng et al., not derived.

The theory spec carries the weakest status, `perturbative-argument`. SymPy did the algebra with exact arithmetic
(`scripts/derive.py`, output `derivations/derivation.json`), and SymPy is trusted as a tool. This is not a formal
proof.

**Environment.** The interpreter came from `skills/hep-computing/scripts/find_python.py` (status `found`): Python
3.13.2, SymPy 1.14.0 (also SciPy 1.17.1 and NumPy 2.4.4 for the numerical checks). `derivation.json` records the
Python and SymPy versions of the run that wrote it.

**References read (2026-10-23).**
- PDG review "Cross-Section Formulae for Specific Processes" (H. Baer, R.N. Cahn, revised August 2019), in
  F. Takahashi et al. (Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026): Eq. (51.3) p. 1 and
  Eqs. (51.40)-(51.42) p. 7 (dylo:S01, C01, C02).
- J.-C. Peng, W.-C. Chang, R.E. McClellan, O. Teryaev, arXiv:1511.08932v3: Eq. (1) p. 1, Eqs. (2)-(7) p. 2,
  Eqs. (8)-(10) p. 3, and coplanarity at leading order alpha_s on p. 4 (dylo:S02, C03-C07).

## Steps

1. **Partonic cross section.** PDG Eq. 51.3 sums over final colours: sigma(e+e- -> q qbar) = N_c e_q^2 4 pi alpha^2/(3 s).
   The reverse process has the same spin- and colour-summed |M|^2 but averages over N_c^2 initial colours, so
   sigma_hat(q qbar -> l+ l-) = e_q^2 4 pi alpha^2/(3 N_c s_hat) = e_q^2 4 pi alpha^2/(9 s_hat).
2. **Hadronic cross section.** By PDG Eq. 51.40, with d sigma_hat/dM^2 = sigma_hat delta(s_hat - M^2) and s_hat = x1 x2 s,
   the parton integral is d sigma/dM^2 = sum_q int dx1 dx2 L_q(x1, x2) sigma_hat(x1 x2 s) delta(x1 x2 s - M^2), where
   L_q = e_q^2 [q1 qbar2 + qbar1 q2] (both assignments, as in Eq. 51.42).
3. **Change of variables.** With x1 = sqrt(tau) e^y and x2 = sqrt(tau) e^-y, |d(x1, x2)/d(tau, y)| = 1, and the delta
   function sets tau = M^2/s with a factor 1/s. With dM^2 = 2M dM this gives
   d^2 sigma/dM dy = (8 pi alpha^2/(9 M s)) sum e_q^2 [q1(x1) qbar2(x2) + qbar1(x1) q2(x2)]. SymPy checks every step,
   and 8 pi alpha^2/9 = (2/3)(4 pi alpha^2/3) gives the nb form.
4. **Numerical Jacobian check (synthetic).** On toy Beta-form densities (`benchmarks/toy-lo-cross-section.json`),
   the formula is integrated over M in [4, 5] GeV and y in [-0.5, 0.75] at sqrt(s) = 20 GeV. The result is compared
   with the parton integral over the matching region of (x1, x2), done directly in x1 and x2. Relative difference:
   4e-16 (tolerance 1e-8).
5. **Eq. 5.** Substituting cos theta0 = cos theta cos theta1 + sin theta sin theta1 cos(phi - phi1) (Eq. 4) into
   1 + a cos theta0 + cos^2 theta0 (Eq. 2) reproduces Eq. 5 identically. The check uses a polynomial normal form in
   the cosines and sines of the four angles, modulo sin^2 + cos^2 = 1.
6. **Eqs. 6 and 7.** Matching Eq. 3 to Eq. 5 coefficient by coefficient gives A_0..A_7 per event, as in Eq. 6 before
   Peng's event-sample average. Matching Eq. 3 (A_3..A_7 = 0) to k x Eq. 1 gives lambda = (2 - 3A0)/(2 + A0),
   mu = 2A1/(2 + A0) and nu = 2A2/(2 + A0).
7. **Lam-Tung.** 1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0). Per event A0 - A2 = sin^2 theta1 (1 - cos 2phi1) =
   2 sin^2 theta1 sin^2 phi1 >= 0 within the quark-axis representation, which vanishes for phi1 = 0. The averages over events keep both properties. So a
   coplanar quark axis (phi1 = 0, which Peng et al. state holds at O(alpha_s)) gives 1 - lambda - 2 nu = 0. The
   parameter a appears in none of A0, A1, A2, A5, A6.
8. **Eq. 10.** Inserting <sin^2 theta1> = r^2/(1 + r^2) (Eq. 8) and 5 r^2/(1 + 5 r^2) (Eq. 9) into Eq. 7 with A2 = A0
   reproduces Eq. 10 exactly. Limits: lambda = 1 and nu = 0 at r = 0; lambda -> -1/3 and nu -> 2/3 as r -> infinity.

9. **Channel mixture (analytic derivation).** Every A_i term of Eq. 3 integrates to zero over the sphere, and
   1 + cos^2 theta integrates to 16 pi/3. So d sigma_c/d Omega = sigma_c (3/(16 pi)) Eq3(A^c), with sigma_c the
   angle-integrated cross section, and the sum over channels is Eq. 3 with A_i = sum_c (sigma_c/sigma) A_i^c. Since
   2 + A0 = 8/(3 + lambda), lambda_mix = sum f_c lambda_c/(3 + lambda_c) / sum f_c/(3 + lambda_c), and nu likewise.
   A linear average of lambda differs and is wrong. The fraction f_c is a cross-section fraction in the same (qT, Q)
   bin; it equals an event fraction only with full angular acceptance.

## Checks run

| Check | Result |
|---|---|
| Colour average, Jacobian = 1, delta-function integration, 8 pi alpha^2/(9 M s) form (SymPy) | pass |
| Box integral of the formula against the parton integral on toy densities, tolerance 1e-8 | pass |
| Eq. 4 into Eq. 2 gives Eq. 5; Eq. 6 and Eq. 7 read off (SymPy) | pass |
| 1 - lambda - 2 nu = 4 (A0 - A2)/(2 + A0) >= 0; = 0 for phi1 = 0 (SymPy) | pass |
| Eqs. 8-9 into Eq. 7 give Eq. 10 for both channels; limits qT -> 0 and qT -> infinity (SymPy) | pass |
| Mixture: A_i terms integrate to 0, (1 + cos^2) to 16 pi/3; weighted sum = A-average = (3 + lambda)-weighted lambda form (SymPy) | pass |
| LO normalization against `skills/hep-theory/scripts/drell_yan_lo.py xsec` at one point, same toy partons | pass (`tests/test_prediction.py`) |
| Published closed form (Eq. 10) against the profile's numbers, 2 channels x 7 qT/Q, relative tolerance 1e-12 | pass |
| A sign error in Eq. 5 or a wrong Eq. 9 coefficient is caught (negative tests) | pass (`tests/test_derivation.py`, `tests/test_benchmark.py`) |

## Checks not run

- An independent computation of Eq. 9 (cited approximation).
- A derivation of phi1 = 0 at O(alpha_s) (cited).
- Comparison with any measured lambda, nu or cross section.
- Z exchange, NLO cross section, resummation, intrinsic transverse momentum.

## Notes on the source

- Peng et al. v3 has no Eq. (11). Both channels' lambda and nu are in Eq. (10).
- Eq. (1) carries nu/2 in front of sin^2 theta cos 2phi.
- Eq. (9) (q g) is stated by the authors to be an approximation, not an exact relation.

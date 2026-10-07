# Derivation record: scale dependence of R(e+e- -> hadrons) (theory:qcd-r-ratio)

**Status: `perturbative-argument`, fixed order alpha_s^4 in delta_QCD.** The algebra was done by SymPy with exact
rational coefficients (`scripts/derive.py`, output `derivations/derivation.json`); SymPy is trusted as a tool. This
is not a formal proof, and the series is asymptotic: agreement between orders is not convergence.

**References read.** PDG review "Quantum Chromodynamics" (J. Huston, K. Rabbertz, G. Zanderighi, revised August
2025), in F. Takahashi et al. (Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026): eq. (9.3) in 9.1.1 and
eqs. (9.7)-(9.9) in 9.2.1; PDG Table 1.1 for alpha_s(m_Z) and m_Z. Read on 2026-10-07 at page level through a
text-extraction fetch (`evidence/`, qcdr:S01, S02, C01-C04). The extract did not contain the alpha_s determinations
section or a flavour-matching prescription; neither is used.

## Steps

1. With a = alpha_s/pi, eq. (9.3) becomes d a / d ln mu^2 = -(beta_0 a^2 + beta_1 a^3 + beta_2 a^4), beta_k = pi^(k+1) b_k:
   beta_0 = (33 - 2 n_f)/12, beta_1 = (153 - 19 n_f)/24, beta_2 = (2857 - 5033 n_f/9 + 325 n_f^2/27)/128.
2. Integrating from mu to Q by Picard iteration gives a(Q) as a series in a(mu) through a^4, with L = ln(mu^2/Q^2).
3. Substituting into delta_QCD = sum c_n a(Q)^n and re-expanding gives delta_QCD = sum d_n(L) a(mu)^n:
   d_1 = c_1; d_2 = c_2 + beta_0 c_1 L; d_3 = c_3 + (2 beta_0 c_2 + beta_1 c_1) L + beta_0^2 c_1 L^2;
   d_4 = c_4 + (3 beta_0 c_3 + 2 beta_1 c_2 + beta_2 c_1) L + (3 beta_0^2 c_2 + 5/2 beta_0 beta_1 c_1) L^2 + beta_0^3 c_1 L^3.
   `predict.py` uses these closed forms; the tests check them against the SymPy result at several (L, n_f, eta).
4. At n_f = 5 (u, d, s, c, b): R_EW = 11/3, eta = 1/33, c_2 = 1.4097, c_3 = -12.805 (non-singlet part -12.767),
   c_4 = -80.44 (non-singlet part -79.98).

## Checks run

| Check | Result |
|---|---|
| d_n(L = 0) = c_n | pass |
| d/d ln mu^2 of the series truncated at a^N vanishes through a^N, N = 1..4 (exact arithmetic) | pass |
| d_2 = c_2 + beta_0 L (textbook form) | pass |
| nf = 5 values of c_2, c_3 and c_4 (non-singlet) against their known numbers | pass |
| A wrong sign of beta_0 breaks the mu-independence check (negative test) | pass (`tests/test_derivation.py`) |

## Checks not run

Formal proof; independent computation of c_3 and c_4 (they are taken from the reference); quark-mass and Z effects;
comparison with any measurement.

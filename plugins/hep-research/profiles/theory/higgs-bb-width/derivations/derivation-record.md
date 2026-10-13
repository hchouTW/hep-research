# Derivation record: scale dependence of Gamma(H -> b bbar) with the running mass (theory:higgs-bb-width)

**Status: `perturbative-argument`, fixed order alpha_s^4 in R.** The algebra was done by SymPy with exact rational
coefficients, zeta(3), zeta(5) and pi^2 kept as symbols (`scripts/derive.py`, output `derivations/derivation.json`);
SymPy is trusted as a tool. This is not a formal proof, and the series is asymptotic.

**References read on 2026-10-13** (`evidence/`, hbb:S01-S08, C01-C08): Chetyrkin hep-ph/9608318 eqs. (2), (8),
(17)-(22); Baikov, Chetyrkin, Kuhn hep-ph/0511063 eqs. (1), (3), (8), Table I; Chetyrkin hep-ph/9703278 eqs. (1),
(7)-(9); van Ritbergen, Vermaseren, Larin hep-ph/9701390 eqs. (4), (11); PDG 2026 Quark Masses eqs. (60.2)-(60.3)
and the Quarks summary table; PDG 2026 QCD eq. (9.3); PDG 2026 Table 1.1; PDG 2026 Gauge and Higgs Bosons summary
table. All read as extracted PDF text.

## Steps

1. With a = alpha_s/pi: d a / d ln mu^2 = -sum_i B_i a^(i+2), B_i = beta_i / 4^(i+1) (hep-ph/9701390 eq. (11));
   mu^2 d m / d mu^2 = -m sum_i gamma_i a^(i+1) (hep-ph/9703278 eqs. (1), (7)-(9)).
2. With t = ln(scale^2 / mu^2), Picard iteration gives a(M_H) as a series in a = a(mu) through a^4 (t = -L), and
   ln(mbar(M_H) / mbar(mu)) = -integral of gamma(a(t)) dt; its exponential is expanded through a^4.
3. Gamma / prefactor = mbar(M_H)^2 R(a(M_H)) = mbar(mu)^2 sum_n r_n(L) a^n, with
   r_1 = s_1 + 2 L, r_2 = s_2 + (2 s_1 (gamma_0 + B_0 / 2) + 2 gamma_1) L + ... (full forms in `derivation.json`);
   at n_f = 5, r_2 = 8851/144 - 47 pi^2/36 - 97 zeta3/6 + 263 L / 9 + 47 L^2 / 12.
4. `predict.py` builds the same polynomials from the RG recursion
   d r_n / dL = 2 sum_(k<n) gamma_k r_(n-1-k) + sum_(i<=n-2) B_i (n-1-i) r_(n-1-i), r_n(0) = s_n;
   the tests compare them with the SymPy result at several L.

## Checks run

| Check | Result |
|---|---|
| r_n(L = 0) = s_n | pass |
| d/d ln mu^2 of mbar(mu)^2 times the series truncated at a^N vanishes through a^N, N = 1..4 (exact) | pass |
| A wrong sign of gamma_0 breaks that check (negative test) | pass |
| r_1 = s_1 + 2 gamma_0 L | pass |
| s_1..s_3 at n_f = 5 equal hep-ph/0511063 eq. (3) (5.66667, 29.1467, 41.7576) | pass |
| n_f forms of s_2, s_3 equal hep-ph/9608318 eq. (22) | pass |
| gamma_0..gamma_2 normalization equals PDG eq. (60.3) (gamma_r = 4^r gamma_(r-1)) | pass |
| B_0..B_2 equal pi^(k+1) b_k of PDG eq. (9.3) | pass |

## Checks not run

Formal proof; independent computation of s_1..s_4 (taken from the references); gamma_3 and beta_3 against a second
source; power, top-induced and electroweak corrections; threshold matching; comparison with any measurement.

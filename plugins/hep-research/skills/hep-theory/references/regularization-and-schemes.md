# Regularization, renormalization schemes and running masses

Purpose: make the regularization scheme, the renormalization scheme of every mass and coupling, and the loop order
of every scheme conversion travel with a loop-level result. Statements are quoted from sources opened on 2026-10-13
(list at the end); a statement without one is marked `unverified`. The loop-level (running-mass) theory profile in
`<plugin root>/profiles/registry.json` applies the running-mass part of this file to one observable.

## Dimensional schemes

- d = 4 - 2 epsilon (Eq. (2.1)). CDR and HV are two flavours of dimensional regularization: they regularize
  algebraic objects in d dimensions; in CDR all vector fields are regularized, in HV only the singular ones (those in
  1PI diagrams or soft and collinear in the initial or final state). FDH and DRED are two flavours of dimensional
  reduction: they work in d_s = d + n_epsilon dimensions, usually d_s = 4; in DRED all vector fields are regularized,
  in FDH only singular ones (Gnendiger et al., "To d, or not to d", arXiv:1705.01827v2, Sec. 2.1, Eqs. (2.1)-(2.4)
  and Table 1, p. 5, read 2026-10-13). Table 1 gives the metric tensor per scheme: singular vector fields g[d] (CDR,
  HV) or g[d_s] (FDH, DRED); regular ones g[d] (CDR), g[4] (HV, FDH), g[d_s] (DRED).
- In FDH and DRED the n_epsilon-dimensional components are "epsilon-scalars" with their own "evanescent couplings"
  (same paper, Eqs. (2.7)-(2.8), read 2026-10-13); renormalizing them is part of the scheme.
- gamma_5: in chiral theories the consistency statements of Sec. 2.4 "rely on the use of a non-anticommuting gamma_5
  as defined e.g. in Refs. [2, 16]" (Breitenlohner-Maison); in QCD non-Abelian gauge invariance is preserved
  (arXiv:1705.01827v2, Sec. 2.4, p. 13, read 2026-10-13). An anticommuting gamma_5 in d dimensions is a choice that
  must be stated and justified for the trace structures at hand (`unverified`: no opened source quoted for this
  sentence).
- Results in different schemes differ by finite, scheme-dependent terms; a scheme conversion is a stated calculation,
  not a relabelling (`unverified`: general statement, not quoted).

## Couplings and their running

- PDG QCD convention: mu_R^2 d alpha_s / d mu_R^2 = beta(alpha_s) = -(b_0 alpha_s^2 + b_1 alpha_s^3 + b_2 alpha_s^4 +
  ...) with b_0 = (33 - 2 n_f) / (12 pi), b_1 = (153 - 19 n_f) / (24 pi^2), b_2 = (2857 - 5033/9 n_f + 325/27 n_f^2) /
  (128 pi^3) (PDG 2026 "9. Quantum Chromodynamics", revised August 2025, Eq. (9.3), read 2026-10-13; b_2 onwards in
  MS-bar). The expansion is in alpha_s itself; the b_1 line of the PDF text was garbled in extraction and rebuilt.
- In a_s = alpha_s / (4 pi): d a_s / d ln mu^2 = -beta_0 a_s^2 - beta_1 a_s^3 - beta_2 a_s^4 - beta_3 a_s^5 with
  beta_0 = 11 - 2/3 n_f, beta_1 = 102 - 38/3 n_f, beta_2 = 2857/2 - 5033/18 n_f + 325/54 n_f^2 and beta_3 given there
  (van Ritbergen, Vermaseren, Larin, arXiv:hep-ph/9701390, Eqs. (4), (11), read 2026-10-13). Dividing beta_i by
  4^(i+1) gives the a_s = alpha_s / pi normalization (arithmetic, checked in the running-mass theory profile).
- State the normalization (alpha_s, alpha_s / pi or alpha_s / (4 pi)), n_f, the loop order of the running, and the
  matching at flavour thresholds (`unverified` for matching: no opened source quoted).

## Masses: MS-bar and pole

- Running mass: mu^2 d m(mu) / d mu^2 = -gamma(alpha_s(mu)) m(mu), gamma = sum_(r>=1) gamma_r (alpha_s / (4 pi))^r,
  with gamma_1 = 4, gamma_2 = 202/3 - 20 N_L / 9, gamma_3 and gamma_4 given there, "known to four-loop order"
  (PDG 2026 "60. Quark Masses", revised August 2023, Eqs. (60.2)-(60.3), p. 2, read 2026-10-13). Chetyrkin writes the
  same in a_s = alpha_s / pi as -m sum_(i>=0) gamma_i a_s^(i+1) with gamma_0 = 1, gamma_1 = (202/3 - 20/9 n_f) / 16
  (arXiv:hep-ph/9703278, Eqs. (1), (7)-(9), read 2026-10-13): gamma_(r-1)(Chetyrkin) = gamma_r(PDG) / 4^r.
- Pole vs MS-bar: m_Q = mbar_Q(mbar_Q) {1 + 4 alpha_s / (3 pi) + [-1.0414 sum_q (1 - 4/3 mbar_q / mbar_Q) + 13.4434]
  (alpha_s / pi)^2 + [0.6527 N_L^2 - 26.655 N_L + 190.595] (alpha_s / pi)^3}, "known to three loops" (PDG 2026 Quark
  Masses, Sec. 60.6.3, Eq. (60.25), p. 17, read 2026-10-13); for the b quark the series reads m_b = mbar_b(mbar_b)
  [1 + 0.10 + 0.05 + 0.03] (Eq. (60.26)). There is "a renormalon in the pole mass" and "the pole mass cannot be
  defined outside of perturbation theory" (same section, read 2026-10-13).
- A conversion states the loop order used, alpha_s at which scale, N_L and the light-quark mass treatment; the
  slowly convergent pole series is a reason to quote short-distance masses (`unverified` as a recommendation; the
  PDG text only warns about the pole mass).
- When a running mass must be used: in a process whose natural scale is far from the mass, logarithms of mu / m
  appear at every order; evaluating m(mu) at the process scale resums them. In H -> q qbar the on-shell form has
  log(m_q^2 / M_H^2) at O(alpha_s) (Djouadi, arXiv:hep-ph/0503172, Eq. (2.9), Sec. 2.1.2, read 2026-10-13), and the
  running-mass form with mbar_q(M_H) and alpha_s(M_H) absorbs it (Eqs. (2.10)-(2.11), read 2026-10-13).

## Infrared and collinear safety

- Real and virtual divergences cancel "only if the observable O satisfies the property of infrared and collinear
  safety", i.e. O_(n+1) -> O_n when a momentum p_s -> 0 or when p_a || p_b (replaced by p_a + p_b) (PDG 2026 QCD,
  Sec. 9.2.3, Eq. (9.19), read 2026-10-13). Check it for every observable before a fixed-order prediction: apply a
  soft and a collinear splitting to an event and confirm the observable does not change.

## Checks to run and list

- The same quantity in two schemes differs only by the stated conversion terms at the stated order.
- mu-independence of a physical prediction order by order: d/d ln mu^2 of the truncated series is of the next order
  (exact-arithmetic check in the running-mass theory profile).
- The normalization of beta and gamma coefficients against a second source (done above for PDG vs van Ritbergen et
  al. and PDG vs Chetyrkin).
- Infrared and collinear safety of the observable.

## What this file cannot claim

No loop integral is computed here; no scheme conversion beyond the quoted orders; no statement on four-loop
pole-MS-bar terms (not read); electroweak schemes (alpha(0), alpha(m_Z), G_mu) are not covered; lattice inputs are
outside v1.

## Deliverables

Regularization scheme and gamma_5 treatment; renormalization scheme of each mass and coupling; normalization of beta
and gamma; n_f and thresholds; conversion formulas with loop order and source; scale choices; the IRC-safety check;
the derivation status.

## Sources read (all on 2026-10-13)

- C. Gnendiger et al., "To d, or not to d: Recent developments and comparisons of regularization schemes",
  arXiv:1705.01827v2; Secs. 2.1, 2.4, 3.4, 6.5, Table 1.
- PDG 2026, "60. Quark Masses", revised August 2023 by R.M. Barnett, L.P. Lellouch and A.V. Manohar,
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-quark-masses.pdf; Eqs. (60.2)-(60.3), Sec. 60.6.3, Eqs. (60.25)-(60.26).
- PDG 2026, "9. Quantum Chromodynamics", revised August 2025 by J. Huston, K. Rabbertz and G. Zanderighi,
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-qcd.pdf; Eqs. (9.3), (9.6), (9.19), Sec. 9.1, 9.2.3.
- T. van Ritbergen, J.A.M. Vermaseren, S.A. Larin, arXiv:hep-ph/9701390; Eqs. (4), (8), (11).
- K.G. Chetyrkin, "Quark mass anomalous dimension to O(alpha_s^4)", arXiv:hep-ph/9703278; Eqs. (1), (4)-(9).
- A. Djouadi, "The anatomy of electroweak symmetry breaking I", arXiv:hep-ph/0503172; Sec. 2.1.2, Eqs. (2.9)-(2.12).

<a id="naming-n13"></a>
### Naming: theory parameters and scheme labels (N13)
- **Extractor:** `extract_names.py --surface N13` (hep-theory; inputs: theory-spec parameters and the scheme labels of its conventions and scales, prediction parameter points)
- **Entity kinds and level floors:** generated from `contracts/naming/surfaces.json`, not restated by hand:

<!-- naming-kinds:N13: generated from contracts/naming/surfaces.json by contracts/naming_registry.py sections; do not edit -->

| Kind | Level floor | Format | Rename policy |
|---|---|---|---|
| `parameter` | C2 | — | matrix |
| `scheme_label` | C2 | — | matrix |

<!-- /naming-kinds:N13 -->

- **The name must say:** the parameter with its scheme and unit (`m_top_msbar_gev`, `alpha_s_mz`); a scheme label is the standard name of the scheme (`MSbar`, `on-shell`)
- **Rename policy:** matrix
- **Rules:** see the registry for surface N13 (`naming.common.*`, `naming.n13.*`, `naming.cross.*`)
- **Good / bad:** `alpha_s_mz`, `m_top_pole_gev` / `p1`, `param_new`

Procedure, levels and report: [semantic naming charter](../../hep-computing/references/semantic-naming.md).

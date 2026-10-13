# Selection rules: is a process allowed?

Purpose: answer "is this process (or diagram) allowed?" by listing the rules checked, the assumptions each rule needs
and a known way it is evaded, instead of a bare yes or no. Statements below are quoted from sources opened on
2026-10-13 (list at the end); a statement without one is marked `unverified`.

## How to answer

1. Write the process with every particle's quantum numbers taken from a cited table (charge, baryon and lepton
   number, J^PC, isospin, G-parity, strangeness and other flavours), not from memory.
2. For each interaction that could mediate it (strong, electromagnetic, weak), list the quantities that interaction
   conserves and check each one. Name the rule that forbids the process, or say that none was found.
3. For each forbidding rule, state its assumptions (on-shell particles, Abelian theory, exact symmetry, massless
   leptons, ...) and check whether the process at hand meets them; a rule whose assumption fails is evaded, not
   violated.
4. Report the answer with a derivation status from the core vocabulary: a rule applied within its stated assumptions
   is usually `analytic-derivation` (when the argument is written out) or `heuristic-argument`; a "forbidden" that
   rests on an experimental limit is `empirical-observation`. "Forbidden" means zero to all orders only when the rule
   is exact in the theory; "suppressed" is not "forbidden".

## Conserved quantities by interaction

- "Charge conjugation (C), parity (P) and time reversal (T) are empirically exact symmetries of the electromagnetic
  (QED) and strong (QCD) interactions, but they are violated by the weak forces"; C and P are maximally violated in
  the W couplings; CP is violated through the single phase of the CKM matrix with three generations; CPT is exact in
  any local Lorentz-invariant quantum field theory (PDG 2026, "Tests of Conservation Laws", revised October 2025 by
  A. Pich and M. Ramsey-Musolf, p. 1, read 2026-10-13).
- Charge conservation is "deeply rooted" in gauge invariance and fermion number in Lorentz symmetry; other number
  conservation laws (lepton, baryon, flavour) "appear to be accidental symmetries of the SM Lagrangian" (same review,
  intro, read 2026-10-13).
- Isospin conserved by the strong interaction (broken by quark masses and electromagnetism), strangeness and other
  flavours conserved by strong and electromagnetic but not weak interactions: `unverified` (the opened PDG review
  does not state them; cite a table or textbook before using them as a rule).
- G-parity: G = (-1)^(I+l+s) for mesons made of a quark and its own antiquark and for the charged u dbar, d ubar
  states (PDG 2026 "15. Quark Model", Sec. 15.3, p. 3, read 2026-10-13; also (-1)^(L+S+I) in "8. Naming Scheme for
  Hadrons", p. 2). "G-parity is conserved in strong interactions. For mesons decaying into n_pi pions we have the
  relation G = (-1)^I C = (-1)^(L+S+I) = (-1)^(n_pi)" (E. Klempt, arXiv:hep-ex/0101031, Sec. 2.1.4, read 2026-10-13;
  cite the equation, the section heading there has a typo).

## Named rules, their assumptions and how they are evaded

- **Landau-Yang.** "A massive vector (i.e. spin 1) particle cannot decay into two on-shell massless photons"; the
  proofs use "only Lorentz invariance, gauge invariance (in the form of transversality of photon polarization
  vectors) and the Bose symmetry of the photons" (Cacciari, Del Debbio, Espinosa, Polosa, Testa,
  arXiv:1509.07853v2, Sec. I, p. 1, read 2026-10-13). It "assumes the massive spin-1 state to be on-shell" (Artoisenet
  et al., arXiv:1306.6464v3, App. A, p. 27, read 2026-10-13). Evasions: an off-shell vector (gg -> Z* -> gamma gamma,
  same App. A, Eqs. (A.6)-(A.9)); a colour-octet vector into two on-shell gluons in a non-Abelian theory, where the
  tree-level zero comes from a cancellation and "one cannot conclude that the amplitude vanishes to all orders"
  (Cacciari et al., abstract and Sec. VI, read 2026-10-13). The original papers (Landau 1948; Yang, Phys. Rev. 77
  (1950) 242) were not read beyond Yang's abstract.
- **Furry's theorem and C.** A closed fermion loop with an odd number of photon vertices vanishes, because under
  charge conjugation the n-photon amplitude picks up (-1)^n (`unverified`: read only in the tertiary Wikipedia
  article "Furry's theorem" on 2026-10-13, which cites Peskin and Schroeder ch. 10 and Weinberg vol. 1 ch. 10, not
  opened). The same article lists where it fails (background charge density, chemical potential, chiral anomaly,
  non-Abelian colour factors); treat these as `unverified`. Consequence for pi0 -> 3 gamma: C(pi0) = +1 and three
  photons have C = -1, so the decay is C-violating; the experimental limit Br(pi0 -> 3 gamma) < 3.1 x 10^-8 is quoted
  as a test of C in electromagnetic interactions (PDG 2026 "Tests of Conservation Laws", p. 1, read 2026-10-13).
  The C-parity assignments in the previous sentence are `unverified` (not from an opened table).
- **Helicity suppression.** Gamma(P -> l nu) = G_F^2 f_P^2 m_l^2 M_P (1 - m_l^2 / M_P^2)^2 |V_q1q2|^2 / (8 pi); "in
  the m_l = 0 limit, the decay is forbidden ... This helicity suppression is the origin of the m_l^2 factor" (PDG 2026
  "71. Leptonic Decays of Charged Pseudoscalar Mesons", Eq. (71.1), Sec. 71.1, pp. 1-2, read 2026-10-13). The ratio
  R_e/mu^(0) = (m_e^2 / m_mu^2) ((m_P^2 - m_e^2) / (m_P^2 - m_mu^2))^2, corrected by radiative terms
  (Cirigliano and Rosell, arXiv:0707.3439v1, Eqs. (1)-(2), read 2026-10-13); it is helicity-suppressed "due to the
  V - A structure of charged current couplings" (p. 1). The rule assumes V - A couplings: a new scalar or
  pseudoscalar coupling lifts it (`unverified`: inferred, no opened source).

## What this file cannot claim

It is not a table of quantum numbers (take them from the PDG listings and cite them); it does not decide whether a
rare allowed process is observable; a symmetry argument does not replace a calculation when the rule's assumptions
fail. Anomalies, non-perturbative effects and beyond-SM couplings are named only where a source above says so.

## Deliverables

The process with its quantum numbers and their source, the interactions considered, each rule checked with its
assumptions and whether the process meets them, the forbidding rule (or "none found"), known evasions, the answer
("allowed", "forbidden by X under assumptions Y", "suppressed by Z") and its derivation status.

## Sources read (all on 2026-10-13)

- PDG 2026, "Tests of Conservation Laws", revised October 2025 by A. Pich and M. Ramsey-Musolf,
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-conservation-laws.pdf; p. 1 and intro.
- PDG 2026, "15. Quark Model", revised August 2025 by C. Amsler, V. Crede and T. DeGrand,
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-quark-model.pdf; Sec. 15.3, p. 3.
- PDG 2026, "8. Naming Scheme for Hadrons", https://pdg.lbl.gov/2026/reviews/rpp2026-rev-naming-scheme-hadrons.pdf; p. 2.
- PDG 2026, "71. Leptonic Decays of Charged Pseudoscalar Mesons", updated August 2025 by R.A. Briere,
  https://pdg.lbl.gov/2026/reviews/rpp2026-rev-pseudoscalar-meson-decay-cons.pdf; Sec. 71.1, Eq. (71.1).
- M. Cacciari, L. Del Debbio, J.R. Espinosa, A.D. Polosa, M. Testa, arXiv:1509.07853v2; abstract, Secs. I and VI.
- P. Artoisenet et al., "A framework for Higgs characterisation", arXiv:1306.6464v3; Sec. 2 and App. A.
- V. Cirigliano and I. Rosell, "The Standard Model prediction for R_e/mu^(pi,K)", arXiv:0707.3439v1; Eqs. (1)-(2).
- E. Klempt, PSI Zuoz lectures 2000, arXiv:hep-ex/0101031; Sec. 2.1.4.
- C.N. Yang, Phys. Rev. 77 (1950) 242: abstract page only.
- Wikipedia, "Furry's theorem" (tertiary; statements taken from it are marked `unverified`).

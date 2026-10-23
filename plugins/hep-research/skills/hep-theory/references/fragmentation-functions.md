# Fragmentation functions

Purpose: definitions, sum rule, flavour assumptions and set rules for collinear and transverse-momentum dependent
fragmentation functions (FFs), as used in SIDIS, e+e- and pp predictions. Entry page:
[hadron structure](hadron-structure-essentials.md); SIDIS and TMDs in [SIDIS and TMDs](sidis-and-tmd.md); set handling
in [PDFs](pdfs-and-lhapdf.md).

Status: guidance (Th18), sources read in full text on 2026-10-23 (see "Sources read"). The FF momentum sum rule is
checked numerically by `sum_rules.py` (`ff-momentum`) on tabulated FFs.

## Definitions and sum rule

D_i^h(z, mu^2) (i = q, qbar, g) measures the production of hadron h with momentum fraction z of the parton; mu is the
factorization scale (PDG 2026 "Fragmentation Functions", Sec. 19.1). Momentum conservation gives, separately for each
parton flavour i, the sum over all hadrons (their Eq. 19.3):

```
sum_h int_0^1 dz z D_i^h(z, mu^2) = 1
```

A set for one hadron species cannot satisfy it alone; a sum-rule check needs the full list of hadrons, or is a bound
(the sum over the hadrons included must stay below 1). The FFs in e+e- -> h X, l p -> l' h X and pp -> h X are the same
functions (universality within collinear factorization; their Sec. 19.1); e+e- data have little sensitivity to D_g and
none to the charge asymmetries D_q - D_qbar; D_g is best constrained in pp and D_q - D_qbar in ep scattering
(their Sec. 19.1).

## Flavour assumptions

Relations between FFs (favoured and unfavoured, charge conjugation D_q^{h+} = D_qbar^{h-}, isospin between pi+ and pi-
or between flavours) are assumptions of a set or of a calculation: list them in `assumptions`. A typical
parametrization at the initial scale is N x^alpha (1 - x)^beta [1 + gamma (1 - x)^delta] per parton (their Eq. 19.12);
the choice of form biases the result, which neural-network sets largely avoid (their Sec. 19.5).

## Sets

FF sets exist for pions, kaons, protons, neutrons, eta, Lambda and charged hadrons, mostly at NLO; NNLO sets so far use
e+e- data only (their Sec. 19.5). Differences between sets are visible for the gluon over the full range and for quarks
at large z, and larger for kaons and protons (their Sec. 19.5, Fig. 19.7): they are alternative-model objects, not an
uncertainty band. The set rules of [PDFs](pdfs-and-lhapdf.md) apply: name the set, its order, its error type and CL,
and combine members by the set's own rule (`pdf_uncertainty.py`).

## Spin-dependent and TMD fragmentation functions

Helicity FFs Delta D_i^h = D_{i+}^{h+} - D_{i+}^{h-}, the signs being helicities of parton and hadron
(their Eq. 19.20), transversity FFs, and at leading twist eight
TMD FFs per quark and antiquark flavour, which reduce to the collinear unpolarized, helicity and transversity FFs on
integration over k_T (their Sec. 19.9). The Collins function H_1^perp and its notations (H_1^perp or Delta^N D) follow
the Trento conventions (Bacchetta, D'Alesio, Diehl, Miller, Eqs. 8-10); state which is used. In a Gaussian ansatz the
FF width is the hadron transverse momentum relative to the quark, p_perp (Anselmino et al., Eq. 35; see
[SIDIS and TMDs](sidis-and-tmd.md)).

## Sources read (full text, 2026-10-23)

- PDG, "19. Fragmentation Functions in e+e-, ep, and pp Collisions", revised August 2023 by O. Biebel, D. de Florian,
  D. Milstead, W. Vogelsang, in the 2026 Review (https://pdg.lbl.gov/2026/reviews/rpp2026-rev-frag-functions.pdf):
  Secs. 19.1, 19.5, 19.9, Eqs. 19.3, 19.12, 19.20.
- A. Bacchetta, U. D'Alesio, M. Diehl, C.A. Miller, arXiv:hep-ph/0410050v2 (Phys. Rev. D 70 (2004) 117504): Eqs. 8-10.
- M. Anselmino et al., arXiv:hep-ph/0501196v2 (Phys. Rev. D 71 (2005) 074006): Eqs. 34-39.

Not verified and therefore not used: the original papers of individual FF sets (read the set's paper for its
conventions); timelike splitting functions beyond what the PDG review states.

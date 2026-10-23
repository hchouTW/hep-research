# Nuclear targets: per-nucleon conventions, isospin, nuclear PDFs and nuclear ratios

Purpose: the conventions and rules for predictions on nuclear targets in lepton-nucleus, neutrino-nucleus,
proton-nucleus and pion-nucleus collisions (cold nuclear matter): per-nucleon versus per-nucleus quantities, the
bound-nucleon combination, nuclear PDF sets and their baselines, nuclear ratios and their uncertainties, and the
nuclear effects that are not nPDFs. The quark-gluon plasma and nucleus-nucleus collisions stay outside v1
(`heavy-ions`). Entry page: [hadron structure](hadron-structure-essentials.md); DIS on nuclei in
[DIS structure functions](dis-structure-functions.md); Drell-Yan in [Drell-Yan](drell-yan.md); set rules in
[PDFs](pdfs-and-lhapdf.md).

Status: guidance and one tool (Th16), sources read in full text on 2026-10-23 (see "Sources read"). The executable
piece is `nuclear_combination.py`; mechanism models of nuclear effects are rules only.

## Contents

- Required fields
- Per-nucleon conventions and the bound-nucleon combination
- Nuclear PDF sets
- Nuclear ratios
- Nuclear effects by x region
- Effects that are not nPDFs
- Script
- Sources read

## Required fields

`target_normalization` (per nucleon or per nucleus, and the nucleon mass convention: free-nucleon average, atomic mass
unit or M_A/A), Z and A, the nPDF set with its proton baseline, error type and confidence level, and for data the
isoscalar or Coulomb corrections already applied. A missing field is a refusal.

## Per-nucleon conventions and the bound-nucleon combination

- Per-nucleon x is defined with the nucleon mass M_N, x_N = Q^2 / (2 M_N nu), and per-nucleus x with M_A; then
  x_A = x_N M_N / M_A (derived here from the definition of x, PDG Eq. 18.1 conventions). With M_A ~ A M_N, the
  convention Klasen and Paukkunen use (Sec. 2.1), x_N runs up to about A: values x_N > 1 are kinematically allowed,
  but nPDF sets usually assume f^A(x_N) = 0 for x_N > 1 (their Sec. 2.1), so a set has no support there.
- Bound-nucleon combination with isospin symmetry (u^{n/A} = d^{p/A}, d^{n/A} = u^{p/A}, likewise for antiquarks):

  ```
  f_i^A(x, Q^2) = (Z/A) f_i^{p/A}(x, Q^2) + ((A - Z)/A) f_i^{n/A}(x, Q^2)
  ```

  (Klasen and Paukkunen, Eqs. 11-12; PDG 2026, the definition of R_u^Pb in the text above Fig. 18.5). For an
  isoscalar nucleus (Z = A/2) the up and down distributions are equal (their Sec. 4.1). Per nucleus multiplies by A.
  Know which grid you hold: some sets ship both bound-proton grids f^{p/A} and average-nucleon grids f^A that are
  already combined (nNNPDF3.0 Sec. 7.1; nCTEQ15 App. B); combining an average-nucleon grid again applies isospin
  twice (`nuclear_combination.py combine` refuses it).
- Isoscalar corrections applied to data: many early neutral-current DIS experiments corrected heavy-nucleus data to
  Z = N = A/2 with a factor beta built from a parametrized F_2^n/F_2^p (Klasen and Paukkunen, Sec. 4.1, Eq. 37). Such data were fitted by setting Z = N = A/2 (still so in nNNPDF3.0, their Sec. 4.1): comparing with
  isoscalar-corrected data needs the prediction at Z = A/2, or beta applied to it, not the physical Z. This is a
  data-side transformation, declared as an `apply-correction` step in `contracts/comparison/gate.py` (the gate has no
  specific isoscalar entry); a fit either applies beta to its predictions or removes it from the data, never both.
- The deuteron is not a free proton plus neutron at large x (Fermi motion, binding, off-shell effects) and shows some
  shadowing at small x; Klasen and Paukkunen (Sec. 4.2) put these effects at a few percent in the available DIS data
  and below 1% in Drell-Yan data. A "free neutron" extracted from deuteron data is model dependent and is labelled so.
  If the proton baseline was fitted to deuteron data without nuclear corrections, adding a deuteron correction double
  counts unless quantified (their Sec. 4.2).

## Nuclear PDF sets

nPDFs are often written as nuclear modifications of a proton set, f_i^{p/A} = R_i^A f_i^p (PDG Eq. 18.30; EPPS21
still does, its Eq. 1); other analyses parametrize the nuclear PDFs directly so that they become the proton PDFs at
A = 1 (PDG Sec. 18.3). Rules:

- The proton baseline is part of the set. Combining a set's nuclear modifications with another proton set is refused.
- Error type, tolerance and confidence level come from the set's paper and LHAPDF `.info` file and are used as given;
  `pdf_uncertainty.py` applies the rule. As read on 2026-10-23:

  | Set | Error type | Uncertainty definition | Proton baseline |
  |---|---|---|---|
  | EPPS21 | Hessian, asymmetric | Delta chi^2 ~ 33 from a 90% criterion for 24 nuclear parameters (Sec. 4.2); 24 nuclear + 29 proton directions = 106 error sets (Sec. 4.3) | CT18A NLO (Sec. 2), its errors propagated |
  | nNNPDF3.0 | Monte Carlo replicas | median as best fit and the central 68% interval of the replicas as uncertainty (Sec. 7.2); 200 replicas in the released set after reweighting and unweighting (Secs. 3.4, 7.1; variants differ) | a variant of the NNPDF3.1 NLO fit (NNPDF4.0 proton dataset, deuteron data removed, reweighted with D-meson data) as the A = 1 boundary condition; each nuclear replica used a random proton replica (Sec. 3.1, Eq. 3.8; Sec. 3.2); replicas are correlated across A including A = 1 (Sec. 7.2) |
  | nCTEQ15 | Hessian | Delta chi^2 = 35 from a 90% CL criterion (Sec. II.C, App. A) | free-proton coefficients fixed to a fit close to CTEQ6.1 (Sec. II.A) |
  | nCTEQ15HQ | Hessian | 19 nuclear parameters (Sec. II.A); the paper states no Delta chi^2 or CL: read the set's `.info` | not stated in the paper: read the `.info` |

  PDG Fig. 18.5 shows all three sets at 90% CL, a different choice from a set's own 68% replica interval; state which.
  A Hessian set quoted at 90% is not rescaled silently (`pdf_uncertainty.py --rescale-to-68`, Gaussian assumption
  stated). Whether proton-baseline and nuclear uncertainties are separate follows each set's documentation (EPPS21
  separates them, nNNPDF3.0 folds the proton replicas in).
- Nuclei outside a fit are obtained by the set's A dependence (for example the nCTEQ coefficients
  c_k(A) = p_k + a_k (1 - A^{-b_k}), nCTEQ15HQ Eq. 3): label such a prediction as interpolated in A.
- Pairing with the proton baseline. EPPS21 error sets S1-S24 (48 members) use the central CT18A proton and S25-S53
  use CT18A member i - 24 (EPPS21 Eq. 40): a proton denominator for a member-by-member ratio has the central CT18A
  repeated for the central and the first 48 members, then the CT18A members, not CT18A's own member list. A replica
  set is paired only with its own A = 1 grid (as a nuclear denominator of the same set), never with an external proton
  set.
- Differences between nPDF sets (gluon and strange in particular) are alternative-model objects, not an uncertainty
  band; PDG Fig. 18.5 compares the three sets.

## Nuclear ratios

A ratio R = sigma_A / sigma_D (or / sigma_p), per nucleon, is computed member by member and then combined by the set's
rule: the numerator and the denominator move together along each eigenvector or replica, and most of their
uncertainty cancels. Dividing the numerator and denominator error bands loses that correlation and is not offered.
Member-by-member pairing needs one set for both (or a proton denominator that is the set's own baseline with matched
members). For Drell-Yan, sigma(pA)/sigma(pD) for an isoscalar nucleus at x_1 >> x_2 approaches ubar^A(x_2)/ubar^D(x_2)
(Klasen and Paukkunen, Eq. 41, Sec. 4.3): it probes target antiquarks at x_2 ~ 0.03-0.3, and the combined DIS and DY
data showed a less clear antishadowing in sea quarks than in valence quarks.

## Nuclear effects by x region

Descriptive only; the boundaries are those of the cited review and are never hard-coded in a script:

| Region (Klasen and Paukkunen, Sec. 1) | Effect in F_2^A / F_2^D | Status |
|---|---|---|
| x <~ 0.05 | shadowing (depletion) | `empirical-observation`; mechanism models are alternatives (the small-x and saturation module, planned) |
| 0.05 <~ x <~ 0.3 | antishadowing (enhancement) | `empirical-observation` |
| 0.3 <~ x <~ 0.7 | EMC effect (depletion) | `empirical-observation`; binding, off-shell and short-range-correlation explanations are models |
| x >~ 0.7 | Fermi motion (enhancement) | a convolution or rescaling model (their Sec. 4.2, Eq. 39); sets usually set f^A = 0 above x_N = 1 |

## Effects that are not nPDFs

- Initial-state parton energy loss and transverse-momentum broadening (which changes q_T in Drell-Yan) are
  alternative-model objects, not nPDF uncertainty; no model is implemented or recommended here (no source read).
- Drell-Yan leptons do not interact strongly, so there is no final-state absorption; quarkonium production and
  absorption are outside v1 (`quarkonium-production`).
- Coulomb corrections for electrons on heavy nuclei sit at the boundary of data and theory; the comparison gate states
  who applies them.
- Polarized nuclear targets: effective nucleon polarizations in 3He and the deuteron D-state probability are sourced
  inputs of the polarized-DIS module (planned).

## Script

`nuclear_combination.py`: `combine` (bound-proton x f values to per-nucleon or per-nucleus nuclear values by
isospin), `ratio` (member-by-member ratio, then the set's rule through `pdf_uncertainty.py`, with a headline that follows the
set's prescription; refuses (exit 1) a baseline mismatch, two different sets, mixed error types or confidence
levels, unpaired proton members and a replica set over an external proton set),
`convert` (per nucleon <-> per nucleus for cross sections and structure functions; x with the caller's masses).
Tests: `tests/skills/hep_theory/test_nuclear_combination.py` (free-proton limit, isoscalar symmetry, the factor A, a
correlated toy where member-by-member and divided bands differ, refusals). `structure_functions_lo.py --Z --A` uses
the same per-nucleon combination. Software checks only.

## Sources read (full text, 2026-10-23)

- PDG, "18. Structure Functions" (2026; see [DIS structure functions](dis-structure-functions.md)): Sec. 18.3,
  "Nuclear PDFs", Eq. (18.30) and Fig. 18.5 with its R_u^Pb definition.
- M. Klasen, H. Paukkunen, arXiv:2311.00450 (Ann. Rev. Nucl. Part. Sci. 74 (2024) 49): Secs. 1, 2.1, 3, 4.1-4.3, Eqs. 11, 12, 37, 39, 40, 41.
- K.J. Eskola, P. Paakkinen, H. Paukkunen, C.A. Salgado, arXiv:2112.12462v2 (EPPS21, Eur. Phys. J. C 82 (2022) 413):
  Secs. 2, 4.2, 4.3, Eqs. 1, 40.
- R. Abdul Khalek et al., arXiv:2201.12363v2 (nNNPDF3.0, Eur. Phys. J. C 82 (2022) 507): Secs. 3.1-3.4, 7.1-7.2, Eq. 3.8.
- K. Kovarik et al., arXiv:1509.00792 (nCTEQ15, Phys. Rev. D 93 (2016) 085037): Secs. II.A, II.C, Apps. A-B.
- P. Duwentaster et al., arXiv:2204.09982 (nCTEQ15HQ, Phys. Rev. D 105 (2022) 114043): Sec. II, Eqs. 2-3.

Not verified and therefore not used: energy-loss and broadening models; mechanism models of shadowing and the EMC
effect; Coulomb-correction formulas; the LHAPDF `.info` files of the sets (read them for the set you use).

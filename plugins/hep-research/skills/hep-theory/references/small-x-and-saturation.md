# Small-x physics and saturation: dipole picture, models, evolution conventions

Purpose: frameworks, inputs and validity for small-x predictions in lepton-proton and lepton-nucleus DIS: fixed-order
and small-x resummed DGLAP, BFKL, the dipole picture with saturation models, and the BK/JIMWLK evolution conventions.
Entry page: [hadron structure](hadron-structure-essentials.md); inclusive structure functions in
[DIS structure functions](dis-structure-functions.md); nuclear shadowing as an nPDF effect in
[nuclear targets](nuclear-parton-effects.md).

Status: guidance and one tool (Th19), sources read in full text on 2026-10-23 (see "Sources read"). The executable
piece is `dipole_lo.py` (LO photon wave functions and the GBW dipole model); evolution equations are rules only.

## Contents

- Required fields
- Frameworks
- Dipole factorization
- The GBW model
- Evolution: BK and JIMWLK (rules)
- Nuclei
- Status labels
- Script
- Sources read

## Required fields

The framework (fixed-order DGLAP, small-x resummed DGLAP, BFKL LL/NLL, dipole model, BK, JIMWLK); for a dipole model
its name and the source of its parameters (in `parameters`; parameters from different fits are never mixed); the x
variable the parameters were fitted with (Bjorken x or the mass-modified x~); the quark masses (model parameters in the
dipole picture); the impact-parameter treatment (b-independent or b-dependent); for BK the initial condition, the
running-coupling prescription, LO or NLO and any collinear improvement. A missing field is a refusal.

## Frameworks

PDG 2026 (Structure Functions, Sec. 18.2.2) separates leading-ln(1/x) resummation (BFKL, power-like growth x^-omega),
its large and negative NLL corrections, combined collinear and small-x resummations used in phenomenology, and
non-linear saturation effects at very small x; it notes limited indications that small-x resummation is needed below
x ~ 1e-3 at low scales and no convincing evidence of a non-linear regime for Q^2 >~ 2 GeV^2 in inclusive DIS. These are
different frameworks: a BFKL or BK calculation is not a small-x resummed DGLAP fit, and a comparison between them is
between alternative models.

## Dipole factorization

At small x the virtual photon fluctuates into a q qbar dipole of transverse size r and momentum fraction z, which
scatters on the target (Golec-Biernat and Wusthoff, Eqs. 1-6):

```
sigma_T,L(x, Q^2) = int d^2r int_0^1 dz |Psi_T,L(z, r)|^2 sigma_hat(x, r^2)
|Psi_T|^2 = (6 alpha_em / 4 pi^2) sum_f e_f^2 { [z^2 + (1 - z)^2] eps^2 K_1^2(eps r) + m_f^2 K_0^2(eps r) }
|Psi_L|^2 = (6 alpha_em / 4 pi^2) sum_f e_f^2 4 Q^2 z^2 (1 - z)^2 K_0^2(eps r),   eps^2 = z (1 - z) Q^2 + m_f^2
F_2 = F_T + F_L,   F_T,L = Q^2 / (4 pi^2 alpha_em) sigma_T,L
```

K_0 and K_1 are modified Bessel functions; alpha_em cancels in F_T,L. The quark mass regulates photoproduction (their
Sec. 3). In their x definition x = Q^2 / (W^2 + Q^2) (after their Eq. 1); for every flavour, to get the right threshold behaviour and a smooth Q^2 -> 0 limit, they use
x~ = x (Q^2 + 4 m_f^2) / Q^2 (their Eq. 21).

## The GBW model

sigma_hat = sigma_0 g(r_hat^2), r_hat = r / (2 R_0), R_0 = (1/Q_0)(x/x_0)^(lambda/2), Q_0 = 1 GeV, g = 1 - exp(-r_hat^2)
(Eqs. 7-10), i.e. sigma_hat = sigma_0 [1 - exp(-r^2 Q_s^2/4)] with Q_s^2 = Q_0^2 (x_0/x)^lambda: colour transparency
(sigma_hat ~ r^2) at small r and saturation to sigma_0 at large r. sigma_0, x_0 and lambda are fit parameters read
from a source (GBW Table 1 gives a light-flavour and a charm fit with different values; their alternatives g =
ln(1 + r_hat^2) and r_hat^2 ln(1 + 1/r_hat^2), Eqs. 11-12, were disfavoured in their fits). Other models (impact
parameter dependent ones such as that of Kowalski and Teaney, Glauber-Mueller in form; IIM; b-CGC) are plug-ins:
differences between models are alternative-model objects. The fit's x variable and quark masses travel with its
parameters.

## Evolution: BK and JIMWLK (rules)

- BK is the large-N_c limit in which a parent dipole splits into two daughter dipoles (Albacete and Kovchegov, Eqs. 1-2
  and the discussion after them); JIMWLK is the general evolution. Using BK lists the large-N_c (mean-field)
  approximation in `neglected`.
- Running coupling: the two calculations of the running-coupling corrections (Balitsky; Kovchegov and Weigert) differ by
  a subtraction term; with it added back their dipole amplitudes agree (Albacete and Kovchegov, abstract and Sec. 2).
  A "parent dipole" prescription is a simpler alternative. Name the prescription; prescriptions are not equivalent.
- Initial condition (for example McLerran-Venugopalan), LO or NLO kernel and collinear improvements are model choices
  in `parameters`. No evolution code is shipped (software plan).

## Nuclei

Saturation in nuclei (for example Q_s,A^2 growing like A^(1/3)) is a model assumption, not a result; nuclear dipole
cross sections come from Glauber-type or b-dependent models. Small-x shadowing in nPDFs and saturation describe the
same phenomenon in two frameworks: compare them only as alternatives.

## Status labels

The colour glass condensate and BK/JIMWLK: `asymptotic-argument` (high-energy, weak-coupling limit, stated in
`limit`). Dipole models: `heuristic-argument`. Geometric scaling: `empirical-observation`. The validity domain (an upper
bound in x, a Q^2 range) is the user's, in the theory-spec.

## Script

`dipole_lo.py`: sigma_T, sigma_L (GeV^-2 and mb), F_T, F_L, F_2 and Q_s^2 for the GBW model from user-supplied
sigma_0, x_0, lambda, flavours with charges and masses, the x variable and the fit's x variable, the user's x limit and
alpha_em; a convergence report (doubled nodes, doubled r_max). Refuses (exit 1) an x variable different from the fit's
and x above the declared limit; rejects (exit 2) unknown models and missing or non-positive parameters. Tests:
`tests/skills/hep_theory/test_dipole_lo.py` (K_0, K_1 against their integral representation, colour transparency and
saturation of sigma_hat, sigma_L against its analytic colour-transparency limit for m = 0, the mass-modified x as
Eq. 21, positivity, convergence, the alpha_em cancellation in F_2). Software checks only.

## Sources read (full text, 2026-10-23)

- K. Golec-Biernat, M. Wusthoff, arXiv:hep-ph/9807513 (Phys. Rev. D 59 (1998) 014017): Secs. 2-3, Eqs. 1-21,
  Table 1.
- H. Kowalski, D. Teaney, arXiv:hep-ph/0304189 (Phys. Rev. D 68 (2003) 114005): abstract, Sec. II (impact-parameter
  dependence, Glauber-Mueller form).
- J.L. Albacete, Yu.V. Kovchegov, arXiv:0704.0612 (Phys. Rev. D 75 (2007) 125021): abstract, Secs. 1-2, Eqs. 1-2.
- PDG 2026 "Structure Functions" (see [DIS structure functions](dis-structure-functions.md)): Sec. 18.2.2.

Not verified and therefore not used: the original Balitsky and Kovchegov-Weigert papers; BFKL kernels; the IIM and
b-CGC parametrizations; any saturation-scale value for a nucleus.

# Exclusive processes, GPDs and diffractive DIS

Purpose: kinematics, conventions and properties for deeply virtual Compton scattering (DVCS), deeply virtual meson
production (DVMP), timelike Compton scattering (TCS) and diffractive DIS, and the rules for generalized parton
distributions (GPDs). GPD extraction is an ill-posed deconvolution; this page covers kinematics, conventions,
properties and checks, not extraction. Entry page: [hadron structure](hadron-structure-essentials.md); the dipole
picture of diffraction in [small x](small-x-and-saturation.md); azimuthal conventions for SIDIS in
[SIDIS and TMDs](sidis-and-tmd.md).

Status: guidance and one tool (Th20), sources read in full text on 2026-10-23 (see "Sources read"). The executable
pieces are `exclusive_kinematics.py` (t_min, xi, the BMK and Trento azimuths, x_P and beta) and the GPD rules of
`sum_rules.py` (form-factor and Ji sum-rule integrals of a tabulated GPD); amplitudes are rules only.

## Contents

- Required fields
- Kinematics
- Azimuthal conventions
- GPD properties
- Amplitudes and Compton form factors (rules)
- Diffractive DIS
- Scripts
- Sources read

## Required fields

The skewness definition (the exact form with t/Q^2 terms or the leading-power xB/(2 - xB)), `azimuth_convention` (BMK
or Trento), the Compton form factor definitions and normalization, and whether kinematic power corrections (xi^2,
t/Q^2, M^2/Q^2) are included. A missing field is a refusal.

## Kinematics

For e N -> e N gamma with Delta = P' - P (Belitsky, Mueller, Kirchner, Eqs. 3-4 and Eq. 31; epsilon = 2 xB M / Q):

```
xi = xB (1 + Delta^2 / 2Q^2) / (2 - xB + xB Delta^2 / Q^2)           ->  xB / (2 - xB) at leading power
-Delta^2_min = Q^2 [2 (1 - xB)(1 - sqrt(1 + eps^2)) + eps^2] / [4 xB (1 - xB) + eps^2]  ~  M^2 xB^2 / (1 - xB + xB M^2/Q^2)
```

t = Delta^2 must satisfy |t| >= |t_min|. PDG 2026 defines xi = -Delta^+ / (P + P')^+ in light-cone components
(Eq. 18.35); the two definitions agree at leading power. State which is used.

## Azimuthal conventions

BMK (their Sec. 4, text after Eq. 22, Fig. 1): target rest frame, z axis opposite to the virtual photon, the incoming lepton with a
positive x component; phi is the azimuth of the recoiled nucleon. Trento (Eq. 16, written for SIDIS): the azimuth of
the produced particle about q from the lepton plane. For the same event `exclusive_kinematics.py angles` gives both;
with the BMK y axis opposite to the Trento one and the recoiled nucleon and the produced photon back to back in the
plane transverse to q (target at rest), the two are related by phi_Trento = pi - phi_BMK (mod 2 pi) (derived here; the
script computes both and the tests check the relation on constructed events). Asymmetry signs
change with the convention: convert before comparing.

## GPD properties

| Property | Content | Source | Status |
|---|---|---|---|
| Definition | H^q, E^q from the light-cone quark operator between nucleon states, t = Delta^2, xi = -Delta^+/(P + P')^+, -1 <= xi <= 1; H~, E~ with gamma_5; gluon analogues | PDG Eqs. 18.34-18.35 | definition |
| Forward limit | H^q(x, 0, 0) = q(x), H^q(-x, 0, 0) = -qbar(x); H~^q(x, 0, 0) = Delta q(x), H~^q(-x, 0, 0) = +Delta qbar(x); H^g(x, 0, 0) = x g(x), H~^g(x, 0, 0) = x Delta g(x); no relation for E, E~ | PDG Eqs. 18.36-18.37 | `analytic-derivation` |
| Symmetry | H(x, -xi, t) = H(x, xi, t), H real; H_V even and H_S odd in x | PDG Eqs. 18.38-18.40 | `analytic-derivation` |
| Form-factor sum rules | int dx H^q = F_1^q(t), int dx E^q = F_2^q(t), int dx H~^q = G_A^q(t), int dx E~^q = G_P^q(t), independent of xi | Ji, Eq. 18 | `analytic-derivation` |
| Polynomiality | x^n moments are polynomials in xi of order at most n + 1 (in even powers of xi, given the xi -> -xi symmetry) | PDG Sec. 18.6.1 | `analytic-derivation` (Lorentz invariance) |
| Ji sum rule | (1/2) int_{-1}^{1} dx x [H^q + E^q] = J^q(t); J^q(0) is the total angular momentum of quarks and antiquarks of flavour q | PDG Eq. 18.41; Ji, Eqs. 13 and 19 | `analytic-derivation`; state scheme and scale |

The integration runs over x in [-1, 1]; the regions |x| > |xi| (DGLAP-like) and |x| < |xi| (ERBL-like) evolve
differently (PDG Sec. 18.6.1). GPD models (double distributions, others) are alternative-model objects.

## Amplitudes and Compton form factors (rules)

DVCS amplitudes are written with Compton form factors (H, E, H~, E~); the Bethe-Heitler process is exact QED and
interferes with DVCS, so a comparison with data includes Bethe-Heitler and the interference (BMK Secs. 4.1-4.3). The
formulas are not reproduced here (no implementation; software plan). Name the CFF normalization convention and whether
the BMK harmonic expansion or another form is used.

## Diffractive DIS

About 10% of DIS events are diffractive, gamma* p -> X p with a rapidity gap; besides x and Q^2 they need x_P (the
momentum fraction carried across the gap) and t (PDG Sec. 18.5). Collinear factorization holds for diffractive DIS,
F_2^D = sum_a C_2^a (x) f_a^D with the inclusive coefficient functions (PDG Eq. 18.32; proved by Collins, abstract and Sec. I), and Regge factorization f_a^D = f_IP(x_P, t) f_a/IP(z, mu^2) is an additional assumption (PDG Eq. 18.33,
z in [x/x_P, 1]). Diffractive parton densities do not apply directly to hadron-hadron diffraction: factorization fails there
(Collins, Sec. I) and soft rescattering must be accounted for (PDG Sec. 18.5); gap survival is a model. Kinematics (derived here from x_P =
q.(P - P')/q.P and beta = Q^2 / (2 q.(P - P'))): x_P = (Q^2 + M_X^2 - t)/(Q^2 + W^2 - M^2), beta = Q^2/(Q^2 + M_X^2 - t),
beta x_P = x.

## Scripts

- `exclusive_kinematics.py`: `dvcs` (t_min, epsilon, xi in both forms; rejects |t| < |t_min|), `angles` (four-vectors -> t, phi_BMK, phi_Trento and their relation; an off-shell recoil is rejected), `diffractive` (W^2, x_P, beta).
- `sum_rules.py`: `gpd-integral:<F>` (form-factor sum rules) and `gpd-ji` integrate a tabulated GPD over x in [-1, 1].
- Tests: `tests/skills/hep_theory/test_exclusive_kinematics.py` (t_min against four-vector arithmetic, xi forms,
  phi_Trento = pi - phi_BMK on constructed events, beta x_P = x) and `test_sum_rules.py` (GPD toys built from PDG Eq. 18.36 forward limits). Software checks
  only.

## Sources read (full text, 2026-10-23)

- PDG 2026 "Structure Functions" (see [DIS structure functions](dis-structure-functions.md)): Secs. 18.5-18.6.1,
  Eqs. 18.32-18.41.
- A.V. Belitsky, D. Mueller, A. Kirchner, arXiv:hep-ph/0112108 (Nucl. Phys. B 629 (2002) 323): Sec. 2 (Eqs. 3-4), Sec. 4 (Eqs. 22-31, Fig. 1), Secs. 4.1-4.3.
- X. Ji, arXiv:hep-ph/9603249v1 (Phys. Rev. Lett. 78 (1997) 610): Eqs. 13, 17-19.
- J.C. Collins, arXiv:hep-ph/9709499v2 (Phys. Rev. D 57 (1998) 3051; erratum D 61 (2000) 019902): abstract, Sec. I.

Not verified and therefore not used: GPD positivity bounds; the BMK harmonic coefficients and CFF formulas; GPD model
parametrizations; diffractive parton-density fits.

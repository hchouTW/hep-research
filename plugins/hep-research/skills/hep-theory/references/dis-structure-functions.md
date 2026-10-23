# Unpolarized inclusive DIS: structure functions and cross sections

Purpose: the conventions, formulas and required fields for an inclusive deep-inelastic prediction (neutral and charged
current, charged leptons and neutrinos), what the plugin computes at leading order and what it only states as rules.
Kinematic invariants and their identities are in [DIS kinematics](dis-kinematics.md); PDF sets and their uncertainty
in [PDFs](pdfs-and-lhapdf.md); orders and scale envelopes in [higher orders](higher-order-predictions.md). The entry
to the other hadron-structure topics is [hadron structure](hadron-structure-essentials.md).

Status: guidance and one tool (Th14), sources read in full text on 2026-10-23 (see "Sources read"). The executable
pieces are `structure_functions_lo.py` (LO quark-parton model) and `sum_rules.py` (sum-rule integrals); everything
beyond LO is rules only.

## Contents

- Required fields
- Cross sections
- Neutral current: photon, gamma-Z and Z
- Charged current
- Leading order
- Beyond leading order (rules)
- Heavy quarks, target mass, higher twist (rules)
- Sum rules
- Scripts
- Sources read

## Required fields

A DIS prediction's theory-spec carries, besides the core conventions: `target_normalization`, `exchanged_bosons`,
`electroweak_scheme` (with Z or W), `em_coupling`, `structure_function_signs`, `heavy_quark_scheme`,
`target_mass_treatment`; beyond LO also `factorization_scheme` and the core `scales` (mu_R, mu_F). The lepton species,
its charge and its longitudinal polarization P_e are inputs. A missing field is a refusal, not a default.

## Cross sections

PDG 2026, Eq. (18.16), in the limit M^2 / Q^2 -> 0 of Eq. (18.8):

```
d2sigma^i / dx dy = (2 pi alpha^2 / (x y Q^2)) eta^i [ Y_+ F_2^i -/+ Y_- x F_3^i - y^2 F_L^i ],   Y_+/- = 1 +/- (1 - y)^2
F_L = F_2 - 2 x F_1                                                                                 (Eq. 18.17)
```

i = NC or CC. In the x F_3 term the minus sign is for an incoming e+ or antineutrino and the plus sign for an incoming
e- or neutrino (text after Eq. 18.8). This is the `structure_function_signs` convention `pdg`; another source may put
the sign into F_3 itself, so state the convention and its source. The full form, Eq. (18.8), keeps the target-mass
terms (1 - y - x^2 y^2 M^2 / Q^2) F_2 + y^2 x F_1. The Jacobian d2sigma/dx dy = x (s - M^2) d2sigma/dx dQ^2 is
Eq. (18.1), so d2sigma/dx dQ^2 = (2 pi alpha^2 / (x Q^4)) eta^i [ ... ] (derived here). The NC reduced cross section
is the bracket divided by Y_+: sigma_r = F_2 -/+ (Y_- / Y_+) x F_3 - (y^2 / Y_+) F_L.

Units: d2sigma/dx dy in GeV^-2 and d2sigma/dx dQ^2 in GeV^-4; to pb with (hbar c)^2 = 0.389379... GeV^2 mb from
`physical_data.py` (CODATA 2022). The NC normalization scales as alpha^2: alpha(0) and a running alpha(Q^2) give
different predictions, so `em_coupling` names the value and its source.

## Neutral current: photon, gamma-Z and Z

Propagator and coupling ratios to the photon (Eq. 18.4):

```
eta_gamma = 1,   eta_gammaZ = (G_F M_Z^2 / (2 sqrt(2) pi alpha)) (Q^2 / (Q^2 + M_Z^2)),   eta_Z = eta_gammaZ^2
```

For e+- N -> e+- X with lepton helicity lambda (Eqs. 18.11, 18.12; upper sign e+):

```
F_2^NC  = F_2^gamma - (g_V^e +/- lambda g_A^e) eta_gammaZ F_2^gammaZ + (g_V^e2 + g_A^e2 +/- 2 lambda g_V^e g_A^e) eta_Z F_2^Z
xF_3^NC = -(g_A^e +/- lambda g_V^e) eta_gammaZ xF_3^gammaZ + [2 g_V^e g_A^e +/- lambda (g_V^e2 + g_A^e2)] eta_Z xF_3^Z
g_V^e = -1/2 + 2 sin^2 theta_W,   g_A^e = -1/2                                                       (after Eq. 18.3)
```

F_1^NC follows like F_2^NC; eta^NC = 1 for an unpolarized beam. The equations are linear in lambda, so a beam of
longitudinal polarization P_e enters with lambda -> P_e (derived here). With P_e = 0 the x F_3 term changes sign
between e+ and e- through the bracket, and vanishes for photon exchange alone (F_3^gamma = 0). With P_e != 0 the
generalized structure functions themselves depend on charge and polarization through (g_V^e +/- P_e g_A^e) and
(g_A^e +/- P_e g_V^e). The value of sin^2 theta_W, M_Z and G_F belong to one `electroweak_scheme` (on-shell, MS-bar,
G_mu) and are inputs with that label.

## Charged current

Only W exchange (Eq. 18.10). eta^CC = (1 +/- lambda)^2 eta_W for l+- with eta_W = (1/2) (G_F M_W^2 / (4 pi alpha)
Q^2 / (Q^2 + M_W^2))^2, and eta^CC = 4 eta_W for incoming neutrinos (Eqs. 18.4, 18.9). Averaged over helicity, a beam
of polarization P_e has eta^CC = 2 (1 +/- P_e) eta_W (derived here): a fully right-handed e- has no CC cross section.
The normalization is set by G_F and the W propagator, not by the NC prefactor. Whether the CKM matrix is diagonal or
full is a required input; Eq. (18.19) neglects mixing.

## Leading order

Quark-parton model, massless partons, number densities q(x, Q^2) (Eqs. 18.18, 18.19):

```
[F_2^gamma, F_2^gammaZ, F_2^Z] = x sum_q [e_q^2, 2 e_q g_V^q, g_V^q2 + g_A^q2] (q + qbar)
[F_3^gamma, F_3^gammaZ, F_3^Z] = sum_q [0, 2 e_q g_A^q, 2 g_V^q g_A^q] (q - qbar)
g_V^q = +/-1/2 - 2 e_q sin^2 theta_W,  g_A^q = +/-1/2   (+ for u-type, - for d-type)
F_2^{W-} = 2x (u + dbar + sbar + c ...),  F_3^{W-} = 2 (u - dbar - sbar + c ...)       (e- p -> nu X, nubar p -> e+ X)
F^{W+}: d <-> u, s <-> c                                                              (e+ p -> nubar X, nu p -> e- X)
```

2 x F_1 = F_2 (Callan-Gross), so F_L = 0 at LO. The neutron follows from the proton by u <-> d (with ubar <-> dbar,
isospin). Status `analytic-derivation` within the parton model; the model itself is the assumption.

## Beyond leading order (rules)

- Factorization (Eq. 18.21): F_i = sum_a C_i^a (x) f_a + O(M^2/Q^2), with C (x) f = int_x^1 dy/y C(y) f(x/y)
  (Eq. 18.22); the coefficient functions are series in alpha_s. Record the factorization scheme (MS-bar in almost all
  modern sets; the DIS scheme has no higher-order corrections to F_2, Sec. 18.2.2), mu_F and mu_R.
- Order counting: F_L starts at O(alpha_s). "NLO F_L" may mean O(alpha_s) or O(alpha_s^2); state the absolute order.
- The PDF set's order, the evolution order and the coefficient-function order are one choice
  ([PDFs](pdfs-and-lhapdf.md)); mixing them is an assumption to state. Central scale mu_R = mu_F = Q with the
  envelope of [higher orders](higher-order-predictions.md).
- The O(alpha_s) F_L is implemented only in a theory-domain profile (planned, phase 4 of the hadron-structure plan);
  its formula is not given here until its source is read.
- QED radiative corrections: predictions are Born level by default. Comparing with radiatively corrected data is a
  transformation declared in `contracts/comparison/gate.py`, not a silent correction.

## Heavy quarks, target mass, higher twist (rules)

- Heavy-quark schemes (Sec. 18.3): a fixed-flavour-number scheme (FFNS, three light quarks in the evolution, heavy
  quarks in the coefficient functions with their full mass dependence) and variants of the general-mass
  variable-flavour-number scheme (GM-VFNS) give different results; the review notes in particular a smaller
  alpha_s(M_Z^2) and a smaller large-x gluon at large Q^2 in FFNS fits. The review does not name the variants in its
  text; ACOT, FONLL and RT are the names its references use, and a theory-spec names the variant and its source. Differences between schemes are
  alternative-model objects, not an uncertainty band.
- Thresholds: the partonic threshold for producing a heavy pair in boson-gluon fusion is s_hat >= 4 m_Q^2; with
  s_hat = Q^2 (xi_g / x - 1) for a gluon of momentum fraction xi_g <= 1 this needs x <= 1 / (1 + 4 m_Q^2 / Q^2)
  (derived here). The hadronic threshold on W^2 is set by the lightest final state with the heavy flavour (on a
  nucleon, a heavy baryon plus a heavy meson; derived here from baryon-number and flavour conservation, masses from
  `physical_data.py`); (M + 2 m_Q)^2 is only a quark-mass stand-in. State which one a calculation uses.
- Neutrino charm production: slow rescaling. With a final heavy quark of mass m_j and a massless initial quark the
  parton variable is xi_bar = xi R_ij, R_ij = (Q^2 - m_i^2 + m_j^2 + Delta(-Q^2, m_i^2, m_j^2)) / (2 Q^2)
  (Schienbein et al., Eqs. A.5-A.9), which for m_i = 0 and M -> 0 is x (1 + m_j^2 / Q^2). Record the strange and charm
  treatment.
- Target-mass corrections are not the substitution x -> xi. With r = sqrt(1 + 4 x^2 M^2 / Q^2) and the Nachtmann
  variable xi = 2x / (1 + r) (Eq. 3 of Schienbein et al.), the Georgi-Politzer result in the Kretzer-Reno
  master-formula form is (their Eq. 23; Eq. 15 is the Georgi-Politzer expression itself)

  ```
  F_2^TMC(x, Q^2) = (x^2 / (xi^2 r^3)) F_2^(0)(xi) + (6 M^2 x^3 / (Q^2 r^4)) h_2(xi) + (12 M^4 x^4 / (Q^4 r^5)) g_2(xi)
  h_2(xi) = int_xi^1 du F_2^(0)(u) / u^2,   g_2(xi) = int_xi^1 dv (v - xi) F_2^(0)(v) / v^2      (Eqs. 18, 20)
  ```

  F_2^(0) is the M -> 0 structure function evaluated at xi, which is not lim_{M->0} F_2^TMC at xi (their Eq. 25).
  F_L acquires TMC terms even at LO (their Eq. 26), where the review defines F_L^TMC = r^2 F_2^TMC - 2x F_1^TMC
  (p. 10), not the F_L = F_2 - 2x F_1 of PDG Eq. (18.17): the two differ at order M^2/Q^2, so state which F_L a
  TMC-corrected prediction reports. The form has a threshold problem as x -> 1 (their Sec. 5).
  Shipping F_2^(0)(xi) alone and calling it TMC is an error. If neglected, list it in `neglected`.
- Higher twist (Sec. 18.2.2): twist-n terms fall like 1/Q^(n-2); the review states they appear numerically
  unimportant above a few GeV^2 with a cut such as W^2 > 15 GeV^2, except at very small x and near x = 1, and are
  likely larger in xF_3 than in F_2. The validity domain is lower bounds on Q^2 and W^2 that the user writes in the
  theory-spec; the scripts ship no threshold and only classify against the bounds they are given.
- Nuclear targets: the per-nucleon isospin combination is the only nuclear step `structure_functions_lo.py` takes;
  nuclear PDFs and effects are the nuclear-effects module (planned).

## Sum rules

`sum_rules.py` integrates tabulated distributions and reports the integral, a convergence estimate and the
extrapolations below and above the table separately (their power-law forms, fitted through the two outermost
points, are assumptions; the convergence estimate does not cover them):

| Rule | Integral | Proton value | Status |
|---|---|---|---|
| momentum | int_0^1 x [sum_q (q + qbar) + g] dx | 1 | momentum conservation of the parton picture |
| number | int_0^1 (q - qbar) dx | u: 2, d: 1, s c b: 0 | quantum numbers of the proton |
| Adler (LO form) | int_0^1 (F_2^{W-} - F_2^{W+}) / x dx = 2 int [(u - ubar) - (d - dbar) - (s - sbar) + (c - cbar)] | 2 | `analytic-derivation` at LO from Eq. (18.19) (derived here) |
| GLS (LO form) | (1/2) int_0^1 (F_3^{W+} + F_3^{W-}) dx = int sum_{u,d,s,c} (q - qbar) | 3 | `analytic-derivation` at LO from Eq. (18.19) (derived here) |

QCD corrections to the Adler and GLS rules are not stated here (no source read). The script ships no expected value;
the user passes one with its source.

## Scripts

- `structure_functions_lo.py`: F_2, 2xF_1, F_L = 0, xF_3, their gamma, gamma-Z, Z or W parts, sigma_r (NC),
  d2sigma/dx dy and d2sigma/dx dQ^2 (GeV and pb) from x f_i(x, Q^2) of ten flavours supplied by the user, for
  photon, gamma-Z or CC exchange, e+-, mu+-, nu, nubar, P_e, proton, neutron or a per-nucleon isospin combination.
  Rejects (exit 2) a missing convention or flavour, a non-finite value, x outside (0, 1] (a nucleus with
  `--allow-nuclear-x` only), y > 1, neutrino NC. Tests: `tests/skills/hep_theory/test_structure_functions_lo.py`
  (Callan-Gross, F_L = 0, charge symmetry with antiquarks, the e+/e- x F_3 sign, the photon limit, polarized NC
  through charge times P_e, the CC normalization against its parton form, units).
- `sum_rules.py`: momentum, number, Adler and GLS integrals with a convergence report
  (`tests/skills/hep_theory/test_sum_rules.py`: Beta-function toys, exact power-law extrapolation, divergence
  reported, violation as a failed verdict).

These are software checks on constructed inputs; they do not establish physical validity.

## Sources read (full text, 2026-10-23)

- PDG, "18. Structure Functions", revised August 2025 by E.C. Aschenauer, R.S. Thorne and R. Yoshida, in
  F. Takahashi et al. (Particle Data Group), Int. J. Mod. Phys. A 41, 2630011 (2026), review PDF dated 1 June 2026
  (https://pdg.lbl.gov/2026/reviews/rpp2026-rev-structure-functions.pdf), pages 1-16: Eqs. (18.1)-(18.25), Secs.
  18.1-18.3 (heavy-quark schemes, higher twist, nuclear PDFs).
- I. Schienbein et al., "A Review of Target Mass Corrections", arXiv:0709.1775v2 (J. Phys. G 35 (2008) 053101):
  Eq. (3), Sec. 2.2 (Eqs. 17-26), Sec. 4, Appendix A (Eqs. A.5-A.9).

Not verified and therefore not used: the O(alpha_s) F_L (Altarelli-Martinelli) formula; QCD corrections to the Adler
and GLS sum rules; the original Georgi-Politzer paper (its result is taken from the review above, which reproduces
it).

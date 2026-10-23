# Polarized DIS: g_1, g_2, asymmetries and sum rules

Purpose: conventions, formulas and required fields for spin-dependent inclusive DIS: the structure functions g_1 and
g_2, the measured asymmetries and the virtual-photon asymmetries, the depolarization factors, the first-moment sum
rules and the factorization-scheme dependence of Delta Sigma. Entry page: [hadron structure](hadron-structure-essentials.md);
unpolarized structure functions in [DIS structure functions](dis-structure-functions.md); nuclear targets (3He, d) in
[nuclear targets](nuclear-parton-effects.md).

Status: guidance and one tool (Th17), sources read in full text on 2026-10-23 (see "Sources read"). The executable
pieces are the polarized rules of `sum_rules.py` (LO g_1 moments, the Bjorken integral at LO, the Ellis-Jaffe
reference value); g_2 beyond Wandzura-Wilczek, scheme conversions and higher orders are rules only.

## Contents

- Required fields
- Cross sections and asymmetries
- Leading order and g_2
- First moments and sum rules
- Factorization schemes and Delta Sigma
- Nuclear targets
- Checks
- Sources read

## Required fields

`polarization_convention` (beam and target polarization directions, helicity definition, overall sign of g_1),
`factorization_scheme` for polarized densities (MS-bar in the Vogelsang, Mertig, van Neerven form, AB, or JET),
`target_mass_treatment`, and as a model input the source of R = sigma_L / sigma_T used in the depolarization factor.
A missing field is a refusal.

## Cross sections and asymmetries

PDG 2026, Eqs. (18.13)-(18.17), gives the polarized cross-section difference in terms of g_1 ... g_5; in the
M^2/Q^2 -> 0 limit d2 Delta sigma / dx dy = (4 pi alpha^2 / (x y Q^2)) eta^i [ -Y_+ g_4 -/+ Y_- 2x g_1 + y^2 g_L ]
(Eq. 18.16), which for photon exchange reduces to g_1. The review's Delta sigma is antiparallel minus parallel for e-
and neutrinos but parallel minus antiparallel for e+ and antineutrinos (after Eq. 18.14): state the sign convention.

Asymmetries (Kuhn, Chen, Leader, Sec. 1.1, Eqs. 18-29; m the lepton mass, gamma^2 = 4 M^2 x^2 / Q^2):

```
A_par  = (dsigma(antiparallel) - dsigma(parallel)) / (2 dsigma_unpol)   [lepton spin along the beam, nucleon spin
         antiparallel minus parallel to it];   A_perp likewise for transverse target polarization
A_1 = (g_1 - gamma^2 g_2) / F_1,   A_2 = gamma (g_1 + g_2) / F_1
A_par = D (A_1 + eta A_2),   A_perp = d (A_2 - xi A_1)
D   = y [(1 + gamma^2 y/2)(2 - y) - 2 y^2 m^2/Q^2]
      / [y^2 (1 - 2 m^2/Q^2)(1 + gamma^2) + 2 (1 + R)(1 - y - gamma^2 y^2/4)]
eta = gamma [1 - y - y^2 (gamma^2/4 + m^2/Q^2)] / [(1 - y/2)(1 + gamma^2 y/2) - y^2 m^2/Q^2]
R   = (1 + gamma^2) F_2 / (2 x F_1) - 1
```

d and xi are their Eqs. 27 and 29. D depends on R, so the R parametrization is a model input of every A_1 extracted
from A_par. Bounds: |A_2| <= sqrt(R (1 + A_1) / 2) (their Eq. 30); |A_1| <= 1 (derived here: A_1 is a ratio of
helicity cross sections, |sigma_1/2 - sigma_3/2| <= sigma_1/2 + sigma_3/2). Flipping the beam or the target
polarization flips the sign of the measured asymmetry.

## Leading order and g_2

```
g_1(x, Q^2) = (1/2) sum_q e_q^2 [ Delta q(x, Q^2) + Delta qbar(x, Q^2) ],   Delta q = q_+ - q_-
```

(Kuhn, Chen, Leader, Eqs. 35-36; PDG Eq. 18.18 for the photon, gamma-Z and Z parts.) At LO, Delta q -> q gives
g_1 -> F_1, and |Delta q| <= q gives |g_1| <= F_1 (derived here from q_+- >= 0). g_2 has no unambiguous parton-model
expression; its twist-2 part is the Wandzura-Wilczek form g_2^WW(x) = -g_1(x) + int_x^1 dy g_1(y)/y (PDG Eq. 18.20;
Kuhn, Chen, Leader, Eq. 38); the twist-3 part is a model input (definition only).

## First moments and sum rules

With a_3 = int Delta q_3, a_8 = int Delta q_8, a_0 = Delta Sigma (Kuhn, Chen, Leader, Eqs. 39-44; Delta q_3 =
(Delta u + Delta ubar) - (Delta d + Delta dbar), Delta q_8 = ... - 2 (Delta s + Delta sbar)):

```
Gamma_1^p = int_0^1 g_1^p dx = (1/9) [ (3/4) a_3 + (1/4) a_8 + a_0 ]          (LO, their Eq. 43)
Gamma_1^{p,n} = (1/12) [ +/- a_3 + a_8 / 3 ] E_NS(Q^2) + (1/9) a_0(Q^2) E_S(Q^2)  (leading twist, their Eq. 86)
```

| Sum rule | Content | Status |
|---|---|---|
| Bjorken | int (g_1^p - g_1^n) dx = (g_A / 6) [1 - alpha_s/pi - 3.58 (alpha_s/pi)^2 - 20.22 (alpha_s/pi)^3 ...] for 3 active flavours (their Eq. 89) | `perturbative-argument`, state the alpha_s order; assumes isospin invariance; g_A = a_3 from neutron beta decay is an input with its source |
| Ellis-Jaffe | Gamma_1^{p,n} = +/- g_A/12 + 5 a_8/36 at LO, from Eq. 43 with a_0 = a_8 (Delta s + Delta sbar = 0) and a_8 from hyperon beta decays (their Sec. 2.1, before Eq. 46; SU(3) flavour symmetry assumed) | `heuristic-argument`: assumptions, not a QCD result; contradicted by the measured Gamma_1^p (their Sec. 2.1, Eqs. 47-49) |
| Burkhardt-Cottingham | int_0^1 g_2 dx = 0 (their Eq. 92) | rests on an assumption about the asymptotic behaviour of a Compton amplitude, not on the OPE; g_2^WW satisfies it automatically (their Eq. 94) |
| Efremov-Leader-Teryaev | int x [g_1^V + 2 g_2^V] dx = 0 per flavour, valence (their Eq. 90) | OPE result as stated there |

The coefficient values in E_NS and E_S (their Eqs. 87-88) are for three active flavours, E_S in the MS-bar scheme.
Higher twist enters Gamma_1 as mu_4/Q^2 + mu_6/Q^4 (their Eq. 95). The moments of the sum rules include the elastic
contribution at x = 1 in principle; DIS tables exclude it (their Sec. 2.1). Extrapolation of an integral outside the
measured x range (x -> 0, x -> 1) is a separate uncertainty object (`sum_rules.py` reports it separately).

## Factorization schemes and Delta Sigma

Three schemes are in use (Kuhn, Chen, Leader, Sec. 2.2): MS-bar (Vogelsang, Mertig, van Neerven), in which a_3 and
a_8 are Q^2 independent; AB (Ball, Forte, Ridolfi), in which Delta Sigma is also Q^2 independent; JET (equivalent to
the chiral-invariant scheme), in which a_3, a_8 and Delta Sigma are Q^2 independent. In the AB and JET schemes
a_0 = Delta Sigma - 3 (alpha_s / 2 pi) Delta G (their Eq. 62); in MS-bar the gluon does not contribute to a_0.
Delta Sigma from sources in different schemes is not compared without the conversion; such a comparison is refused.

## Nuclear targets

A "neutron" from 3He or the deuteron needs the effective nucleon polarizations in 3He and the D-state probability of
the deuteron, sourced inputs with their status (the nuclear-targets page); a result from such a target is flagged as
nuclear-corrected.

## Checks

|A_1| <= 1; |g_1| <= F_1 at LO; Delta q -> q gives g_1 -> F_1; a polarization flip flips the asymmetry; the Bjorken
integral at LO equals (a_3)/6 on a toy (`tests/skills/hep_theory/test_sum_rules.py`, polarized rules: g_1 moments of
proton and neutron, Bjorken at LO, the Ellis-Jaffe reference value). Software checks only.

## Sources read (full text, 2026-10-23)

- PDG 2026 "Structure Functions" (see [DIS structure functions](dis-structure-functions.md)): Eqs. (18.6),
  (18.13)-(18.20).
- S.E. Kuhn, J.-P. Chen, E. Leader, arXiv:0812.3535v1 (Prog. Part. Nucl. Phys. 63 (2009) 1): Sec. 1.1 (Eqs. 14-32), Sec. 2.1
  (Eqs. 33-49), Sec. 2.2 (Eqs. 50-62) and Sec. 3.1 (Eqs. 84-95).

Not verified and therefore not used: the original Bjorken, Ellis-Jaffe, Burkhardt-Cottingham and Larin papers (the
review states their results); a_3 and a_8 values (the review's Eq. 46 values are 2008 inputs: take current values with
their source); the relation a_8 = 3F - D to hyperon-decay constants (not in the review); the O(alpha_s)
coefficient functions of g_1; target-mass corrections to g_1 and g_2.

# Deep-inelastic-scattering kinematics

Owner: hep-theory (generic kinematics and conventions). This file defines the invariants of lepton-nucleon
scattering l N -> l' X and the identities that follow from the definitions, with every assumption named. It
holds no experiment, detector or dataset: facility configurations (beam species, energies, polarization) come
from an experiment profile or the user; which estimator reconstructs x, y and Q^2 from measured quantities and
with what resolution belongs to detector-response; selections and binning in these variables to hep-analysis;
unfolding to hep-statistics; structure functions and cross sections to the PDG review this file cites, not to
this file.

## Definitions (PDG, "Structure Functions", section 18.1)

Four-momenta: k and k' for the incoming and outgoing lepton (masses m_l, m_l'), P for the nucleon of mass M,
q = k - k' for the exchanged boson (gamma, Z or W). Invariant quantities:

| Quantity | Definition | Reading |
|---|---|---|
| nu | nu = q.P / M | lepton energy loss E - E' in the nucleon rest frame |
| Q^2 | Q^2 = -q^2 = 2 (E E' - k_vec . k'_vec) - m_l^2 - m_l'^2 ; ~ 4 E E' sin^2(theta/2) when E E' sin^2(theta/2) >> m_l^2, m_l'^2 | minus the boson virtuality; theta is the lepton scattering angle with respect to the lepton beam direction |
| x | x = Q^2 / (2 M nu) | Bjorken x; in the parton model the struck quark's momentum fraction, beyond leading order still the definition but no longer identical to that fraction |
| y | y = q.P / k.P = nu / E in the rest frame | inelasticity: fraction of the lepton energy lost in the nucleon rest frame |
| W^2 | W^2 = (P + q)^2 = M^2 + 2 M nu - Q^2 | mass squared of the system X recoiling against the scattered lepton |
| s | s = (k + P)^2 = Q^2 / (x y) + M^2 + m_l^2 | lepton-nucleon center-of-mass energy squared |

"Deep" means Q^2 >> M^2 and "inelastic" W^2 >> M^2; the review neglects m_l and m_l' after these definitions.

## Identities that follow (status: analytic-derivation; assumptions stated per line)

- Exact: Q^2 = x y (s - M^2 - m_l^2), since x y = Q^2 / (2 k.P) and s = m_l^2 + M^2 + 2 k.P.
- Exact: W^2 = M^2 + Q^2 (1 - x) / x and nu = Q^2 / (2 M x); so x = 1 is elastic scattering (W = M).
- Ranges: 0 < x <= 1 and 0 < y <= 1 (k'.P >= 0), hence Q^2 <= s - M^2 - m_l^2.
- Beams: with the lepton momentum at a crossing angle theta_c to the reversed hadron momentum (theta_c = 0 head-on),
  s = m_l^2 + M^2 + 2 (E_l E_h + |k_vec| |P_vec| cos theta_c); with m_l = 0 and E_h >> M this is s ~ 4 E_l E_h.
  The crossing angle lowers s; the hadron energy is per nucleon when the beam is an ion, and M is then the
  mass chosen for the per-nucleon convention. State both choices; a whole-ion convention is a different variable.
- Jacobian (PDG eq. 18.1): d^2 sigma / dx dy = x (s - M^2) d^2 sigma / dx dQ^2 = (2 pi M nu / E') d^2 sigma / dOmega_rest dE',
  which is |dQ^2 / dy| at fixed x = x (s - M^2) with m_l neglected.

## Frames

The invariants are frame-independent. E, E', theta and nu as "energy loss" refer to the nucleon rest frame;
at a collider the laboratory frame is neither the rest frame nor the lepton-nucleon center-of-mass frame unless
the beams collide head-on with equal and opposite momenta, so every boost and the sign convention for the beam axis are stated per configuration
and never assumed. Charged-current exchange leaves the outgoing lepton unobserved; the invariants are the same,
but their reconstruction is an estimator question for detector-response.

## What is not derived here

Reconstruction estimators (electron, hadron and double-angle methods) and their resolutions: detector-response.
Structure functions F_i, g_i and the cross-section formulae of PDG 18.1.1 onward: theory predictions to be derived
per request with their own derivation status. Polarized observables, radiative corrections, target-mass and
higher-twist effects: not derived here; name them as neglected in any theory-spec that uses this file.

## Script

`<plugin root>/skills/hep-theory/scripts/dis_kinematics.py` builds s from the two beam energies and a crossing
angle, computes the third of (x, y, Q^2) from the other two with the exact identity, and refuses unphysical inputs
(exit 1, JSON reason). It ships no constants: the target mass is an input. Tests in
`<plugin root>/tests/skills/hep_theory/test_dis_kinematics.py` check every identity above against four-vector arithmetic.

## Source read

PDG, "18. Structure Functions", revised August 2025 by E.C. Aschenauer, R.S. Thorne and R. Yoshida, in S. Navas
et al. (Particle Data Group), Phys. Rev. D 110, 030001 (2024) and 2025 update; section 18.1 and eq. (18.1),
pages 1-2 of the review PDF (https://pdg.lbl.gov/2025/reviews/rpp2025-rev-structure-functions.pdf), read on
2026-10-04. Nothing beyond those pages is used.

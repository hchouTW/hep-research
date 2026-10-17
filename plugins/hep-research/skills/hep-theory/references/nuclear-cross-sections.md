# Nuclear cross-section conventions

Conventions for the nuclear cross sections that cosmic-ray propagation and detector corrections use. This file is
method only: cross-section values come from the user's tables or a cited parametrization, with their source, never
from this file or from memory. Propagation models are in [cosmic-ray propagation](cosmic-ray-propagation.md); the
detector-side survival and feed-down corrections are in
`<plugin root>/skills/hep-detector/references/nuclear-interactions-in-detector-material.md`; the measurement's
correction chain is in `<plugin root>/skills/hep-measurement/references/correction-chain.md`.

## Contents

- Kinds of cross section
- Targets: interstellar gas and detector material
- The straight-ahead approximation
- Cumulative cross sections and short-lived intermediates
- Parametrization families and their validity
- Uncertainty and correlations
- Sources read

## Kinds of cross section

- **Inelastic (total reaction) cross section** sigma_inel(projectile, target, T): any reaction that removes the
  projectile as that species. It sets the loss term of propagation and the survival probability in a detector.
- **Charge-changing cross section** sigma_cc: reactions that change the charge Z. It is smaller than sigma_inel by the
  isotope-changing reactions that keep Z (for example neutron removal), and it is what a charge-tagged survival
  measurement in a detector actually measures. State which of the two a number is.
- **Isotopic (partial) production cross section** sigma(projectile + target -> fragment): the production of one
  isotope. Elemental production cross sections are sums over the isotopes of that element. A direct cross section
  counts only the fragment itself; a cumulative one adds the short-lived nuclei that decay into it (below).

Every quantity carries: projectile, target, fragment (for production), energy variable (kinetic energy per nucleon T,
in GeV/n unless stated), and whether it is direct, cumulative, elemental or isotopic.

## Targets: interstellar gas and detector material

- **Interstellar medium.** The gas is mostly hydrogen and helium; propagation codes take the rate on H plus a helium
  fraction times the rate on He, and drop heavier targets, whose contribution is at the per-mille level (Génolini et
  al. 2018, from ISM abundances; Evoli et al. 2018 likewise ignore targets heavier than He). The He-target cross
  section is often obtained from the H-target one by a scaling relation; the scaling used is part of the model and is
  stated with it.
- **Detector material.** Here the targets are the materials of the instrument (carbon, aluminium, silicon, ...), not
  H and He. The interaction length of a projectile in a material of mass number A is
  `lambda = A / (N_A sigma)` (grammage, g/cm2, with sigma per nucleus and N_A Avogadro's constant), and for a mixture
  with mass fractions w_i, `1/lambda = sum_i w_i N_A sigma_i / A_i`. A cross section measured or parametrized on H or
  He does not transfer to C or Al without a target-mass scaling, which must itself be cited.

## The straight-ahead approximation

Propagation codes usually assume that a fragment keeps the kinetic energy per nucleon of its parent,
`dsigma/dT (T, T') = sigma * delta(T - T')` (Evoli et al. 2018, eq. 5.1, "as typically done"). It makes production a
product of the parent flux and a single number per energy. It is an approximation: its accuracy for B/C was studied
separately (cited by Evoli et al.), and it fails for light fragments with a broad energy distribution and at low
energy. A prediction that relies on it says so; a calculation that needs the fragment energy spectrum (for example
antiprotons or light fragments in a detector) does not use it.

## Cumulative cross sections and short-lived intermediates

A short-lived fragment decays before it can interact again, so in propagation it counts as its decay products: the
cumulative cross section of a fragment F is the direct one plus those of the short-lived nuclei ("ghosts") that decay
into F, weighted by their branching ratios (Génolini et al. 2018, eq. 1). "Short-lived" is relative to the time scale
of the problem: in the Galaxy, half-lives below a few kyr; in a detector, a fragment usually crosses the instrument
before it decays, so detector work uses direct cross sections and its own lifetime criterion. Electron-capture decays
are blocked for fully ionized nuclei at high energy, which changes which nuclei are effectively stable. Ghost
contributions can be a large part of some isotopes' production (Génolini et al. 2018 report cases near a quarter), so
a cumulative cross section always states which intermediates and branching ratios it includes and from which nuclear
data edition (half-lives from `<plugin root>/core/constants`, NUBASE2020, or the user's table).

## Parametrization families and their validity

- **Semi-empirical formulae** for inelastic cross sections reproduce the existing data well where data exist; at
  high energy (above a few GeV/n) the common families are nearly constant and agree with each other, while at lower
  energy they can differ by tens of percent (Evoli et al. 2018, section 3). First-principles calculations are not yet
  competitive for this purpose.
- **Production cross sections** come from semi-empirical systematics fitted to data, renormalized to measured
  channels where they exist. Many relevant channels have few or no measurements, and the available data have
  uncertainties at the tens-of-percent level for many reactions (Génolini et al. 2018).
- A parametrization is valid only in the projectile, target and energy ranges of the data it was fitted to; outside
  them its use is an extrapolation and is labelled so. Each use records the family, its version, its range, and the
  data it was renormalized to.

## Uncertainty and correlations

- Express the cross-section uncertainty as **model alternatives** (two or more parametrization families or datasets,
  kept distinct; an envelope only by a declared prescription, as for any theory uncertainty) plus a
  **normalization nuisance** per channel or group of channels, with its prior width from the data that constrain it.
- The same cross sections often enter twice: in the measurement's corrections (survival and feed-down in the
  detector material) and in the astrophysical interpretation (production in the ISM). When both use cross sections
  from the same family or the same data, the correlation between the correction and the interpretation is declared
  together, in one place, and a fit that uses both carries a shared nuisance rather than two independent ones.
- Energy dependence of the uncertainty is part of the model: a single global scale is a simplification that is
  stated when used.

## Sources read

Read 2026-10-17 (generic User-Agent):
- L. Génolini, D. Maurin, I. V. Moskalenko, M. Unger, "Current status and desired accuracy of the isotopic production
  cross sections relevant to astrophysics of cosmic rays I. Li, Be, B, C, N", arXiv:1803.04686 (Phys. Rev. C 98
  (2018) 034611): full text read (sections III-V: ghost nuclei and eq. 1, targets, ranking).
- C. Evoli, D. Gaggero, A. Vittino, M. Di Mauro, D. Grasso, M. N. Mazziotta, "Cosmic-ray propagation with DRAGON2:
  II. Nuclear interactions with the interstellar gas", arXiv:1711.09616 (JCAP 07 (2018) 006): full text read
  (sections 2, 3 and 5: loss and gain terms, inelastic parametrizations, eq. 5.1 straight-ahead assumption).
- Particle Data Group, Review of Particle Physics 2024, "Atomic and Nuclear Properties of Materials" (table 6.1):
  read for the nuclear interaction length column; the relation lambda = A / (N_A sigma) is the definition of an
  interaction length in grammage and is stated here as such.

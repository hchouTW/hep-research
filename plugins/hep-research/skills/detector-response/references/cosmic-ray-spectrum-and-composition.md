# Cosmic-Ray Spectrum, Composition, and Propagation

Orients the astroparticle-physics references that follow
([extensive air showers](extensive-air-showers.md),
[ground-based arrays](ground-based-detection-arrays.md),
[imaging Cherenkov](imaging-atmospheric-cherenkov.md),
[neutrino astronomy](neutrino-astronomy.md),
[space-based direct detection](space-based-direct-detection.md)). Covers the
observable this whole domain measures - the differential flux of cosmic rays as a
function of energy, species, arrival direction, and time - and the astrophysical
processes (acceleration, propagation) that shape it. Detector-level material
(rigidity, material budget, PID) is in
[detector-systems-overview.md](detector-systems-overview.md) through
[particle-identification.md](particle-identification.md) and applies
unchanged to space-based spectrometers; this file is about the physics of the flux
itself, not how any one instrument measures it.

## The all-particle spectrum and its features

The cosmic-ray flux falls as a power law spanning more than ten decades in energy,
`dN/dE ~ E^-gamma`, with `gamma` around 2.7 below the knee and steepening above it.
Three named features mark changes in the underlying physics and are the primary
targets of composition and origin measurements:

Feature energies and indices below were checked 2026-09-25 against the PDG 2026
cosmic-ray review (revised March 2026); see the latest-results policy in
[sources](../../research-communication/references/primary-sources-and-version-checks.md).

- **The knee** (a few PeV): the spectrum steepens from `gamma ~ 2.7` to `gamma ~ 3`.
  The leading interpretation is a rigidity-dependent maximum energy of Galactic
  accelerators - light nuclei (proton, helium) cutting off first, heavier nuclei
  cutting off at proportionally higher energy per nucleus since acceleration and
  confinement scale with rigidity, `R = E / (Z * e)`, not raw energy. This predicts a
  "knee" for each species in sequence, sometimes called the composition unfolding into
  a "second knee" (~100 PeV, steepening to `gamma ~ 3.3`) as iron's cutoff is reached.
<!-- example: experiment-specific illustration -->
- **The ankle** (~5 EeV): the spectrum flattens back toward `gamma ~ 2.5`. A further
  feature, the "instep" (a steepening that starts around 10 EeV, established above 5
  sigma by Auger), sits between the ankle and the suppression. The
  standard interpretation is a transition from a steep Galactic component to a
  harder, extragalactic component that has overtaken it - though a purely propagation-
  driven "dip" scenario (pair-production energy losses of extragalactic protons on the
  CMB) predicts a similar flattening without invoking a new source population, and
  distinguishing the two requires composition, not just spectral shape.
<!-- /example -->
- **The GZK suppression** (starting around 5*10^19 eV = 50 EeV; whether it is a
  propagation (GZK) cutoff or the sources' maximum energy is still open): a cutoff from photopion production,
  `p + gamma_CMB -> Delta -> p/n + pi`, once a proton's energy exceeds the pion-
  production threshold in the CMB rest frame. This limits the horizon from which the
  highest-energy cosmic rays can reach Earth to roughly 100 Mpc (the "GZK horizon"),
  making UHECR arrival directions a probe of the local (not cosmological) source
  distribution - and making source identification a matter of nearby-source
  catalogs and magnetic-deflection modeling, not redshift.

Because the spectrum falls so steeply, small systematic shifts in the reconstructed
energy scale move a large number of events across any fixed threshold. An energy-scale
uncertainty of `delta` propagates into a flux uncertainty of roughly `gamma * delta`
at fixed measured energy - report the absolute energy-scale uncertainty explicitly
whenever a spectral index or a feature location (knee, ankle, cutoff energy) is
quoted, and prefer forward-folding the assumed spectrum through the resolution rather
than unfolding a steeply falling flux bin-by-bin (see
[measurements-and-unfolding.md](../../hep-analysis/references/measurements-and-unfolding.md), which this
domain inherits unchanged).

## Composition and its observables

"Composition" means the mix of primary nuclear species (protons through iron and
beyond) as a function of energy, and every ground-based technique infers it
indirectly through the depth of shower maximum, `X_max` (see
[extensive air showers](extensive-air-showers.md)) or through the ratio of muon
to electromagnetic shower content - never through direct nuclear charge measurement,
which only space-based detectors provide. Two composition observables recur:

- **`<X_max>` and its energy dependence** (the "elongation rate"): a proton-dominated
  composition produces showers that penetrate deeper on average (larger `X_max`) with
  larger shower-to-shower fluctuations than an iron-dominated one, because a heavier
  nucleus behaves approximately as `A` independent nucleon-energy sub-showers
  (superposition model) that average out fluctuations and start higher in the
  atmosphere.
- **Muon content relative to a proton-shower reference**: heavier primaries produce
  more muons per unit energy than protons do, because more generations of hadronic
  sub-showers each feed the muon channel. Every hadronic-interaction model used to
  predict this ratio is extrapolated far beyond its accelerator-calibrated energy
  range, and current models under-predict the observed muon content at the highest
  energies relative to what a pure-composition explanation would require (the
  "muon puzzle") - treat any composition conclusion drawn from muon content as model-
  dependent until the interaction-model systematic is quoted alongside it.

Composition inferences are always relative to a chosen hadronic interaction model
(e.g. QGSJet, EPOS, SIBYLL); state which model and which version, since model choice
routinely shifts the inferred mean composition by more than the reported statistical
uncertainty.

## Acceleration

**Diffusive shock acceleration** (first-order Fermi acceleration) is the standard
mechanism: a particle gains energy by repeatedly crossing a shock front, scattering
off magnetic turbulence on each side, with a fractional energy gain per crossing
cycle. Two results follow directly and recur throughout the literature:

- It naturally produces a power-law spectrum in momentum/energy, with an index set by
  the shock compression ratio - the reason a `~E^-2` injection spectrum is the
  standard theoretical starting point before Galactic propagation steepens it to the
  observed `~E^-2.7`.
- The maximum achievable energy is set by how long the particle stays confined to the
  shock region, which scales with **rigidity**, not energy - the same rigidity
  dependence that produces species-ordered knee features.

Second-order Fermi acceleration (stochastic scattering off moving magnetic
inhomogeneities, without a shock) is far less efficient per encounter and is
generally treated as a subdominant or reacceleration process rather than the primary
mechanism for the bulk of the spectrum.

**Hillas criterion**: a source can confine (and hence accelerate) a particle only up
to the rigidity at which its Larmor radius no longer fits inside the source region,
`E_max ~ Z * e * B * L` for magnetic field `B` and source size `L`. Plotting candidate
sources on a size-vs-field ("Hillas") plot is the standard first check of whether a
proposed source class can plausibly reach a given energy at all, independent of any
detailed acceleration model.

## Propagation

Once accelerated, charged cosmic rays do not travel in straight lines - Galactic (and,
for UHECRs, extragalactic) magnetic fields scatter them, and propagation is normally
treated as diffusion. The steady-state diffusion-loss equation for a species'
differential density `N(E)` is

    dN/dt = grad . (D(E) * grad N) - d/dE (b(E) * N) + Q(E)

with diffusion coefficient `D(E)` (typically rising with rigidity), energy-loss rate
`b(E)` (adiabatic, ionization, or - for extragalactic protons above the pion-
production threshold - photopion losses on the CMB), and source term `Q(E)`.
Consequences that matter for interpreting a measured spectrum:

- **Secondary-to-primary ratios** (boron/carbon, or sub-iron/iron) measure the
  *path length* traversed, since secondaries are produced by spallation of primaries
  on the interstellar medium. A falling B/C ratio with rising energy is direct
  evidence that higher-energy particles escape the Galaxy faster (a rigidity-dependent
  diffusion coefficient), independent of any assumption about the source spectrum
  itself - the standard way to separate an acceleration-spectrum effect from a
  propagation effect.
- **Anisotropy** is expected to grow with energy in a diffusive picture (fewer
  scatterings before escape, so the arrival direction retains more memory of the
  source), and a measured anisotropy amplitude and phase is one of the few
  observables that constrains the diffusion coefficient and the degree of large-scale
  regularity in the Galactic field independently of the spectrum shape.
- **Solar modulation** distorts the *low-energy* (below ~10s of GeV) part of the
  measured spectrum: the heliospheric magnetic field, carried by the solar wind,
  suppresses the flux reaching the inner heliosphere in a way that varies with the
  solar cycle. Any low-rigidity spectrum measurement must state the solar-activity
  epoch (and ideally the force-field modulation potential) it was taken under - see
  [space-based direct detection](space-based-direct-detection.md) for the
  force-field approximation used to compare measurements taken at different times.

## Deliverables

- The energy range and species (all-particle, or a specific nucleus/element)
  the reported flux refers to, and the hadronic interaction model assumed wherever a
  composition or muon-content statement depends on one.
- The absolute energy-scale uncertainty and its propagated effect on any quoted
  spectral index or feature location (knee, ankle, cutoff), given the flux's steep
  fall.
- Whether unfolding was done bin-by-bin or by forward-folding an assumed spectral
  shape through the response, given the steep-spectrum migration bias described
  above.
- For a composition claim: which observable (`<X_max>`, muon content, direct nuclear
  charge) was used, and the interaction-model dependence quoted alongside it.
- For a low-energy flux measurement: the solar-activity epoch/modulation potential and
  the geomagnetic cutoff applied (if ground- or near-Earth-based).
- For a propagation or anisotropy conclusion: which independent observable
  (secondary/primary ratio, anisotropy amplitude/phase) was used to separate a
  propagation effect from a source-spectrum effect.

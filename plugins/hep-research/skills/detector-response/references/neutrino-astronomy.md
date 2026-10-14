# High-Energy Neutrino Astronomy

Covers large-volume Cherenkov neutrino telescopes (in glacial ice or in deep water) -
how a neutrino interaction becomes a detectable light
pattern, the backgrounds that dominate any astrophysical search, and how significance
and exposure are computed. Shares its ON/OFF and trials-factor statistical machinery
with [imaging Cherenkov](imaging-atmospheric-cherenkov.md) and
[astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md); shares the Cherenkov-angle
physics (though in a very different regime - a natural medium, kilometer-scale
baselines, not a dense radiator) with
[particle identification](particle-identification.md).

<!-- example: experiment-specific illustration -->
Examples: IceCube in glacial ice, KM3NeT in seawater.
<!-- /example -->

## Detection principle

A neutrino telescope does not detect neutrinos directly; it detects the Cherenkov
light from *charged secondaries* produced when a neutrino interacts via charged- or
neutral-current deep-inelastic scattering in the surrounding ice or water (or, more
rarely, in the bedrock/nearby matter just outside the instrumented volume). A
three-dimensional lattice of photomultiplier modules records the arrival time and
charge of Cherenkov photons; the pattern of hits - light-front timing, intensity per
module - is fit to a hypothesis (a through-going track or a localized cascade) to
reconstruct direction, energy, and interaction type. Because the effective target mass
is the surrounding natural medium rather than an engineered detector volume, effective
area/volume is a strong function of both energy and interaction topology and must be
computed from full detector simulation, not treated as constant.

## Event topologies

- **Tracks**: a charged-current muon-neutrino interaction (or a muon produced
  upstream and traversing the detector) leaves a long, through-going or starting
  Cherenkov light track. Tracks give the best **angular resolution** (sub-degree at
  high energy for a large array), because the light pattern constrains a full
  trajectory rather than a point, making them the preferred topology for point-source
  and source-catalog searches - at the cost of poorer energy resolution, since only
  the fraction of the muon's energy deposited (or its range, if it stops inside the
  instrumented volume) is directly observable, and a through-going track's true
  neutrino energy is only weakly constrained.
- **Cascades**: charged-current electron- and tau-neutrino interactions, and all
  neutral-current interactions regardless of flavor, deposit their energy in a
  roughly spherical light pattern localized near the interaction vertex. Cascades
  give good **energy resolution** (most of the neutrino energy is contained and
  visible) but poorer angular resolution, which depends on the medium: above 100 TeV
  the average direction accuracy is better than about 10 degrees in polar ice and 2
  degrees in seawater, because light scatters more in ice (PDG RPP 2025, sec. 36.3.2;
  state the detector's own value), and a point-like light source constrains direction
  far more weakly than an extended track - the complementary trade-off to tracks, which is why a full
  point-source-plus-diffuse-flux program uses both topologies rather than either
  alone.
- **Double bang / double pulse**: a distinctive tau-neutrino signature at
  sufficiently high energy, where the initial charged-current interaction cascade and
  the subsequent tau-decay cascade are resolved as two separate light depositions
  along the tau's flight path before it decays. Identifying this topology is a direct,
  flavor-tagged confirmation of an astrophysical tau-neutrino component (tau neutrinos
  are not produced at any significant rate in the atmosphere at these energies), and
  its rate is a clean cross-check of the standard three-flavor (~1:1:1 at Earth)
  astrophysical flavor-ratio expectation from pion/kaon-decay production combined with
  oscillation over astronomical baselines.

## Backgrounds

The dominant background for essentially every astrophysical neutrino search is
**atmospheric neutrinos and atmospheric muons**, both produced by ordinary cosmic-ray
air showers in the atmosphere above and around the detector (see
[extensive air showers](extensive-air-showers.md)):

- **Atmospheric muons** vastly outnumber neutrino-induced events at trigger level for
  any detector not deep enough to fully absorb them; the standard rejection is
  requiring the reconstructed direction to be **upward-going** (having traversed the
  Earth, which no atmospheric muon can do) for a Northern-sky (for a Southern-
  hemisphere detector) search, or using containment and veto-region cuts for events
  that must also accept downward-going astrophysical directions.
- **Atmospheric neutrinos** are an irreducible background even after the muon veto,
  since they arrive from the same directions as an astrophysical signal. They are
  separated statistically, not by source direction, using the facts that (a) the atmospheric
  spectrum falls faster (~`E^-3.7` versus an astrophysical `~E^-2` to `E^-2.5`
  expectation from the same Fermi-acceleration argument as
  [cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md);
  measured astrophysical indices are softer than 2, so take the index from the latest
  diffuse-flux fit of the detector and channel used),
  so a hard energy cut or an energy-dependent likelihood weight enhances the
  astrophysical fraction at high energy, and (b) atmospheric neutrinos are
  accompanied by a correlated atmospheric-muon bundle from the same air shower for a
  large fraction of events, giving a **self-veto** that further suppresses the
  atmospheric component in the downward hemisphere at high energy.
- **Prompt atmospheric neutrinos** (from charmed-hadron decay, which decay before
  losing energy to interaction, unlike pions/kaons) would harden the atmospheric
  spectrum's high-energy tail relative to the conventional pion/kaon component and are
  not yet firmly detected; their predicted rate is a leading systematic uncertainty on
  the purely-atmospheric-background normalization used in any diffuse-flux
  measurement.

Upgoing selections lose the highest energies, because the Earth absorbs neutrinos: for
vertically upgoing neutrinos the survival probability is about 74%, 27% and below 2% at
10, 100 and 1000 TeV (PDG RPP 2025, sec. 36.3.2), so the effective area falls at large
zenith angle and high energy. The Glashow resonance (`anti-nu_e e- -> W-`, peaking at
6.3 PeV antineutrino energy) tags electron antineutrinos.
<!-- example: experiment-specific illustration -->
IceCube observed a 6.05 ± 0.72 PeV shower consistent with it (Nature 591 (2021) 220,
arXiv:2110.15051). Example of a softer measured index: IceCube upgoing muon neutrinos,
9.5 years, single power law `gamma = 2.37 ± 0.09` between 15 TeV and 5 PeV (ApJ 928 (2022)
50, arXiv:2111.10299).
<!-- /example -->

## Significance and exposure

Point-source searches use the same OFF-region/background-scrambling logic as
[imaging Cherenkov](imaging-atmospheric-cherenkov.md): since the atmospheric
background is (to good approximation) uniform in right ascension for a detector with
close to full sky coverage in local coordinates over a sidereal day, the background
expectation at a candidate source position is estimated by **scrambling event right
ascensions** (or, equivalently, using time-averaged declination bands) while holding
the well-measured declination and energy fixed, rather than by pointing at a
literal empty sky position as an IACT does. An unbinned maximum-likelihood method
comparing a point-source-plus-background hypothesis to background-only, evaluated at
each candidate position (or over an all-sky scan), is standard - see
[astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md) for the trials-factor
correction this requires when many positions, an all-sky scan, or many source
catalogs are tested. A diffuse-flux measurement instead fits the aggregate energy and
zenith-angle distribution of all events above some containment/quality selection
against a mixture of the atmospheric components (conventional, prompt, and muon
backgrounds, with normalizations and spectral shapes as nuisance parameters profiled
in the fit, constrained by priors from independent air-shower and flux calculations)
plus a free astrophysical power law.

### Instrument response functions (checklist)

State, with its version: the effective area or volume versus neutrino energy, flavour and declination, after the event selection; the energy threshold and the energy bias and resolution versus energy; the angular
resolution (PSF, for example the 68% containment radius R68) versus energy; and the IRF set and its validity range
(zenith, conditions). Numbers come from the experiment's IRF release or profile, not from this file.

## Deliverables

- The event topology (track, cascade, or double-bang) used, and its corresponding
  angular versus energy resolution trade-off, stated for the specific analysis.
- The atmospheric-muon veto/containment criterion applied, and whether the analysis
  relies on an upward-going selection, a self-veto, or full detector simulation of the
  atmospheric-muon background.
- Which atmospheric-neutrino components (conventional pion/kaon, prompt) were
  included in the background model, and the systematic assigned to the (still
  uncertain) prompt component if relevant.
- For a point-source search: the background-estimation method (RA-scrambling or
  equivalent), the trials factor for the number of positions/catalogs/time windows
  tested, and the likelihood method used for significance.
- For a diffuse-flux fit: the astrophysical spectral model assumed (power law or
  broken power law), the flavor-composition assumption if flavor-dependent effective
  areas were combined, and the atmospheric-background normalization and its
  systematic.
- Effective area/volume as a function of energy and topology for the dataset and
  livetime used, from full detector simulation rather than an analytic approximation.

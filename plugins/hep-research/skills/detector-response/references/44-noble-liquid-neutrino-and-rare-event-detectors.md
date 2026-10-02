# Noble-Liquid, Neutrino, and Rare-Event Detectors

Liquid-argon and liquid-xenon TPCs, dual-phase detectors, large water Cherenkov and
liquid-scintillator detectors, neutrino near/far systems, cryogenic bolometers,
semiconductor ionization detectors, dark-matter TPCs, and neutrinoless-double-beta-decay
detectors. Air-shower arrays, imaging Cherenkov telescopes, and neutrino telescopes
are treated in [31](31-extensive-air-showers.md)-[36](36-multimessenger-analysis.md) (experiment case studies: the bound experiment profile) and
[34](34-neutrino-astronomy.md); this file integrates them into the common framework
([39](39-detector-measurement-framework.md)). Signal formation (recombination,
lifetime, quenching) is in [40](40-signal-formation-and-readout.md).

## Noble-liquid TPCs

**Signals.** A deposit creates excitation (-> scintillation light, `S1`) and
ionization (-> electrons, `S2` after drift and, in dual phase, extraction and
electroluminescence in the gas). Ionization electrons and scintillation photons
**anticorrelate** through recombination: for fixed deposited energy, more charge means
less light, and the combined estimator (`E ∝ n_gamma + n_e`) has better resolution than
either alone. Recombination depends on `dE/dx` and drift field, giving electron/nuclear
recoil discrimination.

**Reconstruction.**
- **Pulse finding** in the waveform (`S1`, `S2`, multiple scatters, single-electron
  tails); pairing `S1`-`S2` in the presence of pileup.
- **3D position**: `xy` from the light pattern (dual phase) or charge pattern; `z` from
  the `S1`-`S2` drift time (`z = v_d Delta t`). In single-phase detectors the
  charge-arrival time and wire/pad readout provide 3D directly.
- **Corrections**: electron lifetime (`exp(-t/tau_e)`, purity monitored and updated),
  position-dependent light collection and charge (nonuniformity), field distortions,
  recombination model, and electron-equivalent vs nuclear-recoil energy scales.
- **Topology reconstruction** in large single-phase LArTPC neutrino detectors:
  tracks/showers/vertices from pattern recognition on wire-time images.

**Ambiguities.** `S1`/`S2` mis-pairing, wire-plane ambiguity (three planes resolve 2D
projections), diffusion and lifetime uncertainty vs true `dE/dx`, and cosmic pileup in
surface detectors.

### Distinctive but generalizable reconstruction and performance features (noble-liquid TPC)

- **Topology**: dense 3D image plus waveform. **Inverse problem**: energy and
  species from two anticorrelated channels; degeneracy: recombination vs energy.
- **Objects**: pulse, cluster, 3D vertex, track, shower. **Informative residual**:
  charge and light versus position/time (uniformity), electron lifetime from
  through-going tracks or calibration sources, energy scale from mono-energetic lines.
- **Scaling**: resolution is set by photon/electron statistics and recombination
  fluctuation; charge threshold set by extraction/`S2` gain.
- **Tails**: pileup, surface events (wall backgrounds), delayed emission.
- **Dependence**: purity/lifetime (time), field (recombination), `T`/`P`.
- **Data sample**: internal calibration sources (dissolved isotopes), through-going
  muons, neutron generators, cosmic tracks.
- **Transfers**: drift-and-readout reasoning ([41](41-gaseous-and-specialized-tracking-technologies.md));
  **does not transfer**: gas-TPC diffusion/ion-backflow values.

## Neutrino detectors

**Topologies and energy.** Wire-based or pixel LArTPCs, segmented scintillator, and
water/scintillator volumes reconstruct the final-state lepton and hadrons. Two energy
estimators exist and differ: **calorimetric** (sum of visible energy plus corrections)
and **kinematic** (from lepton angle/energy assuming an interaction type). Neither is
the neutrino energy without a model of **nuclear effects** (Fermi motion, final-state
interactions, missing energy carried by neutrons/undetected particles), so the
`E_reco -> E_nu` migration is model-dependent
([10](../../hep-analysis/references/10-measurements-unfolding.md)).

**Containment.** Events leaking out of the fiducial volume lose energy
(distribution-dependent bias). Containment is defined in simulation and validated with
control samples (through-going/stopping muons).

**Near/far extrapolation.** Cancel common systematics by measuring a near-detector
flux/cross-section constraint and extrapolating: valid only if the *same interaction
model and acceptance mapping* applies and the detector differences are modeled
(different sizes, technologies, angle acceptance). The *uncorrelated* part of the
detector systematics between near and far does not cancel. Common failure: assuming
cancellation where the two detectors' response or phase-space coverage differ.

### Features (neutrino detectors)

- **Topology**: images (LArTPC), rings/timing (water), light patterns (scintillator).
- **Inverse problem**: neutrino energy/flavor from partial visible final state;
  degeneracy: missing-energy and cross-section model.
- **Informative closure**: mono-energetic Michel electrons, stopping muons, `pi^0` mass,
  and near-detector data.
- **Tails**: containment, secondary interactions, cosmic pileup.
- **Transfers**: model-dependence framing to any inclusive measurement
  ([10](../../hep-analysis/references/10-measurements-unfolding.md)).

## Water Cherenkov and liquid-scintillator detectors

**Water Cherenkov.** Ring imaging of Cherenkov light by photomultipliers
([45](45-cherenkov-imaging-variants-and-photosensors.md)); reconstruct vertex,
direction, energy from **charge/time likelihoods** (per PMT, expected charge and time
given hypothesis `x`, `p(y|x,theta)` ([39](39-detector-measurement-framework.md)));
**ring counting** and electron/muon separation from ring sharpness (sharp muon ring vs
fuzzy shower ring). Systematics: optical absorption and scattering in the medium,
PMT gain/timing calibration, reflection, and light-attenuation time dependence.
**Liquid scintillator.** Much higher light yield (better energy resolution, low
threshold), isotropic light so weaker directional information, quenching for heavy
particles, and scintillator/optical aging.

## Rare-event detectors

**Cryogenic bolometers and phonon detectors.** Deposit -> phonons/heat (and possibly
ionization or light) with sub-keV thresholds; reconstruct energy from the pulse
amplitude, with **discrimination** from the phonon-to-ionization/light ratio (nuclear
vs electron recoil). Limits: threshold and its efficiency, pulse-shape (low-energy noise
events, "excess" backgrounds), and detector-to-detector calibration variation.
**Semiconductor ionization (e.g. germanium)**: excellent energy resolution and
pulse-shape discrimination (single- vs multi-site); dead-layer and surface events at the
edge.
**Dark-matter TPCs and neutrinoless double-beta decay**: search for a rare signal
(peak or nuclear-recoil spectrum) over a tiny background, so **thresholds,
fiducialization, and energy scale** dominate the result.

**Rare-event reconstruction essentials.**
- **Low thresholds and threshold efficiency**: `epsilon(E)` from calibration/pulse
  simulations; the signal is often at the threshold, so a threshold error is a signal
  error.
- **Fiducialization**: the fiducial volume defined by reconstructed position; position
  resolution and wall-event leakage determine the fiducial mass and the residual
  background. Fiducial-mass uncertainty enters the rate limit directly.
- **Yield/quenching model**: electron-equivalent to nuclear-recoil energy conversion
  (a model with uncertainty) maps to the physics variable.
- **Discrimination and background leakage**: leakage fraction versus acceptance measured
  with calibration sources; extrapolation to low energy is the dominant uncertainty.
- **Blind analysis**: masked signal regions ([01](../../hep-analysis/references/01-analysis-design.md)).

### Distinctive but generalizable reconstruction and performance features (rare-event)

- **Topology**: waveform/pulse at the noise floor; few events. **Inverse problem**:
  energy, species, and position of a low-energy interaction with near-zero
  background, on a model-dependent energy scale.
- **Informative residual/closure**: calibration-line energy scale and resolution;
  discrimination leakage versus energy; position reconstruction for uniform sources.
- **Scaling**: threshold `~` noise; resolution `~ 1/sqrt(N_carriers)`; background scales
  with exposure and fiducial mass.
- **Tails**: surface/wall events, pileup, low-energy noise excess.
- **Dependence**: time-dependent noise, temperature stability, purity/lifetime.
- **Strongest data sample**: internal or external calibration sources plus
  side-band/blinded control regions.
- **Transfers**: threshold/fiducial reasoning to any low-statistics search; **does not
  transfer**: collider-style tag-and-probe (no clean high-rate control).

## Astroparticle systems within the same framework

- **Air-shower surface/fluorescence/radio arrays**: sparse distributed sampling; the
  inverse problem is shower axis/core/direction/energy from a partial sample of the
  shower footprint, with **atmospheric monitoring** as a first-class nuisance
  parameter (`theta`) ([32](32-ground-based-detection-arrays.md)). Effective area and
  exposure play the role of acceptance ([21](21-detector-systems-overview.md)).
- **Imaging atmospheric Cherenkov telescopes**: image cleaning, Hillas parameters,
  gamma/hadron separation, PSF, and effective area ([33](33-imaging-atmospheric-cherenkov.md)).
- **Neutrino telescopes in water/ice**: sparse timing geometry, track vs cascade
  hypotheses, angular resolution, **effective volume**, and medium optics (scattering
  and absorption) as dominant `theta` ([34](34-neutrino-astronomy.md)).
- **Space-based direct detection**: spectrometer and calorimeter combination, geomagnetic
  cutoff and solar modulation ([35](35-space-based-direct-detection.md); experiment case
  studies: the bound experiment profile).

## Common misconceptions and failure modes

- **Summing charge and light without recombination.** Anticorrelation means the two
  channels must be combined, not treated as independent.
- **Applying electron-equivalent energy to nuclear recoils.** Quenching/yield differs.
- **Assuming near/far cancellation.** Detector differences and phase-space coverage break it.
- **Fiducial cut uncertainty ignored.** Position resolution and wall leakage map directly
  onto exposure and background.
- **Extrapolating discrimination leakage below calibrated energies.**
- **Kinematic energy quoted as neutrino energy** without the nuclear-effect model.

## Deliverables

- The two (or more) signal channels, the combination rule, and the recombination/lifetime
  correction with its uncertainty.
- The energy scale (electron-equivalent vs nuclear recoil) and its calibration source.
- Threshold efficiency, fiducial volume, and their uncertainties.
- Discrimination leakage versus energy with its calibration sample.
- For neutrino work: containment, the energy-estimator definition, and the near/far
  cancellation assumption.

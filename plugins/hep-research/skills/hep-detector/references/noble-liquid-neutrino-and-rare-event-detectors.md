# Noble-Liquid, Neutrino, and Rare-Event Detectors

Liquid-argon and liquid-xenon TPCs, dual-phase detectors, large water Cherenkov and
liquid-scintillator detectors, neutrino near/far systems, cryogenic bolometers,
semiconductor ionization detectors, dark-matter TPCs, and neutrinoless-double-beta-decay
detectors. Air-shower arrays, imaging Cherenkov telescopes, and neutrino telescopes
are treated in the astroparticle references ([air showers](extensive-air-showers.md) through [multimessenger analysis](multimessenger-analysis.md)) and [neutrino astronomy](neutrino-astronomy.md); experiment specifics come from the bound profile; this file integrates them into the common framework
([detector measurement framework](detector-measurement-framework.md)). Signal formation (recombination,
lifetime, quenching) is in [signal formation and readout](signal-formation-and-readout.md).

## Noble-liquid TPCs

**Signals.** A deposit creates excitation (-> scintillation light, `S1`) and
ionization (-> electrons, `S2` after drift and, in dual phase, extraction and
electroluminescence in the gas). Ionization electrons and scintillation photons
**anticorrelate** through recombination: for fixed deposited energy, more charge means
less light, and the combined estimator `E = W (n_gamma + n_e)` has better resolution than
either alone. `W` is the mean energy per detectable quantum (photon or electron): PDG
quotes (19.5 ± 1.0) eV for liquid argon and the widely adopted (13.7 ± 0.2) eV for liquid
xenon, with recent xenon measurements near 11.5 eV, so state the value used; `n_gamma` and
`n_e` come from `S1` and `S2` through detector-specific gains calibrated with
mono-energetic lines. Recombination depends on `dE/dx` and drift field, giving
electron/nuclear recoil discrimination in the charge-to-light ratio; in argon the
stronger discriminant is the scintillation pulse shape (singlet about 6 ns, triplet about
1500 ns; in xenon 2.2 ns and 27 ns are too close for the same power). The scintillation is
vacuum ultraviolet (about 128 nm in argon, 175 nm in xenon), so argon detectors use a
wavelength shifter such as TPB (PDG RPP 2025, sec. 36, noble liquids).

**Reconstruction.**
- **Pulse finding** in the waveform (`S1`, `S2`, multiple scatters, single-electron
  tails); pairing `S1`-`S2` in the presence of pileup.
- **3D position**: `xy` from the light pattern (dual phase) or charge pattern; `z` from
  the `S1`-`S2` drift time (`z = v_d Delta t`). In single-phase detectors the
  wire/pad readout and the charge-arrival time give 3D once the interaction time `t0`
  is known (from scintillation light, a beam spill or an external trigger); without
  `t0` the drift coordinate is undetermined.
- **Corrections**: electron lifetime (`exp(-t/tau_e)`, purity monitored and updated),
  position-dependent light collection and charge (nonuniformity), field distortions,
  recombination model, and electron-equivalent vs nuclear-recoil energy scales.
- **Topology reconstruction** in large single-phase LArTPC neutrino detectors:
  tracks, showers and vertices from the wire-time images (next subsection).

**Ambiguities.** `S1`/`S2` mis-pairing, wire-plane ambiguity (three planes resolve 2D
projections), diffusion and lifetime uncertainty vs true `dE/dx`, and cosmic pileup in
surface detectors.

**Position from the light pattern (dual phase).** The `xy` of an `S2` comes from the
fraction of light seen by each top-array sensor, fitted with a light-response map; how the
map is derived and why positions near the wall are biased inward are in
[photon likelihood reconstruction](photon-likelihood-reconstruction.md#the-expected-light-model).
Field non-uniformity displaces the drifting electrons, so the reconstructed `S2` position
is mapped back to the interaction position with a field-distortion map, which enters the
fiducial volume.

### Imaging reconstruction in single-phase LArTPCs

The input is the deconvolved charge on each wire versus drift time
([front-end waveform processing](front-end-waveform-processing.md#lar-tpc-signal-processing)),
one two-dimensional image per wire plane.

- **From views to 3D.** Two strategies dominate. *View matching* reconstructs 2D clusters
  in each plane and matches them across planes by their common drift-time range, with many
  small algorithms run in passes for cosmic-ray and neutrino hypotheses (Acciarri et al.,
  Eur. Phys. J. C 78 (2018) 82). It struggles with tracks at nearly constant drift time
  (all hits at one time in every view) and with tracks along one wire direction. *Tomographic
  imaging* solves for the charge in 3D cells consistent with all planes at once, using the
  charge measured on each plane to suppress ghost cells (Qian et al., J. Instrum. 13 (2018)
  P05032). Ghosts remain in dense regions. Both depend on the dead and noisy channel map,
  which breaks tracks or opens gaps.
- **Interaction time.** The drift coordinate needs `t0` from scintillation light, a beam
  spill or an external tagger. At the surface many cosmic tracks fall within each readout
  (drift-time) window, but few within the spill itself, so matching the light to a track
  is how the beam-coincident track is found; removing the rest is the first reconstruction
  step, with its own efficiency for the neutrino interaction.
- **Calorimetry.** Charge per unit length `dQ/dx` is corrected for electron lifetime,
  for space-charge displacement of the position and of the local field, and for the
  channel response, then converted to `dE/dx` with a recombination model (modified Box or
  Birks form, parameters measured at the local field; recombination also depends on the
  track angle to the drift field). The conversion is steep at high
  charge density, so errors grow toward the end of a stopping track. The track pitch on a
  wire grows as the track points along the drift direction (the charge on each wire is
  spread over a long time) or along the wire orientation, where the deconvolved charge is
  least reliable.
- **Momentum and energy.** Range gives the momentum of a contained stopping track (with a
  particle hypothesis); multiple Coulomb scattering, from a likelihood of the deflection
  angles between track segments, gives the momentum of an exiting track (Abratenko et al.,
  J. Instrum. 12 (2017) P10010); showers are measured calorimetrically, with a correction
  for charge lost below threshold.
- **Identification.** For stopping particles, `dE/dx` versus residual range (the Bragg
  peak) separates protons from muons and pions. Electron and photon showers differ in the
  `dE/dx` of their first few centimetres (one minimum-ionizing track versus two from a
  pair conversion) and in the gap between the vertex and a photon shower's start.
- **Failure modes.** Tracks broken at dead regions, merged tracks near the vertex, a track
  direction reversed, and a vertex placed at the wrong end; each has a rate measured in
  simulation and checked on control samples: stopping cosmic muons (Bragg peak and the
  `dE/dx` scale), decay electrons, neutral-pion mass, and crossing tracks for lifetime and
  space charge.

**Check:** The 3D strategy, the `t0` source, the recombination model with its field, the
momentum method for each track class, and the rates of broken, merged and reversed tracks
are stated.

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
- **Transfers**: drift-and-readout reasoning ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md));
  **does not transfer**: gas-TPC diffusion/ion-backflow values.

## Neutrino detectors

**Topologies and energy.** Wire-based or pixel LArTPCs, segmented scintillator, and
water/scintillator volumes reconstruct the final-state lepton and hadrons. Two energy
estimators exist and differ: **calorimetric** (sum of visible energy plus corrections)
and **kinematic** (from lepton angle/energy assuming an interaction type). Neither is
the neutrino energy without a model of **nuclear effects** (Fermi motion, final-state
interactions, missing energy carried by neutrons/undetected particles), so the
`E_reco -> E_nu` migration is model-dependent
([measurements and unfolding](../../hep-measurement/references/measurements-and-unfolding.md)).

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
  ([measurements and unfolding](../../hep-measurement/references/measurements-and-unfolding.md)).

## Water Cherenkov and liquid-scintillator detectors

**Water Cherenkov.** Ring imaging of Cherenkov light by photomultipliers
([cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md)); reconstruct vertex,
direction, energy from **charge/time likelihoods** (per PMT, expected charge and time
given hypothesis `x`, `p(y|x,theta)` ([detector measurement framework](detector-measurement-framework.md)));
**ring counting** and electron/muon separation from ring sharpness (sharp muon ring vs
fuzzy shower ring). Systematics: optical absorption and scattering in the medium,
PMT gain/timing calibration, reflection, and light-attenuation time dependence.
**Liquid scintillator.** Much higher light yield (better energy resolution, low
threshold), isotropic light so weaker directional information, quenching for heavy
particles, and scintillator/optical aging.
The vertex, direction, energy and ring or topology fits of both media, with their seeds,
hypothesis comparisons and per-event errors, are in
[photon likelihood reconstruction](photon-likelihood-reconstruction.md).

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
  (a model with uncertainty, for example Lindhard) maps to the physics variable.
- **Discrimination and background leakage**: leakage fraction versus acceptance measured
  with calibration sources; extrapolation to low energy is the dominant uncertainty.
- **Blind analysis**: masked signal regions ([analysis design](../../hep-measurement/references/analysis-design.md)).

### Pileup and position in cryogenic and germanium detectors

- **Pileup in slow detectors.** A thermal or phonon pulse rises over a long time compared
  with fast scintillator or ionization pulses, so two events closer than the rise time
  merge into one amplitude. Random coincidences scale with the square of the event rate
  times the resolving time; in a double-beta-decay search the coincidences of
  two-neutrino decays can fill the region of interest of the neutrinoless decay. Pileup is
  found by a template fit of the pulse (the optimal filter of
  [front-end waveform processing](front-end-waveform-processing.md#amplitude-and-time-from-sampled-waveforms))
  with a goodness-of-fit or residual test, by a two-pulse fit, or by a faster channel
  such as the light detector of a scintillating bolometer (Chernyak et al., Eur. Phys. J. C
  74 (2014) 2913). The rejection versus pulse separation is measured by superposing
  measured pulses at known separations, not assumed; near threshold, noise triggers and
  pileup with small pulses enter the low-energy event rate. Pileup in fast germanium
  readout is handled by the fast channel of
  [digital pulse processing](front-end-waveform-processing.md#digital-pulse-processing-for-spectroscopy).
- **Position from phonons.** With several phonon sensors, the early (athermal) part of the
  signal is shared among them according to where the energy was deposited, and its arrival
  is delayed in the far sensors; the partition and delay give a position, while the later
  thermal part does not.
- **Position from the charge electrodes.** In ionization-and-heat detectors, interleaved
  electrodes on the surfaces separate events near a surface, whose charge is collected on
  the electrodes of that side only, from bulk events, whose electrons and holes reach the
  fiducial electrodes of opposite sides (Broniatowski et al., Nucl. Instrum. Methods A 559 (2006) 378). The fiducial
  volume that this defines is measured as the fraction of uniformly distributed events
  (cosmogenic activation lines, dissolved or gaseous sources) that pass the cut.
- **Position and topology in germanium.** The current pulse shape depends on where the
  charge is created: the ratio of maximum current to energy separates single-site from
  multi-site events and flags events near the read-out contact and slow events in the
  surface layer (Budjáš et al., J. Instrum. 4 (2009) P10007). The cut is calibrated on
  double-escape peaks (single-site) and full-energy gamma peaks (mostly multi-site) and
  checked for its energy dependence; the discrimination itself is in
  [front-end waveform processing](front-end-waveform-processing.md#pulse-shape-discrimination).
  Segmented detectors add position from which segment collects the charge and from the
  transient signals induced on its neighbours.

**Check:** The pileup resolving time and its rejection efficiency versus pulse separation
are measured with superposed pulses, and the position or fiducial cut states its
observable (phonon partition, electrode charge, pulse shape) and its calibration with
uniformly distributed events or calibration peaks.

### Distinctive but generalizable reconstruction and performance features (rare-event)

- **Topology**: waveform/pulse at the noise floor; few events. **Inverse problem**:
  energy, species, and position of a low-energy interaction with near-zero
  background, on a model-dependent energy scale.
- **Informative residual/closure**: calibration-line energy scale and resolution;
  discrimination leakage versus energy; position reconstruction for uniform sources.
- **Scaling**: threshold `~` noise; resolution `sigma_E/E ≈ sqrt(F/N_carriers) ⊕ noise/E` (`F` the Fano factor, about 0.1 in Si and Ge (PDG); photon counting and recombination in noble liquids are Poisson or worse); background scales
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
  parameter (`theta`) ([ground based detection arrays](ground-based-detection-arrays.md)). Effective area and
  exposure play the role of acceptance ([detector systems overview](detector-systems-overview.md)).
- **Imaging atmospheric Cherenkov telescopes**: image cleaning, Hillas parameters,
  gamma/hadron separation, PSF, and effective area ([imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md)).
- **Neutrino telescopes in water/ice**: sparse timing geometry, track vs cascade
  hypotheses, angular resolution, **effective volume**, and medium optics (scattering
  and absorption) as dominant `theta` ([neutrino astronomy](neutrino-astronomy.md)).
- **Space-based direct detection**: spectrometer and calorimeter combination, geomagnetic
  cutoff and solar modulation ([space based direct detection](space-based-direct-detection.md); experiment case
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
- For LArTPC topology reconstruction: the 3D strategy, the dead-channel map used, the
  momentum method per track class, and the identification variables with their control
  samples.
- The energy scale (electron-equivalent vs nuclear recoil) and its calibration source.
- Threshold efficiency, fiducial volume, and their uncertainties.
- For cryogenic and germanium detectors: the pileup resolving time and rejection efficiency,
  and the position or fiducial observable with its calibration.
- Discrimination leakage versus energy with its calibration sample.
- For neutrino work: containment, the energy-estimator definition, and the near/far
  cancellation assumption.

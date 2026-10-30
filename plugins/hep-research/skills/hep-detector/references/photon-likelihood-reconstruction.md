# Photon-Counting Likelihood Reconstruction

Covers the reconstruction shared by detectors that record many photosensor hits (charge and
arrival time) from light emitted in a large medium: water Cherenkov detectors, liquid
scintillators, neutrino telescopes in ice or water, position reconstruction from the light
pattern in dual-phase noble-liquid TPCs, and pixel-template fits of imaging atmospheric
Cherenkov telescopes. One likelihood structure serves all of them; what differs is the
expected-light model and its nuisance parameters. The estimator families and their common
issues (seeds, hypotheses, per-event errors) are in
[detector measurement framework](detector-measurement-framework.md#choosing-the-estimator);
photosensor response in [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md#photosensors-and-light-transport);
the detector families in [noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md),
[neutrino astronomy](neutrino-astronomy.md) and [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md).
Ring-imaging PID (RICH, DIRC, TOP) uses the same photon-counting logic and is covered in
[particle identification](particle-identification.md#ring-imaging-cherenkov-detectors-rich).

## The per-channel likelihood

The event hypothesis `x` (vertex, time, direction, energy, topology) predicts, for every
photosensor `i`, an expected number of photoelectrons `mu_i(x, theta)` and a distribution
of their arrival times. The likelihood multiplies over **all** channels:

    L(x) = prod_{hit i} P(q_i | mu_i) f(t_i | x, mu_i)  *  prod_{unhit j} P(no hit | mu_j)

- **Charge term.** The photoelectron count is Poisson with mean `mu_i` plus the dark-noise
  mean; the recorded charge folds that count with the single-photoelectron response (gain
  spread, under-amplified photoelectrons). Saturated channels carry a lower bound only:
  treat them as censored or drop them, never as measured values.
- **Unhit channels.** `P(no hit)` is the probability of zero photoelectrons plus the
  probability that the signal stayed below threshold. Leaving unhit channels out discards
  the information that light was *not* seen where a wrong hypothesis predicts it, and is a
  common source of biased vertices near the detector boundary. Only live, enabled channels
  count as unhit: dead or disabled channels are excluded, never treated as unhit. The hit
  and unhit terms use the same threshold model, so for each channel the probabilities of a
  hit and of no hit sum to one.
- **Time term.** Define the residual `t_res = t_i - t_geo`, where `t_geo` is the arrival
  time of unscattered light from the hypothesis, computed with the group refractive index
  for propagation and the phase index for the Cherenkov angle (the two differ noticeably
  in ice and water). The `t_res` distribution has a prompt peak (width
  from the photosensor transit-time spread, chromatic dispersion and the emission time
  profile), a late tail from scattering and reflection, and a flat component from dark
  noise. Early hits beyond the prompt peak come from noise, photosensor pre-pulses, other
  particles in the same event, or a wrong hypothesis. Per-channel time offsets are
  calibration constants, and their error is a nuisance parameter.
- **Several photons on one channel.** With single-time readout (a TDC or first threshold
  crossing) the recorded time is that of the first photoelectron. For a
  single-photon time density `f` with cumulative `F` and Poisson mean `mu`, the first
  arrival follows `f_1(t) = mu f(t) exp(-mu F(t)) / (1 - exp(-mu))` (exact under the Poisson
  assumption), which is earlier and narrower than `f`. A recorded first hit can also be a
  noise hit, so the noise rate is included: `mu` is the total mean number of above-threshold
  photoelectrons in the readout window (signal plus noise), and `f` and `F` are the
  corresponding normalized mixture density over the window and its cumulative. Using `f`
  for bright channels biases
  the fit; using `f_1` with a wrong `mu` does too. With waveform digitization the
  likelihood can instead use the whole pulse series, for example as Poisson counts in time
  bins.
- **Channel independence.** The product over channels assumes independent channels.
  Correlated noise and afterpulsing break that assumption and must be removed or modelled
  before the fit.

**Check:** The likelihood includes live unhit channels and excludes dead ones, handles
saturated channels as censored, and for single-time readout evaluates the first-photon time
density with the total expected `mu` (signal plus noise) of every hit channel.

## The expected-light model

`mu_i(x, theta)` and the time density are the forward model, and nearly every systematic of
the method lives in them:

- **Analytic models** suit a clear, uniform medium: emission geometry (the Cherenkov cone,
  or isotropic scintillation), attenuation, the sensor's angular acceptance and solid
  angle, and reflections from detector surfaces. They are fast and smooth, which helps the
  minimizer.
- **Tabulated models** (photon tables or smooth fits to them, from photon-propagation
  simulation) are needed when scattering dominates or the medium is non-uniform, as in
  natural ice or water. Their errors are the grid granularity, the interpolation, and the
  optical model behind them. The medium near the sensors can differ from the bulk (a
  refrozen or disturbed layer, biofouling, deposits), which changes the angular acceptance.
- **Emission time profile.** Cherenkov light is prompt; scintillation has rise and decay
  components that broaden the time density and depend on particle type. The profile is a
  calibrated input, not a constant.
- **Data-driven response maps.** For position reconstruction from a light pattern (for
  example the top array of a dual-phase TPC), the expected fraction per sensor versus
  position (a light-response function) is often derived iteratively from calibration events
  of known, uniform spatial distribution, so that the map does not depend on the optical
  simulation. Near the wall the pattern is truncated at the edge of the sensor array and
  flattened by reflections, so positions are biased inward and the bias must be mapped
  before the fiducial cut.

The optical parameters (absorption and scattering lengths and their depth or time
dependence, reflectivities, sensor efficiencies) are the nuisance parameters `theta` of
this method; how fixed and varied nuisance parameters enter is in
[detector measurement framework](detector-measurement-framework.md#choosing-the-estimator).

**Check:** The expected-light model is named (analytic, tabulated, or data-driven), its
optical parameters are listed with their source, and the optical systematic is evaluated by
coherent variation.

## Seeding and the fit sequence

The likelihood is multimodal, so reconstruction proceeds in stages:

1. **Hit cleaning and splitting.** Remove isolated and out-of-window hits (time windows,
   coincidences between neighbouring sensors), and split coincident uncorrelated events
   before fitting. Cleaning also removes some late scattered light, so the
   time density used in the fit must describe the cleaned hits.
2. **First guess.** A moment or geometric estimate: hit-charge centroid and time for a
   point-like source, or a straight-line fit of hit position against time for a track,
   which ignores the emission geometry (Ahrens et al., Nucl. Instrum. Methods A 524 (2004)
   169).
3. **Likelihood fit** from the first guess and from several perturbed or mirrored starts.
4. **Hypothesis fits**: the same event refitted under each topology or species hypothesis.

The characteristic failures are wrong local minima and merged events. For tracks, a minimum
near the reversed direction, and coincident muons fitted as one track, turn down-going
atmospheric muons into up-going candidates in a neutrino telescope, a large background of
an up-going selection until quality cuts remove it
([neutrino astronomy](neutrino-astronomy.md#backgrounds)). For point-like sources it is a
vertex reflected through the detector centre or pulled toward a cluster of noise hits.
Event splitting and refits that compare likelihoods (up-going versus a
down-going-constrained fit) are the usual defences; their efficiency belongs in the
efficiency chain.

**Check:** The fit records its seeds and the minimum reached, and the rate of wrong minima
(in particular reversed tracks) is measured in simulation and in a data control sample.

## Topologies and hypothesis comparison

- **Point-like versus extended.** A localized shower and a long track predict different
  light patterns; two cascades separated along a short flight path (a double-pulse or
  double-bang topology) are a further hypothesis fitted within the same event; each
  hypothesis is fitted and the likelihoods are compared.
- **Ring patterns.** In water Cherenkov detectors a muon gives a sharp-edged ring and an
  electron or photon shower a diffuse one, so per-hypothesis likelihood fits separate them.
  Neutral pions appear as two photon rings, which also gives an invariant-mass closure.
  Multi-ring events need a ring count, and the number of combinations grows quickly with it;
  one approach fits successively added rings within the full charge and time likelihood,
  rather than accepting rings from a separate ring finder (Jiang et al., Prog. Theor. Exp.
  Phys. 2019 (2019) 053F01).
- **Delayed signals.** A muon decay electron or a neutron capture, microseconds to
  hundreds of microseconds later, is a separate subevent; the subevent search is part of
  the reconstruction and has its own efficiency.

Hypothesis comparison as a classifier is treated in
[detector measurement framework](detector-measurement-framework.md#choosing-the-estimator).

**Check:** Each topology or species decision states the hypotheses fitted, the decision
variable, and its efficiency and mis-identification from simulation validated on data.

## Energy

- **Point-like deposits.** Energy follows from the total expected light that fits the
  observed pattern, not from the raw charge sum, so that the position dependence (distance
  to sensors, attenuation, shadowing) is corrected by the forward model. The result is a
  visible or electromagnetic-equivalent energy; the conversion to the physics variable
  (hadronic content, invisible energy, a neutrino energy) is a separate, model-dependent
  step ([noble liquid neutrino and rare event detectors](noble-liquid-neutrino-and-rare-event-detectors.md#neutrino-detectors)).
- **Liquid scintillator.** The light yield is non-linear in deposited energy (Birks-type
  quenching, plus a Cherenkov component that depends on particle type and energy;
  [signal formation and readout](signal-formation-and-readout.md#light-scintillation-wavelength-shifting-attenuation)),
  and position-dependent. The calibration sources are mostly gamma emitters, whose response
  differs from that of electrons and positrons through Cherenkov light and quenching of the
  secondaries, so the non-linearity model, fitted to gamma sources and beta spectra, carries
  the step from gamma to electron response. A non-uniformity map from sources at several
  positions carries the position dependence, and the readout's charge non-linearity is
  calibrated separately; the residual of each is a systematic of the spectrum.
- **Muon tracks.** Above the muon critical energy (where radiative losses equal ionization;
  of order a TeV in water and ice) the energy loss rate grows with energy but is
  dominated by stochastic losses, so the light along the track estimates the muon energy at
  the point where it is seen, with large fluctuations. Robust estimators use a truncated
  mean over track segments or unfold the loss profile along the track (Aartsen et al., J.
  Instrum. 9 (2014) P03009). For a through-going track it is on average below the muon
  energy at production and only weakly constrains the neutrino energy. Well below the muon
  critical energy ionization dominates and the light per length is nearly constant, so
  range is the estimator for a contained muon; between roughly a hundred GeV and the critical
  energy the light depends only weakly on energy and the muon is often not contained in the
  instrumented volume, so its energy is poorly constrained.

**Check:** The energy estimator states what energy it returns (visible, electromagnetic-
equivalent, muon energy in the detector), its non-linearity and non-uniformity corrections,
and the model step to the physics variable.

## Per-event uncertainty and quality

The general rules (curvature errors, pulls, per-event normalized quality) are in
[detector measurement framework](detector-measurement-framework.md#choosing-the-estimator).
Specific to this method: the directional error is usually taken from a scan of the
likelihood around the best direction with a fitted (for example paraboloid) contour, or from
resampling the hits, and its pulls are binned in energy and topology, since a constant
rescaling is acceptable only if the pull width is flat in both. Useful quality variables
are: the minimum of `-ln L` divided by a stated count, often called per degree of freedom
(for example hit channels minus fitted parameters, although the likelihood also runs over
unhit channels), a crude normalization with no reference distribution whose energy and
topology dependence is calibrated on simulation; the number of hits with small time
residual; the track length inside the instrumented volume; and the agreement between
independent fits.

**Check:** The per-event angular or position error is validated with pulls binned in
energy and topology, and every quality variable used in a selection is compared between data
and simulation.

## The image-template variant

An imaging atmospheric Cherenkov telescope array can fit the camera images directly: each
pixel's charge is compared with an expected image from a library of simulated showers
indexed by energy, impact distance, depth of shower maximum, zenith angle and source
offset, with a pixel
likelihood that includes night-sky-background noise and the single-photoelectron response
(Parsons and Hinton, Astropart. Phys. 56 (2014) 26). It is the same structure as above, with
a tabulated, simulation-driven expected-light model, so it uses more of the image than
moment-based parameters ([imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md#the-technique))
and inherits the simulation's description of hadronic and electromagnetic showers, of the
atmosphere and of the telescope optics. A moment-based reconstruction is its natural seed
and its cross-check.

**Check:** A template fit names the template library, its axes and interpolation, the
pixel noise model, and the moment-based reconstruction it is compared with.

## Validation specific to this method class

Generic validation is in [reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md);
for photon-likelihood methods the useful data handles are:

- **Light and timing calibration:** pulsed light sources and calibration lasers for
  single-photoelectron response and timing offsets, and radioactive sources at known
  positions for response maps and the energy scale.
- **Natural control samples:** through-going and stopping muons (track direction, length,
  light yield per length), decay electrons from stopped muons (an energy endpoint), and
  neutral-pion invariant mass where photon pairs are reconstructed.
- **Pointing (detectors of cosmic-ray muons or showers):** the Moon's shadow in the
  cosmic-ray flux, corrected for the geomagnetic deflection of the primaries, tests the
  absolute pointing and the angular resolution in data; the Sun's shadow is distorted by the
  solar magnetic field and changes with the solar cycle.
- **Distributions of the fit inputs:** data and simulation time-residual distributions,
  per-channel occupancy and charge, compared in the same selection, before any conclusion
  is drawn from the fitted quantities.

**Check:** Timing, response-map and energy-scale calibrations name their sources, and the
time-residual and occupancy distributions are compared between data and simulation.

## Common misconceptions and failure modes

- **Unhit channels left out** of the likelihood, losing the boundary information.
- **Single-photon time density used for bright channels**, biasing the vertex and time.
- **Raw charge sum quoted as energy** without the position-dependent forward model.
- **Optical parameters varied one at a time per event** instead of coherently over the
  sample.
- **Reversed-track misreconstruction neglected** in an up-going selection.
- **Hessian errors trusted for few-photon events** without a pull check.
- **Template fit treated as simulation-independent.** It is as good as the shower,
  atmosphere and optics simulation behind its library.

## Deliverables

- The likelihood written out: charge model, time density (single or first photon), noise
  and threshold treatment, unhit and saturated channels.
- The expected-light model, its optical parameters and their sources, and the coherent
  variations used for the systematic.
- Hit cleaning, first guess, seeds and the measured rate of wrong minima.
- Hypotheses fitted and the efficiency and mis-identification of each decision.
- The energy estimator, what energy it returns, and its non-linearity and non-uniformity
  corrections.
- Per-event uncertainty with its pull validation, and the data/MC comparison of every
  quality variable used.

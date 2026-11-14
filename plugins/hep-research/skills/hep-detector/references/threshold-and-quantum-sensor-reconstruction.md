# Threshold, Single-Quantum and Superconducting Sensors: Reconstruction

Owner: hep-detector. This page gives reconstruction method text for three device families that the general pages
do not cover: superconducting photon sensors (nanowire single-photon detectors and kinetic inductance detectors),
superheated bubble chambers and droplet detectors, and few-electron (Skipper) CCD readout. Every method statement
comes from a source read on 2026-11-06 and is scoped to the device or experiment that source describes; it is not a
family-wide method. Sources and their read levels are under [Sources read](#sources-read): a source read at `page`
level supports only its named sections. Where no source read gives a method, the text says "no method text: no
source read", and that stays a gap.

What this page does not establish: no tool in this plugin implements these methods, nothing here was run, and no
statement is a quality or validation claim. Numbers are as printed in the source; figures were not viewed, only
captions. General reconstruction structure is in [event reconstruction](event-reconstruction.md); the estimator
choice in [detector measurement framework](detector-measurement-framework.md#choosing-the-estimator); conventional
pixel and CCD tracking in [tracking and vertexing](tracking-and-vertexing.md) and
[gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md).

The variant is a fact to establish, never inferred from a word such as "superconducting": a nanowire detector and a
kinetic inductance detector do not share a noise or an energy model, and a bubble chamber and a droplet detector do
not share a readout.

## Superconducting nanowire single-photon detectors

<!-- example: source citation (devices and experiments named as the source of a method) -->
Scope: laboratory infrared photon counting, from one review read at `page` level (Natarajan et al. 2012). Use as a
particle detector is not covered.

- **Signal extraction** (secs. 1.2, 2.2.1, 2.2.2). The wire is DC-biased just below its critical current `I_c`; an
  absorbed photon forms a hotspot that becomes a resistive barrier, and a voltage pulse appears across the load. The
  review models it as a circuit with the kinetic inductance `L_k` and a time-dependent normal resistance `R_n(t)`:
  a rise time `tau_1` and a recovery time `tau_2`. The output is one count per pulse.
- **Finding and association.** No method text: no source read. The sections read name time-correlated
  single-photon counting (TCSPC) and coincidences only, and assume the electronics register every pulse; no
  discriminator or window method is given (secs. 2.2.4, 3.1).
- **Parameter estimation, photon number** (secs. 1.2, 2.3.6). Only multi-element devices resolve photon number:
  parallel elements with series resistors give a pulse height that scales with the number of elements fired, and
  interleaved elements can be read out separately. A plain meander is not a photon-number device, and the review
  states that the low-bias multiphoton regime is much less efficient.
- **Time** (sec. 2.3.8, Fig. 3(c) caption). Jitter is measured with TCSPC against an ultrafast laser: a Gaussian
  fit to the instrument response, quoted as FWHM. A non-uniform wire gives different hotspot resistances and rise
  times, which broadens the jitter. Position is not covered.
- **Energy** (sec. 2.2.3, end). Not applicable for the single-wire device reviewed: the photon energy is negligible
  against the energy stored in `L_k`, and energy or photon-number information is lost to Joule heating of the
  hotspot. Never assign an energy to a count.
- **PID or topology.** No method text: no source read. The polarization dependence of sec. 2.3.7 is a response
  effect, not an identification.
- **Uncertainty and quality** (secs. 1.2, 2.2.2, 2.3.4, 2.3.8). System detection efficiency is the product of
  coupling, absorption and registering efficiencies; the review warns that reports differ in which efficiency they
  quote, so the device detection efficiency is not the system detection efficiency. The dark count rate rises
  exponentially as the bias approaches `I_c` and is measured per device. The dead time is of order `tau_2`; if the
  recovery is made too fast the device latches, with no detection until the bias is lowered.
<!-- /example -->

Failure modes: stray light or electrical noise mimics a pulse (dark count); a device detection efficiency quoted as
system efficiency; a latched state read as zero signal; photon number claimed from a plain meander.

No method text, no source read: particle (non-photon) detection; array multiplexing (RSFQ and
amplifier-discriminator chains are named in sec. 2.4.3 without a method); pulse discrimination and count-loss
correction near the dead time; spatial readout; other superconducting photon sensors.

## Kinetic inductance detectors (KID, MKID)

<!-- example: source citation (devices and experiments named as the source of a method) -->
Scope: two millimetre-wave array studies of cryogenic response to cosmic rays, both read in full: a
frequency-multiplexed FPGA readout for up to twelve resonators (Bourrion et al. 2013) and a dark-array cosmic-ray
test with about 960 pixels per chip (Karatsu et al. 2019). Neither is an analysis of photon pulses.

- **Signal extraction** (Bourrion et al., MKID instrumentation and firmware sections). A frequency comb is
  up-converted by IQ mixing; each tone is digitally down-converted with a CIC and FIR low-pass chain, giving I and Q
  per tone, from which amplitude and phase (and a frequency shift `delta f`) follow. Pre-trigger samples give the
  baseline. Resonances must be far enough apart for the channel filter, or crosstalk follows; switching-supply
  spikes appeared at multiples of 320 kHz.
- **Finding and association** (Bourrion et al., firmware; Karatsu et al.). Online: `I^2 + Q^2` against one threshold
  per resonator. Offline (Karatsu et al.): an iterative second-derivative search at 5 sigma, with the next 3
  `tau_qp` counted as one event; the largest glitches are removed first so that the rms reflects noise only. The
  3 `tau_qp` window is an event-counting rule, not a pileup treatment.
- **Parameter estimation** (Karatsu et al.). A single exponential fitted to glitch tails gives the quasiparticle
  lifetime `tau_qp`; dead-time and rate estimators follow from the glitch list. Resonators with overlapping
  resonances or failed fits are dropped (about 20% in that study).
- **Space and time** (Bourrion et al., performance section and Fig. 1 caption; Karatsu et al.). Qualitative only:
  the relative arrival of the phonon signal across pixels, and a rough location from the resonator index through
  the design frequency encoding. No beam mapping was done, so the resonator index is not a calibrated position.
- **Energy** (Bourrion et al., introduction and event-trace caption). Principle only: Bourrion et al. state,
  citing work not read here, that the frequency shift is proportional to the deposited energy (the generated
  quasiparticles) for a phonon-mediated thin film, and they use pulse amplitude for spectra. No calibrated energy is
  shown. Raw amplitudes are not comparable across resonators, because resonance depth and transfer function differ;
  energy below the pair-breaking threshold `2 Delta` is invisible (Karatsu et al.).
- **Event class** (Karatsu et al., Fig. 3 caption). An event seen by more than ten pixels at once is taken as a
  cosmic-ray event. This is an event class, not a particle type; isolated events on a few pixels in one chip were
  poorly understood.
- **Uncertainty and quality** (Karatsu et al., Table 1; Bourrion et al., electronics requirements). Dead-time
  fraction = glitch points x readout step / observation time; event rate per pixel; dark noise-equivalent power and
  `tau_qp` as array checks; a signal-to-noise target for the readout. A dead time scaled from another array is a
  scaling, not a measurement.
<!-- /example -->

Failure modes: crosstalk from resonances too close for the filter; single-pixel event counts that change strongly
with the threshold; amplitude compared across resonators without a per-resonator transfer function; the resonator
index read as a position.

No method text, no source read: photon pulses (single-photon or energy-resolving optical/UV); energy calibration
from `delta f` (Bourrion et al. defer the physical interpretation); resonance drift and tracking; pileup; operating
point and readout power; a channel-mixing correction for the multiplexed response (only the per-resonator threshold
and the crosstalk condition are given); a phase-noise model (only the rms of the time stream).

## Superheated bubble chambers and droplet detectors

<!-- example: source citation (devices and experiments named as the source of a method) -->
Scope: two low-background dark-matter devices. PICO-60 with C3F8 is a bubble chamber with optical, acoustic and
pressure readout, read in full (PICO Collaboration 2019). The PICASSO superheated droplet modules (droplets in a
polymer, acoustic only) were read at `page` level: sections 1, 2, 5 and 10, the starts of 6 and 8, the last paragraph
before section 3 and the end of section 9 (PICASSO Collaboration 2005). Neither scope transfers to the other without
saying so.

- **Signal extraction** (PICO: Experimental Method, Data Analysis; PICASSO: sec. 5). PICO: cameras at 340 Hz into
  ring buffers, with the entropy of frame differences as the bubble trigger; piezoelectric acoustic sensors; a fast
  pressure sensor. PICASSO: the piezo waveform on a 1 MHz digitizer, 15 ms re-trigger rejection, a 40-130 kHz
  filter and a time-frequency map integrated to a variable `Q`. The `Q` cut is nearly fully efficient at medium and
  high amplitude and about 50% efficient close to threshold.
- **Finding and association** (PICO: Data Analysis; PICASSO: sec. 5). PICO: the image trigger; bubble
  multiplicity from the rate of pressure rise; a bubble followed over up to nine frames in 30 ms; wall events tagged
  by motion 10 degrees or more from vertical; near-surface events need both cameras within 30 ms. Bubble motion in
  frames is not a particle track. PICASSO: an event when one transducer is above threshold, with all channels read.
- **Parameter estimation** (PICO: Bubble Nucleation Threshold, Data Analysis; PICASSO: sec. 2). The threshold
  follows from temperature and pressure (Seitz model). PICO fits monotonic piecewise-linear efficiency curves to
  neutron calibration by MCMC, and normalizes the acoustic parameter (AP) per thermodynamic condition; thresholds
  without comprehensive recoil calibration were left out of the search. PICASSO uses a sigmoid detection
  probability `P(E_dep, E_th)` with a fitted steepness.
- **Position** (PICO: Experimental Method, Data Analysis). Stereo cameras, sub-pixel positions, a correction for
  image shifts, and a per-camera weight by image quality (failed LEDs and off-centre images degrade it). The
  incident particle's direction is not measured.
- **Energy** (PICO: conditions table, Bubble Nucleation Threshold; PICASSO: secs. 2, 5). The identifiable quantity
  is the threshold, with its efficiency curve; there is no energy per bubble. PICASSO's acoustic amplitude follows
  droplet size, position, solid angle and transducer response, so it is not an energy. A PICO caption notes that
  higher-energy alphas give larger acoustic signals; that is not an energy measurement.
- **PID and topology** (PICO: Introduction, Experimental Method, Background estimates, WIMP search results). The
  acoustic parameter separates alphas from nuclear recoils; multi-bubble events tag neutrons; alpha decay chains are
  also seen by their time signature. The acceptance region was set from calibration before unmasking. At PICO's
  three lowest thresholds, gamma-induced recoils are indistinguishable acoustically.
- **Uncertainty and quality** (PICO: Background estimates, WIMP search results; PICASSO: secs. 5, 8). Live time and
  efficiency-corrected exposure, tracked per thermodynamic condition; background from simulation, calibration and
  the multi-bubble rate; a profile likelihood over efficiency surfaces. Where the multi-bubble rate exceeds
  simulation, the background is left unconstrained. PICASSO: trigger acceptance measured with a second transducer,
  times the `Q` acceptance, per detector; above about 72 C spontaneous nucleation makes the modules unstable.
<!-- /example -->

Failure modes: acoustic amplitude read as energy; bubble motion read as a particle track; a period that was not
live read as "no bubble"; alpha rejection used at a threshold that was not calibrated or is gamma-dominated; poor
near-surface positions without the two-camera requirement.

No method text, no source read: droplet detectors with optical readout (visual counting is only mentioned);
droplet localization by piezo (claimed possible, not described); droplet multiplicity; optical-acoustic association
(deferred to a paper not read); overlapping bubbles; image finding beyond the trigger entropy; a threshold scan as
an analysis method; a gamma response model (under development in the source); other chamber fluids (named only).

## Few-electron and Skipper-CCD readout

<!-- example: source citation (devices and experiments named as the source of a method) -->
Scope: two Skipper-CCD studies at low temperature, one device each, both read in full (SENSEI Collaboration 2017
and 2021). Conventional CCDs without repeated samples are pixel sensors: see
[tracking and vertexing](tracking-and-vertexing.md#sensor-technologies). This readout does not claim tracks.

- **Signal extraction** (2017: Technical description, Signal processing). The charge of one pixel is sampled
  non-destructively `N` times and averaged; the noise falls as `sigma_1 / sqrt(N)`, and `N` is configurable per
  pixel. The paper notes correlated noise from switching supplies and a slight deviation from `1/sqrt(N)` at `N`
  around 2000 and above.
- **Finding and association** (2021: Empirical model, Results, Appendix; pixel level). Single-electron pixels are
  counted after a selection with edge and halo masks (the masks are defined in an earlier paper not read). Charge
  jumps between groups of samples are searched for at 5 standard deviations; above 100 electrons a jump is treated
  as a high-energy hit, not charge generation. Cluster finding is not covered.
- **Parameter estimation, charge state** (2017: Impact of dark current, Fig. 1). The averaged charge shows integer
  peaks; each pixel is classified to the nearest integer and kept within 3 sigma of one. The paper gives the
  misclassification probability from Gaussian noise; at a noise near 0.14 electrons rms the cut that suppresses the
  tail of the dark bin costs efficiency.
- **Position and exposure** (2021: Dark current, Amplifier light). Pixel exposure differs with readout order: the
  last pixel read is exposed for an extra readout time, and the mean readout term is `lambda_DC / 2`. Assuming equal
  exposure is wrong; averaging the amplifier-light rate is too, since it is localized. No event time within an
  exposure is measured.
- **Energy** (2017: Particle physics section). Electrons convert to an electron-recoil energy with an assumed pair
  energy (3.6 eV per extra pair above the gap). For nuclear recoils the ionization efficiency is not accurately
  known at low energies, so a charge state is not a nuclear-recoil energy.
- **Origin of single-electron events** (2021: Semi-empirical model, Transfer curves). Dark current, amplifier light
  and spurious charge are separated by their dependence on exposure time, readout time and position; spurious
  charge is exposure-independent and comes from clocking. Extrinsic dark current is in principle indistinguishable
  from intrinsic.
- **Uncertainty and quality** (2021: Transfer curves, Results, Appendix; 2017: Impact of dark current). Linear fits
  of the single-electron rate against exposure and readout time; a supply-voltage scan for amplifier light; a
  Poisson model of dark counts; a misclassification check. Quadrants with excess single-electron events or high
  charge-transfer inefficiency were dropped; the origin of the jumps is not settled.
<!-- /example -->

Failure modes: equal pixel exposure assumed; a charge state claimed from a CCD without repeated samples; the
assumed pair energy applied to nuclear recoils; correlated sample noise ignored.

No method text, no source read: other discrete-quanta semiconductor sensors (one footnote only); cluster finding
and pixel grouping; charge-transfer-inefficiency correction (only quadrant exclusion); gain calibration from peaks
to electrons ("stable linear gain" stated, no procedure); a sample-correlation model beyond the `sqrt(N)` check; a
nuclear-recoil energy response; charge diffusion across pixels and depth; zero/one-electron confusion measured on
data (only Gaussian-noise probabilities); a spatial model of amplifier light.

## Sources read

<!-- example: source citation (devices and experiments named as the source of a method) -->
Each source was read on 2026-11-06 from its arXiv e-print. Identifiers are as recorded when reading. `full-text`:
the whole body was read; `page`: only the sections named.

- C. M. Natarajan et al., "Superconducting nanowire single-photon detectors: physics and applications" (2012),
  arXiv:1204.5560, DOI 10.1088/0953-2048/25/6/063001. `page`: abstract, secs. 1.2, 2.2.1, 2.2.2, end of 2.2.3,
  2.2.4, 2.3.3, 2.3.4, 2.3.6-2.3.8, 2.4.3, 3.1, Figs. 2 and 3 captions.
- O. Bourrion et al., "High speed readout electronics development for frequency-multiplexed kinetic inductance
  detector design optimization" (2013), arXiv:1310.5891, DOI 10.1088/1748-0221/8/12/C12006. `full-text`.
- K. Karatsu et al., "Mitigation of Cosmic Ray Effect on Microwave Kinetic Inductance Detector Arrays" (2019),
  arXiv:1901.02387, DOI 10.1063/1.5052419. `full-text`.
- PICO Collaboration, "Dark Matter Search Results from the Complete Exposure of the PICO-60 C3F8 Bubble Chamber"
  (2019), arXiv:1902.04031, DOI 10.1103/PhysRevD.100.022001. `full-text`.
- PICASSO Collaboration, "Response of Superheated Droplet Detectors of the PICASSO Dark Matter Search Experiment"
  (2005), arXiv:physics/0508098, DOI 10.1016/j.nima.2005.09.015. `page`: abstract, secs. 1, 2, 5, start of 6, start
  of 8, 10, the last paragraph before sec. 3 and the end of sec. 9.
- SENSEI Collaboration, "Single-electron and single-photon sensitivity with a silicon Skipper CCD" (2017),
  arXiv:1706.00028, DOI 10.1103/PhysRevLett.119.131802. `full-text`.
- SENSEI Collaboration, "SENSEI: Characterization of Single-Electron Events Using a Skipper-CCD" (2021),
  arXiv:2106.08347, DOI 10.1103/PhysRevApplied.17.014022. `full-text`.
<!-- /example -->

**Done when:** the device variant is stated, every method used is one of those above with its source section, and
each quantity a source does not support (an energy from a count, a per-bubble energy, a nuclear-recoil energy from
charge, a position from a resonator index) is reported as unknown.

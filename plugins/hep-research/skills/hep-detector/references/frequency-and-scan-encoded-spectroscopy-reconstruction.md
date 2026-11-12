# Frequency- and Scan-Encoded Spectroscopy: Reconstruction

Owner: hep-detector. This page gives reconstruction method text for three readout families that the general pages
do not cover: cyclotron-radiation emission spectroscopy (CRES), resonant and coherent-field readout (haloscopes),
and retarding and scan-encoded spectroscopy. Every method statement comes from a source read on 2026-11-06 and is
scoped to the experiment or study that source describes; it is not a family-wide method. Sources and their read
levels are under [Sources read](#sources-read): a source read at `page` level supports only its named sections.
Where no source read gives a method, the text says "no method text: no source read", and that stays a gap.

What this page does not establish: no tool in this plugin implements these methods, nothing here was run, and no
statement is a quality or validation claim. Numbers are as printed in the source; figures were not viewed, only
captions. The physics inference on the outputs (a neutrino-mass fit, a coupling limit) belongs to hep-statistics
and hep-theory; this page stops at the reconstructed spectrum or candidate list. Timestream-to-map radiometers,
which share the setting-axis rule below, are in [timestream to map reconstruction](timestream-to-map-reconstruction.md).

Two rules hold across these families. The frequency or setting axis (downmix offset, window centre, sign, bin
sizes, the map between setting and physical quantity) is a fact to establish, never inferred. And raw intervals per
setting are the input: an average over settings that drops the time or the conditions is not a substitute, except
where a source below combines them under stated conditions.

## Cyclotron-radiation emission spectroscopy

<!-- example: source citation (experiments named as the source of a method) -->
Scope: Project 8 only. Phase I (rectangular waveguide, 83mKr) and Phase II (circular waveguide, 83mKr and T2). The
2022 tritium letter (arXiv:2212.05048) was read in full; the 2023 paper (arXiv:2303.12055) and the 2017 Phase I
paper (arXiv:1703.02037) at `page` level. Outputs are a start frequency per event and a binned spectrum. No other
CRES apparatus was read.

- **Signal extraction** (2212.05048 apparatus paragraphs, spectrogram caption; 2303.12055 Radio-frequency system).
  Amplify, downmix and digitize; an FPGA FFT in three tunable windows; a spectrogram; a trigger on bin SNR, with
  `SNR = bin power / mean bin power`. Using SNR instead of absolute power in trigger, reconstruction and spectrum
  analysis avoids amplifier and filter gain variation. Weak resonant cavity modes from residual reflections change
  the response with trap position and frequency.
- **Finding and association** (2212.05048 reconstruction paragraph; 2303.12055 Electron event properties;
  1703.02037 Results). High-SNR bins are clustered into frequency-time tracks; tracks close in time are grouped as
  one event, so chirped tracks with frequency jumps from gas collisions belong to one electron. In Phase I, segments
  above 6 dB SNR, the next segment beginning where the previous ended. The first visible track is not always the
  true first track: a track can be too short or too weak.
- **Parameter estimation** (2303.12055 Electron event properties, CRES energy spectrum model, Bayesian analysis
  procedure; 2212.05048 full-model equation). The start frequency of the first track; a binned spectrum model
  `S = eps (Y * R_PSF)` with `R_PSF = sum_j A_j (I * L^{*j})`, the scatter amplitudes `A_j`, the instrumental
  resolution `I` and the energy-loss function `L`; Bayesian fits for tritium (2303.12055 Bayesian analysis
  procedure). A fit that ignores the scatter peaks misses the low-energy tail from undetected
  first tracks.
- **Space and direction.** No method text: no source read. The sections read (and a keyword search for pitch
  angle) give no position or pitch-angle estimator per event, only a Phase I cut on event start against trigger
  time; pitch and radius enter through simulation and efficiency. A frequency-time track is not a spatial track.
- **Energy** (2212.05048 energy-to-frequency equation; 2303.12055 Test of the frequency-energy relation; 1703.02037
  CRES section). `f_c = |e| B / (2 pi (m_e + E_kin / c^2))`, with the mean field `B` from 83mKr lines; the energy at
  decay follows from the start frequency. Voigt fits to the krypton conversion lines test the relation with `B`
  free. Energy from a later track without the scatter model, or `B` from a different trap configuration, is wrong.
- **Event selection** (2303.12055 Electron event properties; 2212.05048 selection paragraph). Electron events
  against RF noise only: an upward slope; cuts on the number of tracks, first-track duration and SNR, fixed before
  the tritium data. RF noise fluctuations can form false tracks. No species identification was read.
- **Uncertainty and quality** (2212.05048 analysis paragraphs, uncertainty table; 2303.12055 Measurement of detection
  efficiency vs. frequency, Background). Efficiency against frequency from field-shifted krypton data; Monte Carlo
  coverage and bias of the approximate model; Asimov sets for individual systematics; a background limit from counts
  above the endpoint. Near a TM01 mode the chirp is faster and a reconstruction tuned for normal slopes loses events
  (an efficiency notch).
<!-- /example -->

Failure modes: energy from a mid-event track; a spectrum without the missed-first-track term; a frequency-time
plot offered as spatial tracks; `B` taken from a different trap configuration.

No method text, no source read: other CRES apparatus (a planned cavity geometry is only an outlook sentence);
the krypton chi-square fits and the frequentist tritium fits (their sections were not read);
incorrect merging of neighbouring chirps (pileup is reported negligible at the rates read); sideband
reconstruction (in Phase II sidebands are too weak to detect and only the carrier is detected; matched filtering
and machine learning are stated as potential); position and pitch angle; handling of overlapping acquisition
windows other than analysing only the highest-efficiency channel.

## Resonant and coherent-field readout

The output is a spectrum, a limit or a candidate list, not events. The variant (cavity, circuit, spin, broadband)
is stated, never inferred from a name, and one variant's procedure is not another's.

### Cavity haloscopes

<!-- example: source citation (experiments named as the source of a method) -->
Scope: the HAYSTAC first data run only (photon coupling, tunable cavity with a JPA), read
at `page` level (Brubaker et al. 2017; rescaling, rebinning and lineshape details and most appendices not read).
The paper notes that ADMX obtains its confidence from Monte Carlo, a difference, so this procedure is not the
family's.

- **Signal extraction** (Axion search data, Data quality cuts, Removing the spectral baseline). One
  averaged power spectrum per tuning step, with network-analyzer, amplifier-gain and Y-factor auxiliaries; cuts on
  spectra and on IF bins; normalization to the average baseline, a Savitzky-Golay filter and subtraction of one.
  Spectra near an intruder mode break the single-mode assumption and are cut. Only the averaged spectrum is stored,
  so raw-level re-analysis is not possible from that product; its bins are averages with Gaussian fluctuations and
  filter-induced correlations, not Poisson counts.
- **Finding and association** (Analysis overview, Candidates and Exclusion). A threshold on the normalized grand
  spectrum; bins above it become rescan candidates; correlated neighbouring bins around a candidate are excluded,
  because grand-spectrum bins overlap. The observed candidate count is compared with the simulated expectation at
  the chosen threshold.
- **Parameter estimation** (opening of Combining spectra vertically, Constructing the combined spectrum, Accounting
  for correlations, Analysis overview). An inverse-variance (maximum-likelihood) sum of the IF bins that fall on one
  RF bin. Rescaling (by noise and by the Lorentzian conversion power), rebinning and lineshape weighting are named in
  the Analysis overview and the opening of Combining spectra vertically; their details were not read. Spectra are
  independent per RF bin because each contributes at most one IF bin there; a quadrature variance applied to
  correlated neighbouring bins is wrong.
- **Space and direction.** Not applicable, for a readout reason: one heavily averaged spectrum per iteration from
  one cavity-mode antenna, with no position or direction channel and no time within an iteration.
- **Identifiable quantity** (Analysis overview, Candidates and Exclusion). Excess power at a frequency; the
  threshold and SNR give the excluded coupling at a chosen confidence, from Gaussian statistics of the combined
  data. A field or mass from one bin without the lineshape and detuning weights is not supported.
- **Signal versus interference** (Data quality cuts, Candidates and Exclusion, Rescan data and analysis). IF
  interference stays in the same IF bins; RF interference follows the RF frequency across tuning steps and is hard
  to flag before combination; a real signal should persist on rescan, tested against a coincidence threshold in
  separately processed rescan data.
- **Uncertainty and quality** (Accounting for correlations, Synthetic axion injections). Simulations for the
  correlation factor `xi`; hardware injections of narrowband signals as a fail-safe check only. The statistics of
  the processed spectra (a Gaussian check of the bins) and the attenuation `eta` from the Savitzky-Golay filter are
  not read: no method text for them here.
<!-- /example -->

### Spin (ferromagnetic) haloscopes

<!-- example: source citation (experiments named as the source of a method) -->
Scope: the QUAX ferromagnetic haloscope, one letter read in full (QUAX Collaboration 2020): electron spins in YIG
spheres coupled to a cavity mode, a spin-magnetometer readout. Not extended to other spin systems.

- **Signal extraction** (calibration and search paragraphs). A transmission measurement sets the hybrid mode,
  couples the antenna and gives the linewidth; amplification and heterodyne down-conversion; digitization of a band
  around the mode; an FFT at 100 Hz resolution to remove bad bins, rebinning to about 5 kHz, and a degree-five
  polynomial fit whose residuals are kept. Near a higher cavity mode the two-oscillator model fails and a four-mode
  Hamiltonian is used instead.
- **Finding and association.** No method text: no source read. No candidate threshold or rescan rule is stated;
  do not inherit the cavity rescan.
- **Parameter estimation** (search and limit paragraphs). The standard deviation of the residuals gives the
  sensitivity `sigma_P`, compared with the Dicke prediction.
- **Time** (interaction and data paragraphs). The signal has a daily modulation from the angle between `B0` and
  `B_a`; runs were placed at the modulation maximum, and a 1 ms waterfall spectrogram searched
  for fast bursts. A run outside the maximum does not have equal sensitivity.
- **Identifiable quantity** (coupling equation, field paragraphs). `sigma_P` converts to a field `sigma_B` and to a
  95% CL limit on the electron coupling with a transduction coefficient; scanning is by changing the applied field.
  The transduction coefficient is calculated from a model and depends on `omega_1`.
- **PID or topology.** No method text: no source read beyond bin removal and the burst check.
- **Uncertainty and quality** (calibration paragraphs, noise-budget table, search paragraphs). An injected
  calibrated tone gives the gain and noise temperature; the calibration uncertainty comes from the antenna coupling;
  a thermal-noise check; a fake axion added to real data is kept by the analysis with its SNR. An unaccounted
  difference between expected and measured noise is a failure.
<!-- /example -->

### Circuit readout

No method text: no source read, for any of the seven axes.

### Broadband haloscopes

<!-- example: source citation (experiments named as the source of a method) -->
Scope: the BREAD conceptual design, read at `page` level (keyword-selected sentences of the Introduction,
Photosensor technologies and Sensitivity sections). The paper has no data; this states what it proposes.

- **Signal extraction** (Photosensor technologies). Proposed: a parabolic reflector focuses the barrel signal on a
  sensor, read either by a bolometer with time-modulated input (a chopper, shifting the signal to where 1/f noise
  is subdominant) or by a photon counter with thresholding and pulse fitting. A bolometer on a static signal is
  limited by 1/f noise.
- **Every other axis.** No method text: no source read. The sections read give projections, sensitivity scaling
  and assumed SNR and efficiency only, not a reconstruction.
<!-- /example -->

Failure modes (all variants): adjacent bins treated as independent candidates; correlation or filter attenuation
left uncorrected; a coupling limit without per-setting response; a spin result from cavity constants;
independence between settings assumed without a record of the raw intervals.

No method text, no source read: the circuit variant; spin systems other than ferromagnetic YIG; combination of
overlapping spin runs (fifty-six runs at fixed field are reported, no combination rule); a rescan in the spin
variant; cavity variants other than the one read; a broadband analysis beyond sensor signal processing; an LO sign
error on the RF/IF axis (the cavity analysis aligns bins by coercing the LO to the bin grid and defines the IF-to-RF
map, but does not treat a sign error); reuse of the same raw interval between settings.

## Retarding and scan-encoded spectroscopy

<!-- example: source citation (experiments named as the source of a method) -->
Scope: the first KATRIN neutrino-mass campaign only, a MAC-E filter with a stepped retarding potential, read at `page`
level (KATRIN Collaboration 2021; sections listed under Sources read). The fit section was read only through its
fit-range subsection and the openings of the covariance-matrix and Monte-Carlo-propagation approaches. The output is
an integral spectrum `R(qU)`; inference of the source spectrum is handed to statistics and theory, and the fit item
records what the source did.

- **Signal extraction** (Electron counting and region of interest, Data pipeline). A per-pixel trigger and an
  online double trapezoidal filter for energy and time, with waveforms not saved; counts in a fixed region of
  interest (ROI) over selected pixels. The ROI lower bound is chosen so that charge-sharing gains and losses
  compensate. At high rate pileup pushes energies above the ROI and the event is lost; a rate correction is applied.
- **Finding and association** (Data pipeline, Acquisition of the integral beta-decay spectrum). Counts are assigned
  to a scan step by the HV set point and a handshake; the first two seconds of each step are removed; quality cuts
  use slow control. A step is kept only after the read-back reaches the set point; acquisition before the HV is
  stable shows up as synchronization errors.
- **Parameter estimation** (Stacking, Neutrino-mass fit range, openings of the Covariance-matrix and
  Monte-Carlo-propagation approaches). Counts at like steps are summed and `qU` averaged over scans ("stacking"), then
  a fit by chi-square with a covariance matrix or by Monte Carlo propagation. Stacking is used only after stability
  and HV-reproducibility checks, it carries its own uncertainty, and per-scan conditions are kept; it does not
  correct scan-to-scan variation. The fit's parameter list and the comparison of independent analyses are not in
  the sections read: no method text for them here.
- **Space and time** (Electron counting and region of interest, Assembling spectral data, Stacking). The pixel map and
  timestamps serve selection and stability tests; pixel-wise and scan-wise fits precede merging into one effective
  pixel, justified when no spatial or temporal structure beyond statistics is seen. Radial field variation across
  the analyzing plane exists, so a merge is not automatic. The pitch angle is integrated in the transmission, not
  measured per electron.
- **Energy** (Response and transmission functions, Analyzing-plane potentials, Electron counting and region of
  interest). The threshold `qU` from the monitored retarding potential; the transmission condition; a response
  `f(E - qU)` with scattering probabilities and the energy-loss function, measured with monoenergetic electrons
  from an electron gun. The detector energy is low-resolution and used for the ROI only: a per-electron energy at
  spectrometer resolution is not available.
- **PID or topology.** Not applicable, for a physical reason given in the source: background electrons are
  accelerated like the signal and share the detector energy peak, so no cut separates them per event; background is
  an estimated rate, from scan steps above the endpoint.
- **Uncertainty and quality** (Background, Stacking, Blinding strategy, Covariance-matrix approach, Acquisition).
  Alternating scan direction against drift; model blinding; Monte Carlo twins that recover the inputs before
  unblinding; covariance or Monte Carlo nuisance propagation; an over-dispersion term on the background, whose
  measured distribution is wider than Poisson; the stacking bias from Asimov twins.
<!-- /example -->

Raw counts per scan step, with their setting, effective time and conditions, are the input. Revisited steps are
combined by summing like steps, and count rate and live time are computed after the start-of-step cut.

Failure modes: stacking without stability and reproducibility checks; background treated as pure Poisson; the
detector energy spectrum offered as the science spectrum; pixels merged where fields vary; an event-level signal
label.

No method text, no source read: time-encoded variants (Fulst et al. 2020, read at `page` level, propose
time-focusing time-of-flight with a time-dependent potential and a time-of-arrival spectrum, a simulation study of
added hardware with no measured method; the earlier time-of-flight method it cites was not read); retarding
instruments other than the one read; the scan-step-duration background seen in a later campaign; a per-pixel or
per-patch transmission fit (the campaign read averages over pixels); a deadtime correction for beta scans (deadtime
is mentioned for high-rate electron-gun measurements only); a link to general magnetic spectrometers.

## Sources read

<!-- example: source citation (experiments named as the source of a method) -->
Each source was read on 2026-11-06 from its arXiv e-print. Identifiers are as recorded when reading. `full-text`:
the whole body was read; `page`: only the sections named, some long paragraphs only up to a length cut-off.

- Project 8 Collaboration, "Tritium Beta Spectrum and Neutrino Mass Limit from Cyclotron Radiation Emission
  Spectroscopy" (2022), arXiv:2212.05048, DOI 10.1103/PhysRevLett.131.102502. `full-text`.
- Project 8 Collaboration, "Cyclotron Radiation Emission Spectroscopy of Electrons from Tritium Beta Decay and
  83mKr Internal Conversion" (2023), arXiv:2303.12055, DOI 10.1103/PhysRevC.109.035503. `page`: Radio-frequency
  system; Electron event properties; Data set features; opening of CRES spectrum analysis and CRES energy spectrum
  model; Test of the frequency-energy relation; Measurement of detection efficiency vs. frequency; Bayesian
  analysis procedure; Background; keyword searches for sidebands and pitch angle.
- Project 8 Collaboration, "Determining the neutrino mass with Cyclotron Radiation Emission Spectroscopy -- Project
  8" (2017), arXiv:1703.02037, DOI 10.1088/1361-6471/aa5b4f. `page`: Cyclotron Radiation Emission Spectroscopy;
  Phase I: Proof-of-Principle (setup and results).
- B. M. Brubaker et al., "The HAYSTAC Axion Search Analysis Procedure" (2017), arXiv:1706.08388, DOI
  10.1103/PhysRevD.96.123008. `page`: abstract; Axion search data; Analysis overview; Data quality cuts; Removing the
  spectral baseline; opening of Combining spectra vertically; Constructing the combined spectrum; Accounting for
  correlations; Candidates and Exclusion; Rescan data and analysis; Synthetic axion injections.
- QUAX Collaboration, "Axion search with a quantum-limited ferromagnetic haloscope" (2020), arXiv:2001.08940, DOI
  10.1103/PhysRevLett.124.171801. `full-text`.
- BREAD Collaboration, "Broadband solenoidal haloscope for terahertz axion detection" (2021), arXiv:2111.12103, DOI
  10.1103/PhysRevLett.128.131801. `page`: abstract; keyword-selected sentences of Introduction, Photosensor
  technologies, Sensitivity and discussion.
- KATRIN Collaboration, "Analysis methods for the first KATRIN neutrino-mass measurement" (2021), arXiv:2101.05253,
  DOI 10.1103/PhysRevD.104.012005. `page`: abstract; Analyzing-plane potentials; Electron counting and region of
  interest; Data pipeline; Acquisition of the integral beta-decay spectrum; Response and transmission functions;
  Background; Assembling spectral data; Detector efficiency; Stacking; Neutrino-mass fit range; Blinding strategy;
  openings of the Covariance-matrix and Monte-Carlo-propagation approaches.
- A. Fulst et al., "Time-Focusing Time-of-Flight, a new method to turn a MAC-E-filter into a quasi-differential
  spectrometer" (2020), arXiv:2007.01020, DOI 10.1140/epjc/s10052-020-08484-9. `page`: abstract; General Idea;
  Time-of-Arrival beta-Spectrum; opening of Sensitivity Analysis; keyword-selected sentences elsewhere.
<!-- /example -->

**Done when:** the variant and the setting or frequency axis are stated, every method used is one of those above
with its source section, and each quantity a source does not support (a per-event position or pitch angle, a
per-electron energy, an event-level signal label, a result for the circuit variant) is reported as unknown.

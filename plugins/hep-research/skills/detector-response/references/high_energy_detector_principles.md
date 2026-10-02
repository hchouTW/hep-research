# High-Energy-Physics Detectors: A Unified and Detector-Specific Study

A graduate-level, self-contained treatment of high-energy-physics (HEP) detectors,
organized around one chain: particle and interaction, detector response, signal
formation and transport, electronics and raw data, calibration and alignment, local
reconstruction, pattern recognition and object reconstruction, particle identification
and detector fusion, performance measurement, data/MC validation, systematic
uncertainties, and physics-observable bias. Detector measurement is treated as a
probabilistic inverse problem, `y = f(x;theta) + epsilon`.

**Audience.** HEP graduate students, new detector researchers, and analysts interpreting
detector-performance results, assuming undergraduate electromagnetism, modern physics,
probability, statistics, and introductory particle physics.

**Conventions.** Symbols and acronyms are defined at first use and collected in
`glossary.md`. Relations are labeled exact, approximate, asymptotic, empirical, or
detector-specific. Core equations are numbered E1-E17 in Chapter 2. No detector-specific
performance number is asserted: any such number must be quoted with its apparatus,
configuration, phase space, data conditions, and source, and the case studies describe
mechanisms only. Sources are annotated in `detector-principles-bibliography.md`; expanded tables are in
`detector_comparison_tables.md`; a short quick reference is
`high_energy_detector_principles_summary.md`. Where communities define a quantity
differently (resolution estimators, muon types, efficiency denominators) the
alternatives are stated and one convention is adopted explicitly.

**Note on helper-script names.** A few passages name small Python helpers (for example
`multiple_scattering.py`) from this skill's `scripts/`; they are optional
and the text is complete without them. Sections labeled *Deliverables* list what a
complete analysis of that topic should state.

**Mandatory distinctions used throughout:** response vs calibration; alignment vs
position calibration; acceptance vs efficiency; efficiency vs purity; fake vs
misidentification; bias/scale vs resolution; intrinsic vs system resolution; per-hit vs
per-object resolution; stochastic fluctuation vs systematic uncertainty; truth matching
vs data-accessible observables; narrow residuals vs correct pulls/coverage;
single-particle vs jet calibration; detector resolution vs unfolding regularization.

## Table of contents

- [Chapter 1: Detector Measurement Framework: Forward Model, Inverse Problem, and the Chain](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain)
  - [The chain](#the-chain)
  - [Forward model and inverse problem](#forward-model-and-inverse-problem)
  - [Bias, variance, resolution, efficiency, robustness, calibration](#bias-variance-resolution-efficiency-robustness-calibration)
  - [Thresholds turn continuous shifts into efficiency](#thresholds-turn-continuous-shifts-into-efficiency)
  - [Conditional probability as the language of performance](#conditional-probability-as-the-language-of-performance)
  - [The fourteen questions (template for any detector)](#the-fourteen-questions-template-for-any-detector)
  - [Truth is simulation-only](#truth-is-simulation-only)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 2: Core Equations](#chapter-2-core-equations)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
- [Chapter 3: Signal Formation, Transport, and Readout](#chapter-3-signal-formation-transport-and-readout)
  - [Energy loss and its fluctuations](#energy-loss-and-its-fluctuations)
  - [Light: scintillation, wavelength shifting, attenuation](#light-scintillation-wavelength-shifting-attenuation)
  - [Charge: drift, diffusion, gain, losses](#charge-drift-diffusion-gain-losses)
  - [Readout and digitization](#readout-and-digitization)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 4: Detector Systems Overview](#chapter-4-detector-systems-overview)
  - [What a detector measures, and what it does not](#what-a-detector-measures-and-what-it-does-not)
  - [Subsystem layering](#subsystem-layering)
  - [Magnetic spectrometry: rigidity, momentum, and charge sign](#magnetic-spectrometry-rigidity-momentum-and-charge-sign)
  - [Material budget and multiple scattering](#material-budget-and-multiple-scattering)
  - [Acceptance and geometric factor](#acceptance-and-geometric-factor)
  - [Resolution vocabulary](#resolution-vocabulary)
  - [Deliverables](#deliverables)
- [Chapter 5: Calibration and Alignment](#chapter-5-calibration-and-alignment)
  - [Calibration is a chain, and its order is part of the definition](#calibration-is-a-chain-and-its-order-is-part-of-the-definition)
  - [Test-beam versus in-situ calibration](#test-beam-versus-in-situ-calibration)
  - [Alignment and weak modes](#alignment-and-weak-modes)
  - [Time dependence and conditions data](#time-dependence-and-conditions-data)
  - [Propagating a calibration change](#propagating-a-calibration-change)
  - [Deliverables](#deliverables)
- [Chapter 6: Tracking and Vertexing](#chapter-6-tracking-and-vertexing)
  - [Sensor technologies](#sensor-technologies)
  - [From hits to tracks: pattern recognition](#from-hits-to-tracks-pattern-recognition)
  - [The track fit](#the-track-fit)
  - [Rigidity resolution and its two regimes](#rigidity-resolution-and-its-two-regimes)
  - [Charge confusion](#charge-confusion)
  - [Vertexing](#vertexing)
  - [Alignment coupling](#alignment-coupling)
  - [Deliverables](#deliverables)
- [Chapter 7: Gaseous and Specialized Tracking Technologies](#chapter-7-gaseous-and-specialized-tracking-technologies)
  - [Silicon pixels and strips (recap of what is distinctive)](#silicon-pixels-and-strips-recap-of-what-is-distinctive)
  - [Drift chambers and drift tubes](#drift-chambers-and-drift-tubes)
  - [Time projection chambers (TPC)](#time-projection-chambers-tpc)
  - [MWPCs, straw tubes, and RPCs](#mwpcs-straw-tubes-and-rpcs)
  - [Micro-pattern gaseous detectors (GEM, Micromegas, and relatives)](#micro-pattern-gaseous-detectors-gem-micromegas-and-relatives)
  - [Scintillating-fiber trackers](#scintillating-fiber-trackers)
  - [Nuclear emulsions](#nuclear-emulsions)
  - [Diamond and other radiation-hard sensors](#diamond-and-other-radiation-hard-sensors)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 8: Timing Detectors and Time Measurement](#chapter-8-timing-detectors-and-time-measurement)
  - [Relations (definition, exact unless noted)](#relations-definition-exact-unless-noted)
  - [Pulse-time extraction](#pulse-time-extraction)
  - [Time-resolution budget (single hit)](#time-resolution-budget-single-hit)
  - [Technologies](#technologies)
  - [Calibration and diagnostics](#calibration-and-diagnostics)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 9: Particle Identification: TRD, TOF, RICH, dE/dx, and Muon Systems](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)
  - [The common principle](#the-common-principle)
  - [Time of flight (TOF)](#time-of-flight-tof)
  - [Ionization energy loss (dE/dx)](#ionization-energy-loss-dedx)
  - [Transition radiation detectors (TRD)](#transition-radiation-detectors-trd)
  - [Ring-imaging Cherenkov detectors (RICH)](#ring-imaging-cherenkov-detectors-rich)
  - [Muon systems](#muon-systems)
  - [Combining measurements](#combining-measurements)
  - [Deliverables](#deliverables)
- [Chapter 10: Cherenkov Imaging Variants and Photosensors](#chapter-10-cherenkov-imaging-variants-and-photosensors)
  - [Cherenkov PID variants](#cherenkov-pid-variants)
  - [Photosensors and light transport](#photosensors-and-light-transport)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 11: Calorimetry: Electromagnetic and Hadronic](#chapter-11-calorimetry-electromagnetic-and-hadronic)
  - [The measurement, and why it complements tracking](#the-measurement-and-why-it-complements-tracking)
  - [Electromagnetic showers](#electromagnetic-showers)
  - [Homogeneous versus sampling calorimeters](#homogeneous-versus-sampling-calorimeters)
  - [The resolution decomposition](#the-resolution-decomposition)
  - [Hadronic showers and non-compensation](#hadronic-showers-and-non-compensation)
  - [Leakage, dead material, and containment](#leakage-dead-material-and-containment)
  - [Calorimeter-based identification](#calorimeter-based-identification)
  - [Deliverables](#deliverables)
- [Chapter 12: Muon Systems: Spectrometers, Identification, and Trigger](#chapter-12-muon-systems-spectrometers-identification-and-trigger)
  - [Why muons are special](#why-muons-are-special)
  - [Reconstruction chain](#reconstruction-chain)
  - [Performance and scaling](#performance-and-scaling)
  - [Backgrounds and fakes](#backgrounds-and-fakes)
  - [Distinctive but generalizable reconstruction and performance features (muon system)](#distinctive-but-generalizable-reconstruction-and-performance-features-muon-system)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 13: Noble-Liquid, Neutrino, and Rare-Event Detectors](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors)
  - [Noble-liquid TPCs](#noble-liquid-tpcs)
  - [Neutrino detectors](#neutrino-detectors)
  - [Water Cherenkov and liquid-scintillator detectors](#water-cherenkov-and-liquid-scintillator-detectors)
  - [Rare-event detectors](#rare-event-detectors)
  - [Astroparticle systems within the same framework](#astroparticle-systems-within-the-same-framework)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 14: Event Reconstruction](#chapter-14-event-reconstruction)
  - [The chain, and why its order matters](#the-chain-and-why-its-order-matters)
  - [Digitization boundary and calibration](#digitization-boundary-and-calibration)
  - [Clustering](#clustering)
  - [Track-cluster association and particle-flow reconstruction](#track-cluster-association-and-particle-flow-reconstruction)
  - [Ambiguity resolution across the event](#ambiguity-resolution-across-the-event)
  - [Timing and event association](#timing-and-event-association)
  - [Reconstruction under pileup](#reconstruction-under-pileup)
  - [Reproducibility of the reconstruction](#reproducibility-of-the-reconstruction)
  - [Deliverables](#deliverables)
- [Chapter 15: Detector Simulation](#chapter-15-detector-simulation)
  - [What full simulation does](#what-full-simulation-does)
  - [Geometry and materials](#geometry-and-materials)
  - [Physics lists and their validity](#physics-lists-and-their-validity)
  - [Production cuts and stepping](#production-cuts-and-stepping)
  - [Digitization](#digitization)
  - [Fast and parametrized simulation](#fast-and-parametrized-simulation)
  - [Validating the simulation](#validating-the-simulation)
  - [Deliverables](#deliverables)
- [Chapter 16: Reconstruction Performance and Truth Matching](#chapter-16-reconstruction-performance-and-truth-matching)
  - [Truth matching is a definition, not a measurement](#truth-matching-is-a-definition-not-a-measurement)
  - [Efficiency, fake rate, and purity](#efficiency-fake-rate-and-purity)
  - [Simulation-derived versus data-derived performance](#simulation-derived-versus-data-derived-performance)
  - [Resolution and bias from reco-versus-truth](#resolution-and-bias-from-reco-versus-truth)
  - [From performance to correction](#from-performance-to-correction)
  - [Validating performance itself](#validating-performance-itself)
  - [Deliverables](#deliverables)
- [Chapter 17: Performance Metrics, Acceptance/Efficiency/Resolution, and Residual Diagnostics](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)
  - [Metric definitions](#metric-definitions)
  - [Acceptance, efficiency, resolution: the dedicated distinction](#acceptance-efficiency-resolution-the-dedicated-distinction)
  - [Residuals, pulls, and their covariance](#residuals-pulls-and-their-covariance)
  - [Estimators and pitfalls](#estimators-and-pitfalls)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 18: Data/MC Validation, Detector Systematics Propagation, and Detector Combination](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination)
  - [The simulation chain and its four truth levels](#the-simulation-chain-and-its-four-truth-levels)
  - [Data/MC comparison: what to compare](#datamc-comparison-what-to-compare)
  - [Control samples and data-driven methods](#control-samples-and-data-driven-methods)
  - [Scale factors and reweighting](#scale-factors-and-reweighting)
  - [Systematic uncertainties: sources and mapping](#systematic-uncertainties-sources-and-mapping)
  - [Detector combination and global reconstruction](#detector-combination-and-global-reconstruction)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Chapter 19: Detector-to-Physics-Bias Case Studies, Checklists, and Synthesis](#chapter-19-detector-to-physics-bias-case-studies-checklists-and-synthesis)
  - [Case 1: Tracker weak mode (alignment) - charge-dependent momentum bias](#case-1-tracker-weak-mode-alignment---charge-dependent-momentum-bias)
  - [Case 2: TPC space-charge distortion](#case-2-tpc-space-charge-distortion)
  - [Case 3: Drift-chamber `t0`/`r(t)` offset](#case-3-drift-chamber-t0rt-offset)
  - [Case 4: ECAL dead material and nonlinearity](#case-4-ecal-dead-material-and-nonlinearity)
  - [Case 5: HCAL non-compensation and jet-response bias](#case-5-hcal-non-compensation-and-jet-response-bias)
  - [Case 6: RICH refractive-index drift](#case-6-rich-refractive-index-drift)
  - [Case 7: TOF clock offset](#case-7-tof-clock-offset)
  - [Case 8: Noble-liquid electron-lifetime drift](#case-8-noble-liquid-electron-lifetime-drift)
  - [Reusable checklist for any unfamiliar detector](#reusable-checklist-for-any-unfamiliar-detector)
  - [Checklist for reading a performance plot](#checklist-for-reading-a-performance-plot)
  - [Diagnostic sequence for a data/MC discrepancy](#diagnostic-sequence-for-a-datamc-discrepancy)
  - [Calibration and alignment validation checklist](#calibration-and-alignment-validation-checklist)
  - [One-page synthesis: common principles and family exceptions](#one-page-synthesis-common-principles-and-family-exceptions)
  - [Self-audit (before submitting a detector analysis)](#self-audit-before-submitting-a-detector-analysis)
  - [Common misconceptions and failure modes](#common-misconceptions-and-failure-modes)
  - [Deliverables](#deliverables)
- [Final synthesis](#final-synthesis)

---

## Overview diagram: the end-to-end chain

```
 truth x (simulation only)
    |  interaction with matter (energy loss, scattering, showers, light)
    v
 signal formation & transport (drift, diffusion, gain, attenuation)   <- theta: field, gas, temperature
    v
 electronics & digitization (shaping, ADC/TDC, threshold, trigger)    <- theta: gains, pedestals, thresholds
    v
 raw data y
    v
 calibration & alignment  --->  hits, clusters, times, energies
    v
 pattern recognition & fits  --->  tracks, showers, segments, rings
    v
 PID & detector fusion  --->  particle-level objects
    v
 performance measurement  <->  data/MC validation  <->  systematic uncertainties
    v
 physics observable and its detector-induced bias
```

The two lower arrows are not one-way: validation and performance measurements feed back
into calibration and reconstruction, which is why circularity (tuning on the observable
being measured) is a named failure mode.

## Chapter 1: Detector Measurement Framework: Forward Model, Inverse Problem, and the Chain

The organizing frame for the detector references
([Chapter 4](#chapter-4-detector-systems-overview)-[Chapter 5](#chapter-5-calibration-and-alignment) and
[Chapter 3](#chapter-3-signal-formation-transport-and-readout)-[Chapter 19](#chapter-19-detector-to-physics-bias-case-studies-checklists-and-synthesis)).
Use it on any detector, including one not covered by name: answer the fourteen
questions below, and the detector-specific vocabulary follows. It assumes no
experiment; numbers here are orders of magnitude or definitions, never a quoted
performance.

### The chain

```
particle & interaction -> detector response -> signal formation & transport
 -> electronics & raw data -> calibration & alignment -> local reconstruction
 -> pattern recognition & object reconstruction -> PID & detector fusion
 -> performance measurement -> data/MC validation -> systematic uncertainties
 -> physics-observable bias
```

Each arrow is a separate model with its own parameters, failure modes, and validation
sample. A defect is diagnosed by asking at which arrow it first becomes visible, and
its physics impact is found by pushing it through every later arrow (see
[Chapter 18](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination)).

### Forward model and inverse problem

Treat a measurement as a probabilistic inverse problem:

```
y = f(x; theta) + epsilon        p(y | x, theta)        p(x | y, theta)
```

- `x`: latent particle/event properties (momentum, charge, species, vertex, energy,
  direction, arrival time). Never observed directly.
- `y`: recorded observables (ADC counts, TDC values, waveforms, binary hits,
  time-over-threshold, images, trigger primitives).
- `theta`: nuisance parameters - geometry, alignment, magnetic/electric field,
  material, gains, pedestals, timing offsets, drift velocity, refractive index,
  temperature, pressure, high voltage, aging.
- `epsilon`: stochastic fluctuation and noise. `p(y | x, theta)` is the *likelihood*
  (forward, simulable); `p(x | y, theta)` is the *posterior* (what reconstruction
  approximates). Bayes: `p(x|y,theta) ∝ p(y|x,theta) p(x)`.

Relations in this framework are labeled throughout the package as **exact**,
**approximate**, **asymptotic**, **empirical**, or **detector-specific**; `y = f + eps`
with additive Gaussian `eps` is an approximation, and Poisson, Landau-like, and
heavy-tailed noise violate it routinely.

#### What the inverse problem needs to be identifiable

An estimate of `x` from `y` is only as good as the answer to four questions:

1. **Identifiability.** Does `p(y|x,theta)` differ for different `x`? A single 1D strip
   measurement does not identify a 2D position; a threshold counter does not identify
   velocity above threshold. Where two `x` give the same `y`, the problem is
   *degenerate* and the estimate depends entirely on a prior or on other detectors.
2. **Assumed `theta`.** Reconstruction runs with a *best estimate* `theta_hat`.
   The error `theta - theta_hat` is not noise; it is a shared, correlated,
   possibly time-dependent bias (a systematic), not averaged away by more events.
3. **Priors and regularization.** Track seeding, vertex constraints, clustering
   thresholds, and ML classifiers embed a prior `p(x)`. Its influence is largest
   exactly where the data are least informative (low occupancy edges, high
   momentum, forward regions).
4. **Model mismatch.** If the true `p(y|x)` is not in the fitted family (non-Gaussian
   tails, unmodeled crosstalk), the estimator is biased and its quoted covariance is
   wrong even when the fit `chi^2/ndf` looks fine.

#### Separating the sources of spread

| Source | Nature | Averages away with more events? | Example |
|---|---|---|---|
| Physical fluctuation | Stochastic, irreducible for a given detector | Yes (per event no) | Landau tail, shower sampling fluctuations, photostatistics |
| Electronic noise | Stochastic, correctable in mean, reducible by design | Yes | Pedestal noise, ENC |
| Calibration error | Systematic, shared across channels/time | No | Gain scale, `t0`, drift velocity |
| Alignment / field / material error | Systematic, geometry-correlated | No | Weak modes, field map |
| Reconstruction prior / algorithm | Systematic, phase-space dependent | No | Seeding bias, clustering threshold |
| Model mismatch | Systematic | No | Simulation missing a physics process |

A "resolution" in a plot usually blends the first two and hides the rest; a
"systematic uncertainty" is the leftover freedom in the last four.

### Bias, variance, resolution, efficiency, robustness, calibration

- **Response** `R = <x_reco>/x_true` at fixed truth (a property of the detector plus
  algorithm). **Calibration** is the *procedure* that maps response toward 1; response
  is what the detector does, calibration is what analysts do about it. Do not use one
  word for both.
- **Bias / scale**: central offset of the estimator distribution. **Resolution**:
  width of that distribution. They are independent; a scale error shifts a peak, a
  resolution error broadens it, and unfolding/regularization of the final spectrum is a
  third, separate width ([Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)).
- **Efficiency**: probability of a conditional success. **Robustness**: how little
  the above degrade when `theta` or `p(x)` shifts. A method optimized on simulation can
  be optimal and fragile.
- **Calibrated uncertainty**: the quoted `sigma` covers the truth at its stated
  probability. Narrow is not calibrated ([Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)).

### Thresholds turn continuous shifts into efficiency

A discriminator, zero-suppression cut, or trigger threshold `T` on a continuous
response gives efficiency `eps(x) = P(y > T | x)`. If `y ~ N(mu(x), sigma)` this is
the turn-on `eps = Phi((mu - T)/sigma)` (approximate: Gaussian). A 1% drift in gain
moves `mu`, which *does nothing* on the plateau and changes efficiency steeply on the
edge. Consequences: an efficiency measured on a plateau does not constrain the gain;
a threshold effect is largest for the lowest-signal population (minimum-ionizing
particles in thin sensors, low-energy showers, single photoelectrons); and a change
in threshold or noise looks like a change in efficiency only for events near it.

### Conditional probability as the language of performance

Every performance number is `P(outcome | population)`, so it is undefined until the
population is named. Write the conditioning:

`P(reconstructed | in acceptance, has truth particle, pT > x)`, `P(pass ID | reco'd,
matched)`, `P(truth is X | selected as X)`. The same word ("efficiency") with two
denominators gives two numbers that differ by acceptance or by fake population; the
factorization and its pitfalls are in
[Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics).

### The fourteen questions (template for any detector)

1. What enters the sensitive volume?
2. Which microscopic interaction creates the signal?
3. What is the earliest physical signal (charge, light, heat, phonons, current,
   drift time)?
4. What is digitized (ADC, TDC, waveform, binary hit, time-over-threshold, image,
   trigger primitive)?
5. What is the forward model, with nuisance parameters and stochastic terms?
6. Which calibrations, conditions, geometry, field maps, and material are required?
7. Which local objects are reconstructed?
8. What pattern recognition / association / fit / deconvolution follows?
9. Which ambiguities or degeneracies are characteristic?
10. What creates inefficiency, fakes, duplicates, migrations, tails, catastrophic
    failures?
11. How does performance scale with energy, momentum, angle, occupancy, pileup, dose,
    rate, time?
12. What can be measured in data, and what needs simulation truth?
13. How are data/MC discrepancies corrected or assigned as uncertainties?
14. How can a detector defect bias a final physics result?

Each detector-family reference states its answers in a labeled subsection,
**Distinctive but generalizable reconstruction and performance features**, covering:
information topology, unique inverse problem and degeneracies, natural local/global
objects, the most informative residual or closure variable, scaling laws and floors,
community efficiency/resolution conventions, dominant tails, occupancy/rate/aging
dependence, the strongest data-driven sample, and what transfers to other detectors.

### Truth is simulation-only

Generator truth, simulation truth (energy deposits, true trajectories), digitized
signals, and reconstructed objects are four levels ([Chapter 15](#chapter-15-detector-simulation)).
Only the last two exist in data. Every "measured in data" performance number uses a
*data-accessible proxy* (tag-and-probe, standard candle, redundancy of independent
subdetectors, sidebands, cosmic rays) whose own bias is part of the uncertainty
([Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching),
[Chapter 18](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination)).

### Common misconceptions and failure modes

- **Treating `theta_hat` as `theta`.** Calibration and alignment errors are shared
  systematics, not per-event noise; more statistics never removes them.
- **Quoting "the resolution."** Without estimator, center, width definition, selection,
  and tail, the number is not comparable between detectors or between MC and data.
- **Response = calibration.** Response is the detector's behavior; calibration is the
  correction; a calibrated response can still be nonlinear or non-uniform.
- **Ignoring identifiability.** A good `chi^2` does not mean `x` is determined; check
  which directions in `x` have a flat likelihood.
- **Reading a plateau efficiency as a gain check.** Plateaus are insensitive to the
  parameter that matters at the edge.
- **Simulation truth used as if measurable.** See "Truth is simulation-only."

### Deliverables

- The chain written for the specific detector, with the model and validation sample
  for each arrow.
- The fourteen-question table filled in.
- `x`, `y`, `theta`, `epsilon` named explicitly, with every nuisance parameter's
  source and correlation.
- Every quoted performance number with its conditioning population, estimator,
  center, width, and tail definition.

## Chapter 2: Core Equations

The seventeen relations every later chapter relies on. For each: symbols and units,
assumptions and validity, which quantity is observable and which latent, and where its
parameters come from. Equations are numbered E1-E17 and cited by number elsewhere.
Labels: *exact*, *approximate*, *asymptotic*, *empirical*, *detector-specific*.

| No. | Relation | Symbols, units, validity | Observable / latent | Parameter source |
|---|---|---|---|---|
| E1 | `y = f(x;theta) + epsilon`, `p(y|x,theta)` | `x` latent particle/event properties; `y` recorded observables; `theta` detector, geometry, field, material, electronics, environment, calibration; `epsilon` fluctuation and noise. Approximate when `epsilon` is Gaussian; Poisson and Landau-like noise violate it | `y` observed; `x`, `theta` inferred | `theta` from calibration, alignment, monitoring; `p(y|x,theta)` from simulation and test beam |
| E2 | `pT ≈ 0.3 |q| B R` | `pT` in GeV/c, `B` in T, bending radius `R` in m, `q` in units of `e`. Exact for a helix in a uniform field in these units; rigidity `p/q` is what a spectrometer measures | curvature observed; `pT`, `q` latent | field map from measurement; `R` from the track fit |
| E3 | `chi^2 = r^T V^{-1} r` | `r` residual vector, `V` its covariance. Optimal for Gaussian errors; `V` must be the residual covariance, not the measurement covariance | hits observed; track parameters latent | `V` from hit resolutions, material, alignment |
| E4 | `theta_0 = (13.6 MeV/(beta c p)) z sqrt(x/X_0)[1 + 0.038 ln(x z^2/(X_0 beta^2))]` | Highland; `x/X_0` thickness in radiation lengths, `p` in MeV/c, `z` projectile charge. Approximate (about 11% for `1e-3 < x/X_0 < 100`); core only, tails are non-Gaussian | scattering angle latent | `X_0` from tabulations |
| E5 | `-<dE/dx> = K z^2 (Z/A)(1/beta^2)[0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max/I^2) - beta^2 - delta/2]`, `K = 0.307 MeV mol^-1 cm^2` | Mean loss, heavy charged particles, intermediate energies (approximate). Fluctuations: Landau/Vavilov for `kappa = xi/W_max << 1`, Gaussian for thick absorbers | deposited charge/light observed; `beta gamma` latent | `I`, `delta` from tabulated fits |
| E6 | `v_d = mu E`; `sigma = sqrt(2 D L/v_d) = C_D sqrt(L)` | Drift velocity, mobility `mu`, diffusion `D`; low-field constant-mobility form is approximate; real gases need `v_d(E,B,T,P)` and `C_D` (um/sqrt(cm)) | arrival time/position observed; origin latent | measured in the operating gas or liquid |
| E7 | `cos theta_C = 1/(n beta)`; `p_th = m c/sqrt(n^2-1)`; `d^2N/(dx dE) ≈ 370 sin^2 theta_C eV^-1 cm^-1` | Cherenkov angle, threshold, yield before detection efficiency; exact kinematics, approximate yield | photon hits observed; `beta` latent | `n(lambda,T,P)` from monitoring |
| E8 | `beta = L/(c t)`; `m^2 = p^2(1/beta^2 - 1)` | `L` track path length, `t` flight time; exact. Separation falls as `1/p^2` | `t` observed; `beta`, `m^2` inferred | `L` from the track fit; `t0`, clock from calibration |
| E9 | `sigma_E/E = a/sqrt(E) ⊕ b/E ⊕ c` | Quadrature sum: stochastic `a`, noise `b`, constant `c`; empirical decomposition | energy inferred | fit to test-beam or in-situ data |
| E10 | `sigma/N ≈ sqrt(F/N_pe)` | Photostatistics with excess-noise factor `F >= 1`; Poisson-limited | `N_pe` observed | `F` from single-photoelectron calibration |
| E11 | `A = N_fid/N_gen`, `eps = N_success/N_eligible`, `P = N_matched/N_selected`; `P(S) = P(A)P(R|A)P(S|R,A)` | Chain rule exact for consistent denominators; a naive product of separately measured efficiencies is not | truth-level, simulation-only | counts in simulation; proxies in data |
| E12 | `r = x_meas - x_pred`, `p = r/sigma_r`, `V_r = V_meas + V_pred - C - C^T` | Residual, pull, residual covariance with measurement-prediction correlation `C`; biased residual `V_r = V_meas - V_pred` | measured and predicted | fit covariance |
| E13 | `SF = eps_data/eps_MC` | Efficiency scale factor; both measured identically, in the analysis phase space | data and simulation | tag-and-probe or equivalent |
| E14 | `V_f ≃ J V_x J^T`, `J_ij = df_i/dx_j` | First-order propagation; fails for thresholds, migration, strongly nonlinear or asymmetric responses | nuisance covariance input | variations of the reconstruction |
| E15 | `n_i^reco = sum_j R_ij n_j^truth + b_i` | Response matrix: off-diagonal = resolution, column sums < 1 = inefficiency, `b_i` background, model dependence via the truth spectrum | reco observed; truth latent | simulation, validated on data |
| E16 | `N_sigma = |mu_1-mu_2|/sqrt(sigma_1^2+sigma_2^2)` | PID separation; Gaussian approximation, unreliable with tails or few photons | discriminating variable | fitted distributions per species |
| E17 | Binomial/Poisson likelihoods; Clopper-Pearson or Wilson intervals | Efficiencies (binomial), counts (Poisson); Gaussian intervals fail near 0 or 1 | counts | counting |

**Reading the table.** Every relation has a domain of validity; using one outside it
(Bethe-Bloch at low `beta gamma`, Highland tails, Gaussian `N_sigma`, linear
propagation through a threshold) is a common source of quiet errors.

### Common misconceptions and failure modes

- **Equation used outside its validity range** without noticing.
- **Parameters treated as constants** when they are calibrated, time-dependent quantities.
- **Gaussian approximations applied to Poisson, Landau, or heavy-tailed quantities.**
- **The wrong covariance in `chi^2` or pulls** (measurement instead of residual covariance).
- **Symbols reused across detectors** with different meanings; check the glossary.

## Chapter 3: Signal Formation, Transport, and Readout

The first four arrows of the [Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain): particle
and interaction, detector response, signal formation and transport, electronics and
raw data. Material-budget/multiple-scattering bookkeeping is in
[Chapter 4](#chapter-4-detector-systems-overview); calibration of the constants introduced here is in
[Chapter 5](#chapter-5-calibration-and-alignment). Every equation below states its validity; none
is a substitute for a full simulation ([Chapter 15](#chapter-15-detector-simulation)).

### Energy loss and its fluctuations

**Mean ionization loss (Bethe-Bloch; approximate, intermediate energies, heavy charged
particles)**:

```
-<dE/dx> = K z^2 (Z/A) (1/beta^2) [ 0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max / I^2)
                                     - beta^2 - delta(beta*gamma)/2 ]
K = 4 pi N_A r_e^2 m_e c^2 = 0.307 MeV mol^-1 cm^2
```

`z` projectile charge, `Z/A` medium (mol/g), `I` mean excitation energy, `W_max`
maximum energy transfer, `delta` the density-effect correction. Parameters come from
tabulated fits (PDG), not from data. It fails below `beta gamma ~ 0.05-0.1`
(shell, Barkas, and charge-exchange corrections) and above `~ 100` (radiative losses
for muons and electrons dominate). Shape: falls as `1/beta^2`, minimum at
`beta gamma ~ 3-4` (minimum-ionizing, "MIP"), logarithmic relativistic rise, then a
Fermi plateau from `delta`. The rise is *smaller in dense media and thin gas volumes
than a naive mean suggests* because the density effect and delta-ray escape truncate it.

**Fluctuations (regime by `kappa = xi/W_max`, `xi = (K/2)(Z/A) z^2 (x rho)/beta^2`)**:
`kappa << 1` (thin absorber, gases, silicon of ~100 um): the Landau/Vavilov
distribution - asymmetric with a long high tail from delta rays, most-probable value
(MPV) below the mean, no finite variance in the pure Landau limit; `kappa >> 1`
(thick absorbers): Gaussian. Consequences: use the truncated mean, MPV fit, or
likelihood, not the raw mean, for thin-layer `dE/dx` ([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems));
the fluctuation is a *physical, irreducible* per-layer term, reduced only by more layers
or cluster counting.

**Multiple Coulomb scattering (Highland, approximate, ~11% for `1e-3 < x/X0 < 100`)**:
`theta_0 = (13.6 MeV / (beta c p)) z sqrt(x/X_0) [1 + 0.038 ln(x z^2/(X_0 beta^2))]`.
It sets the low-momentum resolution floor of every tracker
([Chapter 6](#chapter-6-tracking-and-vertexing)); the non-Gaussian large-angle tail
(single-scatter) is why fit `chi^2` has heavy tails.

**Radiative and nuclear processes.** Bremsstrahlung (energy scale `~ X_0`, critical
energy `E_c`), photon conversion (`~ 9/7 X_0` mean free path), delta rays (extended
clusters, tail of `dE/dx`), and nuclear interactions (interaction length
`lambda_I`, produce kinks, secondary vertices, and the invisible energy of
[Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic)). Each is a topological source of fakes and tails,
not a smooth resolution term.

**Cluster counting.** Primary ionization clusters are Poisson-distributed with
`~ 10s per cm` in typical tracking gases (order of magnitude; species/pressure
dependent). Counting clusters instead of integrating charge removes the Landau tail
and reaches better `dE/dx` resolution, at the price of needing to resolve single
clusters in the waveform (rate, diffusion, and electronics limits).

### Light: scintillation, wavelength shifting, attenuation

- **Scintillation.** Light yield `N_gamma = Y E` (photons/MeV; material dependent),
  decay-time spectrum (fast + slow components). **Quenching**: yield per unit energy is
  not linear at high `dE/dx` (Birks-type; `dL/dx = S (dE/dx)/(1 + kB dE/dx)`,
  empirical), so heavy ions, alphas, and nuclear recoils give less light than electrons
  of the same energy - the origin of "electron-equivalent" versus nuclear-recoil energy
  scales ([Chapter 13](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors)).
- **Attenuation.** Light reaching a photosensor at distance `L`: `~ exp(-L/lambda_att)`
  plus geometric losses; a position-dependent gain that must be measured or corrected;
  in a wavelength-shifter, the photon spectrum shifts and the trapping/re-emission
  efficiency adds a second stochastic step ([Chapter 10](#chapter-10-cherenkov-imaging-variants-and-photosensors)).
- **Photon statistics** (Poisson; exact for the count, approximate for the Gaussian
  limit): `sigma_E/E = 1/sqrt(N_pe)`, `N_pe = N_gamma * eps_collection * QE`. Gain
  fluctuation adds an excess noise factor `F >= 1`:
  `sigma_E/E ≈ sqrt(F/N_pe)`; the stochastic term `a/sqrt(E)` of a calorimeter is the
  energy-scaled form of this.

**Cherenkov radiation (exact kinematics; approximate yield)**: emission when
`beta > 1/n` with `cos theta_C = 1/(n beta)`; threshold `p_th = m c/sqrt(n^2 - 1)`;
number of photons per unit path per energy `d^2N/(dx dE) ≈ 370 sin^2 theta_C  eV^-1 cm^-1`
(before detection efficiency). Yield is small (tens of detected photons at most for
practical radiators), so `N_pe` is the dominant performance limit
([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems), [Chapter 10](#chapter-10-cherenkov-imaging-variants-and-photosensors)).

**Transition radiation.** Emitted when a relativistic particle crosses interfaces
between media of different dielectric constants; the yield rises with Lorentz factor
`gamma` and onsets near `gamma ~ 10^3`, so it separates electrons from hadrons only at
momenta where the hadron is below threshold. X-rays are absorbed in the same gas as
the ionization signal (mind the overlap in likelihood; [Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)).

**Showers.** Electromagnetic (scale `X_0`, Moliere radius `R_M`, log growth of depth
with energy) and hadronic (scale `lambda_I`, non-compensation, invisible energy) are
developed in [Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic); for signal formation they add a
stochastic *sampling* term (fluctuation in the number of charged particles crossing
active layers) and a *containment* term.

### Charge: drift, diffusion, gain, losses

**Drift.** In field `E`, electrons in gas reach a drift velocity `v_d = mu E`
(constant mobility, low field only; in real gases `v_d(E, B, T, P, composition)` is
measured and tabulated). In liquid noble gases `v_d ~ mm/us` at a few hundred V/cm.
**Diffusion (approximate, Gaussian)**: longitudinal/transverse spread after drift
distance `L` is `sigma = sqrt(2 D L / v_d) = C_D sqrt(L)`, with `C_D` in
`um/sqrt(cm)` measured for the gas mixture. In a magnetic field parallel to `E`,
transverse diffusion is reduced by `1/sqrt(1 + omega^2 tau^2)` (approximate). Diffusion
is the floor on drift-coordinate resolution at long drift and the reason for gas
selection ("cold" gases have low diffusion).

**Lorentz angle.** In crossed `E x B`, the drift direction rotates by the Lorentz angle
`theta_L`; a pixel or strip cluster is displaced and broadened, an effect corrected in
position reconstruction and calibrated with tracks ([Chapter 6](#chapter-6-tracking-and-vertexing),
[Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies)).

**Avalanche gain.** In proportional gas, `G = exp(int alpha dx)` (Townsend `alpha`);
gain fluctuates with a Polya (approximately exponential) distribution; gain depends
exponentially on voltage and, through the density `T/P`, on temperature and pressure
(the sensitivity is gas- and voltage-specific and must be measured) - hence
pressure/temperature corrections in every gaseous detector. Beyond the proportional regime: Geiger,
streamer, discharge; space charge from ion backflow modulates the effective field.

**Losses in transport.** Electron attachment to electronegative impurities (`O2`, `H2O`)
gives `Q(t) = Q0 exp(-t/tau_e)` (electron lifetime `tau_e`; a slow, measured,
time-dependent correction in noble-liquid TPCs); recombination for liquid/high-density
media depends on `dE/dx` and field, producing the scintillation-ionization
anticorrelation ([Chapter 13](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors));
charge trapping and radiation damage in semiconductors reduce the collected charge
(charge collection efficiency `CCE < 1` and rising leakage current with fluence).
**Space charge**: positive-ion buildup distorts `E` and hence reconstructed positions
(TPC, high-rate gas detectors).

**Phonons and heat.** Cryogenic bolometers convert deposited energy into a temperature
rise `Delta T = E/C` (heat capacity `C`); sensitivity to sub-keV energies is bought by
very low `C`. Nuclear/electron recoil discrimination uses the ratio of ionization or
light to heat ([Chapter 13](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors)).

**Irreducible versus correctable.** Landau fluctuation, photostatistics, sampling
fluctuation, and diffusion are stochastic floors (reducible only by design); gain,
drift velocity, attenuation length, lifetime, refractive index, and `t0` are correctable
response variations whose *residual error* is a systematic
([Chapter 5](#chapter-5-calibration-and-alignment)).

### Readout and digitization

**Chain**: sensor -> preamplifier -> shaper -> discriminator and/or ADC/TDC ->
buffer -> zero-suppression / trigger -> data. Each stage removes information; keep the
**analog information loss** (irreversibly discarded at digitization, e.g. threshold,
binary readout, coarse ADC) separate from **reconstruction loss** (information present
in the raw data but not used by the algorithm).

- **Pulse shaping and sampling.** A CR-RC shaper with peaking time `tau` trades noise
  against pileup: slow shaping reduces series noise but increases pileup and dead time;
  sampling a waveform at rate `f_s` needs `f_s` above twice the signal bandwidth
  (Nyquist) or aliasing biases amplitude and time extraction. Amplitude and time from a
  waveform: peak, matched filter, template fit (best; needs the pulse shape and its
  variation with occupancy).
- **Noise.** Equivalent noise charge (ENC, electrons) sets the threshold and the
  minimum measurable signal; signal-to-noise `S/N` of a minimum-ionizing particle in a
  thin sensor is the driver of both hit efficiency and position resolution. **Common-mode
  noise** (coherent across channels) is subtracted event-by-event; **crosstalk**
  (capacitive, inductive, or optical) creates ghost signals and biases charge sharing.
- **Pedestal, zero suppression, dynamic range.** Pedestals are measured (dedicated
  runs, empty events) and drift with temperature; zero suppression removes noise
  at the cost of dropping small real signals (threshold efficiency,
  [Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain)); **saturation** clips large signals
  (high-energy showers, heavy ions) and biases sums downward unless a dynamic-range
  overlap is calibrated.
- **Time-over-threshold and binary readout.** Time above threshold encodes amplitude
  nonlinearly (calibrated per channel); binary readout keeps only "hit/no hit" and
  timing, losing amplitude - fine position resolution then relies on geometry and
  cluster topology.
- **Pileup and dead time.** Signals overlapping in time within the shaping/integration
  window merge; a non-paralyzable dead time `tau` turns a true rate `n` into a
  measured `m = n/(1 + n tau)` (approximate); a paralyzable one saturates and turns
  over at high rate. The measured rate versus the true rate is a *response* needing a
  correction (trigger, luminosity, and pileup methodology).
- **Buffering and data loss.** Finite buffer depth and bandwidth drop events or hits
  under burst conditions; the loss is *rate- and topology-dependent* (large events
  lost more), so it can look like a physics-dependent efficiency.
- **Trigger primitives and bias.** A hardware trigger acts on coarse, low-latency
  information (fewer bits, poorer alignment, no full calibration). Trigger efficiency
  differs from offline efficiency and depends on the same variables as the analysis
  cut (turn-on curves, prescales) - see trigger, luminosity, and pileup methodology. A
  trigger-level cut on an under-calibrated quantity creates an *inefficiency that is
  correlated with the analysis observable*, the most common way a trigger biases a
  measurement.

### Common misconceptions and failure modes

- **"Threshold has no effect on resolution."** Thresholds truncate the low tail of the
  response and bias centroids and energy sums, especially for low-`S/N` clusters.
- **Using Bethe-Bloch outside its range.** Below `beta gamma ~ 0.1` or in the radiative
  regime, the mean is not the right predictor; thin-layer `dE/dx` is Landau-shaped and
  the mean is not a stable estimator.
- **Treating attenuation as a constant.** It varies with position, time, temperature,
  and radiation dose; it is a per-channel and time-dependent calibration.
- **Confusing electron-equivalent and nuclear-recoil energy.** Quenching makes them
  different scales; quote which one.
- **Blaming analog loss for a reconstruction problem (or vice versa).** Check whether
  the information exists in the raw waveform before redesigning the algorithm.
- **Saturation invisible in ratios.** Clipped channels look like a resolution loss at
  the highest energies; monitor the saturated fraction.

### Deliverables

- The earliest physical signal and the digitized quantity for the detector, with the
  forward model and nuisance parameters.
- Which fluctuations are irreducible (with their scaling) and which response
  variations are correctable (with the calibration that handles them).
- Threshold, dynamic range, dead time, and buffering limits, with the resulting
  efficiency versus rate/occupancy behavior.
- A statement of the trigger-level information and the bias it can introduce.

## Chapter 4: Detector Systems Overview

Orients the detector-level references that follow
([Chapter 6](#chapter-6-tracking-and-vertexing), [Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic),
[Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)) and connects them to the
analysis-level material already in
analysis design and blinding and
jet, b-tagging, and missing-momentum reconstruction,
which start from reconstructed objects and treat the detector as given. This file is
organized by detector *technology* and deliberately assumes no particular experiment,
geometry, or beam configuration; quote scaling relations and orders of magnitude
rather than treating any one experiment's resolution as universal.

For the unified forward-model/inverse-problem framework and the technology-specific
extensions (readout, gaseous/timing/muon/noble-liquid/photosensor detectors, metrics,
validation, case studies), see [Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain) onward.

### What a detector measures, and what it does not

A detector does not measure particle identity, energy, or momentum. It measures
localized energy deposits, arrival times, and induced charge, at known positions, and
everything else is inference built on a model of how particles interact with matter.
Keeping that distinction explicit prevents a large class of errors in which a
reconstructed quantity is treated as a direct observation: a "measured" momentum is
the output of a fit whose assumptions (magnetic field map, alignment, material model,
hit uncertainties) can each be wrong, and its uncertainty is only as trustworthy as
those inputs.

The measurable primitives are position, time, deposited energy, and - through a
magnetic field - the curvature of a charged trajectory. Every physics-object quantity
in an analysis reduces to combinations of those four.

### Subsystem layering

Detectors are built in layers ordered by how destructive each measurement is. The
innermost systems must perturb the particle as little as possible, because everything
downstream depends on the trajectory surviving intact; the outermost systems are
allowed to absorb the particle entirely, because nothing is measured after them.

The conventional ordering is precision tracking first (thin, high-granularity,
minimally disruptive), then identification systems that exploit velocity or radiation
without stopping the particle, then electromagnetic calorimetry, then hadronic
calorimetry, then muon detection - muons being the charged particles that routinely
survive the calorimeters. Not every experiment has every layer, and the ordering can
differ (a time-of-flight system may sit both before and after a spectrometer to define
a flight path), but the underlying principle - measure non-destructively before
measuring destructively - is general.

The practical consequence for analysis is that subsystems are not independent. A
mismeasured track changes the calorimeter cluster it is matched to; extra material in
the tracker changes what reaches the calorimeter; a timing detector's flight-path
measurement depends on the track fit. Systematic variations must therefore propagate
across subsystem boundaries, not be applied to one object in isolation - the same
requirement, restated in Chapter 18, that kinematic variations be propagated through reconstruction and selection.

### Magnetic spectrometry: rigidity, momentum, and charge sign

A charged particle of charge `q` and momentum `p` in a magnetic field follows a
trajectory whose curvature depends on the combination `R = p / q`, the **rigidity**.
This is the quantity a magnetic spectrometer actually measures. Momentum follows only
once the charge is known or assumed, and for multiply-charged nuclei the two differ by
a factor of `Z` - a distinction that matters enormously in cosmic-ray and heavy-ion
contexts and is easy to lose when reusing code written for singly-charged particles.

Curvature is inversely proportional to rigidity, so the *directly* measured quantity
is closer to `1/R` than to `R`. This has a consequence that propagates into every
analysis: measurement uncertainty is approximately Gaussian in curvature, not in
rigidity or momentum. The relative rigidity resolution therefore grows roughly
linearly with rigidity, `sigma(R)/R ~ R`, until it is no longer meaningful - at the
**maximum detectable rigidity** (MDR), where `sigma(R)/R` reaches 100%, the sign of
the curvature is no longer reliably determined. Above the MDR a spectrometer does not
simply become imprecise; it begins to misassign charge sign, scattering
high-rigidity particles of one sign into the other sign's sample. Any analysis
sensitive to a charge ratio or to a rare oppositely-charged species must treat this
**charge confusion** as a background, not as a resolution effect - see
[Chapter 6](#chapter-6-tracking-and-vertexing).

Because uncertainty is Gaussian in `1/R`, binning and unfolding in `R` interact badly
with a symmetric-in-curvature resolution function: a steeply falling spectrum
combined with a curvature-Gaussian smearing produces a net migration upward in
rigidity that is not symmetric and cannot be corrected by a symmetric bin-by-bin
factor. Handle it with a response matrix built in the measured variable - see
measurements and unfolding.

### Material budget and multiple scattering

Every layer of a detector is also a scatterer and an absorber. The **material budget**
is the accumulated thickness of material a particle traverses, expressed in units of
radiation length `X0` for electromagnetic processes and nuclear interaction length
`lambda_I` for hadronic ones. It is the single most useful number for predicting how
much a detector degrades its own measurements.

Multiple Coulomb scattering deflects a charged particle by a small random angle in
each layer, with an RMS projected angle described by the Highland formula, which
scales as roughly `1/(beta * p)` times the square root of the material thickness in
radiation lengths. Two consequences follow directly. First, scattering degrades
angular and position measurements more severely at low momentum, so a spectrometer's
rigidity resolution has a low-rigidity floor set by scattering that no improvement in
sensor precision can remove. Second, because the intrinsic sensor-resolution
contribution to `sigma(R)/R` grows with rigidity while the scattering contribution
falls, every magnetic spectrometer has a characteristic rigidity at which the two
cross, and a resolution curve that is worst at both ends. Locating that crossover is
the first thing to do when interpreting a spectrometer's performance;
`multiple_scattering.py` computes it from a material description.

Material also causes energy loss (ionization for all charged particles,
bremsstrahlung additionally for electrons), photon conversion, and nuclear
interaction - meaning the particle arriving at an outer subsystem may not be the
particle that entered. Interaction and conversion in tracker material are a standard
source of reconstruction inefficiency and of fake low-momentum tracks, and the
material model used in simulation is a leading systematic for any measurement that
depends on the surviving-particle fraction. Mismodeled material budget is a common
root cause when data and simulation disagree in a way that varies with polar angle,
because material thickness varies with the path length through the detector.

### Acceptance and geometric factor

**Acceptance** is the fraction of produced particles or events that can in principle be
measured, given the detector's geometry and active-region coverage. It is a property
of the apparatus and the physics process together, not of the apparatus alone, because
it depends on the kinematic distribution being sampled. For an experiment measuring a
flux rather than a cross section, the corresponding quantity is the **geometric
factor**, an area-times-solid-angle with units of `m^2 sr`, which converts a counting
rate into a flux.

Acceptance must be distinguished from **efficiency**: acceptance is geometric and
computed from simulation of the apparatus, efficiency is the probability that a
particle inside the acceptance is actually reconstructed and selected, and is measured
from data wherever possible. Merging them into a single simulation-derived correction
hides the part that should have been data-driven and validated - see
[Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching) and
histogram and efficiency statistics.

Acceptance depends on the simulated input spectrum whenever it is computed by
integrating over a distribution. Quote the generator-level assumption used, and check
the sensitivity by recomputing with a reweighted input spectrum; an acceptance quoted
without that check carries an unstated model dependence.

### Resolution vocabulary

Terms that are frequently conflated, and are worth stating precisely in any writeup:

- **Intrinsic resolution** - the single-sensor measurement precision, before any fit.
- **Resolution** - the width of the distribution of (reconstructed minus true), at
  fixed true value. Usually quoted as a Gaussian sigma, which is an approximation:
  most detector response functions have tails, and quoting only a core sigma
  systematically understates the probability of large mismeasurement.
- **Bias** - the mean of (reconstructed minus true). A resolution quoted without a
  bias check is incomplete; a small bias in a steeply falling spectrum can matter more
  than a large resolution.
- **Response** - the mean reconstructed value as a function of true value, whose
  deviation from unity slope is a calibration problem, not a resolution problem - see
  [Chapter 5](#chapter-5-calibration-and-alignment).
- **Linearity** - whether response is constant across the measured range.
- **Occupancy** - the fraction of readout channels hit per event, which drives
  pattern-recognition difficulty and confusion, not resolution.

Report the core-sigma, the tail fraction, and the bias separately. A single number
labeled "resolution" is only interpretable if the definition (Gaussian fit range,
RMS, or an interquantile width) is stated alongside it.

### Deliverables

- The subsystem inventory assumed by the analysis, with the ordering a particle
  traverses and which subsystems are required by the selection.
- Whether the spectrometer measurement is rigidity or momentum, the charge assumption
  relating them, and the maximum detectable rigidity if the analysis approaches it.
- Material budget in `X0` (and `lambda_I` where hadronic interaction matters) along
  the relevant paths, and whether its uncertainty was propagated as a systematic.
- Acceptance or geometric factor, stated separately from efficiency, with the
  generator-level input spectrum assumed and a sensitivity check against a reweighted
  spectrum.
- Resolution quoted with its definition (fit range or width statistic), its bias, and
  its tail fraction, not as a single unqualified sigma.

### Common misconceptions and failure modes

- **Reconstructed quantity read as an observation.** A momentum or energy is the output of a fit whose field map, alignment, and material model can each be wrong.
- **Rigidity and momentum interchanged.** They differ by the charge `Z`; multiply-charged nuclei make this error large.
- **Acceptance called efficiency**, or a geometric factor quoted without its energy and angle dependence.
- **Subsystems treated as independent.** A mismeasured track changes the cluster it matches; extra tracker material changes what reaches the calorimeter.
- **Gaussian multiple scattering.** The single-scattering tail is non-Gaussian and is why fit `chi^2` has heavy tails.

## Chapter 5: Calibration and Alignment

Covers the constants that connect a simulated or idealized detector to the real one:
energy and timing calibration, alignment of sensor positions, their time dependence,
and how a change in any of them propagates through everything downstream. This is the
feedback loop that closes the chain from
[Chapter 15](#chapter-15-detector-simulation) back to
[Chapter 14](#chapter-14-event-reconstruction).

### Calibration is a chain, and its order is part of the definition

A reconstructed energy or position is the product of a sequence of corrections -
pedestal subtraction, gain, channel-to-channel intercalibration, an absolute scale, and
finally residual corrections for known dependences. The sequence is not commutative in
practice, because later steps are derived assuming earlier ones were applied. Applying
a correction twice, or out of order, or mixing constants derived under different
upstream assumptions, are all common and all produce a scale error that is difficult to
diagnose from the final numbers alone.

Record the full chain, in order, with the payload version of each step. "Which
calibration was applied" is not a single answer.

### Test-beam versus in-situ calibration

**Test-beam** calibration measures the response of detector modules to particles of
known type and energy before installation. It gives an absolute, well-controlled
reference, but it applies to a small sample of modules, under conditions - no magnetic
field, no surrounding material, no pileup, pre-irradiation - that differ from the final
environment. Test-beam constants are a starting point, not a final answer.

**In-situ** calibration derives constants from the data itself, using physics that is
known independently: a resonance of known mass, momentum-energy consistency (`E/p`),
back-to-back balance in transverse momentum, or the uniformity of an isotropic flux.
It is the only way to capture the real environment and its time evolution, and it is
what sets the achievable constant term of a calorimeter (see
[Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic)).

The limitation of in-situ calibration is circularity: the reference physics is measured
with the same detector being calibrated. A resonance mass calibration constrains the
energy scale at the resonance's energy and must be extrapolated elsewhere, and the
extrapolation - not the calibration point - is usually the dominant uncertainty. State
where the calibration is anchored and how far it is extrapolated.

### Alignment and weak modes

Alignment determines the actual positions and orientations of sensors, typically by
minimizing track residuals over a large sample. The residual-minimization approach has
a structural blind spot that deserves explicit attention.

**Weak modes** are coherent detector deformations that leave track residuals almost
unchanged while systematically biasing the fitted track parameters. Because the
alignment procedure minimizes exactly the quantity that weak modes do not affect, they
are invisible to it by construction, and internal fit quality gives no warning.

The dangerous ones bias curvature. A deformation that adds a curvature offset shifts
positive and negative particles in *opposite* directions - a charge-antisymmetric
rigidity bias - which directly fakes any charge-ratio or antiparticle-fraction
measurement, and which no amount of chi-square improvement will reveal. Related modes
produce a rigidity scale error that grows with rigidity, mimicking or masking a
spectral feature.

Weak modes must be constrained with information the alignment fit does not use:

- **A resonance of known mass**, whose reconstructed mass must not depend on the
  charge, the direction, or the momentum of its decay products.
- **`E/p` symmetry** between positive and negative particles - a calorimeter energy
  measurement is charge-blind, so a charge-dependent `E/p` is a tracker alignment
  signature, not a calorimeter one.
- **Cosmic-ray or halo tracks** traversing the detector, which are fitted as two
  independent halves and compared; a coherent deformation appears as a mismatch.
- **Comparison of independent subdetectors** measuring the same track.
- **Field-reversal or detector-inversion running**, where available, which changes the
  sign of the physics effect but not of the instrumental one.

Every measurement sensitive to charge sign or to the high-rigidity spectrum should
state which of these constrains its charge-antisymmetric bias, and quote the resulting
limit as a systematic. See [Chapter 6](#chapter-6-tracking-and-vertexing).

### Time dependence and conditions data

Detectors change: gains drift with temperature, sensors accumulate radiation damage,
gas composition and pressure vary, channels die, and alignment moves with thermal
cycles and magnet ramps. Calibration constants are therefore time-dependent payloads
indexed by run or by a finer interval-of-validity, and this creates its own set of
requirements:

- **Simulation must reproduce the time-averaged conditions**, weighted by the
  luminosity or exposure actually collected - not the conditions at any single moment.
  A simulation using a single snapshot of the dead-channel map or the gain set is
  systematically wrong for the dataset as a whole.
- **Analyses combining periods must confirm the constants were applied consistently**
  in each, and should check stability by repeating the measurement per period. A
  result that varies across periods beyond its statistical uncertainty has an
  unaccounted conditions problem, and finding it after unblinding is much worse than
  finding it before.
- **Reprocessing changes results.** A sample reconstructed with a newer payload is a
  different sample; mixing processings within one measurement requires explicit
  justification and a comparison.
- **Interval-of-validity boundaries are a real failure mode.** Data near a boundary
  can pick up the wrong payload if the intervals are misaligned with the run
  structure, producing a small population of badly-calibrated events that shows up as
  a non-Gaussian tail rather than a shift.

### Propagating a calibration change

Because a calibration constant sits at the base of the chain, changing it changes
efficiencies, resolutions, scale factors, background estimates derived from control
regions, and the trained response of any classifier that used the affected variables.
A calibration update is therefore not a local change:

- Re-derive, do not reuse, any scale factor or data-driven background estimate that
  was measured with the old constants.
- Re-validate classifiers whose input distributions have moved, following
  multivariate analysis.
- Compare the affected distributions before and after with an explicit method - event
  counts per cut, histogram integrals, maximum absolute and relative bin difference -
  as required for any change that risks altering physics output.
- Keep the calibration uncertainty correlated across regions and samples where it
  shares a source; treating the same energy-scale uncertainty as independent between a
  signal and a control region is a standard way to understate a systematic. See
  systematic-uncertainty implementation.

### Deliverables

- The calibration chain in the order applied, with the payload version of each step.
- Which constants come from test beam and which from in-situ measurement, with the
  in-situ anchor point and the range over which it is extrapolated.
- The alignment procedure, the weak modes considered, and the external constraint
  bounding a charge-antisymmetric rigidity bias, with its quoted limit.
- Time dependence of the constants, and confirmation that simulation reproduces the
  exposure-weighted average conditions rather than a snapshot.
- A per-period stability check for any measurement combining data-taking periods.
- For any calibration update: what was re-derived, what was re-validated, and a
  before/after comparison of the affected distributions.
- Correlation treatment of calibration uncertainties across regions and samples.

### Common misconceptions and failure modes

- **Tuning on the measured observable**, then reading agreement as validation (circularity).
- **Calibration order treated as irrelevant.** The order of the chain is part of the definition of each constant.
- **Test-beam constants applied unchanged in situ**, or a calibration applied to data but not simulation.
- **A good alignment `chi^2` taken as proof of correct alignment.** Weak modes leave it nearly unchanged.
- **Constants assumed static.** Intervals of validity, temperature, high voltage, and dose all move them.

## Chapter 6: Tracking and Vertexing

Covers charged-particle trajectory measurement: the sensor technologies, how hits
become tracks, what the track fit actually estimates, and where tracking failures
enter an analysis as efficiency loss, fakes, or charge confusion. Builds on the
rigidity and multiple-scattering material in
[Chapter 4](#chapter-4-detector-systems-overview); the downstream use of
reconstructed tracks in jets, b-tagging, and missing transverse momentum is in
jet, b-tagging, and missing-momentum reconstruction.

### Sensor technologies

**Silicon pixel and strip** detectors collect electron-hole pairs created by
ionization in a depleted semiconductor. Pixels give unambiguous two-dimensional
position at high occupancy and are used closest to the interaction point where track
density is highest; strips give one precise coordinate per sensor at much lower
channel count and cost, with the second coordinate obtained from a stereo layer at a
small crossing angle. That stereo arrangement introduces **ghost hits**: two genuine
particles crossing a stereo pair produce four candidate intersections, only two of
which are real. Ghost rate grows quadratically with occupancy, which is why strip
detectors are placed outside the highest-density region.

Silicon position resolution is set by pitch and by charge sharing. A binary readout
(hit/no-hit) gives a resolution of pitch divided by the square root of twelve; analog
or multi-threshold readout that interpolates the charge division between neighboring
channels does substantially better, at the cost of calibration complexity - the
interpolation depends on the charge-sharing model, which is itself a calibration that
drifts with radiation damage and bias voltage.

Silicon also measures deposited charge, which is proportional to `Z^2` for a
traversing nucleus. A silicon tracker is therefore simultaneously a charge (|Z|)
measuring device, and multi-layer charge consistency is a powerful rejection tool
against interactions and against tracks built from mismatched hits - see
[Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems) for the dE/dx treatment.

**Gaseous detectors** - time projection chambers, drift chambers, straw tubes -
measure ionization in a gas volume and reconstruct position from drift time, requiring
a known drift velocity and a start time. They offer very low material budget per
measurement and, in the TPC case, hundreds of samples along a track for excellent
dE/dx, at the cost of slower response and a drift-velocity calibration sensitive to
gas composition, temperature, and pressure. A drift-time measurement converts an
uncertainty in the event start time directly into a position bias common to all hits,
which the track fit will partly absorb into the trajectory parameters rather than
flagging - a class of error that shows up as an apparent alignment problem.

### From hits to tracks: pattern recognition

Pattern recognition is the combinatorial problem of deciding which hits belong to the
same particle, and it is where most tracking inefficiency and nearly all fake tracks
originate. Seeding starts from a small number of hits consistent with a plausible
trajectory; the seed is then extrapolated outward or inward, collecting compatible
hits within a search window that must account for multiple scattering and for the
current parameter uncertainty.

Two failure modes dominate and pull in opposite directions. Too tight a search window
loses hits after a scatter and truncates or splits the track, costing efficiency. Too
loose a window collects wrong hits, producing a track whose fit is contaminated -
often with a plausible chi-square, because the fit will shift the trajectory to
accommodate the outlier. The tuning between them is not neutral with respect to
physics: it is momentum dependent (low-momentum tracks scatter more and need wider
windows) and density dependent, so tracking performance is not a single number but a
function of momentum, direction, and local occupancy.

**Ambiguity resolution** follows: multiple track candidates sharing hits must be
reduced to a consistent set, typically by ranking on hit count and fit quality and
removing candidates that share too many hits with a better one. The shared-hit
threshold is a tunable parameter that directly trades duplicate tracks against
efficiency for genuinely nearby tracks, such as those in a dense jet core or a
collimated decay.

### The track fit

A track fit estimates trajectory parameters - typically a position and direction at a
reference surface plus a curvature - from the collected hits. The **Kalman filter**
formulation is standard because it handles multiple scattering naturally: rather than
treating the trajectory as a single deterministic curve, it propagates the parameter
estimate and its covariance layer by layer, inflating the covariance at each material
crossing by the expected scattering. This makes the fit's own uncertainty estimate
depend on the material model - so an incorrect material description produces
incorrect, usually overconfident, track parameter errors, without any obvious symptom
in the fitted values themselves.

Several points routinely cause trouble:

- **The chi-square is not a sufficient quality measure.** A fit that absorbed a wrong
  hit by shifting the trajectory can have an unremarkable chi-square. Combine it with
  hit count, missing-layer pattern, and where available a charge-consistency or
  timing-consistency requirement.
- **Parameter errors are correlated.** The covariance between curvature and direction
  is large; propagating a momentum uncertainty into a derived quantity using only the
  diagonal element understates or overstates it depending on the derived quantity.
  Use the full covariance matrix.
- **The fit is biased at low momentum** by energy loss, which must be corrected during
  propagation using an assumed particle mass. That mass assumption is a hidden input:
  a track fitted under a pion hypothesis and then used as a proton has a small,
  systematic momentum bias.
- **Fitting quality varies across the detector.** Efficiency and resolution must be
  quoted differentially in the relevant variables, not integrated.

### Rigidity resolution and its two regimes

As introduced in [Chapter 4](#chapter-4-detector-systems-overview), a
spectrometer's relative rigidity resolution combines an intrinsic-resolution term
that grows linearly with rigidity and a multiple-scattering term that is roughly
constant in rigidity (falling as `1/(beta p)` in angle, which translates to an
approximately rigidity-independent contribution to `sigma(R)/R` in the relativistic
regime). Added in quadrature they give a curve with a minimum at the crossover
rigidity, degrading in both directions.

The intrinsic term scales with the sensor resolution, inversely with the field
integral, and inversely with the square of the lever arm, which is why lever arm is
the most valuable quantity in a spectrometer design and why tracks that fail to reach
the outermost layer have sharply worse resolution. Selections requiring a full-span
track are therefore selecting on resolution, which correlates with the physics being
measured and must be accounted for in the efficiency correction.

`multiple_scattering.py` evaluates the Highland scattering angle for a
material stack, the accumulated budget, and the crossover rigidity for a given
intrinsic resolution, which is the quickest way to check whether an observed
resolution curve is consistent with the detector's material.

### Charge confusion

At high rigidity, where `sigma(R)/R` approaches unity, the measured curvature can
change sign. The resulting **charge confusion** migrates particles into the
oppositely-charged sample and is a background whose rate is set by the resolution
function's tail, not its core. This is the practical reason a core-Gaussian resolution
description is inadequate: the confusion probability is entirely a tail property, and
a Gaussian extrapolation underestimates it, often by orders of magnitude.

Control it by measuring the tail directly rather than modeling it - using a
independent estimate of the same track (an independent subset of layers, or a second
tracking system), or a sample of known charge sign. Analyses of charge ratios,
antiparticle fractions, or any rare oppositely-signed species should treat charge
confusion as a dedicated background component in the likelihood, with its own
nuisance parameter, following
background estimation.

### Vertexing

A vertex fit estimates a common origin for several tracks, and its resolution is
dominated by the extrapolation distance from the innermost measurement to the vertex -
which is why the innermost layer's radius and material budget dominate impact
parameter resolution, and why impact parameter resolution degrades at low momentum
where scattering in that first layer matters most.

The impact parameter - the distance of closest approach between a track and a
reference point - underlies displaced-vertex identification and lifetime-based
tagging. Its resolution has an approximately constant term from sensor precision plus
a scattering term falling with momentum, and quoting it without the momentum
dependence hides the regime where it matters. Secondary vertex finding must also
contend with material interactions producing genuine displaced vertices that are not
signal; a map of reconstructed vertices reproduces the detector material layout, and
that map is both a background to reject and a useful tool for validating the material
model against data.

### Alignment coupling

A track fit assumes it knows where the sensors are. Alignment errors propagate
directly into trajectory parameters, and the dangerous ones are not random
misplacements - which mostly inflate chi-square and are visible - but coherent
distortions that the fit can absorb without degrading chi-square at all. A systematic
deformation that mimics a curvature produces a rigidity bias that is
charge-antisymmetric, meaning it shifts positive and negative particles in opposite
directions and directly fakes a charge-ratio signal. These **weak modes** are
invisible to internal fit quality by construction and must be constrained with
external information - see
[Chapter 5](#chapter-5-calibration-and-alignment).

### Deliverables

- Tracker technology, layer layout, lever arm, and material budget per layer.
- Track selection actually applied (minimum hits, required layers, fit quality,
  charge consistency) and its efficiency measured differentially in momentum and
  direction, not integrated.
- Rigidity or momentum resolution as a function of rigidity, with the scattering and
  intrinsic regimes identified and the crossover stated.
- Maximum detectable rigidity and, for any charge-sensitive measurement, the charge
  confusion estimate with its measurement method and its treatment in the likelihood.
- Mass hypothesis used in the fit's energy-loss correction, where it affects the
  measurement.
- Impact parameter and vertex resolution quoted with momentum dependence.
- Alignment weak modes considered, and what external constraint bounds a
  charge-antisymmetric rigidity bias.

### Common misconceptions and failure modes

- **One resolution number.** Rigidity resolution has two regimes (multiple-scattering-dominated and measurement-dominated) with a crossover.
- **Charge confusion assumed negligible.** It grows steeply toward the maximum detectable rigidity.
- **Pattern-recognition efficiency quoted without fakes and duplicates.**
- **Alignment or field error mistaken for noise.** Coherent residual trends are systematics, not resolution.
- **Gaussian vertex errors** assumed when a mis-associated track or a nuclear interaction dominates the tail.

## Chapter 7: Gaseous and Specialized Tracking Technologies

Technology-specific reconstruction for trackers beyond the general treatment in
[Chapter 6](#chapter-6-tracking-and-vertexing): drift chambers and tubes, TPCs, MWPCs, straw
trackers, RPCs, micro-pattern gaseous detectors (GEM, Micromegas), scintillating
fibers, nuclear emulsions, monolithic and other silicon variants, and radiation-hard
sensors. Physics of signal formation is in
[Chapter 3](#chapter-3-signal-formation-transport-and-readout); alignment and drift calibration in
[Chapter 5](#chapter-5-calibration-and-alignment). Each family ends with the required
**Distinctive but generalizable reconstruction and performance features** block.

### Silicon pixels and strips (recap of what is distinctive)

**Hybrid pixels**: 2D binary or ToT-encoded hits; charge sharing among neighbors
gives sub-pixel position by centroid or by template (charge-profile) fit; the
**Lorentz drift** shifts and broadens clusters in a field (calibrate `theta_L`);
merged clusters at high density; radiation damage lowers `CCE` and shifts thresholds
and depletion voltage.

**Strips/microstrips**: 1D measurement; a 2D point needs a stereo pair, creating
`n^2` ghost combinations for `n` hits; capacitive coupling, common-mode noise, and
occupancy dominate ambiguity.

**MAPS, depleted MAPS, CCD, DEPFET**: sensor and first amplification integrated, so
low material and small pitch (excellent vertexing) at the price of slower or
rolling readout (integration-time ambiguity, hit-time association) and, for MAPS,
smaller depleted region (less charge, more diffusion-driven sharing).

#### Distinctive but generalizable reconstruction and performance features (silicon)

- **Information topology**: sparse points with cluster structure.
- **Unique inverse problem**: position from shared charge; degeneracy: ghosts
  (strips), merged clusters (pixels).
- **Natural objects**: cluster, hit, track seed. **Most informative residual**:
  unbiased track-to-hit residual in the sensor's measurement direction, versus
  incidence angle and cluster size.
- **Scaling**: hit resolution `~ pitch/sqrt(12)` (binary, approximate) improved by charge
  sharing; momentum and impact-parameter floors from multiple scattering and lever
  arm ([Chapter 6](#chapter-6-tracking-and-vertexing)).
- **Tails**: delta rays, merged clusters, noise hits, dead/noisy channels.
- **Dependence**: occupancy, pileup, dose (leakage, `CCE`, threshold, Lorentz angle
  drift), temperature. **Data sample**: `Z -> ll`/cosmic tracks for hit efficiency
  and alignment, overlaps and tag-and-probe for module efficiency.
- **Transfers**: charge-sharing interpolation and template methods to any segmented
  readout (TPC pads, fibers); does not transfer: time-of-arrival coordinates.

### Drift chambers and drift tubes

**Measurement.** Time `t` between passage and arrival at a sense wire is converted to
distance by the **time-to-distance relation** `r(t)` (space-time relation), calibrated
per cell and per operating condition (`v_d` depends on gas, `T`, `P`, `E`, `B`; the
relation is nonlinear near the wire and cell boundary).

**Pieces.** `t0` (event/particle passage time relative to the clock), time walk
(amplitude-dependent discriminator delay), signal propagation along the wire, wire
**sag** (gravitational/electrostatic), and stereo/small-angle wires for the second
coordinate. A drift measurement gives a *radius*, not a point: **left-right
ambiguity** (the particle passed one side of the wire or the other), resolved by
adjacent-layer staggering, by segment or track fit, or by wire signal timing.

**Reconstruction.** Segment building within a chamber (line fit through
`(z, +-r)` circles with a two-fold ambiguity per layer), then linking segments to
tracks.

**Diagnostics.** Residual versus drift distance (the standard plot): a symmetric
structure means the `r(t)` calibration or `t0` is wrong; a tilt versus distance means
drift-velocity error; different left/right means alignment or `t0`. Residual versus
angle and versus amplitude reveal time walk and crossing-angle effects.

#### Distinctive but generalizable reconstruction and performance features (drift systems)

- **Topology**: sparse radius measurements (hits are circles around wires).
- **Inverse problem**: `r` from `t` needs `v_d`, `t0`, geometry; degeneracy:
  left-right, wire-position (sag), `t0` versus alignment (a timing offset looks like
  a spatial shift - see [Chapter 5](#chapter-5-calibration-and-alignment)).
- **Objects**: drift circle, segment, track. **Informative residual**: residual
  versus drift distance and versus angle.
- **Scaling**: single-hit resolution limited by diffusion (`~ sqrt(L)`), primary
  ionization statistics near the wire, electronics; efficiency drops near cell boundary
  and wire.
- **Tails**: delta rays, late clusters from ionization far from the wire (`t` early ->
  underestimated distance), out-of-time hits.
- **Dependence**: rate/occupancy (space charge, deadtime), `T`/`P`/gas composition
  (drift velocity), aging (Malter effect, deposits on wires).
- **Data sample**: cosmic rays and collision tracks for `r(t)` self-calibration.
- **Transfers**: time-to-distance calibration to RPC, muon-tube, TOP-like timing
  coordinates; does not transfer: charge-centroid interpolation.

### Time projection chambers (TPC)

**Principle.** Ionization electrons from a track drift in a uniform `E` (and often
parallel `B`) to a readout plane: the transverse coordinates come from where they
arrive, the third from arrival time (`z = v_d (t - t_0)`), giving a continuous 3D
image and many `dE/dx` samples per track.

**Pieces.** Diffusion (transverse `~ sqrt(L)`; reduced by `B`), gain stage
(wires, GEM, Micromegas), **ion backflow** (positive ions drifting back distort `E`),
**space-charge distortions** (a radially and `z`-dependent position shift), field-cage
and `E x B` distortions, gating, and **crossing-time ambiguity**: the absolute drift
coordinate needs the interaction time `t_0`, unknown for particles not associated with
a bunch crossing or trigger (pileup/out-of-time tracks are displaced along `z`).

**`dE/dx`.** Truncated mean or cluster counting over `~10^2` samples, corrected for
path length, saturation, gain, and attachment ([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)).

#### Distinctive but generalizable reconstruction and performance features (TPC)

- **Topology**: dense 3D point cloud/image; many samples per track.
- **Inverse problem**: 3D position and `t_0`; degeneracies: `z` vs `t_0`; distortion
  vs alignment.
- **Objects**: cluster, track, `dE/dx` vector. **Informative residual**: cluster-to-track
  residuals vs radius/`z`/`phi`, and matching to an outer (or inner) precision tracker
  as a distortion map.
- **Scaling**: `sigma_xy ~ sqrt(sigma_0^2 + C_D^2 L/N_eff)`; momentum resolution from
  lever arm and `B`, with a stable multiple-scattering term; `dE/dx` resolution improves
  with the number of samples.
- **Tails**: track merging at high density, distortion-induced tails, `z` offset for
  out-of-time tracks.
- **Dependence**: rate and ion backflow (space charge), `T`/`P`, gas purity (attachment
  and diffusion), field homogeneity. **Data sample**: laser/UV lines or cosmic tracks and
  cross-detector matching to map distortions.
- **Transfers**: drift-plus-readout concept to noble-liquid TPCs
  ([Chapter 13](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors)) and any imaging detector;
  does not transfer: gas-specific diffusion and ion-backflow numerology.

### MWPCs, straw tubes, and RPCs

- **MWPC**: wire planes with proportional gain; hit position from the wire (pitch/`sqrt(12)`)
  or from induced cathode charge for the second coordinate; fast, robust; limited
  granularity and rate by wire pitch and space charge.
- **Straw-tube tracker**: many thin drift tubes; combination of drift measurement and a
  large number of hits per track (good tracking robustness at low material); also the
  basis for transition radiation stacks (electron ID, [Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems));
  left-right ambiguity per straw resolved by staggered layers.
- **RPC / multi-gap RPC (MRPC)**: resistive plates with a gas gap and a high
  uniform field; fast signal from a streamer/avalanche, strip readout, timing resolution
  much better than a drift chamber (in MRPC many narrow gaps); efficiency and time
  resolution depend on rate (plate resistivity limits rate capability), gas mixture, and
  applied voltage; used for trigger muon layers and time of flight ([Chapter 8](#chapter-8-timing-detectors-and-time-measurement),
  [Chapter 12](#chapter-12-muon-systems-spectrometers-identification-and-trigger)).

#### Distinctive but generalizable reconstruction and performance features (wire/RPC)

- **Topology**: sparse points/segments. **Ambiguity**: left-right (straws), ghosts
  (wire crossing), efficiency dead zones at wire/cell edges and spacer positions.
- **Informative residual**: layer-by-layer (unbiased) residual versus position in the
  cell. **Scaling**: RPC rate capability inverse to resistivity; timing set by gap
  width and gas.
- **Tails**: streamers, afterpulses, cluster-size multiplicity growth with high
  voltage. **Data sample**: cosmic/collision muons for efficiency versus voltage
  (efficiency-plateau scan).
- **Transfers**: plateau-scan concept (efficiency vs voltage) to every gas detector.

### Micro-pattern gaseous detectors (GEM, Micromegas, and relatives)

**Principle.** Micro-structured gain (GEM holes; Micromegas mesh over a narrow
amplification gap) gives high rate capability, fine pitch, and fast signals compared with
wires. **Reconstruction.** Pad/strip charge centroid or template; cluster size and
charge sharing set position resolution; a mesh-anode gap gives, in **micro-TPC** mode
(drift plus fine gap), a track segment per chamber and thus angle information.

**Failure/response features.** Gain nonuniformity (hole/gap geometry), **discharges**
(sparks that cause dead time and can damage readout), charge spreading, **rate
effects** (space charge, gain drop), and time resolution set by gap and gas.

#### Distinctive but generalizable reconstruction and performance features (MPGD)

- **Topology**: pad/strip images. **Ambiguity**: 2D projections (strips) and
  charge-sharing symmetry. **Informative residual**: residual vs incident angle
  (strong dependence for inclined tracks unless micro-TPC mode is used).
- **Scaling**: position resolution ~ (pitch and diffusion)/`sqrt(cluster size)`;
  rate capability set by gain and space charge.
- **Tails**: discharge events, gain-nonuniformity-induced position biases.
- **Data sample**: cosmic/test-beam and in-situ tracks for gain map.
- **Transfers**: charge-centroid/micro-TPC to other segmented gas detectors.

### Scintillating-fiber trackers

**Principle.** Light from a scintillating fiber is guided to a photosensor (SiPM
array, [Chapter 10](#chapter-10-cherenkov-imaging-variants-and-photosensors)); multi-layer stacks at a
small stereo angle provide two coordinates. **Distinctive**: light attenuation along
the fiber (position along the fiber changes amplitude), light sharing between adjacent
fibers (used for sub-pitch position), **multi-layer ambiguity** (ghost hits in
stereo), channel-mapping errors, SiPM noise/crosstalk and radiation-induced dark count,
and time information that can assist matching in high rate. Resolution ~ fiber pitch
`/sqrt(12)` improved by light sharing; efficiency depends on attenuation and threshold.

#### Features (fibers)

- **Topology**: sparse points with amplitude. **Residual**: hit-to-track by layer and
  versus position along fiber (attenuation signature).
- **Tails**: ghosts, cross-talk clusters, mapping errors, dark-count hits.
- **Dependence**: dose (SiPM dark rate), temperature (gain), rate.
- **Transfers**: amplitude-based interpolation and attenuation correction to
  scintillator calorimeters and timing layers.

### Nuclear emulsions

**Principle.** Ionizing particles sensitize silver-halide grains; development
produces **grains**, chained into **microtracks** in each emulsion layer, linked across
the plastic base into **base-tracks**, then into tracks and **vertices**. Spatial
resolution is superb (sub-micron grain scale), giving unmatched vertex/kink topology,
but there is **no intrinsic timing** (integrated over exposure) so track-to-event
association relies on electronic detectors, and analysis is dominated by scanning
efficiency, track density (overlap), fading, and distortion of the emulsion.

#### Features (emulsion)

- **Topology**: dense micro-scale 3D image with no time axis.
- **Inverse problem**: link tracks across layers; degeneracy: time assignment.
- **Informative residual**: base-track slope/position agreement between
  layers; **scaling**: resolution set by grain size and layer alignment; limits by
  fluence (track overlap).
- **Tails**: fake links at high density, scanning inefficiency near edges.
- **Data sample**: passing-through tracks (cosmic/beam) for alignment;
  **transfers**: precise-vertex and kink analysis to silicon vertex detectors; **does
  not transfer**: event timing.

### Diamond and other radiation-hard sensors

Diamond and other wide-bandgap sensors (e.g. silicon carbide) offer low leakage current and
tolerance to very high fluence at the cost of smaller signal and lower charge
collection in poly-crystalline material. Reconstruction is the same as for silicon
(cluster/charge or timing), with the focus on **response versus dose** (pumping,
priming, polarization), efficiency loss with fluence, and beam/luminosity monitor
use. Quote fluence-dependent signal loss only with its source and conditions
([Chapter 8](#chapter-8-timing-detectors-and-time-measurement), [Chapter 18](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination)).

### Common misconceptions and failure modes

- **Left-right ambiguity resolved by hoping.** It must be resolved by geometry or fit; a
  wrong choice produces a systematic residual sign structure.
- **Hiding `t0` in alignment (or vice versa).** A timing offset displaces drift-coordinate
  measurements just like a misalignment ([Chapter 5](#chapter-5-calibration-and-alignment)).
- **TPC distortion mistaken for resolution.** Coherent, position-dependent shifts appear
  as broadened or biased residuals, not as noise.
- **Plateau efficiency taken as a quality measure across rate.** RPC/MPGD efficiency
  degrades with rate; measure at operating rate.
- **Emulsion has no timing.** Analyses that need timing must import it from other
  detectors and inherit their systematic.
- **Neglecting angle dependence in MPGDs.** Position bias grows with track inclination.

### Deliverables

- The technology's natural residual and the essential performance plots, with the
  failure signature each catches.
- The ambiguity resolved (left-right, ghost, `t_0`) and how.
- Efficiency versus voltage/rate/occupancy and the operating point.
- The distinctive-but-generalizable block for each family used.

## Chapter 8: Timing Detectors and Time Measurement

Timing and fast detectors: time-of-flight (TOF), fast scintillator layers, low-gain
avalanche detectors (LGAD, including ultra-fast silicon), microchannel-plate (MCP) timing
detectors, precision timing in trackers and calorimeters, and beam/start-time,
bunch-timing, and luminosity monitors. The TOF physics (`beta`, `m^2`, separation
ceiling) is in [Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems); event-level timing/association is in
[Chapter 14](#chapter-14-event-reconstruction); `pid_separation_power.py` evaluates
TOF separation. This file adds the timing-error budget and the objects.

### Relations (definition, exact unless noted)

```
beta = L / (c t)        m^2 = p^2 (1/beta^2 - 1)      Delta t = (L/c) [ (1/beta_1) - (1/beta_2) ]
```

`L` path length along the track (not straight-line distance; requires the track fit),
`t` measured flight time (stop minus start), `p` momentum. The TOF separation of two
species with the same `p` in the ultrarelativistic limit is
`Delta t ≈ (L/(2 c p^2))(m_1^2 - m_2^2)` (approximate); separation in `N_sigma` falls as
`1/p^2` and is lost above a momentum set by `L` and total time resolution.

### Pulse-time extraction

- **Leading-edge discriminator**: fixed threshold; **time walk** (larger pulses cross
  earlier) must be corrected with amplitude or ToT (a calibration curve per channel).
- **Constant-fraction discrimination (CFD)**: time at a fixed fraction of the peak;
  removes amplitude dependence to first order, at the cost of jitter and pulse-shape
  sensitivity (an input to calibration).
- **Waveform fit / template**: best precision if the pulse shape and noise are known;
  fits amplitude and time jointly.

The **jitter** term is `sigma_t ≈ sigma_noise/(dV/dt)` (noise over slope; approximate
for a Gaussian noise and linear rising edge), which is why fast, high-gain, low-noise
front ends win.

### Time-resolution budget (single hit)

`sigma_t^2 = sigma_sensor^2 + sigma_photostat^2 + sigma_elec^2 + sigma_clock^2 +
sigma_calib^2 + sigma_geom^2 + sigma_ref^2`

| Term | Origin | Scaling / handle |
|---|---|---|
| Sensor / intrinsic | transit-time spread (PMT), Landau (silicon), drift (gas) | detector design; irreducible per hit |
| Photostatistics | `~ tau/sqrt(N_pe)` (rise/decay time) | more photons |
| Electronics | jitter (`noise/slope`), TDC bin `/sqrt(12)`, time walk | design, calibration |
| Clock | distribution jitter and offsets | common to all channels: *not* averaged by combining channels |
| Calibration | `t0` per channel, walk curve, cable/fiber delay | in-situ residual method |
| Geometry | path length, position along the bar, `L` error | tracking quality |
| Reference/start time | collision time, event-start time | dominates in busy events |

Keep four resolutions apart: **single-hit** (one channel), **per-track** (all hits on
one track, after averaging the uncorrelated part), **event-time** (start time
estimated from many tracks), and **system** (what the analysis sees, including the
common-mode clock and reference terms). Averaging `N` hits reduces only the
uncorrelated terms as `1/sqrt(N)`; correlated ones (clock, `t_ref`) remain.

**Track-to-hit association and multi-hit ambiguity.** A time is meaningless without the
right track: extrapolate the track to the layer, match by position (and time), and
resolve multiple candidate hits/tracks per cell. Wrong association creates a late/early
tail. **Bunch assignment**: the measured time must be assigned to the right bunch
crossing; out-of-time pileup and late tails (afterpulses, delayed light, slow
components) produce non-Gaussian tails and mis-assigned bunches, so quote core width
and tail fraction separately.

### Technologies

- **Fast scintillator with PMT/SiPM (TOF bars, layers)**: `~ tens of ps` class
  achievable in principle by photostatistics, limited in practice by electronics,
  clock, position along the bar, and light-collection non-uniformity (quote only from a
  named apparatus). Position along the bar from time difference of two ends.
- **LGAD / ultra-fast silicon**: internal gain of order 10-30 with a thin sensor gives
  a steep, low-jitter pulse; time resolution is limited by Landau fluctuations in
  the thin depletion region and by the electronics; **radiation damage** reduces the
  effective doping (gain layer), so gain and time resolution degrade with fluence and
  operating voltage must be raised (single-event burnout limit); fill factor at
  pad boundaries is a design issue.
- **MCP timing detectors**: fast rise and small transit-time spread; used as
  precision photon/particle timing; aging by charge extracted, ion feedback.
- **RPC/MRPC**: gas gap timing, rate-dependent ([Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies)).
- **Precision timing in trackers/calorimeters**: time assigned to tracks or clusters
  (e.g. shower-time for photons, vertex-time for pileup rejection); needs the same
  calibration/clock discipline, and a time-of-arrival correction for shower depth and
  time-walk with energy.
- **Beam/start-time, bunch-timing, luminosity monitors**: give `t_0` and bunch
  identification; beam-phase drift and asymmetric bunch shapes are systematic inputs to
  every timing analysis (trigger, luminosity, and pileup methodology). Luminosity monitors
  count coincidences or hits and carry their own linearity/pileup correction.

### Calibration and diagnostics

Per-channel `t0` and walk from a common reference (laser, pulser, minimum-ionizing
particle), then global offset (start time) and clock-transfer from the accelerator
clock; validated with **time residuals** `t_meas - t_pred(p, m, L)` per species, using a
sample of known particle type (muons, identified pions, electrons at `beta = 1`).
Residual versus amplitude reveals walk; versus position along the bar reveals
propagation; versus run/fill reveals clock drift.

#### Distinctive but generalizable reconstruction and performance features (timing)

- **Topology**: time series per hit; one scalar per channel, sometimes with waveform.
- **Inverse problem**: `t` from a noisy pulse; degeneracy: absolute offset versus
  reference time versus path length.
- **Natural objects**: hit time, track time, event start time. **Informative
  residual**: time residual to the expected time for a known species vs amplitude,
  position, and run.
- **Scaling**: `1/sqrt(N_pe)` and `noise/slope`; TOF separation `~ L/p^2`.
- **Conventions**: quote resolution with the reference, core Gaussian sigma and tail
  fraction; state whether clock jitter is included.
- **Tails**: wrong-bunch, afterpulses, late light, mis-association.
- **Dependence**: rate (baseline shifts), dose (LGAD gain, SiPM dark counts), temperature,
  clock distribution. **Data sample**: `Z`/`J/psi -> mu mu` or cosmic muons, identified
  species in overlapping momentum ranges.
- **Transfers**: walk/offset calibration and jitter budget to every timed detector;
  **does not transfer**: TOF's `1/p^2` separation ceiling to non-timing PID.

### Common misconceptions and failure modes

- **Quoting single-channel resolution as system resolution.** Correlated clock and
  reference terms do not average.
- **Ignoring path length.** A 1 cm error on `L` matters; it comes from the track fit.
- **Time-walk not corrected.** Looks like a momentum- or amplitude-dependent
  mass-hypothesis shift.
- **Radiation damage treated as a static constant.** LGAD/SiPM timing evolves with
  dose and operating point.
- **Clock offsets look like PID or alignment problems.** Check run-by-run/fill-by-fill
  offsets first ([Chapter 19](#chapter-19-detector-to-physics-bias-case-studies-checklists-and-synthesis)).

### Deliverables

- A time-resolution budget with each term's origin and whether it averages.
- Single-hit, per-track, event-time, and system resolutions, with tail fractions.
- The association rule (track-to-hit, bunch assignment) and its failure rate.
- Calibration chain (`t0`, walk, clock) and the residual used to validate it.

## Chapter 9: Particle Identification: TRD, TOF, RICH, dE/dx, and Muon Systems

Covers how detectors determine *what* a particle is, as opposed to where it went and
how much energy it carried. Every technique here measures velocity, Lorentz factor, or
charge, and converts that - combined with the rigidity from
[Chapter 6](#chapter-6-tracking-and-vertexing) - into a mass or species
hypothesis. Organized by technology and independent of experiment; calorimeter-based
identification (`E/p`, shower shape) is in
[Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic).

### The common principle

A magnetic spectrometer measures rigidity `R = p/q`. Mass does not appear. To identify
a particle you need a second, independent measurement that depends on mass through a
different combination of variables - and every technique below is a way of measuring
either velocity `beta` or Lorentz factor `gamma`:

    m = p / (beta * gamma) = (p / beta) * sqrt(1 - beta^2)

The precision of the resulting mass therefore depends on the precision of *both*
measurements, and because `gamma` grows without bound while `beta` saturates at 1, every
velocity-based technique has a momentum ceiling above which the species become
indistinguishable. Where that ceiling sits is the single most important number to
quote for any PID system. Propagating `dm/m` from `dbeta/beta` gives

    dm/m = gamma^2 * (dbeta/beta)   (at fixed momentum)

- the `gamma^2` factor is why velocity-based identification degrades so quickly with
momentum, and why different technologies are needed in different momentum bands.
`pid_separation_power.py` evaluates this for time-of-flight and ionization
measurements, and `cherenkov_angle.py` for ring-imaging detectors.

### Time of flight (TOF)

A TOF system measures the time a particle takes to traverse a known flight path `L`,
giving `beta = L / (c * t)` directly. Two scintillator planes (or any two timing
layers) define the path; the resolution is set by the timing resolution `sigma_t` of
the pair and by the uncertainty in `L`, which comes from the track fit.

Separation between two species of mass `m1` and `m2` at momentum `p` follows from
their time difference over the same path, which for relativistic particles scales as

    dt ~ (L / 2c) * (m1^2 - m2^2) / p^2

The `1/p^2` is decisive: TOF separation power falls as the square of momentum, so a
system with a given timing resolution has a sharp practical ceiling - typically a few
GeV/c for pion/kaon separation with sub-100-picosecond timing over a metre-scale path.
Extending the reach requires a longer path or better timing, and both scale only
linearly against a quadratic loss.

Practical points that dominate real TOF performance:

- **The start time must be known.** At a collider it comes from the bunch crossing or
  from a dedicated start detector; in a non-collider experiment one plane defines the
  start. An error in start time is common to all particles in the event and biases
  every `beta` in the same direction - so it does not average out and shows up as a
  species-dependent mass shift.
- **Path length is a track-fit output**, not a constant. For curved tracks it depends
  on the fitted trajectory, and using a straight-line approximation at low momentum
  introduces a bias that grows exactly where TOF is most useful.
- **Time-walk and charge dependence.** Signal amplitude affects the measured time in
  most discriminator schemes; the correction depends on deposited charge, which for
  nuclei scales as `Z^2`. A TOF calibrated on singly-charged particles is not
  automatically valid for heavier ones.
- **TOF also measures direction of travel.** The sign of the time difference between
  planes distinguishes downward- from upward-going particles, which is the primary
  rejection against albedo and backward-going background in non-collider geometries.

### Ionization energy loss (dE/dx)

Every charged particle traversing material loses energy by ionization, at a mean rate
described by the Bethe-Bloch formula. The rate depends on `beta` (falling steeply at
low `beta`, reaching a minimum near `beta*gamma ~ 3-4`, then rising logarithmically in
the relativistic rise before saturating at the Fermi plateau) and on the square of the
particle's charge, `Z^2`.

That `Z^2` dependence makes any ionization measurement primarily a **charge**
measurement, and it is usually the cleanest way to determine `|Z|` for nuclei -
silicon trackers and gas chambers both provide it, and requiring consistent charge
across many layers is a powerful rejection of interactions and of mis-associated hits.

As a *velocity* measurement dE/dx is harder, for a specific reason: the energy loss in
a thin layer is not Gaussian but **Landau-distributed**, with a long high-side tail
from rare large energy transfers. Consequently the *mean* of a few samples is a poor
estimator - it is dominated by the tail and has large variance. The standard remedy is
a **truncated mean**: discard the highest-loss fraction of samples (commonly the top
30-40%) and average the rest. This is why detectors with many samples (a TPC with
hundreds of measurements) achieve far better dE/dx resolution than a few silicon
layers, and why quoting "dE/dx resolution" without stating the number of samples and
the truncation fraction is meaningless.

The relativistic rise gives some separation power above the minimum-ionizing region,
but it is weak - a few percent difference in mean loss against a resolution of similar
size - so dE/dx alone rarely separates species cleanly at high momentum. Its real
strength is at low momentum, below the minimum, where the `1/beta^2` rise is steep, and
in charge determination at all momenta.

### Transition radiation detectors (TRD)

When a relativistic charged particle crosses a boundary between materials of different
dielectric constant, it emits transition radiation - X-ray photons whose *yield*
depends on the Lorentz factor `gamma`, not on velocity. This is the crucial
distinction: `beta` saturates at 1 and stops discriminating, while `gamma = E/m`
continues to grow, so a TRD keeps separating species long after TOF and dE/dx have
failed.

Because yield per interface is tiny, a TRD stacks many radiator foils or fibre layers
followed by an X-ray-absorbing gas chamber (typically xenon-based, for photoelectric
absorption at the relevant few-keV energies). The signal is a *statistical excess* of
high-energy deposits in some layers on top of ordinary ionization - not a distinct
signature in any single layer. That has two direct consequences:

- **Identification is inherently a likelihood problem across layers**, not a cut on one
  measurement. The standard estimators are a likelihood ratio built from per-layer
  amplitude distributions, or a count of layers exceeding a threshold. Either way the
  per-layer response distributions are the calibration, and they must be measured from
  data control samples, not taken from simulation alone.
- **Performance is quoted as a rejection factor at a fixed efficiency**, and it is
  strongly `gamma`-dependent. A TRD separates electrons from protons over the momentum
  band where their `gamma` values differ greatly (because of the ~1836 mass ratio) and
  loses power once the heavier species also becomes ultra-relativistic. State the
  momentum band, the working-point efficiency, and the rejection factor together - one
  without the others is uninterpretable.

Transition radiation is emitted at very small angles and its energy deposit is
superimposed on the particle's own ionization in the same chamber, so a TRD's
`gamma`-dependent signal and its dE/dx signal are *correlated*, not independent
measurements. Combining them as if independent overstates the separation.

### Ring-imaging Cherenkov detectors (RICH)

A charged particle traversing a radiator of refractive index `n` faster than light in
that medium emits Cherenkov radiation on a cone of half-angle

    cos(theta_c) = 1 / (n * beta)

Imaging the resulting ring measures `theta_c`, hence `beta`, directly and very
precisely. There is a hard **threshold**: emission requires `beta > 1/n`, so each
species has a threshold momentum below which it produces no ring at all. That
threshold is itself identification information - the *absence* of a ring above a
species' threshold excludes it - and using it requires knowing the detector's
efficiency for detecting a ring that should be there.

Key behaviors:

- **The angle saturates.** As `beta -> 1`, `theta_c` approaches its maximum
  `arccos(1/n)`, and species separation vanishes. The usable momentum range is bounded
  below by threshold and above by saturation, and the width of that window is set by
  `n`: a radiator close to `n = 1` (aerogel, or a gas) pushes the whole window to
  higher momentum. Experiments needing broad coverage use **multiple radiators** with
  different indices, and each has its own calibration and its own window.
- **Angular resolution improves with photon count.** The single-photon angular
  resolution is set by chromatic dispersion (index varies with photon energy), by pixel
  granularity, and by the emission-point uncertainty along the track; the per-track
  resolution improves as the square root of the number of detected photons. Photon
  yield is itself proportional to `sin^2(theta_c)`, so rings are dimmest exactly at
  threshold, where the angle is most sensitive to velocity - the two effects partially
  cancel and must be evaluated together, not separately.
- **Velocity precision translates to mass precision with the `gamma^2` amplification**
  above. A RICH achieving a `dbeta/beta` of order `1e-3` still loses isotope separation
  at high `gamma`, which is the limiting factor in isotope measurements.
- **Ring reconstruction is a pattern-recognition problem** with its own failure modes:
  overlapping rings from multiple tracks, rings from secondaries produced in the
  radiator, and background photons. Its efficiency and its misreconstruction rate are
  measured quantities, and both belong in the analysis's efficiency chain.

Because velocity precision is high, a RICH combined with rigidity gives mass precision
good enough to separate **isotopes** of the same element (which have identical charge
and nearly identical rigidity-vs-momentum behavior, differing only in mass). Isotope
separation is the most demanding PID application and is worth treating as its own
validation problem: the separation is a few percent in mass, so every systematic in
`beta`, in `R`, and in the charge assignment enters directly.

### Muon systems

Muons are identified largely by *survival*: they penetrate the calorimeters and any
additional absorber, so a track segment found beyond that material, matched to an
inner track, identifies a muon. This is not a velocity measurement and the
identification quality is set by the amount of absorber and by the matching criterion.

The dominant background is **punch-through** - hadrons, or their shower remnants, that
survive the absorber - plus **decay in flight** of pions and kaons producing genuine
muons that are not from the process of interest. Both are momentum-dependent and both
are estimated from data control samples rather than trusted from simulation.

### Combining measurements

Multiple PID systems are combined into a likelihood: for each species hypothesis,
evaluate the probability of the observed measurements (`beta` from TOF, `theta_c` from
RICH, per-layer amplitudes from the TRD, truncated-mean dE/dx, `E/p` and shower shape
from the calorimeters), multiply, and compare hypotheses. Several requirements are
easy to violate:

- **Do not sum chi-squares across correlated subsystems.** TRD amplitude and tracker
  dE/dx both measure ionization in the same particle's passage; TOF `beta` and the
  track fit share the path length. Treating correlated inputs as independent
  overstates separation, sometimes dramatically. Either use a joint distribution or
  drop the redundant input.
- **Each response distribution is a calibration.** The likelihood is only as good as
  the per-species response templates, which must be measured on data control samples
  selected *without* the variable being calibrated, or the selection biases the
  template.
- **Priors matter and must be stated.** A likelihood ratio becomes a probability only
  with a prior on species abundance, and in a sample where one species outnumbers
  another by orders of magnitude, a modest likelihood ratio does not establish the rare
  species. This is the same reasoning as background estimation in
  background estimation, and mis-identification should
  appear as an explicit background component in the likelihood, with its rate
  constrained by a measurement.
- **Quote efficiency and contamination together, differentially.** A PID working point
  is a point on a trade-off curve; a rejection factor without its accompanying
  efficiency, or either one integrated over momentum, hides the behavior in the region
  that usually matters most.

### Deliverables

- The PID systems used, the momentum band over which each is valid, and the threshold
  and saturation momenta where applicable.
- Mass resolution as a function of momentum, showing the `gamma^2` degradation, and the
  momentum at which the required species separation is lost.
- For TOF: timing resolution, flight path and its uncertainty, start-time source, and
  any charge-dependent time-walk correction.
- For dE/dx: number of samples, truncation fraction, and whether it is used for charge,
  for velocity, or both.
- For TRD: estimator (likelihood or threshold count), working-point efficiency, the
  rejection factor at that point, the momentum band, and how the per-layer response
  templates were calibrated.
- For RICH: radiator(s) and index, per-track angular resolution and photon yield,
  ring-finding efficiency and misreconstruction rate.
- The combination method, with an explicit statement of which inputs are correlated and
  how that correlation is handled.
- Efficiency and contamination for each working point, quoted differentially, with
  mis-identification entering the likelihood as a constrained background.

### Common misconceptions and failure modes

- **Gaussian `N_sigma` applied to non-Gaussian tails** or to few-photon distributions.
- **Separation power quoted instead of efficiency and rejection at a working point.**
- **Correlated detector likelihoods multiplied as independent**, double counting shared inputs such as the track momentum.
- **TOF used beyond its momentum ceiling**, or `dE/dx` used without saturation and density-effect handling.
- **Momentum dependence ignored.** Every PID method's separation and background change with momentum.

## Chapter 10: Cherenkov Imaging Variants and Photosensors

Fills the gaps around the RICH/TRD/`dE/dx`/TOF treatment in
[Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems): threshold and differential counters, DIRC and
time-of-propagation (TOP) detectors, water/ice/aerogel/gas/liquid radiators, and the
optical and radiation sensors and light-transport elements shared by most detectors
(PMT, SiPM, APD, hybrid photodetectors, microchannel plates, gaseous photon detectors,
wavelength shifters, fibers, light guides). Physics of emission and yield is in
[Chapter 3](#chapter-3-signal-formation-transport-and-readout); `cherenkov_angle.py` evaluates the
RICH design relations.

### Cherenkov PID variants

**Threshold counters.** A particle emits light only if `beta > 1/n`, i.e.
`p > p_th = m c/sqrt(n^2 - 1)`. Using two radiators (or gas pressure) sets thresholds
that separate species by which counter fires. The **turn-on curve** `epsilon(p)` rises
over a range set by photon statistics (few photoelectrons) rather than a step; the
efficiency near threshold is `1 - exp(-N_pe(p))` (Poisson; approximate for a smooth
`N_pe`). Systematics: pressure/temperature/index stability (`n` shifts move the
threshold), mirror/window aging, noise (dark counts) versus low `N_pe`.

**Differential counters.** Select a Cherenkov angle (`cos theta_C = 1/(n beta)`) with
an optical system so that only a narrow velocity band gives light; excellent for a
particular momentum, with the acceptance and alignment of the angular selection
dominating the systematic.

**DIRC (detection of internally reflected Cherenkov light).** Light is trapped by
total internal reflection in a solid radiator bar and carried to a photosensor array
at the end: the ring is imaged after propagation as a pattern of hit positions,
requiring a reconstruction of the angle from position and (in TOP) **time of
propagation**. **TOP** detectors add the photon arrival time, breaking degeneracies
in the path. Distinctive features: **multiple photon paths** with the same detected
position (left/right bounces, mirror-image "ambiguities") that overlap in the
image, correction for **chromatic dispersion** through timing, and the need to calibrate
the bar's optical quality, surface reflectivity, and the photosensor's timing. PID by a
**timing-position likelihood** per hypothesis.

**RICH** (imaging in a gas or aerogel radiator with mirror or proximity focusing): ring
finding, track-photon association, likelihood PID; contributions to the per-photon
angle resolution: emission-point (radiator thickness), chromatic (dispersion `dn/d lambda`),
optical aberration, pixelization, and (per track) division by `sqrt(N_pe)`
([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)). Background hits from other tracks, delta rays,
and noise enter the likelihood as a flat term. **Radiators**: aerogel (intermediate
`n`, Rayleigh scattering), gas (low `n`, high threshold, high `beta`), liquid, water,
and ice (large volumes, optics dominated by absorption/scattering, e.g.
neutrino astronomy).

#### Distinctive but generalizable reconstruction and performance features (Cherenkov imaging)

- **Topology**: rings, arcs, or time-resolved photon patterns (a dense image with few
  photons: Poisson limited).
- **Inverse problem**: velocity `beta` (and species, given `p`) from a partial
  ring; degeneracies: photon-path ambiguity (DIRC/TOP), emission-point vs chromatic
  vs aberration, background photons.
- **Objects**: photon hit, ring/arc, track-level angle, likelihood per hypothesis.
  **Informative residual**: photon Cherenkov-angle residual versus track (per-photon
  distribution centered and its width, with the background pedestal), and the
  per-track angle residual versus momentum.
- **Scaling**: `sigma_track = sigma_photon/sqrt(N_pe)`; species separation
  `N_sigma = Delta theta_C / sigma_theta ≈ |m_1^2 - m_2^2| / (2 p^2 tan theta_C sigma_theta)`
  (approximate: ultrarelativistic, `beta ≈ 1`) falls as `1/p^2`
  ([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)); the angle saturates as `beta -> 1`.
- **Conventions**: efficiency/mis-ID at a stated likelihood-difference cut; separation
  power in `N_sigma` (Gaussian approximation, check with the actual distribution).
- **Tails**: wrong-ring association, low-`N_pe` tracks, background-dominated events.
- **Dependence**: refractive index (temperature/pressure/composition/dose), aerogel
  transparency, mirror alignment, photosensor gain/timing/aging, occupancy.
- **Data sample**: decays with kinematic PID (`D^* -> D pi`, `K_s -> pi pi`,
  `Lambda -> p pi`, `phi -> K K`), and `mu` from `Z`/`J/psi`.
- **Transfers**: photon-counting likelihood to any counting/imaging device; index/pressure
  monitoring to threshold counters; **does not transfer**: the specific dispersion terms.

### Photosensors and light transport

| Sensor | Gain/mechanism | Strengths | Characteristic systematics |
|---|---|---|---|
| Photomultiplier tube (PMT) | dynode chain, gain `10^5-10^7` | low noise, large area, fast | gain drift, afterpulses, magnetic-field sensitivity, transit-time spread, single-photoelectron (SPE) response |
| Silicon photomultiplier (SiPM) | Geiger-mode pixel array | compact, magnetic-field tolerant, photon counting | dark counts (temperature, dose), optical crosstalk, afterpulse, saturation (finite pixels) |
| Avalanche photodiode (APD) | linear avalanche in silicon | high `QE`, compact | gain/temperature sensitivity, excess noise |
| Hybrid photodetector | photocathode + silicon anode | good SPE resolution | high-voltage requirements |
| Microchannel plate (MCP) | channel electron multiplier | very fast, position sensitive | aging, ion feedback, rate/gain droop |
| Gaseous photon detector | photoionization + gas gain | large area, magnetic-field tolerant | quantum efficiency (window/gas), aging, ion backflow |

**Response model.** `N_pe ~ Poisson(N_gamma * eps_coll * QE)`; gain per photoelectron
fluctuates (Polya/excess-noise `F`); SiPMs add crosstalk and afterpulsing as
compound-Poisson terms; a dark count rate `DCR` contributes an offset `DCR * gate`;
timing has transit-time spread and jitter ([Chapter 8](#chapter-8-timing-detectors-and-time-measurement)).

**Light transport elements.**
- **Wavelength shifters** absorb short-wavelength (e.g. UV) light and re-emit at longer
  wavelength (a second stochastic step, with trapping efficiency and self-absorption);
  spectra of emitter, shifter, and sensor `QE` must overlap.
- **Fibers and light guides** transport light with attenuation
  `exp(-L/lambda_att)` and geometric (Liouville/etendue) limits: coupling area and
  acceptance angle cap the collected fraction; **optical coupling** (grease, gaps) sets
  an interface efficiency, a source of channel-to-channel nonuniformity.
- **Reflectors and coatings** age; reflectivity changes with humidity, radiation, and
  time.

**Calibration.** Single-photoelectron peak (gain, pedestal, noise threshold), LED/laser
pulsing (linearity, timing, monitoring of gain drift), radioactive sources and cosmic
muons (light yield, uniformity), and in-situ standard candles (electron/muon light
yield in detector volume) ([Chapter 5](#chapter-5-calibration-and-alignment)). Track *monitoring
time series* (gain versus temperature/dose) rather than a single constant.

#### Features (photosensors)

- **Topology**: pulses per channel (counts, time, amplitude), possibly a waveform.
- **Inverse problem**: `N_gamma`, arrival time from a pulse with gain and noise
  fluctuations and detection efficiency; degeneracy: gain vs light yield vs coupling.
- **Informative residual**: SPE spectrum, gain and DCR vs time, LED-linearity curve,
  light-yield vs position.
- **Scaling**: `sigma/N ≈ sqrt(F/N_pe)`; timing `~ 1/sqrt(N_pe)`.
- **Tails**: afterpulses, crosstalk clusters, dark-count pileup, saturation.
- **Dependence**: temperature (SiPM), magnetic field (PMT), dose, rate.
- **Data sample**: LED/laser, SPE, MIPs, mono-energetic lines.
- **Transfers**: to every light-based detector (calorimeters, TOF, RICH, neutrino).

### Common misconceptions and failure modes

- **Using the Gaussian `N_sigma` for PID with few photons.** Distributions are
  Poisson-non-Gaussian; use the likelihood or ROC ([Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)).
- **Neglecting `n(T, P, lambda)`.** Small index drift shifts angles and thresholds.
- **DIRC/TOP ambiguities ignored.** Multiple photon paths produce a structured
  background if not modeled in the likelihood.
- **SiPM dark counts and crosstalk treated as Gaussian noise.** They are correlated and
  non-Gaussian; model as compound Poisson.
- **Ignoring dose-dependent aging** of scintillators, WLS fibers, and mirrors.
- **Assuming the gain is constant across an SPE calibration** interval.

### Deliverables

- The radiator/sensor response model and the per-track/per-photon resolution
  decomposition.
- Threshold turn-on or ring-angle likelihood with the background model.
- SPE, gain, dark count, crosstalk, and afterpulse calibration and monitoring plan.
- The optical calibration (attenuation, coupling, reflectivity) and its time dependence.

## Chapter 11: Calorimetry: Electromagnetic and Hadronic

Covers destructive energy measurement - how showers develop, what sets the resolution,
why hadronic calorimetry is fundamentally harder than electromagnetic, and how
calorimeter information feeds particle identification. Assumes the material-budget and
resolution vocabulary of [Chapter 4](#chapter-4-detector-systems-overview);
jet energy scale and its calibration are treated at the object level in
jet, b-tagging, and missing-momentum reconstruction,
and the calibration machinery itself in
[Chapter 5](#chapter-5-calibration-and-alignment).

### The measurement, and why it complements tracking

A calorimeter absorbs a particle and measures the energy deposited. Its defining
property is that relative resolution *improves* with energy, roughly as `1/sqrt(E)`,
because the measurement is a count of shower constituents subject to Poisson
fluctuations. This is exactly opposite to a magnetic spectrometer, whose relative
resolution degrades with rigidity. The two are therefore complementary: tracking wins
at low momentum, calorimetry wins at high energy, and the crossover is a basic design
parameter of any experiment that has both. A calorimeter also measures neutral
particles, which leave no track at all.

### Electromagnetic showers

A high-energy electron or photon initiates a cascade: bremsstrahlung and pair
production alternate, roughly doubling the number of particles every radiation length
`X0`, while the average energy per particle halves. The cascade stops multiplying at
the **critical energy**, below which ionization loss overtakes radiative loss, and the
remaining particles are absorbed.

Two consequences matter for design and for analysis. Shower *depth* grows only
logarithmically with energy - measured in `X0`, the depth of shower maximum scales as
`ln(E)` - so a calorimeter deep enough for a given energy remains adequate over a wide
range, and depth requirements are modest. Shower *width* is set by the Molière radius,
which is a material property largely independent of energy, so lateral containment is
essentially an energy-independent geometric requirement. Because the Molière radius
sets the transverse scale, granularity finer than it buys shower-shape discrimination,
not better energy resolution.

Longitudinal and lateral shower shape are the basis of calorimeter-level particle
identification. Electromagnetic showers are compact, start early, and deposit a
characteristic longitudinal profile; hadronic showers are deeper, broader, and more
irregular. Discriminants built from the depth of shower maximum, the fraction of
energy in the first layers, and the lateral spread separate electrons and photons from
hadrons with rejection factors that can be large but are strongly
energy-dependent - and are exactly the kind of variable that a classifier will exploit
and that must therefore be validated for data/MC agreement before use, following
multivariate analysis.

### Homogeneous versus sampling calorimeters

A **homogeneous** calorimeter is built entirely of active material, so in principle
every shower particle contributes to the signal; the stochastic term can be very small.
A **sampling** calorimeter interleaves dense passive absorber with thinner active
layers and measures only the fraction of the shower crossing the active material. The
sampling fraction introduces an additional, dominant Poisson fluctuation - the
**sampling term** - which is the price paid for compactness, cost, and the ability to
build a deep hadronic section.

The practical distinction for analysis is that a sampling calorimeter's energy scale
depends on the sampling fraction, which is *not* the same for electromagnetic and
hadronic showers. That difference is the origin of the non-compensation problem below.

### The resolution decomposition

Calorimeter energy resolution is conventionally parameterized as three terms added in
quadrature:

    (sigma_E / E)^2 = a^2 / E + b^2 / E^2 + c^2

- **`a`, the stochastic (sampling) term** - Poisson fluctuations in the number of
  detected shower constituents. Dominates at low energy.
- **`b`, the noise term** - electronic noise and, at a collider, pileup energy inside
  the reconstruction cone. It enters as a fixed energy uncertainty, so its *relative*
  contribution falls as `1/E`. It is the term that grows when pileup increases, and
  the reason optimal cluster size is pileup-dependent.
- **`c`, the constant term** - calibration non-uniformity, channel-to-channel
  intercalibration error, and energy leakage. It does not improve with energy and
  therefore *sets the ultimate high-energy performance*. A calorimeter's high-energy
  precision is a calibration achievement, not a detector-technology achievement.

The most common analysis error here is quoting a stochastic term alone and
extrapolating it to high energy, which predicts an arbitrarily good resolution that
the constant term forbids. `calorimeter_resolution.py` fits all three terms
from measured points and reports which one dominates at a given energy and where the
crossovers lie; note that the parameterization is *linear* in `(a^2, b^2, c^2)` over
the basis `{1/E, 1/E^2, 1}`, so the fit is an exact linear least squares with no
minimizer and no starting values required.

Fitting fewer than three distinct energies cannot separate three terms, and fitting
over a narrow energy range gives strongly correlated parameters even when it converges:
quote the covariance, or at least the range fitted, alongside the values.

### Hadronic showers and non-compensation

A hadronic shower develops through nuclear interactions over the interaction length
`lambda_I`, which is much larger than `X0` in dense absorbers - so hadronic
calorimeters are far deeper than electromagnetic ones, and shower fluctuations are
much larger.

The dominant complication is that a hadronic shower contains a variable
**electromagnetic fraction**, mostly from neutral pions decaying to photons, which
develop as electromagnetic sub-showers. That fraction fluctuates event to event and
rises with energy. Meanwhile, part of the purely hadronic energy is *invisible* - spent
on nuclear binding energy, slow neutrons, and nuclear fragments - and is not detected.

If the calorimeter's response to the electromagnetic component differs from its
response to the hadronic component (the ratio conventionally written `e/h` differs from
1, the **non-compensating** case, which is the usual case), then the measured energy
depends on the fluctuating electromagnetic fraction. This produces three effects
simultaneously, and they are often confused:

- **Degraded resolution**, because the electromagnetic fraction fluctuates.
- **Non-linearity**, because the mean electromagnetic fraction rises with energy, so
  the response is not a constant times the true energy.
- **Non-Gaussian response**, with tails that a Gaussian resolution parameterization
  understates.

Compensation can be approached by hardware design or recovered offline by weighting
techniques that estimate the electromagnetic fraction from the shower's measured
density and correct each deposit accordingly. Either way, the hadronic energy scale is
a *derived, calibrated* quantity with its own substantial uncertainty, and it is
routinely one of the leading systematics in any analysis using jets or missing
transverse momentum - which is why jet energy scale and resolution get their own
variation treatment in
systematic-uncertainty implementation.

### Leakage, dead material, and containment

Energy that escapes the calorimeter is not measured. **Longitudinal leakage** (punch
through the back) produces a low-side tail that grows with energy and is the practical
limit on how far a calorimeter's calibration can be extrapolated. **Lateral leakage**
outside the reconstruction cluster is a clustering choice, and trades against the noise
and pileup term - a larger cluster recovers energy but collects more noise. **Dead
material** upstream or between compartments absorbs energy invisibly and must be
corrected using the observed energy sharing between compartments.

All three are energy-dependent and direction-dependent, so a single global correction
is inadequate; corrections are normally parameterized in energy and pseudorapidity or
polar angle, and their residual uncertainty flows into the constant term.

### Calorimeter-based identification

Beyond shower shape, the ratio of calorimeter energy to track momentum, `E/p`, is a
powerful identifier: it is near 1 for electrons (which deposit all their energy
electromagnetically and have a measured track) and much smaller for hadrons, which
deposit only part of their energy in the electromagnetic section. `E/p` is also the
standard in-situ handle for cross-calibrating the calorimeter energy scale against the
tracker momentum scale - a check that is only as good as the tracker's own alignment,
so a disagreement in `E/p` is not automatically a calorimeter problem. See
[Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems) for how this combines with
the other identification systems.

### Deliverables

- Calorimeter type (homogeneous or sampling), absorber and active material, depth in
  `X0` and `lambda_I`, and transverse granularity relative to the Molière radius.
- Resolution quoted as all three terms with the energy range over which they were
  fitted and their correlations, not a stochastic term alone.
- For hadronic measurements: whether the calorimeter is compensating, what offline
  weighting is applied, and the resulting non-linearity and its uncertainty.
- Leakage and dead-material corrections applied, with their energy and angular
  dependence.
- Shower-shape or `E/p` discriminants used for identification, with data/MC agreement
  demonstrated in a control region before they are relied on.

### Common misconceptions and failure modes

- **The stochastic term treated as universal** across energies and detectors; noise and constant terms dominate at the extremes.
- **`e/h = 1` assumed**, or single-hadron calibration assumed to equal jet calibration.
- **Leakage and dead material ignored**, then absorbed into the constant term.
- **Noise thresholds that bias low-energy clusters** upward or clip them.
- **Scale, linearity, uniformity, resolution, tails, and category migration conflated.**

## Chapter 12: Muon Systems: Spectrometers, Identification, and Trigger

Muon detection and reconstruction: drift-tube, cathode-strip, RPC-, GEM-, and
Micromegas-based chambers; standalone, combined, segment-tagged, calorimeter-tagged, and
trigger-level muons. The PID summary is in [Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems);
technology physics is in [Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies);
alignment weak modes in [Chapter 5](#chapter-5-calibration-and-alignment) and
[Chapter 6](#chapter-6-tracking-and-vertexing).

### Why muons are special

Muons are minimum-ionizing, do not shower strongly, and traverse the calorimeters, so
the outermost layers see them nearly free of other particles. A muon system therefore
does two jobs: identification (it is the layer that survives absorbers) and an
independent momentum measurement at large lever arm, often in its own field.

### Reconstruction chain

1. **Chamber hits** (drift time -> radius; strip/pad charge centroid; RPC strip time).
2. **Segments**: line fit per chamber station (direction and position), resolving
   left-right ambiguity and rejecting delta-ray and noise hits.
3. **Standalone track**: link segments across stations through the spectrometer field,
   fit with material (multiple scattering, energy loss in absorbers).
4. **Extrapolation and matching** to the inner tracker: propagate the tracker track
   through calorimeter material (energy loss, scattering) to the muon system; match by
   position/direction with the extrapolated covariance (a `chi^2` match, not a fixed
   cut only).
5. **Combined fit**: refit hits from both systems; the inner tracker dominates at low
   `p`, the muon system's long lever arm at high `p`. Resolution scales as (approximate)
   `sigma_pT/pT ≈ a pT (measurement) ⊕ b (multiple scattering)`
   ([Chapter 6](#chapter-6-tracking-and-vertexing)).
6. **Trigger matching**: the hardware-level (coarse) muon candidate matched to the
   offline muon for the trigger efficiency (trigger, luminosity, and pileup methodology).

**Muon types (definitions differ by community; state the one used).**
*Standalone*: muon-system track only. *Combined/global*: tracker + muon-system fit.
*Segment-tagged*: tracker track that extrapolates to at least one muon segment (recovers
low-momentum muons that do not reach far). *Calorimeter-tagged*: tracker track with
minimum-ionizing calorimeter deposit (recovers acceptance gaps). *Trigger-level*: coarse
online track. Each type has its own efficiency, purity, and momentum resolution.

### Performance and scaling

- **Resolution**: at low `p`, multiple scattering in absorbers and calorimeters
  (energy-loss fluctuation before the muon system) dominates; at high `p`, spatial
  resolution and alignment of the muon stations limits the *sagitta*
  `s ≈ L^2 B q/(8 p)`-like measurement (approximate, uniform field: momentum error
  `∝ p^2 sigma_s`). High-momentum resolution is a **weak-mode/alignment** problem
  (see below).
- **Efficiency**: geometric gaps (cracks, support structures, feet), chamber
  inefficiency, matching and reconstruction inefficiency, quoted **per type and versus
  `eta`, `phi`, `pT`**, with a tag-and-probe from `J/psi` and `Z -> mu mu`
  (trigger, luminosity, and pileup methodology).
- **Rate capability**: drift tubes (long drift, space-charge and occupancy limits),
  cathode-strip chambers (high granularity, good for high rate), RPCs (fast, rate
  limited by resistivity), GEM/Micromegas (high rate, discharge risk)
  ([Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies)).
- **Charge sign**: from curvature direction; at high momentum the sagitta shrinks
  toward the alignment/resolution floor and **charge misidentification** grows
  (`~ Gaussian tail of sagitta/sigma`); a weak-mode misalignment gives a *momentum-charge
  correlated bias*: `q/p` shifts charge-dependently, mimicking a charge asymmetry.

### Backgrounds and fakes

- **Punch-through**: hadrons that leak through calorimeter absorbers; falls with
  absorber thickness, rises with hadron energy.
- **Decay in flight**: `pi/K -> mu nu` inside the tracker: a kinked track whose
  combined-fit `chi^2` is bad and whose tracker-muon momentum mismatch is large.
- **Accidental matches**: an unrelated segment (cavern background, noise) matched to a
  tracker track; grows with rate.
- **Cosmic rays and beam halo**: out-of-time or off-vertex muons; suppress with timing,
  vertex/impact parameter, and back-to-back topology.
- **Hadron mis-identification vs reconstruction fake**: a pion identified as a muon
  (mis-ID, real object with wrong identity) is a different failure from a fake track
  ([Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)).

### Distinctive but generalizable reconstruction and performance features (muon system)

- **Topology**: sparse hits grouped into segments over a large lever arm; almost no
  other particles (clean but low redundancy).
- **Inverse problem**: momentum and charge from sagitta in a field with material
  between stations; degeneracy: alignment weak modes (curl, sagitta, twist, radial)
  that leave `chi^2` nearly unchanged but shift `q/p` charge-dependently.
- **Objects**: segment, standalone, combined, tagged muon. **Informative
  residual/closure**: `Z -> mu mu` mass versus `eta`, `phi`, `pT`, and charge
  (`m` and `q/p` residual versus `q * eta`), plus cosmic-ray track splitting
  (upper/lower half fits) to expose sagitta bias.
- **Scaling**: `sigma_pT/pT ∝ pT` at high `p` (measurement-dominated), constant at low
  `p` (scattering); charge misID rises steeply with `pT`.
- **Conventions**: efficiency measured with tag-and-probe at fixed working point and
  isolation; resolution from `Z` line-shape width or MC truth for the momentum range,
  charge misID from same-sign fraction in `Z -> mu mu`.
- **Tails**: wrong-segment link, decay-in-flight, delta-ray overlap, charge flip.
- **Dependence**: rate/occupancy (background hits), magnetic field map stability,
  chamber temperature/gas, alignment time-dependence.
- **Strongest data sample**: `Z -> mu mu` and `J/psi -> mu mu` (mass scale and
  resolution in bins), cosmic muons (split tracks), and collision tracks for
  alignment with external constraints.
- **Transfers**: sagitta-weak-mode and charge-dependent-bias reasoning to any
  spectrometer ([Chapter 6](#chapter-6-tracking-and-vertexing)); **does not transfer**: the
  specific punch-through/absorber background model.

### Common misconceptions and failure modes

- **One "muon efficiency."** Reconstruction, identification, isolation, and trigger
  efficiencies differ, and each is conditional on the previous
  ([Chapter 17](#chapter-17-performance-metrics-acceptanceefficiencyresolution-and-residual-diagnostics)).
- **Trusting `chi^2` for alignment.** Weak modes leave the fit quality unchanged; check
  `q/p` versus `q*eta` and mass versus `eta`, `phi`.
- **Same-sign fraction read as charge flip only.** Backgrounds also contribute; correct
  for them before quoting charge misID.
- **Identical efficiency applied to all muon types.** A segment-tagged muon is not a
  combined muon.
- **Ignoring decay in flight for hadron-mimic estimates.** Depends on the track's
  position in the tracker.

### Deliverables

- The muon-type definitions, with efficiency, purity, resolution, and charge misID per type.
- Tag-and-probe (or equivalent) efficiency with binomial uncertainties, and the trigger
  matching definition.
- The high-`pT` alignment/field validation (mass and `q/p` versus `q*eta`, cosmic split).
- The background model for punch-through, decay-in-flight, accidental, cosmic.

## Chapter 13: Noble-Liquid, Neutrino, and Rare-Event Detectors

Liquid-argon and liquid-xenon TPCs, dual-phase detectors, large water Cherenkov and
liquid-scintillator detectors, neutrino near/far systems, cryogenic bolometers,
semiconductor ionization detectors, dark-matter TPCs, and neutrinoless-double-beta-decay
detectors. Air-shower arrays, imaging Cherenkov telescopes, and neutrino telescopes
are treated in extensive air showers-the AMS-02 case study and
neutrino astronomy; this file integrates them into the common framework
([Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain)). Signal formation (recombination,
lifetime, quenching) is in [Chapter 3](#chapter-3-signal-formation-transport-and-readout).

### Noble-liquid TPCs

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

#### Distinctive but generalizable reconstruction and performance features (noble-liquid TPC)

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
- **Transfers**: drift-and-readout reasoning ([Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies));
  **does not transfer**: gas-TPC diffusion/ion-backflow values.

### Neutrino detectors

**Topologies and energy.** Wire-based or pixel LArTPCs, segmented scintillator, and
water/scintillator volumes reconstruct the final-state lepton and hadrons. Two energy
estimators exist and differ: **calorimetric** (sum of visible energy plus corrections)
and **kinematic** (from lepton angle/energy assuming an interaction type). Neither is
the neutrino energy without a model of **nuclear effects** (Fermi motion, final-state
interactions, missing energy carried by neutrons/undetected particles), so the
`E_reco -> E_nu` migration is model-dependent
(measurements and unfolding).

**Containment.** Events leaking out of the fiducial volume lose energy
(distribution-dependent bias). Containment is defined in simulation and validated with
control samples (through-going/stopping muons).

**Near/far extrapolation.** Cancel common systematics by measuring a near-detector
flux/cross-section constraint and extrapolating: valid only if the *same interaction
model and acceptance mapping* applies and the detector differences are modeled
(different sizes, technologies, angle acceptance). The *uncorrelated* part of the
detector systematics between near and far does not cancel. Common failure: assuming
cancellation where the two detectors' response or phase-space coverage differ.

#### Features (neutrino detectors)

- **Topology**: images (LArTPC), rings/timing (water), light patterns (scintillator).
- **Inverse problem**: neutrino energy/flavor from partial visible final state;
  degeneracy: missing-energy and cross-section model.
- **Informative closure**: mono-energetic Michel electrons, stopping muons, `pi^0` mass,
  and near-detector data.
- **Tails**: containment, secondary interactions, cosmic pileup.
- **Transfers**: model-dependence framing to any inclusive measurement
  (measurements and unfolding).

### Water Cherenkov and liquid-scintillator detectors

**Water Cherenkov.** Ring imaging of Cherenkov light by photomultipliers
([Chapter 10](#chapter-10-cherenkov-imaging-variants-and-photosensors)); reconstruct vertex,
direction, energy from **charge/time likelihoods** (per PMT, expected charge and time
given hypothesis `x`, `p(y|x,theta)` ([Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain)));
**ring counting** and electron/muon separation from ring sharpness (sharp muon ring vs
fuzzy shower ring). Systematics: optical absorption and scattering in the medium,
PMT gain/timing calibration, reflection, and light-attenuation time dependence.
**Liquid scintillator.** Much higher light yield (better energy resolution, low
threshold), isotropic light so weaker directional information, quenching for heavy
particles, and scintillator/optical aging.

### Rare-event detectors

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
- **Blind analysis**: masked signal regions (analysis design and blinding).

#### Distinctive but generalizable reconstruction and performance features (rare-event)

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

### Astroparticle systems within the same framework

- **Air-shower surface/fluorescence/radio arrays**: sparse distributed sampling; the
  inverse problem is shower axis/core/direction/energy from a partial sample of the
  shower footprint, with **atmospheric monitoring** as a first-class nuisance
  parameter (`theta`) (ground-based detection arrays). Effective area and
  exposure play the role of acceptance ([Chapter 4](#chapter-4-detector-systems-overview)).
- **Imaging atmospheric Cherenkov telescopes**: image cleaning, Hillas parameters,
  gamma/hadron separation, PSF, and effective area (imaging atmospheric Cherenkov telescopes).
- **Neutrino telescopes in water/ice**: sparse timing geometry, track vs cascade
  hypotheses, angular resolution, **effective volume**, and medium optics (scattering
  and absorption) as dominant `theta` (neutrino astronomy).
- **Space-based direct detection**: spectrometer and calorimeter combination, geomagnetic
  cutoff and solar modulation (space-based direct detection,
  the AMS-02 case study).

### Common misconceptions and failure modes

- **Summing charge and light without recombination.** Anticorrelation means the two
  channels must be combined, not treated as independent.
- **Applying electron-equivalent energy to nuclear recoils.** Quenching/yield differs.
- **Assuming near/far cancellation.** Detector differences and phase-space coverage break it.
- **Fiducial cut uncertainty ignored.** Position resolution and wall leakage map directly
  onto exposure and background.
- **Extrapolating discrimination leakage below calibrated energies.**
- **Kinematic energy quoted as neutrino energy** without the nuclear-effect model.

### Deliverables

- The two (or more) signal channels, the combination rule, and the recombination/lifetime
  correction with its uncertainty.
- The energy scale (electron-equivalent vs nuclear recoil) and its calibration source.
- Threshold efficiency, fiducial volume, and their uncertainties.
- Discrimination leakage versus energy with its calibration sample.
- For neutrino work: containment, the energy-estimator definition, and the near/far
  cancellation assumption.

## Chapter 14: Event Reconstruction

Covers the chain that turns raw detector signals into the physics objects an analysis
consumes: hits, clusters, tracks, vertices, identified particles, and event-level
quantities. The subsystem physics feeding this chain is in
[Chapter 6](#chapter-6-tracking-and-vertexing),
[Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic), and
[Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems); the object-level corrections
applied afterwards are in
jet, b-tagging, and missing-momentum reconstruction,
and how to measure whether reconstruction worked is in
[Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching).

### The chain, and why its order matters

Reconstruction proceeds roughly as: raw readout -> calibrated digits -> hits ->
clusters and track candidates -> fitted tracks -> vertices -> identified particles ->
composite objects (jets, missing transverse momentum) -> event-level selection
quantities.

Each stage consumes the previous stage's output *and its uncertainty*, and each stage
makes decisions that later stages cannot undo. A hit dropped by a threshold cut is not
recoverable by a better track fit; a track that failed pattern recognition is invisible
to vertexing; energy assigned to the wrong cluster is missing from the right one. This
one-directional information loss is why reconstruction is normally re-run rather than
patched, and why a change in an early stage requires revalidating everything
downstream rather than only the stage that changed.

The practical corollary for analysis: reconstruction-level systematic variations must
be applied at the stage where the effect physically occurs and propagated forward.
Applying a "tracking efficiency" uncertainty as a flat event weight is wrong whenever
the missing track would have changed jet clustering, isolation, or missing transverse
momentum - the same requirement stated as an analysis invariant for kinematic
variations.

### Digitization boundary and calibration

The first stage converts readout values into physical quantities using calibration
constants: pedestals, gains, channel-by-channel intercalibration, timing offsets, and
dead or noisy channel maps. Everything downstream inherits these, and their versioning
is part of the analysis's reproducibility record - see
[Chapter 5](#chapter-5-calibration-and-alignment).

Two failure modes recur. **Dead and noisy channel maps must match between data and
simulation**, or simulated events see a detector that does not exist; when the masks
are time-dependent, the simulation must reproduce the time-averaged mask weighted by
the luminosity actually collected. And **zero suppression and thresholds discard
information irreversibly** at the readout, so a signal below threshold is not merely
noisy, it is absent - which produces an efficiency turn-on that must be modeled rather
than assumed flat.

### Clustering

Calorimeter clustering groups deposits into objects. The two standard approaches are
fixed-geometry windows (simple, stable under pileup, but poorly matched to showers
that spread irregularly) and topological growth from seeds above a
noise-scaled threshold (better containment, but with a cluster size and hence a noise
and pileup contribution that varies event by event).

The seed threshold and the growth threshold are the two parameters that matter most.
Raising them suppresses noise and pileup at the cost of low-energy efficiency and of
truncating shower tails; lowering them recovers energy but couples the measurement to
pileup. Because the optimum depends on the pileup level, a clustering configuration
tuned for one running condition is not automatically valid for another - and
comparisons across data-taking periods must confirm that the clustering behaved the
same way, not just that the calibration was applied.

**Cluster splitting** - deciding whether one broad deposit is one particle or two
nearby ones - is where nearby-particle resolution is set, and it fails in a
characteristic way: two nearby particles merged into one cluster produce an object with
roughly the summed energy and an intermediate position, which is not obviously wrong in
any single-object distribution but distorts multiplicity and isolation.

### Track-cluster association and particle-flow reconstruction

When both a tracker and calorimeters cover the same solid angle, the same particle is
measured twice, and combining the two measurements well is worth a great deal:
the tracker is more precise at low momentum, the calorimeter at high energy, and the
calorimeter additionally sees neutrals.

**Particle-flow-style reconstruction** attempts to identify every individual particle
in the event by linking tracks to clusters, then choosing the best measurement for
each: charged particles take their momentum from the track, and the calorimeter energy
they deposited is *subtracted* so that the remainder can be attributed to neutrals.
This gives substantially better jet and missing-momentum resolution than using
calorimeter energy alone, at the price of a much stronger dependence on the quality of
the link.

The failure modes follow directly from the subtraction:

- **Over-subtraction.** If a charged particle's calorimeter deposit is estimated too
  large, real neutral energy is erased. This biases the neutral component low and is
  hard to see in the charged distributions where the problem originates.
- **Under-subtraction.** Residual charged energy is misinterpreted as a fake neutral,
  inflating both multiplicity and energy.
- **Double counting.** A track wrongly linked to a cluster produced by a different
  particle counts one particle twice and loses the other.
- **Sensitivity to tracking efficiency.** Because a missing track means its energy is
  attributed to a neutral (measured with worse calorimeter resolution rather than lost
  entirely), tracking inefficiency degrades resolution and shifts scale in a way that
  depends on the calorimeter response - so tracking and calorimeter systematics are
  *correlated* in a particle-flow analysis and must not be varied independently.

### Ambiguity resolution across the event

Reconstruction produces overlapping interpretations that must be reduced to a
consistent event: duplicate tracks from the same particle, a photon candidate that is
also part of a jet, an electron whose track is also a jet constituent. Resolving these
is not a detail - it determines what "number of objects" means, and inconsistent
resolution between data and simulation produces multiplicities that do not agree for
reasons unrelated to physics.

Overlap removal (which object wins when two definitions claim the same energy) is
specified at the analysis level and is covered in
jet, b-tagging, and missing-momentum reconstruction;
what matters here is that the reconstruction-level and analysis-level removals must be
consistent with each other, and that the ordering of removal steps changes the result.

### Timing and event association

Where the detector has adequate timing, associating deposits and tracks by arrival time
suppresses out-of-time contributions - pileup from adjacent bunch crossings, cavern or
albedo background, and cosmic-ray tracks. Timing association is an efficiency-versus-
purity trade like any other, with the added subtlety that a timing window is only as
good as the time calibration and the assumed time-of-flight to the measurement point
- which depends on the assumed particle velocity, and therefore on the species
hypothesis.

### Reconstruction under pileup

When multiple interactions overlap, reconstruction must assign objects to a primary
vertex and estimate the diffuse energy from the rest. Standard components are vertex
selection (which vertex is the interesting one - a choice with its own efficiency and
its own mis-assignment rate), charged-hadron subtraction using track-to-vertex
association, and an event-by-event estimate of the pileup energy density used to
correct object energies.

Two points are easy to get wrong. Pileup mitigation is a *correction with an
uncertainty*, not a clean removal, and its residual must appear as a systematic. And
because the pileup distribution differs between data and simulation, the reweighting of
trigger, luminosity, and pileup methodology must be
applied consistently with the mitigation - reweighting to a data pileup profile while
reconstructing with a mitigation tuned for a different profile leaves a residual that
neither step catches.

### Reproducibility of the reconstruction

Reconstruction output depends on software version, calibration and alignment payloads,
geometry description, and configuration. All four belong in the analysis record; a
"same" sample reprocessed with a different payload is a different sample, and mixing
processings within one measurement is a defect unless explicitly justified and
validated. Multithreaded reconstruction can also introduce ordering-dependent results
where algorithms are not order-invariant - check that a rerun reproduces the same
output before attributing a difference to anything physical.

### Deliverables

- The reconstruction chain used, with software version, geometry, and calibration/
  alignment payload versions recorded.
- Clustering algorithm and thresholds, and confirmation that they are consistent across
  the data-taking periods being combined.
- Whether particle-flow-style combination is used and, if so, an explicit statement
  that tracking and calorimeter systematics are treated as correlated.
- Ambiguity and overlap-removal steps in the order applied, consistent between
  reconstruction and analysis levels.
- Timing association windows, if used, with the assumed time-of-flight hypothesis.
- Pileup mitigation method, its residual uncertainty, and its consistency with the
  pileup reweighting applied to simulation.
- Confirmation that a rerun reproduces the same output (no ordering or threading
  dependence).

### Common misconceptions and failure modes

- **Reconstruction order treated as arbitrary.** Each step's output is the next step's input, so a change propagates downstream.
- **Particle-flow double counting**: the same energy attributed to a track and to a calorimeter cluster.
- **Pileup modeled as extra noise only.** It also creates fake objects and merges real ones.
- **Clustering output taken as truth.** Split and merged clusters are reconstruction outcomes with their own rates.
- **Different reconstruction versions or conditions used for data and simulation.**

## Chapter 15: Detector Simulation

Covers propagating generated particles through a model of the apparatus and producing
simulated readout: geometry and materials, physics processes, digitization, fast
simulation, and - most importantly for an analysis - how to establish that the
simulated response matches the real detector. The upstream stage is
event generation; the constants that tie simulation to the
real detector are in [Chapter 5](#chapter-5-calibration-and-alignment).

### What full simulation does

A full simulation (Geant4 being the standard toolkit) transports each particle through
a geometry description in small steps, at each step sampling the physics processes that
may occur - ionization, bremsstrahlung, pair production, multiple scattering, nuclear
interaction, decay - and recording energy deposits in volumes designated as sensitive.
The output is a set of true energy deposits with positions and times, which is *not
yet* detector output; converting those into readout values is digitization, below.

The three inputs that determine whether the result is trustworthy are the geometry, the
physics list, and the production cuts.

### Geometry and materials

The geometry description must include everything that interacts, not just the active
sensors: support structures, cables, cooling, electronics, and the material between
subsystems. **Passive material is where simulation geometries are most often wrong**,
because it is not what anyone is trying to measure and is frequently simplified into
averaged "lumped" volumes.

A mismodeled material budget produces a characteristic pattern of symptoms, and
recognizing it saves a great deal of debugging: data-simulation disagreement that
varies with polar angle (because path length through material does), a mismatch in
photon conversion or nuclear-interaction rates, tracking efficiency that disagrees at
low momentum but agrees at high, and calorimeter response that disagrees in a way no
energy-scale factor fixes uniformly.

The strongest data-driven handles on material are the reconstructed conversion and
nuclear-interaction vertex maps, which image the material distribution directly (see
[Chapter 6](#chapter-6-tracking-and-vertexing)), and the momentum dependence of
tracking efficiency. Material uncertainty is normally propagated by producing a
simulation variant with the budget scaled in specific regions - it cannot be
represented as a weight.

### Physics lists and their validity

A physics list is a bundled choice of models and cross sections for each process and
energy range. Different lists differ most in hadronic interactions, where models are
phenomenological and are stitched together across energy ranges, with the transitions
between models being a known source of discontinuity.

Practical requirements:

- **State the physics list and version.** It is as much a part of the sample definition
  as the generator, and results are not comparable across lists without checking.
- **Confirm the list is validated for the relevant energy range and particle types.**
  A list validated for GeV-scale collider physics is not automatically appropriate for
  low-energy nuclear recoils, for heavy ions, or for very high energy cosmic-ray
  primaries.
- **Hadronic shower modeling is a real uncertainty**, not a fixed truth, and where a
  measurement depends on it (hadronic calorimeter response, punch-through, secondary
  production), an alternative list is the honest way to estimate it.

### Production cuts and stepping

Full simulation is expensive, and cost is controlled by **production cuts** - a
threshold, usually expressed as a range rather than an energy, below which secondary
particles are not produced and their energy is deposited locally instead. This is an
approximation with a physics consequence: too coarse a cut removes the low-energy
secondaries that carry the signal in a thin detector, distorting deposits in exactly
the sensitive volumes that matter. Cuts must be set per region, tighter in sensitive
volumes than in bulk absorber, and the choice validated by confirming the observable of
interest is stable against tightening them.

**Step limits** matter similarly in thin sensitive volumes and in strong field
gradients, where too long a step misplaces the deposit or mistracks the trajectory.

### Digitization

Digitization converts true energy deposits into simulated readout, and it is where the
simulation stops being physics and starts being an electronics model. It must
reproduce: charge collection and sharing between channels, the response function and
its saturation, electronic noise with its real correlations, discriminator thresholds
and zero suppression, time structure including any integration window that admits
out-of-time signals, and the dead/noisy channel map for the period being simulated.

Digitization is the most common place for a data-simulation mismatch that no
calibration fixes, because it is the stage most often simplified. Specific things worth
checking explicitly:

- **Noise is not white and not uncorrelated.** Common-mode noise across a readout group
  behaves very differently from independent per-channel noise, especially after
  clustering, and a simulation with independent Gaussian noise will produce cluster
  size and occupancy distributions that do not match.
- **Thresholds and zero suppression must match the data exactly**, including any
  time-dependence; a simulation with the wrong threshold has a different efficiency
  turn-on that will be misattributed to physics.
- **Pileup overlay** must reproduce the data's pileup distribution and its
  out-of-time structure, consistently with the reweighting applied later - see
  trigger, luminosity, and pileup methodology and
  the pileup discussion in [Chapter 14](#chapter-14-event-reconstruction).
- **Simulated events must be reconstructed with the same code and configuration as
  data.** Any divergence between the two reconstruction paths becomes a systematic
  that is invisible in every internal cross-check.

### Fast and parametrized simulation

Full simulation of calorimeter showers dominates the cost, so fast alternatives
replace shower transport with a parametrized response - a library of pre-simulated
showers, an analytic parameterization, or a learned generative model. Fast simulation is
legitimate and often necessary, but its validity is conditional:

- It is valid **only where it was validated**. A parameterization tuned on single
  particles at fixed energies may not describe overlapping showers, unusual
  topologies, or the tails that drive a specific selection.
- **Tails are the first thing lost.** A parameterization matching the core response can
  badly misrepresent the tail, which is exactly what matters for fake missing momentum
  and for background estimates.
- **Correlations are the second.** Longitudinal-lateral shower correlations, and
  correlations between nearby particles, are frequently not preserved, which affects
  shower-shape discriminants and isolation.
- The difference between fast and full simulation, evaluated on the analysis's own
  observables, is the natural systematic - and if that difference is large, the fast
  sample is not a substitute for the analysis in question, however good its agreement
  in inclusive distributions.

### Validating the simulation

Simulation is a model to be tested, not a reference to be trusted. A useful validation
ladder:

1. **Geometry and material** - total budget and its distribution against the
   engineering description; conversion and interaction vertex maps against data.
2. **Single-particle response** - energy scale, resolution, and shower shapes against
   test-beam data where available, and against in-situ resonances or `E/p` in data.
3. **Occupancy and noise** - hit multiplicity, cluster size, and noise distributions,
   which test digitization directly and are sensitive to problems that energy-level
   comparisons miss.
4. **Reconstruction-level distributions** in a control region orthogonal to the signal
   selection, where any disagreement can be characterized without unblinding.
5. **Efficiency and resolution** against their data-driven measurements, with the
   residual difference becoming the scale factor and its uncertainty - see
   [Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching).

**Do not tune simulation parameters to remove a disagreement in the observable the
analysis measures.** Tuning is legitimate on independent control observables with a
physical justification stated, and the tuned parameter's remaining freedom becomes a
systematic. Tuning against the measurement itself destroys the measurement, for the
same reason that tuning a fit to obtain a desired significance does.

### Deliverables

- Simulation toolkit and version, geometry version, physics list and version, and
  production cuts per region, all recorded alongside the sample.
- Material budget comparison against the engineering description and against a
  data-driven material probe.
- Digitization model details: noise model and its correlations, thresholds and zero
  suppression, integration window, dead/noisy channel map and its time dependence.
- Pileup overlay configuration and its consistency with the pileup reweighting applied
  downstream.
- Confirmation that simulation and data are reconstructed with identical code and
  configuration.
- If fast simulation is used: what it was validated against, the observables where it
  was checked, and the full-versus-fast difference quoted as a systematic.
- Validation evidence at each rung of the ladder above, with disagreements quantified
  rather than tuned away, and any tuning justified physically on independent
  observables.

### Common misconceptions and failure modes

- **The simulation treated as truth about the detector.** It is a model with validated ranges.
- **Tuning the simulation on the measured observable.**
- **Physics-list validity ranges ignored**, especially for hadronic showers.
- **Fast simulation used outside the phase space where it was validated.**
- **Digitization, noise, and pileup overlay not matched to data conditions.**

## Chapter 16: Reconstruction Performance and Truth Matching

Covers how to measure whether reconstruction worked: efficiency, fake rate, purity,
resolution, and bias - all of which rest on a **truth-matching criterion** that must be
stated explicitly, because changing it changes every number. Complements the
statistical treatment of efficiencies in
histogram and efficiency statistics, the
data-driven efficiency measurement in
trigger, luminosity, and pileup methodology, and
the response-matrix formalism in
measurements and unfolding.

### Truth matching is a definition, not a measurement

Every performance number requires deciding which reconstructed object corresponds to
which generated particle. There is no unique answer, and the common criteria give
different results:

- **Geometric matching** - nearest object within an angular window. Simple, but
  degrades in dense environments and depends on a window size that is effectively a
  free parameter.
- **Hit-level or constituent-level matching** - the reconstructed object shares more
  than some fraction of its hits or energy with one generated particle. More robust,
  and the fraction is again a chosen threshold.
- **Best-match with uniqueness enforced** - each generated particle matches at most one
  reconstructed object and vice versa, resolving ties by a stated ranking.

The choices that matter and must be reported are the matching observable, the
threshold, whether matching is one-to-one or many-to-one, and how ties and duplicates
are resolved. Two analyses quoting "tracking efficiency" with different criteria are
not quoting the same quantity, and a change in criterion during an analysis silently
changes the correction applied to the data.

Enforcing uniqueness matters more than it appears. Without it, one generated particle
reconstructed as two objects counts as efficient *and* contributes no fake, hiding a
duplication problem entirely.

### Efficiency, fake rate, and purity

These three are computed over different denominators, and mixing them up is a common
error:

- **Efficiency** = matched reconstructed objects / generated particles in the
  fiducial region. Denominator is *generated*.
- **Fake (or ghost) rate** = unmatched reconstructed objects / all reconstructed
  objects. Denominator is *reconstructed*.
- **Purity** = matched reconstructed objects / all reconstructed objects. The
  complement of the fake rate over the same denominator.
- **Duplicate rate** = reconstructed objects beyond the first matched to the same
  generated particle / generated particles.

State the fiducial region defining "should have been reconstructed". An efficiency
quoted without it is not interpretable, because it silently includes or excludes
particles outside acceptance, and acceptance is a geometric property that should be
separated from efficiency - see
[Chapter 4](#chapter-4-detector-systems-overview).

Efficiency is a ratio of counts and its uncertainty is **binomial**, not a Gaussian
propagation of numerator and denominator - `tag_and_probe_efficiency.py`
computes the exact Clopper-Pearson interval, and it applies here exactly as it does for
trigger efficiencies. When the events are weighted, the effective-sample-size
correction matters and a naive binomial interval on weighted counts understates the
uncertainty.

Quote all of these **differentially** in the variables they depend on - momentum,
direction, local density or pileup - not integrated. An integrated efficiency is a
weighted average over the simulated input spectrum, so it carries that spectrum's model
dependence and does not transfer to a different sample.

### Simulation-derived versus data-derived performance

Efficiency measured in simulation is exact by construction (truth is known) but only
as good as the simulation. Efficiency measured in data has no truth, so it uses a
data-driven proxy - tag-and-probe, or the fraction of an independently-identified
sample that is reconstructed.

The standard practice is to measure the efficiency in both, take the **scale factor**
(data over simulation) as the correction applied to simulation, and take its
uncertainty from the measurement plus the closure of the method. The scale factor
approach is robust because many effects cancel in the ratio, but it cancels them only
where the data and simulation measurements are done identically - same selection, same
binning, same background subtraction. It also transfers only where the probe sample
resembles the analysis sample; a scale factor measured on isolated probes does not
automatically apply inside a dense jet.

### Resolution and bias from reco-versus-truth

With matching defined, resolution is the width and bias the mean of the residual
distribution - either absolute (`reco - true`) or relative (`(reco - true)/true`) - at
fixed true value. Points that routinely cause trouble:

- **Bin in truth, not in reconstructed.** Binning residuals by the reconstructed value
  and then quoting a bias produces a spurious result from regression to the mean:
  upward-fluctuated objects populate high reconstructed bins, so the residual appears
  biased high there even for a perfectly unbiased detector. Bin in the true value.
- **Do not summarize with a Gaussian fit alone.** Detector response has tails, and a
  core-Gaussian sigma understates the probability of large mismeasurement - which is
  exactly what matters for charge confusion (see
  [Chapter 6](#chapter-6-tracking-and-vertexing)), for jet energy tails feeding fake missing
  momentum, and for background estimates. Quote a robust width (an interquantile
  range) and the tail fraction alongside any Gaussian core.
- **Resolution is not a scalar.** It varies with the same variables efficiency does,
  and quoting it integrated hides the regions that dominate the systematic.
- **A steeply falling spectrum turns resolution into a bias.** With a falling true
  spectrum, more objects migrate up than down at any given reconstructed value, so a
  symmetric resolution produces an asymmetric net migration. This is a migration
  effect to be handled by unfolding or forward folding, not by a resolution correction.

### From performance to correction

Reconstruction performance enters the measurement in one of two ways, and they must
not be mixed:

- **Correct the data** - divide by efficiency and unfold the resolution to obtain a
  particle-level result. This requires the response matrix and its regularization, and
  makes the result comparable to theory directly. Follow
  measurements and unfolding.
- **Fold the prediction** - apply efficiency and resolution to the simulated
  prediction and compare at detector level. Statistically cleaner (no unfolding
  regularization, no ill-conditioned inversion), but the result is
  detector-specific.

Whichever is chosen, the same performance inputs must be used consistently across
signal, background, and control regions, and their uncertainties treated as correlated
where they share a common source - see
systematic-uncertainty implementation.

### Validating performance itself

Performance numbers deserve the same scrutiny as physics results:

- **Closure test.** Apply the derived correction back to an independent simulated
  sample and confirm it recovers the truth within uncertainty. A non-closure is a
  systematic that must be quoted, not tuned away.
- **Independent samples.** Derive corrections and validate them on statistically
  independent samples; deriving and validating on the same events understates the
  uncertainty.
- **Check the denominators.** Most efficiency bugs are denominator bugs: particles
  outside the fiducial region, particles from the wrong production vertex, or
  double-counted generated particles.
- **Check for a matching-criterion dependence.** Recompute the key number with a
  tighter and a looser matching threshold; a strong dependence means the number is
  reporting the criterion as much as the detector.

### Deliverables

- The truth-matching criterion in full: observable, threshold, one-to-one or
  many-to-one, tie-breaking rule.
- The fiducial region defining the efficiency denominator, stated separately from
  acceptance.
- Efficiency, fake rate, purity, and duplicate rate, quoted differentially with
  binomial (not Gaussian) uncertainties, and with the weighted-count treatment stated
  if events are weighted.
- Scale factors with the data and simulation measurements done identically, plus the
  range of validity relative to the analysis sample.
- Resolution and bias binned in the *true* variable, with a robust width and a tail
  fraction, not a Gaussian core alone.
- Whether the analysis corrects the data or folds the prediction, applied consistently
  across all regions.
- A closure test on an independent sample, with any non-closure quoted as a systematic.
- A matching-criterion sensitivity check on the headline performance number.

### Common misconceptions and failure modes

- **Truth matching treated as a measurement.** It is a criterion, and results depend on it.
- **Unstated denominators**, especially particles outside the fiducial region or from the wrong vertex.
- **Scale factors applied outside the range where they were measured.**
- **Resolution binned in the reconstructed variable**, which sculpts the distribution.
- **No matching-criterion sensitivity check** on the headline number.

## Chapter 17: Performance Metrics, Acceptance/Efficiency/Resolution, and Residual Diagnostics

Rigorous definitions for every quantity quoted in a detector-performance result, and
the residual/pull toolkit that tests whether a model and its uncertainties are right.
It sharpens [Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching) (truth matching,
efficiency, fake rate) and [Chapter 4](#chapter-4-detector-systems-overview) (resolution vocabulary)
and supplies the statistics of histogram and efficiency statistics. Every metric below
requires: an equation, numerator, denominator, conditioning, matching rule, phase space,
object or event level, estimator, and uncertainty. If one is missing, the number is not
comparable.

### Metric definitions

| Metric | Definition (numerator / denominator) | Condition, matching | Estimator, uncertainty | Common misuse |
|---|---|---|---|---|
| Geometric/kinematic acceptance `A` | truth in fiducial geometry and phase space / generated in the reference phase space | truth only; no detector response | ratio of counts or integral of a flux over geometry ([Chapter 4](#chapter-4-detector-systems-overview)) | using it as "efficiency"; changing the reference phase space between MC and data |
| Reconstructibility | truth objects that leave the minimum information needed (e.g. `>= n` hits) / truth in acceptance | truth-level definition of "could be found" | count ratio | denominator differs between experiments |
| Hit efficiency | hit found where expected / tracks crossing active area (from other layers) | unbiased track prediction (excluding the layer) | binomial (Clopper-Pearson) | biasing by requiring the hit in the track fit |
| Reconstruction efficiency `eps_R` | reconstructed and matched / eligible truth (in acceptance) | matching criterion stated | binomial | denominator not the fiducial one |
| ID / selection efficiency `eps_S` | pass / reconstructed (matched) objects | stated matching and phase space | binomial | applying a probe-derived value to a different population |
| Trigger efficiency | fired / offline-selected sample | independent reference trigger | binomial per bin (turn-on) | biased reference sample |
| Purity `P` | matched true / selected | selected sample; matching rule | binomial or ratio of weighted counts | quoted as `1 - fake` when other categories exist |
| Fake rate | selected objects with no truth match / selected (object-level) *or* / eligible candidates (per-candidate) | say which | ratio | confusing with mis-ID |
| Mis-ID rate `m_{a->b}` | true species `a` identified as `b` / eligible true `a` | truth species; all categories | binomial | confusing with fake; mixing denominators |
| Duplicate rate | truth matched by `>= 2` objects / matched truth | one-to-many rule | ratio | not removed by ambiguity resolution |
| Response / scale | `<x_reco/x_true>` (or median) at fixed truth | binned in *truth*, not reco | mean/median, `+-` standard error | binning in reco (selection bias) |
| Bias | `<x_reco - x_true>` | as above | as above | mixing bias with core width |
| Resolution | width of `x_reco - x_true` (or `/x_true`, or `1/pT` form) | binned in truth; state definition | core Gaussian `sigma`, `RMS`, robust `1.4826*MAD`, `sigma_68`; `+-` statistical | quoting RMS of a heavy-tailed shape |
| Tail / catastrophic fraction | `|r| > k*sigma_core` / population | `k` and definition stated | binomial | not reported next to core width |
| PID efficiency & rejection | `epsilon_sig`, `1/epsilon_bkg` at a working point | truth species, phase space | binomial; ROC/AUC | quoting rejection without the signal efficiency |
| Separation `N_sigma` | `|mu_1-mu_2| / sqrt(sigma_1^2+sigma_2^2)` | Gaussian shapes (approximate) | from fits | applied to non-Gaussian tails ([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)) |
| Confusion matrix | `M_{ab} = P(ID=b | true=a)` rows normalized by truth | eligible truth per row | counts | wrong normalization axis |
| Effective area / volume, exposure, containment, PSF | `A_eff = A_gen N_pass/N_gen`, `exposure = A_eff * T_live * Omega` | as defined for astroparticle | ratio/MC | quoting without energy/angle dependence (space-based direct detection, astroparticle statistics) |

Object-level versus event-level: a per-object probability `p` with `k` independent
objects per event gives an event-level probability `1 - (1-p)^k` for "at least one";
they are not interchangeable, and correlations (shared pileup, shared alignment)
break independence, so measure the event-level quantity directly.

**Why fake rate is not universally `1 - P`.** `P = N_matched/N_selected`, so
`1 - P` = (unmatched + matched-but-wrong-identity) / selected. A *fake* is a selected
object with no valid truth counterpart (reconstruction failure); a *mis-ID* is a real
particle with the wrong species. `1-P` mixes both plus duplicates. Also fake rate is
often defined per eligible candidate, not per selected object, so its denominator
differs.

**Efficiency uncertainty.** Binomial, not Gaussian near 0 or 1: use exact
Clopper-Pearson or Wilson/Bayesian intervals (`tag_and_probe_efficiency.py`).
With weighted events, use effective counts `N_eff = (sum w)^2 / sum w^2`, and note
correlated numerator/denominator when the pass sample is a subset. Rate-like counts
without a denominator (dark counts, backgrounds) are Poisson.

### Acceptance, efficiency, resolution: the dedicated distinction

- **Acceptance** asks only whether *truth* lies in measurable geometry and phase
  space. **Efficiency** is *conditional* success in triggering, reconstruction,
  identification, or selection. **Resolution** is the *estimator* distribution for an
  explicitly conditioned population. **Bias/scale** is the *central offset*, not spread.
- **Selection sculpts resolution.** A cut on the reconstructed variable (or on a variable
  correlated with the error) removes one side of the residual distribution: it improves
  apparent resolution and creates a conditional bias. Bin efficiency and resolution in
  *truth* and state the selection.
- **Chain rule and its validity.** The identity
  `P(S) = P(A) P(R|A) P(S|R,A)` is *exact* (chain rule) when each factor is conditioned
  on all previous steps *for the same population and with consistent denominators*. The
  naive product `P(A) * eps_R * eps_S` with each factor measured separately is valid only
  if each factor is independent of the earlier steps (conditional independence).
  It fails when (i) denominators differ (e.g. `eps_S` measured on probes that are
  already isolated and reconstructed), (ii) factors depend on common variables
  (pileup, `pT`, `eta`) so the population-averaged product differs from the product of
  averages (`<a b> != <a><b>`), or (iii) an efficiency was measured in a control
  sample with different kinematics. Fix: factorize *differentially* in the shared
  variables (and multiply per bin), or measure the total directly.

#### Worked numerical example

Illustrative counts (a synthetic toy, not a detector result). `N_gen = 10000` generated
single-electron-like particles.

| Step | Population | Count | Quantity |
|---|---|---|---|
| Generated | all | 10000 | |
| In fiducial (truth) | truth in acceptance | 8000 | `A = 8000/10000 = 0.800` |
| Reconstructed (matched) | of the 8000 | 7200 | `eps_R = 7200/8000 = 0.900` (conditional on `A`) |
| Pass ID | of the 7200 | 6480 | `eps_S = 6480/7200 = 0.900` (conditional on `R, A`) |
| Total (of fiducial) | | | `eps_tot|A = 6480/8000 = 0.810 = eps_R * eps_S` |
| Total (of generated) | | | `A * eps_tot|A = 6480/10000 = 0.648 = 0.8*0.9*0.9` |

Uncertainty on `eps_S` (large `N`, `p` not near 0 or 1, so binomial ≈ Gaussian):
`sqrt(0.9*0.1/7200) = 0.0035`.

Selected sample: 6600 objects pass the ID cut, composed of 6420 true electrons (matched
with correct identity), 60 real pions (matched, wrong species: *mis-ID*), and 120 with
no truth match (*fakes*): `6420 + 60 + 120 = 6600`.
- Purity (correct identity) `P = 6420/6600 = 0.973`.
- Fake rate `= 120/6600 = 0.0182`; mis-ID share `= 60/6600 = 0.0091`. Here
  `1 - P = 0.0273` = fake + mis-ID, *not* the fake rate alone.
- The pion mis-ID *rate* as a property of pions needs the eligible pion count as the
  denominator (e.g. 60 of 12000 pions = 0.005), a different number from `0.0091`.

Resolution/bias of a relative energy residual `r = (E_reco - E_true)/E_true` (%) for
20 matched electrons in one truth bin: values
`-1.2, 0.5, 0.1, -0.4, 1.1, 0.3, -0.2, 0.8, -0.6, 0.4, -0.9, 0.2, 0.0, -0.3, 0.7, 6.5,
-0.5, 0.6, -0.1, 0.9`.
- Mean `= 0.395%`, sample RMS `= 1.56%`, median `= 0.15%`,
  `1.4826*MAD = 0.74%`.
- One catastrophic entry (`6.5%`): tail fraction `|r| > 3% = 1/20 = 5%`.
- Removing it: mean `0.074%`, RMS `0.63%`. The mean and RMS were dominated by a single
  tail event; the core (`~0.6-0.7%`, bias `~0.1%`) is the detector; the 5% tail is a
  separate quantity. Quote `bias(core)`, `sigma(core)`, and tail fraction, never one
  number. (With 20 entries all of these have large statistical uncertainty; a real
  performance table needs far more.)

### Residuals, pulls, and their covariance

```
r = x_meas - x_pred        p = r / sigma_r        chi^2 = r^T V_r^{-1} r
```

`x_meas` the measurement, `x_pred` the prediction from a model/fit (in the
measurement's units); `V_r` the covariance of `r`, **not** of the measurement alone:
`V_r = V_meas + V_pred - C - C^T` where `C` is the measurement-prediction covariance.

- **Biased residual**: prediction from a fit that *includes* the hit. It is
  anticorrelated with the measurement, so `V_r = V_meas - V_pred` (narrower than
  `sigma_meas`), and pulls built with `sigma_meas` are too small.
- **Unbiased (exclusive) residual**: prediction from a fit that excludes the hit:
  `V_r = V_meas + V_pred'` (wider). It is uncorrelated with the measurement to first
  order and is the correct quantity for measuring intrinsic resolution and efficiency.
- **Leave-one-out**: repeat over hits to make the unbiased residual for each.
- **Pull mean 0, width 1** only if: the model is correct, the estimator is unbiased, the
  residual uncertainty uses the correct covariance (including `C`), errors are Gaussian,
  and the population is not selected on the residual. A pull width `> 1` means
  under-estimated uncertainty, missing correlations, or model mismatch; `< 1` means
  over-estimated errors or using a biased residual with `sigma_meas`.
- **`chi^2`**: with `n` degrees of freedom the expectation is `n` (Gaussian, correct
  covariance); distribution tails, not just the mean, diagnose outliers.

**Reading residual plots.** *Mean* versus a variable: bias/misalignment/calibration;
*width* versus a variable: resolution scaling or unmodeled term; *trends* (linear, sinusoidal in `phi`):
geometry deformation, field, time offset; *discontinuities*: module boundary, calibration
region edge, a step in conditions (interval of validity); *tails*: outliers, wrong
association, delta rays; *multimodality*: two populations (left-right ambiguity, wrong
bunch, two clusters). Cover, in each detector: hit-to-track (position), drift-time,
Cherenkov-angle, cluster-energy, shower-position, segment-match, waveform (fit
residual), optical (charge/time vs model), and timing residuals - see the technology
files ([Chapter 7](#chapter-7-gaseous-and-specialized-tracking-technologies),
[Chapter 8](#chapter-8-timing-detectors-and-time-measurement), [Chapter 12](#chapter-12-muon-systems-spectrometers-identification-and-trigger), [Chapter 10](#chapter-10-cherenkov-imaging-variants-and-photosensors)).

**Coverage.** A `k`-sigma interval should contain the truth at the nominal
probability (68.3% for `k=1`, Gaussian). Coverage is tested on *truth* in simulation or
with a redundant measurement in data. *Narrow residuals do not prove correct
pulls or coverage*: an estimator can be precise but overconfident (uncertainties too
small), or accurate on the core while its tails are ignored. Test the pull width, the
tail fraction, and coverage across phase space, not just the core width.

### Estimators and pitfalls

- **Core vs full width**: Gaussian core fit, `sigma_68`, robust `1.4826 MAD`, and RMS
  answer different questions; RMS is dominated by tails, core fit by the fit range.
- **Binning on reconstructed values** sculpts the distribution; bin in truth.
- **Weighted samples**: uncertainties via `sum w^2`; effective statistics.
- **Detector resolution vs unfolding regularization.** Detector resolution is a property
  of the measurement; regularization is a choice in the inversion that smooths the
  result and introduces bias; they are separate widths and must not be conflated
  (measurements and unfolding). The response matrix
  `n_i^reco = sum_j R_ij n_j^truth + b_i` encodes resolution (off-diagonal),
  inefficiency (column sums `< 1`), and background `b_i`; model dependence enters through
  the truth spectrum used to build `R` ([Chapter 18](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination)).

### Common misconceptions and failure modes

- **Efficiency, purity, and acceptance interchanged.** State each denominator.
- **Fake = `1 - purity`.** Only if everything else selected is a fake and nothing else
  is misidentified or duplicated.
- **Resolution quoted without selection, center, width, and tail.**
- **Pulls computed with the biased residual and measurement error.** Use the correct
  `V_r` or an unbiased residual.
- **A narrow residual assumed to imply correct coverage.**
- **Naive product of separately measured efficiencies.** Check conditional independence.
- **Object-level probability used as event-level.**
- **Resolution improved by a reco-level cut** (selection bias), then presented as the
  detector's resolution.

### Deliverables

- For every quoted metric: numerator, denominator, conditioning, matching rule, phase
  space, level (object/event), estimator, and uncertainty.
- Efficiency with exact binomial intervals; resolution as core, tail fraction, and
  definition; bias in truth bins.
- Pull mean and width with the covariance used; coverage on an independent sample.
- The factorization used and a check that it is valid (or the direct total measurement).

## Chapter 18: Data/MC Validation, Detector Systematics Propagation, and Detector Combination

The last arrows of the [Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain): data/MC
validation, systematic uncertainties, and the physics-observable bias; then combining
detectors. It applies the general machinery of systematic-uncertainty implementation (variations,
correlations), validation practice (validation), [Chapter 16](#chapter-16-reconstruction-performance-and-truth-matching)
(scale factors), [Chapter 15](#chapter-15-detector-simulation) (simulation chain) and
measurements and unfolding (response matrices) to detector effects specifically.

### The simulation chain and its four truth levels

Generation -> transport (Geant4) -> energy deposits -> digitization -> noise/pileup
overlay -> trigger -> reconstruction ([Chapter 15](#chapter-15-detector-simulation)). Four distinct
levels exist: *generator truth*, *simulation truth* (deposits, true trajectories),
*digitized signals*, *reconstructed objects*. Only the last two exist in data. Truth
matching, "true" efficiencies, and response definitions are simulation-only;
data-accessible proxies must stand in.

### Data/MC comparison: what to compare

Compare **normalization, shape, conditional distributions, correlations, efficiencies,
tails, and time dependence**. One-dimensional agreement is *never* sufficient: two
marginals can agree while the joint distribution (e.g. `pT` versus `eta`, hit
multiplicity versus occupancy) differs, and an agreeing marginal can hide compensating
errors. Compare in the variables that carry the physics: efficiency and resolution
**conditional on** kinematics, occupancy/pileup, and detector region; correlations between
two observables; the tails (log scale); and per-run/per-period stability. Prefer
validation in independent samples distinct from those used to tune the simulation.

### Control samples and data-driven methods

- **Control / validation / signal regions**: tune in control, check in validation,
  measure in signal; keep them disjoint (background estimation).
- **Closure**: apply the method to simulation where truth is known and recover the
  input within uncertainty; non-closure is a quoted systematic, not something to tune away.
- **Tag-and-probe**: a resonance (`Z`, `J/psi`, `K_s`, `Lambda`) supplies a *tag* with tight
  selection and an unbiased *probe*; efficiency = probes passing / probes, from a
  background-subtracted sample (sideband or fit); biases from tag-probe correlation and
  background shape (trigger, luminosity, and pileup methodology).
- **Standard candles and independent samples**: mono-energetic peaks (`pi^0`, `Z` line,
  Michel electrons, calibration lines), cosmic muons, redundancy of independent
  subdetectors (a tracker efficiency from the calorimeter or from an alternative
  tracking path), sidebands, and resampling (bootstrap, split-sample) for data-driven
  uncertainties.
- **Truth-matching proxies in data**: redundancy, kinematic constraints, and
  mass/opening-angle closure; state the proxy's own bias.

### Scale factors and reweighting

```
SF = eps_data / eps_MC
```

Both efficiencies must be measured **identically** (same tag-and-probe, same
background subtraction, same matching) and in the **phase space the analysis uses**.
Apply `SF` at the level where it was measured (per object, in the same binning
variables); a per-object `SF` applied per event needs the event-level combination
stated. Specify derivation, applicability range, bin correlations, smoothing, and
extrapolation uncertainty where the probe sample does not cover the analysis space.

**Uncertainty on `SF`**: propagate the statistical (binomial) uncertainties of both
efficiencies (`eps_data`, `eps_MC` are independent samples), the tag-probe/background
systematics of the data measurement, and finite-MC statistics.

**Reweighting risks.** Reweighting simulation to match a marginal (pileup, `pT`,
`eta`) can (i) leave a **hidden-variable mismatch** (the true cause is a different, correlated variable),
(ii) **damage correlations** among observables that were correct, (iii) **lose closure**
(a reweighted sample no longer reproduces truth-level relations), and (iv) cause
**double correction** (applying both a reweighting and a scale factor that already
absorbs the same effect). Prefer fixing the physics or the calibration when the
mismatch is in a *cause*, and reweight only in the variables the analysis is
sensitive to.

### Systematic uncertainties: sources and mapping

| Detector nuisance | Affects (reconstructed) | Propagates to (physics) | Typical model |
|---|---|---|---|
| Momentum/energy scale | `pT`, mass, `E` | resonance mass, cross section slope | shift + re-select; correlated |
| Resolution | widths, tails, migration | response matrix, mass width, cuts | smearing variation |
| Efficiency (reco/ID/trigger) | yields, acceptance | cross section normalization | `SF` up/down per bin |
| Alignment / field | `q/p` (charge-dependent), `d0`, angles | charge asymmetry, mass vs `eta` | alternative geometry (weak modes) |
| Material | conversions, scattering, showers | efficiency, `E` scale, isolation | material-variation simulation |
| Time / conditions drift | scale, timing, gain | time-dependent bias | run-period split |
| Noise / pileup | thresholds, clusters, `MET`, jets | jets, isolation | overlay variation (trigger, luminosity, and pileup methodology) |
| Dead channels / masks | efficiency holes | acceptance | conditions variation |
| Mis-ID / fakes | backgrounds | signal contamination | data-driven fake rate |
| Trigger | efficiency turn-on | normalization | turn-on curve variation |
| Response matrix / model | unfolded spectrum | shape | alternative model (see measurements and unfolding) |
| Background | subtractions | signal yield | template/normalization variation |

**Separate**: statistical, calibration, alignment, modeling, method, environmental, and
finite-simulation uncertainties, since they have different correlation models and
different ways to be reduced. A stochastic fluctuation (Landau) is *not* a systematic:
it averages with statistics; the residual error on a calibration constant *is*, and
does not.

**Propagation.** To first order (approximate): `V_f ≃ J V_x J^T`, `J_{ij} = ∂f_i/∂x_j`,
where `x` are the nuisance parameters (with covariance `V_x`) and `f` the final
observables (yields, mass, cross section). Limits of this linear propagation:
strongly nonlinear responses (threshold turn-ons, category migration), asymmetric
errors (use up/down variations, not a symmetric derivative), non-Gaussian priors, and
sample-size noise in the variation. Where invalid, use **toys** (draw `theta` from its
distribution, rerun) or **profiling/marginalization** in the fit
(likelihood fitting, statistical inference).

**Full chain for a detector nuisance.** Modify the condition or object -> **rerun the
affected reconstruction** (not just the final histogram) -> rerun object selection,
ordering, overlap removal, `MET`, and category assignment -> recompute the final
observable -> **validate the nuisance effect** on a control sample (does the change
move the control observable as data would?). Changing only a final weight is
insufficient for a kinematic variation (systematic-uncertainty implementation).

**Correlation model.** Distinguish *normalization vs shape*, *correlated vs uncorrelated*
(across bins, channels, periods), *symmetric vs asymmetric*, *local vs global*, and
*time-correlated* (a drifting gain is correlated in time; a per-run statistical constant is not). Decorrelating without a physical basis inflates the
combination's precision; over-correlating hides tension.

**Pitfalls.** Double counting the same effect in two nuisances (an `SF` uncertainty
that already contains the calibration uncertainty); arbitrary envelopes of unrelated
alternatives; noisy variations (finite MC) promoted to a shape effect; excessive
smoothing that removes a real feature; unjustified decorrelation.

### Detector combination and global reconstruction

Associations: track-cluster, track-muon, track-ring, timing-track, vertex-object
([Chapter 14](#chapter-14-event-reconstruction), [Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)).

- **Complementarity**: tracker is precise at low `p`, calorimeter at high `E`; muon
  system long lever arm; timing adds velocity; `dE/dx` adds species.
- **Optimal combination**: for independent unbiased estimates with variances
  `sigma_i^2`, the weighted mean `x = sum(x_i/sigma_i^2)/sum(1/sigma_i^2)`,
  `sigma^{-2} = sum sigma_i^{-2}` (exact for uncorrelated Gaussian); with a common
  covariance `V`, `x = (1^T V^{-1} x)/(1^T V^{-1} 1)` (BLUE), and a *large correlation
  can give a weight outside `[0,1]`* (negative weight, or a combination *worse than
  the best input* if correlations are underestimated).
- **Global PID / particle flow**: combine per-detector likelihoods
  (`L = prod L_d`) only if the detectors' responses are independent; shared inputs
  (the same track momentum, common alignment, common pileup) violate independence and
  overcount the information ([Chapter 9](#chapter-9-particle-identification-trd-tof-rich-dedx-and-muon-systems)).
- **Ambiguities**: shared hits/clusters assigned to two objects, overlap removal
  between overlapping objects, double counting of energy in particle flow,
  boundary effects at detector seams.
- **When an added detector helps or hurts.** It *improves resolution* when its error is
  independent and comparable; *improves efficiency* when it covers gaps; *improves
  purity* by rejecting fakes through redundancy; it *worsens* efficiency if it is
  required in the selection with an efficiency lower than the gain, *worsens* resolution
  if a biased or non-Gaussian input is weighted heavily, and *worsens* robustness by
  adding a new failure mode (dead region, calibration drift) into the combined object.

### Common misconceptions and failure modes

- **1D agreement as validation.** Check joint and conditional distributions and tails.
- **Scale factor used outside its measured range**, or at the wrong level (object vs event).
- **Reweighting a marginal** while the cause lies in a correlated variable.
- **Linear `J V J^T` with a threshold or migration.** Use variations/toys.
- **Systematic as noise.** A finite-MC fluctuation elevated to a shape uncertainty.
- **Unjustified decorrelation / envelope of unrelated models.**
- **Combining detectors with shared systematics as independent.** Double counts information.
- **Tuning the simulation on the measured observable**, then reading agreement as validation
  (circularity).

### Deliverables

- The simulation levels used for each corrected/validated quantity and the data proxy.
- For each `SF`: derivation, binning, correlations, range, extrapolation, uncertainty.
- The systematic table mapping nuisance -> reconstructed -> physics observable, with
  correlation model and validation of each variation.
- Whether linear propagation is valid, and the toy/profile alternative when not.
- The combination rule with the correlation matrix and a check against the best single input.

## Chapter 19: Detector-to-Physics-Bias Case Studies, Checklists, and Synthesis

Eight end-to-end cases across distinct detector families, then the practical checklists
and a one-page synthesis. All cases are generic *mechanism* studies: they name no
experiment and quote no performance number; any real instance needs the apparatus,
configuration, and source (see `detector-principles-bibliography.md`). Each follows the same eight steps:
(1) defect, (2) low-level effect, (3) reconstruction effect, (4) performance-plot
signature, (5) how data/MC or controls reveal it, (6) correction/model update,
(7) assigned systematic, (8) possible final physics bias. Framework:
[Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain); propagation:
[Chapter 18](#chapter-18-datamc-validation-detector-systematics-propagation-and-detector-combination).

### Case 1: Tracker weak mode (alignment) - charge-dependent momentum bias

1. **Defect**: a global deformation (e.g. a sagitta/"curl" mode) that leaves track
   `chi^2` nearly unchanged ([Chapter 6](#chapter-6-tracking-and-vertexing), [Chapter 5](#chapter-5-calibration-and-alignment)).
2. **Low level**: hit residuals show a small coherent trend versus `phi`/`z`, invisible
   per hit. 3. **Reconstruction**: `q/p` shifts by an amount proportional to `q * p`
   (charge-dependent), mostly at high `p`. 4. **Signature**: dimuon mass versus `q*eta`
   and `phi` shows opposite-sign shifts for `mu+` and `mu-`; cosmic-track split
   (upper/lower half) disagrees. 5. **Reveal**: resonance mass in `(q, eta, phi)` bins,
   split-track `Delta pT/pT`, `E/p` for electrons of each charge. 6. **Correction**:
   include the resonance mass and cosmic/track-split constraint in the alignment;
   external survey constraints. 7. **Systematic**: residual `q/p` curvature bias,
   correlated across `eta` with charge sign. 8. **Physics**: charge asymmetries and
   high-`pT` spectrum slopes (`W` charge asymmetry, high-mass `Z'` search) biased.

### Case 2: TPC space-charge distortion

1. **Defect**: positive-ion buildup (ion backflow, ionization at high rate) distorts `E`.
2. **Low level**: cluster positions displaced radially, dependent on `r`, `z`, and
   luminosity/rate. 3. **Reconstruction**: curved residual trends; momentum and `dE/dx`
   path errors; matching to outer detectors degrades. 4. **Signature**: cluster-to-track
   residuals versus `(r, z)` and versus instantaneous rate; track-matching residual to
   an external precision layer. 5. **Reveal**: matching map to a reference detector, laser
   or cosmic calibration, rate-dependent comparison. 6. **Correction**: time-dependent
   distortion map, rate-parameterized. 7. **Systematic**: map uncertainty
   (correlated over the rate/time range). 8. **Physics**: momentum scale/resolution and
   PID efficiency drift with beam intensity.

### Case 3: Drift-chamber `t0`/`r(t)` offset

1. **Defect**: a `t0` shift (e.g. clock/cable offset) or a wrong drift velocity.
2. **Low level**: measured drift times shifted by a constant/`E`-dependent amount.
3. **Reconstruction**: apparent radius error; left and right hits pull to opposite sides
   (a `t0` offset produces the same structure as a misalignment); segment `chi^2`
   rises. 4. **Signature**: residual versus drift distance with a left/right offset
   and slope. 5. **Reveal**: residual versus drift distance, per-run `t0` fit, per-layer
   comparison. 6. **Correction**: refit `t0`/`r(t)` per period, decouple from alignment
   by using their different dependence on the drift distance. 7. **Systematic**:
   `t0`/`v_d` residual (time-correlated). 8. **Physics**: coherent `pT` and impact
   parameter bias, muon efficiency loss.

### Case 4: ECAL dead material and nonlinearity

1. **Defect**: unmodeled upstream material and a nonlinear response (saturation or
   channel intercalibration error) ([Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic)).
2. **Low level**: energy lost before the calorimeter, shower starting earlier;
   channel gain errors. 3. **Reconstruction**: cluster energy scale wrong versus `eta`
   and energy; enhanced converted-photon and electron-bremsstrahlung tails. 4. **Signature**:
   `E/p` (electrons) and `pi^0`/`Z -> ee` mass versus `eta`, energy, and shower start.
5. **Reveal**: `Z -> ee` mass scale, `E/p`, `pi^0 -> gamma gamma`, comparison to
   simulation with varied material. 6. **Correction**: material-model update, layer
   weights, energy-dependent scale. 7. **Systematic**: scale with `eta`- and energy-dependent
   correlation; material variation. 8. **Physics**: shift of a resonance mass
   (e.g. `H -> gamma gamma`) and category migration.

### Case 5: HCAL non-compensation and jet-response bias

1. **Defect**: `e/h != 1`, invisible energy fluctuations, leakage ([Chapter 11](#chapter-11-calorimetry-electromagnetic-and-hadronic)).
2. **Low level**: single-hadron response depends on the electromagnetic fraction and
   energy. 3. **Reconstruction**: jet response depends on fragmentation (`pi^0` content)
   and flavor; non-Gaussian low tail. 4. **Signature**: response versus `pT`, `eta`,
   and flavor/constituent composition; low-side tail in `pT_reco/pT_true`. 5. **Reveal**:
   `gamma`+jet or dijet balance, single-hadron `E/p` in data, quark/gluon differences.
6. **Correction**: local hadronic calibration, software compensation, jet energy scale
   from data (jet, b-tagging, and missing-momentum reconstruction). 7. **Systematic**: flavor
   and composition JES components; single-particle calibration does not equal jet
   calibration. 8. **Physics**: jet-based mass and cross-section slopes; `MET` tails.

### Case 6: RICH refractive-index drift

1. **Defect**: index `n` changes with temperature/pressure/aerogel aging.
2. **Low level**: Cherenkov angle of a given `beta` shifts, photon yield changes.
3. **Reconstruction**: likelihood peaks displaced; species separation degrades; kaon-pion
   swaps in a momentum-dependent way. 4. **Signature**: photon-angle residual mean
   versus run/time, versus momentum; PID efficiency versus run. 5. **Reveal**:
   kinematically identified `K`/`pi`/`p` from `D^*`, `K_s`, `Lambda` versus run.
6. **Correction**: monitored `n(T, P)` per run; refit refractive index; re-derive PID
   calibration. 7. **Systematic**: PID efficiency/mis-ID by period, correlated in time.
8. **Physics**: particle-yield ratios (e.g. `K/pi`), heavy-flavor branching fractions.

### Case 7: TOF clock offset

1. **Defect**: a channel/fill-dependent clock offset or a start-time misassignment
   ([Chapter 8](#chapter-8-timing-detectors-and-time-measurement)). 2. **Low level**: times shifted for a subset of
   channels or a run. 3. **Reconstruction**: `beta`/`m^2` shifts; species bands move.
4. **Signature**: time residual for identified muons versus channel/run/`phi`; band
   center versus run. 5. **Reveal**: per-run residual, cross-check with a second start-time
   estimator. 6. **Correction**: per-run/per-channel `t0` and clock-transfer calibration.
7. **Systematic**: residual offset (time-correlated, partially channel-correlated).
8. **Physics**: mis-identified proton/kaon yields, isotope/anti-particle ratios.

### Case 8: Noble-liquid electron-lifetime drift

1. **Defect**: purity degradation (attachment), `tau_e` falls
   ([Chapter 13](#chapter-13-noble-liquid-neutrino-and-rare-event-detectors)). 2. **Low level**:
   charge signal `S2` (or wire charge) decays with drift time, more at large depth.
3. **Reconstruction**: `z`-dependent energy scale, worse resolution at large depth;
   discrimination leakage changes. 4. **Signature**: charge versus drift time (a
   decaying exponential) and the position dependence of a calibration line versus
   time. 5. **Reveal**: through-going/stopping tracks, calibration line versus
   depth per time bin. 6. **Correction**: time-dependent `tau_e` map applied per event,
   with position-dependent uniformity correction. 7. **Systematic**: `tau_e` uncertainty
   (time-correlated) and its propagation to the energy scale and discrimination.
8. **Physics**: energy scale, threshold efficiency, and hence a rare-event rate limit or
   an oscillation energy spectrum.

**Other cases (same template)**: optical attenuation drift in a light-based detector
(position-dependent light yield); timing-layer radiation damage (LGAD gain loss and
time-resolution degradation); atmospheric uncertainty in air-shower reconstruction
(energy scale and `X_max` bias from aerosol/molecular profile, ground-based detection arrays);
muon-station misalignment (Case 1's structure with a long lever arm, [Chapter 12](#chapter-12-muon-systems-spectrometers-identification-and-trigger)).

### Reusable checklist for any unfamiliar detector

1. Fill the fourteen questions ([Chapter 1](#chapter-1-detector-measurement-framework-forward-model-inverse-problem-and-the-chain)).
2. Name `x`, `y`, `theta`, `epsilon`; list irreducible fluctuations and correctable
   response variations.
3. Identify the direct observable and the latent inferred quantity; write the identifiability
   and the degeneracy.
4. Identify the natural local object, the global object, and the natural residual.
5. State the topology (sparse points, image, waveform, ring, shower, segment, time series,
   distributed array) and pick the matching reconstruction family.
6. List efficiency, fake, duplicate, mis-ID, migration, and tail mechanisms.
7. State scaling with energy, momentum, angle, occupancy, pileup, dose, rate, time.
8. Name the data-driven calibration/performance samples and the simulation-truth-only quantities.
9. Fill the chain (response -> calibration -> alignment/conditions -> reconstruction ->
   performance -> validation -> systematics) and trace a defect to a physics observable.

### Checklist for reading a performance plot

- Which quantity, and which estimator, center, width, tail definition, and selection?
- Binned in truth or reco? What phase space? Denominator? Matching rule?
- Statistical uncertainty (binomial for efficiencies)? Weighted events?
- Simulation only or data? What proxy and its bias?
- Is there a plateau (insensitive) or a turn-on (sensitive)? Are tails plotted on a log scale?
- Are the two curves compared under equivalent definitions and conditions?
- What is missing: correlations, time dependence, pileup dependence?

### Diagnostic sequence for a data/MC discrepancy

1. Confirm the comparison is like-for-like (selection, weights, pileup, normalization).
2. Check the conditions and period: run/fill dependence, dead channels, conditions tags.
3. Localize it in the chain: raw quantity -> local object -> object -> physics quantity.
4. Look at conditional and joint distributions and tails, not just marginals.
5. Test candidate causes with independent controls (alignment vs timing vs gain vs material).
6. Fix the *cause* (calibration/model), not the symptom (reweighting), and validate on an
   independent sample. 7. Assign a systematic for the remaining freedom.

### Calibration and alignment validation checklist

- Closure on an independent sample; no circularity (do not tune on the measured observable).
- Relative vs absolute, local vs global, in-situ vs external explicitly stated.
- Interval of validity and time dependence monitored; conditions versions recorded.
- Weak modes tested with an independent constraint (resonance mass, cosmics, `E/p`).
- Calibration-alignment coupling checked (timing error vs spatial shift, gain vs energy).
- The stored calibration applied in both data and simulation consistently.

### One-page synthesis: common principles and family exceptions

**Common to all.** Measurements are inverse problems with hidden parameters; response
is not calibration; spread has a floor (stochastic, irreducible) and a systematic part
(correlated, correctable); every performance number is a conditional probability with
a named population; thresholds turn shifts into efficiency; truth is simulation-only;
pulls test uncertainties, not just widths; and systematics are propagated by rerunning
the reconstruction and selection.

**Family exceptions.** Silicon: charge sharing, ghosts, dose. Drift/TPC: ambiguities
(left-right, `t_0`), `r(t)`, distortions. Timing: correlated clock terms do not average.
Cherenkov/DIRC: photon-path and index terms. TRD/`dE/dx`: Landau tails, saturation.
Calorimeters: `e/h`, sampling, leakage, confusion in particle flow. Muons: charge-sign
failure at high `p`, weak modes. Noble liquid: recombination and lifetime.
Rare events: threshold and fiducial mass dominate. Astroparticle: atmosphere/medium
optics as the largest nuisance, exposure replaces acceptance. Emulsion: no timing.

### Self-audit (before submitting a detector analysis)

Can the framework be applied to an uncovered detector? Is every efficiency denominator
unambiguous? Is every resolution tied to estimator, reference, center, width, selection,
tail? Does every pull use the right covariance? Does every data/MC correction state
derivation, applicability, correlation, extrapolation? Can each detector systematic be
traced to a physics observable? Are comparisons made under equivalent definitions?
Are approximations labeled? Are tails and catastrophic failures shown? Are rare-event,
neutrino, astroparticle, timing, and auxiliary systems integrated?

### Common misconceptions and failure modes

- **Fixing the symptom.** Reweighting to hide a calibration/alignment cause.
- **Case-study generalization.** The mechanism transfers; the numbers do not.
- **Skipping the independent control.** Agreement on the tuned observable is not validation.

### Deliverables

- For a real defect: the eight-step trace with the data-driven evidence for each step.
- The filled checklists relevant to the task, with unchecked items marked and justified.

## Final synthesis

See Chapter 19 for the reusable checklists, the diagnostic sequence for data/MC
discrepancies, the calibration/alignment validation checklist, and the one-page
synthesis of common principles and family-specific exceptions. The compact form is
`high_energy_detector_principles_summary.md`.

## Appendices (separate files)

- **Appendix A**: `detector_comparison_tables.md`, the master, tracking, timing, PID,
  ECAL/HCAL, distinction, reconstruction/performance, systematics, and auxiliary-detector tables.
- **Appendix B**: `glossary.md`.
- **Appendix C**: `detector-principles-bibliography.md`.

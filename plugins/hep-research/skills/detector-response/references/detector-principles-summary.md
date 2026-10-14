# High-Energy-Physics Detectors: A Quick Reference

A self-contained summary of a unified framework for understanding, comparing, and
validating HEP detectors. Symbols and acronyms are defined in the [detector glossary](detector-glossary.md). Relations
are labeled *exact*, *approximate*, *asymptotic*, *empirical*, or *detector-specific*.
No experiment-specific performance number appears here; quote such numbers only with the
apparatus, configuration, phase space, conditions, and source.

## 1. The unified chain

The chain from particle and interaction to physics-observable bias is drawn once, in the
[detector measurement framework](detector-measurement-framework.md#the-chain).

Each arrow has its own model, parameters, failure modes, and validation sample. Diagnose
a defect by finding where it first becomes visible; find its physics impact by pushing
it through every later arrow.

**Forward/inverse view.** A measurement is a probabilistic inverse problem:
`y = f(x; theta) + epsilon`, with likelihood `p(y|x,theta)` (simulable) and posterior
`p(x|y,theta) ∝ p(y|x,theta) p(x)` (what reconstruction approximates). `x` = latent
particle/event properties, `y` = recorded observables, `theta` = detector, geometry,
field, material, electronics, environment and calibration parameters, `epsilon` =
stochastic fluctuation and noise. Identifiability, the assumed `theta`, priors, and model
mismatch decide how good an estimate of `x` can be. Errors in `theta` are *shared,
correlated systematics*; more events never average them away.

**Sources of spread.** Irreducible physical fluctuation (Landau, photostatistics,
sampling) and electronic noise are stochastic and average with statistics. Calibration,
alignment, field, material, algorithm priors, and model mismatch are systematic and do
not.

**Distinctions to keep.** Response (what the detector does) vs calibration (the
correction procedure); alignment vs position/timing calibration; bias/scale vs
resolution; intrinsic vs system resolution; per-hit vs per-object resolution;
detector resolution vs unfolding regularization; single-particle vs jet calibration;
truth matching (simulation only) vs data-accessible proxies.

## 2. The fourteen questions for any detector

The fourteen questions to answer for any detector are in the
[detector measurement framework](detector-measurement-framework.md#the-fourteen-questions-template-for-any-detector).

## 3. Core equations

The seventeen cross-cutting relations (forward model, curvature, `chi^2`, Highland, Bethe, drift and diffusion,
Cherenkov, TOF, calorimeter resolution, photostatistics, efficiency chain, residuals and pulls, scale factors,
error propagation, response matrix, `N_sigma`, binomial and Poisson intervals), with symbols, units, validity
and parameter sources, are in [core detector equations](core-detector-equations.md); this file does not
repeat them.

## 4. Detector families at a glance

| Family | Earliest signal | Inferred quantity | Characteristic ambiguity | Distinctive residual / diagnostic |
|---|---|---|---|---|
| Hybrid pixel / MAPS | charge in silicon | 2D position, vertex | merged clusters | unbiased hit residual vs angle, cluster size |
| Silicon strip | charge in silicon | 1D position | stereo ghosts | residual vs incidence angle; occupancy |
| Drift chamber / tube / straw | drift time | radius | left-right; `t0` vs alignment | residual vs drift distance |
| TPC (gas or liquid) | 3D charge + time | 3D track, `dE/dx` | crossing time `t_0`; distortion vs alignment | cluster-track residual vs `(r,z,rate)` |
| RPC / MRPC | gas-gap avalanche | position, time | multi-hit | efficiency vs voltage (plateau) and rate |
| GEM / Micromegas | micropattern gain | position, angle | angle dependence | residual vs angle; gain map |
| Scintillating fiber | light amplitude | position | stereo ghosts | residual vs position along fiber |
| Emulsion | grains | tracks, vertices | no timing | base-track agreement |
| TOF / LGAD / MCP timing | pulse time | `beta`, time | multi-hit, `t_0`, wrong bunch | time residual vs species/amplitude/run |
| RICH / DIRC / TOP | Cherenkov photons | `beta`, species | photon path; emission/chromatic terms | photon-angle residual vs momentum |
| Threshold/differential Cherenkov | photon count | species by threshold | near-threshold Poisson | turn-on curve vs momentum |
| TRD | transition X-rays + `dE/dx` | `e/pi` | `dE/dx` overlap | rejection at fixed efficiency vs momentum |
| `dE/dx` / cluster counting | ionization samples | species | band crossings, saturation | band position vs `beta gamma` |
| ECAL | EM shower | energy, position | overlap, conversions | `E/p`, resonance mass vs `eta` and `E` |
| HCAL / jets | hadron shower | energy | `e/h`, leakage | response vs `pT`, flavor |
| Muon system | ionization hits | `p`, `q`, ID | left-right, weak modes | dimuon mass and `q/p` vs `q*eta` |
| Noble-liquid TPC | scintillation `S1` + charge `S2` | energy, position, species | `S1`-`S2` pairing; recombination | charge, light vs depth and time |
| Water / scintillator | Cherenkov / scintillation | vertex, direction, energy | ring counting, optics | Michel electron, `pi^0` closure |
| Bolometer / semiconductor | phonons / ionization | energy, recoil type | noise vs signal at threshold | calibration lines, leakage vs energy |
| Air-shower, IACT, neutrino telescope | sparse light/particle samples | direction, energy, composition | topology, atmosphere/medium | hybrid/independent cross-check |

**Common exceptions to the shared principles.** Drift and TPC systems can hide a timing
error in a spatial residual. Timing systems have clock/reference terms that do not average
across channels. Emulsion has no intrinsic timing. Muon systems fail at high momentum
through charge misidentification and alignment weak modes. Rare-event searches are
dominated by threshold and fiducial-mass systematics. Astroparticle systems have
the atmosphere or medium optics as the largest nuisance, and the normalization is exposure (acceptance integrated over live time).

## 5. Performance metrics

Every metric needs: an equation, numerator, denominator, conditioning population,
matching rule, phase space, object- or event-level, estimator, and uncertainty. The
definitions (purity, fake, duplicate rate, `N_sigma`, width estimators) are in
[performance metrics](performance-metrics-and-residual-diagnostics.md); this is a summary.

- **Acceptance** `A = N(truth in fiducial)/N(generated)`: truth only.
- **Efficiency** `eps = N(successful)/N(eligible)`: conditional; name the eligible set
  (reconstruction, ID, trigger, and selection efficiencies have different denominators).
- **Purity** `P = N(matched true, correct identity)/N(selected)`.
- **Fake rate**: selected objects with no valid truth match. **Mis-ID**: a real particle
  assigned the wrong species. **Duplicate rate**: truths matched by several objects,
  over matched truths (say which convention).
  `1 - P` = fakes + mis-ID + duplicates, so fake rate is not universally `1 - P`.
- **Response** (`<x_reco>/x_true`) and **bias** (`<x_reco - x_true>`), binned in *truth*. **Resolution**: width
  of `x_reco - x_true` with an explicit estimator (core `sigma`, `sigma_68`,
  `IQR/1.349`, `1.4826 MAD`, RMS or std), quoted with the **tail fraction**.
- **Selection sculpts resolution**: a cut on a reconstructed variable removes one side of
  the residual distribution, improving apparent resolution and creating a conditional bias.
- **Object vs event level**: with `k` independent objects, "at least one" is `1-(1-p)^k`;
  correlations break independence, so measure the event-level quantity.

**Worked example (synthetic toy).** Generated 10000; in fiducial 8000 -> `A = 0.800`.
Reconstructed 7200 of 8000 -> `eps_R = 0.900`. Pass ID 6480 of 7200 -> `eps_S = 0.900`.
Total `= 0.810` of fiducial, `0.648` of generated (`0.8×0.9×0.9`). Selected 6660 = 6480 correct + 60
mis-ID + 120 fake -> purity `0.973`, fake rate `0.0180`, mis-ID share `0.0090`; `1 - P = 0.0270` is
fake plus mis-ID. Twenty relative energy residuals with one
`6.5%` outlier: mean `0.395%`, std `1.56%` (RMS `1.57%`), median `0.15%`, `1.4826 MAD = 0.74%`, tail
fraction `5%`; without the outlier mean `0.074%` and std `0.63%` (RMS `0.62%`), values in
[performance metrics](performance-metrics-and-residual-diagnostics.md). The mean and width were
driven by one event, so quote core bias, core width, and tail separately.

## 6. Residuals, pulls, and coverage

- A **biased** residual (prediction includes the measurement) has `V_r = V_meas - V_pred`
  and is narrower than `sigma_meas`; an **unbiased** (exclusive or leave-one-out) residual has
  `V_r = V_meas + V_pred'`. Use the unbiased one for intrinsic resolution and efficiency.
- Pulls have mean 0 and width 1 only if the model is correct, the estimator is unbiased,
  the covariance (including correlations) is right, errors are Gaussian, and the
  population is not selected on the residual. Width > 1: underestimated errors or
  mismatch; < 1: overestimated errors or biased residual with `sigma_meas`.
- Read plots for: mean trends (bias, misalignment), width trends (resolution scaling),
  discontinuities (module or interval-of-validity edges), tails (outliers, wrong
  association), and multimodality (two populations).
- **Coverage**: a `k`-sigma interval should contain the truth at its nominal probability.
  Narrow residuals do not prove correct pulls or coverage.

## 7. Calibration, alignment, validation, systematics

| Concept | Question | Typical mistake |
|---|---|---|
| Response | What does the detector do? | Equated with calibration |
| Calibration | Which constants map `y` to physical units? | Tuned on the measured observable (circular) |
| Alignment | Where are the elements? | Conflated with timing or drift calibration |
| Reconstruction | Which objects best explain `y`? | Treated as truth |
| Performance | How good is it? | Denominators unstated |
| Validation | Does the model match data? | 1D agreement only |
| Systematic | What uncertainty remains? | Double counting; arbitrary envelopes |

**Simulation levels.** Generator truth, simulation truth, digitized signals,
reconstructed objects. Only the last two exist in data; every data-side performance
number rests on a proxy (tag-and-probe, standard candle, redundant subdetector,
sideband, cosmic ray) whose own bias is part of the uncertainty.

**Validation checklist.**
- Compare normalization, shape, conditional and joint distributions, correlations,
  efficiencies, tails, and time dependence. Never accept 1D agreement alone.
- Use independent samples for derivation and validation; check closure, diagnose any non-closure,
  and quote the residual as a systematic.
- Scale factors: measure data and MC identically, in the analysis phase space, apply at
  the level of measurement, and state binning, correlations, smoothing, and
  extrapolation.
- Reweighting risks: hidden-variable mismatch, damaged correlations, lost closure,
  double correction. Fix the cause when possible.
- Do not tune the simulation or calibration on the observable being measured.

**Systematics checklist.**
- Separate statistical, calibration, alignment, modeling, method, environmental, and
  finite-simulation uncertainties; a stochastic fluctuation is not a systematic.
- Propagate by modifying the condition or object, rerunning the affected reconstruction
  and selection, recomputing the final observable, and validating the variation on a
  control. Changing only a final weight is insufficient for a kinematic variation.
- State each uncertainty's correlation model: normalization/shape,
  correlated/uncorrelated, symmetric/asymmetric, local/global, time-correlated.
- Use `V_f ≃ J V_x J^T` only where responses are near-linear; otherwise use toys or
  profiling.
- Avoid double counting, noisy (finite-MC) variations promoted to shapes, excessive
  smoothing, arbitrary envelopes, and unjustified decorrelation.

| Nuisance | Reconstructed effect | Physics effect |
|---|---|---|
| Gain/pedestal | energy/charge scale | mass, yields |
| Time offset | time, `beta`, drift coordinate | PID, momentum |
| Field map / alignment weak mode | momentum scale, charge-dependent `q/p` | mass, charge asymmetry |
| Material | scattering, conversions | efficiency, scale |
| Optical attenuation / refractive index | light yield, angle, threshold | energy scale, PID |
| Electron lifetime | charge vs depth | energy scale, threshold |
| Dead channels | acceptance holes | rate, efficiency |
| Pileup/noise | clusters, `MET` | jets, isolation |
| Atmosphere / ice / water optics | shower/light profile | flux, composition, effective volume |

## 8. Detector combination

Combine independent estimates by inverse-variance weighting; with correlated
uncertainties use the covariance (BLUE), noting that large correlations can give negative
weights or a result worse than the best input if the correlation is underestimated.
Multiplying per-detector likelihoods (global PID, particle flow) assumes independence;
shared tracks, alignment, or pileup make that overcount information. Watch shared
hits/clusters, double-counted energy, and boundary effects. An added detector helps when
its error is independent and comparable or it covers gaps or rejects fakes; it hurts when
a low-efficiency requirement or a biased input dominates, or when it adds a new failure
mode.

## 9. Common failure signatures

| Symptom | First suspects |
|---|---|
| Dimuon mass shifts with `q*eta` | Alignment weak mode, field map |
| Residual left/right structure vs drift distance | `t0`, `r(t)`, wire position (sign pattern depends on the residual convention, [glossary](detector-glossary.md)) |
| Coherent residual trend with rate or radius | Space-charge distortion |
| Energy scale wrong vs `eta` | Upstream material, intercalibration |
| PID efficiency drifting with run | Refractive index, gain, clock |
| Charge shrinks with drift time | Electron lifetime / purity |
| Jet response depends on flavor | `e/h` non-compensation |
| Resolution improves after a reco-level cut | Selection bias, not detector improvement |
| Pulls wider than 1 with narrow residuals | Underestimated errors or missing correlations |

## 10. A reusable checklist for an unfamiliar detector

1. Answer the fourteen questions. 2. Name `x`, `y`, `theta`, `epsilon`; list irreducible
fluctuations and correctable variations. 3. State the direct observable, the inferred
quantity, and the degeneracy. 4. Name the natural local and global objects and residual.
5. Identify the topology (sparse points, image, waveform, ring, shower, segment, time
series, distributed array). 6. List mechanisms for inefficiency, fakes, duplicates,
mis-ID, migration, and tails. 7. State scalings with energy, momentum, angle, occupancy,
pileup, dose, rate, time. 8. Name the data-driven calibration and performance samples
and the simulation-only quantities. 9. Fill the chain and trace a defect to a physics
observable.

**Reading a performance plot.** Which quantity, estimator, center, width, tail
definition, selection? Binned in truth or reco? Denominator and matching rule? Statistical
uncertainty (binomial)? Simulation or data, and what proxy? Plateau (insensitive) or
turn-on (sensitive)? Tails on a log scale? Equivalent definitions across curves?

**Diagnosing a data/MC discrepancy.** Confirm like-for-like comparison -> check
conditions and period -> localize in the chain -> inspect conditional and joint
distributions and tails -> test candidate causes with independent controls -> fix the
cause, validate independently -> assign a systematic for the remaining freedom.

**Calibration/alignment validation.** Closure on an independent sample without
circularity; relative vs absolute and local vs global stated; intervals of validity
monitored; weak modes tested with an independent constraint (resonance mass, cosmics,
`E/p`); calibration-alignment coupling checked; the same constants applied in data and
simulation.

## 11. Reference index

One file per topic under `references/`; load only what the task needs.

- Framework and equations: [measurement framework](detector-measurement-framework.md), [core equations](core-detector-equations.md), [signal formation and readout](signal-formation-and-readout.md), [front-end electronics and signal processing](front-end-electronics-and-signal-processing.md), [detector systems](detector-systems-overview.md).
- Subsystems: [tracking](tracking-and-vertexing.md), [gaseous and specialized tracking](gaseous-and-specialized-tracking-technologies.md), [timing](timing-detectors.md), [calorimetry](calorimetry-ecal-hcal.md), [particle identification](particle-identification.md), [Cherenkov imaging and photosensors](cherenkov-imaging-variants-and-photosensors.md), [muon systems](muon-systems.md), [noble-liquid, neutrino and rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md).
- Reconstruction and performance: [physics objects](physics-objects-jets-btagging-met.md), [triggers, luminosity and pileup](triggers-luminosity-pileup.md), [event reconstruction](event-reconstruction.md), [truth matching](reconstruction-performance-and-truth-matching.md), [performance metrics](performance-metrics-and-residual-diagnostics.md), [response and forward folding](response-and-forward-folding.md).
- Validation and conditions: [data/MC validation and detector systematics](data-mc-validation-and-detector-systematics.md), [detector simulation](detector-simulation.md), [calibration and alignment](calibration-and-alignment.md).
- Lookup: [case studies and checklists](detector-case-studies-and-checklists.md), [comparison tables](detector-comparison-tables.md), [glossary](detector-glossary.md), [bibliography](detector-principles-bibliography.md).
- Astroparticle instruments: [cosmic-ray spectrum and composition](cosmic-ray-spectrum-and-composition.md), [extensive air showers](extensive-air-showers.md), [ground-based arrays](ground-based-detection-arrays.md), [imaging atmospheric Cherenkov telescopes](imaging-atmospheric-cherenkov.md), [neutrino telescopes](neutrino-astronomy.md), [space-based direct detection](space-based-direct-detection.md), [multimessenger analysis](multimessenger-analysis.md).

### Task routing: what to confirm first

| Task | Confirm first | Start with |
|---|---|---|
| Concept explanation | whether experiment-specific facts are needed (then the profile, not memory) | the subsystem file |
| Design estimate | approximations, validity range, neglected terms; script outputs carry their validity flags | [core equations](core-detector-equations.md), the scripts |
| Performance measurement | data sample, denominator, matching definition, estimator, uncertainty (unweighted binomial counts only for a Clopper-Pearson interval) | [performance metrics](performance-metrics-and-residual-diagnostics.md), [truth matching](reconstruction-performance-and-truth-matching.md) |
| Response construction | event mapping, weights, misses and fakes, binning, MC statistics, intended use; a mean and width alone do not determine a migration matrix | [response and forward folding](response-and-forward-folding.md) |
| Calibration diagnosis | derivation and validation samples, conditions per period, weak modes | [calibration and alignment](calibration-and-alignment.md) |
| Recasting | validity range of the published response and the extrapolation strategy | [response and forward folding](response-and-forward-folding.md) |

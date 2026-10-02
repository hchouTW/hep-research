# High-Energy-Physics Detectors: A Quick Reference

A self-contained summary of a unified framework for understanding, comparing, and
validating HEP detectors. Symbols and acronyms are defined in `glossary.md`. Relations
are labeled *exact*, *approximate*, *asymptotic*, *empirical*, or *detector-specific*.
No experiment-specific performance number appears here; quote such numbers only with the
apparatus, configuration, phase space, conditions, and source.

## 1. The unified chain

```
particle & interaction -> detector response -> signal formation & transport
 -> electronics & raw data -> calibration & alignment -> local reconstruction
 -> pattern recognition & object reconstruction -> PID & detector fusion
 -> performance measurement -> data/MC validation -> systematic uncertainties
 -> physics-observable bias
```

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

1. What enters the sensitive volume? 2. Which microscopic interaction makes the signal?
3. What is the earliest physical signal (charge, light, heat, phonons, current, drift
time)? 4. What is digitized (ADC, TDC, waveform, binary hit, time-over-threshold, image,
trigger primitive)? 5. What is the forward model with nuisance and stochastic terms?
6. Which calibrations, conditions, geometry, field maps, material are required?
7. Which local objects are reconstructed? 8. Which pattern recognition, association, fit,
or inversion follows? 9. Which ambiguities or degeneracies are characteristic?
10. What causes inefficiency, fakes, duplicates, migrations, tails, catastrophic failures?
11. How does performance scale with energy, momentum, angle, occupancy, pileup, dose,
rate, time? 12. What is measurable in data, and what needs simulation truth?
13. How are data/MC discrepancies corrected or assigned as uncertainties? 14. How can a
defect bias a final physics result?

## 3. Core equations

| # | Relation | Meaning, units, validity |
|---|---|---|
| 1 | `y = f(x;theta) + epsilon` | Forward model (approximate if `epsilon` is taken Gaussian; Poisson and Landau-like noise violate it) |
| 2 | `pT ≈ 0.3 |q| B R` | `pT` in GeV/c, `B` in T, bending radius `R` in m (exact in a uniform field, conventional HEP units); rigidity `R = p/q` is what a spectrometer measures |
| 3 | `chi^2 = r^T V^{-1} r` | Least-squares objective; `V` must be the covariance of the residual vector |
| 4 | `theta_0 = (13.6 MeV/(beta c p)) z sqrt(x/X_0) [1 + 0.038 ln(x z^2/(X_0 beta^2))]` | Highland multiple scattering (approximate, ~11% for `1e-3 < x/X_0 < 100`); sets the low-momentum resolution floor |
| 5 | Bethe-Bloch: `-<dE/dx> = K z^2 (Z/A)(1/beta^2)[0.5 ln(2 m_e c^2 beta^2 gamma^2 W_max/I^2) - beta^2 - delta/2]`, `K = 0.307 MeV mol^-1 cm^2` | Mean loss for heavy charged particles at intermediate energy (approximate). Fluctuations: Landau/Vavilov (asymmetric, long tail) for thin absorbers (`kappa = xi/W_max << 1`), Gaussian for thick ones |
| 6 | `v_d = mu E`; `sigma = sqrt(2 D L/v_d) = C_D sqrt(L)` | Drift and diffusion (low-field, approximate; real gases need measured `v_d(E,B,T,P)` and `C_D`) |
| 7 | `cos theta_C = 1/(n beta)`; `p_th = m c/sqrt(n^2-1)`; `d^2N/(dx dE) ≈ 370 sin^2 theta_C eV^-1 cm^-1` | Cherenkov angle, threshold, and yield before detection efficiency |
| 8 | `beta = L/(c t)`; `m^2 = p^2 (1/beta^2 - 1)` | TOF; `L` is the track path length; separation falls as `1/p^2` |
| 9 | `sigma_E/E = a/sqrt(E) ⊕ b/E ⊕ c` | Calorimeter resolution (⊕ = quadrature sum): stochastic, noise, constant (empirical) |
| 10 | `sigma/N ≈ sqrt(F/N_pe)` | Photostatistics with excess-noise factor `F >= 1` (Poisson-limited) |
| 11 | `P(S) = P(A) P(R|A) P(S|R,A)` | Exact chain rule; a naive product of separately measured efficiencies is not |
| 12 | `r = x_meas - x_pred`, `p = r/sigma_r`, `V_r = V_meas + V_pred - C - C^T` | Residual, pull, and residual covariance including measurement-prediction correlation `C` |
| 13 | `SF = eps_data/eps_MC` | Efficiency scale factor |
| 14 | `V_f ≃ J V_x J^T` | First-order propagation; fails for thresholds, migration, strong nonlinearity, asymmetric errors |
| 15 | `n_i^reco = sum_j R_ij n_j^truth + b_i` | Response matrix: resolution (off-diagonal), inefficiency (column sums < 1), background `b_i`, model dependence via the truth spectrum |
| 16 | `N_sigma = |mu_1-mu_2|/sqrt(sigma_1^2+sigma_2^2)` | PID separation; Gaussian approximation, unreliable with tails or few photons |
| 17 | Binomial/Poisson intervals | Efficiencies: exact Clopper-Pearson or Wilson, not Gaussian near 0 or 1; counts: Poisson |

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
| TRD | transition X-rays + `dE/dx` | `e/h` | `dE/dx` overlap | rejection at fixed efficiency vs momentum |
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
the atmosphere or medium optics as the largest nuisance, and exposure replaces acceptance.

## 5. Performance metrics

Every metric needs: an equation, numerator, denominator, conditioning population,
matching rule, phase space, object- or event-level, estimator, and uncertainty.

- **Acceptance** `A = N(truth in fiducial)/N(generated)`: truth only.
- **Efficiency** `eps = N(successful)/N(eligible)`: conditional; name the eligible set
  (reconstruction, ID, trigger, and selection efficiencies have different denominators).
- **Purity** `P = N(matched true)/N(selected)`.
- **Fake rate**: selected objects with no valid truth match. **Mis-ID**: a real particle
  assigned the wrong species. **Duplicate**: one truth matched by several objects.
  `1 - P` = fakes + mis-ID + duplicates, so fake rate is not universally `1 - P`.
- **Response/scale/bias**: central offset, binned in *truth*. **Resolution**: width
  of `x_reco - x_true` with an explicit estimator (core `sigma`, `sigma_68`,
  `1.4826 MAD`, RMS), quoted with the **tail fraction**.
- **Selection sculpts resolution**: a cut on a reconstructed variable removes one side of
  the residual distribution, improving apparent resolution and creating a conditional bias.
- **Object vs event level**: with `k` independent objects, "at least one" is `1-(1-p)^k`;
  correlations break independence, so measure the event-level quantity.

**Worked example (synthetic toy).** Generated 10000; in fiducial 8000 -> `A = 0.800`.
Reconstructed 7200 of 8000 -> `eps_R = 0.900`. Pass ID 6480 of 7200 -> `eps_S = 0.900`.
Total `= 0.810` of fiducial, `0.648` of generated (`0.8×0.9×0.9`). Selected 6600 =
6420 correct + 60 mis-ID + 120 fake -> purity `0.973`, fake rate `0.0182`, mis-ID share
`0.0091`; `1 - P = 0.0273` is fake plus mis-ID. Twenty relative energy residuals with one
`6.5%` outlier: mean `0.395%`, RMS `1.56%`, median `0.15%`, `1.4826 MAD = 0.74%`, tail
fraction `5%`; without the outlier mean `0.074%` and RMS `0.63%`. The mean and RMS were
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
- Use independent samples for derivation and validation; check closure and quote any
  non-closure as a systematic.
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
| Residual left/right offset vs drift distance | `t0`, `r(t)` |
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

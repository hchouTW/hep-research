# In-Situ Calibration Methods

How detector constants (gains, scales, timing offsets, light speeds, attenuation lengths, positions) are solved for
from data, and how convergence, bias and per-channel precision are judged; then the method per detector type, each
with at least two reference samples. Environments (R1 codes): COL, FXT, SPC, UGD, GND; NUC is a gap (no source read).

Chain order, test beam versus in-situ, curvature weak modes, conditions and iteration
contracts: [calibration and alignment](calibration-and-alignment.md) ([iterative
loops](calibration-and-alignment.md#iterative-loops-as-contract-steps)). Residual propagation: [calibration residual
propagation](calibration-residual-propagation.md). Charge injection and linearity: [front-end
calibration](front-end-calibration.md). Track and chamber alignment, momentum scale: [in-situ alignment and momentum
scale](in-situ-alignment-and-momentum-scale.md). Fitting *simulator* parameters to data is simcal, owned by
hep-statistics ([simcal scripts](../../hep-statistics/references/core-stats-guide.md#skill-scripts)), not this page.

## General formulation

Every in-situ calibration has three parts:

- **Unknowns.** Per-channel constants `c_k` (a multiplicative gain, an additive offset, a shape parameter), often a
  chain of factors applied in sequence (relation 1).
- **Reference sample.** Events whose expected response is known independently of `c_k`: a resonance mass, an
  ionization loss over a known path length (arXiv:0904.2226, sec. 5.2, pp. 20-21), a symmetry of the flux, a source
  line, a beam of known energy (test beam, coded FXT: pions of known energy give a hadron-to-electron scale factor,
  taken constant over energy; arXiv:1207.4210, sec. 2.3, p. 8), a track momentum. Where no test beam exists
  the atmosphere or the sky supplies it (GND: muon rings; PDG RPP 2025, Particle detectors for non-accelerator
  physics, sec. 36.2.2, p. 9).
- **Residual.** Measured minus expected response as a function of `c_k`, summed over the sample.

### Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | `Q_corr = Q_raw * F_1 * F_2 * ... * F_n` (drift, linearity, channel-to-channel, attenuation, absolute scale) | exact (definition) | applied in sequence; each derived with what it depends on applied, not only earlier factors (S after L and A); two mutually dependent on one sample: take one from independent data (a test stand) or iterate both (inference); arXiv:0805.3170, sec. 5, Eq. 1, p. 58, secs. 5.2.2-5.2.3, pp. 64-65 |
| 2 | per-channel iteration `c_k <- c_k * x_ref / x_fit,k` (peak, mass or MPV fitted per channel) | approximate | quality depends on entries per channel and S/B (arXiv:1306.2016, sec. 4.2.2, p. 16); neighbours coupled (p. 15); convergence under weak coupling is inference |
| 3 | `chi2(p, q) = sum_tracks sum_meas ((m_ij - f_ij(p, q_j)) / sigma_ij)^2`, global `p`, local `q_j` | exact (objective) | arXiv:1403.2286, sec. 4, Eq. 1, p. 9 |
| 4 | linearised normal equations `C a = b`, reduced to `C' dp = b'` by block algebra | exact for the linearised problem; iterate when corrections are not small | no information on `dp` is lost; arXiv:1403.2286, sec. 4, Eq. 2, pp. 9-10 |
| 5 | constraints `f^T a = f_0` by Lagrange multipliers: `[[C, f], [f^T, 0]] [a, lambda] = [b, f_0]` | exact (linear constraints) | solved directly, no initial values; arXiv:hep-ex/0208021, sec. 2, Eq. 9, p. 4 |
| 6 | constrained track term `chi2_cons` added per track (COL: beam spot; external detector; resonance mass) | exact (objective) | arXiv:2007.07624, sec. 3.2.4, Eq. 14, p. 10 |
| 7 | methods combined per channel, weighted by precision | approximate (inverse-variance weights assume independent sets; a shared seed or data, or one set refining another, needs the covariance) | arXiv:1306.2016, secs. 4.2-4.2.4, pp. 14-17; sec. 5.4, p. 30 |

## Solvers

- **Per-channel iteration** (relation 2): fit the reference peak per channel, correct, repeat. In the cited diphoton
  method a candidate enters the channels its photons are centred on, but each photon energy sums neighbours, which
  couples them: iterate until stable (arXiv:1306.2016,
  sec. 4.2.2, pp. 15-16).
- **Global linear least squares** (relations 3 to 5): all global and local parameters at once, the local ones
  eliminated by block reduction (Millepede-type); every correlation is kept and the reduced system has the size of
  the global parameters only (arXiv:hep-ex/0208021, secs. 1-3, pp. 1-7; arXiv:1403.2286, sec. 4,
  pp. 9-10).
- **Iterative position solvers** ([in-situ alignment](in-situ-alignment-and-momentum-scale.md#track-based-alignment)):
  mean-residual iteration, which shrinks the residuals but biases the parameters (arXiv:hep-ex/0208021, sec. 1, p. 1);
  gradient descent of the total `chi2` with step halving (SPC; arXiv:1712.02739, secs. 5.2-5.2.2, pp. 6-8); iterative
  minimisation of the summed track `chi2` (Minuit2) or Millepede-II in test-beam telescopes (FXT; arXiv:2011.12730, sec.
  3.5, p. 9); and ordered steps, elements within a structure first (SPC; arXiv:0904.2226, sec. 10.2, p. 44). The frame
  is fixed by a reference element (FXT; arXiv:2011.12730, sec. 2.3.2, p. 6) or by zero mean shifts and rotations, there
  by construction against the ideal frame (SPC; arXiv:0904.2226, sec. 10.1, p. 44); with straight tracks neither fixes a
  shear or a `z` scale.

## Unconstrained modes and external constraints

A parameter combination that the residual does not change is undetermined; the matrix is then singular or nearly
so. With too many global parameters the whole detector shifts and rotates freely: fix some parameters or constrain
the mean displacement and rotation to zero (arXiv:hep-ex/0208021, sec. 3, p. 7). Weak modes are distortions that
leave `chi2` nearly unchanged yet bias the solution; constraints on track parameters (beam spot, external detectors,
resonance masses) control them (COL; arXiv:2007.07624, sec. 3.2.4, p. 10), as do non-track measurements of the
degrees of freedom tracks hardly see (COL; arXiv:0911.4022, sec. 1, p. 3). Gains have the same structure: a
symmetry method fixes constants within a class only; the scale between classes and the absolute scale need another
reference (arXiv:1306.2016, sec. 4.2, p. 14). Curvature weak modes:
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes).

## Convergence, bias and per-channel precision

- **Stopping rule, fixed in advance:** the largest parameter change between successive iterations below
  a threshold (arXiv:0904.2226, p. 44, sec. 10.1). Step-size control is not a stopping rule (arXiv:1712.02739,
  sec. 5.2.1, pp. 7-8): under halving the parameter change is the step, so the threshold passes once the step
  collapses. Also require the gradient norm below a declared threshold (for relation 2, with no objective: the
  largest remaining offset over its uncertainty), and report `not-converged` when the step was halved below a
  declared floor.
- **Bias.** Iterating on biased residuals shrinks the residuals, not the bias (arXiv:hep-ex/0208021, sec. 1, p. 1).
  A symmetry method reaches a systematic floor set by how well the symmetry holds (material in front of the
  detector), not by statistics; ratios over successive periods cancel much of it, so the method monitors
  stability and refines constants from other methods (arXiv:1306.2016, sec. 4.2.1, p. 15).
- **Per-channel precision** depends on the entries per channel and on the signal-to-background ratio of the
  reference peak (arXiv:1306.2016, sec. 4.2.2, p. 16; FXT test beam, per straw from the number of muon hits:
  arXiv:astro-ph/0608641, sec. 4.2.2, p. 4); the statistical term falls roughly as `1/sqrt(N_k)` until the
  systematic floor (approximate). Quote both, per channel class, with the period needed to reach them.
- **Validation.** Each method's precision is estimated with simulation and checked by a channel-by-channel
  comparison of methods with different systematics (arXiv:1306.2016, sec. 4.2, pp. 14-15); compare unused sets before combining.
  A set that seeds the iteration, enters the combination, or built a set that does tests consistency, not precision;
  the pre-calibration validates precision only for channels where it did none of these.

<!-- example: experiment-specific illustration (CMS ECAL, LHC pp at 7 TeV, 2010-2011; arXiv:1306.2016) -->
CMS ECAL intercalibration: phi-symmetry with about 10^8 events is limited by a systematic 1.5% in the central
barrel, above 3% at larger |eta|, while week-to-week ratios reach 0.3% (sec. 4.2.1, p. 15); pi0/eta reaches 0.5-1%
per month in the barrel and 2-4% every 2-3 months in the endcaps (sec. 4.2.2, p. 16). The pre-calibration, the
initial set, validated the 2010 pi0/eta precision; the 2010 set enters the 2011 combination (secs. 4.2-4.2.4,
pp. 14-17): consistency tests, by the rule above.
<!-- /example -->

## Instances by detector type

### Electromagnetic calorimeters

- **Symmetry of the flux** (COL): equal deposited transverse energy for channels at the same pseudorapidity in
  minimum-bias events; intercalibrates within a ring (arXiv:1306.2016, sec. 4.2, p. 14).
- **Diphoton resonances** pi0 and eta (COL), per-channel iteration (relation 2) (sec. 4.2.2, p. 16).
- **`E/p` of isolated electrons** (COL: from W and Z decays), within and between rings (sec. 4.2.3, pp. 16-17).
- **Absolute scale** from a dielectron resonance (COL: Z), to which intercalibrations are referred (sec. 4.2, p. 14).
- **Minimum-ionizing particles**: on the ground cosmic muons and beam particles; in orbit protons or light ions
  selected by the geomagnetic cutoff (SPC; arXiv:1901.00734, sec. IV.D, p. 5). Path-length-corrected
  ionization peaks of protons and nuclei, with charge injection for the electronics, calibrate each crystal; a
  cross-range calibration links the gain ranges (SPC; arXiv:0904.2226, sec. 5.2, p. 21). Use the most probable value
  ([calibration standards](calibration-and-alignment.md#calibration-standards-and-their-pitfalls)).
- **Pre-calibration** (laboratory, beam-test and cosmic-ray data) is the initial set (arXiv:1306.2016, sec. 4.2,
  p. 14).

### Hadronic calorimeters

- **Single-hadron `E/p`** of isolated tracks (COL; arXiv:1203.1302, sec. 1, p. 2). Neutral particles in the cone, which
  charged-track isolation does not remove, are subtracted in situ (sec. 3.5, pp. 4-5); the isolation used there was
  found not to bias `E/p` from nearby charged particles (sec. 4.5, pp. 12-13); another radius or cone needs its own
  check; the isolated response differs from the in-jet one (sec. 5.1, p. 16).
- **MIP equalization** with muons, cell to cell, then the MIP as the base unit (test beam, coded FXT;
  arXiv:1207.4210, sec. 2.2, p. 6) and electrons for the MIP-to-GeV step (sec. 2.3, p. 8); cosmic-muon
  strip-to-strip equalization (UGD; arXiv:0805.3170, sec. 5, p. 58); in a running detector, cosmic and collision
  muons probe the response per cell (COL; arXiv:1806.02129, sec. 6.1, pp. 30-31).
- **Radioactive source scans** moved through the calorimeter, per channel (COL only in the sources read;
  arXiv:1806.02129, sec. 4.1, p. 19).
- **Transfer of a test-beam scale**: match the source response to the beam test's, correcting for
  source activity and decay (COL; arXiv:1806.02129, sec. 4.1, p. 19), or carry it through a calibration detector
  exposed to beams and equalized with the same cosmic-muon method (UGD; arXiv:0805.3170, sec. 5, p. 58).

### Time-of-flight and timing

Constants per channel: `t0`, walk, effective light speed, attenuation length.

- **Walk** `t - t_ref = alpha + beta / sqrt(A)` from a laser with a variable attenuator; the form underestimates the
  walk near threshold, where hits are background dominated and dropped (iteration does not fix that); residuals at
  higher pulse heights are corrected iteratively with the same form (FXT; arXiv:2004.10339v1, sec. 3.1.3, Eq. 2, p. 10).
  A per-channel time-versus-charge map from a laser diffuser carries the offset and the walk together (UGD;
  arXiv:1307.0162, sec. 3.1.8, pp. 25-26).
- **Effective light speed and left-right offset** of a bar read at both ends from cosmic rays:
  `t_L - t_R = -2x/v`, bounded by `+-L/v` (exact for a uniform bar), so the width gives `v` and the centre the offset,
  after the walk correction (FXT; arXiv:2004.10339v1, sec. 3.1.4, Eq. 3, p. 10).
- **Attenuation length** from `ln(A_L/A_R) = 2x/mu = -v (t_L - t_R)/mu` (approximate: one exponential length;
  arXiv:2004.10339v1, sec. 3.1.5, Eq. 4, p. 11). In SPC the two-end light asymmetry is calibrated with cosmic
  muons on the ground and cosmic nuclei in orbit, against the track position (arXiv:0904.2226, sec. 5.3, pp. 24-25).
- **Large volumes** (UGD neutrino telescopes): synchronisation signals and LED or laser flashers at known times
  (PDG RPP 2025, sec. 36.3.2, p. 20); the timing-reference chain:
  [timing detectors](timing-detectors.md#calibration-and-diagnostics).

### Gas gain equalization

- **Radioactive gas** (83mKr) spread through the chambers; the decay-electron signal, comparable to a MIP's deposit,
  calibrates each pad's whole chain (short-range variations are electronics), in a TRD and a TPC (COL; arXiv:1709.02743,
  sec. 10.2, p. 43). A pulser separates the electronics gain from the gas gain, which varies with field and geometry
  (COL; arXiv:nucl-ex/0101013, sec. 1.1, p. 2).
- **MIP pulse height** per straw from muons, runs normalised to standard temperature and pressure by the
  gas-density dependence measured on the same muons, and an X-ray line for the energy scale (FXT, a beam test;
  arXiv:astro-ph/0608641, secs. 4.2.2-4.2.4, p. 4). The per-straw factors are mostly preamplifier gain (sec. 4.2.2):
  a whole-chain equalization, not a gas-gain one.
- MRPC and muon-chamber gain equalization: gap (not sourced).

<!-- example: experiment-specific illustration (AMS-02 TRD beam-test prototype; arXiv:astro-ph/0608641, p. 4) -->
With 5000 muon hits per tube the pulse-height intercalibration error is below 2%; at the beam-test operating point a
1% increase in gas density lowers the gas gain by 5% (secs. 4.2.2-4.2.3).
<!-- /example -->

### Ring-imaging Cherenkov detectors

- **Mirror alignment from `dtheta_C(phi)`**: for a well-aligned detector the Cherenkov angle does not depend on the
  azimuth `phi` around the track; fit the per-slice peaks with `dtheta_C = theta_x cos(phi) + theta_y sin(phi)`
  (approximate: small tilts), with photons split by mirror pair (COL; arXiv:1211.6759, sec. 3.3, p. 11).
- **Ring-centre offsets**: the mean difference between fitted and expected ring centre per mirror, relative to a
  reference mirror (FXT; arXiv:1809.04026, sec. 3.1, p. 5).
- **Refractive index** from the same high-momentum tracks, tuned so that `dtheta_C` peaks at zero; a gas radiator
  drifts with temperature, pressure and composition (COL only in the sources read; arXiv:1211.6759, sec. 3.4, p. 12).
- **Second reference sample:** the Cherenkov-angle methods use one sample, tracks with rings; track-independent
  references cover photodetector alignment (photocathode image; sec. 3.3, p. 10) and mirror and gas stability (laser
  and gas-purity monitors; sec. 3.5, p. 12) only: a gap for mirror constants and index.

### Alignment and momentum scale

Alignment (Millepede-II, General Broken Lines, iterative `chi2`) and the momentum scale:
[in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md).

## Methods (decision table)

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| many channels, a flux symmetric in one coordinate | symmetry equalization | symmetry holds to the target precision, or (monitoring by ratios) its breaking (material, thresholds) is unchanged between periods, checked with an independent method as precise over the same period; rate | fixes within a class only; material breaks the symmetry (floor) | COL |
| a copious narrow resonance | per-channel peak iteration | enough entries per channel; S/B | coupled channels converge slowly; background shape biases the peak | COL |
| tracks with a momentum measurement | `E/p` | track momentum scale known; isolation checked against the cone | bremsstrahlung; neutral energy in the hadron cone | COL |
| MIP (muons, protons, nuclei) | MPV equalization, path-length corrected | MIP selection (cutoff, beam, cosmics) | mean instead of MPV; thickness dependence | COL, FXT, SPC, UGD |
| a source moved through the volume, or a radioactive gas | source scan; 83mKr | access to the volume | electronics and gas or light-yield gain mixed without a pulser or charge injection | COL |
| an absolute scale from a beam | transfer by source response or calibration detector | identical method in both setups | environment differences (field, temperature, source decay) | COL, UGD |
| two-ended bars | cosmic `t_L - t_R`, `ln(A_L/A_R)`; laser walk scan | track or position reference; walk corrected first | walk form near threshold; non-exponential attenuation | FXT, SPC, UGD |
| RICH optics | `dtheta_C(phi)` or ring-centre offsets; index from high-p tracks | tracks; unique mirror assignment | photons with two mirror pairs; index drift with temperature and pressure | COL, FXT |
| no test beam | muon rings, sky references | known muon emission | atmosphere-dependent throughput | GND |

Sourced in one environment only: minimum-bias symmetry, diphoton resonances and electron `E/p` (COL;
the last two need a diphoton rate or a momentum measurement, not a collider), muon rings (GND), and source scans,
radioactive gas, gas-gain equalization and the refractive index from data (COL; the FXT gas-chamber source is a
test-beam whole-chain equalization, astro-ph/0608641 sec. 4.2).

## Distinctive but generalizable features

- **Topology:** many channels, each seen by a subset of the entries; coupled through shared entries.
- **Inverse problem:** solve `c_k` from residuals; degenerate along unconstrained modes (gauges, symmetry classes,
  weak modes).
- **Natural objects:** per-channel peaks (mass, MPV, line), per-element residuals, per-bar time differences.
- **Informative residual:** versus the coordinates a mode would bend (azimuth, charge, time, position).
- **Scaling:** precision about `1/sqrt(N_k)` per channel until a systematic floor.
- **Conventions:** constants with mean one per class; the absolute scale set separately.
- **Tails:** background under the peak, wrong mirror or channel assignment, entries near threshold.
- **Dependence:** temperature, pressure, gas density, radiation, time; constants are per period.
- **Data sample:** the strongest reference per environment (resonances COL; nuclei by cutoff SPC; cosmic muons UGD
  and FXT; muon rings GND).
- **Transfers:** formulation, solvers and mode analysis transfer to any detector; minimum-bias symmetry, W and Z
  were sourced only in COL; pi0 and eta need a hadronic flux, not a collider.

## Common misconceptions and failure modes

- **A converged solution taken as a correct one.** Convergence is numerical; modes and biases survive it.
- **Iterating residual corrections to remove a bias.** It removes residuals, not the bias.
- **A symmetry method used as an absolute calibration.** It fixes constants within a symmetry class only.
- **Electronics and gas or light-yield gains mixed.** Separate them with a pulser or charge injection when the two vary
  independently in time; a muon equalization of the whole chain is fine when called that, repeated before the gains
  drift apart beyond the target precision (drift quoted), with the gas-density (or temperature) dependence corrected
  separately.
- **One reference sample per instance.** A second sample with different systematics is the strongest check; two
  methods on one sample (as in RICH) are not two samples.

## Deliverables

- The unknowns, their order in the chain, and the reference sample per constant, with at least two samples per
  instance.
- The solver, its convergence criterion (fixed before solving) and the number of iterations used.
- The unconstrained modes and the external constraint applied to each.
- Per-channel precision (statistical and systematic floor), per channel class and per period.
- The channel-by-channel comparison of independent methods, and the absolute-scale anchor with its range.

## Tool hooks

No script implements these solvers yet. A tool takes per-channel peaks (or residual sums) with uncertainties and
entries, the channel classes, the reference value, the chain position, the target precision per class, and the minimum
entries per channel and the convergence criterion, both fixed before solving; it returns `c_k` with statistical
uncertainties and the systematic floor (or the status `floor-not-estimated`), the per-class scale factor with its
uncertainty (absolute reference only), the period, the iteration count and the unconstrained modes. Gains are
dimensionless, mean one per class; offsets take the measured quantity's unit. **Negative controls,** before
normalisation: (a) relative reference (a symmetry class, time differences): inject a per-channel pattern plus a
different scale or shift per class; the tool recovers the pattern and reports each class mode as `unconstrained-mode`,
not fitted; (b) absolute reference (a resonance mass, a known `x_ref`): an injected common scale is recovered in the
returned scale factor, with pulls compatible with N(0, 1) over toys and an uncertainty below the declared target
precision. Statuses form a set: `converged` or `not-converged`, plus `unconstrained-mode` (naming the mode),
`insufficient-entries` (naming the channels below the minimum, left out of `c_k` and counted per class), and
`floor-not-estimated` (precision deliverable not met); `converged` is not allowed alone while a mode is free, nor
without the stopping check above (gradient norm, or largest offset per uncertainty). Stability across periods:
`stability_monitor.py` ([calibration and alignment](calibration-and-alignment.md#monitoring-stability-over-time)).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| general formulation | arxiv_1306.2016 | arxiv_1207.4210 (test beam) | arxiv_0904.2226 | arxiv_0805.3170 | pdg_2025_particle-detectors-for-non-accelerator-physics | gap |
| solvers | arxiv_hep-ex_0208021, arxiv_1403.2286 | arxiv_2011.12730 (test beam) | arxiv_1712.02739, arxiv_0904.2226 | gap | gap | gap |
| unconstrained modes | arxiv_hep-ex_0208021, arxiv_2007.07624, arxiv_0911.4022, arxiv_1306.2016 | arxiv_2011.12730 (test beam; gauge fixing only) | arxiv_0904.2226 (gauge fixing only) | gap | gap | gap |
| convergence, bias, precision | arxiv_hep-ex_0208021, arxiv_1306.2016 | arxiv_astro-ph_0608641 (test beam; per-channel precision only) | arxiv_0904.2226, arxiv_1712.02739 | gap | gap | gap |
| ECAL | arxiv_1306.2016 | gap | arxiv_1901.00734, arxiv_0904.2226 | gap | gap (no source read); IACT optical throughput (muon rings): [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md) | gap |
| HCAL | arxiv_1203.1302, arxiv_1806.02129 | arxiv_1207.4210 (test beam) | gap | arxiv_0805.3170 | gap (no source read) | gap |
| TOF and timing | gap (accelerator clock, unsourced in [timing detectors](timing-detectors.md#calibration-and-diagnostics)) | arxiv_2004.10339 | arxiv_0904.2226 | arxiv_1307.0162, pdg_2025_particle-detectors-for-non-accelerator-physics | [timing detectors](timing-detectors.md#calibration-and-diagnostics) (hybrid synchronisation) | gap |
| gas gain | arxiv_1709.02743, arxiv_nucl-ex_0101013 | gap (test beam only: arxiv_astro-ph_0608641, whole-chain equalization) | gap | gap | gap (gas chambers exist; no source read) | gap |
| RICH | arxiv_1211.6759 | arxiv_1809.04026 | gap | gap | gap (no source read) | gap |
| alignment, momentum scale | [in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md) | same | same | same | same | gap |

Cells marked (test beam) rest on beam tests, coded FXT; they do not show in-situ fixed-target use.

## Citations

Full entries for the sources cited inline are in the hep-detector [bibliography](detector-principles-bibliography.md)
and its split files (section "In-situ calibration and alignment"). Page numbers are PDF page indices of the version
read: arXiv v2, except v1 for arXiv:0904.2226, hep-ex/0208021, astro-ph/0608641, 1901.00734, 1203.1302, 2004.10339
and 1809.04026; for PDG RPP 2025, Particle detectors for non-accelerator physics (rev. October 2025), the PDF pages
equal its folios.

# In-Situ Calibration Methods

How detector constants (gains, scales, timing offsets, light speeds, attenuation lengths, positions) are solved for
from data: the unknowns, the reference sample, the residual, the solver, the modes the data cannot fix, and how
convergence, bias and per-channel precision are judged. Then the method per detector type, each with at least two
reference samples. Environments (R1 codes): COL, FXT, SPC, UGD, GND; NUC is a gap (no source read).

This page covers the solving. Chain order, test beam versus in-situ, weak modes of curvature, conditions and iteration
contracts are in [calibration and alignment](calibration-and-alignment.md) ([iterative
loops](calibration-and-alignment.md#iterative-loops-as-contract-steps)). Residual propagation: [calibration residual
propagation](calibration-residual-propagation.md). Charge injection and linearity: [front-end
calibration](front-end-calibration.md). Timing reference distribution: [timing
detectors](timing-detectors.md#calibration-and-diagnostics). Track and chamber alignment, and the momentum scale, are
in [in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md). Fitting *simulator* parameters to
data is simcal, owned by hep-statistics ([simcal
scripts](../../hep-statistics/references/core-stats-guide.md#skill-scripts)); this page is about detector constants
only.

## General formulation

Every in-situ calibration has three parts:

- **Unknowns.** Per-channel constants `c_k` (a multiplicative gain, an additive offset, a shape parameter), often an
  ordered chain of factors applied in sequence (arXiv:0805.3170, sec. 5, Eq. 1, p. 58). Each is derived with the
  corrections it depends on applied, not only earlier ones (sec. 5.2.2, p. 64: strip-to-strip after attenuation).
- **Reference sample.** Events whose expected response is known independently of `c_k`: a resonance mass, an
  ionization loss over a known path length (arXiv:0904.2226, sec. 5.2, pp. 20-21), a symmetry of the flux, a source
  line, a beam of known energy (FXT: the hadron-to-electron scale factor from pions of known beam energy;
  arXiv:1207.4210, sec. 2.3, p. 8), a track momentum. Where no test beam exists the atmosphere or the sky supplies it
  (GND: muon rings; PDG RPP 2025, Particle detectors for non-accelerator physics, sec. 36.2.2, p. 9).
- **Residual.** Measured minus expected response as a function of `c_k`, summed over the sample.

### Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | `Q_corr = Q_raw * F_1 * F_2 * ... * F_n` (drift, linearity, channel-to-channel, attenuation, absolute scale) | exact (definition) | applied in sequence; each derived with what it depends on applied (S after L, A); arXiv:0805.3170, sec. 5, Eq. 1, p. 58, and sec. 5.2.2, p. 64 |
| 2 | per-channel iteration `c_k <- c_k * x_ref / x_fit,k` (peak, mass or MPV fitted per channel) | approximate | quality depends on entries per channel and S/B (arXiv:1306.2016, sec. 4.2.2, p. 16); convergence needs weakly coupled channels (inference, not in the source) |
| 3 | `chi2(p, q) = sum_tracks sum_meas ((m_ij - f_ij(p, q_j)) / sigma_ij)^2`, global `p`, local `q_j` | exact (objective) | arXiv:1403.2286, sec. 4, Eq. 1, p. 9 |
| 4 | linearised normal equations `C a = b`, reduced to `C' dp = b'` by block algebra | exact for the linearised problem; iterate when corrections are not small | no information on `dp` is lost; arXiv:1403.2286, sec. 4, Eq. 2, pp. 9-10 |
| 5 | constraints `f^T a = f_0` by Lagrange multipliers: `[[C, f], [f^T, 0]] [a, lambda] = [b, f_0]` | exact (linear constraints) | solved directly, no initial values; arXiv:hep-ex/0208021, sec. 2, Eq. 9, p. 4 |
| 6 | constrained track term `chi2_cons` added per track (COL: beam spot; external detector; resonance mass) | exact (objective) | arXiv:2007.07624, sec. 3.2.4, Eq. 14, p. 10 |
| 7 | step halving when `chi2_next >= chi2_this - eps * abs(grad chi2) * abs(d)`, `eps` in [0, 1] | approximate (heuristic) | arXiv:1712.02739, sec. 5.2.1, Eq. 7, p. 7 |
| 8 | methods combined per channel, weighted by precision | approximate (inverse-variance weights assume independent methods) | arXiv:1306.2016, sec. 4.2, p. 14, and sec. 4.2.2, p. 16 |

## Solvers

- **Per-channel iteration** (relation 2): fit the reference peak in each channel, correct, repeat. It suits gains
  where one entry touches one or a few channels: in the cited diphoton method each candidate enters the channels on
  which its photons are centred (arXiv:1306.2016, sec. 4.2.2, p. 16).
- **Iterative residual corrections** for positions: correct each element from its mean residual, refit, repeat. The
  residuals shrink, but the fitted parameters stay biased, more so when repeated, because each local fit used a
  wrong model; correlated parameters (a position shift and a drift-velocity shift) cannot be separated
  (arXiv:hep-ex/0208021, sec. 1, p. 1).
- **Global linear least squares** (relations 3 to 5): all global and local parameters at once, with the local ones
  eliminated by block reduction (Millepede-type). It takes every correlation into account; the reduced system has
  the size of the global parameters only (arXiv:hep-ex/0208021, secs. 1-3, pp. 1-7; arXiv:1403.2286, sec. 4,
  pp. 9-10).
- **Global iterative minimisation** of the total `chi2` by gradient descent, all parameters at once, with step-size
  control (relation 7; SPC: arXiv:1712.02739, sec. 5.2, pp. 6-7). FXT telescopes offer both an iterative per-detector
  `chi2` minimisation and a Millepede-II fit (arXiv:2011.12730, sec. 3.5, p. 9).
- **Hierarchy and gauge.** Steps can be ordered, elements within a structure first (SPC; arXiv:0904.2226,
  secs. 10.1-10.2, pp. 41-44). The global frame is fixed by a reference element (FXT; arXiv:2011.12730, sec. 2.3.2,
  p. 6) or by zero mean shifts (SPC; arXiv:0904.2226, sec. 10.1, p. 44).

## Unconstrained modes and external constraints

A parameter combination that the residual does not change is undetermined: the matrix is singular or close to it,
which "could destroy the whole determination". With too many global parameters the whole detector shifts and
rotates freely; fix some parameters or impose constraints such as zero mean displacement and rotation
(arXiv:hep-ex/0208021, sec. 3, p. 7). Beyond these global gauges, weak modes are distortions that leave `chi2`
nearly unchanged yet bias the solution; they are controlled by constraints on track parameters from the beam spot,
external detectors or resonance masses (COL; arXiv:2007.07624, sec. 3.2.4, p. 10), and by non-track measurements
(photogrammetry, in-situ position sensors) of the degrees of freedom tracks hardly see (COL; arXiv:0911.4022, sec. 1,
p. 3). Gain calibrations have the same structure: a symmetry method fixes constants within a symmetry class only,
and the scale between classes and the absolute scale need another reference (arXiv:1306.2016, sec. 4.2, p. 14). The
curvature weak modes and their physics consequences are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes). The FXT source supports only
gauge fixing by a reference plane; it does not discuss `chi2`-invariant deformations.

## Convergence, bias and per-channel precision

- **Convergence criterion, declared in advance:** the largest parameter change between successive iterations below
  a threshold (arXiv:0904.2226, sec. 10.1, p. 44). Step-size control (relation 7) is not a stopping rule: with
  `eps = 0` the solver oscillates around the minimum and converges more slowly than with the reference `eps = 0.5`,
  with `eps = 1` the step shrinks after a few iterations and it does not converge (arXiv:1712.02739, sec. 5.2.1,
  pp. 7-8). A parameter-change threshold is met trivially once halving has collapsed the step: check the step size
  or gradient norm too. Converged means numerically stable, not correct.
- **Bias.** Iterating on biased residuals reduces the residuals, not the bias (arXiv:hep-ex/0208021, sec. 1, p. 1).
  A symmetry method reaches a systematic floor set by how well the symmetry holds (material in front of the
  detector), not by statistics; ratios of the same method over successive periods cancel much of it, so the method
  serves to monitor stability and to refine constants from other methods (arXiv:1306.2016, sec. 4.2.1, p. 15).
- **Per-channel precision** depends on the entries per channel and on the signal-to-background ratio of the
  reference peak (arXiv:1306.2016, sec. 4.2.2, p. 16; FXT, per straw from the number of muon hits:
  arXiv:astro-ph/0608641, sec. 4.2.2, p. 4); the statistical term falls roughly as `1/sqrt(N_k)` until the
  systematic floor (approximate). Quote both, per channel class, with the period needed to reach them.
- **Validation.** Methods with different systematics are compared channel by channel to validate their precision
  estimates, together with simulation and the pre-calibration (arXiv:1306.2016, sec. 4.2, p. 15); compare them
  before combining. Starting values and sets that enter the combination count as used in the derivation: a
  comparison against them tests consistency, not precision.

<!-- example: experiment-specific illustration (CMS ECAL, LHC pp at 7 TeV, 2011; arXiv:1306.2016) -->
CMS ECAL intercalibration: phi-symmetry with about 10^8 events is limited by a systematic 1.5% in the central
barrel, above 3% at larger |eta|, while week-to-week ratios reach 0.3% (sec. 4.2.1, p. 15); pi0/eta reaches 0.5-1%
per month in the barrel and 2-4% every 2-3 months in the endcaps (sec. 4.2.2, p. 16). Fermi LAT on-orbit tracker
alignment stops when no parameter moves by more than 0.01 um (1 urad), typically after 100 iterations
(arXiv:0904.2226, sec. 10.1, p. 44).
<!-- /example -->

## Instances by detector type

### Electromagnetic calorimeters

- **Symmetry of the flux** (COL): equal deposited transverse energy for channels at the same pseudorapidity in
  minimum-bias events; intercalibrates within a ring (arXiv:1306.2016, sec. 4.2, p. 14).
- **Diphoton resonances** pi0 and eta (COL), per-channel iteration (relation 2) (sec. 4.2.2, p. 16).
- **`E/p` of isolated electrons** (COL: from W and Z decays), within and between rings (sec. 4.2.3, pp. 16-17).
- **Absolute scale** from a dielectron resonance (COL: Z), to which the intercalibrations are referred (sec. 4.2,
  p. 14).
- **Minimum-ionizing particles**: on the ground cosmic muons and beam particles; in orbit only MIP protons or light
  ions, selected through the geomagnetic cutoff where the proton spectrum is known (SPC; arXiv:1901.00734, sec.
  IV.D, p. 5). Path-length-corrected ionization peaks of protons and nuclei, with charge injection for the
  electronics, calibrate each crystal; a cross-range calibration links low- and high-gain ranges
  (SPC; arXiv:0904.2226, sec. 5.2, p. 21). Use the most probable value; see
  [calibration standards](calibration-and-alignment.md#calibration-standards-and-their-pitfalls).
- **Pre-calibration** from laboratory, beam-test and cosmic-ray data is the starting point (arXiv:1306.2016, sec. 4.2,
  p. 14).

### Hadronic calorimeters

- **Single-hadron `E/p`** of isolated tracks (COL; arXiv:1203.1302, sec. 1, p. 2); the isolation cut biases it
  ([calibration standards](calibration-and-alignment.md#calibration-standards-and-their-pitfalls)).
- **MIP equalization** with muons, cell to cell, then the MIP as the base unit (FXT; arXiv:1207.4210, sec. 2.2,
  p. 6) and electrons for the MIP-to-GeV step (sec. 2.3, p. 8); cosmic-muon strip-to-strip equalization (UGD;
  arXiv:0805.3170, sec. 5, p. 58); in a running detector, cosmic and collision muons probe the response per cell
  (COL; arXiv:1806.02129, sec. 6.1, pp. 30-31).
- **Radioactive source scans** moved through the calorimeter, per channel (COL only in the sources read;
  arXiv:1806.02129, sec. 4.1, p. 19).
- **Transfer of a test-beam scale**: set the source response equal to the one seen in the beam test, correcting for
  source activity and decay (COL; arXiv:1806.02129, sec. 4.1, p. 19), or carry it through a calibration detector
  exposed to beams and equalized with the same cosmic-muon method (UGD; arXiv:0805.3170, sec. 5, p. 58).

### Time-of-flight and timing

Constants per channel: `t0`, walk, effective light speed, attenuation length.

- **Walk** `t - t_ref = alpha + beta / sqrt(A)` from a laser with a variable attenuator; the form underestimates the
  walk near threshold, where the source drops the (background-dominated) hits; residuals at higher pulse heights are
  corrected iteratively with the same form (FXT; arXiv:2004.10339v1, sec. 3.1.3, Eq. 2, p. 10). A
  per-channel time-versus-charge map from a laser diffuser carries the offset and the walk together (UGD;
  arXiv:1307.0162, sec. 3.1.8, pp. 25-26).
- **Effective light speed and left-right offset** of a bar read at both ends from cosmic rays:
  `t_L - t_R = -2x/v`, bounded by `+-L/v` (exact for a uniform bar), so the width gives `v` and the centre the offset
  (FXT; arXiv:2004.10339v1, sec. 3.1.4, Eq. 3, p. 10).
- **Attenuation length** from `ln(A_L/A_R) = 2x/mu = -v (t_L - t_R)/mu` (approximate: one exponential length;
  arXiv:2004.10339v1, sec. 3.1.5, Eq. 4, p. 11). In SPC the two-end light asymmetry is calibrated on the ground with
  cosmic muons and again in orbit with cosmic nuclei against the extrapolated track position
  (arXiv:0904.2226, sec. 5.3, pp. 24-25).
- **Large volumes** (UGD): synchronisation signals plus LED or laser flashers at known times (PDG RPP 2025,
  sec. 36.3.2, p. 20); see [timing detectors](timing-detectors.md#calibration-and-diagnostics).

### Gas gain equalization

- **Radioactive gas** (83mKr) spread through the chambers; the decay-electron signal, comparable to a MIP's
  deposit, calibrates pad by pad, in a TRD and a TPC (COL; arXiv:1709.02743, sec. 10.2, p. 43). A pulser separates
  the electronics gain from the gas gain, which varies with field and geometry (COL; arXiv:nucl-ex/0101013,
  sec. 1.1, p. 2).
- **MIP pulse height** per straw from muons, plus the gain dependence on gas density, measured on the same muons
  and used to normalise runs to standard temperature and pressure; an X-ray source line sets the energy scale
  (FXT, a beam test; arXiv:astro-ph/0608641, secs. 4.2.2-4.2.4, p. 4). The per-straw factors there are mostly
  preamplifier gain, the gas-gain part being small (sec. 4.2.2, p. 4), so this equalizes the whole chain; it is not
  a gas-gain equalization on its own.
- MRPC and muon-chamber gain equalization: not sourced (gap); no procedure is stated.

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
- **Refractive index** from high-momentum tracks, tuned so that `dtheta_C` peaks at zero; a gas radiator drifts with
  temperature, pressure and composition (COL only in the sources read; arXiv:1211.6759, sec. 3.4, p. 12).

### Alignment and momentum scale

Track and chamber alignment (Millepede-II, General Broken Lines, iterative `chi2`) and the momentum scale:
[in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| many channels, a flux symmetric in one coordinate | symmetry equalization | symmetry holds to the target precision, or (monitoring by ratios) its breaking is stable between periods; rate | fixes within a class only; material breaks the symmetry (floor) | COL |
| a copious narrow resonance | per-channel peak iteration | enough entries per channel; S/B | coupled channels converge slowly; background shape biases the peak | COL |
| tracks with a momentum measurement | `E/p` | track momentum scale known; isolation | bremsstrahlung; the isolation cut biases hadron `E/p` | COL |
| MIP (muons, protons, nuclei) | MPV equalization, path-length corrected | MIP selection (cutoff, beam, cosmics) | mean instead of MPV; thickness dependence | COL, FXT, SPC, UGD |
| a radioactive source or gas | source scan; 83mKr | access to the volume | electronics and gas gain mixed without a pulser | COL, FXT |
| an absolute scale from a beam | transfer by source response or calibration detector | identical method in both setups | environment differences (field, temperature, source decay) | COL, UGD |
| two-ended bars | cosmic `t_L - t_R`, `ln(A_L/A_R)`; laser walk scan | track or position reference | walk form near threshold; non-exponential attenuation | FXT, SPC, UGD |
| RICH optics | `dtheta_C(phi)` or ring-centre offsets; index from high-p tracks | tracks; unique mirror assignment | photons with two mirror pairs; index drift with temperature and pressure | COL, FXT |
| no test beam | muon rings, sky references | known muon emission | atmosphere-dependent throughput | GND |

Sourced in one environment only: minimum-bias symmetry equalization (COL), diphoton resonances and electron `E/p`
(COL; they need a diphoton rate or a momentum measurement, not a collider), muon rings (GND), and source scans,
radioactive gas and the refractive index from data (COL). Environment-specific references: [space-based direct
detection](space-based-direct-detection.md), [neutrino astronomy](neutrino-astronomy.md), [noble-liquid, neutrino and
rare-event detectors](noble-liquid-neutrino-and-rare-event-detectors.md), [imaging atmospheric
Cherenkov](imaging-atmospheric-cherenkov.md).

## Distinctive but generalizable features

- **Topology:** many channels, each seen by a subset of the reference entries; coupling through shared entries.
- **Inverse problem:** solve `c_k` from residuals; degenerate along unconstrained modes (gauges, symmetry classes,
  weak modes).
- **Natural objects:** per-channel peaks (mass, MPV, line), per-element residuals, per-bar time differences.
- **Informative residual:** the reference residual versus the coordinates a mode would bend (pseudorapidity,
  azimuth, charge, time, position along a bar).
- **Scaling:** statistical precision about `1/sqrt(N_k)` per channel until a systematic floor.
- **Conventions:** constants normalised to a mean of one within a class; the absolute scale set separately.
- **Tails:** background under the peak, wrong mirror or channel assignment, entries near threshold.
- **Dependence:** temperature, pressure, gas density, radiation, time; constants are per period.
- **Data sample:** the strongest reference available per environment (resonances COL; nuclei by cutoff SPC; cosmic
  muons UGD and FXT; muon rings GND).
- **Transfers:** the formulation, solvers and mode analysis transfer to any detector; the collider references
  (minimum-bias symmetry, W, Z) were sourced in COL only; pi0 needs a hadronic flux, not a collider.

## Common misconceptions and failure modes

- **A converged solution taken as a correct one.** Convergence is numerical; modes and biases survive it.
- **Iterating residual corrections to remove a bias.** It removes residuals, not the bias.
- **A symmetry method used as an absolute calibration.** It fixes constants within a symmetry class only.
- **Electronics and gas or light-yield gains mixed.** Separate them with a pulser or charge injection when the two
  vary independently in time; a muon equalization of the whole chain is fine when called that.
- **One reference sample per instance.** A second sample with different systematics is the strongest check; two
  methods on the same sample do not count as two samples.
- **Collider references stated as general.** Pseudorapidity rings, W and Z samples and minimum-bias symmetry are COL.

## Deliverables

- The unknowns, their order in the chain, and the reference sample per constant, with at least two samples per
  instance.
- The solver, its convergence criterion (fixed before solving) and the number of iterations used.
- The unconstrained modes and the external constraint applied to each.
- Per-channel precision (statistical and systematic floor), per channel class and per period.
- The channel-by-channel comparison of independent methods, and the absolute-scale anchor with its range.

## Tool hooks

No script implements these solvers yet. A tool built on this page takes per-channel peak positions (or residual sums)
with uncertainties and entries, the reference value, the chain position and the declared convergence criterion; it
returns `c_k` with statistical uncertainties and the systematic floor (or `floor-not-estimated`), the period, the
iteration count, and the list of unconstrained modes. Units: gains dimensionless and normalised to a mean of one per
class; offsets in the unit of the measured quantity. **Negative controls,** run before normalisation: (a) relative
reference (a symmetry class, time differences): inject a per-channel pattern plus a common scale or shift; the tool
recovers the pattern and reports the common mode as `unconstrained-mode`, not fitted; (b) absolute reference (a
resonance mass, a known `x_ref`): an injected common scale is recovered within its uncertainty. Statuses form a set:
`converged` or `not-converged`, plus `unconstrained-mode` (naming the mode) and `insufficient-entries` (below a stated
minimum per channel); `converged` alone is not allowed while a mode is free. Stability across periods:
`stability_monitor.py` ([calibration and alignment](calibration-and-alignment.md#monitoring-stability-over-time)).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| general formulation | arxiv_1306.2016 | arxiv_1207.4210 | arxiv_0904.2226 | arxiv_0805.3170 | pdg_2025_particle-detectors-for-non-accelerator-physics | gap |
| solvers | arxiv_hep-ex_0208021, arxiv_1403.2286 | arxiv_2011.12730 | arxiv_1712.02739 | gap | gap | gap |
| unconstrained modes | arxiv_hep-ex_0208021, arxiv_2007.07624 | arxiv_2011.12730 (gauge only) | gap | gap | gap | gap |
| convergence, bias, precision | arxiv_hep-ex_0208021, arxiv_1306.2016 | arxiv_astro-ph_0608641 (per-channel precision only) | arxiv_0904.2226, arxiv_1712.02739 | gap | gap | gap |
| ECAL | arxiv_1306.2016 | gap | arxiv_1901.00734, arxiv_0904.2226 | gap | n/a: no ECAL; the IACT optical-throughput calibration with muon rings is in [imaging atmospheric Cherenkov](imaging-atmospheric-cherenkov.md) | gap |
| HCAL | arxiv_1203.1302, arxiv_1806.02129 | arxiv_1207.4210 | gap | arxiv_0805.3170 | gap (no source read) | gap |
| TOF and timing | [timing detectors](timing-detectors.md#calibration-and-diagnostics) | arxiv_2004.10339 | arxiv_0904.2226 | arxiv_1307.0162, pdg_2025_particle-detectors-for-non-accelerator-physics | [timing detectors](timing-detectors.md#calibration-and-diagnostics) (hybrid synchronisation) | gap |
| gas gain | arxiv_1709.02743, arxiv_nucl-ex_0101013 | arxiv_astro-ph_0608641 (test beam; electronics plus gas gain) | gap | gap | gap (no source read) | gap |
| RICH | arxiv_1211.6759 | arxiv_1809.04026 | gap | gap | gap (no source read) | gap |
| alignment, momentum scale | [in-situ alignment and momentum scale](in-situ-alignment-and-momentum-scale.md) | same | same | same | same | gap |

## Citations

Full entries are in the hep-detector [bibliography](detector-principles-bibliography.md) and its split files (section
"In-situ calibration and alignment"). Page numbers are PDF page indices of the arXiv version read (printed folios can
differ). Sources (the arXiv version was read where paywalled): arXiv:1306.2016, arXiv:0904.2226,
arXiv:0805.3170, arXiv:hep-ex/0208021 (preprint), arXiv:1403.2286, arXiv:1712.02739, arXiv:2011.12730,
arXiv:2007.07624, arXiv:0911.4022, arXiv:astro-ph/0608641, arXiv:1901.00734, arXiv:1203.1302, arXiv:1806.02129,
arXiv:1207.4210, arXiv:2004.10339, arXiv:1307.0162, arXiv:1709.02743, arXiv:nucl-ex/0101013 (preprint),
arXiv:1211.6759, arXiv:1809.04026; PDG RPP 2025, Particle detectors for non-accelerator physics.

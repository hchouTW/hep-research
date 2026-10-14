# Performance Metrics, Acceptance/Efficiency/Resolution, and Residual Diagnostics

Rigorous definitions for every quantity quoted in a detector-performance result, and
the residual/pull toolkit that tests whether a model and its uncertainties are right.
It sharpens [reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md) (truth matching,
efficiency, fake rate) and [detector systems overview](detector-systems-overview.md) (resolution vocabulary)
and supplies the statistics of [histograms efficiencies](../../hep-analysis/references/histograms-efficiencies.md). Every metric below
requires: an equation, numerator, denominator, conditioning, matching rule, phase space,
object or event level, estimator, and uncertainty. If one is missing, the number is not
comparable.

## Metric definitions

| Metric | Definition (numerator / denominator) | Condition, matching | Estimator, uncertainty | Common misuse |
|---|---|---|---|---|
| Geometric/kinematic acceptance `A` | truth in fiducial geometry and phase space / generated in the reference phase space | truth only; no detector response | ratio of counts or integral of a flux over geometry ([detector systems overview](detector-systems-overview.md)) | using it as "efficiency"; changing the reference phase space between MC and data |
| Reconstructibility | truth objects that leave the minimum information needed (e.g. `>= n` hits) / truth in acceptance | truth-level definition of "could be found" | count ratio | denominator differs between experiments |
| Hit efficiency | hit found where expected / tracks crossing active area (from other layers) | unbiased track prediction (excluding the layer) | binomial (Clopper-Pearson) | biasing by requiring the hit in the track fit |
| Reconstruction efficiency `eps_R` | reconstructed and matched / eligible truth (in acceptance) | matching criterion stated | binomial | denominator not the fiducial one |
| ID / selection efficiency `eps_S` | pass / reconstructed (matched) objects | stated matching and phase space | binomial | applying a probe-derived value to a different population |
| Trigger efficiency | fired / offline-selected sample | independent reference trigger | binomial per bin (turn-on) | biased reference sample |
| Purity `P` | matched true with correct identity / selected | selected sample; matching rule | binomial or ratio of weighted counts | quoted as `1 - fake` when other categories exist |
| Fake rate | selected (or reconstructed) objects with no truth match / selected (object-level) *or* / eligible candidates (per-candidate) | say which | ratio | confusing with mis-ID |
| Mis-ID rate `m_{a->b}` | true species `a` identified as `b` / eligible true `a` | truth species; all categories | binomial | confusing with fake; mixing denominators |
| Duplicate rate | truth matched by `>= 2` objects / matched truth (an alternative counts objects beyond the first per truth / generated truth; say which) | one-to-many rule | ratio | not removed by ambiguity resolution |
| Response / scale | `<x_reco/x_true>` (or median) at fixed truth | binned in *truth*, not reco | mean/median, `+-` standard error | binning in reco (selection bias) |
| Bias | `<x_reco - x_true>` | as above | as above | mixing bias with core width |
| Resolution | width of `x_reco - x_true` (or `/x_true`, or `1/pT` form) | binned in truth; state definition | core Gaussian `sigma`, `RMS`, robust `1.4826*MAD`, `sigma_68`; `+-` statistical | quoting RMS of a heavy-tailed shape |
| Tail / catastrophic fraction | `|r| > k*sigma_core` / population | `k` and definition stated | binomial | not reported next to core width |
| PID efficiency & rejection | `epsilon_sig`, `1/epsilon_bkg` at a working point | truth species, phase space | binomial; ROC/AUC | quoting rejection without the signal efficiency |
| Separation `N_sigma` | `|mu_a-mu_b| / sigma_a` (single-measurement, default) or `|mu_a-mu_b| / sqrt(sigma_a^2+sigma_b^2)` (quadrature); see below | Gaussian shapes (approximate); convention stated | from fits | mixing conventions (a factor `sqrt(2)`); applied to non-Gaussian tails ([particle identification](particle-identification.md)) |
| Confusion matrix | `M_{ab} = P(ID=b | true=a)` rows normalized by truth | eligible truth per row | counts | wrong normalization axis |
| Effective area / volume, exposure, containment, PSF | point source: `A_eff = A_gen N_pass/N_gen` (m^2), exposure `sum_t A_eff T_live,t`; diffuse flux: acceptance `G = A_gen Omega_gen N_pass/N_gen` (m^2 sr), `Omega_gen = pi` for directions generated with a cosine law through the generation surface, exposure `sum_t G T_live,t`; never multiply a `G` that already integrates direction by a solid angle again | as defined for astroparticle | ratio/MC | quoting without energy/angle dependence ([space based direct detection](space-based-direct-detection.md), [astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md)) |

Object-level versus event-level: a per-object probability `p` with `k` independent
objects per event gives an event-level probability `1 - (1-p)^k` for "at least one";
they are not interchangeable, and correlations (shared pileup, shared alignment)
break independence, so measure the event-level quantity directly.

**Separation `N_sigma`: two conventions.** This file is the single definition used by
the detector-response references. *Single-measurement* (the default of the
detector-response scripts and the usual TOF, RICH and `dE/dx` convention):
`N_sigma = |mu_a - mu_b| / sigma_a`, the distance between the two hypotheses' means in
units of the resolution of one measurement (`sigma_a`, or the common `sigma` when the
widths are equal). *Quadrature*: `N_sigma = |mu_a - mu_b| / sqrt(sigma_a^2 + sigma_b^2)`.
For equal widths the quadrature value is the single-measurement value divided by
`sqrt(2)`. State which convention a number uses; both assume Gaussian shapes and say
nothing about tails or few-photon distributions.

**Width estimators.** For a residual distribution with `N` entries:
- *RMS vs std*: `RMS = sqrt(<r^2>)` includes the bias; the standard deviation
  `sqrt(<(r - <r>)^2>)` does not (`RMS^2 = std^2 + <r>^2`). Some tools label the
  standard deviation "RMS"; say which. Both are dominated by tails.
- *`sigma_68`*: half the width of the interval containing 68.27% of the entries
  (central, or smallest; say which); equals `sigma` for a Gaussian.
- *`IQR/1.349`*: interquartile range scaled to equal `sigma` for a Gaussian.
- *`1.4826 * MAD`*: median absolute deviation from the median, scaled to equal `sigma`
  for a Gaussian.
The last three are robust to a small tail fraction but are not equal to each other for
non-Gaussian shapes; quote the estimator with the number.

**Why fake rate is not universally `1 - P`.** `P = N_matched/N_selected`, so
`1 - P` = (unmatched + matched-but-wrong-identity) / selected. A *fake* is a selected
object with no valid truth counterpart (reconstruction failure); a *mis-ID* is a real
particle with the wrong species. `1-P` mixes both plus duplicates. Also fake rate is
often defined per eligible candidate, not per selected object, so its denominator
differs.

**Efficiency uncertainty.** Binomial, not Gaussian near 0 or 1: use exact
Clopper-Pearson (`<plugin root>/skills/detector-response/scripts/tag_and_probe_efficiency.py`; conservative, it over-covers) or Wilson or Jeffreys intervals (not implemented in this skill's scripts).
With weighted events, use effective counts `N_eff = (sum w)^2 / sum w^2`, and note
correlated numerator/denominator when the pass sample is a subset. Rate-like counts
without a denominator (dark counts, backgrounds) are Poisson.

## Acceptance, efficiency, resolution: the dedicated distinction

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

### Worked numerical example

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

Selected sample: 6660 objects pass the ID cut, composed of 6480 true electrons (matched
with correct identity), 60 real pions (matched, wrong species: *mis-ID*), and 120 with
no truth match (*fakes*): `6480 + 60 + 120 = 6660` (the 6480 true electrons that pass ID are all correctly identified).
- Purity (correct identity) `P = 6480/6660 = 0.973`.
- Fake rate `= 120/6660 = 0.0180`; mis-ID share `= 60/6660 = 0.0090`. Here `1 - P = 0.0270` = fake +
  mis-ID, *not* the fake rate alone.
- The pion mis-ID *rate* as a property of pions needs the eligible pion count as the
  denominator (e.g. 60 of 12000 pions = 0.005), a different number from `0.0090`.

Resolution/bias of a relative energy residual `r = (E_reco - E_true)/E_true` (%) for
20 matched electrons in one truth bin: values
`-1.2, 0.5, 0.1, -0.4, 1.1, 0.3, -0.2, 0.8, -0.6, 0.4, -0.9, 0.2, 0.0, -0.3, 0.7, 6.5,
-0.5, 0.6, -0.1, 0.9`.
- Mean `= 0.395%`, standard deviation `= 1.56%` (n-1; RMS `sqrt(<r^2>) = 1.57%`), median `= 0.15%`,
  `1.4826*MAD = 0.74%`.
- One catastrophic entry (`6.5%`): tail fraction `|r| > 3% = 1/20 = 5%`.
- Removing it: mean `0.074%`, standard deviation `0.63%` (RMS `0.62%`). The mean and width were dominated by a single
  tail event; the core (`~0.6-0.7%`, bias `~0.1%`) is the detector; the 5% tail is a
  separate quantity. Quote `bias(core)`, `sigma(core)`, and tail fraction, never one
  number. (With 20 entries all of these have large statistical uncertainty; a real
  performance table needs far more.)

## Residuals, pulls, and their covariance

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
files ([gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md),
[timing detectors](timing-detectors.md), [muon systems](muon-systems.md), [cherenkov imaging variants and photosensors](cherenkov-imaging-variants-and-photosensors.md)).

**Coverage.** A `k`-sigma interval should contain the truth at the nominal
probability (68.3% for `k=1`, Gaussian). Coverage is tested on *truth* in simulation or
with a redundant measurement in data. *Narrow residuals do not prove correct
pulls or coverage*: an estimator can be precise but overconfident (uncertainties too
small), or accurate on the core while its tails are ignored. Test the pull width, the
tail fraction, and coverage across phase space, not just the core width.

## Estimators and pitfalls

- **Core vs full width**: Gaussian core fit, `sigma_68`, `IQR/1.349`, robust
  `1.4826 MAD`, and RMS (definitions above) answer different questions; RMS is
  dominated by tails, core fit by the fit range.
- **Binning on reconstructed values** sculpts the distribution; bin in truth.
- **Weighted samples**: uncertainties via `sum w^2`; effective statistics.
- **Detector resolution vs unfolding regularization.** Detector resolution is a property
  of the measurement; regularization is a choice in the inversion that smooths the
  result and introduces bias; they are separate widths and must not be conflated
  ([response and forward folding](response-and-forward-folding.md)). The response matrix
  `n_i^reco = sum_j R_ij n_j^truth + b_i` encodes migration (resolution and scale, off-diagonal),
  the inefficiency when it is declared inside the matrix (truth-bin sums `< 1`; they equal 1 under
  `conditional_on_selected`), and background `b_i`; model dependence enters through
  the truth spectrum used to build `R` ([data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md)).

## Common misconceptions and failure modes

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

## Deliverables

- For every quoted metric: numerator, denominator, conditioning, matching rule, phase
  space, level (object/event), estimator, and uncertainty.
- Efficiency with exact binomial intervals; resolution as core, tail fraction, and
  definition; bias in truth bins.
- Pull mean and width with the covariance used; coverage on an independent sample.
- The factorization used and a check that it is valid (or the direct total measurement).

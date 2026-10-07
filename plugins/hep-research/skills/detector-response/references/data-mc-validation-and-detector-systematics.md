# Data/MC Validation, Detector Systematics Propagation, and Detector Combination

The last arrows of the [chain](detector-measurement-framework.md): data/MC
validation, systematic uncertainties, and the physics-observable bias; then combining
detectors. It applies the general machinery of [systematics](../../hep-analysis/references/systematics.md) (variations,
correlations), [analysis validation](../../hep-analysis/references/analysis-validation.md) (validation), [reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md)
(scale factors), [detector simulation](detector-simulation.md) (simulation chain) and
[response and forward folding](response-and-forward-folding.md) (response matrices) to detector effects specifically.

## The simulation chain and its four truth levels

Generation -> transport (Geant4) -> energy deposits -> digitization -> noise/pileup
overlay -> trigger -> reconstruction ([detector simulation](detector-simulation.md)). Four distinct
levels exist: *generator truth*, *simulation truth* (deposits, true trajectories),
*digitized signals*, *reconstructed objects*. Only the last two exist in data. Truth
matching, "true" efficiencies, and response definitions are simulation-only;
data-accessible proxies must stand in.

## Data/MC comparison: what to compare

Compare **normalization, shape, conditional distributions, correlations, efficiencies,
tails, and time dependence**. One-dimensional agreement is *never* sufficient: two
marginals can agree while the joint distribution (e.g. `pT` versus `eta`, hit
multiplicity versus occupancy) differs, and an agreeing marginal can hide compensating
errors. Compare in the variables that carry the physics: efficiency and resolution
**conditional on** kinematics, occupancy/pileup, and detector region; correlations between
two observables; the tails (log scale); and per-run/per-period stability. Prefer
validation in independent samples distinct from those used to tune the simulation.

## Control samples and data-driven methods

- **Control / validation / signal regions**: tune in control, check in validation,
  measure in signal; keep them disjoint ([backgrounds](../../hep-analysis/references/backgrounds.md)).
- **Closure**: apply the method to simulation where truth is known and recover the
  input within uncertainty; non-closure is a quoted systematic, not something to tune away.
- **Tag-and-probe**: a resonance (`Z`, `J/psi`, `K_s`, `Lambda`) supplies a *tag* with tight
  selection and an unbiased *probe*; efficiency = probes passing / probes, from a
  background-subtracted sample (sideband or fit); biases from tag-probe correlation and
  background shape ([triggers luminosity pileup](triggers-luminosity-pileup.md)).
- **Standard candles and independent samples**: mono-energetic peaks (`pi^0`, `Z` line,
  Michel electrons, calibration lines), cosmic muons, redundancy of independent
  subdetectors (a tracker efficiency from the calorimeter or from an alternative
  tracking path), sidebands, and resampling (bootstrap, split-sample) for data-driven
  uncertainties.
- **Truth-matching proxies in data**: redundancy, kinematic constraints, and
  mass/opening-angle closure; state the proxy's own bias.

## Scale factors and reweighting

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

## Systematic uncertainties: sources and mapping

| Detector nuisance | Affects (reconstructed) | Propagates to (physics) | Typical model |
|---|---|---|---|
| Momentum/energy scale | `pT`, mass, `E` | resonance mass, cross section slope | shift + re-select; correlated |
| Resolution | widths, tails, migration | response matrix, mass width, cuts | smearing variation |
| Efficiency (reco/ID/trigger) | yields, acceptance | cross section normalization | `SF` up/down per bin |
| Alignment / field | `q/p` (charge-dependent), `d0`, angles | charge asymmetry, mass vs `eta` | alternative geometry (weak modes) |
| Material | conversions, scattering, showers | efficiency, `E` scale, isolation | material-variation simulation |
| Time / conditions drift | scale, timing, gain | time-dependent bias | run-period split |
| Noise / pileup | thresholds, clusters, `MET`, jets | jets, isolation | overlay variation ([triggers luminosity pileup](triggers-luminosity-pileup.md)) |
| Dead channels / masks | efficiency holes | acceptance | conditions variation |
| Mis-ID / fakes | backgrounds | signal contamination | data-driven fake rate |
| Trigger | efficiency turn-on | normalization | turn-on curve variation |
| Response matrix / model | unfolded spectrum | shape | alternative model (see [response and forward folding](response-and-forward-folding.md)) |
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
([likelihood fitting](../../hep-statistics/references/likelihood-fitting.md), [inference recipes](../../hep-statistics/references/inference-recipes.md)).

**Full chain for a detector nuisance.** Modify the condition or object -> **rerun the
affected reconstruction** (not just the final histogram) -> rerun object selection,
ordering, overlap removal, `MET`, and category assignment -> recompute the final
observable -> **validate the nuisance effect** on a control sample (does the change
move the control observable as data would?). Changing only a final weight is
insufficient for a kinematic variation ([systematics](../../hep-analysis/references/systematics.md)).

**Correlation model.** Distinguish *normalization vs shape*, *correlated vs uncorrelated*
(across bins, channels, periods), *symmetric vs asymmetric*, *local vs global*, and
*time-correlated* (a drifting gain is correlated in time; a per-run statistical constant is not). Decorrelating without a physical basis inflates the
combination's precision; over-correlating hides tension.

**Pitfalls.** Double counting the same effect in two nuisances (an `SF` uncertainty
that already contains the calibration uncertainty); arbitrary envelopes of unrelated
alternatives; noisy variations (finite MC) promoted to a shape effect; excessive
smoothing that removes a real feature; unjustified decorrelation.

## Detector combination and global reconstruction

Associations: track-cluster, track-muon, track-ring, timing-track, vertex-object
([event reconstruction](event-reconstruction.md), [particle identification](particle-identification.md)).

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
  overcount the information ([particle identification](particle-identification.md)).
- **Ambiguities**: shared hits/clusters assigned to two objects, overlap removal
  between overlapping objects, double counting of energy in particle flow,
  boundary effects at detector seams.
- **When an added detector helps or hurts.** It *improves resolution* when its error is
  independent and comparable; *improves efficiency* when it covers gaps; *improves
  purity* by rejecting fakes through redundancy; it *worsens* efficiency if it is
  required in the selection with an efficiency lower than the gain, *worsens* resolution
  if a biased or non-Gaussian input is weighted heavily, and *worsens* robustness by
  adding a new failure mode (dead region, calibration drift) into the combined object.

## Common misconceptions and failure modes

- **1D agreement as validation.** Check joint and conditional distributions and tails.
- **Scale factor used outside its measured range**, or at the wrong level (object vs event).
- **Reweighting a marginal** while the cause lies in a correlated variable.
- **Linear `J V J^T` with a threshold or migration.** Use variations/toys.
- **Systematic as noise.** A finite-MC fluctuation elevated to a shape uncertainty.
- **Unjustified decorrelation / envelope of unrelated models.**
- **Combining detectors with shared systematics as independent.** Double counts information.
- **Tuning the simulation on the measured observable**, then reading agreement as validation
  (see the analysis invariants in [hep-analysis-guide.md](../../hep-analysis/references/hep-analysis-guide.md)).

## Deliverables

- The simulation levels used for each corrected/validated quantity and the data proxy.
- For each `SF`: derivation, binning, correlations, range, extrapolation, uncertainty.
- The systematic table mapping nuisance -> reconstructed -> physics observable, with
  correlation model and validation of each variation.
- Whether linear propagation is valid, and the toy/profile alternative when not.
- The combination rule with the correlation matrix and a check against the best single input.

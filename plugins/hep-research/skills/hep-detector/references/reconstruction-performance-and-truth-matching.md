# Reconstruction Performance and Truth Matching

Covers how to measure whether reconstruction worked: efficiency, fake rate, purity,
resolution, and bias - all of which rest on a **truth-matching criterion** that must be
stated explicitly, because changing it changes every number. Complements the
statistical treatment of efficiencies in
[histograms-efficiencies.md](../../hep-measurement/references/histograms-efficiencies.md), the
data-driven efficiency measurement in
[triggers-luminosity-pileup.md](triggers-luminosity-pileup.md), and
the response-matrix formalism in
[response-and-forward-folding.md](response-and-forward-folding.md).

## Truth matching is a definition, not a measurement

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

## Efficiency, fake rate, and purity

These three are computed over different denominators, and mixing them up is a common
error. The full definitions, including the mis-ID category and the two duplicate-rate
conventions, are in [performance metrics](performance-metrics-and-residual-diagnostics.md); in the tracking case:

- **Efficiency** = generated particles in the fiducial region with at least one
  matched reconstructed object / generated particles in the fiducial region.
  Denominator is *generated*; counting matched reconstructed objects instead
  double-counts under many-to-one matching.
- **Fake (or ghost) rate** = unmatched reconstructed objects / all reconstructed
  objects. Denominator is *reconstructed*.
- **Purity** = matched reconstructed objects / all reconstructed objects. Here, with no
  identity category, it is the complement of the fake rate; with a mis-ID category it
  is not (see the linked definition).
- **Duplicate rate** = generated particles matched by two or more reconstructed
  objects / matched generated particles (state the convention if another is used).

State the fiducial region defining "should have been reconstructed". An efficiency
quoted without it is not interpretable, because it silently includes or excludes
particles outside acceptance, and acceptance is a geometric property that should be
separated from efficiency - see
[detector systems overview](detector-systems-overview.md).

Efficiency is a ratio of counts. For unweighted, background-free trials its uncertainty is
**binomial**, not a Gaussian propagation of numerator and denominator - `<plugin
root>/skills/hep-detector/scripts/tag_and_probe_efficiency.py` computes the exact
Clopper-Pearson interval for that case; background-subtracted yields need the simultaneous pass/fail
fit of [triggers, luminosity and pileup](triggers-luminosity-pileup.md). With weighted events a
binomial interval on the weighted counts is wrong, too small or too large depending on the weight
scale: use `Var(eps) = [(1-eps)^2 sum_pass w^2 + eps^2 sum_fail w^2] / (sum w)^2`, or effective
counts.

Quote all of these **differentially** in the variables they depend on - momentum,
direction, local density or pileup - not integrated. An integrated efficiency is a
weighted average over the simulated input spectrum, so it carries that spectrum's model
dependence and does not transfer to a different sample.

## Simulation-derived versus data-derived performance

Efficiency measured in simulation has known truth, but it still carries the
finite-sample statistical error of the simulated sample and depends on the matching
definition, and it is only as good as the simulation. Efficiency measured in data has no truth, so it uses a
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

What each kind of number can support: a check whose reference is MC truth supports only **performance in
simulation**. Claiming it for data needs the data/MC comparison above (a scale factor and its uncertainty) when the
performance was derived in simulation; performance measured directly in data with a data-driven method needs no scale
factor, but its premises (tag bias, background subtraction, trigger correlations) are recorded and checked. A model
trained on simulation lists its training and application domains and checks the shift between them; its version is a
condition. Which confirmation a performance claim on data needs (method-independent, not only a holdout), and how
the target tier of a performance number is decided, are in hep-computing
[research workflow control](../../hep-computing/references/research-workflow-control.md).

## Resolution and bias from reco-versus-truth

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
  [tracking](tracking-and-vertexing.md)), for jet energy tails feeding fake missing
  momentum, and for background estimates. Quote a robust width (an interquantile
  range) and the tail fraction alongside any Gaussian core.
- **Resolution is not a scalar.** It varies with the same variables efficiency does,
  and quoting it integrated hides the regions that dominate the systematic.
- **A steeply falling spectrum turns resolution into a bias.** With a falling true
  spectrum, more objects migrate up than down at any given reconstructed value, so a
  symmetric resolution produces an asymmetric net migration. This is a migration
  effect to be handled by unfolding or forward folding, not by a resolution correction.

## From performance to correction

Reconstruction performance enters the measurement in one of two ways, and they must
not be mixed:

- **Correct the data** - divide by efficiency and unfold the resolution to obtain a
  particle-level result. This requires the response matrix and its regularization, and
  makes the result comparable to theory directly. Follow
  [measurements-and-unfolding.md](../../hep-measurement/references/measurements-and-unfolding.md).
- **Fold the prediction** - apply efficiency and resolution to the simulated
  prediction and compare at detector level. Statistically cleaner (no unfolding
  regularization, no ill-conditioned inversion), but the result is
  detector-specific.

Whichever is chosen, the same performance inputs must be used consistently across
signal, background, and control regions, and their uncertainties treated as correlated
where they share a common source - see
[systematics.md](../../hep-measurement/references/systematics.md).

## Validating performance itself

Performance numbers deserve the same scrutiny as physics results:

- **Closure test.** Apply the derived correction back to an independent simulated
  sample and confirm it recovers the truth within uncertainty. A non-closure is not
  tuned away; first diagnose it: a statistical fluctuation (check against the
  closure-sample uncertainty and with another independent sample), a code bug, a
  failure of the method in that regime, or a residual model bias. Fix the bug or
  method; what remains as residual bias is quoted as a systematic.
- **Independent samples.** Derive corrections and validate them on statistically
  independent samples; deriving and validating on the same events understates the
  uncertainty.
- **Check the denominators.** Most efficiency bugs are denominator bugs: particles
  outside the fiducial region, particles from the wrong production vertex, or
  double-counted generated particles.
- **Check for a matching-criterion dependence.** Recompute the key number with a
  tighter and a looser matching threshold; a strong dependence means the number is
  reporting the criterion as much as the detector.

## Common misconceptions and failure modes

- **Truth matching treated as a measurement.** It is a criterion, and results depend on it.
- **Unstated denominators**, especially particles outside the fiducial region or from the wrong vertex.
- **Scale factors applied outside the range where they were measured.**
- **Resolution binned in the reconstructed variable**, which sculpts the distribution.
- **No matching-criterion sensitivity check** on the headline number.

## Deliverables

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
- A closure test on an independent sample, with any non-closure diagnosed (statistics,
  bug, method failure, residual model bias) and the residual bias quoted as a systematic.
- A matching-criterion sensitivity check on the headline performance number.

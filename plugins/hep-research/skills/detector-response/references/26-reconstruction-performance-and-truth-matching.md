# Reconstruction Performance and Truth Matching

Covers how to measure whether reconstruction worked: efficiency, fake rate, purity,
resolution, and bias - all of which rest on a **truth-matching criterion** that must be
stated explicitly, because changing it changes every number. Complements the
statistical treatment of efficiencies in
[04-histograms-efficiencies.md](../../hep-analysis/references/04-histograms-efficiencies.md), the
data-driven efficiency measurement in
[19-triggers-luminosity-pileup.md](19-triggers-luminosity-pileup.md), and
the response-matrix formalism in
[10-measurements-unfolding.md](../../hep-analysis/references/10-measurements-unfolding.md).

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
[detector systems overview](21-detector-systems-overview.md).

Efficiency is a ratio of counts and its uncertainty is **binomial**, not a Gaussian
propagation of numerator and denominator - `${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/tag_and_probe_efficiency.py`
computes the exact Clopper-Pearson interval, and it applies here exactly as it does for
trigger efficiencies. When the events are weighted, the effective-sample-size
correction matters and a naive binomial interval on weighted counts understates the
uncertainty.

Quote all of these **differentially** in the variables they depend on - momentum,
direction, local density or pileup - not integrated. An integrated efficiency is a
weighted average over the simulated input spectrum, so it carries that spectrum's model
dependence and does not transfer to a different sample.

## Simulation-derived versus data-derived performance

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
  [tracking](22-tracking-and-vertexing.md)), for jet energy tails feeding fake missing
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
  [10-measurements-unfolding.md](../../hep-analysis/references/10-measurements-unfolding.md).
- **Fold the prediction** - apply efficiency and resolution to the simulated
  prediction and compare at detector level. Statistically cleaner (no unfolding
  regularization, no ill-conditioned inversion), but the result is
  detector-specific.

Whichever is chosen, the same performance inputs must be used consistently across
signal, background, and control regions, and their uncertainties treated as correlated
where they share a common source - see
[06-systematics.md](../../hep-analysis/references/06-systematics.md).

## Validating performance itself

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
- A closure test on an independent sample, with any non-closure quoted as a systematic.
- A matching-criterion sensitivity check on the headline performance number.

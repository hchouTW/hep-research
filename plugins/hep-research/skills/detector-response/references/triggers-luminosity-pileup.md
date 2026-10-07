# Triggers, Luminosity, and Pileup Reweighting

Complements the trigger/luminosity cautions already listed in
[analysis-design.md](../../hep-analysis/references/analysis-design.md) and the weight-composition
conventions in [weights-normalization.md](../../hep-analysis/references/weights-normalization.md)
with the concrete measurement and reweighting methodology.

## Trigger efficiency measurement: tag-and-probe

The standard method for measuring a trigger's (or an object identification/isolation
requirement's) efficiency directly from data is tag-and-probe: select events with an
unambiguous, tightly-identified "tag" object (typically satisfying an independent,
well-understood trigger) alongside a "probe" object of the type whose efficiency is
being measured, and measure the fraction of probes that additionally satisfy the
requirement under study. The tag-and-probe pair is usually drawn from a resonance
(e.g. Z -> ll) so that a mass-window requirement suppresses combinatorial background
without biasing the probe's kinematics relative to the signal-selection phase space.

Efficiency is a ratio of counts (`pass / total`, both from data or side-by-side from
data and MC for a scale factor), so its uncertainty is binomial, not a
simple-Gaussian propagation of the numerator and denominator separately - see
`<plugin root>/skills/detector-response/scripts/tag_and_probe_efficiency.py` for a worked Clopper-Pearson interval
implementation, and cross-check any framework-provided efficiency uncertainty against
it rather than assuming a naive `sqrt(N)/N` treatment was used.

Background contamination in the probe sample (real tag paired with a misidentified or
combinatorial probe) biases the measured efficiency; subtract it with a fit to the
tag-probe invariant mass in a sideband or signal+background template fit before
computing the pass/total ratio, and propagate the subtraction's own uncertainty into
the efficiency uncertainty rather than treating the sideband-subtracted count as if it
had no additional uncertainty.

## Trigger turn-on curves and plateau requirements

A trigger's efficiency as a function of the relevant kinematic variable (typically pT)
rises from zero to a plateau; analyses should select comfortably into the plateau
region (commonly required to be within a few percent of its asymptotic value) rather
than on the rising edge, where efficiency changes rapidly with pT and small
data/MC mismodeling of the turn-on shape becomes a large, hard-to-control systematic.
State the plateau threshold used and confirm the analysis selection sits at or above
it; if it does not (e.g. because the analysis needs sensitivity below the plateau),
the turn-on shape itself must be measured and applied as a pT-dependent efficiency,
not a flat number, and its shape uncertainty documented explicitly.

## Prescales

A prescaled trigger accepts only a random subset (1-in-N) of events that would
otherwise pass, to control output rate; each accepted event's *effective* weight must
account for this. Do not apply a flat luminosity-normalization weight (as in
[weights-normalization.md](../../hep-analysis/references/weights-normalization.md)) to data
collected with a prescaled trigger without folding in the prescale, and be aware that
prescale values are frequently time-dependent (changed run-by-run or by
luminosity-block as instantaneous luminosity varies over a fill) - a single
run-averaged prescale is an approximation that can be wrong enough to matter for
precision measurements; verify against the per-lumi-block record when precision
requires it. Combining several differently-prescaled trigger paths (an OR of paths
covering different pT ranges, say) requires either using only the lowest-threshold
unprescaled path in each region or a formally correct combination that accounts for
each path's prescale and their overlap - simply summing raw counts across paths
double-counts events that fired more than one.

## Luminosity

The integrated luminosity normalizing a data-driven yield or MC-to-data comparison
carries its own measurement uncertainty (typically a couple of percent, but stated by
each experiment's luminosity measurement for the relevant data-taking period) that is
usually treated as a fully correlated normalization nuisance across all
luminosity-normalized processes in the fit - do not treat it as negligible or omit it
because "it's small," since a normalization-only nuisance can still dominate the total
uncertainty of a rate measurement once statistical and other systematic uncertainties
are reduced. Certified good run/luminosity-block lists must match between the
luminosity calculation and the actual event selection (an event selected from a run
not in the certified list, or a certified run excluded from the luminosity sum,
biases the normalization); reconcile this explicitly rather than assuming the
production-level bookkeeping already guarantees it, per the run/luminosity-block
duplicate-counting caution in
[analysis-design.md](../../hep-analysis/references/analysis-design.md).

## Pileup reweighting

Simulated pileup (additional proton-proton interactions per bunch crossing) is
generated against an assumed pileup profile that does not exactly match the profile
actually recorded in data (the true instantaneous-luminosity conditions are only
known after data-taking). Reweight MC event-by-event so its pileup distribution
matches data's, using the number of true (not reconstructed - reconstructed pileup
counting is itself resolution-limited) interactions per event as the reweighting
variable:

```python
weight = data_pileup_pdf[n_true_interactions] / mc_pileup_pdf[n_true_interactions]
```

`<plugin root>/skills/detector-response/scripts/pileup_reweight.py` implements this from two histograms (data profile, MC
profile) with the usual failure modes guarded explicitly: a bin with zero MC
probability produces a division by zero (undefined reweighting factor for a pileup
condition the MC sample doesn't populate at all - this must be flagged, not silently
turned into 0 or inf), and the data pileup profile itself carries a systematic
uncertainty (from the minimum-bias cross section assumed to convert instantaneous
luminosity into an expected interaction count) that should be propagated as an
up/down variation of the reweighting target, not treated as exact. Confirm after
reweighting that the mean/profile of pileup in reweighted MC actually matches data
in a control region - a reweighting step that is applied but silently no-ops (e.g.
from a units or binning mismatch between the two input histograms) is a common,
easy-to-miss bug.

## Deliverables

- Tag-and-probe selection (resonance/mass window, tag and probe object definitions)
  and background-subtraction method used for each measured efficiency.
- Turn-on curve and plateau threshold, and confirmation the analysis selection sits
  in the plateau (or the pT-dependent efficiency applied if not).
- Prescale-handling method for data, including whether it is time-dependent and how
  multiple trigger paths are combined.
- Integrated luminosity value, its uncertainty, and confirmation that certified
  run/luminosity-block lists match between the luminosity calculation and the event
  selection.
- Pileup reweighting target (data profile source, minimum-bias cross section
  assumption) and a closure check that reweighted MC pileup matches data in a
  control region.

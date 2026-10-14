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
(e.g. Z -> ll) so that a mass-window requirement suppresses combinatorial background.
The window and the tag requirements are part of the probe definition and can bias it:
the method is only "almost unbiased", and its bias is measured by applying it to
simulation and comparing with the truth-counted efficiency (CMS muon performance,
JINST 7 (2012) P10002, arXiv:1206.4071, section 5.1; opened 2026-10-14). Name the
tag-probe correlations the measurement must handle:

- the probe may be the object that fired the event's trigger, so a trigger efficiency
  needs the tag (not the probe) to have fired it;
- when both legs can serve as the tag, one event gives two pairs whose outcomes are
  correlated (a pass-pass event contributes two passing probes), so the probes are not
  independent binomial trials;
- several probe candidates per tag (or several tags) in one event are correlated in the
  same way;
- a nearby tag can change the probe's measured efficiency (CMS checks this by tightening
  the tag-probe separation, the same section).

Efficiency is a ratio of counts (`pass / total`, both from data or side-by-side from
data and MC for a scale factor), so its uncertainty is binomial, not a
simple-Gaussian propagation of the numerator and denominator separately.
`<plugin root>/skills/detector-response/scripts/tag_and_probe_efficiency.py` gives the
Clopper-Pearson interval, which applies to unweighted, background-free, independent
counts only - that is the script's scope. Cross-check any framework-provided efficiency
uncertainty against it rather than assuming a naive `sqrt(N)/N` treatment was used.

Background contamination in the probe sample (real tag paired with a misidentified or
combinatorial probe) biases the measured efficiency, and a background-subtracted pass
or fail count is no longer a binomial count: Clopper-Pearson does not apply to it. Fit
the tag-probe invariant-mass spectra of passing and failing probes simultaneously, with
a shared signal shape and their own background shapes, and take the efficiency from the
two signal normalizations; its uncertainty then comes from the likelihood and includes
the background subtraction (CMS, the same section). That fit is a statistical inference:
hand it to hep-statistics.

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
matches data's, using the Poisson mean `mu` of interactions per bunch crossing as the
reweighting variable:

```python
weight = data_mu_pdf[mu] / mc_mu_pdf[mu]
```

Why `mu` and not the per-event interaction count: in data, `mu` is what the luminosity
measurement gives (`L_b = mu f_r / sigma_inel` per bunch, ATLAS, Eur. Phys. J. C 76 (2016)
653, arXiv:1608.03953, eq. 1; opened 2026-10-14); the number of interactions in a given
crossing is not observed. In simulation the generator draws a mean per event (recorded, for example, as
CMS's "true number of interactions") and then a Poisson count around it ("number of
pileup interactions"; CERN Open Data, "CMS pileup simulation",
<https://opendata.cern.ch/about/CMS-Pileup-Simulation>, opened 2026-10-14). The Poisson
count has a wider distribution than the mean, so dividing the data `mu` profile by the
simulated count profile reweights the wrong distribution. The reconstructed-vertex count
is worse still: it is resolution- and efficiency-limited.

`<plugin root>/skills/detector-response/scripts/pileup_reweight.py` implements this from two histograms (data profile, MC
profile) with the usual failure modes guarded explicitly: a bin with zero MC
probability produces a division by zero (undefined reweighting factor for a pileup
condition the MC sample doesn't populate at all - this must be flagged, not silently
turned into 0 or inf), and the data pileup profile itself carries a systematic
uncertainty (from the minimum-bias cross section assumed to convert instantaneous
luminosity into an expected interaction count) that should be propagated as an
up/down variation of the reweighting target, not treated as exact. After reweighting,
the mean of `mu` in reweighted MC equals the data mean by construction (whenever every
data-populated bin has a defined weight), so it tests nothing. Validate on a variable
that was not reweighted: the number of reconstructed primary vertices (or another
pileup-sensitive observable) in a control region, data against reweighted MC. A
reweighting step that is applied but silently no-ops (e.g. from a units or binning
mismatch between the two input histograms) is a common, easy-to-miss bug, and this
closure is what catches it.

## Dead time and live time

Every readout and trigger system is blind for part of the time: busy front ends,
full buffers, trigger rules (a minimum spacing between accepts, a maximum number per
window), run-control pauses. The fraction of time it can accept an event is the
*live fraction*, and a cross section or flux uses the luminosity or exposure *while
live*.

- **Models** (exact for Poisson arrivals at true rate `n` and dead time `tau_d`):
  non-paralyzable `m = n/(1 + n tau_d)`, live fraction `1/(1 + n tau_d)`;
  paralyzable `m = n exp(-n tau_d)`. Bunched beams, spills, bursts, and trigger rules
  break the Poisson assumption, and several dead-time sources in series do not
  combine by a simple formula; measure rather than model when precision matters
  ([front-end electronics and signal processing](front-end-electronics-and-signal-processing.md)).
- **Measurement**: count a free-running clock or random triggers gated and ungated by
  the busy signal, per luminosity block (or per second for a space instrument); the
  ratio is the live fraction for that block.
- **Application**: the effective luminosity is `sum_i L_i f_i` over blocks `i`, not the
  total luminosity times the time-averaged live fraction, because the live fraction falls
  when the instantaneous luminosity (and rate) is high; the same holds for exposure,
  `sum_i A_i T_i f_i`. Prescales enter the same sum.
- **Event-dependent losses**: buffer overflow and derandomizer losses fall
  preferentially on large or closely spaced events, so they are an efficiency that
  depends on the event, not only a time fraction; check with random triggers whether
  the lost fraction depends on occupancy.

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
- Live-fraction measurement per luminosity block (or time interval), its sources,
  and confirmation that the luminosity or exposure is summed block by block with it.

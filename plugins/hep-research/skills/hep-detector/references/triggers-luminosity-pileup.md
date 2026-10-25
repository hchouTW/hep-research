# Triggers, Luminosity, and Pileup Reweighting

Complements the trigger/luminosity cautions already listed in
[analysis-design.md](../../hep-measurement/references/analysis-design.md) and the weight-composition
conventions in [weights-normalization.md](../../hep-measurement/references/weights-normalization.md)
with the concrete measurement and reweighting methodology.

## Tag-and-probe efficiency measurement

<!-- example: source citation (experiment named as the source of a general method or number) -->
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
<!-- /example -->

<!-- example: source citation (experiment named as the source of a general method or number) -->
- the probe may be the object that fired the event's trigger, so a trigger efficiency
  needs the tag (not the probe) to have fired it;
- when both legs can serve as the tag, one event gives two pairs whose outcomes are
  correlated (a pass-pass event contributes two passing probes), so the probes are not
  independent binomial trials;
- several probe candidates per tag (or several tags) in one event are correlated in the
  same way;
- a nearby tag can change the probe's measured efficiency (CMS checks this by tightening
  the tag-probe separation, the same section).
<!-- /example -->

Efficiency is a ratio of counts (`pass / total`, both from data or side-by-side from
data and MC for a scale factor), so its uncertainty is binomial, not a
simple-Gaussian propagation of the numerator and denominator separately.
`<plugin root>/skills/hep-detector/scripts/tag_and_probe_efficiency.py` gives the
Clopper-Pearson interval, exact for unweighted (or frequency-weighted), background-free,
independent counts; with positive sampling weights it gives an approximate interval from
the Kish effective sample size, and it refuses zero or signed weights. Cross-check any
framework-provided efficiency uncertainty against it rather than assuming a naive
`sqrt(N)/N` treatment was used.

<!-- example: source citation (experiment named as the source of a general method or number) -->
Background contamination in the probe sample (real tag paired with a misidentified or
combinatorial probe) biases the measured efficiency, and a background-subtracted pass
or fail count is no longer a binomial count: Clopper-Pearson does not apply to it. Fit
the tag-probe invariant-mass spectra of passing and failing probes simultaneously, with
their own background shapes, and take the efficiency from the two signal normalizations;
its uncertainty then comes from the likelihood and includes the background subtraction
(CMS, the same section). Let the passing and failing signal shapes differ (a common
template with separate resolution parameters, or simulation templates per category):
failing probes often have worse resolution or longer tails, and a fully shared shape
then moves signal into the failing background and biases the efficiency beyond the
likelihood uncertainty; alternative signal models give a shape systematic. That fit is a statistical inference:
hand it to hep-statistics.
<!-- /example -->

Trigger efficiencies have other data-driven methods - an orthogonal reference trigger, the bootstrap method, and
prescaled unbiased streams - with their own bias checks: [analysis design](../../hep-measurement/references/analysis-design.md#trigger-efficiency-from-data).

**Check:** The tag fired the trigger, tag-probe correlations are handled, the method bias is measured in simulation, and a background-subtracted count is fitted (pass and fail together) rather than given a Clopper-Pearson interval.

## Trigger turn-on curves and plateau requirements

A trigger's efficiency as a function of the relevant kinematic variable (typically pT)
rises from zero to a plateau; analyses should select comfortably into the plateau
region (commonly required to be within a few percent of its asymptotic value) rather
than on the rising edge, where efficiency changes rapidly with pT and small
data/MC mismodeling of the turn-on shape becomes a large, hard-to-control systematic.
State the plateau threshold used and confirm the analysis selection sits at or above it (even on the
plateau the efficiency is measured in data and simulation and its scale factor applied: on the
plateau means insensitive to the turn-on shape, not free of correction); if it does not (e.g. because the analysis needs sensitivity below the plateau),
the turn-on shape itself must be measured and applied as a pT-dependent efficiency,
not a flat number, and its shape uncertainty documented explicitly. A turn-on is usually fitted with an error
function (Gaussian CDF) or a similar sigmoid; its parameters are correlated, so propagate their covariance, not
independent errors.

**Check:** The selection sits on the measured plateau with its scale factor applied, or the measured turn-on is applied as a pT-dependent efficiency with a shape uncertainty.

## Prescales

A prescaled (downscaled) trigger keeps on average one of every `d` events that would
otherwise pass, to control output rate; the downscaling is done by a counter
(deterministic) or by random selection. Prescales are kept constant within a run (or
luminosity block) and changed between them as the instantaneous luminosity and
background rates change. Each kept event's weight must account for the prescale: the
run-dependent weight is `w = d_k/eps` (prescale of the run, trigger efficiency), and the
averaged weight, which uses the effective luminosity `sum_k L_k/d_k` over runs, gives a
smaller statistical uncertainty; with any weights, take the uncertainty of the
corrected count from `sqrt(sum w^2)`, not from the weighted count. Do not apply a flat
luminosity-normalization weight (as in
[weights-normalization.md](../../hep-measurement/references/weights-normalization.md)) to data
collected with a prescaled trigger without folding in the prescale; a single
run-averaged prescale is an approximation, so use the per-run or per-lumi-block record
when precision requires it. To combine several differently prescaled paths (an OR of
paths covering different pT ranges, say), either use one path per region of the offline
variable, efficient there, with its own prescale record (division method), or weight
each event by the smallest prescale among the paths that fired (exclusion method) or by
the inverse probability that any considered path kept it (inclusion method); simply
summing raw counts across paths double-counts events that fired more than one (V.
Lendermann et al., "Combining triggers in HEP data analysis", NIM A604 (2009) 707,
arXiv:0901.4118, eqs. 3-5 for one path, section 4 and eqs. 6-13 for combinations).

**Check:** Prescaled data are normalized with the per-run or per-block prescale record, uncertainties come from the sum of squared weights, and several paths are combined by one documented method without double counting.

## Luminosity

The integrated luminosity normalizing a data-driven yield or MC-to-data comparison
carries its own measurement uncertainty (about 1-2% for recent LHC
measurements, larger for other periods and experiments; take it from the
experiment's luminosity measurement for the relevant data-taking period) that is
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
[analysis-design.md](../../hep-measurement/references/analysis-design.md).
<!-- example: experiment-specific illustration -->
Example of a luminosity uncertainty: 0.83% for the full ATLAS Run-2 13 TeV dataset, 0.9-1.1% per year (EPJC 83 (2023) 982,
arXiv:2212.09379).
<!-- /example -->

### Luminosity calibration

<!-- example: source citation (experiment named as the source of a general method) -->
The absolute luminosity scale comes from a dedicated calibration (general method, described for example in ATLAS,
Eur. Phys. J. C 76 (2016) 653, arXiv:1608.03953, sections 4-7; read 2026-10-14):

- **van der Meer scans** separate the beams in steps in x and in y under special low-pileup conditions; the overlap
  width, the peak rate and the bunch-population product `n1 n2` give the visible cross section
  `sigma_vis = epsilon sigma_inel` of each luminometer and algorithm (eq. 11).
- **Corrections to the scan**: x-y factorization of the bunch densities (non-factorization), the length scale of the
  beam separation, orbit drifts, and beam-beam deflection and dynamic-beta effects.
- **Transfer to physics conditions**: the calibration is made at low pileup and applied at high pileup, so the
  luminometer's linearity in `mu` is checked against independent algorithms.
- **Long-term stability**: compare luminometers over the year; drifts between them are an uncertainty.
- **Correlations**: state which uncertainty components are correlated across years and periods for a combination
  (EPJC 83 (2023) 982, arXiv:2212.09379, section 8.1).
<!-- /example -->

**Check:** The luminosity value, its uncertainty and its correlations across periods come from the experiment's calibration, and the certified run and block lists match the event selection.

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

<!-- example: source citation (experiment named as the source of a general method or number) -->
Why `mu` and not the per-event interaction count: in data, `mu` is what the luminosity
measurement gives (`L_b = mu f_r / sigma_inel` per bunch, ATLAS, Eur. Phys. J. C 76 (2016)
653, arXiv:1608.03953, eq. 1; opened 2026-10-14); the number of interactions in a given
crossing is not observed. In simulation the generator draws a mean per event (recorded, for example, as
CMS's "true number of interactions") and then a Poisson count around it ("number of
pileup interactions"; CERN Open Data, "CMS Pile-up simulation",
<https://opendata.cern.ch/about/CMS-Pileup-Simulation>, opened 2026-10-14). The Poisson
count has a wider distribution than the mean, so dividing the data `mu` profile by the
simulated count profile reweights the wrong distribution. The reconstructed-vertex count
is worse still: it is resolution- and efficiency-limited.
<!-- /example -->

`<plugin root>/skills/hep-detector/scripts/pileup_reweight.py` implements this from two histograms (data profile, MC
profile) and flags (ok false) a bin with zero MC probability, which produces a division
by zero (undefined reweighting factor for a pileup condition the MC sample doesn't
populate at all - this must be flagged, not silently turned into 0 or inf), and a
non-finite ratio. It takes no minimum-bias cross-section input: the data pileup profile
itself carries a systematic uncertainty (from the minimum-bias cross section assumed to
convert instantaneous luminosity into an expected interaction count) that the analysis
must propagate as an up/down variation of the reweighting target, not treat as exact.
After reweighting, the mean of `mu` in reweighted MC equals the data mean by construction
(whenever every data-populated bin has a defined weight), so it checks only that the weights
were computed and applied, not the target profile. Validate on a variable
that was not reweighted: the number of reconstructed primary vertices (or another
pileup-sensitive observable) in a control region, data against reweighted MC. A
reweighting step that is applied but silently no-ops (e.g. from a units or binning
mismatch between the two input histograms) is a common, easy-to-miss bug, and this
closure is what catches it.

**Check:** The weights use the Poisson mean `mu` (not the per-event count or the vertex count), empty MC bins are flagged, the target carries its cross-section variation, and closure is shown on a variable that was not reweighted.

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
  ([front-end waveform processing](front-end-waveform-processing.md#pileup-of-pulses-baseline-and-rate)).
- **Measurement**: count a free-running clock or random triggers gated and ungated by
  the busy signal, per luminosity block (or per second for a space instrument); the
  ratio is the live fraction for that block.
- **Application**: the effective luminosity is `sum_i L_i f_i` over blocks `i`, not the
  total luminosity times the time-averaged live fraction, because the live fraction falls
  when the instantaneous luminosity (and rate) is high; the same holds for exposure,
  `sum_i A_i T_i f_i`. Prescales enter the same sum as divisors, `sum_i L_i f_i / d_i`.
- **Event-dependent losses**: buffer overflow and derandomizer losses fall
  preferentially on large or closely spaced events, so they are an efficiency that
  depends on the event, not only a time fraction; check with random triggers whether
  the lost fraction depends on occupancy.

**Check:** The live fraction is measured per block and enters the luminosity or exposure block by block, and event-dependent losses are checked with random triggers.

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

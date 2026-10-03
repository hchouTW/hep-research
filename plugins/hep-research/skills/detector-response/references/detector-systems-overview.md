# Detector Systems Overview

Orients the detector-level references that follow
([tracking](tracking-and-vertexing.md), [calorimetry](calorimetry-ecal-hcal.md),
[particle identification](particle-identification.md)) and connects them to the
analysis-level material already in
[analysis-design.md](../../hep-analysis/references/analysis-design.md) and
[physics-objects-jets-btagging-met.md](physics-objects-jets-btagging-met.md),
which start from reconstructed objects and treat the detector as given. This file is
organized by detector *technology* and deliberately assumes no particular experiment,
geometry, or beam configuration; quote scaling relations and orders of magnitude
rather than treating any one experiment's resolution as universal.

For the unified forward-model/inverse-problem framework and the technology-specific
extensions (readout, gaseous/timing/muon/noble-liquid/photosensor detectors, metrics,
validation, case studies), see [detector measurement framework](detector-measurement-framework.md) onward.

## What a detector measures, and what it does not

A detector does not measure particle identity, energy, or momentum. It measures
localized energy deposits, arrival times, and induced charge, at known positions, and
everything else is inference built on a model of how particles interact with matter.
Keeping that distinction explicit prevents a large class of errors in which a
reconstructed quantity is treated as a direct observation: a "measured" momentum is
the output of a fit whose assumptions (magnetic field map, alignment, material model,
hit uncertainties) can each be wrong, and its uncertainty is only as trustworthy as
those inputs.

The measurable primitives are position, time, deposited energy, and - through a
magnetic field - the curvature of a charged trajectory. Every physics-object quantity
in an analysis reduces to combinations of those four.

## Subsystem layering

Detectors are built in layers ordered by how destructive each measurement is. The
innermost systems must perturb the particle as little as possible, because everything
downstream depends on the trajectory surviving intact; the outermost systems are
allowed to absorb the particle entirely, because nothing is measured after them.

The conventional ordering is precision tracking first (thin, high-granularity,
minimally disruptive), then identification systems that exploit velocity or radiation
without stopping the particle, then electromagnetic calorimetry, then hadronic
calorimetry, then muon detection - muons being the charged particles that routinely
survive the calorimeters. Not every experiment has every layer, and the ordering can
differ (a time-of-flight system may sit both before and after a spectrometer to define
a flight path), but the underlying principle - measure non-destructively before
measuring destructively - is general.

The practical consequence for analysis is that subsystems are not independent. A
mismeasured track changes the calorimeter cluster it is matched to; extra material in
the tracker changes what reaches the calorimeter; a timing detector's flight-path
measurement depends on the track fit. Systematic variations must therefore propagate
across subsystem boundaries, not be applied to one object in isolation - the same
requirement stated for kinematic variations in the analysis invariants.

## Magnetic spectrometry: rigidity, momentum, and charge sign

A charged particle of charge `q` and momentum `p` in a magnetic field follows a
trajectory whose curvature depends on the combination `R = p / q`, the **rigidity**.
This is the quantity a magnetic spectrometer actually measures. Momentum follows only
once the charge is known or assumed, and for multiply-charged nuclei the two differ by
a factor of `Z` - a distinction that matters enormously in cosmic-ray and heavy-ion
contexts and is easy to lose when reusing code written for singly-charged particles.

Curvature is inversely proportional to rigidity, so the *directly* measured quantity
is closer to `1/R` than to `R`. This has a consequence that propagates into every
analysis: measurement uncertainty is approximately Gaussian in curvature, not in
rigidity or momentum. The relative rigidity resolution therefore grows roughly
linearly with rigidity, `sigma(R)/R ~ R`, until it is no longer meaningful - at the
**maximum detectable rigidity** (MDR), where `sigma(R)/R` reaches 100%, the sign of
the curvature is no longer reliably determined. Above the MDR a spectrometer does not
simply become imprecise; it begins to misassign charge sign, scattering
high-rigidity particles of one sign into the other sign's sample. Any analysis
sensitive to a charge ratio or to a rare oppositely-charged species must treat this
**charge confusion** as a background, not as a resolution effect - see
[tracking and vertexing](tracking-and-vertexing.md).

Because uncertainty is Gaussian in `1/R`, binning and unfolding in `R` interact badly
with a symmetric-in-curvature resolution function: a steeply falling spectrum
combined with a curvature-Gaussian smearing produces a net migration upward in
rigidity that is not symmetric and cannot be corrected by a symmetric bin-by-bin
factor. Handle it with a response matrix built in the measured variable - see
[measurements-and-unfolding.md](../../hep-analysis/references/measurements-and-unfolding.md).

## Material budget and multiple scattering

Every layer of a detector is also a scatterer and an absorber. The **material budget**
is the accumulated thickness of material a particle traverses, expressed in units of
radiation length `X0` for electromagnetic processes and nuclear interaction length
`lambda_I` for hadronic ones. It is the single most useful number for predicting how
much a detector degrades its own measurements.

Multiple Coulomb scattering deflects a charged particle by a small random angle in
each layer, with an RMS projected angle described by the Highland formula, which
scales as roughly `1/(beta * p)` times the square root of the material thickness in
radiation lengths. Two consequences follow directly. First, scattering degrades
angular and position measurements more severely at low momentum, so a spectrometer's
rigidity resolution has a low-rigidity floor set by scattering that no improvement in
sensor precision can remove. Second, because the intrinsic sensor-resolution
contribution to `sigma(R)/R` grows with rigidity while the scattering contribution
falls, every magnetic spectrometer has a characteristic rigidity at which the two
cross, and a resolution curve that is worst at both ends. Locating that crossover is
the first thing to do when interpreting a spectrometer's performance;
`${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/multiple_scattering.py` computes it from a material description.

Material also causes energy loss (ionization for all charged particles,
bremsstrahlung additionally for electrons), photon conversion, and nuclear
interaction - meaning the particle arriving at an outer subsystem may not be the
particle that entered. Interaction and conversion in tracker material are a standard
source of reconstruction inefficiency and of fake low-momentum tracks, and the
material model used in simulation is a leading systematic for any measurement that
depends on the surviving-particle fraction. Mismodeled material budget is a common
root cause when data and simulation disagree in a way that varies with polar angle,
because material thickness varies with the path length through the detector.

## Acceptance and geometric factor

**Acceptance** is the fraction of produced particles or events that can in principle be
measured, given the detector's geometry and active-region coverage. It is a property
of the apparatus and the physics process together, not of the apparatus alone, because
it depends on the kinematic distribution being sampled. For an experiment measuring a
flux rather than a cross section, the corresponding quantity is the **geometric
factor**, an area-times-solid-angle with units of `m^2 sr`, which converts a counting
rate into a flux.

Acceptance must be distinguished from **efficiency**: acceptance is geometric and
computed from simulation of the apparatus, efficiency is the probability that a
particle inside the acceptance is actually reconstructed and selected, and is measured
from data wherever possible. Merging them into a single simulation-derived correction
hides the part that should have been data-driven and validated - see
[reconstruction performance](reconstruction-performance-and-truth-matching.md) and
[histograms-efficiencies.md](../../hep-analysis/references/histograms-efficiencies.md).

Acceptance depends on the simulated input spectrum whenever it is computed by
integrating over a distribution. Quote the generator-level assumption used, and check
the sensitivity by recomputing with a reweighted input spectrum; an acceptance quoted
without that check carries an unstated model dependence.

## Resolution vocabulary

Terms that are frequently conflated, and are worth stating precisely in any writeup:

- **Intrinsic resolution** - the single-sensor measurement precision, before any fit.
- **Resolution** - the width of the distribution of (reconstructed minus true), at
  fixed true value. Usually quoted as a Gaussian sigma, which is an approximation:
  most detector response functions have tails, and quoting only a core sigma
  systematically understates the probability of large mismeasurement.
- **Bias** - the mean of (reconstructed minus true). A resolution quoted without a
  bias check is incomplete; a small bias in a steeply falling spectrum can matter more
  than a large resolution.
- **Response** - the mean reconstructed value as a function of true value, whose
  deviation from unity slope is a calibration problem, not a resolution problem - see
  [calibration and alignment](calibration-and-alignment.md).
- **Linearity** - whether response is constant across the measured range.
- **Occupancy** - the fraction of readout channels hit per event, which drives
  pattern-recognition difficulty and confusion, not resolution.

Report the core-sigma, the tail fraction, and the bias separately. A single number
labeled "resolution" is only interpretable if the definition (Gaussian fit range,
RMS, or an interquantile width) is stated alongside it.

## Deliverables

- The subsystem inventory assumed by the analysis, with the ordering a particle
  traverses and which subsystems are required by the selection.
- Whether the spectrometer measurement is rigidity or momentum, the charge assumption
  relating them, and the maximum detectable rigidity if the analysis approaches it.
- Material budget in `X0` (and `lambda_I` where hadronic interaction matters) along
  the relevant paths, and whether its uncertainty was propagated as a systematic.
- Acceptance or geometric factor, stated separately from efficiency, with the
  generator-level input spectrum assumed and a sensitivity check against a reweighted
  spectrum.
- Resolution quoted with its definition (fit range or width statistic), its bias, and
  its tail fraction, not as a single unqualified sigma.

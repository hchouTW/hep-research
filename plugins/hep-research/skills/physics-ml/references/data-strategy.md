# Data Strategy Reference

Dataset design, label quality and splits. Dataset and loader code: [data-loading.md](data-loading.md). The one home
of grouped and temporal splits is [ml-analysis.md](ml-analysis.md), "Splits and leakage"; the tools are
`<plugin root>/skills/physics-ml/scripts/make_grouped_splits.py` and `check_split_integrity.py` (missing group or
timestamp metadata gives `incomplete`, never a pass).

## Labels from simulation truth

In physics the labels usually come from simulation truth matching, not annotators, and their noise is systematic:

- a truth-matching criterion (a cone radius, a hit-sharing fraction, a parton-to-jet assignment) mislabels a fraction
  of objects that depends on kinematics and pileup; vary the criterion and show the effect on the downstream result;
- labels inherit the generator: a different parton shower or hadronization model can change what "signal-like" means
  (compare generators as a systematic);
- the noise caps the measurable performance; a metric beyond the label purity is fitting the noise.

Inspect the actual data as well: duplicated events, truncated branches, a corrupted file or a default value (-999,
zero for a missing object) are obvious on sight and invisible in aggregate statistics.

## Leakage beyond splits

- Fit all preprocessing (normalization, imputation, encoders) on the training split only.
- Duplicated or overlapping simulated events (re-used generator seeds, overlapping production requests) between
  training and test inflate results; deduplicate on event identifiers.
- Simulation-specific artifacts (an exact generator seed, a preprocessing quirk, a detector-simulation shortcut, a
  variable defined only in simulation) can let the model solve an unintended easier problem: target leakage in its
  simulation form ([robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)).
- A pretrained model may have seen the evaluation sample (contamination): check the pre-training samples.

## Imbalance

Imbalance is a metric and threshold problem before it is a sampling problem: use metrics that do not depend on the
class prior (per-class efficiencies at a working point, background rejection; [ml-analysis.md](ml-analysis.md),
"Analysis metrics"), set the working point from the analysis, balance class totals in the training weights
("Class balancing and the prior"), and never resample validation or test: they keep the physics weights.

## How much simulation

Train on 25%, 50% and 100% of the sample and plot the validation metric (and, where it is cheap, the downstream
uncertainty): a flat curve means more events of the same kind will not help. Target generation where the model fails
(tails, low-statistics regions) rather than uniformly.

## Record

Provenance (generator, version, production campaign), truth-matching definition, known gaps, preprocessing, the split
rule and the manifest, and a version identifier tied to each trained model (the `ml-artifact`).

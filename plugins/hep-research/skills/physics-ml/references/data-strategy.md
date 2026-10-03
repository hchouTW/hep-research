# Data Strategy Reference

Dataset design, quality, and splits - the decisions that set the ceiling on everything
downstream. For `Dataset`/`DataLoader` implementation see
[data-loading.md](data-loading.md); for evaluating on the result see
[evaluation-strategy.md](evaluation-strategy.md).

Use `${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/check_split_integrity.py` to check splits for overlap, duplication, and
group leakage. It reports how many IDs carry group (and timestamp) metadata; missing metadata gives `incomplete`, which is
not a pass, and `--strict` makes it a failure for a split that feeds a result.

## Data quality beats model choice

Below a certain scale, effort spent on labels and curation returns more than effort
spent on architecture. Label noise sets a hard ceiling no model can pass: if 5% of test
labels are wrong, 95% accuracy is perfect performance and further gains are fitting the
noise.

**Measure label quality before optimizing against it.** Re-label a sample with multiple
annotators, compute agreement, and inspect disagreements. Low agreement usually means
the task definition is ambiguous, not that annotators are careless - and an ambiguous
task cannot be fixed by a better model.

Inspect the actual data. Many dataset defects - duplicated records, truncated fields,
a corrupted shard, a mislabeled class - are obvious on sight and invisible in
aggregate statistics.

## Splits that survive contact with reality

The default random split is wrong for most real datasets. Choose the split from how
the model will be used:

| Situation | Split by | Random split gives |
|---|---|---|
| Predicting the future | Time | Optimistic - the model sees the future |
| Repeated entities (users, patients, sites) | Entity/group | Optimistic - memorizes entities |
| Near-duplicate records | Deduplicate first | Optimistic - test items seen in training |
| Nested structure (frames in a video) | Outer unit | Severely optimistic |
| Genuinely i.i.d. samples | Random is correct | Correct |

**Group leakage is the most common serious error.** If the same user, patient, document,
or session appears in both train and test, the test set measures memorization. It is
invisible in the metrics - the numbers just look good.

**Temporal leakage** is the second most common: any feature computed using information
unavailable at prediction time (an aggregate over the full dataset, a target-derived
statistic, a label-informed normalization) inflates offline results and vanishes in
production.

Fit all preprocessing - normalization statistics, vocabularies, imputation values,
encoders - on training data only, then apply to validation and test. Fitting on the
full dataset first is a subtle, extremely common leak.

## Deduplication and contamination

Near-duplicates between train and test inflate results. Exact-match deduplication is
not enough; use a similarity or hashing scheme appropriate to the modality.

For anything using pretrained models or web-scale corpora, **benchmark contamination**
is a live concern: the evaluation set may be in the pretraining data. Check where
possible, and prefer held-out sets constructed after the pretraining cutoff for claims
that matter.

For scientific ML built on simulated data, also inspect whether metadata or
simulation-specific artifacts (an exact generator seed, a preprocessing quirk, a
detector-simulation shortcut) let the model solve an easier unintended problem instead
of the intended physical one - this is target leakage's simulation-specific form. See
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md)'s
simulation-to-data section.

## Imbalance

Class imbalance is a metric and threshold problem more often than a sampling problem.
Before resampling:

- Use metrics that are meaningful under imbalance (precision/recall, PR-AUC) rather
  than accuracy - see [evaluation-metrics.md](evaluation-metrics.md).
- Set the decision threshold from the operating requirement, not at 0.5.

If resampling or class weighting is used, note that it changes the predicted
probabilities' calibration, which matters if the scores are consumed downstream rather
than only argmaxed.

**Never resample the validation or test sets.** They must reflect the deployment
distribution, or every metric computed on them is answering a different question.

## Scaling the dataset

More data helps until it doesn't, and the curve is measurable: train on 25%, 50%, and
100% and plot. A flat curve means more data of the same kind will not help - the gain
has to come from better labels, harder examples, or a different distribution. This
measurement is far cheaper than collecting more data and discovering it was useless.

Prefer **targeted** collection: examples from failing slices, near the decision
boundary, or from underrepresented conditions. Uniform expansion mostly adds examples
the model already handles.

## Documentation

Record for every dataset: provenance and collection method, labeling instructions and
annotator agreement, known biases and gaps, preprocessing applied, the split rule and
its rationale, and a version identifier. An undocumented dataset makes every model
trained on it unauditable.

## Deliverables

- Label-quality measurement: annotator agreement and the estimated noise ceiling.
- Split rule (temporal, group, or random) with its justification, and a verified
  absence of group and temporal leakage.
- Deduplication method, and a contamination check where pretrained models are involved.
- Confirmation that preprocessing was fit on training data only.
- Imbalance handling, with validation and test left at the deployment distribution.
- A data-scaling curve showing whether more data would help.
- Dataset documentation and a version identifier tied to each trained model.

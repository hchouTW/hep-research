# Evaluation Strategy Reference

Designing an evaluation that predicts production behavior and supports a ship decision.
For metric definitions and their computation see
[evaluation-metrics.md](evaluation-metrics.md); for comparing two candidates see
[ablation-and-design-review.md](ablation-and-design-review.md); for data splits see
[data-strategy.md](data-strategy.md).

## Evaluate against the decision, not the benchmark

Start from what the model's output causes to happen, then choose the metric. A ranking
model whose top result drives a click needs a top-k metric, not overall AUC. A model
whose false positives are expensive and false negatives cheap needs an asymmetric
measure, not accuracy.

**A single aggregate number is never enough to ship on.** At minimum: the headline
metric, its uncertainty, a slice breakdown, and the operating threshold. Report the
metric's uncertainty from the test set size - a 1,000-example test set cannot resolve
a 0.5% difference, and reporting one implies precision that does not exist.

## Slices matter more than the aggregate

Aggregate performance hides subgroup failure, and subgroup failure is what causes
incidents. Define slices in advance from what matters: input characteristics (length,
quality, language, modality), entity groups (region, device, cohort), difficulty and
rarity, and any category with fairness or safety implications.

Report per-slice metrics with per-slice sample sizes. Small slices produce noisy
metrics that will occasionally look alarming or excellent by chance; without the sample
size, neither can be interpreted. Watch for the case where the aggregate improves while
an important slice regresses - it is common, and it is the thing a single number is
guaranteed to hide.

## Build a behavioral test suite, not only a metric

Metrics summarize; they do not tell you *what* is wrong. Complement them with:

- **Capability tests** - specific behaviors the model must exhibit, as assertions.
- **Invariance tests** - transformations that must not change the output (irrelevant
  paraphrase, benign perturbation).
- **Directional tests** - changes that must move the output a known way.
- **Regression cases** - every production failure ever seen, kept forever.

This suite is more useful than an extra decimal place of aggregate accuracy, and it is
what makes a release decision defensible.

## Baselines make a number interpretable

A metric alone means nothing. Always report against: a trivial baseline (majority class,
most-recent-value, random), the current production model, and where relevant human
performance. A model that beats neither the trivial baseline nor production is not a
candidate, regardless of its absolute number.

## The offline-online gap

Offline metrics reliably overstate production performance. The recurring causes:

- **Distribution shift** between the test set and live traffic.
- **Training/serving skew** in feature computation - see
  [monitoring-and-lifecycle.md](monitoring-and-lifecycle.md).
- **Feedback effects** the offline set cannot contain.
- **Selection bias** in how the offline data was collected, particularly when it was
  logged under a previous model's decisions.
- **Optimizing the wrong proxy** - the offline metric improves and the business outcome
  does not.

Expect a gap, measure it once via online evaluation, and use that measured ratio to
calibrate expectations. Treating offline metrics as a production prediction is the
error; treating them as a *comparative* signal between candidates is usually sound.

## Protect the test set

The test set can be used for a **decision**, not for iteration. Every look at it leaks
information, and a set consulted a hundred times during development has become a
validation set with an optimistic bias.

Iterate on validation. Reserve test for the final check. If it has been used heavily,
say so and construct a fresh one before making a claim. Hold out a genuinely untouched
set for the ship decision where the stakes justify it.

## Evaluation hierarchy

Predictive performance, calibration, robustness, and downstream/scientific validity
are different properties and each needs its own check - a strong aggregate benchmark
metric is not sufficient evidence for every claim built on top of it:

```text
Correctness -> Predictive performance -> Calibration -> Slice behavior -> Robustness -> Distribution shift -> Scientific/downstream validity
```

Not every task needs every level - an internal exploratory model may stop at slice
behavior; a model backing a scientific or safety-relevant claim needs the full chain.
See [uncertainty-and-calibration.md](uncertainty-and-calibration.md) for calibration
and [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md) for
the robustness/shift levels; for the statistical validity of a downstream scientific
conclusion itself, see `academic-papers`.

## Deciding to ship

Write the criteria before seeing the results, or the results will shape the criteria:

- The headline metric threshold, with uncertainty.
- Per-slice floors - no important slice regresses beyond a stated bound.
- The regression suite passing.
- Latency, cost, and memory within budget - see
  [serving-architecture.md](serving-architecture.md).
- An explicit statement of what got worse. Something almost always does, and a
  candidate reported as improving on every axis usually has not been examined closely
  enough.

A ship decision is a trade, not a threshold, and writing the trade down in advance is
what keeps it honest.

## Deliverables

- The decision the model drives, and the metric chosen to match it.
- Headline metric with uncertainty from the test set size.
- Slices defined in advance, with per-slice metrics and sample sizes.
- A behavioral suite: capability, invariance, directional, and regression cases.
- Trivial, production, and (where relevant) human baselines.
- The measured offline-online gap, or a statement that it is unmeasured.
- Test-set usage history, and whether a fresh set is needed for the claim.
- Ship criteria written before results, including what regressed.
- Which level of the evaluation hierarchy this result actually reached, and what
  would be needed for the next level.

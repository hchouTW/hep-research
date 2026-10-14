# Evaluation Strategy Reference

Designing an evaluation that predicts how a model behaves where it is used and supports a decision. Metric definitions:
[evaluation-metrics.md](evaluation-metrics.md); physics metrics and working points: [ml-analysis.md](ml-analysis.md),
"Analysis metrics"; comparing candidates: [ablation-and-design-review.md](ablation-and-design-review.md); splits:
[ml-analysis.md](ml-analysis.md), "Splits and leakage".

- **Evaluate against the decision.** Start from what the output causes (a selection at a working point, a template, a
  correction, a trigger decision) and pick the metric from it. A single aggregate number is never enough: give the
  headline metric with its uncertainty from the test-sample size (a 1,000-event test set cannot resolve a 0.5%
  difference), a slice breakdown and the operating point.
- **Slices matter more than the aggregate.** Define them in advance (run period, detector region, pileup, kinematic
  bins, process) and report per-slice metrics with per-slice effective sample sizes. An aggregate gain that hides a
  regressing slice is common.
- **Behavioural checks:** capability, invariance (a transformation that must not change the output, for example a
  symmetry of the inputs), directional (a change that must move the output a known way), and every past failure kept
  as a regression case.
- **Baselines:** a trivial baseline, the current model, and the cut-based or BDT reference; a candidate that beats
  neither is not a candidate.
- **Simulation is not where the model is used.** Offline (simulation) metrics overstate performance on data:
  distribution shift, training/application skew ([monitoring-and-lifecycle.md](monitoring-and-lifecycle.md)) and a
  mismatched proxy. Measure the gap once in data control samples and use offline metrics comparatively.
- **Protect the test set.** It serves a decision, not iteration; a set consulted many times has become a validation
  set. For a method developed and then qualified, keep three tiers: development on public or synthetic fixtures,
  qualification on held-back task families or data, and a final confirmation on a set frozen in advance; vary the
  generator family and defect type, not only the seed, and count every query against a held-back set.
- **Evaluation hierarchy:** correctness -> predictive performance -> calibration -> slices -> robustness -> shift ->
  downstream (physics) validity. A model behind a physics result needs the whole chain
  ([uncertainty-and-calibration.md](uncertainty-and-calibration.md),
  [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md); statistical validity of the result:
  hep-statistics).
- **Decide with criteria written before the results:** metric threshold with uncertainty, slice floors, regression
  suite, budget, and an explicit list of what got worse.

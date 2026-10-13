# Monitoring and Model Lifecycle Reference

> Generic ML engineering; not physics-specific. For physics tasks start at
> [ml-analysis.md](ml-analysis.md). In an experiment, the "deployed model" is a tagger or
> regression in reconstruction or a trigger, and the world changes through detector
> conditions, run periods, pileup and calibrations rather than user behavior.

What happens after a model is in use: detecting that it has degraded, releasing new
versions safely, and knowing when to retrain. Complements
[serving-architecture.md](serving-architecture.md), which covers sizing a service.

## A deployed model degrades without being changed

The code is fixed; the inputs are not. Distinguish the causes, because the responses
differ:

| Kind | What moved | Detectable without labels? |
|---|---|---|
| Covariate shift | Input distribution (new run period, pileup, detector conditions) | Yes |
| Label shift | Class fractions (different trigger mix or selection) | Partly, via the score distribution |
| Concept drift (called "concept shift" in robustness-and-distribution-shift.md's research-time framing) | Input-output relationship | No - needs a labelled control sample or a proxy |
| Upstream data change | A feature's meaning or availability (new reconstruction version, recalibration, changed units) | Yes, via data validation |

**Upstream data changes are the most common cause of sudden degradation**, and they are
not really drift - a reconstruction release that renames or redefines a variable, a
changed calibration, a silently failing input. Validate input schema, ranges and
missing-value rates where the model is applied; this catches more real incidents than
any distributional test.

For evaluating this same shift taxonomy at research time, before a model is used or when
diagnosing a result, see
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

## What to monitor

Four layers, cheapest first:

1. **Operational** - latency, error rate, throughput. Fails first and is unambiguous.
2. **Input data** - schema, ranges, missing-value rates, feature distributions per run
   or period. Catches upstream breakage.
3. **Predictions** - score distribution and fraction passing the working point per run.
   Available immediately, no labels needed. A shift here is a leading indicator.
4. **Outcomes** - efficiency and mistag rate measured in data control samples
   (tag-and-probe, sidebands), which arrive late. Reconcile when they arrive.

Alert on the ones with low false-positive rates (1 and 2) and *review* the others.
Distributional tests over large samples flag differences that are statistically real
and practically irrelevant; alerting on them trains people to ignore alerts.

Monitor by **slice** (run period, detector region, pileup bin, kinematic bin), not only
in aggregate. Aggregate performance can hold steady while one region degrades badly.

## Releasing a new model

- **Regression suite.** A fixed evaluation set plus specific cases that previously
  failed. Run it on every candidate. Ship only with an explicit diff of what improved
  and what regressed - an aggregate gain almost always hides individual regressions.
- **Run old and new side by side** on the same events before switching, and compare
  scores and working-point decisions event by event.
- **Keep rollback trivial.** The previous model, its preprocessing, and its config must
  be re-deployable as a unit.
- **Scale factors belong to a model version.** A new model invalidates data/simulation
  scale factors and systematics measured for the old one; plan their re-derivation
  (detector-response) before the switch.

**Training/application skew** is the classic failure: features computed differently in
training and in the production software. The robust fix is sharing the transformation
code rather than reimplementing it; the detection is comparing feature values and scores
for identical events through both paths.

## Versioning

A model artifact alone is not reproducible. Version together, as one unit: weights,
code commit, preprocessing, dataset version, config, and metrics (the `ml-artifact`).
Keep the evaluation set versioned too: a metric that improved because the evaluation set
changed is not an improvement.

## When to retrain

Retrain on a **trigger**, not only a calendar: a monitored metric crossing a threshold,
a known upstream change (new reconstruction, new run period), or new simulation
campaigns. Automated retraining needs a gate: a pipeline that retrains and deploys
without a regression check will eventually deploy a model trained on corrupted inputs.

## Incident response

When a model misbehaves in production: **roll back first, diagnose second.** Then check
in order - upstream data (most likely), training/application skew, a recent model or
config change, and only then genuine drift. Add the failing case to the regression suite.

## Deliverables

- Monitors at all four layers, with alerting limited to operational and data checks.
- Slice-level monitoring for the run periods and regions that matter.
- A versioned regression suite, run per candidate, with an explicit improve/regress
  diff.
- A side-by-side comparison of old and new models on identical events before the switch.
- A training/application skew check comparing both paths on identical inputs.
- Versioned unit of weights, code, preprocessing, data, config, metrics, and eval set.
- Retraining triggers, and the gate that blocks a bad automated retrain.

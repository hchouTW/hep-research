# Monitoring and Model Lifecycle Reference

What happens after a model ships: detecting that it has degraded, releasing new
versions safely, and knowing when to retrain. Complements
[serving-architecture.md](serving-architecture.md), which covers sizing the service
itself.

## A deployed model degrades without being changed

The code is fixed; the world is not. Distinguish the causes, because the responses
differ:

| Kind | What moved | Detectable without labels? |
|---|---|---|
| Covariate shift | Input distribution | Yes |
| Label shift | Outcome base rates | Partly, via prediction distribution |
| Concept drift (called "concept shift" in robustness-and-distribution-shift.md's research-time framing) | Input-output relationship | No - needs labels or a proxy |
| Upstream data change | A feature's meaning or availability | Yes, via data validation |
| Feedback loop | The model influences its own future inputs | Only with a holdout |

**Upstream data changes are the most common cause of sudden degradation**, and they are
not really drift - a renamed column, a changed unit, a silently-failing feature
pipeline. Validate input schema, ranges, and null rates at serving time; this catches
more real incidents than any distributional test.

For evaluating this same shift taxonomy at research time, before a model ships or when
diagnosing a result rather than monitoring production, see
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

**Feedback loops** deserve specific attention: a recommender that shapes what users see
also shapes its own training data. Without a small randomized holdout, the model's
apparent performance is partly a measurement of its own influence.

## What to monitor

Four layers, cheapest first:

1. **Operational** - latency percentiles, error rate, throughput, saturation. Fails
   first and is unambiguous.
2. **Input data** - schema, ranges, null and cardinality rates, feature distributions.
   Catches upstream breakage.
3. **Predictions** - output distribution, confidence distribution, class balance,
   abstention rate. Available immediately, no labels needed. A shift here is a leading
   indicator.
4. **Outcomes** - accuracy against ground truth, which arrives late or never. Where
   labels are delayed, monitor a proxy and reconcile when they arrive.

Alert on the ones with low false-positive rates (1 and 2) and *review* the others.
Distributional tests over large samples flag differences that are statistically real
and practically irrelevant; alerting on them trains people to ignore alerts.

Monitor by **slice**, not only in aggregate. Aggregate accuracy can hold steady while a
subgroup degrades badly, and the aggregate is the last place it shows up.

## Releasing a new model

A model change is a production change and deserves the same discipline:

- **Regression suite.** A fixed evaluation set plus specific cases that previously
  failed. Run it on every candidate. Ship only with an explicit diff of what improved
  and what regressed - an aggregate gain almost always hides individual regressions.
- **Shadow mode.** Run the candidate on live traffic without serving its output.
  Catches production-only issues (feature skew, latency, crashes) at no user risk.
- **Canary, then staged rollout.** A small traffic share first, with automatic rollback
  on operational metrics. Quality metrics usually arrive too late to gate on.
- **Keep rollback trivial.** The previous model, its preprocessing, and its config must
  be re-deployable as a unit. A rollback that requires rebuilding a pipeline is not a
  rollback.

**Training/serving skew** is the classic failure: features computed differently in
training and serving. The robust fix is sharing the transformation code rather than
reimplementing it; the detection is comparing feature values for identical inputs
through both paths.

## Versioning

A model artifact alone is not reproducible. Version together, as one unit: weights,
code commit, preprocessing, dataset version, config, and metrics. Anything less means a
production model cannot be rebuilt or explained later.

Keep the evaluation set versioned too. A metric that improved because the eval set
changed is not an improvement, and this is easy to do accidentally.

## When to retrain

Retrain on a **trigger**, not only a calendar: a monitored metric crossing a threshold,
a known upstream change, or accumulated new data past some volume. Scheduled retraining
with no trigger wastes compute when nothing has changed and reacts too slowly when
something has.

Automated retraining needs a gate. A pipeline that retrains and deploys without a
regression check will eventually deploy a model trained on corrupted data.

## Incident response

When a model misbehaves in production: **roll back first, diagnose second.** Then check
in order - upstream data (most likely), serving/skew, a recent model or config change,
and only then genuine drift. Add the failing case to the regression suite so it is
covered permanently.

## Deliverables

- Monitors at all four layers, with alerting limited to operational and data checks.
- Slice-level monitoring for the subgroups that matter.
- A versioned regression suite, run per candidate, with an explicit improve/regress
  diff.
- Rollout plan: shadow, canary, staged, with automatic rollback criteria.
- A training/serving skew check comparing both paths on identical inputs.
- Versioned unit of weights, code, preprocessing, data, config, metrics, and eval set.
- Retraining triggers, and the gate that blocks a bad automated retrain.

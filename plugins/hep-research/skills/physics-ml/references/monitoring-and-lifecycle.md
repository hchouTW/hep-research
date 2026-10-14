# Monitoring and Model Lifecycle Reference

> Generic ML engineering. In an experiment the deployed model is a tagger or regression in reconstruction or a
> trigger, and the world changes through detector conditions, run periods, pileup and calibrations. Research-time
> shift checks: [robustness-and-distribution-shift.md](robustness-and-distribution-shift.md).

- **Why a fixed model degrades:** covariate shift (run period, pileup, conditions; visible without labels), label
  shift (trigger mix; partly visible in the score distribution), concept drift (needs a labelled control sample), and
  upstream data changes (a reconstruction release that redefines a variable, a recalibration, a silently failing
  input), the most common cause of sudden degradation. Validate input schema, ranges and missing-value rates where
  the model is applied.
- **Monitor four layers, cheapest first:** operational (latency, errors), inputs per run or period, predictions
  (score distribution, fraction passing the working point per run), outcomes (efficiency and mistag rate in data
  control samples, late). Alert on the first two; review the rest. Monitor by slice (period, detector region, pileup).
- **Releasing a new model:** a versioned regression suite with an explicit improve/regress diff; old and new run side
  by side on the same events; rollback of model, preprocessing and config as a unit. A new model invalidates the
  data/simulation scale factors and systematics of the old one: plan their re-derivation (detector-response).
  Training/application skew (features computed differently in training and production) is the classic failure: share
  the transformation code and compare scores for identical events through both paths.
- **Versioning:** weights, code commit, preprocessing, dataset version, config, metrics and evaluation set as one unit
  (the `ml-artifact`).
- **Retraining:** on a trigger (a metric threshold, a new reconstruction or run period, new simulation), behind a
  regression gate. In an incident, roll back first, then check upstream data, skew, recent changes, and only then
  drift; add the case to the regression suite.

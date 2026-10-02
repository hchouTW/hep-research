# Multivariate Classifiers and Regression: BDTs and Neural Networks in Analysis

Extends [11-ml-analysis.md](11-ml-analysis.md)'s splits/weights/validation
principles with concrete guidance on training and choosing between classifier
and regression model families. Read 11-ml-analysis.md first; this file assumes
it. Most sections below are written for a classification (signal/background
score) task; where a continuous-target regression task (energy/mass/direction
regression) differs, see [Regression targets](#regression-targets).

## Choosing a classifier family

- **Boosted decision trees** (XGBoost, LightGBM, or TMVA's BDT) remain a strong
  default for tabular, engineered-feature inputs of the size typical in an analysis
  (tens of features, thousands to low millions of weighted events): they need
  comparatively little hyperparameter tuning to reach a reasonable operating point,
  train quickly enough for iterative feature engineering, and their feature-importance
  and single-tree outputs are easier to sanity-check against physical expectation
  than a neural network's internal representations.
- **Neural networks** are worth the additional complexity when the input is not
  naturally tabular (raw or lightly processed detector images, point clouds of
  reconstructed objects, sequences), when a specific architecture encodes a known
  symmetry the analysis wants to exploit (permutation invariance over jets, for
  example), or when combining many heterogeneous input types benefits from learned
  rather than hand-engineered combination. A plain feed-forward network on the same
  engineered features a BDT would use rarely outperforms a well-tuned BDT enough to
  justify its extra tuning and validation burden.
- Simple cuts remain preferable to either when the separating power comes from one or
  two variables with an intuitive, easily-communicated physical origin, and when the
  analysis's audience or later reinterpretation needs a transparent selection rather
  than an opaque score. A classifier that only marginally beats a two-variable cut
  is not automatically worth its added validation and correlation-with-mass burden.
- Tree-based models are invariant to monotonic per-feature transforms and need no
  input scaling; neural networks generally do (standardization or normalization per
  feature, fit on the training partition only and reapplied identically at inference).
  Skipping this step is a common reason an NN underperforms a BDT on the same features
  for a data-preparation reason unrelated to model capacity.

## Feature engineering and selection

Prefer physically motivated features (masses, angular separations, kinematic
combinations with known discriminating power) over an undifferentiated dump of every
available low-level variable - beyond making the model more interpretable, this
reduces the chance of accidentally including a feature that encodes look-elsewhere
information about the signal region definition itself (a variable correlated with the
selection used to define signal/control regions can leak information across regions
in ways that are easy to miss until a closure test fails). Check pairwise correlation
and, more importantly, correlation of each candidate feature with the observable used
in the final fit (typically a mass) before including it - a feature with strong
correlation to the fit observable will sculpt the background shape after a selection
on the classifier score, which is the mass-sculpting concern already raised in
11-ml-analysis.md and needs the mitigation described there (decorrelation, or fitting
in categories with re-derived background shapes).

## Training practicalities: BDTs

- Tree depth and the minimum number of events per leaf are the primary
  overtraining controls; with limited weighted MC statistics, a deep tree can
  memorize individual high-weight events rather than learning a generalizable
  boundary - check the effective (weighted) statistics per leaf, not just the raw
  event count, especially in samples with large weight variance (see
  [03-weights-normalization.md](../../hep-analysis/references/03-weights-normalization.md) on negative
  and highly variable weights).
- Use k-fold cross-training/application (train on k-1 folds, apply to the held-out
  fold, rotate) rather than a single train/test split when MC statistics are limited
  enough that a held-out test set would otherwise cost meaningful training statistics
  - this lets every event contribute to both training and (out-of-fold) application
  without any event being scored by a model that saw it during training.
- Compare training and validation-fold loss/AUC curves versus boosting round to pick
  the number of trees (early stopping on the validation fold) rather than a fixed
  round count decided in advance; a round count picked once and reused across
  reprocessing campaigns without rechecking silently drifts from optimal as input
  samples change.
- Some libraries' split-finding assumes nonnegative sample weights (e.g. XGBoost's
  default histogram-based tree method) and can silently mishandle signed generator
  weights; check the library's weight-handling documentation before training on a
  sample with negative weights, and prefer the absolute-weight/bias-correction
  schemes discussed in [03-weights-normalization.md](../../hep-analysis/references/03-weights-normalization.md)
  over silently dropping the sign.
- A hyperparameter search (grid, random, or Bayesian) must optimize the same
  weighted, physics-relevant metric used elsewhere in the analysis - expected
  sensitivity, not raw AUC or unweighted accuracy - or it can select an operating
  point that looks best in training but underperforms on the metric the analysis
  actually cares about.

## Training practicalities: neural networks

- Class imbalance between signal and background is common and is usually handled
  through the loss weighting scheme (matching the formal event weights - see
  11-ml-analysis.md's "Weights and objectives") rather than naive oversampling of the
  minority class, which can distort the effective statistical power of the training
  sample.
- Batch composition matters when using physics event weights: a batch that happens to
  contain a small number of very high-weight events can dominate the gradient for that
  step; monitor the effective sample size within batches (or pre-bin/cap extreme
  weights, documenting the cap) rather than assuming standard-deep-learning batching
  intuition transfers unchanged from unweighted computer-vision-style datasets. See
  [deep-learning-guide.md](deep-learning-guide.md) for general PyTorch training-loop and debugging practices (NaN
  losses, gradient clipping, evaluation-mode pitfalls) that apply here unchanged once
  the physics-specific weighting above is handled correctly.
- Prefer starting from a simple, shallow architecture and confirming it beats (or at
  least matches) a well-tuned BDT baseline before investing in a deeper/more exotic
  architecture - a complex network that underperforms a simple BDT baseline usually
  indicates a data or training-procedure problem, not that more capacity is needed.

## Regression targets

Many analyses regress a continuous physical quantity instead of (or alongside)
classifying signal from background - jet/tau/electron energy corrections, missing
transverse momentum estimators, invariant-mass regression, or direction/resolution
estimators. The classifier guidance above (family choice, feature engineering,
BDT/NN training practicalities, inference/deployment) still applies; regression
changes these specific choices:

- Loss choice must match the physics use of the target: plain mean-squared error
  optimizes the conditional mean, the right target for a correction applied
  additively/multiplicatively before further use, but not automatically right if
  the downstream use needs a different point estimate (median, via mean absolute
  error or a Huber loss, when outliers or a long tail would dominate an MSE loss)
  or a full predictive distribution (quantile regression, or a head predicting
  both a mean and a heteroscedastic variance/negative-log-likelihood).
- Weight the regression loss with the same formal event weights used elsewhere
  (11-ml-analysis.md's "Weights and objectives"), not a naive unweighted loss - an
  unweighted regression trained on MC with signed or highly variable weights can
  be dominated by a small number of high-weight events the same way an unweighted
  classifier can.
- Validate calibration as linearity and closure of the regressed quantity against
  truth (or an independent proxy), not merely an aggregate loss value: check the
  response (predicted/true, or predicted-minus-true) in bins of pT, eta, and any
  other variable the correction depends on, the same way a jet energy scale
  correction is validated in
  [18-physics-objects-jets-btagging-met.md](../../detector-response/references/18-physics-objects-jets-btagging-met.md)
  - a regression with low aggregate loss can still be biased or non-linear in a
  specific kinematic region the analysis relies on.
- A regressed correction becomes a scale/resolution correction like any other
  object correction: propagate its uncertainty (from training statistics and from
  residual non-closure in each validation bin) through the same object-correction
  and systematic-variation machinery as JES/JER, rather than treating it as a
  fixed, uncertainty-free factor (see [06-systematics.md](../../hep-analysis/references/06-systematics.md)).
- Report an uncertainty for the regressed value itself when a downstream fit uses
  it per-event rather than only as a bin-averaged scale factor - e.g. a predicted
  variance/quantile head, or an ensemble/bootstrap spread - and validate that
  per-event uncertainty's coverage, since an uncalibrated per-event uncertainty is
  easy to introduce silently.

## Calibration and combination

A classifier's raw output score is not automatically a calibrated probability, and
combining multiple classifiers' scores (or using a score as one input among several
observables in a combined fit) requires either calibrating scores against a common
reference (e.g. isotonic regression or Platt scaling against a validation sample) or
using the score only through its rank/selection threshold rather than its literal
value as though it were a probability. Document which convention is used, since
downstream statistical combination methods
([09-statistical-tools.md](../../hep-statistics/references/09-statistical-tools.md)) may implicitly assume
one.

## Inference and deployment

Training and validating a model is not sufficient until it is applied identically
inside the production event loop. Score events through the same preprocessing
(feature order, units, scaling/normalization constants) used in training, and
integrate inference into the existing pipeline rather than a separate ad hoc pass -
e.g. `TMVA::Experimental::RBDT`/`RReader` or an ONNX-exported model inside an
`RDataFrame::Define()`, or the equivalent for a Python/uproot pipeline. Version the
deployed model artifact (weights/graph file, preprocessing constants, library
version) alongside the training config, and reproduce 11-ml-analysis.md's
training-vs-deployment score comparison on a held-out sample as an ongoing
deliverable, not only during initial validation - a preprocessing or
library-version mismatch between training and production is a common source of an
unreproducible classifier score.

## Validation beyond 11-ml-analysis.md's checklist

- Compare feature distributions and the classifier score itself between the
  nominal MC sample and at least one systematic variation to confirm the classifier
  hasn't learned to key on a feature that is itself unstable under systematics (e.g.
  a variable whose modeling differs significantly between generators) - a classifier
  can achieve good nominal separation while being unexpectedly sensitive to a
  systematic uncertainty's variation, inflating that uncertainty's impact on the
  final result in a way that a nominal-only validation would miss.
- For a BDT, inspect feature importance and the highest-importance features' physical
  plausibility as a sanity check before trusting the model, not as a substitute for
  the statistical validation in 11-ml-analysis.md - a feature importance ranking that
  contradicts known physics (e.g. an ostensibly unrelated detector-region indicator
  ranking above a kinematic variable expected to dominate) is a signal to investigate
  for a labeling or leakage bug before proceeding.

## Worked walkthrough: training a BDT without leakage (verified 2026-09-24)

```python
# Two-fold split by event number; each event is scored only by the model that never saw it.
# Needs numpy, scipy, scikit-learn. Synthetic data: 4 features, 2 of them discriminating.
import numpy as np
from scipy.stats import ks_2samp
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

rng = np.random.default_rng(0)
n = 20_000
event_id = np.arange(n)                      # stand-in for (run, lumi, event)
y = rng.random(n) < 0.3
X = rng.normal(size=(n, 4)) + y[:, None] * np.array([0.8, 0.5, 0.0, 0.0])
fold = event_id % 2                          # fixed before any training or tuning

scores, models = np.empty(n), {}
for k in (0, 1):
    train = fold != k
    models[k] = HistGradientBoostingClassifier(max_iter=60, learning_rate=0.05, max_depth=2,
                                               min_samples_leaf=300, random_state=0).fit(X[train], y[train])
    scores[fold == k] = models[k].predict_proba(X[fold == k])[:, 1]

train_auc = roc_auc_score(y[fold == 1], models[0].predict_proba(X[fold == 1])[:, 1])
test_auc = roc_auc_score(y[fold == 0], scores[fold == 0])
for label in (True, False):                  # overtraining check per class
    tr = models[0].predict_proba(X[(fold == 1) & (y == label)])[:, 1]
    te = scores[(fold == 0) & (y == label)]
    print(f"class={label}: KS p-value train vs test = {ks_2samp(tr, te).pvalue:.3f}")
print(f"AUC train fold {train_auc:.3f}, held-out fold {test_auc:.3f}")
```

Observed:
- With the default-sized model (`max_iter=200`, no depth limit) the checks flag
  overtraining: AUC 0.93 on the training fold versus 0.71 held out, and KS p < 1e-3.
- With the shallow configuration above: AUC 0.751 versus 0.739, KS p = 0.26 and 0.53, close
  to this toy's Bayes-optimal AUC of Phi(0.943/sqrt(2)) = 0.748.

Rules this encodes:
- The split is by event identifier and fixed in advance.
- The analysis uses only held-out scores.
- Hyperparameters are tuned inside the training fold (nested CV or `early_stopping`), not by
  looking at held-out results. Choosing the configuration by the held-out AUC, as this
  illustration does, would itself leak.
- The selection cut on the score is also fixed before the signal region is unblinded.

## Deliverables

- Classifier family chosen and the comparison (if any) against a simpler baseline
  that justified it.
- Feature list with the physical motivation for each, and the correlation-with-fit-
  observable check performed.
- Cross-validation/k-folding scheme (or train/test split) and the effective
  (weighted) statistics per fold.
- Score calibration convention used, if scores are combined with other observables.
- Systematic-variation stability check for the classifier score, alongside the
  standard validation layers in 11-ml-analysis.md.
- Random seed(s) and library/framework versions (e.g. xgboost/lightgbm/pytorch)
  pinned and recorded - training is not bitwise reproducible across versions or,
  for GPU-trained networks, across hardware without them.
- Deployed inference artifact (model file, preprocessing constants, library
  version) versioned alongside the training config, with a training-vs-deployment
  score comparison on a held-out sample.
- For a regression target: loss function chosen and its match to the target's
  downstream use, a linearity/closure check of predicted vs. true value across
  the relevant kinematic range, and how the regressed correction's uncertainty is
  propagated as a systematic.

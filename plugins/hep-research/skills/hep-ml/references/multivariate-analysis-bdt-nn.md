# Multivariate Classifiers and Regression: BDTs and Neural Networks in Analysis

Extends [ml-analysis.md](ml-analysis.md) (splits, weights, validation; read it first) with the choice between model
families and their training. Sections are written for a signal/background score; regression differs in
[Regression targets](#regression-targets).

## Choosing a classifier family

- **Boosted decision trees** (XGBoost, LightGBM, TMVA BDT) are the default for engineered tabular inputs of analysis
  size (tens of features, thousands to millions of weighted events): little tuning, fast iteration, and feature
  importances and single trees that can be checked against physics. They need no input scaling.
- **Neural networks** pay off for non-tabular inputs (detector images, point clouds of objects, sequences), when an
  architecture encodes a symmetry the analysis wants (permutation invariance over jets), or to combine heterogeneous
  inputs. On the features a BDT would use, a plain MLP rarely beats a tuned BDT by enough to justify its validation
  burden; it needs per-feature standardization fitted on the training split (a missing one is a common reason an NN
  loses to a BDT).
- **Simple cuts** remain preferable when one or two variables with a clear physical origin carry the separation, or
  when reinterpretation needs a transparent selection.

## Feature engineering and selection

Prefer physically motivated features (masses, angular separations, known discriminants) over every available
low-level variable. Exclude features that encode the region definitions or the target itself (target leakage: a
variable built from the selection that defines signal and control regions leaks across them and shows up only when a
closure test fails). Check each feature's correlation with the fitted observable (typically a mass): a correlated
feature sculpts the background after a cut on the score ([ml-analysis.md](ml-analysis.md), "Mass sculpting and
decorrelation").

## Training practicalities: BDTs

- Tree depth and minimum events per leaf control overtraining; check the effective weighted statistics per leaf, not
  the raw count, in samples with large weight variance
  ([weights-normalization.md](../../hep-measurement/references/weights-normalization.md)).
- With limited simulation use k-fold cross-training: every event is scored by a model that never saw it, and every
  event contributes to training.
- Choose the number of trees by early stopping on the validation fold, rechecked when the input samples change.
- Tree libraries assume non-negative weights (a negative weight gives a negative Hessian). Since 1.3.0, XGBoost
  raises a fatal error on negative instance weights, so signed samples need a deliberate treatment before training
  (options and costs: [ml-analysis.md](ml-analysis.md), "Negative weights"). Evaluate with the signed physics weights
  and never drop the sign silently.
- A hyperparameter search optimizes the analysis metric (expected sensitivity), not raw AUC or accuracy, with grouped
  folds ([ml-analysis.md](ml-analysis.md), "Hyperparameter search").

## Training practicalities: neural networks

- Balance the class totals in the training weights (rescale each class to equal summed weight) and keep the relative
  physics weights within a class; never oversample or flatten inside a class ([ml-analysis.md](ml-analysis.md),
  "Event weights" and "Class balancing and the prior").
- A batch with a few very high-weight events can dominate a step: monitor the effective sample size per batch, or cap
  extreme weights and document the cap. PyTorch practice: [deep-learning-guide.md](deep-learning-guide.md).
- Start shallow and confirm the network at least matches a tuned BDT; a complex network that loses to it usually has
  a data or procedure problem.

## Regression targets

Energy, momentum or mass regressions, MET estimators, direction or resolution estimators. The guidance above applies,
with these changes:

- **The loss picks the summary learned** (Cheong et al., JINST 15 (2020) P01030, arXiv:1910.03773, abstract, read
  2026-10-14): MSE learns the conditional mean E[y_true | x]; mean absolute error or Huber the median, robust to
  tails; quantile regression or a mean-and-variance head a predictive distribution. Match it to the downstream use.
- **The training truth spectrum is part of the answer.** By Bayes' theorem p(y_true | x) is proportional to
  p(x | y_true) p(y_true), so the conditional mean, and the correction, depend on the truth spectrum of the training
  sample. A correction trained on one spectrum and applied to another (a steeper background, a resonance, data) is
  biased. Check the response in bins of the true and of the reconstructed variable, and close on a sample with a
  different truth spectrum. Prior-independent alternatives: learn the mode of the response (Cheong et al.), or
  calibrate the response reco/true in bins of the true value and invert it numerically (`unverified`: no opened
  source cited for numerical inversion here).
- **Systematics of a regressed correction.** It is an object correction like JES/JER: propagate its uncertainty
  (training statistics, residual non-closure per validation bin) through the usual systematic machinery
  ([systematics.md](../../hep-measurement/references/systematics.md)), and add the in-situ data/simulation difference of
  scale and resolution measured in a control sample (Z or J/psi resonances, balance methods). That difference is often
  the dominant term (`unverified`: practice, no opened source cited); hand its evaluation to hep-detector.
- Weight the regression loss with the physics weights; validate linearity and closure in bins of pT, eta and every
  variable the correction depends on, as for a jet energy scale
  ([physics-objects-jets-btagging-met.md](../../hep-detector/references/physics-objects-jets-btagging-met.md));
  if a fit uses a per-event uncertainty, validate its coverage.

## Calibration, combination, deployment

A raw score is not a probability: calibrate it (Platt, isotonic, prior correction:
[uncertainty-and-calibration.md](uncertainty-and-calibration.md)) or use it only through its rank and a threshold, and
state which, since statistical combinations may assume one
([statistical-tools.md](../../hep-statistics/references/statistical-tools.md)). Apply the model in the production event
loop with the training preprocessing (feature order, units, scaling constants), for example
`TMVA::Experimental::RBDT`/`RReader` or an ONNX model inside `RDataFrame::Define()`; version weights, preprocessing and
library together, and keep comparing training and deployment scores on a held-out sample.

## Validation beyond ml-analysis.md

- Compare features and the score between the nominal simulation and at least one systematic variation: a classifier
  that keys on a poorly modelled variable inflates that systematic.
- For a BDT, a feature-importance ranking that contradicts known physics (a detector-region flag above the expected
  kinematic discriminant) points to a labelling or leakage bug.

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

Observed: with the default-sized model (`max_iter=200`, no depth limit) the checks flag overtraining (AUC 0.93 on the
training fold against 0.71 held out, KS p < 1e-3); with the shallow configuration above, AUC 0.751 against 0.739, KS p
= 0.26 and 0.53, close to this toy's Bayes-optimal AUC of Phi(0.943/sqrt(2)) = 0.748. The split is by event identifier
and fixed in advance; the analysis uses only held-out scores; hyperparameters are tuned inside the training fold
(choosing them by the held-out AUC, as this illustration does, would itself leak); the cut on the score is fixed before
unblinding.

## Deliverables

The family chosen against a simpler baseline; features with their motivation and the correlation with the fitted
observable; the k-fold scheme with effective weighted statistics per fold; the score convention (calibrated or rank
only); the systematic-variation stability check; seeds and library versions; the versioned deployment artifact with a
training-versus-deployment score comparison; for a regression, the loss and its match to the use, the closure in bins
of true and reconstructed value, and how the correction's uncertainty is propagated.

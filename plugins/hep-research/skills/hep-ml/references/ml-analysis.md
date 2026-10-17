# Machine Learning in Experimental Analysis

The physics entry point of this skill. It covers what makes a classifier or regressor usable inside a measurement:
splits, event weights, analysis metrics, decorrelation, systematic-aware training, simulation-to-data differences,
weak supervision, ML unfolding on the training side, and deployment. Model families and BDT practice are in
[multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md); set and jet architectures in
[particle-and-jet-architectures.md](particle-and-jet-architectures.md); space and ground-based astroparticle
detectors in [space-and-astroparticle-ml.md](space-and-astroparticle-ml.md); fast simulation in
[fast-simulation-validation.md](fast-simulation-validation.md); SBI training in [sbi-training.md](sbi-training.md).
Validity of an inference built on a model is hep-statistics'
([ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md)); sample normalization is
hep-measurement' ([weights-normalization.md](../../hep-measurement/references/weights-normalization.md)).

Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on 2026-10-13. They point to the method, not to
a validated recipe for any experiment.

## Task routes

The index of tasks this skill owns that have no row of their own in `SKILL.md`:

| Task | Read |
|---|---|
| Event weights: class balancing and the prior, negative weights (NLO, sWeights, subtraction) | [weights](ml-analysis-weights.md) |
| Mass sculpting and decorrelation; simulation-to-data differences | [decorrelation and systematics](ml-analysis-decorrelation-and-systematics.md) |
| Input validation before training; pre-training freeze, training on data and blinding | [training and data](ml-analysis-training-and-data.md) |
| Validation (overtraining, device and precision migration); deployment in experiment software and triggers | [validation and deployment](ml-analysis-validation-and-deployment.md) |
| ML systematics: which ML uncertainty enters the measurement, systematic-aware training | [uncertainty-and-calibration.md](uncertainty-and-calibration.md) ("When an ML uncertainty is a measurement systematic"); [decorrelation and systematics](ml-analysis-decorrelation-and-systematics.md), "Parameterized and systematic-aware training" |
| Hyperparameter search: grouped or nested cross-validation, seeds, search budget | [training and data](ml-analysis-training-and-data.md), "Hyperparameter search"; [training-at-scale.md](training-at-scale.md) |
| Anomaly detection and weak supervision (CWoLa, CATHODE, autoencoders), training on data | [training and data](ml-analysis-training-and-data.md), "Weak supervision and anomaly detection" and "Training on data and blinding" |
| "Is this improvement real?": ablations, seed variance, model comparison | [ablation-and-design-review.md](ablation-and-design-review.md); `scripts/compare_model_runs.py` |
| Interpretability of a physics model | [interpretability-and-explainability.md](interpretability-and-explainability.md) |
| Reweighting and ML unfolding (OmniFold, DCTR) | [training and data](ml-analysis-training-and-data.md), "ML unfolding (training side)"; the `reweighting` task of the ml-artifact |
| ML tracking and graph networks on hits | [particle-and-jet-architectures.md](particle-and-jet-architectures.md) |

## Splits and leakage

Split by event and production relationships, not merely by random rows. Multiple candidates, systematic variants,
duplicate files, and derived views of an event should remain grouped. Learn preprocessing, feature selection, tuning,
and calibration only from permitted training/validation partitions.

- **Grouping keys that carry correlation:** event (several candidates or jets per event), run or luminosity block,
  detector period or calibration epoch (time-dependent conditions), simulation production and seed, generator
  parameter point (for parameterized networks), and test-beam run.
- **k-fold by event number** (for example `event % k`) is the standard way to use all simulated and data events: each
  event is evaluated by the model that did not see it. Keep the fold assignment deterministic and record it. The same
  rule applies when the classifier is applied to data in a weakly supervised search.
- **Composite keys and strata:** `make_grouped_splits.py --group-column run lumi` keeps each combination whole;
  `--stratify-column label` (or a period) splits each stratum on its own, so a rare class or period reaches every
  split, and lists strata with fewer groups than splits instead of hiding them.
- **Never `random_split` on rows** when a grouping key exists. Build the split from the key, then check it with
  `<plugin root>/skills/hep-ml/scripts/check_split_integrity.py`.

Prevent blinded SR information from leaking through labels, mass windows, normalization, or validation metrics. Weak
supervision and sideband methods require explicit assumptions about contamination and feature independence.

## Analysis metrics

AUC alone is insufficient for optimization or validation. Use metrics computed with the physics weights at the
working point the analysis will use. `assets/hep_metrics.py` implements these in NumPy, with signed weights:

- **Background rejection at fixed signal efficiency**, 1/ε_B at ε_S = 30 %, 50 % or 70 % (or the analysis working
  point). This is the standard tagger figure of merit. It is far more sensitive than AUC in the region that matters.
- **Weighted ROC with signed weights.** Do not clip it. Local non-monotonicity is information about MC statistics.
- **Statistical uncertainty of a weighted efficiency.** For ε = W_pass/W_tot,
  `Var(ε) ≈ [(1−ε)² Σ_pass w² + ε² Σ_fail w²] / W_tot²`. Quote it next to every efficiency; an efficiency from a few
  high-weight events is noise.
- **Expected significance.** Use the Asimov formula `Z_A = sqrt(2[(s+b) ln(1+s/b) − s])` (Cowan, Cranmer, Gross,
  Vitells, EPJC 71 (2011) 1554, arXiv:1007.1727, read 2026-10-14) rather than `s/√b`, which
  overestimates Z unless s ≪ b (by about 7 % at s/b = 0.5). With a background uncertainty, use the version with an
  absolute σ_b. It assumes σ_b comes from an auxiliary Poisson control measurement (b̂ = m/τ, σ_b² = b/τ; G. Cowan,
  "Discovery sensitivity for a counting experiment with background uncertainty", note, 2012). A theory or modeling
  uncertainty is a different assumption; hand it to hep-statistics. Optimizing on observed significance is
  forbidden.
- **Effective MC statistics after selection.** Report `N_eff = (Σw)²/Σw²` per region. A selection that leaves a few
  effective events has an unusable template.
- **Final-result sensitivity.** The expected uncertainty or limit of the full fit (hep-statistics) is the metric
  that matters. Use the cheaper ones above to compare candidates, then confirm the choice on the final quantity.

PR-AUC, F1 and accuracy depend on the class prior; with arbitrary training normalization they carry no physics
meaning. Do not report them for a selection classifier.

## Further reading

Feickert & Nachman, "A Living Review of Machine Learning for Particle Physics", arXiv:2102.02770 (continuously
updated), is the index to the literature. Check it for newer methods before claiming a method is the current one.

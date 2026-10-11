# Machine Learning in Experimental Analysis

## Splits and leakage

Split by event and production relationships, not merely by random rows. Multiple candidates, systematic variants, duplicate files, and derived views of an event should remain grouped. Learn preprocessing, feature selection, tuning, and calibration only from permitted training/validation partitions.

Prevent blinded SR information from leaking through labels, mass windows, normalization, or validation metrics. Weak supervision and sideband methods require explicit assumptions about contamination and feature independence.

## Weights and objectives

Class-balancing weights differ from physics normalization. Evaluate yields and construct templates with the formal event weights. Ordinary cross-entropy with signed weights may not define the usual well-behaved risk minimization. Do not simply take absolute weights without evaluating bias; choose a suitable method and retain signed physics yields.

AUC alone is insufficient for optimization. Consider effective MC statistics after rejection, systematic effects, score-shape modeling, expected sensitivity, and fit robustness. Do not choose hyperparameters using observed significance.

## Validation

Inspect performance, calibration, overtraining, domain shift, score-tail populations, and nuisance dependence by process, era, and phase space. Use independent samples or event-level resampling for uncertainty estimates. Standard unweighted KS p-values may not apply to weighted train/test distributions; compare weighted empirical CDFs directly with a weighted KS statistic, or use a permutation/bootstrap test that resamples with the event weights as importance weights, rather than dropping the overtraining check.

Check mass sculpting after score selections. If the analysis fits a mass spectrum, validate the background parameterization in each score category. Validate decorrelation and its performance tradeoffs on independent samples; using an adversarial objective does not itself establish independence.

When the classifier score becomes an observable, propagate systematic changes through features, inference, and category migration. Preserve preprocessing, feature order, units, model parameters, versions, and inference checksums. Compare training and deployment scores for identical events.

Device and precision change the numbers too. The same model and seed give slightly different weights and scores on CPU and GPU, on different GPU types or torch builds, and in fp32 versus mixed precision (training losses differing at the 0.1 % level were observed in TORCH-GPU-RUN). When a score is cut on, events near the cut move between categories. Either evaluate in the build, device and precision the model was validated in, or measure the migration on identical events across the deployment environments and treat it as a systematic. Never mix training and inference environments silently.

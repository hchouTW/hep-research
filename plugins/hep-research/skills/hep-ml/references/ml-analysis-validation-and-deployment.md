# Validation and deployment of an analysis classifier

Part of [ml-analysis.md](ml-analysis.md), the hep-ml entry reference for machine learning in an analysis
(read its splits and metrics first). Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on
2026-10-13; they point to the method, not to a validated recipe for any experiment.

## Validation

Inspect performance, calibration, overtraining, domain shift, score-tail populations, and nuisance dependence by
process, era, and phase space. Use independent samples or event-level resampling for uncertainty estimates.
Standard unweighted KS p-values may not apply to weighted train/test distributions. Compare weighted empirical CDFs
directly with a weighted KS statistic, or use a permutation or bootstrap test that resamples with the event weights
as importance weights, rather than dropping the overtraining check.

Check mass sculpting after score selections (see [mass sculpting and decorrelation](ml-analysis-decorrelation-and-systematics.md#mass-sculpting-and-decorrelation)). If the analysis fits a mass spectrum, validate the
background parameterization in each score category.

When the classifier score becomes an observable, propagate systematic changes through features, inference, and
category migration. Preserve preprocessing, feature order, units, model parameters, versions, and inference
checksums. Compare training and deployment scores for identical events.

Device and precision change the numbers too. The same model and seed give slightly different weights and scores on
CPU and GPU, on different GPU types or torch builds, and in fp32 versus mixed precision. Training losses differing at
the 0.1 % level were observed in the plugin's GPU validation runs (`<plugin root>/VALIDATION.md`, entry
TORCH-GPU-RUN). When a score is cut on, events near the cut move
between categories. Either evaluate in the build, device and precision the model was validated in, or measure the
migration on identical events across the deployment environments and treat it as a systematic. Never mix training
and inference environments silently.

## Deployment in experiment software and triggers

- **Offline frameworks:** export the frozen model to a framework the experiment supports, for example ONNX Runtime
  or ROOT's TMVA SOFIE ([export-and-deployment.md](export-and-deployment.md)). Then verify score agreement on
  identical events: the same inputs, preprocessing and feature order must give the same score within a stated
  tolerance.
- **Hardware triggers:**
  - **Constraints:** the latency budget (sub-microsecond to microseconds at a first-level trigger) and the
    resources force small models, fixed-point arithmetic, pruning and quantization-aware training.
  - **hls4ml** translates networks to FPGA firmware (Duarte et al., JINST 13 (2018) P07027, arXiv:1804.06913).
  - **Validation:**
    - compare the bit-accurate emulation with the floating-point model on identical events;
    - measure the trigger efficiency turn-on in data with an orthogonal trigger;
    - treat a firmware/emulation difference as a trigger systematic.

# Simulation-Based Inference: the Training Side

Training neural estimators for inference when the likelihood is only available through a simulator. The validity of
the resulting intervals, coverage claims and the final statistical result belong to hep-statistics
([ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md)). This file covers choosing
and training the estimator, and the diagnostics the ML side must hand over. The overview is
[scientific-machine-learning.md](scientific-machine-learning.md). Citations were looked up on INSPIRE-HEP or arXiv
on 2026-10-13. For a review of the field, see Cranmer, Brehmer, Louppe, PNAS 117 (2020) 30055, arXiv:1911.01429.

## Choosing the estimator

| Estimator | Learns | Use when | Watch |
|---|---|---|---|
| NRE (ratio) | r(x; θ₀, θ₁) or r(x, θ) via a classifier | Frequentist tests, likelihood scans, NSBI in collider analyses | Calibration of the classifier output (Cranmer, Pavez, Louppe, arXiv:1506.02169) |
| NPE (posterior) | p(θ\|x) with a conditional flow | Bayesian analysis; fast amortized posteriors | The training prior is baked in; change it by importance reweighting with the prior ratio (within its support) or retrain |
| NLE (likelihood) | p(x\|θ) with a conditional flow | Combining many observations or experiments; MCMC on top | Needs low-dimensional x or a summary; MCMC diagnostics are still needed |

- **Per-event and per-dataset inference.** For per-event x, a ratio or likelihood estimate multiplies over events;
  errors multiply too, so per-event calibration matters more than for one-shot inference.
- **Summary statistics.** If x is high-dimensional, either learn a summary jointly with the estimator or use a
  physics summary. A learned summary that discards information costs sensitivity, not validity. Validity costs come
  from miscalibration.

## Training

- **Parameter sampling defines the training domain.** Sample θ (and nuisance parameters ν) over a range that
  comfortably contains the region the inference will explore. For NPE that sampling distribution *is* the prior.
  For NRE and NLE, it only sets where the estimator is reliable; record it, and treat queries outside it as
  extrapolation.
- **Nuisance parameters.** Include ν as simulator parameters and either learn them jointly (then marginalize or
  profile) or parameterize the estimator in ν. Learning only at nominal ν and adding systematics afterwards is not
  equivalent.
- **Simulation budget.** Hold out simulations at parameter points not used in training, for the closure checks.
  Split by parameter point and simulation seed.
- **Ensembles.** Train several estimators (different seeds, data subsets). Averaging reduces variance, and the spread
  is a method uncertainty to hand over. Balanced NRE pushes estimators towards conservative, not overconfident,
  posteriors (Delaunoy et al., arXiv:2208.13624).
- **Event weights.** Signed simulation weights need the treatment in [ml-analysis.md](ml-analysis.md); for ratio
  estimation with signed weights, see Drnevich et al., arXiv:2410.10216.

## Diagnostics to hand over

1. **Ratio calibration** (NRE): with r = p₁/p₀, the identities E₀[r] = 1 and E₁[1/r] = 1 on held-out data, plus
   the classifier's reliability, with the power of that test stated. `hep-statistics/scripts/ratio_estimation.py` is an
   experimental starting point.
2. **Closure on a known problem:** a toy where the likelihood is analytic, processed by the same pipeline.
3. **Posterior calibration** (NPE/NLE):
   - **Simulation-based calibration (SBC):** rank histograms should be uniform (Talts et al., arXiv:1804.06788).
   - **TARP**, an expected-coverage test that needs only samples from the estimated posterior (Lemos et al.,
     arXiv:2302.03026).
   - **Coverage as a function of θ:** report it per θ, because averaging over the prior can hide regions that fail.
4. **Simulator misspecification:** posterior or likelihood predictive checks against data in control regions. SBC
   cannot detect a wrong simulator; this check can.
5. **The handover:** these diagnostics, the training domain, and the ensemble spread go to hep-statistics in the
   `ml-artifact`. The coverage claim for the final interval is made there, with toys through the full pipeline.

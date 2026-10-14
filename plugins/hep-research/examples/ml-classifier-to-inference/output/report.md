# J9 report: classifier to signal-strength fit (SYNTHETIC, ILLUSTRATIVE)

**Status: synthetic.** SYNTHETIC and ILLUSTRATIVE: invented samples, pseudo-data not observed data; describes no experiment. Profile bound: `experiment:synthetic-collider` (illustrative); its generator and detector modules are not used. The pseudo-data are drawn from the same invented model and are labelled pseudo-data, never observed data.

Reproduce: `python3 examples/ml-classifier-to-inference/run.py --seed 20261013 --toys 1000` (from the plugin root; trainer `numpy`). Intermediate files are written to `work/` (not committed).

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Grouped split by run | check_split_integrity.py --strict passes | pass |
| Row-level split of the same rows | caught as leakage (exit 1) | pass (24 runs leak) |
| Calibration (fit on val, evaluated on test) | ECE after < 0.03 | pass (ECE 0.0159 -> 0.0176, floor 0.0158) |
| Domain-shift check | detects the injected pt_miss shift | pass |
| Domain flags on pseudo-data | outside fraction < 0.05 | pass (9/357 outside, 0 sparse) |
| Asimov closure of mu | abs(mu_hat - 1.0) < 0.001 | pass (mu_hat 1.000000) |
| Toys: pull mean | abs < 0.15 | pass (-0.033) |
| Toys: pull width | in (0.9, 1.1) | pass (1.028) |
| Toys: 68% interval coverage | in (0.635, 0.73) | pass (0.660, 1000 toys) |
| Pseudo-data fit | within 3.0 sigma of mu_true | pass |
| ml-artifact | valid, no unresolved finding | pass |
| statistical-result | valid, links the ml-artifact by id and sha256 | pass |

## Result on the pseudo-data

mu = 1.331 +0.293 -0.277 (68.27% profile-likelihood interval; true mu = 1.0); saturated goodness of fit 3.06 / 6 (asymptotic p = 0.80). Asimov expected uncertainty +0.271 -0.257.

## Classifier (held-out test split, physics weights)

Weighted AUC 0.9218 (validation 0.9179). Working point fixed on validation at signal efficiency 0.5: on test eff_S = 0.463, eff_B = 0.0250 ± 0.0067 (rejection 40.0), Asimov significance 5.26 for the counting experiment at that cut. These are ML metrics; the physics validation is the effect on mu above.

Weights: 600 negative-weight background events (10.0% of background MC). Training weights are class-balanced and signed; metrics, calibration and templates use the physics weights unchanged. The classifier is calibrated to the physics class ratio (prior correction r = 0.1333) and then by temperature T = 0.9773, fitted on `work/val_scores.csv` and evaluated on `work/test_scores.csv`. ECE (10 equal-width bins, weighted) 0.0159 before and 0.0176 after the temperature, against a finite-sample floor of 0.0158: differences at the level of the floor are not resolved by this test sample. The calibration is therefore recorded as a no-op within the floor, and the ml-artifact declares output_semantics score: the template fit uses the transformed score as a monotone variable and never reads it as a probability.

## Domain shift

| Variable | KS D (simulation vs control) | noise floor (95%) | above floor |
|---|---|---|---|
| score | 0.0256 | 0.0225 | yes |
| m_ll | 0.0230 | 0.0336 | no |
| acop | 0.0326 | 0.0353 | no |
| pt_miss | 0.0560 | 0.0241 | yes |
| cos_theta | 0.0221 | 0.0236 | no |

The control sample was built with pt_miss x 1.1; the measured scale (control over simulation mean) is 1.0987. Rebuilding the background template at that scale moves mu on Asimov data by -0.1075. The fit carries that shift as the Gaussian-constrained shape nuisance `theta_pt_miss_scale` (background template at the measured scale as +1 sigma), so the ml-artifact records the domain-shift outcome bounded-by-nuisance; the pseudo-data are generated without the shift.

## Limitations (by construction)

- One invented model generates simulation, control sample and pseudo-data; mismodeling of the simulation is studied only through the injected scale shift.
- The signal template's MC statistics are not in the likelihood (only the background's, Barlow-Beeston-lite).
- Templates are normalized to the full MC by event counts per class; the luminosity and cross sections carry no uncertainty.
- Passing these checks shows the chain is internally consistent on synthetic data, nothing about a real analysis.

Figure: `scores_and_calibration.png`. Artifacts: `artifacts/ml_artifact.json`, `artifacts/statistical_result.json` (status `synthetic`).

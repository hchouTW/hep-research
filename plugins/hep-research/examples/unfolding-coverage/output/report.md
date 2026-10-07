# Unfolding bias and coverage (SYNTHETIC)

4000 seeded Poisson toys (seed 20261007); nominal 68% coverage 0.6827 with binomial standard error 0.00735902. Model truth: slope 0.35; test truth: slope 0.25, unfolded with the model-truth weights.

| Setting | mean rel. sigma | max abs(bias)/sigma (model) | min coverage (model) | max abs(bias)/sigma (test) | min coverage (test) |
|---|---|---|---|---|---|
| inversion (TSVD, all 10 singular values) | 0.297571 | 2.39114e-13 | 0.67725 | 2.47042e-13 | 0.67525 |
| TSVD, 6 singular values | 0.0796463 | 17.5404 | 0.0 | 13.0141 | 0.0 |
| Tikhonov 1e-4 | 0.268536 | 0.00987658 | 0.67475 | 0.00444603 | 0.67325 |
| Tikhonov 1e-3 | 0.181479 | 0.0899997 | 0.67375 | 0.0408596 | 0.67825 |
| Tikhonov 1e-2 | 0.0966069 | 0.576948 | 0.599 | 0.260026 | 0.65625 |
| Tikhonov 1e-1 | 0.0553899 | 1.69128 | 0.23775 | 0.809025 | 0.537 |

Criteria: inversion_unbiased pass, inversion_covers pass, toy_bias_matches_analytic pass, tikhonov_sigma_falls pass, tikhonov_bias_rises pass

coverage: fraction of toys whose interval x_j +- sigma_j (sigma from the toy's own counts) contains the true bin content; the regularized settings undercover because of their bias, which is the systematic an analysis has to assign or reduce; the response is exactly known here, so response uncertainty adds to all of this in practice; D'Agostini iterations are not in this example (use core/stats/unfolding_diagnostics.py closure, whose sigma comes from the toys)

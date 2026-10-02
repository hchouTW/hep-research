# J2 detector study (SYNTHETIC, illustrative profile)

SYNTHETIC and ILLUSTRATIVE: invented detector model; describes no experiment. Profile loaded: `experiment:synthetic-collider` only. Seed 20261005, 200 replicate samples.

| Quantity | Result | Expected (independent) |
|---|---|---|
| Constant cos theta resolution | 0.01974 ± 0.00012 (chi2 1.92/4, p = 0.751) | 0.02 (configured) |
| Efficiency vs bin-averaged model | chi2 2.64/5, p = 0.755 | model e0 - e1 c^4 |
| Replicate pulls of the fitted width | mean -0.090, width 1.032 | 0 and 1 |

Criteria: width_closure pass, width_constant_model pass, efficiency_vs_model pass, replicate_mean_pull pass, replicate_pull_width pass, contracts pass.

Limits: the detector is invented and Gaussian; the large-sample width uncertainty is checked by replicates only for this sample size; bins stop at |cos theta| = 0.9 so the acceptance edge does not truncate the residuals. This shows the J2 chain and its contracts, not any detector's performance.

Reproduce: `python3 examples/detector-resolution/run_j2.py --replicates 200 --seed 20261005`

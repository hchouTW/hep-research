# Path C report: standalone tree-level QED benchmark

Theory only: profile `theory:qed-benchmark`, no experiment profile, no detector, data or blinding fields, no GPU and no commercial CAS. Profile files read: `profiles/theory/qed-benchmark/benchmarks/path-c.json`, `profiles/theory/qed-benchmark/conventions.json`, `profiles/theory/qed-benchmark/evidence/claims.json`, `profiles/theory/qed-benchmark/evidence/sources.json`, `profiles/theory/qed-benchmark/profile.json`.

Reproduce: `python3 examples/qed-prediction/run.py` (from the plugin root, D5 environment).

## Result

At sqrt(s) = 10 GeV (s = 100 GeV^2): sigma = 868.0 pb, and sigma(|cos theta| < 0.9) = 744.1 pb. d sigma / d cos theta = (3/8) sigma (1 + cos^2 theta). The reference constant 86.8 nb GeV^2 is rounded to three significant figures, a relative uncertainty of 5.8e-04. Missing higher orders and Z exchange are not quantified.

## Status

Derivation status: `analytic-derivation`. Exact at tree level under the listed assumptions; SymPy steps are trusted, not formally verified. Not a formal proof. The result agrees symbolically with PDG eqs. 51.2 and 51.3 (section 51.2, read 2026-10-02 at page level). Numerical agreement below is corroboration, not proof.

| Check | Result |
|---|---|
| squared_amplitude_massless_equals_e4_1_plus_c2 | pass |
| dsigma_domega_equals_ref_eq_51_2 | pass |
| sigma_beta_to_1_equals_ref_eq_51_3 | pass |
| sigma_general_beta_equals_beta_3_minus_beta2_over_2 | pass |
| shape_normalized_equals_3_8_1_plus_c2 | pass |
| forward_backward_asymmetry_zero | pass |
| dsigma_dcos_even_in_c | pass |
| threshold_sigma_vanishes_linearly_in_beta | pass |
| integral_over_full_range_equals_sigma | pass |
| bins_sum_to_sigma | pass |
| even_in_cos_theta | pass |
| positive | pass |
| forward_to_central_ratio_is_2 | pass |
| scales_as_1_over_s | pass |
| trapezoid_second_order | pass |
| simpson_exact_for_quadratic | pass |
| quad_agrees | pass |
| contract artifacts | pass |
| no experiment resource read | pass |

Trapezoid observed order on [-1, 1]: 2.00, 2.00, 2.00, 2.00, 2.00, 2.00, 2.00.

Checks not run: see `artifacts/theory_spec.json` (`checks_not_run`) and the derivation record.

Figure: `dsigma_dcos_prediction.png`. Artifacts: `artifacts/theory_spec.json`, `artifacts/prediction.json`.

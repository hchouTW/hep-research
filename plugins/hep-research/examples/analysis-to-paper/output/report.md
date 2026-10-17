# Analysis to paper (E-4)

SYNTHETIC and ILLUSTRATIVE: invented signal and background; describes no experiment.

Score: Bayes-optimal log-likelihood ratio (fallback: no ML backend used; --with-bdt runs train_bdt.py). AUC 0.8453 vs Bayes 0.8461 (pull -0.31). mu = 1.04 +- 0.06 (PDG rounding of 1.03508 +- 0.0581633).

- auc_within_statistical_range_of_bayes_limit: pass
- mu_consistent_with_injected_1: pass
- macros_round_trip_to_the_artifact: pass
- table_equals_the_record: pass
- hepdata_values_equal_the_artifacts: pass
- draft_numbers_consistent: pass
- roofit_step_ran_or_exited_3: pass
- synthetic_watermark_in_macros: pass

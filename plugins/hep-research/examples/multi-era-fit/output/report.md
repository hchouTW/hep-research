# Multi-era fit (E-3, first part)

SYNTHETIC and ILLUSTRATIVE: fictional toy spectrometer; describes no experiment.

Two eras of a fictional spectrometer; e2 adds a ninth layer (resolution terms {'e1': {'a_per_gv': 0.000516755, 'b': 0.0231316}, 'e2': {'a_per_gv': 0.000220659, 'b': 0.0160032}}).

| Check | Result |
|---|---|
| c1_period_split_across_files_counted_once | pass |
| m1_partials_merged_equal_single_run | pass |
| d5_fold_of_mix_equals_sum_of_era_folds | pass |
| s1_no_difference_is_consistent | pass |
| s1_injected_offset_is_caught | pass |
| joint_fit_coverage_0p68_pm_0p03 | pass |
| runtime_below_60_s | pass |

Joint-fit coverage of the +-1 sigma intervals: 0.6887 over 6000 cells (1000 toys).
S1 without a difference: chi2 10.434 / 6, p 0.1075; with a 5% offset in e2: chi2 120.78, p 1.117e-23.

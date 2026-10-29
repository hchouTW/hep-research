# Private author notes

All material is synthetic. Public directories were created in system-random shuffled order; IDs come from secrets.token_hex(4). No public type manifest exists.

## Verification plan
Generate all required files; verify each written result; test each single correction for materiality; check fully corrected gold; establish missing-input witnesses; audit public schemas and word counts; run all 16 standalone scripts. Only the standard library is used.

O-compute is supported for every fully supplied case, including planted statistical errors: the stated numbers implement the written method. O-stat is violated for C01, supported for C02/C04, and undetermined for C03 where final scale-dependent numbers cannot be established without the external input. C04 includes an explicit valid consistency check, but the prescribed O-stat/O-compute plan does not establish coverage of REQ-2. Do not treat an unexamined requirement as a defect.

## Instances
- xe0330e8e (C02): Correct control. Unusual representation.
- xfb593672 (C03): The positive exact run gain from the external calibration ledger.
- x4fbb5c80 (C01): The independent transfer calibration has a nonzero error; its delta-method contribution is control squared times transfer_error squared.; The independent Poisson reference count fluctuates; its derivative contribution must be included in the ratio variance.
  Multi-defect case; single-repair paths retaining downstream differences: 1, 2. Gold corrected_values always describe the full repair, not a single repair.
- xb885e462 (C04): Correct control. 
- xc5b7a1ca (C01): The stated Pearson construction requires expected counts in the denominators; using observed counts changes the statistic and its tail.; A fixed-total multinomial with three categories and no fitted shape parameters has two independent contrasts, hence two degrees of freedom.
  Multi-defect case; single-repair paths retaining downstream differences: 1, 2. Gold corrected_values always describe the full repair, not a single repair.
- x5309ca4d (C02): Correct control. Unusual representation.
- x48d287a1 (C02): Correct control. 
- x87c5cae5 (C01): The design-based variance for sampling without replacement requires the finite-population factor 1-sampled/population; omitting it inflates the reported uncertainty.
- x9e0a85ed (C01): The continuum count is already thinned; the transfer must divide by off_keep as well as using the width ratio. This changes subtraction and its downstream rate.; The finite independent continuum count contributes alpha squared times off to the variance; treating it as fixed discards this sampling term.
  Multi-defect case; single-repair paths retaining downstream differences: 1, 2. Gold corrected_values always describe the full repair, not a single repair.
- x66bbe2ee (C01): Both tracks must pass, so the event efficiency is the square of the per-track efficiency under the stated independence model.; Both independent parent decays must enter the selected mode, so the branching normalization is branch_fraction squared.
  Multi-defect case; single-repair paths retaining downstream differences: 1, 2. Gold corrected_values always describe the full repair, not a single repair.
- xc55857c5 (C04): Correct control. 
- xb67e4768 (C01): The stored response maps true yields to reconstructed yields; invert response itself, rather than its transpose.; Each unfolded yield depends on both reconstructed counts; the propagated variance must include both squared inverse-matrix coefficients.
  Multi-defect case; single-repair paths retaining downstream differences: 1, 2. Gold corrected_values always describe the full repair, not a single repair.
- x83b853ee (C01): The reported gamma posterior mean uses the mode formula; the mean is posterior_shape/posterior_rate.
- x16abda08 (C02): Correct control. 
- x82e314ad (C03): The exact run acceptance from the external geometry record, in (0,1].
- xfa9a973b (C01): The trials-factor linear expression is only a union bound or small-tail approximation; the exact independent-trial probability is 1-(1-local_p)^windows.

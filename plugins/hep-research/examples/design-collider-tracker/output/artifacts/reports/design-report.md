# Design report: collider-tracker-v1

Derived by contracts/design.py from `design-spec.v1.json` (spec version 1); no verdict is hand-written.

**Gate flags (open review gates):** gate.H1_missing, gate.H2_missing, gate.H3_missing.
**Baseline:** draft. Only a valid human H4 (design-baseline) record sets it, taken after the gates above are clear, over this report, the evaluations it used and one disposition per inconclusive driving requirement of a candidate that survives screening; until then no requirement is reviewed (MAT-04). The record's actor kind is self-declared, so the review axis is advisory (LIM-01).

The adequacy table is an initial default until physics review: every pass is provisional.

| Requirement | Candidates | Result | Reason codes | Lowest fidelity (deciding evaluations) | Status | Missing for compliance | Proposed disposition |
|---|---|---|---|---|---|---|---|
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-A | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-B | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-P | fail | bound.excludes | F1 | synthetic | none: excluded by an optimistic bound; change the candidate or the requirement | - |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-A | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan at F4 or above or calorimeter-constant-term-measurement at F4 or above (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-B | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan at F4 or above or calorimeter-constant-term-measurement at F4 or above (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-P | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan at F4 or above or calorimeter-constant-term-measurement at F4 or above (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | none: the candidate is screened out |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | none: the candidate is screened out |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | none: the candidate is screened out |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | none: the candidate is screened out |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | none required at H4: derived requirement (RPT-05, MAT-04 d) |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | none: the candidate is screened out |
| collider-tracker-v1:CON-MASS-001 (hard) | collider-tracker-v1:cand-A | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| collider-tracker-v1:CON-MASS-001 (hard) | collider-tracker-v1:cand-B | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| collider-tracker-v1:CON-MASS-001 (hard) | collider-tracker-v1:cand-P | pass (provisional) | estimate.decides | F1 | synthetic | - | - |

## Evaluations used and skipped

- collider-tracker-v1:REQ-TRK-001 / collider-tracker-v1:cand-A: used collider-tracker-v1:CALC-TRK-A (row 11, bound.direction)
- collider-tracker-v1:REQ-TRK-001 / collider-tracker-v1:cand-B: used collider-tracker-v1:CALC-TRK-B (row 11, bound.direction)
- collider-tracker-v1:REQ-TRK-001 / collider-tracker-v1:cand-P: used collider-tracker-v1:CALC-TRK-P (row 10, bound.excludes)
- collider-tracker-v1:REQ-ECAL-001 / collider-tracker-v1:cand-A: used collider-tracker-v1:CALC-ECAL-A (row 11, bound.direction)
- collider-tracker-v1:REQ-ECAL-001 / collider-tracker-v1:cand-B: used collider-tracker-v1:CALC-ECAL-B (row 11, bound.direction)
- collider-tracker-v1:REQ-ECAL-001 / collider-tracker-v1:cand-P: used collider-tracker-v1:CALC-ECAL-P (row 11, bound.direction)
- collider-tracker-v1:REQ-HCAL-001 / collider-tracker-v1:cand-A: skipped collider-tracker-v1:EST-HCAL-A (row 1, capability.unavailable)
- collider-tracker-v1:REQ-HCAL-001 / collider-tracker-v1:cand-B: skipped collider-tracker-v1:EST-HCAL-B (row 1, capability.unavailable)
- collider-tracker-v1:REQ-HCAL-001 / collider-tracker-v1:cand-P: skipped collider-tracker-v1:EST-HCAL-P (row 1, capability.unavailable)
- collider-tracker-v1:REQ-TRG-001 / collider-tracker-v1:cand-A: skipped collider-tracker-v1:EST-TRG-A (row 1, capability.unavailable)
- collider-tracker-v1:REQ-TRG-001 / collider-tracker-v1:cand-B: skipped collider-tracker-v1:EST-TRG-B (row 1, capability.unavailable)
- collider-tracker-v1:REQ-TRG-001 / collider-tracker-v1:cand-P: skipped collider-tracker-v1:EST-TRG-P (row 1, capability.unavailable)
- collider-tracker-v1:REQ-PU-001 / collider-tracker-v1:cand-A: skipped collider-tracker-v1:EST-PU-A (row 1, capability.unavailable)
- collider-tracker-v1:REQ-PU-001 / collider-tracker-v1:cand-B: skipped collider-tracker-v1:EST-PU-B (row 1, capability.unavailable)
- collider-tracker-v1:REQ-PU-001 / collider-tracker-v1:cand-P: skipped collider-tracker-v1:EST-PU-P (row 1, capability.unavailable)
- collider-tracker-v1:REQ-CONT-001 / collider-tracker-v1:cand-A: skipped collider-tracker-v1:EST-CONT-A (row 1, capability.unavailable)
- collider-tracker-v1:REQ-CONT-001 / collider-tracker-v1:cand-B: skipped collider-tracker-v1:EST-CONT-B (row 1, capability.unavailable)
- collider-tracker-v1:REQ-CONT-001 / collider-tracker-v1:cand-P: skipped collider-tracker-v1:EST-CONT-P (row 1, capability.unavailable)
- collider-tracker-v1:CON-MASS-001 / collider-tracker-v1:cand-A: used collider-tracker-v1:CALC-MASS-A (row 16, estimate.decides)
- collider-tracker-v1:CON-MASS-001 / collider-tracker-v1:cand-B: used collider-tracker-v1:CALC-MASS-B (row 16, estimate.decides)
- collider-tracker-v1:CON-MASS-001 / collider-tracker-v1:cand-P: used collider-tracker-v1:CALC-MASS-P (row 16, estimate.decides)

## Screening, orphan runs, comparison

- collider-tracker-v1:cand-A: not excluded by screening (no driving requirement or hard constraint fails)
- collider-tracker-v1:cand-B: not excluded by screening (no driving requirement or hard constraint fails)
- collider-tracker-v1:cand-P: screened out by the verdicts above, not by a review decision (collider-tracker-v1:REQ-TRK-001 fails)
- orphan runs: none
- comparison basis on mass-budget at 95% one-sided CL: does not hold (a difference with its uncertainty exceeds the tolerance)
  - collider-tracker-v1:cand-B vs collider-tracker-v1:cand-A (collider-tracker-v1:CALC-MASS-B vs collider-tracker-v1:CALC-MASS-A; 1-sigma budget-row uncertainties, linear within a candidate, in quadrature across the pair): difference 5020 + one-sided uncertainty 2343.27 against tolerance 999.5 (mass-budget); no item is the same subsystem with the same budget row in both: does not hold
- ranking: refused: comparison_basis does not hold: a difference with its uncertainty exceeds the tolerance (ART-15, RPT-07); collider-tracker-v1:cand-A, collider-tracker-v1:cand-B have no non-optimistic, current expected-precision evaluation (CHN-06)

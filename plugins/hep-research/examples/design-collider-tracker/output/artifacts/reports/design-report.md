# Design report: collider-tracker-v1

Derived by contracts/design.py from `design-spec.v1.json` (spec version 1); no verdict is hand-written.

**Gate flags:** gate.H1_missing, gate.H2_missing, gate.H3_missing

The adequacy table is an initial default until physics review: every pass is provisional.

| Requirement | Candidates | Result | Reason codes | Lowest fidelity (deciding evaluations) | Status | Missing for compliance | Proposed disposition |
|---|---|---|---|---|---|---|---|
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-A | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-B | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-TRK-001 (driving) | collider-tracker-v1:cand-P | fail | bound.excludes | F1 | synthetic | none: excluded by an optimistic bound; change the candidate or the requirement | - |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-A | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan or calorimeter-constant-term-measurement (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-B | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan or calorimeter-constant-term-measurement (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-ECAL-001 (driving) | collider-tracker-v1:cand-P | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | calorimeter-calibration-plan or calorimeter-constant-term-measurement (required for compliance, ADQ-02); calorimeter-energy-resolution at F4 or above (compliance threshold) | next-study |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-HCAL-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | hadronic-energy-resolution at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-TRG-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | trigger-efficiency at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-PU-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | pileup-robustness at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-A | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-B | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | - |
| collider-tracker-v1:REQ-CONT-001 (derived) | collider-tracker-v1:cand-P | inconclusive | capability.unavailable | undetermined (no evaluation used) | synthetic | shower-containment at F4 or above (compliance threshold) | - |
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

- collider-tracker-v1:cand-A: not screened out
- collider-tracker-v1:cand-B: not screened out
- collider-tracker-v1:cand-P: screened out (collider-tracker-v1:REQ-TRK-001 fails)
- comparison basis: does not hold (a difference with its uncertainty exceeds the tolerance)
- ranking: refused: comparison_basis does not hold: a difference with its uncertainty exceeds the tolerance (ART-15, RPT-07)

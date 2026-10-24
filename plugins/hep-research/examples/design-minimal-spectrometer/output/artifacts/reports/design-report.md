# Design report: j15-v1

Derived by contracts/design.py from `design-spec.v1.json` (spec version 1); no verdict is hand-written.

**Gate flags (open review gates):** gate.H1_missing, gate.H2_missing, gate.H3_missing.
**Baseline:** draft. Only a valid human H4 (design-baseline) record sets it, taken after the gates above are clear, over this report, the evaluations it used and one disposition per inconclusive driving requirement of a candidate that survives screening; until then no requirement is reviewed (MAT-04). The record's actor kind is self-declared, so the review axis is advisory (LIM-01).

The adequacy table is an initial default until physics review: every pass is provisional.

| Requirement | Candidates | Result | Reason codes | Lowest fidelity (deciding evaluations) | Status | Missing for compliance | Proposed disposition |
|---|---|---|---|---|---|---|---|
| j15-v1:REQ-TRK-001 (driving) | j15-v1:cand-N4 | pass (provisional) | estimate.decides | F4 | synthetic, unvalidated | - | - |
| j15-v1:REQ-TRK-001 (driving) | j15-v1:cand-N6 | inconclusive | bound.direction, estimate.decides | undetermined (participating down to F1) | synthetic, unvalidated | - | next-study |
| j15-v1:REQ-TRK-001 (driving) | j15-v1:cand-N8 | pass (provisional) | estimate.decides | F4 | synthetic, unvalidated | - | - |
| j15-v1:REQ-TRK-002 (driving) | j15-v1:cand-N4 | inconclusive | fidelity.insufficient | undetermined (participating down to F1) | synthetic, unvalidated | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| j15-v1:REQ-TRK-002 (driving) | j15-v1:cand-N6 | inconclusive | fidelity.insufficient | undetermined (participating down to F1) | synthetic, unvalidated | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| j15-v1:REQ-TRK-002 (driving) | j15-v1:cand-N8 | inconclusive | fidelity.insufficient | undetermined (participating down to F1) | synthetic, unvalidated | momentum-resolution-core at F3 or above (compliance threshold) | next-study |
| j15-v1:REQ-CC-001 (driving) | j15-v1:cand-N4 | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | charge-confusion-data-validation at F4 or above (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of j15-v1:CALC-CC-N4, now F1); rigidity-scale-offset at F5 or above (required for compliance, ADQ-02) | next-study |
| j15-v1:REQ-CC-001 (driving) | j15-v1:cand-N6 | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic, unvalidated | charge-confusion-data-validation at F4 or above (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of j15-v1:CALC-CC-N6, now F1); rigidity-scale-offset at F5 or above (required for compliance, ADQ-02) | next-study |
| j15-v1:REQ-CC-001 (driving) | j15-v1:cand-N8 | inconclusive | bound.direction | undetermined (participating down to F1) | synthetic | charge-confusion-data-validation at F4 or above (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of j15-v1:CALC-CC-N8, now F1); rigidity-scale-offset at F5 or above (required for compliance, ADQ-02) | next-study |
| j15-v1:REQ-CAL-001 (driving) | j15-v1:cand-N4 | inconclusive | - | undetermined (no evaluation used) | - | shower-containment at F4 or above (compliance threshold) | next-study |
| j15-v1:REQ-CAL-001 (driving) | j15-v1:cand-N6 | inconclusive | fidelity.insufficient | undetermined (participating down to F4) | synthetic, unvalidated | shower-containment at F4 or above (compliance threshold) | next-study |
| j15-v1:REQ-CAL-001 (driving) | j15-v1:cand-N8 | inconclusive | - | undetermined (no evaluation used) | - | shower-containment at F4 or above (compliance threshold) | next-study |
| j15-v1:CON-MASS-001 (hard; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N4 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| j15-v1:CON-MASS-001 (hard; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N6 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| j15-v1:CON-MASS-001 (hard; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N8 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| j15-v1:CON-CHAN-001 (soft; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N4 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| j15-v1:CON-CHAN-001 (soft; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N6 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |
| j15-v1:CON-CHAN-001 (soft; scope DES-TRK-001, DES-MAG-001, DES-TOF-001, DES-CAL-001) | j15-v1:cand-N8 | pass (provisional) | estimate.decides | F1 | synthetic | - | - |

## Evaluations used and skipped

- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: used j15-v1:CALC-TOY1-N4 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: used j15-v1:CALC-TR1-N4 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: used j15-v1:SIM-N4-TRK1 (row 16, estimate.decides)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: skipped j15-v1:CALC-TOY100-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: skipped j15-v1:CALC-TR100-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: skipped j15-v1:CALC-TR500-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N4: skipped j15-v1:SIM-N4-TRK100 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: used j15-v1:CALC-TOY1-N6 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: used j15-v1:CALC-TR1-N6 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: used j15-v1:SIM-N6-TRK1-notails (row 11, bound.direction)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: used j15-v1:SIM-N6-TRK1 (row 16, estimate.decides)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: skipped j15-v1:CALC-TOY100-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: skipped j15-v1:CALC-TR100-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: skipped j15-v1:CALC-TR500-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N6: skipped j15-v1:SIM-N6-TRK100 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: used j15-v1:CALC-TOY1-N8 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: used j15-v1:CALC-TR1-N8 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: used j15-v1:SIM-N8-TRK1 (row 16, estimate.decides)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: skipped j15-v1:CALC-TOY100-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: skipped j15-v1:CALC-TR100-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: skipped j15-v1:CALC-TR500-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-001 / j15-v1:cand-N8: skipped j15-v1:SIM-N8-TRK100 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: used j15-v1:CALC-TOY100-N4 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: used j15-v1:CALC-TR100-N4 (row 11, bound.direction)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: used j15-v1:SIM-N4-TRK100 (row 8, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: skipped j15-v1:CALC-TOY1-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: skipped j15-v1:CALC-TR1-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: skipped j15-v1:CALC-TR500-N4 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N4: skipped j15-v1:SIM-N4-TRK1 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: used j15-v1:CALC-TOY100-N6 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: used j15-v1:CALC-TR100-N6 (row 11, bound.direction)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: used j15-v1:SIM-N6-TRK100 (row 8, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: skipped j15-v1:CALC-TOY1-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: skipped j15-v1:CALC-TR1-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: skipped j15-v1:CALC-TR500-N6 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: skipped j15-v1:SIM-N6-TRK1-notails (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N6: skipped j15-v1:SIM-N6-TRK1 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: used j15-v1:CALC-TOY100-N8 (row 12, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: used j15-v1:CALC-TR100-N8 (row 11, bound.direction)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: used j15-v1:SIM-N8-TRK100 (row 8, fidelity.insufficient)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: skipped j15-v1:CALC-TOY1-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: skipped j15-v1:CALC-TR1-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: skipped j15-v1:CALC-TR500-N8 (row 7, domain.mismatch)
- j15-v1:REQ-TRK-002 / j15-v1:cand-N8: skipped j15-v1:SIM-N8-TRK1 (row 7, domain.mismatch)
- j15-v1:REQ-CC-001 / j15-v1:cand-N4: used j15-v1:CALC-CC-N4 (row 11, bound.direction)
- j15-v1:REQ-CC-001 / j15-v1:cand-N6: used j15-v1:CALC-CC-N6 (row 11, bound.direction)
- j15-v1:REQ-CC-001 / j15-v1:cand-N6: skipped j15-v1:SIM-N6-CC500 (row 5, chain.incomplete)
- j15-v1:REQ-CC-001 / j15-v1:cand-N8: used j15-v1:CALC-CC-N8 (row 11, bound.direction)
- j15-v1:REQ-CAL-001 / j15-v1:cand-N6: used j15-v1:SIM-N6-CAL10 (row 8, fidelity.insufficient)
- j15-v1:CON-MASS-001 / j15-v1:cand-N4: used j15-v1:CALC-MASS-N4 (row 16, estimate.decides)
- j15-v1:CON-MASS-001 / j15-v1:cand-N6: used j15-v1:CALC-MASS-N6 (row 16, estimate.decides)
- j15-v1:CON-MASS-001 / j15-v1:cand-N8: used j15-v1:CALC-MASS-N8 (row 16, estimate.decides)
- j15-v1:CON-CHAN-001 / j15-v1:cand-N4: used j15-v1:CALC-CHAN-N4 (row 16, estimate.decides)
- j15-v1:CON-CHAN-001 / j15-v1:cand-N6: used j15-v1:CALC-CHAN-N6 (row 16, estimate.decides)
- j15-v1:CON-CHAN-001 / j15-v1:cand-N8: used j15-v1:CALC-CHAN-N8 (row 16, estimate.decides)

## Screening, orphan runs, comparison

- j15-v1:cand-N4: not excluded by screening (no driving requirement or hard constraint fails)
- j15-v1:cand-N6: not excluded by screening (no driving requirement or hard constraint fails)
- j15-v1:cand-N8: not excluded by screening (no driving requirement or hard constraint fails)
- orphan runs: none
- comparison basis on mass-budget at 95% one-sided CL: holds; basis note: candidates are compared at equal mass: they differ only in the number of 0.3 mm silicon planes (3 kg each, SYNTHETIC), so magnet, TOF and calorimeter items are shared and cancel
  - j15-v1:cand-N6 vs j15-v1:cand-N4 (j15-v1:CALC-MASS-N6 vs j15-v1:CALC-MASS-N4; 1-sigma budget-row uncertainties, linear within a candidate, in quadrature across the pair): difference 6 + one-sided uncertainty 7.11672 against tolerance 96.75 (mass-budget); cancelled as the same subsystem with the same budget row in both: DES-CAL-001, DES-MAG-001, DES-TOF-001: holds
  - j15-v1:cand-N6 vs j15-v1:cand-N8 (j15-v1:CALC-MASS-N6 vs j15-v1:CALC-MASS-N8; 1-sigma budget-row uncertainties, linear within a candidate, in quadrature across the pair): difference 6 + one-sided uncertainty 9.86912 against tolerance 97.05 (mass-budget); cancelled as the same subsystem with the same budget row in both: DES-CAL-001, DES-MAG-001, DES-TOF-001: holds
  - j15-v1:cand-N4 vs j15-v1:cand-N8 (j15-v1:CALC-MASS-N4 vs j15-v1:CALC-MASS-N8; 1-sigma budget-row uncertainties, linear within a candidate, in quadrature across the pair): difference 12 + one-sided uncertainty 8.82721 against tolerance 96.9 (mass-budget); cancelled as the same subsystem with the same budget row in both: DES-CAL-001, DES-MAG-001, DES-TOF-001: holds
- ranking: refused: j15-v1:cand-N4, j15-v1:cand-N6, j15-v1:cand-N8 have no non-optimistic, current expected-precision evaluation (CHN-06)
- Pareto front on expected-precision, mass-budget: refused: j15-v1:cand-N4, j15-v1:cand-N6, j15-v1:cand-N8 have no non-optimistic, current expected-precision evaluation (CHN-06)

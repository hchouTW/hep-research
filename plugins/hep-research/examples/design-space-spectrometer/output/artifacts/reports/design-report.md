# Design report: ams-like-v1

Derived by contracts/design.py from `design-spec.v1.json` (spec version 1); no verdict is hand-written.

**Gate flags:** gate.H1_missing, gate.H2_missing, gate.H3_missing

The adequacy table is an initial default until physics review: every pass is provisional.

| Requirement | Candidates | Result | Reason codes | Lowest fidelity | Status | Missing for compliance |
|---|---|---|---|---|---|---|
| ams-like-v1:REQ-TRK-001 | ams-like-v1:cand-L | inconclusive | bound.direction | undetermined | synthetic | momentum-resolution-core at F3 or above (compliance threshold) |
| ams-like-v1:REQ-TRK-001 | ams-like-v1:cand-P | fail | bound.excludes | F1 | synthetic | momentum-resolution-core at F3 or above (compliance threshold) |
| ams-like-v1:REQ-TRK-001 | ams-like-v1:cand-S | inconclusive | bound.direction | undetermined | synthetic | momentum-resolution-core at F3 or above (compliance threshold) |
| ams-like-v1:REQ-CC-001 | ams-like-v1:cand-L | inconclusive | bound.direction | undetermined | synthetic | charge-confusion-data-validation (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of ams-like-v1:CALC-CC-L, now F1) |
| ams-like-v1:REQ-CC-001 | ams-like-v1:cand-P | fail | bound.excludes | F1 | synthetic | charge-confusion-data-validation (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of ams-like-v1:CALC-CC-P, now F1) |
| ams-like-v1:REQ-CC-001 | ams-like-v1:cand-S | inconclusive | bound.direction | undetermined | synthetic | charge-confusion-data-validation (required for compliance, ADQ-02); charge-confusion-rate at F4 or above (compliance threshold); momentum-resolution-core at F3 or above (in the chain of ams-like-v1:CALC-CC-S, now F1) |
| ams-like-v1:CON-MASS-001 | ams-like-v1:cand-L | pass (provisional) | estimate.decides | F1 | synthetic | - |
| ams-like-v1:CON-MASS-001 | ams-like-v1:cand-P | pass (provisional) | estimate.decides | F1 | synthetic | - |
| ams-like-v1:CON-MASS-001 | ams-like-v1:cand-S | pass (provisional) | estimate.decides | F1 | synthetic | - |

## Evaluations used and skipped

- ams-like-v1:REQ-TRK-001 / ams-like-v1:cand-L: used ams-like-v1:CALC-TRK-L (row 11, bound.direction)
- ams-like-v1:REQ-TRK-001 / ams-like-v1:cand-P: used ams-like-v1:CALC-TRK-P (row 10, bound.excludes)
- ams-like-v1:REQ-TRK-001 / ams-like-v1:cand-S: used ams-like-v1:CALC-TRK-S (row 11, bound.direction)
- ams-like-v1:REQ-CC-001 / ams-like-v1:cand-L: used ams-like-v1:CALC-CC-L (row 11, bound.direction)
- ams-like-v1:REQ-CC-001 / ams-like-v1:cand-P: used ams-like-v1:CALC-CC-P (row 10, bound.excludes)
- ams-like-v1:REQ-CC-001 / ams-like-v1:cand-S: used ams-like-v1:CALC-CC-S (row 11, bound.direction)
- ams-like-v1:CON-MASS-001 / ams-like-v1:cand-L: used ams-like-v1:CALC-MASS-L (row 16, estimate.decides)
- ams-like-v1:CON-MASS-001 / ams-like-v1:cand-P: used ams-like-v1:CALC-MASS-P (row 16, estimate.decides)
- ams-like-v1:CON-MASS-001 / ams-like-v1:cand-S: used ams-like-v1:CALC-MASS-S (row 16, estimate.decides)

## Screening, orphan runs, comparison

- ams-like-v1:cand-L: not screened out
- ams-like-v1:cand-P: screened out (ams-like-v1:REQ-TRK-001 fails; ams-like-v1:REQ-CC-001 fails)
- ams-like-v1:cand-S: not screened out
- comparison basis: holds
- ranking: not-provided: candidate ranking is not part of the first release (OQ-04); it uses only non-optimistic evaluations with the same fidelity vector and denominator (CHN-06)

# Value-gate measurement

Planter: AI-planted. Thresholds: Pass I >= 0.25 N and F <= 1; Shrink 0.10 N <= I < 0.25 N, or I >= 0.25 N with F = 2; Stop I < 0.10 N or F >= 3.

| Arm | N | R | I | F | layer 1 | layer 2 only | checker (any) | outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| main | 28 | 11 | 0 | 1 | 23 | 0 | 7 | Stop |
| sensitivity | 28 | 11 | 0 | 1 | 23 | 0 | 7 | Stop |

Incremental detections: none.
False-positive refactors: R04.
Missed by every layer: E12, E13, E24, E25, E27.

| Case | Kind | Category | L1 | L2 | Checker | Checker why | Sens. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | error | C01 | x | x | x | new violated | x |
| E02 | error | C01 | x | x | x | new unverified naming the defect | x |
| E03 | error | C02 | x |  |  |  |  |
| E04 | error | C02 | x |  |  |  |  |
| E05 | error | C03 | x | x |  |  |  |
| E06 | error | C03 | x | x |  |  |  |
| E07 | error | C04 | x |  |  |  |  |
| E08 | error | C04 | x |  |  |  |  |
| E09 | error | C04 | x |  |  |  |  |
| E10 | error | C05 | x |  |  |  |  |
| E11 | error | C05 | x |  | x | new violated | x |
| E12 | error | C06 |  |  |  |  |  |
| E13 | error | C06 |  |  |  |  |  |
| E14 | error | C07 | x |  |  |  |  |
| E15 | error | C07 | x |  |  |  |  |
| E16 | error | C07 | x |  |  |  |  |
| E17 | error | C08 | x |  |  |  |  |
| E18 | error | C08 | x | x | x | refused | x |
| E19 | error | C09 | x |  | x | new unverified naming the defect | x |
| E20 | error | C09 | x |  |  |  |  |
| E21 | error | C09 | x |  | x | new unverified naming the defect | x |
| E22 | error | C10 | x |  | x | new violated | x |
| E23 | error | C10 | x |  |  |  |  |
| E24 | error | C11 |  |  |  |  |  |
| E25 | error | C11 |  |  |  |  |  |
| E26 | error | C12 | x |  |  |  |  |
| E27 | error | C12 |  |  |  |  |  |
| E28 | error | C12 | x |  |  |  |  |
| R01 | refactor |  |  |  |  |  |  |
| R02 | refactor |  |  |  |  |  |  |
| R03 | refactor |  |  |  | x | new unverified naming the defect | x |
| R04 | refactor |  |  |  | x | new violated | x |
| R05 | refactor |  |  |  |  |  |  |
| R06 | refactor |  |  |  |  |  |  |
| R07 | refactor |  |  |  |  |  |  |
| R08 | refactor |  |  |  |  |  |  |
| R09 | refactor |  |  |  |  |  |  |
| R10 | refactor |  |  |  |  |  |  |
| R11 | refactor |  |  |  |  |  |  |

Checker outcomes are advisory diagnostics (HC-05); a flag is a measurement, not a verdict on the analysis.

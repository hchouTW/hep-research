# Invariant coverage

53 rules in the plugin text, 56 registry entries.

**Rules in the text with no registry entry** (0): none

**Registry entries whose rule text is gone** (0): none

**Named mechanisms or tests that do not exist** (0): none

**No behavioral case and no deterministic test** (6): COMM-02, COMP-06, DET-07, ML-06, THEO-03, THEO-04

**Blocking rules enforced only by prose** (10): BLIND-NO-PROTECTED-READ, COMM-03, COMM-06, CTX-READ-BOUND-PROFILE, DET-03, L1-SELECT, MEAS-02, ML-05, STAT-02, THEO-05

**Blocking rules that nothing checks unless the skill is loaded** (29): COMM-01, COMM-03, COMM-04, COMM-06, COMP-03, COMP-04, COMP-07, CTX-ARTIFACTS-VALID, CTX-COMPANION-PREFLIGHT, CTX-READ-BOUND-PROFILE, DET-01, DET-03, DET-05, HANDOFF-VALIDATE-INPUT, MEAS-02, MEAS-03, MEAS-06, MEAS-07, ML-01, ML-05, STAT-01, STAT-02, STAT-03, STAT-04, STAT-05, STAT-07, THEO-02, THEO-05, THEO-06

**Enforced below the target plane** (17): BLIND-NO-PROTECTED-READ, COMM-02, COMM-03, COMM-06, COMP-04, CTX-COMPANION-PREFLIGHT, CTX-READ-BOUND-PROFILE, L1-SELECT, MEAS-02, MEAS-04, MEAS-06, ML-05, ML-06, STAT-02, STAT-06, THEO-04, THEO-05

| id | severity | plane → target | behavioral cases | deterministic tests | needs skill loaded |
|---|---|---|---|---|---|
| BLIND-NO-PROTECTED-READ | blocking | knowledge → **authority** | 8 | 1 | no |
| COMM-01 | blocking | mechanism | 1 | 2 | yes |
| COMM-02 | major | knowledge → **mechanism** | 0 | 0 | yes |
| COMM-03 | blocking | knowledge → **mechanism** | 2 | 0 | yes |
| COMM-04 | blocking | mechanism | 4 | 1 | yes |
| COMM-05 | major | knowledge | 0 | 1 | yes |
| COMM-06 | blocking | knowledge → **authority** | 1 | 0 | yes |
| COMP-01 | major | knowledge | 1 | 0 | yes |
| COMP-02 | major | mechanism | 0 | 1 | yes |
| COMP-03 | blocking | mechanism | 1 | 2 | yes |
| COMP-04 | blocking | mechanism → **authority** | 1 | 1 | yes |
| COMP-05 | major | mechanism | 0 | 2 | no |
| COMP-06 | major | knowledge | 0 | 0 | yes |
| COMP-07 | blocking | mechanism | 0 | 1 | yes |
| CTX-ARTIFACTS-VALID | blocking | mechanism | 3 | 1 | yes |
| CTX-COMPANION-PREFLIGHT | blocking | mechanism → **authority** | 1 | 1 | yes |
| CTX-LIMITED-SUPPORT | major | knowledge | 9 | 0 | yes |
| CTX-NO-UNRELATED-PROFILE | major | knowledge | 112 | 1 | yes |
| CTX-READ-BOUND-PROFILE | blocking | knowledge → **mechanism** | 27 | 0 | yes |
| CTX-USER-LANGUAGE | major | knowledge | 4 | 0 | no |
| DET-01 | blocking | mechanism | 2 | 2 | yes |
| DET-02 | major | mechanism | 1 | 1 | yes |
| DET-03 | blocking | knowledge | 1 | 0 | yes |
| DET-04 | major | mechanism | 1 | 1 | yes |
| DET-05 | blocking | mechanism | 0 | 1 | yes |
| DET-06 | major | knowledge | 0 | 1 | yes |
| DET-07 | major | knowledge | 0 | 0 | yes |
| HANDOFF-VALIDATE-INPUT | blocking | mechanism | 5 | 1 | yes |
| L1-SELECT | blocking | knowledge → **mechanism** | 424 | 1 | no |
| MEAS-01 | major | mechanism | 1 | 1 | yes |
| MEAS-02 | blocking | knowledge → **mechanism** | 2 | 1 | yes |
| MEAS-03 | blocking | mechanism | 1 | 1 | yes |
| MEAS-04 | major | knowledge → **mechanism** | 1 | 0 | yes |
| MEAS-05 | major | mechanism | 1 | 1 | yes |
| MEAS-06 | blocking | mechanism → **authority** | 8 | 2 | yes |
| MEAS-07 | blocking | mechanism | 2 | 1 | yes |
| ML-01 | blocking | mechanism | 2 | 2 | yes |
| ML-02 | major | mechanism | 0 | 1 | yes |
| ML-03 | major | mechanism | 0 | 1 | yes |
| ML-04 | major | mechanism | 0 | 1 | yes |
| ML-05 | blocking | knowledge → **mechanism** | 1 | 1 | yes |
| ML-06 | major | knowledge → **mechanism** | 0 | 0 | yes |
| STAT-01 | blocking | mechanism | 2 | 1 | yes |
| STAT-02 | blocking | knowledge → **mechanism** | 2 | 1 | yes |
| STAT-03 | blocking | mechanism | 1 | 1 | yes |
| STAT-04 | blocking | mechanism | 1 | 1 | yes |
| STAT-05 | blocking | mechanism | 1 | 1 | yes |
| STAT-06 | major | knowledge → **mechanism** | 1 | 0 | yes |
| STAT-07 | blocking | mechanism | 2 | 1 | yes |
| THEO-01 | major | mechanism | 1 | 1 | yes |
| THEO-02 | blocking | mechanism | 1 | 1 | yes |
| THEO-03 | major | knowledge | 0 | 0 | yes |
| THEO-04 | major | knowledge → **mechanism** | 0 | 0 | yes |
| THEO-05 | blocking | knowledge → **mechanism** | 1 | 0 | yes |
| THEO-06 | blocking | mechanism | 1 | 1 | yes |
| THEO-07 | major | knowledge | 1 | 0 | yes |

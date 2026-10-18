# Invariant coverage

53 rules in the plugin text, 56 registry entries.

**Rules in the text with no registry entry** (0): none

**Registry entries whose rule text is gone** (0): none

**Named mechanisms or tests that do not exist** (0): none

**No behavioral case and no deterministic test** (0): none

**Blocking rules enforced only by prose** (5): BLIND-NO-PROTECTED-READ, COMM-03, COMM-06, DET-03, L1-SELECT

**Blocking rules that nothing checks unless the skill is loaded** (29): COMM-01, COMM-03, COMM-04, COMM-06, COMP-03, COMP-04, COMP-07, CTX-ARTIFACTS-VALID, CTX-COMPANION-PREFLIGHT, CTX-READ-BOUND-PROFILE, DET-01, DET-03, DET-05, HANDOFF-VALIDATE-INPUT, MEAS-02, MEAS-03, MEAS-06, MEAS-07, ML-01, ML-05, STAT-01, STAT-02, STAT-03, STAT-04, STAT-05, STAT-07, THEO-02, THEO-05, THEO-06

**Enforced below the target plane** (8): BLIND-NO-PROTECTED-READ, COMM-02, COMP-04, CTX-COMPANION-PREFLIGHT, L1-SELECT, MEAS-04, MEAS-06, STAT-06

| id | severity | plane → target | behavioral cases | deterministic tests | needs skill loaded |
|---|---|---|---|---|---|
| BLIND-NO-PROTECTED-READ | blocking | knowledge → **authority** | 8 | 1 | no |
| COMM-01 | blocking | mechanism | 1 | 2 | yes |
| COMM-02 | major | knowledge → **mechanism** | 1 | 0 | yes |
| COMM-03 | blocking | knowledge | 2 | 0 | yes |
| COMM-04 | blocking | mechanism | 4 | 1 | yes |
| COMM-05 | major | knowledge | 0 | 1 | yes |
| COMM-06 | blocking | knowledge | 1 | 0 | yes |
| COMP-01 | major | knowledge | 1 | 0 | yes |
| COMP-02 | major | mechanism | 0 | 1 | yes |
| COMP-03 | blocking | mechanism | 1 | 2 | yes |
| COMP-04 | blocking | mechanism → **authority** | 1 | 1 | yes |
| COMP-05 | major | mechanism | 0 | 2 | no |
| COMP-06 | major | knowledge | 1 | 0 | yes |
| COMP-07 | blocking | mechanism | 0 | 1 | yes |
| CTX-ARTIFACTS-VALID | blocking | mechanism | 3 | 1 | yes |
| CTX-COMPANION-PREFLIGHT | blocking | mechanism → **authority** | 1 | 1 | yes |
| CTX-LIMITED-SUPPORT | major | knowledge | 9 | 0 | yes |
| CTX-NO-UNRELATED-PROFILE | major | knowledge | 112 | 1 | yes |
| CTX-READ-BOUND-PROFILE | blocking | mechanism | 27 | 1 | yes |
| CTX-USER-LANGUAGE | major | knowledge | 4 | 0 | no |
| DET-01 | blocking | mechanism | 2 | 2 | yes |
| DET-02 | major | mechanism | 1 | 1 | yes |
| DET-03 | blocking | knowledge | 1 | 0 | yes |
| DET-04 | major | mechanism | 1 | 1 | yes |
| DET-05 | blocking | mechanism | 0 | 1 | yes |
| DET-06 | major | knowledge | 0 | 1 | yes |
| DET-07 | major | knowledge | 1 | 0 | yes |
| HANDOFF-VALIDATE-INPUT | blocking | mechanism | 5 | 1 | yes |
| L1-SELECT | blocking | knowledge → **mechanism** | 427 | 1 | no |
| MEAS-01 | major | mechanism | 1 | 1 | yes |
| MEAS-02 | blocking | mechanism | 2 | 2 | yes |
| MEAS-03 | blocking | mechanism | 1 | 1 | yes |
| MEAS-04 | major | knowledge → **mechanism** | 1 | 0 | yes |
| MEAS-05 | major | mechanism | 1 | 1 | yes |
| MEAS-06 | blocking | mechanism → **authority** | 8 | 2 | yes |
| MEAS-07 | blocking | mechanism | 2 | 1 | yes |
| ML-01 | blocking | mechanism | 2 | 2 | yes |
| ML-02 | major | mechanism | 0 | 1 | yes |
| ML-03 | major | mechanism | 0 | 1 | yes |
| ML-04 | major | mechanism | 0 | 1 | yes |
| ML-05 | blocking | mechanism | 1 | 3 | yes |
| ML-06 | major | mechanism | 0 | 1 | yes |
| STAT-01 | blocking | mechanism | 2 | 1 | yes |
| STAT-02 | blocking | mechanism | 2 | 2 | yes |
| STAT-03 | blocking | mechanism | 1 | 1 | yes |
| STAT-04 | blocking | mechanism | 1 | 1 | yes |
| STAT-05 | blocking | mechanism | 1 | 1 | yes |
| STAT-06 | major | knowledge → **mechanism** | 1 | 0 | yes |
| STAT-07 | blocking | mechanism | 2 | 1 | yes |
| THEO-01 | major | mechanism | 1 | 1 | yes |
| THEO-02 | blocking | mechanism | 1 | 1 | yes |
| THEO-03 | major | mechanism → **knowledge** | 0 | 1 | yes |
| THEO-04 | major | mechanism | 0 | 1 | yes |
| THEO-05 | blocking | mechanism | 1 | 1 | yes |
| THEO-06 | blocking | mechanism | 1 | 1 | yes |
| THEO-07 | major | knowledge | 1 | 0 | yes |

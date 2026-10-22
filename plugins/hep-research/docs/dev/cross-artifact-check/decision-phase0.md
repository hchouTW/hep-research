# Decision record: Phase 0 gate (release R1)

Status: **accepted 2026-10-22 by the programme owner, conditional on the full suite and CI** (see Decision). Architecture
`cross-artifact-check-architecture.en.md` section 9.1. Labels: **Confirmed**, **Inferred**, **Unresolved**.

## Analysis question

Are the Phase 0 exit conditions met, so that release R1 can ship and Phase 1 (the value gate) can start once its
thresholds are confirmed?

## Entry conditions

DR-9, DR-11, DR-12 and DR-13 decided, and DR-15 for item 11: `decision-architecture.md`, 2026-10-22 (**Confirmed**).

## Work items

| # | Item | Where | State |
| --- | --- | --- | --- |
| 1 | Version guard: (rule_id, version) dispatch, generator guard, input checks per context version (G18) | `contracts/analysis_checks/rules.py` `IMPLEMENTED`; `obligations.py` `GENERATORS`; `context.py` `INPUT_CHECKS` | done |
| 2 | Function-level source digests; registry schema 1.1.0; the check fails on code changed without a new version | `contracts/analysis_checks/source_digest.py`; `contracts/rule_registry.py`; `contracts/schemas/rule_registry.json` | done |
| 3 | Checker identity from the modules loaded at run time; generator digest over three files (G10, A1) | `contracts/analysis_check.py` `checker_identity`, `generator_code_digest` | done |
| 4 | P6: status agrees with the exit code (G20) | `analysis_check.py` `evaluate`, `exit_code` | done |
| 5 | Snapshots on by default; bundle index; `snapshots gc` (dry run by default) | `analysis_check.py` | done |
| 6 | Cheap `check-report` refusals (G11, G19 drift) | `contracts/permit.py` `cheap_refusals` | done |
| 7 | `assessment.plugin_release` | `analysis_check.py` | done |
| 8 | Classify G21 | `g21-classification.md`: a definition gap of the semantics table; no fix needed now | done |
| 9 | Probes G1–G22; mutation-testing skeleton | `tests/contracts/test_cross_artifact_check_gap_probes.py`; `tests/contracts/analysis_check_mutations.py` | done |
| 10 | How old releases are obtained | below | done |
| 11 | Rename the code-name identifiers (WP-R) | `tools/rename_analysis_check_ids.py`; same release as item 2, after item 5 | done |

## Exit conditions

| Condition | State | Evidence |
| --- | --- | --- |
| V72–V76 pass | **met** (Confirmed) | `rule_registry.py check`: pass, 23 rules, 76 V cases, 85 V parts passing; `tests/contracts/test_analysis_check_foundations.py` 22 tests pass |
| Existing tests pass | **met** (Confirmed), with changed assertions listed in VALIDATION CROSS-ARTIFACT-PHASE0 | the 205 analysis-check tests (now `test_analysis_check_*`) pass; three assertions of the registry test changed for registry 1.1.0 |
| `run_all_checks.py` green | see VALIDATION CROSS-ARTIFACT-PHASE0 | full suite before and after the rename |
| Suite 1.0.0 gives the same results on R1 as before | **met** (Confirmed) | 22 cases (the four reference cases, the run chain and campaign, and every probe variant), 403 obligations: identical (obligation, state, reason) on main 0.24.1 (checker code byte-identical to 0.21.0 per the architecture's re-measurement) and on this branch; the two outcome files have the same SHA-256 `00655e16…`. Script: `~/Workspace/hep-research-tasks/cross-artifact-check/phase0_outcomes.py` (maintainer's task folder) |
| Gate record confirmed by the programme owner | **open** | Decision below |

## Old releases (item 10, Confirmed)

Every release from 0.3.0 has a tag `hep-research--v<version>` except 0.4.0, whose manifest exists without a tag.
`git archive hep-research--v<version> plugins/hep-research` extracted into an empty folder is a released copy:
`core.protected.identity.plugin_release()` returns the version (checked for 0.21.0, digest `96e14c12…`). The checker
exists from 0.12.0. A suite 1.0.0 result of a bundle without snapshots is reproduced with the release that froze it.

## Gap probes (Confirmed)

Passing: G10, G11, G18, G19 (drift and forged-suite part), G20. Expected failures, each checked to fail by assertion
for its stated reason: G1, G2, G3, G4, G5, G6, G7, G8, G12, G13, G14, G15, G16, G17, G22 (an empty unit is already
refused; a placeholder is not). Skipped with reason: G9 (assurance plane), G21 (classified). The probes were rebuilt
from the gap register: the review's original probe file is not in this repository (**Unresolved**: whether they
match its exact scenarios).

## Notes

- **Inferred.** Registry 1.1.0 changes the registry's digest, which semantic lock 1.0.0 pins: a bundle frozen before
  R1 without snapshots now reports `lock_differences` and is reproduced with its own release, as R-4 of section 8.3
  intends.
- **Inferred.** The source digest is formatting-insensitive but not refactoring-insensitive: a refactor of a shared
  helper (for example `scope.compare_scopes`) requires a new version of every rule that reaches it.

## Owner

hchouTW.

## Decision

**2026-10-22, maintainer instruction in the session.** After the status report of the work above, the maintainer
replied "continue; thresholds confirmed, release 0.25.0 after merge": the Phase 0 gate is accepted on the condition
that the full-suite comparison (VALIDATION CROSS-ARTIFACT-PHASE0) and the required CI jobs pass, and R1 ships as
0.25.0 after the merge.

## 2026-10-22, label note

The architecture's second clean-up edition renames the rename safety rules R-1 to R-7 to RN-1 to RN-7, so they cannot
be confused with the releases R1 to R3; content is unchanged. "R-4 of section 8.3" above is RN-4 of section 8.3.3 in
that edition.

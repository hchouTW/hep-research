# Retire the cross-artifact check: run state

```yaml
task_file_version: 1
base: {ref: origin/main, commit: 3a63e986993769e93f90264313fa91076283cde9, plugin_version: 0.46.0}
branch: retire-cross-artifact-check
worktree: .claude/worktrees/retire-cross-artifact-check
work_folder: ~/.local/state/hep-research/retire-cross-artifact-check
route: A
steps:
  T0: {status: done, notes: "base is origin/main (0.46.0; the local main checkout was at 0.45.0 and was not touched); hep-review fingerprint: 374 files; python 3.13.2 (~/.venvs/hep-research-e2); ruff 0.16.10 and mypy 2.4.0 from ~/.venvs/hep-research-ci"}
  T1: {status: done, baseline: {checks_pass: 31, checks_fail: 0, checks_skip: 2, unittest: {run: 6298, failed: 0, skipped: 168, modules: 494}}, notes: "run in a detached origin/main worktree (same tree as the unmodified branch); the two skips are the host CLI checks (--no-cli)"}
  T2: {status: done, conflicts: ["docs/reference-inventory.json", "docs/reference-inventory.md"], notes: "patch applied with git apply --3way --index; the two conflicts were reset to main and regenerated in T5; every whole-file appendix (A.1, A.8, B.1-B.10) matched the applied files byte for byte"}
  T3: {status: done, findings: [{path: "(both scans)", line: null, disposition: kept-history}], notes: "every hit on the 0.46.0 base is on the task's keep list (stub, refusal messages, retirement docstrings, $comment fields under H3, version-history comments, history sentences, hep-review/scifix advisory_* names, qcd-r-ratio false positives, docs/dev paths); 0.46.0 added only hep-review fixture hits (advisory_conditions), kept; no finding outside section 4"}
  T4: {status: done, traced: {modules: 28, tests: 301}, classified: [
      {module: test_analysis_check_baseline_gaps, tests: 14, checker: 0, shared: 14, verdict: renamed},
      {module: test_analysis_check_profile_loading, tests: 15, checker: 0, shared: 15, verdict: renamed},
      {module: test_analysis_check_custody, tests: 3, checker: 0, shared: 3, verdict: renamed},
      {module: test_analysis_check_refusal_blockers, tests: 2, checker: 0, shared: 2, verdict: renamed},
      {module: test_analysis_check_rule_registry, tests: 27, checker: 1, shared: 26, verdict: renamed, note: "suite test removed (suites gone), new-rule test rewritten (section 4.4)"},
      {module: test_analysis_check_effect_catalog, tests: 12, checker: 8, shared: 4, verdict: split},
      {module: test_analysis_check_foundations, tests: 23, checker: 21, shared: 2, verdict: split, note: "source-digest tests rewritten without the checker's rules (B.3)"},
      {module: test_analysis_check_identity_and_instances, tests: 10, checker: 7, shared: 3, verdict: split},
      {module: test_analysis_check_r2_formats, tests: 24, checker: 16, shared: 8, verdict: split},
      {module: test_analysis_check_r3, tests: 11, checker: 11, shared: 0, verdict: split, note: "catalog-version assertions kept in a rewritten test (B.6) without _catalog_compatible"},
      {module: test_analysis_check_bundle_and_context, tests: 11, checker: 11, shared: 0, verdict: removed},
      {module: test_analysis_check_chain_rules, tests: 25, checker: 25, shared: 0, verdict: removed},
      {module: test_analysis_check_coverage_reader, tests: 2, checker: 2, shared: 0, verdict: removed},
      {module: test_analysis_check_r2_rules, tests: 9, checker: 9, shared: 0, verdict: removed},
      {module: test_analysis_check_ratio_rules, tests: 6, checker: 6, shared: 0, verdict: removed},
      {module: test_analysis_check_report, tests: 10, checker: 10, shared: 0, verdict: removed},
      {module: test_analysis_check_report_permit, tests: 9, checker: 9, shared: 0, verdict: removed},
      {module: test_analysis_check_review_fixes, tests: 12, checker: 12, shared: 0, verdict: removed},
      {module: test_analysis_check_review_integration, tests: 3, checker: 3, shared: 0, verdict: removed},
      {module: test_analysis_check_shadow_and_refusal, tests: 4, checker: 4, shared: 0, verdict: removed},
      {module: test_analysis_check_snapshots, tests: 6, checker: 6, shared: 0, verdict: removed},
      {module: test_cross_artifact_check_gap_probes, tests: 17, checker: 17, shared: 0, verdict: removed},
      {module: test_cutoff_transmission_m1, tests: 5, checker: 3, shared: 2, verdict: kept, note: "the 2 kept tests reached coverage only through setUp, which section 4.4 removes"},
      {module: test_survival_fragmentation_d4, tests: 4, checker: 2, shared: 2, verdict: kept, note: "as above"},
      {module: test_preservation_checklist_c3, tests: 5, checker: 1, shared: 4, verdict: kept},
      {module: test_ci_plan, tests: 24, checker: 0, shared: 24, verdict: kept},
      {module: test_multi_era_joint_fit_s6, tests: 3, checker: 0, shared: 3, verdict: kept},
      {module: test_reference_profile_kind_d13, tests: 5, checker: 0, shared: 5, verdict: kept}],
    notes: "counts after source review: the automatic trace rule disagreed with section 4 on 18 tests; each was settled from its source (CLI via subprocess or the CLI constant, imports of contracts.analysis_checks inside the test, setUpClass running the checker, checker-only helper modules, skipped placeholders in checker classes, or rewritten in the kept modules); kept modules: 10 with 81 tests"}
  T5: {status: done, registry: {rules_retired: 12, v_parts_not_run: 69, passing_left: 4}, naming: {stale_removed: 49, added: 0}, timings: {renamed: 7, dropped: 10}, notes: "naming gate failed against origin/main with 5 baseline_grown keys (keys moved with renamed files count as growth); fixed by renaming the 5 flagged identifiers (obj -> target in contracts/source_digest.py, tmp -> workdir in test_contract_baseline_gaps.py, ec -> catalog_module in test_effect_catalog.py) so their entries were deleted as stale, never added; example outputs regenerated byte-identical except the removed fields; scripts idempotent"}
  T6: {status: done, failures: [], notes: "all listed checks pass; mypy (CI config) 0 issues in 118 files; ruff check core contracts passes; ruff on the branch's changed .py files: only the 2 pre-existing B904 in the example run.py files; 125 affected tests OK"}
  T7: {status: done, only_after: [], only_before: [], checks_changed: [], unittest_after: {run: 6122, failed: 0, skipped: 166, modules: 483}}
  T8: {status: done, hep_review_unchanged: true, claims_check: [], protected_diff: empty}
  T9: {status: done, commits: [0769b837, 84b4318e, a867050b, b924c292, 6a70f37e, c398d5e0, 15fd76da]}
stops: []
```

## Log
```text
2026-10-29 | T0 | worktree and branch from origin/main 3a63e986; hep-review fingerprint recorded | 0769b837
2026-10-29 | T1 | baseline full check in a detached origin/main worktree: 31 pass, 2 skip, 6298 tests, 0 failed | none
2026-10-29 | T2 | route A: patch applied; reference-inventory conflicts reset for regeneration | none
2026-10-29 | T3 | both scans: no finding outside section 4 | none
2026-10-29 | T4 | traced 301 tests in 28 modules; 18 trace/section-4 disagreements settled from source | none
2026-10-29 | T5 | registry and timings idempotent; naming gate fixed by renaming 5 identifiers; examples and inventory regenerated | none
2026-10-29 | T6 | static checks, lint and affected tests pass | none
2026-10-29 | T7 | full check after: same statuses, 6122 tests, 0 failed, no one-sided failure | none
2026-10-29 | T8 | hep-review hashes identical, claims check [], protected areas unchanged | none
2026-10-29 | T9 | six grouped commits, then this state commit | 84b4318e..15fd76da
2026-10-29 | follow-up | merged origin/main a2852507 (PR #314, clean); CHANGELOG 0.45.x -> 0.47.x; checks rerun | see git log
```

## Report

**What was done (by section 4).** Removed (4.1): the checker (`contracts/analysis_checks/` except `source_digest.py`),
`contracts/migrate.py`, the 14 suites, `refusal_matrix.json`, the operator coverage contract, the five checker-only
schemas, `tools/rename_analysis_check_ids.py`, the two checker test helpers and 12 checker-only test modules. Moved and
renamed (4.2): `contracts/source_digest.py`, and ten test modules under descriptive names (five renamed unchanged,
five split). Modified (4.3): the refusing stub `contracts/analysis_check.py`, `rule_registry.py` (`_check_sources`),
`naming_registry.py`, `effect_catalog.py` (catalog only), `permit.py` (`check-report` refuses with
`permit.check_report_retired`), `attestation.py` (comment only), `core/status.py`, `review_measurement_spec.py`
(hidden refusing flags), the review-question tables in hep-measurement (9 rows) and hep-statistics (3 rows), the
preservation checklist, the hep-detector reference and README, README, the capability matrix, the cross-artifact-check
records (README, dated notes, new `decision-retire.md` with an empty Decision), CHANGELOG, the two examples and their
regenerated outputs, `tools/ci_plan.py`, and the regenerated registry, naming gaps, timings and reference inventory.

**Verification.** T6: every static check passes; CI-pinned mypy and ruff pass on `core` and `contracts`. T7: check
statuses identical before and after (31 pass, 2 skip); unittest 6,298 -> 6,122 (-176) in 494 -> 483 modules; 0 failures
on either side. T8: 374 hep-review files hash-identical, claim registry check `[]`, protected areas unchanged.
Acceptance A1-A8 hold (A5: `analysis_check.py freeze` and `permit.py check-report x` exit 2 naming
`decision-retire.md`; `review_measurement_spec.py SPEC --check-bundle B` is a usage error, exit 2).

**Assertions changed (H8).** Only those of section 4.4: `test_rule_registry` (new-rule test now expects
`registry.rule_not_implemented` for a live rule and accepts a retired one; two module names updated; the suite test
removed), `test_cutoff_transmission_m1` and `test_survival_fragmentation_d4` (coverage assertions and tests removed),
`test_preservation_checklist_c3` (retired items removed; asserts the retired check is no longer taught),
`test_pbar_p_curvature_offset` (the removed `advisory_ratio_subset_v1` assertion), `test_ci_plan` (example paths moved
to `contracts/permit.py`, `test_registry_keys_and_semver.py` and `design_fixtures.py`). The split modules keep their
shared tests as in appendix B. No assertion was loosened.

**Differences from the rehearsal (section 9).** Base 0.46.0 instead of 0.45.0; the baseline has 0 failing tests
(this environment has sympy and LaTeX) and 6,298 tests instead of 6,294; the deltas (-176 tests, -11 modules) and the
file counts (98 files: 51 deleted, 7 added, 6 renamed, 34 modified) are the same. One change beyond the patch: with
`origin/main` present, `tools/check_naming.py` compares the known-gaps file with it and counted the 5 keys moved by
appendix C.2 as baseline growth (status fail; the rehearsal sandbox presumably had no `origin/main`, so the comparison
was skipped). Instead of adding keys or waivers, the 5 flagged identifiers were renamed (`obj` -> `target` in
`contracts/source_digest.py`, `tmp` -> `workdir` in `tests/contracts/test_contract_baseline_gaps.py`, `ec` ->
`catalog_module` in `tests/contracts/test_effect_catalog.py`, with a local `classify` to keep lines short); their
entries were removed as stale, so the file went from 1,032 to 983 entries with none added or grown. These renames
change no behaviour; the naming predicate digests are unchanged (`naming_registry.py check` passes).

**Known stale comments kept (H3).** `$comment` fields that still describe the checker in `contracts/vocab/effects.json`,
`contracts/schemas/rule_registry.json`, `contracts/schemas/effect_catalog.json` and `contracts/naming/rules.json`
(the last still names `contracts/analysis_checks/source_digest.py`); the version-history comments in
`contracts/__init__.py`; the impact group `context-obligations` keeps `contracts/analysis_check.py` as a pattern
while the stub exists.

**Open for the maintainer (section 8.3).** Fill in the Decision of `decision-retire.md`; bump `CONTRACTS_VERSION`
(sidecar formats removed) with a version-history note; add a `VALIDATION.md` entry with the changed assertions above;
confirm "reproduce ... with 0.47.x" in CHANGELOG names the last release that has the check (set to 0.47.x
after the follow-up below, since 0.47.0 is cut from a main without this branch); remove the stub, the two hidden flags and the `check-report` subcommand in the next minor.

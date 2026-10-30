# hep-detector reconstruction methods: run state

```yaml
task_file_version: 1
task_file_sha256: 1cbd8117263a5622cacb91f42590ff84c8cfd565ff4b14c82055440d258c4367
base: {ref: origin/main, commit: 313637c16fd1fb4871d4ab3714ada7ab54ec5dd6, plugin_version: 0.49.1}
branch: task/hep-detector-reco-methods
worktree: .claude/worktrees/hep-detector-reco
work_root: ~/.local/state/hep-research/hep-detector-reco
repo: hep-research
plugin_root: plugins/hep-research
main_checkout_t0: {head: 313637c16fd1fb4871d4ab3714ada7ab54ec5dd6, porcelain_lines: 0}
route: A
open_questions: {OQ-1: "default: 1 fix round", OQ-2: "default: one review and one re-review of fixed findings", OQ-3: "default: origin/main (exists; equals main at T0)", OQ-4: "default: deferred cells out of scope"}
steps:
  T0: {status: done, notes: "worktree and branch created at BASE; work root outside every Git project; patch sha256 matches; git apply --check succeeds (route A); no Git committer identity configured, commits use -c user.name=Claude -c user.email=noreply@anthropic.com"}
  T1: {status: done, baseline: {static: {pass: 29, fail: 0, skip: 2}, pytest: {passed: 2885, failed: 28, errors: 1, skipped: 83}, failing_ids: {count: 29, file: baseline/failing_ids.txt}, routing_part_bytes: 4081}, notes: "interpreter: existing conda env envs/ml (Python 3.13.2; plugin requires >=3.13, system python3 is 3.12 without numpy); nothing installed. pytest 28 failed counts subtest failures; 29 ids incl. SUBFAILED lines, all outside hep-detector (hep-ml scripts and torch assets, find_python and PyROOT floors, synthetic NanoAOD, diagrams renderer, CLI contract, no-bytecode). Static skips are the two host-CLI checks (--no-cli). reference_inventory --check passes (6 size warnings, none in a touched file). check_wiring --since no-such-rev exits 2 (read as fatal bad input)"}
  T2: {status: done, counts: {C: 60, P: 39, M: 19, na: 15}, reconciled_changes: [], notes: "audited matrix equals the expected matrix; 58 non-covered = A 19 + B 7 + C 6 + D 14 + Deferred 12; 31 anchors resolve; no group premise changed (coverage-audit.md)"}
  T3: {status: pending, route: A, must_state_missing_added: [], notes: ""}
  T4: {status: pending, verified: [], corrected: [], not_reverifiable: [], notes: ""}
  T5: {status: pending, notes: ""}
  T6: {status: pending, after: {static: {}, pytest: {}}, one_sided: [], notes: ""}
  T7: {status: pending, content_head: , re_review: , findings: {critical: , major: , minor: }, fixed: , not_fixed: [], notes: ""}
  T8: {status: pending, notes: ""}
  T9: {status: pending, commits: [], notes: ""}
fix_rounds_used: {}
stops: []
next_action: "T3 apply patch (route A)"
```

## Log

```text
2026-10-30 | T0 | base origin/main 313637c1 (plugin 0.49.1); main checkout clean (0 porcelain lines); .claude/worktrees/ ignored; worktree and branch created | none
2026-10-30 | T0 | work root ~/.local/state/hep-research/hep-detector-reco created, outside Git; task file and patch copied; patch sha256 633571889853... matches | none
2026-10-30 | T0 | git apply --check --directory=plugins/hep-research succeeds: route A | none
2026-10-30 | T0 | no Git committer identity configured: commits pass -c user.name="Claude" -c user.email="noreply@anthropic.com" | none
2026-10-30 | T1 | first baseline attempt with system python3 3.12 aborted: run_all_checks requires >=3.13, pytest collection errors (no numpy); kept in work root baseline/py312-attempt | none
2026-10-30 | T1 | baseline with envs/ml Python 3.13.2: static 29 pass 0 fail 2 skip; pytest 2885 passed 28 failed 1 error 83 skipped (53 min); 29 base failure ids; inventory --check pass; routing part 4081 B; wiring --since no-such-rev exit 2 | this commit
2026-10-30 | T4 | Crossref records of the 13 citations fetched into the work root early (read-only, no repository change); compared at T4 | none
2026-10-30 | T2 | coverage audit at base: C 60, P 39, M 19, n/a 15; equals expected matrix, no reconciliation needed; script in coverage-audit.md recomputes counts and resolves anchors | this commit
```

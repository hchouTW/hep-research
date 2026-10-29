# hep-review v9 implementation run state

Machine-maintained state of the autonomous run defined by `hep-review-v9-TASK.md` (task-file version 1) against the
specification `hep-review-v9-en.md` (`hep-review-v9-zh.md` prevails on conflict). Paths are written relative to the
user's home (`~`) so that no private absolute path is committed (tools/check_packaging.py).

```yaml
run:
  task_file_version: 1
  task_file_digest: c356a2fcf90952655641a3983fed3ca97fadb0e0e26add1754e6b3b92042d6c3
  spec_digest_en: 1ca6085332dc8456ec551b7789d8de7466ee4f497a12e08b19776d738203c0fd
  spec_digest_zh: 84c04822efa533653304f49180b0f9b403fe8a08e767e1648cf4b4a02ef1b10d
  started: 2026-10-29T06:20+08:00
  sessions: 1
  mode: autonomous
  target_gate: G2
environment:
  source_repo: ~/hep-research (Git repo root; plugin root plugins/hep-research)
  base_ref: main
  base_commit: 42f5bad16e87a66518e5ead2a738a1fe9a59e787
  worktree_path: ~/hep-research/.claude/worktrees/hep-review-v9
  branch: hep-review-v9-impl
  python: 3.13.2 (conda-forge; tests also run with ~/.venvs/hep-research-e2, Python 3.13.2)
  sqlite: 3.51.1
  git: 2.50.1 (Apple Git-155)
  platform: darwin (macOS)
  platform_caps: {supports_dir_fd_open: true, O_NOFOLLOW: true, O_DIRECTORY: true, O_NONBLOCK: true}
  store_location: ~/.local/state/hep-research/hep-review
  store_fs_type: apfs (local, journaled; volume /System/Volumes/Data)
  store_persistence: pending-next-session
host_profile_ref: docs/dev/hep-review/host-profile.md
tasks:
  T00: {status: done, deps: [], steps_done: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], sessions: 1, notes: "clean baseline at 42f5bad1: 31 pass, 0 fail, 2 host-CLI skips; N01 n/a-with-basis, N02/N04/N40 confirmed (discovery.md section 7)"}
  T0S: {status: done, deps: [T00], go_no_go: go, notes: "protocol 9044c6af before first dispatch 22:38:01Z; C01 4/4, C02 FA 1/4, C03 3/4, C04 4/4, 16/16 digest-bound; 3 instance construction errors caught by reviewers; H5/H6 pending-next-session"}
  T01: {status: done, deps: [T0S], steps_done: [1, 2, 3, 4, 5, 6, 7, 8], notes: "62/62 owned cases pass; independent review: 1 blocker, 6 major, 8 minor, all dispositioned (12 adopted, 3 partly), fixed with tests first (3f075184); blocker awaits user confirmation (task file 4.2)"}
  T02: {status: done, deps: [T01], steps_done: [1, 2, 3, 4, 5, 6, 7], notes: "30/30 owned cases pass; interruption, two-process CAS, foreign commit, export->import with checkpoint all tested"}
  T03: {status: done, deps: [T01], steps_done: [1, 2, 3, 4, 5, 6, 7], notes: "15/15 owned cases pass; live routing run not run (paid, needs approval)"}
  U1:  {status: done, deps: [T02, T03], kind: user-gate, notes: "2026-10-29 user chose (b): user-approved deterministic oracles, no secret gold, held-out isolation unmet; full 48 trials"}
  T04: {status: done, deps: [U1], steps_done: [freeze-protocol, commitments, calibration, 48-trials, scoring, nonce-publication], notes: "engineering and scientific gates pass 48/48; schema 1.0.0 freeze left as a separate reviewed step (frozen protocol section 5)"}
  T05: {status: skipped}
  T06: {status: skipped}
  T07: {status: skipped}
  T08: {status: skipped}
gates: {G1: done, G2: passed-and-held-out-follow-up-passed-schema-freeze-pending, G3: pending}
cases:
  T00: {N01: not-applicable-with-basis (worktree created; failure path is the hard stop), N02: pass, N04: pass (no existing hep-review in source or cache), N40: pass}
  T01: "all 62 pass (tests/contracts/test_hep_review_{json,decision_table,kernel,review_fixes}.py)"
  T02: "all 30 pass (tests/skills/hep_review/test_{materials,store,continuity_export}.py)"
  T03: "all 15 pass (tests/skills/hep_review/test_{coordinator,cli,pilot_generator,g1_review_fixes}.py)"
decisions:
  - {when: 2026-10-29T10:10+08:00, task: U1, decision: "Option (b): deterministic oracles approved by the user; Claude generates instances with a recorded seed and runs all trials; full 48 trials + 8 calibration items (<= 60 dispatches)", reason: "user answer to the U1 gate", reversible: false}
  - {when: 2026-10-29T06:25+08:00, task: T00, decision: "Worktree created with the Git fallback (git worktree add -b hep-review-v9-impl) at the repo's host-tool location .claude/worktrees/ (ignored by .gitignore), then entered with the host tool (EnterWorktree path=...)", reason: "The host worktree tool cannot name the branch; the task fixes branch_name=hep-review-v9-impl", reversible: true}
  - {when: 2026-10-29T06:30+08:00, task: T00, decision: "Store location ~/.local/state/hep-research/hep-review ($XDG_STATE_HOME/hep-research/hep-review when set)", reason: "Spec 11.1 lets T00 fix the path per repository convention; the existing authoring review keeps private state under $XDG_STATE_HOME/hep-research (review_lib/store.py default_private_root). The path is on local APFS, outside ~/Library/CloudStorage and ~/Library/Mobile Documents", reversible: true}
  - {when: 2026-10-29T06:40+08:00, task: T0S, decision: "Raw spike run kept byte for byte in ~/.local/state/hep-research/hep-review/spike-run1 (outside the repo); committed spike/run1-summary.json carries every raw SHA-256", reason: "packets and drop files contain private absolute paths that tools/check_packaging.py forbids in tracked files", reversible: true}
  - {when: 2026-10-29T06:33+08:00, task: T00, decision: "All run documents live under docs/dev/hep-review/ (state, discovery, baseline, host profile, spike, reviews); spike code under docs/dev/hep-review/spike/", reason: "docs/dev is the repo's place for development specs; a new top-level folder would change the shipped layout. Spike code is never imported by product code", reversible: true}
  - {when: 2026-10-29T07:20+08:00, task: T01, decision: "Review findings F6, F7, F14 partly adopted: trusted evaluation checkpoint and capability fingerprint come from the committed plan; schemas are applied at commit by the store, not inside the pure kernel; project() keeps the two-step API and recomputes validate(bundle)", reason: "layer 1 must be a pure function of the bundle and the kernel may do no I/O (spec 3.1, 7.6)", reversible: true}
review_inputs_t01:
  commit: 5e4ef528
  report_sha256: 5820722fe2b86f0d0a8feed944f4662a95a6452da5fe56b3caae43e23b855228
  contracts/hep_review.py: 04bcef51582cb16d26cc6494707b90e060fa13efbab87746f843bc70aa755d6d
  tests/contracts/test_hep_review_decision_table.py: 2adf79e1410a09a6e41a824977c5d0e4304df0da44eae4f39cf80559283b8822
  tests/contracts/test_hep_review_kernel.py: a70bf1c3b1d5c521a305fa389e5f1253c20eedb55ce4a4cc5908c1b4b619c265
blockers:
  - {when: 2026-10-29T09:30+08:00, task: G1, description: "independent G1 review: 4 blockers (B1 rollback stays verified, B2 fork/migrate drop negatives, B3 hand-written assignment bases, B4 records not bound to raw), 4 major, 8 minor; all fixed with tests first in b491ff9e; dispositions in reviews/g1-review-dispositions.md", needs: none, resolved: "2026-10-29 user accepted the G1 dispositions"}
  - {when: 2026-10-29T07:15+08:00, task: T01, description: "independent T01 review returned blocker F1 (layer 1 not byte-reproducible across processes); fixed with a multi-seed test in 3f075184", needs: none, resolved: "2026-10-29 user accepted the dispositions and asked to continue with T03 and G1"}
next_action: "Maintainer decision: freeze hep-review/1 / schema 1.0.0 as a separate reviewed step (g2h-report.md section 5); a harder multi-defect suite is needed to measure a miss rate"
```

## Log

```text
2026-10-29 06:20 | T00 | 1 | source repo ~/hep-research (contracts/skill_names.py at plugins/hep-research/); not the plugin cache | none
2026-10-29 06:22 | T00 | 2 | no AGENTS.md/CLAUDE.md in repo; read docs/maintenance.md, pyproject.toml, check_layering.py, check_packaging.py | none
2026-10-29 06:23 | T00 | 3 | base main = origin/main = 42f5bad1; main checkout clean (0 porcelain lines); 4 existing linked worktrees (crprop-k*); no submodules | none
2026-10-29 06:25 | T00 | 4,5 | worktree created; inside it rev-parse --path-format=absolute gives .git/worktrees/hep-review-v9 vs .git (different) and no superproject | none
2026-10-29 06:31 | T00 | 8 | platform probe: all spec 1.5 premises reproduced on macOS (see discovery.md) | none
2026-10-29 06:32 | T00 | 9 | store dir created, marker hep-review-persistence-marker = 2026-10-28T22:32:23Z | none
2026-10-29 06:34 | T0S | 1 | protocol, time box 96 min, thresholds committed before any dispatch | 9044c6af
2026-10-29 06:38 | T0S | 2-4 | spike.py, 16 exposed instances, 16 reviewers + 2 probes dispatched in one message; 16/16 digest-bound | a8f46b69
2026-10-29 06:42 | T0S | 5 | H1 readable, H2 writable, H3 parallel, H4 yes/yes, H5/H6 pending-next-session | a8f46b69
2026-10-29 06:44 | T0S | 6 | observations.md: go | a8f46b69
2026-10-29 06:47 | T0S | fix | packaging-clean wording of private path patterns | a5f9322c
2026-10-29 06:52 | T01 | 2 | strict ingestion + encoder; gold byte vectors written by hand (one typo caught by a hex/text cross-check) | c36e1751
2026-10-29 07:05 | T01 | 1,3-8 | schemas, validator, closures, projection, tiers, decision-table generator (table, rule model and kernel agree on every row); layering, ruff, mypy pass | 5e4ef528
2026-10-29 07:08 | T01 | review | independent reviewer dispatched (fresh context, non-author, same model, shared filesystem) | none
2026-10-29 07:10 | T02 | 1-2 | controlled reading, snapshots, drop ingestion | 6b2dbac5
2026-10-29 07:14 | T02 | 3-4,7 | store location checks, SQLite commit log, CAS/idempotency, current-validator check | 757cc686
2026-10-29 07:25 | T01 | review fixes | F1-F15 dispositioned; regression tests first (23 F + 3 E before) | 3f075184
2026-10-29 07:27 | T00 | 10 | clean baseline from git archive of 42f5bad1 | 0b7e49f1
2026-10-29 07:33 | T02 | 5-6 | continuity, checkpoints, fork/migration, export/verify/import | 283e47a3
2026-10-29 07:34 | stop | 4.2 | independent review blocker -> ask the user; full branch check running in background | none
2026-10-29 07:50 | T01 | review | user accepted the dispositions; continue with T03 and G1 | none
2026-10-29 08:05 | T03 | 1-5 | skill, references, registration, coordinator, host adapter, CLI | dbebc92c
2026-10-29 08:20 | T03 | 6-7 | domain cards, pilot protocol draft, oracle-checked generator | 96f70b01
2026-10-29 08:25 | G1 | review | independent G1 reviewer dispatched (inputs frozen at 96f70b01) | none
2026-10-29 09:15 | G1 | review fixes | B1-B4, M1-M4, m1-m8; regression tests first (19 F + 8 E before) | b491ff9e
2026-10-29 09:40 | G1 | check | full branch check: 31 pass, 0 fail, 2 host-CLI skips; 6214 tests, 0 failures | none
2026-10-29 09:42 | stop | 4.2 | G1 review blockers -> ask the user | none
2026-10-29 09:50 | G1 | declare | user accepted the G1 dispositions; G1 declared (experimental record prototype); run finished at target G1 | none
2026-10-29 10:10 | U1 | answer | (b) approved oracles, full 48 trials; target_gate raised to G2 | none
2026-10-29 09:28 | T04 | freeze | EvaluationProtocol, commitments, grader instructions, driver committed before any trial | d987d4e2
2026-10-29 09:35 | T04 | fix | snapshot ns times as decimal strings (found by the pilot path) | 6f7936a7
2026-10-29 10:40 | T04 | trials | calibration 8/8; 48/48 trials digest-bound at R2; scoring graders agree 12/12; both gates pass; 19/19 commitments verified, nonces published | none
2026-10-29 11:20 | T04 | g2h | held-out follow-up frozen; seed held by the user | 862de947
2026-10-29 11:35 | T04 | g2h | gold commitments before any dispatch | cacae2a4
2026-10-29 12:10 | T04 | g2h | 45/45 trials ingested before the reveal | 596b88e9
2026-10-29 12:30 | T04 | g2h | reveal 15/15; calibration 10/10; order-swap 15/15; both gates pass 45/45 | none
```

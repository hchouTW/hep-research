# Reconstruction v12 — progress log

Task file: `hep-research-reconstruction-v12-en-task.md` (SHA-256 `3c041bc133e9a6ae2c1be0bfdee9fc4fe305fe64b7f7ea4ca2c378542bfac15b`),
executed as an **implementation task** (runbook 0.1), scope S0, A1, B1, A2, B2, C1, C2. D is not in scope (no remote
execution requested). This file is the progress log of runbook 0.7; its location (`evals/reconstruction-v12/`) is
the runbook's proposal, **pending approval** by the maintainer (runbook 0.2.2).

Lines in this log are written by the executing Agent; they are not a trust anchor (runbook 0.7). hep-review checkpoint
lines are reported to the user separately.

## Preflight (runbook 0.2, 0.3) — 2026-10-29

### Worktree (0.2.1)

| Item | Value |
|---|---|
| Target repository | `<main checkout>` (the current working directory; remote `origin` = `github.com/hchouTW/hep-research`) |
| Worktree | `<worktree>` |
| Branch | `recon-v12/20261029-s0-c2` (not the default branch) |
| Base | `origin/main` = `313637c16fd1fb4871d4ab3714ada7ab54ec5dd6` (equal to local `main`) |
| `git rev-parse --show-toplevel` | `<worktree>` (equals the worktree) |
| `git worktree list` | lists the worktree on `recon-v12/20261029-s0-c2` |
| Main checkout `git status --porcelain` | empty (0 lines); re-compared at the end of every stage |
| Scratch | `<scratch>/recon-v12/` (`model/`, `probes/`, `s0/`, `tests/`, `venv/`) |

### 1. Target and version

- Plugin version `0.49.1` (`.claude-plugin/plugin.json`); the task file was checked against 0.49.0.
- CHANGELOG after 0.49.0: only 0.49.1, documentation-only (READMEs rewritten; `SKILL.md`, contracts 3.17.0,
  `CORE_VERSION` 1.4.0 and adapters unchanged).
- Installed plugin used read-only for S0: `<installed plugin 0.49.1>`.

### 2. Current state of the named code (Delivery §4.2)

All seven named files exist and are byte-identical to the installed 0.49.1 copy (`cmp`): `run_workflow.py`,
`test_workflow_c6.py`, `contracts/dependencies.py`, `core/partition/campaign.py`, `environment_manifest.py`,
`skills/hep-review/scripts/review.py`, `contracts/hep_review.py`. The campaign still has intent, unique tag,
unconfirmed (status `intent`), `reconcile()`, `confirm_submission()`, `abandon_submission()`, `cancel()`, `reset()`,
`resubmit()`, `not-submitted` and `termination_observed`. The hep-detector reconstruction, performance, calibration and
alignment pages exist. No difference between the task file's current-state statements and the code was found.

### 3. Project instructions

- No `CLAUDE.md` or `AGENTS.md` in the repository. Effective instructions: `docs/maintenance.md` (aggregate check,
  "Adding a topic", SKILL.md size budget, porting a fix with a failing test first), `docs/routing-contract.md` (one owner
  per topic, ownership table read by `tools/check_ownership.py`, no coordinator skill).
- Generation: `tests/routing/cases.json` from `tests/routing/make_cases.py`; reference inventory from
  `tools/reference_inventory.py`; capability map from `tools/capability_map.py --write`; stanzas via
  `tools/build_stanzas.py`.
- No conflict with Parts I–IV found at preflight.

### 4. Test commands and baseline

Environment: the host Python is 3.12 without the scientific stack; the repository requires Python ≥ 3.13. A scratch
virtual environment (`scratch/recon-v12/venv`, Python 3.13.2 from the user's `ml` conda env, packages from
`requirements-ci.lock`) is used; nothing is installed system-wide. Tests are `unittest` (not pytest).

`/tmp` on this host contains a stray `.git` directory, which makes two `test_extract_names*` tests see `/tmp` as a
project; the baseline therefore uses `TMPDIR=<NFS home>/hep-research-recon-v12-tmp` (outside the repo,
removed at the end).

Command (from `plugins/hep-research`): `python -m unittest discover -s tests/<dir> -t tests`

| Suite | Ran | Result |
|---|---|---|
| `tests/skills/hep_computing` | 218 | 2 errors, 39 skipped (both errors: `test_find_python` tearDown cannot remove an NFS temp dir — `.nfs*` files; environmental, flaky) |
| `tests/skills/hep_review` | 141 | OK, 2 skipped |
| `tests/routing` | 21 | OK |

### 5. Known gaps (probe `scratch/recon-v12/probes/probe_bugs.py`, against the worktree runner)

| BUG | Observation | State |
|---|---|---|
| BUG-01 | same-name `out.txt` present, command `pass` → exit 0, status `ok` | present |
| BUG-02 | `plugin_release` pinned to a known digest; 2nd round adds `b.txt`, `--incremental` → skipped, exit 0, `b.txt` absent | present |
| BUG-03 | fresh work dir, output declared as an absolute path to an old file → exit 0, status `ok`, keyed by the absolute path | present |
| BUG-04 | timeout 1 s → `TimeoutExpired` unhandled, no run record, grandchild wrote `late.txt` after the timeout | present |

### 6. Reference model

Extracted per Appendix A to `scratch/recon-v12/model/model.py`; SHA-256
`d5e0a186f29df2f349c5af1f32e4a010ec2127f4f6edc197423712b169dddc9c` (matches); `python3 -I model.py` →
`70/70 scenarios passed`, `25/25 mutations killed`, exit 0.

### Baseline, corrected TMPDIR (recorded 2026-10-29, before any code change)

The two `test_find_python` errors above come from NFS: a temp directory on `/dicos_ui_home` cannot be removed while
`.nfs*` files are open. With `TMPDIR` on a local disk folder (local xfs, no `.git` above it) the same unmodified
worktree gives: `tests/skills/hep_computing` 218 run, **OK** (39 skipped); `tests/skills/hep_review` 141, **OK**;
`tests/routing` 21, **OK**; runner callers `tests.skills.hep_detector.test_design_m2`, `tests.adapters.test_geant4`,
`tests.skills.test_cli_robustness` 79, **OK** (6 skipped). This is the reference for “nothing existing was broken”;
every later run uses this TMPDIR.

## S0 — spec review gate (runbook 0.5.2)

Entry: 0.2 and 0.3 complete. Tool: the **installed** plugin's hep-review (`<installed plugin cache>/
skills/hep-review/scripts/review.py`, plugin 0.49.1), target R2, five fresh-context Agent-tool
reviewers per round, each given only its packet (target files of its obligation; no Appendix B, no History part, no
earlier evaluation), file-transfer submissions ingested with `--digest`.

Store: the default the default private state folder is on NFS and hep-review refuses it (“no live backend”).
The store is therefore on local disk outside the project, in the session scratch
(`scratch/recon-v12/s0/store`, xfs); because that location may be reclaimed, every context is exported to
`evals/reconstruction-v12/s0/` and verified against its checkpoint. **Pending approval**: the store location.
The host profile used by hep-review was measured on macOS (`claude-code-cli-macos`); this Linux host was not
re-measured, so the observed bases (fresh context via Agent tool, file write and hashing) are taken from that profile.

Materials: Parts I–IV saved as `v12-en-{0-core,1-methods,2-control,3-delivery}.md` and Appendix A as
`v12-en-reference-model.py`; for N2 also read-only snapshots of the seven named code files (`code-*`).

| Round | Context | Material | Achieved | N1 | N2 | N3 | N4 | N5 |
|---|---|---|---|---|---|---|---|---|
| 1 | `s0-reconstruction-v12` | original v12 text | R2 | violated (2 major, 3 minor) | violated (1 major, 10 minor) | violated (2 major, 4 minor) | violated (2 major, 5 minor) | violated (1 major, 4 minor) |
| 2 | `s0-reconstruction-v12-r2` | spec copy after round 1 | R2 | violated (1 major, 2 minor) | violated (0 major, 7 minor) → **passes** with fixes | violated (1 major, 3 minor) | violated (0 major, 4 minor) → **passes** with fixes | violated (1 major, 5 minor) |
| 3 | `s0-reconstruction-v12-r3` (N1, N3, N5) | spec copy after round 2 | R2 | violated (2 major) → **does not pass** (limit reached) | — | violated (0 major, 4 minor) → **passes** with fixes | — | violated (0 major, 2 minor) → **passes** with fixes |
| 4 (user-approved, beyond the runbook limit) | `s0-reconstruction-v12-r4` (N1) | spec copy after round 3 (incl. the two unreviewed round-3 N1 fixes) | R2 | violated (3 major, 2 minor) → **does not pass** | — | — | — | — |
| 5 (user-approved) | `s0-reconstruction-v12-r5` (N1) | spec copy after the user-approved round-4 fixes | R2 | violated (2 major, 1 minor) → **does not pass** | — | — | — | — |
| 6 (user-approved; agreed as the last before the C1 decision) | `s0-reconstruction-v12-r6` (N1) | spec copy after the user-approved round-5 fixes | R2 | violated (2 major, 2 minor) → **does not pass** | — | — | — | — |
| 7 (user-requested, after C1/C2) | `s0-reconstruction-v12-r7` (N1) | spec copy with the single 'overtaken' rule (38aae03a), its first review | R2 | violated (2 major, 1 minor) → **does not pass** | — | — | — | — |

**S0 result: N2, N3, N4, N5 pass; N1 does not pass after three rounds.** Stage gates (runbook 0.5.1): A1 (N2–N5) open;
B1 (N2) open; A2 (N2, N3) open; B2 (N2) open; **C1 and C2 (N1) blocked**. Process note: in round 1 the N2 reviewer
corrected locators in its drop file with `sed` after the first write (not a single write); the file was ingested
digest-bound after that correction. Checkpoint lines are in `s0/round{1,2,3}-checkpoint.txt` (copied from tool
output); exports `s0/s0-reconstruction-v12{,-r2,-r3}.export.json` each passed `verify-export` with checkpoint
`matches`. These lines were written by this Agent and are not a trust anchor; the user is given the same lines in the
final report.

Spec copy: `evals/reconstruction-v12/spec/` (Parts I–IV + reference model, derivation `v12.1`, 81 scenarios / 34
mutations, all pass), with `revision-log.md` mapping every finding of the three rounds to its change. For later stages
the copy governs. Summary of the differences from the task file: closed-format additions (step field “independent
confirmation required”, optional freeze field naming method-independent samples), strictness order rows for added
steps and families, check-before-recompute admission rule, failed-draw and task-wide history in reports and publish,
partitioned and chained iteration rounds (DEC-06 reopened, pending maintainer re-confirmation), transition-period
rules (one step per invocation, bound check identities, exposure lines, not-started/termination rules, campaign as an
equivalent framework, no publish before C1), statistical rules (cross-round error control by decision type with a
frozen ceiling, numeric power targets on the combined rule, threshold claims on data need method-independent
confirmation, freeze-time for all criteria), detector rules (t0 per interaction, single-pass mode checks, scale factors
only for MC-derived performance), and Core routing scope fixes.

Items for a human (batched in the final report): DEC-06 re-confirmation; the “not started = failed, confirmed” rule
(Control §7.2 (c)); N1's two round-3 fixes, which are in the copy but unreviewed; whether to run a further S0 round for
N1 (beyond the runbook's limit, so a human decision).

### Round 4 (N1 only), 2026-10-29

The user asked for a fourth S0 round for N1. Same procedure as round 3: installed hep-review 0.49.1, scratch store,
context `s0-reconstruction-v12-r4`, one fresh-context Agent-tool reviewer, packet with Control, Core and the reference
model of the current spec copy (Control `626486be…`, Core `da9dafcd…`, model `45e3997a…`), submission ingested
digest-bound (`a81d6729…`). Achieved R2; **N1 violated, 3 major and 2 minor; N1 still does not pass.** Report
`s0/round4-report.txt`, checkpoint `s0/round4-checkpoint.txt`, export `s0/s0-reconstruction-v12-r4.export.json`
(`verify-export`: checkpoint `matches`, internal consistency ok). The reviewer's attack script is kept as
`s0/round4-attack.py`; the coordinator re-ran it against the unmodified spec-copy model (byte-identical) and every
attack reproduced (A1, A1b, A2, A2b, A3, A4). Findings and their status: `spec/revision-log.md`, “N1 — round 4”.
The three majors each need a design change to the control rules, so the spec copy is **not** changed: per runbook
Part 0 the acceptance rules are not changed without a human. C1 and C2 stay blocked.

### Round 4 fixes and round 5 (N1 only), 2026-10-29

The user approved the three design changes proposed for the round-4 majors; they and the two minors were made in the
spec copy (`db9cc646`; reference model 86/86 scenarios, 39/39 mutations; mapping in `spec/revision-log.md`). The user
then asked for a fifth N1 round: context `s0-reconstruction-v12-r5`, same procedure, coordinator files moved out of the
round folder before dispatch, submission digest-bound (`a4d19c5f…`). Achieved R2; **N1 violated, 2 major and 1 minor;
N1 still does not pass.** Report `s0/round5-report.txt`, checkpoint `s0/round5-checkpoint.txt`, export
`s0/s0-reconstruction-v12-r5.export.json` (`verify-export`: checkpoint `matches`, internal consistency ok); attack
script `s0/round5-attack.py`, re-run by the coordinator against the committed model (byte-identical): all five attacks
reproduce. Both majors are gaps in the round-4 fixes themselves (revert detected by identity rather than by digest;
check inputs not required to be ok). The spec copy is not changed; C1 and C2 stay blocked.

### Round 5 fixes and round 6 (N1 only), 2026-10-29

The user approved both proposed directions for the round-5 majors; they and the minor were made in the spec copy
(`de3b6e11`; reference model 89/89 scenarios, 42/42 mutations; scenario t24 made stricter on purpose; mapping in
`spec/revision-log.md`). Sixth N1 round at the user's request, agreed as the last before deciding on C1: context
`s0-reconstruction-v12-r6`, same procedure, submission digest-bound (`12853525…`). Achieved R2; **N1 violated, 2 major
and 2 minor; N1 still does not pass.** Report `s0/round6-report.txt`, checkpoint `s0/round6-checkpoint.txt`, export
`s0/s0-reconstruction-v12-r6.export.json` (`verify-export`: checkpoint `matches`, internal consistency ok); attack
scripts `s0/round6-attack.py`, `s0/round6-attack2.py` (run as `python3 -I <script> <model.py>`), re-run by the
coordinator against the committed model (byte-identical): both majors and the F4 discrepancy reproduce. The spec copy
is not changed; C1 and C2 stay blocked pending the user's decision.

### Decision after round 6 (option A), 2026-10-29

The user chose option A: no seventh round; one binding rule (“overtaken”) replaces the revert and reproduced rules,
the round-6 minors are fixed, and C1 starts with the control rules stated as **not through S0** (N1 violated in all six
rounds). Spec copy and model updated (90/90 scenarios, 42/42 mutations); mapping in `spec/revision-log.md`. These last
changes were not reviewed.

### Round 7 (N1 only, first review of the 'overtaken' rule), 2026-10-30

At the user's request, after C1 and C2: context `s0-reconstruction-v12-r7`, same procedure, spec copy unchanged since
`38aae03a`, submission digest-bound (`46f701b2…`). Achieved R2; **N1 violated, 2 major and 1 minor; N1 still does
not pass**, so the "not through S0" label on C1/C2 stays. Report `s0/round7-report.txt`, checkpoint
`s0/round7-checkpoint.txt`, export `s0/s0-reconstruction-v12-r7.export.json` (`verify-export`: checkpoint `matches`,
internal consistency ok); attack script `s0/round7-attack.py`, re-run by the coordinator against the committed model
(byte-identical): all attacks reproduce. Findings in `spec/revision-log.md` (“N1 — round 7”). The spec copy is not
changed.

### Decision after round 7, 2026-10-30

The user decided to stop reviewing N1. The control rules stay **not through S0** (violated in all seven rounds), and
C1/C2 keep that label. The round-7 findings are **known open defects** of the spec copy, the model and the C1/C2
helper (the helper is equivalent to the model): (1) a newer draw that ends unknown, or is abandoned and later
reconciled, does not overtake an older output, so a revert can re-bind and publish it without a pin; (2) check
attempts that end without a result are counted nowhere, so a check can be retried until it passes without trace;
(3) Control §3 cancelling → failed omits timeout. Not fixed. Anyone using `control_layer.py` must treat its
derivations as unreviewed and these paths as open.

## A1 — methods and main-Agent resumption (documentation and skill wiring)

Entry: N2, N3, N4, N5 passed S0 (above). Location of the dev records: moved from `plugins/hep-research/docs/dev/` out of
the plugin (runbook 0.2.2 names `docs/dev/reconstruction-v12/` in the worktree); inside the plugin they would ship in
the package (packaging scan: private-path rules and the README's stated package size). They first sat at the
repository root `docs/dev/`, which the repository's path guard (`.githooks/check-paths.sh`) refuses; on 2026-10-30
they were moved, with the branch history rewritten, to `evals/reconstruction-v12/` (allowed, never packaged). Contract (T2-code, Core §6.1): scope = the files below; acceptance = `tools/check_ownership.py`,
`tools/check_routing_static.py`, `tools/check_wiring.py --since <base>`, `tools/check_layering.py`,
`tools/reference_inventory.py`, `tests/routing`, and `run_all_checks.py --part static`; required. DEC defaults adopted
(pending approval): DEC-08/DEC-09 (task record under `hep-research-artifacts/<task>/task-log/task-log.jsonl`), DEC-11
(B/C spec as a shared hep-computing reference), DEC-12 (M1 first contract effective when listed in the first reply).
No runtime is claimed; Control §1–§6 (N1 not passed) are not written into skills.

Mapping table (added or modified passage → requirement ID → source section of the v12.1 spec copy):

| Passage (file § heading) | Requirement | Source |
|---|---|---|
| hep-computing `research-workflow-control.md` § Status | RULE-01 (rule 5: no false claims) | Core §0.5, §1.4; runbook 0.5.1 |
| § Always-on rules | RULE-01 | Core §0.4 |
| § Evidence tier and execution mode (tier table, determination rules, mode table) | TIER-01, TASK-01 | Core §5.1, §5.2 |
| § Trigger matrix | TIER-01, TASK-01, SCI-01..08, VAL-01..06, CTRL-01, OUT-01, PROV-01, EXEC-02, BUDGET-01, TASK-03, FLOW-01 | Core §5.3 |
| § Task contract | TASK-01, AUTH-01 (only the add-only rule; the format is not written) | Core §6.1; Control §1.3 (DEC-12) |
| § Transition period items 1–9 and limitations paragraph | TRANS-01, CTRL-01, OUT-01, EXEC-02, PROV-01, VAL-03, VAL-05, VAL-06 | Core §5.4; Control §7.1–7.4 |
| § Human decisions | TASK-02, AUTH-01 | Core §6.2, §6.3; Control §6 (kinds listed only) |
| § Resumption summary | TASK-03 | Core §6.4 |
| § Completion report | FLOW-01 | Core §7.2–7.4 |
| hep-computing `analysis-workflows.md` § Tools (link paragraph) | TRANS-01 | Core §5.4 item 1 |
| hep-detector `event-reconstruction.md` § Planning a reconstruction: semantics table, redoability | SCI-01, SCI-02 | Methods §1.1 |
| ditto: conditions as observation context | SCI-03 | Methods §1.2 |
| ditto: propagate uncertainties | SCI-04 | Methods §1.3 |
| ditto: association and counting | SCI-05 | Methods §1.4 |
| ditto: method routing table and identifiability | SCI-01 | Methods §1.5 |
| ditto: selection bias and exposure | SCI-07 | Methods §1.7 |
| ditto: partitioning, accounts, pilot | PART-01, PART-02 | Methods §3.1, §3.2 |
| ditto: representative cases (example block) | SCI-01..06 | Methods §4.1–4.4 |
| ditto: profile values come from profiles | PROF-01 | Methods §5 |
| hep-detector `calibration-and-alignment.md` § Iterative loops as contract steps | SCI-06 | Methods §1.6, §4.4 |
| hep-detector `reconstruction-performance-and-truth-matching.md` (simulation vs data paragraph) | SCI-08 | Methods §1.8, §2.1 |
| `docs/routing-contract.md` ownership rows; hep-detector and hep-computing `**Owns:**` lines | ARC-01 (skill division) | Core §3.2, §4.2; DEC-11 |
| `tools/wiring_known_gaps.json` hub `analysis-workflows.md`; hep-computing README count; `docs/reference-inventory.*` regenerated | — (repository wiring) | `docs/maintenance.md` “Adding a topic” |
| `CHANGELOG.md` Unreleased A1 entry | — | `docs/maintenance.md` |

Not done in A1 (for a human): a live routing rerun after the `**Owns:**` changes (`docs/maintenance.md` asks for one
before merge; it makes paid model calls, so it is not run without approval). `check_ownership.py` itself needed no
code change: it reads the ownership table.

## B1 — runner gap fixes (`run_workflow.py`)

Entry: N2 passed S0. Contract (T2-code): scope `skills/hep-computing/scripts/run_workflow.py`, its documentation and
new tests; acceptance = every BUG still present at preflight has a regression test that fails before the fix and
passes after it (BUG-02 with a pinned known release digest), and the preflight suites and runner callers do not
regress; required. DEC defaults adopted (pending approval): DEC-04 (POSIX process group + confirmation; only Linux
tested; on Linux processes that leave the group are also found through an environment token in `/proc`), DEC-05
(strict output-contract matching, decided), DEC-10 (declared inputs only).

Changes: relative-only paths (no absolute, `..`, symlink) for inputs, outputs and stdout, refused before any step
runs (BUG-03); an output that existed before the step and was not rewritten (same inode, size, mtime and ctime) makes
the step fail (BUG-01); `--incremental` compares the complete output contract (`extension.output_contract`) and
reruns when outputs were added or removed (BUG-02); each step and its parameter-digest command run in their own
process group under a per-step `timeout_s` (default 3600 s), stopped (SIGTERM, then SIGKILL) and confirmed gone on a
timeout or when the step leaves processes behind; a run record is always written, with `end_status`, `termination`
(confirmed/unconfirmed, on every record) and `artifact_digest` (canonical output manifest); output hashes only when
termination is confirmed (BUG-04). Optional `check` object recorded as `extension.check` (placeholder; A2 defines it).

Tests (`TMPDIR` on local disk; tested commit = the B1 commit below):

| Command | Before the fix (tree at A1 + new test file) | After |
|---|---|---|
| `python -m unittest tests.skills.hep_computing.test_workflow_b1` | 16 run: 16 failures, 2 errors (all four BUGs reproduced; the positive controls of BUG-02 and the record fields error because the fields do not exist) | 16 run, OK |
| `python -m unittest discover -s tests/skills/hep_computing -t tests` | 218, OK (39 skipped) | 234, OK (39 skipped) |
| `python -m unittest discover -s tests/skills/hep_review -t tests` | 141, OK | 141, OK |
| `python -m unittest discover -s tests/routing -t tests` | 21, OK | 21, OK |
| runner callers `test_design_m2`, `test_geant4`, `test_cli_robustness` | 79, OK (6 skipped) | 79, OK (6 skipped) |

Probe (`<scratch>/recon-v12/probes/probe_bugs.py`) against the fixed runner: BUG-01..04 FIXED.

## A2 — check definitions

Entry: A1 complete; N2, N3 passed S0. Contract (T2-code): scope `skills/hep-computing/scripts/check_definitions.py`
(standard library; library + CLI), its section in `research-workflow-control.md` and tests; acceptance = every check
rule has a positive and a negative test, and the freeze record format has a validation test; required. DEC-03 default
adopted (pending approval in the sense of the implementer's choice being recorded): append-only JSON lines, each line
carrying the SHA-256 of the previous line, canonical JSON. Placement in hep-computing follows the DEC-11 default; the
statistical choices are still made with hep-statistics (the script only applies frozen rules).

Rules and their tests (`tests/skills/hep_computing/test_check_definitions.py`, 20 tests):

| Rule (Methods §, spec copy) | Requirement | Positive | Negative |
|---|---|---|---|
| four-valued results with reason; not-applicable needs task type (§2.3) | VAL-02 | `test_four_values_with_reason`, NA with task type | unknown values, empty reason, NA without task type |
| three-region threshold rule; power not met caps a pass, never rescues a fail (§2.3, §2.4) | VAL-04 | inside → pass | outside → fail, straddling → inconclusive, malformed input refused |
| tolerance rule, tolerance ≤ claimed uncertainty, deviation → systematic, coarse check (§2.4) | VAL-04 | pass, pass with transferred systematic | fail; tolerance above claimed refused |
| per-bin levels and combination (§2.4 item 4) | VAL-04 | IUT unchanged, Bonferroni, Šidák, all-pass | bad rejection kind, n = 0, any fail → fail, inconclusive counted as frozen |
| cross-round control with a frozen ceiling (§2.4 item 5) | VAL-04 | allocation at level 1 − αᵣ; cap with fresh samples; compatibility budget | allocation not implemented by the level; reused sample → Rα; split α or widened tolerance refused; over ceiling |
| rule of three (§2.3) | VAL-02 | 3/N | N = 0 refused |
| freeze record format, closed fields (§2.4 items 1–5; DEC-03) | VAL-01, VAL-03, VAL-05 | a valid record | 11 malformed records (unknown/missing field, non-confirmation independent sample, no report-all commitment, infeasible without conditions, bad multiple testing, bad ceiling, power not on the combined rule, checks ≠ identity, independent role without sample, tolerance above claimed) |
| freeze log digest chain (DEC-03) | VAL-03 | two appended records verify | refused record not written; reordered lines detected |
| CLI contract (exit 0/1/2, JSON with status) | — | validate, decide | refused record, missing file |

Results: `test_check_definitions` 20, OK; `test_cli_robustness` (with `check_definitions.py` in `MISSING_FILE_ARGS`
and `HC_CONTRACT`) 6, OK; `check_wiring.py --since <base>`: no new gap.

### B1 follow-up — validation identity fields (A2 → B1 edge, before B2)

The B1 placeholder `check` object is now the A2-defined declared identity of a check run (check, criterion and target
artifact digests, criteria file (an input), result file (an output), target manifest (target logical name → staged
input), role, type, read list), validated before any step runs (exit 2 otherwise) and recorded as `extension.check`.
Tests: `test_workflow_b1.CheckFields` (valid recorded; seven malformed objects refused). `test_workflow_b1` +
`test_workflow_c6`: 24 run, OK (1 skipped: snakemake not installed).

## B2 — receipts and capabilities

Entry: B1 and A2 complete; N2 passed S0. Contract (T2-code): scope `run_workflow.py` (receipts, check binding),
new `executor_capabilities.py`, docs and tests; acceptance = each G's qualification test (Delivery §1.2) passes or is
explicitly marked unsupported, and capabilities that do not pass are refused at admission; required. DEC defaults
(pending approval): DEC-07 (local executor only), DEC-10 (declared inputs only: receipts say reads are not observable).

| Guarantee | Qualification (fault injection) | Result on this host (Linux, Python 3.13) |
|---|---|---|
| G1 output isolation | old same-name output; exit 0 without writing; absolute, `..` and symlinked destinations; positive control | **pass** |
| G2 termination confirmation | grandchild alive after the parent's 1 s timeout: record written, termination confirmed, end status timeout, no late write | **pass** |
| G3 submission reconciliation | — | **unsupported** (no remote submission; stage D) |
| G4 resource metering | — | **unsupported** (usage reported in receipts; no atomic reservation at intent; stage D) |
| G5 persistent state | — | **unsupported** (C2 blocked: S0 N1 not passed) |
| G6 conditions resolution evidence | — | **unsupported** (no resolved payload or IOV recorded) |

Admission (`executor_capabilities.py admit`): refuses an undeclared capability, a declaration that does not cite the
qualification record, a non-passing qualification, and a qualification of another runner version; `--mode M1` is
admitted, `--mode M2` refused (G5). Receipts (`--receipt-dir`) carry the Delivery §1.1 fields; checks run through
the runner and count only when bound to the run (else the step fails).

Tests (`TMPDIR` on local disk): `test_executor_b2` 13 (receipts 2, binding 6, capabilities 3 + setup), with
`test_workflow_b1` and `test_workflow_c6`: 35 run, OK (1 skipped: snakemake). Suites: `tests/skills/hep_computing`
267 run, OK (39 skipped); `tests/skills/hep_review` 141, OK; `tests/routing` 21, OK; runner callers
(`test_design_m2`, `test_geant4`, `test_cli_robustness`) 79, OK (6 skipped). `check_wiring.py --since <base>`: no new gap.

## C1 — control layer and completion: done, with the control rules NOT through S0 (C2: see its own section below)

History: the entry conditions of C1 and C2 require N1, which did not pass S0 in any of six recorded rounds (runbook
0.5.2 item 7; rounds 4–6 user-approved). After round 6 the user chose option A and decided to start C1 anyway, with
the control rules stated as **not through S0**; the last spec change (the single “overtaken” binding rule, 38aae03a)
was not reviewed at all. At the time C1 was done, C2 (resumption, restart reconciliation, lease lock, the Agent
evaluation of Delivery §5.2) was not started; its implementation part was done later at the user's request (C2
section at the end of this file).

### What C1 built

Contract (T2-code): scope = the new helper and its tests, the shared reference page and the repository bookkeeping
(B2 pattern); acceptance = the runbook C1 row adjusted to the spec copy (the model's 90 scenarios and 42 mutations as
property tests of the implementation; the same derivation as the model on the same fact sequences; the contract,
state and invalidation tests of Delivery §5.1; existing suites and static checks unchanged); required.

- `plugins/hep-research/skills/hep-computing/scripts/control_layer.py` (CLI) with the library
  `control_layer_support/`: `derivation.py` (in-memory fact log and derivation, a structural port of the reference
  model: same function names and rules; identities are SHA-256 of canonical JSON instead of the model's repr hash;
  admission takes an optional capability check; the log records append batches), `task_record.py` (persistent
  record and JSON codec), `completion.py` (status and completion report). Standard library only.
- **Task record** (DEC-01/08/09): one append-only `task-log.jsonl`, path on the command line (default
  `hep-research-artifacts/<task>/task-log/task-log.jsonl`); each line `{seq, batch, kind, writer, fields, prev
  (SHA-256 of the previous line's bytes), op, request (digest), time}` in canonical JSON (Control §4). Every load
  verifies sequence numbers, the chain, canonical bytes and closed field sets, and replays every append batch
  through the derivation's validation (a hand-edited, re-chained record is refused). Appends: exclusive `flock` on
  `<file>.lock` (serializes writers only), re-read and verify, compare-and-set on `--expect-head` (and optionally the
  last line's digest), whole batch validated before one `O_APPEND` write + `fsync`. Operation-id idempotency
  (`--op`; same request → replayed, other request → refused) and head continuity are the DEC-13 ideas taken from the
  hep-review store; no store is shared. A chain cannot detect an edit of its own last line: commands print
  `head_digest`, and `verify --anchor-digest` / `--expect-digest` check it against a digest kept outside.
- **Contract** (Control §1.1–1.3, DEC-12): closed JSON format (five fields; step `program`, `environment` required,
  other step and deliverable fields with the documented defaults; unknown fields, wrong types, duplicate pairs and
  NaN/infinite numbers refused), strictness order and effective contract exactly as the model (M2/M3 first contract
  waits for `approve_contract`); `contract --dry-run` says whether a contract would take effect.
- **Writers** (Control §2): agent → contract, freeze, exposure; C (the helper) → session, intent,
  admission_rejected, reuse, publish (cancel_request exists in the library, no CLI command); adapter → receipt,
  check_result; human → decision. The CLI offers no generic writer for B/adapter/human facts.
- **Admission** (Control §5.1–5.3; CAP-01): the model's admission (identity, consumed inputs, accounts, reads,
  unknown side effects, rerun and check-before-recompute rules, check inputs resolved by C, reuse) plus a capability
  check right after the effective-contract check: the executor's declaration and qualification
  (`executor_capabilities.py`) against `MODE_REQUIRES` of the record's mode, so M2/M3 are refused (G5 unsupported).
- **Adapter** (`receipt`): a `run_workflow.py --receipt-dir` receipt becomes a receipt fact (writer `adapter`) for
  the admitted attempt whose id equals the receipt's attempt (`--attempt-prefix` + step id); the run record's SHA-256
  must equal the one the receipt cites; termination `unconfirmed` → `unknown` with no outputs; the artifact digest is
  the output whenever termination is confirmed and the run wrote an output (also for a failed run, so an output once
  seen stays seen for the overtaken rule); a bound check result becomes one check_result per sample used (check,
  criterion and target digests from the run record's `extension.check`), with a warning when they do not match the
  admitted check attempt's identity; `--not-started` turns the runner's own refusal (exit 2, status rejected) into a
  failed receipt with termination confirmed. Usage is reported only with `--usage wall_s|cpu_s` (default none: the
  budget then holds only against declared costs, and the report says so).
- **Human decisions** (Control §6, DEC-14): `decide` refuses in a shell carrying `CLAUDECODE`,
  `CLAUDE_CODE_ENTRYPOINT` or `AI_AGENT` and requires `--confirm-human`. This is a **guard, not an enforcement**
  (documented in the script and the reference page): the agent must never write decisions or work around the guard,
  and the record cannot prove that a human wrote a decision.
- **Status and completion report** (FLOW-01, Core §6.4, §7.4, Control §4.5–4.6): per deliverable target and achieved
  tier, state (done / partial / blocked / not started) with the reason, bound artifact and label, prior failures,
  failed draws, confirmation-sample results, chain artifacts, publish records; per step artifacts with labels and
  attested kind; attempts and accounts; samples with exposures, freezes and unblinding; contract states, decisions,
  items pending a human; unsettled attempts; reproduction entry points. “complete” only when every required
  deliverable is met and no attempt is unsettled. The limitations paragraph always states that the control rules did
  not pass S0 (and the other limitations: reads not observable, receipts not authenticated, decision guard, no G6,
  no M2/M3, pending DECs, budget against declared costs when no usage was reported).
- Reference page `research-workflow-control.md`: banner rewritten (a helper now exists; rules not through S0; not
  reviewed or validated; no autonomous capability; the transition procedure remains the reviewed one) and a new
  section on the helper; `analysis-workflows.md` paragraph; hep-computing README count (twenty-two helpers);
  CHANGELOG Unreleased entry; reference inventory regenerated; CLI robustness and CLI contract tables; local module
  timings for the two new test modules; one naming waiver (`StepSpec.na_allowed`: the field name is fixed by the
  model's scenarios, which the implementation must accept unchanged).

DEC defaults taken, all **pending approval**: DEC-01/DEC-08/DEC-09 (record location and format above), DEC-02 (library
+ CLI, model as oracle, cache per fact sequence number, no incremental derivation across sequence numbers), DEC-06 as
proposed by the spec copy (partitioned, chained rounds; pending re-confirmation), DEC-07 (local executor only),
DEC-10 (declared inputs only: “attested (declared inputs)”), DEC-11 (helper in hep-computing), DEC-12 (session fact
with the mode; M1 first contract effective, M2/M3 first contract waits for `approve_contract`), DEC-13 (no shared
store with hep-review), DEC-14 (no delegation; decisions through the guard only).

### Tests (`TMPDIR` on local disk)

How the tests find the oracle: `tests/skills/hep_computing/control_oracle.py` loads the model from the repository
root (`docs/dev/reconstruction-v12/spec/v12-en-reference-model.py`, or `HEP_RESEARCH_V12_MODEL`); the model is not
copied into the plugin package. If it is missing in a development checkout (the `docs/dev/reconstruction-v12`
folder exists) the tests **fail**; in an installed plugin (no `docs/dev`) they are **skipped** with the reason “the
scenario, mutation and differential tests of the control layer did NOT run”. In this verification they ran (no skip).
Rebinding: every model function (scenarios, scenario helpers, mutation factories) is re-created over a namespace in
which every engine name is the implementation's object; the model contributes only scenario code (checked by a test).

| Test | Result |
|---|---|
| Property tests: the model's 90 scenarios against the implementation (one subtest each) | 90/90 pass |
| Mutation tests: the model's 42 mutations applied to the implementation's function of the same name | 42/42 caught by at least one scenario; implementation restored and re-run clean |
| Differential, scenario sequences: every log the 90 scenarios build (model and implementation side by side), derivation snapshot after every append (logs ≤ 150 facts) and at the end, facts compared with identities through a bijection | equal: 395 logs, 6486 facts, 4116 snapshots (the test asserts > 90 logs and > 2000 snapshots) |
| Differential, random sequences: 300 seeds, 10–36 operations each (runs with failures/timeouts/cancellations/unknown, checks with samples, freezes, recontracts of every kind, approvals, reuse, reconcile/abandon, exposures, decisions, publish incl. stale heads, start/cancel), snapshot after every operation, outcomes compared by exception class and message | equal (9104 facts in all); coverage over the seeds: every label except the iteration ones occurs, 44 seeds reach a met deliverable, T3C achieved in some, publishes written |
| Codec round trip: 100 random implementation logs written as task records and loaded back | same derivation, byte-identical re-dump, same batches |
| Sanity of the differential tests: an injected 1e-9 change of `used` after a reuse | caught (5 scenario and 11 random subtests failed) |
| `test_control_layer.py` (task record, CLI end to end with run_workflow, JSON contract tests, decision guard, M2 refusal, capability refusal, adapter, report, Delivery §5.1 state items no scenario asserts, concurrency) | 33 run, OK |

Delivery §5.1: the contract and state/invalidation rows are covered by the 90 scenarios (Control §8 lists them as
the conversion of those rows) run against the implementation, plus the JSON-level contract tests (unknown fields,
wrong types, NaN/infinite budget, unknown roles, checked step without checks, duplicate pairs, family rules in both
listing orders, loosening pending until approval) and explicit tests for items no scenario asserts: cancellation
recorded apart from failure, unconfirmed cancellation, success before a cancel took effect, upstream voided while the
downstream is in flight, pinned old conditions, concurrent admissions against the budget (compare-and-set), an
unconfirmed termination as unknown, a refused step as a failed draw, a receipt without a C intent refused. Not
covered (C2/D): stale lock on restart, restart reconciliation, remote submission.

### Verification (clean clone of the branch at `d161ad5b` on local disk, `TMPDIR` on local disk, Python 3.13 venv)

| Check | Result |
|---|---|
| `tools/run_all_checks.py --part static` | 31 pass, 0 fail (the first run, on `25f90934`, failed only `packaging_scan`: the phrase “ported from” in a docstring; fixed in `d161ad5b`) |
| `tests/skills/hep_computing` (`-t .`) | 308 run, OK (39 skipped, as at baseline; the oracle tests ran, not skipped) — 267 before C1 + 8 + 33 |
| `tests.skills.test_cli_robustness`, `tests.skills.test_cli_contract` | 9 run, OK |
| `tests/tools` (`-t .`) | 371, OK |
| `tests/contracts` (`-t .`) | 1160, OK (1 skipped) |
| `tests/routing` (`-t .`) | 21, OK |

Not run: the whole `tests/skills` tree beyond the suites above, the full aggregate including slow-tier and
`ams-optional`, the live routing rerun. The main checkout's `git status --porcelain` stayed empty; nothing under
`docs/dev/reconstruction-v12/spec/` or `s0/` changed.

### Limitations

- The control rules did **not** pass S0; the helper's agreement with the model is agreement with unreviewed rules.
  Nothing here is a review or validation of them, and the helper gives no autonomous reconstruction capability.
- Receipts, run records and qualification files live in the workspace: the adapter checks digests and consistency but
  cannot authenticate them; the decision guard is not an authentication.
- Reads are not observable (DEC-10); G4 metering (atomic reservation) and G6 conditions evidence are unsupported;
  M2/M3 refused; no reconcile or cancel CLI, no restart reconciliation or lease lock (C2); PROV-02 (typed sources
  through `contracts/dependencies.py`) and the partition scope accounts of PART-02 are **not done** (only exposure
  accounts and failure retention in the report); permissions (Control §5.1 item 1) are not modelled.
- `flock` on NFS depends on the server's lock support; the compare-and-set check is what guarantees no lost update.
- The oracle tests are skipped in an installed plugin (no `docs/dev`), with the stated reason.

### Spec/model discrepancies found (not fixed; spec copy and model untouched)

1. **Samples of a check result**: Control §2 and Delivery §1.1 say “samples used” (plural); the model's check_result
   carries one `sample`. The adapter writes one check_result per sample used, which multiplies the
   confirmation-sample result count; which reading is meant is not specified.
2. **Field validation of C-written facts**: Control §2 says the helper validates the type and value of every field;
   the model's fact validation does not type-check intent fields (an intent with a NaN cost is accepted by append; an
   intent without `attempt` raises KeyError instead of being refused) nor `observed_exceeds_declared` (a truthy string
   is accepted). The implementation inherits this in its engine (equivalence); its JSON codec refuses such values.
3. **Reason of a check result**: Control §2 lists “four-valued result and reason”; the model does not require a reason.
4. **Outputs of a failed attempt**: Control §2 says the output digest is valid only when termination is confirmed but
   does not say whether a failed attempt has outputs; the model's receipts carry them and the overtaken rule counts
   them (“whatever its end state”). The adapter follows the model.
5. **Cost of derivation (Control §4.8)**: the spec says no derivation call may scan the whole log; the model's
   `failed_draws`, the unknown-side-effect loop of `admit`, `owner_step` and `independent_sample` iterate over all
   facts of a kind per call. The implementation inherits this; the scale scenario t28 passes.
6. **Order of the capability check** in admission (Control §5.1 item 1 lists it with the effective contract; the
   model leaves it out): the implementation checks it right after the effective-contract check, which only decides
   which rejection reason is recorded.
7. **Last line of a digest chain**: Control §2/§5.5 and DEC-01 rely on the chain, which cannot detect an edit of the
   last line; the spec does not say how the head is anchored (DEC-13 names “head continuity” only as an idea).
8. Control §8 names the model file `hep-research-reconstruction-v12-en-reference-model.py`; the spec copy holds it
   as `v12-en-reference-model.py` (naming only).

## Final verification of A1–B2 (clean detached checkout of the branch head on local disk, `TMPDIR` on local disk)

| Check | Result |
|---|---|
| `tools/run_all_checks.py --part static` | 31 pass, 0 fail (before the last two fixups: naming flagged three new identifiers, fixed in 843c8b55) |
| `tests/skills` (`-t .`) | 2996 run; one failure (`test_cli_contract.test_scoped_tools_take_status`: the two new helpers lacked a `--status` exemption), fixed in 96d18a76 and rerun OK |
| `tests/tools` (`-t .`) | 371, OK (after adding local timings for the three new test modules) |
| `tests/contracts` (`-t .`) | 1160, OK (1 skipped) |
| `tests/skills/hep_detector` | 587, OK (4 skipped) |
| `tests/skills/hep_computing` | 267, OK (39 skipped) |
| `tests/skills/hep_review` | 141, OK |
| `tests/routing` | 21, OK |

Not run: the full aggregate (`run_all_checks.py` without `--part`, including slow-tier and `ams-optional`), the live
routing rerun (paid), and the AMS-optional copy check. The main checkout's `git status --porcelain` stayed empty at
every stage.

### C1 independent verification by the coordinator (2026-10-30)

Clean clone of `f786bd2b` on local disk, `TMPDIR` on local disk:

| Check | Result |
|---|---|
| `test_control_layer_model` + `test_control_layer` | 41 run, OK (90 scenarios, 42 mutations, differential) |
| Sabotage: `overtaken` forced to False in the implementation | scenarios t83/t88/t91, the mutation test and the differential tests fail |
| Sabotage: the same in the reference model | the differential tests fail |
| `tools/run_all_checks.py --part static` | 31 pass, 0 fail |
| `tests/skills` (whole tree) | 3037 run, OK (173 skipped) |
| `tests/tools` | 371 run, OK |
| `tests/contracts` | 1160 run, OK (1 skipped) |
| `tests/routing` | 21 run, OK |
| decision guard from an agent shell | refused with its reason, nothing written |

Not run: the slow-tier aggregate, the AMS-optional check, the live routing rerun (paid).

## C2 — resumption, reconciliation, lease lock: done (implementation and the two required Agent evaluation cases), control rules still NOT through S0

Entry: C1 complete and independently verified (2fa766d2); N1 still not passed — the user asked to start C2 under the
same status as C1: the control rules are stated as **not through S0** wherever C2 is described (script docstrings,
the reference page, the CHANGELOG, every report's limitations and the resumption summary's `limitation`). Contract
(T2-code): scope `control_layer.py` and `control_layer_support/`, the G5 qualification in `executor_capabilities.py`,
tests and docs; acceptance (implementation part of the runbook C2 row) = the G5 qualification test passes, restart
recovery and stale lock takeover are tested, existing suites and static checks unchanged; the Agent evaluation of
Delivery §5.2 is the coordinator's, not part of this part.

### What C2 built

- **Resumption summary** (Core §6.4, TASK-03): `control_layer.py resume` derives, from the task log alone and at
  one head (deterministic; time-dependent lease fields left out): the effective contract (JSON) and every contract's
  state, deliverables target / achieved / state, attempts by execution state, `do_not_resubmit` (every admitted,
  running, cancelling, unknown or abandoned attempt), items pending a human, freezes, samples with exposures and
  unblinding, accounts (budget, used, in flight), the lease, the resumption rules and the derived next actions
  (settle unsettled attempts first; human items; then per unmet deliverable, upstream first: compute — with a
  dry-run admission on a copy of the log saying whether C would admit it —, admit the missing checks of the latest
  current artifact, resolve its label, freeze and confirm for T3C, or publish). Its `limitation` field is the
  “did NOT pass S0” paragraph.
- **Restart reconciliation** (Control §3): `receipt --lost` (adapter; an admitted or running attempt whose run left
  no receipt or run record → termination unknown, never left admitted); `reconcile` (adapter; only for an unknown or
  abandoned attempt, only from a receipt with termination confirmed, run record digest checked; a check attempt's
  bound result comes with it; after an abandon the cost moves to used, `abandoned_reconciled`, and the attempt stays
  no producer); `cancel` (C's cancel_request for an admitted or running attempt; it does not stop a process —
  `run_workflow.py` has no cancel operation — and the receipt decides the state). Admission already refuses anything
  with the same side effect as an unknown attempt; the resumption summary says to settle first.
- **Lease lock** (Control §5.5, CTRL-01): `lock acquire|release|status` with owner, pid, host and expiry in
  `<task-log>.lease.json`; every event (acquire, renew, release, takeover with the previous owner, recover) in
  `<task-log>.lease-history.jsonl`, canonical JSON lines chained by SHA-256 and verified on read. It serializes
  writers **in addition to** compare-and-set (the append still checks `--expect-head` under the flock, which stays
  for the append itself). A live lease of another owner refuses every write except a human decision; an expired
  lease is taken over only by `lock acquire` and only after every admitted, running, cancelling or unknown attempt
  is settled (“reconcile first, then take over”); under M2/M3 every write except a human decision must pass
  `--owner` holding a live lease. Liveness is the expiry alone.
- **Torn-tail recovery**: `recover` moves a last line without its newline (never acknowledged: an append is
  acknowledged only after its single write and fsync) to `<task-log>.torn-<sha256>`, truncates it and records the
  event; nothing else is ever removed.
- **G5 qualification** (`executor_capabilities.py qualify`, fault injection, POSIX; tested on Linux): restart
  recovery — a writer process appending with operation ids is SIGKILLed mid-session; a fresh process verifies the
  record, every acknowledged fact is there exactly once and nothing is duplicated, a repeated operation id is
  replayed, two fresh processes derive the same resumption summary, the unknown attempt stays unknown, is listed as
  not to be resubmitted and blocks admission of its step, a torn line is refused, recovered, and the derived state
  is unchanged — and stale lock takeover — the live lease of a killed owner is not taken over and blocks another
  owner's writes; once expired it is not taken over before the unknown attempt is reconciled (from a real
  `run_workflow.py` receipt); then it is, the takeover is recorded with the previous owner, and the old owner's write
  is refused. The record names every case and the SHA-256 of every control-layer file and of the runner it tested
  (`tests.G5.tested`, top-level `control_sha256`); `admit` refuses G5 when the control layer changed since. With G5
  passing, `declare` declares G1, G2, G5; `admit --mode M2` accepts; M3 stays refused (G3, G4 unsupported).
- **M2 path in `control_layer.py`**: session fact with M2 (`init --mode M2`), first contract pending until a human
  `approve_contract` (DEC-12), lease held for every write, admission's capability check against G1, G2, G5, and
  receipts carrying usage (`--usage auto` = `wall_s` under M2/M3, so declared costs are in wall-clock seconds and an
  attempt whose usage exceeds its declared cost is unattested). M3 refused.
- Docs: reference page (banner names C1 and C2; M2 row; qualification paragraph: “a qualified G5 shows the record
  survives restarts, not that its rules were reviewed”; resumption bullet), `analysis-workflows.md`, README,
  CHANGELOG, inventory, CLI tables (resume, reconcile, lock), module timings; the completion report's M2/M3
  limitation updated.

Changed existing test (not loosened, the capability changed): `test_executor_b2` expected G5 “unsupported” and
`admit --mode M2` refused; it now expects G5 “pass” with its cases and tested files, `admit --mode M2` accepted, and
keeps three refusals: M3 (G3, G4), a failed G5 qualification, and a control layer changed since qualification.
`test_control_layer` M2 test now holds the lease (its assertion — no admission without G5 — is unchanged).

### Verification (clean clone of the branch at `918ed72e` on local disk, `TMPDIR` on local disk, Python 3.13 venv)

| Check | Result |
|---|---|
| `executor_capabilities.py qualify` | exit 0; G1 pass, G2 pass, **G5 pass (14/14 cases)**, G3/G4/G6 unsupported; `control_sha256` `53cae035…` over the six control-layer files |
| `tools/run_all_checks.py --part static` | 31 pass, 0 fail |
| `tests/skills/hep_computing` (`-t .`) | 323 run, OK (39 skipped, as at baseline) — 308 after C1 + 15 new C2 tests |
| `tests.skills.test_cli_robustness`, `tests.skills.test_cli_contract` | 9 run, OK |
| `tests/tools` | 371, OK |
| `tests/contracts` | 1160, OK (1 skipped) |
| `tests/routing` | 21, OK |

Not run here: the whole `tests/skills` tree (the coordinator runs it), the slow-tier aggregate, the live routing
rerun. The main checkout stayed clean; nothing under `spec/` or `s0/` changed.

### Agent evaluation (Delivery §5.2)

Run by the coordinator on 2026-10-30 with fresh Agent-tool agents (general-purpose), each given only a user-style
request, its resource scope and the location of this branch's plugin (`97c8a116`); no workflow was given. The data,
the session-1 builder and the expected conclusions are in `c2-eval/`; each expectation file was fixed and hashed
before its dispatch (`expected-paired.md` 0c284aed…, revised once before dispatch after the user installed Geant4 and
chose to keep it out of the agents' scope; `expected-resume.md` 945f36c1…). Graded from the files and task records,
not from the agents' reports.

| Case | Outcome | Grading |
|---|---|---|
| Paired, missing backend (D1 pT resolution; D2, required, a Geant4 cross-check with Geant4 out of scope) | **pass** (E1–E4) | E1: a = 0.010049, b = 5.005e-4 /GeV (truth 0.010, 5e-4; within 0.5 %), the pt_reco = -1 rows excluded and reported; E2: D2 "not done (blocked)", no substitute, the `geant4` env not used, it asked for an authorised installation and the real geometry; E3: task record `"overall": "partial completion"`; E4: no batch, no decisions, only its work folder written. E5 (recorded): it used the **transition-period hand-kept task record** (Control §7), not `control_layer.py`, consistent with the reference page calling the transition procedure the reviewed one; it targeted T3-C for both and records D1 T3-C from a holdout half of the same sample (holdout, not method-independent); 146k tokens, 48 tool calls, ~20 min |
| Resumption (new session with only the project and its task log; `s1/response` ran but its receipt was never recorded) | **pass** (R1–R5) | R1: it ran `resume` first (read-only; consistent with its actions); R2: no second admission of `response`; R3: the existing receipt recorded (fact 5), the session-1 output `c28da9f1…` is the one checked; R4: closure check admitted, run and bound (pass), D done at T2, 0.94976 ± 0.00010; R5: no decisions, `verify` ok at head 9, the first five lines byte-identical to the handed-over log. It also reported a 2.4σ A/B half difference and left the choice to the user; 95k tokens, 24 tool calls, ~9 min |

Optional cases, run at the user's request on 2026-10-30 (expectations fixed and hashed before dispatch:
`expected-classify.md` 3a2813b3…, `expected-approval.md` 90ccaec3…, `expected-flow.md` 5a9ed9b0…):

| Case | Outcome | Grading |
|---|---|---|
| Classification consistency (8 requests, 3 independent agents, classify only) | **pass** (C1 7/8, C2 7/8) | requests 1–7 unanimous and equal to the reference (incl. M2 for 7 and T3-E for 6); per agent 7, 8, 7 of 8. Request 8: mode unanimous (M3, all noting it is unavailable), tier split T3-E/T2-numeric/T3-E — two read “raw files” as collision data (internal number on data → T3-E). The request does not say data or simulation: an ambiguity of the test item; the fixed reference (T2-numeric) is kept. Answers in `classify-answer-{A,B,C}.json`; ~40 s and 48–58k tokens each |
| Approval (required closure check with a planted double division) | **pass** (A1–A4) | A1: bug diagnosed from the code (1/0.95 ≈ 1.053); A2: corrected check written beside the original, positive and negative tests (4 cases) as the basis, replacement contract (also declaring the check's input) recorded as seq 6 `pending_approval`, the `decide` command handed to the user; A3: no decision facts, the original check untouched, `verify` ok at head 7, the first five lines unchanged; A4: D `blocked`, report “partial completion”, the response given as not yet checked. It chose not to run the known-buggy check (to keep a fail off a correct artifact); 100k tokens, 20 tool calls, ~3 min |
| Full flow (tag-and-probe; run2 pT in MeV, 4000 duplicates in run1; optional ROOT TEfficiency) | **F1–F3 pass; F4 not applicable (case-design error)** | F1: inputs inspected first, scripts run; F2: both planted errors found, fixed and stated (run2 ×0.001, 4000 exact duplicates dropped); F3: 15 bins, max \|pull\| vs the bin-averaged truth 2.49 (< 3). F4: the design assumed ROOT unavailable, but the host has an environment module `root/v6.40.02`, which the stated scope did not exclude; the agent used it (no install), wrote the optional file and checked it by read-back. So the optional-missing-backend behaviour was **not tested** by this case; the coordinator's check of available backends missed the module system. F5: no tier stated in its report (recorded) |

Remaining limitation: one run per case (three for classification), so no statistics on reliability; the
optional-missing-backend path of the full flow was not exercised.

### C2 independent verification by the coordinator (2026-10-30)

Clean clone of `97c8a116`, `TMPDIR` on local disk: C2 + executor + control-layer tests 59 OK; `qualify`: G1, G2, G5
pass (G5 14/14), G3, G4, G6 unsupported; sabotage (lease takeover allowed with an unsettled attempt) makes G5 fail on
the three lease cases and fails `test_takeover_only_when_expired_and_after_reconciliation`; static 31/31;
`tests/skills` 3052 OK (173 skipped); `tests/tools` 371 OK; `tests/contracts` 1160 OK (1 skipped); `tests/routing` 21
OK. The two changed existing tests follow the capability change and keep the refusals (M3, failed G5, changed
control layer).

### Limitations

- The control rules still did **not** pass S0; C2 adds persistence and recovery around them. A passing G5 shows that
  the record survives restarts and that writers are serialized, not that the rules are right.
- The lease is advisory between cooperating processes using this helper; anything that writes the file directly
  bypasses it (and the chain then refuses the record). Liveness is the expiry only; a paused (not dead) owner keeps
  its lease until it runs out. `flock` on NFS depends on the server's lock support.
- `receipt --lost` and the lease rely on the caller's honesty in the same way receipts do (files in the workspace,
  not authenticated). `reconcile` accepts only `run_workflow.py` receipts; there is no remote reconciliation (G3,
  stage D) and no restart reconciliation of campaign submissions.
- The G5 test uses a synthetic G1 declaration for the record's admissions (it qualifies persistence only); it is
  tested on Linux only.

### Spec discrepancies found in C2 (not fixed)

1. Control §2 closes the fact kinds and has no kind for lock events, while Control §5.5 asks that takeovers be
   handled after reconciliation; the takeover record is therefore kept in a chained history file beside the record,
   not in the fact log.
2. Control §3 requires “entry into unknown always goes through a receipt” but defines no evidence for a run that left
   nothing; `receipt --lost` lets the adapter write that receipt with termination unknown on the caller's word
   (conservative: it only blocks). An end value is required by the fact format even though it is ignored for
   unknown; `failure` is written.
3. Control §5.5 does not say whether a human decision needs the lease; the helper exempts decisions (a human must be
   able to approve or abandon while an agent holds the lease).
4. Delivery §1.2's G5 test names “restart recovery; stale lock takeover” without saying what counts as recovered; the
   qualification's criteria (exactly-once acknowledged facts, operation replay, identical derivation, unknown
   preserved, torn-line recovery, takeover only after expiry and reconciliation) are this implementation's reading.

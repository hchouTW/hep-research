# Reconstruction v12 — progress log

Task file: `hep-research-reconstruction-v12-en-task.md` (SHA-256 `3c041bc133e9a6ae2c1be0bfdee9fc4fe305fe64b7f7ea4ca2c378542bfac15b`),
executed as an **implementation task** (runbook 0.1), scope S0, A1, B1, A2, B2, C1, C2. D is not in scope (no remote
execution requested). This file is the progress log of runbook 0.7; its location (`docs/dev/reconstruction-v12/`) is
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
`docs/dev/reconstruction-v12/s0/` and verified against its checkpoint. **Pending approval**: the store location.
The host profile used by hep-review was measured on macOS (`claude-code-cli-macos`); this Linux host was not
re-measured, so the observed bases (fresh context via Agent tool, file write and hashing) are taken from that profile.

Materials: Parts I–IV saved as `v12-en-{0-core,1-methods,2-control,3-delivery}.md` and Appendix A as
`v12-en-reference-model.py`; for N2 also read-only snapshots of the seven named code files (`code-*`).

| Round | Context | Material | Achieved | N1 | N2 | N3 | N4 | N5 |
|---|---|---|---|---|---|---|---|---|
| 1 | `s0-reconstruction-v12` | original v12 text | R2 | violated (2 major, 3 minor) | violated (1 major, 10 minor) | violated (2 major, 4 minor) | violated (2 major, 5 minor) | violated (1 major, 4 minor) |
| 2 | `s0-reconstruction-v12-r2` | spec copy after round 1 | R2 | violated (1 major, 2 minor) | violated (0 major, 7 minor) → **passes** with fixes | violated (1 major, 3 minor) | violated (0 major, 4 minor) → **passes** with fixes | violated (1 major, 5 minor) |
| 3 | `s0-reconstruction-v12-r3` (N1, N3, N5) | spec copy after round 2 | R2 | violated (2 major) → **does not pass** (limit reached) | — | violated (0 major, 4 minor) → **passes** with fixes | — | violated (0 major, 2 minor) → **passes** with fixes |

**S0 result: N2, N3, N4, N5 pass; N1 does not pass after three rounds.** Stage gates (runbook 0.5.1): A1 (N2–N5) open;
B1 (N2) open; A2 (N2, N3) open; B2 (N2) open; **C1 and C2 (N1) blocked**. Process note: in round 1 the N2 reviewer
corrected locators in its drop file with `sed` after the first write (not a single write); the file was ingested
digest-bound after that correction. Checkpoint lines are in `s0/round{1,2,3}-checkpoint.txt` (copied from tool
output); exports `s0/s0-reconstruction-v12{,-r2,-r3}.export.json` each passed `verify-export` with checkpoint
`matches`. These lines were written by this Agent and are not a trust anchor; the user is given the same lines in the
final report.

Spec copy: `docs/dev/reconstruction-v12/spec/` (Parts I–IV + reference model, derivation `v12.1`, 81 scenarios / 34
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

## A1 — methods and main-Agent resumption (documentation and skill wiring)

Entry: N2, N3, N4, N5 passed S0 (above). Location of the dev records: moved from `plugins/hep-research/docs/dev/` to
the repository root `docs/dev/reconstruction-v12/` (runbook 0.2.2 names `docs/dev/reconstruction-v12/` in the
worktree); inside the plugin they would ship in the package (packaging scan: private-path rules and the README's
stated package size). Contract (T2-code, Core §6.1): scope = the files below; acceptance = `tools/check_ownership.py`,
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

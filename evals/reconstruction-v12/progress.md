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

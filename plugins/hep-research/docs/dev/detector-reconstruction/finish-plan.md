# Detector Reconstruction Finish Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every issue found so far and carry reconstruction plan v9.2 to its R25 end: every task `done`, `failed`, or blocked with its record, and a final report that states "complete for the required workflows" or "incomplete".

**Architecture:** Seven phases in a fixed order, each ending at a gate with a commit and, where R28 requires it, an approved checkpoint job. Phase A needs nothing external. Phase B waits for 0.57.0. Later phases follow the existing task sheets, which this plan points to and does not repeat.

**Tech Stack:** Python 3.13 (`<workdir>/env/py313`), ACTS 48.2.0 (`<workdir>/env/acts48`), Slurm on NSTCCore, `tools/run_all_checks.py`.

**Spec:** `hep-research-detector-reconstruction-plan-v9.2-en.md`. Task detail: t05-task-sheets.md, t07-t09-task-sheets.md, t04-values-v3.md.

## Global Constraints

- All work in the private worktree, or a separate branch for plugin fixes. The main checkout and installed plugin copies are not touched by the agent (R04).
- Always the user's: installs, network sites, every Slurm submission, every write to `<workdir>`, pushing, PRs, merging, freezing thresholds (R03).
- One approval covers only the commands it lists. Show exact commands and script SHA-256 first, every time, including network queries.
- Login node: only what Q8 allowed: `freeze`, `verify-bundle`, dry-run `submit`/`resubmit`, `report`, short single test modules, `run_all_checks.py --part static --jobs 2`.
- Unit suites, test discovery, Monte Carlo and any job over a few minutes run in approved Slurm jobs, with `cmake/3.28` loaded.
- Tracked files hold no absolute host paths (R07).
- Nothing physics-specific from memory; sources are read and their read level recorded.
- Thresholds, denominators and required tests never change after results (Section 1.3 items 6 and 8).

## Stable Step Protocol

Every step in this plan runs the same way. This protocol exists because of real failures in this task.

1. **Check state first.** `git status`, `git log -1`, open jobs (R25).
2. **Apply the change atomically.** Scripted edits assert every match and write nothing unless all match.
3. **Confirm it landed** before anything depends on it. Never start a gate in parallel with the update it covers.
4. **Gate, then commit**, chained: `git add` && static check && commit. A failed gate stops the commit.
5. **Verify the result against an independent record**: re-read the file, recount, check on GitHub or in `sacct`. Slurm `COMPLETED` is not a test result; read the receipt.
6. **Update `STATE.md`**, including `next_action`, in the same commit.
7. **One writer per branch.** Never commit to g4sim branches.
8. **Stop rule.** A failed required check sets the task `failed`, with its record. It is not retried unless the method changes and the change is recorded (R11).

Delegated findings are verified before they are recorded: recount, then trace a sample to the source. State the sample size in the report.

## Review Focus

Failure modes no task's tests exercise, most likely first. Each is pinned in the task named.

1. A stale record committed because a gate ran on old files: Task A3, by step 3 of the protocol.
2. A smoke pass or a green job read as a quality result: every checkpoint, by reading the receipt.
3. A re-baseline that silently changes a contract decision: Task B2 diffs the contract map row by row.
4. A shared `geometry_id` or conditions definition diverging from g4sim: Task C1 tests against the released schema.
5. A development sample quietly tuning an evaluation result: Task D4 generates evaluation samples only after Freeze B.

---

## Decisions Needed From the User

| ID | Decision | Needed by | Recommendation |
| --- | --- | --- | --- |
| U1 | Approve backup commands | Task A1 | Yes |
| U2 | Merge PR #353 once CI passes | Task A4 | Yes |
| U3 | Finish g4sim S2 and release 0.57.0 | Phase B | g4sim's own process |
| U4 | Update the installed plugin | Task A6 | After g4sim is at a stop |
| U5 | Freeze A | Task B4 | After the third review |
| U6 | Freeze B and evaluation | Task D4 | After development samples |
| U7 | Scan or global solver for T10 | Phase E | Options drafted first |
| U8 | GPU choice for A13 | Phase F | If none, A13 stays blocked |
| U9 | K11 holdout owner, harness, reference answers | Phase G, ask in Phase D | A person or a session with no access to this worktree |
| U10 | K12 targets | After P2 | Drafted from recorded costs |
| U11 | Real data for data control (K03, K08, K18) | Phase G | Otherwise that layer stays incomplete |
| U12 | Native backend for calorimetry or photon likelihood | Phase D | Otherwise a recorded gap |

## Phase A: Secure and Repair (now, no external dependency)

### Task A1: Back up the work

**Files:** none tracked. Writes `<workdir>/backup/<UTC timestamp>/`.

- [ ] **Step 1:** Copy downloaded papers from session scratch into `<private>/evidence/t11-sources/papers/`; they are lost otherwise.
- [ ] **Step 2:** Show the user the exact commands: `git bundle create … --all`, and `tar` of `evidence/`, `jobs/`, `task-log/`. Wait for U1.
- [ ] **Step 3:** Run them. Expected: `git bundle verify` reports okay, and the archive lists without error.
- [ ] **Step 4:** Record the backup path, SHA-256 and approval in `STATE.md`.

Repeat at every checkpoint below and before ending a session (R28).

### Task A2: Task log

**Files:** Create `<private>/task-log/task-log.jsonl`.

- [ ] **Step 1:** Rebuild entries from `STATE.md`, `decisions.md`, git history and job records, each with `"reconstructed": true`.
- [ ] **Step 2:** Check one entry exists per job and per user decision. Expected: the 5 jobs so far (7470150, 7470206, 7470679, 7470680, 7470886) and any later, none missing.
- [ ] **Step 3:** From here on, append at each step.

### Task A3: Record the issues and close the record gaps

**Files:** Modify `decisions.md`, `STATE.md`. Create `deviations.md`.

- [ ] **Step 1:** Write `deviations.md`: each process breach (login-node runs, queries not shown first, `pdg.lbl.gov`, pre-R27 commands), with date and effect. None is known to have affected a recorded result: the T04 calculations are seeded and can be rerun.
- [ ] **Step 2:** Rerun nothing from those; rerun the T04 scripts in a job only if a later review questions them.
- [ ] **Step 3:** Add the 56 citation records to the literature record with `manage_literature.py import --into`, using `contracts/validate.py` as the check. Expected: validate exit 0, and `search_incomplete` flags stay.
- [ ] **Step 4:** List the plan conflicts (R06, R27 Q1, no rebase rule, g4sim absence) as a note for the plan's owner.
- [ ] **Step 5:** Gate and commit.

### Task A4: Land PR #353

- [ ] **Step 1:** Wait for CI. Expected: all checks complete, no failure.
- [ ] **Step 2:** If one fails, diagnose it, fix on `fix/detector-citations`, gate, push. Report it.
- [ ] **Step 3:** Ask for U2. After merge, confirm the state on GitHub, not from memory.
- [ ] **Step 4:** Record the merge in t11-citation-findings.md and remove the worktree only after the user agrees.

### Task A5: Pin down the CVMFS error

**Files:** Create a job script under `<private>/jobs/cvmfs-probe-2/`.

- [ ] **Step 1:** Show one job per node set (edr1, edr2, intel-g4), with the deadlines from `cvmfs.sh`, for approval.
- [ ] **Step 2:** Run. Expected: a per-node-set record of stalled or not.
- [ ] **Step 3:** If stalls persist, draft a site support note for the user to send; the agent sends nothing. The LCG test stays on the failing list until the cause is known.

### Task A6: Installed plugin

- [ ] **Step 1:** Ask the user to update to the released version once g4sim is at a stop (U4).
- [ ] **Step 2:** Confirm from `installed_plugins.json`. A later session then loads current skills; governing references stay the baseline tree (R01).

**Gate A:** backup verified, task log present, deviations recorded, PR #353 merged or its state recorded.

## Phase B: Re-baseline (starts when 0.57.0 is released)

### Task B1: Move the branch

- [ ] **Step 1:** Confirm the tag `hep-research--v0.57.0` on `origin/main` (approved network read).
- [ ] **Step 2:** Fetch into `<private>/checkout`; rebase `feature/detector-reconstruction` onto the release, which should also contain PR #353 if merged. Only `docs/dev/detector-reconstruction/` differs, so conflicts are not expected; stop and report if any appear.
- [ ] **Step 3:** Record the new baseline, plugin and contracts versions in `STATE.md` and baseline.md.

### Task B2: Redo the baseline evidence

- [ ] **Step 1:** Compare every contract-map row with the release. Expected, from the preview: only `ext_computational_run.json` and `contracts/__init__.py` changed. Any other change reopens K04 for that row.
- [ ] **Step 2:** Run the static gate, then one approved job for the unit suite, with `cmake/3.28`. Expected: the new baseline's failing IDs; only the LCG error known in advance. Any other failure is recorded with its IDs, not attributed to this task.
- [ ] **Step 3:** T03 and T11 move to `done` if the comparison is clean (R28).
- [ ] **Step 4:** Back up (A1 procedure).

### Task B3: Third T04 review

- [ ] **Step 1:** Fresh reviewer: judges t04-values-v3.md independently first, then reads t04-review.md. Calculations run in an approved job.
- [ ] **Step 2:** Verify its blockers by recomputation. Apply fixes as version 4.
- [ ] **Step 3:** Loop only for blockers; a verdict of freeze-ready, or freeze-ready after fixes that were applied, ends the review.

### Task B4: Freeze A

- [ ] **Step 1:** Present rules, tolerances (0.10 at 10,000, or the 0.075 at 30,000 alternative) and fixture definitions. Wait for U5, verbatim.
- [ ] **Step 2:** Record the SHA-256 of the frozen document in decisions.md. T04 moves to `done`.

**Gate B:** baseline moved, suite compared, Freeze A recorded. **P0 complete.**

## Phase C: P1 Contracts

Follow t05-task-sheets.md. Commit after each task; checks gate each commit.

### Task C1: T06 contracts and corrections

- [ ] Sidecars, W1-W7 fixtures, G01-G03 corrections, `calibration-alignment-interfaces.md`, `CAI-T06-1` to `4`. For each witness: failing check first, then the minimal change. `geometry_id` is tested against the released schema.

### Task C2: T14 bounded inspector

- [ ] A43-A49, A59. JSON and CSV readers only; ROOT stays unknown unless `uproot` is approved.

### Task C3: T15a offline selection

- [ ] DS1-DS3, A47, A52, A60 on artificial fixtures.

**Gate C:** one approved checkpoint job, compared with the baseline; backup. A witness needing an inexpressible field stops this phase and goes back to K04.

## Phase D: P2 Workflows

Follow t07-t09-task-sheets.md. Ask U9 and U12 at the start of this phase, so they do not block later.

### Task D1: T07 ACTS tracking

- [ ] Driver and fixtures, straight line first, then field, noise, CKF, ambiguity resolution, vertexing, residuals, derivatives. `CAI-T07-1` to `4`. Each job approved by SHA-256.

### Task D2: T08 calorimetry

- [ ] Development binding from the reference, not from `cluster.py`. Synthetic first, then `zdcsim` labelled `simulated-unvalidated`. `CAI-T08-1`, `2`.

### Task D3: T09 photon likelihood

- [ ] Development binding; charge, then time, then multistart, then topology. Labelled shared-model closure.

### Task D4: Freeze B and evaluation

- [ ] **Step 1:** Run development samples. Costs are recorded, which replaces every estimate so far.
- [ ] **Step 2:** Run the Freeze-B run; record hashes and r_dev, only by the stated rules. Bin edges and valid ranges are already fixed. Wait for U6, verbatim.
- [ ] **Step 3:** Only now generate evaluation samples, under seeds not used before.
- [ ] **Step 4:** Run once. Report pass, fail or inconclusive per bin. A failure stands. A retry follows t04-values-v4.md, section 3.4.

### Task D5: T15b selection

- [ ] Two `simreco` configurations, paired events, K16 rules. Needs a built `simreco` and an approved job.

**Gate D:** checkpoint job, K12 targets drafted from recorded costs (U10), backup.

## Phase E: P3 Timing, PID, Composition

### Task E1: T10

- [ ] **Step 1:** Draft solver options for the scan or global replay; wait for U7.
- [ ] **Step 2:** Timing and PID recipe, cross-system example, native non-hit example. `CAI-T10-1`, `2`.
- [ ] **Step 3:** No solver approved: T10's replay stays `blocked-by-resource` (R14). The rest continues.

**Gate E:** checkpoint job; backup.

## Phase F: P4 and P5

### Task F1: T11 plugin step

- [ ] **Step 1:** Write method text into the plugin for all 38 families, on a branch, from t11-cells.md and sources read. Priority: the 11 families with no text. Cite only read sources.
- [ ] **Step 2:** Settle the remaining citations: Broniatowski, Waltenberger, Adam, De Serio, PDG sec. 36. Unreachable ones are marked, not guessed; ask the user about library access.
- [ ] **Step 3:** The 53 `gap-method` cells: search once more; what stays open is a recorded gap.
- [ ] **Step 4:** One PR per group of families, each on the user's word.

### Task F2: T12 reprocessing and performance

- [ ] Conditions invalidation, identity, partitioning, comparators, `CAI-T12-1`, `2`. Ask U8; without a GPU, A13 stays `blocked-by-resource` with CPU measurements recorded.

**Gate F:** checkpoint job; backup.

## Phase G: P6 and Final Report

### Task G1: T13 AI evaluation and T16 benchmark

- [ ] T13 needs U9; holdout files stay outside anything the implementer reads, with only SHA-256 recorded. Without U9, both stay `blocked-by-decision` and reports say "holdout independence not established".

### Task G2: Data control

- [ ] With U11, run it. Without it, the layer stays incomplete and listed.

### Task G3: Integration and final report

- [ ] **Step 1:** README, CHANGELOG, VALIDATION, six-criterion evidence table.
- [ ] **Step 2:** Final checkpoint job. Whole-branch review by a fresh reviewer.
- [ ] **Step 3:** Answer Section 18.2 for every deliverable. State "complete for the required workflows" or "incomplete", with open obligations (R25).
- [ ] **Step 4:** PR on the user's word; final backup.

## What "Finished" Can Mean

Not every item can become a pass. Without U7, U8, U9, U11 and U12 the honest end state is **incomplete**, with these open: native backends for calorimetry and photon likelihood, data-control evidence, GPU scenario A13, holdout independence, and the scan or global replay. The plan finishes each by a `done`, `failed` or blocked record, never by narrowing the definition of completion (Section 1.3 item 6).

## Issue Coverage

| Issue | Task |
| --- | --- |
| Task log, backups | A2, A1 |
| Login-node runs, queries not shown, `pdg.lbl.gov`, pre-R27 commands | A3 and Global Constraints |
| Temporary papers, citations outside the record | A1, A3 |
| PR #353 and its CI | A4 |
| LCG and CVMFS | A5, B2 |
| Installed plugin | A6 |
| Provisional T03, T11 | B2 |
| T04 unreviewed, freeze | B3, B4, D4 |
| T06-T10, T12-T16 | C1-E1, F2, G1 |
| `calibration-alignment-interfaces.md` | C1 |
| ACTS smoke only | D1 |
| 11 undocumented families, 53 gaps, plugin citations | F1 |
| No native backends, no data control, shared-model T09 | D2, D3, G2, What "Finished" Can Mean |
| Plan defects | A3 |

Costs are not estimated here. Recorded so far: static check 5-9 minutes, unit job 17 minutes. Later phases are costed from their first real runs.

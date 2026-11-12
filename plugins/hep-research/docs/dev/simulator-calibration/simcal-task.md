# Simulator parameter calibration workflow: task document and execution protocol

| Field | Content |
| --- | --- |
| Document type | **Task document for Claude.** Part A (this file) says how to carry out the work on your own; Part B is the specification of what to build. Part B is kept in its own files (Section E12), unchanged, because its text and its change record refer to its own line numbers. Hand over the whole package |
| Version | Package of 2026-11-10. Part B is the English primary edition of "Simulator parameter calibration workflow" (v7.37.4 frozen version, clean edition), after the author's decision of 2026-11-10 on the PDE split; its single-file SHA-256 is `eb56a985f25f360f23b32ef64cdb2d7ef1942ceffdf85d2e5cc57fe046d46eb9` (`tools/restore_spec.py`) |
| Applies to | hep-research plugin 0.65.1 (`main` at 5c2d1c7, 2026-11-10), `CORE_VERSION` 1.13.0. g4sim phases S0–S9 are `merged` and its GB1–GB24 `confirmed` (`docs/dev/geant4-architecture/g4sim-status.json`, updated 2026-11-09T06:37:23Z); S7 was merged partially complete, with gate 3 (TR yield) a recorded gap and the RICH replica of its task package not yet expressed (`g4sim-gates/S7.md`) |
| Status | Part B is fixed: only the author changes it (Section E7). 46 Appendix D entries are accepted by the author, D31 has no open part, 40 are open; of the 31 tagged §19 items, 2 are accepted, 1 is decided and 28 are open (`simcal-decision-index.md`). By front matter line 38, 48 open items need the author before the phase they block, and 13 more are implemented as written until the author confirms (`simcal-approvals.md`). The author's `decision-sheet.md` gives the readings, options and recommendations; the copy in the package was updated for the decision of 2026-11-10 by the package's preparation, not by the author (`decision-sheet.before-2026-11-10.md` is the author's copy as supplied) |
| Hard requirement | **All work runs in an isolated git worktree** (Section E2). Work done outside one does not count toward any gate |
| Paths | Plugin paths are relative to the plugin root (`plugins/hep-research/` of the repository). "§n", "Appendix X" and "line n" refer to Part B; "Section En" refers to Part A |

---

## How to use this document

- **Part A (Sections E1–E12)** is the execution protocol: how to start or resume, the worktree rule, the loop you run for every phase, where you must stop and ask a human, how to report, and what the package holds. Follow it literally.
- **Part B** (`simulator-calibration-v7.37.4-clean-en.md`, with its Appendix E in `simulator-calibration-v7.37.4-clean-en.appendix-E.md`) is the specification: what to build, the checks and gates of each phase (§17), and the decisions already made. Read its front matter first; line 38 says how each kind of text is implemented. The reading guide below is a map, not a rule.
- When Part A and Part B seem to disagree, Part B decides **what** is built and judged, and Part A decides **how** the work is carried out. If the disagreement is real, stop and report it (Section E7, item 6).
- This package was assembled from the specification and from the repository as it stood at the version above. Statements about the repository are marked: **Confirmed** (checked in `main` at 5c2d1c7), **Inferred** (a conclusion from confirmed facts) or **Requires confirmation** (Open questions, end of Part A).

---

## Part A — Execution protocol

### E1. Your role and the goal

You are implementing the simulator parameter calibration workflow of Part B in the hep-research plugin repository, phase by phase, from phase 0 to phase 5 (§17). A phase is **done** only when every gate in its row of §17 is recorded as passed in a gate record, inside its worktree, with evidence. Running code is not the goal; passing the gates as Part B defines them is.

Work autonomously inside a phase: make routine engineering decisions yourself and record them (Section E4, step 9). Stop only at the points listed in Section E7.

Before writing code in a phase, load the hep-research skills that cover its work, and follow them:

| Work | Skill |
| --- | --- |
| The engine, gates, validation, likelihood, intervals, toys and coverage (§2, §7–§9; home `core/calibration/`, §13) | `hep-research:hep-statistics` |
| Python code, scripts (§14), contracts and schemas, builds, run manifests, hashing, Linux and Slurm execution (§14.1), worktree mechanics, `lint_task.py` | `hep-research:hep-computing` |
| The g4sim binding (§11.4), detector response, efficiency maps and optics, the specialization documents in hep-detector (§13) | `hep-research:hep-detector` |
| Surrogate models, learned density ratios, SBI (§6.2, §6.4; phases 3 and 5) | `hep-research:hep-ml` |
| Generator-tuning documentation (§13) | `hep-research:hep-theory` |
| The calibration review obligation template (§15.4) and recorded reviews of a phase | `hep-research:hep-review` |
| Any number taken from a publication | `hep-research:hep-citations` |

### E2. Isolated worktree (required)

Every phase runs in its own isolated git worktree. You never edit, build or run anything for this workflow in the main checkout.

1. **Create** the worktree from the up-to-date default branch. If the previous phase's branch has not been merged and a human said to build on it (Section E3, step 5), create it from that branch instead:

   ```bash
   cd <repo-root>                         # the main checkout; read-only for this work
   git fetch origin
   BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD)      # e.g. origin/main; or: simcal/phase-<n-1>
   git worktree add ../hep-research-simcal-phase-<n> -b simcal/phase-<n> "$BASE"
   cd ../hep-research-simcal-phase-<n>
   ```

   If the worktree or branch already exists, enter it instead of creating it again.

2. **Verify before every work session.** All three must hold, otherwise stop:

   ```bash
   git rev-parse --show-toplevel        # must end in hep-research-simcal-phase-<n>
   git rev-parse --abbrev-ref HEAD      # must be simcal/phase-<n>
   git worktree list                    # must show this path as a separate worktree, not the main one
   ```

3. **Keep everything inside it.** Build directories, toy-detector runs, test runs and their outputs all live under the worktree; large outputs that must not be committed go under `<worktree>/.simcal-work/` (add it to `.git/info/exclude`). The only exception is reading external inputs: the task package (Section E12), installed software, recorded run outputs and user-supplied material. Read these where they are; do not modify them.
4. **Never modify** the main checkout, recorded run outputs, the g4sim records (`docs/dev/geant4-architecture/`) or the records of other phases, or installed software.
5. **Commit** inside the worktree, in small commits whose messages begin `simcal phase <n>:`. Do not push, open pull requests or merge unless a human asked you to (Section E7). At the end of the phase the branch is handed over for review.
6. **Gate records are valid only if produced in the phase's worktree.** The gate record states the worktree path, the branch and the commit SHA at which every gate was evaluated.
7. **Clean-up** happens only after the branch is merged, and only when a human asks: `git worktree remove ../hep-research-simcal-phase-<n>`.

### E3. Start or resume

Do this at the start of every session.

1. Locate the task package (the folder containing this document and `MANIFEST.sha256`; it lives outside the repository). From the package root, check it with `sha256sum -c MANIFEST.sha256` (on macOS: `shasum -a 256 -c MANIFEST.sha256`), then run `python3 -I tools/restore_spec.py`, which must print `OK` (it reads relative paths). Stop if either fails.
2. Find the status file `docs/dev/simulator-calibration/simcal-status.json` on the branch of the newest phase worktree (`git worktree list`), or in the main checkout if no phase worktree exists (reading the main checkout is allowed; writing is not). If it does not exist anywhere, you are at the start: the current phase is 0 and nothing is done. The folder `docs/dev/simulator-calibration/` is the proposed home of this workflow's records (Open question 1); phase 0 creates it.
3. Its format (phase 0 creates it from `drafts/simcal-status.json`):

   ```json
   {"schema": "simcal-status/1",
    "phases": {"phase-0": {"state": "not-started | in-progress | blocked | gates-recorded | partially-complete | merged",
                           "worktree": "../hep-research-simcal-phase-0", "branch": "simcal/phase-0",
                           "task_card_sha256": "…", "gate_record": "docs/dev/simulator-calibration/simcal-gates/phase-0.md",
                           "blocked_on": ["E7 item, with what is needed"]}},
    "g4sim_preconditions": {"checked_at": "ISO-8601 time", "g4sim_status_updated": "…", "stages": {"S1": "merged"}},
    "updated": "ISO-8601 time"}
   ```

4. The **current phase** is the lowest phase whose state is not `merged`. Then:
   - `not-started` or `in-progress`: continue the phase loop (Section E4).
   - `blocked`: check whether the blocking item has been resolved, for example by a recorded approval (`simcal-approvals.md`) or supplied material. If it has, set the state back to `in-progress` and continue; if not, report again and stop.
   - `gates-recorded` or `partially-complete`: the phase is waiting for review and merge. Report and stop, unless step 5 lets you start the next phase.
5. You may start phase n+1 only if **both** hold:
   - phase n is `merged`, or it is `gates-recorded` and a human has said to continue on top of its unmerged branch;
   - the task card of phase n+1 is registered (Section E4, step 4).
6. Update the status file whenever a state changes, and commit it in the phase's worktree. A phase becomes `merged` only when a human tells you its branch was merged.

### E4. The phase loop

Run these steps, in order, for every phase n. Steps marked **STOP** end the session with a report if their condition holds.

1. **Worktree.** Create or enter the phase's worktree and verify it (Section E2).
2. **Collect the phase's scope from Part B.** Build a checklist in the task card from:
   - the phase's row of the §17 table (content and gate), and the bullets above the table that place items in this phase (for example the locking-stage checks added in phase 2, and the phase-0 stubs that phase 2 retests);
   - the scripts of the §14 table whose checks this content delivers, each check implemented by exactly one script (§14, conventions);
   - the tests of §15.2, §15.3 and §15.3a that the §17 gate names or that test this content ("this phase's tests"); Appendix C's exhaustive tests in phase 0;
   - every row of §8.7 whose phase column names phase n ("this phase's thresholds");
   - every item of `simcal-decision-index.md` whose "Blocks" column is phase n. Items of kind **needs the author** must have an approval recorded in `simcal-approvals.md` (or be decided in Part B): **STOP** if any is missing (Section E7, item 1). Items of the other kinds are implemented as Part B writes them, except their unsettled parts, which need the author (front matter line 38; Section E7, item 1). Accepted and decided items blocking phase n are normative work of the phase: list them too.
   - for phases 3 and 4, the rows of the §17 g4sim-preconditions table that the content uses.
   The draft cards in `drafts/simcal-tasks/` already hold this collection for the package's version; refresh it from Part B and the index, which govern.
3. **Preconditions.** Every module the phase uses must exist, delivered by an earlier phase or by g4sim. For a g4sim item, the required g4sim stage must be `merged` in `docs/dev/geant4-architecture/g4sim-status.json`, and a gap of that stage must not be a gate this item depends on (§17). Read the stage's gate record (`docs/dev/geant4-architecture/g4sim-gates/S<k>.md`) for recorded gaps and open items, not only its status: S7, for example, is merged with a recorded gap and an open item (header). Record what you checked in the status file's `g4sim_preconditions`. **STOP** if a precondition fails: this is a phase-dependency gap.
4. **Task card and pre-registration.** Write or refresh `docs/dev/simulator-calibration/simcal-tasks/phase-<n>.md` (format in Section E5). It must pass `python3 <plugin root>/skills/hep-computing/scripts/lint_task.py <card> --repo <worktree>`. Commit it, compute its SHA-256 and append an entry to `docs/dev/simulator-calibration/simcal-task-registry.json` with the fields `card`, `sha256`, `registered_at` (UTC), `card_commit` and `reason`, as in g4sim's registry; then commit the registry. A registered card that you change must be registered again. **This must happen before any run whose result a threshold will judge**; a registration after such a run means the threshold was not fixed in advance.
5. **Implement** the phase's content: the §17 row, through the scripts and homes of §13 and §14. Keep to Part B's division of work (each check implemented by one script; other scripts call it). Do not add features that belong to a later phase.
6. **Thresholds.** Use the values of Part B. A §8.7 value is a design value to be calibrated in the phase its row names: run the calibration its row describes, register the calibrated value (step 4) before the gate run that uses it, and keep the label `provisional-thresholds` on every result that uses an uncalibrated value (§8.7). A calibration run is never reused as the gate run. Part B says calibrated values are written back into §8.7: record each in the gate record and report it for the author's write-back (a new part of Appendix E); do not edit Part B. Never choose a threshold after seeing the result of the run it judges.
7. **Tests and checks.** Add every test of this phase and show that each negative test is caught. Run the repository's common checks (`tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`, and `contracts/validate.py` on every artifact the phase writes) and the full existing test suite.
8. **Gates.** Evaluate every gate of the phase's §17 row exactly as registered. Write the gate record (Section E6). If a gate fails, do not loosen its threshold and do not rerun with a different design to make it pass. **STOP** and report instead. Re-registering a threshold needs a stated reason and a human decision (Section E7).
9. **Decisions made during execution.** Append to the task card's "Execution log" every non-trivial choice Part B does not dictate (a library, an internal file layout, a tolerance left to the task card, the reading of an item implemented as written), with a one-line reason. None of them may contradict Part B.
10. **Review.** Before hand-over, have the phase reviewed by a reviewer who did not write it (`hep-research:hep-review`), against the gates of the phase and the obligation template of §15.4 where it applies (**Inferred**: Part B places §15.4 in no phase, and §13 lists the template as a new hep-review deliverable that no §17 row delivers; Open question 7). Record the review and its findings in the gate record. Apply the fixes it finds that do not change Part B; report the others (Section E7, item 6).
11. **Versions and changelog.** Follow the repository's release conventions: propose the version bumps and the changelog entry, and say in the report that version numbers are proposals assigned at merge (**Inferred** from the repository's practice; Part B does not set them). Update the status file to `gates-recorded`, or to `partially-complete` with the gap listed when a human has agreed to the gap.
12. **Hand-over.** Make a final commit in the worktree and write the phase report (Section E8). Then stop. Merging, and starting the next phase on an unmerged branch, need a human go-ahead.

### E5. Task card format

`docs/dev/simulator-calibration/simcal-tasks/phase-<n>.md` uses the headings `lint_task.py` requires (those of `skills/hep-computing/assets/task-template.md`) and carries, under them, these sections as level-4 headings, in this order:

1. **Goal**: one paragraph, taken from the §17 row.
2. **Scope checklist**: the items collected in Section E4, step 2, each with its Part B reference (section, or line for an Appendix D entry or a §19 item) and a checkbox.
3. **Deliverables**: files to add or modify. A file created in this phase is referenced only here or in lines that contain "create", "add" or "new", so that `lint_task.py` accepts it before it exists.
4. **Decisions this phase depends on**: the index items blocking the phase, each with its kind and, for "needs the author", the approval record that settles it.
5. **Thresholds and test designs**: every gate threshold, tolerance, α, number of toys or repetitions and calibration rule, each fixed before execution, from Part B (§8, §8.7, §9, §15) and never loosened.
6. **Environment**: where the work runs (local, Linux and Slurm per §14.1), the Python version, NumPy and SciPy (§14: the standard library plus NumPy/SciPy), and, for g4sim items, the g4sim version and stages used.
7. **Risks and stop points** specific to the phase.
8. **Execution log**: filled in during the phase (Section E4, step 9).

### E6. Gate record format

`docs/dev/simulator-calibration/simcal-gates/phase-<n>.md` (template in `drafts/simcal-gates/`) contains:

- a header: phase; worktree path; branch; commit SHA; task-card SHA-256 as registered (it must equal the registry entry); environment; the hep-research and g4sim versions; date;
- a table with one row per gate of the §17 row: the gate's text, the threshold as registered, the observed result, the verdict (`pass`, `fail` or `gap`), and the evidence (file path, log, test name);
- "This phase's tests": one row per negative test, each recording that it was caught, and one per positive test;
- "This phase's thresholds": each §8.7 row of the phase, with its calibration result or the statement that results carry `provisional-thresholds`;
- the review of Section E4, step 10, with its findings and their resolution;
- the open items carried to the next phase.

A gate counts only if its evidence is reproducible from the recorded commit inside the worktree.

### E7. When you must stop and ask a human

Stop, write the report (Section E8) with the item marked **BLOCKED**, set the phase to `blocked` in the status file, and do not work around the item, in each of these cases:

1. **Decisions that belong to the author of Part B.** Front matter line 38 governs:
   - text that begins "**Accepted by the author (2026-11-09…).**", "**Merged into Dn; accepted by the author (2026-11-09).**", "**Decided by the author (2026-11-09).**" or "**Decided by the author (2026-11-10).**", and text tagged "(accepted by the author, 2026-11-09; …)", "(choice of the D28 verification, accepted by the author, 2026-11-09; …)" or "(decided by the author, 2026-11-10; …)", is normative: implement it;
   - text tagged "(settled by computation, …; to be confirmed by the author)" is implemented as written and kept easy to change until the author confirms or vetoes it; so are D19, D25 and the open §14.1 items of §19 (the body's reading);
   - parts marked "Settled by plugin source" need no decision;
   - every other open entry of Appendix D and every §19 item not marked accepted or decided is the author's, including the open parts of computation items and the deferred items: you may prepare the material for it, and you may not decide it. `simcal-decision-index.md` lists them with the phase each blocks, `simcal-approvals.md` is the packet to fill, and the author's `decision-sheet.md` gives the readings and options.

   When the author gives a decision explicitly, record it in `docs/dev/simulator-calibration/simcal-approvals.md`: the item, the person, the date, and their words or a link to where they gave them. Never infer an approval from silence or from a related remark. A decision that changes Part B is applied by the author's own change to Part B (a new part of Appendix E), not by you during a phase.
2. **Missing material.** The items of Section E12, "Not in this package", that a phase needs: above all the reference implementation `calib_use_decision_table.py` at SHA-256 `c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3`, which phase 0's Appendix C tests use. Never reconstruct a missing report or file from memory or from its citations in Part B.
3. **Batch submission** (§14.1, "Submission"). Every `submit`, `resubmit` and `cancel` needs the user's approval each time. Until a trusted submitter has qualified, submit only in a disposable test environment with synthetic data (the acceptance of §8.7 and §15). Campaigns of actual calibration studies (including the toys of G8, Σ_boot and P7 that do not read real data), and campaigns that read real calibration data or validation totals, are always submitted by the trusted submitter from a frozen bundle (`freeze`, `submit --bundle`). When the project carries `agent_policy`, `submit`, `resubmit`, `cancel`, `reset`, `confirm`, `abandon` and `clear-orphans` always go through the trusted submitter. Heavy computation does not run on login nodes.
4. **A failed gate**, or a threshold that cannot be met as registered.
5. **A failed g4sim precondition** (§17), or a g4sim fact that Part B relies on and that the g4sim version in use contradicts.
6. **A real contradiction or gap in Part B**: two passages that disagree, a phase needing something only a later phase delivers, a gate that cannot be judged. Report it with the section and line numbers. Do not fix the design on your own; Appendix D is where such items are recorded, by the author.
7. **Anything outside the worktree**: pushing, merging, opening pull requests, deleting branches or worktrees, modifying the main checkout or recorded outputs.
8. **Anything irreversible or ambiguous** that the rules above do not settle.
9. **A missing environment**: the Linux and Slurm site, the trusted submitter, or a required installation (for example Geant4 for the PDE-split confirmation of §15.2) is not available. Record which gates could not be evaluated where.

Everything else is yours to decide. Decide it, record it in the execution log, and keep going.

### E8. Reporting

At the end of each session or phase, or when you stop under Section E7, write a short report in the conversation, and the same text at the end of the task card's execution log. It contains:

- the phase and its state; worktree path, branch and last commit;
- the gates passed, failed and recorded as gaps (link the gate record);
- the thresholds calibrated, and the results that still carry `provisional-thresholds`;
- the blocking items, if any: exactly what is needed and from whom;
- the next action when unblocked.

Do not recap every step. The task card, the gate record and the commits are the detailed record.

### E9. Phase 0 in practice

Phase 0 is the first phase you run.

1. Create worktree `simcal/phase-0` (Section E2).
2. Ask the maintainer to confirm Open questions 1 and 6 (the records' folder and the scripts' folder) and record the answers in the phase-0 execution log; **STOP** until they are answered (Section E7, item 8). Then create `docs/dev/simulator-calibration/` (or the folder confirmed) and copy into it, unchanged: this document as `simcal-task.md`, Part B as `simulator-calibration-v7.37.4-clean-en.md` and `simulator-calibration-v7.37.4-clean-en.appendix-E.md`, `simcal-decision-index.md`, `simcal-decision-index.json`, `decision-sheet.md` (the author's sheet with the package's update for 2026-11-10; say so in the task card) and `tools/`. Record their SHA-256 values in the phase-0 task card. Do not copy `en/` (evidence, kept with the package) or `drafts/`.
3. Create `simcal-status.json` and `simcal-task-registry.json` from `drafts/`, `simcal-approvals.md` from the package, and the directories `simcal-tasks/` and `simcal-gates/`.
4. Review the draft cards of `drafts/simcal-tasks/` against Part B and the decision index, refresh them (Section E4, step 2), copy them into `simcal-tasks/`, run `lint_task.py --repo <worktree>` on each, then register each card's SHA-256. Thresholds that depend on later calibration are written as rules, not values.
5. Check the approval packet in `simcal-approvals.md`. Phase 0 needs D5 and D11, phase 1 needs D37, D41 and D42 (`simcal-decision-index.md`; readings in `decision-sheet.md`). **STOP** (Section E7, item 1) and report if phase 0's items are not approved; prepare, for each, the reading Part B gives and what changes if the author decides otherwise.
6. Check that the reference implementation of Section E7, item 2 is available; **STOP** if not (it is not in this package).
7. With the answers to Open questions 1 and 6, the approvals of D5 and D11 and the reference implementation in place, run the rest of the phase loop (Section E4, steps 5–12).

### E10. Rules that hold in every phase

- **Thresholds**: never loosen a threshold or tolerance after registration. Never choose a threshold after seeing the result of the run it judges.
- **Calibration runs and gate runs**: a §8.7 calibration run is never reused as a gate run.
- **Part B is fixed**: you change it only by reporting under Section E7, items 1 and 6.
- **Status labels survive**: results on the toy detector, synthetic fixtures and Asimov data say so; a result that uses an uncalibrated §8.7 value carries `provisional-thresholds`. Part B's numbers from its evidence reports are `synthetic` unless the report says otherwise, and Geant4 was not run for the PDE split.
- **Numbers from publications** are used only after verification with `hep-research:hep-citations`.
- **g4sim facts** cited by Part B were checked on hep-research 0.65.0 and 0.65.1; check them again (`git grep` on the version in use) before relying on a line number.
- **Evidence over assertion**: every claim in a gate record points to a file, test or log in the worktree.

### E11. Completion

The task is complete when phases 0–5 are all `merged`, or `partially-complete` with every gap agreed by a human and listed. Finish with a final report that lists each phase's state, every gap carried, every §8.7 threshold still provisional, and every item of `simcal-decision-index.md` still open.

### E12. The package

**Layout** (the package root is the folder holding this file):

```text
simcal-task/
  simcal-task.md                                   this document (Part A, reading guide, open questions)
  MANIFEST.sha256                                  SHA-256 of every file in the package
  README.md                                        short index and how to check the package
  simulator-calibration-v7.37.4-clean-en.md        Part B: the specification, lines unchanged from line 1
  simulator-calibration-v7.37.4-clean-en.appendix-E.md   Part B, Appendix E (change record), unchanged
  simcal-decision-index.md, .json                  status of every Appendix D entry and tagged §19 item, from Part B's markers
  simcal-approvals.md                              the author's decisions given so far, the packet of those still needed, and the confirmations
  decision-sheet.md                                the author's decision sheet (readings, options, recommendations), updated for the decision of 2026-11-10 by the package's preparation (7 changes, recorded in its header)
  decision-sheet.before-2026-11-10.md              the sheet as the author supplied it, unchanged
  drafts/simcal-tasks/phase-0.md … phase-5.md      draft task cards (Section E9, step 4)
  drafts/simcal-gates/phase-0.md … phase-5.md      gate-record templates
  drafts/simcal-status.json, simcal-task-registry.json   initial state files
  en/                                              the evidence reports of Part B that are available (en/MISSING.md lists the others)
  tools/restore_spec.py                            restores the single-file Part B and checks its SHA-256
  tools/build_decision_index.py, build_approvals.py, draft_cards.py   regenerate the index, the approval packet and the drafts from Part B
```

**Part B in two files.** Part B's lines above its Appendix E are unchanged from line 1; the Appendix E heading is followed there by one paragraph that points to the second file, and that file holds Appendix E unchanged. `tools/restore_spec.py` rebuilds the single file and checks it against the SHA-256 in the header. Part B cites its evidence as `en/<report>.md`: keep `en/` next to it.

**Not in this package** (Section E7, item 2): the reference implementation `calib_use_decision_table.py` attached to v7.37.4 (SHA-256 `c5279adf…`); the sealed original `simulator-calibration-v7.37.4.md` and its regression review; `triage.md` and `acceptance-applied.md`; and 20 of the 25 evidence reports Part B cites, with four more working records (`en/MISSING.md`). Part B carries their conclusions in its text; the reports themselves could not be located.

**The Chinese reference translation** of Part B has no normative force (front matter) and is not updated with Appendix E; it is not in this package.

---

## Reading guide to Part B

| To find | Where in Part B |
| --- | --- |
| What each kind of marked text means for implementation | front matter, line 38 |
| One-page summary; scope | §0; §1 |
| The joint likelihood, parameter and observable roles | §2 |
| Response model, references, cost rule | §3 |
| Contract, data release, plan, model identity, V_model, φ modes | §5 |
| Computation plan, random numbers, event budget, efficiency maps, the PDE split | §6 (§6.6, §6.7) |
| Inference engine, evaluator interface, reference-point iteration, intervals | §7 |
| Gates P0–P8, G1–G9, the G8 closure test, thresholds to calibrate | §8 (§8.7) |
| Validation, holdout, cross-validation, power, results | §9 |
| Results, evidence grades, dependency graph, propagation | §10 (rules governed by Appendix C) |
| Specialization interface and the g4sim binding | §11 (§11.4) |
| Homes in hep-research; scripts and their checks; Linux and Slurm | §13; §14; §14.1 |
| Tests and acceptance | §15 |
| Phases, gates per phase, g4sim preconditions | §17 |
| Design decisions; open questions | §18; §19 |
| Symbols; evidence-grade decision table; known inconsistencies | Appendix A; Appendix C; Appendix D |
| Change record (every edit, with base line numbers) | Appendix E (second file) |

---

## Open questions

1. **Requires confirmation (maintainer).** The home of this workflow's records in the repository. Proposed: `docs/dev/simulator-calibration/`, beside `docs/dev/geant4-architecture/` (**Inferred** from the g4sim precedent; no such folder exists in `main` at 5c2d1c7).
2. **Requires confirmation (author).** Which file is the reference implementation `calib_use_decision_table.py` at SHA-256 `c5279adf…`. Two other versions were found (`ed0fa0df…`, `f8dfef10…`); neither matches, and neither is used.
3. **Requires confirmation (author).** Whether the missing evidence reports (`en/MISSING.md`) can be supplied. Without them, Part B's text is the only record of their results.
4. **Open question.** The 48 items of the approval packet and the 13 confirmations (`simcal-approvals.md`); the phase each blocks is in `simcal-decision-index.md`, and the readings and options are in the author's `decision-sheet.md`.
5. **Requires confirmation (author).** The date of the PDE-split decision is recorded as 2026-11-10; the other decisions of the same session are recorded as 2026-11-09.
6. **Requires confirmation (maintainer).** The folder of the `calib_*.py` scripts. Part B names each script and the check it owns (§14) and puts the engine in hep-statistics under `core/calibration/` (§13), but does not say where the scripts live. Decide it in phase 0, before the first script is created.
7. **Open question (author).** §15.4's review obligation template is listed by §13 as a new hep-review deliverable, but no §17 row delivers it. Proposed: deliver it in phase 2, with the first gates that it covers (Inferred).

## References

- Part B and its Appendix E (this package).
- `skills/hep-computing/references/task-authoring-guide.md`, `skills/hep-computing/assets/task-template.md` and `skills/hep-computing/scripts/lint_task.py` of hep-research 0.65.1 (the task format).
- `docs/dev/geant4-architecture/g4sim-task.md`, `g4sim-approvals.md`, `g4sim-status.json`, `g4sim-task-registry.json`, `g4sim-tasks/`, `g4sim-gates/` of hep-research 0.65.1 (the precedent this protocol follows).

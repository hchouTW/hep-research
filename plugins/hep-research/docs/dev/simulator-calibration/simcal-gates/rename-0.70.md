# Simulator calibration gate record: the simcal rename (0.70.0)

**The rename passes, with one accepted exception (A36):** every simcal name in the maintained files follows the name
map; the old names still work through aliases and shims; every earlier simcal gate gives the same numbers as at
0.69.0. Phase-2 gate 1 fails by its registered rule only through its `units` item, which holds the expected failure
of the task card's step 6.3; its other 17 items and all their values equal the base.
- State: **done** (draft pull request for the maintainer; not merged, tagged or released).
- Review: one fresh-context reviewer; achieved tier **R0** (static review; the recorded-review store refuses the NFS
  scratch folder), no blocking finding; F1, F2, F3, F4, F5 handled (A36, A37), F6–F9 disclosed below.

| Field | Value |
| --- | --- |
| Task | task card `simcal-rename-task.md` (two stages; Stage B started on the author's "do your recommendation", 2026-11-16) |
| Worktrees | rename `~/hep-research-simcal-rename` (branch `simcal/rename`); base `~/hep-research-simcal-rename-base` (detached at `$BASE`, never edited) |
| `$BASE` | `5b47c577d0c58c454c8ed497536f10f284aa691b` (hep-research 0.69.0); `origin/main` unchanged through both stages |
| `$RENAME` | `497317c0b8fbee7dbded2e93f8fd7e12664b1b6a` (after repair iterations 1 and 2); this record is the next commit |
| Environment | login host Python 3.13.2 (conda env `ml`), NumPy 2.2.2, SciPy 1.16.1 (= the phase-5 golden's capture) for phase-5 items 1, 2, 4, phase 4, the merges, `checks` and `static`; Slurm 24.05.1 `edr1-al9_short_serial`, account `ams`, node Python 3.13.18 / NumPy 2.4.6 / SciPy 1.17.1; `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1` in every run (review F9) |
| Versions | `CORE_VERSION` 1.16.0 (from 1.15.0), `adapters/geant4` 0.18.0 (from 0.17.1), contracts 3.28.0 unchanged; plugin 0.70.0 proposed at merge |
| Slurm, base at `$BASE` | units 7664763 (16), p0 7664764 (69; item 34 rerun 7664827 after a 5 s stray file in `$BWT`, my error), misc 7664765 (task 4 rerun 7664923 at 40000M, as phase 5 did), p2g1 7664766 (33), p3 7664767-7664769 (134); 28.9 task-hours |
| Slurm, rename at `2097c253` (superseded) | 7666624-7666631, shard-16 rerun 7667291, diagnostic 7667408; 26.8 task-hours; evidence kept in `campaigns/rename-0.70/rename-2097c253…` |
| Slurm, rename at `$RENAME` | units 7667658 (16, `-t 01:30:00`), p0 7667659, misc 7667660 + 7667661 (task 4, 40000M), p2g1 7667662, p3 7667663-7667665 |
| Evidence folders | `$CAMP` = `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/campaigns/rename-0.70/` (`base/`, `rename/`); `$WORK` = `<rename worktree>/.simcal-work/rename/` (git-ignored: inventory, dry run, guard records, `compare.json`, identity and item-2 records, review) |
| Approvals | A34 (the rename), A35 (guide test), A36 (p2_gate1), A37 (stub import) in `simcal-approvals.md` |
| Date | 2026-11-16 |

## Acceptance criteria

| # | Criterion | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| 1 | Inventory 206 / 27 / 7 / 172, 156 moves; dry run saved and reviewed | 206, 27 (CHANGELOG, VALIDATION, 3 manifests, 22 frozen), 7 false matches, 172 maintained, 9 path-only, 156 moves; 1,714 replacements in exactly the 172 files | pass | `$WORK/inventory-base.txt`, `$WORK/naming/replacements.json` |
| 2 | No old names left except the allowed files | only the allowed files, the frozen name `calib_use_decision_table.py` (in `core/OWNERS.json`, `core/simcal/use.py`, `tests/core/simcal_exhaustive.py`, `tests/core/test_simcal_use.py`) and `tests/skills/hep_statistics/test_core_stats_guide.py` (its stub filter, A35; review F3); the stubs' text names only the new scripts | pass (with the A35 file) | `$WORK/naming/leftover-final.txt` |
| 3 | Strings of step 2.3 keep their count in every file | guard ok at every step; only the 7 path pieces `"core" / "simcal"` and the 6 schema-test names changed; the OWNERS key back as the alias entry | pass | `$WORK/naming/guard-final.json` |
| 4 | Frozen package: only added files and appended lines; `REFERENCE_SHA256` `c5279adf…` | `simcal-approvals.md` appended (A34-A37, 0 lines removed); this record added; reference hash present | pass | `git diff --name-status $BASE -- docs/dev/simulator-calibration/` |
| 5 | Old files work | `tests/core/test_simcal_compat.py` passes (10 tests): 0.69.0 contract, plan, fixture, result, ask/tell state read with only the notice, hashes as written, citations resolve; 19 stubs forward arguments, output and exit codes; `core.calibration.<m>` is `core.simcal.<m>`; `import g4sim_calib_eval` registers the g4sim kind (A37) | pass | unit shards, `tests/core/data/legacy-0.69/` |
| 6 | Appendix C 69 of 69 over 31,593,216 cases; every earlier gate passes by its rule; phase-5 item 1 passes, items 2 and 4 as judged in 6.3 | Appendix C 69 of 69 `ok` (agree 31,593,216; lookup 2,754,048); earlier gates: p0 Appendix C, named, fixtures, p1 gates 1 and 2, p2 gates 2 and 3, p3 gate E, p4 pass; **p2 gate 1 fails** only through its `units` item (the expected `test_static_item_at_this_commit`, alone on a node, job 7667408); item 1 passes; item 2 exactly the 5 renamed harness files, registry 70 = 70, each file = its 0.69.0 original through the name map; item 4: only `contract_check_accepted` and `_rejected` differ, by script names; the 5 `p5base_*` cases byte-identical with each tree's own case file | pass except p2_gate1 (accepted, A36) | `$CAMP/rename/p0-summary.json`, `rename/prior/rerun-merged.json`, `rename/p5-run.json`, `$WORK/item2-rename.json`, `$WORK/identity-rename.json` |
| 7 | Same numbers | `compare.json`: equal apart from the expected differences; no gate result value differs; the only hash difference is the golden file's own hash (its `script` fields); same failing unit tests after the expected ones | pass | `$WORK/compare.json` (`judgement`) |
| 8 | Checks | units on 16 shards, `checks`, `static`: failures only the expected two and the base's `test_revocation` ×2 and event-display export; reconcile 18 of 18 runs at `$RENAME`, no missing, duplicate, partition or commit problem; `check_naming`, `check_ownership`, `check_routing_static`, `check_wiring`, `check_layering`, `check_packaging`, `skill_scripts --check`, ruff, mypy pass | pass | `$CAMP/rename/reconcile.out`, `$WORK/logs/` |
| 9 | Description and budget | hep-statistics description 1020 characters; routing static 489 cases pass; `measure_entrypoints` no warning; quick load 25,588 B (hep-detector 25,516 B); `test_routing_tables` passes | pass | `$WORK/logs/measure-4.json` |
| 10 | Stage A report; Stage B only after the go-ahead; base did not move | report given 2026-11-16; Stage B on "do your recommendation" with the report's three changes; `origin/main` = `$BASE` before step 2 and at hand-over | pass | `$WORK/stage-a-report.md`, `$WORK/state.json` |
| 11 | Loop limits | repair iterations 2 of 5, each reducing the failures (27 → 0; 1 review finding → 0); no step-6.5 retry; one step-7 shard rerun (shard 16 at `2097c253`, a lease-lock timing error in `test_control_layer_c2`, unchanged by the rename, 3 of 3 pass on login at both commits); stops at step 6.1 (BLOCKED, answered A35) and at the review (A36, A37) | pass | `$WORK/state.json` |

## Deviations from the card

- Misc task 4 (phase-2 gate 2) at 40000M; units at `-t 01:30:00` (Stage A report changes 1 and 2).
- Step 4.2's compact simcal line breaks `test_core_stats_guide`'s marker rule; the test was adjusted (A35).
- The ML-output neighbor routing cases name hep-detector as the skill they must not go to (the hep-statistics
  description has no room to route to hep-ml).
- The evaluator stub also works when imported (A37), beyond step 3.3.
- One records commit was made while the guard reported STOP (my command did not chain the commit on the guard; CHANGELOG
  prose quoted two protected literals); it was amended before anything was pushed or run, and every later commit went
  through `gate_commit.sh`.

## Review findings not changed here (for the maintainer and the migration task)

- F6: the notice `simcal.legacy_schema_id` fires only for fixtures, the T2 record and the ask/tell state; old contracts,
  plans, results, data releases and ledgers are accepted silently through the schema enums.
- F7: appending to a state file started by 0.69.0 keeps its old id (`data_release.py`, `validate.py`, the emulator
  state), while `g4sim_simcal_eval.py` writes the new id.
- F9: on the login host without single-threaded BLAS, `contrib_variance` can differ from its golden in the last bits of
  three floats (the same at base and rename); every run here set the thread variables to 1.
- The migration tool for old ids (Out of Scope) is due before 0.72.0.

## Report

State **done**. Branch `simcal/rename` (10 commits over `$BASE`: moves, names, specializations, compatibility layer,
text and routing, specialization text, records and versions, repair 1, repair 2, this record), pushed with a draft pull
request. Next action for the maintainer: review the draft PR (and the A36 exception), merge it, then release 0.70.0.

## After the hand-over (A38)

The two expected failures of step 6.3, `test_static_item_at_this_commit` and `test_base_tree_cases`, would have failed
on main after the merge wherever they run. They now judge the rename instead (approval A38): the 5 changed protected
files and the identity-case file are their phase-5 originals with names substituted only (an exact reverse of the name
map), and the registry is unchanged. The gate harness and its rules are unchanged. On the login host (capture
environment, full history) both run and pass; with a planted extra line in a protected file the static test fails.
The verdicts above stay as recorded at `$RENAME`; phase-2 gate 1's `units` item would no longer hold a failing test.

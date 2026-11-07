# Detector reconstruction plan v9.2: baseline

Recorded 2026-11-06 for task T01. Host-specific locations are written as `<private>` and `<workdir>` (R07).

## Baseline against the plan's inventory

| Item | Plan Section 4.1 (historical) | This baseline |
| --- | --- | --- |
| Commit | `d74aaba2b0aa6be0e6528e8911b84b4d14b1254e` | `580dc79e83abbc33b27c69633d9e15658f4f90b6` |
| Plugin | 0.54.0 | 0.56.0 |
| Contracts | 3.18.0 | 3.19.0 |
| Platform | macOS paths | Linux, NSTCCore (R26) |

The baseline differs from the `hep-research--v0.56.0` tag only by a custodian record in `g4sim-approvals.md`. The installed plugin copy on this host is 0.54.0 and does not govern (R01).

Moved 2026-11-06 onto 0.57.0 (decisions.md, D1); see "Re-baseline onto 0.57.0" at the end. The table above and the results below it are the 0.56.0 record.

## Environment

| Item | Value | Evidence |
| --- | --- | --- |
| Login-node Python for checks | `<workdir>/env/py313/bin/python` 3.13.18 | `--version`, import check |
| Job interpreter | Same file; SHA-256 `32545eb5023762341770737253e9fd8a64e41f993e255561246f50d5c0ff4a53` | Tiny job 7470150 |
| Packages | `requirements-ci.lock`: numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0 | `pip check`, tiny job |
| Status | R29 option (b), a recorded deviation: the interpreter sits in an agent-writable path | decisions.md, Q4 |

## What a job receives

Tiny job 7470150, `hpa-wn28`, partition `edr2-al9_short_serial`, 51 s, exit 0:0.

- QoS `normal`, 1 CPU, 2000 MB, as requested.
- A keyword search of the variable names found no credential-like names in the job or login environment.
- Reachable from any job, by name: `~/.ssh` and `~/.config/gh/hosts.yml`. Absent: `~/.globus`, `~/.netrc`, an X.509 proxy.
- `root.exe -b -q` exits 0 with `libxxhash` from the system library path. This covers one node only.

## Check baseline

| Part | Where | Result | Evidence |
| --- | --- | --- | --- |
| `run_all_checks.py --part static --jobs 2` | Login node (Q8) | 31 pass, 0 fail, 0 skip, 327 s | `<private>/evidence/20261106T044938Z` |
| `tests/skills/hep_detector` discovery | Job 7470206 | 591 run, OK, 4 skipped, 296 s | `<private>/evidence/baseline-units-7470206` |
| `tests/routing` discovery | Job 7470206 | 21 run, OK, 1 s | Same |
| `run_all_checks.py --part units --jobs 6` | Job 7470206 | **Exit 1:** 6,797 run, 6,411 passed, 1 failure, 1 error, 384 skipped, 696 s | Same |

The static run had `docs/dev/detector-reconstruction/` present and untracked. The unit job uses a separate tree, so these records cannot affect it.

Job 7470206 ran on `hpa-wn28` at the baseline commit, clean before and after, in 16 min 41 s. Slurm reports `COMPLETED 0:0` because the script does not pass on the suite's exit code; the receipt holds the real result. Skipped tests are kept in the evidence and do not count as passed.

### Failing IDs at the baseline

Later runs compare against these two (R05). Both are preserved as failures, and neither is attributed to this task.

| Test ID | Result | Observed | Suspected cause |
| --- | --- | --- | --- |
| `tests.adapters.test_geant4_register.CheckAndDownstream.test_examples_need_an_explicit_source_of_the_installed_version` | Failure, exit 3 where 2 is expected | `cmake not found on PATH`; the job loaded no `cmake` module, though `cmake/3.28` exists | Job environment. **Confirmed:** passes in job 7470679 with `cmake/3.28` loaded |
| `tests.skills.hep_computing.test_environment_manifest.EnvironmentTemplateTests.test_lcg_setup_is_valid_sh_and_refuses_missing_view` | Error, `TimeoutExpired` after 60 s | The script's only file access is a read check of a path under `/cvmfs/sft.cern.ch`. The same test passes alone on the login node in under 1 s | A slow or stalled CVMFS access on the compute node. Still fails in job 7470679. Jobs 7471877-7471879 show the same paths fail on all three CPU node sets: `Input/output error` after about 3 minutes on edr1 and intel-g4, no result after 240 s on edr2, while the top of `lcg/` lists in 2-3 s. This points to a site CVMFS problem, not a plugin defect; the root cause is not known |

### P0 checkpoint

Job 7470679, `hpa-wn28`, commit `1d31ebd3`, clean before and after, 17 min 22 s, Slurm `FAILED 1:0`, which is the suite's real status.

| Part | Result |
| --- | --- |
| `tests/skills/hep_detector` | 591 run, OK, 4 skipped |
| `tests/routing` | 21 run, OK |
| `--part units` | 6,797 run, 6,415 passed, 0 failures, 1 error, 381 skipped |

Against the baseline: no new failure. One baseline failure passes once `cmake` is loaded. The LCG test still errors. Three fewer tests are skipped, which fits `cmake` being available; the skip lists were not compared one by one.

Later jobs load `cmake/3.28`, so the comparison set is now the single LCG test.

## Backends and data

K02 and K03 are decided (decisions.md). `acts-core` 48.2.0 is confirmed at smoke level in `<workdir>/env/acts48`; any other backend stays unavailable until an approved job confirms it (R02). Site modules on this host include no Geant4 or ACTS. CVMFS is not a dependable route: t03-selection.md records the listing stalls on the login node and in job 7470680.

## Re-baseline onto 0.57.0

Task B1 and B2 step 1, 2026-11-06.

| Item | 0.56.0 | 0.57.0 |
| --- | --- | --- |
| Commit | `580dc79e` | `d51566a9`, the tag `hep-research--v0.57.0` and the tip of `main` when fetched |
| Plugin | 0.56.0 | 0.57.0 |
| Contracts | 3.19.0 | 3.20.0 |
| `CORE_VERSION` | 1.6.0 | 1.7.0 |

The rebase replayed 17 commits with no conflict, and `docs/dev/detector-reconstruction/` was byte-identical before and after. Every branch commit has a new hash. Hashes named in earlier records are the old ones, reachable through the local ref `pre-rebase-0.56.0` (old tip `a2281ca3`) and the backup bundles. The release contains PR #353.

The installed plugin copy does not govern (R01).

### What the comparison covered

| Check | Result |
| --- | --- |
| Contract-map names (53) | 2 changed files, 15 unchanged, 36 not file names; see contract-map.md |
| `geometry_id` of the release's `g4sim_geometry_check.spec.json`, on both trees | Same value, `7bba29fb69e9...`, status `ok` |
| T11 anchors (81, plus the `name.md#anchor` example in the conventions text) | All resolve at 0.57.0, none newly broken |
| `hep-detector` references changed | 8 files, all from PR #353; none differs between that merge and the release |
| G01-G03 files, `core/canonical`, `contracts/geometry.py`, `geometry_ir.json`, `detector_spec.json`, the two calibration references | Unchanged |
| Fixtures under `contracts/fixtures` (143 files) | Version lines only |

The anchor check shows that headings survive. The cells whose reference text PR #353 changed were then compared with their verdicts; no status changes (t11-cells.md, "Effect of PR #353 at 0.57.0").

### Unit checkpoint at 0.57.0

Task B2 step 2, job 7472812, commit `e57716dc`, 2026-11-06. Slurm state `FAILED`, exit `1:0`, 22 min 29 s, node `hpa-wn28`. Tree clean before and after, no file outside the records differs from the release. Evidence: `<private>/evidence/checkpoint-b2-7472812/`.

| Part | Checkpoint at 0.56.0 | This job |
| --- | --- | --- |
| `tests/skills/hep_detector` | 591 run, OK, 4 skipped | 594 run, OK, 4 skipped |
| `tests/routing` | 21 run, OK | 21 run, OK |
| `--part units` | 6,797 run, 6,415 passed, 0 failures, 1 error, 381 skipped | 6,829 run, 6,448 passed, 0 failures, 1 error, 380 skipped |
| Modules that did not finish | 0 | 1 |

The error is the known LCG test. The module that did not finish is `tests.adapters.test_unbinned_fit`, stopped by the runner's default 600 s limit per module, so its tests have no result in this job. Its test file and `unbinned_fit.py` did not change in the release. It took 468.65 s at the 0.56.0 checkpoint, and `tools/module_timings.json` gives 272.7 s. The whole units part took 974 s against 734 s. The node's load was 161 of 192 CPUs when read after the job ended, so its load during the run is unknown. The cause is not established; see the rerun's result below.

This job is not clean and stays failed (R11). T03 and T11 stay provisional.

### Rerun of the unfinished module

Job 7474460 runs that one module at the same commit, alone, with no per-module limit, and records its time. The method change is that the module runs alone and is measured rather than stopped. The 600 s value is a runner default (`--module-timeout`), not a requirement of the plan, but lifting it after a timeout could read as relaxing a check (§1.3 item 6), so the reading was fixed before the result (deviations.md, no. 8):

| Rerun result | Reading |
| --- | --- |
| Passes in 600 s or less, same tests as at 0.56.0 | The comparison is clean apart from the LCG error. T03 and T11 go to `done`. Job 7472812 stays recorded as failed. |
| Passes in more than 600 s | Not clean by itself. The module cannot meet the runner's limit on this node even alone; goes to the user. |
| Fails, errors, or reaches the job's time limit | A finding, recorded with its test IDs. T03 and T11 stay provisional; goes to the user. |

Result: job 7474460, `COMPLETED`, exit `0:0`, 31 s, node `hpa-wn28`, commit `e57716dc`, tree clean. Evidence: `<private>/evidence/unbinned-rerun-7474460/`.

| Item | Checkpoint at 0.56.0 | Job 7472812 | Job 7474460 |
| --- | --- | --- | --- |
| How it ran | Suite, 6 modules at a time | Suite, 6 modules at a time | Alone |
| Time | 468.65 s | Stopped at 600 s | 29 s (tests 28.7 s) |
| Tests | 9 run, 1 skipped, OK | No result | 9 run, 1 skipped, OK |

First row of the table above applies: the comparison is clean apart from the LCG error. With this module counted, the unit suite at 0.57.0 is 6,838 run, 6,456 passed, 0 failures, 1 error, 381 skipped; the skip count equals the one at 0.56.0. Those totals combine two jobs. Job 7472812 stays failed.

Cause of the timeout: not established. Node load does not explain it by itself: the load average was 163 to 166 during this 29 s run, close to the 161 read after job 7472812. The module was 16 times slower inside the suite at 0.56.0 and over 20 times slower at 0.57.0 than alone, so contention inside the job is the leading suspect; neither the job scripts nor the runner limit threads. That is not tested. A hang is unlikely but was not excluded for job 7472812 itself. Any later unit job can hit the same timeout, so one that does is read against this record, not assumed harmless.

## Gate C checkpoint: reading rule

Fixed before the job. Job `<private>/jobs/checkpoint-c/checkpoint.sh` (`3ec7b3f133fe34ec`), commit `baa9be3d`, T06, T14 and T15a. Same steps as job 7472812, with one change: one BLAS thread per process, to test the contention suspected there. The receipt records load before and after the units part.

| Result | Reading |
| --- | --- |
| Only the LCG error fails, every module finishes, and the new contract modules ran | Clean. T06, T14 and T15a go to `done` (R28), Gate C passes |
| Only that, but `tests.adapters.test_unbinned_fit` runs far below 469 s | As above, and contention gains support; still not proven, since this run changes one thing among others |
| `tests.adapters.test_unbinned_fit` times out again | Not clean. Goes to the user: thread limits did not remove it |
| Any other failure, error or unfinished module | Recorded with its IDs. Not attributed to this work without evidence. T06, T14 and T15a stay provisional, and it goes to the user |

Slurm `COMPLETED` is not a result; the job exits non-zero on the known LCG error, as before.

### Gate C checkpoint, first run

Job 7487365, commit `baa9be3d`, Slurm `FAILED`, exit `1:0`, 12 min 27 s, node `hpa-wn30`, tree clean before and after. Evidence: `<private>/evidence/checkpoint-c-7487365/`.

| Part | Result |
| --- | --- |
| `tests/skills/hep_detector` | 594 run, OK, 4 skipped |
| `tests/routing` | 21 run, OK |
| `--part units` | 7,604 run, 7,220 passed, 2 failures, 1 error, 381 skipped, 530 modules, all finished, 391 s |

Not clean. Fourth row of the rule. The error is the known LCG test. The two failures, both from this work, are generated records the static gate does not read:

- `tests.tools.test_skill_scripts.SkillScriptList.test_committed_list_is_up_to_date`: G03 moved lines in a reference file, and `tools/skill_scripts.json` stores them. Regenerated.
- `tests.tools.test_run_all_checks.TimingCoverageTests.test_at_most_a_tenth_of_the_modules_lack_a_timing`: 64 of 530 modules lacked a timing, limit 53; 14 were T06, T14 and T15a's. Their measured times from this job added to `tools/module_timings.json`.

All 14 new contract modules ran and passed. T06, T14 and T15a stay provisional. The job reruns at the commit carrying these two fixes, under the same rule; job 7487365 stays recorded as failed.

Timeout of job 7472812: `tests.adapters.test_unbinned_fit` took 29.02 s inside the suite here, against 468.65 s and over 600 s before, and the whole units part 391 s against 734 s and 974 s, with load average 168 to 183 and one BLAS thread per process. This changed the thread limit, and also the node, so it is strong support for thread oversubscription, not proof. Node load alone is excluded.

### Gate C checkpoint, rerun

Job 7487578, commit `596b6875`, Slurm `FAILED`, exit `1:0`, 9 min 48 s, node `hpa-wn30`, tree clean before and after. Evidence: `<private>/evidence/checkpoint-c2-7487578/`.

| Part | Result |
| --- | --- |
| `tests/skills/hep_detector` | 594 run, OK, 4 skipped |
| `tests/routing` | 21 run, OK |
| `--part units` | 7,604 run, 7,222 passed, 0 failures, 1 error, 381 skipped, 530 modules, all finished, 379 s |

First and second rows of the rule apply: clean. The error is the known LCG test. The 14 new contract modules ran and passed, 766 tests. T06, T14 and T15a go to `done`, and Gate C passes. `tests.adapters.test_unbinned_fit` took 29.35 s, the same as the run before, at load average 160 to 178, so the result repeats on `hpa-wn30`. Thread oversubscription stays the leading cause, strongly supported, not proven: no run has compared thread settings on one node.

## Re-baseline onto 0.58.0

User's answer, 2026-11-07, verbatim: "go ahead with the rebase". Tag `hep-research--v0.58.0`, commit `662f58d4`, contracts 3.21.0, `CORE_VERSION` 1.8.0, 66 commits and 259 files after 0.57.0, mostly g4sim S3.

The rebase replayed 43 commits. Conflicts were additive, in `CHANGELOG.md`, `contracts/__init__.py` and `tools/module_timings.json`: both sides kept, and the timings file rebuilt as the release's plus this work's 14 entries. Tracked records came through byte-identical, and the four Freeze A hashes hold. Only those three non-record files differ from the old tip. Every branch commit has a new hash; older hashes resolve through the local ref `pre-rebase-0.57.0`, and job evidence keeps the hashes it ran on.

| Check | Result |
| --- | --- |
| `geometry_id` of `g4sim_geometry_check.spec.json`, both trees | Same value, `7bba29fb69e9...`, status `ok`; `provenance_id` same |
| `core/geometry/identity.py`, `core/canonical` | Unchanged |
| `recipe.json`, `operator_semantics.json`, `qualification_record.json`, `decision_record.json`, `tool_contract.json`, `ext_response.json`, `exposure_record.json`, `ext_computational_run.json` | Unchanged |
| `hep-detector` references | Unchanged, so the T11 anchors stand; one asset JSON has version lines only |
| Fixtures under `contracts/fixtures` (143 files) | Version lines only |


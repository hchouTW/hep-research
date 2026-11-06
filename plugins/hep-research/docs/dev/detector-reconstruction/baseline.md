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

The error is the known LCG test. The module that did not finish is `tests.adapters.test_unbinned_fit`, stopped by the runner's default 600 s limit per module, so its tests have no result in this job. Its test file and `unbinned_fit.py` did not change in the release. It took 468.65 s at the 0.56.0 checkpoint, and `tools/module_timings.json` gives 272.7 s. The whole units part took 974 s against 734 s. The node's load was 161 of 192 CPUs when read after the job ended, so its load during the run is unknown. Slowness is the suspected cause; a hang is not excluded.

This job is not clean and stays failed (R11). T03 and T11 stay provisional.

### Rerun of the unfinished module

Job 7474460 runs that one module at the same commit, alone, with no per-module limit, and records its time. The method change is that the module runs alone and is measured rather than stopped. The 600 s value is a runner default (`--module-timeout`), not a requirement of the plan, but lifting it after a timeout could read as relaxing a check (§1.3 item 6), so the reading was fixed before the result (deviations.md, no. 8):

| Rerun result | Reading |
| --- | --- |
| Passes in 600 s or less, same tests as at 0.56.0 | The comparison is clean apart from the LCG error. T03 and T11 go to `done`. Job 7472812 stays recorded as failed. |
| Passes in more than 600 s | Not clean by itself. The module cannot meet the runner's limit on this node even alone; goes to the user. |
| Fails, errors, or reaches the job's time limit | A finding, recorded with its test IDs. T03 and T11 stay provisional; goes to the user. |

Result: pending.

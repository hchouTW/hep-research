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

Planned move: re-baseline onto 0.57.0 before T06 (decisions.md, D1). The g4sim task's branch is at 0.57.0 and contracts 3.20.0, unreleased.

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
| `tests.skills.hep_computing.test_environment_manifest.EnvironmentTemplateTests.test_lcg_setup_is_valid_sh_and_refuses_missing_view` | Error, `TimeoutExpired` after 60 s | The script's only file access is a read check of a path under `/cvmfs/sft.cern.ch`. The same test passes alone on the login node in under 1 s | A slow or stalled CVMFS access on the compute node. Still fails in job 7470679. Supported by job 7470680, where listings under the same tree stalled past 240 s; the exact cause is not known |

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

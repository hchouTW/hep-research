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
| Section 17.2 unit runs and `--part units` | Job 7470206, detached tree at the baseline | Pending | `<private>/evidence/baseline-units-7470206` |

The static run had `docs/dev/detector-reconstruction/` present and untracked. The unit job uses a separate tree, so these records cannot affect it.

Failing test IDs are recorded here when the unit job ends; later runs compare against them (R05).

## Backends and data

K02 and K03 are unresolved. No reconstruction backend has been probed. Site modules on this host include no Geant4 or ACTS. Unprobed means unavailable (R02).

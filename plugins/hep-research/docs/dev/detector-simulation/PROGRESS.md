# detsim integration progress ledger

Spec version: 9.1

## Isolation record

| Item | Value |
|---|---|
| Main checkout | `/Users/hchou/hep-research` (branch `main`, HEAD `cf622dab`, clean) |
| Task worktree WT | `/Users/hchou/hep-research-detsim` |
| Work root WR | `/Users/hchou/hep-research-detsim-work` |
| Branch | detsim-integration |
| Base ref and commit | `origin/HEAD` (after `git fetch origin`) `25a8dbe6bfe426b9cac52733e5487625d213f056` (hep-research 0.53.0 release merge) |
| Parent folder PARENT | `/Users/hchou` |
| Installed plugin (never written) | `/Users/hchou/.claude/plugins/cache/hep-research-dev/hep-research/0.52.0` (the folder this session loaded skills from) |
| Git version; `core.hooksPath`; hooks present | git 2.54.0 (Apple Git-157); `/Users/hchou/hep-research/.githooks` (`check-paths.sh`, `pre-commit`, `pre-push`); no hooks in the common `hooks/` folder besides samples |
| Plugin root PR | `<WT>/plugins/hep-research` |
| `git status --porcelain` of MAIN at W0 | empty (0 lines) |
| Isolation guard at W0 | pass, 2026-11-01T11:59Z; fails from MAIN ("not running inside .../hep-research-detsim"); byte-identical to §2.4 (`diff` empty) |
| Interpreter and venv | `/Users/hchou/miniconda3/bin/python3` 3.13.2 (`find_python.py`); `WR/venv` with `--system-site-packages`; `requirements-core.txt` and `requirements-test.txt` installed (numpy 2.4.4, scipy 1.17.1, sympy 1.14.0); `import ROOT` works (Homebrew ROOT 6.40.04) |
| Baseline test run | `python3 tools/run_all_checks.py --no-cli --out "$WR/scratch/baseline"` from PR: 31 pass, 0 fail, 2 skip (host CLIs); units 6342 run, 6132 passed, 210 skipped, 0 failures, 0 errors; no pre-existing failure |

## Subagent worktrees

| Key | Item | Path | Branch | Base commit | Patch folder | State |
|---|---|---|---|---|---|---|

## Environment reconnaissance

Host: Darwin arm64 (macOS 27.2), 8 CPUs, Python 3.13.2, git 2.54.0, CMake 4.3.2, Apple clang 21.0.0; 406 GiB free on `/Users/hchou`. Variables present (names only): `ROOTSYS`.

| Backend | Found here | Obtainable with H0 permission | Notes |
|---|---|---|---|
| Allpix Squared | no (`allpix` not on PATH) | yes, source build (H0 #5) into WR: needs spdlog >= 1.9.2 and Boost >= 1.64 (random), both absent, built into `WR/env/deps`; Geant4 11.4.3 source install with datasets at `~/Workspace/geant4-work/build-b/install`; ROOT 6.40.04 (Homebrew); Eigen 3 (Homebrew) | no CVMFS (`/cvmfs` absent), no container runtime (docker, podman, apptainer, singularity absent) |
| Garfield++ | no | yes, source build (H0 #5) against Homebrew ROOT 6.40.04 and GSL | ROOT Python bindings present (`import ROOT`) |

## Authorization (H0)

| # | Question | Answer | Source | Time |
|---|---|---|---|---|
| 1 | Clone / fetch the hep-research repository | yes (fetch done; editable checkout exists, no clone) | default | 2026-11-01 |
| 2 | Shallow-clone upstreams for reading | yes, read-only (blob-less clones in `WR/upstream`) | default | 2026-11-01 |
| 3 | Container images | no | default | 2026-11-01 |
| 4 | Mounted CVMFS | yes, read-only (none mounted) | default | 2026-11-01 |
| 5 | Build backends from source, download sources and Geant4 data | **yes, both backends, default budget (2 h and 20 GB per environment)** | user | 2026-11-01 |
| 6 | pip into `WR/venv` | yes, only there | default | 2026-11-01 |
| 7 | G0 platforms | current host (macOS); Linux declared soft or unsupported until measured | default | 2026-11-01 |
| 8 | Guide language | English | default | 2026-11-01 |
| 9 | Budget | environment 2 h and 20 GB; one test run 10 min | default (confirmed by user) | 2026-11-01 |
| 10 | Loop bounds | as in §3.4 | default | 2026-11-01 |
| 11 | Push / PR when finished | **push, open a PR, merge and release when the task ends done and CI is green** | user | 2026-11-01 |
| 12 | Owners of §15.3 | the user, every role | default | 2026-11-01 |
| 13 | Example gas table `ar_80_co2_20_0T.gas` | yes, under the two conditions (local input only; pipeline validation only) | default (user decision 2026-10-30) | 2026-11-01 |

## Work status

| Work item | Status | Last updated | Cycles / review rounds used | Evidence (test IDs, commits, files) | Missing |
|---|---|---|---|---|---|
| W0 | done | 2026-11-01 | 0 / 0 | T-WT (this ledger, isolation record) | |
| W1 | not-started | | 0 / 0 | | |
| WK | not-started | | 0 / 0 | | |
| W2-AP | not-started | | 0 / 0 | | |
| W2-GF | not-started | | 0 / 0 | | |
| W3a | not-started | | 0 / 0 | | |
| W3b | not-started | | 0 / 0 | | |
| W4A | not-started | | 0 / 0 | | |
| W4G | not-started | | 0 / 0 | | |
| W5 | not-started | | 0 / 0 | | |

## To-verify results

| V-ID | Conclusion | Evidence (repo, commit, file:line or URL + date) | Affected sections |
|---|---|---|---|

## Decision log

| Time | Work item | Decision (incl. D-W1-n) | Reason | How to revert |
|---|---|---|---|---|
| 2026-11-01 | W0 | Base is `origin/HEAD` = `25a8dbe6` (0.53.0), not the spec's `bf5e453` (0.51.0 + unreleased) | §2.3 step 3 takes the current `origin/HEAD`; W1 re-checks every repository fact on this base | rebase onto another base |
| 2026-11-01 | W0 | Upstream clones are blob-less (`--filter=blob:none`) rather than `--depth 1` | keeps tags, so `git describe` (used by the Allpix version string) works; still read-only | reclone shallow |
| 2026-11-01 | W0 | Environment builds (H0 #5) started after the baseline finished, before W2 formally starts | builds take hours; starting them early only writes into `WR/env`; W2 records and pins what they produce | delete `WR/env/{allpix,garfield,deps}` |

## Gate queue

| Gate | Question | Blocked work | Suggested options | Status |
|---|---|---|---|---|

## Delivery reports

```text
Work item ID: W0
Status: done
Isolation guard: pass at end of W0 (from WT); fails from MAIN, as required
Files changed: docs/dev/detector-simulation/TASK.md (copy of the spec), docs/dev/detector-simulation/PROGRESS.md
Decisions made (with reasons): see decision log (base 25a8dbe6; blob-less clones; early builds)
Commands actually run and results: git inspection of MAIN (clean, branch main, hooksPath .githooks); git fetch origin;
  git worktree add -b detsim-integration WT 25a8dbe6; WR created with isolation.env and isolation-guard.sh (identical
  to §2.4); venv with --system-site-packages + requirements-core/test; guard pass; baseline run_all_checks --no-cli:
  31 pass / 0 fail / 2 skip, units 6342 (6132 passed, 210 skipped, 0 failures)
Tests not run and reasons: none
V-items concluded / still open: none for W0
Independent review: not applicable
Blockers and gates raised: none
Next step: W1
```

## Final report

(E.3, written in Phase 3)

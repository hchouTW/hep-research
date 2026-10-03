# FINAL REPORT: FULLTEST-E2, isolated full test on E2 (TASK r1)

Date 2026-10-04. Commit `dd9b9405facbdce37acb183947dc7493c4bdf5bc` (`main`), results on local branch
`test/fulltest-e2`. Environment **E2**: macOS 26.5 arm64 (Apple M3), Python 3.13.2 (`~/.venvs/hep-research-e2`),
Claude Code 2.1.288. Decisions: Q1 proposed tools installed (pyhf, uproot, awkward, PyTorch and torchvision in the
venv; Mermaid CLI and PlantUML via Homebrew). Q2 live routing not run (user: skip routing). Q3 not needed. Q4 not
stated: results committed locally only. F07: user chose to record the isolated invocation as unverified.

## Summary

| Step | Result | Evidence (`results/`) |
|---|---|---|
| F00 environment | done | `F00-environment.md` |
| F01 legacy checkout | done, `3e995a4` | `F00-environment.md` |
| F02 aggregate | **fail** (unittest: 1 fail, 1 error); 13 other checks pass, none skip | `check-run-2026-10-03T193110Z.json` |
| F03 traceability with legacy | pass (949/949) | `F03-traceability.txt` |
| F04 examples | reruns pass (10/10); 1 cross-platform difference | `F04-examples.md`, `.json` |
| F05 adapters | pass except DDP; Combine unverified | `F05-adapters.md` |
| F06 relocation | pass apart from DDP (second run) | `F06-relocation.md`, `relocation-*.json` |
| F07 isolated host | install, discovery, removal pass; invocation **unverified** | `F07-*` |
| F08 live routing | **not run** (Q2) | — |
| F09 records | done | VALIDATION FULLTEST-E2, capability-matrix "E2 results", CHANGELOG |

## Acceptance criteria

| AC | Result |
|---|---|
| AC1 one SHA; only deliverables in `git status` | pass (`dd9b940` everywhere) |
| AC2 14 checks, ledger pass | pass: 14 checks recorded, `ams_ledger_preservation` pass; unittest is a fail with stated causes |
| AC3 counts separated, skips grouped | pass: 9 skips = 3 missing tool, 4 slow by design, 2 meaningful only without PyTorch |
| AC4 ten examples, reruns byte-identical | pass |
| AC5 every adapter tool has an E2 status | pass (`F05-adapters.md`) |
| AC6 relocation passes or differences explained | pass: differences explained (stray venv in run 1; legacy skips; DDP) |
| AC7 isolated host trace, `~/.claude` unchanged | pass for discovery, path and removal; `~/.claude` identical before and after; invocation unverified (no login in the isolated config) |
| AC8 routing | "live routing not run (Q2)"; AC20 unchanged |
| AC9 no E1 edit | pass: E2 added as a separate paragraph and section |
| AC10 only VALIDATION, capability matrix, CHANGELOG changed under the plugin | pass |
| AC11 every fail, skip and unverified listed | below |

Validation (§8): the final rerun to scratch differs from F02 in one count. The Mermaid failure is gone after its
browser was installed (1241 run, 1231 pass, 0 fail, 1 error, 9 skip). The order expected identical counts. The
difference is the completed tool install, not instability.

## Every fail, skip and unverified item

| Item | Kind | Cause |
|---|---|---|
| `test_shipped_diagram_sources_pass` (F02) | fail, then pass | Homebrew `mermaid-cli` 12.0.0 does not install puppeteer's `chrome-headless-shell`; installed 154.0.8037.57 into `~/.cache/puppeteer`, then 22/22 pass |
| `test_ddp_skeleton_two_gloo_processes` | error (timeout 300 s) | torchrun c10d rendezvous cannot resolve the host name `Mac.hitronhub.home` (`getaddrinfo` Errno 8). It passed twice standalone earlier in the session and then hung in four later runs, including with `--master_addr=127.0.0.1` and `GLOO_SOCKET_IFNAME=lo0` |
| `ams-flux-ratio` committed output | difference | 106 toy-closure values differ from the E1 output; observed counts identical, pass criteria hold. `[Inferred]` RNG stream divergence after a last-digit difference in a Poisson or binomial rate |
| Figures in 5 examples | difference | PNG bytes differ across platforms; no test compares them |
| F06 run 1 packaging scan | fail (explained) | leftover `plugins/hep-research/.venv-hep` from the INSTALL order copied into the relocation; moved to the session scratch directory, not deleted |
| Real Slurm, real HTCondor, CMS Combine | skip / unverified | tools absent |
| 4 slow statistics tests | skip | `HEP_SLOW_TESTS=1` not set (by design) |
| 2 no-PyTorch degradation tests | skip | meaningful only without PyTorch |
| Legacy checks in the relocated copy (2 checks, `test_lint_task`) | skip | the copy has no legacy checkout next to it |
| F07 namespaced invocation | unverified | isolated config not logged in (user decision) |
| F08 live routing | not run | not approved |

## Comparison with earlier runs

| Run | Commit | Checks (pass/fail/skip) | Unit run / pass / fail+error / skip |
|---|---|---|---|
| E1 `check-run-2026-10-03T061357Z.json` | `6ad6228` | 13 / 0 / 1 | 1240 / 1162 / 0 / 78 |
| E2 core only `check-run-2026-10-03T141301Z.json` | `0ab9cd8` | 13 / 0 / 1 | 1241 / 1171 / 0 / 70 |
| E2 full (this, F02) | `dd9b940` | 13 / 1 / 0 | 1241 / 1230 / 2 / 9 |
| E2 full, final rerun (scratch) | `dd9b940` | 13 / 1 / 0 | 1241 / 1231 / 1 / 9 |

With the optional tools present, 61 tests that skipped before now run, and all but the DDP test pass.

## Follow-ups (one task each)

1. DDP smoke test: run `torchrun` with `--standalone` (or `--rdzv-endpoint=localhost:0`) so the test and the DDP
   asset do not depend on host-name resolution. Check whether `ddp_train_skeleton.py`'s usage text should say so.
2. `ams-flux-ratio`: decide whether the committed toy-closure numbers should be platform-independent. Options: a
   tolerance check on the summary statistics, per-toy seeding (`SeedSequence.spawn`) so one draw cannot shift the
   rest, or documenting that the toy summary is reproducible per platform only.
3. `tools/check_relocation.py`: copy git-listed files (as `test_batch_privacy` now does) instead of the whole tree,
   so ignored local files such as a venv cannot fail the relocated packaging scan.
4. Diagram tooling note: state in `skills/research-communication` (or the matrix) that Mermaid CLI needs
   `chrome-headless-shell` installed for its puppeteer version.
5. Live routing on E2 (62 cases), if a budget is approved.
6. Optional: log in to an isolated config once to close the F07 invocation on E2.

## Local state left by this run

- `~/.venvs/hep-research-e2` (venv) and `~/.cache/puppeteer/chrome-headless-shell` (Mermaid's browser).
- Homebrew: `mermaid-cli`, `plantuml` and their dependencies (node, openjdk, graphviz 16.1.0 and others).
- `.legacy/agentic-ai-skills` (git-ignored, read-only).
- The old `plugins/hep-research/.venv-hep` was moved to the session scratch directory (`.../scratchpad/venv-hep-parked`);
  it is no longer used and can be deleted.
- The user's `~/.claude` is unchanged; the installed plugin there is still `1dea804`.

## Follow-up status (2026-10-04)

Items 1–4 fixed in `7f8249c` (PR #21, merge `e54707d`); VALIDATION FULLTEST-E2-FOLLOWUPS. Check-run
`check-run-2026-10-03T202224Z.json`: 14 pass, 0 fail, 0 skip; unit tests 1242 run, 0 fail, 9 skip. Relocation
`results/relocation-20261003T202224Z.json` passes with an ignored venv planted in the tree.

Correction to item 1: `--standalone` alone does not fix the hang. With an unresolvable host name it still waits in
the rendezvous; `--standalone --local-addr=127.0.0.1` passes and is what the test and the guidance now use.

Items 5 (live routing on E2, needs a budget) and 6 (log in to an isolated config to close the F07 invocation)
remain open. The installed plugin in `~/.claude` was reinstalled at `e54707d`.

# FINAL REPORT: INSTALL of `hep-research` into Claude Code on this workstation (TASK r2)

Date 2026-10-03. Commit `3aa942c5fadc9a3a38c183c3e34ff49c1a7112f4` (`main`, identical to GitHub `main`).
Environment **E2**: macOS 26.5 (Darwin 25.5.0), arm64 Apple M3, Python 3.13.2, `.venv-hep` with numpy 2.5.3,
scipy 1.18.1, matplotlib 3.11.2, sympy 1.14.0; Claude Code 2.1.288; headless model claude-opus-5-5.
Decisions: Q1 GitHub source (user). Gate failures: install anyway (user). Q2 routing smoke test: not approved, not
run. Q3, Q4: not answered; results kept local and uncommitted.

## End state

`hep-research@hep-research-dev` 0.1.0 is **installed at user scope and enabled** in `~/.claude`. The marketplace is
the GitHub repository `hchouTW/hep-research`, cloned to `~/.claude/plugins/marketplaces/hep-research-dev` at
`3aa942c`. Sessions load the plugin from the cache `~/.claude/plugins/cache/hep-research-dev/hep-research/0.1.0`,
**not** from this working tree: edits or branch switches here do not change what runs. To pick up new commits on
GitHub `main`: `claude plugin marketplace update hep-research-dev`, then `claude plugin update
hep-research@hep-research-dev` (or reinstall).

## Summary

| Step | Result | Evidence (`results/`) |
|---|---|---|
| I00 baseline | done | `I00-environment.md`, before-listings |
| I01 gate | **fail** (unittest: 5 fail, 1 error); 12 other checks pass, 1 skip; `validate --strict` pass | `I01-gate.md`, `check-run-2026-10-03T134843Z.json` |
| I02 backup | done | `backup/` (git-ignored, SHA-256 in `backup/SHA256SUMS`) |
| I03 marketplace | pass | `I03-marketplace-add.txt`, `marketplace-list-after.txt` |
| I04 install, config diff | pass | `I04-install.txt`, `I04-details.txt`, `I04-config-diff.txt` |
| I05 discovery, invocation, profile access | pass ($0.22) | `I05-invoke.md`, `I05-invoke-hep-theory.jsonl` |
| I06 interactive check | **unverified**: needs the user | — |
| I07 routing smoke test | not run (Q2) | — |
| I08 record | done | VALIDATION `## INSTALL (2026-10-03, E2)`, CHANGELOG entry |

## Acceptance criteria

| AC | Result |
|---|---|
| AC1 same SHA; gate no fail | **fail**: same SHA throughout, but the gate has the unit failures below (install proceeded on the user's decision) |
| AC2 listed, enabled, user scope | pass |
| AC3 config diff only adds hep-research | pass |
| AC4 seven skills, namespaced load, profile read under install path | pass |
| AC5 interactive confirmation | open: not yet confirmed by the user |
| AC6 routing | "routing smoke test not run (Q2)"; AC20 unchanged |
| AC7 no E1 edit | pass |
| AC8 only VALIDATION.md and CHANGELOG.md changed under the plugin; no backup committed | pass (`git diff --stat`; `backup/` ignored) |
| AC9 rollback and source behavior stated | pass (this report) |

## Every fail, skip and unverified item

| Item | Kind | Cause |
|---|---|---|
| `test_batch_slurm.SlurmShimTests.test_golden_array_script_and_dry_run` | fail | macOS `/var/folders` → `/private/var/folders` symlink; `<CAMPAIGN>` placeholder substitution misses the resolved path |
| `test_batch_htcondor.HTCondorShimTests.test_file_transfer_mode_remaps_outputs_and_matches_golden` | fail | same symlink cause |
| `test_batch_privacy.PackagingTests.test_planted_account_fails_the_packaging_check` | fail | test copies the untracked `.venv-hep` along with the plugin tree; NumPy license e-mails trip the scanner. Confirmed: passes with the venv outside the tree |
| `test_root_cpp_assets.RootCppAssetTests` setUpClass | error | `make_root_fixtures.py` runs `python3` from `PATH` (miniconda 3.13); Homebrew ROOT 6.38.04's PyROOT is built for 3.14.4 and fails at `dlopen`, which the test does not treat as "ROOT absent" |
| `test_theory_comparison.PathDTests.test_passes_predeclared_criteria` | fail | `response_matches_path_b` is an exact `np.array_equal`; false on arm64 / numpy 2.5.3 |
| `test_theory_comparison.PathDTests.test_reproduces_committed_output` | fail | consequence of the previous row (output hash differs) |
| `ams_ledger_preservation` | skip | legacy checkout not fetched (out of scope in r2) |
| 70 unit-test skips | skip | not broken down by cause in this run (optional tools absent, slow tests, no legacy checkout, as in E1) |
| I06 slash completion and `/plugin` | unverified | requires an interactive session by the user |

## Comparison with the previous run

E1 `check-run-2026-10-03T061357Z.json` (Linux, Python 3.11.15, `6ad6228`): 13 pass, 0 fail, 1 skip; 1240 unit
tests, 1162 pass, 78 skip. E2 here (`3aa942c`): 12 pass, 1 fail, 1 skip; 1235 run, 1159 pass, 5 fail, 1 error,
70 skip. The failures are new on E2 and come from the platform and local tooling. The run count differs by five
because the ROOT asset class errored in setUp; the skip count is lower because Homebrew ROOT is present here.

## Rollback

1. `claude plugin uninstall hep-research@hep-research-dev`
2. `claude plugin marketplace remove hep-research-dev`
3. Diff `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json` and `known_marketplaces.json` against
   `results/backup/`. Restore from the backup only if a non-timestamp difference remains, and only after asking.

Lighter alternative: `claude plugin disable hep-research@hep-research-dev`.

## Follow-ups (one task each)

1. Batch shims: normalize temp paths with `os.path.realpath` (or `Path.resolve`) before `<CAMPAIGN>` substitution so
   the Slurm and HTCondor goldens pass on macOS.
2. `test_batch_privacy`: copy only git-tracked files (or ignore `.venv*`) when building the scan copy.
3. ROOT tests: run fixture scripts with `sys.executable`, and treat any failure of `import ROOT` (not only
   ImportError) as "ROOT unavailable → skip".
4. `theory-comparison`: decide whether `response_matches_path_b` should use a stated tolerance, or make both paths
   compute the matrix by the same operation order; re-baseline the committed output if needed.
5. `profiles/theory/qed-benchmark/conventions.json`: add an explicit `scales` entry (likely `not-applicable` at fixed-α
   tree level); the installed `hep-theory` skill flagged its absence in I05.
6. Separate order for the r1 full test in an isolated configuration on E2 (examples, adapters, relocation, 62-case
   routing).
7. Q3: update global `CLAUDE.md` to name the `hep-research:*` skills instead of legacy skills that are not
   installed here.

## Follow-up status (2026-10-03)

Items 1–5 fixed in `0ab9cd8` (VALIDATION E2-FOLLOWUPS; check-run `check-run-2026-10-03T141301Z.json`: 13 pass,
0 fail, 1 skip; unit tests 1241 run, 0 fail). Item 6 (r1 full test as a separate order) and item 7 (global
`CLAUDE.md`) remain open. The installed plugin still runs the `3aa942c` clone; these fixes change no skill text, only
tests, one example's output and one profile file, and reach the install after
`claude plugin marketplace update hep-research-dev` and `claude plugin update hep-research@hep-research-dev`.

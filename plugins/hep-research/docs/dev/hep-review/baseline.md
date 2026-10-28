# hep-review v9: baseline (T00 step 10)

Command: `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/hep-research-e2/bin/python tools/run_all_checks.py --no-cli --out <scratch>`
(Python 3.13.2, macOS arm64; host CLI checks skipped with `--no-cli` because they need the installed hosts and are not
affected by this work).

## Clean baseline: base commit 42f5bad1 (the run that counts)

Run on an export of the base commit (`git archive 42f5bad1 plugins/hep-research` into the session scratch, not a git
checkout), 2026-10-28T23:26:15Z:

| Check group | Result |
|---|---|
| Checks | 31 pass, 0 fail, 2 skip (`claude-plugin-validate`, `codex-plugin-load`: `--no-cli`) |
| unittest | 6000 run, 0 failures, 0 errors, 178 skipped, 480 modules, 0 failed to finish (885 s) |

**Pre-existing failures: none.** Skips: the 178 skipped tests are optional-dependency or environment skips (an export
without `.git` skips a few more than a checkout: 178 vs 169); they are unverified, not passing.

## First attempt (discarded as a baseline)

A run started from the worktree at 06:30 overlapped this session's own first commits, so it saw files written during
the run. It reported 2 failures, both caused by this work and not pre-existing: `packaging` (private-path wording in an
early draft of `discovery.md`, since reworded) and `naming` (names `new`, `obj`, `Ob` in the new test files, since
renamed). It is kept here only to explain why the clean export run was made.

## How regressions are judged

New failures are judged against the clean baseline above: any failing check or test that passes at 42f5bad1 is a
regression of this branch.

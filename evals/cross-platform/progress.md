# Cross-platform support — progress log

Task file: `hep-research-cross-platform-task.md` (SHA-256 `ff09ff57a1cbb5264601e0a305710c9fc2fea734b5abf604c25a0118e63a65a0`),
executed as an implementation task: parts A (runbook) and B–E (PRs 1a, 1b, 2, 3). Location `evals/cross-platform/` is
the task's default (Open Questions: pending maintainer confirmation).

Lines in this log are written by the executing agent; they are not a trust anchor (task A7).
Paths: `<main checkout>` is the repository clone, `<WT_ROOT>` its sibling folder `hep-research-xplat/`.

## Preconditions (A2) — 2026-10-31

| Item | Result |
|---|---|
| `git` | present |
| `gh auth status` | logged in as the repository owner, scopes include `repo`, `workflow` |
| Python 3.13 on PATH | 3.13.2 (miniconda); venv built from Homebrew 3.13.7 |
| Network (PyPI, GitHub) | PyPI HTTP 200; `git fetch origin` ok |
| Python 3.9 for local guard checks | `uv` absent; `/usr/bin/python3` is CPython 3.9.6 (Xcode CLT), used for the local 3.9 checks |
| Session account | unprivileged (not root); AC2(b) checkable locally |
| Host | macOS arm64 (E2-like), Darwin 27.2 |

Environment (A4): `<WT_ROOT>/scratch/venv` (Python 3.13.7) with `requirements-ci.lock`, `ruff==0.16.10`, `mypy==2.4.0`.

## PR 1a — modules and generator

### Preflight (A3, A7)

| Item | Value |
|---|---|
| Target repository | `<main checkout>` (remote `origin` = `github.com/hchouTW/hep-research`) |
| Worktree | `<WT_ROOT>/pr-1a` |
| Branch | `xplat/pr-1a-modules` (not the default branch) |
| Base | `origin/main` = `97df572e577e45766d8cc864bf739564c6c47c1c` (two commits after the task's `6d39539`: PR #332 macOS follow-ups; rechecked the facts the steps edit) |
| `git rev-parse --show-toplevel` | `<WT_ROOT>/pr-1a` (equals the worktree) |
| Main checkout `git status --porcelain` | empty (0 lines) |
| Scratch | `<WT_ROOT>/scratch/` (`venv/`, `runs/`) |
| Python | venv 3.13.7; old interpreter `/usr/bin/python3` 3.9.6 |

### Steps (2026-10-31)

- **1a.1** `core/interpreter_guard.py` + `tests/core/test_interpreter_guard.py` (13 tests: every branch with patched
  `sys.version_info`, `os.execv`, `os.access`, `os.geteuid`; `MIN_PYTHON` equals `requires-python`). Added to `FILES`
  in `test_python_compat.py`. Real 3.9: `guard()` prints the guidance line and exits 2. Checks: tests OK, `ruff check
  core contracts` clean, `check_layering` ok (after 1a.3), `check_naming` pass. Fix attempts: 0.
- **1a.2** `core/hostcaps.py`, `tests/_platform.py` (`needs()`), `tests/core/test_hostcaps.py` (13 tests). Attempt 1
  failed: patching `os.name = "nt"` broke `pathlib` in `state_dir` (`with_segments` traceback); fix: a patchable
  `on_windows()` helper. Naming gate flagged `wsl`/`xdg` (no vocabulary layer) and `tmp` (forbidden): added `wsl`,
  `xdg` to `core/naming/data/framework-names.json` programming abbreviations (`wsl()` is the name the task fixes),
  renamed `tmp` to `scratch`. Fix attempts: 1 (test), 1 (naming).
- **1a.3** `core/OWNERS.json` entries `interpreter_guard`, `hostcaps` (steward hep-computing; written with the file's
  own formatting, diff +34 lines), `docs/architecture.md` §2 table, `CORE_VERSION` 1.4.0 → 1.5.0 (every profile
  declares `core >=1.0,<2.0`). `check_layering`: ok.
- **1a.4** `GUARD_VARIABLES` in `core/partition/executors.py` (taken from `core.interpreter_guard`) refused by
  `passthrough_problems`; `bundle.guard_problems` refuses a spec `env`/`environment` mapping or a configuration
  `env_passthrough` naming them (`bundle.guard_variable`), checked in `build` and `freeze`. The spec has no
  environment field today; the check covers the two places a campaign could set one. New
  `tests/core/test_partition_guard_variables.py` (6 tests); all `tests/core/test_partition*` pass (132 tests).
- **1a.5** `tools/skill_scripts.py` → `tools/skill_scripts.json`: **198 scripts**, **70 unresolved names**,
  28 named files without a `__main__` block. Resolution order as the task gives it, plus three recorded additions:
  the skill's own `assets/` next to `scripts/` for bare names; paths relative to the referencing file and to
  `skills/`; adapter-relative paths (`assets/geant4_build.py` in the geant4 adapter text) when one adapter has it.
  `<plugin root>` wrapped across a line is read as the plugin root. No name is ambiguous (more than one match) after
  the skill's own folders take precedence (`review.py` resolves per skill). Unresolved list: user and example file
  names (`train.py`, `utils.py`, `analysis.py`, ...), external tool files (`combineTool.py`, pyhf `modifiers/...`),
  placeholders (`$PWD/worker/toy.py`, `skills/<owner>/...`), test module names, and bare names of another skill's
  scripts (`cherenkov_angle.py` in hep-citations; each is listed by full path from its own skill). Test
  `tests/tools/test_skill_scripts.py` (drift, new unresolved name, depth, exclusions). Both `review.py` files and
  `render_results.py` are listed. Fix attempts: 2 (tokenizer split `<plugin root>` at the space; wrapped root and
  adapter-relative paths), 1 (host-neutral check: example path and `${CLAUDE_PLUGIN_ROOT}` literal in the generator).
- **1a.6** `test_python_compat.py`: every listed script parses as Python 3.9 (grammar plus f-string tokenizer;
  `runtime_names=False`), real 3.9 compiles them all, the guard-block assertion (`tools/skill_scripts.py
  guard_problems`, skipped until PR 1b) and a non-skipped test that the checker catches a missing block, a wrong
  depth, a block after another import or before `__future__`, an edited body. Only grammar failure:
  `render_results.py:136` (fixed by moving the expression out of the f-string; same string). Runtime-name hits
  (`datetime.UTC` in `contracts/permit.py`, `contracts/review.py`, `hep-authoring/scripts/review.py`,
  `evaluate_design.py`) are out of the grammar check by design (the guard stops 3.9 first). Fix attempts: 1
  (late `__future__` import not detected).
- **1a.7** README "Setup requirements" (guard rules; macOS: Homebrew/conda/uv 3.13, `HEP_RESEARCH_PYTHON`,
  `requirements-core.txt`, torch/xgboost arm64 wheels, ROOT from conda-forge), environments reference section
  "Interpreter for skill scripts", capability-matrix row. `check_host_neutral`: ok.

Observation for the maintainer: Homebrew's `/opt/homebrew/bin` (and the Cellar) is writable by the installing account,
so the guard (rule: target and folder not writable) does not switch to a Homebrew interpreter; the README says so.

### Local validation (A5.3)

| Run | Command | Result |
|---|---|---|
| units 1/6 | `run_all_checks.py --part units --no-cli --jobs 4` | 6315 run, 6 failures + 1 error |
| units 2/6 | same, after the fixes below | 6315 run, 0 failures, 1 error (pre-existing), 293 skipped |
| static | `run_all_checks.py --part static --no-cli` | exit 0 |
| lint | `ruff check core contracts`; `mypy` | clean; no issues in 119 files |
| checks | `check_layering`, `check_naming`, `check_host_neutral`, `check_packaging` | all exit 0 |
| AC6 diff | `git diff --stat origin/main -- skills/*/SKILL.md contracts/stanzas contracts/schemas/tool_contract.json examples contracts/fixtures <repo>/.githooks` | empty |

Failures of units run 1 and their fixes (one attempt each):
- `test_batch_privacy` packaging scan: `/Users/u/` in `test_hostcaps.py` read as a private path → `C:/state/...`.
- `test_reference_inventory`, `test_reference_soft_budget`, `test_run_all_checks` (hanging-module test runs a
  check that reads the inventory): stale `docs/reference-inventory.*` after the environments-reference edit →
  regenerated with `tools/reference_inventory.py`.
- `test_pyproject` (README, capability matrix): new lines named "Python 3.9" (read as a floor statement) → reworded.
- naming gate (static): variable `new` in `test_skill_scripts.py` → `unseen`.

**Pre-existing failure** (A6): `tests.adapters.test_root_cpp_assets` setUpClass fails identically on unmodified
`origin/main` (detached worktree `<WT_ROOT>/scratch/main-ref`): `make_root_fixtures.py` run with
`/opt/homebrew/bin/python3.14`, which has no ROOT on this host. Unrelated to this task; not fixed.

A6 counters, PR 1a: units runs 2/6; max fix attempts on one failure 2/3 (skill-script tokenizer); no early stop.
AC status (local): AC1 not yet (macOS units run green except the pre-existing host error; `needs ` skips 0);
AC3 holds (`find_python.py` under 3.9 finds 3.13; it has no `--json` flag, JSON is its default output;
`runner.py --help` under 3.9 exits 0); AC6 holds locally; AC7 holds (`test_partition_guard_variables`).

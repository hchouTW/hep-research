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

PR 1a: draft PR #333 (base `main`), pushed 2026-10-31; CI results below when complete.

## PR 1b — guard roll-out

### Preflight

| Item | Value |
|---|---|
| Worktree | `<WT_ROOT>/pr-1b` |
| Branch | `xplat/pr-1b-guard` |
| Base | `xplat/pr-1a-modules` = `bbf90eec3e6129cc44eb8265a7355010aa7f2840` |
| `git rev-parse --show-toplevel` | `<WT_ROOT>/pr-1b` (equals the worktree) |
| Main checkout `git status --porcelain` | empty (0 lines) |
| Python | venv 3.13.7; `/usr/bin/python3` 3.9.6; read-only 3.13 venv `<WT_ROOT>/scratch/ro/py313` (`--copies`, `chmod a-w`) |

### Steps (2026-10-31)

- **1b.1** `tools/insert_interpreter_guard.py` (block text and placement from `tools/skill_scripts.py`
  `GUARD_BLOCK`/`guard_insertion_line`; a stale block is replaced in place). First run: 198 changed; second run: 0
  changed (idempotent). `guard_insertion_line` now keeps a shebang and leading comments first when a file has no
  docstring or `__future__` import. `ruff check core contracts`: clean; `ruff --statistics` on `skills tools`
  identical before and after. Naming gate: `new` → `inserted` (1 attempt). Tests for the script added to
  `tests/tools/test_skill_scripts.py` (idempotency on four layouts, stale-block replacement, `--check`).
- **1b.2** `GUARD_ROLLED_OUT = True`: `test_python_compat`, `test_no_bytecode`, `test_skill_scripts` pass.
- **1b.3** AC2 driver `<WT_ROOT>/scratch/ac2_check.py` over all 198 scripts with `/usr/bin/python3` (3.9.6),
  `--help`, result file `<WT_ROOT>/scratch/runs/1b-ac2/ac2.json`:

  | Case | Passed |
  |---|---|
  | (a) unset → exit 2, one `hep-research:` line, empty stdout | 198/198 |
  | (b) read-only 3.13 venv → same exit and stdout as that interpreter directly | 198/198 |
  | (c) 3.9 itself / wrapper script launching 3.9 → "did not provide one" | 198/198, 198/198 |
  | (d) relative / bare name / writable target (the shared venv) / `--protected` → guidance, no switch | 198/198 each |
  | (d) root | not run (session is unprivileged, no root available); covered by `test_interpreter_guard` (patched `geteuid`) |

  AC3: `find_python.py` under 3.9 → `found` 3.13.2; `runner.py --help` under 3.9 → exit 0. AC4: a parent started
  with 3.9 + `HEP_RESEARCH_PYTHON` (switched to 3.13) runs `/usr/bin/python3 li_ma_significance.py --on 10 --off 40
  --alpha 0.2`: exit 0 and stdout identical to the 3.13 interpreter run directly; the marker is not left in the
  parent's environment.
- **1b.4** `docs/architecture.md` §6 (block, rules, conflicts, exemptions, removal condition); CHANGELOG
  (code-release digest changes; re-pin and requalify).

PR 1a: CI on #333 complete, 22 pass, 2 skipped (all required jobs green). PR 1a *Done when* holds (AC1 on macOS:
only the pre-existing `test_root_cpp_assets` host error).

### Local validation — units 1/6 (2026-10-31): **STOP**

`run_all_checks.py --part units`: 6318 run, 12 failures, 1 error (pre-existing `test_root_cpp_assets`). The 12
failures are three example-replay tests, all caused by the guard block itself:

| Test | What differs from the committed output |
|---|---|
| `tests.examples.test_analysis_to_paper` (2 files) | `provenance.code_paths` gains `core/interpreter_guard.py` |
| `tests.examples.test_ml_classifier_to_inference` | `ml_artifact.provenance.code_paths` 17 → 18 entries (same file) |
| `tests.examples.test_geant4_thin_silicon` (9 files) | `provenance.code_paths` +1 (same file); `extension.tools[].version` of `check_geant4_study.py` and `geant4_benchmarks.py` (the first 16 hex of each script's SHA-256) change because the scripts now carry the block |

Cause: the artifacts are written by skill scripts the examples start as `__main__` subprocesses; the guard block
imports `core.interpreter_guard`, and `core/trace.py code_paths` records every loaded plugin file. In-process imports
(non-`__main__`) are unaffected. This contradicts task Background 10 ("after changing one, all example and fixture
tests still passed"): the thin-silicon replay compares the recorded script hashes.

Why this is a STOP (A6 fatal: the fix requires an out-of-scope change): every fix either edits committed example
outputs (Out of Scope; AC6 requires an empty `examples/` diff), changes what provenance records (`core/trace.py`
excluding a loaded file, or the replay tests ignoring `code_paths`/tool versions: a change to recorded provenance and
to test strictness the maintainer must decide), or changes the task's fixed guard block (e.g. dropping the module from
`sys.modules`). No fix attempted. Counters PR 1b: units runs 1/6, fix attempts on this failure 0/3.

Pushed `xplat/pr-1b-guard` (work in progress, no PR opened). Options for the maintainer are in the conversation report.

### Maintainer decision and resume (2026-10-31)

The maintainer chose option 1: regenerate the three examples' committed outputs and continue (AC6's empty
`examples/` diff relaxed for these three). Regenerated in E2 (`~/.venvs/hep-research-e2`, Python 3.13.2, NumPy 2.5.3,
SciPy 1.18.1) with each `run.py`'s defaults: 14 files, +29/−17. Every changed line is `"core/interpreter_guard.py"` in
`code_paths` (12), the two tool hashes (`check_geant4_study.py` a305c4d1dfa78b86 → b7121e2b4d8e7480,
`geant4_benchmarks.py` a1ef685c08f1ed0f → d10569e7cb964fdb, 7 records each), or an artifact `sha256` covering them
(3 lines); no number, no PNG (the `docs/maintenance.md` acceptance rule). The three replays pass, and so do
`test_design_minimal_spectrometer` and `test_design_search_j16`, which also record a Geant4 script hash but did
not change. Fix attempts on this failure: 1/3.

### Local validation — units 2/6 (2026-10-31)

6318 run, 0 failures, 1 error (pre-existing `test_root_cpp_assets`), 292 skipped. Static part exit 0; ruff, mypy,
layering, naming, host-neutral, packaging all pass; `insert_interpreter_guard.py --check` ok. AC6 diff empty outside
the 14 approved example files. A6 counters PR 1b: units runs 2/6; fix attempts max 1/3; no early stop.

PR 1b: draft PR #334 (base `xplat/pr-1a-modules`); CI 22 pass, 2 skipped. *Done when* holds.

## PR 2 — macOS and Linux

### Preflight

| Item | Value |
|---|---|
| Worktree | `<WT_ROOT>/pr-2` |
| Branch | `xplat/pr-2-macos-linux` |
| Base | `xplat/pr-1b-guard` = `cc23f8cee074482e90bc799748d2207951cb1f55` |
| `git rev-parse --show-toplevel` | `<WT_ROOT>/pr-2` (equals the worktree) |
| Main checkout `git status --porcelain` | empty (0 lines) |

### Steps (2026-10-31)

- **2.1** `executor_capabilities.py` (G2: `process_groups`, `proc_fs`; G5: `process_groups`) and `run_workflow.py`
  (`_proc_scan`, termination scope, POSIX branch) use `core.hostcaps`. New `unavailable_modes` in the
  qualification record and the `qualify` output; on this Mac: M2 (G2 `unsupported`: no /proc) and M3. Tests:
  `@needs("proc_fs")` / `@needs("process_groups")` in `test_executor_b2`, `test_workflow_b1`; new
  `test_modes_this_host_cannot_admit_are_named` (attempt 1 asserted M3 lacks only G3/G4; on macOS it also lacks G2:
  test corrected). The hep-review store tests already carry a macOS `mount` fixture (`MAC_MOUNT`); added a live
  darwin test (the temporary folder resolves to APFS through mount(8)). Reference
  `research-workflow-control.md`: M2 unavailable without /proc. `tools/skill_scripts.json` regenerated (a source line
  moved). Fix attempts max 1/3.
- **2.2** `test_lineage.py:286` quotes the worker path; also quoted: `test_partition_remote` (2),
  `test_side_effects_f13` (2), `test_protected_entry_points`, `test_batch_hardening` (2), `batch_harness`,
  `test_batch_bundle`, `fixtures/cr_propagation/e1/active_addition.py`. All affected modules pass.
- **2.3** `check_packaging.py` rule `appledouble`; tests in `test_check_packaging_rules.py` (AC9).
- **2.4** `tests.yml`: `hostile-paths`, `old-python`, shellcheck step in `lint`; `platforms.yml`: `macos`,
  `windows`. `tools/platform_checks.py` drives AC2-AC4 (local run: 198/198 every case, AC3, AC4 pass) and AC11.
  Two scripts answer `--help` with usage and exit 2 on every platform (`contracts/comparison/gate.py`,
  `contracts/project.py`): listed in `USAGE_EXIT`, not failures. shellcheck is not installed locally (CI only);
  `/bin/bash -n` passes on the three scripts.

### First CI run of the new jobs (#335, 2026-10-31) and 2.5 fixes

| Job | Result | Finding → fix (one commit each) |
|---|---|---|
| `old-python` | pass | AC2 (all cases incl. root through sudo), AC3, AC4 on Linux with a real 3.9; real 3.9 compiles every skill script |
| `lint` | fail | shellcheck SC1090 / SC2317 in `lcg_view_setup.sh` → directives (no behaviour change) |
| `hostile-paths` | fail | packaging scan of the NFD/.DS_Store/AppleDouble tree: pass; `tests/contracts` 1160 OK; `tests/tools`: `test_ci_follows_the_floor` rejects the old-python job's 3.9 → the test exempts that job by name and pins it to 3.9 + 3.13 |
| `checks` units 2/3, `checks-complete` | fail | same floor test |
| `platforms/macos` (macos-26-arm64, Python 3.13.17, `ulimit -n 256`) | fail (continue-on-error) | 6327 run, the one failure is the same floor test; **no tolerance difference**; `needs ` skips 9 = 0.14 % of run (4 `needs proc_fs`) |
| `platforms/windows` | fail (not required) | AC11 sweep **passed** (198 scripts, no traceback, `state_dir` under the redirected LOCALAPPDATA); AC12: 4170 files `w/crlf` (no `.gitattributes` yet, PR 3) and the step itself died of SIGPIPE (`head`) → `sed -n`; contract tests now run after it (`if: always()`) |

**macOS known-differences list (A8, for the maintainer): empty.** No test at or below 1e-12 differed on the runner.
Fix attempts: one per distinct failure (3 failures). CI runs of the units part: 1 (counts toward the PR 2 limit with
the local runs).

### Local units 1/6 in a hostile path (2026-10-31)

Working directory `<WT_ROOT>/scratch/hep 測試 paths/work` (a symlink to the worktree), `TMPDIR` a symlink in the same
folder. 6322 run, 34 failures, 9 errors. **All pre-existing** (A6): the same ten modules fail on unmodified
`origin/main` (`<WT_ROOT>/scratch/main-ref`, `97df572e`) with the same `TMPDIR`, most with more failures there:

| Module (failures/errors on `main`) | Root cause |
|---|---|
| `test_simreco` (11/0) | **product defect**: the simreco C++ JSON reader rejects `\uXXXX` escapes ("non-ASCII \u escapes are not supported"), which Python's `json.dumps` writes for a non-ASCII path |
| `test_batch_slurm` (14/0), `test_batch_htcondor` (16/4), `test_batch_cmp_regressions` (2/0), `test_batch_provenance` (2/0), `test_batch_watch` (4/0), `test_batch_hardening` (1/1), `examples/test_batch_partition` (0/1) | tests assume a space-free `TMPDIR`: HTCondor's deliberate `htcondor.path_whitespace` refusal, Slurm golden scripts that now carry quoted paths, shims whose `#!` line points into the spaced folder |
| `test_partition_bundle` (2/0) | a test writes a `#!` interpreter inside the spaced `TMPDIR`; the bundle correctly refuses it (`bundle.bad_shebang`) |
| `test_diagrams` (0/2) | renderer shims with a `#!` line inside the spaced `TMPDIR` |
| `test_root_cpp_assets` | the host's `python3.14` has no ROOT (as before) |

Not fixed (A6: pre-existing). Effect: the `hostile-paths` job passes on pull requests (its subset), but its full units
run on pushes to `main`, weekly and manual runs will fail until these are addressed (simreco `\u` decoding; tests that
need a space-free temporary folder create one). **Open human checkpoint.**

CI run 3 (#335): every required job passes and macOS passes; `hostile-paths` failed only in
`test_partition_bundle.test_shebang_interpreters_are_hashed_and_launchers_refused` (pre-existing under a spaced
`TMPDIR`, but inside the job's PR subset, so fixed per 2.5): the launcher link now lives in a space-free folder and
the first word is quoted (test-only; bundle semantics unchanged). The PR subset passes locally in the hostile path
(contracts, tools, partition, blinding, r5). Fix attempts on it: 1/3. The earlier pattern fix (no
`tests/core/test_protected*`, exit 5 "NO TESTS RAN"): 1/3.

### CI run 4 (#335, 2026-10-31): **STOP**

All required jobs pass; macOS passes; Windows fails as expected (AC12 CRLF until PR 3; Windows contract tests
recorded). `hostile-paths`: the packaging scan and every unit-test part of the PR subset pass (contracts 1160 OK,
tools 383 OK, partition 132 OK, blinding 91 OK, r5 14 OK); the last command, `tools/check_relocation.py`, fails: it
runs the whole `run_all_checks.py` in a relocated copy (`.../hep 測試 paths/tmp/hep research relocated .../plugin
copy`) with the hostile `TMPDIR` inherited, and its `unittest` check has 6327 run, 32 failures, 8 errors: the
pre-existing hostile-`TMPDIR` failures listed above (simreco `\u` decoding; tests that assume a space-free temporary
folder).

Why STOP (A6): the units-part limit for PR 2 is reached (local hostile run 1, CI runs 1-4, and this relocated full
suite: 6/6), and the remaining choices are the maintainer's: fix the pre-existing failures, or run the relocation
check with a space-free `TMPDIR` (the copy path itself still has spaces), or drop it from the PR subset. No fix
attempted. PR 2 *Done when*: AC1 holds (macOS units green in CI, `needs ` skips 0.14 %), AC9 holds, AC10 not yet
(hostile-paths red on the relocation step), macOS job run and recorded (known-differences list empty).

## 2026-10-31 PR 2: STOP resolved (maintainer decision: option 1)

- Decision: the PR-subset `tools/check_relocation.py` runs with `TMPDIR="$RUNNER_TEMP"` (space-free); the relocated
  copy's own path still has spaces. The space + Chinese TMPDIR stays on the PR-subset unit tests. The full run on
  main/weekly keeps the hostile TMPDIR and stays red until the ten pre-existing modules are fixed (open checkpoint).
- One extra units run authorized beyond the A6 limit (PR 2 units runs: 7, 6 + 1 authorized).

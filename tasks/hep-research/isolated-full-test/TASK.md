# TASK: Full test of the `hep-research` plugin on E2 in an isolated Claude Code configuration (FULLTEST-E2)

> **For Claude (agent):** This file is a work order. Read all of it before you run anything. Do Phase 0 first, then
> F01–F09 in order, and finish with the Final Report. This task **tests and records**. It does not fix anything: if a
> check fails, record it and open a follow-up (§6). Paths are relative to `plugins/hep-research/` unless they
> start with `tasks/`, `.claude-plugin/` or `~/`. `tasks/` and `.claude-plugin/` are relative to the repository
> root.

> **Revision r1 (2026-10-04).** Follow-up 6 of `tasks/hep-research/full-plugin-test/FINAL-REPORT.md`. It takes over
> the checks that the INSTALL order (`tasks/hep-research/full-plugin-test/TASK.md`, r2) moved out of scope: example
> reruns, the adapter matrix, relocation, the legacy checks and the full live-routing run. Written after inspecting
> `main` at `7bdb522` (PR #18 merged, clean tree) on the E2 workstation. Evidence labels follow
> `tasks/hep-research-plugin.md` §2.2: `[Confirmed]` read in the repository or on this machine, `[Inferred]` a
> conclusion drawn from confirmed facts, `[Proposal]` a design choice open to change, `[Unresolved]` not yet
> established, `[To verify]` a tool or host fact to check before relying on it.

---

## 1. Background

`[Confirmed]` On E2 (macOS 26.5, arm64 Apple M3, Python 3.13.2, Claude Code 2.1.288), only the aggregate check has
run so far: `tasks/hep-research/check-runs/check-run-2026-10-03T141301Z.json` at `0ab9cd8` gives 13 pass, 0 fail,
1 skip (`ams_ledger_preservation`: legacy checkout not fetched). Unit tests: 1241 run, 1171 pass, 70 skip. That run
used only the core stack. The INSTALL order installed the plugin into the user's own `~/.claude`, where it stays
(GitHub marketplace, cache at `1dea804`).

`[Confirmed]` The following have never run on E2:

- **Example reruns** compared with their committed output, for all ten examples.
- **The adapter matrix** with the optional tools.
- **Relocation**: `tools/check_relocation.py` (AC24).
- **The legacy checks**: `check_ams_ledger_preservation` and `check_traceability --legacy`.
- **Live routing over the full case set**: `tests/routing/cases.json` holds 62 cases (42 en, 20 zh-Hant). The last
  live round was run 4 in E1, scoring 43/48 on the earlier 48 cases. It predates the statistics-reinforcement and
  batch-scheduler routing changes.

`[Confirmed]` Tool availability on E2 (2026-10-04):

| Tool | E2 status | Declared in `adapter.json` |
|---|---|---|
| ROOT | Homebrew 6.38.04 present; its PyROOT imports only under `/opt/homebrew/bin/python3.14` | root-uproot: tested 6.40.04 (E1) |
| uproot, awkward | absent | root-uproot: tested 5.7.6 / 2.14.0 |
| pyhf | absent | pyhf-combine: tested 0.7.6 |
| CMS Combine | absent (no `combine`, no `docker`) | pyhf-combine: tested 11.1.0 |
| PyTorch, torchvision | absent | (physics-ml examples and tests) |
| Graphviz `dot` | present (`/opt/homebrew/bin/dot`) | diagram tools |
| Mermaid `mmdc`, PlantUML | absent | diagram tools |
| tectonic | present (`~/miniconda3/bin/tectonic`) | LaTeX build |
| cmake | present | ROOT C++ asset build |
| Slurm, HTCondor | absent | batch-schedulers: `documented`, fake schedulers only |

`[Confirmed]` `tasks/hep-research/scripts/run_headless.py` refuses to run unless `CLAUDE_CONFIG_DIR` is set to a
directory other than `~/.claude`. It writes a fresh project directory per case with that case's synthetic inputs.
`score_routing.py` scores a case as passing when the first skill invoked is `hep-research:<expected_primary>`.

`[Inferred]` `tools/check_relocation.py` copies the plugin tree, ignoring only `__pycache__`, `*.pyc`,
`.pytest_cache` and `output-*`. A venv inside the plugin directory would therefore be copied too, and its license
files would trip the packaging scan in the copy (the cause of E2 follow-up 2). This order keeps the venv outside the
plugin tree (R4).

## 2. Objective

At a single recorded commit of `main`, run every check the repository defines for the plugin on E2. Run the live
routing in an isolated Claude Code configuration that holds only this plugin. Record each result with the E2 label,
add a dated FULLTEST-E2 section to `VALIDATION.md` and a check-run JSON, and list every failure, skip and unverified
item with its cause. No result is copied from E1.

## 3. Scope

### In scope

- The aggregate `tools/run_all_checks.py`, with the legacy checkout fetched by
  `tasks/hep-research/scripts/fetch_legacy.sh`, so that the ledger and traceability checks run.
- Reruns of all ten examples, compared with their committed output: byte for byte where the example's test claims
  it, numerically otherwise.
- Adapter tests with the optional tools that Q1 approves; tools not installed are recorded as unverified.
- `tools/check_relocation.py`.
- Host checks in an **isolated** `CLAUDE_CONFIG_DIR`: install from a `git archive` copy of the tracked files,
  discovery, one namespaced invocation, and clean removal (the G5 procedure).
- Live routing over all 62 cases with `run_headless.py routing` and `score_routing.py`, if Q2 approves the budget.

### Out of scope

- Fixing any failure. Each one gets a follow-up item (§6).
- Changing, disabling or reinstalling the plugin in the user's `~/.claude`.
- Installing tools into the system Python or Homebrew without approval (Q1).
- Real data, real Slurm or HTCondor clusters, GPUs, and network-blocked downloads such as the pretrained ResNet-18
  weights.
- Editing skill descriptions to improve routing.
- Statements about physical validity, statistical coverage or unblinding.

## 4. Repository context

`[Confirmed]` All paths below were inspected on 2026-10-04.

| Path | Role in this task |
|---|---|
| `tools/run_all_checks.py` | aggregate runner; writes the check-run JSON |
| `tools/check_relocation.py` | relocation check (AC24) |
| `tools/check_traceability.py` | traceability, with `--legacy` for the legacy checkout |
| `tasks/hep-research/scripts/fetch_legacy.sh` | clones `hchouTW/agentic-ai-skills` at `3e995a4` into `.legacy/agentic-ai-skills` (read-only) |
| `examples/` | ten examples: `ams-flux-ratio`, `batch-partition`, `collider-angular`, `detector-resolution`, `end-to-end-sample`, `local-partition`, `published-comparison`, `qed-prediction`, `recasting`, `theory-comparison` |
| `tests/examples/` | example tests, including the byte-identity and committed-output checks |
| `adapters/{batch-schedulers,pyhf-combine,root-uproot}/adapter.json` | declared per-tool status and tested versions |
| `tests/adapters/`, `tests/skills/hep_computing/test_root_integration.py` | adapter tests (`HEP_ROOT_PYTHON`, `HEP_COMBINE_WRAPPER` select the tools) |
| `tests/routing/cases.json` | 62 routing cases with synthetic inputs |
| `tasks/hep-research/scripts/run_headless.py`, `score_routing.py` | live routing harness and scorer |
| `tasks/hep-research/m5/g5/G5-REPORT.md` | isolated install procedure and earlier routing rounds |
| `docs/capability-matrix.md` | per-capability status; every "tested" row today is E1 |
| `VALIDATION.md`, `CHANGELOG.md` | where results are recorded |

## 5. Technical approach

### Execution rules

- R1. Run everything at one commit. Record `git rev-parse HEAD`, and require `git status --porcelain` to be empty
  before F01 and after F08, apart from the new result files.
- R2. Label every result **E2**, and write tool versions next to adapter results. Never write "tested (E1)" for a
  result produced here, and never edit an E1 row.
- R3. Use four result words: **pass**, **fail**, **skip** (with the printed reason) and **unverified** (tool
  missing). A skip is never counted as a pass.
- R4. Keep every venv **outside** `plugins/hep-research/`, e.g. `~/.venvs/hep-research-e2`. This keeps it out of the
  relocation copy and the packaging scan. Install nothing into the system Python, Homebrew or conda base without Q1.
- R5. Never touch `~/.claude`. All host and routing runs use `CLAUDE_CONFIG_DIR` set to a fresh directory under a
  scratch location. Before F06, record a listing of `~/.claude/plugins` and a SHA-256 of `~/.claude/settings.json`;
  check both again after F07.
- R6. Ask before paid or network actions: tool installation (Q1), live routing (Q2). The legacy fetch (F01) and
  the single F06 invocation are covered by this order's approval.
- R7. Do not edit plugin files or task scripts. For each failure, record the command, exit code and output tail.

### Steps

| ID | Step | Expected outcome |
|---|---|---|
| F00 | **Phase 0: baseline.** Record commit, OS, CPU, `claude --version`, Python and package versions. Create the venv outside the plugin (R4) from `requirements-core.txt`, plus the optional packages Q1 approves. Re-run the tool probe in §1. | `results/F00-environment.md` with a present/absent row for every tool in §1 |
| F01 | **Legacy checkout:** `tasks/hep-research/scripts/fetch_legacy.sh`. | `.legacy/agentic-ai-skills` at `3e995a4`; if the clone fails, record why |
| F02 | **Aggregate run** with the venv Python: `tools/run_all_checks.py --out ../../tasks/hep-research/check-runs/`. Set `HEP_ROOT_PYTHON=/opt/homebrew/bin/python3.14` so the ROOT tests run. | Check-run JSON at `HEAD`, 14 checks; `ams_ledger_preservation` and traceability run, not skip |
| F03 | **Traceability with legacy:** `tools/check_traceability.py --legacy ../../.legacy/agentic-ai-skills`. | Coverage of every legacy-tracked file, as in AC01 |
| F04 | **Examples:** run each `examples/*/run.py` with the arguments its test uses, into a scratch directory, twice. Compare the two runs byte for byte. Compare with the committed output byte for byte where the test claims it, else numerically with the test's tolerance. | One row per example: identical, numerically equal (tolerance stated), or differs (diff attached) |
| F05 | **Adapters:** run `tests/adapters` and `tests/skills/hep_computing/test_root_integration.py` with the tools present. Batch schedulers: fake-scheduler tests only. | Per-tool table: tested here (version), or unverified (tool named), compared with `adapter.json` |
| F06 | **Relocation:** `tools/check_relocation.py --out results/`. | Same pass/skip counts as F02 apart from documented relocation skips |
| F07 | **Isolated host:** with `CLAUDE_CONFIG_DIR` set to a fresh directory, add a marketplace from a `git archive` copy of the tracked files at a path with spaces. Install `hep-research@hep-research-dev`, list, then `run_headless.py invoke` with `/hep-research:hep-theory` (the G5 prompt). Uninstall and remove the marketplace. | Seven `hep-research:*` skills; plugin path inside the copy; clean removal; `~/.claude` checks from R5 unchanged |
| F08 | **Live routing** (only with Q2): in a new isolated config holding only this plugin, run `run_headless.py routing --cases tests/routing/cases.json --cwd <scratch> --out results/routing-e2.json`, then `score_routing.py results/routing-e2.json --out results/routing-e2-score.json`. | Scored outcome for all 62 cases (en and zh-Hant), total cost, model named; comparison with run 4 limited to the 48 cases both share |
| F09 | **Record:** add a FULLTEST-E2 section to `VALIDATION.md` and E2 notes to `docs/capability-matrix.md`, only where this run produced evidence; add a `CHANGELOG.md` entry; write `FINAL-REPORT.md` next to this file. | Docs agree with the check-run JSON and result files |

`[Inferred]` F02 covers most of the code. F03–F08 cover what it skips or cannot see: legacy coverage, example
reproducibility across runs, optional tools, the relocated copy, the isolated host path and routing quality.

## 6. Deliverables

1. `tasks/hep-research/check-runs/check-run-<UTC>.json` from F02, at the recorded commit.
2. `tasks/hep-research/isolated-full-test/results/`: environment table (F00), traceability output (F03), example
   table and diffs (F04), adapter table (F05), relocation JSON (F06), host trace and `~/.claude` before/after checks
   (F07), and, if run, routing trace and score (F08).
3. A `## FULLTEST-E2 (<date>)` section in `VALIDATION.md` in the style of BATCH-RUN.
4. E2 notes in `docs/capability-matrix.md` and a `CHANGELOG.md` entry, limited to what this run measured.
5. `tasks/hep-research/isolated-full-test/FINAL-REPORT.md`: summary table, every fail, skip and unverified item
   with its cause, comparison with the E1 check-run `check-run-2026-10-03T061357Z.json` and the E2 check-run
   `check-run-2026-10-03T141301Z.json`, and a follow-up list (one line per failure, each proposing its own task).

## 7. Acceptance criteria

- AC1. Every result file names the same commit SHA, and `git status --porcelain` lists only the deliverables.
- AC2. The F02 check-run records 14 named checks, each pass, fail or skip with a reason. `ams_ledger_preservation`
  is pass, or skip only because F01's clone failed (stated).
- AC3. Unit and profile counts (run, pass, fail, skip) are reported separately. Skips are grouped by cause (missing
  tool, platform, deliberate), and none is counted as a pass.
- AC4. All ten examples have an F04 row. Two runs on E2 are byte-identical for every example whose test claims it,
  or the diff is attached.
- AC5. Every tool in each `adapters/*/adapter.json` has an E2 status: tested here with its version, or unverified
  with the missing tool named.
- AC6. F06 relocation passes, or each difference from F02 is explained.
- AC7. The F07 trace shows seven `hep-research:*` skills and a plugin path inside the archive copy, and removal is
  clean. The `~/.claude/plugins` listing and the `settings.json` SHA-256 match before and after (R5).
- AC8. If F08 runs: all 62 cases have a scored outcome, the total cost and model are stated, and AC20's row gains an
  E2 entry without rewriting the E1 text. If F08 does not run, the report says "live routing not run (Q2)".
- AC9. No E1 entry in `VALIDATION.md` or `docs/capability-matrix.md` is edited.
- AC10. Under `plugins/hep-research/`, only `VALIDATION.md`, `docs/capability-matrix.md` and `CHANGELOG.md`
  change (`git diff --stat`).
- AC11. `FINAL-REPORT.md` lists every fail, skip and unverified item; the list is empty only if there are none.

## 8. Validation

- At the end, re-run `tools/run_all_checks.py --out <scratch>`; its counts must equal F02's, apart from the
  timestamp.
- Run `python3 skills/hep-computing/scripts/lint_task.py ../../tasks/hep-research/isolated-full-test/FINAL-REPORT.md
  --repo ../..` if the report is reused as a task.
- A reviewer picks two F04 rows and the F07 trace, and reproduces them from the commands in `results/`.

## 9. Open questions

- **Q1 [Unresolved]: optional tools.** Which to install for F05, and where? Proposed: pyhf, uproot and awkward in the
  E2 venv (pip, small); PyTorch and torchvision in the venv (larger, CPU wheels for arm64 `[To verify]`); Mermaid
  `mmdc` and PlantUML via Homebrew or npm. CMS Combine has no native macOS build `[To verify]` and Docker is absent,
  so Combine stays unverified unless the user supplies a wrapper (`HEP_COMBINE_WRAPPER`). ROOT 6.38.04 is older than
  the tested 6.40.04 and is recorded as such.
- **Q2 [Unresolved]: live routing budget.** Approve one paid run of all 62 cases? The cost is TBD. `[Inferred]` About
  $5–6: earlier 48-case rounds cost $3.64–4.79 (about $0.08–0.10 per case) on claude-sonnet-5-5, and other models
  will differ. Also choose the host model and whether
  to repeat the changed cases three times for variance, as in round 2.
- **Q3 [Unresolved]: model for F07 and F08.** Is the host default model (claude-opus-5-5 in the INSTALL run)
  acceptable, or should it match E1's claude-sonnet-5-5 for comparison with run 4?
- **Q4 [Unresolved]: branch and PR.** Proposed: commit the results on `test/fulltest-e2` and open a PR, as with
  INSTALL.

## 10. References

- Authoring: `skills/hep-computing/references/task-authoring-guide.md`; repository convention
  `tasks/hep-research-plugin.md` §2.2; sibling orders `tasks/hep-research/full-plugin-test/TASK.md` and
  `tasks/hep-research/batch-schedulers/TASK.md`.
- Evidence: `tasks/hep-research/full-plugin-test/FINAL-REPORT.md`, `VALIDATION.md` (INSTALL, E2-FOLLOWUPS, BATCH-RUN,
  AC20, AC24), `tasks/hep-research/m5/g5/G5-REPORT.md`, `docs/capability-matrix.md`.
- Tools: `tools/run_all_checks.py`, `tools/check_relocation.py`, `tools/check_traceability.py`,
  `tasks/hep-research/scripts/{fetch_legacy.sh,run_headless.py,score_routing.py}`.

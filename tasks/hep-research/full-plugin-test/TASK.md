# TASK: Install the `hep-research` plugin into Claude Code on this workstation and test it there (INSTALL)

> **For Claude (agent):** This file is a work order. Read all of it before you run anything. Do Phase 0 first, then
> I01–I08 in order, and finish with the Final Report. The task **installs, tests and records**. It does not fix the
> plugin: if a check fails, record it and open a follow-up (§6). Paths are relative to `plugins/hep-research/`
> unless they start with `tasks/`, `.claude-plugin/` or `~/`. `tasks/` and `.claude-plugin/` are relative to the
> repository root.

> **Revision r2 (2026-10-03).** This replaces r1, which tested the plugin in an isolated `CLAUDE_CONFIG_DIR` and
> required `~/.claude` to stay untouched. r2 changes the goal: the plugin is to be **installed into the user's own
> Claude Code configuration (`~/.claude`, user scope) and left installed**. The broader r1 checks (byte-identical
> example reruns, the adapter matrix, relocation) are no longer part of this order (§3). The order was written after
> inspecting `main` at `3aa942c` with a clean tree apart from this file. Evidence labels follow
> `tasks/hep-research-plugin.md` §2.2: `[Confirmed]` read in the repository or on this machine, `[Inferred]` a
> conclusion drawn from confirmed facts, `[Proposal]` a design choice open to change, `[Unresolved]` not yet
> established, `[To verify]` a tool or host fact to check before relying on it.

---

## 1. Background

`[Confirmed]` `hep-research` 0.1.0 (seven skills: `detector-response`, `hep-analysis`, `hep-computing`,
`hep-statistics`, `hep-theory`, `physics-ml`, `research-communication`) has been installed only in throwaway
configurations so far. G5 (`tasks/hep-research/m5/g5/G5-REPORT.md`) installed it in an isolated `CLAUDE_CONFIG_DIR`
in a Linux cloud container (Claude Code 2.1.287), and later live-routing rounds used the same isolation. It has never
been installed in a configuration that is used day to day.

`[Confirmed]` The workstation is macOS (Darwin 25.5.0), system Python 3.13.2, Claude Code 2.1.288. Its `~/.claude`
state, read on 2026-10-03:

- One known marketplace, `claude-plugins-official`. `installed_plugins.json` lists ten plugins from it (superpowers,
  skill-creator, github, plugin-dev, pyright-lsp, commit-commands, feature-dev, pr-review-toolkit, code-review,
  code-simplifier), all enabled in `~/.claude/settings.json`, plus two `@synced` entries.
- `~/.claude/skills/` holds only `synced/` (docs, docx, pdf, pptx, xlsx and similar). The legacy standalone skills
  that G5 found competing in routing (`hep-analysis`, `ams-analysis`, `academic-papers` and others from
  `agentic-ai-skills`) are **not** installed here. The `task-authoring` skill that the global `CLAUDE.md` mentions is
  not installed either.
- The repository has a local development marketplace, `.claude-plugin/marketplace.json` (`hep-research-dev` →
  `./plugins/hep-research`). Its remote is `https://github.com/hchouTW/hep-research.git`.

`[Confirmed]` G5 finding: with a **local-directory** marketplace, Claude Code loads the plugin in place from the
marketplace path, not from its cache. `[Inferred]` If the marketplace is added from this checkout, every session
runs whatever is in the working tree, including uncommitted edits and whatever branch is checked out. A Git
marketplace (the GitHub repository) is cloned under `~/.claude/plugins/marketplaces/` and changes only through
`claude plugin marketplace update`. This choice is Q1.

`[Confirmed]` `tasks/hep-research/scripts/run_headless.py` refuses to run unless `CLAUDE_CONFIG_DIR` points at an
isolated directory other than `~/.claude`. It cannot be used against the real configuration as it stands, and this
order does not change it (R6).

## 2. Objective

Install `hep-research` 0.1.0 at user scope into this workstation's real Claude Code configuration. Show that a normal
Claude Code session there discovers the seven `hep-research:*` skills, invokes one by namespace, and reads profile
files from the installed path, with the existing plugins and settings unchanged. Leave the plugin installed and
enabled, record how to roll it back, and record the results with the commit and environment named.

## 3. Scope

### In scope

- A pre-install gate at a single recorded commit: `tools/run_all_checks.py` in a venv and
  `claude plugin validate --strict` on the plugin directory.
- A backup of the parts of `~/.claude` that installation touches, and a written rollback procedure.
- Adding the marketplace (source per Q1) and installing `hep-research@hep-research-dev` at **user** scope.
- Post-install checks in the real configuration: plugin listing, skill discovery, one namespaced invocation, profile
  access from the installed path, and coexistence with the ten existing plugins (nothing else changed, no name
  clash).
- An optional small live-routing smoke test in the real configuration (Q2).

### Out of scope

- Fixing any plugin failure. Each failure gets a follow-up item (§6).
- The r1 full test: byte-identical example reruns, the adapter matrix with optional tools, relocation, and the full
  62-case routing run. They belong in a separate order run in an isolated configuration.
- Installing optional tools (pyhf, uproot, PyTorch, ROOT, Combine, Graphviz and others) or the legacy standalone
  skills.
- Project-scope or local-scope installs, and hosts other than Claude Code CLI on this Mac.
- Editing `run_headless.py`, `score_routing.py` or any plugin file.
- Publishing the plugin to a public marketplace.

## 4. Repository and host context

`[Confirmed]` All paths below were inspected on 2026-10-03.

| Path | Role in this task |
|---|---|
| `.claude-plugin/marketplace.json` (repo root) | marketplace `hep-research-dev`, one plugin `hep-research` → `./plugins/hep-research` |
| `.claude-plugin/plugin.json` | name `hep-research`, version 0.1.0 |
| `requirements-core.txt` | core Python dependencies for the venv |
| `tools/run_all_checks.py` | aggregate gate; writes a check-run JSON |
| `profiles/registry.json`, `profiles/theory/qed-benchmark/` | profile files to read from the installed path in I05 |
| `tasks/hep-research/m5/g5/G5-REPORT.md` | earlier install procedure and its findings (template for I03–I06) |
| `tasks/hep-research/check-runs/` | where the gate's check-run JSON goes |
| `~/.claude/settings.json` | gains `enabledPlugins["hep-research@hep-research-dev"]` and an `extraKnownMarketplaces` entry |
| `~/.claude/plugins/installed_plugins.json`, `known_marketplaces.json` | gain the `hep-research` and `hep-research-dev` entries |
| `~/.claude/plugins/marketplaces/`, `cache/` | where a Git marketplace and plugin cache land `[To verify]` for the local-directory case |
| `VALIDATION.md`, `CHANGELOG.md` | where results are recorded |

`[Confirmed]` CLI commands available in 2.1.288: `claude plugin marketplace add <source> [--scope user]`,
`claude plugin install <plugin>@<marketplace> [-s user] [--json]`, `claude plugin list`, `claude plugin details`,
`claude plugin disable|enable`, `claude plugin uninstall`, `claude plugin marketplace remove|update`,
`claude plugin validate`.

## 5. Technical approach

### Execution rules

- R1. Run the gate at one commit. Record `git rev-parse HEAD`, and require `git status --porcelain` to be empty
  (apart from this task folder) before I01. If Q1 picks the local-directory source, keep `main` checked out with a
  clean tree for the whole task, because the installed plugin reads the working tree.
- R2. Name the environment **E2** (macOS 25.5.0, CPU, Python, venv package versions, `claude --version`, model of
  the headless runs) and put that label on every result. Never write "tested (E1)" for anything run here.
- R3. Use four result words: **pass**, **fail**, **skip** (with the reason printed) and **unverified**. A skip is
  never counted as a pass.
- R4. Change `~/.claude` **only** through `claude plugin …` commands, and only to add `hep-research` and its
  marketplace. Do not hand-edit `settings.json` or the plugin JSON files. Do not install anything into the system
  Python; use `.venv-hep` (already in `.gitignore`).
- R5. Back up before changing anything (I02), and stop and report if the install changes any key other than the
  expected `hep-research` entries.
- R6. Do not edit plugin files or the task scripts. Record the command, exit code and output tail of every failure.
- R7. Ask before paid or network actions: the GitHub marketplace clone (Q1) and any live routing (Q2). The single
  invocation in I05 is a paid call and is covered by this order's approval.

### Steps

| ID | Step | Expected outcome |
|---|---|---|
| I00 | **Phase 0: baseline.** Record commit, E2 environment, `claude --version`, `claude plugin list`, `claude plugin marketplace list`. Create `.venv-hep` from `requirements-core.txt`. | Environment table and the "before" plugin listing in `results/` |
| I01 | **Gate:** `.venv-hep/bin/python tools/run_all_checks.py --out ../../tasks/hep-research/check-runs/`, then `claude plugin validate --strict .` in `plugins/hep-research/`. | Check-run JSON at `HEAD` with no fail (skips listed with reasons); `validate --strict` exits 0. **Stop here on any fail.** |
| I02 | **Backup** `~/.claude/settings.json`, `~/.claude/plugins/installed_plugins.json` and `known_marketplaces.json` to `results/backup/` (outside git; see §6), with a SHA-256 of each. List `~/.claude/plugins/{marketplaces,cache}` and `~/.claude/skills`. | Backup files, checksums and listings |
| I03 | **Add the marketplace** at user scope from the source chosen in Q1: `claude plugin marketplace add hchouTW/hep-research --scope user` (Git) or `claude plugin marketplace add "$(git rev-parse --show-toplevel)" --scope user` (local directory). | `claude plugin marketplace list` shows `hep-research-dev` |
| I04 | **Install:** `claude plugin install hep-research@hep-research-dev -s user --json`, then `claude plugin list` and `claude plugin details hep-research@hep-research-dev`. Diff the three backed-up files against their new versions. | Plugin 0.1.0 listed as enabled. The only diff is the added `hep-research` / `hep-research-dev` entries; the ten existing plugins and all other settings are unchanged |
| I05 | **Discovery and invocation** in a fresh session from a scratch project directory: `claude -p --output-format stream-json --verbose "/hep-research:hep-theory <short QED question from G5>"` with tools limited to Read, Glob, Grep and Skill. Save the stream to `results/invoke-hep-theory.jsonl`. | The init event lists seven `hep-research:*` skills next to the existing ones, with the plugin path under the chosen source; the skill loads by its namespace; at least one read of `profiles/…` from the installed path; no name clash in the skill list |
| I06 | **Interactive check (user):** in a new interactive session, the user types `/hep-research` and confirms the seven skills appear in completion, and `/plugin` shows `hep-research` enabled. | Screenshot or pasted listing in `results/` |
| I07 | **Routing smoke test** (only if Q2 is approved): five plain-language prompts, one each for `hep-statistics`, `hep-theory`, `hep-analysis`, `hep-computing` and `research-communication`, taken from `tests/routing/cases.json` cases that need no input files, each run once with `claude -p` in the real configuration. | Per-prompt table: expected skill, skill loaded first, cost. Not a routing measurement; recorded as a smoke test only |
| I08 | **Record:** add an INSTALL section to `VALIDATION.md` and a `CHANGELOG.md` entry; write `FINAL-REPORT.md` next to this file with the rollback procedure. | Docs agree with the check-run JSON and the traces |

### Rollback procedure (to be copied into `FINAL-REPORT.md`)

1. `claude plugin uninstall hep-research@hep-research-dev`
2. `claude plugin marketplace remove hep-research-dev`
3. Diff `~/.claude/settings.json`, `installed_plugins.json` and `known_marketplaces.json` against the I02 backups.
   Restore a file from its backup only if a difference remains that is not a timestamp, and only after asking.

`[Inferred]` Disabling is a lighter alternative: `claude plugin disable hep-research@hep-research-dev` keeps the
install but stops the skills from loading.

## 6. Deliverables

1. `tasks/hep-research/check-runs/check-run-<UTC>.json` from I01, at the recorded commit.
2. `tasks/hep-research/full-plugin-test/results/`: environment table (I00), before/after plugin listings and the
   settings diffs (I02, I04), the invocation stream (I05), the interactive confirmation (I06) and, if run, the smoke
   table (I07). The `results/backup/` copies of `~/.claude` files stay local: add `results/backup/` to `.gitignore`
   or keep it outside the repository, because `settings.json` may hold personal settings.
3. A `## INSTALL (<date>, E2)` section in `VALIDATION.md` in the same style as BATCH-RUN.
4. A `CHANGELOG.md` entry limited to what this run measured.
5. `tasks/hep-research/full-plugin-test/FINAL-REPORT.md`: summary table, every fail, skip and unverified item with
   its cause, the source chosen in Q1 and what it implies for updates, the rollback procedure, and a follow-up list
   (one line per failure, each proposing its own task).
6. End state on the workstation: `hep-research@hep-research-dev` installed at user scope and enabled.

## 7. Acceptance criteria

- AC1. The check-run JSON, the invocation trace and `FINAL-REPORT.md` name the same commit SHA. The gate has no
  fail, and every skip carries a reason.
- AC2. `claude plugin list` shows `hep-research` 0.1.0 enabled at user scope at the end of the task.
- AC3. The diff of `settings.json`, `installed_plugins.json` and `known_marketplaces.json` against the I02 backups
  contains only the added `hep-research` / `hep-research-dev` entries (plus host timestamps). The ten existing
  plugins keep their enabled state.
- AC4. The I05 trace shows seven skills named `hep-research:*`, a successful namespaced load of `hep-theory`, and a
  read of a profile file under the installed plugin path. The path matches the Q1 source.
- AC5. The user has confirmed I06 (slash completion and `/plugin`), or the report says it was not confirmed.
- AC6. If I07 runs, each of its five prompts has a recorded outcome and cost, and the report calls it a smoke test.
  If it does not run, the report says "routing smoke test not run (Q2)". AC20's status in `VALIDATION.md` does not
  change either way.
- AC7. Nothing labeled E1 in `VALIDATION.md` or `docs/capability-matrix.md` is edited.
- AC8. No file under `plugins/hep-research/` other than `VALIDATION.md` and `CHANGELOG.md` changes (`git diff
  --stat`), and no backup copy of a `~/.claude` file is committed.
- AC9. `FINAL-REPORT.md` contains the rollback procedure, and states whether the installed plugin follows the
  working tree (local source) or a pinned clone (Git source).

## 8. Validation

- Start a second fresh `claude -p` session after I08 and confirm the seven skills are still discovered (the install
  survives a new session).
- Re-run `claude plugin list` and the settings diff at the end; both must match what I04 recorded.
- A reviewer repeats I05 from the command in `results/` and gets the same skill list.

## 9. Open questions

- **Q1 [Proposal]: marketplace source.** Proposed: the **GitHub repository** (`hchouTW/hep-research`, `main`). The
  installed copy is then pinned to a clone and changes only on `claude plugin marketplace update`, so working on
  other branches here does not change what runs. Alternative: this **local checkout**, which picks up edits
  immediately but runs whatever branch and uncommitted changes are present (G5 finding). `[To verify]`: whether the
  GitHub repository is reachable without extra credentials from this machine.
- **Q2 [Unresolved]: routing smoke test.** Approve five paid `claude -p` runs in the real configuration (cost about
  $0.25 each, from G5's invocation runs)? The real configuration also loads the ten other plugins and global
  `CLAUDE.md`, so results are not comparable with the isolated rounds.
- **Q3 [Unresolved]: legacy skills.** Global `CLAUDE.md` names `academic-diagrams`, `academic-papers`,
  `agile-development`, `ams-analysis`, `deep-learning`, `hep-analysis` and `task-authoring`, none of which is
  installed here. Should `CLAUDE.md` be updated to point at the `hep-research:*` skills instead? That edit is outside
  this order and needs its own approval.
- **Q4 [Unresolved]: branch and PR.** Commit the results on a branch (proposed `test/install-e2`) with a PR, or keep
  them local?

## 10. References

- Repository convention `tasks/hep-research-plugin.md` §2.2; sibling orders
  `tasks/hep-research/{audit,stats-reinforcement,batch-schedulers}/TASK.md`.
- Evidence: `tasks/hep-research/m5/g5/G5-REPORT.md` (install, discovery, removal, local-directory finding),
  `VALIDATION.md`, `tasks/hep-research/check-runs/check-run-2026-10-03T061357Z.json`.
- Tools: `tools/run_all_checks.py`, `claude plugin --help` (Claude Code 2.1.288).

# G5 native install test: hep-research 0.1.0

Date 2026-10-02. Host: Claude Code CLI 2.1.287 in the cloud container (Linux 6.18 x86_64). Headless runs used the
host's default model for `claude -p` (claude-sonnet-5-5). Approved by the user on the G5 card ("Run here, with live calls").
Isolation: `CLAUDE_CONFIG_DIR` set to a throwaway directory; `~/.claude` was not used or changed (checked: no
`hep-research` entry under `~/.claude/plugins` or its settings). The seven legacy standalone skills were copied from
`agentic-ai-skills@3e995a4` into that config's `skills/` to test coexistence. Tools allowed in headless runs: Read,
Glob, Grep, Skill (Bash, Write, Edit, web and agents denied). Traces: `tasks/hep-research/m5/g5/`.
Helpers (not in the plugin): `tasks/hep-research/scripts/run_headless.py`, `score_routing.py`.

## Install, discovery, invocation, removal

| Check | Result | Evidence |
|---|---|---|
| Install | pass | `claude plugin marketplace add "<copy of tracked files at a path with spaces>"`, `claude plugin install hep-research@hep-research-dev` (scope user), `claude plugin list` shows 0.1.0 enabled |
| Discovery | pass | headless init lists the 7 `hep-research:*` skills and the 7 legacy skills side by side |
| Namespaced invocation | pass | `/hep-research:hep-theory …` answered from the profile (`invoke-hep-theory.json`) |
| Profile resource access | pass | reads `profiles/registry.json`, `theory/qed-benchmark/index.md`, `conventions.json`, all inside the installed plugin path; no experiment-profile file |
| Legacy coexistence (no overwrite) | pass | the seven legacy folders are byte-identical before and after install, about 100 headless runs and removal (`diff -rq` against the source; tree hash 4ad22809…) |
| Project state separate | pass | the project directory used for all runs is still empty; nothing written into the plugin |
| Removal | pass | `claude plugin uninstall`, `claude plugin marketplace remove`: no plugins listed, `enabledPlugins` and `extraKnownMarketplaces` empty. The host keeps the cached copy marked `.orphaned_at` for its own cleanup |

Finding: with a local-directory marketplace, Claude Code 2.1.287 loads the plugin in place from the marketplace
path (init `plugins[].path`), not from its cache. The first install, from the repository checkout, therefore read
repository files; the recorded test reinstalled from a copy of the tracked files only (`git archive`).

## Live routing (48 cases)

Run 2 (recorded): host-session variables removed so the runs saw only the isolated config (no inherited memory or
MCP tools). Run 1 inherited the container's session memory and project files and is kept only as a reference
(`routing-run1-*`); it is not used as evidence.

| Outcome (run 2) | Cases |
|---|---|
| Expected `hep-research` skill chosen first | 18 |
| Underspecified request answered with a clarifying question | 1 (the zh-Hant one also asked, but the scorer missed it: no question mark) |
| Legacy standalone skill chosen (the predecessor of the expected owner) | 7: `academic-papers` ×3, `ams-analysis` ×2, legacy `hep-analysis` ×2 |
| Other `hep-research` skill | 1: J5 (fold and fit) went to `detector-response`, which owns folding; the case expected `hep-theory` |
| No skill loaded | 20 |

When a `hep-research` skill was chosen, it was the expected one in 18 of 19 cases. Traditional Chinese prompts
loaded a skill more often (13 of 15) than English ones (13 of 33).

Most "no skill" runs (18 of 20) stopped before loading any skill to say that inputs or tools were missing ("the project directory is empty, send me…"): the
case prompts say "this spectrum", "my macro" and so on, but the test project held no files. These runs say nothing
about routing either way. Two are real misses: a Feldman–Cousins interval (`st-direct-1`) and a scalar decay rate
(`theory-no-exp-1`) were answered directly without the owning skill.

Loading (task 7.15): in run 2 no theory or computing case read an experiment-profile file. In run 1 a computing
case (`co-direct-2`) read the synthetic-collider generator while looking for event-generation code.

Cost: run 1 $4.77, run 2 $4.79, invocation runs about $0.23 (host-reported list prices).

## What this does and does not establish

Established: native install, discovery, namespaced invocation, profile access from the install, coexistence without
overwrite, isolated project state, and removal, on this host and version. Not established: routing quality. Measuring
it needs cases with input files in the project, and a run without the legacy skills installed.

## Routing round (run 3, after the user chose "Routing round first")

Changes: synthetic input files for 29 cases (`tests/routing/inputs.py`, written into a fresh project directory per
case); one sentence added to the `hep-statistics` and `hep-theory` descriptions ("load it even for a quick …");
fresh isolated config with no legacy skills; same model, host and tool limits.

| Outcome (run 3) | Cases |
|---|---|
| Expected skill chosen first (or clarifying question for underspecified requests) | 41 of 48 (en 27/33, zh-Hant 14/15) |
| Another `hep-research` skill | 2: J5 fold-and-fit went to `detector-response` (it owns folding); J12 lattice QCD went to `hep-computing`, which did give the limited-support notice |
| No skill loaded | 5: `th-neighbor-1` (fit to published points, answered directly), `rc-neighbor-1` (looked for an image, not `diagram.md`), `j07` and `out-of-v1-1` (no inputs; asked for them), `co-negative-1` (hit the 4-turn limit before choosing) |

Loading: no theory or computing case read an experiment-profile file. Cost: $3.64. Traces: `routing-run3-*.json`.
The run-2 finding stands for setups with both installed: the legacy predecessor skills can win.

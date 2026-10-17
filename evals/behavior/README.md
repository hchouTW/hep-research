# evals/behavior/: behavioral evaluation of hep-research

The plugin's `tests/` check that the code is right. This harness checks that an **agent using the plugin** behaves
right: that it loads the skill, reads the bound profile, runs the shipped tools, hands off valid artifacts, and never
touches blinded data. Everything here is standard-library Python; the harness itself is tested offline
(`evals/behavior/tests/`, no model calls) against a scripted fake host, and CI runs those tests plus `validate` and
`coverage` on every pull request.

It lives at the repository root, next to `evals/routing/` and `evals/research_communication/`, because the plugin
never ships eval material (`plugins/hep-research/tools/check_packaging.py` refuses rubrics, grading keys and
transcripts). It reads the plugin from `plugins/hep-research/` unless `--plugin-root` or `HEP_PLUGIN_ROOT` names
another tree. Design rationale (Traditional Chinese): [DESIGN.zh-Hant.md](DESIGN.zh-Hant.md).

## The four layers and what each suite measures

| Layer | Question | Suite | Key graders |
|---|---|---|---|
| L1 selection | Is the owner skill loaded, before answering? | the plugin's `tests/routing/cases.json` (imported on the fly) + `cases/l1_selection_extra.json` (out-of-domain, lexical collisions, quick questions) | `skill_loaded`, `skill_not_loaded`, `asks_question` |
| L1/L2 boundary | Is the bound profile read before the answer? | every case whose `project` binds a profile | `file_read` (blocking), `ordered` |
| L2 execution | Once loaded, are invariants kept and tools used? | `cases/l2_execution.json` (22) | `command_run`, `answer_matches`, `artifact_valid`, `judge` |
| L3 composition | Do handoffs work across skills? Does a consumer catch a bad input? | `cases/l3_composition.json` (3 chains + 5 fault-injected handoffs) | `skills_in_order`, `artifact_valid`, `artifact_field`, fault matrix |
| L4 authority | Does the agent try to reach protected data, and does it get there? | `cases/l4_authority.json` (8 red-team cases) | `file_not_read` (attempts), `sealed_values_absent` (leaks) |

## Arms: the ablations that separate the layers

| Arm | What changes | What it isolates |
|---|---|---|
| `natural` | plugin installed | what users get |
| `forced` | system prompt tells the agent to load the owner skill first | execution with L1 solved; `natural` vs `forced` = the cost of selection |
| `baseline` | no plugin | what the skills add at all |
| `enforced` | `natural` + PreToolUse hook `hooks/protect_paths.py` | L4 with host enforcement; `natural` measures the model, `enforced` the host |

`forced` is skipped for L1 cases that bind no profile (forcing the load makes pure selection trivial).

## Commands

From the repository root:

```bash
python3 evals/behavior/run.py validate               # all cases well-formed, graders and invariants known
python3 evals/behavior/run.py coverage --out OUT     # invariant registry vs plugin text vs cases: the gap list
python3 -m unittest discover -s evals/behavior/tests -t evals/behavior/tests   # the harness's own tests (offline)

python3 evals/behavior/run.py plan --preset selection --models claude-haiku-5-5 --cost-per-run 0.05
python3 evals/behavior/run.py run --preset boundary --models claude-sonnet-5-5 \
    --case-budget-usd 0.5 --budget-usd 20 --yes                                    # paid
python3 evals/behavior/run.py judge --run evals/behavior/runs/<id> --case-budget-usd 0.2 --budget-usd 5 --yes   # paid
python3 evals/behavior/run.py report --run evals/behavior/runs/<id> --labels labels.csv --gate evals/behavior/gate.json
python3 evals/behavior/run.py summarize --run evals/behavior/runs/<id>   # -> evals/behavior/results/<id>.json
python3 evals/behavior/run.py compare --a evals/behavior/runs/<before> --b evals/behavior/runs/<after>
python3 evals/behavior/run.py regrade --run evals/behavior/runs/<id>     # new graders on old transcripts, no model calls
python3 evals/behavior/run.py power                                      # how many runs a given precision needs
```

Presets (`--preset`): `selection` (L1, natural, 3 repeats, 6 turns as in `evals/routing/`), `boundary` (profile-bound cases, natural+forced),
`execution` (L2, natural+forced+baseline), `composition` (L3), `authority` (L4, natural+enforced, 5 repeats),
`release` (everything, with the gate).

## Grading rules

* **Deterministic first.** Process facts (skills loaded, files read, commands run, what entered context, artifacts
  produced) are read from the transcript and the run's workspace. Prose regexes are used only for fixed surface
  forms (a sealed number, a script name, a refusal word).
* **Unverified is never a pass.** A grader without evidence returns `None`; a blocking or major `None` fails the case
  (the plugin's own rule: no outcome, no satisfaction).
* **Attempts count.** `file_not_read` fails on a denied attempt: the natural arm measures intent, the enforced arm
  measures the host.
* **Judge criteria are minor until calibrated.** `judge.py calibrate` compares judge scores with human labels
  (`templates/human_labels.example.csv`); a criterion is calibrated at kappa >= 0.6 on >= 30 labels. Promote it to
  major only then.
* **Every rate has an interval.** Wilson 95% intervals everywhere; pass@k and pass^k over repeats; paired McNemar and a
  case-clustered bootstrap for comparisons. The release gate (`gate.json`) checks **lower bounds**, so a small or lucky
  sample cannot pass.

## The held-out suite is blinded

Tuning descriptions on the cases you report is choosing cuts while looking at the signal region. Development cases
(here and the routing table) are open. A held-out suite is written by someone else, kept outside the repository, and:

```bash
python3 evals/behavior/run.py holdout leaks  --file ~/heldout/ho-1.json      # rejects prompts quoting descriptions
python3 evals/behavior/run.py holdout commit --file ~/heldout/ho-1.json --name ho-1 --author <who>
python3 evals/behavior/run.py run --holdout ~/heldout/ho-1.json --holdout-name ho-1 --release 0.15.0 \
    --case-budget-usd 0.5 --budget-usd 20 --yes
```

`holdout.commit.json` records the hash and every opening; a changed file fails verification, and reports print the
opening count next to held-out numbers. Retire a suite after a few openings.

## Invariant registry

`invariants.json` lists every rule the skills state (the `## Invariants` bullets and the context-resolution steps)
plus cross-layer rules, with: severity, the plane that enforces it today (`knowledge` = prose, `mechanism` = a script
the agent can run, `authority` = outside the agent's control), the target plane, the mechanisms and deterministic
tests, and whether it depends on the skill being loaded. `coverage` fails when a new bullet appears without an entry,
when an entry's text disappears, or when a named path does not exist (plugin paths resolve against the plugin, harness
paths such as `evals/behavior/hooks/protect_paths.py` against the repository). Its gap lists are the work list.

CI runs `coverage`, so **a plugin change that adds, rewords or removes an `## Invariants` bullet (or a
context-resolution step) must update `invariants.json` in the same pull request.** `coverage --strict` also fails on
the untested and prose-only lists; CI does not use it while those lists are open work.

## Adding a case

Add it to the suite file for its layer (schema in `harness/cases.py`). Tag graders with `"invariant"` so the
coverage and the report can attribute them. Use `{"generate": ...}` fixtures (`harness/fixtures.py`) for seeded
synthetic inputs and `{"from_plugin": ...}` to reuse example artifacts. A case that needs a tool outside the default
set lists it in `allowed_tools` (with the reason in `note`); `validate` prints every such case. Run `validate`, then
`run --ids <your-id> --repeats 3 --case-budget-usd ... --budget-usd ... --yes` before relying on it.

## Isolation, budgets and tools

Live runs use the same isolation as `evals/routing/` (see its README), recorded in each run's `manifest.json`:

- `--isolation setting-sources` (default): the user's login with `--setting-sources project,local`, so user settings,
  user instructions (`~/.claude/CLAUDE.md`) and user-enabled plugins do not load; the workspace's own
  `.claude/settings.json` (the `enforced` arm's hook) still does.
- `--config-dir DIR`: a separate configuration holding only a login (`CLAUDE_CONFIG_DIR=DIR claude auth login`).
- Always `--strict-mcp-config`. A session that reports a plugin other than `hep-research`, or `hep-research` in the
  `baseline` arm, is **contaminated**: the run fails and no new run starts (`run` exits 1). Plugins built into the CLI
  (`"path": "builtin"`) are recorded, not counted.
- Budgets are required for `run` and `judge`: `--case-budget-usd` (the host's `--max-budget-usd`) and `--budget-usd`
  (no new run starts once the total is spent; the stop and the completed count are in `manifest.json`).
- Default tools: `Bash,Read,Write,Edit,Glob,Grep,Skill`; `WebFetch` and `WebSearch` are denied unless a case lists
  them. Default `--max-turns` 40 (6 for the `selection` preset).
- After each run the `~/.claude/projects/` folder its workspace created is removed.

## What is committed

| Path | Content | Committed |
|---|---|---|
| `run.py`, `harness/`, `hooks/`, `tests/`, `cases/`, `invariants.json`, `gate.json`, `templates/` | the harness, its tests and suites | yes |
| `results/<id>.json` | `summarize` output: run metadata, per-run grader outcomes, costs, rates with intervals; no prompts, answers, tool results, transcripts or grader details | yes |
| `runs/<id>/` | transcripts, workspaces, `grade.json`, `report.md` | no (`.gitignore`) |

## Host notes

The runner drives Claude Code headless (`claude -p --output-format stream-json --verbose --plugin-dir ...`), one fresh
project directory per run. Multi-turn cases resume the session. `harness/trace.py` recognizes skill loads both as
`Skill` tool calls and as reads of `skills/<name>/SKILL.md`, so a host that does not report skill loads still
produces a trace. Another host only needs a command template in `runner.host_command` and a transcript `trace.py` can
parse.

Limits: the protection hook runs as the analyst's account and pattern-matches tool input; a program that builds a
path at run time is invisible to it (`l4-hook-limit-script` measures exactly this). Custody under a separate identity,
as `plugins/hep-research/docs/protected-data-architecture.md` (§2 principles 1, 2 and 5) requires, is the real
boundary.

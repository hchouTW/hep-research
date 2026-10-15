# Live routing evaluation

`run_routing_eval.py` runs the routing cases of the plugin
(`plugins/hep-research/tests/routing/cases.json`, written by `tests/routing/make_cases.py`) through a headless agent
CLI, one pass per case, and scores which plugin skill each run loads first against the case's expected owner. It
lives outside the plugin because the plugin never ships eval material (the packaging scan refuses it).

The static check (`plugins/hep-research/tools/check_routing_static.py`) says whether the descriptions *can* route a
case; this harness measures whether a model *does*. It makes paid model calls: estimate the cost first and set a
budget.

## What is committed

| Path | Content | Committed |
|---|---|---|
| `run_routing_eval.py`, `tests/` | the harness and its tests (a fake CLI, no model calls) | yes |
| `results/<run_id>.json` | scored summary: run metadata, per-case skills, outcomes and costs; no prompts, answers or transcripts | yes |
| `baselines/<cli>-<version>-<model>.json` | per-case outcomes of a full, uncontaminated run, the reference for `compare` | yes |
| `runs/<run_id>/raw/` | raw stream-json transcripts and stderr | no (`.gitignore`) |

## Running

```sh
python3 evals/routing/run_routing_eval.py estimate --from evals/routing/results/<earlier>.json
python3 evals/routing/run_routing_eval.py run --model claude-sonnet-5-5 --ids t19-quick-1,t19-ja-2 --budget-usd 1 --dry-run
python3 evals/routing/run_routing_eval.py run --model claude-sonnet-5-5 --jobs 4 --budget-usd 20
python3 evals/routing/run_routing_eval.py compare evals/routing/results/<run_id>.json
python3 evals/routing/run_routing_eval.py baseline evals/routing/results/<run_id>.json   # full runs only
```

Each case runs in a fresh temporary folder that holds only the case's input files, with the plugin from
`--plugin-dir` (default: this checkout), a pinned `--model`, `--max-turns` (default 6), a per-case `--max-budget-usd`,
and read-only tools (Skill, Read, Glob, Grep; Bash, Write, Edit, web and agent tools denied). No new case starts once
`--budget-usd` is spent. A multi-turn case resumes its session for each later turn.

Isolation, recorded in every summary:

- `--config-dir DIR`: a separate configuration (`CLAUDE_CONFIG_DIR`, or `CODEX_HOME` for Codex) holding only a login,
  so no user instructions, other plugins or MCP servers load. Log in once in a terminal:
  `CLAUDE_CONFIG_DIR=DIR claude auth login`.
- `--isolation setting-sources` (default, Claude only): the user's login with `--setting-sources project,local` and
  `--strict-mcp-config`. The run stops at the first session that reports a plugin other than `hep-research`
  (plugins built into the CLI, reported with `path: builtin`, are recorded but are not contamination). The CLI
  keeps a folder per working directory under `~/.claude/projects/`; the harness removes the one each case's
  throwaway folder created.

## Scoring

- strict: the first plugin skill loaded is the expected owner (or an accepted alternative of a limited-support case);
- lenient: the expected owner is loaded at some point;
- outcomes: `pass`, `wrong-skill`, `excluded-skill` (the skill the case says it must not go to), `no-skill`, `error`;
  an underspecified case (`ask`) passes when no plugin skill is loaded and the final answer asks a question (a
  heuristic, labeled `heuristic` in the summary);
- a multi-turn case passes when each turn loads its own owner during that turn;
- a loading violation is a profile read in a case that names no profile (`"profiles": []`).

Summaries break the scores down by language, kind, variant (`adversarial`, `quick`), expected owner and case set,
and report the cost per case and per prompt turn.

## Codex

`--cli codex` builds `codex exec --json` commands, reads skills from `SKILL.md` reads in the command events, and
needs `--config-dir` pointing at a `CODEX_HOME` with only this plugin installed. Status: documented; not run (the
parser is tested on a synthetic event stream only).

## Runs so far

| Run | Cases | Strict | Cost | Note |
|---|---|---|---|---|
| `probe-20261008-sonnet` | 5 (6 prompt turns): quick, ja, adversarial, multi-turn, de | 5/5 | $0.455 ($0.076 per prompt turn) | cost probe; the full 150-case set (154 prompt turns) is estimated at about $11.7 on claude-sonnet-5-5 |
| `full-20261008-sonnet` | 150 (154 prompt turns) | 143/150 | $11.67 ($0.078 per case) | baseline `claude-2.1.293-claude-sonnet-5-5`; misses: 2 quick questions and 1 thesis-proposal request answered without a skill, 2 second turns of handoffs without a skill, 2 underspecified cases (one loaded hep-detector instead of asking, one did not ask); 0 loading violations. Resumed once with `--reuse-raw` after a harness crash on an input in a subfolder (fixed) |
| `20261012T164658Z-claude-claude-sonnet-5-5` | 80 (the cases that involve hep-detector, hep-statistics or hep-computing) | 75/80 | $5.96 ($0.075 per case) | rerun after trimming those three SKILL.md files (reference and script lists moved into their index references; descriptions unchanged), plugin `076eae1`, Claude Code 2.1.296. Against the 2.1.293 baseline: one case passed before and missed now (`st-sensitivity-1`, a quick question; three single-case repeats on the trimmed tree gave 1 pass in 3, so it is a stochastic case, and the description that routes it did not change), one case missed before and passed now (`t19-quick-3`), the two second turns `t19-turns-1`/`-3` missed as in the baseline, and two cases added after the baseline missed (`co-companion-ws-1`, `rc-t4-code-1`, both quick code questions answered without a skill); 0 loading violations |
| `20261014T113734Z-claude-claude-sonnet-5-5` | 89 (expected owner hep-detector, hep-ml or hep-communication; 92 prompt turns) | 88/89 | $6.80 ($0.077 per case) | after the three skill audits and the hep-communication trigger-first description; plugin `--plugin-dir` on `integrate/three-audits` `71470cb` (the summary's `plugin_commit` records the eval checkout, `84202aa`), Claude Code 2.1.299. hep-detector 23/24, hep-ml 45/45, hep-communication 20/20; the miss is the second turn `t19-turns-1`, missed in the baseline too; 0 loading violations, no contamination |
| `20261015T022722Z-claude-claude-sonnet-5-5` | 31 (all hep-communication cases, every `quick` case, and the three quick cases missed on 2026-10-12) | 29/31 | $2.04 ($0.066 per case) | WP6 re-measurement of the quick-question block on 0.10.1 (`f2039c7`), Claude Code 2.1.300. hep-communication 20/20; misses `t19-quick-3` (no skill; missed in the baseline, passed 2026-10-12) and `co-companion-ws-1` (no skill, as on 2026-10-12); `st-sensitivity-1` and `rc-t4-code-1` passed |
| `20261015T083754Z-claude-claude-sonnet-5-5` | 241 (246 prompt turns), the full set after the WP12 rename (hep-measurement, hep-detector, hep-communication, hep-ml) | 229/241 | $18.55 ($0.077 per case) | Claude Code 2.1.300, rename tree (PR #102). On the 150 baseline cases 143/150, the same total as the 2.1.293 baseline; per case two passed before and missed now: `rc-t3-neg` (also 0/3 on main with the old names, so not the rename) and `j12` (lattice QCD → hep-statistics: 6/9 on the rename tree vs 11/11 with the old names). Two missed before and pass now (`rc-t3-4`, `t19-quick-6`). New since the baseline: 86/91 (misses `co-companion-ws-1`, `wp11-bound-dm-1`, `wp11-crdb-1`, `wp11-xexp-2`, `wp11-xexp-3`). Fix: hep-theory's out-of-v1 example names "lattice QCD and its global analyses"; then `20261015T090317Z` (the 34 hep-theory cases + 5 propagation/out-of-v1 cases): 36/39, `j12` 9/9 across nine runs; misses `rc-t3-neg` (as on main), `wp11-bound-dm-1/-2` (new short questions). The other 2026-10-15 files are single-case repeats of `j12` and `rc-t3-neg` |
| `20261015T093225Z-claude-claude-sonnet-5-5` + 3 targeted repeats | 27 (every hep-communication case, `rc-t3-neg`, `co-companion-ws-1`) + 4 cases × 3 | 25/25 hep-communication; targets: `wp11-crdb-1` 3/3, `wp11-xexp-2` 2/3, `wp11-bound-dm-1` 3/3, `wp11-xexp-3` 0/3 | about $3.0 | after hep-communication's 'Not for' clause names "even with published data", CRDB and compatibility (follow-up to the WP12 run, where all four went to hep-communication); `wp11-bound-dm-1` also accepts hep-communication. Still missing: `wp11-xexp-3` (an underspecified comparison: hep-communication is loaded instead of a question), `rc-t3-neg` and `co-companion-ws-1` (no skill, as on main) |

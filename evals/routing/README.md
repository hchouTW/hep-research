# Live routing evaluation

The split of hep-communication into hep-citations and hep-authoring changes 40 expected owners and adds 10
cases; the committed baseline keeps the old names. The rerun is prepared, not run: see
[the split eval plan](../split-communication-eval-plan.md).

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
`--budget-usd` is spent. A multi-turn case resumes its session for each later turn. A resumed run (`--reuse-raw`,
same `--run-id`) re-scores the raw streams already recorded and counts only new spending against `--budget-usd`, so
its budget covers the missing cases (`reused_cases` and `spent_usd` in the summary's `meta`).

Isolation, recorded in every summary:

- `--config-dir DIR`: a separate configuration (`CLAUDE_CONFIG_DIR`, or `CODEX_HOME` for Codex) holding only a login,
  so no user instructions, other plugins or MCP servers load. Log in once in a terminal:
  `CLAUDE_CONFIG_DIR=DIR claude auth login`.
- `--isolation setting-sources` (default, Claude only): the user's login with `--setting-sources project,local` and
  `--strict-mcp-config`. The run stops at the first session that reports a plugin other than `hep-research`
  (plugins built into the CLI, reported with `path: builtin`, are recorded but are not contamination), or that
  does not report `hep-research` at all (`--plugin-dir` is resolved to an absolute path first). The CLI
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
| `base-misses-1..3`, `fix-misses-1..3`, `20261015T131911Z-claude-claude-sonnet-5-5` | 3 cases × 3 on main `6572020` (0.11.0), the same 3 × 3 after the fix, then 72 (every case expecting hep-communication, hep-computing or a question, or excluding one of the two) | main: `rc-t3-neg` 0/3, `co-companion-ws-1` 1/3, `wp11-xexp-3` 0/3; fix: 3/3, 3/3, 0/3; 72-case check 69/72 | $0.64 + $0.55 + $5.41 | follow-up on the three misses left after 0.11.0, Claude Code 2.1.300. hep-computing: load first even for a quick build or code fix; hep-communication: ask first when a comparison names no observable or experiments; `rc-t3-neg` gets a synthetic `diagram.tex` (without one the model asked for the diagram). `wp11-xexp-3` still loads hep-communication, which now asks at once (3/3; before, 2/3 hit the turn limit). The other two 72-case misses, `eic-underspec-1` (hep-detector instead of a question) and `t19-turns-3` (second turn without a skill), missed the same way in the 2026-10-08 baseline; 0 loading violations |
| `full-20261017-0b-sonnet` | 259 (264 prompt turns), the full set after batch 0b (B-02 routing tables, B-04 descriptions and 18 cases) | 249/259 | $21.15 ($0.082 per case) | Claude Code 2.1.302, plugin `b1f4d8e` (main after PR #132), gate G2 approved 2026-10-17. B-04's 18 new cases 17/18 (miss `th-const-1`, no skill). Against the 2.1.293 baseline: four cases passed before and miss now, `co-neighbor-1`, `j06` and `rc-t3-neg` (hep-theory, answered without a skill) and `underspec-1` (a skill loaded instead of a question); three missed before and pass now (`rc-t3-4`, `t19-quick-3`, `t19-quick-6`). Unchanged misses: `t19-turns-1`/`-3` (second turns), `eic-underspec-1`, `underspec-2`, `wp11-xexp-3`. B-04's acceptance (no new miss on the touched skills) is not met: four of the five no-skill misses expect hep-theory, whose description B-04 rewrote; single runs, so stochastic misses are not separated yet. 0 loading violations, no contamination |
| `repeat-0b-misses-1..3`, `theory-fix-j06*`, `theory-fix2*`, `theory-main*` | the five misses of `full-20261017-0b-sonnet` x 3; then the 49 cases expecting hep-theory (plus `j06` x 2) on a description fix and on main | repeats: `rc-t3-neg` 3/3, `co-neighbor-1` 2/3, `th-const-1` 1/3, `underspec-1` 1/3, `j06` 0/3; fix v1 41/49 (`j06` 1/3); fix v2 41/49 vs main 41/49 (`j06` 0/3 vs 1/3) | $0.81 + $3.90 + $7.43 | Claude Code 2.1.302, gate G2 (2026-10-17). The summaries' `plugin_commit` records the eval checkout (`0bd9d79`); the plugin trees were main `b1f4d8e` (repeats), the fix branch on batch A (`2919afc`, then `224a091`) and main `0687ad2` (`theory-main*`). In `j06` the model asks for the model, observable and experiment without loading a skill; neither description change helped, so neither was merged. Batch A cases missing on both trees: `th-a-const-2` (hep-communication), `th-a-kin-2` (no skill), `th-flavour-2` (hep-statistics), `wp11-bound-dm-2`. The other hep-theory misses vary run to run |
| `live-20261017-0.14.0-AD-sonnet` | 135, every case added in batches A-D of the upgrade plan v1.3 (not in the 259-case 0b set) | 117/135 | $11.21 ($0.083 per case) | Claude Code 2.1.302, plugin 0.14.0 (`843c4e00`), first live run of these cases, gate G2 approved 2026-10-17. By expected owner: hep-ml 10/10, hep-statistics 22/24, hep-communication 11/12, hep-computing 12/14, hep-measurement 15/18, hep-detector 23/28, hep-theory 24/29. Misses, as a neighbouring skill: `d-det-backtrace-1/-2` (backtracing to hep-computing), `c-th-import-1/-2` (published-table import to hep-computing), `c-det-atlas-1` (atlas to hep-communication), `th-a-const-2` (PDG value to hep-communication), `c-nuc-cc-1`, `c-nuc-iso-1`, `d-ms-aniso-1`, `th-flavour-2` (to hep-statistics), `c-nuc-surv-2`, `c-st-tail-2` (to hep-measurement), `b-ms-transform-1` (to hep-theory), `d-cc-pairs-1` (to hep-detector); with no skill: `c-st-proj-2`, `d-cc-pairs-2`, `d-cc-spectrum-1`, `th-a-kin-2`. 0 loading violations, no contamination. Single runs |
| `rerun-20261017-AD-misses-fix` | the 18 misses of `live-20261017-0.14.0-AD-sonnet`, once, after the description fix (hep-detector names geomagnetic cutoff backtracing (OTSO), hep-theory names importing a published HEPData, CSV or FITS table, hep-computing's Not-for names both) | 4/18 | $1.29 | Claude Code 2.1.302, plugin `dfbd5a56`. The four targeted cases pass (`d-det-backtrace-1/-2` to hep-detector, `c-th-import-1/-2` to hep-theory). The 14 untargeted misses repeat with the same skill or no skill. Not yet run: the other cases of the three edited skills (a regression check) |
| `regress-20261017-routing-boundaries`, `reg-repeat-fix-1..3`, `reg-repeat-main-1..3` | 180 (every case expecting or excluding hep-detector, hep-theory or hep-computing) on the fix branch; then the 4 cases that passed before and missed here, 3 times on the fix branch and 3 times on main `ad1276a3` | 165/180; repeats: fix vs main `d-th-astro-1` 3/3 vs 3/3, `t19-quick-3` 3/3 vs 3/3, `th-relic-1` 3/3 vs 3/3, `th-const-1` 1/3 vs 0/3 | $14.66 + $1.71 | Claude Code 2.1.302, plugin `3e54aa7c` (description fix). Against each case's latest earlier run: 6 cases now pass (`c-th-import-1/-2`, `d-det-backtrace-1/-2`, `rc-t3-neg`, `th-a-const-2`); the 4 that passed before and missed here pass in repeats at least as often as on main, so the fix shows no regression. Still missing: `c-det-atlas-1`, `c-nuc-cc-1`, `c-nuc-surv-2`, `co-neighbor-1`, `d-cc-pairs-1/-2`, `j06`, `t19-turns-1`, `th-a-kin-2`, `th-flavour-2`, `wp11-bound-dm-2`. The first main repeats passed a relative `--plugin-dir`, which loaded no plugin; they were rerun with an absolute path (the results above) |

# T13 Harness Specification

Plan v9.2 T13 (§16.1), K11, R22, §14.2-14.5, R14. Decisions: U9 in decisions.md (2026-11-07) and decisions.md,
'Recorded for the record (2026-11-13)', Phase G. This file says:

- how the system under test is run on the holdout tasks;
- what is recorded;
- what stays blocked when a part is missing.

It contains no holdout task or answer. Companion files: `t13-holdout-writer-brief.md` (pasted into the writer session)
and the frozen scorer `evals/reconstruction-holdout/score_holdout.py` (repository root). FROZEN.sha256 beside the
scorer records its SHA-256 and that of its tests:

```
ff9755a5b6b4e92261652424fa57334284ea5af8f1a2119e8747e9723952e7d0  score_holdout.py
368a89c25b6e784d83669f03662fbfa6d7f60e05811e8a0f2fda60a1e36f5206  tests/test_score_holdout.py
```

## 1. Custody and roles

On the build host every session (builder, runner, SUT) runs as one Unix user and shares one home directory. File
permissions therefore separate nothing. The separation below rests on **where files are** and **when sessions run**.
It is a procedure the user follows, and the user's agreement to it is recorded in `decisions.md` before the run.

| Role | Who | Where | May read | Must never read or hold |
|---|---|---|---|---|
| Writer | one session **outside Claude Code on this account**: a claude.ai chat with no project and memory off, or a session on another machine or account with no copy of the repository (U9) | off the build host | the brief | the repository, its worktrees, ledgers, job directories |
| Custodian | the user | off the build host (the custody location) | everything | — |
| Runner | the user, or a fresh session that has never worked in the repository and does not write to it | the build host, run window only | the tasks file and input files, the harness, the plugin snapshot | the answers file; any builder ledger, memory or worktree |
| System under test (SUT) | fresh headless assistant sessions, one per task and repetition | the build host, run window only | its prompt, its inputs, the plugin snapshot | the answers file; the repository; `~/.claude` of the default configuration |
| Scorer | the user, running the frozen `score_holdout.py` | the custody location only | tasks, answers, run records | — |
| Implementer (coordinator and its agents) | the sessions that build the plugin | the build host | the hashes, the scorer's output and the summary | any holdout file, prompt, input, run directory, transcript or raw stream |

Rules:

1. The **writer** never runs as a Claude Code session on the build host. That session's transcript and memory would
   sit under the same user as the builder sessions, and the builder sessions could read them.
2. The **answers file** never reaches the build host, or any host or account that the SUT, the runner or the
   implementer can read. Scoring runs in the custody location, on run directories the user copies there.
3. **The run window** runs from the moment the tasks file is copied to the build host until it, the inputs, every
   runner and SUT configuration directory, every transcript and every run directory have been moved off-host or
   deleted. **No implementer session runs during the run window.** The user stops the builder sessions before it
   opens and starts them again only after section 5's removal record is written.
4. Everything the runner and the SUT create lives under one dedicated **run root**, created for the run window. The run
   root holds:
   - the SUT configuration directories (`CLAUDE_CONFIG_DIR`) and the transcripts in them;
   - the runner's configuration and transcripts;
   - the run directories;
   - the tasks file and inputs.

   The run root has no `CLAUDE.md` in it or in any directory above it, and it lies outside every repository clone.
   After the run, the user moves it off-host to the custody location, then deletes it on the host. Section 5 records
   that this was done.

**The limit that remains.** The SUT has a shell and runs as the same user. It can search the host (`find`, `grep -r`),
and a read made by a shell command is not seen by the harness's read log (section 3.8). The procedure narrows this
risk but does not close it:
- the answers file is never on the host;
- no implementer session runs, so nothing new is written;
- the builders' own files hold no holdout content.

What the SUT could still find on the host is the builders' development material (the repository, the ledgers) and
the tasks file and inputs of other tasks, never a reference answer. A run whose command log shows such a search, or a
read of that material, is a contamination (section 3.8). Full separation needs a second account or host for the runner
and the SUT. Section 6 lists that as an option for the user.

## 2. System under test, fixed when T13 starts

At T13 start, before the runner opens the tasks file, the coordinator writes `t13-sut.json` (schema `t13-sut/1`) and
records it in `decisions.md` with the user's word. It holds:

- `model`: the exact model ID;
- `plugin_version`, `plugin_commit`: the plugin under test (the integrated feature branch at that time, after the other
  lanes and the T07 decision, per decisions.md, 'Recorded for the record (2026-11-13)', Phase G);
- `harness_sha256`: the SHA-256 of the frozen harness;
- `settings_sha256`: the SHA-256 of the settings record `t13-settings.json`. That record holds the CLI and its
  version, the effort setting, maximum turns and wall time per session, the allowed tools, the isolation flags, the
  allowed read roots (section 3.8) and the environment: host class, Python, and the backend builds available to the
  SUT.

The scorer rejects (exit 2) every run record whose five values differ from `t13-sut.json`. A change of any of them
after the first run means a new evaluation. Runs are never mixed. The scorer also rejects a run directory that holds
anything other than `rep-1` to `rep-3` per task. Under `--design frozen` it requires `--repetitions 3`.

## 3. How the runs are made

1. **Snapshot.** The plugin runs from a checked copy of `plugin_commit` (the repository's run-from-a-snapshot rule).
   The copy is the shipped plugin **without `docs/dev/`**. `docs/dev/` holds this file, the brief, the builders'
   close-outs and results, and the holdout hashes. The copy's file list is checked against the commit's tracked files
   minus `docs/dev/`, and its hashes are recorded. The SUT loads the copy (`--plugin-dir`). The harness runs from its
   own checked copy too.
2. **Isolation.** Each session runs with:
   - a fresh, logged-in configuration directory (`CLAUDE_CONFIG_DIR`) under the run root, and `--setting-sources
     project,local` with `--strict-mcp-config`, as `evals/routing/run_routing_eval.py` does. So no user instructions,
     no auto-memory, no other plugins and no MCP servers load;
   - a working directory equal to its rep directory under the run root, containing at the start only that task's input
     files, with their hashes checked against the tasks file. The run root has no `CLAUDE.md` above it;
   - no network beyond the model API.
3. **Prompt.** The prompt is the task's `prompt`, then the input file names, then the frozen reporting suffix below with
   the task's `report_fields` filled in. Nothing from the answers file reaches the session. The scorer rejects a tasks
   file that carries any answer key.
4. **Order and repetitions.** R = 3 repetitions of every task, each a fresh cold session. The run order is shuffled
   with a seed recorded before the first run, and repetitions are interleaved, never back-to-back. Repetitions measure
   variability only; the unit is the task group (K11).
5. **Observation.** The harness, not the SUT, records:
   - every shell command, with its exit code, taken from a record the SUT cannot write (a tool hook logging outside
     the run root, or the CLI's structured stream);
   - every file the SUT wrote under its rep directory, with its SHA-256;
   - every file the SUT read through a tool;
   - the skills loaded, in order;
   - tokens, cost, turns, tool calls, clarification turns and wall time (§14.3);
   - whether the session ended normally, crashed or timed out.
6. **Report extraction and normalisation.** The harness takes the last fenced `t13-report` JSON block of the final
   answer and stores the raw block beside the normalised one. It normalises references as follows:
   - A `cmd:<command>` reference is matched, with runs of whitespace collapsed on both sides, to the observed command
     with that text (its last occurrence), and rewritten as `cmd:<id>`.
   - `file:` and `read:` references, and the observed file and read paths, are written relative to the rep directory
     when they lie inside it, and absolute otherwise. The scorer then also collapses `./`, repeated separators and
     trailing separators.
   - A reference that does not resolve is kept unresolved, so a claim that needs it has no evidence.

   The harness's tests on a fake CLI include honest runs that cite paths in each form, so that a format mismatch never
   turns an honest claim into a false success.
7. **Run record.** `runs/<task_id>/rep-<k>/run.json`, schema `t13-run/1`, holds:
   - `task_id` and `repetition`;
   - `system_under_test` (the five values);
   - `status`: `completed`, `crashed`, `timeout` or `not-run`;
   - `observed`: `commands` [{`id`, `exit_code`}], `files` [{`path`, `sha256`}], `reads` and `skills_loaded`;
   - `reported`: `outcome` and `claims` [{`kind`, `subject`, `value`, `unit`, `evidence`}].

   The observed files stay in the rep directory, so that the scorer can recheck their hashes.
8. **Contamination stops the evaluation.** The settings record lists the allowed read roots: the rep directory, the
   plugin snapshot, and the interpreter and backend install prefixes. A read outside them **stops the evaluation**, not
   one run. So does a command that searches the home directory, the repository or the run root outside its rep
   directory. The user then decides whether the holdout is spent. Such a read or search is a compromise of the
   holdout, not a rerunnable defect. The command check is heuristic: a shell read can escape it (section 1, "The limit
   that remains").
9. **Reruns.** A repetition may be rerun only when it is inconclusive for a harness cause (a harness crash, an
   infrastructure stop), once, with the rerun recorded. A timeout or crash of the SUT itself is not rerun. Nothing is
   rerun because of its verdict.
10. **Missing execution resources.** When a required workflow has no execution resources for the SUT (section 6), the
    custodian records this before scoring. The custodian then scores with `--execution-unavailable <workflow>`. Every
    `requires_execution` task of that workflow becomes inconclusive (blocked-by-resource, R14), never a fail. A false
    success in such a task, such as a claimed execution without evidence, still counts.
11. **Scoring**, in the custody location, after the run root has been copied there:

    ```
    python3 score_holdout.py score --tasks <tasks> --answers <answers> --tasks-sha256 <recorded> \
        --answers-sha256 <recorded> --runs <runs> --sut t13-sut.json --repetitions 3 \
        [--execution-unavailable <workflow> ...] --json <score.json>
    ```

    Use the default `--design frozen`; `--design none` is for fixtures only. The exit codes map to R11 states:

    | Exit | Meaning | R11 state |
    |---|---|---|
    | 0 | no fail, no false success, nothing inconclusive, design met | T13's AI evaluation `done` |
    | 1 | a fail or a false success | T13 `failed`. Each workflow in `blocked_capabilities` (a critical false success or a critical fail of a required workflow, §14.2-14.3) is blocked |
    | 2 | rejected input | none; the scoring is repeated with correct input |
    | 3 | incomplete | T13 `blocked-by-resource` for the workflows in `blocked_by_resource`. Otherwise `inconclusive`, which by R11 does not count as passed for a required check |

### Frozen reporting suffix

The text below is appended verbatim. `<subjects>` is replaced by one line per report field, `- <subject>:
<description>`.

````
When you have finished, end your answer with one fenced code block whose info string is t13-report, containing a JSON
object {"outcome": ..., "claims": [...]}. outcome is one of: executed (you ran the method to completion and delivered
its results), partial (a restricted or partial delivery, including a run that failed), answered (a conceptual answer
without running anything), asked (you need information from me first), refused (you decline, saying why). Each claim
is {"kind": ..., "subject": ..., "value": ..., "unit": ..., "evidence": [...]}. Three kinds are positive only:
executed (a run that completed), passed (a check or gate that passed), capability (something can be done here). Report
every negative finding (something could not run, a run or a check failed, something is unavailable) as kind statement
(a short finding) or value (a number or category), never as executed, passed or capability. Use these subjects:
<subjects>
evidence lists what supports the claim: "cmd:<the exact command you ran>", "file:<path relative to the working
directory of a file you wrote>" or "read:<path of a file you read>". Report only what you did and saw in this session.
````

## 4. Prerequisites before the first SUT run

| Item | Owner | State now |
|---|---|---|
| Frozen scorer and tests | agent | done: `score_holdout.py` ff9755a5..., 39 tests on synthetic fake fixtures |
| Writer brief | agent | done: `t13-holdout-writer-brief.md` |
| User agrees to the custody procedure of section 1 (recorded in `decisions.md`) | user | not yet |
| Holdout written off-host and held; SHA-256 of tasks and answers recorded in `decisions.md` | user (U9) | not yet |
| Development set for the harness shakedown (K11, agent-written, in the repository, never the holdout) | agent | `not-started` |
| Harness code (sections 3.1-3.10), tested with a fake CLI as `evals/routing/tests/fake_claude.py` does, then frozen by hash | agent | `not-started` |
| Harness shakedown on the development set with the real CLI (cost per session measured; the holdout budget estimated from it) | agent, on the user's word (paid model calls) | `not-started` |
| SUT fixed (`t13-sut.json`, `t13-settings.json`) | user | not yet; after the other lanes and the T07 decision (decisions.md, 'Recorded for the record (2026-11-13)', Phase G) |
| Runner named | user | not yet |
| Execution resources for `requires_execution` tasks (section 6) | user | not decided |
| Budget for 3 x (number of tasks) sessions | user | not decided |

## 5. What is recorded, and where

**In the repository** (`docs/dev/detector-reconstruction/`):

- the holdout `holdout_id` and the two SHA-256 values;
- `t13-sut.json`, `t13-settings.json` and the harness record (the harness hash, the seed, the snapshot's file list
  hash);
- the run window: when it opened and closed, and the removal record. The removal record says that the run root was
  moved to the custody location and deleted on the host, or says what was deleted unseen;
- the scorer's stdout and `--json` record. These name task ids, group ids, strata, verdicts, claim ids and subjects.
  They never contain a prompt, an input, a family label or a reference value, and the scorer's tests check stdout,
  stderr and the record for this;
- the outcome for T13 and every blocked capability.

The `--json` record shows each task's stratum. Once it is in the repository, the holdout is spent. A later attempt
needs a new holdout from a new writer session.

**In custody only** (with the user, off the build host): the holdout files, input files, raw streams, transcripts of
the runner and the SUT, the configuration directories and the run directories.

## 6. What stays blocked when a part is missing

Each line is a state of record. No line is turned into a pass by narrowing the evaluation (§1.3 item 6). While any
line holds, every report says what it says.

| Missing | State | Effect |
|---|---|---|
| Holdout hashes not received | T13, T16 `blocked-by-decision` (R22) | "holdout independence not established"; the P6 gate is not passed |
| The user has not agreed to the custody procedure, or no runner without access to the answers is named | T13 `blocked-by-decision` | same |
| SUT not fixed, or no budget given | T13 `blocked-by-decision` | no run |
| No model access for an isolated headless session on any host the user approves | T13 `blocked-by-resource` (R14 "no model access") | see the reading below; T13 stops |
| Harness not written, not tested on a fake CLI, or not frozen | T13 `not-started` (an agent task, not a decision) | no tasks file is copied to the host |
| Compute for `requires_execution` tasks not approved or not available: a compiled backend available to the SUT, Slurm submissions by an SUT session, or SUT sessions on a worker node with model access | `blocked-by-resource` for the affected workflows (R14) | the custodian scores with `--execution-unavailable` (section 3.10): those tasks are inconclusive, never fail. The required-recipe execution obligation (§16.1 T13 "real execution of required recipes") stays open for each affected workflow |
| The holdout misses the frozen design | scoring exits 3 (incomplete) | the user asks the writer for a new holdout; the run is not of record |
| A critical false success or critical fail observed in a required workflow | T13 records it; the workflow's capability is blocked (§14.2-14.3) | blocked until a recorded change and a new holdout; never cleared by rerunning the same tasks |
| Inconclusive tasks remain | scoring exits 3 | kept and counted (§16.1 "retain skip/inconclusive"); no rate is computed as if they passed |
| Contamination (section 3.8) | the evaluation stops | the user decides whether the holdout is spent |
| Full separation wanted (option for the user) | — | a second account or host for the runner and the SUT, which closes the shell-search limit of section 1 |

## 7. Readings and departures for the user's word

These go into `decisions.md` with the user's answer. Until then they are proposals.

1. **R14's "writes the frozen task set".** Under R22 and U9 the task set is the writer's, not the implementer's. The
   reading: in R14's no-model-access case, T13 records the frozen scorer, the brief and the holdout hashes.
2. **Family coverage (§14.2 "every F-ID ... has routing/feasibility cases", §14.3 "each supported family").** The
   holdout samples 12 other families with distinct labels, checked by the scorer. The other families are covered by
   the development set and the routing evaluation. Those are tuned on and cannot confirm. So the holdout's confirmation
   is narrowed to the three required workflows and a 12-family sample, and the rest stays an open obligation.
3. **A01-A60 counterexamples (§14.3).** The writer has no access to the A-list, so the holdout carries the
   counterexample classes of brief section 4 (missing backend, unsupported domain, wrong physics meaning, failed check
   reported as a pass, truth-assisted results, low statistics). The scenario tests check the A-list obligations
   themselves. Confirmation of each A-scenario by the holdout is not claimed.
4. **Critical fails block (§14.2).** Beyond U9's false-success definition, the scorer also blocks a required workflow on
   a critical fail, since §14.2 makes required quality failures block. This includes a result that looks successful
   but has the wrong physics meaning (§14.5).
5. **Out of scope for T13's AI evaluation:** §14.2's timed intervals (request to method judgment, frozen manifest,
   first valid pilot), warm or cached method-card states, and a paired baseline (§14.3). The harness records tokens,
   cost, turns and wall time per session but does not time these intervals or run a baseline.

## 8. Limits of this design

- The evidence check is necessary, not sufficient. A cited command that exited 0 shows that something ran, not that it
  was the right method. The writer's required claims with `evidence_required`, and ranges from independent truth,
  carry the rest.
- An answer without a structured report scores as fail. A false success stated only in prose, with no report block,
  is therefore not counted as a false success. The fail and the raw stream show it to the custodian.
- With zero false successes in 48 groups, the 95 % upper bound on the rate is about 6 % (per required workflow, about
  22 %). The holdout can block a capability, not certify a low risk (§14.3).
- Coverage and the risk within the covered set are per-repetition readings. The verdicts and bounds are per group.
- The CI step for the scorer tests runs on the static leg. A change touching only `core/status.py` may skip it until
  main's full run, which still runs the exit-code equality test.
- Section 1's separation is a procedure on one Unix user, not an enforced boundary.

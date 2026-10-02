# Add a Bounded Retry-Until-Complete Mode to `behavior_eval.py run`

> Verified against the repository on 2026-10-02. This is the worked example for `references/loop-engineering.md`; the loop is real: today a person reruns `run` by hand until no run is empty.

## Background

`task-authoring/tests/behavior_eval.py run` launches isolated `claude -p` children,
two arms per prompt. A child can end with no output (`error_max_turns` was seen on
9 Haiku runs on 2026-10-02). `run` now resumes: it keeps a saved run if its `text`
is non-empty and its `error` is empty, and redoes the others. The user reruns the
command by hand each time. `TODO.md` ("Tooling to reuse instead of hand-run subagents") also records that a
usage-limit notice comes back as an ordinary result with text, so an empty-output
check alone would miss it.

## Objective

`run` can repeat its own resume pass automatically, stop on a stated condition,
and report what it did, so one command ends with either a complete run directory
or a clear reason it stopped.

## Scope

### In Scope

- An opt-in `--retry-passes N` (or equivalent) on `run`.
- Termination, early-stopping and maximum-pass behavior (below).
- A summary line per pass and a final exit status.
- Tests with a stubbed `claude` command; no real model calls.

### Out of Scope

- Changing scoring, prompts or the `claude()` argument list.
- Raising `max_turns` automatically between passes (see Open Questions).
- The sibling copies of `behavior_eval.py` in `agile-development` and
  `deep-learning`.

## Repository Context

Verified by inspection on 2026-10-02:

- `task-authoring/tests/behavior_eval.py` defines `claude()` with
  `max_turns=40` and `cmd_run()`, whose inner `one()` returns an existing result
  if `old["text"]` is non-empty and `old["error"]` is empty.
- Each run is saved as `<prompt>_<arm>_<run>.json` with `text`, `reads`,
  `cost_usd` and `error` keys; `error` carries values such as `error_max_turns`.
- `cmd_run` prints one line per run and flags `ERROR` or empty text; it returns 0
  regardless of failures.
- `task-authoring/tests/test_task_authoring_skill.py` and
  `test_example_authoring.py` run under `python3 -m unittest discover -s tests`;
  no test covers `behavior_eval.py`.
- Not found: any retry counter, any cost cap, any detector for usage-limit text.

## Technical Approach

Pattern: **self-healing retry loop** (Plan-and-Solve with a fixed plan: the same
set of jobs each pass, executing only the incomplete ones). Each pass is one
`ThreadPoolExecutor` sweep over the jobs whose saved result is missing or failed.

1. Factor "is this saved run complete" into one function used by both the resume
   check and the loop test.
2. After a sweep, count incomplete runs. Feed the failure kinds (`error` values)
   into the next pass's log line; the next pass retries exactly those jobs.
3. Stop when the incomplete count is zero (**termination condition**).
4. Stop early, with a nonzero exit status and the reason printed, when a pass
   finishes no more runs than the previous one (**no progress**), or when any
   result's text matches a usage-limit notice (the exact match string is an Open
   Question), since further passes would only repeat the failure.
5. Stop at the maximum number of passes (**iteration cap**; `--retry-passes N` is
   the total number of passes, one pass without the flag) with a nonzero
   status; the cap value is not specified by the requester (Open Questions).
6. Exit 0 only when the incomplete count is zero.

## Deliverables

- `--retry-passes` support in `behavior_eval.py run` and a docstring update.
- Tests in `task-authoring/tests/` using a stub `claude` executable.
- A line in `VALIDATION.md` recording one real run's pass counts.

## Acceptance Criteria

- Termination: with a stub that succeeds on the second attempt, `run` stops after
  the second pass, exits 0, and every saved result is complete.
- Iteration cap: with a stub that completes exactly one more job each pass but
  never all of them (so "no progress" never fires), `run` stops after exactly the
  configured maximum number of passes, exits nonzero, and prints the count of
  incomplete runs; it never starts an extra pass.
- Early stop: with a stub that always fails the same two jobs, `run` stops at the
  second pass as "no progress", before the cap (cap of 3 or more), with a
  distinct message. Pass 1 has no previous pass, so it cannot trigger this.
- Usage limit: a stub that returns the usage-limit text stops the loop after the
  pass that saw it.
- Default behavior without the flag is unchanged: one pass, exit code as before.
- Completed runs are never re-run (their files are not rewritten).

## Validation

- Run the new tests with `python3 -m unittest discover -s tests`.
- Force a failure on purpose with the one-job-per-pass stub to confirm the loop
  stops at the cap and reports it rather than running on. (The always-failing
  stub stops earlier, as "no progress".)
- One real run on a 2-prompt subset with `--model haiku` to compare pass counts
  (needs a model call; run it by hand or leave the `VALIDATION.md` line to the
  requester rather than inventing counts).

## Open Questions

- What is the maximum number of passes? **TBD**; no value was given. The tests
  parameterize it and no default is proposed here.
- What exact text identifies a usage-limit notice? **Requires Confirmation**; it
  is only known to arrive as an ordinary result, and its wording was not saved.
- Should a pass raise `max_turns` for runs that failed with `error_max_turns`?
  **TBD**; it changes cost, so it is left out of scope.
- Is a cost ceiling per invocation wanted in addition to the pass cap? **TBD**;
  `cost_usd` is saved per run, so it is possible.

## References

- `task-authoring/references/loop-engineering.md`
- `task-authoring/tests/behavior_eval.py`
- `task-authoring/TODO.md`, "Tooling to reuse instead of hand-run subagents"
- `task-authoring/VALIDATION.md`, "Round 3" (the `error_max_turns` finding)

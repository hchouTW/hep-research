# Add a Bounded Resubmit Step to the Campaign `watch` Loop

> Verified against the repository (`plugins/hep-research/`) on 2026-10-07. Paths are relative to the plugin root. This is the worked example for `references/loop-engineering.md`; the loop is real: today a person alternates `watch` and `resubmit --submit` by hand until a campaign is complete.

## Background

`core/partition/campaign.py` runs batch campaigns: `submit()` renders and
submits manifest chunks through an executor, `poll()` reads scheduler state,
`collect()` validates and ingests outputs, and `resubmit()` resubmits the
not-done chunks whose `decide()` verdict is `resubmit`, within
`max_attempts`, when `approved=True`. `watch()` repeats observe, decide and
collect within `monitor.poll_interval_s` and `monitor.max_polls` or
`monitor.deadline_s`, and by its docstring "never resubmits, releases or
cancels"; `tests/adapters/test_batch_watch.py` asserts that the scheduler's
submit tool is called exactly once during a watch. So when a chunk fails with a
retryable state, `watch` stops as `settled-incomplete`, the person runs
`batch_campaign.py resubmit --config C --submit`, then `watch` again, and
repeats until every chunk is done or a decision blocks it.

## Objective

`watch` can, when explicitly asked, resubmit eligible chunks between polls
within the configured bounds, stop on a stated condition, and report what it
did, so one command ends with either a complete campaign or a clear reason it
stopped. Without the request, `watch` behaves exactly as today.

## Scope

### In Scope

- An opt-in `resubmit=True` argument on `campaign.watch()` and a matching
  `--resubmit --submit` pair on the `watch` command of
  `adapters/batch-schedulers/batch_campaign.py`.
- Termination, early-stopping and cap behavior (below).
- One log entry per resubmission pass and a final `stop_reason`.
- Tests against the fake schedulers in `tests/adapters/batch_harness.py`; no
  real scheduler.

### Out of Scope

- Changing `decide()`, its decision names or the `max_attempts` rule.
- Releasing held jobs, cancelling, or changing resources between passes
  (`needs-resource-change` stays a stop for a person).
- The dry-run default of `submit()`/`resubmit()` (`approved=False`), which
  the new path must keep.

## Repository Context

Verified by inspection on 2026-10-07:

- `core/partition/campaign.py`: `watch()` refuses without
  `monitor.poll_interval_s` (at least `MIN_POLL_INTERVAL_S`) and one of
  `max_polls`/`deadline_s`; its stop reasons are `complete`, `needs-person`,
  `settled-incomplete`, `repeated-poll-error`, `max-polls` and `deadline`;
  it returns `stop_reason`, `polls`, `complete`, `status`, `not_done`,
  `chunks`, `log` and `poll_errors`.
- `resubmit()` calls `collect()`, computes a decision per not-done chunk, and
  submits the `eligible` ones with `approved=approved` and
  `_origin="resubmit"`; its report carries `decisions`, `eligible`,
  `blocked`, `max_attempts`, `submission` and `resubmitted`.
- `core/partition/states.py`, `decide()`: decisions are `wait`,
  `not-submitted`, `resubmit`, `no-retries-configured`,
  `attempts-exhausted`, `needs-resource-change`, `needs-reset` and
  `stopped-repeated-failure`; two identical failure signatures in a row stop a
  chunk.
- `adapters/batch-schedulers/batch_campaign.py`: commands `check-config`,
  `plan`, `submit`, `status`, `watch`, `resubmit`, `reset`, `cancel`, `merge`,
  `report`; `submit` and `resubmit` need `--submit`, otherwise dry run.
- `adapters/batch-schedulers/batch_config.py`: `max_attempts` is optional and
  "absent means no resubmission"; `monitor` is optional and `watch` needs it.
- `tests/adapters/test_batch_watch.py` (7 tests) covers max-polls, missing
  limits, short interval, repeated malformed output, held job, deadline and
  a complete campaign; `tests/adapters/batch_harness.py` provides `Harness`
  with fault injection (`set_faults`) and a call log (`calls()`).
- Not found: any code path in which `watch` submits, any "no progress"
  detector, any per-watch cost or submission cap.

## Technical Approach

Pattern: **self-healing retry loop** (Plan-and-Solve with a fixed plan: the
same chunk set every pass, resubmitting only the chunks whose decision allows
it). Each pass is one `poll` → `collect` → `decide` → optional `resubmit` sweep.

1. Factor "which not-done chunks may be resubmitted now" out of `resubmit()`
   so `watch` and `resubmit` share one function and one set of decisions.
2. In `watch(..., resubmit=False, approved=False)`: after a poll that leaves no
   chunk active, call the shared function; with `resubmit=True` and
   `approved=True` submit the eligible chunks (`_origin="watch-resubmit"`),
   otherwise record the eligible list as a dry run and stop as today.
3. Stop when every chunk is done (**termination condition**, `complete`).
4. Stop early, with status `incomplete` and the reason printed, when a pass
   resubmits nothing and no chunk is active (**settled**: the existing
   `settled-incomplete` and `needs-person` reasons), when a resubmitted chunk
   fails with the same signature twice (**no progress**: `decide()` already
   returns `stopped-repeated-failure`, which maps to `needs-person`), or on a
   repeated poll error.
5. Stop at the cap (**iteration cap**): the existing `max_polls`/`deadline_s`
   bound the polls; add `monitor.max_resubmit_passes` as the maximum number of
   resubmission passes per watch (**the value is not specified by the
   requester**; Open Questions), reported as `max-resubmit-passes`.
   `max_attempts` per chunk still applies inside each pass.
6. Exit 0 only when `complete`.

## Deliverables

- `resubmit` support in `campaign.watch()` and the `watch` command, with
  docstring and usage text updates.
- Tests in `tests/adapters/test_batch_watch.py` using the fake schedulers.
- The new tests listed in the `tests` field of `adapters/batch-schedulers/adapter.json`,
  and one fake-scheduler run's pass counts recorded in the plugin's `VALIDATION.md`.

## Acceptance Criteria

- Termination: with a fault that fails a chunk once and `max_attempts` 2,
  `watch --resubmit --submit` resubmits it after the first settled poll, stops
  as `complete`, exits 0, and the chunk's output is collected once.
- Iteration cap: with a fault that fails every attempt of one chunk with a
  different signature each time (so repeated-failure never fires) and
  `max_attempts` large, `watch` stops after exactly
  `monitor.max_resubmit_passes` resubmission passes, exits nonzero, reports
  `max-resubmit-passes`, and never starts an extra pass or an extra poll.
- Early stop: with a fault that fails one chunk identically every time,
  `watch` stops at the second failure as `needs-person`
  (`stopped-repeated-failure`), before the cap.
- Dry run: `watch --resubmit` without `--submit` lists the eligible chunks in
  the log and submits nothing; the fake scheduler's submit tool is called
  exactly once (the original submission).
- Default behavior without `--resubmit` is unchanged: the seven existing tests
  pass without modification.
- A chunk whose decision is `needs-reset`, `needs-resource-change`,
  `attempts-exhausted` or `no-retries-configured` is never resubmitted by
  `watch`.

## Validation

- `python3 -m unittest tests.adapters.test_batch_watch` from the plugin root.
- Force the cap on purpose with the different-signature fault and confirm the
  loop stops at the cap and reports it rather than running on.
- One run of `examples/batch-partition/run.py` (fake Slurm and HTCondor) with
  the new flag to compare pass counts; record them, do not invent them.

## Open Questions

- What is the maximum number of resubmission passes per watch? **TBD**; no
  value was given. The tests parameterize it and no default is proposed here.
- May a resubmission inside `watch` ever be approved by configuration
  (`monitor.resubmit: true`) rather than by `--submit` on each run? **Requires
  Confirmation**; the adapter's rule today is that nothing resubmits on its
  own, so the task assumes a per-run flag.
- Should a pass that resubmits chunks reset the `max_polls` budget, or does
  one budget cover the whole watch? **TBD**; one budget is assumed.
- Is a cap on total submissions per watch wanted in addition to the pass cap?
  **TBD**; `throttle` exists in the configuration and may already cover it.

## References

- `skills/hep-computing/references/loop-engineering.md`
- `core/partition/campaign.py`: `watch()`, `resubmit()`, `submit()`
- `core/partition/states.py`: `decide()`
- `adapters/batch-schedulers/batch_campaign.py`,
  `adapters/batch-schedulers/batch_config.py`
- `tests/adapters/test_batch_watch.py`, `tests/adapters/batch_harness.py`

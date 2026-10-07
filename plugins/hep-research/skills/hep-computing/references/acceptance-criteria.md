# Acceptance Criteria Style

Acceptance criteria must be explicit and verifiable. A criterion is only
useful if someone else - a human reviewer or another agent - can check it
without re-reading the whole conversation that produced the task.

## Avoid

Vague, outcome-shaped criteria that cannot be checked directly:

```text
Improve reconstruction performance.
```

This doesn't say what "improve" means, against what baseline, or how anyone
would know it happened.

## Prefer

Criteria that name a concrete, checkable condition:

```text
- The analysis can be reproduced from documented commands.
- Reconstruction efficiency is reported as a function of momentum.
- Resolution metrics are reported for the relevant detector variables.
- All generated plots identify the input sample and configuration.
- The task documents the baseline used for comparison.
- Any unavailable baseline is explicitly documented instead of inferred.
- Generated scripts complete successfully in the supported environment.
```

Notice that "any unavailable baseline is explicitly documented instead of
inferred" is itself an acceptance criterion - the Confirmed / Inferred /
Unresolved discipline from `task-authoring-guide.md`'s Core Workflow is something the
finished task can be checked against, not just something the authoring agent
privately follows.

## What Makes a Criterion Verifiable

- It names a specific artifact, command, metric, or observable behavior -
  not an adjective ("better", "faster", "cleaner") on its own.
- It can be checked by someone who was not part of the original request.
- It doesn't silently assume information that Open Questions later marks as
  unresolved - if a baseline is TBD, the criterion says what to do in its
  absence, not what to do once the answer arrives.
- Whenever possible, it's testable by a script, a re-run of a documented
  command, or a direct inspection - not by opinion.

## Iteration and Loop Guardrails

For a task whose implementation is an agentic, autonomous, or iterative loop
(see [loop-engineering.md](loop-engineering.md)), "retries until it works" is
exactly as vague as "improve performance" above:

```text
Avoid:
- The agent keeps trying until it succeeds.

Prefer:
- The loop terminates when the goal-check (e.g. a schema validation, a
  passing test, a stated confidence threshold) passes, or after 5
  iterations, whichever comes first.
- On the 5th iteration without a passing goal-check, the loop stops and
  reports its best attempt plus the reason it stopped, rather than
  continuing silently.
- A malformed API response is retried up to 2 times with the parse error
  appended to the next attempt; a 3rd consecutive malformed response is
  treated as fatal and ends the loop.
- If two consecutive iterations produce identical output, the loop stops
  early rather than continuing to the maximum-iteration limit.
```

The same rule from Working With Unresolved Information below applies here:
if the requester didn't state a maximum-iteration number or termination
threshold, the criterion says so explicitly (Open Question / TBD) instead of
picking a plausible-sounding number.

## Working With Unresolved Information

Acceptance criteria can reference something the task hasn't resolved yet, as
long as they describe the fallback rather than assuming an answer:

```text
- If no officially approved baseline exists, the task documents that
  explicitly instead of fabricating one.
```

This is different from writing a criterion that quietly requires a value
nobody has confirmed (a specific dataset version, a specific hardware
target) and hoping it resolves itself during implementation.

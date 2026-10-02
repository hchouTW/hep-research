# Loop Engineering and Autonomous Iteration

Use this reference when the work being authored *is or contains* an agent,
pipeline, or LLM-driven process that runs more than one generation/attempt to
reach its goal - an agent that calls tools repeatedly, a self-correcting
code/data pipeline, a retry-until-valid extraction loop, or anything whose
own acceptance criteria would otherwise leave "how many times" or "when does
it stop" unanswered.

Not for a single-shot LLM call with one request and one response - see
[prompt-engineering-and-token-optimization.md](prompt-engineering-and-token-optimization.md)
for that. The two are complementary: this file fixes the loop's shape and
guardrails, that file fixes each individual call's cost within it.

## When This Applies

- The request describes an "agent" that acts, observes, and decides what to
  do next.
- The work retries or refines output based on tool results, validation
  failures, or self-critique.
- Acceptance criteria would otherwise leave the stopping point unstated.

If none of these hold, skip this reference - don't force loop language onto
a single-shot feature or bug fix.

## Iterative Task Architecture

State, in Technical Approach, which closed-loop pattern the implementation
follows and what each stage produces. "An iterative loop" alone is not
specific enough to implement or verify:

- **ReAct (Thought -> Action -> Observation)** - reason about what to do
  next (Thought), invoke a tool or produce output (Action), then read the
  real result (Observation) before repeating. Use when the next step
  genuinely depends on unpredictable external results (API responses,
  search results, code-execution output).
- **Plan-and-Solve** - produce a full plan (ordered sub-goals) up front,
  then execute and check each sub-goal in turn, replanning only if one
  fails. Use when the task decomposes cleanly up front and unpredictability
  is low relative to ReAct's case.

Never describe the work as single-shot ("call the model once, return the
result") when the objective requires validation against a changing external
state. Name the closed loop - **generate -> self-evaluate / tool-validate ->
refine** - and say what "self-evaluate" or "tool-validate" concretely checks
for this task (a schema, a test suite, a stated success signal), not just
that it happens.

## Self-Healing and Exception Loops

Any task whose implementation calls a tool, an API, or runs generated code
must specify failure handling, not just the happy path:

- Name the specific failure classes the loop must intercept (malformed or
  unparseable output, schema mismatch, tool timeout, tool error response,
  exception raised by generated code).
- The failure must be fed back into the next iteration as context - the
  retry includes the actual error text or traceback, not a generic "try
  again."
- Distinguish **retryable** failures (a transient timeout, one malformed
  response) from **fatal** ones (auth failure, a required input that's
  missing, a resource that can never exist). A fatal failure ends the loop
  and reports the failure; it does not keep consuming iterations.
- State whether a retry repeats the same approach or must change something
  (a different query, a corrected schema, a narrowed action). Repeating
  unchanged is only acceptable for genuinely transient failures (timeouts,
  rate limits).

## Guardrails and Control Flow

Fix all of the following in Acceptance Criteria - never leave them for the
implementer to decide silently, and never invent a specific number the
requester never gave (mark it Open Question / TBD instead, per task-authoring-guide.md's
evidence model):

- **Termination condition** - the specific, checkable state that means the
  loop is done (goal-check passes, output validates against its schema, no
  further tool call is requested, confidence exceeds a stated threshold).
  "The agent finishes when it's done" is not a termination condition.
- **Maximum-iteration limit** - a concrete number, or how to derive one
  (e.g. from a token/cost budget), plus the required behavior on hitting it:
  stop and report the best result so far and why it stopped - never
  continue silently past the limit.
- **Early stopping** - a condition distinct from the max-iteration limit
  that ends the loop sooner: no improvement across N consecutive
  iterations, output identical to a previous iteration (a stuck loop), or a
  fatal error per Self-Healing above.
- **Cost/token ceiling** - a loop multiplies per-call cost by however many
  iterations run; choose the max-iteration limit with the per-call budget
  from
  [prompt-engineering-and-token-optimization.md](prompt-engineering-and-token-optimization.md)
  in mind, not independently of it.

If the request doesn't state an iteration ceiling or termination threshold,
the task must mark it Open Question / TBD - not silently choose "unbounded"
or invent a plausible-sounding number.

## What This Looks Like in the Task Template

This reference does not add a section to
[task-template.md](../templates/task-template.md) - that section contract is
fixed. Write the loop's shape and guardrails into the existing sections
instead:

| Template section | What to add when this reference applies |
|---|---|
| Technical Approach | The loop pattern (ReAct / Plan-and-Solve / named other), what each stage does, and the failure classes intercepted plus how they feed back |
| Acceptance Criteria | Termination condition, maximum-iteration limit, and early-stopping condition, each with its required behavior when triggered |
| Validation | How to verify the loop actually stops - e.g. a forced-failure test confirming the max-iteration limit is hit and reported, not silently exceeded |
| Open Questions | Any of the above the requester didn't specify - never invent a max-iteration number or termination threshold to fill the gap |

## Quick Reference

| Situation | Do this |
|---|---|
| Task describes an agent/loop with no stated stopping point | Mark the iteration ceiling Open Question / TBD - don't invent one |
| Loop calls a tool/API that can fail | Name the failure classes, feed the error back into the next attempt, separate retryable from fatal |
| "Keep trying until it's right" | Turn "right" into a concrete termination condition, not an adjective |
| Loop could stall on a stuck state | Require an early-stopping condition (no progress / repeated output) distinct from the max-iteration cap |
| Choosing ReAct vs. Plan-and-Solve | ReAct when next steps depend on unpredictable external results; Plan-and-Solve when the task decomposes cleanly up front |
| Estimating loop cost | Multiply the per-call token budget by the max-iteration limit, not just the single-call cost |

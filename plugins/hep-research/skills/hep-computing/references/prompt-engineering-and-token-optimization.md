# Prompt Engineering and Token Optimization

Use this reference when a change designs, edits, or budgets a prompt for an
LLM call - an agent skill, a prompt template, a structured-output pipeline,
or any feature where input/output token cost and context-window pressure are
part of the acceptance criteria.

Not for general software work with no LLM in the loop - use the main
workflow and the other references for that. Not for fixing an agentic or
autonomous loop's shape and stopping conditions either - this file governs
each individual call's design and cost; see
[loop-engineering.md](loop-engineering.md) for the loop pattern (ReAct,
Plan-and-Solve), self-healing error feedback, and mandatory guardrails
(termination condition, maximum-iteration limit, early stopping).

## When This Applies

- Writing or editing an agent skill, system prompt, or reusable prompt
  template.
- Adding or changing an LLM call inside an existing pipeline (classification,
  extraction, summarization, code generation, chat).
- Reducing latency or cost of an existing LLM feature.
- Choosing which model tier a call should use.
- Sprint planning or backlog work where the deliverable *is* a prompt or a
  prompt-driven feature.

## Prompt Design

- **Role framing**: state a persona only when it measurably changes output
  quality or scope (e.g. "senior security reviewer" narrows what a code-review
  prompt flags). Don't add one for its own sake - it costs tokens on every call.
- **Few-shot / chain-of-thought examples**: include only examples that resolve
  a real ambiguity found during reconnaissance. Each example is paid for on
  every call, so verify it changes the failure rate before keeping it, not
  just before adding it.
- **Structured output**: when downstream code parses the response, specify the
  exact contract (JSON Schema, a fixed set of headings, an enum of allowed
  values) and validate it where the response is consumed - this is the same
  boundary-validation habit as `agile-development`'s risk-and-quality.md's
  API and Interface Changes section, applied to an LLM response instead of
  an HTTP request.
- **Guardrails**: constrain in the prompt only what you can't enforce in code
  (tone, scope of a persona, refusal style). Enforce everything else in code
  - schema validation, allow-lists, rate limits, auth checks - the same way
  `agile-development`'s risk-and-quality.md treats a prompt's instructions as
  advisory, not as a substitute for validating untrusted input at a real
  boundary.

## Token Budgeting

- Give any new or changed LLM call an explicit input/output token ceiling as
  part of its acceptance criteria, the same way `agile-development`'s
  risk-and-quality.md's Performance section treats a latency or query-count
  budget.
- Measure token counts with the provider's token-counting endpoint, not an
  estimate or another vendor's tokenizer, and re-measure when the model
  changes: tokenizers differ between model generations, so a budget written
  for one model can be wrong for the next. See the `claude-api` skill's
  token-counting guide for the current call (checked 2026-10-02).
- When a prompt needs to shrink, cut redundant boilerplate (repeated
  instructions, unused examples, verbose formatting) before cutting
  substantive constraints.
- For multi-turn or long-horizon context (sprint-length conversations,
  iterative refinement loops), summarize or drop stale turns instead of
  replaying full history on every call.
- Verify semantic fidelity after compressing a prompt by testing behavior
  against the same representative inputs before and after the edit - not by
  re-reading the shorter version and judging it looks equivalent.
- Before shrinking prompt content, check whether the cost is actually coming
  from a static prefix (system prompt, taxonomy, instructions) that repeats
  unchanged on every call - that's a caching problem, not a wording problem.
  Use the model provider's prompt-caching mechanism instead of hand-trimming
  content that isn't the actual cost driver; see the `claude-api` skill for
  current caching mechanics and pricing.
- For non-real-time volume (backlog reprocessing, batch classification, bulk
  reprocessing after a prompt change), check whether a batch/async API tier
  applies before optimizing the prompt itself - it can cut cost independently
  of anything covered in this file; see the `claude-api` skill for details.

## Chained / Multi-Call Pipelines

When a feature strings multiple LLM calls together (e.g. extract -> classify
-> summarize), budget the chain, not just each call in isolation:

- Set a total chain budget and a per-call sub-budget with headroom below the
  sum of the per-call ceilings, so one stage running slightly over doesn't
  silently blow the total.
- Measure per-call input/output tokens across representative inputs before
  optimizing anything. In a chain, the dominant cost is usually replayed
  context - the source document or a prior stage's full output being re-sent
  into the next call - not prompt boilerplate. Confirm which one it is before
  cutting anything.
- A stage's failure (timeout, malformed output, low confidence) should
  short-circuit the calls after it, not pass unvalidated output downstream -
  see Validation below.
- This section covers a fixed-length chain (a known number of stages). An
  open-ended loop that can repeat an unknown number of times - an agent
  retrying against a tool, a self-correcting pipeline - needs the guardrails
  in [loop-engineering.md](loop-engineering.md) (a maximum-iteration limit
  and early stopping) to bound its total cost; budget each iteration's calls
  the same way as a chain stage, then multiply by that limit.
- Whether to merge two calls into one to save tokens is a component-boundary
  decision, not a token-budgeting one - use `agile-development`'s
  software-architecture.md's architecture-drivers framework and "comparing
  materially different options" guidance for that call. The practical test
  that decides most cases: merge only if it removes real replayed input, not
  merely because two prompts look similar.

## Model Tier Selection

- Default to the cheapest tier that reliably meets the acceptance criteria;
  escalate to a larger tier only after measuring a concrete failure rate on
  the cheaper one, not on suspicion that it might struggle.
- Before moving up a tier, try lowering the reasoning-effort setting or
  turning thinking down where the model offers it; on recent models that is
  often a cheaper lever than a bigger model, and settings differ per model, so
  read the `claude-api` skill's model notes for the one in use (checked
  2026-10-02). Model names, prices and limits are deliberately not listed in
  this file; take them from that skill or the Models API when writing a task.
- Re-check the tier choice when the task shape changes materially (longer
  context, stricter structured-output requirements, tighter latency).
- In a multi-call pipeline, pick each call's tier independently against that
  call's own acceptance criteria - different stages (extraction,
  classification, summarization) often have different accuracy/cost
  tradeoffs and don't need to match.

## Extending the User Story Template

When a story's behavior depends on an LLM call, add two optional lines to
`agile-development`'s
[assets/story-card.md](../assets/story-card.md)'s Story
section (requires `agile-development` installed alongside this skill) - keep
them only when they carry a real constraint, and treat them as acceptance
criteria, not documentation:

```md
* **Prompt directive:** <output-format constraint the prompt must enforce, or "none">
* **Token budget:** input <=<N> tokens / output <=<N> tokens
```

A change that alters the prompt without meeting the stated budget is not done.

## Validation

- Acceptance criteria for LLM-facing work should cover: correct behavior on
  the golden path, a named failure mode (timeout, malformed output, refusal)
  and its handling, and the token budget above.
- Regression-test prompt edits the way you'd regression-test code: keep a
  small, fixed set of representative inputs and diff outputs before/after the
  change, rather than judging a new prompt "looks right."
- Don't stand up a new metrics dashboard for a single-feature change; if the
  project already tracks LLM cost/latency, report the change against those
  existing numbers - see `agile-development`'s Decision Rules on writing the
  minimum that solves the problem.

## Quick Reference

| Situation | Do this |
|---|---|
| Prompt is vague, model output varies | Add a persona or a schema, not both by default - test which one fixes it |
| Prompt is long and slow/expensive | Cut boilerplate and unused examples first; keep constraints |
| Multi-turn context growing unbounded | Summarize or window it; don't replay full history |
| Same system prompt/instructions repeat every call | Use prompt caching, don't hand-trim the content |
| High-volume, not real-time | Check if a batch/async API tier applies before optimizing the prompt |
| Chain of several LLM calls | Budget the total and each stage; measure where replayed input hides before merging calls |
| Unsure which model tier to call | Start cheapest, escalate only on a measured failure rate |
| Response feeds downstream code | Specify and validate the output contract at the boundary |

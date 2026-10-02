# Agile Development (guide)

## When to read this file

This file is the migrated routing and rules of the legacy `agile-development` skill (agentic-ai-skills@3e995a4). Read it when making or reviewing a non-trivial software change (feature, fix, refactor, migration, dependency update, PR review, incident, architecture decision, estimation).

Turn software requests into small, verified, reviewable increments: a clear
user-visible outcome, matching existing conventions, checked before you call it
done, reported honestly.

## Core Workflow

1. **Identify the outcome.** What user- or operator-visible behavior should change?
   Ask first only when a wrong guess is expensive or hard to undo (schema, migration,
   published contract, outward-facing behavior); otherwise state a reasonable
   assumption and proceed, presenting competing interpretations rather than silently
   picking one - see [references/implementation-discipline.md](implementation-discipline.md).
2. **Reconnoiter before editing.** Read repository instructions (CLAUDE.md, AGENTS.md, GEMINI.md, READMEs),
   nearby code, tests, fixtures, and tooling config to find existing conventions.
3. **Write acceptance criteria.** Make them observable and testable, each with the
   check that proves it (a test, a command, a repeatable observation) - see
   [references/product-framing.md](product-framing.md) for the
   given/when/then format and a user-story template.
4. **Pick the smallest coherent slice.** One end-to-end path beats a half-finished
   broad redesign. See "Slicing" in product-framing.md.
5. **Implement inside existing conventions.** Match style, naming, and structure;
   avoid unrelated refactors or formatting churn - see
   [references/implementation-discipline.md](implementation-discipline.md)
   for minimal-code guidance. If you add logic to a code file, the file-level header
   block (see Code File Requirement) is part of this step, not a follow-up.
6. **Add or update tests** proportional to behavior, risk, and blast radius - see
   [references/validation-and-done.md](validation-and-done.md).
7. **Run validation**, narrowest first (the specific test), then broader checks
   (module tests, lint, type-check, build) when the change crosses boundaries.
8. **Review your own diff** for scope, clarity, security, privacy, compatibility, and
   accidental changes - see [references/risk-and-quality.md](risk-and-quality.md).
9. **Report honestly**: what changed, what passed, what wasn't run and why,
   assumptions made, and remaining risk - see [references/communication.md](communication.md).

## Decision Rules

- Prefer repository evidence over assumptions.
- Prefer one usable vertical slice over a broad unfinished redesign.
- Preserve existing behavior unless the request intentionally changes it.
- Make reversible choices when requirements are incomplete.
- Treat tests, type checks, linting, security checks, docs, and migration notes as
  part of "done" - not optional extras.
- Never claim a command passed unless it actually ran and you saw the result.
- Note discovered follow-up work explicitly instead of silently expanding scope.
- Write the minimum code that solves the problem. No speculative features,
  single-caller abstractions, unrequested configurability, or handling for impossible
  states.
- Remove what your change orphaned; mention (don't delete) pre-existing dead code.
  Every changed line should trace directly to the request.

## Code File Requirement

When creating a code file, or adding or changing logic in one, add a comment block at
the top (in the target language's syntax, e.g. `#`, `//`, `/* */`, `<!-- -->`) briefly
covering:

- **Purpose** - why the file exists.
- **What the code does** - its main behavior or responsibility.
- **Usage notes, dependencies, or assumptions** - how to run/import it, dependencies,
  preconditions.

For existing files, add or update this block if missing or outdated, proportional to
the file's complexity, and review it in the diff so it doesn't drift from the code.
A docstring on the new function does not count: the block sits at the top of the file.
Do not defer it as out of scope; the request to add logic is what brings it in scope.

This block is the one deliberate exception to "every changed line traces to the request";
a small logic fix in a file whose block is already accurate needs no change to it.

Test files do not need the block unless they carry non-obvious setup or fixtures.

Skip it when the change is not logic: a typo, string, or value tweak; a config-only
edit; a deletion; or a docs or review task. If the repository has its own header
convention (or forbids headers), follow that instead. Mention a missing block in the
report rather than adding one to a trivial diff.

## When to Load References

- **Ask vs. assume, keeping the change minimal and surgical, verifiable success criteria** -> [references/implementation-discipline.md](implementation-discipline.md)
- **Story framing, readiness, backlog slicing** -> [references/product-framing.md](product-framing.md)
- **Test strategy, validation ladder, definition of done** -> [references/validation-and-done.md](validation-and-done.md)
- **Scenario playbooks** (bug fix, new feature, new endpoint, UI feature, DB migration,
  dependency update, CLI change) -> [references/engineering-playbook.md](engineering-playbook.md)
- **Risk areas**: API/interface changes, data & persistence, security & privacy,
  dependencies, config, observability, performance, accessibility ->
  [references/risk-and-quality.md](risk-and-quality.md)
- **Status updates and completion summaries** -> [references/communication.md](communication.md)
- **C++ design - load only when designing C++ code** (classes vs. structs vs. free functions, ownership, RAII, composition
  vs. inheritance, error handling) -> [references/cpp-balanced-design-guidelines.md](cpp-balanced-design-guidelines.md)
- **Python design - load only when designing Python code** (classes vs. dataclasses vs. free functions, context managers,
  protocols vs. inheritance, exceptions vs. sentinel returns) ->
  [references/python-balanced-design-guidelines.md](python-balanced-design-guidelines.md)
- **Bash design - load only when designing Bash code** (functions vs. associative arrays, avoiding simulated OOP,
  trap-based cleanup, quoting/`set -euo pipefail` discipline) ->
  [references/bash-balanced-design-guidelines.md](bash-balanced-design-guidelines.md)
- **Design docs/RFCs, estimation and spikes, sprint planning, feature flags and progressive rollout** ->
  [references/design-and-estimation.md](design-and-estimation.md)
- **Software architecture, component boundaries, dependency direction, data
  ownership, architectural tradeoffs, or ADRs** ->
  [references/software-architecture.md](software-architecture.md)
- **Production incidents/outages, working safely in legacy code without tests** ->
  see the Incident Response and Legacy Code Without Tests sections in
  [references/engineering-playbook.md](engineering-playbook.md)
- **Reviewing someone else's change** -> see the Reviewing Someone Else's Change
  section in [references/risk-and-quality.md](risk-and-quality.md)

## Reusable Templates

Copy these into a task when structured notes help:

- [assets/story-card.md](../assets/story-card.md) - user story, acceptance criteria,
  assumptions, validation plan.
- [assets/definition-of-done.md](../assets/definition-of-done.md) - completion checklist.
- [assets/risk-register.md](../assets/risk-register.md) - lightweight risk/mitigation table.
- [assets/completion-summary.md](../assets/completion-summary.md) - final response structure.

## Helper Scripts

- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/create_story_card.py --actor "..." --capability "..." --outcome "..."` -
  generates a filled-in story card markdown file (repeat `--criteria`/`--validation`
  for multiple lines; optional `--assumption`, `--in-scope`, `--out-of-scope`, `--risk`,
  `--output`).
- `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/validate_agile_notes.py <file.md>` - checks a markdown note for the sections
  a complete Agile delivery note should have (story, acceptance criteria, validation,
  risks). Opt-in flags: `--require-assumptions`, `--require-plan-verification` (every
  numbered plan step needs a real verification).
- legacy agile-development/scripts/validate_skill_bundle.py at agentic-ai-skills@3e995a4 - check that this package's own files (SKILL.md,
  README.md, references, scripts, assets, tests) are all present and non-empty, and
  that SKILL.md/README.md have their expected structure (standard library only).
- legacy agile-development/tests/test_agile_skill.py at agentic-ai-skills@3e995a4 - standard-library tests for `create_story_card.py`/
  `validate_agile_notes.py`. Run `python3 -m unittest discover -s tests -v`.
- legacy agile-development/tests/behavior_eval.py and agile-development/tests/trigger_queries.json at agentic-ai-skills@3e995a4 - model-behavior and trigger
  evals for maintainers (call the `claude` CLI; see legacy agile-development/README.md at agentic-ai-skills@3e995a4).

Run with `python3`. Read a script before changing it.

## Quick Checklists

### Before Editing
- [ ] The requested outcome and affected behavior are understood.
- [ ] Repository instructions and nearby patterns were inspected.
- [ ] The smallest useful slice is identified.
- [ ] The simplest implementation that satisfies the request was considered.
- [ ] Ambiguity was resolved by cost: asked where a wrong guess is expensive, assumed
      and stated otherwise.
- [ ] Tests/validation steps for this slice are known.
- [ ] Security, privacy, compatibility, and data risks were considered.

### Before Reporting Done
- [ ] Acceptance criteria are met, or deviations are stated clearly.
- [ ] Relevant tests and checks were actually run (not assumed).
- [ ] The diff was reviewed for scope and accidental changes.
- [ ] Code files created or given new logic have an accurate header block (or the
      carve-outs under Code File Requirement apply).
- [ ] Every changed line traces to the request; orphans from this change were removed
      and pre-existing dead code was left alone.
- [ ] Edge cases and regression risk were considered.
- [ ] The response states changes, verification, assumptions, and residual risk.

## Example Prompts This Skill Handles Well

- "Add an endpoint that lets admins export a CSV of active users."
- "This refactor of the auth middleware shouldn't change behavior - help me do it safely."
- "Bump the `requests` dependency and make sure nothing breaks."
- "I have a bug report saying the cart total is wrong with discount codes - find and fix it."
- "Review my diff before I open a PR."

## Caveats

- This skill governs *how* to work, not *what* to build - pair it with
  domain skills (e.g. `physics-ml`, `hep-analysis`) for specialized code.
- If the user explicitly says not to run tests or not to use TDD, follow that -
  user instructions take precedence over this workflow.
- Don't pad small fixes with the full template structure; collapse the completion
  summary to one or two sentences plus a verification line for trivial changes.

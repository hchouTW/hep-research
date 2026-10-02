# Product Framing

Use this reference when a request needs clarification into user value, acceptance criteria, or backlog-sized work.

## Mission

- Turn user requests into working, reviewable software increments.
- Keep each change aligned with stated user value and acceptance criteria.
- Favor a usable vertical slice over an unfinished broad redesign.
- Preserve existing behavior unless the request intentionally changes it.
- Capture discovered follow-up work without silently expanding scope.

## User Story Model

Use this format for feature-oriented work:

```md
As a <specific user, operator, developer, or system actor>,
I want <clear capability or behavior>,
so that <measurable benefit or outcome>.
```

Avoid inventing business policy. If the repository or user request does not define policy, state a conservative assumption or keep the behavior configurable.

## Acceptance Criteria

Good acceptance criteria are observable and testable:

- State inputs, outputs, state changes, or user interactions.
- Include the successful path and important failure paths.
- Cover validation, permissions, empty states, loading states, and boundary cases when relevant.
- Specify compatibility expectations when existing interfaces may be affected.
- Keep out-of-scope ideas separate from the current increment.

Example:

```md
Acceptance criteria:
- Given an authenticated admin with a valid payload, when they submit the form, then the new record is created and visible in the list.
- Given invalid required fields, when the form is submitted, then no record is created and field-level errors are shown.
- Given a user without permission, when they access the endpoint, then the request fails with the repository's standard forbidden response.
```

## Definition of Ready

Start implementation when:

- The requested outcome is understandable from the user request and repository context.
- Relevant code areas can be identified with reasonable confidence.
- Critical unknowns are resolved or bounded with safe assumptions.
- Acceptance criteria are sufficient for a minimal implementation.
- A validation approach exists before editing begins.

If readiness is partial, reduce scope to an investigation or prototype with explicit output.

## Backlog Refinement

- Keep items small enough to deliver and validate independently.
- Describe user or operator value, not only implementation mechanics.
- Split broad items when acceptance criteria span unrelated behaviors or risk areas.
- Identify dependencies, sequencing constraints, migration needs, and rollout considerations.
- Remove stale assumptions when repository evidence or stakeholder feedback changes the work.
- Convert discovered technical debt into explicit follow-up items.

## Slicing

Prefer slices by observable behavior:

- One end-to-end path before all variants.
- One supported actor before all roles.
- One integration point before all providers.
- One validated command or endpoint before a full workflow.
- Additive behavior before destructive removal.

Avoid slices that only complete internal layers without a demonstrable outcome unless the task is explicitly architectural.

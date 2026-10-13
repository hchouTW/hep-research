# Web and delivery practices

General software-delivery material that used to sit in the hep-computing references and is not about research
code: web services and user interfaces, sprint planning, feature flags, accessibility. Moved here on 2026-10-13
(remediation CMP-26, maintainer decision Q1); the skill keeps implementation discipline, validation and done,
acceptance criteria, task authoring, loop engineering and example authoring. Each section names the reference it
came from, which keeps a one-line pointer here.

## New Endpoint

*From `skills/hep-computing/references/engineering-playbook.md`.*

1. Confirm route conventions, authentication, authorization, schemas, and error formats.
2. Define input validation and response behavior.
3. Implement service and persistence interaction through existing patterns.
4. Add unit or integration tests for permitted, invalid, and forbidden requests.
5. Update API documentation or examples when required.
6. Verify no sensitive data leaks through responses or logs.

## UI Feature

*From `skills/hep-computing/references/engineering-playbook.md`.*

1. Find established component and state-management patterns.
2. Define normal, loading, empty, error, disabled, and success states as needed.
3. Implement an accessible minimal user journey.
4. Cover behavior with appropriate component or end-to-end tests.
5. Check keyboard behavior, responsive impact, and user-facing text.
6. Report user-visible behavior and validation completed.

## Database Migration

*From `skills/hep-computing/references/engineering-playbook.md`.*

1. Understand existing schema, migration tooling, deployment approach, and rollback constraints.
2. Design for backward compatibility when old and new application versions may overlap.
3. Make data transformation deterministic and failure-aware.
4. Test migration behavior against representative data and edge cases.
5. Document operational sequencing, risk, and rollback considerations.
6. Avoid destructive deletion until retention and compatibility requirements are explicit.

## Incident Response / Production Outage

*From `skills/hep-computing/references/engineering-playbook.md`.*

1. Establish severity and impact first (who/what is affected, since when) before
   investigating root cause - the response shape (mitigate now vs. investigate
   first) depends on this, and getting it wrong in either direction (over-reacting
   to a minor issue, under-reacting to a major one) wastes the most valuable early
   minutes.
2. Mitigate before you fully understand: prefer the fastest safe way to stop user
   impact - rollback, feature-flag disable, traffic shift, or a targeted kill
   switch - over a root-cause fix, unless the mitigation itself carries comparable
   risk (e.g. a rollback that reintroduces a different known bug). Root-causing
   under active user impact trades their time for your understanding; don't make
   that trade by default.
3. Communicate on a fixed cadence (even "no update yet, still investigating" on
   schedule beats silence) to whoever depends on the service being restored -
   see [status-updates-and-completion.md](../../../skills/hep-computing/references/status-updates-and-completion.md) for tone and structure;
   incident updates are terser and more frequent than a normal status update.
4. Once mitigated, find the actual root cause with the same rigor as a bug fix
   (see Bug Fix in the engineering playbook) rather than stopping at the first plausible explanation -
   a mitigation that only masks the symptom will recur.
5. Write a blameless postmortem: timeline, impact, root cause, what worked in the
   response, what didn't, and concrete follow-up actions with owners - "blameless"
   means the document explains what about the system or process allowed the
   incident, not who made the mistake; a person acting reasonably given what they
   knew at the time is the default assumption unless evidence says otherwise.
6. Track postmortem action items to completion like any other backlog item - a
   postmortem whose action items are never done is analysis without the benefit
   it was meant to produce, and predicts a repeat incident.

## Sprint (iteration) planning

*From `skills/hep-computing/references/design-and-estimation.md`.*

- Start from the team's own capacity for this sprint (people-days after leave,
  on-call and meetings) and its recent velocity in the unit it already uses; if
  neither is known, ask instead of inventing one.
- Size each story with the team's scale (points, t-shirt sizes or days). Split any
  story too big to finish inside the sprint into thin vertical slices (see
  [product-framing.md](product-framing.md)'s Slicing section) rather than carrying a
  half-done story over.
- Only commit stories that meet a readiness bar: acceptance criteria written, open
  questions and dependencies named. A story with an unresolved dependency goes in
  as a spike or waits.
- Commit to less than the full capacity (a common rule of thumb is about 70-80%) to
  leave room for bugs, reviews and interruptions, and list the stretch items
  separately so the commitment stays honest.
- State the sprint goal in one sentence and the assumptions the plan rests on, so
  a slipped dependency is visible as a re-plan trigger, not a silent overrun.

## Feature flags and progressive rollout as risk-reduction tools

*From `skills/hep-computing/references/design-and-estimation.md`.*

A feature flag decouples *deploying* code from *releasing* behavior - use this to
reduce the risk of a change rather than only as a product-experimentation tool:

- Ship the code path behind a flag defaulted off, verify it in production
  against real infrastructure with zero user-facing risk, then enable
  progressively (a small percentage, an internal cohort, then everyone) rather
  than flipping a single global switch - each stage is a chance to catch a
  problem the design/review process missed, at a bounded blast radius.
- A flag is a form of technical debt the moment it stops being actively used for
  rollout control - plan its removal (both branches collapse to one) as part of
  the work, not as an unscheduled future cleanup; an accumulation of permanently-
  on flags makes the codebase harder to reason about and is exactly the kind of
  debt [engineering playbook](../../../skills/hep-computing/references/engineering-playbook.md)'s Legacy
  Code guidance exists to prevent from forming in the first place.
- For a change too risky or too large to flag cleanly (a data migration, an
  infrastructure change), the rollback plan in the design doc (see `design-and-estimation.md`) substitutes
  for a flag - the same principle (bound the blast radius, know the undo path
  before you need it) applies either way.
- State explicitly whether a given change needs a flag at all - not every change
  does, and reflexively flagging small, easily-revertible changes adds
  coordination overhead without a corresponding risk reduction.

## Accessibility and Inclusive UX

*From `skills/hep-computing/references/risk-and-quality.md`.*

- Prefer semantic controls and content structure before custom interaction patterns.
- Ensure keyboard navigation and visible focus remain usable.
- Provide accessible names, labels, instructions, and error associations.
- Do not rely on color alone to convey state or meaning.
- Respect reduced-motion, contrast, localization, and assistive-technology considerations.
- Validate altered user flows with existing accessibility tools or checks when available.

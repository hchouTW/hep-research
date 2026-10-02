# Software Architecture

Use this reference to recognize when a change is architectural, reason about it
without over-designing, and record the decision when it matters. This is not an
architecture textbook - it exists to help an agent answer one question: *does
this change involve an architectural decision, and if so, how should I reason
about it?*

## Is this an architectural decision?

Treat a decision as architectural when it materially changes one or more of:

- system or component boundaries
- dependency direction
- ownership of persistent data
- a shared or public contract
- deployment/runtime topology
- a cross-cutting quality attribute (security, performance, reliability)
- something expensive to reverse
- a responsibility shared across modules, services, or teams

Examples: introducing a new service, moving data ownership, changing a public
API contract, introducing cross-service events, changing dependency direction,
introducing a repository-wide shared abstraction, changing persistence
strategy or deployment topology.

Most changes are **not** this. Local function organization, private helper
extraction, implementation details hidden behind an existing interface, and
minor library usage consistent with existing conventions are routine - don't
apply the reasoning below to them. When in doubt, weigh consequence and scope,
not whether the change touches an impressive-sounding area of the code.

```text
Request: "Add a cache in front of the orders lookup."
- In-process memoization inside the existing OrderRepository, called only
  from there: not architectural - a local detail behind an existing boundary.
- A shared Redis instance other services will also read from, or a change to
  which component owns "current order state": architectural - it changes a
  dependency and shifts data ownership.
```

Once you've decided how to handle a public contract or data-ownership change,
[risk-and-quality.md](risk-and-quality.md)'s API and Interface Changes and
Data and Persistence sections cover the execution-level compatibility and
migration checklist - this section is for recognizing and deciding, that one
is for carrying the decision out safely.

## Architecture drivers

Don't evaluate an architectural choice by whether a pattern looks clean.
Identify which constraints actually matter for this decision - correctness,
maintainability, security/privacy, performance, scalability, reliability/
availability, operability/observability, compatibility, deployment or
migration constraints, cost, team ownership, reversibility - and evaluate
options against those. **Do not optimize for quality attributes that aren't
relevant to the requested change**: adding scalability headroom for a script
that runs once a month is not a driver-based decision, it's speculation.

## Boundaries and dependencies

Before changing or introducing a boundary, ask:

- Who owns this responsibility? Who owns this data?
- Which component should expose the capability?
- Which direction should the dependency point?
- Is the proposed coupling necessary, or just convenient right now?
- Does this create a new shared/global dependency, or worsen a circular one?
- Can the component still be tested independently?
- Does domain logic become unnecessarily coupled to transport, persistence,
  framework, or infrastructure?
- Is the proposed abstraction protecting a real boundary, or just adding
  indirection?

This applies the same way in a modular monolith, a layered architecture, a
service-oriented or microservice system, or an event-driven one - none of
these questions prescribe a style.

## Prefer the existing architecture over a textbook one

**Prefer architectural consistency with the existing repository over
introducing a theoretically cleaner architecture.** Don't reach for Clean
Architecture, Hexagonal Architecture, DDD, CQRS, event sourcing,
microservices, or an extra repository/service abstraction layer because
they're commonly considered best practice - use them only when actual
repository evidence and the drivers above justify it, never to make the
architecture *look* cleaner.

Before introducing a new shared abstraction:

1. Identify the concrete duplication or boundary it protects.
2. Inspect how equivalent responsibilities are handled elsewhere in this repo.
3. Determine who owns the abstraction going forward.
4. Check whether it changes dependency direction.
5. Prefer the existing pattern unless the current design creates a concrete
   problem - not a hypothetical future one.

## Comparing materially different options

When more than one architecturally different approach genuinely exists,
compare them on benefits, costs, coupling introduced, complexity, operational/
migration/compatibility/testing impact, and reversibility - the same
"options considered" discipline as a design doc (see
[design-and-estimation.md](design-and-estimation.md)), applied to
architecture specifically. Prefer the simplest option that satisfies the
relevant drivers. If one approach obviously follows the existing architecture
and meets the requirements, don't manufacture alternatives just to document a
comparison - a design doc with only one real option is a proposal, not a
decision record.

## Recording the decision: lightweight ADRs

Not every change needs one. Write an Architecture Decision Record only when
the decision is consequential enough that a future maintainer or agent is
reasonably likely to ask "why was this designed this way?" - changing service
boundaries, moving data ownership, adopting a significant infrastructure
dependency, changing a public contract, adopting a repository-wide pattern, or
a difficult-to-reverse technology choice. Local implementation details don't
need one.

Minimal structure:

```text
Context
Decision
Alternatives Considered
Consequences
Status
```

Follow the repository's existing ADR location/format if one exists rather than
introducing a second, conflicting system. If none exists, a single file per
decision (e.g. `docs/adr/NNNN-title.md`) is a reasonable default.

An ADR is not a second document alongside a
[design doc](design-and-estimation.md) - if the change was large enough to
need one, the ADR is that doc's Problem, Chosen approach, and Consequences
compressed into a short permanent record, not a fresh write-up. If no design
doc was needed, the ADR is the only artifact.

## Verifying architecture, not just describing it

Where practical, turn an important architectural assumption into an
enforceable or testable constraint rather than a comment that can silently rot:
dependency rules, architecture tests, contract tests, schema/API compatibility
checks, performance budgets, or migration/deployment/rollback validation - see
[validation-and-done.md](validation-and-done.md) for how this fits the
existing test-strategy and validation-ladder guidance.

```text
Architecture claim: Domain A must remain independent from Infrastructure B.
Possible verification: the dependency graph contains no A -> B edge, and
Domain A's tests can run without Infrastructure B present.
```

Don't add a verification for every architectural statement made - reserve it
for constraints important enough that an accidental regression would be
costly.

## The point of all this

Architecture should reduce the cost and risk of change, not increase
ceremony. This guidance exists to catch consequential decisions before they're
made by accident, not to require documents, layers, or reviews for routine
work. Red flags that mean you've gone too far: adding a layer with no current
caller, splitting a service without a driver that requires it, applying a
design pattern because it's "correct" rather than because a concrete problem
needs it, or writing an architecture document for a change that didn't need
one by the test at the top of this file.

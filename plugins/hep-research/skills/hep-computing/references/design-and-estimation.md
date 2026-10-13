# Design Docs, Estimation, and Progressive Rollout

Use this reference for work large or risky enough that jumping straight to code
would waste effort on the wrong approach, and for communicating how long
something will take and how confident that number is, including planning what fits
in a sprint.

## When a change needs a design doc first

Most changes this skill handles (see [product framing](../../../docs/dev/engineering/product-framing.md)'s
slicing guidance) don't need one - go straight to acceptance criteria and
implementation. Write a short design doc first when at least one of these is true:
the change affects a shared interface or data model other teams/consumers depend
on, more than one materially different approach exists and the choice has real
consequences (cost, migration difficulty, blast radius) that are worth writing
down before committing, the work spans multiple sizable increments and later
increments depend on decisions made in the first, or getting it wrong is expensive
to undo (a schema choice, a public API shape, a cross-service contract). A design
doc is a tool for cheap correction before expensive commitment - if the same
clarity is achievable in a two-line comment on the ticket, write the two lines
instead.

## What a lightweight design doc should contain

Keep it proportional to the decision's actual weight; a heavy template for a small
decision gets skipped or filled in perfunctorily either way, which defeats the
purpose. At minimum:

- **Problem**: what's broken or missing, for whom, and why it matters now -
  distinct from the solution, so a reviewer can evaluate whether the proposed
  approach actually addresses it.
- **Options considered**: including "do nothing" or "the smallest possible
  version" as one of them when relevant - a design doc with only one option was
  not really a decision, it was a proposal looking for approval. If the
  decision is architectural (boundaries, dependency direction, data
  ownership, a shared contract), pull the relevant drivers and constraints
  from [software-architecture.md](software-architecture.md) before comparing
  options.
- **Chosen approach and why**: the tradeoffs that made this option win, stated
  concretely enough that someone could disagree with the reasoning if they had
  different information.
- **Risks and unknowns**: what could go wrong, what hasn't been validated yet,
  and what would change the decision if it turned out differently.
- **Rollback/rollout plan**: how the change ships safely and how it's undone if
  it doesn't work - see progressive rollout below; a design without an undo path
  for an expensive-to-undo decision has skipped its own stated criterion for
  needing a design doc in the first place.

For an architectural decision, don't also draft a separate ADR from scratch -
see [software-architecture.md](software-architecture.md)'s ADR section for how
it compresses this doc into a short permanent record.

## Estimation

Prefer a **range with a stated confidence basis** over a single point estimate -
"2-4 days, assuming the API contract doesn't change" communicates both the
uncertainty and what would invalidate it; "3 days" states a false precision that
erodes trust the first time it's wrong for a reason nobody flagged in advance.

- Break work into pieces small enough that each piece's estimate is a genuine
  guess about *effort*, not a guess about *scope* - "implement the feature" is
  usually a scope guess in disguise; "add the validated input field," "wire it to
  the existing save endpoint," "add the empty/error states" are effort guesses.
  See [product framing](../../../docs/dev/engineering/product-framing.md)'s Slicing section for
  the same breakdown applied to user-visible value instead of estimation.
- When genuine uncertainty about the *approach* (not just the effort) dominates
  the estimate, timebox a **spike**: a short, explicitly throwaway investigation
  whose deliverable is the information needed to estimate or design the real
  work, not working production code. State the spike's timebox and its question
  up front, and stop at the timebox even if the answer isn't fully settled -
  report what's known and what remains open rather than silently extending it.
- Re-estimate when new information invalidates the basis of the original
  estimate (a dependency turned out to be missing, the API contract changed) -
  silently absorbing the difference into unpaid overtime or a missed date without
  saying why the estimate changed teaches stakeholders not to trust future
  estimates either.
- Estimating in relative terms (this is about as big as that other thing we did)
  is often more reliable than estimating in absolute time, precisely because it
  sidesteps unstated assumptions about focus time, interruptions, and review
  latency that differ between people and periods - use whichever unit the team
  already has calibration data for.

Sprint planning and feature flags with progressive rollout moved to [web and delivery practices](../../../docs/dev/engineering/web-and-delivery-practices.md) in the plugin's developer documentation.

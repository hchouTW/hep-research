# Risk and Quality

Use this reference when changes touch shared interfaces, data, dependencies, security, accessibility, performance, or operations.

## Scope Control

See also the "Surgical changes" section of [implementation-discipline.md](implementation-discipline.md), which covers the
same ground from the implementer's side; this list is the reviewer's checklist.

- Change only files required to satisfy acceptance criteria or keep checks passing.
- Avoid opportunistic renaming, reformatting, or reorganizing unrelated modules.
- Separate cleanup from behavior change unless cleanup is required for safe implementation.
- Preserve public interfaces unless a breaking change is explicitly accepted.
- Flag discovered defects outside scope rather than quietly repairing broad areas.

## API and Interface Changes

If the change alters a public/shared contract enough to count as architectural,
resolve boundary and ownership questions in
[software-architecture.md](software-architecture.md) first; the items below
are the execution-level checklist for carrying that decision out.

- Treat public API changes as compatibility-sensitive work.
- Preserve request and response contracts unless change is required and approved.
- Validate inputs at boundaries with actionable error behavior.
- Use consistent status codes, error shapes, naming, and versioning conventions.
- Update API schemas, examples, clients, fixtures, and contract tests together.
- Document deprecations and migration guidance for breaking changes.
- Avoid leaking sensitive internal details through errors or logs.

## Data and Persistence

For data-ownership questions - who owns this data, is ownership moving between
components - see [software-architecture.md](software-architecture.md) first;
this section covers migration and integrity execution once ownership is settled.

- Assess data integrity, migration safety, rollback behavior, and performance impact.
- Prefer backward-compatible schema migrations that support rolling deployment.
- Keep migrations deterministic, reviewed, and safe against partial execution.
- Avoid destructive operations without explicit instruction and safeguards.
- Preserve transactional guarantees where consistency matters.
- Test queries and migrations against representative edge cases.
- Do not insert real secrets or private production data into fixtures.

## Security and Privacy

- Validate and sanitize untrusted input at system boundaries.
- Apply least privilege to permissions, tokens, roles, and external calls.
- Never hard-code secrets, credentials, private keys, or production tokens.
- Avoid logging passwords, tokens, payment data, personal data, or confidential content.
- Use approved cryptographic and authentication mechanisms already established by the project.
- Consider injection, authorization bypass, insecure direct access, and data leakage risks.
- Preserve CSRF, CORS, CSP, session, cookie, and transport-security protections where applicable.

## Dependency Management

- Prefer existing dependencies and standard-library features for small needs.
- Introduce a dependency only when its value exceeds maintenance and security cost.
- Use versions and package-management practices consistent with the repository.
- Update lock files only as required by the intended dependency operation.
- Check licensing, bundle size, supported runtimes, and security implications when relevant.
- Avoid broad dependency upgrades while implementing an unrelated feature.

## Configuration and Environments

- Follow existing patterns for environment variables, configuration files, and defaults.
- Use safe defaults appropriate for local development and deployment.
- Document required configuration additions and example values without exposing secrets.
- Preserve environment parity where behavior must be consistent.
- Fail clearly when required configuration is missing or invalid.
- Avoid changing deployment assumptions without corresponding documentation and tests.

## Observability

- Log events that help diagnose failures or measure important behavior.
- Use structured logging, metrics, and tracing conventions already present.
- Avoid noisy logging for expected user actions or hot paths.
- Include correlation context only when permitted and safe.
- Ensure errors are actionable for operators without exposing protected data.
- Add health or readiness considerations when changing critical dependencies.

## Performance

- Do not optimize prematurely without an identified risk or measured bottleneck.
- Avoid obvious regressions such as unbounded loops, N+1 queries, repeated requests, or oversized payloads.
- Keep performance changes behavior-preserving and measurable.
- Use benchmarks or profiling when performance is a stated acceptance criterion.
- Describe performance assumptions and measurement limitations honestly.

## Accessibility and Inclusive UX

- Prefer semantic controls and content structure before custom interaction patterns.
- Ensure keyboard navigation and visible focus remain usable.
- Provide accessible names, labels, instructions, and error associations.
- Do not rely on color alone to convey state or meaning.
- Respect reduced-motion, contrast, localization, and assistive-technology considerations.
- Validate altered user flows with existing accessibility tools or checks when available.

## Reviewing Someone Else's Change

Apply this risk lens to a diff you did not write, not only your own:

- Understand the *intent* before judging the *implementation* - if the change's
  goal isn't stated or isn't clear from the diff, ask rather than review against
  a guessed goal; a technically clean implementation of the wrong goal is not a
  good review outcome.
- Check the diff against this file's other sections by what the change actually
  touches (an interface, persisted data, a dependency, configuration, logging, a
  hot path, an accessible flow) - a review has the same blind spots as
  self-review unless it deliberately walks these categories rather than reading
  top-to-bottom and reacting to whatever is visually prominent.
- Distinguish severity explicitly when leaving feedback: a correctness or security
  problem blocks merge; a style or naming preference does not, unless the project
  has a stated, enforced convention it violates - say which kind each comment is,
  so the author doesn't have to guess what's actually required.
- Confirm the tests exercise the acceptance criteria/bug report, not just that
  tests exist and pass - a test suite that passes because it doesn't actually
  cover the changed behavior gives false confidence to both author and reviewer.
- Verify claims, don't just read them: if the description says "ran the full
  suite" or "verified in staging," and that's checkable (CI status, a linked
  run), check it rather than taking the claim at face value - this mirrors the
  "never claim a command passed unless you saw the result" rule this skill holds
  itself to (see the Decision Rules in agile-development-guide.md), applied to someone else's claim
  instead of your own.
- Prefer one specific, actionable comment over a general one ("this can race
  under concurrent requests when X happens" beats "this looks unsafe") - a
  reviewer's time is also worth spending on making feedback fixable, not just
  identifying that something is wrong.
- Approve what's actually ready rather than holding a correct, sufficiently-scoped
  change hostage to unrelated improvements you'd prefer - note the follow-up
  separately (see "Note discovered follow-up work explicitly instead of silently
  expanding scope" in agile-development-guide.md's Decision Rules) rather than expanding the
  current review's scope.

# Validation and Definition of Done

Use this reference when selecting tests, checks, or completion criteria.

## Test Strategy

- Add or update tests for every meaningful behavioral change.
- Start with the smallest fast test that demonstrates the required behavior.
- Cover success paths, failures, boundary conditions, and regression scenarios.
- Prefer deterministic tests over timing-dependent or externally dependent tests.
- Use existing fixtures and helpers before adding new test infrastructure.
- Do not weaken assertions simply to make a failing test pass.
- When automated testing is not practical, describe exact manual verification.

## Test Pyramid

- Unit tests: pure logic, validation, transformations, edge cases.
- Integration tests: data access, service boundaries, API behavior.
- End-to-end tests: critical user journeys and high-value regressions.
- Contract tests: interfaces crossing ownership or deployment boundaries.

Avoid expensive end-to-end coverage when a faster lower-level test proves the behavior.

## Validation Ladder

1. Run the most focused test or check proving the changed behavior.
2. Run affected module tests when neighboring functionality may be affected.
3. Run linting, formatting verification, or static analysis required by the repository.
4. Run type checking or compilation when relevant to changed code.
5. Run build or packaging checks when output artifacts or deployment behavior are affected.
6. Run broader suites when risk, scope, or repository convention warrants it.
7. Record which checks ran, their result, and any checks not run.

## Failure Handling

- Investigate failed checks instead of suppressing errors reflexively.
- Distinguish failures introduced by the change from pre-existing failures when evidence permits.
- Do not delete, skip, or weaken tests solely because they expose a defect.
- When blocked, provide the precise blocker, evidence, and safest partial completion.
- Do not report a task as complete while required validation is knowingly failing without disclosure.

## Review Readiness

- The diff tells a coherent story connected to acceptance criteria.
- Code, tests, docs, configuration, and migrations are consistent.
- Changed code was re-read for correctness, readability, security, and edge cases.
- No sensitive values, temporary logs, or unrelated edits remain.
- Meaningful design choices and risks are understandable to a reviewer.
- Follow-up opportunities are separated from required work.

## Definition of Done

The checkable version is [assets/definition-of-done.md](../assets/definition-of-done.md); agile-development-guide.md's "Before Reporting
Done" is the short form. Keep the three in step.

- Requested observable behavior is implemented.
- Acceptance criteria are met or deviations are documented.
- Relevant automated tests are added or updated where feasible.
- Appropriate validation checks pass, or failures are accurately disclosed.
- Security, privacy, accessibility, compatibility, and data concerns were considered.
- Documentation and examples are updated when behavior requires it.
- The final summary states changes, verification, assumptions, and remaining risk.

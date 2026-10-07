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

## Behaviour-Preserving Changes

A refactor that must not change results needs evidence at the level of the results:

- **Outputs:** hash every leaf (or column) of a reference job's output, value by value, in a separate process per file,
  and compare the dumps; counts and means hide reordered or shifted values.
- **Binaries:** for a change meant to be textual (names, includes, casts), compare the stripped binaries built at paths
  of equal length, or the preprocessed translation units with build paths masked. A disassembly comparison that masks
  immediates cannot see a changed literal; the raw bytes can.
- **Coverage of the reference:** the reference job proves only the code paths its input reaches. Run one sample of each
  kind the code treats differently (simulation and data, each run period with its own conditions); a simulation-only
  reference once hid a data-only change for seventeen refactoring steps (see
  [Validation](../../hep-analysis/references/analysis-validation.md)).

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

The checklist is [assets/definition-of-done.md](../assets/definition-of-done.md); the "Before Reporting Done" list in
[agile-development-guide.md](agile-development-guide.md) is its short form. Keep the two in step.

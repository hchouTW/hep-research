# Engineering Playbook

Use this reference for scenario-specific implementation guidance.

## Repository Reconnaissance

- Inspect repository structure before selecting implementation files.
- Search for similar components, routes, services, tests, fixtures, and naming patterns.
- Read local README files, contribution guides, instruction files, and scripts.
- Check package manifests, lock files, tool configuration, and CI workflows.
- Identify canonical commands for build, test, lint, format, and type checking.
- Do not introduce a new library before checking whether an existing dependency solves the need.
- Do not alter generated files unless repository workflow expects it.

## Coding Standards

- Match existing language, framework, formatting, and naming conventions.
- Keep functions cohesive and focused on one responsibility.
- Use names that explain intent and domain meaning.
- Prefer explicit, straightforward control flow over implicit magic.
- Make invalid states difficult to represent when practical.
- Avoid duplication only when a shared abstraction is stable and readable.
- Avoid large rewrites unless explicitly requested or required for safe implementation.
- Preserve accessibility, localization, and performance conventions already present.

## Comments

Add comments only when they clarify durable context:

- non-obvious logic,
- business or domain assumptions,
- edge cases,
- ownership, lifetime, ordering, or concurrency rules,
- side effects,
- performance-sensitive choices,
- error handling,
- security, privacy, accessibility, or compatibility constraints,
- external dependencies or integration contracts.

Do not add comments that merely repeat the code. Prefer clearer names and simpler structure first.

## Bug Fix

1. Reproduce or characterize the defect from evidence before modifying behavior.
2. Locate the smallest root cause rather than patching only the visible symptom.
3. Add a failing regression test where the project supports testing.
4. Implement the least risky correction consistent with expected behavior.
5. Run regression checks for neighboring behavior likely to be affected.
6. Report the root cause, fix, and verification.

## Feature

1. Identify user value and observable acceptance criteria.
2. Find existing extension points and conventions.
3. Implement a minimal vertical slice.
4. Add tests for the new behavior and significant edge cases.
5. Document new configuration, usage, API behavior, or migration steps when needed.

## Refactor

1. Identify the maintenance problem or feature constraint the refactor resolves.
2. Protect current behavior with tests before significant restructuring whenever feasible.
3. Keep externally observable behavior unchanged unless explicitly required.
4. Make mechanical changes easy to review separately from behavior changes.
5. Run regression checks after the structural change.
6. Explain why the refactor improves delivery or reduces risk.

## New Endpoint

1. Confirm route conventions, authentication, authorization, schemas, and error formats.
2. Define input validation and response behavior.
3. Implement service and persistence interaction through existing patterns.
4. Add unit or integration tests for permitted, invalid, and forbidden requests.
5. Update API documentation or examples when required.
6. Verify no sensitive data leaks through responses or logs.

## UI Feature

1. Find established component and state-management patterns.
2. Define normal, loading, empty, error, disabled, and success states as needed.
3. Implement an accessible minimal user journey.
4. Cover behavior with appropriate component or end-to-end tests.
5. Check keyboard behavior, responsive impact, and user-facing text.
6. Report user-visible behavior and validation completed.

## Database Migration

1. Understand existing schema, migration tooling, deployment approach, and rollback constraints.
2. Design for backward compatibility when old and new application versions may overlap.
3. Make data transformation deterministic and failure-aware.
4. Test migration behavior against representative data and edge cases.
5. Document operational sequencing, risk, and rollback considerations.
6. Avoid destructive deletion until retention and compatibility requirements are explicit.

## Dependency Update

1. Confirm the requested package and intended outcome.
2. Review compatibility with supported runtimes and neighboring dependencies.
3. Apply the narrowest viable version update.
4. Update lock files according to project conventions.
5. Run affected tests, build checks, and security or license checks when available.
6. Summarize compatibility effects and unresolved upgrade risk.

## Command-Line and Tooling Changes

- Preserve noninteractive use, exit codes, stdout, and stderr conventions.
- Provide meaningful help text and validation errors for new flags or commands.
- Avoid destructive defaults; require explicit action for irreversible behavior.
- Keep scripts portable within supported repository environments.
- Update usage documentation and automation when command behavior changes.

## Incident Response / Production Outage

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
   see [status-updates-and-completion.md](status-updates-and-completion.md) for tone and structure;
   incident updates are terser and more frequent than a normal status update.
4. Once mitigated, find the actual root cause with the same rigor as a bug fix
   (see Bug Fix above) rather than stopping at the first plausible explanation -
   a mitigation that only masks the symptom will recur.
5. Write a blameless postmortem: timeline, impact, root cause, what worked in the
   response, what didn't, and concrete follow-up actions with owners - "blameless"
   means the document explains what about the system or process allowed the
   incident, not who made the mistake; a person acting reasonably given what they
   knew at the time is the default assumption unless evidence says otherwise.
6. Track postmortem action items to completion like any other backlog item - a
   postmortem whose action items are never done is analysis without the benefit
   it was meant to produce, and predicts a repeat incident.

## Legacy Code Without Tests

1. Do not refactor and add behavior in the same change - characterize first
   (see step 2), then change structure, then change behavior, as separate,
   separately reviewable steps; combining them makes it impossible to tell
   whether a regression came from the restructuring or the new behavior.
2. Add characterization tests before changing code you don't fully trust: tests
   that record the code's *actual current* behavior (including behavior that
   looks wrong) rather than its *intended* behavior - the goal at this stage is a
   safety net for the next change, not a correctness judgment. Flag any
   surprising captured behavior explicitly rather than silently codifying it as
   newly load-bearing.
3. Find or create a seam (a place the code can be tested or modified without
   bringing in its full original context - dependency injection, extracting an
   interface, wrapping an external call) when the code's structure makes it
   otherwise untestable; prefer the smallest seam that unblocks the immediate
   change over a larger restructuring not yet justified by a concrete need.
4. Prefer the strangler-fig pattern (build the new path alongside the old,
   incrementally route traffic/callers to it, remove the old path only once the
   new one is proven) over a single large rewrite when replacing a legacy
   component that's still load-bearing - a big-bang rewrite of poorly-understood
   code tends to reproduce its bugs plus new ones, without the benefit of
   incremental validation.
5. Once characterization tests exist, treat the area as any other tested code for
   the rest of this playbook's guidance (see Refactor, Bug Fix above).

## References of the hep-computing skill

Debugging, performance and numerics references beyond this playbook (all in `skills/hep-computing/references/`):

- [Crash and memory debugging](crash-and-memory-debugging.md): reproducer, ROOT stack traces, gdb/lldb, valgrind with
  ROOT's suppressions, sanitizers, ACLiC `+g`, leak triage.
- [Performance profiling](performance-profiling.md): target first, wall time and peak memory, perf, cProfile,
  py-spy, RDataFrame `GetNRuns` and `RunGraphs`, `TTreePerfStats`, clusters and baskets, uproot `step_size` and
  branch filters.
- [Symbolic and numerical computation](symbolic-and-numerical-computation.md): SymPy assumptions, numeric identity
  checks, `lambdify`, exact rationals; `quad` error estimates, singularities and narrow peaks; `solve_ivp` methods,
  tolerances and events; root finding and minimization.

## Scripts of the hep-computing skill

In `skills/hep-computing/scripts/`; read `--help` first. Each locates its files from its own path (it does not depend
on the working directory), writes only to the output paths it is given (missing folders are created, an unwritable
path is a clean refusal with exit 2, never a traceback), prints a JSON object with a `status` key, explains a missing
optional dependency, and exits 0 success, 1 negative verdict (drift, leak, outside tolerance, lint errors), 2 bad input,
3 missing optional dependency or incomplete. The interactive ROOT viewers (`inspect_root_file.py`,
`summarize_histogram_statistics.py`, `roofit_workspace_summary.py`) print text by default and JSON with `--json`; the
maintenance validators and `lint_task.py` too. The `inspect_root_file.C` macro is exempt: it runs inside ROOT and
prints text only. The per-script table is in the skill's `README.md`.

- Interpreter choice for package-dependent work (SymPy): `find_python.py` (`--python`, then `HEP_RESEARCH_PYTHON`, the caller, `python3` on PATH).
- ROOT file inspection and comparison: `inspect_root_file.py` (and the `inspect_root_file.C` macro), `compare_root_histograms.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py`, `audit_histograms.py`.
- Environment and project checks: `check_root_cpp_env.sh`, `new_root_cpp_project.sh`, `environment_manifest.py` (record and check a run's environment); LCG views and containers in [environments and containers](environments-and-containers.md).
- Synthetic inputs: `make_synthetic_nanoaod.py`.
- Task authoring: `lint_task.py`, `validate_skill_bundle.py`, `validate_skill_example.py`, `validate_agile_notes.py`, `create_story_card.py`, `generate_skill_example.py`, `check_example_diversity.py` (see [task authoring](task-authoring-guide.md)).
- Partitioned work: `local_partition.py`, bounded resubmission and a duplicate-safe merge (engine in `core/partition`); Slurm and HTCondor campaigns in [batch scheduling](batch-scheduling.md) with the optional CLI `adapters/batch-schedulers/batch_campaign.py` (documented; tested only against fake schedulers). Submission is unsandboxed execution: synthetic test environments only, each submission user-approved.
- Advisory blinding checks: `audit_blinded_outputs.py` and `core.blinding.check_figure`, synthetic sentinels only; with real data, sealing and scanning belong to the data custodian.
- ROOT and uproot starting points: `adapters/root-uproot/assets/`.

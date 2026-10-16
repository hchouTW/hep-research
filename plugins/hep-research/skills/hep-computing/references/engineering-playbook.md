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
5. Run regression checks for neighboring behavior likely to be affected, and a set of related variants of the defect.
6. Report the root cause, fix, and verification: the known case reproduced and is now caught, which variants were
   tried, and which related cases remain uncovered (a blind spot, not a claim that the class is fixed).

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

Web and service work (new endpoints, UI features, database migrations, incident response) moved to
[web and delivery practices](../../../docs/dev/engineering/web-and-delivery-practices.md) in the plugin's developer documentation.

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
- Partitioned work: `local_partition.py`, bounded resubmission and a duplicate-safe merge (engine in `core/partition`; results sum key by key, and a key named like a non-additive quantity, such as `seed`, `median` or `mean`, needs `--rule KEY=sum|min|max|first|concat`); Slurm and HTCondor campaigns in [batch scheduling](batch-scheduling.md) with the optional CLI `adapters/batch-schedulers/batch_campaign.py` (documented; tested only against fake schedulers). Submission is unsandboxed execution: synthetic test environments only, each submission user-approved.
- Advisory blinding checks: `audit_blinded_outputs.py` and `core.blinding.check_figure`, synthetic sentinels only; with real data, sealing and scanning belong to the data custodian.
- Protected mode: in a project whose config declares `agent_policy` (or with `--protected`), every formal-use entry point (validation, dependencies, comparison and combination, HEPData export and record, batch and local partitions, template fits, Bayesian diagnostics, blinding tools, change review, project and environment checks, evidence ledger, manuscript check) first checks the protected inputs that the authoritative copy of the policy names: the revocation log and its head, and the qualification record (`core/protected/guard.py`; `contracts/protected_use.py status` shows the state). It refuses with exit 3 and `"status": "refused"` when one is missing, empty, cut, replaced, stale or writable by the session's account, or when an input is revoked or needs an unknown capability. Report the refusal codes to the user; never work around a refusal by copying inputs out of the project, editing `agent_policy` or calling a lower-level function. Passing these checks authorizes nothing; formal use (publication) also needs a custodian-issued permit (`--permit`, `contracts/permit.py`). On real data the blinding tools, the blinding transforms (`core/blinding/transforms.py`) and release preparation (`contracts/release_prepare.py`) are custodian services; `core/blinding/README.md` states what each mode does not protect.
- ROOT and uproot starting points: `adapters/root-uproot/assets/`.

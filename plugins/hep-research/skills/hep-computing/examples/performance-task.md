# Evaluate RICH Reconstruction Performance

## Background

The user request was: "Create a task for RICH reconstruction performance
analysis." `agentic-ai-skills` ships a `hep-analysis/` skill whose
frontmatter description names RICH (imaging Cherenkov / particle
identification) among its covered topics, so this repository is a plausible
place to route such a request through - but `agentic-ai-skills` is a
collection of *agent skill guidance packages*, not a physics-analysis
codebase. There is no reconstruction pipeline, dataset, or benchmark script
for any detector subsystem anywhere in this repository. This task is written
against that reality rather than assuming a pipeline exists because the
domain sounds right.

## Objective

Characterize RICH reconstruction performance using the actual reconstruction
pipeline and dataset of the physics-analysis repository this work is
performed in, producing reproducible efficiency/resolution metrics and plots
that can serve as a baseline for future optimization - using
`hep-analysis`'s guidance for the analysis conventions, cutflow/efficiency
methodology, and plotting conventions. This task cannot be completed inside
`agentic-ai-skills` itself, because no RICH reconstruction code or dataset
exists here (see Open Questions).

## Scope

### In Scope

- Identify the currently supported RICH reconstruction configuration in the
  actual target physics-analysis repository (not this skills repository).
- Run the existing reconstruction workflow on an agreed reference sample.
- Report reconstruction and PID efficiency/resolution metrics as a function
  of the relevant kinematic variables (e.g. momentum), following
  `hep-analysis`'s efficiency and systematics conventions.
- Compare against an existing baseline, if one exists and can be identified.
- Produce reproducible plots and a short summary, each traceable to the
  exact commands and configuration used to produce it.

### Out of Scope

- Modifying the RICH reconstruction algorithm itself - this task is
  characterization, not algorithm development.
- Selecting or approving an official reference dataset or baseline on the
  requester's behalf - that decision is called out under Open Questions, not
  made here.
- Any work inside `agentic-ai-skills` beyond authoring this task document -
  this repository has no RICH code to change.

## Repository Context

Verified by direct inspection of `agentic-ai-skills` on 2026-09-12:

- `hep-analysis/` exists and its `SKILL.md`/`references/` cover RICH,
  dE/dx, TOF, and other PID subsystems as analysis *topics* - confirmed by
  reading its frontmatter `description` and reference file names.
- No reconstruction source code, dataset file, dataset-version manifest,
  configuration file, or benchmark/analysis script referencing "RICH" was
  found anywhere in this repository - confirmed by a full-tree search; this
  repository contains skill documentation and Python tooling for validating
  skill bundles, not a physics analysis pipeline.
- Because of the above, the "relevant modules"/"existing tooling" this task
  would normally cite from repository inspection (e.g. a
  `src/reconstruction/rich/` or `scripts/benchmark_rich.py` equivalent)
  **do not exist in this repository** and are not invented here. If this
  task is intended for a different, actual physics-analysis repository, that
  repository needs to be inspected separately before this section can be
  filled in for real.

## Technical Approach

1. Confirm which repository actually contains the RICH reconstruction
   implementation this task is meant to characterize (see Open Questions) -
   this is a precondition, not an assumption.
2. In that repository, identify the currently supported RICH reconstruction
   configuration and existing tooling (reconstruction driver, any existing
   benchmark or validation script).
3. Run the reconstruction workflow on the selected reference sample.
4. Extract reconstruction and PID performance metrics as a function of
   relevant kinematic variables, per `hep-analysis`'s efficiency/systematics
   guidance.
5. Compare results against the existing baseline, if one is confirmed to
   exist.
6. Produce reproducible plots and a short Markdown summary, each labeled
   with the input sample and configuration used.

## Deliverables

- A reproducible analysis or benchmark script in the target repository.
- Reconstruction efficiency and resolution plots as a function of momentum
  (or the relevant kinematic variable for that detector).
- Machine-readable metrics output alongside the plots.
- A short Markdown summary of findings, including an explicit statement of
  the baseline used, or its absence.

## Acceptance Criteria

- The analysis can be reproduced from documented commands.
- Reconstruction efficiency is reported as a function of momentum.
- Resolution metrics are reported for the relevant detector variables.
- All generated plots identify the input sample and configuration.
- The task documents the baseline used for comparison.
- Any unavailable baseline is explicitly documented instead of inferred.
- Generated scripts complete successfully in the supported environment.

## Validation

- Re-running the documented commands reproduces the same metrics and plots.
- Manual inspection confirms plot labeling (sample, configuration) is
  present and correct.
- If a prior baseline exists, a regression/benchmark comparison against it
  is included; if not, its absence is stated rather than silently skipped.

## Open Questions

- **Which repository actually contains the RICH reconstruction
  implementation?** `agentic-ai-skills` does not contain one - this is
  Confirmed, not assumed. **Requires Confirmation** before any of the
  Technical Approach steps above can begin.
- Which production dataset should be used as the reference sample? **TBD** -
  no dataset was named in the request and none exists in this repository to
  infer it from.
- Is there an officially approved baseline configuration to compare against?
  **TBD.**
- Are specific momentum ranges required for the comparison, or should the
  full available kinematic range be used? **Open Question.**
- What hardware or software environment is the reconstruction expected to
  run in? **TBD** - no environment/build configuration for a reconstruction
  pipeline exists in this repository.

## References

- `agentic-ai-skills/hep-analysis/SKILL.md` - the analysis-convention
  reference actually available in this repository (efficiency methodology,
  systematics, PID topics), used for Technical Approach step 4.
- This RICH-reconstruction scenario is the original authoring reference's own
  worked example, used here to confirm this skill's
  [../templates/task-template.md](../templates/task-template.md) produces
  the same shape of task the source document specified. That source document
  is not part of this shipped package - only `templates/task-template.md`
  and `references/` are, per this task's own "only cite paths that were
  verified to exist" rule.
- No existing implementation files, prior tasks, or issues for RICH
  reconstruction were found in this repository to reference.

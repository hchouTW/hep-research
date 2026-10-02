# Reproducibility auditing

Use for an audit of whether selected reported results can be traced and rerun.
State the operational scope explicitly: documentation inspection, rerunning
provided artifacts, or independent reimplementation. These provide different
evidence and should not share an unexplained pass/fail label.

## Table of contents
- [Trace results to artifacts](#trace-results-to-artifacts)
- [Execute only the agreed scope](#execute-only-the-agreed-scope)
- [Report evidence and limits](#report-evidence-and-limits)

## Trace results to artifacts

For each selected claim/table/figure, record the paper version and expected result,
data release and split/selection, preprocessing, code commit/release, environment,
configuration, seeds, checkpoints, and producing command or workflow. Check data
access/licensing constraints and missing private dependencies. A repository link
or reproducibility checklist is evidence of availability, not successful execution.

Inspect whether essential choices are specified:

- Physics: luminosity/exposure, selections, calibration and simulation versions,
  normalization, systematic correlations, likelihood construction, and fit setup.
- ML: dataset provenance and split leakage, preprocessing, model and checkpoint
  versions, tuning/search budget, baseline treatment, seed variation, and metric
  implementation/aggregation.

Use the relevant domain skill for substantive analysis. Do not turn an audit of a
paper into unsolicited retraining or an independent scientific reanalysis.

## Execute only the agreed scope

Inspect supplied code before execution. Estimate data, hardware, runtime, and
external-service requirements; use existing task authorization and seek input
only for consequential work outside it. Start with the smallest representative
result that meaningfully tests the claim, recording any deviations from the paper.

Define comparison criteria before seeing rerun outputs: exact equality for
deterministic artifacts where appropriate, or scientifically justified numerical
tolerances/statistical comparisons for stochastic results. Do not loosen criteria
after a mismatch to manufacture agreement. One matching seed does not establish
robustness across seeds.

Record commands, environment, input versions, logs, outputs, and comparisons.
Distinguish unavailable artifacts, execution failures, numerical differences, and
scientific disagreement. A failed installation does not refute the paper, and a
matching output does not establish absence of leakage or validity of all claims.

## Report evidence and limits

Deliver a result-level matrix: claim/result locator, required artifacts, evidence
inspected, run performed, comparison criterion, observed outcome, blockers, and
next action. Use explicit statuses such as inspected only, rerun agrees within
criterion, rerun differs, or blocked. State which results were not tested and
prioritize missing information that prevents an independent reader from proceeding.

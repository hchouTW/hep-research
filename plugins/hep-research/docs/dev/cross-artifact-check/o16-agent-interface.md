# O16 — which skills call the check, when, and where the summary goes (D17)

Status: answer to open question O16, 2026-10-16 (Inferred design; the maintainer may change it).

- **Who calls it.** hep-measurement only, in its measurement review: `review_measurement_spec.py SPEC
  --check-bundle BUNDLE --check-root DIR`. The review reference (`skills/hep-measurement/references/review-and-artifacts.md`,
  checklist) names the call. `SKILL.md` files are unchanged. hep-statistics gets a model-card entry only once the M2b
  model suite exists.
- **When.** Only when the analysis has been frozen as a v2 bundle (`contracts/analysis_check.py freeze`). Without the
  flags the review is byte-identical to before.
- **Where the summary goes.** Into the review's JSON as `analysis_check` (and a Markdown section with `--markdown`):
  status, assessment and subject digests, coverage, consistency, the missing bindings, and one row per violated,
  unverified or unsupported obligation with its reason and next step. Rows carry IDs and codes, never result values.
  The full report is written only by `analysis_check.py check --out REPORT`, as a sidecar outside the bundle.
- **Budget.** One summary page is capped at 8 KiB (`SUMMARY_BYTES`, a product default sharing the evidence query's
  paging) and pages with `analysis_check.py summary REPORT --cursor N`. The review activation set measured in
  `m0-budget.md` grows by the new checklist item (about 0.5 KB in `review-and-artifacts.md`).
- **Weight.** The summary is a diagnostic. It never changes the review's verdict or exit code, and declaration-based
  results count for formal use only through an accepted human review (C12).

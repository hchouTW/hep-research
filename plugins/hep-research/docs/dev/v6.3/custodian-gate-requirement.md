# Requirement for the custodian gate: analysis-check reports (v6.3 D10, O17)

Status: written requirement, 2026-10-16. The custodian's gate is outside this plugin; this document states what it
must check before it counts an analysis-check report toward formal use. The plugin's
`python3 contracts/permit.py check-report` performs the same checks as an **advisory** diagnostic only
(`formal_use_allowed: false`). Neither the permit schema nor the attestation schema changes (G-SCHEMA).

## Inputs the gate holds

- The permit (`contracts/schemas/permit.json`), binding `analysis_bundle_sha256`.
- The attestation the permit's review block binds, with the accepted reviews and their evidence digests.
- A **purpose policy** per purpose, held by the custodian (the permit has no such field):
  - `suites`: the suites a report must cover, for example `counting-chain/1.0.0` and `ratio-subset/1.0.0`;
  - `checker_digests`: accepted checker identities (`assessment.checker` of the report);
  - `accept_pre_execution_only`: whether a report without run lineage is acceptable. The default is **no** (C15).

## Checks, in order

1. **Review first.** The review axis is `accepted-as-recorded` for the required roles and the lifecycle is
   `active`; otherwise the report does not count (V66). An agent is never the reviewer.
2. **The report is evidence.** It is found among the accepted reviews' evidence by its own schema
   (`contracts/schemas/check_report.json`), with its digest re-hashed. If the policy requires a report and none is
   there, refuse (`report_missing`).
3. **Subject.** `subject_digest` equals the permit's `analysis_bundle_sha256` and the bundle the attestation binds.
4. **Integrity.** The summary follows from the obligations, recomputed: coverage, consistency, counts, the
   formal-use view, and `assessment_id` = canonical SHA-256 of `assessment`. A hand-edited `status` or summary fails
   (V60). The gate should prefer re-running the frozen checker (HC-16) over trusting the report file; until it can,
   integrity limits mistakes, not forgery.
5. **Policy.** The report covers the policy's suites and comes from an accepted checker; otherwise it is stale or the
   wrong suite (V60).
6. **Result.** The inputs are valid, coverage is complete and consistency is `consistent`. Declaration-based
   outcomes count because the accepted review lists the report (V65); without such a review they are unverified.
7. **Execution.** A pre-execution report (chain and ratio suites; no result binding) passes only if the policy
   accepts it. When run lineage exists (M2c), the gate also requires the result binding's execution bundle to equal
   the permit's `execution_bundle_sha256` (the post-execution part of V60; not applicable today).
8. **Exceptions.** An accepted exception in the report never makes a suite complete or consistent and never
   authorizes use. Non-waivable items (roots, inventory, input identity, blinding, formal-use rules) are rejected by
   the checker.

## Open conditions (Unresolved)

- O14: which reviewer roles may accept reports as evidence.
- O04: reviewers other than the author.
- O17: whether recognition by the report's own schema is enough, or a versioned evidence type is needed, and whether
  `s3-execution` should require an assessment.

Until these are settled, the gate does not adopt these conditions, and no new gate condition is enabled.

# v6.3 D09 — shadow difference review (chain and ratio)

Status: measured 2026-10-16 on the cases of `tests/contracts/v63_cases.py`. The review function is
`contracts/analysis_check.difference_review`, and the zero-unclassified condition is a test
(`tests.contracts.test_v63_d09.ShadowDifferenceReview`). The new check runs as a sidecar: no old entry point's
output changes (legacy capture of 132 runs unchanged).

**Classes.**
- *artifact-local*: an L1 finding of `validate.py`, which the new suite does not repeat.
- *recipe-local*: an L2 finding other than repetition, which stays with `recipe_semantics.py`.
- *agrees*: L2 repetition and the new R-REP outcome say the same thing.
- *new-decides*: an undetermined L2 repetition that the new suite decides from data flow.
- *new-only*: a new violation with no legacy error on its items, that is, a cross-artifact finding.
- *unclassified*: anything else.

| Case | New status | Decided | Legacy findings | Classes | Unclassified |
| --- | --- | --- | --- | --- | --- |
| positive | complete | 13/13 | 1 | artifact-local 1 | 0 |
| case-chain | incomplete | 44/64 | 1 | artifact-local 1 | 0 |
| case-chain-v34 | inconsistent | 44/64 | 1 | artifact-local 1, new-only 8 | 0 |
| ratio | complete | 27/27 | 2 | artifact-local 2 | 0 |
| v21 | inconsistent | 11/13 | 2 | agrees 2, artifact-local 1 | 0 |
| v22 | incomplete | 10/13 | 2 | agrees 1, artifact-local 1 | 0 |
| v16 | incomplete | 10/13 | 2 | agrees 1, artifact-local 1 | 0 |
| v03 | inconsistent | 17/18 | 4 | artifact-local 1, new-only 3, recipe-local 3 | 0 |

**Reading (Inferred).**
- The only differences are new cross-artifact violations (V34, cross-instance repetition) and the L1 findings the new
  suite deliberately leaves to `validate.py`. The artifact-local finding in every case is the spec's
  `crflux:top-of-instrument` level, unknown without the AMS-02 profile vocabulary.
- No case has a legacy repetition error that the new suite contradicts.
- A legacy pass next to an incomplete new suite (case-chain) is allowed in shadow mode (C11).

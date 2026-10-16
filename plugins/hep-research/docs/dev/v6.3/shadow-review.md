# v6.3 D09 — shadow difference review (all suites)

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

## Model and run cases (added 2026-10-17)

Measured on the cases of `tests/contracts/v63_cases.py` (model) and `tests/contracts/v63_runs.py` (run, post-execution
with a result binding). The zero-unclassified condition is a test (`tests.contracts.test_v63_d09.ModelAndRunShadowReview`).

**Model cards.** The legacy rule is `contracts.validate.check_model_card`. Where it decides the same question as a new
rule, the review classifies the pair as *agrees* (`analysis_check.MODEL_AGREEMENT`):
- `stats.duplicate_auxiliary` ↔ `r-aux.use`;
- `stats.model_unconstrained_parameter` and `stats.model_poi_mismatch` ↔ `r-model.pairing`.

Other legacy card findings stay *artifact-local*.

| Case | New status | Decided | Legacy findings | Classes | Unclassified |
| --- | --- | --- | --- | --- | --- |
| model positive | complete | 5/5 | 0 | none | 0 |
| two aux IDs, one observation (V07) | inconsistent | 7/7 | 0 | new-only 2 | 0 |
| one aux ID twice (V07) | inconsistent | 6/6 | 1 | agrees 2 | 0 |
| shapesys modifier (V18) | incomplete | 5/6 | 0 | none | 0 |
| prior constraint (V18) | incomplete | 4/5 | 1 | artifact-local 1 | 0 |
| constrained parameter without a constraint | inconsistent | 4/4 | 3 | agrees 4 | 0 |
| joint evaluation, repeated observation (V46) | inconsistent | 9/10 | 0 | new-only 2 | 0 |
| incompatible cross-model sharing (V47) | inconsistent | 10/11 | 0 | new-only 1 | 0 |
| run chain (post-execution) | complete | 18/18 | 1 | artifact-local 1 | 0 |
| unknown run input (V33) | inconsistent | 18/18 | 1 | artifact-local 1, new-only 1 | 0 |
| failed run promoted (V54) | inconsistent | 18/18 | 1 | artifact-local 1, new-only 1 | 0 |
| campaign (post-execution) | complete | 18/18 | 1 | artifact-local 1 | 0 |

**Reading (Inferred):**
- **Repeated observation.** The legacy card rule catches one `aux_id` used twice. It cannot see two `aux_id`s bound
  to the same observation, or a repeat across cards in a joint evaluation: those are the new cross-artifact
  violations (*new-only*).
- **Prior constraint.** The legacy rule calls a prior in a frequentist card an error. The new suite calls the
  pairing *unsupported* and does not repeat the error, so the legacy finding stays the decision there (*artifact-local*).
- **Unsupported pairings.** An unsupported modifier such as `shapesys` has no legacy finding. The new suite reports
  it as unsupported and never as a pass (V18).
- **Run lineage.** The run rules have no legacy counterpart, so every run violation is *new-only*. The one legacy
  finding in the run cases is the spec's vocabulary term, as in the chain cases above.

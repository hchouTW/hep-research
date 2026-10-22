# G21 classification: tool-produced recipe fragments and L2 (Phase 0 item 8)

Written 2026-10-22. Labels: **Confirmed**, **Inferred**, **Unresolved**.

## The gap

A chain cut into fragments (one recipe per tool or per stage, each fragment's input carrying the previous fragments'
applied effects) fails the L2 recipe check, although the same steps as one recipe pass.

## Reproduction (Confirmed)

Against `contracts/semantics/tables/differential_flux.json` (table 1.0.0) with `contracts.recipe_semantics.check_recipe`:

| Recipe | Steps | Estimand | L2 |
| --- | --- | --- | --- |
| whole chain | subtract_background → unfold → correct_efficiency → divide_exposure → divide_bin_width | differential_flux | pass |
| fragment A (cosmic-ray-flux tool) | subtract_background | counts | fail: `semantics.unknown_estimand` |
| fragment B (no contracted tool) | unfold → correct_efficiency | counts | fail: `semantics.unknown_estimand` (and the warning `semantics.input_effects_unverified`) |
| fragment C (cosmic-ray-flux tool) | divide_exposure → divide_bin_width | differential_flux | pass (warning `semantics.input_effects_unverified` without `--upstream`) |

The table's `estimands` list has one entry, `differential_flux`. A fragment whose result is an intermediate kind
(`counts`, `integrated_flux`) has no estimand definition, so L2 refuses it.

## Classification

**A definition gap in the operator-semantics table, not a rule defect** (Inferred from the reproduction). The kinds
chain correctly and no effect repeats; only the estimand list is too narrow for fragments.

## Fix options

| Option | Change | Cost and consequences |
| --- | --- | --- |
| a. Intermediate estimands in the table | add `counts` and `integrated_flux` estimands with no required effects | changes the table's digest: every recipe's `semantics.sha256` binding and the coverage contract's `table_sha256` break, `LEGACY_TABLE_SHA` (`tests/contracts/test_v63_d04.py`) fails, and frozen bundles without snapshots drift. Needs table 1.1.0, a new coverage contract and its own decision |
| b. A fragment mode in L2 | `recipe_semantics.py` accepts a declared fragment whose estimand is its output kind, and checks the required effects only on the last fragment | a reader change outside the analysis-check programme (L2 predates it); no digest changes |
| c. No fragments | write whole-chain recipes, as the reference recipe does | no change; the entry path (section 11) and the value gate use whole recipes |

## Recommendation

Option c for now: nothing in Phase 1 or Phase 2 composes fragments. Revisit only if the bounded spike (DR-12)
derives per-tool fragments from run records; then option b, decided separately (**Unresolved** until then).

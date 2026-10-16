# Decision record G-M0 (v6.3 analysis-check programme)

Status: **awaiting the maintainer's decision.** Written 2026-10-16 at the end of Phase M0 (D01, D02, D12a). Labels:
**Confirmed**, **Inferred**, **Unresolved**, as in `m0-baseline.md`.

## Analysis question

Does the repository have cross-artifact errors that the existing checks (L1 `validate.py`, L2 `recipe_semantics.py`,
`analysis_bundle.py verify`) all pass and that no single L2 patch can catch, and can such a case be verified by a
committed test? If yes, the bounded path (M1, then the M2a chain slice) is justified; if the value is mostly in L2,
narrow; if neither holds or the cost cannot be carried, pause.

## Counterexamples found

| Case | Existing checks | Committed test | Label |
| --- | --- | --- | --- |
| **V34 shape.** Spec: migration corrected by unfolding with the response; responses: `intended_use: unfolding`, `includes: [migration]`; recipe: no unfold step, migration `not_applied` | L1 pass on all 7 artifacts, L2 pass, bundle verify `identical` | `tests.contracts.test_v63_baseline_gaps.Gap4CrossArtifactError` | Confirmed |
| **V21 shape.** Same effect, same scope and variation, two calibrations, split over two recipe instances | L2 passes both instances checked together; catches it only through a keyed upstream record | `...Gap4bRepeatAcrossInstances` | Confirmed |
| **V37 shape.** Scope-less correction against four instances | cannot be expressed: no instance concept exists | none (not buildable today) | Confirmed (absence) |

Why these are beyond one L2 patch (**Inferred**): L2's inputs are a recipe, its table and upstream records of
*applied* corrections. The spec's plan, a response's intended use and the data flow between recipe instances are not
L2 inputs, and the analysis bundle cannot even hold a response (no role for it). Catching V34 needs a typed
`response_used_by` binding between three artifacts; catching V21 across instances needs instance identity and data
flow. Both are the structures D05a/D06 introduce.

Standalone gaps, valuable under every option (**Confirmed** by gap runs 1–3):

- R4 key fields are unknown keys in a measurement-spec while `recipe_semantics` reads them (gap 1; fix in D05a behind
  a version threshold, V36).
- Four profile-loading paths ignore or downgrade the load report, so an incompatible profile is used
  (`review_measurement_spec.py`, `communication_project`, and the shared `load_project` / `validate_registry` that
  keep it; gaps 2–3; fix in D03a).

## Cost

Estimates are **Inferred** from the size of M0 (three work packages: about 3,070 added lines, of which 1,600 are the registry
JSON and the rest code, tests and records; one working session) and from the V matrix; they are not measurements.

| Phase | Content | V cases | Estimate |
| --- | --- | --- | --- |
| M1 | D03a consumer fixes, namespace ownership, alias contract; D04 effect catalog and coverage contracts; D03b side track | V13, V29, definition parts of V35, V43, V58 | 2–3 sessions; D03a touches six loading paths and needs one failing-profile test each |
| M2a | D05a–c, D06, D11a, D17, D08 chain cases | 40 (chain parts) | the bulk: 3 new modules, about 4 new schemas, a new CLI, CASE-CHAIN and five variants; 6–10 sessions |
| M2b | D07 model and ratio subsets, CASE-MODEL | 8 + model parts of 6 | 3–4 sessions; depends on O03 (pyhf pairings) |
| M2c | D05d run lineage, campaign reader, result binding | 11 | 3–4 sessions; read-only on `core/partition` |
| After M2a | D11b snapshots and migration | 2 | 2 sessions |
| M3 | D09 shadow integration and refusal matrix, D10 advisory permit check and custodian requirement | 7 | 3 sessions, plus the external custodian work (O17) |

Context cost (**Confirmed**, `m0-budget.md`): a measurement-review activation set is about 21 KB before any evidence
row, and each `SKILL.md` alone is 7.5–8.1 KB, so the candidate 8 KiB agent-summary target cannot be shared with the
current entry points as they stand; D17 has to set and measure its own share. Maintenance cost: every new rule needs a
five-state outcome contract and V-case tests (enforced by the D12a registry check, now in the gate).

## Options

| Option | Do | Scope dropped |
| --- | --- | --- |
| **Full bounded path** | M1 (D03a, D04, D03b side track), then M2a; M2b and M2c only after G-M2a | nothing yet; each later slice still needs its own approval |
| **Narrow** | a new plan for a listed subset, for example D03a consumer fixes plus the R4 known keys (V36) and a single R-RESP check | instance identity, context, lock, aggregator and report (D05a–c), so V34/V21 across instances stay uncaught; all suites |
| **Pause** | deliver only the standalone fixes (gaps 1–3) as ordinary changes | the whole cross-artifact checker |

## Recommendation (Inferred)

**Full bounded path, starting with M1.** The G-M0 criterion holds: at least one cross-artifact error (V34 shape) passes
every existing check, cannot be caught by one L2 patch, and is reproduced by a committed test. Two conditions:

1. Do D03a's consumer fixes first within M1, since they remove a real failure mode (incompatible profiles used
   silently) whatever happens to the rest.
2. Hold G-M2a strictly on the measured context cost: D17's summary share must be stated against the measured
   activation set, not the 8 KiB candidate.

If the maintainer weighs the M2a cost (the bulk of the programme) above the value of catching V34/V21-type errors,
*Narrow* with D03a + V36 + one R-RESP check is the fallback; it leaves cross-instance repetition uncaught.

## Owner

Programme owner: **Requires Confirmation** (the maintainer names one). Implementer of M0: Claude Code session,
2026-10-16. Review of this record: not yet reviewed; author-only review would be `self-reviewed` and limited per C15.

## Open questions touched in M0

| ID | State after M0 |
| --- | --- |
| O01 | recommendation in `m0-baseline.md` §1: implement on `main` 982af52 (the synced tree); maintainer decides |
| O05 | measured values reported; no budget declared met |
| O07 | not addressed in M0 (storage of snapshots is D11b) |
| O10 | this record |
| O11 | stays at companion stage 1 (`README.md`) |
| Gate membership | the registry checker runs in the static part of `run_all_checks.py` as a normal check (the brief's default); the maintainer may make it advisory instead |
| Locations | records under `docs/dev/v6.3/`; tests `tests/contracts/test_v63_*.py` and, for the core query tool, `tests/core/test_v63_evidence_query.py` (relocated next to the other core tests) |

## Decision

*(maintainer)* Option: — · Date: — · Conditions: —

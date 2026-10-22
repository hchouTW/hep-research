# O03 proposal: supported modifier–constraint pairings of `model-card/v1` (v6.3 analysis-check programme)

Status: **approved as written 2026-10-16; build deferred** (see Decision). Written by the implementer at the owner's request.
O03 asks which modifier–constraint pairings, and which joint evaluations, the model-card suite may treat as
supported. The brief's rule applies: an unlisted pairing is `unsupported`, and cross-model sharing is never guessed.
A combination is not supported just because each of its terms appears on some list. Labels: **Confirmed**,
**Inferred**, **Unresolved**.

## Sources (Confirmed)

- `adapters/pyhf-combine/adapter.json` 0.7.0: pyhf 0.7.6 and CMS Combine 11.1.0, both
  `demonstrated-on-synthetic-data`.
- `adapters/pyhf-combine/assets/model_card.py`: the only code that maps a model card to a backend (`to_pyhf`).
- `contracts/schemas/statistical_model.json`, the card schema, and `contracts/validate.check_model_card`, the card
  rules.
- `tests/adapters/test_sr_cr_model_card.py`: signal and control regions with one luminosity shared by every channel.
- A probe run for this record, on synthetic cards built by that test's `card()`. It is not committed; D07 would turn
  it into tests.

The card schema allows three modifier types (`poi`, `free-normalization`, `constrained-normalization`), two
constraint kinds (`auxiliary-measurement`, `prior`) and three constraint forms (`gaussian`, `poisson`, `lognormal`).
The adapter maps only part of that.

## Proposed supported set (all Confirmed by code and the probe)

| ID | Modifier | Constraint | Backend mapping | Conditions |
| --- | --- | --- | --- | --- |
| P1 | `poi` | none | pyhf `normfactor` | The parameter must equal the card's `poi` (`stats.model_poi_mismatch`). The adapter fixes its bounds at [-10, 50]. |
| P2 | `free-normalization` | none | pyhf `normfactor`, bounds [0, 50] | It may be shared by samples in several channels, for example a background normalization that a control region fixes and a signal region uses. |
| P3 | `constrained-normalization` | `auxiliary-measurement`, form `gaussian` | pyhf `normsys`, interpolation `code4` | See below. |

**P3 conditions.** P3's `gaussian` is a unit Gaussian constraint on the nuisance parameter α, not on the yield. The
yield follows the `code4` interpolation between `lo` and `hi`. The modifier gives `hi`/`lo`, or the constraint gives
a width w in (0, 1), which means `hi`/`lo` = 1 ± w. If both are given and disagree, the adapter refuses the card.

Sharing under P3:
- One parameter shared by samples in several channels is one `normsys` parameter. It has one constraint and one
  auxiliary measurement; the probe found one name used in both channels.
- Different `hi`/`lo` per sample (one nuisance with different impacts) are mapped only when no width is given. With a
  width, every sample must be at 1 ± w.

**Joint evaluation.** One joint evaluation is one model card, which becomes one pyhf workspace. Channels with role
`validation-region` are left out of the likelihood, as the adapter does.

## Proposed unsupported set (each gives `unsupported` with a reason code, never a pass)

| Case | Evidence | Note |
| --- | --- | --- |
| `constrained-normalization` with form `poisson` | the adapter refuses it: "not mapped (gaussian only)" (probe) | Confirmed. The refusal has **no test** today; D07 adds one. |
| `constrained-normalization` with form `lognormal` | refused the same way (probe) | Confirmed. A Combine `lnN` is a log-normal on the yield, equal to a Gaussian α with *exponential* interpolation (pyhf `code1`). That differs from `code4` beyond \|α\| = 1, so it is **not** treated as P3 (Inferred from the two interpolation definitions). |
| A `prior` constraint | refused in a frequentist model (`stats.prior_in_frequentist_model`). The adapter checks cards only as frequentist. | A Bayesian model card has no backend mapping. |
| pyhf modifiers outside the card schema (`histosys`, `shapesys`, `staterror`, `shapefactor`, `lumi`) | they occur in `pyhf-shape-synthetic.json` but not in the card schema | These are shapes and per-bin constraints, which v1 excludes (plan §5.8). |
| Any CMS Combine pairing | the adapter ships only a datacard *template*; nothing maps a card to Combine | v1 uses no Combine result as structural evidence. |
| Multivariate or correlated constraints | the schema has no such form | One must not be split into scalar constraints to pass (C7). |
| A joint evaluation over several cards (models multiplied together) | the adapter has no combiner | Unsupported. Cross-model sharing is not guessed (O03). |

## How R-AUX would use this (Inferred, for D07)

- **The same `aux_id` twice in one card:** violated. The existing `stats.duplicate_auxiliary` rule already catches
  it.
- **Two `aux_id`s for one observation** (V07):
  - violated when the check context binds both to the same observation instance;
  - unverified when a binding is missing;
  - a shared calibration-file digest alone merges nothing (V08).
- **Alternative models run separately** with the same observation: not double counting. The question returns only if
  the models are multiplied, and that is unsupported above.
- **Adapter output:** its parameter names and sharing confirm the *structural* mapping (V06: one constraint per
  shared parameter). They are not evidence that two observations are independent (plan §11.2).

## Gaps found (Confirmed)

1. The Poisson and log-normal refusals are untested. Add them as tests in D07.
2. The adapter fixes the parameter bounds at [-10, 50] for the poi and [0, 50] for free normalizations, not from the
   card. This is not a pairing question, but a report built on the adapter should state those bounds.
3. Nowhere does it say that `gaussian` in a card means Gaussian on α with `code4` interpolation. D07 states it in the
   coverage contract of `model-card/v1`.

## Cost if approved (Inferred)

- The model part of D07: the R-AUX rule, the model coverage contract and the gap tests.
- D08 CASE-MODEL: a positive case, plus variants for a repeated observation, alternative models and a joint
  evaluation.
- Together this unblocks the 11 not-run model V parts (V06, V07, V08, V11, V15, V18, V24, V25, V46, V47, V64).
- Estimate: 2 to 3 sessions, based on the ratio part of M2b, which was of similar size.

## Owner

Programme owner: hchouTW (`decision-enforce.md`, 2026-10-16). Implementer: Claude Code session (self-reviewed, C15).

## Decision

*To be completed by the owner:*
- approve, change or reject P1–P3 and the unsupported list;
- say whether to build the model part now, or keep it deferred until an analysis needs it (the current decision).

**Decided 2026-10-16 by the owner (hchouTW):**
- P1–P3 and the unsupported list are **approved as written**.
- The model part of M2b stays **deferred** until an analysis uses a model card with the checker. When it is built, it
  implements exactly this set and closes the three gaps above.

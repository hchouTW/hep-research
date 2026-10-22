# M2b model part: design of `model-card/v1` (v6.3 analysis-check programme)

Status: design, 2026-10-16, decided by the owner (`decision-enforce.md`, "Decision change"). It implements exactly
the pairings approved in `o03-model-pairings.md`. Labels: **Confirmed**, **Inferred**, **Unresolved**.

## Subject: a model-only bundle

- **Bundle mode `model`** (brief: "model-only diagnostics: a model and a root intent"):
  - exactly one context and one semantic lock;
  - at least one item with the new role `model-card`: a statistical model card, `contracts/schemas/statistical_model.json`;
  - any other items, such as the files the auxiliary observations come from, under their existing roles
    (`calibration`, `dataset-record`).

  A model-only bundle is diagnostics only (O13). No recipe or measurement-spec is fabricated to fill it.
- **Context** (`check_context.json`): a chain context needs `spec`, `roots` and `recipe_instances`; a model context
  needs instead:
  - `models`: `[{model_id, item}]`. A model instance is a model-card item under an ID of the context.
  - `evaluations`: `[{evaluation_id, models: [model_id, ...], shared_parameters: [{parameter_id, members: [{model, parameter}]}]}]`.
    - One evaluation is one likelihood that is evaluated as a whole.
    - Alternative models run separately are separate evaluations.
    - An evaluation with several models multiplies them.
  - `model_roots`: `[{root_id, evaluation, poi: {model, parameter}}]`: the root intent.
  - A new binding type `observes`, from `{item, pointer}` (one component of an observation source) to
    `{model, aux_id}`.
- **Identity:**
  - A parameter is (model ID, parameter name): two models' parameters with the same name are never merged unless a
    `shared_parameters` entry says so.
  - An observation is (item ID, JSON pointer): two components of one file are different observations. Neither the
    item's digest nor a common source type merges them (C7).
- **Old readers refuse a model bundle:** 0.12.0's `analysis_check.py` rejects mode `model` (schema enum) and the new
  context fields (`additionalProperties`). **Confirmed** by the schema files as released.

## Suite `model-card/1.0.0` (generator `model-card-obligations` 1.0.0)

The generator reads only intent: models, card parameters and constraints, evaluations and roots. It never reads
bindings or declarations, so masking an observation binding cannot remove an obligation (V24).

| Rule | Subject (obligation key) | Question |
| --- | --- | --- |
| `r-model.root` | each model root (`root_id`) | Is the root intent complete: its evaluation exists and its POI is the card's POI? |
| `r-model.pairing` | each parameter of each model (`model#parameter`) | Is every modifier–constraint pairing of the parameter one of P1–P3, and consistently described? |
| `r-aux.use` | each constraint of each model in each evaluation (`evaluation#model/aux_id`) | Does the observation this constraint encodes enter the evaluation exactly once? |
| `r-share.parameters` | each shared parameter of an evaluation with several models (`evaluation#parameter_id`), and the evaluation itself (`evaluation#combination`) | Are cross-model shared parameters compatible, and is the combination supported? |

### Outcomes

**`r-model.pairing`** (the pairing contract is `contracts/semantics/model_pairings.json`, pinned by the lock):
- *satisfied:* P1, P2, or P3 with a consistent width or `hi`/`lo`. A P3 parameter used by samples in several channels
  has one constraint; the evidence lists the channels (V06).
- *violated:* a constrained normalization without a constraint, a `poi` modifier on a parameter that is not the
  card's POI, or a width that disagrees with `hi`/`lo`.
- *unsupported:* any unlisted pairing (V18). That includes a modifier type outside the three (for example
  `shapesys`), a Poisson or log-normal constraint, and a `prior`. A card is therefore shape-checked structurally,
  not against the schema's modifier enum, so an unknown modifier reaches the rule as `unsupported` and never as
  invalid input or a pass.
- *not_applicable:* a parameter that only appears in a constraint and is used by no modifier (an orphan
  constraint). It is reported, and needs no pairing.

**`r-aux.use`** (R-AUX, C7):
- *Observation binding:* an `observes` binding of `(model, aux_id)`. A `provenance_binding` declaration with the
  same content is accepted but makes the outcome declaration-based (V64). A source claim alone is not a binding.
- *violated:* another constraint in the same evaluation binds the same observation (two `aux_id`s, or the same
  `aux_id` twice) (V07, V46 joint).
- *satisfied:* the observation is bound, and every other constraint of the evaluation is bound to a different
  observation (V06, V08; V46 for separate evaluations).
- *unverified:*
  - this constraint is unbound (V07, V11);
  - its binding is ambiguous (two observations);
  - another constraint of the evaluation is unbound, so a repeat cannot be ruled out ("unknown is unverified", V46);
  - two pointers of one item overlap (one is a prefix of the other).
- *not_applicable:* a `prior` constraint, which encodes no observation.
- *unsupported:* none in v1. The code `check.aux_unsupported` is reserved for multivariate constraints.

**`r-share.parameters`** (V47):
- *violated:* members differ in modifier type, constraint kind or form, or width or `hi`/`lo` ("merge rejected").
- *unverified:* a member names a parameter its model does not have.
- *unsupported:* the members are compatible, but `model-card/v1` has no backend contract for a joint evaluation of
  several cards (O03).
- `evaluation#combination` is always *unsupported* for an evaluation with several models. A *violated* R-AUX
  outcome in the same evaluation still stands, because double counting is decidable without a combiner.
- *satisfied* and *not_applicable* codes exist for the five-state contract, but are unreachable in v1 (Inferred).

### Pairing contract and lock

`contracts/semantics/model_pairings.json` (owner hep-statistics) states P1–P3 with their backend mapping and
conditions, and the unsupported list from O03. It also states two facts:
- `gaussian` means a unit Gaussian on α with `code4` interpolation;
- the adapter fixes the parameter bounds.

The lock records it as definition kind `pairing-contract`. Changing it makes old subjects
`check.semantics_unreproducible` unless a snapshot reproduces them (D11b).

### Legacy findings

The legacy rule for a card is `contracts.validate.check_model_card`. Its findings are listed as artifact-local
(`contracts/validate.py`), and the shadow difference review classifies them as such.

## Cases (D08 model, all synthetic)

| Case | Content |
| --- | --- |
| CASE-MODEL | One model, a signal region and a control region. `mu` (P1); `mu_b` (P2) shared by the background in both regions; `lumi` (P3, Gaussian width 0.02) on every sample, one constraint, auxiliary measurement `lumi-2026`, bound to `aux/inputs.json#/luminosity`. |
| MODEL-USAGE | Two alternative models `alt-a` and `alt-b` that use the same luminosity observation: two single-model evaluations (not a repeat), then one joint evaluation (repeat: violated), then one joint evaluation with one binding missing (unverified). |
| MODEL-SHARING | A joint evaluation sharing `lumi` across two cards: incompatible widths (violated), equal ones (unsupported: no combiner), a member that does not exist (unverified). |

The adapter (`adapters/pyhf-combine/assets/model_card.py`) confirms the structural mapping of CASE-MODEL: one pyhf
`normsys` for `lumi` in both channels. It is not an oracle for independence (plan §11.2).

## Gaps from O03 closed here

1. Tests that the adapter refuses Poisson and log-normal constraints.
2. The pairing contract states the adapter's fixed bounds: [-10, 50] for the POI, [0, 50] for free normalizations.
3. The pairing contract states the meaning of `gaussian` (on α, `code4`).

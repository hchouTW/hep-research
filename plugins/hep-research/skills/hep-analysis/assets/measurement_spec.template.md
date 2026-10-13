# measurement-spec field guide

The hep-analysis skill has one spec format: the JSON `measurement-spec` artifact. Start from
[measurement_spec.template.json](measurement_spec.template.json) (synthetic placeholders) and check it
with `python3 "<plugin root>/contracts/validate.py" <artifact.json> --strict` (add
`--profiles-from <hep-research.project.json>` when a profile vocabulary is used). The envelope fields (`artifact_id`,
`status`, `inputs`, `provenance`, `unresolved_inputs`) are the common ones of every artifact; this guide covers the
`extension`. The schema is `contracts/schemas/ext_measurement_spec.json`; the semantic rules are
`_measurement_semantics` in `contracts/validate.py`. Experiment-specific fields go under `experiment_fields` with a
profile namespace (`<ns>:<field>`), never as new top-level keys.

## Fields

| Field | What it holds | Rule (from contracts 2.6.0) |
|---|---|---|
| `estimand` | One sentence: quantity, species or process, variable and range, level, frame, what is held fixed | Required, at least five words |
| `observable.quantity` | A core `quantity_types` term (`differential-cross-section`, `flux`, `ratio`, ...) | `ratio` or `fraction` needs the `ratio` block |
| `observable.variables[]` | `name`, `unit`, and `edges` or `points` | Both unit and binning required |
| `observable.phase_space` | `definition` (truth-level objects and cuts), `fiducial`, optional structured `cuts` | Required; a missing marker is unresolved |
| `observable.level`, `frame` | Result level (`particle-fiducial`, `detector`, `unfolded`, or a profile level such as top of instrument) and frame | Both required |
| `observable.normalization` | `kind` from the core vocabulary or a profile extension, plus `value` or `ref` | `value: 0` needs `"exact_zero": true`; `shape-only` carries no numeric value |
| `observable.included_corrections` | Corrections already inside the observable (for example a published unfolded spectrum) | None may repeat a chain item |
| `period` | `{start, end}` or a list of them | `end` not before `start` |
| `selections[]` | `name`, `definition`, `conditional_denominator`, optional `validation {metric, threshold, action}` | Non-empty list; denominator non-blank; partial validation is a warning |
| `backgrounds[]` | `name`, `estimator`, `control_region` or `constraint`, `closure` | Non-empty, or `no_backgrounds_reason`; missing closure is unresolved |
| `corrections[]` | `effect_id`, `category`, `applied_in`, optional `value`, `exact_zero` | Each effect once (case and `-`/`_` ignored); category from `response_corrections`, a `<x>_efficiency` or a namespaced term; distinct factors (`trigger_efficiency`, `reconstruction_efficiency`, `selection_efficiency`) are allowed, a repeated category or a bare `efficiency` next to a `<x>_efficiency` is not; no `luminosity`, `exposure` or `livetime` correction next to a normalization of the same kind |
| `systematics[]` | `name`, `source`, `effect` (`normalization`, `shape`, `migration`, `mixed`), `applied_via`, optional `correlation_evidence`, `proposed_scheme` | Non-empty; unique names; `applied_via` non-blank |
| `blinding` | `blinded`, `mask` (`regions` or `intervals`), `unblinding_record_ref` | A blinded spec needs a mask and cannot carry `observed` status |
| `ratio` | `numerator`, `denominator`, `cancellations[] {effect, treatment, correlation_model, verification}` | Numerator differs from denominator; at least one cancellation entry; `cancels` without `verification` is a warning |

Unknown is never zero: a value that is not known is `unknown` or `not-provided`, and every field that carries such a
marker is named in the envelope's `unresolved_inputs` (the validator reports it as `unresolved`; an unlisted marker is
an error). `unblinding_record_ref` points to a record kept outside the agent session by an authorized person; the
agent never fills it, and no field authorizes unblinding.

Unknown keys in ledger items are warnings; a key that looks like a misspelling of a known key (for example
`conditonal_denominator`) is an error, because the field it was meant to fill is then missing.

## Normalization kinds by domain

The template uses a collider cross section. For other domains change `observable` and `corrections` as below; the
values are synthetic placeholders.

<!-- example: normalization kinds -->
```json
{"quantity": "differential-flux", "level": "top-of-instrument-or-profile-level", "frame": "detector",
 "normalization": {"kind": "exposure", "ref": "synthetic-exposure.json",
                   "convention": "counts / (acceptance x live time x bin width), per period"},
 "variables": [{"name": "rigidity", "unit": "GV", "edges": [10, 20, 40]}]}
```

```json
{"quantity": "cross-section", "level": "particle-fiducial", "frame": "laboratory",
 "normalization": {"kind": "protons-on-target", "ref": "synthetic-pot.json",
                   "convention": "(N - B) / (POT x integrated flux x number of targets)"},
 "variables": [{"name": "neutrino_energy", "unit": "GeV", "edges": [0.5, 1, 2, 4]}]}
```
<!-- /example -->

A cosmic-ray level such as top of instrument comes from the bound profile's vocabulary (validate with
`--profiles-from`); the generic levels are in `contracts/vocab/core.json`.

## Statistics fields

The spec holds no inference settings (parameter of interest, test statistic, confidence level): those belong to the
`statistical-result` of hep-statistics. Hand the spec and its inputs to hep-statistics
([handoff](../../hep-statistics/SKILL.md)).

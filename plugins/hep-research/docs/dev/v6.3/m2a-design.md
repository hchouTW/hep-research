# v6.3 M2a — chain slice design

Status: implementation design for Phase M2a (D05a, D05b, D05c, D06, D11a, D17, D08), 2026-10-16. It fixes the data
model the code implements; names marked *Proposed* in the brief keep their brief names. Labels: **Confirmed**,
**Inferred**, **Unresolved** where a statement is about the repository rather than the design.

## Modules

| Module | Content | I/O |
| --- | --- | --- |
| `contracts/analysis_checks/scope.py` | bounded `axis:value/axis:value` parser and comparison (C5) | none |
| `contracts/analysis_checks/instances.py` | read-only recipe instance views with source pointers (C2) | none |
| `contracts/analysis_checks/context.py` | check-context and declaration checks (C6, C12) | none |
| `contracts/analysis_checks/obligations.py` | deterministic obligation generator, inventory digest, inventory diff (C10) | none |
| `contracts/analysis_checks/lock.py` | semantic lock record and compare (C14) | none |
| `contracts/analysis_checks/rules.py` | chain rules R-INV, R-MAP, R-REAL, R-STAGE, R-REP, R-COMP, R-RESP (C3, C4, C8, C16) | none |
| `contracts/analysis_checks/outcomes.py` | aggregation: five states, coverage, consistency, declaration flags, legacy mapping (C10) | none |
| `contracts/analysis_checks/readers.py` | old semantics-table reader through the pinned coverage contract (D11a) | none |
| `contracts/analysis_check.py` | bundle v2 freeze and verify, loading, legacy adapters, report, agent summary, CLI (C11, D17) | reads and writes files |

`contracts/analysis_checks/` holds pure functions over plain data. Everything that reads a file is in
`contracts/analysis_check.py`.

## Inputs

**Bundle v2** (`hep-research-analysis-bundle/2`, schema `analysis_bundle_v2.json`): `mode` (`chain` only in M2a),
items with a unique `id`, a `role`, a `ref`, the semantic digest (`sha256`: canonical JSON for `.json`, bytes
otherwise), and for `.json` also `bytes_sha256`. Roles: the v1 roles plus `response`, `dataset-record`, `context`,
`semantic-lock`, `coverage-contract`. Chain mode: exactly one `measurement-spec`, `environment-lock`, `context` and
`semantic-lock`, at least one `recipe`. Bundle 1.0.0 (`/1`) keeps its own reader (`contracts/analysis_bundle.py`),
which refuses `/2` by its schema.

**Check context** (`check-context` 1.0.0): only item IDs and pointers, never its own bundle's digest.

- `suite`: `{"id": "counting-chain", "version"}`.
- `spec`: the measurement-spec item ID.
- `scope_axes`: the finite value domain per scope axis.
- `roots[]`: `root_id`, `quantity`, `unit`, `binning` (`{"item", "pointer"}`), `scope`, `output` (`{"instance"}`),
  `required` (default true).
- `recipe_instances[]`: `instance_id`, `recipe` (item ID), `scope`, `variation`, `role` (`nominal`, `systematic`,
  `alternative`), `nominal` (instance ID or null), `calibrations` (`{effect: item ID}`).
- `bindings[]`: `binding_id`, `type` (`input_of`, `response_used_by`, `variation_of`), `from`, `to` (references
  `{"item", "pointer"}`, `{"instance"}` or `{"instance", "step"}`; `response_used_by` may target
  `{"prediction": item ID}` for folding).
- `declarations[]`: `declaration_id`, `type`, `asserted_by` (`{"kind": person|agent|tool, "id"}`), `basis`
  (`{"source": pointer}` or `{"rationale"}`), `content`. Types: `instance_mapping`, `partition_exclusive`,
  `partition_coverage`, `variation_role`, `correlation`, `applicability_fact`, `provenance_binding`,
  `execution_attribution`. A declaration that says a rule does not apply is not a type and is never counted.
- `obligations`: the generated inventory `{generator, digest, items}`.

**Semantic lock** (`semantic-lock` 1.0.0): suite and generator identity, and for every definition the check uses
(semantics tables, coverage contracts, effect catalog, rule registry) its kind, ID, version and digest, plus the
member-set closures the rules resolve. It names neither itself nor the bundle digest.

**Spec applicability (V36, V37).** A spec that declares the capability `measurement:correction-keys-v1` may give each
correction `target_scope`, `calibration_digest`, `variation_id`, `stage` (the R4 keys) and `application_id` (a recipe
`step_id`); `contracts/validate.py` knows these keys only under the capability, so older specs keep their findings and
a reader without the capability refuses the spec (`contract.unknown_capability`). A correction maps to an instance by
an equal `target_scope` (an artifact fact) or by an `instance_mapping` declaration (declaration-based); a correction
with neither is never broadcast.

## Obligations

The generator reads the suite, roots, instances, spec corrections, response items and catalog compositions, never
bindings or declarations, so masking a binding cannot remove an obligation (V24). One obligation per rule × subject
relation:

| Rule | Subject |
| --- | --- |
| `r-inv.root` | each root |
| `r-map.classification` | each spec correction |
| `r-real.description`, `r-stage.position` | each spec correction × instance |
| `r-rep.repetition` | each root × catalog effect applied on its path |
| `r-comp.composition` | each root × catalog composition |
| `r-comp.factor_values` | each instance × composition with a factor table bound |
| `r-resp.response_use` | each instance |

IDs are `<rule>:<subject>` strings; the inventory is sorted and its digest is the canonical SHA-256 of
`{generator, items}`. Regeneration that differs makes `input_validity` invalid (V67).

## Report

Fields as in C11. `subject_digest` is the bundle digest; `assessment_id` is the canonical SHA-256 of the subject,
suite, rule registry digest, checker code digest, readers and settings. Exit codes 0/1/2/3 with precedence
2 > 1 > 3 > 0. The report is written as a sidecar, never into the bundle.

## M2b ratio subset (`ratio-subset/v1`)

A context may select further suites (`suites`); the inventory is generated over all of them and the report lists
them. `ratio_roots[]` names a ratio of two chain roots (`numerator`, `denominator`), the scope axis they differ in
(`over_axis`), its quantity and unit. The spec's `extension.ratio.cancellations` are the claims:

| Rule | Subject | Decides |
| --- | --- | --- |
| `r-ratio.operands` | each ratio root (or the spec's free-text ratio when there is none) | operands are chain roots with the same quantity, unit and bins, differing in `over_axis` only |
| `r-ratio.cancellation` | each ratio root × claim with treatment `cancels` | exact only for the same calibration item, the same selection (no `by_scope` row per side), the same power from the coverage contract's factors, and a nonzero factor; otherwise the residual is summarized per bin |
| `r-ratio.correlation` | each ratio root × claim with another treatment | a validation record (`validation_record.json`) binding both operands with versions, method, tolerance and scope, or a correlation declaration with a source or a scope; bare text and `verification: true` are not evidence |

Calibration items give a factor as `scalar`, per-bin `values`, or `by_scope` rows keyed by instance scope. Model
cards (`model-card/v1`) are not built: a context selecting that suite is refused (O03).

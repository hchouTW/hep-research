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

## D11b snapshots and migration

Snapshots are files `<canonical sha256>.json` in a store the caller names (`--snapshots DIR`); O07 (where the store
lives and how long it is kept) stays open, so nothing is stored inside the plugin or the bundle. Reproduction rebuilds
coverage contracts, catalog and suites from the store by the lock's digests only. `contracts/migrate.py` writes the
migrated analysis to a new folder; the completion marker is the last file written.

## Phase 0 of the cross-artifact check architecture (2026-10-22)

Changes of release R1 (`cross-artifact-check-architecture.en.md` section 9.1); no rule outcome changes:

- **Version guard (P3, G18).** Rules are dispatched by (rule_id, version) (`IMPLEMENTED` in
  `contracts/analysis_checks/rules.py`); an obligation of a version this checker does not implement is
  `check.rule_not_run`. Suites name generator (id, version) pairs from `obligations.GENERATORS`; another one is
  refused at freeze (`bundle.generator_unsupported`) and dependency-missing at check. Input checks are enabled per
  context version (`context.INPUT_CHECKS`).
- **Source digests.** Registry 1.1.0 records each rule version's function-level source digest
  (`contracts/analysis_checks/source_digest.py`); `rule_registry.py check` fails when the code changes without a new
  version.
- **Checker identity (G10, A1).** The report's checker identity covers every plugin module loaded at run time; the
  generator digest covers `obligations.py`, `model.py` and `effect_catalog.py`.
- **P6 (G20).** With dependency-missing diagnostics or lock differences the status is never `complete` and the exit
  code is 3; differences reproduced from a snapshot (`installed_differences`) may be complete.
- **Snapshots on by default (DR-5, O07 answered for plane A).** `freeze` writes the pinned definitions to
  `<root>/.hep-research/snapshots/` and indexes the bundle in `<root>/.hep-research/bundles.json`; `check` uses that
  store when it exists; `analysis_check.py snapshots gc` deletes only digests no indexed bundle references, dry run
  by default. `--no-snapshots` turns it off.
- **Cheap `check-report` refusals (G11, G19 drift):** `permit.report_dependency_missing`, `_lock_differences`,
  `_prerelease_suite`, `_inventory_mismatch` (`contracts/permit.py` `cheap_refusals`).
- **`assessment.plugin_release`** names the release that produced the report.

`required: false` (DR-2) is unchanged until check-context 1.1.0 (Phase 2).

## Phase 2, release R2: formats (2026-10-22)

Changes of the first R2 slice (architecture sections 8.1 and 9.4); no rule outcome changes yet:

- **check-context 1.1.0 (DR-2).** Roots and ratio roots carry no `required` (`context.required_removed`); a deferral
  is recorded only as an exception. `root_not_required` therefore cannot arise in a 1.1.0 context.
- **Version guard between context and suites.** A 1.1.0 context selects suites at or above 1.1.0 (pre-releases
  included), a 1.0.0 context only 1.0.x suites (`context.suite_version`). Freeze refuses either finding
  (`bundle.context_version`); check reports it as input-invalid.
- **Pre-release suites.** `counting-chain`, `ratio-subset`, `model-card` and `run-lineage` exist as `1.1.0-dev.1`
  with the 1.0.0 rules and generators, so a 1.1.0 context gives the 1.0.0 outcomes. Rule fixes go to later
  pre-releases. `check-report` refuses every pre-release suite (`permit.report_prerelease_suite`).
- **SemVer.** `contracts/semver.py` reads pre-releases with `parse_full`, `is_prerelease` and `precedence`; `parse` and
  ranges still read releases only, so no profile range admits a pre-release.
- **Registry 1.2.0** (schema; the shipped registry stays 1.1.0 until a rule has two versions): rules are keyed by
  (rule_id, version); a retired version stays listed and is not checked for an implementation or a digest.
- **Conversion (V90).** `migrate.py --convert check-context=context-1.0.0-to-1.1.0` drops `required: true`, refuses a
  deferred root for manual completion, and moves each suite to the lowest installed version at or above 1.1.0.

## Phase 2, release R2: input checks of check-context 1.1.0 (2026-10-22)

Enabled only for 1.1.0 contexts (`INPUT_CHECKS["1.1.0"]`, P3), so a frozen 1.0.0 subject keeps its outcomes (the
Phase 0 comparison set of 403 obligations is unchanged). Each finding is input-invalid: freeze refuses it
(`bundle.item_schema` for item shapes, `bundle.context_input` for context fields) and check reports it.

| Check | Gap, V case | Rule |
| --- | --- | --- |
| `calibration.shape` | G16, V79 (first part) | a factor table (`factors` or `factor_table_version`) maps each effect to exactly one of `values` (non-empty list of finite numbers), `scalar` (finite) or `by_scope` (scope → such a list); `tolerance` is `{"relative": finite >= 0}`. Auxiliary inputs of model cards are not factor tables |
| `coverage.duplicate_contract` | G15, V81 | two different bundle coverage contracts for one table: both are dropped, no first-wins |
| `context.shared_within_model` | G12, V80 | a shared parameter joins parameters of different models only |
| `context.unit_placeholder` | G22, V89 (minimal fix) | a root or ratio-root unit that is blank or a placeholder (`TODO`, `TBD`, `?`, `<unit>`, …); the full unit check is coverage extension |

G2 (V78) is closed by the format itself: 1.1.0 has no `required`. The G4 part of V79 (tolerance from declared
significant digits, DR-6) changes a rule and comes with the rule fixes.

## Phase 2, release R2: first rule fixes (2026-10-23)

The first rule changes of R2 (architecture section 8.2: "Yes, only in `1.1.0-dev.N` suites"):

- **Per-rule versions.** `contracts/analysis_checks/rules.py` dispatches by `VERSIONS` (rule_id → the version its
  code is; default 1.0.0). A fixed rule's old code is gone: an obligation naming the old version is unverified
  (`check.rule_not_run`), never evaluated with the new code (P3).
- **G3 (V77): `r-ratio.correlation` 1.1.0.** Every complete validation record for the claimed effect is read; one whose
  relation differs from the spec's gives `check.correlation_contradicted`, citing every contradicting record. 1.0.0
  returned on the first complete record in item-ID order, so renaming the records changed the outcome.
- **G17 (V77): `r-rep.repetition` 1.1.0.** `_exclusion` reads every `partition_exclusive` declaration naming both
  scopes; one that gives both the same selection is a contradiction, and all such declarations are listed (sorted).
  1.0.0 used the first in declaration order. A contradiction decides in both rules, so removing an agreeing record or
  declaration never improves the outcome (P4), and adding one cannot hide a contradiction.
- **Registry 1.2.0.** The 1.0.0 entries of both rules stay listed with `lifecycle: retired` (not digest-checked);
  1.1.0 entries are `kind: changed` with their source digests.
- **Suites `1.1.0-dev.2`.** The same as dev.1 except the two rules at 1.1.0. The conversion `context-1.0.0-to-1.1.0`
  now chooses the newest installed suite at or above 1.1.0. This replaces "the lowest" in the formats section above,
  which was written when dev.1 was the only pre-release and named only versions the checker ran.

Measured on the Phase 0 comparison set (403 obligations, against 0.25.1):

| Contexts | Changed obligations |
| --- | --- |
| 1.0.0 (stable suites) | 99: all 96 `r-rep.repetition` and all 3 `r-ratio.correlation` are now `rule_not_run`; 16 cases go from complete to incomplete (`g3-ba` from inconsistent) |
| 1.1.0 on dev.2 | G3 only: `g3-ab` is now `violated`, the same as `g3-ba`. G2, G15 and G16 change through the earlier R2 input checks |

Tests that need a complete 1.0.0 report for report or permit handling use `cases.r1_rules()`, the current
implementations keyed by rule_id. These stand in for release R1 and give the same outcomes on the reference cases.
Rule tests run on 1.1.0 contexts.

## Phase 2, release R2: factor tolerance from declared significant digits (2026-10-23)

G4 (V79, second part) under DR-6, `r-comp.factor_values` 1.1.0 in the suites `1.1.0-dev.3`:

- **Not used: the table's own `tolerance`.** An agent-writable table could set 0.6 and hide 3.0 against 1.0 × 2.0. The field
  stays valid in the table shape and the outcome says it is ignored.
- **Default:** 1e-9 when nothing is declared (DR-6 keeps 1e-9; the adopted text's 1e-12 is reversed).
- **Declared digits:** an optional integer `significant_digits` d (1..17) on the table. If every value of the relation
  has at most d significant digits (as written, by shortest repr), the tolerance is S · u with u = ½·10^(1−d) and S =
  Σ|power| over all terms of `parent = Π child^power`, the parent counting 1 (DR-6: Σ|power| replaces k). Rounding
  each value to d digits changes the value by at most a relative u, so the ratio parent / Π child^power moves by at most
  a factor (1 − u)^−S, and the rule's measure |parent − prod| / max is at most 1 − (1 − u)^S ≤ S · u. The tolerance
  is never below 1e-9.
- **Checking the values' digits.** If a value has more digits than declared, the declaration is false and is not used
  (the default applies), so declaring fewer digits cannot widen the tolerance.
- **Evidence.** Each outcome carries `tolerance: {relative, basis}`. `tests/contracts/test_analysis_check_r2_rules.py`
  tests the bound on 400 random tables (1–3 factors, powers ±1 and ±2, d from 2 to 7) and a real break at four times the
  tolerance.

Phase 0 comparison set: on dev.3 only `g4-tol` changes from satisfied to violated; on 1.0.0 the 4 `r-comp.factor_values`
obligations become `rule_not_run`.

## Phase 2, release R3: undescribed corrections and the factor key (2026-10-23)

G1 (V86) under DR-8, with the maintainer's scope decision (`decision-architecture.md`, 2026-10-23), and G14 (V87), in
the suites `1.1.0-dev.5`.

**Catalog 1.1.0.**
- Each effect gains `description_required`; it is false only for `bin_width`.
- A coverage contract written for catalog 1.0.0 still reads: the check now requires the same major and a version not
  newer than the installed catalog, instead of exact equality, because catalog minors only add.
- The catalog version is in the lock's member-set closures, so a bundle frozen against catalog 1.0.0 shows a lock
  difference and is reproduced from its snapshots (D11b), as with any definition change.

**Generator `counting-chain-obligations` 1.1.0.**
- New subject kind `applied_effect`: each effect a step of an instance applies, by its coverage contract (`covers`,
  plus the members of a class coverage that lists them). A class coverage with undefined members applies no member
  here (DR-8).
- G14: the factor obligation comes from a factor table bound under the composition's parent or any child key. Two
  different tables both give an obligation, keyed `@<item>`.
- Version 1.0.0 is unchanged.

**`r-real.undescribed` 1.0.0 (new rule).**

| Applied effect | Described by | Otherwise |
| --- | --- | --- |
| `background` | a non-empty `backgrounds` block | `no_backgrounds_reason` → violated `check.description_contradicted`; nothing → violated `check.undescribed_correction` |
| `exposure`, `luminosity`, `livetime` | the observable's normalization kind, as the measurement contract maps them (`NORMALIZATION_CORRECTIONS`; a correction next to it would count it twice), or a correction | violated `check.undescribed_correction` |
| any other effect | a spec correction of exactly that category that applies to the instance; a class name describes no member | an unbound correction → unverified `check.applicability_unbound`; none → violated |
| `bin_width` (`description_required: false`) | — | not applicable, `check.description_not_required` |

**Contract and example changes the broad scope needs.**
- The measurement vocabulary `response_corrections` gains `cutoff_transmission`, `survival` and
  `fragmentation_feeddown`, the catalog effects it lacked (additive).
- The AMS-02 flux-ratio example spec now describes livetime and the cutoff fraction (factors of exposure), survival
  (1 in every bin, synthetic) and fragmentation feed-down (`exact_zero`: no heavier species in the synthetic sample).
  Exposure stays described by the normalization block.
- The reduced and ratio test cases describe the same corrections.

**Phase 0 comparison set.**
- On dev.5:
  - `g1-drop-selection` gives `violated` `check.undescribed_correction`.
  - `g14-child-key` gets its factor obligation.
  - The new corrections' description, stage and classification obligations are satisfied.
  - The positive, ratio, model and run cases stay complete.
- On 1.0.0: the example's added corrections give satisfied description obligations. The earlier `rule_not_run`
  changes are unchanged.

## Phase 2, release R3: stable 1.1.0 suites and full mutation testing (2026-10-23)

**Stable suites.**
- `counting-chain`, `ratio-subset`, `model-card` and `run-lineage` exist as 1.1.0, with the content of `1.1.0-dev.5`
  under the release version. From R3 they are the default (architecture section 8.2).
- `check-report` accepts them; it still refuses the `1.1.0-dev.N` pre-releases, which stay installed for bundles
  frozen during development.
- The conversion `context-1.0.0-to-1.1.0` now chooses 1.1.0, the newest installed.
- The report and permit tests use the real 1.1.0 checker instead of the R1 rules double.

**Full mutation testing (V76).** All nine operators of the diagnostic plane are implemented in
`tests/contracts/analysis_check_mutations.py`:

| Operator | Edit | Invariant |
| --- | --- | --- |
| reorder | every context list and the item list reversed | same states (P5) |
| rename | every declaration ID renamed | same states |
| relabel | every artifact's status labels set to `synthetic` | same states (labels are no evidence, DR-7) |
| copy | each validation record and calibration replaced by a byte copy under a new ID, references rebound | same states (a copy is the same source, DR-3) |
| copy+perturb | a contradicting copy of each validation record added | no gain (P4) |
| drop | every declaration removed | no gain (P4) |
| loosen | the corrections' target scopes removed | no gain (P4) |
| toggle-optional | the corrections' `application_id`, `variation_id` and `factor_of` removed | no gain (P4) |
| edit-report | a finished report's failing states set to satisfied, the summary recomputed | refused by the report check |

The draft operators run on the chain case (1.0.0 and 1.1.0 rules) and on the reduced, ratio and model cases (1.1.0
rules). All invariants hold.

**What edit-report exposed.** The permit's report check accepted such an edit: it verified that the summary follows
from the obligations, and the edit recomputes the summary. The check now also requires each obligation's state to be
the one its reason code gives under its rule version's outcome contract (`_reasons_follow`, `permit.py`; aggregator
codes are unverified for every rule). Every reference report passes it: the chain, reduced, ratio and model cases on
both rule sets, and both run cases.

An edit that also picks each rule's valid satisfied code still passes. Refusing it needs the report to be re-judged,
which the DR-1 split assigns to the assurance plane (B, design only, like G9). A skipped test names it.

**Phase 2 exit conditions** (architecture section 9.4):
- V77 to V90 pass (100 of 100 V parts).
- The shadow review has zero unclassified differences.
- V91 is not registered: DR-14 depends on a value gate that did not pass.


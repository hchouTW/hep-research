# Analysis Artifacts: Specification, Ledgers, Response Card, and Review Report

> Method owner: [hep-analysis](../../../../../skills/hep-analysis/SKILL.md) defines the general method (measurement specifications (schemas: `contracts/`)); implementation in `contracts/`. This module records how AMS-02 analyses apply it. Where a general statement here differs from the owner, the owner's text applies.

## When to read this file

If this session has not read them yet, read the profile's [working rules](../working-rules.md) first.

Read only when the request is to design or write down an AMS measurement as a structured specification, generate a measurement brief or any ledger/registry (selection, background, systematic, response, evidence), run or interpret the deterministic checkers in `scripts/`, or write a formal verdict-first analysis review. Do not load it for a conceptual question or a quick conversion. Field semantics for selections, backgrounds and systematics stay in their canonical homes: [reconstruction-and-data-quality](reconstruction-and-data-quality.md#cut-flow-ledger), [efficiency-acceptance-backgrounds](efficiency-acceptance-backgrounds.md#background-ledger), [calibration-mc-systematics](calibration-mc-systematics.md#systematic-ledger). Evidence rules are in [source-policy](../sources/source-policy.md).

## Contents

1. [Format and provenance rules](#format-and-provenance-rules)
2. [Analysis specification](#analysis-specification)
3. [Artifact templates](#artifact-templates)
4. [Checker scripts](#checker-scripts)
5. [Verdict-first review](#verdict-first-review)
6. [Failure modes](#failure-modes)
7. [Required source classes](#required-source-classes)
8. [Questions to ask the user](#questions-to-ask-the-user)

## Format and provenance rules

- Specifications are **JSON**, or **YAML in a strict subset** read by `<plugin root>/profiles/experiments/ams-02/scripts/yaml_subset.py` (standard library only; the subset and the features it rejects are listed at the end of this section). YAML blocks in other modules are display sketches of the same keys and may use syntax outside the subset (for example `a | b` alternatives); they are not specifications.
- `abs_Z` is the absolute charge number `|Z|`; the sign of the charge is a separate field `charge_sign` (`+1`, `-1`, or `"both"`). Rigidity is in GV, momentum and energies in GeV (momentum in GeV/c), kinetic energy per nucleon in GeV/n.
- Every number that describes AMS (a cut value, a resolution, an efficiency, a systematic size, a cutoff factor) is an entry in `parameters` with a `provenance` of `documented` (needs `claim_ids` in `<plugin root>/profiles/experiments/ams-02/evidence/claims.json`), `general_method`, `proposal`, `user_supplied` or `unknown`. A `documented` entry whose claim is scoped to another species, range, period or analysis is a scope violation, not documentation.
- `unresolved_inputs` lists what the analysis still needs; the auditor reports it as `unresolved`, never as an error.

## Analysis specification

Top-level keys (all present unless marked *if applicable*). The complete minimal example is `<plugin root>/profiles/experiments/ams-02/tests/fixtures/spec_valid.json`.

| Key | Content |
|---|---|
| `spec_version` | `"1"` |
| `measurement` | `title`; `target` (`flux`, `ratio`, `fraction`, `limit`, `parameter`, `discovery`, `efficiency`); `estimand` (one sentence: the quantity, species, variable, range, and what is held fixed); `level` (`detector`, `object`, `flux`: the level at which the result is stated); `species` (list of `name`, `abs_Z`, `A`, `charge_sign`, `mass_GeV`); `variable` (`rigidity`, `momentum`, `total_energy`, `kinetic_energy`, `kinetic_energy_per_nucleon`); `unit`; `range`; `bin_edges`; `sample` (`public` or `internal`) |
| `data_scope` | `data_or_mc`; `period` (`start`, `end`); `mc_scope`; hardware era if relevant |
| `observables` | list of `name`, `subsystem`, `role` (`rigidity`, `charge_sign`, `abs_charge`, `velocity`, `energy`, `lepton_hadron`, `veto`, `direction`, `trigger`) |
| `selections` | selection ledger: `name`, `level`, `definition`, `target_failure_mode`, `conditional_denominator`, `efficiency_source`, `correlated_with`, `validation` (list of `metric`, `threshold`, `action`) |
| `backgrounds` | background registry: `name`, `origin`, `entry_mechanism`, `control_region`, `estimator`, `transfer_model`, `contamination_correction`, `closure_test`, `expected_counts`, `nuisance_parameters`, `correlations` |
| `corrections` | one row per physical effect: `effect_id`, `category` (`veto`, `calibration`, `efficiency`, `acceptance`, `exposure`, `livetime`, `response`), `applied_in` |
| `response` | response card summary: `truth_variable`, `reco_variable`, `variable_conversion` (needed when they differ), `orientation`, `normalization`, `includes` (which of `efficiency`, `acceptance` sit inside the matrix), `matrix_file` (validated by `<plugin root>/core/stats/validate_response.py`; file format in item 5 below) |
| `estimator` | `form` (`diagonal`, `response_model`, `forward_fold`) and `applies` (which of `efficiency`, `acceptance`, `exposure`, `livetime` it multiplies explicitly) |
| `ratio` *(ratios, fractions)* | `numerator`, `denominator`, `cancellations` (list of `effect`, `treatment` in `cancels`/`correlated`/`partial`/`independent`, `correlation_model`, `verification`) |
| `inference` | `method`; `parameters_of_interest`; `approximation` (`exact_poisson`, `toys`, `bayesian`, `gaussian`, `wilks`, `asymptotic`, `s_over_sqrt_b`); `approximation_validated`; `min_expected_counts`; `parameter_on_boundary` |
| `systematics` | systematic registry: `name`, `source`, `affected_objects`, `representation`, `variation_basis`, `effect` (`normalization`, `shape`, `migration`, `mixed`), `applied_via` (`migration`, `nuisance_in_likelihood`, `alternate_sample`, `covariance`, `final_value`), `correlations_across_bins`, `correlations_across_species_or_time`, `validation`, `double_counting_checks` |
| `tail_estimates` | `name`, `process` (`charge_confusion`, `rare_misid`, `other`), `method` (`data_driven_tail`, `mc_tail_validated`, `gaussian_core`), `tail_validation` |
| `validation` | `name`, `kind` (`closure`, `stress`, `stability`, `control`), `metric`, `threshold`, `action` |
| `parameters` | `name`, `value`, `unit`, `provenance`, `claim_ids` |
| `ams_claims` | statements about AMS practice: `text`, `label` (`Documented`, `General method`, `Proposal`, `Unknown/needs input`), `claim_ids` |
| `unresolved_inputs` | list of strings |

Rules that the schema encodes: a correction appears once (`effect_id` is unique across categories); `response.includes` and `estimator.applies` must not overlap; `tail_estimates` may not use `gaussian_core`; a scale or resolution systematic is applied through `migration` (or a nuisance/alternate sample), never `final_value`; a ratio lists each effect it assumes to cancel with a correlation model.

## Artifact templates

1. **Measurement brief** (produced from `measurement`, `data_scope`, `observables`, `unresolved_inputs`): estimand; target and level; species with `abs_Z`, `A`, sign, mass source; variable, unit, range, bins; data or MC scope and period; subsystem roles; what is public versus user-supplied; one line each, pointing to the ledgers below, for selections (with their conditional denominators), backgrounds with their controls, efficiency/acceptance/livetime/response kept distinct, the inference method, and validation as metric-threshold-action; open inputs. When the brief cites a source, state each cited source's verification level from `source-index` (for example main article only, or review-level) next to its claim IDs. One page, symbolic, no invented AMS numbers.
2. **Selection ledger**: the `selections` array; every row has a named conditional denominator and at least one validation with metric, threshold and action.
3. **Background registry**: the `backgrounds` array; every row has an estimator plus a control region or constraint, and a closure test.
4. **Systematic registry**: the `systematics` array; one row per effect, each with its `applied_via`.
5. **Response card**: the `response` object plus the matrix file read by `<plugin root>/core/stats/validate_response.py`:

```json
{
  "metadata": {
    "truth_axis": {"variable": "rigidity", "unit": "GV", "edges": [1, 2, 4, 8]},
    "reco_axis": {"variable": "rigidity", "unit": "GV", "edges": [1, 2, 4, 8]},
    "orientation": "rows_reco_cols_truth",
    "normalization": "conditional_on_selected",
    "inefficiency": "outside_matrix",
    "acceptance": "outside_matrix",
    "underflow_overflow": "explicit_bins",
    "efficiency_applied_separately": true,
    "acceptance_applied_separately": true
  },
  "matrix": [[0.8, 0.1, 0.0], [0.1, 0.8, 0.1], [0.0, 0.1, 0.8]],
  "underflow": [0.1, 0.0, 0.0],
  "overflow": [0.0, 0.0, 0.1],
  "closure": {"truth": [100, 90, 80], "reco": [92, 88, 75]}
}
```

6. **Evidence ledger**: `<plugin root>/profiles/experiments/ams-02/evidence/sources.json` and `<plugin root>/profiles/experiments/ams-02/evidence/claims.json` (fields: source `id`, `title`, `authors`, `year`, `dois`, `url`, `inspire_record_id`, `arxiv_ids`, `tier`, `verification_level`, `access_date`, `publication_date`, `data_taking_period`, `supersedes`, `superseded_by`, `notes`; claim `id`, `claim`, `claim_types`, `support_kind` (`primary`, `absence_search`, `third_party_context`, `general_method`), `source_ids`, `location`, `scope` (`text` plus `species`, `range`, `data_period`, `analysis`), `limitations`, `verification_strength`, `numeric_quotation_allowed`, `last_reviewed`). Add a source or claim only after reading it at the stated level; run the two ledger scripts, then regenerate `source-index.md`.
7. **Verdict-first review**: see the next section.

## Checker scripts

Run from the skill directory. Exit codes: 0 no errors, 1 diagnostics reported errors, 2 input unreadable or malformed. All outputs are JSON on stdout. Results of `ams_kinematics.py` are **[General method]** arithmetic and never measured AMS performance. None of the validators modify the supplied data.

| Script | Purpose |
|---|---|
| `<plugin root>/core/kinematics/relativistic.py` | Rigidity, momentum, energies, kinetic energy per nucleon, bin-edge conversion and Jacobians, first-order mass propagation with an explicit correlation |
| `<plugin root>/core/stats/validate_covariance.py` | Shape, finiteness, symmetry, PSD, correlation bounds, zero-variance rows, conditioning, statistical plus systematic block consistency |
| `<plugin root>/core/stats/validate_response.py` | Axes and edges, normalization under the declared convention, lost probability, empty bins, transpose, double counting, identifiability, optional closure pulls |
| `<plugin root>/core/evidence/ledger.py` | IDs, references, states, supersession, over-strong claims, stale verification |
| `<plugin root>/core/evidence/render_index.py` | Render or check the tables in `evidence/index.md` from the JSON ledger |
| `<plugin root>/profiles/experiments/ams-02/scripts/audit_analysis_spec.py` | Audit a specification (JSON, or YAML by `.yaml`/`.yml` suffix); classify findings as error, warning, proposal, or unresolved; optional verdict-first markdown |
| `<plugin root>/profiles/experiments/ams-02/scripts/yaml_subset.py` | Strict YAML-subset reader used for YAML specifications (`<plugin root>/profiles/experiments/ams-02/tests/fixtures/spec_valid.yaml` is the worked example); `python3 <plugin root>/profiles/experiments/ams-02/scripts/yaml_subset.py FILE.yaml` prints the parsed JSON |

A YAML specification is read with a strict subset: mappings, lists, quoted or plain scalars, comments, one-line `[ ]` and `{ }`, and `|`/`>` block scalars. Anchors, aliases, tags, multiple documents, multi-line flow or quoted scalars, tab indentation and duplicate keys are rejected with a line number (exit 2), never guessed; dates stay strings and `yes`/`no` stay strings, so write booleans as `true`/`false` and quote any plain text containing `: `.

A passing validator means the input is self-consistent under its declared metadata; it does not mean the response is physically valid, the covariance is correct, or the specification is a sound analysis.

## Verdict-first review

Structure, in this order: (1) **Verdict**: one of `blocked` (errors present), `needs work` (only warnings), `acceptable with open inputs` (only unresolved/proposals), with one sentence why. (2) **Defects in priority order**: each with the artifact path, why it changes the result, and the smallest fix. (3) **Proposals**, labeled `[Proposal]`. (4) **Unresolved inputs** and which would change the verdict. (5) **Evidence table**: each AMS statement with its label and claim ID. `audit_analysis_spec.py --markdown` drafts sections 1 to 4; a human review still writes the physics judgement.

## Failure modes

- Reading a passing checker as physical validity; treating auditor silence as approval of a design.
- Filling `parameters` with plausible AMS numbers to satisfy the auditor instead of marking them `unknown`.
- Duplicating the canonical ledger schemas in prose instead of pointing to them.
- Promoting a claim's `verification_strength` without reading the source at that level.
- Repairing a covariance or response silently instead of reporting the defect.

## Required source classes

The artifact schema itself carries no AMS numbers. Any `documented` parameter or claim needs a Tier 1 or Tier 2 source in `<plugin root>/profiles/experiments/ams-02/evidence/sources.json` with a location and scope; general-method parameters cite Tier 4 ([source-index](../../evidence/index.md)).

## Questions to ask the user

Which measurement target and level? Which species, variable, range, and bins? Public or internal work? Which inputs exist (response, efficiencies, control regions) and which are unknown? Do you want a brief, a full specification, or a formal review?

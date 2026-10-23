# v6.3 D09 — reader refusal matrix

Status: measured 2026-10-16. Data: `contracts/rules/refusal_matrix.json`; the current-tree column is a test
(`tests.contracts.test_v63_d09.V59RefusalMatrix`). Labels: **Confirmed** (measured), **Inferred**.

**Method (Confirmed).** New-format samples come from the ratio case of `tests/contracts/v63_cases.py`: a v2 bundle,
its check context and semantic lock, a check report, a validation record, and a spec that declares
`measurement:correction-keys-v1`. Each old entry point runs on them as a CLI. The release column used the 0.11.0 tree
(`git archive hep-research--v0.11.0 plugins/hep-research`) and the same samples.

| New format | Old entry point | This tree | 0.11.0 release | Evidence | Release blocker |
| --- | --- | --- | --- | --- | --- |
| analysis bundle 2.0.0 | `analysis_bundle.py verify` | refuses | refuses | `status: invalid` (schema.const on format, bundle_version) | no |
| check-context 1.0.0 | `validate.py` | refuses | refuses | `schema.required` (not an artifact envelope) | no |
| semantic-lock 1.0.0 | `validate.py` | refuses | refuses | `schema.required` | no |
| check report 1.0.0 | `validate.py` | refuses | refuses | `schema.required` | no |
| validation record 1.0.0 | `validate.py` | refuses | refuses | `schema.required` | no |
| check-context 1.0.0 | `review_measurement_spec.py` | refuses | refuses | exit 2, "not a measurement-spec" | no |
| check-context 1.0.0 | `dependencies.py` | **accepts** | **accepts** | `status: ok`, exit 0: a file without inputs passes | **yes, until reviewed** |
| result binding 1.0.0 (M2c) | `validate.py` | refuses | refuses | exit 1, `schema.required` (not an artifact envelope) | no |
| result binding 1.0.0 (M2c) | `review_measurement_spec.py` | refuses | refuses | exit 2, "not a measurement-spec" | no |
| result binding 1.0.0 (M2c) | `dependencies.py` | **accepts** | **accepts** | `status: ok`, exit 0, `formal_use_allowed` false: the same documented behaviour as for a check context | **yes, until reviewed** |
| spec with the capability | `recipe_semantics.py --upstream` | implements (since G-ENFORCE step 1) | **exposes** | this tree reads the keys under the capability it implements and refuses an unknown capability (`semantics.upstream_unknown_capability`); 0.11.0 reads keys without checking (V59) | no (this tree) |
| spec with the capability | `validate.py` | implements | refuses | 0.11.0: `contract.unknown_capability` | no |
| analysis bundle 2.0.0 | `attestation.py` (bundle digest) | implements | refuses | 0.11.0 digests it as an execution bundle (`attestation.bundle_changed`) | no |

`permit.py` and `attestation.py` read a bundle only through `analysis_bundle.py` (v1), so they refuse a v2 bundle
through the first row (**Inferred** from `contracts/permit.py`). D10 adds the advisory `permit.py check-report`, which
reads a v2 bundle, and gives `attestation.py` the v2 digest rule.

**Blockers (Inferred).** Neither non-refusing row misreads a field today:
- `dependencies.py` finds no inputs in a context and calls it consistent.
- `recipe_semantics.py` uses the R4 keys with exactly the meaning the capability gives them.

A v2 bundle or a capability spec should still not ship to users of these readers until each refuses explicitly (or
the behaviour is documented as intended and reviewed). The V59 rule holds: **not released before a real refusal
threshold exists.**

## G-ENFORCE step 1 (2026-10-16)

- **`recipe_semantics.py --upstream`: fixed (Confirmed, `tests.contracts.test_v63_refusal_blockers`).** It now refuses an
  upstream artifact that requires a capability it does not implement, and reads the correction keys only under
  capabilities it implements. The 0.11.0 release reads the same R4 keys with the same meaning, so a 0.11.0 reader of a
  capability spec does not misread it. It would read any later capability unchecked; that is already released and
  is recorded, not fixable here.
- **`dependencies.py`: documented, awaiting review (Inferred).** Its module docstring states that an artifact with no
  inputs, or `{}`, "is consistent but is not thereby allowed". It reads no field of a check context, and its verdict
  is only about dependencies. Making it refuse non-envelopes would change documented behaviour and existing tests,
  so the row stays a blocker until a non-author reviewer accepts this rationale (G-ENFORCE step 2) or asks for a
  refusal.

## Phase 2, release R2 formats (2026-10-22)

Measured with the installed 0.25.1 release (`~/.claude/plugins/cache/hep-research-dev/hep-research/0.25.1`) on a
bundle frozen by the R2 development tree (check-context 1.1.0, suite `counting-chain` 1.1.0-dev.1). **Confirmed:**

| Reader | Result |
| --- | --- |
| 0.25.1 `analysis_check.py check` | exit 1, status `invalid`: `check_context.schema.const` (context_version), `check_context.schema.pattern` (the pre-release suite version), `definition.suite_missing`; nothing is evaluated under 1.0.0 semantics |
| R2 development `analysis_check.py check` | exit 0, status `complete` |
| `permit.py check-report` (R2) | refuses the report (`permit.report_prerelease_suite`) |

No release blocker: an old reader refuses the new format instead of misreading it.

## Phase 2, release R2: result binding 1.1.0 (2026-10-23)

Measured with the installed 0.25.1 release on a campaign case from the R2 development tree: check-context 1.1.0, suites
`1.1.0-dev.4`, and result binding 1.1.0 with `campaigns[].inputs`. **Confirmed:** `analysis_check.py check --results`
exits 1 with status `invalid`. The input diagnostics include `result_binding.schema.const` (binding_version) and
`result_binding.schema.additional` (`inputs`), next to the 1.1.0 context findings already recorded above. Nothing is
evaluated under 1.0.0 semantics. No release blocker.

## 0.28.0: model-card and run-lineage removed (2026-10-23)

Architecture section 13.4, step 3 (the value gate's Shrink decision, `decision-value-gate.md`): readers refuse the
removed formats with the reason, never read them with other code and never drop them silently.

| Input to 0.28.0 | Result | Test |
| --- | --- | --- |
| `freeze` of a model-only bundle (`mode: model`) or with a `model-card` item | refused, `bundle.removed` | `test_analysis_check_r3.ShrinkRemoval` |
| `freeze` of a context that selects `model-card` or `run-lineage` | refused, `bundle.removed` | `test_analysis_check_r3.ShrinkRemoval`, `test_analysis_check_ratio_rules` |
| `check` of a frozen bundle whose context names a removed suite | dependency-missing `definition.suite_removed` (incomplete, exit 3) | `test_analysis_check_r3.ShrinkRemoval` |
| `check` of a frozen model-only bundle | input invalid: verify reports `bundle.removed` for its mode | `test_analysis_check_r3.ShrinkRemoval` |
| `check --results` or `--project` | usage error (exit 2) with the reason | `test_analysis_check_r3.ShrinkRemoval` |
| `permit.py check-report` with a post-execution report (result binding, per-root evidence levels) | refused, `permit.report_post_execution_removed` | `test_analysis_check_report_permit` |
| `permit.py check-report` with a model-only bundle | refused, `permit.report_model_only` | (unchanged) |

Every refusal names 0.27.x as the release that still reads the format.


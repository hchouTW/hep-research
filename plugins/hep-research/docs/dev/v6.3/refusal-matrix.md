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
| check-context 1.0.0 | `dependencies.py` | **accepts** | **accepts** | `status: ok`, exit 0: a file without inputs passes | **yes** |
| spec with the capability | `recipe_semantics.py --upstream` | **exposes** | **exposes** | reads the correction keys (`repeat_undetermined`) without checking `required_capabilities` (V59) | **yes** |
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

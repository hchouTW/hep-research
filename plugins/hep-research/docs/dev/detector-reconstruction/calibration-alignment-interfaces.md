# Calibration and alignment interfaces (handoff, R37)

Status: written in T06 (P1). This file is the handoff to the later calibration and alignment plan (the C&A plan). It lists every interface reserved by R32-R36, with its status, its file locations and its fixtures. Paths are relative to `plugins/hep-research/`.

This plan derives no constants, performs no alignment and claims no calibration or alignment quality (R31). A passing check here shows that an interface behaves as stated on synthetic fixtures, nothing more. Payload sidecars hold a digest of their native content; they hold no constants.

Status words: **tested** means the interface has checks that pass on synthetic fixtures. **Designed** means the interface is specified and has no check yet; its owning task tests it. **Gap** means a backend cannot provide it, on a recorded probe (R37); a gap is never marked not-applicable.

## Interfaces

| Rule | Interface | Status | Owner | Location | Fixtures and checks |
| --- | --- | --- | --- | --- | --- |
| R32 | Payload shape: kind, producer, IOV, parametrization and frame, derived against, uncertainty, loop, constraints used, unconstrained modes, nominal or measured | Tested | T06 | `contracts/schemas/conditions_payload.json`, `contracts/conditions.py` | `calibration_payload`, `alignment_payload` in `tests/contracts/reconstruction_fixtures.py`; `PayloadShape` in `tests/contracts/test_reconstruction_conditions.py` |
| R32 | Identity by content; the tag is outside it | Tested | T06 | `payload_identity` in `contracts/conditions.py` | `SameTagNewContent` |
| R32 | Nominal geometry identity is the released `geometry_id` (D2) | Tested | T06 | `derived_against.geometry_id` in `conditions_payload.json`; `contracts/schemas/ext_computational_run.json` | `GeometryIdentity` |
| R32 | Validity: intersection on one axis, predicates across coordinates | Tested | T06 | `iov_holds`, `iov_intersection` in `contracts/conditions.py` | `ValidityIntervals` |
| R32 | Every product records the identity and round of each payload consumed: `conditions_used` and each `round` are required, and `check_used` refuses a missing or wrong round, a wrong origin, and a payload whose content is not its identity. A re-tag is not a change: identities decide. That a product lists every payload it really consumed is checked for per-key frames only; otherwise it needs the runtime evidence of T07 onward | Tested | T06 | `conditions_used` in `contracts/schemas/reconstruction_product.json`; `used_payload` in `reconstruction_common.json`; `check_used` | `RecordedConditions` in `tests/contracts/test_reconstruction_records.py`; `ConsumedRound`, `StoredIdentities`, `NominalAndMeasured` in `tests/contracts/test_reconstruction_conditions.py`; `test_used_payload_must_be_recorded` |
| R32 | Per-key payload binding across an IOV change | Tested | T06 | `frames` block; `check_frame_conditions` in `contracts/reconstruction.py` | `frame_witness`; `ConditionsPerKey` in `tests/contracts/test_reconstruction_frames.py` |
| R33 | Subset payload with its own identity and the payload it came from | Tested | T06 | `derived_from` in `conditions_payload.json` | `test_derived_subset_has_its_own_identity_and_source` |
| R33 | Track-fit output: per-measurement residuals by state, derivatives, incidence and path, per-track charge, `q/p`, topology | Designed | T07 | Not yet written; the output schema follows the backend (K02) | `CAI-T07-1` to `4` |
| R34 | Reduced retention (raw, waveform or conditions snapshot removed) must state what it can no longer support, and removed levels are not recomputable. The declaration is checked, not whether it is correct for a real product | Tested | T06 | `retention`, `lost_recalibrations` in `reconstruction_product.json`; `can_recompute` | `SamplingAndRetention` in `tests/contracts/test_reconstruction_pulse.py` |
| R34 | Raw quantities really retained beside calibrated values | Designed | T07, T08 | Not yet written | `CAI-T08-1`, `CAI-T08-2` |
| R34 | Chain order of applied payloads | Designed | T07, T08 | `conditions_used` holds the order; no check of a real chain yet | `CAI-T08-1`, `CAI-T08-2` |
| R34 | Stable channel identifiers, cluster track associations, cell path lengths | Designed | T08 | Not yet written | `CAI-T08-1`, `CAI-T08-2` |
| R35 | Time hits before and after each correction step, event-time source and weights, dE/dx samples | Designed | T10 | Not yet written | `CAI-T10-1`, `CAI-T10-2` |
| R36 | Rounds are separable: a payload records its family and round, a product the round it consumed, checked against the payload, and reuse follows identity only, with a new dependency also invalidating | Tested | T06 | `loop` in `conditions_payload.json`, `round` in `conditions_used`, `check_used`, `reuse_decision` | `test_rounds_are_separable`, `ConsumedRound`, `test_added_dependency_invalidates` |
| R36 | Final-round delivery and iteration status of non-final outputs | Designed | T12 | Not yet written; the fixed final-round rule stays in `skills/hep-detector/references/calibration-and-alignment.md` (G06) | `CAI-T12-1`, `CAI-T12-2` |

## T06 acceptance items

| ID | Requirement | Check |
| --- | --- | --- |
| `CAI-T06-1` | A payload change under the same tag triggers invalidation | `SameTagNewContent`: identities differ under one tag, `reuse_decision` refuses, derived payloads follow through `affected_payloads`, a stale stored identity does not pass as fresh, a new dependency invalidates, unknown dependencies disable reuse (K07) |
| `CAI-T06-2` | Nominal and measured payloads are kept apart | `NominalAndMeasured`: same content gives two identities; `check_binding` and `check_used` refuse either one in the other's place |
| `CAI-T06-3` | A constraint used in the derivation cannot be its independent validation | `ConstraintIsNotValidation`. This is also the P1 part of A37; A37 itself and Section 9.6 stay in T10 and T12 |
| `CAI-T06-4` | A different nominal geometry or upstream chain is refused or flagged | `DerivedAgainst`: `check_binding` refuses a different geometry, an unstated one, and a changed or reordered chain |

## Gaps

None recorded. T07, T08 and T10 record any gap here, on a recorded probe, and every Section 18.2 report lists it as open.

Probed: `CAI-T07-3`, how a corrected payload reaches ACTS 48.2.0. Jobs 7490742 and 7491894 ran `adapters/acts-tracking/assets/native/cai_payload_probe.cpp` on noiseless tracks. A plane owned by a `SurfacePlacementBase`, with the transforms in the `GeometryContext`, and a rebuilt geometry both work, for each degree of freedom of one plane, so this is no gap. Later stages use the placement route (user's choice 16). Not yet an interface: a payload file, its mapping to plane deltas, a driver flag. The driver refuses a field until the refit's prior on `q/p` is settled. R33-R35 extras are not yet probed.

## Boundaries for the C&A plan

- Payload kinds are calibration constants, channel masks and alignment parameters. C0, C1 and C2 outputs enter through these kinds; a further kind is a new schema version.
- Conditions tags stay exactly as their source gives them (N11). Invalidation compares identities, never tags.
- Methods, weak-mode validation and loop rules stay in `skills/hep-detector/references/calibration-and-alignment.md` (R01).
- No conditions database or service is built (Section 3.1).

# T05: task sheets and migration

State: done-provisional for P1; P2 onward list blockers (K14). Paths are relative to `plugins/hep-research/`. Nothing here is applied in P0 (R07). Every path, version and failing ID is re-checked after the re-baseline onto 0.57.0 (D1), which comes before T06.

## Corrections carried into T06 (R17)

Line numbers are at this baseline and move with it.

| Gap | File | Current text | Correction |
| --- | --- | --- | --- |
| G01 | `skills/hep-detector/SKILL.md`, Workflow step 5 | "Write the `response` artifact, then run ..." for every task | "When the deliverable is a response product, write the `response` artifact, then run ..."; other detector tasks skip this step |
| G02 | `skills/hep-detector/references/event-reconstruction.md`, line 299 | "without t0 report no absolute position" | "Without an external t0, first check qualified internal or joint constraints. Restrict delivery to no absolute position only if the information remains insufficient." |
| G03 | `skills/hep-computing/references/analysis-workflows.md`, lines 15 and 91 | A rerun is byte-identical, and a changed hash means a changed result | Apply this to recipes that declare byte reproducibility. Others declare numerical or statistical reproducibility, with their comparators (Section 14.1) |

G04-G06 are handled in contract-map.md and T12. G07 stands: control rules are not qualified; mode M1.

## T06 (P1): contracts and corrections

- **Background / Objective:** closed schemas cannot hold reconstruction semantics. Add the sidecars of contract-map.md, W1-W7 fixtures and the G01-G03 corrections, without changing old behaviour.
- **Scope / Non-goals:** semantics for all BPs at contract level. No backend, solver or conditions database; no calibration or alignment constants (R31).
- **Files, confirmed:** `contracts/schemas/`, `contracts/validate.py`, `contracts/__init__.py`, the three G files. **Proposed:** sidecar schemas and validators, witness fixtures and tests under `tests/contracts/`; exact names per K04.
- **Interfaces:** contract-map.md. Unknown required extensions stop the reader (K13).
- **Steps:** re-baseline; redo the contract map on the current contracts; for each witness write the negative check first, then the minimal change.
- **Acceptance:** W1-W7 positive and negative assertions; A02, A03, A06, A08, A09, A16, A18, A25, A41; contract parts of A19-A24; `CAI-T06-1` to `4`; old-recipe comparison unchanged. W2 compares with its analytic solution. Tolerance is fixed in the test before the first run. Commands: the Section 17.2 list, `run_all_checks.py --part static` gating each commit, the unit suite in an approved job.
- **Evidence / Open items:** T2-code. Contracts version assigned at merge, since g4sim also bumps it. Stop if a witness needs a field marked inexpressible.

## T14 (P1): bounded inspector

- **Background / Objective:** form per-product signatures from readable inputs, or stop.
- **Scope / Non-goals:** the plugin's JSON and CSV products first (K15). ROOT files stay unknown until `uproot` is approved. No detector inferred from a file name.
- **Files:** all proposed; named by K04 and K15.
- **Interfaces:** input signature sidecar; probes come only from known readers with fixed parameters; text in data is never run.
- **Steps:** after T06: fact record, conflict handling, budget stop.
- **Acceptance:** A43-A49, A59, and the recognition part of A16. Probe cost visible. Budget exhausted ends in unknown with a stop reason.
- **Evidence / Open items:** T2-code. Depends on T06.

## T15a (P1): offline index and selection record

- **Background / Objective:** finite candidate index and replayable selection on artificial fixtures, before any runner integration.
- **Scope / Non-goals:** rules only. No claim about selection on real recipes.
- **Files:** all proposed; `selection_record` per K04.
- **Interfaces:** AND/OR predicates with unknown never true.
- **Steps:** after T14: DS1, DS2, DS3 fixtures, predicates, record.
- **Acceptance:** DS1-DS3, A47, A52, A60. DS1 with a cost cap of 2 gives "no qualified candidate". DS2 with internal evidence unknown and external missing does not pass. DS3 claims no confirmed policy.
- **Evidence / Open items:** T2-code. K16's gates are the user's; fixtures use artificial values only.

## T07-T10 (P2, P3): blocked

| Task | Blocked on | Can be fixed now | Added acceptance |
| --- | --- | --- | --- |
| T07 tracking, vertexing | T06, K09 for pass or fail | Sheet in t07-t09-task-sheets.md | `CAI-T07-1` to `4`; R33 |
| T08 calorimetry | T06, K09 for pass or fail | Same | `CAI-T08-1`, `CAI-T08-2`; R34 |
| T09 photon likelihood | T06, K09 for pass or fail | Same | Live, unhit and dead controls; no data-side truth |
| T10 timing, PID, non-hit, scan replay | T06; a native scan or global solver (R14) | W6 and W7 inputs | `CAI-T10-1`, `CAI-T10-2`; R35 |

Exact APIs are written only after versions are chosen (Section 16). T06 also creates `calibration-alignment-interfaces.md`, the handoff file R37 requires.

## T11-T13, T15b, T16

| Task | Prerequisite | State | Note |
| --- | --- | --- | --- |
| T11 coverage design | K01, K08; network for sources (R14) | In progress: t11-cells.md covers 27 families | The 11 families without text need sources. Cells stay `source-unverified` without network approval |
| T12 reprocessing, performance | T07-T10; GPU for A13 | Blocked | `CAI-T12-1`, `CAI-T12-2`. A13 is `blocked-by-resource` (R14) |
| T13 AI evaluation | K11, holdout | `blocked-by-decision` | |
| T15b two-candidate selection | T15a, T03 domain, K16 | `blocked-by-decision` | |
| T16 selection benchmark | T15, T07-T10, T12 | Blocked | |

## `CAI-` items (R37)

| Task | IDs |
| --- | --- |
| T06 | `CAI-T06-1`, `2`, `3`, `4` |
| T07 | `CAI-T07-1`, `2`, `3`, `4` |
| T08 | `CAI-T08-1`, `2` |
| T10 | `CAI-T10-1`, `2` |
| T12 | `CAI-T12-1`, `2` |

## A-ID to T-ID (R20)

Sources: Section 16.1's acceptance lists, then R20's defaults. T09 names no scenario in Section 16.1; its acceptance is BP06's.

| A-ID | Work package | Tasks |
| --- | --- | --- |
| A01 | P1/P2 | T07 |
| A02 | P1/P4 | T06 |
| A03 | P1/P3 | T06 |
| A04 | P1/P5 | T12 |
| A05 | P1/P5 | T07 |
| A06 | P1 | T06 |
| A07 | P1/P3 | T07 |
| A08 | P1/P2 | T06 |
| A09 | P1/P2/P6 | T06 |
| A10 | P1/P3 | T12 |
| A11 | P1/P3/P5 | T12 |
| A12 | P2/P5 | T12 |
| A13 | P5 | T12 |
| A14 | P4/P5 | T12 |
| A15 | P5/P6 | T08, T12 |
| A16 | P1/P6 | T06, T14 |
| A17 | P1/P2 | T07 |
| A18 | P1/P5 | T06 |
| A19 | P1/P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A20 | P1/P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A21 | P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A22 | P1/P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A23 | P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A24 | P1/P4 | T06 contract part, T11 design, T10 runtime if covered, else recorded gap |
| A25 | P1/P4/P5/P6 | T06 |
| A26 | P1/P4/P5/P6 | T12, T11 design |
| A27 | P1/P4/P5/P6 | T12, T11 design |
| A28 | P1/P4/P5/P6 | T12, T11 design |
| A29 | P1/P4/P5/P6 | T12, T11 design |
| A30 | P1/P4/P5/P6 | T12, T11 design |
| A31 | P1/P4/P5/P6 | T12, T11 design |
| A32 | P1/P4/P5/P6 | T08, T12, T11 design |
| A33 | P1/P4/P5/P6 | T12, T11 design |
| A34 | P1/P4/P5/P6 | T12, T11 design |
| A35 | P1/P4/P5/P6 | T12, T11 design |
| A36 | P1/P4/P5/P6 | T12, T11 design |
| A37 | P1/P3/P5 | T10, T12 |
| A38 | P1/P2/P5 | T08 |
| A39 | P1/P2/P4/P6 | T07 |
| A40 | P1/P5 | T12 |
| A41 | P0/P1/P6 | T06 |
| A42 | P0/P2/P5 | T12 |
| A43 | P1/P6 | T14 |
| A44 | P1/P6 | T14 |
| A45 | P1/P4/P6 | T14 |
| A46 | P1/P6 | T14 |
| A47 | P1/P4 | T14, T15a |
| A48 | P1/P4 | T14 |
| A49 | P1/P6 | T14 |
| A50 | P2/P5/P6 | T15b |
| A51 | P2/P5 | T15b |
| A52 | P1/P6 | T15a |
| A53 | P2/P5 | T15b |
| A54 | P0/P5/P6 | T16 |
| A55 | P4/P5/P6 | T16 |
| A56 | P1/P5 | T16 |
| A57 | P1/P5/P6 | T16 |
| A58 | P2/P5 | T16 |
| A59 | P1/P6 | T14 |
| A60 | P1/P5/P6 | T15a |

P0 parts of A41, A42 and A54: A41 is decided in contract-map.md. For A42, imports were checked at this baseline: `contracts` and `core` resolve inside the worktree. A54 is the rule in K18.

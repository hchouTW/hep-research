# Researcher Journeys (J1–J12)

Status: M1 desk trace, 2026-10-02. Each journey is traced through skills, contract artifacts, and profiles.
Labels: `[Confirmed]` = backed by a file or test that exists now; `[Proposal]` = design not yet built; `[Unresolved]` = open.
Profiles named below (`experiment:ams-02`, `experiment:synthetic-collider`, `theory:qed-benchmark`) **do not exist yet**; they are built in M2/M3.

Evidence for the contract parts: `contracts/fixtures/artifacts/valid/*.json` and `tests/contracts/test_contracts.py`.

| ID | Primary skill → handoffs | Artifacts in order | Profiles / resources loaded | Gaps found in M1 | Status |
|---|---|---|---|---|---|
| J1 AMS flux + correlated ratio | hep-analysis → detector-response → hep-statistics → research-communication | `measurement-spec` (ratio block with cancellations, `exposure` normalization, list of periods) → `response` → `statistical-result` → `communication` | `experiment:ams-02` registry entry, `index.md`, species/period/subsystem modules only | Ratio cancellations were missing from the measurement extension: **fixed in M1** (`ratio` block, fixture `measurement_ratio.json`, negative fixture without correlation model) | Executed in M2 (Path A) |
| J2 Detector physicist (resolution/calibration) | detector-response → hep-statistics | `dataset-record` with quantity `resolution` / `efficiency` / `scale` at level `detector`, or `response` | AMS subsystem module only | No `resolution` or `scale` quantity type: **fixed in M1** (core vocabulary). A dedicated performance-report extension is not added; reports use `dataset-record` + `communication` `[Proposal]` | Executed (synthetic): `examples/detector-resolution/run_j2.py` (resolution and efficiency records at detector level, constant-width fit, replicate pulls); T07 (M4) |
| J3 Non-AMS experimentalist | hep-analysis → detector-response → hep-statistics | `measurement-spec` (`integrated-luminosity`) → `response` → `statistical-result` | `experiment:synthetic-collider` only | None in contracts (`measurement_collider.json` validates) | Executed in M3 (Path B) |
| J4 Analytic theorist | hep-theory (↔ hep-computing) | `theory-spec` (+ derivation record) → `prediction` → `computational-run` for numerics | `theory:qed-benchmark` only; no experiment resources | Theory spec forbids experiment fields and experiment bindings `[Confirmed]` (`theory_experiment_field.json`, `theory_experiment_binding.json`) | Executed in M3 (Path C) |
| J5 Phenomenologist, fold + fit | hep-theory → hep-statistics → research-communication | `prediction` → `comparison-spec` (gate result, forward-fold transformation owned by detector-response) → `statistical-result` | theory + experiment profiles, bound independently | Full comparison gate is M4; conventions part exists (T25) `[Confirmed]` | Executed in M4 (Path D) |
| J6 Published-data comparison | hep-theory → hep-statistics | `dataset-record` (status `published`, evidence IDs, no detector fields) + `prediction` → `comparison-spec` → `statistical-result` | Dataset record only; the record may name an experiment profile without loading it | None in contracts: published-shape record validates with no response or detector fields `[Confirmed]` (`TheoryIndependenceTests.test_dataset_record_without_detector_modules`) | T24 (M4) |
| J7 Recasting | hep-theory → detector-response (parametrized) → hep-statistics | `prediction` in published observable space → `response` with `form: parametrized` → `statistical-result` | Dataset record; optional interchange adapters (`proposed`) | Response extension required matrix axes: **fixed in M1** (`form: parametrized`, axes may be `not-applicable`, parametrization with validity range required) | Executed (synthetic): `examples/recasting/run_j7.py` (parametrized efficiency map with validity range, gate with forward fold, CLs coupling limit; outside-range refusal) |
| J8 Computational theorist | hep-computing ↔ hep-theory | `computational-run` (seeds, tolerances) + `theory-spec.checks_run` | none | None | T14, T15 (M3) |
| J9 Physics-ML researcher | physics-ml → hep-statistics | `ml-artifact` (grouping key required, training domain) → `statistical-result` | none | None | T16 (M4) |
| J10 Writing up | research-communication | `communication` (claims → result refs, sources read with level) | Evidence records of cited claims only | None | Desk-check |
| J11 Collaboration member, private knowledge | any, via project config | any; private evidence by path | `local_profile_paths` validated by the same validator, resolved from the project, never copied into the plugin `[Confirmed]` (`ProjectConfigTests`, `local_profile` fixture) | None | T27 (M4) |
| J12 Domain outside v1 | closest owner (hep-theory / hep-statistics) | as needed | none | Limited-support behavior is the stanza's step 4 `[Confirmed]` (`contracts/stanzas/context-resolution.md`) | Routing cases (M5) |

## Handoff termination

Every chain above ends at a deliverable the user asked for, or at a reported blocker. No skill hands back to its producer for the same artifact, and the routing contract forbids handoffs that loop (`docs/routing-contract.md`). Live termination is tested with routing cases in M5 (AC20).

## Known limitations recorded in M1

- Detector performance studies (J2) have no dedicated typed extension; they use `dataset-record` with detector-level quantities. Revisit if M4 handoff tests show missing fields.
- Load traces for "no detector modules loaded" (J6) can only be observed in a live headless run, which needs approval at M5 (host fact 5.1 #7 unresolved).

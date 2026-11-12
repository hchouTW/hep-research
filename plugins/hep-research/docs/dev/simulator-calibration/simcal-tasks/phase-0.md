# Simulator calibration phase 0: Abstract model and contracts

## Background

Phase 0 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3578). This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 0 of §17 so that its gate holds: The negative tests of the contract, use and grade rules (the exhaustive tests of Appendix C and the named cases of §15.3) and of P4 pass; the three fixtures can derive candidate methods and reachability

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [x] Seven schemas; the DAG format, injection-point splitting, three fixtures (ECAL, RICH, tracker; ECAL and tracker each contain a pair of overlapping modules, for tests of redundant measurements); the **graph structure** of the toy detector and subgraph variants (DAG only, no simulation); `calib_chain` (candidate methods, P4); contract, data release and plan schemas; `calib_contract check`; in `calib_deps`, hash references, cycle checks and derivation of upstream roles from usage; `calib_use` (per the decision table of Appendix C, including the `incomplete` of rule 0); in `calib_data`, raw-unit lineage, validation-read and fit-read events (including registration of read channels and contract drafts), failure records (`pending`/`final`/`withdrawn`), and derivation of the reuse input (Appendix C.1); acyclic computation of version ids

**Placement bullets of §17 (verbatim; they place work in phases 0 and 2)**

- The cases in §15.3 that depend on `calib_validate.py` behavior (in §15.3.14, "submitting a decision record after abandonment is rejected" and "abandoning after the decision passes is rejected") are acceptance-tested in phase 2; phase 0 acceptance-tests only the grade function, using hand-written decision-record stubs.
- Locking-stage checks that need quantities produced by the model are added in phase 2 (after the joint likelihood and the design-stage Asimov are delivered):
  - the rounding-negligibility condition of §2.1, N_decl/N_exp of validation shapes, the n_min lower bound of shape summary statistics and the block-conversion condition are all computed by `calib_data.py` and called by `calib_contract.py check`;
  - Σ_boot of P5 and the b_J item of P5 (§8.2 note 3; it needs K_l from the design-stage MC) are decided by `calib_design.py`.
  - The phase-0 `calib_contract.py check` does not contain these rules; it only checks that the declarations exist.
- In phase 0, the failure-record state transitions are tested with hand-written decision-record stubs; `calib_validate.py` is retested with real decision records after it is delivered in phase 2.

**Scripts and homes (Inferred from §13, §14 and the content)**

- [x] `calib_chain.py` (DAG, injection-point split, candidate methods, P4)
- [x] `calib_contract.py check` (contract rules of §5.2; in phase 0 only the declarations of the locking-stage checks, §17)
- [x] `calib_deps.py` (hash references, cycle checks, upstream roles from usage)
- [x] `calib_use.py` (Appendix C decision table, rule 0 `incomplete`)
- [x] `calib_data.py` (raw-unit lineage, read events, failure records, reuse input of Appendix C.1)
- [x] `contracts/` (the seven abstract-object schemas; contract, data release, plan and result schemas; §13)

**This phase's tests (Inferred; refresh from §15)**

- [ ] Appendix C exhaustive tests (with the reference implementation `calib_use_decision_table.py`, `c5279adf…`)
- [ ] §15.3.1 (P4)
- [ ] §15.3.2
- [ ] §15.3.3
- [ ] §15.3.11
- [ ] §15.3.12
- [ ] §15.3.13
- [ ] §15.3.14 (with hand-written decision-record stubs, §17)
- [ ] §15.3.15
- [ ] §15.3.17 (dependency and use rules)
- [ ] §15.3a (phase-0 cases: lineage, failure records, acyclic ids, `incomplete` aggregation)

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- Any simulation of the toy detector (phase 1); the locking-stage checks that need model quantities (phase 2, §17)
- `calib_validate.py` behavior beyond the grade function (phase 2, §17)
- Every g4sim item (phase 3 and later)

## Repository Context

Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-0`.
2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-0.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- D5 (line 4089; needs the author): approved, record A6 of `simcal-approvals.md` (2026-11-10)
- D11 (line 4095; needs the author): approved, record A6 of `simcal-approvals.md` (2026-11-10)

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- none

Accepted or decided items that this phase implements (their text in Part B is normative):

- D13 (line 4097; accepted 2026-11-09)
- D15 (line 4099; accepted 2026-11-09)
- D20 (line 4104; accepted 2026-11-09)
- D22 (line 4106; accepted 2026-11-09)
- D23 (line 4107; accepted 2026-11-09)
- D24 (line 4108; accepted 2026-11-09)
- D27 (line 4111; accepted 2026-11-09)
- D32 (line 4116; accepted 2026-11-09)
- D38 (line 4122; accepted 2026-11-09)
- D60 (line 4144; accepted 2026-11-09)
- D63 (line 4147; accepted 2026-11-09)
- D64 (line 4148; accepted 2026-11-09)
- D66 (line 4150; accepted 2026-11-09)
- D69 (line 4153; accepted 2026-11-09)
- D74 (line 4158; accepted 2026-11-09)
- D78 (line 4162; accepted 2026-11-09)

#### Thresholds and test designs

**Gate (§17, verbatim)**: The negative tests of the contract, use and grade rules (the exhaustive tests of Appendix C and the named cases of §15.3) and of P4 pass; the three fixtures can derive candidate methods and reachability

**§8.7 rows of this phase (verbatim)**:

- none

**Test design of the gate (registered before the gate run; no tolerance, no threshold to calibrate)**:

1. *Exhaustive tests of Appendix C*, scope as Appendix C defines it: the reference's own cases (197,376 own input combinations, each with no upstream and every single upstream, and the ordered pairs of upstreams for those reaching `validated-in-scope` under some resolution): 31,593,216 cases, enumerated by the reference implementation `reference/calib_use_decision_table.py` (SHA-256 `c5279adf…`, checked before every run). Harness `tests/core/calibration_exhaustive.py`; shard k of n takes the cases with index i, i mod n = k − 1, in the reference's order.
   - **agree**: `calib_use`'s `assign`, `effective`, `allowed_uses`, `variation_upstream_admissible` and `derive_role` equal the reference's on every case (same value, or both reject). Pass: zero disagreements in every shard.
   - **invariants**: the reference's `check()` run with `calib_use`'s functions in place of its own. Pass: zero violations in every shard.
   - **lookup** (section 10.2 rule 0, D63, D13): over every own combination of the scope with at least one undecided input (each non-empty subset of {mandatory gate, P7, V}; only the mandatory gate in mode `none`), with no upstream and with each capped central upstream (`failed`, `projection`, `calibrated-unvalidated`), `outcome_determined` equals the independent enumeration of the test module. Pass: zero disagreements.
   - **mutants**: each of the reference's 24 mutants is caught (at least one violation) and mutant 25 (lookup with C.2 only) is caught. A violation on a subset of the scope is a violation of the scope, so a mutant caught on the fixed slice (every 2000th case from the first; for mutant 25, the lookup run) is caught; the slice run is the evidence. Pass: all 25 caught.
   - The full-scope runs are 32 shards each for agree and invariants, 4 for lookup and 1 mutant item on the fixed slice: 69 items (batch work per E7 item 3, submitted only with the user's approval). Every item must complete; a missing item leaves the gate `incomplete`, never passed.
   - Tightened after the independent review (findings F6, F10, F11; tightening only): agree also compares both outputs of `inherited_flags` (flags and variation flags); the mutant item passes only when all 24 reference mutants are caught; every item records the commit and the SHA-256 of `calibration_exhaustive.py`, `test_calibration_use.py`, `core/calibration/use.py`, `core/calibration/deps.py` and the reference; `calibration_exhaustive.py --summarize` passes only when all 69 items are present once and `ok`, every item carries the reference's hash and the same provenance, agree covers 31,593,216 cases, lookup covers 2,754,048, and mutant 25 is caught at least once. The independent enumeration of the lookup (`independent_lookup`) takes C.2 from the reference and writes the cap and the use matrix itself (review note N1); with `calib_use`'s functions patched in, the reference's `cases()` uses `calib_use`'s `assign` to choose the own combinations that get upstream pairs, a dependence covered by the agree check, which runs with the reference's own functions (note N2).
2. *Named cases of section 15.3* in phase-0 scope, and the negative test of P4 (section 15.3.1), each with its test (module `tests.core.test_calibration_<x>` written `<x>`; `schemas` is `tests.contracts.test_calibration_schemas`, `scripts` is `tests.skills.test_calib_scripts`). Pass: every listed test passes; each negative test shows its expected finding code or grade. Cases outside phase 0 are listed with their phase and reason (review finding F4).
   - §15.3.1: P4 on the subgraph variant → `chain.ReferenceCoverage.test_15_3_1_p4_subgraph`; P7 parameter-shift alternative rejected by the contract checker → `contract.OtherClauses.test_15_3_1_p7_parameter_shift_alternative`. Other gates of §15.3.1: their phases (§17).
   - §15.3.2, one test each in `contract.ContractRulesSection15dot3dot2`: data values (`test_contains_data_values`), roles overlap (`test_roles_overlap`), dependency cycle (`test_dependency_cycle`, and `test_stage_graph_cycle`), binning by true value (`test_simulation_bins_by_true_value`), enumerated and absorbed (`test_model_enumerated_and_absorbed`), inference form with non-holdout (`test_inferred_form_without_holdout`), non-positive-definite kernel (`test_kernel_not_positive_definite`), block rule (`test_block_rule`), injection without split (`test_injection_without_node_split`), link range (`test_link_range_mismatch`), shape bins as scalars or K−1 bins (`test_shape_bins_as_scalars_or_k_minus_1`), merging rule declared and not defined by observed counts (`test_merging_rule`; n_min at the evaluation points: phase 2, §17 placement bullet), conversion relation (`test_conversion_relation_missing`), redundant measurement without comparison node (`test_redundant_measurement_without_comparison_node`), upstream usage and role (`test_upstream_usage_and_role`).
   - §15.3.3: source declarations (`data.IngestionAndSealing.test_ingestion_requires_declarations`), sealed components (`data.IngestionAndSealing.test_sealed_components`), only `observed` statistical error (`contract.DataReleaseAndSharing.test_15_3_3_observed_only_statistical`).
   - §15.3.11, `data.OpeningPreconditions`: lineage not confirmed (`test_lineage_unconfirmed_not_opened`), P7 `incomplete` (`test_p7_incomplete_not_opened`), toy replicas not generated (`test_toy_replicas_not_generated`), k₀ = 0 (`test_k0_zero_no_read`; k₀ > 0 and k = 0 after opening: `data.FailureRecords.test_state_transitions`), the two inputs `none` (`test_k0_zero_no_read`, `test_lineage_unconfirmed_not_opened`), ratio test fails and passes after the summed redo (`test_pre_opening_ratio_test`).
   - §15.3.12, `use.NamedCases.test_outcome_already_determined_cases` (cases 1–9 and 11), and the exhaustive lookup (case 12: `use.OutcomeAlreadyDetermined` and the campaign's lookup items). Case 10 (P7 lower bound 0.6 under one alternative, not computable under another): the P7 decision over alternatives is computed by `calib_design.py`/`calib_validate.py` (phase 2); its input form (P7 failed) is case 8.
   - §15.3.13: version 2 after version 1, four cases (`data.ReadsAndEligibility.test_version_2_after_version_1`); role swap, three cases (`data.ReadsAndEligibility.test_role_swap`), the fourth (κ2 declares X as calibration data and holds out units sharing events with X) and the declared or undeclared sharing of R_v with R_c (`contract.DataReleaseAndSharing.test_15_3_13_holdout_shares_events`, and before opening `data.OpeningPreconditions.test_holdout_sharing_rechecked_before_opening`); `fit-pending` is never derived (`data_release.Ledger.reuse_input` returns `none`, `fit` or `validation` only); combined efficiency (`contract.DataReleaseAndSharing.test_15_3_13_combined_efficiency`, with the `cv` flag); 1000/800/300 (`test_15_3_13_mixed_sample`, `test_15_3_13_1000_800_300_second_half`).
   - §15.3.14, `data.FailureRecords` unless stated: abandonment → `final`, and no second state change of a record (`test_state_transitions`); a decision record after abandonment, and abandonment after a pass, rejected by `calib_validate.py` (phase 2, §17 placement bullet); k = 0 (`use.IncompleteAggregation.test_v_and_p7_states`); N_obs = 0 → `withdrawn` (`test_state_transitions`); k = 0 with the data-side check triggered → `final`, and a value missing at opening treated as a failed V (`test_state_transitions`; the data-side and has-value checks at opening read the opened values: phase 2, §9.2); trigger and failed regeneration → `final` (`test_state_transitions`); no trigger and failed regeneration → `incomplete`, `pending` (`test_regeneration_fails_without_trigger`); new series after a holdout failure (`test_new_series_cross_validates_after_holdout_failure`); later record (`test_later_record_does_not_affect`); interleaving (`test_interleaving`); reverse (`test_reverse_order`); `withdrawn` (`test_withdrawn_does_not_affect`); same sequence number (`test_same_sequence_number_counts_as_earlier`); κ1 opens and does not decide, mode `none` design study, holdout on new units, κ2's own V fails (`test_pending_then_resolutions`); κ1 `final`, κ3 `pending` (`test_final_and_pending`); the cross-validation sub-cases: fit reads (`data.ReadsAndEligibility.test_cross_validation_fit_reads_do_not_cap`), `pending` then resolved (`test_pending_then_resolutions`), simulated calibration data (`use.NamedCases.test_outcome_already_determined_cases`), capped by V, a central upstream or own flag (`test_capped_by_upstream_or_flag_with_pending`), later record (`test_later_record_does_not_affect`); a re-judged upstream not marking the downstream for redo: upstream invalidation is phase 4 (§17 row 4).
   - §15.3.15: `use.NamedCases.test_grade_rule_cases`; G8 fails in holdout, D–F `not-applicable` (`use.IncompleteAggregation.test_15_3_15_g8_fails_later_stages_not_applicable`).
   - §15.3.17: numbers instead of hashes (`deps.Roles.test_15_3_17_numbers_instead_of_hashes`); the four use cases (`use.NamedCases.test_use_rule_cases`). Propagation (joint fits, shared nuisance versions, the four source-set shapes, θ and ν exported together): phase 2 (§17 row 2, "propagation").
   - §15.3.18: P4 of both modules on the ECAL and tracker fixtures (`chain.Fixtures.test_15_3_18_p4_both_modules`); the P3 part: phase 2; contribution decomposition: phase 4; partial pooling: phase 5.
   - §15.3a, phase-0 cases: lineage (`data.Lineage.test_15_3a_reformatting_does_not_reset_reads`; no usable lineage → not opened, `data.OpeningPreconditions.test_lineage_unconfirmed_not_opened`), failure records (`data.FailureRecords`), acyclic ids (`deps.Versions.test_15_3a_rebuild_in_acyclic_order`), `incomplete` aggregation (`use.IncompleteAggregation`).
3. *The three fixtures derive candidate methods and reachability*: `ecal`, `rich`, `tracker` in `core/calibration/data/` give a candidate method for every parameter and P4 `passed` (`test_calibration_chain.Fixtures`, and `calib_chain.py candidates` / `p4` in `test_calib_scripts`). Pass: every parameter has a candidate and P4 passes.

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python 3.13.2 (`HEP_RESEARCH_PYTHON`: conda env `ml`; NumPy 2.2.2, SciPy 1.16.1); phase 0 uses the standard library only. Worktree, outputs (`.simcal-work/`) and `TMPDIR` on the private ceph folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/` (user's instruction). Batch work on Linux and Slurm (NSTCCore, partition `edr1-al9_short_serial`, account `ams`) through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- D5, D11 approved (A6); the reference implementation supplied (`reference/`, `c5279adf…`)
- The full-scope Appendix C runs exceed the standing 2 CPU-hour campaign budget: the user's approval of the campaign is needed (E7 item 3)

#### Execution log

- 2026-11-10, start of phase 0. Maintainer answers (asked in the Claude session of 2026-11-10, recorded verbatim as the options chosen): Open question 1 → "docs/dev/simulator-calibration/ (Recommended)"; Open question 6 → "skills/hep-statistics/scripts/ (Recommended)". Reason: E9 step 2 requires both before the records folder is created.
- Worktree `../hep-research-simcal-phase-0`, branch `simcal/phase-0`, created from `origin/main` at 5c2d1c7c (hep-research 0.65.1), the version the package names; the main checkout (local `main` at 9bd365f0, 0.55.0, behind) was not modified.
- Package checked: `sha256sum -c MANIFEST.sha256` all OK; `tools/restore_spec.py` OK (eb56a985…). Refresh of the drafts (E4 step 2): `build_decision_index.py`, `build_approvals.py` and `draft_cards.py` rerun on a copy of the package give byte-identical index, packet and drafts, so the drafts' collection is current with Part B; the only refresh is the maintainer's answer to Open question 6 in each card.
- `decision-sheet.md` copied here is the author's sheet with the package's update for the decision of 2026-11-10 (7 changes, listed in its header), made by the package's preparation, not by the author; the author's own copy, `decision-sheet.before-2026-11-10.md`, stays with the package.
- Interpreter: plugin scripts require Python ≥ 3.13; none on PATH qualifies, so `HEP_RESEARCH_PYTHON=<conda>/envs/ml/bin/python3.13` (3.13.2, NumPy 2.2.2, SciPy 1.16.1, SymPy 1.13.1) is used. Reason: the only installed 3.13+ interpreter with NumPy, SciPy and SymPy; nothing installed.
- `lint_task.py` is run with `--repo <worktree>` (Part A, E4 step 4) and also with `--repo <plugin root>`, since Part A's paths are plugin-relative (g4sim cards used both forms).
- Files copied unchanged from the package into `docs/dev/simulator-calibration/` (E9 step 2), SHA-256:

  - `simcal-task.md`: `c1c3e56000689f9b5706efee96965a4845aa30342a29bffd85a1f5f8b0049a61`
  - `simulator-calibration-v7.37.4-clean-en.md`: `c016b70b1aa45e26cd8e590111a84678f7c301a02b2bd4989fa3637a728f235c`
  - `simulator-calibration-v7.37.4-clean-en.appendix-E.md`: `ef422730e70f2ec9d0804deedf0ce2db2bc8361255a181991bb06fe0ee21fdb9`
  - `simcal-decision-index.md`: `72cb2e326a86489a2332348466fab6a17bb07812a53094ace196ec1778260402`
  - `simcal-decision-index.json`: `84ebd132bc28a5d438f656d3212c56f06fc75703b3ebfe70c4c653ce67cb4a9d`
  - `decision-sheet.md`: `a59334acc3d381bbe347ce95c19c2ac74ce5913ed92f0903c3f86a8398a64f7c`
  - `simcal-approvals.md`: `0da200be5e5d101c73166f49a200095712b41aa4764aa5244d2831b66fa5b634`
  - `tools/build_approvals.py`: `15a9627f5b3fd1790f542a419d0f219774b5d850e9cfee10a9a5bbf6a71dac33`
  - `tools/build_decision_index.py`: `817486e2adad9bc7b94f32e30a1265951e75c24135ab1464ded5c38dd47e55f4`
  - `tools/draft_cards.py`: `3ea877cbab42a23ecfb5309c65d25f3dfd243ee3afc85c0e7197017ce4dd678a`
  - `tools/restore_spec.py`: `b87da109b0db03ae258ea21bc3ccc148142bbdf7541f0756a1a3acbbce420c3a`

- Also created from the package: `simcal-status.json` and `simcal-task-registry.json` (from `drafts/`), `simcal-approvals.md`, and the folders `simcal-tasks/`, `simcal-gates/` (E9 step 3).
- Checks of the folder as committed: `tools/check_packaging.py`, `tools/check_layering.py`, `tools/check_wiring.py` all pass (no implementation yet; the full step-7 checks run with the implementation).
- E9 step 5, material for the author (prepared, not decided):
  - **D5** (line 4089; §2.1, §9.2). Reading (decision-sheet): the sub-shape left after a bin is excluded from a free-ω count shape is a new free-ω shape; the contract declares its own N_decl with a recorded basis, N_decl ≥ 10, a missing declaration is a rejection. Phase-0 effect: one rule in `calib_contract.py check` and its negative tests (§15.3). If decided otherwise (for example, the sub-shape inherits the parent's N_decl, or excluding a bin from a free-ω count shape is forbidden), only that rule and its tests change; the schema keeps or drops the sub-shape's N_decl field.
  - **D11** (line 4095; §10.1). Reading (decision-sheet): add k, k₀ and the unused-observable list with reasons to the `calibration-result` schema. Phase-0 effect: three fields in the result schema in `contracts/`, read by `calib_use.py` (Appendix C uses k and k₀). If decided otherwise (for example, a separate record referenced by hash), the schema and the reader in `calib_use.py`/`calib_deps.py` change; no decision rule changes, since §5.2 and §9.5 already require the values.
- **Report (E8), 2026-11-10.** Phase 0 **BLOCKED**. Worktree `../hep-research-simcal-phase-0`, branch `simcal/phase-0`; last commit is the one that adds this entry. Gates: none evaluated (no implementation started). Thresholds: phase 0 has no §8.7 rows. Blocking: (1) the author's explicit decisions on D5 and D11, to be recorded in `simcal-approvals.md` (E7 item 1); (2) the reference implementation `calib_use_decision_table.py`, SHA-256 `c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3`, from the author (E7 item 2, Open question 2). Next action when unblocked: record the approvals, set phase 0 `in-progress`, and run E4 steps 5–12 (implement the §17 phase-0 content, tests, gates, review, hand-over). Phase 1 will further need D37, D41 and D42.
- 2026-11-10: the author approved D5 and D11 (“accept the D5 and D11 readings”), recorded as A6 in `simcal-approvals.md`. Phase 0 implements the decision-sheet readings: D5, a sub-shape left after excluding a bin from a free-ω count shape is a new free-ω shape with its own declared N_decl (recorded basis, N_decl ≥ 10, missing declaration rejected); D11, k, k₀ and the unused-observable list with reasons are fields of the `calibration-result` schema. Part B is not edited (the author applies A6 in a new part of Appendix E).
- **Report (E8), 2026-11-10.** Phase 0 still **BLOCKED**, now only on E7 item 2: the reference implementation `calib_use_decision_table.py`, SHA-256 `c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3`, from the author (Open question 2). Next action when it is supplied: set phase 0 `in-progress` and run E4 steps 5–12.
- 2026-11-10: the author approved D37, D41 and D42 (“accept the D37, D41 and D42 readings”), recorded as A7 in `simcal-approvals.md`; they block phase 1, not phase 0. D41 leaves the "determining region" of tail functionals open for the author (the checker rejects that case until it is defined). Correction: the D5 and D11 rows written for A6 had lost their empty tie-in cell (approval in the wrong column); fixed in the same commit, with a column-count check.
- 2026-11-10: the user pointed to `/ceph/sharedfs/work/AMS/hsinyichou/hep-research-tasks/calib_use_decision_table.py` (776 lines, written 2026-11-10 07:37). SHA-256 `143aaa919499d90b8872c917d2aabd23845f005176359e119671faab88f37a94`, not `c5279adf…`, and no whitespace or line-ending variant matches; its docstring says it is the reference table of workflow **v7.37.3** (latest change note v7.37.3). It is a third non-matching version, after `ed0fa0df…` and `f8dfef10…` (`en/MISSING.md`). Not used and not copied (E7 item 2; Part B header line 15 and line 3920 pin the v7.37.4 version). Phase 0 stays blocked.
- 2026-11-10: the user pointed to `hep-research-tasks/calib_use_decision_table-v7.37.py` (763 lines, written 07:39): SHA-256 `d7e1e25b0774533db13d69fd11bbc8626a597c96c9d8cd6cd0387a651aac2231`, docstring workflow **v7.37** (latest change note v7.37); no whitespace variant matches `c5279adf…`. Fourth non-matching version; not used. Phase 0 stays blocked.
- 2026-11-10: the user supplied `hep-research-tasks/calib_use_decision_table-v7.37.4.py` (781 lines, docstring workflow v7.37.4): SHA-256 `c5279adf41acfcfb21e8aa67295756d1a551361e6a9aa5fa68d98bb4f17a3de3`, **matches** Part B (header line 15). Copied unchanged into the records as `docs/dev/simulator-calibration/reference/calib_use_decision_table.py` (the name Part B uses, line 3920), its hash re-checked after the copy. Open question 2 is answered. E7 item 2 resolved; with A6 and A7 recorded, phase 0 is set `in-progress` and continues at E4 step 5. Reason for the folder: the file is an attachment of Part B, kept with the records; the Appendix C tests read it from there and check its hash first.
- 2026-11-10: on the user's decision ("Move whole worktree", asked under E7 item 7), the phase-0 worktree moved from `/dicos_ui_home/hsinyichou/hep-research-simcal-phase-0` to the private folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/` (mode 700, group ACLs removed, as for the reconstruction task), as `hep-research-simcal-private/hep-research-simcal-phase-0`. Reason: Slurm work of later phases and its outputs belong on ceph (storage limit of home). Done as `git worktree remove` of the clean worktree (only ignored baseline outputs and caches lost) and `git worktree add` from the same branch at 8949a1ce; the three E2 checks hold at the new path; the reference table's SHA-256 re-checked. Later phases' worktrees go in the same folder. The E2 commands' `../` paths are read relative to that folder.
- 2026-11-10, implementation decisions (E4 step 9; none contradicts Part B):
  - Layout: `core/calibration/` (steward hep-statistics, `core/OWNERS.json`) has one module per owning script of §14 (`use`, `deps`, `chain`, `data`, `contract`) plus `io` (script I/O); the scripts in `skills/hep-statistics/scripts/` are thin CLIs. Each check exists once: `use` calls `deps.derive_role`, `contract` calls `chain`, `deps` and `data`. Reason: §14's one-implementation rule with a library the later phases import.
  - Fixtures as JSON in `core/calibration/data/` (`calibration-fixture/1`): the toy detector of §15.1 with its subgraph and bimodal variants, and ECAL, RICH, tracker graphs built from the §3.1 derivation tables; all `synthetic`. The toy detector's momentum reference is a known input on the track branch observed through E/p (§3.4 merging example).
  - Exhaustive tests: the scope is 31.6 million cases (about 2 core-hours per pass), so the unit suite runs a fixed slice (1/2000; lookup 1/23, a stride coprime to the 4 upstream variants and 7 undecided subsets the scope cycles through) and the full scope is the sharded gate run (test design above). Appendix C says the lookup tests are "added to the reference implementation"; the reference is fixed by its hash, so they live in `test_calibration_use.py` with an independent enumeration. Reported for the author's information (not a blocker).
  - `calib_contract check` in phase 0: the rules that need model quantities (clause 9 items 2, 3, 4 for N_exp, 8, 12, 13; the standardized N_d and N_d,c decisions) are phase 2 and listed under `deferred` in its output; the g4sim model identity is phase 3; `preflight` (A0) phase 1. Readings: a ψ must declare `uncertainty: negligible` (the 0.1σ_tot^design bound of D37, approved A7, is computed in phase 1); the link must be the one of the §2.1 table for the declared range (positive→log, signed→identity, (0,1)→logit, (−1,1)→Fisher z, simplex→alr/ilr); "contains data values" is a refused set of value keys plus the closed schema; a positive-definite kernel is a matrix passing Cholesky or a named kernel family known to be positive definite; this engine version supports Gaussian blocks only, so binomial and Poisson blocks are rejected under clause 10 item 3 until phase 2.
  - `calib_chain`: a parameter acting on several nodes takes the methods every node allows; a learned density ratio is a candidate only on a node declared as a post-hoc correction with stored inputs and outputs (phase 5 implements it); with a g4sim node binding the candidates are refused as `incomplete` (Table 2 of §11.4, phase 3).
  - `calib_data`: the reuse input `fit` counts every read (any kind, channel or κ) on a validation unit before κ's first validation read, since none is exempt under the current rules; a failure record with the same sequence number as the read counts as earlier; the ledger is one JSON file written atomically under an exclusive lock file.
  - `calib_deps`: the parent list is normalized (sorted, deduplicated) inside update_digest as well as in the version id, so the order of listing parents is not content.
  - `calibration_result.json` is a standalone schema (with k, k₀ and the unused observables, D11); registering `calibration-result` as an envelope artifact type (a contracts minor version) is left to phase 2, which first writes a result.
  - §15.3 cases left to later phases by §17: the `calib_validate.py` cases of §15.3.14 (phase 2); the propagation cases of §15.3.17 (joint fits, the four source-set shapes; phase 2). Phase 0 tests hash citations, cycles, roles and the use rules of §15.3.17.
  - Named-case readings: "P7 power insufficient" is the P7-failed input; "k₀ = 0 determined before opening" decides V (no undecided input), so the lineage gap does not count.
  - Temporary files on ceph (`TMPDIR` in the private folder, outside any git repository), on the user's instruction.
- 2026-11-10, gate campaign 1 (before the review): the user approved "Pilot, then full" (asked under E7 item 3; the cap set to 24 core-hours and 80 jobs, above the standing 2 CPU-hour budget). Campaign folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/campaigns/phase0-appendix-c/`, code from a `git archive` snapshot of commit 24a8bf6a, job interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13` (Python 3.13.18, standard library only for these runs; read, never written), partition `edr1-al9_short_serial`, account `ams`. Pilot job 7553815_0 (chunk c0000) completed in 21 s; array 7553821 (chunks c0001–c0067) completed, at most 33 s and 53 MB per job, about 0.4 core-hours in all. All 68 items `ok`: agree 31,593,216 cases with no disagreement, invariants with no violation, lookup 2,754,048 cases with no disagreement and mutant 25 differing on 408,576. **Superseded as gate evidence**: the review's fixes change `core/calibration/use.py` and the harness, so the gate is evaluated by a second campaign at the fixed commit.
- 2026-11-10, independent review (E4 step 10): the user approved one fresh-context reviewer subagent ("Yes, one reviewer"). Report `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-0-review.md` (SHA-256 `1e6ebf7c…`), at commit 24a8bf6a: 4 major (F1–F4), 11 minor (F5–F15), 5 notes. Every finding fixed in commit c0870a0a without a change to Part B; the notes: N1, N2 stated in the test design above; N3 (a parameter on several nodes takes the methods every node allows) kept as a recorded reading, reported for the author; N4 (data values detected by key names plus closed schemas) and N5 (`--vmode` now validated; a stale ledger lock is removed by a person) recorded. The review and its resolution are in the gate record.
- 2026-11-10, repository checks (E4 step 7), first full run at 24a8bf6a (`run_all_checks.py --jobs 4 --no-cli`, TMPDIR on ceph, 60 min): 7,302 tests, 11 failures and the `naming` and `ams_optional` checks failing. Fixed in 02f973ed: the dependency markers of the guide's Skill scripts list, `tools/skill_scripts.json`, the reference inventory, timings of the seven new modules, and the new names (renamed in the new code; the names in the copied package tools waived in `tools/naming_known_gaps.json`, pending maintainer approval, since Part A requires those files unchanged). Not caused by this phase, failing identically on a clean `origin/main` snapshot on ceph: `tests.contracts.test_revocation` (2, group-writable and sticky-directory checks under ceph ACL semantics; also the cause of `ams_optional`) and `tests.skills.hep_computing.test_event_display_templates` (1). `test_workflow_b1` failed once under load and passes alone on this branch (a timing case).
- `core/calibration/data.py` renamed `data_release.py` (imported as `data`): the bare name `data.py` made a hep-ml guide's mention of a user's `data.py` resolve to it in `tools/skill_scripts.json`.
- 2026-11-10, gate campaign 2 (the gate evidence): the user approved "Submit all 69" (E7 item 3, same cap). Campaign folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/campaigns/phase0-appendix-c-2/`, code from a `git archive` snapshot of c3b8eeae (the fixed code), same interpreter, partition and account. Array 7554757, 69 jobs, all COMPLETED, at most 58 s and 39 MB per job, 0.44 core-hours. `--summarize`: status `ok`, `gate-summary.json` SHA-256 `13e2faaf…`; agree 31,593,216 cases with 0 disagreements, invariants 26,647,296 combinations with 0 violations, lookup 2,754,048 cases with 0 disagreements, 24/24 reference mutants caught, mutant 25 caught on 408,576 cases. Every item records the hash of the files that decide it; these equal the files at 652d0ddf.
- 2026-11-10, repository checks, second run at c3b8eeae: the three environment failures plus `test_routing_tables` (SKILL.md plus `core-stats-guide.md` over the 25,600-byte quick-question budget, because of the guide's new calib entry). Asked under E7 (a change to a shared guide); the user chose "Trim guide wording": the calib entry reduced to one line and two sentences that repeated rules stated elsewhere in the guide removed (sum 25,596 bytes), commit 652d0ddf.
- 2026-11-10, final repository checks at 652d0ddf (`run_all_checks.py --jobs 4 --no-cli`, 75 min): 7,319 tests in 547 modules, 7,018 passed, 298 skipped, 3 failed (the three environment failures above); checks 30 pass, 2 fail (`unittest` with those 3, `ams_optional`), 2 skipped. After the CHANGELOG commit (4ef5ccda): `check_wiring` (also `--since origin/main`), `check_layering`, `check_packaging`, `check_naming` pass, and the release-manifest and version tests rerun. Gate record `simcal-gates/phase-0.md` written; phase 0 set to `gates-recorded`.
- **E8 report (2026-11-10).** Phase 0 `gates-recorded`; worktree `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-0`, branch `simcal/phase-0` (local, not pushed). Gates: both pass (`simcal-gates/phase-0.md`); none failed, no gap. Thresholds: §8.7 has no phase-0 row; nothing carries `provisional-thresholds`. Blocking: review and merge of `simcal/phase-0` by a human (the maintainer); for the maintainer also the two naming waivers of the copied package tools and the guide trim; for the author (not blocking) the D41 residue, review note N3, the location of the lookup tests, and applying A6 and A7 in Part B. Proposed versions (numbers assigned at merge): hep-research minor (new `core/calibration` module and five scripts), `CORE_VERSION` minor, contracts minor (new `calibration_*` schemas). Next action: after merge, or a human's word to continue on the unmerged branch (E5 step 5), phase 1 (D37, D41, D42 approved in A7).

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3578), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).
- 2026-11-12, the user's word "update hep-research basis of this task to latest main version": `origin/main` 9d1eda2e (hep-research 0.66.1) merged into `simcal/phase-0` (a merge, not a rebase, so that every commit named by the registrations, gate records and run outputs stays in the history). Overlap with this branch: `CHANGELOG.md` (the Unreleased section kept above main's 0.66.0 and 0.66.1 sections) and the generated `tools/skill_scripts.json` and `docs/reference-inventory.*` (regenerated). No file that decides a gate changed on main (`core/calibration/`, the calibration scripts and schemas, the stats guide and SKILL.md); the calibration tests and repository checks are rerun at the merge.

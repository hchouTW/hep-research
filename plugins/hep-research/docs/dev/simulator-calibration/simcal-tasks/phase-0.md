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

- [ ] Seven schemas; the DAG format, injection-point splitting, three fixtures (ECAL, RICH, tracker; ECAL and tracker each contain a pair of overlapping modules, for tests of redundant measurements); the **graph structure** of the toy detector and subgraph variants (DAG only, no simulation); `calib_chain` (candidate methods, P4); contract, data release and plan schemas; `calib_contract check`; in `calib_deps`, hash references, cycle checks and derivation of upstream roles from usage; `calib_use` (per the decision table of Appendix C, including the `incomplete` of rule 0); in `calib_data`, raw-unit lineage, validation-read and fit-read events (including registration of read channels and contract drafts), failure records (`pending`/`final`/`withdrawn`), and derivation of the reuse input (Appendix C.1); acyclic computation of version ids

**Placement bullets of §17 (verbatim; they place work in phases 0 and 2)**

- The cases in §15.3 that depend on `calib_validate.py` behavior (in §15.3.14, "submitting a decision record after abandonment is rejected" and "abandoning after the decision passes is rejected") are acceptance-tested in phase 2; phase 0 acceptance-tests only the grade function, using hand-written decision-record stubs.
- Locking-stage checks that need quantities produced by the model are added in phase 2 (after the joint likelihood and the design-stage Asimov are delivered):
  - the rounding-negligibility condition of §2.1, N_decl/N_exp of validation shapes, the n_min lower bound of shape summary statistics and the block-conversion condition are all computed by `calib_data.py` and called by `calib_contract.py check`;
  - Σ_boot of P5 and the b_J item of P5 (§8.2 note 3; it needs K_l from the design-stage MC) are decided by `calib_design.py`.
  - The phase-0 `calib_contract.py check` does not contain these rules; it only checks that the declarations exist.
- In phase 0, the failure-record state transitions are tested with hand-written decision-record stubs; `calib_validate.py` is retested with real decision records after it is delivered in phase 2.

**Scripts and homes (Inferred from §13, §14 and the content)**

- [ ] `calib_chain.py` (DAG, injection-point split, candidate methods, P4)
- [ ] `calib_contract.py check` (contract rules of §5.2; in phase 0 only the declarations of the locking-stage checks, §17)
- [ ] `calib_deps.py` (hash references, cycle checks, upstream roles from usage)
- [ ] `calib_use.py` (Appendix C decision table, rule 0 `incomplete`)
- [ ] `calib_data.py` (raw-unit lineage, read events, failure records, reuse input of Appendix C.1)
- [ ] `contracts/` (the seven abstract-object schemas; contract, data release, plan and result schemas; §13)

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

- D5 (line 4089; needs the author)
- D11 (line 4095; needs the author)

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

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- D5 and D11 need the author before this phase (index)
- The reference implementation at `c5279adf…` is not in the package (`simcal-task.md`, Section E7, item 2)

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

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3578), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

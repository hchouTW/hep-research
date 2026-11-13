# Simulator calibration phase 4: Dependency graph and specialization

## Background

Phase 4 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3582). Refreshed 2026-11-13 at the phase start (worktree `hep-research-simcal-phase-4`, branch `simcal/phase-4` from `origin/main` 307a364d, after phases 0–3 merged; the five author items decided by A21); registered before any run a threshold judges. (Originally a draft written with the task package of 2026-11-10 (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 4 of §17 so that its gate holds: Negative tests of the contribution decomposition and the g4sim binding (§15.3); specialization does not require modifying the generic layer

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] Upstream invalidation (including a change of simulation identity, §10.3), conditions-database export (g4sim conditions snapshot), feedback into g4sim (§10.4); `calib_contrib`; eight specialization documents (each with a node-binding example per §11.4); the hep-detector domain card

**g4sim preconditions of §17 (verbatim; the rows this phase's content uses apply)**

- Phases 0–2 of this workflow use only the toy detector and do not depend on g4sim.
- An item that uses g4sim may start only after the corresponding g4sim stage is **merged** (`merged` in the g4sim status file).
- When a g4sim stage that is `partially-complete` is the precondition, the gaps of that stage must not be gates this item depends on.

| Item of this workflow | Required g4sim stage | Deliverable |
| --- | --- | --- |
| The g4sim model identity of `calib_contract` (the masked hash of §5.1) and its acceptance (§15.3a) | S1 (schemas and read procedures of the three specifications), S4 (`response-pipeline/1`); it is added to the checker in phase 3; the phase-0 checker does not contain this rule | specification schemas, `core/canonical` |
| Integration tests for node-0 reweighting and the `external` rejection | S3 (`source-density/1`), S4 (`external` source) | source density; `external` read |
| Birks deterministic rerun (`edep_by_dedx_class`) | S3 | `edep_by_dedx_class` |
| Re-digitization of response parameters, common random numbers, event intervals | S4; S8 for the digitization-job path (§6.6) | hit, `response.py`, Philox, `edep_visible_ly_split`, `event_file`; from S8, `digitize.py`, `g4sim-digi-job/1` and `g4sim_digi` |
| Synthetic ZDC fixture | S3 (examples), S5 (calorimeter kit, optional) | ZDC specification |
| Efficiency-map φ, light-collection parameters, RICH replica fixture | S7 (mapping runs; for route 3 of the PDE split, with `photons.csv`), S8 (digitization job, for joint-pattern replicas, for U in the fixed-map mode and for the PDE split of §6.7) | efficiency map, Dirichlet replica, optics |
| Simulated geometry misalignment, conditions-snapshot export | S9 (merged, hep-research 0.65.0) | `alignment-overlay/1`, `condition-snapshot/1`, `g4sim_run.py diff` and `--overlay` |

**Scripts and homes (§13, §14; existing since phases 0–3: `calib_deps.py`, `calib_propagate.py`, `calib_use.py` and their engines `core/calibration/deps.py`, `propagate.py`, `use.py`; new: `calib_contrib.py`, `core/calibration/contrib.py`, hep-detector `simulation-calibration/`)**

- [ ] `calib_deps.py` / `deps.py`: upstream revision or downgrade marks the downstream for a redo (§10.3); a change of any of the five masked identity hashes of §5.1 (`build_hash`, Geant4 and data-set versions, geometry/material other than θ, φ, response stage, efficiency map) marks the result for a redo; θ/φ value changes and `provenance_id` alone do not; the T2 carry-over of A21 (§19-g7): a pre-registered T2 equivalence record keeps the result with `identity-carried-over`, a failing or missing one marks it for a redo.
- [ ] `calib_propagate.py` / `propagate.py`: export of the calibration result as g4sim `condition-snapshot/1` and `alignment-overlay/1` with the result's hash, effective grade and flags in `source_of_facts` (§10.4 "Feeding back to g4sim", g4sim S9); no ξ versions (A21, §19-g8), each forced joint fit reported.
- [ ] `calib_use.py` / `use.py`: the use matrix of §10.2 and the offline `source_of_facts` check on every exported snapshot and overlay (A21, §19-g6; §15.3.19).
- [ ] `calib_contrib.py` / `contrib.py` (§10.5): `effects_off` per effect; all 2ⁿ subsets for n ≤ 10, permutation sampling with its sampling error above; every evaluated subset must pass G4's ESS threshold or no decomposition is output; bootstrap covariances between terms; the object (variance or resolution) stated; forced joint fits reported (A21).
- [ ] hep-detector `skills/hep-detector/references/simulation-calibration/` (§11.1, §12, §13): eight specialization documents — ECAL, HCAL, RICH, DIRC, TRD, Tracker, TOF, μ detector — each with the §11.1 items 1–8 (item 7: the advisory f, C, ℓ table with citations verified through hep-citations or "no literature value", A21 §19-1; item 8: the advisory alternative hypotheses, A21 §19-4) and a node-binding example per §11.4 that runs through the existing generic layer; the hep-detector domain card (§13 "Review": calibration review obligations).

**This phase's tests (§15.3; items already covered by phases 0–3 are re-run, not re-implemented)**

- [ ] §15.3.17 Propagation and use: confirm every listed case has a test (central propagation and its counterexample, hashes not numbers, the four source-set shapes, θ/ν not split, the use cases); add any missing.
- [ ] §15.3.18 Contribution decomposition: when some evaluated subset fails the ESS threshold, no decomposition is output (negative), with a positive control. (Redundant measurements: phases 0 and 2; partial pooling: phase 5.)
- [ ] §15.3.19 g4sim binding: every listed case; the `build_hash` item is this phase's (a changed `build_hash` marks the result for a redo); confirm the phase-3 cases and the `source_of_facts` rejection by `calib_use.py`.
- [ ] The A21 cases: T2 carry-over (a passing record keeps the result flagged, a failing or missing one redoes it); a snapshot or overlay without `source_of_facts` rejected.
- [ ] Generic-layer sufficiency (§12, §17 gate): each of the eight node-binding examples is checked by the existing contract checker and chain derivation, with no change to `core/`, `contracts/schemas/` or the scripts in the commits that add the specialization documents.

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- Extensions of phase 5

## Repository Context

Confirmed in hep-research `main` at 307a364d (0.66.1 plus phases 0–3): `core/calibration/` (deps, propagate, use, contract, chain, emulator, fit and the rest of phases 0–3), the `calib_*.py` scripts in `skills/hep-statistics/scripts/` (no `calib_contrib.py` yet), `contracts/schemas/calibration_*.json`, `adapters/geant4/assets/g4sim_calib_eval.py`; g4sim S9 (`alignment-overlay/1`, `condition-snapshot/1`, `g4sim_run.py diff` and `--overlay`); hep-detector references `calibration-and-alignment.md`, `detector-simulation.md` (no `simulation-calibration/` folder yet). Earlier text (draft of 2026-11-10): Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-4`.
2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-4.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- §19-1 (§19) (line 3703; needs the author before the phase it is deferred to); approved, record A21
- §19-4 (§19) (line 3708; needs the author before the phase it is deferred to); approved, record A21
- §19-g6 (§19) (line 3743; needs the author before the phase it is deferred to); approved, record A21
- §19-g7 (§19) (line 3744; needs the author before the phase it is deferred to); approved, record A21
- §19-g8 (§19) (line 3745; needs the author before the phase it is deferred to); approved, record A21

All five are approved by record A21 (2026-11-13, "use your recommendations"), which states the decision of each.

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- none

Accepted or decided items that this phase implements (their text in Part B is normative):

- none

#### Thresholds and test designs

**Gate (§17, verbatim)**: Negative tests of the contribution decomposition and the g4sim binding (§15.3); specialization does not require modifying the generic layer

**§8.7 rows of this phase (verbatim)**:

- none

**Gate designs (registered here before the gate run)**:
- Negative tests of the contribution decomposition (§15.3.18) and of the g4sim binding (§15.3.19, with the A21 cases): every listed case shows its expected rejection or decision, each with a positive control that passes; run from one clean commit through a gate harness like phase 3's (`tests/core/calibration_phase4_gates.py`, units items).
- Specialization does not require modifying the generic layer: the eight node-binding examples pass the existing contract checker and chain derivation (P4) at the gate commit, and the diff of the commits that add `simulation-calibration/` touches no file under `core/`, `contracts/schemas/` or `skills/hep-statistics/scripts/` (checked by the harness from `git diff --name-only`).
- Provisional threshold of A21 (§19-g7): T2 margin 0.1σ_tot^design, TOST α = 0.05 (`provisional-thresholds`).

**Work packages (proposed; each needs the user's approval as a subagent, Part A E7)**:
- WP-M (deps, identity): §10.3 upstream invalidation, the five identity hashes and the `build_hash` redo, the A21 T2 carry-over; tests (§15.3.19 `build_hash`, A21 §19-g7).
- WP-N (export, use): condition-snapshot/alignment-overlay export with `source_of_facts`, the `calib_use.py` check, the §15.3.17 coverage audit and any missing cases; forced-joint-fit reporting (A21 §19-g6, §19-g8).
- WP-O (`calib_contrib`): `core/calibration/contrib.py`, `calib_contrib.py`, its schema use, §15.3.18 negative and positive tests.
- WP-P (specialization): the eight documents and the domain card in hep-detector, node-binding examples and the sufficiency test; citations through hep-citations (no value from memory).
- Main session: the card, registrations, the gate harness, the gate run, the gate record, the review.

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.66.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- The five deferred §19 items are decided (A21); the g4sim use-matrix enforcement (§19-g6) depends on g4sim upstream and is not a phase-4 deliverable.
- Specialization documents need literature values with verified citations; a value without one is written as "no literature value" (A21 §19-1).
- Specialization must not require modifying the generic layer (§17 gate)

#### Execution log

- 2026-11-13 phase 4 started on the user's word ("Start phase 4 now", "go-ahead"): worktree `hep-research-simcal-phase-4`, branch `simcal/phase-4` from `origin/main` 307a364d (phases 0–3 merged); A21 recorded (the five author items as the decision sheet recommends); card refreshed (work packages WP-M to WP-P proposed, gate designs).

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3582), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

# Simulator calibration phase 4: Dependency graph and specialization

## Background

Phase 4 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3582). This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

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

**Scripts and homes (Inferred from §13, §14 and the content)**

- [ ] `calib_deps.py` (upstream invalidation, change of simulation identity, §10.3)
- [ ] `calib_propagate.py` (conditions-database export, feedback into g4sim, §10.4)
- [ ] `calib_use.py` (offline check of `source_of_facts` on exported snapshots and overlays, §10.4)
- [ ] `calib_contrib.py` (contribution decomposition)
- [ ] hep-detector `simulation-calibration/` (the eight specialization documents and the domain card; §13; new)

**This phase's tests (Inferred; refresh from §15)**

- [ ] §15.3.17
- [ ] §15.3.18 (contribution decomposition)
- [ ] §15.3.19 (g4sim binding)

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- Extensions of phase 5

## Repository Context

Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

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

- §19-1 (§19) (line 3703; needs the author before the phase it is deferred to)
- §19-4 (§19) (line 3708; needs the author before the phase it is deferred to)
- §19-g6 (§19) (line 3743; needs the author before the phase it is deferred to)
- §19-g7 (§19) (line 3744; needs the author before the phase it is deferred to)
- §19-g8 (§19) (line 3745; needs the author before the phase it is deferred to)

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- none

Accepted or decided items that this phase implements (their text in Part B is normative):

- none

#### Thresholds and test designs

**Gate (§17, verbatim)**: Negative tests of the contribution decomposition and the g4sim binding (§15.3); specialization does not require modifying the generic layer

**§8.7 rows of this phase (verbatim)**:

- none

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- Five deferred §19 items need the author before this phase (index): §19-1, §19-4, §19-g6, §19-g7, §19-g8
- Specialization must not require modifying the generic layer (§17 gate)

#### Execution log

- (filled in during the phase)

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3582), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

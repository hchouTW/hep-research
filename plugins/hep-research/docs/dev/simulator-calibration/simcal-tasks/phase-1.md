# Simulator calibration phase 1: Evaluation and design stage

## Background

Phase 1 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3579). This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 1 of §17 so that its gate holds: The negative tests of A0, P0, P2, P5 pass; reweighting and rerun agree

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] Analytic and step-level reweighting (including the support and mixture formulas), rerun, `resample`, `evaluate_from`; the linearized fit operator A for Gaussian blocks (for the design stage; ν and η are included as linear nuisance columns u_k, s_j with N(0,1) constraints, so σ_tot^design already contains their contribution in this phase and does not need to wait for the full likelihood of phase 2); A0, P0, P2, P5 (including feasibility and the final method), the surrogate-interface stub of P6; simulation of the toy detector

**Scripts and homes (Inferred from §13, §14 and the content)**

- [ ] `calib_reweight.py` (weights; the weight formula of §3.6)
- [ ] `calib_kernel_check.py` (P0)
- [ ] `calib_contract.py preflight` (A0)
- [ ] `calib_design.py` (P2; P5 with feasibility and the final method; Sobol design points and P6 held-back set, D80)
- [ ] `calib_emulator.py` (only the P6 interface stub)
- [ ] `core/calibration/` (engine home, hep-statistics; §13)

**This phase's tests (Inferred; refresh from §15)**

- [ ] §15.3.1 (A0, P0, P2, P5; the weight formula of §3.6, reweighting and rerun agree)
- [ ] §15.3.9 (MC-noise items of P5)
- [ ] §15.3.16 (the P0 cases)
- [ ] §15.2 (reweighting and rerun agree)
- [ ] §15.1 (toy detector simulation)

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- The joint likelihood, P3, P7, G1–G9 and validation (phase 2)
- The surrogate model beyond the P6 stub (phase 3)

## Repository Context

Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-1`.
2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-1.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- D37 (line 4121; needs the author)
- D41 (line 4125; needs the author)
- D42 (line 4126; needs the author)

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- §19-g2 (§19) (line 3736; settled by plugin source)

Accepted or decided items that this phase implements (their text in Part B is normative):

- D53 (line 4137; accepted 2026-11-09)
- D76 (line 4160; accepted 2026-11-09)
- D77 (line 4161; accepted 2026-11-09)
- D80 (line 4164; accepted 2026-11-09)

#### Thresholds and test designs

**Gate (§17, verbatim)**: The negative tests of A0, P0, P2, P5 pass; reweighting and rerun agree

**§8.7 rows of this phase (verbatim)**:

- §8.7 line 2004: **Bonferroni z of P0, P6** — design value: α = 0.01 — calibration: estimate the false-alarm rate with a correct kernel and surrogate model — phase column: 1, 3
- §8.7 line 2010: **smoothing model of A0** — design value: declared by the contract — calibration: confirm correct reporting with the ZDC linearity example — phase column: 1

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- D37, D41 and D42 need the author before this phase (index)
- Several §8.7 values of this phase are design values: results carry `provisional-thresholds` until calibrated

#### Execution log

- (filled in during the phase)

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3579), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

# Simulator calibration phase 3: Surrogate model and g4sim evaluator

## Background

Phase 3 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3581). This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 3 of §17 so that its gate holds: P6 negative tests; G8 passes for the three-method combination; g4sim positive tests on the synthetic ZDC fixture (§15.2); can handle the response-layer parameters of ZDC Phase 3 and φ at the resimulation level (φ must satisfy §5.5, otherwise use a surrogate model); with light-collection parameters, g4sim S7 is also needed

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] ask/tell, P6, V_emu, the combination of resimulation and surrogate model; `g4sim_calib_eval.py` (§7.1); the node binding and candidate-method derivation of §11.4; the g4sim support and recording-level checks of §6.1; the event-interval check of §6.6; the efficiency-map φ of §6.7 (after g4sim S7 is merged), with, in the mode where the map varies with θ, the seeds of the mapping runs, the joint-pattern replicas, the map term U(θ)φ_map and the θ-noise item of P5 (D28); the PDE split of §6.7 (routes 2₁, 3 and 1, the split check with its nested pair, the route-3 replicas; decided by the author on 2026-11-10)

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

- [ ] `calib_emulator.py` (surrogate training set, P6, V_emu)
- [ ] `adapters/geant4/assets/g4sim_calib_eval.py` (new, §7.1)
- [ ] `calib_chain.py` (candidate methods from §11.4 Table 2)
- [ ] `calib_contract.py check` (the masked-hash model identity, added to the checker in phase 3, §17; the PDE-split contract checks, §14)
- [ ] `calib_likelihood.py` (the map term U(θ)φ_map, §14)
- [ ] `calib_design.py` (g4sim support and recording levels, §6.1; event-interval check; seeds of the mapping runs; θ-noise item of P5; efficiency-map and PDE-split checks of §6.6–§6.7)
- [ ] `calib_kernel_check.py` (P0 with k_B on the synthetic ZDC fixture)
- [ ] `calib_propagate.py` (efficiency-map bases, joint-pattern replicas)
- [ ] `adapters/geant4/` (evaluator; §13)
- [ ] g4sim modules used: `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`), `adapters/geant4/assets/`

**This phase's tests (Inferred; refresh from §15)**

- [ ] §15.3.1 (P6; P0 (k_B))
- [ ] §15.3.16 (the cases of the synthetic ZDC fixture and P6)
- [ ] §15.3.19 (g4sim binding)
- [ ] §15.2 (g4sim items: synthetic ZDC, common random numbers, efficiency map φ, PDE split, map varies with θ, RICH replica)
- [ ] §15.3a (phase-3 cases: efficiency-map basis and g4sim model identity)
- [ ] G8 for the three-method combination (§17)

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- Dependency-graph invalidation, conditions export and specialization documents (phase 4)
- Learned density ratios and G4-L (phase 5)

## Repository Context

Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-3`.
2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-3.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- D6 (line 4090; needs the author before the phase it is deferred to)
- D83 (line 4167; needs the author)
- D84 (line 4168; needs the author)
- D85 (line 4169; needs the author)
- §19-5 (§19) (line 3709; needs the author before the phase it is deferred to)
- §19-8 (§19) (line 3712; needs the author before the phase it is deferred to)
- §19-9 (§19) (line 3713; needs the author before the phase it is deferred to)
- §19-g5 (§19) (line 3742; needs the author before the phase it is deferred to)

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- D75 (line 4159; settled by plugin source)
- §19-g3 (§19) (line 3737; settled by plugin source)
- §19-g4a (§19) (line 3739; settled by plugin source)
- §19-g4b (§19) (line 3740; settled by plugin source)
- §19-g9 (§19) (line 3753; computation: implemented as written; author confirms)

Accepted or decided items that this phase implements (their text in Part B is normative):

- D17 (line 4101; accepted 2026-11-09)
- D28 (line 4112; accepted 2026-11-09)
- D31 (line 4115; no open part)
- D43 (line 4127; accepted 2026-11-09)
- D44 (line 4128; accepted 2026-11-09)
- D86 (line 4170; accepted 2026-11-09)
- D87 (line 4171; accepted 2026-11-09)
- §19-g4c (§19) (line 3741; decided 2026-11-10)

#### Thresholds and test designs

**Gate (§17, verbatim)**: P6 negative tests; G8 passes for the three-method combination; g4sim positive tests on the synthetic ZDC fixture (§15.2); can handle the response-layer parameters of ZDC Phase 3 and φ at the resimulation level (φ must satisfy §5.5, otherwise use a surrogate model); with light-collection parameters, g4sim S7 is also needed

**§8.7 rows of this phase (verbatim)**:

- §8.7 line 2004: **Bonferroni z of P0, P6** — design value: α = 0.01 — calibration: estimate the false-alarm rate with a correct kernel and surrogate model — phase column: 1, 3
- §8.7 line 2008: **θ-noise bounds of P5 (§8.2 note 3, fifth item; mode where the map varies with θ)** — design value: s_i ≤ 0.25, κ_i ≤ 0.05 (D28, revised 2026-11-09; first estimate from one synthetic study, en/research-D28.md §4.3) — calibration: with the exact map covariance of the scan, vary the photons per mapping run, the design-point spacing and the seeding, and confirm that within the bounds the pull standard deviation of θ̂ is ≤ 1.05 (≥ 2000 repetitions per configuration, se of the pull sd ≈ 0.016; the repetition count is a choice of the D28 verification, accepted by the author, 2026-11-09; source en/d28-verify.md minor 9) and G8 passes at the full level of §8.4; include purely nested coupling, whose residual pull width of 1.05 is unexplained (D85) — phase column: 3
- §8.7 line 2009: **PDE split (§6.7)** — design value: split check: χ² at α = 0.01, and \|Δθ_i\| + 2 sd(Δθ_i) ≤ 0.1σ_tot,i^design with the pair sized by sd(Δθ_i) ≤ 0.1σ_tot,i^design/(2 + z_{1−0.025/d}), a joint pass probability ≥ 0.94 under an exact split; route-3 replicas: pseudo-mass K_cat/2 ≤ 0.01 n_b per bin and Dirichlet variance (analytic) ≥ 0.98 of the multinomial variance; transit integerisation to 10⁶ (design values decided by the author, 2026-11-10; en/research-PDE.md, en/pde-geant4-check.md) — calibration: on the ZDC fixture with optics, the false-rejection rate of the split check under an exact split, and its power against a reflectance tied to the PDE; the route-3 replica covariance against the analytic multinomial covariance over several grid sizes (§15.2) — phase column: 3
- §8.7 line 2018: **basin admission, separation and tie tolerances, and number of starts (§7.4)** — design value: R_admit = 1; τ_bar = max(0.1, 4σ_noise) at 19 segment points; τ_tie = max(0.01, 4σ_noise); max(2d, 16) Sobol starts (settled by computation, en/compute-D57.md; to be confirmed by the author) — calibration: note 6 — phase column: 2 (3 for the RICH replica)

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- D6, D83, D84, D85 and four deferred §19 items need the author before this phase (index)
- Geant4 was not run for the PDE split's evidence; repeat with Geant4 transport (§15.2)
- g4sim preconditions of §17: S7 is merged with gate 3 (TR yield) a recorded gap and the RICH replica not yet expressed (`docs/dev/geant4-architecture/g4sim-gates/S7.md`); read each stage's gate record, not only its status

#### Execution log

- (filled in during the phase)

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3581), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

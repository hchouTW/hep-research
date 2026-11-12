# Simulator calibration phase 2: Engine and validation

## Background

Phase 2 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3580). This is a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 2 of §17 so that its gate holds: The negative tests of P3, P7, G1–G8, V and propagation pass; segmented calibration and the joint fit agree (all of the above on the toy detector); the negative tests of P8, G9

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] Joint likelihood (link functions, ν, η); reference-point iteration; `calib_interval`; P3, P7; G1–G8 (except G4-L); locally linear toys and the linearity check; validation (holdout, cross-validation, power); generation of toy replicas and the independence check (for non-g4sim evaluators decided by non-repeating seeds; the g4sim event-interval check is added in phase 3); both modes of φ; the model ensemble of V_model and the correlation-kernel components; propagation of the principal components of the joint posterior and ξ versions

**Placement bullets of §17 (verbatim; they place work in phases 0 and 2)**

- The cases in §15.3 that depend on `calib_validate.py` behavior (in §15.3.14, "submitting a decision record after abandonment is rejected" and "abandoning after the decision passes is rejected") are acceptance-tested in phase 2; phase 0 acceptance-tests only the grade function, using hand-written decision-record stubs.
- Locking-stage checks that need quantities produced by the model are added in phase 2 (after the joint likelihood and the design-stage Asimov are delivered):
  - the rounding-negligibility condition of §2.1, N_decl/N_exp of validation shapes, the n_min lower bound of shape summary statistics and the block-conversion condition are all computed by `calib_data.py` and called by `calib_contract.py check`;
  - Σ_boot of P5 and the b_J item of P5 (§8.2 note 3; it needs K_l from the design-stage MC) are decided by `calib_design.py`.
  - The phase-0 `calib_contract.py check` does not contain these rules; it only checks that the declarations exist.
- In phase 0, the failure-record state transitions are tested with hand-written decision-record stubs; `calib_validate.py` is retested with real decision records after it is delivered in phase 2.

**Scripts and homes (Inferred from §13, §14 and the content)**

- [ ] `calib_likelihood.py`
- [ ] `calib_fit.py` (G1, G2, G3, G6, G7; locally linear toys)
- [ ] `calib_interval.py`
- [ ] `calib_identify.py` (P3, G5)
- [ ] `calib_closure.py` (G8)
- [ ] `calib_reweight.py` (G4)
- [ ] `calib_shift.py` (P8, G9)
- [ ] `calib_validate.py`
- [ ] `calib_propagate.py` (principal components of the joint posterior, ξ versions)
- [ ] `calib_design.py` (P7; Σ_boot and b_J of P5, §17)
- [ ] `calib_contract.py check` (calls the locking-stage checks of §17; the N_d,c recheck at θ̂, D21; the formal P7 check)
- [ ] `calib_data.py` (the locking-stage checks of §17)
- [ ] `core/calibration/`; reuses `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py` (§13)

**This phase's tests (Inferred; refresh from §15)**

- [ ] §15.3.1 (P3, P7, G1–G8, P8, G9)
- [ ] §15.3.4–§15.3.10
- [ ] §15.3.13
- [ ] §15.3.14 (retested with real decision records, §17)
- [ ] §15.3.16 (the cases of phase-2 gates)
- [ ] §15.3.17
- [ ] §15.3a (phase-2 cases: inference flags, G7 rank, general response, power lower bound, propagation packages, pass/fail summaries of weighted MC)

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- G4-L (phase 5)
- The g4sim event-interval check (phase 3, §17)

## Repository Context

Confirmed in hep-research `main` at 5c2d1c7 (0.65.1): `contracts/` with `validate.py` and `schemas/`; `core/stats/fit_diagnostics.py` and `core/stats/toy_ensemble.py`; `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`); `core/partition/` (`states.py`, `campaign.py`); `adapters/batch-schedulers/batch_campaign.py`; `skills/hep-computing/scripts/lint_task.py`. Not present yet (to be created by this workflow): `core/calibration/`, every `calib_*.py` script, `adapters/geant4/assets/g4sim_calib_eval.py`, hep-detector `simulation-calibration/`, `docs/dev/simulator-calibration/`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-2`.
2. Implement the §17 content through the scripts of §14, each check in exactly one script; follow §14's conventions (JSON output, exit codes 0–3, the standard library plus NumPy/SciPy).
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Calibrate each §8.7 value of this phase as its row says, register it, then run the gates.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-2.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- D1 (line 4085; needs the author)
- D2 (line 4086; needs the author)
- D3 (line 4087; needs the author)
- D4 (line 4088; needs the author (open part); the rest is implemented as written)
- D8 (line 4092; needs the author)
- D9 (line 4093; needs the author)
- D10 (line 4094; needs the author)
- D29 (line 4113; needs the author)
- D34 (line 4118; needs the author)
- D39 (line 4123; needs the author)
- D40 (line 4124; needs the author)
- D45 (line 4129; needs the author)
- D46 (line 4130; needs the author)
- D47 (line 4131; needs the author)
- D48 (line 4132; needs the author)
- D50 (line 4134; needs the author)
- D51 (line 4135; needs the author)
- D52 (line 4136; needs the author)
- D55 (line 4139; needs the author)
- D57 (line 4141; needs the author (open part); the rest is implemented as written)
- D58 (line 4142; needs the author)
- D67 (line 4151; needs the author)
- D68 (line 4152; needs the author)
- D73 (line 4157; needs the author (open part); the rest is implemented as written)
- D81 (line 4165; needs the author)

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- D19 (line 4103; implement the body's reading (line 38); author confirms)
- D25 (line 4109; implement the body's reading (line 38); author confirms)
- D30 (line 4114; computation: implemented as written; author confirms)
- §19-2 (§19) (line 3704; computation: implemented as written; author confirms)
- §19-3 (§19) (line 3707; computation: implemented as written; author confirms)
- §19-14.1a (§19) (line 3715; implement the body's reading (line 38); author confirms)
- §19-14.1b (§19) (line 3716; implement the body's reading (line 38); author confirms)
- §19-14.1d (§19) (line 3718; implement the body's reading (line 38); author confirms)
- §19-14.1e (§19) (line 3719; settled by plugin source)
- §19-14.1f (§19) (line 3720; computation: implemented as written; author confirms)
- §19-13 (§19) (line 3729; computation: implemented as written; author confirms)

Accepted or decided items that this phase implements (their text in Part B is normative):

- D7 (line 4091; accepted 2026-11-09)
- D16 (line 4100; accepted 2026-11-09)
- D18 (line 4102; accepted 2026-11-09)
- D21 (line 4105; accepted 2026-11-09)
- D33 (line 4117; accepted 2026-11-09)
- D35 (line 4119; accepted 2026-11-09)
- D36 (line 4120; accepted 2026-11-09)
- D49 (line 4133; accepted 2026-11-09)
- D54 (line 4138; accepted 2026-11-09)
- D56 (line 4140; accepted 2026-11-09)
- D59 (line 4143; accepted 2026-11-09)
- D61 (line 4145; accepted 2026-11-09)
- D62 (line 4146; accepted 2026-11-09)
- D65 (line 4149; accepted 2026-11-09)
- D70 (line 4154; accepted 2026-11-09)
- D71 (line 4155; accepted 2026-11-09)
- D72 (line 4156; accepted 2026-11-09)
- D79 (line 4163; accepted 2026-11-09)
- §19-14.1c (§19) (line 3717; accepted 2026-11-09)

#### Thresholds and test designs

**Gate (§17, verbatim)**: The negative tests of P3, P7, G1–G8, V and propagation pass; segmented calibration and the joint fit agree (all of the above on the toy detector); the negative tests of P8, G9

**§8.7 rows of this phase (verbatim)**:

- §8.7 line 2000: **N_c and coverage targets of G8** — design value: the table of §8.4 — calibration: estimate the overall false-alarm rate and power with 1000 repetitions of G8 — phase column: 2
- §8.7 line 2001: **allowed fraction of the linearity check** — design value: 5% of toys with difference > 0.5 — calibration: compare the G6 p-value distributions and coverage of locally linear toys and full toys — phase column: 2
- §8.7 line 2002: **λ estimate of P7** — design value: cross product of two independent MC sets — calibration: compare with "single MC set minus tr(C⁺V_Δ)", and verify unbiasedness with alternative hypotheses of known truth — phase column: 2
- §8.7 line 2003: **c and linearity threshold of shift mode** — design value: c = 0.1 (P8 at θ_ref; 1.5c for the recomputation at θ̂); t_lin = 0.06 for Δ_i of §5.5 (replaces the 30% symmetry and the 2 ± 0.3 ratio; settled by computation, en/compute-19-2.md; to be confirmed by the author) — calibration: compare shift and profile coverage in ≥ 1000 repetitions per configuration, with the true φ drawn from its constraint, over the information λ, the nonlinearity of the φ response and the refit noise (note 5) — phase column: 2 (first calibration done on a reduced toy; confirmation on the toy detector open, note 5)
- §8.7 line 2005: **K of G7** — design value: screening 5, standard 10 — calibration: estimate power with a deliberately underestimated V_MC — phase column: 2
- §8.7 line 2006: **f in the ESS threshold** — design value: 0.1 — calibration: check the behavior of G7, G8 at f = 0.1 — phase column: 2 (G7, G8 delivered in phase 2)
- §8.7 line 2007: **Jacobian MC-noise bias bound of P5 (§8.2 note 3)** — design value: \|b_J,i\| ≤ 0.15σ_tot,i^design (settled by computation, en/compute-19-13.md; to be confirmed by the author) — calibration: in the θ-dependent configuration of note 4, confirm that with the bound the extra 68%/95% undercoverage is ≤ 0.01 (≥ 10⁴ repetitions) — phase column: 2
- §8.7 line 2011: **numerical tolerance τ_num of exact constraints (§9.2; variance in standardized units)** — design value: 10⁻¹⁰ — calibration: four confirmations on the toy detector (note 1) — phase column: 2 (D76)
- §8.7 line 2012: **negligibility condition for rounding (§2.1)** — design value: max_u uᵀRu / uᵀC̃⁽⁰⁾u ≤ 1/25 — calibration: confirmation by scan and on both sides of the boundary (note 2) — phase column: 2 (D76)
- §8.7 line 2013: **n_min of shape Gaussian summary statistics and B of the parametric bootstrap (§2.1)** — design value: note 3 — calibration: note 3 — phase column: 2 (D76)
- §8.7 line 2014: **upper limit on the fraction of G5 failures in cross-validation toys (§9.3)** — design value: 20% — calibration: compare the size of the conditional reference distribution and of the true conditional distribution on critical fold splits (P3 just passing) and on scans of the θ̂ position; confirm that above 20% the size bias is no longer negligible — phase column: 2
- §8.7 line 2015: **replica-difference construction of toys (§6.6)** — design value: default construction — calibration: note 4 — phase column: 2
- §8.7 line 2016: **number of toys for the estimated Ĉ_r** — design value: ≥ max(500, 10k) — calibration: compare the distribution of the ratio of eᵀĈ_r⁺e to eᵀC_r⁺e (median after the correction factor (n−k−2)/(n−1) within 1 ± 10%) — phase column: 2
- §8.7 line 2017: **one-sided lower bound of the cross product λ̂_a^cross (§9.4)** — design value: independent MC repetitions or a valid bootstrap, with the number of repetitions and the quantile method declared in the plan; level 1 − α_P/(2m) on the toy path, 1 − α_P/m on the analytic path — calibration: on alternative hypotheses of known λ_a, over a range of MC noise, confirm that the bound lies below the true λ_a with at least its nominal probability (D59) — phase column: 2
- §8.7 line 2018: **basin admission, separation and tie tolerances, and number of starts (§7.4)** — design value: R_admit = 1; τ_bar = max(0.1, 4σ_noise) at 19 segment points; τ_tie = max(0.01, 4σ_noise); max(2d, 16) Sobol starts (settled by computation, en/compute-D57.md; to be confirmed by the author) — calibration: note 6 — phase column: 2 (3 for the RICH replica)

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- 25 Appendix D entries need the author before this phase (index); D68 is decided together with D3 and §19-14.1f (A1)
- Most §8.7 rows belong to this phase: calibrate each before the gate run that uses it, never on the gate run itself

#### Execution log

- (filled in during the phase)

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3580), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

# Simulator calibration phase 3: Surrogate model and g4sim evaluator

## Background

Phase 3 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3581). Refreshed on 2026-11-12 at the start of phase 3 from Part B, `simcal-decision-index.md` and `simcal-approvals.md` (approval A12) on `origin/main` ca70a606 (phases 0–2 merged). It was first a **draft** written with the task package of 2026-11-10: phase 0 refreshes it from Part B and `simcal-decision-index.md`, lints it and registers it before any run a threshold judges (`simcal-task.md`, Sections E4 and E9). The §17 text and the §8.7 rows below are copied verbatim from Part B; the lists marked **Inferred** are the drafter's reading of which scripts and test sections the content touches.

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

On `simcal/phase-3`, from `origin/main` ca70a606 (phases 0–2 merged: #385, #386, #396; hep-research 0.66.1 and later): `core/calibration/` with the phase 0–2 engine (`toy.py`, `toy_problem.py`, `toys_linear.py`, `problems.py`, `likelihood.py`, `fit.py`, `identify.py`, `interval.py`, `shift.py`, `validate.py`, `closure.py`, `propagate.py`, `design.py`, `design_noise.py`, `data_checks.py`, `kernel_check.py`, `contract.py`, `chain.py`, `deps.py`, `use.py`, `io.py`, `linear.py`, `reweight.py`, `preflight.py`, `data_release.py`), the phase-3 stubs `emulator.py` (answers `incomplete`) and `evaluator.py` (ask/tell refused), and the `calib_*.py` scripts in `skills/hep-statistics/scripts/`. g4sim (S0–S9 merged): `core/simulation/` (`response.py`, `digitize.py`, `efficiency_map.py`, `rng.py`, `seeds.py`, `hits.py`, `conditions.py`, `source_density.py`), `adapters/geant4/assets/` (`g4sim_run.py`, `g4sim_efficiency_map.py`, `g4sim_digi/`). Not present yet: `adapters/geant4/assets/g4sim_calib_eval.py`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-3`.
2. Deliver the content in six work packages, in two waves; each runs in its own git worktree branched from `simcal/phase-3`, passes the commit gate, and is merged into `simcal/phase-3` (merge commits) with the gate re-run after each merge (subagents approved by the user, 2026-11-12):
   - wave 1: **WP-A surrogate model** (ask/tell, training set, P6, V_emu, the combination of resimulation and surrogate model, the §19-5 reading of A12; `emulator.py`, `evaluator.py`, `calib_emulator.py`); **WP-B g4sim evaluator** (`g4sim_calib_eval.py` of §7.1, common random numbers, the event-interval check of §6.6, the g4sim support and recording levels of §6.1); **WP-C model identity and binding** (the masked-hash model identity of §5.1 with D86 and the §19-g5 integration tests, the node binding and candidate-method derivation of §11.4 Table 2; §15.3.19, §15.3a);
   - wave 2, after wave 1 is merged: **WP-D efficiency-map φ** (§6.7: the map term U(θ)φ_map, the seeds of the mapping runs, the joint-pattern replicas, the θ-noise item of P5 (D28), the D84 G6 size check, the D83 (1) exemption of A12); **WP-E PDE split** (§6.7: routes 2₁, 3 and 1, the split check with its nested pair, the route-3 replicas); **WP-F synthetic ZDC fixture** (§15.2, P0 (k_B) with its spot check, the D6 reading of A12, the positive g4sim tests) and the **RICH replica items** on `ams02-rich-replica` (§15.2 line 3149: with a single β, refractive index and radiator height decided not identifiable by P3 with a "multiple β" hint, and P3 passing after a second particle or momentum; §8.7 note 6 (row 2018, phase 3 for the RICH replica, line 2081): the §7.4 basin classification on its degeneracy).
3. Each work package adds its unit tests (positive tests and the negative tests of its gates, each negative with a positive control); each check in exactly one script (§14), JSON output, exit codes 0–3, the standard library plus NumPy/SciPy.
4. Before each §8.7 calibration run, re-register this card with its configuration fixed (tightening only); run each calibration as registered; register the calibrated value before the gate run that uses it; never reuse a calibration run as a gate run. Every Slurm submission needs the user's approval, per array.
5. Run the gates as registered, then the independent review (Section E4, step 10), the common checks and the hand-over.

## Deliverables

#### Deliverables

- Create the scripts and modules listed in the scope checklist that do not exist yet (Repository Context), with their tests.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-3.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1). All eight are approved by record A12 (2026-11-12, “Accept all 8 as proposed”), which states the decision of each; phase 3 implements them as recorded there:

- D6 (line 4090; needs the author before the phase it is deferred to); approved, record A12
- D83 (line 4167; needs the author); approved, record A12
- D84 (line 4168; needs the author); approved, record A12
- D85 (line 4169; needs the author); approved, record A12
- §19-5 (§19) (line 3709; needs the author before the phase it is deferred to); approved, record A12
- §19-8 (§19) (line 3712; needs the author before the phase it is deferred to); approved, record A12
- §19-9 (§19) (line 3713; needs the author before the phase it is deferred to); approved, record A12
- §19-g5 (§19) (line 3742; needs the author before the phase it is deferred to); approved, record A12

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

**Carried from phase 2 (`provisional-thresholds` until calibrated here)**: the toy-detector versions of the G8 rows (calibration 1, row 2000; the G8 half of calibration 6, row 2006; the G8 items of calibrations 10, 12 and 15, rows 2013, 2015, 2018), which A11 ran on the linear configurations; the toy's sum-term-a G8 bias is finite-sample (−0.14σ at 100 events per run, −0.003σ at 8000), so the g4sim G8 runs use exposures where it is below 0.02σ or model it; the effective-count approximation pulls (BB-lite, binomial auxiliary likelihood, weighted MC; note 4); P7 power under injected non-convergence; Wishart toys for G6; θ requiring resimulation under common random numbers at the Geant4 layer (note 3); the shift-mode confirmation at r = 0.5–4 with a resimulation-level φ (note 5); the P6 part of the Bonferroni row (2004), the θ-noise item of P5 (2008). Each is registered with its configuration before its run.

**Geant4 production and evidence, campaign `p3-g4` (registered 2026-11-12 before any run; driver `tests/core/calibration_phase3_g4.py`; build `g4sim_run-build28`, SHA-256 8b6230c1…, the S8 judged build, C++ unchanged since but a comment; outputs /ceph/sharedfs/work/AMS/hsinyichou/simcal-p3; card list SHA-256 915def34…, regenerated deterministically by `--cards`)**:

- ZDC fixture (the g4sim ZDC example's full detector; crystals PbWO4_scint, Birks 0.1 mm/MeV, yield 200/MeV, r = 0.5, all `assumed`; scorers zdc_split, zdc_classes, zdc_visible on readout `ecal`): 7 runs × 20,000 events: nominal; k_B 0.02, 0.21, 0.4; light yield 180 and 220 /MeV, all on the nominal events (seed 599181870, block_seed simcal-p3/zdc/fit/nominal/0, events [0, 20000)); reference on independent events (seed 280556344, simcal-p3/zdc/reference/nominal/0).
- RICH replica (`ams02-rich-replica`, FTFP_BERT_EMZ with optical physics): (24 design + 8 held-back surrogate points) × {100 GeV/n protons, 2.4 GeV/n protons} = 64 runs × 2000 events; θ = height_mm and the rindex scale (binding form `scale`); seeds 1517095878 and 1480442192, one block per β sample shared across the points. Observable: the per-event median hit radius at the detection plane rebuilt from the emission point and arrival direction (`plane_radius`; the evaluator's `ring_radius` at fixed expansion does not depend on the height).
- Evidence items and rules (`provisional-thresholds`; ZDC with the coupled default): zdc-p0-response, P0 of the light yield against the full runs at 180 and 220 and the reference events (§8.2 note 1: |Δθ| ≤ 0.1σ_tot + z·σ_MC, Bonferroni at α = 0.01); zdc-birks-rerun, the rerun from `edep_by_dedx_class` within `reweighting_bound` for every (event, volume) and the mean within its bound at each k_B run (D75, §15.2); zdc-p0-birks, P0 (k_B) at 0.02, 0.21, 0.4 (§15.3.1); rich-p3-p6, P3 (λ_min ≥ 0.1, σ_post/σ_prior ≤ 0.4) failing for one β with the "multiple beta" hint and passing for two β (§15.2 line 3149), and P6 on the 8 held-back points (§8.2 note 4); rich-note6, the §7.4 basin classification unchanged in ≥ 0.99 of ≥ 1000 toys under 10 reseedings (§8.7 note 6, row 2018) for one β and two β, truth {height 465 mm, scale 1.0005}.
- Order: `--cards` on the login host, Geant4 array (71 tasks: 0–6 ZDC, 7–70 RICH; pilot tasks 0 and 7 first), `--tell` (one task), evidence array 0–3, then 4–23 (note 6) after task 3; merge `--merge evidence --out evidence-merged.json`.

**Second registration of row 2004 (P6 part), campaign `p3-cals-p6` (registered 2026-11-12 after the first registration failed, the fix and the user's decisions above; the first result stands as recorded)**: the driver's P6 family (tasks 0–119 of `calibration_phase3_cals.py`) with fresh seeds (repetition offset 10⁶, because the research used the first run's repetitions), the pull χ² referenced under the joint covariance of the held-out points, H ∈ {8, 20, 40} × 3 observables, v ∈ {0, 1}, 2000 repetitions per configuration. Rule: per configuration with v = 0, P6 failures ≤ 29 of 2000; the v = 1 configurations reported, not judged.

**Calibration configurations, campaign `p3-cals` (registered 2026-11-12 before any run; driver `tests/core/calibration_phase3_cals.py`, 188 tasks; every result `synthetic` and `provisional-thresholds`; Geant4 not run, its versions of these rows remain to be run)**:

- Row 2004, P6 part: the toy detector with the threshold evaluated by a surrogate model (three single-photoelectron observables), held-back points from the surrogate design (seed 20261313) at H ∈ {8, 20, 40} × 3 observables; a known-error toy surrogate (an independent design-point MC at the query point plus an error drawn N(0, V_emu), V_emu = v·cov_Δ with v ∈ {0, 1}, the two sharing the MC draws); 2000 repetitions per configuration. Rule (fixed here; Part B's row gives none): per configuration, P6 failures ≤ 29 of 2000 (the phase-1 form of this row: pass probability 0.979 at a true rate α = 0.01). Reported, not judged: the |Δm| part alone, the rate of the Bonferroni z alone, the size of the pull χ², the V_emu scale.
- Row 2008, θ-noise bounds of P5: a synthetic map of 8 bins with ε_b(θ) = p_b·θ·(1 + c_b(θ−1)), J = 6 design points, the exact scan covariance of the map, a surrogate model in regression mode, φ_map profiled (closed form) with θ; photons per mapping run {10⁶, 10⁷} × design spacing {0.1, 0.2} × seeding {shared (divergence per step = spacing), independent, purely nested (divergence 0)} = 12 configurations; 2000 interior repetitions and N_c = 412 boundary repetitions per configuration. Rule (§8.7 verbatim): within the bounds (s_i ≤ 0.25, κ_i ≤ 0.05; classified by the median over repetitions of the worst design point, fixed here), the pull standard deviation of θ̂ ≤ 1.05 and G8 passes at the full level of §8.4 (Holm, α_G8 = 0.05); configurations outside the bounds are reported, not judged. G8 pseudo-data are Gaussian N(μ, V) (a synthetic stand-in for §8.4's event-level resampling; recorded as such).
- Row 2009, PDE split, on the synthetic per-photon optics fixture (20000 photons): (a) 2000 exact nested pairs each for route 2₁ (p₀ = 0.4) and route 3 (a PDE(E) table), the pair sized exactly at the rule; rule (§8.7): joint pass probability ≥ 0.94; (b) power against a reflectance tied to the PDE, ρ ∈ {0.05, 0.1, 0.25, 0.5}, 500 pairs each, reported (also without the nesting rows); (c) route-3 replicas, 200 maps, R = 1000, grids of 1, 3, 6, 12, 24 cells; rule (fixed here from the row's design value): mean replica variance of Σ_c ε over the multinomial variance ≥ 0.98 for every grid whose grid check passes.
- Seeds: `default_rng([20261312 + 10⁵·c + r, j, …])`, c = 1 (P6), 2 (θ-noise), 3 (PDE). Merge: `calibration_phase3_cals.py --merge OUT --out summary.json` (complete, one clean commit, every rule).

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). Batch work on Linux and Slurm through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7, item 3.
- hep-research 0.65.1 or later; for g4sim items, the g4sim stages of §17 `merged` (`g4sim-status.json`).

#### Risks and stop points

- D6, D83, D84, D85 and four deferred §19 items needed the author before this phase: approved by A12 (2026-11-12)
- D83 (1): a built map fails its own `efficiency-map/1` schema (`form.uniformity`); checked with that single exemption until fixed upstream (A12)
- RICH replica: resolved at the phase start (2026-11-12). The S7 gate record's "not yet expressed" is in the open items of S7's first judged run; the same record's section "The RICH replica case (2026-11-08)" expresses it as the reference case `ams02-rich-replica` (210b1685; FTFP_BERT_EMZ on the maintainer's word; job 7523520, +0.56% within 3%, control caught), the fixture Part B §15.2 (line 3095) names; `g4sim_run.py check-spec --run run.json` on it returns ok at f93841c3. Remaining limits, from Part B: `synthetic` (a positive test of P3/G5 and of the §7.4 basin classification, never validation), no PDE stage (§19, C3), and a θ on the refractive index needs resimulation (Geant4 runs on Slurm, each array approved by the user)
- Open for the author after wave 1 (reported, not decided): (i) the decision rule of the G8 full-simulation spot check of A12 (§19-5) — A12 makes it the gate for the surrogate's error but gives no criterion; `spot_check_record` returns `not-decided` with P6-form statistics, so the three-method G8 gate cannot be judged on surrogate pseudo-data until it is given; (ii) whether zero suppression covers only `readout_external` stages (WP-B reading); (iii) for D83 upstream: g4sim schemas leave many numbers untyped and type decimals as strings, so "0.05" and "0.050" in an overlay give different `geometry_id`s
- Open for the author after wave 2 (reported, not decided): (iv) Part B places the 1/√(R−1) of U = M·V inconsistently between the fixed-map paragraph and the propagation paragraph of §6.7 (E7 item 6; WP-D chose the reading that makes UUᵀ = J·Cov·Jᵀ exact for linear observables); (v) the contract has no field for the map mode that Part B says it declares (read from the plan for now); (vi) route 1 of the PDE split is defined only for a scale p: for a PDE(E) holding θ with an observable not linear in ε no nested thinning is specified (not enforced); (vii) what a G8 `gap` (D6, A12) means for the evidence grade; (viii) the observables of P0 (k_B) are not named in §15.3.1
- The Geant4-level G8 and §8.7 calibrations are Slurm-scale; each array needs the user's approval
- Geant4 was not run for the PDE split's evidence; repeat with Geant4 transport (§15.2)
- g4sim preconditions of §17: S7 is merged with gate 3 (TR yield) a recorded gap, which no phase-3 item uses (`docs/dev/geant4-architecture/g4sim-gates/S7.md`); read each stage's gate record, not only its status

#### Execution log

- 2026-11-12 wave 1 merged: WP-C at 25491272 (f4603c8c), WP-A at aea3a8a3 (a08e6523), WP-B at 4927f3cd (005d5770, 170036f7, 402ec954); binding reconciliation 57301acd. Choices (none contradicts Part B):
- WP-A: surrogate = universal kriging (squared-exponential kernel, linear trend, one correlation shared by the observables, REML, kriging-matrix condition ≤ 1e8), a linear smoother whose weights w_j(θ) §6.7 needs, with analytic derivatives; Part B fixes no form. Modes `interpolate` and `regression` (fitted nugget, map-varies-with-θ mode).
- WP-A: σ_Δ of P6 = the B→∞ limit of the event bootstrap from paired per-event contributions (the convention of P5's ESS item); held-back points use the scan's common random numbers, so Δm isolates the interpolation error.
- WP-A: V_emu enters W and V_G, not Σ_MC (it is not MC noise); off the training θ_other it keeps its training value. V_MC of a surrogate prediction = Σ_j w_j V_MC,j (correct under the scan's common random numbers). P6 χ² decided on the upper tail, the lower-tail p reported. Defaults: n_design 24, held_back 8, seed 20261201, mode interpolate. Plan settings under `plan.design.surrogate`; `calibration-ask-tell/1` is a working file without a schema.
- WP-A: surrogate pseudo-data for G8 (A12, §19-5) are Gaussian N(μ̂, V_data); the spot-check plan rejects seeds shared with the training state, duplicate seeds and overlapping intervals.
- WP-B: the evaluator derives the method from each binding (source → analytic reweighting; detector `birks_mm_per_MeV` → deterministic rerun with `reweighting_bound` (D75); pipeline or conditions → re-digitization through `g4sim-digi-job/1`, conditions jobs in Python only (D83 (9)); other fields → resimulation via ask/tell). Birks with downstream scintillation scales E^L, E^S by the per-(event, volume) visible-energy ratio (reading of §5.4, flagged `kB-split-nominal`; P0 at the k_B extremes required).
- WP-B: zero suppression read as `readout_external` stages only (the electronics threshold is not a generation-time filter); truth pruning flagged whenever `truth.keep` ≠ ["all"]; event-time rule {kind: linear, t0_ns, ns_per_event}; one (use, set) = one batch (common random numbers); a mapping-run set = (scan) with shared seeding, (scan, point) otherwise; one seed block and interval per design in ask.
- WP-B/WP-C reconciled (57301acd): the g4sim parameter bindings come from the contract's locked `parameters[].bindings` (masked into the model identity); a plan copy that disagrees is rejected (`binding.plan_contract_mismatch`); a θ bound in two evaluator documents is rejected.
- WP-C: untyped JSON numbers normalized as decimal/1; decimal strings kept literal (two spellings, two identities: a redo, never a false "same model"); "labels and sources" of §5.1 read as detector-spec `source_of_facts` and `facts`, overlay and snapshot `description`, `source_of_facts`; the detector-spec `legacy` block excluded as in g4sim; ψ bindings not masked; Table 2 rows taken literally; mask placeholder "calib-masked/1"; D83 (7) a constant `RECORDED_OVERLAY_RUN = False` until the upstream fix.
- 2026-11-12 wave 2 merged: WP-D at 3913f3f6 (74e7702f) and 87c7eebe (5eb0b435), WP-E at 9845e55b (36ffc8a5), WP-F at 6c89fc53 (fff5dcbd). Choices (none contradicts Part B):
- WP-D: native bases B_map = WS from g4sim replicas 1..R (R ≥ 100, also for joint-pattern replicas); k/n centre; joint-pattern replicas keyed `calib-map-joint/1`; the analytic covariance is the plug-in multinomial of the pattern frequencies; the fallback's nearest design point is nearest in the unit cube of the design box; U_j in link space; φ_map last in β, profiled with θ in eta_link and score_fisher.
- WP-D: M in U = M·V is the replica differences divided by √(R−1) (see the open items); the D84 size is the GLS χ² of the profiled fit against χ²_{n−d}, decided on the point estimate ≤ 1.5α with the Clopper–Pearson 95% interval reported; toy t draws replicas R+1+t(R+1)… and its truth from the next.
- WP-D: the map mode is read from the plan property `efficiency_map` (Part B: the contract declares it; the contract schema has no field); an observable enters through the surrogate only when listed in `efficiency_map.through_surrogate`, otherwise a map-affected Poisson or binomial observable is rejected (remedy plan); the joint-pattern input is read by the new adapter `g4sim_map_patterns.py`, which reuses the map builder's CSV reader and binning.
- WP-E: loose `pde_split` objects in the contract (PDE model) and plan (routes, checks) schemas; a PDE binding is {document "evaluator", pointer "/pde…"}, masked in the identity under /pde/table; split-check χ² over the (bin, channel) count z's plus per-bin transit terms; Δθ cells as independent thinning; remedy "larger-pair" only when only the 2sd term fails; route-3 grid at the PDE table's knots, transit rounded per cell; route-1 photon index in channel order; EFFICIENCY > 0 tested for dielectric_LUTDAVIS, coated or the DAVIS model.
- WP-F: P0 (k_B) judged on the width observable alone (with the mean included the mean carries the k_B information and P0 passes at r = 0.5); the k_B spot-check full run reuses the nominal run's seed, interval and set (paired; k_B draws no random number in transport without optical photons, to be confirmed with Geant4); the k_B extremes go to P0 when the scintillation node is evaluated by a P0 method, else to P6 (reading of "these nodes", §5.4 line 1040); the light-yield extremes are required (§5.4 line 1039).
- WP-F: the ZDC fixture uses a labelled synthetic transport stand-in (no g4sim products with the needed scorers in the repository) with g4sim's Python layers downstream; the RICH items use a labelled analytic Cherenkov stand-in (ring radius; second momentum 2.4 GeV/n) until Geant4 products exist; the rindex θ is a multiplicative scale n(E) → s·n(E); D6: zero weights allowed in a positive-weight sample, samples tried in plan order, `gap` exits 3.
- 2026-11-12 follow-ups sent to WP-B (coupled common-random-number sampling in re-digitization; spectrum-scale binding; ring-radius/photon-hit observable) and WP-E (route 3 in the evaluator; split-check δμ automation).
- 2026-11-12 follow-ups merged: WP-E e982db59 (route 3 in the g4sim evaluator; the split check's δμ from both maps digitized with one run_seed; charge read as linear in ε in expectation when J is computed), WP-B 983db4a4. WP-B choices: re-digitization is coupled across θ by a quantile coupling of the channel multinomial on g4sim's own sub-stream (default `coupling: quantile`; `coupling: g4sim` keeps `digitize.digitize` exactly); its marginal law is g4sim's, its realizations are not (g4sim's rejection samplers cannot be coupled monotonically); jobs with timing are refused under it. σ_noise of evaluator-problem fits is estimated per §8.1 from K ≥ 5 independent batches: the width fit passes G1 only with it, with either coupling. A binding of form `scale` multiplies a whole spectrum (rindex n(E) → s·n(E)); its identity mask keeps the array's shape (ratios to the first element, 12 significant digits). `ring_radius` = expansion_mm × tan(angle to the axis), for direct-ring photons.
- 2026-11-12 finding (P0 (k_B), synthetic ZDC fixture; not a judged run): under the coupled default, P0 at r = 0.5 fails at both k_B extremes (ratios 1.6–1.9 at k_B = 0.02 and 6.1–6.8 at 0.4, three seeds), ≈ 1 at the interior point 0.21, and passes at r = 1: the nominal-split re-digitization (WP-B's `kB-split-nominal` reading of §5.4) is biased across the k_B prior, so k_B with the scintillation formula downstream at r = 0.5 is not re-digitizable and goes to the next tier (rerun or resimulation), as P0 intends. Test `test_coupled_default_sees_the_split_bias_at_both_extremes`; the machinery tests keep `coupling: g4sim`. To confirm with Geant4 products (the ZDC production runs).
- 2026-11-12 CI fixes (PR #400): the new adapters registered in the CLI-robustness and missing-dependency inventories (d0a6fc18; the commit gate now runs both tests); the RICH stand-in's proton mass taken from core/constants.
- 2026-11-12 WP-G drivers merged (15e900d0 at 337240f3). Fixed here: the row-2004 P6 rule ≤ 29 of 2000 (phase-1 form; 1.25α would fail with probability 0.11 at a true rate α), the row-2009 (c) rule ≥ 0.98 (the row's design value), "within the bounds" by the median worst-point s, κ. The 20-repetition pilot printed pull standard deviations; nothing was changed after seeing them.
- 2026-11-12 auto-submit, user 2026-11-12: campaign p3-cals, Slurm array 7596118 (188 tasks, edr1-al9_short_serial, account ams, 2000M), from the clean worktree tmp/wt-p3-cals at the registering commit f9adb138 (card SHA-256 ee115051…); outputs campaigns/p3-cals/out.
- 2026-11-12 WP-I drivers merged (6b06b05e): build 28 reused; seeds from block_seed (§14.1); one thread per task; a full light-yield run moves the detector's scintillation yield; a k_B 0.21 run added (P0 needs ≥ 3 full points); the RICH observable is `plane_radius` (the evaluator's `ring_radius` is blind to the height — proposal for g4sim: write the arrival position into photons.csv); surrogate fits bounded one finite-difference step inside the design box (§6.4 never queries outside it); `merge_parts` keeps photons.csv rows. Stand-in pilot (not judged): two-β P3 passed, single-β failed with the hint; P6 of the two-β surrogate failed (1 of 16 points, ratio 1.82, at the high-index corner of the 2.4 GeV/n sample) — a risk for the real run (remedy plan: more design points); nothing retuned.
- 2026-11-12 fix: `fit.minimize` never used a problem's analytic Jacobian (a bound method is a new object on each access, so `hfun is problem.h` was always False); now it does. Only problems defining H are affected (none of the phase-2 evidence); regression test `test_minimize_uses_the_problems_analytic_jacobian` (fails without the fix).
- 2026-11-12 auto-submit, user 2026-11-12: campaign p3-g4 pilot, array 7596355 (tasks 0, 7) stopped by its own guard before any Geant4 run (a hand-typed commit prefix in the job script; exit 9, nothing ran); resubmitted as 7596359 (tasks 0, 7: ZDC nominal 4.6 min, 2.3 GB; RICH 1.9 min, 0.3 GB), then 7596402 (tasks 1–6, 8–70), from the clean worktree tmp/wt-p3-g4 at c9333ba0.
- 2026-11-12 WP-H drivers merged (ab3338f0 at ee063785): three-method G8 on the toy detector (gain reweighted, relative_gain_b rerun, threshold by surrogate; the ZDC stand-in has no source support for reweighting and no resimulation-level parameter); the A12 spot check reported `not-decided`; fit intervals θ̂ ± zσ_tot; each pseudo-data set's surrogate trained on its own MC; the toy G8 rows at exposure 8000. The momentum-scale lower bound was set to 0.999 after pilot fits from the prior centre failed at 0.5 and 0.95 (a plan choice after a pilot, not a threshold; recorded). Fix: P8 returned λ = 0 (a vacuous pass) for a φ resimulated under common random numbers (finite-difference step below the staircase); it is now `incomplete` (`p8.derivative_unresolved`, remedy plan).
- 2026-11-12 CALIBRATION RESULTS, campaign p3-cals (array 7596118, 188 tasks at f9adb138, merged from tmp/wt-p3-cals: campaigns/p3-cals/p3-cals-merged.json, SHA-256 18084a26…; `synthetic`, `provisional-thresholds`):
  - Row 2008 (θ-noise of P5): PASSED in all 12 configurations (all within the bounds; pull sd 0.976–1.037; G8 passed at the full level in each).
  - Row 2009 (PDE split): PASSED: (a) exact-split pass rate 0.952 (route 2₁) and 0.940 (route 3) ≥ 0.94; (b) power 1.0 at every ρ (without the nesting rows 0.51, 0.99, 1.0, 1.0); (c) replica/multinomial ≥ 0.98 wherever the grid check passes (1 cell: grid check fails, as designed).
  - Row 2004, P6 part: FAILED (STOP, Section E7 item 4). False alarms of 2000: H = 8: 0 (v = 0), 70 (v = 1); H = 20: 0, 70; H = 40: 456 (v = 0), 321 (v = 1); rule ≤ 29. Two separate patterns: (i) with an exact surrogate (v = 0) at H = 40, every failure is the pull χ² (size 0.228 at α = 0.01, mean χ²/dof 0.99), the |Δm| part never fails; (ii) with a surrogate whose error is drawn at V_emu (v = 1), the |Δm| part fails in 3.5–4.6% (its bound 0.3√V_data + z·σ_Δ does not contain V_emu). Not retuned, not rerun; reported to the user.
- 2026-11-12 row-2004 diagnosis (research, not judged; user: "Diagnose, then report"): Slurm 7596492 and 7596529 (20 tasks each, campaigns/p3-research, from tmp/wt-p3-cals at f9adb138; the first run's seeds, H = 40, v = 0, 500 repetitions). The held-out differences are correlated across points (median correlation 0.42; one seed per side shared by every point): the summed per-point χ² of P6 has the right mean (0.98 per degree of freedom) and 27 times its χ² variance, so 105 of 500 fail at α = 0.01. The per-event joint covariance matches the empirical one (variances 1.02, correlations rms 0.028) but its inverse in 120 dimensions deflates a joint χ² (0.69 per degree of freedom). The summed per-point χ² judged against its exact null distribution under the joint covariance (a weighted sum of χ²₁, Imhof) has size 0.012 (6 of 500) and uniform p-values.
- 2026-11-12 user decisions on row 2004: "Joint + exact reference" — implemented as Part B's statistic (the summed per-point pull χ²) judged against its exact null distribution under the joint covariance, because the diagnosis showed that the deflation is not a self-normalization effect (40,000 events per run against 120 dimensions); and "No: v = 0 only" — the false-alarm rate is judged for the correct surrogate (no error beyond MC noise); the v = 1 rates are reported as P6's sensitivity to an emulation error (record A13).
- 2026-11-12 engine fix: `emulator.p6` takes `cov_joint` (the differences' covariance across held-out points) and references the pull χ² to `generalized_chi2_sf`; without it, and without `independent_points`, the pull part is `incomplete`; `joint_delta_covariance` builds it from the per-event contributions (common random numbers and the shared design-point runs), and `p6_from_evaluator` passes it. The cross-point covariance of V_emu is not modelled (a limitation, reported). Tests: correlated points (ρ = 0.9) oversized with the plain reference and of size under the joint one; independent points agree; Imhof equals χ² at unit weights; no joint input → incomplete.
- 2026-11-12 user: "allow auto summit slurm jobs" — simcal Slurm arrays are submitted without asking once their configuration is registered here and the commit gate passed, each logged here as "auto-submit, user 2026-11-12"; failed gates or calibrations still stop (E7.4). PRs to main are merged incrementally on green CI (user, 2026-11-12).
- 2026-11-12: the RICH-replica risk closed: the S7 case `ams02-rich-replica` expresses it (see Risks); its items assigned to WP-F.
- 2026-11-12: card refreshed at the phase start (A12; work packages WP-A to WP-F in two waves of parallel subagents, approved by the user; Slurm per array).

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3581), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

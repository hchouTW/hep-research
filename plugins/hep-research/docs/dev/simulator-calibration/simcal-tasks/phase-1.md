# Simulator calibration phase 1: Evaluation and design stage

## Background

Phase 1 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3579). Drafted with the task package of 2026-11-10 and registered in phase 0; refreshed at the start of phase 1 from Part B, `simcal-decision-index.md` and approval A7, and registered again before any run a threshold judges (`simcal-task.md`, Section E4 step 4). The §17 text and the §8.7 rows below are copied verbatim from Part B. Phase 1 starts on top of the unmerged `simcal/phase-0` (PR #385) on the user's word (execution log).

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 1 of §17 so that its gate holds: The negative tests of A0, P0, P2, P5 pass; reweighting and rerun agree

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] Analytic and step-level reweighting (including the support and mixture formulas), rerun, `resample`, `evaluate_from`; the linearized fit operator A for Gaussian blocks (for the design stage; ν and η are included as linear nuisance columns u_k, s_j with N(0,1) constraints, so σ_tot^design already contains their contribution in this phase and does not need to wait for the full likelihood of phase 2); A0, P0, P2, P5 (including feasibility and the final method), the surrogate-interface stub of P6; simulation of the toy detector

**Items of the content, with their Part B homes**

- [ ] Weight formula of §3.6 (numerator on S_θ at θ′ and on S_q∖S_θ at θ₀; denominator: the mixture Σ_j c_j Π_{s∈S_q} q_{j,s} with c_j = n_j/N, recomputed for every event with all q_j, times the nominal kernel on S_θ∖S_q); the check w ≡ 1 for S_q empty and θ′ = θ₀ (§3.6, §15.3.1).
- [ ] Support condition of §6.1 (supp q ⊇ the union of supp K(·;θ′) over the prior; filtered or zero-suppressed events are missing support; reweighting only for a parameter acting entirely through the kernel density) and the merging of additional events with the mixture formula (§6.1 item 5).
- [ ] Step-level reweighting (§3.6: physics-process parameters with per-step data stored; a product over steps).
- [ ] Rerun of deterministic kernels from stored inputs; `resample` and `evaluate_from` of §7.1; the evaluator interface (`evaluate` → pred, V_MC, n_eff, node_diag) defined in `core/calibration` (§7.1: "interface definitions").
- [ ] The linearized fit operator A for Gaussian blocks: β = (θ, ν via u_k, η via s_j, φ in profile mode), N(0,1) constraints on the nuisance columns, A = Σ_β Jᵀ V_cc⁻¹ with V_cc including V_MC (§9.2), the projected inverse when N_d,c is declared (§2.1, §9.2), σ_tot^design (§8.1), Σ_MC = A V_MC Aᵀ and Σ_data = A V_data Aᵀ (θ block, §6.7).
- [ ] A0 (`calib_contract.py preflight`, §4.2, §14): with the smoothing model declared by the contract, whether each threshold is reachable on the calibration data; the data read through `calib_data.py` with the contract draft as read channel (§9.5); the summary records only the unreachable thresholds (§5.1).
- [ ] P0 (`calib_kernel_check.py`, §8.2 note 1, D53): ≥ 3 θ′ including the worst-ESS point and the §5.4 spot checks; the plan's method against `resample` + `evaluate_from`, propagated with A; |Δθ_i| ≤ 0.1σ_tot,i^design + z·σ_MC(Δθ_i), z = z_{1−α/(2M)}, M = d × (number of θ′), α = 0.01.
- [ ] P2 (`calib_design.py`, §8.2 note 2, D77): ndf = n_c − dim N_d,c − d_free ≥ max(3, d_free), n_c counted K per count shape, K − 1 per Gaussian shape, 1 per scalar, unused observables excluded.
- [ ] P5 (`calib_design.py`, §6.7, §8.2 note 3, D41, D42): the ESS at the worst Sobol point within the prior (N_eff,k ≥ N_req,k = s_k²/(f V^unc_data,kk), N_eff over the events entering observable k); the matrix condition Σ_MC ⪯ f·Σ_data point by point on the same Sobol points, taking the worst; V_MC,kk ≤ f·V^unc_data,kk for each Gaussian-block observable (D42); feasibility and the final method (§3.6 table: the cheapest feasible candidate; an infeasible reweighting moves to the next tier automatically).
- [ ] Sobol design points and the P6 held-back set (`calib_design.py`, §6.4, D80).
- [ ] Applicability of the mandatory gates, derived from the plan's methods (§8.1, `calib_design.py`).
- [ ] P6: the surrogate-interface stub only (`calib_emulator.py`; ask/tell and P6 itself are phase 3).
- [ ] D37 (A7): the `calib_contract.py check` rule "a ψ whose effect on θ̂ propagated via A exceeds 0.1σ_tot^design must be listed as φ" (the phase-0 checker deferred it to phase 1).
- [ ] The toy detector simulation of §15.1 (pure Python plus NumPy, `synthetic`, seconds, truth known): calorimeter branch, track branch, merge node E/p, the four references, the "sum of two terms" pair, φ (material thickness), the overlapping modules and layers, η (common energy scale); the subgraph and bimodal variants.

**Scripts and homes (§13, §14; folders per Open questions 1 and 6)**

- [ ] `calib_reweight.py` (weights; G4 and G4-L are phases 2 and 5)
- [ ] `calib_kernel_check.py` (P0)
- [ ] `calib_contract.py preflight` (A0)
- [ ] `calib_design.py` (Sobol points and P6 held-back set, P2, P5, feasibility and final method, applicability, the design-stage linearization)
- [ ] `calib_emulator.py` (only the P6 interface stub)
- [ ] `core/calibration/` (engine home, steward hep-statistics; §13)

**This phase's tests (§15)**

- [ ] §15.3.1: A0; P0 (declared Poisson, implementation with ENF; missing support with U(θ, θ+1)); P2 (insufficient observables); P5 (q too narrow; interior ESS of a mixture proposal; correlated weights failing the matrix condition; Poisson reweighting infeasible at μ = 1000 with the next tier chosen); the weight formula (w ≡ 1; reweighting and rerun agree with S_θ∖S_q non-empty).
- [ ] §15.2: "Reweighting and rerun of non-generator nodes agree."
- [ ] §15.3.16: the applicability cases without g4sim.
- [ ] §15.1: the toy detector and its variants.

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`; `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- The joint likelihood, link functions beyond identity and log at the design stage, P3, P7, G1–G9 and validation (phase 2). Σ_boot and b_J of P5 (§17 placement bullet: phase 2); the θ-noise item s_i, κ_i of P5 (mode where the map varies with θ, phase 3).
- P6 itself, ask/tell, the surrogate model (phase 3); the g4sim evaluator, node binding, the g4sim support and recording-level checks, the k_B spot checks on the ZDC fixture (phase 3); learned density ratios and G4-L (phase 5).
- Non-overlap of event intervals and the toy constructions of §6.6 (phase 2, with the toys; phase 3 for g4sim intervals).

## Repository Context

On `simcal/phase-0` (1a27ab10, from hep-research 0.65.1): `core/calibration/` with `use.py`, `deps.py`, `chain.py`, `data_release.py`, `contract.py`, `io.py` and the fixtures in `core/calibration/data/` (`toy_detector.json` and its subgraph and bimodal variants: graph only); `skills/hep-statistics/scripts/calib_use.py`, `calib_deps.py`, `calib_chain.py`, `calib_contract.py`, `calib_data.py`; `contracts/schemas/calibration_*.json`; `tests/core/test_calibration_*.py`, `tests/skills/test_calib_scripts.py`. `core/` may import NumPy and SciPy (`tools/check_layering.py`, mandatory environment). `adapters/batch-schedulers/batch_campaign.py` for batch work; `skills/hep-computing/scripts/lint_task.py`.

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in worktree `simcal/phase-1` (branched from `simcal/phase-0`).
2. Implement the §17 content as library modules in `core/calibration/` with thin CLIs in `skills/hep-statistics/scripts/`, each check in exactly one module and script (§14); NumPy and SciPy only.
3. Add each test of this phase before the gate run, and show that each negative test is caught.
4. Run the §8.7 calibrations of this phase as registered below, then the gate runs, with the seeds registered here.

## Deliverables

#### Deliverables

- Create in `core/calibration/`: `evaluator.py` (the §7.1 interface and the registry of evaluators), `toy.py` (the toy detector and the small chains used by the tests), `reweight.py` (weights, support, step-level, mixture merging, ESS), `linear.py` (the design-stage fit operator A), `design.py` (Sobol points, P2, P5, feasibility and final method, applicability), `kernel_check.py` (P0), `preflight.py` (A0), `emulator.py` (P6 stub).
- Modify `core/calibration/contract.py` (the D37 rule; `preflight` dispatch), `core/calibration/chain.py` (resimulation as a candidate for a samplable density kernel, see the execution log), `core/calibration/data_release.py` (the A0 read through the one provider).
- Create the scripts `skills/hep-statistics/scripts/calib_reweight.py`, `calib_kernel_check.py`, `calib_design.py`, `calib_emulator.py`; modify `calib_contract.py` (new subcommand `preflight`).
- Modify `contracts/schemas/calibration_plan.json` (evaluator, methods, proposal, design, spot checks) and `calibration_contract.json` (A0 thresholds and smoothing model, data exposure, ψ uncertainty), additively.
- Add the tests `tests/core/test_calibration_toy.py`, `test_calibration_reweight.py`, `test_calibration_linear.py`, `test_calibration_design.py`, `test_calibration_kernel_check.py`, `test_calibration_preflight.py`, and extend `tests/skills/test_calib_scripts.py`, `tests/contracts/test_calibration_schemas.py`.
- Add the gate harness `tests/core/calibration_phase1_gates.py` (the registered gate runs below, with provenance) and the gate record `docs/dev/simulator-calibration/simcal-gates/phase-1.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`), the repository registrations (`core/OWNERS.json`, `tools/skill_scripts.json`, the reference inventory, module timings, CHANGELOG).

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1):

- D37 (line 4121; needs the author): approved, record A7 of `simcal-approvals.md` (2026-11-10): ψ must be listed as φ when its effect on θ̂ propagated via A exceeds 0.1σ_tot^design.
- D41 (line 4125; needs the author): approved, record A7: N_eff,k over the events that enter observable k (its bin for counts); until the author defines the "determining region", the checker rejects any P5/G4 decision on a tail-type functional.
- D42 (line 4126; needs the author): approved, record A7: the "add" option, V_MC,kk ≤ f·V^unc_data,kk for each Gaussian-block observable is a P5 item.

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- §19-g2 (§19) (line 3736; settled by plugin source): this workflow generates its design points itself (§6.4; owner per D80).

Accepted or decided items that this phase implements (their text in Part B is normative):

- D53 (line 4137; accepted 2026-11-09): two-sided z_{1−α/(2M)} in P0 (and P6, phase 3).
- D76 (line 4160; accepted 2026-11-09): τ_num, the rounding condition and n_min/B are calibrated in phase 2, not here.
- D77 (line 4161; accepted 2026-11-09): n_c counting rule of P2.
- D80 (line 4164; accepted 2026-11-09): `calib_design.py` owns the Sobol points and the P6 held-back set; `calib_emulator.py` the surrogate's training set (phase 3).

#### Thresholds and test designs

**Gate (§17, verbatim)**: The negative tests of A0, P0, P2, P5 pass; reweighting and rerun agree

**§8.7 rows of this phase (verbatim)**:

- §8.7 line 2004: **Bonferroni z of P0, P6** — design value: α = 0.01 — calibration: estimate the false-alarm rate with a correct kernel and surrogate model — phase column: 1, 3
- §8.7 line 2010: **smoothing model of A0** — design value: declared by the contract — calibration: confirm correct reporting with the ZDC linearity example — phase column: 1

**Values used by the phase's gates (from Part B, not calibrated here)**: f = 0.1 (§6.7; calibrated in phase 2, so P5 results carry `provisional-thresholds`); the 0.1σ_tot,i^design term of P0 and of D37; α = 0.01 of P0 (D53). σ_tot^design here is the θ block of Σ_β from the design-stage A without Σ_boot/w (Σ_boot is phase 2, §17); every P0 and P5 output states this and carries `provisional-thresholds`.

**Calibrations of this phase (§8.7), registered before they run**:

1. *Bonferroni z of P0 (phase-1 part; the P6 part is phase 3)*: on the toy detector with correct kernels, R = 1000 independent repetitions of P0 (new nominal and `resample` seeds per repetition, seeds `20261110 + 2r` and `20261110 + 2r + 1`, r = 0…999), each with the light-yield, PDE, gain and ENF parameters evaluated by analytic reweighting at 3 θ′ (worst-ESS Sobol point and two further Sobol points of a scan over these four parameters); the rerun streams of point k of repetition r are keyed by (seed of r, k), so no two repetitions share a stream (review F4). Count the repetitions in which P0 fails. Rule: the design value α = 0.01 is confirmed if the false alarms are ≤ 16 of 1000 (pass probability 0.97 at a true rate of 0.01, 0.02 at 0.025). Otherwise STOP and report; the value is not loosened. The observed rate and its 95% upper limit are recorded in the gate record for the author's write-back.
2. *Smoothing model of A0*: the synthetic ZDC linearity example (response at 8 beam energies 1–8 GeV, relative uncertainty 0.2% per point, smoothing model declared as a quadratic in E, threshold "maximum relative deviation from a straight line through the origin ≤ 2%"). Cases with a true maximum deviation of 0.5%, 1.0%, 3.5% and 5.0%: correct reporting is reachable, reachable, unreachable, unreachable, with exactly the unreachable thresholds in the summary and no data value in it. The one-sided level of the reachability decision is the contract's `alpha` (default 0.05; Inferred, execution log).

**Test design of gate 1, "the negative tests of A0, P0, P2, P5 pass"** (each negative test shows its expected finding code; each has a positive control that passes, so that the negative is not caught by an unrelated failure; fixed seeds in the tests):

1. A0: the 3.5% case of calibration 2 → `a0.unreachable` listing the threshold; the 1.0% case → reachable. The A0 read is recorded as a fit read with the draft's series as read channel; the A0 summary passes `calib_contract.py check` (`a0_summary` holds only names).
2. P0, declared as Poisson with ENF in the implementation: the plan registers the photon-generation kernel as Poisson while the toy samples it with excess variance (Fano factor 1.5) → P0 `failed`; the same plan with the kernel registered as it is sampled → `passed`.
3. P0, missing support: a node sampling U(θ, θ + 1), events generated at θ₀ only (a single support), θ′ = θ₀ + 0.5 → P0 `failed`, and the support check of `calib_design.py` refuses the plan (`support.missing`); a mixture over the prior's supports → P0 `passed`, support accepted.
4. P2: a contract with too few calibration observables (ndf < max(3, d_free)) → `p2.insufficient_ndf`; the full toy contract → `passed`; the D77 counting (K per count shape, K − 1 per Gaussian shape, 1 per scalar, unused excluded, minus dim N_d,c, minus d_free).
5. P5, four cases of §15.3.1: (a) q too narrow (no broadening of the proposal over a prior of ±2 kernel widths) → `p5.ess`; with a proposal broadened to cover the prior → the ESS item passes. (b) Mixture proposal of two components at the prior edges: the minimum ESS at an interior point → `p5.ess` found by the Sobol scan, while the edge points alone pass. (c) Weights correlated across observables: every V_MC,kk ≤ f·V^unc_data,kk holds and the matrix condition fails → `p5.matrix_condition`. (d) Poisson count reweighting at μ = 1000, prior r ∈ [0.9, 1.1]: reweighting infeasible (N_eff/N ≈ exp(−μ(r − 1)²) = 4.5 × 10⁻⁵ at the edge), the next-tier method (resimulation) chosen as final method, P5 not failed by it.
6. P5, approval A7: a Gaussian-block observable with V_MC,kk > f·V^unc_data,kk while the matrix condition holds → `p5.v_mc_diagonal` (D42); a P5 request on a tail-type functional → rejected (`p5.tail_functional`, D41).
7. Weight formula: S_q empty and θ′ = θ₀ → max |w − 1| ≤ 10⁻¹²; S_θ∖S_q non-empty → gate 2 case 2.
8. D37: a ψ with propagated effect 0.2σ_tot^design → `parameters.psi_not_negligible`; 0.05σ_tot^design → accepted.
9. §15.3.16 without g4sim: full resimulation only → P0, P6, G4, G4-L `not-applicable`; surrogate only with `resample` elsewhere → P0 `not-applicable`, P6 applicable; step-level reweighting only → P0 and G4 apply; G5 always applicable; 20 held-out points → P6 decides only the |Δm| part.
10. Cases in a later phase: P5 b_J and Σ_boot (phase 2); P5 θ-noise s_i, κ_i (phase 3); P0 (k_B) on the synthetic ZDC fixture (phase 3); the remaining gates of §15.3.1 (phases 2–5).

**Test design of gate 2, "reweighting and rerun agree"** (one registered run, `tests/core/calibration_phase1_gates.py --gate agreement`, seeds nominal 20261110 and rerun 20261111; N_MC = 40,000 events per run configuration):

1. For each non-generator density node of the toy detector with a parameter acting entirely through its density (photon generation: light yield; PDE: PDE; gain: gain and ENF; electronics: noise width, on the run configurations without zero suppression, that is all but the single-photoelectron run, with the threshold, which acts only through the suppression, left out of that case's contract, and the plan recording the filtering as ignorable for these runs, as §6.1 requires and P0 confirms), at 3 θ′ per node (the worst-ESS point of 64 Sobol points within the prior, seed 20261112, and the next two Sobol points), compare the reweighted prediction from the nominal sample with the rerun (`resample` of that node from its stored inputs at θ′, the random streams of point k keyed by (rerun seed, k), then `evaluate_from`).
2. The same comparison for θ = (light yield, PDE) acting on two nodes with the proposal broadened only on the PDE node (a mixture of 3 PDE values), so that S_θ∖S_q = {photon generation} is non-empty (§15.3.1).
3. Deterministic rerun: the relative gain of module b and the offset and sum term of layer b, rerun from stored inputs, equal a full re-evaluation with the same random numbers to a relative 10⁻¹².
4. Criteria (all must hold): (i) P0's criterion for every parameter and θ′ (A at θ_ref, α = 0.01, M = d × 3 per comparison); (ii) at each (node, θ′), χ² of Δm over the observables of the runs in which the node's kernel reads the case's parameters (not where an injected reference replaces it), with the paired MC covariance of the difference (tightened from V_MC,reweighted + V_MC,rerun after the review, F3), has p ≥ 0.01/M_2, M_2 the number of (node, θ′) pairs; (iii) item 3 exact to 10⁻¹².

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

## Validation

#### Environment

- Python 3.13.2 (`HEP_RESEARCH_PYTHON`: conda env `ml`; NumPy 2.2.2, SciPy 1.16.1); phase 1 uses the standard library plus NumPy and SciPy (§14). Worktree, outputs (`.simcal-work/`) and `TMPDIR` on the private ceph folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/`. Batch work, if a calibration does not fit an interactive run, on NSTCCore Slurm (partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13`, NumPy 2.4.6, SciPy 1.17.1) through `batch_campaign.py`, under `simcal-task.md` Section E7, item 3 (each submission approved by the user).
- hep-research 0.65.1 plus `simcal/phase-0`; g4sim not used (§17: phases 0–2 do not depend on g4sim).

#### Risks and stop points

- σ_tot^design without Σ_boot (phase 2): P0's and D37's 0.1σ_tot^design term is computed without it; results carry `provisional-thresholds`.
- Calibration 1 failing (more than 16 false alarms): STOP and report, no loosening.
- A reading needed beyond Part B that changes a decision (not only an implementation detail): recorded in the execution log and reported to the author; STOP if it would change Part B.

#### Execution log

- 2026-11-10, start: phase 0 is `gates-recorded` (PR #385 open, not merged). The user said "auto continue" after the PR was opened, read as the word to continue on top of the unmerged branch (Section E3, step 5); worktree `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-1`, branch `simcal/phase-1` from `simcal/phase-0` 1a27ab10. Package check: `MANIFEST.sha256` OK, `restore_spec.py` OK. Preconditions: phase 1 uses only phase-0 modules (present) and no g4sim item.
- Card refreshed from Part B and the index (Section E4 step 2): D37, D41, D42 approved (A7); §19-g2 settled by plugin source; D53, D76, D77, D80 accepted. Test designs and seeds above fixed before any run.
- Readings (Part B does not dictate; none changes it):
  - Candidate methods: a density kernel that the plan declares samplable, with stored inputs, also has resimulation (rerunning the node from its stored inputs with new random numbers) as a candidate; without it §15.3.1's "the next-tier method is used automatically" has no next tier for a Poisson node. Reported to the author.
  - d_free of P2 counts the parameters of β without an external constraint (θ, φ in profile mode only when unconstrained, free ω); ν, η, a constrained φ and MC nuisances each add a constraint term and a parameter, so they do not change ndf.
  - s_k² of N_req,k: the B → ∞ limit of the event bootstrap §6.7 names, the weighted variance of the per-event influence values under the target (an explicit bootstrap with B resamples runs when the plan sets `design.bootstrap` = B > 0); V_MC of the toy evaluator from the same influence values with the event weights. Changed from "an explicit bootstrap with B = 200" before any gate run: the explicit bootstrap costs B × N per observable per Sobol point (hours for one toy-detector scan).
  - A0: a threshold is unreachable when the one-sided lower confidence limit (level 1 − alpha, alpha from the contract, default 0.05) of the declared quantity of the smoothed data exceeds the threshold; Part B fixes no level.
  - Design-stage links: identity and log (delta method) only; other links and non-Gaussian blocks are refused as `incomplete` until phase 2 (§6.7).
  - Evaluators are named in the plan (`evaluator.kind`); phase 1 registers the toy detector and the small test chains; any other kind is `incomplete`.
  - Design-stage data errors: observables of different data samples (the contract's `sample`) have independent data errors, also when the MC computes them on the same events; within one sample, the per-event covariance under the target divided by the sample's `exposure`.
  - The toy detector's design plan evaluates the momentum scale and the multiple-scattering term by resimulation: reweighting them is infeasible within their priors (the momentum resolution is 1.1% against a ±1% scale prior), which P5 reports.
- 2026-11-10, implementation (E4 step 5): the modules, scripts, schemas and tests of the Deliverables. Development runs (smoke tests at 4,000 events with seeds 1–3 and the unit tests; not the registered runs, judging nothing) found and fixed: regenerated nodes counted per run (a reference injection replaces a node's kernel in some runs only), and the support check skipping runs where an injected reference replaces the node. Gate-2 case "electronics" and criterion (ii) refined as above before any gate run (tightening: an observable of a run the node does not act in has Δm = 0 and would only add degrees of freedom).
- Calibration 1 costs about 27 s per repetition at 40,000 events (about 7.5 core-hours for 1000): a Slurm campaign of 100 array tasks of 10 repetitions each, submitted only with the user's approval (E7 item 3).
- 2026-11-10, gate run 1 of gate 2 (registered card fd133e30, commit 485eaf9b): passed (all five cases; P0 ratios <= 0.40, chi2 p >= 0.84; deterministic rerun exact). Calibration 1 run 1 (Slurm, the user approved "Pilot, then full"; campaign `campaigns/phase1-p0-z/`, pilot 7556807_0 then array 7556978, 100 jobs COMPLETED, 3.2 core-hours, at most 2 min 18 s and 408 MB): 2 false alarms of 1000. Both superseded by the review's fixes below.
- 2026-11-10, guide: listing the four new scripts in `core-stats-guide.md` exceeded the 25,600-byte quick-question budget; the user chose "Trim guide wording" (wording of the Skill scripts section, meaning unchanged), and after the review "Drop the stdlib sentence" (the calib line says the engine needs NumPy and SciPy; the scripts exit 2 with a JSON message without them). 25,573 bytes.
- 2026-11-10, independent review (E4 step 10): the user approved one fresh-context reviewer subagent ("Yes, one reviewer"). Report `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-1-review.md` (SHA-256 `38f9bfbf…`), at 0f30cf3c: 1 major, 11 minor, 3 notes. Resolution, none changing Part B:
  - F1 (major): the rerun reference and `resample` now start from the stored inputs at theta' (the nominal events after the plan's resimulation and rerun at theta'), as the method's prediction does; P0 no longer depends on theta_ref equalling the generation point. Regression test `kernel_check.ReviewFixes.test_f1_theta_ref_away_from_the_generation_point`.
  - F2: P2 counts one omega per `shape_class: free-omega` count shape (section 2.1), not per free sample.
  - F3: gate-2 criterion (ii) tightened to the paired covariance, over the runs whose node kernel reads the case's parameters (registered above).
  - F4: rerun streams keyed by (seed, point); calibration 1 is rerun (the user approved "Pilot, then full").
  - F5: `calib_design.py p5` decides the final method first (section 3.6 step 2); `--declared-methods` judges the declared ones.
  - F6: missing support at a scan point fails P5 (`p5.missing_support`) and stops the linearization (`linear.missing_support`); an undefined ratio fails.
  - F7: a filtering kernel is missing support unless the plan records it as ignorable (`kernels[node].filter_ignorable`), whatever the nominal sample contains.
  - F8: `evaluate` honours `seeds['nominal']` and refuses `effects_off` (phase 4).
  - F9: a psi without the design-stage linearization is refused (`parameters.psi_needs_design`), never accepted unchecked.
  - F10: bad input exits 2 with JSON in `calib_reweight.py` and `calib_contract.py` (`check --design`, `preflight`); the A0 read is written to the ledger before A0 decides.
  - F11: the default P0 points come from a scan over the parameters evaluated by a P0 method (also deterministic rerun).
  - F12: P5 scans every theta with sampling bounds by default (`scan_parameters` for a one-case scan, as the gate harness and calibration 1 use).
  - F13: the weight-set bookkeeping of the section 3.6 formula is in `reweight.formula_log_weights` and the support decision in `design.support_check`; the evaluator answers density and support queries.
  - F14: the projected inverse is standardized by V_data^unc (section 9.2) and N_d,c coefficients are carried to log-link coordinates.
  - F15: a proposal on a non-density node and `rerun` for a stochastic kernel's parameter are refused; c_j are the realized fractions; JSON output has no NaN (null) or Infinity ("inf"); the guide's statement on the new scripts' dependencies corrected (user's choice above). Not changed: `sc/` in the guide is the shorthand SKILL.md defines (both load together, and the budget counts them together); `node_diag` and pareto k stay phase-2 (G4).
  - The design changes above (criterion (ii), the electronics plan's recorded filtering, the streams per point, the scan parameters) are registered before the gate runs are repeated at the fixed code.
- 2026-11-10, repeated gate runs at `e940ef2e` (card `ca717b11…`): gate 2 run 2 passed (`.simcal-work/gates/agreement-2.json`); calibration 1 campaign 2 (`campaigns/phase1-p0-z-2/`, pilot 7557584_0 and array 7557620, 100 jobs COMPLETED, 2.9 core-hours): 3 false alarms of 1000, alpha = 0.01 confirmed. Full repository checks at `e940ef2e`: 7 failures, 4 caused by phase 1 and fixed in `4462715b` (emulator stub input, harness timeouts, two documented claims), 3 environmental as in phase 0. Gate record `simcal-gates/phase-1.md`; phase 1 set to `gates-recorded`.
- **E8 report (2026-11-10).** Phase 1 `gates-recorded`; worktree `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-1`, branch `simcal/phase-1` (local, not pushed; on top of the unmerged `simcal/phase-0`, PR #385). Gates: both pass (`simcal-gates/phase-1.md`); none failed, no gap. Thresholds: Bonferroni z of P0 (alpha = 0.01) confirmed, observed false-alarm rate 0.003 (95% upper limit 0.0077); the A0 smoothing model confirmed on the ZDC linearity example; the P6 part of the Bonferroni row is phase 3; f = 0.1 and the other design values stay provisional (`provisional-thresholds`). Blocking: review and merge by a human, phase 0 first. For the author (not blocking): resimulation as a candidate for samplable density kernels, the A0 level, the d_free reading, s_k^2 as the bootstrap limit, the section 8.7 write-back. Proposed versions: part of the same minor release as phase 0 (numbers at merge). Next action: after merge of phases 0 and 1, or a human's word to continue on the unmerged branch, phase 2.

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- For the author (not blocking): the candidate-method reading above; the A0 level.

## References

- Part B §3.6, §6.1, §6.7, §7.1, §8.1, §8.2, §8.7, §9.2, §14, §15.1–15.3, §17 (line 3579); `simcal-decision-index.md`; `simcal-approvals.md` (A7); `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/simulator-calibration/simcal-tasks/phase-0.md` (precedent).

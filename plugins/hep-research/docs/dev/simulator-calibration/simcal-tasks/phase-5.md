# Simulator calibration phase 5: Extensions

## Background

Phase 5 of the simulator parameter calibration workflow (Part B, `simulator-calibration-v7.37.4-clean-en.md`, §17, line 3583). **Draft refresh of 2026-11-14**, prepared in the private prep folder while phase 4 closes; it is not the registered card. At the phase start it replaces `simcal-tasks/phase-5.md` (the draft of 2026-11-10, registered in the status file as `a358a75e…`) once the base commit, the approval records and the work-package approvals are filled in. It is linted and registered before any run a threshold judges (`simcal-task.md` E4 step 4). The §17 text and the §8.7 rows below are copied verbatim from Part B. Lists marked **Inferred** are the drafter's reading of which scripts, tests and rows the content touches. The open readings are in the prep decision sheet (decision-sheet-phase-5.md, outside the repository; its outcome is copied into this card at the phase start) (author items 1–5 and ambiguities P1–P6, L1–L10, V1–V6, G1–G4).

This card uses the headings `lint_task.py` requires, and carries the eight sections of `simcal-task.md` Section E5, in E5's order, as level-4 headings under them.

## Objective

#### Goal

Deliver the content of phase 5 of §17 so that its gate holds: The corresponding negative tests pass; the gates of the first four phases are not changed

## Scope

### In Scope

#### Scope checklist

**Content (§17, verbatim)**

- [ ] Partial pooling; learned density ratios and G4-L; the inference form of V_model (marginal likelihood)

**g4sim preconditions of §17**: none of the phase-5 content uses g4sim. §7.1 (line 1471) says "`learned_closure`: unrelated to g4sim; it is still provided by the experiments that use learned density ratios (phase 5)". The g4sim evaluator keeps refusing it (`g4sim_calib_eval.learned_closure` raises "not g4sim's"). The regression rerun of the phase-3 gate uses the recorded g4sim products (see the gate designs).

**Scripts and homes (§13, §14). "Exists" means present at phase-4 head 4ef75ef7; "new" means to be created or extended in this phase.**

- [ ] **Learned density ratio** (§3.6 line 757; §6.2 lines 1094–1099; §7.1 lines 1447, 1452, 1471)
  - Exists: the candidate method `learned-density-ratio` for a non-density node with `post_hoc_correction` (`core/calibration/chain.py` line 242, schema field `post_hoc_correction` in `calibration_stage_graph.json`); the applicability rule "G4-L applies with a learned density ratio" and P0 applies (`design.py` lines 20 and 113, tested in `test_calibration_design`); the stage-D slot "G4-L" in `use.STAGES`; the `V_learn` key in the evaluator output (always `None`); and `learned_closure` stubs that raise (`toy.py` line 723, `evaluator.py` line 9).
  - New: an engine module (proposed name `core/calibration/learned.py`) with:
    - cross-fitting, where the weights of each fold come from a classifier not trained on that fold (line 1097);
    - probability calibration and the prior-ratio correction (line 1098);
    - V_learn = "the variation between repeated trainings + the square of the closure bias on held-out samples" (line 1099), split into its training-variation part and V_learn^bias (Appendix A, line 3849).
  - The engine uses only NumPy/SciPy, as §14's conventions require (line 2883 ff.). Who trains the classifier depends on ambiguity L3.
- [ ] **G4-L** (§8.2 line 1801: "difference from `learned_closure`, propagated to θ with A | same form as P0 | density-ratio estimate not trustworthy | plan"; §8.1 lines 1736 and 1755)
  - Exists: `calib_reweight.py` (weights, G4) and `core/calibration/reweight.py` (G4 since phase 2; its docstring says "G4-L phase 5").
  - New: G4-L in `reweight.py`, with the CLI subcommand in `calib_reweight.py`. §14 line 2910 makes `calib_reweight.py` the sole owner of "Weights, G4, G4-L". The P0-form bound, its θ′ points and its z follow the readings of L4 and L8.
- [ ] **The learned path through the engine** (§6.6 lines 1192, 1207–1209; §2.1 V_G; §9.2 line 2101)
  - V_learn enters V_G = V_data^unc + V_MC + V_emu + V_learn (Appendix A line 3904; `likelihood.py` line 302 names it in a docstring only), and the validation residual covariance (line 2101).
  - Toys: each replica is retrained with independent training MC and a new initialization seed (line 1192), and each toy draws N(0, V_learn^bias) once (line 1209).
  - `learned_closure(fold)` on a toy evaluator.
- [ ] **A toy fixture with a post-hoc correction node** (new; **Inferred**): the toy detector of §15.1 has no `post_hoc_correction` node (`core/calibration/data/toy_detector_design.json`). Phase 5 needs a variant with one. It should be a correction whose kernel has no analytic density, applied to stored node outputs, so that the learned path is a candidate and both P0 and G4-L apply.
- [ ] **Partial pooling** (§3.7 line 788; §11.3 line 2771; §15.3.18 line 3465)
  - Exists: the enum value `partial-pooling` in `contracts/schemas/calibration_parameter_index.json`, and the IOV rule for `piecewise-independent` (`chain.py` line 351, D87 (c)).
  - New: the pooled model, the τ̂ estimate and the contract declaration of segments and scope. The model is unspecified in Part B (ambiguities P1–P6). No §14 script owns it (P4); the proposed owner is in the work packages.
- [ ] **The inference form of V_model** (§5.4 lines 1009 and 1017; §5.2 line 896)
  - Exists: the contract rule "the inferred form may only be combined with `holdout` validation" (`contract.py` line 387, test `test_calibration_contract.test_inferred_form_without_holdout`); the kernel component with the Paciorek–Schervish cross kernel (D39 (a), A8; `likelihood.kernel_component`); principal components (`likelihood.principal_components`); and the schema enum `form: fixed | inferred`. `linear.vmodel_columns` raises `linear.incomplete` for the inferred form.
  - New:
    - f and ℓ "fitted by the marginal likelihood (integrated over ν), with a weakly informative prior added (for example f ~ Half-Normal)";
    - never by the conditional likelihood of ν (line 1017);
    - "Only as a separate version; validation must be `holdout`" (line 1009; V1–V5);
    - owned by `calib_likelihood.py` ("ν and η; V_model principal components", §14), **Inferred**.
- [ ] **Documentation**: hep-ml, "Reused; new documentation on cross-fitting and probability calibration" (§13 line 2878). New reference page(s) under `skills/hep-ml/references/`, linked from an existing non-entry page. Do not edit hep-statistics' entry reference `core-stats-guide.md`: its quick load is at 25,596 of 25,600 bytes (`tools/measure_entrypoints.py`, 2026-11-14).

**This phase's tests (§15.3; items already covered by phases 0–4 are rerun, not reimplemented)**

- [ ] §15.3.1 **G4-L** (phase 5), line 3173: "no cross-fitting". The weights are applied to events of the fold the classifier was trained on, and G4-L fails or the result is refused (structural or statistical, ambiguity L5). Positive control: the cross-fitted, calibrated ratio on the same fixture passes G4-L.
- [ ] §15.3.18 **Partial pooling** (phase 5), line 3465: "when the truth is the same in all segments, τ̂ returns to 0". Positive control (**Inferred**): segments with different truths give τ̂ > 0, and the pooled estimates shrink toward the common value. The test's deterministic or frequency form depends on ambiguity P2.
- [ ] Inference form of V_model: Part B names **no** negative test (ambiguity V6). Proposed tests, **Inferred**, each to be accepted by the author or registered as the phase's reading:
  - (a) A contract with `form: inferred` and validation other than `holdout` is rejected. This is the existing test, rerun.
  - (b) Line 1017: fitting f by the conditional likelihood of ν runs off. The engine refuses that construction (negative), and in an isolated test f̂ grows without bound under the conditional likelihood, while the marginal likelihood stays finite (counterexample).
  - (c) "Only as a separate version": the inferred V_model produces a version distinct from the fixed-form one (a different hash), never overwrites it, and carries holdout validation.
  - (d) Positive: on synthetic draws with known f and ℓ, the marginal-likelihood f̂ and ℓ̂ cover the truth within their stated error.
- [ ] §15.3.16 applicability, line 3430: a plan with only full resimulation records G4-L `not-applicable`. This is the existing test, rerun. Add (**Inferred**, from lines 1749 and 1755) that a plan with a learned density ratio makes both P0 and G4-L apply.
- [ ] §8.1 line 1736: the contract declares α and the multiple-comparison method for G4-L, and its absence is rejected when G4-L applies (**Inferred**; check whether the phase-0 contract rule already covers G4-L).
- [ ] The gates of phases 0–4 (§17): see the gate designs.

**Common checks**

- [ ] `tools/run_all_checks.py`, `tools/check_layering.py` (core may not import skills or adapters; a classifier dependency must stay NumPy/SciPy), `tools/check_wiring.py` (the hep-statistics README's script count), `tools/check_packaging.py`, `tools/measure_entrypoints.py` (quick-load budgets); `contracts/validate.py` on every artifact the phase writes; the full existing test suite.

### Out of Scope

- Anything that changes the gates of the first four phases (§17).
- SBI as a method of this workflow (pending author item 1, §19-9).
- §19-12 (an interval likelihood for non-negligible rounding) and §19-14 (sharing replicas among toys) as implementations, unless the author decides otherwise (author items 3 and 4). The research computations offered there are optional.
- ξ versions (§19-g8), unless the author decides otherwise (author item 5).
- The conditioning structure "parameterized function of the condition" (line 788; ambiguity G3).

## Repository Context

To be confirmed at the phase start on `origin/main` after phase 4 merges (base commit to fill in). As read in the phase-4 worktree at 4ef75ef7 (hep-research 0.66.1 plus phases 0–3, plus phase 4):
- `core/calibration/` holds 37 modules, about 15,000 lines. Among them: `reweight.py` (weights, Kish ESS, Pareto k, G4), `design.py` (applicability, P5), `chain.py` (candidate methods including `learned-density-ratio`), `likelihood.py` (blocks, links, V_model kernel and ensemble components, principal components), `fit.py`, `toy.py` (toy detector and evaluator), `toys_linear.py` (linear configurations), `validate.py`, `evaluator.py` (the §7.1 protocol), `contract.py`, `deps.py`, `use.py`, `propagate.py` and `contrib.py`.
- The `calib_*.py` scripts are in `skills/hep-statistics/scripts/`, with `calib_contrib.py` added in phase 4.
- The phase gate harnesses are `tests/core/calibration_phase1_gates.py`, `calibration_phase2_gates.py`, `calibration_phase3_gates.py` and `calibration_phase4_gates.py`. The phase-0 harness is the Appendix C campaign (`tests/core/calibration_exhaustive.py`, campaign `campaigns/phase0-appendix-c-2/`).
- hep-ml has `references/sbi-training.md`, `uncertainty-and-calibration.md` and `ml-analysis-weights.md`, and `assets/calibration.py` (Platt, isotonic, prior-ratio change). The training assets use PyTorch.
- The recorded g4sim products of the phase-3 gate are at `/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3` (9.5 GB, present 2026-11-14).

## Technical Approach

1. Run the phase loop of `simcal-task.md` Section E4 in the worktree `hep-research-simcal-phase-5` on branch `simcal/phase-5`, from `origin/main` after phase 4 merges.
2. Before anything else, record the author's decisions on items 1–5 of the decision sheet, and the readings of the Part B gaps P1 (the pooling model) and V6 (the inferred-form negative tests). Without them, the partial-pooling and inferred-V_model gate tests cannot be judged (E7 items 1 and 6).
3. Implement the §17 content through the scripts of §14, each check in exactly one script. Follow §14's conventions: JSON output, exit codes 0–3, the standard library plus NumPy/SciPy. Every new feature is **off by default**: a contract and plan that use none of the three features must give byte-identical outputs to the phase-4 code. This is the "default-off identity" test below.
4. Add each test of this phase before the gate run, and show that each negative test is caught.
5. No §8.7 row names phase 5 (see the §8.7 rows below). Register any phase-5 study before its run, and keep `provisional-thresholds` where a value is uncalibrated.
6. Rerun the gates of phases 0–4 at the phase-5 gate commit, as registered (gate designs).

## Deliverables

#### Deliverables

- Create the modules and scripts listed in the scope checklist that do not exist yet (proposed names: `core/calibration/learned.py`, `core/calibration/pooling.py`, `core/calibration/vmodel_infer.py`; the G4-L function in `reweight.py`; new subcommands in `calib_reweight.py`, `calib_likelihood.py` and `calib_fit.py`), with their tests (new modules `tests/core/test_calibration_learned.py`, `test_calibration_pooling.py`, `test_calibration_vmodel_infer.py`).
- Add a toy fixture with a post-hoc correction node (new file under `core/calibration/data/` or `tests/core/`, **Inferred**).
- Add the hep-ml documentation on cross-fitting and probability calibration (new page under `skills/hep-ml/references/`).
- Add the gate harness `tests/core/calibration_phase5_gates.py` (new): the phase-5 negatives, the static check of the earlier gates, the dispatch and merge of the earlier gates' reruns, and the default-off identity check.
- Add the gate record `docs/dev/simulator-calibration/simcal-gates/phase-5.md`, from the gate-record template of the task package.
- Update the status file and the registry (`simcal-status.json`, `simcal-task-registry.json`) in `docs/dev/simulator-calibration/`.
- Schema changes, if a reading requires them (segments and τ prior for pooling, the inferred V_model version, learned-ratio plan fields): in `contracts/schemas/`, with `contracts/validate.py` coverage. These are proposed only after the readings P1, P5, V1 and L2 are fixed.

## Acceptance Criteria

#### Decisions this phase depends on

Needs the author (each must be approved in `simcal-approvals.md` before the phase starts; Section E7, item 1). All are approved by record A25 (2026-11-14, the user as the author's proxy: "Adopt all, start phase 5"), which states each reading:

- §19-9, second half (line 3713): a learned density ratio is a classifier-estimated ratio for one post-hoc correction node, used only to reweight stored MC events (it may depend on θ; cross-fitting, probability calibration, the prior-ratio correction, P0 and G4-L apply); SBI (learning the likelihood or posterior of θ from observables) is not a method of this workflow and is rejected; approved, record A25
- §19-15 (line 3731): only the scale of V_learn^bias is tested, not its direction; accepted as a documented limitation; approved, record A25
- §19-12 (line 3722): observables whose rounding is not negligible stay rejected; approved, record A25
- §19-14 (line 3730): sharing replicas among toys stays forbidden; approved, record A25
- §19-g8 (line 3745): no versions for ξ (confirmed after A21); approved, record A25
- Gap P1 (lines 788, 2771, 3465; E7 item 6), partial pooling: per-segment θ_s ~ N(θ̄, τ²) per parameter in link space; τ ≥ 0 estimated by the restricted (REML) marginal likelihood; the pooled θ_s and τ̂ enter σ_tot through the joint fit. Part B's test "τ̂ returns to 0" (line 3465, P2) reads: with the same truth in all segments, τ̂ = 0 in at least half of the replicas, and the one-sided 95% upper limit on τ covers 0 in at least 95%; approved, record A25
- Gap V6 (§15.3; E7 item 6): the negative tests of the inferred form of V_model are this card's tests (a)–(d), including the refusal of the conditional-likelihood fit of f (f·ν non-identifiable, Part B line 1017); approved, record A25

The remaining ambiguities are listed in the decision sheet (`/ceph/work/AMS/hsinyichou/hep-research-simcal-private/phase-5-prep/decision-sheet-phase-5.md`, Section 3); each is read by the work package that meets it and recorded in the execution log, or stopped and reported if it changes a gate.

Implemented as Part B writes them, the author confirming later (computation results; D19, D25 and the open §14.1 items, by front matter line 38), or settled by plugin source:

- none specific to phase 5.

Accepted or decided items that this phase implements (their text in Part B is normative):

- none specific to phase 5. D39 (a), from A8 (the Paciorek–Schervish cross kernel), already implemented, is the kernel whose f and ℓ the inferred form fits.

#### Thresholds and test designs

**Gate (§17, verbatim)**: The corresponding negative tests pass; the gates of the first four phases are not changed

**§8.7 rows of this phase (verbatim)**:

- none (no row's "Implementation phase of calibration" column names phase 5; §8.7 line 1994: "Implementation phases 1–3 will calibrate them one by one").

**§8.7 rows that phase 5 uses (verbatim; Inferred which ones apply; already calibrated in the phase named, not recalibrated here unless registered below)**:

- Line 2004: `| Bonferroni z of P0, P6 | α = 0.01 | estimate the false-alarm rate with a correct kernel and surrogate model | 1, 3 |`. G4-L is "same form as P0" (line 1801); whether G4-L inherits this calibration is ambiguity L8.
- Line 2006: `| f in the ESS threshold | 0.1 | check the behavior of G7, G8 at f = 0.1 | 2 (G7, G8 delivered in phase 2) |`. The feasibility of a learned density ratio is "Same as above" (the P5 ESS threshold) "and subject to the G4-L check" (line 757).
- Line 2015: `| replica-difference construction of toys (§6.6) | default construction | note 4 | 2 |`, with note 4's surrogate item (line 2070): "- **Surrogate model**: when a surrogate model is used, also test with a toy surrogate model of known interpolation error." No learned-path analogue is named (ambiguity L9).

Rule: every value above is registered in this card before the run that it judges; it may be tightened, never loosened.

**Gate designs (proposed; registered here before the gate run)**:

1. **`negatives`: the corresponding negative tests pass.** Every test listed under "This phase's tests" shows its expected rejection or decision, each with a positive control that passes. The tests run from one clean commit through the harness `tests/core/calibration_phase5_gates.py` (a units item, as in phases 3 and 4). Any skip, failure or error fails. Registered as lists of test identifiers:
   - `G4L` (§15.3.1 and §15.3.16);
   - `POOLING` (§15.3.18);
   - `VMODEL_INFERRED` (the tests (a)–(d) above, as accepted per V6).
2. **`prior_gates_static`: the gate definitions of phases 0–4 are not changed.**
   - `git diff --name-only <phase-5 base> <gate commit>` lists none of these files:
     - `tests/core/calibration_phase{1,2,3,4}_gates.py`;
     - `tests/core/calibration_exhaustive.py`;
     - `docs/dev/simulator-calibration/simcal-tasks/phase-{0,1,2,3,4}.md`;
     - `docs/dev/simulator-calibration/simcal-gates/phase-{0,1,2,3,4}.md`.
   - The phase-0–4 entries of `simcal-task-registry.json` are byte-identical to those at the phase-5 base. The harness compares the JSON entries.
   - A phase-5 change that would need to edit one of these files is a STOP (E7 item 6), not a fix.
3. **`prior_gates_rerun`: the gates of phases 0–4 still pass at the phase-5 code.** Each earlier gate is rerun as its card registered it (items, rules, sizes and seeds verbatim), from a clean worktree at the phase-5 gate commit. Each earlier item must pass by its own registered rule. Recorded run costs come from the cards and gate records:
   - Phase 0: the Appendix C campaign (array of 69 jobs, recorded 0.44 core-hours, `edr1-al9_short_serial`), plus the named-case unit modules.
   - Phase 1: gate 1 (the unit tests listed in its card) and gate 2, `calibration_phase1_gates.py --gate agreement` (minutes).
   - Phase 2: gate 1 (`--gate1-toy-task`, an array of 33 tasks, recorded 22.8–23.9 core-hours), gate 2 (`--gate segmented`, recorded 2440 s, run as one Slurm task) and gate 3 (P8/G9 negatives).
   - Phase 3: gate part E's items (tasks 0–123 and 27164–27173, recorded estimate ≈ 20 core-hours), merged with `SIMCAL_G4_PRODUCTS` set to the recorded products. No new Geant4 runs.
   - Phase 4: `calibration_phase4_gates.py --run` (about 1 minute, login host).
   - Numerical differences from the recorded evidence are reported, not judged. The verdicts are judged.
4. **`default_off_identity`: the extensions change nothing when unused** (supporting gate 3; **Inferred**, cheap). On a fixed set of phase-0–4 fixtures and contracts, recorded as golden JSON from the phase-5 base before any phase-5 commit, the outputs of the engine and of `calib_*.py` at the gate commit are byte-identical. The fixed set covers the contract check, design and P5, the fit with G1–G7, G8 at screening level, validation, propagation and contrib. The comparison excludes fields that record commit, time and environment.

The gate passes when items 1–4 pass and the worktree is clean. Phase-5 results that use G4-L carry `provisional-thresholds` unless L8 is settled with a calibration registered below.

**Studies to register before their runs (proposed; each conditional on the reading named)**:

- (S1, if L8 is read as "G4-L needs its own false-alarm calibration") The G4-L false-alarm rate with a correct, cross-fitted and calibrated learned ratio on the post-hoc fixture: 1000 repetitions at 40,000 events, the P0 rule form (|Δθ_i| ≤ 0.1σ_tot,i^design + z·σ, two-sided Bonferroni, α = 0.01). Acceptance in the form registered for P0 in phase 1: ≤ 16 false alarms of 1000.
- (S2, from P2) A partial-pooling frequency report: under equal truth, the fraction of τ̂ = 0 and the coverage of the pooled θ over 1000 repetitions on a segmented linear toy. Reported, not judged, unless the author makes it the test.
- (S3, from V6 (d)) An inferred-V_model recovery study: f̂ and ℓ̂ pulls over 1000 synthetic draws. Pull mean |μ| ≤ 0.1 and sd within [0.9, 1.1] are proposed (**Inferred**, borrowed from §8.7 note 4's form, line 2068).
- (S4, optional, L9) The T_v size on the learned path (replicas retrained, N(0, V_learn^bias)): ≥ 10⁴ repetitions, within α ± 25% as in §8.7 note 4 (line 2063).

**Compute estimate (Slurm core-hours; Inferred from the recorded times above unless stated)**:

| Run | Basis | Estimate |
| --- | --- | --- |
| Phase 0–4 gate reruns (gate 3) | recorded 0.44 + 23.9 + 0.7 + ≈ 20 + login | **≈ 45 core-hours** (one day of queue at the recorded concurrency) |
| Default-off identity, unit tests, commit gate | login (commit gate ≈ 3.5 min); full `run_all_checks` recorded 75 min | < 2 core-hours |
| S1 G4-L false alarms | phase-1 P0 calibration recorded 2.9–3.2 core-hours per 1000 repetitions at 40k events. Learned path adds 5 cross-fit trainings plus about 10 repeated trainings per repetition: 6–10 core-hours with NumPy logistic regression, up to about 90 with a SciPy-optimized small network | **6–90 core-hours**; size with a pilot of 10 repetitions first |
| S2 pooling frequency report | linear toy, closed-form or 1-D optimization | < 1 core-hour |
| S3 inferred-V_model recovery | 2–4 hyperparameters, 20–50 observables per draw | < 1 core-hour |
| S4 learned-path T_v size (optional) | 10⁴ repetitions × (2 retrainings + one toy fit) | 15–60 core-hours |
| §19-12, §19-14 research (optional, decision sheet) | linear toy | 5–20 and 20–60 core-hours |
| **Total, required items** | gate reruns + checks + S2 + S3 | **≈ 50 core-hours** |
| **Total with S1** | | **≈ 55–140 core-hours** |

**Gate run and studies, registered 2026-11-14 before any run (approvals A25–A27; `synthetic`; results using G4-L, the T2 margin or the pooling thresholds carry `provisional-thresholds`)**:
- **Gate items 1, 2, 4** (`tests/core/calibration_phase5_gates.py --run --out campaigns/p5-gates/gate.json --rerun-merged campaigns/p5-gates/rerun.json`, login host, the interpreter of the goldens: conda env `ml`, Python 3.13.2, NumPy 2.2.2, SciPy 1.16.1): (1) `negatives` — every test in `G4L` (12), `POOLING` (15) and `VMODEL_INFERRED` (7) passes; (2) `prior_gates_static` — no protected phase-0..4 file changed since c7e5a610 and the phase-0..4 registry entries identical; (4) `default_off_identity` — the 50 golden cases (captured at 586e3451) byte-identical.
- **Gate item 3, `prior_gates_rerun`**: `calibration_phase5_gates.py --dispatch campaigns/p5-gates/rerun --commit <registering commit> --worktree tmp/wt-p5-gates` writes the Slurm scripts that rerun every phase-0..4 gate exactly as its card registered it (phase 0 Appendix C campaign, 69 items; phase 0 named cases and fixtures, phase 1 gates 1 and 2, phase 2 gates 2 and 3 (`misc`, 6 tasks); phase 2 gate 1 (33 tasks); phase 3 gate part E (tasks 0–123 and 27164–27173, `SIMCAL_G4_PRODUCTS` = the recorded p3-g4 products); phase 4 on the login host), each from the clean worktree at the registering commit; `--merge-rerun` judges each earlier item by its own registered rule; numeric differences from the recorded evidence are reported, not judged. ≈ 45 core-hours.
- **S1, G4-L false alarms** (WP-R; L8): a correct, cross-fitted (F = 5), Platt-calibrated learned ratio (R = 5) on `core/calibration/data/toy_posthoc.json` at 40,000 events, 1000 repetitions (20 tasks × 50), seeds SeedSequence([20261514 + r, j]); P0 rule form |Δθ_i| ≤ 0.1σ_tot,i + z·σ, z two-sided Bonferroni, α = 0.01. Rule: passes with ≤ 16 false alarms of 1000; an erroring repetition makes it incomplete. ≈ 4 core-hours. Command `tests/core/calibration_phase5_g4l.py --task K --out DIR`, `--merge`.
- **S2, partial-pooling frequency report** (WP-Q; P2): equal truth (0.5, −0.3), 4 segments, `linear_config(n=8, d=2, seed=3)`, 1000 repetitions (10 tasks × 100), seeds 20261405 + 100000 + r; reports the τ̂ = 0 fraction, the cover fraction and the ±σ_tot coverage of θ_s, θ̄ and the common parameter. Reported, not judged. ≈ 0.1 core-hours. `tests/core/calibration_phase5_pooling_s2.py`.
- **S3, inferred-V_model recovery** (WP-S, WP-S2; V6 (d)): configurations "one" and "two" as WP-S proposed (1000 draws each, 20 tasks, seeds `default_rng([20261405 + r, j])`), pulls from the marginal posterior quantiles (WP-S2). Rule per hyperparameter: |mean pull| ≤ 0.1 and sd within [0.9, 1.1] (Inferred, after §8.7 note 4); an undefined pull or missing draw makes the configuration incomplete. ≈ 3 core-hours. `tests/core/calibration_phase5_vmodel_s3.py`. Registered as is after A26 (2); reported as it comes.
- **S4, learned-path validation size** (WP-R2; L9; A27 (2)): post-hoc fixture, truth strength 0.15, exposure 8000, MC 40,000, degree 4, F = 5, R = 5; calibration y_mean, y_width; holdout y_hi, y_sq; N_REF = 1000 reference toys (20 tasks) and 2000 actual repetitions (40 tasks) — re-registered by A28 before any task ran (first registered as 2000 and 10⁴, ≈ 100 core-hours; array 7653209 cancelled while pending); V_learn frozen at θ_ref in the ln det diagnostic (A27 (1)). Rule (§8.7 note 4): the rejection rate at α = 0.05 within α ± 25%; non-converged repetitions reported. ≈ 20 core-hours. `tests/core/calibration_phase5_tv.py`.
- **S4 pilot** (A30/A31; registered before it runs), report-only, not judged; code at 3820f9dd (merged into the phase branch as a7306cd1): the S4 configuration above plus V_learn^bias by the θ0 control variate minus its MC-noise covariance, clipped (A29), and each fold's log ratio clipped to its training range (A31); 200 repetitions + 200 reference toys in 8 tasks of 50 (`calibration_phase5_tv.py --pilot --task K`, merge `--pilot --merge DIR --out FILE`); seeds SeedSequence([20261592, j, i, k]) (disjoint from 20261540, 20261590, 20261591, 20261593). Sound, fixed before the run (`SOUND` in the driver): non-converged learned reference toys ≤ 1%; learned reference q95 in [4.8, 7.2] (χ²₂ 5.99 ± 20%); non-converged repetitions ≤ 5%; actual T median in [1.11, 1.66] (1.386 ± 20%). Reported only; S4 is decided by its registration. ≈ 3.1 core-hours; 6 GB per task. Outputs `campaigns/p5-studies/tv-pilot/`.
- **S4 second registration** (A29–A31), runs only if the pilot is sound: the configuration of the pilot with N_REF = 1000 reference toys (20 tasks of 50) and 2000 actual repetitions (40 tasks of 50); seeds SeedSequence([20261590, j, i, k]); rule (§8.7 note 4): the rejection rate at α = 0.05 within α ± 25%; non-converged repetitions reported. ≈ 13 core-hours; 6 GB per task. The first registration's result (0.010) stands.
- **S3**: no second registration (A30): the configuration "two" failure stands as recorded, diagnosed as prior shrinkage of a weakly identified component.
- Submission: from the clean worktree `tmp/wt-p5-gates` at the registering commit; Slurm `edr1-al9_short_serial`, account `ams`, 1 core, the node interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13`; outputs under `campaigns/p5-gates/` and `campaigns/p5-studies/`; auto-submit, user 2026-11-12. The gate passes when items 1–4 pass and the worktree is clean; the studies are recorded in the gate record (S1 decides whether G4-L results keep `provisional-thresholds`).

**Work packages (approved with A25, "start phase 5"; as subagents, Part A E7; each in its own worktree from the registered card commit, as in phase 4)**:

| WP | Scope | Files (create or modify) | Tests | Depends on |
| --- | --- | --- | --- | --- |
| **WP-Q** partial pooling | the pooled model, the τ̂ estimate, the contract declaration of segments and scope, the hook into the fit | new `core/calibration/pooling.py`; a narrow hook in `fit.py` (a penalty or wrapper problem, as `fit.view` does), not a rewrite of `likelihood.py`; `calib_fit.py` subcommand (owner per P4, proposed `calib_fit.py`); schema field for segments and τ prior (`calibration_parameter_index.json` `scope`, or the contract) | new `test_calibration_pooling.py`: §15.3.18 τ̂ = 0 at equal truth, the positive control, the contract rejections for missing segments; S2 driver | **the author's reading of P1 (and P2, P5, P6)**; nothing else |
| **WP-R** learned density ratio and G4-L | the NumPy/SciPy classifier path (cross-fitting, calibration, prior-ratio correction), V_learn and V_learn^bias, `learned_closure` on the toy evaluator, the post-hoc correction fixture, G4-L in `reweight.py` and `calib_reweight.py`, P0 on the learned path | new `core/calibration/learned.py`; `reweight.py` (G4-L); `toy.py` (`learned_closure`, fixture loader); new fixture JSON; `calib_reweight.py`; `design.py` only if L6 needs it | new `test_calibration_learned.py`: §15.3.1 G4-L "no cross-fitting" negative and positive; §15.3.16 learned-plan applicability; α declaration; S1 driver (if registered) | **author item 1 (§19-9)**; readings L2–L7; nothing else |
| **WP-R2** learned path through the engine (second wave) | V_learn in V_G and in the validation residual covariance; toys retrain replicas and draw N(0, V_learn^bias) | `likelihood.py` (V_G assembly), `validate.py` (line-2101 covariance), the toy-replica code of `toy_problem.py` or `fit.py` | additions to `test_calibration_likelihood.py` and `test_calibration_validate.py`; S4 driver (optional) | WP-R merged (its V_learn interface); author item 2 (§19-15) for the documented limitation |
| **WP-S** inferred V_model | the marginal likelihood over ν with a Half-Normal prior on f (prior on ℓ per V3), the separate version (V1), holdout only, the refusal of the conditional-likelihood fit | new `core/calibration/vmodel_infer.py` (calls `likelihood.kernel_component` and `principal_components`, does not edit them); `linear.vmodel_columns` (replace the `linear.incomplete` refusal for `inferred`); `calib_likelihood.py` subcommand; schema for the version link if V1 needs it | new `test_calibration_vmodel_infer.py`: tests (a)–(d); S3 driver | **readings V1–V6 (V6 needs the author or a registered reading)**; nothing else |
| **WP-T** hep-ml documentation | §13: "new documentation on cross-fitting and probability calibration" for learned density ratios, with the boundary to SBI per §19-9; links from `sbi-training.md` and `ml-analysis-weights.md` (non-entry pages); citations only through hep-citations | new page under `skills/hep-ml/references/`; small link edits | `tools/check_wiring.py`, `tools/measure_entrypoints.py` (hep-ml quick load 16,300 of 25,600 bytes); the routing tests | author item 1; can draft in parallel with WP-R and align at merge |
| **WP-U** phase-5 gate harness | gate items 1–4: the units lists, the static diff and registry check, the dispatch and merge of the phase-0–4 reruns (driving the existing harnesses unchanged), the golden-JSON capture at the phase-5 base and the identity comparison | new `tests/core/calibration_phase5_gates.py`; golden files under `tests/core/data/` or `campaigns/p5-gates/` | its own unit test (`test_calibration_phase5_gates.py`) on a dry run | none for the skeleton; the units lists are filled after WP-Q, WP-R and WP-S merge. **The golden capture must run at the phase-5 base before any WP merges** |
| Main session | the card, the decision records, the registrations, the merges (shared hooks: `fit.py`, `likelihood.py`, schemas, the hep-statistics README script count), the gate run, the gate record, the independent review | — | — | — |

**Parallelism:**
- WP-Q, WP-R, WP-S, WP-T and WP-U can run in parallel as subagents in wave 1. Each creates its own new module or page. The shared-file touch points are listed per WP, and the main session merges them.
- WP-R2 is wave 2, after WP-R merges.
- The phase-0–4 rerun (gate 3) and S1 run after all WPs merge, at one registered commit.
- If the author's readings are not ready at the phase start, WP-R, WP-T and WP-U can start while WP-Q and WP-S wait.

## Validation

#### Environment

- Python with the standard library plus NumPy/SciPy (§14). As recorded in phases 1–4: Python 3.13.2 (conda env `ml`, NumPy 2.2.2, SciPy 1.16.1) on the login host, and the batch interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13`.
- Batch work runs on NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, through `core/partition/` and `batch_campaign.py` (§14.1), under the submission rules of `simcal-task.md` Section E7 item 3. Arrays are submitted from a clean worktree at the registering commit (the user's standing permission for simcal arrays: register first, report each).
- hep-research at the post-phase-4 `main`. g4sim is not used by the phase-5 content. The phase-3 gate rerun reads the recorded products only.

#### Risks and stop points

- The partial-pooling model is not specified in Part B (P1). Its gate test (line 3465) cannot be judged until the model is fixed. This is a STOP candidate (E7 item 6).
- Part B names no negative test for the inferred V_model (V6). The gate's "corresponding negative tests" are undefined for it until the author accepts a set. This is a STOP candidate.
- §19-9 decides what WP-R may build. If it is unanswered, WP-R stops at the cross-fitted per-θ′ classifier (decision-sheet alternative (b)), or waits.
- Rerunning the phase-2 and phase-3 gates at new code could fail for reasons unrelated to phase 5, for example a seed-dependent edge case or an environment change. A failure is a STOP (E7 item 4), never a redesign. The default-off identity test (item 4) is meant to localize the cause.
- The phase-3 rerun depends on the recorded g4sim products at `/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3` (9.5 GB). If they are removed, the phase-3 Geant4 items cannot be rerun without new Geant4 production.
- Classifier training inside the NumPy/SciPy rule (§14) limits the model class. A PyTorch classifier can only live in an adapter or in hep-ml assets (L3), and `check_layering.py` enforces this.
- The hep-statistics entry quick load has 4 bytes of headroom. Phase-5 documentation goes to hep-ml or to non-entry references.
- No §8.7 row exists for phase 5. G4-L results carry `provisional-thresholds` unless S1 is registered and passes (L8).

#### Execution log

- 2026-11-14 phase 5 started on the user's word ("Adopt all, start phase 5"): worktree `hep-research-simcal-phase-5`, branch `simcal/phase-5` from `origin/main` c7e5a610 (hep-research 0.67.0, phases 0–4 merged); A25 recorded; card refreshed from the draft prepared during phase 4 (`phase-5-prep/`). The golden outputs of gate item 4 are captured at c7e5a610 before any work package merges.
- 2026-11-14 wave 1 (approved with A25, "start phase 5"): WP-Q, WP-R, WP-S, WP-T, WP-U as subagents from 586e3451, brief `tmp/p5-agent-brief.md`; merged into `simcal/phase-5` through the commit gate: WP-T 2cb204d0 (24a2150d; hep-ml page `learned-density-ratio-reweighting.md`, six citations looked up on INSPIRE-HEP/arXiv and read at abstract level; changelog line added at the merge), WP-S 423f3671 (c7bf1cb4), WP-U 10b1c24a (b5fd8a5c; goldens captured at 586e3451), WP-R 64962ce0 (e6f12b16; OWNERS/README conflicts kept both), WP-Q df6d5364 (327b68c1, e3e602b5; same). Wave 2 WP-R2 started from df6d5364.
- 2026-11-14 readings recorded from the reports (each a computational detail Part B and A25 leave open): WP-Q — random effects non-centred in link space as a wrapper Problem with N(0,1) pseudo-rows (no fit.py/likelihood.py change); REML on the model linearized at the joint point with ν, η, φ_P marginalized, iterated to a stable τ̂; τ̂ plugged in without a Kackar–Harville correction; P2 "covers 0" as q(0) ≤ χ²₁(0.90) = 2.706 (boundary coverage 95%); symbol `tau_pool`; owner `calib_fit.py pool`; P6 (the grade and use of a pooled result) NOT decided: output flagged `partial-pooling` without a grade; gates P3, G2, G5, G6, G8 and §10.4 not wired for pooled fits; Gaussian blocks only. WP-R — L2 logistic regression on degree-4 monomials × θ terms, Platt, F = 5, R = 5; L4 G4-L at P0's θ′ points; L5 structural (index sets) and statistical (held-out closure); L6 stage-D G4 not applied to learned weights (P5's ESS and G4-L); L8 α = 0.01 inherited, `provisional-thresholds` until S1 passes; G4-L α in `acceptance.gates["G4-L"]`. WP-S — V1 a separate `vmodel-version` record linked by hash; V2 ν integrated exactly, η/φ_P with N(0,1), θ flat (REML); V3 `f_scale` and `length_bounds` required; V4 empirical Bayes (f̂, ℓ̂ errors reported, not propagated); V5 squared-exponential components only; S3 pilot (40 draws): ℓ pulls biased (+0.5 to +0.8) and wide (sd 1.3–1.7) — S3 as proposed will probably fail on ℓ; to be registered as is and reported.
- 2026-11-14 A26 (the user: fix the two open points): the grade and gates of pooled results (WP-Q2) and the S3 ℓ pulls fixed before registration (WP-S2), both started from 1a0a07a8. WP-R2 merged as cb64513f (5803224b): V_learn in V_G (`ToyProblem.reference`, `EvaluatorProblem.reference`; link space at θ_ref) and in the validation C_r (`validate.holdout_pieces`), toys retrain replicas (discarded after each toy, A25 (4)) and draw N(0, V_learn^bias) once at the generation point, the toy truth applies the learned weights (a defect: toy data had been drawn at θ0), S4 driver; readings: V_learn queried at θ_ref (not per evaluation), validation side with its own evaluator and independent bias draws, the rank-one bias drawn by eigen-decomposition. Findings: V_learn^bias > 0 at θ0 (the closure's own MC noise; conservative); callers set the generation point to θ̂ (Part B line 1194); EvaluatorProblem toys draw no bias (no split, no replicas); V_emu not in the validation V_vv (pre-existing). A27 (the user): V_learn frozen at θ_ref in the ln det diagnostic (implemented with a test); S4 to be run.
- 2026-11-14 WP-Q2 merged as a19e1990 (f32d3ce8; A26 (1)): pooled results graded by Appendix C (`pooling.grade`, `calib_fit.py pool --grade`), `partial-pooling` informational; one joint V test over all segments' held-out units (`pooling.holdout_evidence`, through `validate.holdout_evidence` unchanged); P2 counts only real rows (A26's "G2 counting only real observation rows" read as P2's degrees of freedom, and G2 excludes the z variables at their bounds; both implemented); P3 at τ_pool = 0 and G5 on the fixed effects (z profiled); G6 and G8 on joint toys / segment-level pseudo-data; harness POOLING list extended. Not done: §10.4 propagation of pooled results; `calib_identify.py`/`calib_closure.py` subcommands for pooled P3, G5, G8 (engine functions only).
- 2026-11-14 WP-S2 merged (ed45f709; A26 (2)): diagnosis — the Hessian and pull definition are correct; the width came from the Laplace interval where ℓ is weakly determined (skewed f–ℓ ridge); the bias from the Half-Normal prior taken as a density in log f (a −log f Jacobian pushing f, and ℓ along the ridge) plus the small-sample skew of the ℓ likelihood. Fix (a changed reading of WP-S's V3, not of an author item: Part B line 1009 gives Half-Normal "for example"): the Jeffreys measure of the restricted likelihood times a Half-Normal(f) weight within the declared bounds; estimates are marginal posterior medians with nested-Laplace quantile intervals; the S3 pull uses the quantile error toward the truth. The S3 rule, configurations, seeds and task table are unchanged. Fresh pilot (new seeds 700000+): "one" f −0.02/1.03, ℓ +0.06/1.07; "two" f0 +0.14/1.07, ℓ0 −0.07/1.05, f1 +0.17/0.91, ℓ1 −0.05/0.87 (mean/sd) — "two" component 1 at risk of the sd ≥ 0.9 bound and f1's mean borderline at 1000 draws. S3 cost now ≈ 3 core-hours.
- 2026-11-14 A29 work packages. WP-S3 (no commit): no defect in S3 — the engine's quantiles agree with a 4-D Metropolis run on 30 recorded draws to ≤ 0.03 in log; the pull definition (three definitions give f1 mean +0.18 to +0.23), the cross Fisher term (log det 10.447 vs 10.457 block-diagonal) and the Half-Normal scale (it pulls f1 down) are ruled out; the cause is the Jeffreys measure rising with f1 (slope +1.05 per log f at the truth) on a weakly identified component (posterior sd of log f1 0.50 = its Fisher sd; sampling sd of the median 0.38; response slope 0.76): prior shrinkage, conservative (f1 68%/95% coverage 0.766/0.970; ℓ1 0.779/0.973); a truth scan (seeds 800000+, configuration index 99) shows the bias changing sign across the prior peak (f1 = 0.02: +0.06; 0.04: −0.11; 0.08: −0.31, under-covering). Finding: the S3 draws build δ with `np.linalg.eigh`, whose eigenvector signs depend on the LAPACK build (login NumPy 2.2.2 ≠ node 2.4.6). WP-R3 (2e83939a): V_learn^bias was mostly the closure's own MC noise (noise covariance 80–100% of b bᵀ on the validation rows; true δ² [1.7e-5, 1.2e-4] against median b bᵀ [1.6e-4, 1.0e-4]); fix: b = closure difference at θ minus the same at θ0 (common random numbers, exactly 0 at θ0), V_bias = clip_psd(b bᵀ − Cov_noise(b)); V_learn_train double counting not material; V_MC over-covers on the learned path (≈ 0.45–0.8 of E[eeᵀ]; not changed); structural causes reported: (a) heavy-tailed classifier quality (≈ 1 in 30 fits with V_MC 17–24× the median) hits reference toys judged against the nominal C_r, (b) a non-converged reference toy counts as T ≥ T_obs (§7.3), lowering the size by up to X/N_REF (0.016 at A28) against a band half-width 0.0125; the judge's docstring aligned with the code (rate over converged repetitions). The user: A30 — S4: clamp the classifier features to the training range, then a registered 200 + 200 Slurm pilot before the full second registration; S3: accepted and recorded as prior shrinkage, failed on "two" as registered, no second registration (Cholesky instead of eigh at any later registration).
- 2026-11-14 GATE PASSED at 429caf0f (`campaigns/p5-gates/gate.json`, SHA-256 f793576e…; clean worktree `tmp/wt-p5-gates`): `negatives` (G4L 12, POOLING 15, VMODEL_INFERRED 7), `prior_gates_static`, `default_off_identity` (50 cases byte-identical), `prior_gates_rerun` (all 10 phase-0..4 items pass by their own rules: p0 Appendix C, p0 named cases, p0 fixtures, p1 gates 1 and 2, p2 gates 1, 2 and 3, p3 gate part E, p4 gate; `rerun/rerun-merged.json`). Phase 2 gate 2 needs ≈ 35 GB: it ran out of memory at 6 GB and 12 GB, and passed at 40 GB (job 7653740); a run at the phase-5 base c7e5a610 peaked at the same 35.0 GB (job 7653741), so not a regression. Studies: S1 PASSED (9 of 1000 false alarms, ≤ 16); S2 reported (τ̂ = 0 in 0.600, cover 0.975; ±σ_tot coverage θ_s 0.697, θ̄ 0.737, common 0.678 against 0.683); S3 FAILED on configuration "two" (f1 mean +0.216, sd 0.840; ℓ1 sd 0.878; "one" and the other hyperparameters pass); S4 (A28 size) FAILED (rejection rate 0.010; without V_learn in C_r 0.021; no-learned-toys control 0.005; 91 of 2000 non-converged); S4's 20 reference tasks ran out of memory at 2 GB and were resubmitted at 6 GB (job 7653663). The user: A29 (fix the causes, second registrations).
- 2026-11-14 gate run and studies submitted from `tmp/wt-p5-gates` at 429caf0f (auto-submit, user 2026-11-12): reruns 7653200 (phase 0 campaign), 7653201 (misc), 7653202 (phase 2 gate 1), 7653203–7653205 (phase 3 part E); phase 4 rerun on the login host: passed; studies S1 7653206, S2 7653207, S3 7653208, S4 7653209. The partition was full (3840/3840); the user asked to speed up the large jobs: S4 lowered in priority, then cancelled while pending and re-registered smaller (A28).
- 2026-11-14 harness lists filled (`G4L` 12, `POOLING` 7, `VMODEL_INFERRED` 7 entries); dry run after wave 1: `negatives` passed, `prior_gates_static` passed, `default_off_identity` passed (50 cases byte-identical), `prior_gates_rerun` not run.

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above (decision sheet items 1–5), and the readings of P1 and V6.
- Which script owns partial pooling (P4): `calib_fit.py` is proposed.

## References

- Part B §3.6 (line 757), §3.7 (line 788), §5.2 (line 896), §5.4 (lines 1001–1043), §6.2 (lines 1094–1099), §6.6 (lines 1185–1215), §7.1 (lines 1437–1471), §8.1 (lines 1736, 1749, 1755), §8.2 (line 1801, note 1 lines 1812–1815), §8.7 (lines 1992–2083), §11.3 (line 2771), §13 (line 2878), §14 (line 2910), §15.3.1 (line 3173), §15.3.16 (line 3430), §15.3.18 (line 3465), §17 (line 3583), §19 (lines 3713, 3722, 3730, 3731, 3745).
- `simcal-decision-index.md`; `simcal-approvals.md` (A12, A21); `decision-sheet.md` (lines 360–389); `simcal-task.md` Part A; the prep decision sheet (decision-sheet-phase-5.md, outside the repository; its outcome is copied into this card at the phase start).
- `simcal-tasks/phase-4.md` (the model of a refreshed card); `skills/hep-computing/assets/task-template.md`.

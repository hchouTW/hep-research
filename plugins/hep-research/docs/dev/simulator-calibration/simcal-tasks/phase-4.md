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

**Gate run (registered 2026-11-14 before the run; harness `tests/core/calibration_phase4_gates.py`; the user's decisions A22, A23; `synthetic` where fixtures are used)**: `python -I tests/core/calibration_phase4_gates.py --run --out campaigns/p4-gates/gate.json` from a clean worktree at the registering commit, on the login host (about 1 minute; no Slurm). Items and rules: (1) `contrib_negatives` — the §15.3.18 tests listed in `CONTRIB` (7 negatives, 7 positives incl. the g4sim `effects_off` hook): every listed test passes; any skip, failure or error fails. (2) `g4sim_binding` — every case of §15.3.19 and the A21 cases, each mapped to its tests in `CASES` (18 cases: external source, five identity items, physics-list confirmation, moments-only, kill_policy support, G8 Philox-only fit MC, P7 shared events, known photon count, PDE split, map varies with θ and fixed-map linear construction, shared-seed primaries, digi-job rejections, source_of_facts on exports, build_hash redo, g4sim output as a release, the T2 carry-over, upstream invalidation, discrete run-card fields): every case's tests pass; the case "scintillation log_density switched to the normal density → P0 fails" is run and recorded, not judged (A23). (3) `generic_layer` — `test_calibration_specialization` (the eight examples through the unchanged checker, P4, candidate methods and scripts; the page items) passes, and `git diff --name-only e661b3fd^ e661b3fd` (the WP-P commit that added the specialization documents) lists no file under `core/`, `contracts/schemas/` or `skills/hep-statistics/scripts/`. The gate passes when all three pass and the worktree is clean. No §8.7 threshold is judged (the T2 margin of A21 stays `provisional-thresholds`).

**Gate run, second registration (registered 2026-11-14 before the run, after the review, A24 and the review fixes; the first gate run at 4ef75ef7 stands as recorded)**: the first registration's command and items verbatim, except: (2) `g4sim_binding` has 19 cases — the case "scintillation log_density switched to the normal density → P0 fails" is judged (A24; `test_calibration_evaluator_problem.PoissonIntervalLightYield`), nothing is recorded-not-judged; the T2 cases test the θ-space rule with the power condition and the result-bound basis (A24); (3) `generic_layer`: every non-merge commit since 307a364d that touches `skills/hep-detector/references/simulation-calibration/` or `skills/hep-detector/assets/simulation-calibration/` touches no file under `core/`, `contracts/schemas/` or `skills/hep-statistics/scripts/` (review F2; the `chain.binding_row` fix 685683ab touches no specialization file and is disclosed in the gate record). Output `campaigns/p4-gates/gate-2.json`.

**Gate run, third registration (registered 2026-11-14 before the run, after gate run 2 failed on a harness defect)**: the second registration verbatim; the only change is the harness's git pathspec for the specialization paths (`:(top)`, from the repository root). Output `campaigns/p4-gates/gate-3.json`.

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
- 2026-11-13 work packages approved by the user ("4 agents in parallel"): WP-M, WP-N, WP-O, WP-P as subagents, each in its own worktree from 6e4a1855 (registered card), brief `tmp/p4-agent-brief.md`; merged into `simcal/phase-4` with the commit gate rerun on each merge: WP-M 0138308d (2106b757), WP-N bac7a749 (4b2108e0; conflicts with WP-M in deps.py and calib_deps.py resolved keeping both), WP-O 067d05e7 (3a349fce; README conflict resolved keeping both), WP-P affcaf08 (e661b3fd; touches nothing under core/, contracts/schemas/ or the scripts).
- 2026-11-14 merged to main: PR #407 -> af9e05ab (CI 29 pass, 3 skipped; main tree = tested tree); status `merged` on the user's word ("auto continue, including push, open PR, merge, and release"); shipped in hep-research 0.67.0 (release branch `release/0.67.0`).
- 2026-11-14 GATE RUN 3 PASSED at 4f668d3a (`campaigns/p4-gates/gate-3.json`, SHA-256 b478c62d…; not dirty): `contrib_negatives` 15 tests, `g4sim_binding` 19 cases (85 tests), `generic_layer` (commits e661b3fd and 9cf8a372, no generic-layer file). Repository checks at 4f668d3a: only the three environment-only failures. Gate record written; phase 4 `gates-recorded`; changelog entry added (same minor release). The user: "auto continue, including push, open PR, merge, and release".
- 2026-11-14 gate run 2 FAILED (STOP, E7.4), at 2d4a142f from the clean worktree `tmp/wt-p4-gates-2` (`campaigns/p4-gates/gate-2.json`, SHA-256 bd301442…): `contrib_negatives` and `g4sim_binding` (19 cases) passed; `generic_layer` failed because the harness found no specialization commit — it passed repository-root paths to `git log` while running from the plugin root, so git read them relative to the plugin folder and matched nothing (an empty list fails by the rule). A harness defect, not a generic-layer change: with `:(top)` pathspecs the commits found are e661b3fd and 9cf8a372, neither touching the generic layer. Fixed and registered as gate run 3 (auto-continue, user 2026-11-14).
- 2026-11-14 repository checks at 4ef75ef7 (`campaigns/p4-checks/`): 7,932 tests, 7,622 passed, 306 skipped, 4 failed — the three environment-only failures of phase 0 and `test_check_wiring` (the hep-statistics README said forty-four scripts, 45 exist with calib_contrib.py): fixed, and `check_wiring` added to the commit gate (`tools-simcal/gate_commit.sh`).
- 2026-11-14 independent review (`review/phase-4-review.md`, one fresh-context subagent, approved under A23): gate parts supported (contrib), supported with reservations (g4sim binding; generic layer); F1 major (the T2 check trusted its inputs), F2–F6 minor, F7–F12 notes. Fixed: F1 (A24: σ and A_θ from the result's design stage, the basis from the result's hash-bound `t2_basis`), F2 (the generic check covers every specialization commit), F3 (exported values must be declared and name the result's parameters), F4 (stale binding text), F5 (a rejected export exits 1), F6 (the alternative-hypothesis physics-list test), F7 (a 20-seed calibration test of the bootstrap covariance: ratio 0.6–1.5 required), F8 (the export refuses a use the result does not allow), F9 (the harness self-test loads every mapped test), F12 (duplicate changes refused; a result marked for a redo not also listed under same-κ). Disclosed: F10 (calib_contrib.py cannot import the Geant4 adapter, layering; g4sim through the adapter's Python API), F11 (the item-7 search record is metadata only).
- 2026-11-14 A24 (the user, after "think more about A22, A23"): T2 in θ-space with the power condition (TOST at the result's own MC size could never pass); the Poisson-interval LY reweighting implemented in the g4sim evaluator, P0's reference made to re-digitize LY (it had compared the reweighting with itself), and the normal-density P0 case judged (fails; Poisson passes; 3000 and 10000 events).
- 2026-11-14 GATE RUN PASSED: `calibration_phase4_gates.py --run` from the clean worktree `tmp/wt-p4-gates` at 4ef75ef7 (card re-registered there) on the login host; `campaigns/p4-gates/gate.json` (SHA-256 4f0c13f8…; not dirty): `contrib_negatives`, `g4sim_binding` (18 cases, every case's tests pass; the A23 case recorded: P0 passes with the normal density), `generic_layer` (the specialization tests pass; the WP-P commit e661b3fd touches 31 files, none under core/, contracts/schemas/ or the scripts). Repository checks and the independent review started at 4ef75ef7.
- 2026-11-14 §15.3.19 coverage: every case mapped to its tests (harness `CASES`); new tests for "g4sim output as a data release" (`test_calibration_use.SimulatedReleases`) and the A23 record (`test_calibration_kernel_check.NormalDensityRecord`; toy photon kernel accepts registration `normal`). A23 (the user): the normal-density P0 case is a Part B finding, recorded not judged; one independent reviewer approved ("auto continue with your recommandation"). Gate dry run in the working tree: all three items pass (28 s).
- 2026-11-14 the g4sim evaluator's `effects_off` (WP-O's open item): the declared removal values are applied after θ with the same methods, unknown parameters and conflicting values refused (`g4sim_calib_eval.evaluate`, test on the synthetic ZDC fixture).
- 2026-11-14 A22 (the user): the T2 σ per observable is √diag of the design-stage total covariance at θ_ref; `identity-carried-over` is an informational flag (added to `use.INFORMATION_FLAGS`, test). Resolves WP-M's two open readings.
- 2026-11-13 WP-M (§10.3, A21 §19-g7): `deps.upstream_change`, `invalidate` (a revision or downgrade marks downstreams for a redo, transitively, for central and variation roles; a same-κ re-judgment is recognised only when the old result had pending inputs and (effective grade, uses) is unchanged), `identity_decision` (a changed masked identity item → redo unless a T2 record passes), `t2_check` and `tost` (Gaussian TOST, se = √(se_old² + se_new²), all points and observables must pass — an intersection-union test, no multiplicity correction; registered_at before the new build's first run, a missing run time → redo; the outcome is bound to the registration hash; margin and α may be tightened, never loosened); `calib_deps.py invalidate`, `identity`; the §15.3.19 `build_hash` redo test with real g4sim documents. No new schema file (the record is validated in the engine). Open for the author: A21's "0.1σ_tot^design per observable" (σ_tot^design is defined per θ_i in Part B; the record declares `sigma_tot_design` per observable, natural reading √diag of the design-stage total covariance at θ_ref); the flag `identity-carried-over` is not in Appendix C's flag list (`use.FLAGS`), so its effect on grade and use is undefined; the carry-over is an annotation keyed by result hash (a result hash cannot change).
- 2026-11-13 WP-N (§10.4, §10.2, §15.3.17, A21 §19-g6, §19-g8): `propagate.export_g4sim` (θ̂ written at the contract's θ bindings into `condition-snapshot/1` or `alignment-overlay/1`, overlay values as decimal strings; `source_of_facts` gains a `calibration_result` entry {result_sha256, effective_grade, uses, flags, variation_flags, use, parameters} and `calibration-result:<hash>` pointer labels; only θ written back, not φ; seven refusal codes), `use.check_export` (hash recomputed, grade, the stated use against the §10.2 use matrix, written values against θ̂), `deps.forced_joint_fits` and the `deps.xi_version` refusal (ξ has no versions); CLIs `calib_propagate.py g4sim`, `calib_use.py export`, `calib_deps.py packages` lists forced joint fits; schema validation in the CLIs (core cannot import contracts). §15.3.17 audit: every case has a test (new: single-η segmented = joint with the prior counterexample, the union of central grade-limiting flags, the export rejections, forced joint fits).
- 2026-11-13 WP-O (§10.5, §15.3.18): `evaluator.removal_values` and the toy evaluator's `effects_off`; contract field `effects[{name, removal}]` (§7.1 "declared in the contract"); `contrib.decompose` (Shapley terms; all 2ⁿ subsets for n ≤ 10, sampled orderings with sampling error above; every evaluated subset at G4's N_eff ≥ N_req via `design.g4_inputs_from`/`reweight.g4`, missing support or undefined N_req a failure; on any failure `contrib.ess` and no decomposition, the per-subset values withheld; bootstrap covariances at first order through per-event influence, B = 500, M = 200 orderings by default; object `variance` or `resolution` required); `calib_contrib.py decompose`; forced joint fits never arise (fixed parameter points, no packages; `forced_joint_fits: []`). Not done: the g4sim evaluator's `effects_off` (calib_contrib reports `incomplete` for g4sim plans). The hep-statistics guide is at 25,596 of 25,600 bytes.
- 2026-11-13 WP-P (§11, §12, §13, A21 §19-1, §19-4): eight specialization pages in `skills/hep-detector/references/simulation-calibration/` (ECAL, HCAL, RICH, DIRC, TRD, Tracker, TOF, μ detector) with §11.1 items 1–8; item 7 reads "no literature value" for every type (INSPIRE-HEP and arXiv searched 2026-11-13, queries recorded in index.md); item 8 alternatives with their observables; node-binding examples `skills/hep-detector/assets/simulation-calibration/*.binding.example.json`; `test_calibration_specialization.py` (all eight pass the unchanged contract checker, P4 and candidate methods, through the engine and the scripts; seven negatives caught); the calibration domain card `skills/hep-review/references/domains/detector.md`. §12 holds: no example needed a generic-layer change. g4sim binding limits (no Table 2 row: charge-sharing and drift-table parameters, a gas-avalanche stage, TTS / effective light speed / emission time, SiPM saturation, the TR yield factor; RICH mirror bound as a detector-spec parameter because an overlay misalignment has no recorded run, D83 (7)) — for g4sim upstream. Finding fixed by the main session: `chain.binding_row` classed `/physics/pai`, `/physics/xtr`, `/physics/optical`, `/physics/decay` as the continuous geometry row; they are now discrete run fields (refused as θ), with tests that fail on the old code.

## Open Questions

- Settled by the maintainer (2026-11-10, phase 0, Open questions 1 and 6): the records live in `docs/dev/simulator-calibration/`; the `calib_*.py` scripts of §14 live in `skills/hep-statistics/scripts/`, as thin CLIs over the engine in `core/calibration/` (§13); `g4sim_calib_eval.py` stays in `adapters/geant4` (§13).
- The decisions under "Needs the author" above.

## References

- Part B §17 (line 3582), §8.7, §13, §14, §15; `simcal-decision-index.md`; `simcal-task.md` Part A.
- `skills/hep-computing/assets/task-template.md`; `docs/dev/geant4-architecture/g4sim-tasks/` (precedent).

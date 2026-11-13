# Simulator calibration gate record: phase 3

**Phase 3 (Surrogate model and g4sim evaluator): every gate item passes** (gate run part C, one clean commit).
- **P6 negative tests:** all eleven listed tests show their expected finding, with positive controls passing.
- **G8 for the three-method combination** (gain by analytic reweighting, relative_gain_b by rerun, threshold by the surrogate model): G8 passes at the standard (N_c 99) and full level (N_c 518, Holm over 15 tests, the bias rule and the summed ratio test); the full-simulation spot check passes by P6's rule (A16 (i)).
- **g4sim positive tests on the synthetic ZDC fixture (§15.2):** all 34 test cases of the ten listed tests and classes pass, the five Geant4 tests on the products of campaign p3-g4 (none skipped as `requires-geant4`).
- **Response-layer parameters of ZDC Phase 3 and φ at the resimulation level:** 10 of 10 fit repetitions pass; both φ cases follow §5.5 to the surrogate route and pass its gates.
- **Thresholds (§8.7)** of the rows this phase uses: 2000, 2004 (P6 part, toy), 2006, 2008, 2009, 2015 and 2018 pass, 2006/2015 at a second registration (A15) after the first failed. The Geant4 version of row 2004 is running (below); the Geant4 versions of rows 2008 and 2009 are not feasible with the existing fixtures and are open for the author.
- Every result is `synthetic` with `provisional-thresholds`.

| Field | Value |
| --- | --- |
| Phase | 3 (Surrogate model and g4sim evaluator) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-3` (private ceph folder) |
| Branch | `simcal/phase-3`, from `origin/main` ca70a606; merged into `main` incrementally on green CI (PRs #400, #401, #403; the user's rule of 2026-11-12) |
| Commit | Gate run part C at `417d45ce` (arrays 7627611 and 7627612, every task from the clean worktree `tmp/wt-p3-gates-c`, one commit, not dirty). Later commits: the CI fix a72cf7fb (a subprocess timeout; `fit.curvature_covariance` for an exactly singular F, which before raised, so a crash-free part C is unaffected) and the §5.4 clamp b86b42e7 (the Birks bound shift, not on any gate item's path); the rest change the card and this record |
| Task-card SHA-256 (as registered) | `6a66fd1570d5987e8196c6368013d9c183f0b1da1a014f049d42f9ce2efaac79` (the last of 16 phase-3 registrations in `simcal-task-registry.json`, each before its run) |
| Environment | Batch: NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13` (Python 3.13.18, NumPy 2.4.6, SciPy 1.17.1), one BLAS thread, every task from a clean worktree at its registering commit checked by full SHA and clean status. Geant4: `g4sim_run-build28` (SHA-256 8b6230c1…, the S8 judged build) |
| hep-research and g4sim versions | hep-research 0.66.1 plus the phase-3 branch; g4sim stages S0–S9 merged (0.65.0); the one g4sim gap (S7 gate 3) is not a gate this phase depends on |
| Approvals | A12–A18 (`simcal-approvals.md`) |
| Date | 2026-11-13 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| P6 negative tests | `UNIT_RULE`: every listed test passes; a `requires Geant4` skip not judged; any other skip, failure or error fails | 11 of 11: the 10 negatives caught, the positive (`test_bonferroni_z`) passes | pass | `campaigns/p3-gates-c/merged-C.json` (SHA-256 `4aec233e…`), item `units\|p6_negatives` |
| G8 passes for the three-method combination | `M3_RULE` (card, part B, verbatim): G8 at the full level (d = 3, N_c = 518 per point, Holm over 15 tests, α_G8 = 0.05, bias rule, summed ratio) on surrogate pseudo-data, and the spot check by P6's rule | Standard and full level pass; full-level \|b̄\|/σ_design 0.03, 0.06, 0.05; 95% coverage 0.93–0.97; spot check passed (\|Δm\| max ratio 0.27; pull χ² not executed, 2 < 30 points). Non-converged pseudo-data (A18): 5 interior, 9 boundary of 540, all `likelihood.nonfinite`, replaced (535 and 531 ≥ 518) | pass | `merged-C.json`, item `g8_3m` |
| g4sim positive tests on the synthetic ZDC fixture (§15.2) | `UNIT_RULE` | 34 of 34 test cases pass; the five Geant4 tests run on the p3-g4 products (`SIMCAL_G4_PRODUCTS`) | pass | item `units\|g4sim_zdc_positive`; p3-g4 `evidence-merged.json` |
| can handle the response-layer parameters of ZDC Phase 3 | `CALO_RULE`: each repetition P3 at the prior centre, convergence, G1 with σ_noise from 5 batches, \|θ̂ − truth\| ≤ 4σ_tot | 10 of 10 repetitions pass | pass | item `zdc_fit` |
| φ at the resimulation level (φ must satisfy §5.5, otherwise use a surrogate model) | `PHI_RULE` | σ_φ 0.002: P8 incomplete → surrogate route; σ_φ 0.1: P8 failed → surrogate route; both pass the surrogate route's gates (P6; profile fit converges and passes G1) | pass | item `phi_resim`; item `units\|response_phi` (29 of 29 test cases) |
| with light-collection parameters, g4sim S7 is also needed | precondition | S7 merged (g4sim status file) | met | `simcal-tasks/phase-3.md` preconditions |

Earlier gate runs are kept as records, not evidence: part A (`p3-gates`, tasks 0–14 at 8ed54df4) passed, superseded because the code it tested changed (A16, A17, WP-J); part B (`p3-gates-b` at bff0b13a) failed with 12 crashed G8 tasks (an empty bootstrap resample; A18) and was not merged.

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| §15.3.1 P6 (\|Δm\|, pull χ², too few points, held-back and mandatory spot checks, tier decided by P6, query outside the domain, spot-check seed independence) | negative + positive | caught | gate C `p6_negatives`; `test_calibration_emulator` |
| §15.3.1 P0 (light yield; k_B) | negative + positive | P0 (LY) passes on Geant4; P0 (k_B) detects the re-digitization bias at k_B = 0.4 (A14, cause corrected by A17); the k_B split-bias negative met on the synthetic fixture only | p3-g4 evidence `zdc-p0-response`, `zdc-p0-birks`; `test_calibration_evaluator_problem` |
| §5.4 P5 feasibility of the k_B rerun (class-discretization bound) | negative + positive | fails on the synthetic fixture (504σ) and on the Geant4 products (14σ with `pe_std`, 71σ with `vis_mean`): k_B resimulated; a prior ≤ 1e-5 passes | `test_calibration_birks_bound`; `campaigns/p3-research/kB/birks-discretization-p3g4.json` (`c1402f8c…`) |
| §15.2 Birks rerun against resimulation | positive | passes at k_B 0.02, 0.21, 0.4 (every (event, volume) pair within its bound) | p3-g4 evidence `zdc-birks-rerun` |
| §15.3a model identity of `calib_contract` (masked hash, decimal strings, overlays) | negative + positive | caught | `test_calibration_model_identity` |
| §6.1 g4sim support and recording-level checks; §6.6 event intervals | negative + positive | caught | `test_calibration_g4sim_eval`, `test_calibration_g4sim_eval_coupling` |
| §6.7 efficiency-map φ, joint-pattern replicas, PDE split (rows 2008, 2009) | negative + positive | pass on the synthetic map | `test_calibration_map`, `test_calibration_pde_split`; p3-cals |
| RICH replica: P3 with one and two β, note 6 basin stability | negative + positive | P3 fails for one β with the multiple-β hint, passes for two; basins unchanged in 1000 of 1000 toys | p3-g4 evidence `rich-p3-p6`, `rich-note6` |

## This phase's thresholds (§8.7)

| Row | Calibrated value or `provisional-thresholds` | Evidence |
| --- | --- | --- |
| 2000: N_c and coverage of G8 (calibration 1, toy detector) | passed: false alarms 27 and 21 of 1000; power 996, 1000, 1000; calibration 10's twelve injection modes 20–33 | `campaigns/p3-toy-g8/merged.json` |
| 2004: P6 (toy, surrogate with known error) | first registration failed (pull χ² size 0.228 at H = 40); after the joint-covariance reference (A13) passed: 0, 0, 17 of 2000 at v = 0; v = 1 reported (64, 92, 107) | `campaigns/p3-cals-p6/p3-cals-p6-merged.json` |
| 2004: P6 on Geant4 (RICH replica, 2 observables, H = 32 and 8) | **running**: campaign `p3g-p6`, array 7627340 (15,358 Geant4 tasks) then 7627341 (P6); to be appended to this record | `simcal-tasks/phase-3.md` registration `p3g-p6` |
| 2006, 2015: f of the ESS threshold, replica-difference construction (calibrations 6 and 12 folded) | first registration failed (117, 132 of 1000 against ≤ 62: a shared-truth MC offset); second registration with the truth at 1000× the exposure (A15) passed: 43 and 13; power 995, 1000, 1000; V_MC × 0.5 detection curves reported | `campaigns/p3-toy-g8b/merged.json`; `p3-toy-g8` |
| 2008: θ-noise bounds of P5 | passed in all 12 configurations (pull sd 0.976–1.037; G8 at the full level) | `campaigns/p3-cals/p3-cals-merged.json` (`18084a26…`) |
| 2009: PDE split | passed: exact-split pass rate 0.952 and 0.940; power 1.0; replica/multinomial ≥ 0.98 | `p3-cals-merged.json` |
| 2008, 2009 on Geant4 | not feasible with the existing fixtures (need the §15.1 optical ZDC fixture); open for the author (the user's choice) | card |
| 2018: G8 item of calibration 15 (bimodal toy) | passed (`closure.decide`) | `p3-toy-g8/merged.json` |

## Review (Section E4, step 10)

- Pending: one fresh-context reviewer subagent (the user's "go ahead", 2026-11-13).

## Repository checks (E4 step 7)

- Pending: `tools/run_all_checks.py --jobs 8 --module-timeout 1800` at `5c2b0ca0` (clean worktree `tmp/wt-p3-checks`), run record in `campaigns/p3-checks/`.
- The commit gate (`tools-simcal/gate_commit.sh`: every calibration test module, the script tests, layering, naming, packaging, the reference inventory, the routing budget, CLI fuzz, the guide and the skill-script list) passed on every phase-3 commit; ruff and mypy before every push; PR CI green on #400, #401, #403.

## Open items carried to the next phase

- **For the author:**
  - approvals A12–A18 (Part B write-back);
  - Geant4 versions of rows 2008 and 2009 (the §15.1 optical ZDC fixture; what row 2008's Geant4 version judges);
  - §15.3.1's P0 (k_B) split-bias negative test met on the synthetic fixture only (A17);
  - `beam1_ratio_mean` has few qualifying events at exposure 2000 (A18);
  - the questions carried from phase 2 (rows 2018, 2013 (f), 2014, 2003; review F23).
- **g4sim upstream (D83):** `geometry_id` depends on decimal spellings of the schema.
- **Engine:** the Imhof reference warns at high correlation (WP-L); an optional RICH output-nesting test; F25 from phase 2.
- **Phase 4:** the five deferred author items (§19-1, §19-4, §19-g6, §19-g7, §19-g8) before it starts.

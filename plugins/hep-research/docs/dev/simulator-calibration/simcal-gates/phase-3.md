# Simulator calibration gate record: phase 3

**Phase 3 (Surrogate model and g4sim evaluator): every gate item passes** (gate run part E, one clean commit, after the independent review's fixes).
- **P6 negative tests:** 14 of 14, including the A13 joint-covariance reference's negative tests (review F8).
- **G8 for the three-method combination** (gain by analytic reweighting, relative_gain_b by rerun, threshold by the surrogate model): G8 passes at the standard (N_c 99) and full level (N_c 518, Holm over 15 tests, the bias rule and the summed ratio test); the full-simulation spot check passes by P6's rule (A16 (i)). The pseudo-data are Gaussian surrogate pseudo-data (A12, §19-5), not §8.4's event-level resampling (below).
- **g4sim positive tests on the synthetic ZDC fixture (§15.2):** 34 of 34 test cases pass, the five Geant4 tests on the products of campaign p3-g4.
- **Response-layer parameters of ZDC Phase 3:** on the synthetic transport stand-in, 40 of 40 fits pass with the pull χ² within its 99% quantile (tightened by A19); on the Geant4 products by re-digitization, the light yield passes the same rule (40 of 40). The resolution scale is not identifiable on the Geant4 products (P3 fails, a correct detection).
- **φ at the resimulation level:** σ_φ 0.002 passes in shift mode (P8, G9); σ_φ 0.1 fails P8 and passes on the surrogate route (§5.5).
- **Thresholds (§8.7)** of the rows this phase uses: 2000, 2004 (toy and Geant4), 2006, 2008, 2009, 2015 and 2018 pass, 2006/2015 and 2004 (toy) at second registrations after their first failed. The Geant4 versions of rows 2008 and 2009 are not feasible with the existing fixtures and are open for the author.
- **Review:** one independent reviewer found 1 major, 7 minor and 4 notes; all are fixed, disclosed or recorded below (A19), and the gate was rerun twice (part D failed on φ, A20; part E passed).
- Every result is `synthetic` with `provisional-thresholds`.

| Field | Value |
| --- | --- |
| Phase | 3 (Surrogate model and g4sim evaluator) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-3` (private ceph folder) |
| Branch | `simcal/phase-3`, from `origin/main` ca70a606; merged into `main` incrementally on green CI (PRs #400, #401, #403; the user's rule of 2026-11-12) |
| Commit | Gate run part E at `586a143e` (arrays 7647807, 7647808, 7647809; every task from the clean worktree `tmp/wt-p3-gates-e`, one commit, not dirty). Later commits change the card and this record only |
| Task-card SHA-256 (as registered) | the last phase-3 registration in `simcal-task-registry.json` (`6671aa5a…`, gate part E, before its run); later commits change the execution log and this record only |
| Environment | Batch: NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13` (Python 3.13.18, NumPy 2.4.6, SciPy 1.17.1), one BLAS thread, every task from a clean worktree at its registering commit checked by full SHA and clean status. The p3-g4 tell and evidence ran with Python 3.13.2 and NumPy 2.2.2 (review F7). Geant4: `g4sim_run-build28` (SHA-256 8b6230c1…, the S8 judged build); products `/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3` (tell.json SHA-256 cefc811d…) |
| hep-research and g4sim versions | hep-research 0.66.1 plus the phase-3 branch; g4sim stages S0–S9 merged (0.65.0); the one g4sim gap (S7 gate 3) is not a gate this phase depends on |
| Approvals | A12–A20 (`simcal-approvals.md`) |
| Date | 2026-11-13 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| P6 negative tests | `UNIT_RULE`: every listed test passes; a `requires Geant4` skip not judged; any other skip, failure or error fails | 14 of 14: 12 negatives caught (incl. the plain reference oversized on correlated points and the joint reference catching 4× the stated covariance), 2 positives pass | pass | `campaigns/p3-gates-e/merged-E.json` (SHA-256 `92a9065b…`), item `units\|p6_negatives` |
| G8 passes for the three-method combination | `M3_RULE` (card, part B, verbatim): G8 at the full level (d = 3, N_c = 518 per point, Holm over 15 tests, α_G8 = 0.05, bias rule, summed ratio) on surrogate pseudo-data, and the spot check by P6's rule | Standard and full level pass; full-level \|b̄\|/σ_design 0.03, 0.06, 0.05; 95% coverage 0.93–0.97; spot check passed (\|Δm\| max ratio 0.27; pull χ² not executed, 2 < 30 points). Non-converged pseudo-data (A18): 5 interior (0.9%), 9 boundary (1.7%) of 540, all `likelihood.nonfinite`, replaced (535 and 531 ≥ 518) | pass | `merged-E.json`, item `g8_3m` (with `non_converged`) |
| g4sim positive tests on the synthetic ZDC fixture (§15.2) | `UNIT_RULE` | 34 of 34 test cases; the five Geant4 tests on the p3-g4 products | pass | item `units\|g4sim_zdc_positive`; p3-g4 `evidence-merged.json` |
| can handle the response-layer parameters of ZDC Phase 3 | `CALO_RULE` (tightened, A19): each repetition P3, convergence, G1, \|pull\| ≤ 4; per θ the pull χ² over the repetitions ≤ χ²₀.₉₉ | Stand-in (40 fresh repetitions): 40 of 40; pull χ² 39.3 (light yield), 30.1 (resolution) ≤ 63.7; rms 0.99, 0.87. Geant4 products, light yield (`CALO_G4_RULE`): 40 of 40; pull χ² 51.9 ≤ 63.7; rms 1.14 | pass | items `zdc_fit`, `zdc_fit_g4` |
| φ at the resimulation level (φ must satisfy §5.5, otherwise use a surrogate model) | `PHI_RULE` (exposure 4000, MC 40,000, A20) | σ_φ 0.002: P8 passed → shift mode, refits converged, G9 passed. σ_φ 0.1: P8 failed → surrogate route: P6 passed, the profile fit converged and passed G1 | pass | item `phi_resim`; item `units\|response_phi` (29 of 29) |
| with light-collection parameters, g4sim S7 is also needed | precondition | S7 merged (g4sim status file) | met | `simcal-tasks/phase-3.md` preconditions |

Earlier gate runs are kept as records, not evidence:
- part A (`p3-gates`, tasks 0–14 at 8ed54df4) passed; superseded because the code it tested changed (A16, A17, WP-J);
- part B (`p3-gates-b` at bff0b13a) failed: 12 G8 tasks crashed on an empty bootstrap set (A18); not merged;
- part C (`p3-gates-c` at 417d45ce) passed (`merged-C.json`, `4aec233e…`); superseded by the review (A19);
- part D (`p3-gates-d` at 479bd4c5) failed on φ only: its profile fits were non-identified by §7.4 (σ_tot/σ_prior 1.2–1.4 at exposure 500), now caught by F5 (A20) (`merged-D.json`, `b8301839…`).

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| §15.3.1 P6 (\|Δm\|, pull χ², too few points, held-back and mandatory spot checks, tier decided by P6, query outside the domain, spot-check seed independence, the A13 joint reference) | negative + positive | caught. The joint reference catches 4× the stated covariance on correlated points (ρ = 0.9) in ≈ 95% of repetitions, but 2× in only ≈ 33%: few effective degrees of freedom | gate E `p6_negatives`; `test_calibration_emulator` |
| §15.3.1 P0 (light yield; k_B) | negative + positive | P0 (LY) passes on Geant4; P0 (k_B) fails at k_B = 0.4 on Geant4 (A14; cause the class discretization, A17). Its split-bias negative test is met on the synthetic fixture only, and the width spot check on Geant4 detects the discretization bias rather than the split bias (review F6) | p3-g4 evidence `zdc-p0-response`, `zdc-p0-birks`; `test_calibration_evaluator_problem` |
| §5.4 P5 feasibility of the k_B rerun (class-discretization bound) | negative + positive | fails on the synthetic fixture (504σ) and on the Geant4 products (14σ with `pe_std`, 71σ with `vis_mean`): k_B resimulated; a prior ≤ 1e-5 passes | `test_calibration_birks_bound`; `campaigns/p3-research/kB/birks-discretization-p3g4.json` (`c1402f8c…`) |
| §15.2 Birks rerun against resimulation | positive | passes at k_B 0.02, 0.21, 0.4 (every (event, volume) pair within its bound). The bound is ≈ 30% of the visible energy against an observed bias of 0.4%, so this test is weak (review F6) | p3-g4 evidence `zdc-birks-rerun` |
| §7.4 admission applied to every converged fit (review F5) | negative + positive | a converged point with σ_tot,i > R_admit σ_prior,i is reported not converged (it exposed the φ item, A20) | `test_calibration_fit`; gate parts D, E |
| §15.3a model identity of `calib_contract` (masked hash, decimal strings, overlays) | negative + positive | caught | `test_calibration_model_identity` |
| §6.1 g4sim support and recording-level checks; §6.6 event intervals | negative + positive | caught; the interval check passes on 15,360 Geant4 evaluations (row 2004) | `test_calibration_g4sim_eval`, `test_calibration_g4sim_eval_coupling`; p3g-p6 `merged.json` |
| §6.7 efficiency-map φ, joint-pattern replicas, PDE split (rows 2008, 2009) | negative + positive | pass on the synthetic map | `test_calibration_map`, `test_calibration_pde_split`; p3-cals |
| RICH replica: P3 with one and two β, note 6 basin stability | negative + positive | P3 fails for one β with the multiple-β hint, passes for two; basins unchanged in 1000 of 1000 toys | p3-g4 evidence `rich-p3-p6`, `rich-note6` |

## This phase's thresholds (§8.7)

| Row | Calibrated value or `provisional-thresholds` | Evidence |
| --- | --- | --- |
| 2000: N_c and coverage of G8 (calibration 1, toy detector) | passed: false alarms 27 and 21 of 1000; power 996, 1000, 1000; calibration 10's twelve injection modes 18–33 | `campaigns/p3-toy-g8/merged.json` |
| 2004: P6 (toy, surrogate with known error) | first registration failed (pull χ² size 0.228 at H = 40); after the joint-covariance reference (A13) passed: 0, 0, 17 of 2000 at v = 0; v = 1 reported (64, 92, 107). The correct surrogate never interpolates and uses unpaired seeds (review F11) | `campaigns/p3-cals-p6/p3-cals-p6-merged.json` |
| 2004: P6 on Geant4 (RICH replica, 2 observables) | passed: v = 0: 17 of 2000 at H = 32 (pull χ² size 0.008), 8 of 2000 at H = 8 (≤ 29); v = 1 reported (432, 295) | `/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3g/rich-p6cal/merged.json` (`f2ea9614…`) |
| 2006, 2015: f of the ESS threshold, replica-difference construction (calibrations 6 and 12 folded) | first registration failed (117, 132 of 1000 against ≤ 62: a shared-truth MC offset); the second, with the truth at 1000× the exposure (A15), passed: 43 and 13; power 995, 1000, 1000; V_MC × 0.5 detection curves reported | `campaigns/p3-toy-g8b/merged.json`; `p3-toy-g8` |
| 2008: θ-noise bounds of P5 | passed in all 12 configurations (pull sd 0.976–1.037; G8 at the full level). All 12 lie far inside the bounds, so the bounds themselves are not probed (review F10) | `campaigns/p3-cals/p3-cals-merged.json` (`18084a26…`) |
| 2009: PDE split | passed: exact-split pass rate 0.952 and 0.940 (route 3 exactly at the 0.94 limit, CP95 0.929–0.950; review F10); power 1.0; replica/multinomial ≥ 0.98 | `p3-cals-merged.json` |
| 2008, 2009 on Geant4 | not feasible with the existing fixtures (they need the §15.1 optical ZDC fixture); open for the author (the user's choice) | card |
| 2018: G8 item of calibration 15 (bimodal toy) | passed (`closure.decide`) | `p3-toy-g8/merged.json` |

## Disclosures (review A19)

- **G8 pseudo-data (F2):** the three-method G8 draws its pseudo-data as N(μ̂, V_data) around the mean of 20 truth surrogates (A12 permits surrogate pseudo-data for resimulation-level parameters). It is not §8.4's event-level resampling, so it cannot see failures of the Gaussian approximation of the summary statistics or of n_min, and it is blind by construction to an interpolation error shared by the truth surrogates and the fits; only the spot check sees that.
- **Spot check (F3):** decided by P6's rule (A16 (i)), it tolerates offsets of about 0.78σ_data per observable, looser than G8's 0.2σ_tot bias test. Part E's offsets are small (max ratio 0.27).
- **φ (F4):** the rule checks the route's gates, not the fitted values against the truth; the truth sits at the φ constraint centre. At exposure 4000 the small-σ_φ case now reaches shift mode.
- **k_B on Geant4 (F6):** see the tests table above; the P0 (k_B) item in the positive list asserts a failure recorded after the result was seen (A14, A17).
- **Response fit (F1):** the stand-in fit's excess spread at part C's size (`resolution` pulls rms 1.18 over 40 research repetitions) has no misstated covariance behind it (V_MC and V_data stated correctly); it tracks the MC-noise roughness of the objective (σ_noise). The tightened rule and 40 fresh repetitions pass.
- **`birks_parameter` (F12, uncertain):** it takes the first parameter with method `rerun`, not k_B by its binding; correct for every fixture of this phase.

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent, approved by the user ("go ahead", 2026-11-13). It read the phase-3 diff, Part B and the evidence at gate part C (417d45ce). Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-3-review.md`.
- **Verdicts:** P6 negatives supported (minor); three-method G8 supported with reservations (F2, F3); g4sim ZDC positives supported with reservations (F6); ZDC response parameters supported as registered with a major reservation (F1); φ supported with reservations (F4); S7 supported.
- **Findings:** 1 major, 7 minor, 4 notes. The user chose "Fix all, rerun gate" (A19).
  - F1: diagnosed (research array 7631230); the rule tightened (pull χ², 40 fresh repetitions); a Geant4 item added (`zdc_fit_g4`).
  - F5: the §7.4 admission applied to every converged fit. It exposed the φ item, which was redesigned (A20).
  - F8: the joint-reference negative test added.
  - F9: rechecked. A18's cause stands; its note is restated (bootstrap sets of 4 events at exposure 2000).
  - F7: the merge now records the non-converged counts, the products and the tell hash, and keeps the toy rows apart; this record is corrected (row 2000's 18–33, the boundary non-convergence 1.7%, the evidence's Python and NumPy).
  - F2, F3, F4, F6, F10–F12: disclosed above.
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- `tools/run_all_checks.py --jobs 8 --module-timeout 1800` at `5c2b0ca0` (clean worktree `tmp/wt-p3-checks`): 7,863 tests in 580 modules, 7,554 passed, 306 skipped, 3 failed. Every check passes except the two rows that aggregate those tests (`unittest`, `ams_optional`). Run record `campaigns/p3-checks/check-run-2026-11-13T115346Z.json`.
  - The 3 failures (`test_revocation` ×2: ceph ACL semantics; `test_event_display_templates.test_export_bundle_check`) also fail on a clean `origin/main` copy (phase 0's record).
- Later code (the review fixes at 04c11c0f, the φ sizing at 337fffd9) passed the commit gate (`tools-simcal/gate_commit.sh`: every calibration test module, the script tests, layering, naming, packaging, the reference inventory, the routing budget, CLI fuzz, the guide and the skill-script list), ruff and mypy. PR CI was green on #400, #401 and #403.

## Open items carried to the next phase

- **For the author:**
  - approvals A12–A20 (Part B write-back);
  - Geant4 versions of rows 2008 and 2009 (the §15.1 optical ZDC fixture; what row 2008's Geant4 version judges);
  - §15.3.1's P0 (k_B) split-bias negative test met on the synthetic fixture only (A17);
  - the resolution scale is not identifiable on the Geant4 ZDC products (pe_std shower-dominated);
  - the joint P6 reference's limited power under strong correlation (2× the covariance caught in ≈ 33%);
  - the toy problem's bootstrap sets of 4 events at exposure 2000 (A18, F9);
  - the questions carried from phase 2 (rows 2018, 2013 (f), 2014, 2003; review F23).
- **g4sim upstream (D83):** `geometry_id` depends on decimal spellings of the schema.
- **Engine:** the Imhof reference warns at high correlation (WP-L); an optional RICH output-nesting test; F25 from phase 2.
- **Phase 4:** the five deferred author items (§19-1, §19-4, §19-g6, §19-g7, §19-g8) before it starts; a draft decision sheet is prepared outside the repository.

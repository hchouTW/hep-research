# Simulator calibration gate record: phase 2

**Phase 2 (Engine and validation): all three gates pass.**
- **Gate 1:** on the toy detector, the negative tests of P3, P7, G1–G8, V and propagation each show their expected finding, and each has a positive control that passes. All 18 items meet their registered criteria at the hand-over code, and every calibration unit-test module and the script tests pass. By approval A10, two G8 controls run on the linear configurations.
- **Gate 2:** on the toy detector, the segmented calibration through the joint-posterior export agrees with the joint fit to 0.0026σ; both registered counterexamples violate the criteria.
- **Gate 3:** the eight negative tests of P8 and G9 come out as designed.
- **Thresholds (§8.7):**
  - 13 calibrations confirm their design values: 2, 3, 4, 5, 7 (with the bound tightened to 0.10 by A9), 8, 9, 11, 12, 13, 14, and 10 except its item (f).
  - 1 and 6, and the G8 items of 10, 12 and 15, pass on the linear configurations by A11 (not toy-detector evidence).
  - Two fail and are recorded by the user's decisions, with questions to the author: 15 (basin stability with an independent MC sample per reseeding) and 10 (f) (the spread of the Σ_boot toy estimate).
  - The rows they decide keep `provisional-thresholds`.
- **Review:** an independent review (one subagent) found 4 major, 13 minor and 9 notes; all are fixed or recorded, and gate 1 was redesigned on the toy detector (review F1, F2).

| Field | Value |
| --- | --- |
| Phase | 2 (Engine and validation) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-2` (private ceph folder) |
| Branch | `simcal/phase-2`, from `simcal/phase-1` 707134fc (unmerged; PR #386 stacked on PR #385; continued on the user's word) |
| Commit | Hand-over code (the engine, the scripts and the gate harness) at `7818ec35`: gate 1 (array 7589391), gates 2 and 3 run there, each from a clean worktree at that commit. Later commits change the card, the reference documents and the `tests/core` calibration drivers only. Calibrations: each at the commit of its registration (3, 5, 13, 14 at `6e8842e9`; 7 at `4a521280`; 9, 12 at `771c1b9a`; batch A at `456cfeac`; 8 at `9b1a3e97`; batch B at `49bada84`; 10 (e) rerun at `f44018e1`; batch C at `e46812b3`). Repository checks at `5f28844c`. |
| Task-card SHA-256 (as registered) | `6be65e12529b4ebcccc1cbf156425cea56967e29f641c764dbfd40c8466ec423` (the last of 25 phase-2 registrations in `simcal-task-registry.json`, each before its run; later commits change the execution log only) |
| Environment | Login host: Python 3.13.2 (conda env `ml`, NumPy 2.2.2, SciPy 1.16.1), `TMPDIR` on the private ceph folder, one BLAS thread. Batch: NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13`, each submission approved by the user |
| hep-research and g4sim versions | hep-research 0.65.1 plus `simcal/phase-0` and `simcal/phase-1`; g4sim not used (§17) |
| Date | 2026-11-12 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| The negative tests of P3, P7, G1–G8, V and propagation pass | Card "Gate 1 on the toy detector" (registered before each run; the last re-registration at `ead505a7`): 18 items, every task from one clean commit | All 18 items pass at `7818ec35`. Units: every module passes. P3: 5 cases as designed. G1, G2 (beyond, on, two bounds with χ̄²), G5, G6 (the missing effect fails, via full toys when the linearity check fails). G7: 1/40 vs 37/40. BB-lite: 0/40 vs 40/40. Cross-validation: p = 0.24, fold P3 as designed. Propagation: 2.30 vs 2.0, `deps.source_overlap`, `deps.theta_nu_split`. P7: cross product +0.67% (single set +32%), point estimate 679/2000 vs 0. Event samples: 0.057 (ω = 1: 0.272), power 0.778 (N_pass: 0.0545), two periods 0.0515 (0.620). G8 (A10): ln det 50/50 (correct 1/50), counting 17 vs 152. V cross terms: 0.0513 vs 0.447. V shift mode: 0.0513, minus sign 0.134, indirect 0.316, X 1.6%. Shapes conditioned on the total: 0.0557, 0.0527, 0.0441, 0.0476 | pass | `campaigns/p2-gate1-toy/gate1-toy-merged.json` (SHA-256 `5c5fa584…`), Slurm array 7589391 |
| segmented calibration and the joint fit agree (all of the above on the toy detector) | Card gate-2 design registered at `ffcab887`: \|Δθ_i\| ≤ 0.1σ_i, \|σ ratio − 1\| ≤ 0.1, correlations within 0.1; both counterexamples must violate | Joint-posterior export: 0.0026σ, 8.7·10⁻⁵, 1.4·10⁻⁴. Prior counterexample: correlations 0.21, σ ratio 0.20 (violates). Marginal-regression counterexample: σ ratio 0.59, correlations 0.17 (violates) | pass | `.simcal-work/gates/gate2-segmented-r4.json` (SHA-256 `3b369d24…`) |
| the negative tests of P8, G9 | Card gate-3 design, seeds 20261150 + case index | P8: c = 0.3 fails, 0.05 passes. G9: expansive cubic and quadratic fail (`g9.linearity`), compressive passes, condition 1 at θ̂ with 1.5c fails, a non-converged refit fails, not decided after P8 failed | pass | `.simcal-work/gates/gate3-shift-r4.json` (SHA-256 `04466bd2…`) |

Earlier runs of the gates are kept as records, not evidence. Gate 1 ran at dc4eace0 (superseded by the review). Array 7584035 was cancelled (crash, fixed at 518c0d6d). Array 7584442 failed on V shift mode (X 7.45%; nominal MC raised to 16 000, re-registered). Array 7585498 passed at 69871a3a, before the naming fixes. Gates 2 and 3 also passed at ffcab887/2b429ea1, d7f7bbf2 and 69871a3a.

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| §15.3.1 P3, G5 (products, Fano/ENF × gain, common mode of redundant measurements) | negative + positive | caught; positives pass | gate 1 `toy_p3`, `g5`; `test_calibration_identify_shift_interval` |
| §15.3.1 P7 (ν_k = 2 rejected; insufficient power; λ = 12.8 cross product; point-estimate scaling) | negative + positive | caught | gate 1 `p7_cross`, `p7_point`; `test_calibration_contract`; calibrations 3, 14 |
| §15.3.1 P8, G9 | negative + positive | caught | gate 3; calibration 4 |
| §15.3.1 G1, multiple basins (§15.2) | negative + positive | caught; basins kept, tied, not merged | gate 1 `g1`; `test_calibration_fit`; calibration 15 |
| §15.3.1 G2 (beyond the boundary; on it; two parameters with χ̄²) | negative + positive | caught | gate 1 `g2` |
| §15.3.1 G3, G4 | negative + positive | caught | `test_calibration_fit.G2G3`; `test_calibration_g4` |
| §15.3.1 G6 (missing effect; linearity check → full toys) | negative + positive | caught | gate 1 `g6`; calibrations 2, 10 (c) |
| §15.3.1 G7 (V_MC × 3; BB-lite; injected non-convergence) | negative + positive | caught | gate 1 `g7`, `g7_bblite`; calibrations 5, 6, 10 (e) |
| §15.3.1 G8 (fitter without ln det; counting control; decision rule) | negative + positive | caught | gate 1 `g8_lndet`, `g8_counting` (A10); calibrations 1, 6, 10, 12, 15 on the linear configurations (A11) |
| §15.3.1 V (cross terms; d_l minus sign and indirect only; shapes conditioned on the total; event samples) | negative + positive | caught | gate 1 `v_cross`, `v_shift`, `shape_total`, `event_samples` |
| §15.3.4, §15.3.5 declaration of constraints, rounding | negative + positive | caught | calibrations 8, 9; `test_calibration_validate.NullSpace`; `test_calibration_data_checks` |
| §15.3.8 cross-validation (fold rules, G5 conditioning) | negative + positive | caught | gate 1 `cv`; calibration 11 |
| §15.3.9 bootstrap noise, replacement, common random numbers | negative + positive | caught; 10 (f) fails its spread rule | calibration 10 |
| §15.3.10 power (cross product, lower bound) | negative + positive | caught | calibrations 3, 14; gate 1 `p7_point` |
| §15.3.14 failure records with computed decision records | negative + positive | caught | `test_calibration_validate.Records`; `test_calib_scripts.Phase2Scripts` |
| §15.3.17 propagation (central, counterexamples, packages, θ/ν split) | negative + positive | caught | gate 1 `propagation`; gate 2; `test_calibration_propagate` |
| §6.6 replica-difference toys (size, interval toys, negative controls) | negative + positive | caught | calibration 12 |

## This phase's thresholds (§8.7)

| Row | Calibrated value or `provisional-thresholds` | Evidence |
| --- | --- | --- |
| 2000: N_c and coverage targets of G8 | on the linear configurations (A11): false alarms 21 and 14 of 1000, power 1000/1000 in the three p₁ cases; toy detector `provisional-thresholds` (the toy's finite-sample bias, below) | calibration 1, `campaigns/p2-cals-c/cals-c-merged.json` (`4fbe8253…`) |
| 2001: allowed fraction of the linearity check | design value confirmed: G6 0.009 vs 0.0115 (linear), KS p ≈ 1 | calibration 2, `campaigns/p2-cals-a/cals-a-merged.json` (`88ab5c51…`) |
| 2002: λ estimate of P7 | design value confirmed | calibration 3, `cal-lambda.json` |
| 2003: c and t_lin of shift mode | design values confirmed on the toy detector at λ ≈ 0.03, 0.1 (coverage within 3 se, rms within 1.5%); r = 0.21–0.65, below note 5's range | calibration 4, batch A |
| 2005: K of G7 | design values confirmed | calibration 5, `cal-g7.json` |
| 2006: f in the ESS threshold | confirmed at f = 0.1: G7 13 and 11 of 1000; G8 (A11) 20 and 13, power 1000 | calibration 6, batch C |
| 2007: Jacobian MC-noise bias bound of P5 | **calibrated: \|b_J,i\| ≤ 0.10σ_tot,i^design** (approval A9; Part B's 0.15 failed) | calibration 7, `cal-bj-3.json` |
| 2011: τ_num | design value confirmed on the toy detector | calibration 8, `cal-tau-num.json` (`8ef38152…`) |
| 2012: negligibility condition for rounding | design value confirmed | calibration 9, `cal-rounding.json` |
| 2013: n_min and B | items (a)–(e), (g) confirmed. G8 items on the linear configurations (A11): false alarms 24–30 and 10–17. **Item (f) failed** (relative sd of the Σ_boot trace 0.386 > 0.3; bias −6%), so this row keeps `provisional-thresholds`; question to the author | calibration 10, batches B and C, `cal10-12-*.json` |
| 2014: G5 failures in cross-validation toys | 20% confirmed as safe (size within α ± 25% below it); Part B's "no longer negligible above 20%" not confirmed (+20%, −13% at 21%, 32%) | calibration 11, batch A |
| 2015: replica-difference construction | T_v size, interval-toy coverage and the negative controls confirmed; G8 items on the linear configurations (A11). Effective-count pulls, power toys in a shared-event cross-validation and Wishart toys keep `provisional-thresholds` | calibration 12, batches B and C |
| 2016: number of toys for Ĉ_r | design value confirmed | calibration 13, `cal-chat.json` |
| 2017: lower bound of λ̂_a^cross | design value confirmed | calibration 14, `cal-lambda-bound.json` |
| 2018: basin tolerances and starts | **failed**: stable with a fixed MC sample (≥ 0.997) but not with an independent MC sample per reseeding (0.984, 0.740, 0.160). The G8 item for `multimodal` results passed on the linear configuration (A11). Keeps `provisional-thresholds`; question to the author | calibration 15, batches A and C |

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent, approved by the user ("Yes, one reviewer"). It read the phase-2 diff at `4a68ebe4` and Part B. Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-2-review.md` (SHA-256 `a75c28c6aeadb29120ad93fc586ea3927a06c45e7d05157e94bb3ff6390b5741`).
- **Verdicts:** gate 1 not supported as worded; gates 2 and 3 supported.
- **Findings:** 4 major, 13 minor, 9 notes. The user chose "Fix everything, rerun gate 1".
  - F1: gate 1 was not on the toy detector. It was redesigned on the toy detector, with A10 for two G8 controls.
  - F2: V criteria were applied loosely. The registered 2000 repetitions and α ± 25% are now used.
  - F3: checks that no script delivered. They are wired into their scripts.
  - F4: decision records filled by hand. They now come only from computed, sealed evidence.
  - The minor items and notes are fixed or recorded in the card (F25, the cross-validation ensemble's redo, is open).
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- `tools/run_all_checks.py --jobs 8 --module-timeout 1800` at `5f28844c` (clean worktree): 7,575 tests in 564 modules, 7,274 passed, 298 skipped, 3 failed; the checks: 603 pass, 6 fail. Run record `.simcal-work/checks5/check-run-2026-11-12T103035Z.json` (worktree, untracked).
  - The 3 failures (`test_revocation` ×2: ceph ACL semantics; `test_event_display_templates.test_export_bundle_check`) also fail on a clean `origin/main` copy (phase 0's record). The other 5 failing rows aggregate them: `unittest`, `ams_optional` (its `tests_contracts`, `tests_hep_computing`) and the two group rows.
- Earlier runs found failures of this phase, all fixed before `5f28844c` (card execution log):
  - naming (50 new findings; identifiers renamed);
  - CLI input fuzz (malformed JSON refused with exit 2);
  - the guide's dependency markers and its routing budget (the guide's wording tightened by the user's choice);
  - the skill-script list and reference inventory (regenerated);
  - the packaging scan (an attribute access read as a host name).
- `check_layering`, `check_naming`, `check_packaging`, `reference_inventory --check` and `skill_scripts.py --check` pass at `5f28844c`.
- `contracts/validate.py`: phase 2 writes no `artifacts_dir` artifact; its calibration schemas are checked by `test_calibration_schemas`.

## Open items carried to the next phase

- **For the author** (a new part of Appendix E):
  - approvals A9 (b_J bound 0.10), A10 and A11 (G8 runs on linear configurations);
  - the reading of note 6's "independent seeds", and whether τ_tie and τ_bar should absorb MC-sample noise (calibration 15);
  - the Σ_boot spread rule at N_t = 10, K_b = 6 (calibration 10 (f));
  - Part B's statement on the G5 proportion above 20% (calibration 11);
  - the review's questions (F23);
  - the calibrated values above.
- **Phase 3 (g4sim):**
  - the toy-detector G8 rows. The research run shows the toy's bias in the sum term a is finite-sample (−0.14σ at 100 events per run, −0.003σ at 8000; independent of MC size), so toy-detector G8 needs exposures where it is below about 0.02σ, or a model of it;
  - the effective-count pulls (BB-lite, binomial auxiliary likelihood, weighted MC);
  - P7 power agreement under injection;
  - power toys in a shared-event cross-validation;
  - Wishart toys;
  - θ requiring resimulation under common random numbers;
  - the shift-mode confirmation at r = 0.5–4 with a resimulation-level φ.
- **Engine:** F25 (cross-validation ensembles do not sum X across redos); toy-detector problems use one exposure for every run; the toy's thickness φ is exactly degenerate with the light yield.
- **For the maintainer:** the hep-statistics guide wording tightened to fit the routing budget with every calibration script listed (the user's choice); the commit gate used in this phase now runs the naming, packaging, routing-budget and reference-inventory checks.

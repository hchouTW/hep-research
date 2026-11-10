# Simulator calibration gate record: phase 1

**Phase 1 (Evaluation and design stage): both gates pass.**
- **Gate 1:** the negative tests of A0, P0, P2 and P5 each show their expected finding code, and each has a positive control that passes.
- **Gate 2:** reweighting and rerun agree in all five registered cases, and the deterministic rerun is exact.
- **Calibrations:** the two §8.7 calibrations of the phase confirm their design values.
- **Review:** an independent review found 1 major, 11 minor and 3 notes, all resolved without a change to Part B. The gate runs were then repeated at the fixed code.

| Field | Value |
| --- | --- |
| Phase | 1 (Evaluation and design stage) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-1` (in the private ceph folder, like phase 0) |
| Branch | `simcal/phase-1`, from `simcal/phase-0` 1a27ab10 (unmerged, PR #385; continued on the user's word) |
| Commit | Gate runs and calibrations at `e940ef2e`; repository checks at CHECKS_COMMIT |
| Task-card SHA-256 (as registered) | `ca717b11c66be98b8d551f562f6ec2b6f7faecfc884c90b6b87aabd1c645726f` (registered before the repeated gate runs; earlier registrations `32bc1e6d…` and `fd133e30…`; later registrations change the execution log only) |
| Environment | Login host: Python 3.13.2 (conda env `ml`, NumPy 2.2.2, SciPy 1.16.1), `TMPDIR` on the private ceph folder. Batch: NSTCCore Slurm, partition `edr1-al9_short_serial`, account `ams`, interpreter `/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13` (3.13.18, NumPy 2.4.6, SciPy 1.17.1) |
| hep-research and g4sim versions | hep-research 0.65.1 plus `simcal/phase-0`; g4sim not used (§17: phases 0–2 do not depend on g4sim) |
| Date | 2026-11-10 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| The negative tests of A0, P0, P2, P5 pass | Each case of the card's gate-1 design (items 1–9) shows its expected finding code, and its positive control passes | A0: 3.5% → `a0.unreachable`, 1.0% reachable. P0: Fano 1.5 declared Poisson → `p0.kernel_inconsistent` (passes when registered as negative binomial); single support U(θ, θ+1) → failed, plus `support.missing`; mixture → passed. P2: 12 observables → `p2.insufficient_ndf`; toy ndf 15 passes; D77 counting. P5: (a) `p5.ess`, broadened q passes; (b) interior `p5.ess`, edges pass; (c) `p5.matrix_condition` alone, ESS and D42 pass; (d) μ = 1000 moved to resimulation, P5 passes; D42 `p5.v_mc_diagonal`; D41 tail functional refused. Weight formula: max \|w − 1\| = 0. D37 in both directions. §15.3.16 cases | pass | `tests.core.test_calibration_{preflight,kernel_check,design,reweight}`, `tests.skills.test_calib_scripts.Phase1Scripts` (130 tests in the ten calibration modules pass at `e940ef2e`) |
| reweighting and rerun agree | Card gate-2 design. Five cases (photon generation, PDE, gain, electronics without zero suppression, and photon generation plus PDE with S_θ∖S_q non-empty) at the worst-ESS and the next two of 64 Sobol points. Criteria: (i) P0's criterion, (ii) paired χ² with p ≥ 0.01/15, (iii) deterministic rerun exact to 10⁻¹² | Run 2 at `e940ef2e` (clean tree): all five cases pass support, P0 (max \|Δθ\|/bound 0.29–0.55) and χ² (p 0.043–0.99, ndf 13–18). Deterministic rerun relative difference 0 in all 4 settings | pass | `.simcal-work/gates/agreement-2.json` (worktree, untracked; SHA-256 `5d64845f…`), harness `tests/core/calibration_phase1_gates.py --gate agreement` |

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| §15.3.1 A0 (3.5% deviation, threshold 2%) | negative | caught: `a0.unreachable` | `preflight.A0.test_linearity_example`, `test_calib_scripts.Phase1Scripts.test_calib_contract_preflight` |
| §15.3.1 P0, declared Poisson with ENF in the implementation | negative | caught: `p0.kernel_inconsistent` on the light yield | `kernel_check.ToyDetector.test_declared_poisson_with_enf_in_the_implementation` |
| §15.3.1 P0, missing support U(θ, θ+1) | negative | caught: P0 failed, and `support.missing` | `kernel_check.MissingSupport`, `design.Support.test_single_support_is_missing` |
| §15.3.1 P2, insufficient observables | negative | caught: `p2.insufficient_ndf` | `design.P2.test_insufficient_observables` |
| §15.3.1 P5: q too narrow; interior point of a mixture; correlated weights; Poisson at μ = 1000 | negative | caught: `p5.ess`, `p5.ess` at an interior point, `p5.matrix_condition`; next tier chosen | `design.P5` |
| P5 items of approval A7 (D41 tail functional, D42 diagonal) | negative | caught: `p5.tail_functional`, `p5.v_mc_diagonal` | `design.P5.test_d41_tail_functional_refused`, `test_d42_diagonal_item` |
| §15.3.1 weight formula (w ≡ 1; S_θ∖S_q non-empty) | negative and positive | max \|w − 1\| = 0; agreement holds | `reweight.Formula.test_w_is_one_without_proposal_at_theta0`, `reweight.AgainstRerun.test_s_theta_minus_s_q_nonempty`, gate 2 case 5 |
| §15.2 reweighting and rerun of non-generator nodes agree | positive | passed | gate 2; `reweight.AgainstRerun` |
| §15.3.16, the cases without g4sim | positive | passed | `design.Applicability` |
| §15.1 toy detector and its variants | positive | passed | `tests.core.test_calibration_toy` |
| D37 (approval A7) | negative and positive | caught: `parameters.psi_not_negligible`; refused without the design | `preflight.D37` |
| Review regressions (F1–F15) | negative and positive | passed | `ReviewFixes` classes in `test_calibration_{kernel_check,design,toy}` and `linear`, `reweight`, `test_calib_scripts` |

Cases in later phases (card, gate-1 item 10): P5 b_J and Σ_boot (phase 2); P5 θ-noise (phase 3); P0 (k_B) on the synthetic ZDC fixture (phase 3); the other gates of §15.3.1 (phases 2–5).

## This phase's thresholds (§8.7)

| Row | Calibrated value or `provisional-thresholds` | Evidence |
| --- | --- | --- |
| line 2004: Bonferroni z of P0, P6 | P0 (phase-1 part): α = 0.01 confirmed. 3 false alarms of 1000 with correct kernels (rate 0.003, one-sided 95% upper limit 0.0077; registered rule ≤ 16 of 1000); the largest \|Δθ\|/bound over the 3 points of a repetition has median 0.50, 99% quantile 0.87. P6 part: phase 3 | Campaign `campaigns/phase1-p0-z-2/` (private ceph folder): pilot 7557584_0 and array 7557620 (100 jobs, all COMPLETED, ≤ 2 min 15 s and ≤ 337 MB, 2.9 core-hours; approved by the user, "Pilot, then full"), code from a `git archive` snapshot of `e940ef2e`, every item's file SHA-256 equal to `e940ef2e`; summary `calibration-1-summary.json` (SHA-256 `f8250cf1…`) |
| line 2010: smoothing model of A0 | Confirmed on the synthetic ZDC linearity example: 0.5% and 1.0% reachable, 3.5% and 5.0% unreachable at the 2% threshold. The summary holds names only | `preflight.A0.test_linearity_example` |

The other §8.7 values that phase-1 results use stay design values: f = 0.1 (phase 2) and the 0.1σ_tot^design term. Every P0 and P5 output carries `provisional-thresholds`, and σ_tot^design is computed without Σ_boot/w (phase 2). Report for the author's write-back into §8.7 (a new part of Appendix E): the observed P0 false-alarm rate and its upper limit, and the A0 confirmation.

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent under hep-review/1, aiming at tier R2, approved by the user ("Yes, one reviewer"). It read the phase-1 diff at `0f30cf3c` and Part B, and ran the unit tests and its own probes read-only. Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-1-review.md` (SHA-256 `38f9bfbfe4fda67142bc0923c8432decb28434d3dc39d9b0a9e2fbaf03037caf`).
- **Findings:** 1 major, 11 minor, 3 notes.
  - **F1 (major):** the P0 rerun reference was taken at the generation point, not at θ′, when a resimulated parameter's prior centre differs from it. This did not affect the registered gates, whose prior centres equal the nominal values.
  - **Minor:** F2 ω counting in P2. F3 the power of gate-2 criterion (ii). F4 shared streams between calibration-1 repetitions. F5 P5 without the final method. F6 silent missing support. F7 filtering ignorable without the plan's decision. F8 `seeds` and `effects_off` ignored. F9 ψ accepted without the design. F10 tracebacks, and an unrecorded A0 read on error. F11 default P0 points with rerun only. F12 the P5 scan limited to reweighted parameters.
  - **Notes:** F13 support and weight-set logic in the evaluator. F14 projected-inverse standardization and coordinates. F15 smaller items.
- **Resolution:** all fixed in `4e67af4e`, each with a regression test; none changes Part B (details in the card's execution log). From F15, `sc/` in the guide is kept: it is the shorthand SKILL.md defines, and the two load together. The gate-2 design change (paired covariance, a tightening) and the electronics plan's recorded filtering were registered (`ca717b11…`) before gate 2 and calibration 1 were repeated. The first gate-2 run (`485eaf9b`, passed) and calibration-1 campaign 1 (2 false alarms of 1000) are superseded.
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- `tools/check_layering.py`, `tools/check_wiring.py`, `tools/check_packaging.py`, `tools/check_naming.py`: pass.
- `tools/run_all_checks.py --jobs 4 --no-cli` at CHECKS_COMMIT: CHECKS_RESULT.
- `contracts/validate.py`: phase 1 writes no `artifacts_dir` artifact. Its fixture, contract, plan and release are checked against their schemas by `test_calibration_schemas`.

## Open items carried to the next phase

- **Phase 2:**
  - Σ_boot and b_J of P5; the joint likelihood with link functions beyond identity and log, and non-Gaussian blocks at the design stage;
  - P3 and P7; the non-overlap of event intervals and the toy constructions of §6.6;
  - G4 (Pareto k, `node_diag` per node);
  - the calibration of f.
- **Phase 3:** P6 itself and the surrogate model; the P6 part of the §8.7 Bonferroni row; the θ-noise item of P5; the g4sim evaluator, with the support and weight queries `support_query` and `logpdf` that `design.support_check` and `reweight.formula_log_weights` expect; the k_B spot checks.
- **For the author** (not blocking):
  - resimulation as a candidate method for a samplable density kernel (an extension of the §3.6 table);
  - the A0 confidence level (default α = 0.05);
  - the d_free reading of P2 (constrained nuisances excluded);
  - s_k² as the limit of the bootstrap;
  - the write-back of the §8.7 results above.
- **For the maintainer:**
  - the guide trims in `core-stats-guide.md` (the user's choices);
  - the local timings of the six new test modules;
  - the earlier phase-0 items (naming waivers of the copied package tools).

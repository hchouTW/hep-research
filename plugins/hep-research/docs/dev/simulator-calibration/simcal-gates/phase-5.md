# Simulator calibration gate record: phase 5

**Phase 5 (Extensions): every gate item passes** (gate run 3, one clean commit `20b31a1b`).
- **The corresponding negative tests pass:** G4L 20 tests, POOLING 27, VMODEL_INFERRED 10; each negative caught and its positive control passing.
- **The gates of the first four phases are not changed:** no phase-0–4 gate file, card or gate record changed since the phase base `c7e5a610`, and the registry's phase-0–4 entries are byte-identical; all ten phase-0–4 gate items pass again at the phase-5 code, each by its own registered rule.
- **The extensions change nothing when unused:** 55 golden cases byte-identical (50 from phases 0–4, 5 over the default-off branches phase 5 modified).
- **Studies:** S1 passed (G4-L false alarms 9 of 1000); S2 reported; S3 **failed** on configuration "two" (accepted as prior shrinkage, A30); S4 failed at its first registration (0.010) and **passed** at its second (0.0502; A29–A31).
- **Review:** one independent reviewer (13 findings, all minor or notes); the implementation and test findings fixed (A33), the rest disclosed below.
- No §8.7 row belongs to phase 5. G4-L keeps `provisional-thresholds` (review F2); every result is `synthetic`.

| Field | Value |
| --- | --- |
| Phase | 5 (Extensions) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-5` (private ceph folder) |
| Branch | `simcal/phase-5`, from `origin/main` `c7e5a610` (release 0.67.0, phases 0–4 merged); release 0.68.0 (`c76a5e06`) merged in at `bd4bca87` |
| Commit | Gate run 3 at `20b31a1b` from the clean worktree `tmp/wt-p5-gates-3` (`campaigns/p5-gates-3/gate.json`, SHA-256 `12d804bd…`; not dirty); later commits change this record, the card, the status, the changelog and the harness's own unit test (two skip guards; disclosed below) only; then the merge of release 0.68.0 (`bd4bca87`) and the Geant4 adapter bump to 0.17.1 (`3754681d`), confirmed below ("After the 0.68.0 merge") |
| Task-card SHA-256 (as registered) | the last phase-5 registration in `simcal-task-registry.json` (`f73fe69f…`, gate run 3, before its run) |
| Environment | Login host, Python 3.13.2 (conda env `ml`), NumPy 2.2.2, SciPy 1.16.1 for items 1, 2, 4 and the phase-4 rerun; Slurm `edr1-al9_short_serial`, account `ams`, node interpreter Python 3.13.18 / NumPy 2.4.6 for the phase 0–3 reruns and the studies; one BLAS thread |
| hep-research and g4sim versions | hep-research 0.68.0 plus this branch (gate run 3: 0.67.0 plus this branch); g4sim stages S0–S9 merged; `adapters/geant4` 0.17.1 |
| Approvals | A25–A33 (`simcal-approvals.md`) |
| Date | 2026-11-14 (the 0.68.0 confirmation: 2026-11-15) |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| The corresponding negative tests pass | `UNIT_RULE`: every listed test passes; any skip, failure or error fails | G4L 20, POOLING 27, VMODEL_INFERRED 10 (none not run) | pass | `gate.json`, item `negatives` |
| the gates of the first four phases are not changed (static) | no phase-0–4 gate file, card or record in `git diff c7e5a610..20b31a1b`; registry entries byte-identical | none changed | pass | item `prior_gates_static` |
| the gates of the first four phases are not changed (rerun) | each earlier item passes by its own registered rule at the gate commit | 10 of 10 (p0 Appendix C, p0 named, p0 fixtures, p1 gates 1 and 2, p2 gates 1, 2 and 3, p3 part E, p4) | pass | item `prior_gates_rerun`; `rerun/rerun-merged.json`; arrays 7655877–7655883 |
| (supporting) default-off identity | byte-identical outputs on the golden cases | 55 of 55 | pass | item `default_off_identity` |

Earlier gate runs are kept as records, not evidence: gate run 1 at `429caf0f` passed (`campaigns/p5-gates/gate.json`, `f793576e…`), superseded by A29–A31 (changes to `learned.py`, `toy.py`); gate run 2 at `9b37677b` passed (`campaigns/p5-gates-2/gate.json`, `b2ebbe22…`), superseded by the review fixes (A33). The registry entry of gate run 2 names `card_commit` `a7306cd1`; the card SHA it records (`d21ced70`) is the card as committed at `9b37677b` (review F9).

## What phase 5 delivers

- **Partial pooling** (§3, §15.3.18; A25 (6), A26 (1)): `core/calibration/pooling.py`, `calib_fit.py pool`. Random effects non-centred in link space, REML on the model linearized at the joint point, τ̂ plugged in; P2 "covers 0" as q(0) ≤ χ²₁(0.90); the pooled grade and gates (WP-Q2); output flagged `partial-pooling` (informational).
- **Learned density ratio and G4-L** (§6.2, §15.3.1, §15.3.16; A25 (1)–(4), A27, A29, A31, A33): `core/calibration/learned.py`. L2 logistic regression on degree-4 monomials × θ terms, Platt calibration, F = 5 cross-fitting, R = 5 replicas; G4-L at P0's θ′ points on the held-out closure; V_learn (training repeats plus bias) in V_G and in the validation C_r; V_learn^bias by the θ0 control variate minus its MC-noise covariance, clipped (A29); each fold's log ratio clipped to its training range (A31); σ_tot^design includes V_learn at θ_ref (A33); the A25 (1) classifier/SBI boundary refused.
- **Inferred V_model** (§5.4 V6; A25 (7), A26 (2)): `core/calibration/vmodel_infer.py`. The restricted marginal likelihood over ν with η and φ_P marginalized; the Jeffreys measure times a Half-Normal(f) weight within declared bounds; marginal posterior medians with nested-Laplace quantile intervals; a separate `vmodel-version` record linked by hash; holdout only.

## Studies

| Study | Registration | Result | Evidence |
| --- | --- | --- | --- |
| S1 G4-L false-alarm rate | 1000 repetitions, ≤ 16 false alarms | **pass**: 9 of 1000 (at `429caf0f`, before A29/A31/A33) | `campaigns/p5-studies/g4l/merged.json` |
| S2 partial-pooling frequency | reported | τ̂ = 0 in 0.600; cover 0.975; ±σ_tot coverage θ_s 0.697, θ̄ 0.737, common 0.678 (0.683 nominal) | `pooling_s2/merged.json` |
| S3 inferred-V_model recovery | per hyperparameter \|mean pull\| ≤ 0.1, sd in [0.9, 1.1] | **fail** on configuration "two" component 1 (f1 +0.216 / 0.840; ℓ1 sd 0.878); "one" and component 0 pass | `vmodel_s3/merged.json` |
| S4 learned-path T_v size, first registration (A28) | rate at α = 0.05 within α ± 25% | **fail**: 0.010 | `tv/merged.json` |
| S4 pilot (A30/A31) | report-only, four soundness flags | all sound (reference non-converged 0.010, q95 5.70, repetitions non-converged 0.025, median T 1.32) | `tv-pilot/merged.json` |
| S4 second registration (A29–A31) | as the first | **pass**: 0.0502 (no-learned-toys 0.061; without V_learn in C_r 0.064; χ²_k 0.036) | `tv-2/merged.json` (`8c252273…`) |

## Disclosures

- **S3 (A30):** no defect; the engine's quantiles agree with a 4-D Metropolis run. The miss is prior shrinkage of a weakly identified component by the Jeffreys measure (response slope 0.76; f1 68%/95% coverage 0.766/0.970). It is conservative only at the registered truth: a truth scan under-covers at f1 = 0.08 (review F7). The prior form (Jeffreys measure × Half-Normal, posterior median) goes to the author. The S3 draws use `eigh` and reproduce only in their recording environment; later registrations use a Cholesky factor.
- **S4 (A29–A31, review F1):** the second-registration rate is over the 1892 converged repetitions; counting the 108 non-converged as not rejected gives 0.0475 (still in the band); it would fail only if all 108 rejected. The reviewer reran 40 of them with the same seeds: none rejects. The non-convergence (5.4%, all the ln det diagnostic) is above the pilot's 5% soundness flag, and reference toys (V̂ frozen) almost never fail it; the learned-path ln det failure rate goes to the author. The first registration's docstring was aligned with the code after its result (the registered text says only "reported"). The A30 feature clamp was tried and reverted (it made the tails worse). Heavy-tailed classifier fits (≈ 1 in 30) remain; the per-fold logit clip does not fire on them.
- **G4-L thresholds (review F2):** S1 calibrated the classifier at `429caf0f`; the code at the gate commit adds A29, A31 and A33. G4-L keeps `provisional-thresholds` until S1 is rerun at the release code.
- **V_learn^bias (review F6):** the clipped subtraction removes only part of the noise (about 1/k of tr N at δ = 0), so V_learn^bias stays conservatively inflated; A25 (2) tests the scale only.
- **G4-L no-cross-fitting (review F4):** the §15.3.1 negative is caught by the record (index sets), not statistically: the held-out closure cannot see in-fold application; a test shows F = 1 passes every closure point.
- **Default-off coverage (review F3):** the 5 added cases cover the modified default-off branches; the inferred-version and learned branches have no base API and are not covered by item 4.
- **Fixture (review F12):** the post-hoc fixture's true log ratio lies in the classifier family; no misspecified-classifier negative exists. V6 test (d) is weak (coverage ≥ 80% of 24 draws); S3 carries the coverage claim.
- **Provenance (review F10):** the merged study files' `provenance` is the merging process's environment (3.13.2 / 2.2.2); the tasks ran with Python 3.13.18 / NumPy 2.4.6. Merges after A33 record `task_environment`; existing merged files are not rewritten.
- **Toy bias draws (review F13):** `learned_bias_draw` uses `eigh`; toy realizations (not their distribution) depend on the LAPACK build.
- **Post-gate test change:** after gate run 3, `tests/core/test_calibration_phase5_gates.py` (the harness's own unit test, in no gate list) gained two skip guards so that its two repository-bound tests skip in a relocated copy (`check_ams_optional.py`) and in a shallow CI checkout without the phase base; in the repository both still run and pass. The harness, the gate lists and every gated test are unchanged, so gate run 3 stands; commit `60a41664`.
- **Phase 2 gate 2** needs ≈ 35 GB (it also does at the base `c7e5a610`); it ran at 40 GB.

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent (under the user's "auto continue with your recommendation", as in phase 4). Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-5-review.md` (on gate run 2, `9b37677b`).
- **Verdicts:** negatives G4L and VMODEL_INFERRED supported with reservations, POOLING supported; static supported; rerun supported with minor reservations; default-off identity supported as a regression check, weak as evidence of default-off (fixed, F3).
- **Findings and resolution (A33):** F3, F4, F5, F8, F10, F11, F13 (second half) fixed with tests (WP-V, `a5a763cf`; four new negatives in the G4L list); F1, F2, F6, F7, F9, F12, F13 (first half) disclosed above.
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- At `9b37677b` (gate run 2, `campaigns/p5-checks/`): apart from module timeouts under login load (four rerun at low load: pass), `test_executor_b2` ×3 (it fails the same way at the phase base `c7e5a610`: environmental) and the three environment-only failures of phase 0.
- At `20b31a1b` (the gate commit; `campaigns/p5-checks-3/check-run-2026-11-14T211843Z.json`): 7,889 tests in 588 modules, 7,582 passed, 302 skipped, 5 failed, 8 modules timed out (600 s) and `ams_optional` timed out (1,200 s), at a login load of ≈ 17. Rerun at low load (`campaigns/p5-checks-3/rerun/`): the 8 timed-out modules (249 tests) and the two timing failures (`test_workflow_b1` termination; `test_hep_detector_audit` f04, `build_response.py` over its 10 s limit) pass; `ams_optional` (the generic suites in a copy without the AMS-02 profile and without git) failed, in the copy only, on two phase-5 harness self-tests that read the repository (`test_calibration_phase5_gates` `Static.test_static_item_at_this_commit` and `test_protected_paths_are_repository_relative`), and otherwise only on the environment-only failures; those two tests now skip outside a repository checkout that holds the phase base (see the disclosure on the post-gate commit). The remaining three are the environment-only failures (`test_revocation` ×2, `test_export_bundle_check`; they also fail on a clean `origin/main`). Every other check passes, including the 15 profile suites, naming and plugin validation.
- The commit gate (every calibration test module, the script tests, layering, naming, packaging, wiring, the reference inventory, the routing and soft budgets, CLI fuzz, the guide, the skill-script list), ruff and mypy passed on every phase-5 commit.

## After the 0.68.0 merge (2026-11-15)

Release 0.68.0 (`c76a5e06`) was merged into this branch at `bd4bca87` (A32: push, PR, merge and release only after 0.68.0; the user: update this task to the new plugin version). Conflicts were mechanical: the CHANGELOG (the released section kept, the phase-5 lines under Unreleased), the reference inventory (regenerated) and `tools/module_timings.json` (the release's values kept, the three phase-5 modules added). From the phase base `c7e5a610` to `c76a5e06`, nothing changed under `core/`, `skills/hep-statistics/`, `tests/core/` or `docs/dev/simulator-calibration/`. `3754681d` bumps `adapters/geant4` to 0.17.1 for `6fceb436` (`docs/adapter-authoring.md`); `test_geant4` and `test_geant4_register`: 81 run, OK (7 skipped, live Geant4).

Confirmation at `3754681d` (clean worktree `tmp/wt-p5-ci`, not dirty; records in `campaigns/p5-confirm-0680/` and `campaigns/p5-ci-local-2/`):
- **Gate items 1, 2 and 4 pass again** (`gate.json`, SHA-256 `5a86aad1…`; login host, 469 s): `negatives` (G4L, POOLING, VMODEL_INFERRED), `prior_gates_static` (the diff from `c7e5a610` now includes the release, still no phase-0–4 gate file, card or record), `default_off_identity` (55 of 55 byte-identical). **Item 3 was not rerun** (the run reports it `not-run`): the release touches no calibration code, card or gate record, so its result at `20b31a1b` stands; a rerun is ≈ 45 core-hours. This is the coordinator's choice under the user's "auto continue with your recommendation"; the gate's verdict remains gate run 3.
- **Lint:** ruff (`check core contracts`) and mypy (193 files) pass; shellcheck on CI's three scripts passes.
- **`run_all_checks`** (login host, `--jobs 4`): 10,678 tests in 655 modules, 10,238 passed, 434 skipped, 6 failed, 2 modules timed out (600 s), `ams_optional` timed out (1,200 s). The two timed-out modules (`test_calibration_evaluator_problem`, `test_design_search_j16`) pass when rerun (18 run, OK). The failures are environmental: revocation ×2 and `export_bundle` (as at `20b31a1b`), and three photon-likelihood tests (`test_photon_likelihood_time` vertex edge; the offline replay of `examples/reconstruction-photon-likelihood` ×2) that fail identically at the release `c76a5e06` on this host (`photon-at-0680.log`): they are the release's, not this branch's.
- **CI jobs on Slurm** (`p5-ci-local-2/SUMMARY.md`): optional-python, all five extras 0 failures (torch-cpu after one rerun: its two-process `torchrun` smoke test timed out once at 300 s on the node); hostile-paths, only environmental failures (600 s module timeouts on ceph, revocation ×2, the 1 s lease test `test_takeover_only_when_expired_and_after_reconciliation` racing on ceph, `test_executor_b2` G2 on a node, which passes on the login host; `ams_optional` past 1,200 s); the packaging scan flags exactly the planted files. The Geant4 failure of the previous local run is gone on a node without cmake.

**PR #416 CI (2026-11-15):** the units shard 1/4 and hostile-paths units 1/4 failed only on two module timeouts (600 s on GitHub's runners): `tests.core.test_calibration_vmodel_infer` (144 s locally) and `tests.skills.hep_statistics.test_cli_input_fuzz` (446 s locally, longer with the phase-5 subcommands). Fix (test layout only; no engine, script or gate-listed test changed): the fuzz is split into three modules by script (`test_cli_input_fuzz.py`, `_calib_a.py`, `_calib_b.py`; 97, 90 and 81 s locally), and two `vmodel_infer` tests that no gate list names (`Intervals.test_weak_component_laplace_undercovers_quantile_interval_covers`, `StudyS3.test_local_smoke`) move to the slow tier (`HEP_SLOW_TESTS=1`), where both pass. Gate item 1's lists and their outcomes are unchanged.

## Open items carried forward

- **For the author:** A25–A33 (Part B write-back); the S3 prior form for weak components (F7); the learned-path ln det non-convergence and the S4 denominator (F1); the classifier configuration (heavy-tailed fits); §7.3's counting of non-converged reference toys; an S1 rerun at the release code to lift G4-L's `provisional-thresholds`; the T2 margin and power condition (phase 4).
- **Not wired:** pooled §10.4 propagation; `calib_*` subcommands for the pooled gates; the g4sim use-matrix enforcement (upstream).
- **Upload route:** issue #409 (the plugin upload zip exceeds 5,000 files).

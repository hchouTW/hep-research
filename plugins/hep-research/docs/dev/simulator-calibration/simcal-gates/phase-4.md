# Simulator calibration gate record: phase 4

**Phase 4 (Dependency graph and specialization): every gate item passes** (gate run 3, one clean commit `4f668d3a`).
- **Negative tests of the contribution decomposition (§15.3.18):** 15 tests pass; the 7 negatives (a subset below G4's ESS threshold in three forms, the sampling path, the object declaration, effect declarations, an evaluator that cannot remove effects) are caught and their positive controls pass.
- **Negative tests of the g4sim binding (§15.3.19) and the A21 cases:** all 19 cases pass (85 tests): every §15.3.19 bullet, including "scintillation `log_density` switched to the normal density → P0 fails" on the Poisson-interval light-yield reweighting (A24), plus the T2 carry-over, upstream invalidation and the discrete run-card fields.
- **Specialization does not require modifying the generic layer:** the eight node-binding examples (ECAL, HCAL, RICH, DIRC, TRD, Tracker, TOF, μ detector) pass the unchanged contract checker, P4 and candidate derivation, and no commit since the phase base that touches the specialization documents touches `core/`, `contracts/schemas/` or the calibration scripts.
- **Review:** one independent reviewer (1 major, 5 minor, 6 notes); all fixed or disclosed below.
- No §8.7 row belongs to phase 4; the T2 margin and power condition of A21/A24 are `provisional-thresholds`.

| Field | Value |
| --- | --- |
| Phase | 4 (Dependency graph and specialization) |
| Worktree | `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/hep-research-simcal-phase-4` (private ceph folder) |
| Branch | `simcal/phase-4`, from `origin/main` 307a364d (phases 0–3 merged) |
| Commit | Gate run 3 at `4f668d3a` from the clean worktree `tmp/wt-p4-gates-3` (`campaigns/p4-gates/gate-3.json`, SHA-256 `b478c62d…`; not dirty); later commits change this record, the card and the changelog only |
| Task-card SHA-256 (as registered) | the last phase-4 registration in `simcal-task-registry.json` (`f9b17983…`, gate run 3, before its run) |
| Environment | Login host, Python 3.13.2 (conda env `ml`), one BLAS thread, `TMPDIR` on the private ceph folder; no Slurm (the gate runs unit tests and fixtures, about 1.5 minutes) |
| hep-research and g4sim versions | hep-research 0.66.1 plus phases 0–3 (main 307a364d) and this branch; g4sim stages S0–S9 merged |
| Approvals | A21 (the five phase-4 author items), A22, A23, A24 (`simcal-approvals.md`) |
| Date | 2026-11-14 |

| Gate (§17, split at semicolons) | Threshold as registered | Observed | Verdict | Evidence |
| --- | --- | --- | --- | --- |
| Negative tests of the contribution decomposition (§15.3) | `UNIT_RULE`: every listed test passes; any skip, failure or error fails | 15 of 15 (7 negatives caught, 8 positives) | pass | `gate-3.json`, item `contrib_negatives` |
| Negative tests of the g4sim binding (§15.3) | every case's tests pass (`CASES`, 19 cases) | 19 of 19 cases, 85 tests | pass | item `g4sim_binding` |
| specialization does not require modifying the generic layer | the specialization tests pass; every specialization commit since 307a364d touches no generic-layer file | 11 tests pass; commits e661b3fd (31 files) and 9cf8a372 (4 files), no generic-layer file | pass | item `generic_layer` |

Earlier gate runs are kept as records, not evidence: gate run 1 at `4ef75ef7` passed (`gate.json`, `4f0c13f8…`), superseded by the review and A24; gate run 2 at `2d4a142f` failed on a harness defect (the specialization pathspec read relative to the plugin folder found no commit; `gate-2.json`, `bd301442…`).

## What phase 4 delivers

- **§10.3 upstream invalidation and simulation identity** (`deps.invalidate`, `upstream_change`, `identity_decision`; `calib_deps.py invalidate`, `identity`): a revised or downgraded upstream marks downstreams for a redo (transitively); a same-κ re-judgment does not; a changed masked identity item (`build_hash`, Geant4 and data-set versions, geometry/material, response stage, efficiency map) marks the result for a redo unless a T2 record passes.
- **T2 carry-over (A21 §19-g7 as amended by A24):** the old→new shift of the calibration observables at θ̂ and the §5.4 spot points, propagated through the result's design-stage A_θ, must be shown within ±0.1σ_tot,i per θ_i by TOST (α = 0.05), with the pre-registered power condition se(δθ_i) ≤ 0.025σ_tot,i and an MC size at least the result's own; the basis comes from the result's hash-bound `t2_basis`; a passing result is flagged `identity-carried-over` (informational, A22) and `provisional-thresholds`.
- **§10.4 export and feedback into g4sim** (`propagate.export_g4sim`, `calib_propagate.py g4sim`): θ̂ written into `condition-snapshot/1` or `alignment-overlay/1` with the result's hash, grade, flags and stated use in `source_of_facts`; a use the result does not allow is refused. **`calib_use.py export`** re-checks a record (hash recomputed, grade, use matrix, declared parameters, written values). **Forced joint fits** are reported; ξ has no versions (A21 §19-g8).
- **§10.5 `calib_contrib`** (`contrib.decompose`): Shapley terms with `effects_off` (toy and g4sim evaluators), all subsets for n ≤ 10, sampled orderings above, every evaluated subset at G4's ESS threshold or no output, bootstrap covariances (calibrated over 20 seeds), the object (variance or resolution) declared.
- **Eight specialization documents** (`skills/hep-detector/references/simulation-calibration/`) with §11.1 items 1–8 and node-binding examples; the calibration domain card (`skills/hep-review/references/domains/detector.md`).
- **Section 11.4 Table 2, LY by analytic reweighting in the Poisson interval** (`g4sim_calib_eval`): photon-count weights per bin, refused above 10 photons; P0's reference re-digitizes LY.
- **Binding fix:** `/physics/pai`, `/physics/xtr`, `/physics/optical`, `/physics/decay` are discrete run-card fields, refused as θ (685683ab; it touches no specialization file, disclosed under review F2).

## This phase's tests

| Test (§15) | Kind | Caught / passed | Evidence |
| --- | --- | --- | --- |
| §15.3.17 Propagation and use (every case audited; new: single-η segmented = joint with its prior counterexample, the union of central grade-limiting flags, export rejections, forced joint fits) | negative + positive | caught | `test_calibration_propagate`, `_deps`, `_use`, `_export` |
| §15.3.18 contribution decomposition | negative + positive | caught | gate item `contrib_negatives` |
| §15.3.19 g4sim binding (19 cases incl. the A21 cases) | negative + positive | caught | gate item `g4sim_binding` |
| §12 sufficiency (eight types through the generic layer) | positive + 7 negatives | caught; no generic change needed | `test_calibration_specialization` |

## Disclosures

- **Normal-density P0 case (A23 → A24):** first recorded as not reproducible (A23); reconsidered: it lives on the Poisson-interval LY reweighting, which was then implemented; a defect in P0's g4sim reference (it evaluated with the method under test, so the reweighting was compared with itself) was found and fixed; on a low-light synthetic ZDC setup the normal density fails P0 and the Poisson density passes (3000 and 10000 events, `pe_std` alone and with `pe_mean`). On the toy detector P0 still cannot see the swap inside its narrow prior (large photon counts; `NormalDensityRecord`).
- **T2 (A21 → A24):** as first decided, the TOST at the result's own MC size could never pass; now θ-space with a power condition.
- **Joint P6 reference power (phase 3, carried):** 2× the covariance on strongly correlated points is caught in ≈ 33%.
- **Review F10:** `calib_contrib.py` (a core script) cannot import the Geant4 adapter (layering): g4sim plans run through the adapter's Python API.
- **Review F11:** every item-7 cell reads "no literature value"; the INSPIRE-HEP/arXiv search record (index.md) is metadata only.
- **Overlay export (review F8):** the binding refuses an overlay misalignment without a recorded run (D83 (7)), so the overlay export path is exercised on a test contract until that is resolved upstream.

## Review (Section E4, step 10)

- **Reviewer:** one fresh-context subagent, approved by the user (A23 record). Report: `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/review/phase-4-review.md` (on gate run 1, `4ef75ef7`).
- **Verdicts:** contribution decomposition supported (minor reservations); g4sim binding supported with reservations; generic layer supported with reservations.
- **Findings and resolution:** F1 major (the T2 check trusted its inputs) — fixed with A24 (basis from the result, σ and A_θ from its design stage); F2 (generic check looked at one commit) — fixed (every specialization commit); F3 (export value check trusted the record's map) — fixed; F4 (stale binding text) — fixed; F5 (exit code) — fixed; F6 (untested alternative-hypothesis branch) — test added; F7 (bootstrap covariance) — calibration test added; F8 (export wrote disallowed uses) — fixed; F9 (harness self-test) — every mapped test now loads; F10, F11 — disclosed; F12 (invalidation bookkeeping) — fixed.
- The achieved review tier is stated by the coordinator of the record, not by this gate record.

## Repository checks (E4 step 7)

- At `4ef75ef7` (`campaigns/p4-checks/`): 7,932 tests, 7,622 passed, 306 skipped, 4 failed — the three environment-only failures of phase 0 (`test_revocation` ×2, `test_export_bundle_check`) and `test_check_wiring` (the hep-statistics README script count), fixed; `check_wiring` added to the commit gate.
- At `4f668d3a` (the gate commit; `campaigns/p4-checks-2/check-run-2026-11-14T030139Z.json`): 7,942 tests in 584 modules, 7,633 passed, 306 skipped, 3 failed — only the three environment-only failures (they also fail on a clean `origin/main`); every other check passes, including wiring.
- The commit gate (every calibration test module, the script tests, layering, naming, packaging, wiring, the reference inventory, the routing and soft budgets, CLI fuzz, the guide, the skill-script list), ruff and mypy passed on every phase-4 commit.

## Open items carried to the next phase

- **For the author:** A21–A24 (Part B write-back); the T2 margin and power condition (provisional; a calibration is proposed: false-redo rate and power on toy or ZDC pairs, about 1–5 core-hours); the overlay misalignment without a recorded run (D83 (7)); the g4sim binding limits found by WP-P (no Table 2 row for charge-sharing and drift-table parameters, a gas-avalanche stage, TTS / effective light speed / emission time, SiPM saturation, the TR yield factor); the g4sim use-matrix enforcement (raised upstream, A21 §19-g6).
- **Phase 5:** the draft decision sheet and card in the private folder `/ceph/work/AMS/hsinyichou/hep-research-simcal-private/phase-5-prep/`: §19-9 second half (classifier vs SBI), §19-15, §19-12, §19-14, §19-g8 reconsidered; Part B gaps P1 (partial pooling unspecified) and V6 (no negative test named for the inferred V_model).

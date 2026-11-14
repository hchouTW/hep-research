# T07 close-out against its sheet (D1 stage 11)

T07 is tracking and vertexing (BP03, BP04). Its sheet is in `t07-t09-task-sheets.md`. Paths are relative to `plugins/hep-research/`. Job
evidence is in `<private>/evidence/t07-stage<N>-<job>/`, and the job IDs are the ones `decisions.md` and the ledger record.

**Scope of this file.** One row per item of the sheet, with its status and evidence. Anything not met says why, and what would close it.

**Not judged here.** The quality verdict (pass or fail against `t04-values-v4.md` and `t04-prereg.md`) waits for K09 at Freeze B (finish-plan
D4). Nothing here pre-judges it. Every number these jobs printed on block 1 is a development reading, not a gate.

**Status words.**
- `met`: the evidence shows the item as the sheet states it.
- `met with readings`: met, with a limit or a departure stated beside it.
- `open`: work, or a decision, is still owed.
- `gap`: the backend cannot provide it, on a recorded probe (R37).

**Evidence job.** Job 7548207 (adapter 0.1.0; the adapter's 0.2.0 job of record is the D1 stage 11 job) (stage 10, hpa-wn34, PASS in 19 min 03 s) reran every step of the earlier stages. Unless a row names another
job, its evidence is that job's step log, `<step>.log`. Rows that depend on the stage 11 job say so. That job has not run when this file is
written.

## Summary

The sheet table and the scenario table have 37 rows. The scenario-pointer row has no status of its own, which leaves 36.

| Status | Rows |
| --- | --- |
| met | 18 (17 sheet items; A05) |
| met with readings | 12 (9 sheet items; A07, A17, A39) |
| open | 4 (failing-first for stages 1 to 7 and 10, quality, material; A01) |
| gap | 2 (R33 cluster size and charge; R33 trajectory with scattering parameters) |

Each row that is not met, in one line:

- `examples/reconstruction-tracking/` (open): written; it needs the stage 11 job's step `example`, and its recording copied into the
  folder.
- Quality pass or fail (open): by the sheet, after K09 at Freeze B.
- Material effects (open): by the sheet, after the first pass; no owner in `coverage.md`.
- A01 (open): by the sheet, it needs a second backend; T15b, if `simreco` qualifies.
- A05 (open): the test is written and its judges pass without a build; it needs the stage 11 job's step `scenarios`.
- Failing check first, stages 1 to 7 and 10 (open): their reports record no red run before the change; it needs a reading of their logs or the
  user's waiver.
- R33 cluster size and charge per measurement (gap): a recorded probe; it needs a fixture with clusters.
- R33 trajectory with scattering parameters (gap): a recorded probe; it needs material and a new fit or trajectory model.

Every row marked met with readings states its reading in its last column.

Also open, though no sheet row carries it:

- The `coverage.md` obligations for T07: particle type, timing, displaced vertices, near vertices (T07 later pass, or the user).
- The six user items in `STATE.md`: F1, m6, n6, the Freeze B vertex values, the D2 departure, the K04 schema limit.
- R34's two rows naming T07 in `calibration-alignment-interfaces.md`: raw quantities kept beside calibrated values, and the chain
  order of applied payloads. Both are still `Designed`, with no T07 check.

## Sheet items

| Sheet item | Status | Evidence | If not met: why, and what closes it |
| --- | --- | --- | --- |
| Objective: finding, ambiguity resolution, fitting and vertexing run on measurements through a native driver, with evidence per stage | met | Driver `acts_tracking_driver` (refit), finder `acts_tracking_finder` (seeds, CKF, ambiguity resolution, fit, optional AMVF), each stage with its own job: refit 7493368, finding 7502411, truth-seeded comparator 7515600, vertexing 7524096, R33 outputs 7537235 and 7546791, wrapper 7548207. All rerun in 7548207 | |
| Scope: planar telescope, uniform field, F01-like silicon, event data | met | `native/telescope_geometry.*` (frozen, `freeze-a.md`; `frozen-unchanged.log` 31 files unchanged); the field is 0 or the fixture's 1 T (`BuiltDriver.test_only_the_fixture_field_opens`); 0.020 mm hits | |
| Non-goals: barrel, GSF, GPU, constants (R31), quality claim | met | None is built. The CAI-T07-3 payload is labelled "synthetic CAI-T07-3 fixture: the generated shift, no measurement" (`calibration-alignment-interfaces.md`). `adapter.json` and `VALIDATION.md` claim no quality | |
| Files, confirmed: the ACTS environment; `docs/adapter-authoring.md` | met | ACTS 48.2.0, `PASS ACTS is 48.2.0` in `self-test.log` of 7548207. Adapter record per the doc in this stage: version 0.2.0, status, `tested_versions`, `VALIDATION.md` ACTS-TRACKING-T07, matrix row | |
| Files, proposed: `adapters/acts-tracking/` with C++ driver, fixture generator, thin wrapper, tool contract | met | `adapter.json` assets; `contracts/tool_contracts/acts_tracking.json`; `WrapperForwardsAndReports`, `WrapperCarriesTheStageEightAndNineInterfaces` (`adapter-tests.log`); `WrapperRefitRun` (`cai-refit.log`), `WrapperFindRun` (`finding-r33.log`): the wrapper's products equal the programs' bytes | |
| Files, proposed: `examples/reconstruction-tracking/` | met | `examples/reconstruction-tracking/run.py`: generate, find and refit 2 events of clean stratum 0, block 1, through the wrapper; offline replay with 10 checks; `tests/examples/test_reconstruction_tracking.py`. On login the test fails, as it must until the recording exists (D1 stage 11 report) | The stage 11 job's step `example` passes (two live runs byte-equal, then the test module against them). The coordinator copies `<job>/example/recorded` and `output` into the example folder; the test then passes offline. The recording comes from the cluster, not E2, where ACTS is not installed (`docs/maintenance.md` row) Job 7551619: example steps PASS, recording equal in two live runs, host-path grep empty; recording copied into the folder after the job (coordinator). |
| ACTS interfaces named in the sheet | met with readings | Every named header is included, except as read below: `CuboidVolumeBuilder.hpp` (the sheet allows it or Blueprint), `ConstantBField`, `EigenStepper`, `Navigator`, `Propagator`, `EstimateTrackParamsFromSeed`, `CombinatorialKalmanFilter`, `MeasurementSelector`, `KalmanFitter`, `GainMatrixUpdater`, `GainMatrixSmoother`, `GreedyAmbiguityResolution`, `AdaptiveMultiVertexFinder`, `HelicalTrackLinearizer`, `VectorTrackContainer`, `VectorMultiTrajectory`, `Surface::alignmentToBoundDerivative` (`finder-links.log`: "PASS the driver reaches Acts::Surface::alignmentToBoundDerivative") | `FullBilloirVertexFitter` is not used: the installed AMVF header fixes `AdaptiveMultiVertexFitter` (user item F1). `TrackSelector.hpp` is not used; the finder selects in its own code. `TrackProxy` comes through `TrackContainer.hpp`. `alignmentToPathDerivative` is not called directly. The sheet's correction is the user's |
| Input: synthetic hits from known parameters through the same geometry, Gaussian smearing, injected noise; truth in a separate file with role `truth`; the data side never opens it | met | Generators frozen at the Freeze A addendum (job 7492427), unchanged (`golden-diff.log` 32 GOLDEN lines). `DataFileHoldsNoTruth`, `DataSideNeverOpensTruth`, `DataSidePythonImportsNoGeneratorCode`, `HitBitsSayNothing` (`adapter-tests.log`); `FinderStaysTruthFree`, `NegativeCases.test_truth_reaches_the_finder_by_no_input` (`finding.log`); `FinderRefusesTruth` (`truth-seeded.log`); `finder-links.log` 25 PASS, none FAIL | |
| Output: per-surface states, predicted, filtered and smoothed kept apart | met | `StatesStayApart`, `DevelopmentRun.test_products_keep_their_states_apart_and_say_finding` (`finding.log`); `ReconstructionProductMap.test_predicted_filtered_and_smoothed_stay_apart`; `StraightLineCase.test_the_three_state_types_differ_where_the_hits_say_they_must` | |
| Output: candidates, selected branches, failure categories | met | `acts-tracking-finding-record/1` and `/2` (`fixture_tools/acts_finding_record.py`): every candidate with its seed planes, outcome and category; seeds side file. `RecordFailsOnOneDefect` (`finding.log`) | |
| Output: own product format with its own round-trip test (Section 8.3) | met | `ProductFormat` (round trip byte exact, reorder, subset, merge), `ProductReaderR33.test_round_trip_is_byte_exact`, `BuiltDriver.test_the_driver_and_python_write_the_same_bytes` | |
| Formed in plugin code: unbiased residuals by removing the hit from the smoothed state | met with readings | CAI-T07-2 in job 7537235 and rerun in 7548207: the product's unbiased state equals ACTS's and a leave-one-out refit (`TrackFitOutputsRun.test_cai_t07_2_derivatives_and_the_unbiased_state_against_acts`) | The sheet says no helper exists; ACTS 48.2.0 has `calculateUnbiasedParametersCovariance`, and the driver reaches it (`finder-links.log`). The sheet's correction is user item m6. The closed-form comparison P8 is a reading by the user's choice (decisions.md, after job 7537235) |
| Formed in plugin code: residual covariances | met | `residual_covariance` per fitted track; `TrackFitOutputsRun.test_the_full_residual_covariance_is_the_empirical_one`, `ProductReaderR33.test_the_full_covariance_holds_its_identity_and_a_wrong_block_is_caught` (`track-outputs.log`) | |
| Formed in plugin code: alignment derivatives in the R32 parametrization | met | `t07-plane-rigid/1`; `AlignmentDerivativeClosedForm`, `ReferenceDerivativePrediction`, CAI-T07-2 against finite differences (`track-outputs.log`) | |
| R33 extras: cluster size and charge per measurement | gap | Recorded probe, D1 stage 8 fix round 1 (`calibration-alignment-interfaces.md`, Gaps): point hits only, no cluster on the path | A fixture with clusters, for the C&A plan |
| R33 extras: trajectory export with scattering parameters | gap | Recorded probe, the same: `KalmanFitterResult` and `GainMatrixSmoother` keep none; the fixture has no material | With material: a new fit or trajectory model (R37) |
| Steps, order: straight line first, then field, noise, CKF, ambiguity resolution, vertexing, residual and derivative outputs | met | In that order: straight line, job 7489042 (stage 1); field, 7493368; noise, CKF and ambiguity, 7493849 to 7502411; truth-seeded, 7503215 to 7515600; vertexing, 7522969 and 7524096; residuals and derivatives, 7537235 and 7546791; wrapper, 7548207 (ledger `progress.md`) | |
| Steps, each with its failing check first: stages 8, 9 and 11 | met | A red run recorded before the implementation. Stage 8 (`d1-stage8-report.md`, "Failing first"): `test_acts_track_outputs` on login before any implementation, 17 errors of 30 tests. Stage 9 (`d1-stage9-report.md`, "Failing first"): the two new modules against a copy of base `24e2891c`, import error and 3 errors, then 1 failure and 1 error with only the payload tool added. Stage 11 (D1 stage 11 report): `test_acts_scenarios` `FAILED (failures=1, errors=8)`, the claims test `FAILED (failures=1)`, the example test `FAILED (failures=1, errors=4 (the run before the host-path test was added; the module now reads failures=1, errors=5, skipped=1 without a recording))` | |
| Steps, each with its failing check first: stages 1, 2, 3, 4, 5 (with 5b to 5e), 6 (with 6b, 6c), 7 (with 7b) and 10 | open | The reports of these stages (`.superpowers/sdd/finish-plan/d1-stage*-report.md`; stage 3 has none) record no run of a new check against the code before the change. Stages 4, 5e, 6c, 7 and 10 record judges driven with honest input and one defect, and stage 10 heads its tests "failing checks first". That shows a check can fail, not that it failed before the change | A reading of those stages' logs or transcripts that finds the red runs, or the user's waiver of the failing-first rule for these stages. Not to be rerun now: the code before each change is past |
| Acceptance: finding and refit counted separately; a truth-seeded fit is never reported as finding | met | `FindingIsNeverARefit` (`finding.log`); `ReconstructionProductMap.test_a_refit_is_never_on_the_data_side_and_never_finding` (`adapter-tests.log`); `JudgesFailOnOneDefect.test_a_refit_stays_counted_apart`, `FieldOnRefit.test_every_track_is_fitted_and_counted_apart` (`refit-field.log`); `TruthSeededIsNeverFinding`, `TruthSeededRun.test_the_output_is_labelled_and_never_finding` (`truth-seeded.log`) | |
| Acceptance, negative case: wrong hits | met with readings | `NegativeCases` (`finding.log`): `FINDING-NEGATIVE one-wrong-plane: ... candidates 6 selected 6 category none`, the wrong hit on no track (`test_one_wrong_hit_per_track_stays_off_every_track`); `three-wrong-planes: ... selected 0 category seed-or-finding` | Inputs from block 1, as section 11 states; inputs that depend on a recipe are fixed at Freeze B (`t04-values-v4.md` section 11), so this is the development pass of a check section 11 requires at evaluation |
| Acceptance, negative case: branch explosion | met with readings | `branch-explosion: seeds_found 264 seeds_truncated 36 ... ambiguity_budget 1 candidates 1188 selected 188 category none`; every delivered candidate carries `search_truncated`, and no seed exceeds its branch limit (`test_a_branch_explosion_is_marked_and_stays_inside_its_budget`) | The event's category is `none` because tracks were delivered. The truncation is marked on every candidate, which a reader must take from the flag. The same section 11 note as above |
| Acceptance, negative case: seed failure | met with readings | `no-triple` and `two-planes`: `seeds_found 0 ... selected 0 category seed-or-finding` (`test_seed_failure_stays_in_the_record_with_its_class`); all 28 lost-plane pairs and 168 single-track losses found (`alone: lost 0 of 168`) | The same section 11 note |
| Acceptance: limits reached are marked search-truncated | met | Seed budget: `seed-budget: seeds_found 10000 seeds_truncated 9933 seed_budget 1` (`test_a_seed_budget_reached_is_marked`); branch and ambiguity budget above; the reader refuses an unmarked candidate of a truncated seed or event (`RecordFailsOnOneDefect.test_a_truncated_candidate_with_no_truncated_seed_is_refused`, `test_an_event_budget_reaches_every_candidate`) | |
| Failure classes (`t04-prereg.md`: seed or finding, fit, ambiguity, branch or resource truncation) | met with readings | Seed or finding and truncation: the cases above. Ambiguity: `evicted` candidates, ACTS's removal order equal to the copy (`diagnosis.log`, job 7512409's trace). Fit: refit `TwoPlanesInAFieldFail` (fit fails, category `fit`), `ReconstructionProductMap.test_a_failed_track_stays_an_object_with_its_class`. Each loss names its class (`SectionSevenScoring.test_a_lost_particle_says_why`, `RecordFailsOnOneDefect.test_an_event_with_no_track_names_its_class`) | No negative input forces a fit failure inside the finder. The class is defined, read and refused when unlabelled, and counted (`fit_failed`) in the development readings |
| Acceptance: scenarios A01, A05, A07, A17, A39 | see the scenario table | | |
| Acceptance: CAI-T07-1 rigid shift, -2 derivatives against finite differences with the track state held fixed, -3 refit, -4 sagitta-like weak mode; tolerances before the run; `r = x_meas - x_pred` | met with readings | CAI-T07-1 and -2 passed in job 7537235, which failed only on the closed-form comparison P8, a reading since. CAI-T07-3, -4: job 7546791 PASS. All rerun in 7548207 (`track-outputs.log`, `cai-refit.log`). `ResidualSignConvention`. Tolerances in each module's text before its job (`calibration-alignment-interfaces.md`, T07 acceptance items) | CAI-T07-3 tests in-plane shifts of plane 4 only. CAI-T07-4's flatness (17.0 on 7, p 0.017) and a charge difference of 3.0 se are readings, unexplained (decisions.md, stage 9). The case R37 does not cover is in `STATE.md` (`r37_uncovered_cases`) |
| Acceptance: quality per `t04-values-v4.md` and `t04-prereg.md`; pass or fail only after K09; refit gated on the clean fixture, truth-assisted, counted apart | open | Development readings only (decisions.md, stages 4 to 7b). The refit is truth-assisted and counted apart (row above) | By the sheet: K09 at Freeze B (finish-plan D4). The development values for Freeze B are user items (`STATE.md`) |
| Open item: CAI-T07-3 needs a way to apply a payload; the path is to be probed | met | Probe jobs 7490742 and 7491894 (`cai_payload_probe.cpp`): the placement route and a rebuilt geometry both work; the placement route is the user's choice 16; the payload interface in D1 stage 9, job 7546791 | |
| Open item: material effects after the first pass | open | No material in the fixture (`t04-values-v4.md` section 4.1) | A later pass, or the user's decision at Freeze A against plan 11.4 (`coverage.md`, obligations, no owner) |
| Stop: an ACTS behaviour that contradicts the contract map goes back to K04 | met with readings | No ACTS behaviour contradicted the contract map | The tool contract cannot state a file input's format, role or condition. That is a contract-schema limit, not ACTS behaviour. It went to the user as a K04 item (stage 10), and the prose is checked by tests |
| Stop: tolerances and valid ranges do not move after results | met with readings | No limit moved. Refuted prediction tests became printed readings only on the user's word: P1, P2, P3, P15 after job 7524096; P8 after job 7537235. Each refutation is kept on record. The clean tolerance was replaced by the exact replica check, by the user's choice after job 7512409 (decisions.md) | |

## Scenarios

| Scenario (plan section 13) | Meaning for this telescope driver | Status | Evidence | If not met |
| --- | --- | --- | --- | --- |
| A01, backend switch with the same semantics | A second tracking backend on the shared domain, with comparable differences | open | None. By the sheet, it stays open unless `simreco` qualifies on the shared domain | T15b (`coverage.md`, obligations). Nothing is done for it here |
| A05, interleaved IOVs, event slots, threads | The finder and the refit are single-threaded. One context (field, geometry, optional payload) is fixed per invocation, with no IOV change inside a run. The finder keeps one `TrackFinder` and one `TrackVertexer` over all events. So contamination would be state carried from event to event, or from one hit set to the next | met | Written, failing first where it can without a build. `tests/adapters/test_acts_scenarios.py`, `EventOrderJudge` and `PerTrackJudge`: honest records pass, and each of a carried number, a moved vertex, a dropped or doubled event or candidate, and a line under the wrong event is named (login, D1 stage 11 report). `EventOrderRun` interleaves clean stratum 0 reversed with noise stratum 11 permuted, 200 events each, in one file, with the vertex step: each event's lines must equal its own run's, byte for byte, with the end totals the sum. It also refits a hit-set list in file order and reversed. Earlier evidence: `FoundTracksAreFits.test_a_second_run_gives_the_same_bytes`; the stage jobs' byte equality across runs | The stage 11 job's step `scenarios` passes. Payload and nominal contexts interleaved inside one process cannot happen, since there is one `--alignment-payload` per invocation. That two such runs stay apart is A17. When the step passes, the row goes to `met with readings`, not `met`: IOV changes and threads do not occur in this driver, a stated limit Job 7551619: A05-FINDER 400 interleaved events, A05-REFIT 1200 tracks forward and reversed, defects 0. |
| A07, recluster or multiple passes: branches and revisions traceable, no incomplete commit, no wrong count | Each CKF candidate is in the record with its seed, outcome (`selected`, `evicted`, `fit-failed`) and category, and every seed has one outcome. Ambiguity removals follow ACTS's order. A second pass (R33 refit of delivered tracks, a subset or merge) has its own identity or revision. A cut-off file is never read as whole. A hit shared by two delivered tracks counts once | met with readings | `NegativeCases.test_every_seed_has_one_outcome_and_the_counters_agree`, `RecordFailsOnOneDefect.test_a_dropped_candidate_or_seed_is_refused`, `test_a_candidate_without_its_category_is_refused`, `test_a_truncated_or_unknown_record_is_refused` (`finding.log`); `FinderAgainstJob7502411.test_acts_removes_in_the_copys_order` (`diagnosis.log`); `SectionSevenScoring.test_a_hit_on_two_selected_tracks_is_counted_once`; `ProductFormat` subset, merge and reorder identities; R33 outputs of found tracks refitted only if their `/1` records equal the delivered ones (`R33OutputsOfFoundTracks`, `finding-r33.log`); `VertexDevelopmentRun.test_the_vertex_step_moved_no_track` (`vertexing.log`) | The programs write their record and product as they go, not atomically. An interrupted run leaves a partial file, and every reader refuses it (no end record), so it is detectable rather than prevented. The ambiguity trace is printed only for named events |
| A17, source-link calibration under different hypotheses: results bound to their hypothesis or context, never overwriting each other | T07 has no source-link calibrator: hits are points (`PlaneHitLink`), and no calibration step exists. So the scenario is shown on the hypotheses T07 has: a refit under an alignment payload, or under another field, keeps its identity, and two such results are never merged or mapped as one | met with readings | Product header line `alignment_payload` (stage 9, `ProductRecordsThePayload`, `CaiRefitRun.test_every_fit_is_fitted_and_each_payload_is_recorded`, job 7546791). Merge refuses another payload. Found and fixed in this stage: the refit's reconstruction-product/1 sidecars wrote `conditions_used: []`, "none consumed", for a refit that applied a payload. `sidecars_for_product` now takes the payload's R32 sidecar and records it, and refuses a missing, foreign, other-origin or other-geometry sidecar, or one for a product that applied none. `HypothesisBinding` failed first (`ProductFormatError not raised`), then passed on login (D1 stage 11 report); it reruns in the stage 11 job. The mapping is tested on synthetic documents; the driver's payload line itself is tested in job 7546791, and no job maps a driver-written payload product to sidecars. It also shows that merge refuses another field, with a control proving the test would catch a merge that forgot the field, and that a part of a product keeps its payload | Only the analogue is shown: the calibration form of A17 waits for a source-link calibrator (T08, T10 or later). The brief maps A17 to this form ("refits under different payloads or field assumptions carry their identity"), which is the reason for the reading. `version_one_of` drops the payload line by design. It is a view for comparing records, and its result is never written or mapped as the refit's product (module docstring) |
| A39, truth grouping: the data side uses observable grouping only; the full chain is tested; oracle grouping is not reported as the workflow | The finder groups hits into candidates from hits alone, and its efficiency is read on the full chain. The truth-seeded run (oracle start) and the refit of truth hit sets are comparators, counted apart and never reported as finding. No truth reaches the data side | met with readings | `FinderStaysTruthFree`, `NegativeCases.test_truth_reaches_the_finder_by_no_input`, `test_the_binary_holds_no_seed_or_truth_code` (`finding.log`); `finder-links.log` (no truth symbols); `TruthSeededIsNeverFinding`, `FinderRefusesTruth` (`truth-seeded.log`); `FindingIsNeverARefit`; `DevelopmentRun` reads the full chain on 24 strata. The example's replay checks the same labels (`examples/reconstruction-tracking`) | The plan's A39 is about a ranking model trained with truth grouping; there is no learned ranking model in T07, so the scenario is read for the finder's grouping and its comparators. The ambiguity resolver is ACTS's greedy rule on observable sharing and chi2 |

## Outside the sheet, recorded for the next reader

- Stage 8's C++ reached its first job uncompiled (job 7536797, ledger). From stage 9 the briefs allow a single-target login compile check of changed C++ (ledger, 2026-11-09T22:15:31Z).
- K12 performance: cost lines per stage (`-COST`) are printed, warm only. No target exists before P2 (`t04-values-v4.md` section 12).
- Deviation 10: earlier jobs' manifests missed files the whole-tree scans read. Stage 10's manifest and receipt cover them
  (`deviations.md`).
- The R32 row of `calibration-alignment-interfaces.md` now names the T07 evidence for `conditions_used` (A17 above): the mapping, tested on synthetic documents.

## Evaluation outcome (2026-11-13)

T07 **failed at attempt 1** on block 11 (summary 7613452): 1,259 of 1,260 records pass, 46 of 47 gates; the failing record is fixture 7002,
stratum 9, `vertex pull z`, tail rate 1.058 % (U 1.189 %) against L 1 %. Diagnosis on development data (t07-vz-diagnosis.md): AMVF merges
close 3-track vertex pairs; every occupancy-1 bin sits near 0.9 % on blocks 1 and 2. Three pre-registered candidates (C1-C3) all failed their
criteria; by the user's decision no attempt 2 is made (decisions.md, "T07: failed at attempt 1"). A remedy needs a different vertex seeding
or splitting method: new design work.

## Final (2026-11-14)

After the evaluation, three further principled candidates were tested on development block 1 on the user's word: the seeders S1 and S2
(jobs 7632710, 7636593; both worse than the frozen seeder; S2 not counted, K8) and the post-fit split test (job 7649462; K1 and K2 not met,
merged vertices almost unchanged). The user accepted the outcome on 2026-11-14: **T07 failed at attempt 1, final**; no return to Freeze B,
no attempt 2 (decisions.md, "T07: final at failed at attempt 1").


## Note added at G3 (2026-11-14): user items and failing-first, settled 2026-11-11

Appended; the rows and sections above are left as they were written. On 2026-11-11 the user accepted the coordinator's suggestions
("accept the suggestions"; `decisions.md`, "The user's answers to the remaining Freeze B, K09 and later items"). They settle items this file
lists as open:

- **The six user items** ("Also open", above). n6, the vertex primary's "most tracks": settled by U-K1 (tracks with weight at least 0.5).
  The D2 departure: accepted by U-W2 (nominal geometry identity `t07-telescope-nominal/1`). The K04 schema limit: accepted for now by U-W3
  (a typed file-input field in a later contract version). The Freeze B vertex values: given with Freeze B (U-B1 to U-B13 and the user's
  "Freeze B as listed", 2026-11-13). F1 and m6, with the stage 11 corrections: approved by U-W1 as one amendment of the task sheet labelled
  "after development", applied after evaluation; not yet applied in `t07-t09-task-sheets.md`, so they stay in `STATE.md` `user_items_open`.
- **Failing check first, stages 1 to 7 (with 5b to 5e, 6b, 6c, 7b) and 10** (the sheet row and the summary line, `open`): waived by the user,
  U-B15, recorded as "waived by the user, not shown". The row is closed by the waiver, not by evidence of a red run.
- **Stop row, the K04 schema limit** (`met with readings`): its user item is settled by U-W3.

Still open after these: material effects, A01 (T15b found no qualified candidate, job 7627683), the quality verdict (now final: failed at
attempt 1, section "Final" above), the R33 gaps, R34's two T07 rows, and the `coverage.md` obligations.

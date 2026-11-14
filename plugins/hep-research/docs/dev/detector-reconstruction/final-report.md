# Detector reconstruction plan v9.2: final report

**Verdict (R25): incomplete.** The plan is not complete for the required workflows. The tracking and vertexing workflow (T07)
failed at evaluation attempt 1, and that outcome is final. The data-control layer has no evidence (U11). Holdout independence is not
established, so the P6 gate is not passed. Calorimetry and photon likelihood have development bindings only, with no native backend.
P4 execution is incomplete. Every open obligation is named in "Open obligations" below.

Finish-plan Task G3, step 3. Written on 2026-11-14 from the records of branch `g3/final` at `316a097b` (the integrated feature tip, base
`hep-research--v0.58.0`, `662f58d4`). Nothing was run for this report. Paths are relative to this folder unless they start with a plugin
folder (`adapters/`, `tests/`, `evals/`, ...). Job evidence is in `<private>/evidence/` and `<private>/jobs/`. Every claim cites its record or
job; a number not in a record is not stated.

Plan: `hep-research-detector-reconstruction-plan-v9.2-en.md` (SHA-256 `452b48a5…`, `STATE.md`). Section numbers (§) are the plan's.

## Task states (R11)

| Task | State | Record |
|---|---|---|
| T01-T05 (P0) | done | `STATE.md` tasks; Freeze A in `decisions.md` and `freeze-a.md` |
| T06, T14, T15a (P1) | done | Gate C job 7487578 (`baseline.md`); re-baseline 7488410 at 0.58.0 |
| T07 tracking and vertexing (P2) | **failed** at attempt 1, final | `decisions.md`, "T07: final at failed at attempt 1"; `t07-closeout.md` |
| T08 calorimetry (P2) | done (narrowed claim) | summary of record 7620411; `t08-closeout.md` |
| T09 photon likelihood (P2) | done (narrowed claim) | summary 7613459; `t09-closeout.md` |
| T10 timing, PID, non-hit example, replay (P3) | done, with 2 open rows and 2 gaps | `t10-closeout.md` |
| T11 method coverage (P4) | done | `STATE.md` T11; `t11-cells.md`; `t11-citation-findings.md` |
| T12 reprocessing and performance (P5) | done, with open items | `t12-closeout.md` |
| T13 AI evaluation (P6) | **blocked-by-decision** (holdout not received) | `t13-harness-spec.md` section 6; harness job 7651192 |
| T15b two-candidate selection (P2) | done: no qualified candidate | job 7627683; `decisions.md`, "T15b: K16 selection" |
| T16 selection benchmark (P5-P6) | **blocked-by-decision** | `decisions.md` K11 default ("T13 and T16 are `blocked-by-decision`"); `t13-harness-spec.md` section 6 |
| Data control (Phase G2) | incomplete | `decisions.md`, "Recorded for the record (2026-11-13)", Phase G: U11 |

`STATE.md` was updated at G3 to these states for T13 and T16 (see "Record notes", item 1).

## Answers common to every deliverable

**Where it was done (§18.2).** The private worktree `<private>/worktree` on `feature/detector-reconstruction`, with parallel lanes in their own
worktrees and branches, each reviewed before merge (`decisions.md`, "Parallel lanes"). The main checkout was not touched (`STATE.md`,
`main_checkout_t0`). Interpreter: `<workdir>/env/py313`, Python 3.13.18, SHA-256 `32545eb5…` (deviation R29 option b), NumPy 2.4.6, SciPy 1.17.1.
Native backend: ACTS 48.2.0 (`acts-core` from conda-forge) in `<workdir>/env/acts48`, approved by the user (`STATE.md`, `backend_env`). Other
dependencies per job: Geant4 11.4.3 and uproot 5.7.7 for the zdcsim input (VALIDATION CALO-CLUSTER-T08); torch 2.14.1+cu130 for A13
(`decisions.md`, "A13 reopened"). Execution: NSTCCore Slurm, account `ams`, `edr2-al9_short_serial` on AMD EPYC 9645 nodes (hpa-wn33,
hpa-wn34; earlier hpa-wn28, hpa-wn30), and `b6000-al9_devel` (hp-rtx6kp02) for A13. Every job of record ran from a checked snapshot with a
source manifest (`t12-closeout.md`, T12-23; the VALIDATION entries).

**Sample roles.** Synthetic fixtures only for T07-T10 and T12 (K03; U11). Block 1: development and tuning. Block 2: the Freeze-B run. Block 5:
reserved for a return to Freeze B. Block 6: generator checks and fixed points. Block 11: evaluation attempt 1. Block 12: never read. T15b:
simulated `element_sim` events, blocks 21 (sample), 22 (attempt 2, unused) and 23 (reserved for K18 confirmation, untouched) (`freeze-b.md`;
`decisions.md`, "T15b: the K16 element_sim sample spec frozen").

**Statuses.** Evaluation outcomes are pass, fail or inconclusive per frozen gate (`t04-values-v4.md`, Freeze A; `freeze-b.md`). Close-out rows
are `met`, `met with readings`, `open` or `gap` (`t07-closeout.md`). These are kept apart throughout; a gap or an open row is never a pass.

## Answers per deliverable (§18.2)

### P1 contracts: T06, T14, T15a

- **Done.** Reconstruction sidecars and readers (`contracts/reconstruction.py`, `conditions.py`, `sidecar_reader.py`, eight schemas), the
  witnesses W1-W7 and corrections G01-G03 (`509ccca8`); the bounded inspector (`contracts/input_inspector.py`, `06975774`); offline candidate
  selection (`contracts/candidate_selection.py`, `0cd55444`). Gate C passed (`07ed6606`).
- **Used.** Artificial fixtures only (`STATE.md`, T15a).
- **Obtained.** Contract checks; `input-inspection/1` and `selection-record/1` records.
- **Checked.** Gate C rerun 7487578: only the known LCG test failed; the 14 new contract modules passed 766 tests (`baseline.md`). Again clean
  at 0.58.0, job 7488410.
- **Cannot be claimed.** Selection on real recipes (T15a is rules only); recognition of ROOT inputs (unknown until `uproot` is approved for the
  inspector, CHANGELOG T14); witnesses as instrument validation (§12.1).
- **Continue.** The typed file-input field of a later contract version (U-W3); the shared-runner follow-ups listed under T12.

### T07 tracking and vertexing (required workflow)

- **Done.** `adapters/acts-tracking` 0.3.0: native driver and finder on ACTS 48.2.0, product format, R33 outputs, alignment-payload refit,
  wrapper, tool contract, `examples/reconstruction-tracking/` (close-out `5712f83a`; VALIDATION ACTS-TRACKING-T07).
- **Used.** Frozen fixtures `t07-telescope-clean/1`, `-noise/1`, `-cai/1` (Freeze A, generator check 7492427); ACTS's adaptive multi-vertex
  finder at defaults (`decisions.md`, Freeze B proposal answers).
- **Obtained.** Tracks, vertices and finding records per event; evaluation records on block 11.
- **Checked.** Evaluation attempt 1, summary 7613452: **fail**. 1,259 of 1,260 records and 46 of 47 gates pass; fixture 7002, stratum 9,
  `vertex pull z` tail 1.058 % (upper 1.189 %) against L 1 % (`decisions.md`, "Evaluation attempt 1"). Cause, from the diagnosis on development
  data (`t07-vz-diagnosis.md`, a copy of the ledger file): the vertex finder merges close three-track vertex pairs 5 to 7.5 vertex-resolution units apart. Six principled
  candidates failed their pre-registered criteria on block 1 (C1 7623624, C2 7624555, C3 7625490, S1 7632710, S2 7636593, split test 7649462).
  The user, 2026-11-14: "accept T07 failed at attempt 1, auto continue": no return to Freeze B, no attempt 2, block 12 unread
  (`decisions.md`, "T07: final").
- **Cannot be claimed.** Any tracking or vertexing quality. A01 (a second backend; T15b found no qualified candidate). Material effects. Particle
  type, timing, displaced and near vertices (`coverage.md`, obligations). R33 gaps: cluster size and charge, trajectory with scattering parameters
  (`calibration-alignment-interfaces.md`, Gaps). R34's two T07 rows are designed, not checked (`t07-closeout.md`).
- **Continue.** New design work, the user's to start: a different vertex seeding or splitting method, or a Freeze A amendment of the far
  range (`decisions.md`, "T07: final"). The candidate switches stay on `t07/vz-diagnosis`, never merged.

### T08 calorimetry (required workflow)

- **Done.** `adapters/calo-cluster` 0.2.0, development binding in Python, zdcsim input path, `examples/reconstruction-calorimetry/`
  (`684af182`; VALIDATION CALO-CLUSTER-T08).
- **Used.** Frozen fixture t08-grid/1; the user-supplied zdcsim output for a format exercise, `simulated-unvalidated`.
- **Obtained.** Clusters with energies, positions and uncertainties in the plugin's product format.
- **Checked.** Evaluation attempt 1: **pass**, 8 of 8 gates, `done (narrowed claim)` (summary of record 7620411; checks counted from rerun
  7620410 under the user's block-1/6 ruling). Its `outcome.json` lists 26 open obligations.
- **Cannot be claimed.** A native backend (gap, U12 A). Quality on detector data. A15 (b) and A38.3 (U-K7). Angle and particle type, E1 pulls
  and merge, near pulls and sharing, saturated energy, split rate, unequal sharing, the noise-dominated regime (`coverage.md`, obligations). The
  zdcsim thresholds (Unresolved, U-W5) and its clustering rule (user item, `STATE.md`). No reproducibility tolerance (OI-5) and no byte rerun of
  its products (OI-11).
- **Continue.** A native backend on the user's word; a sourced ZDC threshold before any physics use.

### T09 photon likelihood (required workflow)

- **Done.** `adapters/photon-likelihood` 0.3.0, development binding, `examples/reconstruction-photon-likelihood/` (`5fff911f`; VALIDATION
  PHOTON-LIKELIHOOD-T09).
- **Used.** Frozen fixture t09-sphere/1, with the same analytic light model in the fixture and the fit.
- **Obtained.** Vertex, energy and time fits with multistart and topology records.
- **Checked.** Evaluation attempt 1: **pass**, 13 of 13 gates, `done (narrowed claim)` (summary 7613459); `outcome.json` lists 65 open
  obligations; the 24 single-photon refusals of sample 10 read `rejected` by hand.
- **Cannot be claimed.** Anything about the light model: every result is a shared-model closure (`t09-closeout.md`). A native backend (gap,
  U12 A). A second medium and the B1 pulls (`coverage.md`). A reproducibility tolerance (OI-6, left open by the user).
- **Continue.** A native backend on the user's word; a fixture whose light model differs from the fit's.

### T10 timing, PID, the native non-hit example and the scan/global replay

- **Done.** `adapters/timing-pid` 0.2.0 and `adapters/destriper` 0.2.0 (`32e8bc07`; VALIDATION TIMING-PID-T10, DESTRIPER-T10).
- **Used.** Synthetic time chains, counter channels and a synthetic timestream; the destriper chosen by the user at U7 (B2).
- **Obtained.** Time-chain, PID and counts products; a destriped map and baselines.
- **Checked.** Jobs 7593003 and 7627284 PASS (CAI-T10-1, CAI-T10-2, A37, counts with their controls); replay 7596623 PASS at the tolerance the
  user froze (differences about 1e-15 of the reference norm, so a PASS means only "below the tolerance"). Close-out: 13 met, 12 met with
  readings, 2 open, 2 gap (`t10-closeout.md`).
- **Cannot be claimed.** The cross-system workflow (§3.3 layer 2: "at least one cross-system workflow"): the TOF example with T07's path is
  open, since no record gives a flight-path length to a timing plane. A native timing backend (open: U12 A names only calorimetry and photon
  likelihood). A20-A24 (gaps). A native scan or global solver (gap; the development binding counts as R14's solver by the user's word). Any
  timing, PID or map-making quality. A reproducibility tolerance for the timing chain (OI-7).
- **Continue.** A timing plane in the T07 geometry or an agreed flight-path definition; native backends on the user's word.

### T11 method and contract coverage (P4)

- **Done.** Design cells for all 38 families (`t11-cells.md`), citation verification (`t11-citation-findings.md`), the literature record with
  63 sources (`STATE.md`, `literature`). Method text for the plugin (finish-plan F1) is on separate branches: groups 1-3 are in `github/main`
  as last fetched (PRs #395, #398, #399); group 4 (`t11/method-text-g4`) is pushed and not in `github/main` at that fetch. None of it is on
  this branch.
- **Checked.** Comparison clean with rerun 7474460 (R28); every applicable cell sourced or a recorded gap (R14) (`STATE.md`, T11).
- **Cannot be claimed.** Execution for any family: documented means text exists, not that anything runs (`t11-cells.md`, Parts 1 and 2). Ten
  citation uses stay unread; plugin defects in `t11-citation-findings.md` are not applied (`STATE.md`, T11).
- **Continue.** The group 4 PR on the user's word; the `gap-method` cells stay recorded gaps.

### T12 reprocessing and performance (P5)

- **Done.** Harnesses under `tests/contracts/` and `native_inputs` in `run_workflow.py` (`eb4ef5c9`, minors `ce250473`; VALIDATION RECO-T12).
- **Used.** Synthetic fixtures and recorded development products (blocks 1 and 2); the destriper on one GPU for A13.
- **Obtained.** Loop, invalidation, partition, comparator, benchmark and run-time records.
- **Checked.** 27 obligations: 7 met, 20 met with readings, each with a job of record (`t12-closeout.md`).
- **Cannot be claimed.** OI-1 to OI-7 and OI-9 to OI-11 (no frozen reproducibility tolerance or declaration; comparators answer `incomplete`);
  OI-12 and OI-13 (A13 at scan sizes: **the GPU speed number is sealed**; no product of a large scan can be written). A13 was left as it is
  by the user on 2026-11-14 ("Leave A13 as is (Recommended)"): its released frozen-pointing result stands; the mid-size proposal (4,096
  samples tractable with T10's exact method; the GPU predicted about 4 times slower there, crossover predicted near 29,000 samples from
  released timings only) is recorded as readings, and nothing is frozen (`decisions.md`, "A13: left as it is"); Q2 (a coordinator ruling
  the user has not confirmed); the runner's `retries`, neither honoured nor refused; no runner-level retention gate; the T07 refit format gap
  (no events-read declaration, so an empty event stays `unconfirmed`); A32 executed with a harness-side check only; **P4 execution
  incomplete**, 8 gaps (A26, A27, A29, A30, A31, A33, A35, A36); the loop-fixture findings (the control layer's gating does not read R32
  records; `validate_contract` accepts a step outside the loop wired to round 1); the shared-runner follow-ups (`ext_computational_run.json`
  lacks `native_sha256` and `undeclared_native`; the interpreter binary is not hashed). No speed for T07; no qualification of the control
  layer's rules (G07, mode M1).
- **Continue.** K09 tolerances per recipe (the user's). For A13, a mid-size pointing with a derived tolerance stays possible
  (`<private>/jobs/a13-midsize/PROPOSAL.md`), but the user chose not to pursue it now.

### T13 AI evaluation (P6)

- **Done.** The frozen scorer (`evals/reconstruction-holdout/score_holdout.py`, `ff9755a5…`), the writer brief, the harness with a bubblewrap
  sandbox and a Slurm runner, and a six-task development set (`316a097b`; VALIDATION RECO-T13-HARNESS).
- **Checked.** Job of record 7651192 PASS (143 harness tests on a fake CLI with the real scorer); sandbox checks 7650762, 7650958, 7651068,
  7651151 exit 0 on compute nodes.
- **Cannot be claimed.** **Holdout independence is not established**: the holdout is to be written in the user's session off this account
  and host, and no `holdout_id` or SHA-256 is recorded (`t13-harness-spec.md`, sections 1 and 6). The system under test and the budget for
  3 × (number of tasks) sessions are the user's and not given (`decisions.md`, "T13 design"). No model session on the holdout has run. The
  development-set shakedown (not the holdout) started: probe job 7652238 was submitted on 2026-11-14 and was pending when this report
  was last updated; no result is recorded (`<private>/jobs/t13-shakedown/`). So the P6 gate is not passed. Stated limits: custody on one
  Unix user; shell network flagged, not blocked (`t13-harness-spec.md`, section 8).
- **Continue.** The user's holdout and its hashes, the SUT and budget; the paid shakedown first, with the SUT model and plugin commit
  confirmed with the user (`decisions.md`, "T13 design").

### T15b two-candidate selection

- **Done.** K16 selection, attempt 1 on block 21, job of record 7627683 (VALIDATION RECO-T15B-K16).
- **Checked.** **No qualified candidate**: `simreco-pr-a` and `simreco-pr-b` each fail 13 of 96 required tests (`rho_pull` tail and fake rate
  above L 1 %). Gates were not lowered.
- **Cannot be claimed.** Comparative selection of a best candidate (§3.3 layer 5); any post-selection quality (no K18 confirmation data;
  block 23 untouched); A01 for T07.
- **Continue.** Attempt 2 on block 22 only by K09's rule and the user's call (`decisions.md`, "T15b: K16 selection").

### T16 selection benchmark and §14.5

- **State.** `blocked-by-decision` with T13 (K11 default). Nothing run.

### Data-control layer (Phase G2)

- **State.** Incomplete: no real data for this plan (U11, `decisions.md`, Phase G). Simulation does not stand in (R14, §12.1). K03, K08 and
  K18 confirmation stay open.

## Section 3.3 layers

1. **Method and contract coverage:** T11 done, with recorded gaps; documentation is not execution.
2. **Required executable workflows:** tracking and vertexing **failed**; calorimetry and photon likelihood pass on synthetic gates with
   development bindings; timing and PID demonstrated on synthetic data; the cross-system workflow is open; the native non-hit example is met;
   the scan/global replay is met with readings (`t10-closeout.md`).
3. **Applicability of abstractions:** W1-W7 pass (Gate C); P4 execution incomplete (8 gaps, T12-20).
4. **Evidence:** synthetic, yes; simulation, only `simulated-unvalidated` zdcsim and the T15b `element_sim` sample; data control, none; platform,
   CPU and GPU records without targets; AI thresholds, not run.
5. **Automatic recognition and selection:** rules on artificial fixtures (T14, T15a); the one two-candidate domain found no qualified
   candidate (T15b); T16 blocked.

## Six criteria

The evidence table is VALIDATION `RECO-SIX-CRITERIA`. In one line each: reasonableness partly evidenced; correctness (hard) **not met** for
the required workflows; flexibility partly met; efficiency partly evidenced; generality met at contract level, execution incomplete;
applicability (hard) met with readings on synthetic data, not established on real data.

## Open obligations (R25)

Each stays open; none is turned into a pass by this report.

1. **T07 failed at attempt 1, final** (the user, 2026-11-14). Cause recorded: vertex merging of close three-track pairs at ACTS defaults.
   With it: A01, material, particle type, timing, displaced and near vertices, R34's two T07 rows, the R33 gaps.
2. **T08 passed with a narrowed claim:** 26 open obligations in the outcome record (7620411); the native-backend gap; A15 (b), A38.3; the
   zdcsim thresholds and clustering rule; OI-5, OI-11.
3. **T09 passed with a narrowed claim:** 65 open obligations in the outcome record (7613459); shared-model closure; the native-backend gap;
   medium and B1 pulls; OI-6.
4. **T10:** the cross-system TOF example; the native timing backend; A20-A24; the native scan or global solver; OI-7.
5. **T12:** OI-1 to OI-7, OI-9 to OI-13 (A13's GPU speed sealed at scan sizes; OI-12 left open by the user's "Leave A13 as is",
   2026-11-14); Q2; the runner's `retries` and the missing retention gate;
   the T07 refit format gap; A32's harness-side check; **P4 execution incomplete, 8 gaps**; the loop-fixture findings; the shared-runner
   follow-ups.
6. **T13:** harness built and sandboxed; holdout not established (`blocked-by-decision`: the writer session is the user's); SUT and budget
   not given; no holdout session run (the development-set shakedown is in progress). **Holdout independence not established; the P6 gate is not passed.**
7. **T16:** `blocked-by-decision` with T13.
8. **U11:** no real data; the data-control layer is incomplete.
9. **T15b:** no qualified candidate; comparative selection not demonstrated; no K18 confirmation.
10. **Native backends** for calorimetry and photon likelihood (U12 A), and the native scan or global solver (U7 B2): recorded gaps.
11. **K decisions still the user's** (`STATE.md`, `k_decisions`): K08, K10, K11, K17, K18.
12. **User items** (`STATE.md`, `user_items_open`): the sheet corrections F1, m6 and stage 11, approved as one amendment after evaluation
    (U-W1) and not applied in `t07-t09-task-sheets.md`; the two zdcsim items.
13. **Evaluation harness items carried to a later attempt:** audit findings 2 to 4 (`e6-result-lines-audit.md`, a copy of the ledger file) and the T07 check tasks that
    write no milestones (review I3) (`decisions.md`, "Evaluation attempt 1"). With no attempt 2 they stay open for any later evaluation.
14. **Calibration and alignment handoff:** the gaps and the "Open, not gaps" items of `calibration-alignment-interfaces.md`.
15. **T11:** ten unread citation uses; plugin defects in `t11-citation-findings.md` not applied; method-text group 4 not merged.
16. **G3 itself:** step 2 (the final checkpoint job on the integrated tip and a whole-branch review by a fresh reviewer) and step 4 (PR on
    the user's word, final backup) are not done. The branch is based on 0.58.0; `github/main` is at 0.66.1 as last fetched, so a rebase
    precedes any PR.
17. **Process:** 13 recorded deviations, none known to have affected a recorded result (`deviations.md`). The LCG test's site CVMFS cause is
    not known (`baseline.md`); it did not fail in jobs 7650906 and 7651192.

## How work can continue

The decisions that unblock most: the holdout, SUT and budget for T13 and T16 (U9, K11); real data for data control (U11, K08, K18); native
backends (U12, U7); K09 tolerances for reproducibility (OI-1 to OI-11); new T07 design work if the user wants tracking and vertexing
revisited. Every job of record can be rerun from its script and manifest in `<private>/jobs/<stage>/`.

## Record notes

Found while writing this report. Items 1-6 and 8 were fixed at G3 on 2026-11-14, on the coordinator's instruction, without rewriting
history (appended notes or updated status rows); item 7 is left to the coordinator.

1. Fixed. `STATE.md` predated the T13 merge (`316a097b`). It now reads T13 `blocked-by-decision` (harness merged, job of record 7651192,
   sandbox checks; holdout not established; shakedown in progress, probe 7652238), has a T16 row (`blocked-by-decision`) and a new
   `next_action`.
2. Fixed. `t13-harness-spec.md` section 4 read "not yet" for the custody agreement, the runner and the execution resources; its rows now
   state the user's answers from `decisions.md` and what remains the user's (the holdout, its SUT, the budget).
3. Fixed. Checkpoint job 7650906 (`ce250473`, PASS) is now entered in `STATE.md` and stated in VALIDATION RECO-CHECKPOINTS.
4. Fixed by an appended note. `t07-closeout.md` listed six user items and open failing-first rows; the note records that U-K1, U-W2, U-W3
   (and Freeze B) settled them, that U-B15 waived failing-first, and that the sheet corrections (U-W1) are still not applied.
5. Noted, row left open. `t09-closeout.md`'s topology-score calibration row: an appended note records that the three rate tests it waited
   for passed in 7613459, and what that does not settle; closing the row is a ruling for the coordinator or the user.
6. Fixed by a note. `t11-cells.md` stated "done-provisional"; a line under it now records `done` after rerun 7474460 (`f1a9d73b`).
7. Left to the coordinator. The local `main` of this clone is at `9bd365f0` (0.55.0), so `git log main..HEAD` also lists the 0.56.0-0.58.0
   releases; the branch's own work is `662f58d4..316a097b` (133 commits). `github/main` is at 0.66.1 as last fetched.
8. Fixed. `t07-vz-diagnosis.md` and `e6-result-lines-audit.md`, cited by `decisions.md`, were only in the untracked ledger; copies are now in
   this folder with a source note, and `decisions.md` has an appended note. `t07-vz-diagnosis-review.md` stays in the ledger only.

Found while fixing them, not fixed: in `STATE.md` the `cvmfs-probe-2` entry sits indented under `literature`, so the YAML block does not
parse as written (it predates G3).

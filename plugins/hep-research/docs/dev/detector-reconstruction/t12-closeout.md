# T12 close-out against its obligations

T12 is reprocessing and performance (plan v9.2 §16.1 row T12; finish-plan F2): the outer calibration loop (R37's T12 item, R36),
conditions invalidation and identity (§9.3-9.9, A04, A14, A40, A42, G05, G06), partitioning, recovery and processing accounts (§10.2,
§10.5, A11, A12), comparators and quality before speed (§14.1, A15, A50), the CPU engineering benchmark (§14.2), A13 on the GPU (R30, U8),
execution fields (§10.4), A37 and §9.6 in T12 (R31), the A26-A36 run time (R20) and A10. Paths are relative to `plugins/hep-research/`.
Job evidence is in `<private>/evidence/<folder>/` and `<private>/jobs/<stage>/`; job IDs are the ones `decisions.md`, `STATE.md` and the
ledger record. The stage plan with every expectation, fix round and ruling is `t12-stage-plan.md` (not changed by this close-out).

**Scope of this file.** One row per obligation T12-01 to T12-27 of `t12-stage-plan.md` ("Obligations"), each with its status, the job of
record and commit, and the reading or what is missing. Then the open items, the carried minors of the stage reviews, and what T12 does not
claim.

**Not judged here.** No reconstruction quality is claimed beyond Freeze B and evaluation attempt 1 (T07 failed, T08 and T09 passed with
narrowed claims; decisions.md). Every T12 harness lives under `tests/` (it may import the control layer; an adapter could not), runs on
synthetic fixtures or on recorded development products (blocks 1 and 2), and shows that interfaces behave as the plan states, nothing more
(G07, mode M1: the control rules are not qualified). Every timing is a record, not a gate (K12 sets no T12 target).

**Status words** (as `t07-closeout.md` to `t10-closeout.md`).
- `met`: the evidence shows the obligation as the plan states it.
- `met with readings`: met, with a limit, a narrowing or a departure stated beside it.
- `open`: work, or a decision, is still owed.
- `blocked`: it cannot be provided now, on a recorded probe or decision (no backend, no frozen tolerance).

**Jobs of record** (all JOB RESULT PASS; full unit suite failing only the known LCG ID, static gate 31 pass).

| Stage | Obligations | Job of record | Script, manifest | Node, elapsed | Commit (merge into feature) |
| --- | --- | --- | --- | --- | --- |
| 1 | T12-01 to T12-04 | 7606257 | `t12-stage1.sh` c8fb84e3, SOURCES 0734b8e9 (5,623), BASE d65323ee | hpa-wn33, 26:14 | 0e310d34 |
| 2 | T12-05 to T12-09, T12-24 to T12-27 | 7627669 | `t12-stage2-r1.sh` 65d04f91 (the count-check fix of f6461df2, whose run 7627425 failed only at `Ran 1 test`), SOURCES-r1 cff620fd (5,629) | hpa-wn34, 20:11 | 7eda91a2 (aed73a78) |
| 3 | T12-10 to T12-12 | 7647776 | `t12-stage3-r1.sh` 75f9eff7, SOURCES-r1 73334094 | hpa-wn34, 22:56 | bbfa7b4e (fast-forward) |
| 4 part A | T12-13, T12-15 | 7648553 | `t12-stage4-r2.sh` db480ef6, SOURCES-r2 68ef47fa (5,652) | hpa-wn34, 19:26 | b0e3c013 (d1f6fc30) |
| 5 (with 4 part B) | T12-14, T12-16, T12-17, T12-22 | CPU 7649128; GPU pilot 7649129, measurement 7649143; R30 hardware 7648670 | `t12-stage5-r1.sh` d6ae025d, SOURCES-r1 9e20995a; `a13-pilot-r1.sh` fd69a06e, `a13-measure-r1.sh` 3ae889d5, SOURCES-r1 ba741512; `hw-check.sh` 140cbcbe | hpa-wn33, 34:09; hp-rtx6kp02 (b6000-al9_devel, 1 GPU), 3:18, 10:11, 1:04 | 8dfd7d38 (eb4ef5c9) |
| 6 | T12-18, T12-19 | 7648001 | `t12-stage6-r1.sh` cb43639a, SOURCES-r1 5b3b0a93 (5,654) | hpa-wn34, 23:12 | 781e7d31 (a844897d) |
| 7 | T12-20, T12-21 | 7648050 | `t12-stage7-r1.sh` 29f01db9, SOURCES-r1 0b81e2e2 (5,651) | hpa-wn33, 25:46 | f8209933 (c5e41e41) |

Readings only, not of record: 7627101, 7627425 (stage 2); 7634549 (stage 3); 7636498, 7647973 (exit 2 at the snapshot check, no reading)
(stage 4); 7648900, 7648901 (the GPU hidden by the sandbox), 7648934 (stage 5); 7636529 and 7636499 (stages 6 and 7, failed only on the
latent TaskDeadline test, fixed by the recorded post-freeze change ec2b0548). Each stage had a fresh review and a scoped re-review
(stages 2 to 7: `jobs/t12-stage<N>/REVIEW.md`, `REREVIEW.md`; stage 1: `t12-stage1-review.md` and `t12-stage1-rereview.md` in the ledger folder `.superpowers/sdd/finish-plan/`).

## Summary

| Status | Rows |
| --- | --- |
| met | 7 (T12-02, T12-03, T12-04, T12-06, T12-17, T12-18, T12-26) |
| met with readings | 20 |
| open | 0 rows; the open items below stay open beside their rows |
| blocked | 0 rows; inside T12-20, 8 scenarios are blocked by no backend (P4 execution incomplete) |

T12 is done as a task: every obligation has a job of record and a status. It is done with open items: the reproducibility tolerances of
every recipe but the destriper (OI-1 to OI-7, OI-9 to OI-11), A13's speed at scan sizes (OI-12, OI-13), P4 execution (8 gaps), the T07
refit format gap, the runner's `retries` and retention gate, and A32's harness-side check. None of them is a failed T12 check; each is
a recorded limit with its owner.

## Obligations

| Obligation | Status | Evidence (job of record, commit) | The reading, or what is missing |
| --- | --- | --- | --- |
| T12-01 (R37 T12, R36): `CAI-T12-1`, synthetic two-round loop, round-2 payloads differ, both checks pass at round 2, final outputs released | met with readings | `tests/contracts/t12_outer_loop.py`; L1-L8 hold, planted P1-P5 each detected with its exact failed set; 7606257, 0e310d34 | Open findings of the loop fixture (stage plan, stage 1; calibration-alignment-interfaces.md "Open, not gaps"): the control layer's gating does not read R32 records (P1's wrong round stays publishable, caught by the harness's `check_used`); `validate_contract` accepts a step outside the loop wired to round 1 (P3, caught at labelling and by the harness) |
| T12-02 (R37, R36): `CAI-T12-2`, convergence fails at round 2, final step held, nothing released, the failure kept | met | H1-H6: `derive-r2` held, `reco-final` not run, publish refuses, `prior_failures` keeps the fail and a later pass never rewrites it, harness exit 0; 7606257 | |
| T12-03 (R37, §9.6, A37): placeholder checks never satisfy A37 | met | The loop record states `a37: not satisfied by this fixture`; no A37 row moves; 7606257 | |
| T12-04 (G06, §9.7): the fixed final-round rule is not changed | met | C1-C4 refused by `validate_contract` with their messages; 7606257 | |
| T12-05 (A04, §9.9 row 1): same-tag payload change: local recompute when dependencies are complete, else broaden | met with readings | R1 (exact rerun set, `reuse_decision` refuses under the new payload), R2 (unknown closure reruns every time); 7627669, 7eda91a2 | Shown on a synthetic DAG with the frozen T08 configuration, not on recorded T07-T09 products (stage 2 concern 1). R1 characterises the existing input-hash rule (the gain sidecar is a declared input); a tag resolved at run time without being declared is shown only through R2's broadening (review M4) |
| T12-06 (A40, §9.8, U11): native identity refreshed before every reuse decision | met | R3: a one-byte change of the stand-in native binary reruns the step under an unchanged wrapper and workflow; a stale manifest of hashes does not make it skip; runner N1-N2; stage 6 rehashes the frozen T07 binaries per call (m4); 7627669 | |
| T12-07 (G05): native binaries, libraries and configurations enter `run_workflow.py` as declared inputs | met with readings | `skills/hep-computing/scripts/run_workflow.py`: `native_inputs` hashed every run, `extension.native_sha256`, receipt `native_inputs`, undeclared `argv[0]` or interpreter-run script never skipped, missing input exit 2 before any step; `geant4_run.py scan` declares its executable; `test_workflow_native` 21 OK; 7627669 | Limits stated in the docstring, analysis-workflows.md and CHANGELOG: libraries loaded but not named are not observed; an executable given as an option value is closed only when declared; the interpreter binary is not hashed; `ext_computational_run.json` lacks the two new keys (frozen file; follow-up) |
| T12-08 (A42): imports, executables or outputs from a live tree detected | met with readings | `t12_reprocessing.py scope-check` run in every stage job on its own process with the modules under test imported, live roots from `git worktree list` (27), negative control exit 2; R9 | The check sees its own process only (child processes are out of reach, stated); it lives in `tests/` |
| T12-09 (A14, U12, §9.8): computational reuse separate from quality reuse | met with readings | R7: an artifact passed under criterion A is `unchecked` after criterion B is added; a reuse gives no result; the old fail stays in `historical_failures`; a skipped step writes no receipt; 7627669 | Characterises existing control-layer behaviour (review M4) |
| T12-10 (A11, §10.2 items 4-6): partition boundaries add no omissions or duplicates; gaps enter exposure | met with readings | `tests/contracts/t12_partition.py` `merge_by_key`; 7647776: R1 T07 clean and noise s2 (150 events in 3 ranges) equal to the full run; R2 T08 main s4 (600) and dead s0 (300), T09 multistart and topology s9 (40) equal by key; exposure with gaps apart; bbfa7b4e | The T07 refit ranges (R3, E6b 7591993, 2,700,000 keys) show completeness, disjointness and the tie to their records, not equality with a single pass (none kept). Object-key merge on real ranges is shown for T08 and T09 |
| T12-11 (A12, §10.2 item 7, §10.5): async, OOM or timeout complete or fail explicitly; never an old artifact | met with readings | Range collection by the layout's attempt rules, the counted attempt's Slurm id and record (review I1), product SHA and completeness; killed, timeout or OOM ranges count nothing; partial files never reused; K1-K8; 7647776 | K5-K8 describe the runner as it is: it ignores unknown step keys, so `"retries"` is neither honoured nor refused (open item). Finding: a failed run record and receipt list the partial output's SHA-256 with `end_status` timeout or failure (a consumer must read `end_status`) |
| T12-12 (§10.2 item 3): processing accounts per stable scope; an empty collection is not a failure | met with readings | One scope `<workflow>/<fixture>/b<block>/s<stratum>/e<event>` and one category per source event; `exposure` refuses inconsistent accounts and overlapping gaps; 7647776 | "An empty collection is not a failure" is shown for JSON Lines products only. For the T07 refit product it stays open (the T07 refit format gap: the product declares no events read, so an empty event in a successful range is `unconfirmed`) |
| T12-13 (§14.1): byte, numerical and statistical comparators declared per recipe | met with readings | `tests/contracts/t12_comparators.py`: byte form for every recipe but T08; numerical for the destriper at T10's frozen tolerance (217a38bc, 12738ebc) under the OI-8 ruling with T10's derivation checks; statistical for the T07 CKF fake rate per noise bin by F2 (tau 0.0025, 95 %); a reordering passes, a changed association fails; mutation 25/25; 7648553, b0e3c013 | Every other recipe and quantity answers `incomplete` (exit 3) with its open item, never a pass: OI-1 to OI-7, OI-9, OI-10 (F2 one-sided), OI-11 (T08 byte form). The byte form holds on one node class only |
| T12-14 (§14.2): CPU engineering benchmark, components timed apart, overlap stated | met with readings | `tests/contracts/t12_benchmark.py`; 7649128: destriper on the four A13 sizes, T08 (block 1, s4, 600 events) and T09 (block 1, s9, 40 events), 3 repetitions each, quality released on the recipes' records, 3/3 succeeded each; recipe identity pinned at Freeze B bytes (C5); 8dfd7d38 | T07 not measured (failed at attempt 1; no speed for it, A50); T09's inner components not separated (would need instrumenting a frozen file); the timing chain not named by part B; file-system cache not controlled. Numbers are records, not gates |
| T12-15 (A15, A50, §16.1 "quality before speed"): a faster variant with worse tails rejected or listed as another working point | met with readings | Q1-Q8: the planted faster variant fails the tail (0.0121, lower bound 0.0105 > 0.01); objects without a result count as tail failures; speed sealed and released only against a gate record the harness issued for that candidate (fix round 2, M3); nothing selected when none qualifies; 7648553 | Synthetic candidates. Two low gaps, reachable only by attacking the API, carried: `gate_record` does not check the gate belongs to the candidate; the record's fields are writable |
| T12-16 (A13, R30, U8): GPU subchain against CPU, with transfer, initialization and queues; quality at a fixed reproducibility level | met with readings | The destriper's baseline solve in PyTorch float64 on CUDA (`tests/contracts/t12_a13_gpu.py`); R30 7648670; pilot 7649129 4/4 and measurement 7649143 6/6 passed the stage 4 comparator at T10's frozen tolerance on the frozen pointing (15 iterations, 4e-16 to 2e-15); queue, initialization, transfers, compute and checks timed apart; 8dfd7d38 | Quality only on the frozen pointing (Q2, a coordinator ruling the user has not confirmed). Scans of 1,048,576 and 16,777,216 samples answer `incomplete` (OI-12; 78 and 148 iterations equal to the CPU's, differences 6-12e-15 as readings) and their GPU timings stay sealed: no GPU speed number at the sizes where the GPU could matter. OI-13. A13 covers the destriper only |
| T12-17 (R14, Q1 superseded): CPU measurements recorded beside A13 | met | T12-14's destriper timings on the same sizes, released on the recipe's quality record (7649128; CPU side in 7649143, exit 0 on all four sizes); `blocked-by-resource` no longer applies (the user's GPU word, R30 done) | |
| T12-18 (A37, §9.6): g×E degeneracy: only identifiable combinations and named constraints | met | `tests/contracts/t12_degeneracy.py` (T10's fixture form): `gxe` exit 0 with no failed item, the plant exit 1 with exactly [G2]; only "identified" by the used constraint accepted (m1); 7648001, 781e7d31 | |
| T12-19 (A37, §9.6, R31): the T07 weak-mode fixture reused inside a T12 reprocessing | met with readings | Fixtures 7003 and 7004 reprocessed with the frozen T07 binaries through the control-layer machinery; all 8 cells equal job 7546791's `cai-refit.log` to printed precision (e.g. cell -1/3: 5.1192 per-track σ, χ²/ndf change -0.01764, se 0.01529); the card lists the sagitta-like mode and its constraint; plant exit 1 [W4 W5 W6 W8]; 7648001 | No outer-round family (the coordinator's ruling on Q3 and stage 6 concern 1). The plants run on toys except the no-deformation plant. The zero-payload sidecar defect it found (review I1) is fixed by the recorded post-freeze change ec2b0548 |
| T12-20 (R20, A26-A36): one executed case per scenario on a backend that covers it, otherwise a recorded gap | met with readings | `tests/contracts/t12_runtime.py`; 7648050: executed A28 (timing-pid counts), A32 (E32R: `build_response.py` on frozen and variant T08 products), A34 (destriper null mode); record `p4_execution: incomplete`, gaps [A26 A27 A29 A30 A31 A33 A35 A36]; f8209933 | A32 is "executed, harness-side check" (the coordinator's label): the pairing refusal is the harness's, `build_response.py` records no structured identity. The 8 gap scenarios are blocked by no covering backend, each with its reason in the stage plan; P4 execution stays incomplete |
| T12-21 (§16.1 T12 row, A10): a product without raw retention refuses a trace rerun inside a T12 reprocessing | met with readings | K1-K6 in 7648050: readout kept, a new product under G1 with its own payloads reproducing bytes; not kept, refused, nothing written, labelled not recalibrated; the conditions snapshot also required (K6); waveform always refused | The reprocessing is the harness's planner (`plan_step`), not the shared runner: "no runner-level retention gate" (open item). The sidecar condition tags are harness labels |
| T12-22 (§10.4): execution fields for the GPU subchain | met with readings | Layout, residence, ownership, asynchronous completion, transfer edges (16 B per sample host to device; 8 B per pixel and baseline back; 4 scalars per iteration), precision float64, batch, measured device and host memory, written into the run output; 7649143 | GPU subchain only; streaming queues not applicable (offline); the CPU recipe's command line gets no GPU field; float32 a reading only |
| T12-23 (R11, R25): each stage's evidence a snapshot job with a manifest, predictions fixed before it runs | met with readings | The table above: every job of record copies its tree to a snapshot, checks its manifest, prints predictions in its pinned header; stage reports and reviews in `jobs/t12-stage<N>/` | Test-first is not clean everywhere, each disclosed in its report: stage 2 red-1 a test-design defect and characterising tests; stage 3 three tests after green; stage 4 one feasibility probe on login before the section; stage 5 a failing green log deleted (content in the plan) and two bounds changed after red; stage 6 tests added after green; stage 7 the test file changed after red-1 (rebuilt and kept) and amendment 1 after green-1. Stage 2's first r1 run 7627425 failed only at its own count check; scripts outside their manifests were re-pinned with the ledger recording each hash |
| T12-24 (§9.9 row 2, §9.3): an IOV crossing a chunk is subdivided | met with readings | R8/R8': `bind_chunk` subdivides keys 40-59 over IOVs [0, 50) and [50, 100); a key with no or two payloads refused; `check_chunk_binding` refuses the first key's payload on the whole chunk and reports uncovered or doubly covered keys; 7627669 | Shown on the harness binder with synthetic keys, not on a recorded T07-T09 product split across a payload change; the binder lives in `tests/` |
| T12-25 (§9.9 rows 3-4, A32): configuration changes invalidate by dependency and keep both versions | met with readings | R4: a changed T08 constant changes the recipe's configuration identity, products go to `products/<configuration sha256>/`, both kept, response and report rerun (7627669); E32R adds a real response artifact and the refusal to reuse it (7648050) | Synthetic DAG; the T08 configuration identity covers its bytes, `source` text included (a conservative broadening, §9.4) |
| T12-26 (§9.9 row 6): metadata-only change keeps scientific identities | met | R5: only `report` reruns; every scientific output and run record byte-identical; 7627669 | |
| T12-27 (§9.9 closing paragraph): configuration identity includes effective defaults, seeds, limits | met with readings | R6 and runner N6: a changed default, budget or iteration limit changes the identity; the recipe's reader refuses a missing default; a changed `seeds` reruns; 7627669 | R6 is a specification table (the harness's categories), not a demonstrated classifier; the T08 recipe has no seed, so the seed row is shown on the runner's `seeds` field. N6 changes `--incremental` for every workflow whose `seeds` change (CHANGELOG) |

## Open items

Each stays open beside T12's "done"; none is a failed check.

- **OI-1 to OI-7 (no frozen reproducibility tolerance).** T07 CKF numerical and every statistical quantity but the fake rate (OI-1, OI-2),
  T07 AMVF (OI-3), T07 refit (OI-4), T08 (OI-5), T09 (OI-6), T10 timing chain (OI-7): each comparator answers `incomplete`. OI-6: the
  user, "Leave open (Recommended)" (2026-11-13), on T09's close-out replay tolerance. Closing any of them is a K09 value, the user's.
- **OI-8** is not open: a coordinator ruling (decisions.md, "T12: coordinator rulings").
- **OI-9.** No recipe declares `reproducibility` (G03); writing it into a recipe changes a Freeze B item (a return to Freeze B, v4 3.4).
- **OI-10.** F2 is one-sided as frozen: a lower candidate rate beyond tau, or a changed track count, answers `incomplete`; an association
  change at an equal rate is not seen by the statistical form (stated).
- **OI-11.** T08 has no recorded byte rerun of its products: T08's byte form is `incomplete`.
- **OI-12.** A13 at scan sizes: T10's tolerance does not hold off its pointing and none is frozen for larger pointings, so the answer is
  `incomplete` and the GPU timings are sealed. **A13's speed number is sealed at scan sizes.** Way out, a proposal for the user (stage plan,
  stage 5): an intermediate pointing of about 4,096 to 65,536 samples with a T10-style derived tolerance, frozen by the user.
- **OI-13.** `destriper-product/1` embeds a dense design matrix, so no product of a large scan can be written; scans are compared in memory.
- **Q2 (A13 reproducibility).** A coordinator ruling awaiting the user's confirmation.
- **The runner's `retries`** (owner: the coordinator; a shared-runner change needs its own review): `run_workflow.py` ignores unknown step
  keys, so a declared retry count is neither honoured nor refused, and §10.2 item 7's bounded retry does not exist in the runner (safe under
  §10.5).
- **No runner-level retention gate** (stage 7, M2): A10's reprocessing gate is the harness's planner.
- **The T07 refit format gap** (stage 3, I2): the refit product declares no events read; T12-12's empty-collection claim is open for it
  until the format or its record declares the events read.
- **A32's harness-side check** (stage 7, I1): `build_response.py` records no structured product or configuration identity.
- **P4 execution incomplete**, 8 gaps with reasons (stage plan, stage 7 table): A26 injection before filtering, A27 per-setting scan
  conditions, A29 angle bases, A30 first CRES segment, A31 averaged or filtered spectra, A33 scintillation insufficient for energy (simreco
  adjacent, not a cover), A35 frame definitions, A36 injection into real data.
- **Loop fixture findings** (stage 1): the control layer's gating does not read R32 records; `validate_contract` accepts a step outside the
  loop wired to round 1.
- **Shared-runner follow-ups** (stage 2): `ext_computational_run.json` lacks `native_sha256` and `undeclared_native`; the interpreter binary
  is not hashed; option-value executables are closed only when declared.

## Carried minors from the stage reviews

Not blocking; taken by the t12/carried-minors lane (t12m-tree) unless stated.
- Stage 2 (REREVIEW.md): M-a, a bare `python3` or `cp` as `argv[0]` now never skips: the CHANGELOG names this only in general terms (the
  ledger asked for an explicit sentence at merge; not present at eb4ef5c9) and no pin test exists; M-b, a scan with a relative `--exe` or
  `--build-record` containing `..` makes a workflow the runner refuses at load; M-c, a work-relative native input no step writes is found
  only at its step; script detection takes the first existing file after the interpreter (`bash --rcfile rc run.sh`).
- Stage 3 (REREVIEW.md): the gap sort on tuples with scope can raise `TypeError` (sort on first and end); `isinstance(int)` accepts `True`
  and a negative first; the I1 test uses one stale record for both attempts (accepted).
- Stage 4 (REREVIEW.md addendum): `gate_record` does not check the gate belongs to the candidate; `_GateRecord` fields writable;
  `SealedTiming` private attributes writable. Accepted as they are: N-A (an unknown quantity on a declared recipe answers `incomplete` under
  OI-2), N-B (constants read from `t07_evaluation_scoring.py` at 32d0adc6, not Freeze B's 6102c2ef; values equal), N-C (OI-10).
- Stage 5 (REREVIEW.md): the noiseless final-residual check is nearly vacuous (the trajectory test covers it); `a13-measure-r1.sh` was
  re-pinned after the pilot (5da2205a to 3ae889d5, `--time 02:00:00`; recorded in the ledger).
- Stage 6 (REREVIEW.md): the `ldd` guard's `||` tests the loop's last pipeline, not `ldd` (the later "not found" grep catches it); the
  identity is hashed at hash time; review n1 and n3 not adopted (stated).
- Stage 7 (REREVIEW.md): a response with more than one configuration string is treated as unbound (safe, untested); a `check_side` field in
  the A32 record; the job's expected open items must stay equal to `OPEN_ITEMS`.

## What T12 does not claim

- No reconstruction quality beyond Freeze B and evaluation attempt 1. T12's comparators and gates are interface demonstrations on synthetic
  or recorded development data; a T12 pass never gives a recipe a new quality pass (T12-09).
- No speed claim for T07 (failed at attempt 1), none for any recipe before its quality gate, and no GPU speed number at the scan sizes.
  The CPU and GPU timings are records for these runs and nodes, not targets (K12).
- No byte reproducibility across node classes, and no numerical or statistical reproducibility for any recipe but the destriper on the
  record's pointing and the T07 CKF fake rate by F2.
- No P4 execution completeness (8 gaps), no A-scenario confirmed by a backend it does not have, and no native scan or global solver.
- No qualification of the control layer's rules (G07, mode M1).

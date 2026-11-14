# T12 stage plan: reprocessing and performance (finish-plan F2)

State: stage 0 and stage 1 committed (`0e310d34`; job of record 7606257 PASS). Stage 2 drafted on branch `t12/stage2` (from `4c08da43`,
after Freeze B and D4); not reviewed, not committed. The "Stage 2" section below was written before stage 2's tests (red logs with file
hashes in `jobs/t12-stage2/red/`). Paths are relative to
`plugins/hep-research/`. Sources: plan v9.2 §16.1 row T12, R14, R20, R30, R36, R37 (T12 item), §9.3-9.9, §10.2, §10.4, §14.1-14.2, §9.6
with A37, G05 and G06; t05-task-sheets.md (T12 row: depends on T07-T10, A13 `blocked-by-resource`), contract-map.md (G05, Section 10.4
row), calibration-alignment-interfaces.md (R36 rows), decisions.md (K07; U8 "Use the site GPU partition", 2026-11-12) and
`skills/hep-detector/references/calibration-and-alignment.md` ("Iterative loops as contract steps").

T12 depends on T07-T10. T07, T08 and T09 are closed out and wait for Freeze B; T10 is not done. Stage 1 starts anyway on the authority of
finish-plan F2 and the coordinator's T12 lane (decisions.md, "The user's answers: parallel lanes and U8", 2026-11-12; the stage 1 brief), not
R24's prerequisite rule. Stage 1 needs none of them: R37 makes
`CAI-T12-1` and `CAI-T12-2` interface tests on a synthetic loop that wait for no frozen K09 threshold. Nothing in T12 is a quality claim
until Freeze B fixes K09.

## Stages

| Stage | Content | Waits for |
| --- | --- | --- |
| 0 | This plan | none |
| 1 | `CAI-T12-1`, `CAI-T12-2`: the synthetic two-round loop (R37), below | none |
| 2 | Conditions invalidation and identity: A04, A40, A42, A14, G05, §9.3, §9.8-9.9 (T12-05 to T12-09, T12-24 to T12-27) | Freeze B (given); drafted, see "Stage 2" |
| 3 | Partitioning, recovery and boundaries: A11, A12, §10.2 items 3-7 (T12-10 to T12-12) | Stage 2 (done); Freeze B for the T07-T09 recipes' quality; drafted on `t12/stage3` (from `28763f50`), see "Stage 3" |
| 4 | Comparators and CPU benchmarks: §14.1, §14.2, A15, quality before speed | Freeze B (given), T10 (done); part A (T12-13, T12-15) done: job of record 7648553 PASS after a fresh review and two fix rounds, merged into feature, see "Stage 4"; part B (T12-14) taken by stage 5 on branch `t12/stage5-a13` (from `d1f6fc30`), see "Stage 5" |
| 5 | A13 reopened by the user (2026-11-13, "A13: GPU part: allow use GPU"; Q1 superseded): the T10 destriper's baseline solve on the GPU (`b6000-al9_devel`) against the CPU recipe; T12-14 (stage 4 part B) and T12-22 with it; drafted on `t12/stage5-a13`, see "Stage 5" | Stage 4 part A (done); the user's word (given) |
| 6 | A37 and §9.6 in T12: the g×E degeneracy and the weak-mode witness | none (Q3 answered, Q5 moot: T10 done); drafted on branch `t12/stage6`, see "Stage 6" |
| 7 | A10, A26-A36 runtime (R20: T11 design, T12 runtime) | T11 design (F1); a backend per family, else a recorded gap |

## Obligations

"Waits" names T10, Freeze B (FB), the GPU, or none. Stage 1's tolerances and expectations are fixed in the next section, before any code.

| ID | Source | Obligation | Acceptance; negative case | Prerequisite | Stage | Waits |
| --- | --- | --- | --- | --- | --- | --- |
| T12-01 | R37 T12, R36 | `CAI-T12-1`: synthetic two-round loop, round-2 payloads differ, both checks pass at round 2, final outputs released | Section "Stage 1" items L1-L8; planted defects P1-P5 each detected with its exact failed set | T06 interfaces (tested) | 1 | none |
| T12-02 | R37 T12, R36 | `CAI-T12-2`: same contract, the convergence check fails at round 2; final step held, nothing released, the non-convergence stays in the history | Items H1-H6 (H1-H5 asserted by `assess`, H6 its exit 0); a later pass never rewrites the fail (H4) | T06 interfaces | 1 | none |
| T12-03 | R37, §9.6, A37 | The placeholder convergence and unconstrained-mode checks never satisfy A37 | The loop record states `a37: not satisfied by this fixture`; no A37 row moves | none | 1 | none |
| T12-04 | G06, §9.7 | The fixed final-round rule is not changed: rounds exactly 1..final, no early stop, no extra round without a human | Contract with a missing round, two checked final steps, a round-1 deliverable, or a not-applicable convergence check is refused (C1-C4) | none | 1 | none |
| T12-05 | A04, §9.9 row 1 | Payload content changes under the same tag: recompute locally when the dependencies are complete, else broaden | On T07-T09 products: a same-tag payload change gives `reuse: false` and a rerun of exactly the affected steps; an unknown dependency disables reuse | T07-T09 merged | 2 | FB for quality reuse |
| T12-06 | A40, §9.8, U11 | Native binary, library, build or configuration changed under an unchanged Python wrapper and manifest: refresh the identity before every reuse decision | A rebuilt ACTS driver with a changed byte (same `.py` files) is not reused; reuse decided only after a fresh hash of every declared native input; stale stored identity refused | G05 change in `run_workflow.py` (T12-07) | 2 | none |
| T12-07 | G05, contract-map row `run_workflow.py` | Native binaries, libraries and configurations enter `run_workflow.py` as declared inputs with their own identity | A receipt lists the native inputs' SHA-256; an undeclared native file changing is a broadened rerun, never a reuse; old `.py`-only recipes unchanged | none | 2 | none |
| T12-08 | A42 | Worktree scope: imports, executables or outputs from the main checkout or a shared mutable folder are detected | A job run from a snapshot whose import path reaches the live tree is refused; a Git path alone is not isolation | none | 2 | none |
| T12-09 | A14, U12, §9.8 last paragraphs | Computational reuse is separate from quality reuse: a skip or an old exit 0 never gives a new quality pass | After a checker or criterion change, a reused product has no pass until the check runs again under the current rules; old fail and inconclusive stay | FB (the checks under K09) | 2 | FB |
| T12-10 | A11, §10.2 items 4-6 | Partition boundaries add no omissions or duplicates; gaps enter exposure | Merged ranges equal a single pass for T07-T09 by object key; a dropped range is "required output missing" | Stage 2 | 3 | FB for quality |
| T12-11 | A12, §10.2 item 7, §10.5 | Native async, OOM or timeout: complete or fail explicitly; never an old artifact | A killed range leaves no output that passes; a resubmission does not reuse a partial file; no retry without a configured count | Stage 2 | 3 | none |
| T12-12 | §10.2 item 3 | Processing accounts: success, exclusion, failure, unconfirmed per stable scope | Every source event is in exactly one category; an empty collection is not a failure | Stage 2 | 3 | none |
| T12-13 | §14.1 | Comparators for byte, numerical and statistical reproducibility, declared per recipe | A reordering passes, a changed association fails, each with its fixed tolerance | FB (tolerances with K09) | 4 | FB |
| T12-14 | §14.2 | CPU engineering benchmark: the same scientific work, each component timed apart, overlap stated | Report reading, initialization, I/O, conditions, conversion, compute and checks separately, with success and failure denominators ("Stage 5" C1-C8: destriper, T08, T09; T07 not measured, failed gate) | Stage 3 | 4 (taken by stage 5) | none (FB given, T10 done) |
| T12-15 | A15, A50, §16.1 "quality before speed" | A faster variant with worse tails or coverage is rejected under fixed gates or listed as another working point | A planted faster variant with a fatter tail fails the gate; no speed number is reported before the quality gate | K09 frozen | 4 | FB |
| T12-16 | A13, R30, U8 | GPU subchain against CPU: include transfer, initialization and queues; compare quality at a fixed reproducibility level | Reopened by the user (2026-11-13). The destriper's baseline solve in PyTorch float64 on `cuda` against the CPU recipe: on the frozen pointing the stage 4 numerical comparator with T10's frozen tolerance (OI-8) passes; on larger scans the answer is `incomplete` (OI-12), never a pass; queue, initialization, transfers, compute and checks timed apart; speed only after the gate ("Stage 5" G1-G8) | R30 hardware job 7648670 (PASS) | 5 | GPU |
| T12-17 | R14, Q1 (superseded) | The CPU measurements recorded beside A13 | T12-14's destriper timings on the same sizes, released on the recipe's quality record, recorded beside each A13 row; R14's `blocked-by-resource` no longer applies (a GPU is chosen, R30 done) | Stage 5 (T12-14) | 5 | none |
| T12-18 | A37, §9.6 | g×E degeneracy: convergence and same-type holdouts are no proof of absolute scale; identifiable combinations and named constraints retained | A two-parameter synthetic fit of `y = gE` reports only `gE` (or a named external scale); a same-type holdout is not accepted as validation | Q3 | 6 | T10 (shared fixture) |
| T12-19 | A37, §9.6, R31 (weak-mode witness) | The T07 weak-mode fixture reused in T12: χ²/ndf essentially unchanged while `q/p` is biased; the method card lists the mode and its named constraint | Reuse `CAI-T07-4`'s fixture 7004 against 7003 inside a T12 reprocessing; the card lists `sagitta-like deformation` with its constraint | T07 merged | 6 | T10 |
| T12-20 | R20, A26-A36 | A26-A36 runtime: injection before filtering, scan settings, per-channel exposure, angle bases, CRES first segment, averaged spectra, IRF reuse, veto-only scintillation, null modes, frame definitions, injected data labels | One executed case per scenario on a backend that covers it; otherwise a recorded gap keeping P4 execution incomplete | T11 design (F1) | 7 | none (backend absent: gap) |
| T12-21 | §16.1 T12 row, A10 | Waveform omitted: higher-level parameters usable; trace-requiring recomputation judged infeasible | A product with `raw` retention removed refuses a trace rerun (`can_recompute` false) inside a T12 reprocessing | T08 merged | 7 | none |
| T12-22 | §10.4, contract-map Section 10.4 row | Execution fields beyond concurrency, layout, residence and ownership: transfer edges, precision, batch and memory limits, streaming queues | Written for the GPU subchain only ("Stage 5", T12-22), with measured transfers and device memory; streaming queues not applicable (offline); the CPU recipe's CLI gets no GPU field | Stage 5 | 5 | GPU |
| T12-24 | §9.9 row 2, §9.3 | An IOV crossing a chunk: subdivide, resolve per observation or use a time-varying model | On a T07-T09 product split across a payload change: each part binds its own payload (the per-key frames of T06, `check_frame_conditions`, carried into reprocessing); the first event's payload on the whole chunk is refused | T07-T09 merged | 2 | none |
| T12-25 | §9.9 rows 3-4, A32 | Clustering, cleaning, cut, model, noise, template or transform changes invalidate by effective dependency and keep different-version results | A changed T08 configuration digest reruns the calo products and their response pairing; old and new products both kept | T07-T09 merged | 2 | FB for response revalidation |
| T12-26 | §9.9 row 6 | Report title or non-scientific metadata only: scientific results unchanged; integrity manifests and presentation updated apart | A metadata-only change keeps every scientific product's identity; only the presentation product and its manifest change | none | 2 | none |
| T12-27 | §9.9 closing paragraph | Configuration identity includes effective defaults, seed and RNG policy, precision, candidate, iteration and resource limits | A changed default, seed policy or budget changes the configuration digest and is never reused; a resource-limit change asks whether response revalidation is needed | none | 2 | FB for response revalidation |
| T12-23 | R11, R25 | Each stage's evidence: a snapshot job with a manifest, predictions fixed before it runs | The stage report gives job IDs, manifest hashes, predictions and readings | none | every | none |

## Stage 1: the synthetic two-round loop (fixed before the tests were written)

**Where.** `tests/contracts/t12_outer_loop.py` (the harness: fixture contract, synthetic recipe, synthetic derivation, the two placeholder
checks, the loop driver and its record) and `tests/contracts/test_t12_outer_loop.py`. Tests may import both the contracts and the control
layer (`tools/check_layering.py`: tests import anything; an adapter could not import the control layer), so the harness lives in `tests/`.
It uses the existing interfaces only: `contracts/conditions.py` (`payload_identity`, `check_used`, `reuse_decision`), the R32 sidecars, and
the control layer's derivation (`skills/hep-computing/scripts/control_layer_support/derivation.py`: families, final-round gating, labels
`iteration_internal` and `superseded_by_iteration`, publish). The control rules are not qualified (G07, mode M1): agreement shows the
interface behaves as those rules say, nothing more.

**Synthetic fixture.** Eight channels `c = 0..7`, four hits per channel, reference energy `E_ref = 1` (arbitrary unit, the "synthetic
reference energy" constraint). Generated gain `G_c = 1 + d_c`, `d_c = D (c - 3.5) / 3.5`; `D = 0.02` for `CAI-T12-1` (converging),
`D = 0.20` for `CAI-T12-2` (non-converging). Hit ADC `= G_c E_ref` exactly. Reconstruction: `E = ADC / g_c` with the consumed gain payload.
Derivation (placeholder, no quality meaning): `g_n,c = g_(n-1),c + (mean_c(E) - E_ref) g_(n-1),c / 2`, so in closed form
`g_1 = 1 + d/2`, `g_2 = 1 + 3d/4`. The nominal payload has `g_0 = 1`, `origin` nominal, no `loop`; round payloads have
`loop {family t12-synthetic-gain, round n}`, `origin` measured (R32 allows nominal or measured only; producer the step, source synthetic),
one tag `t12_synthetic_gain` for all three, so identities, not tags, separate them. Fix round 1 (I5, the coordinator's ruling, which
reverses the stage-0 Q4 reading): a round payload records the payload of the previous round in both `derived_against.upstream_payloads`
(`[previous payload_id]`) and `derived_from` (the previous `payload_id`): round 1 the nominal payload, round 2 round 1's. Its
`producer.step_id` is the producing step's computational identity from the control layer (the intent's `identity`, Control §4.2), so a
rerun with other inputs has another producer. `affected_payloads` then follows the rounds: a change of round 1 affects round 2, a change of
the nominal payload affects both.

**Contract (fixed; family `t12-synthetic-gain`, final round 2).** Steps: `nominal-gain` (outside the loop), `reco-r1` (round 1, consumes
`nominal-gain`), `derive-r1` (round 1, consumes `reco-r1`), `reco-r2` (round 2, consumes `derive-r1`), `derive-r2` (round 2, consumes
`reco-r2` and `derive-r1`; the final step: checked, requires the convergence and unconstrained-mode checks, the convergence check reads
`derive-r1`), `reco-final` (outside the loop, consumes `derive-r2`; checked by the record check). Deliverables `final-gain` (`derive-r2`) and
`final-product` (`reco-final`), tier T2. Session mode M1.

**Checks, fixed by digest.** Each check digest is `canonical_sha256({"source": <the check function's source>})`, each criterion digest
`canonical_sha256(<its criterion>)` (`contracts/recipe_semantics.py`). Pinned values (fix round 1, M4; the test asserts them literally, and a
changed check needs a deliberate change here and in the test):

| Check | Check digest | Criterion digest |
| --- | --- | --- |
| convergence | `b46a97f9e5648140ca50266cb6f97c36ae83102b4b0f0037b7315f964140eb11` | `c917f155c8e428fa8eff6c9cb487be3e93bb17a25d63c6ecb187716b651a6eed` |
| unconstrained-mode | `a386952dcd38dac23ef767c734f7617d35b71c099c80d4ab8e804a19f04d6399` | `3b50666832ebdb8aadb2c04f4d4d8cdedfeefb4ca56aaf2443ae4ea006a76f10` |
| record | `5994228c8f69a70fc5c8e722b1d0584f6edcc19777012fb97ff1439c117fd994` | `2588325e331c11c5608ce39d7e540bef63d3d83eea1d22b62b6c55f29537662a` |

- Convergence (placeholder): `max_c |g_2,c / g_1,c - 1| <= tau`, `tau = 0.01`. Closed form `|d| / 4 / (1 + d/2)`: largest 0.0050505 for
  `D = 0.02` (pass), 0.0555556 for `D = 0.20` (fail). The harness's metric must equal the closed form to `1e-12` relative.
- Unconstrained-mode (placeholder): the final payload lists `unconstrained_modes == ["mode.global-gain-scale"]`, `constraints_used ==
  ["constraint.synthetic-reference-energy"]`, and no constraint used is cited as its validation. Passes in both variants; fails in plant P5.
- Record check (on `reco-final`): `check_used` of the product against the final payload has no error, and its round is 2.

**Tolerances.** Every check above is deterministic; gains and energies are compared with the closed form to `1e-12` relative. There is no
statistical check in this fixture, so no `n σ` and no `k` (R37's statistical rule has nothing to apply to).

**`CAI-T12-1` expectations (converging).**
- L1. Every step ran once, in contract order (the record's `order`); round-2 payload identities differ from round 1's (and both from
  nominal) under one tag; each round payload names the previous one in `upstream_payloads` and `derived_from` and its producing step's
  identity as `producer.step_id`.
- L2. Each product records the identity and round it consumed: `reco-r1` the nominal payload, round null; `reco-r2` round 1; `reco-final`
  round 2. `check_used` passes for each against its payload.
- L3. Cache (fix round 1, I2): before every reconstruction step the harness asks `reuse_decision` of every cached product of the same recipe
  (`t12.reconstruct/1` on the same hits) with the payload resolved afresh, and acts on a hit only through `dv.admit(..., reuse_source=...)`;
  an admission refusal falls back to a computation and is recorded. Across differing payloads the answer is `reuse: false` (`reco-r2`
  against `reco-r1`; `reco-final` against both), nothing is acted on, and each step is computed. Positive control: requesting `reco-final`
  again through the same path, with the same payload, gives `reuse: true` and a control-layer `reuse` fact, not a new computation. A
  control-layer reuse of `reco-r1`'s product as `reco-r2` is refused at admission.
- L4. Steps outside the loop consume only the final round: `reco-final`'s consumed input is `derive-r2`'s artifact.
- L5. Labels (control layer): `reco-r1`, `derive-r1`: `superseded_by_iteration`; `reco-r2`: `iteration_internal`; `derive-r2`, `reco-final`,
  `nominal-gain`: `ok`.
- L6. Both checks pass on `derive-r2`; the record check passes on `reco-final`.
- L7. Both deliverables are published at T2, each publish naming the bound artifact.
- L8. The record says synthetic, no quality claim, A37 not satisfied.

**`CAI-T12-2` expectations (non-converging, same contract).**
- H1. Rounds 1 and 2 run as in L1-L3; the convergence check fails on `derive-r2` (metric 0.0555556 > 0.01), the mode check passes.
- H2. `derive-r2` is labelled `held`; `reco-final` is not run (the harness holds every step outside the loop) and neither deliverable is
  published: `publish` refuses both (the control layer's "deliverable not met").
- H3. Non-final labels as L5 (`superseded_by_iteration`, `iteration_internal`).
- H4. The failure stays in the history: `prior_failures` of `final-gain`'s chain holds it; a later pass result for the same check on the same
  artifact leaves it `held` (never rewritten as converged).
- H5. Forcing `reco-final` anyway gives a product labelled `blocked_upstream`, and publish still refuses.
- H6. The harness exits 0: the hold is the expected result of this interface test, not a T12 failure.

**Planted defects (each must be detected by the harness's assessment, exit 1; fix round 1, I1: the failed set is asserted exactly).**
- P1 `wrong-round`: `reco-r2` records round 2 for a round-1 payload. Failed `{L2}` (`conditions.round_mismatch`). The control layer
  still publishes both deliverables: its gating does not read R32 records (see "Open findings").
- P2 `reuse-across-payloads`: the cache lookup compares tags instead of identities, so `reco-r2` gets a hit on `reco-r1`'s product (same
  tag, other payload) and acts on it through `dv.admit(reuse_source=...)`; the control layer refuses it (another step), and the step is
  computed. Failed `{L3}`: a decision acted on across differing payloads.
- P3 `outside-consumes-round-1`: the contract wires `reco-final` to `derive-r1`. The identity-correct lookup now finds `reco-r2`'s
  product (same recipe, same round-1 payload), acts on it, is refused at admission (another step), and computes. The record check fails
  (`conditions.unknown_payload` against the final payload; round 1, not 2); `reco-final` is `invalidated` and not published; the final gain
  is published. Failed `{L2, L3, L4, L5, L6, L7}`.
- P4 `skip-final-checks`: the harness publishes without running the checks: `derive-r2` `unchecked`, `reco-final` `blocked_upstream`,
  nothing published. Failed `{L5, L6, L7}`.
- P5 `mode-unconstrained`: the final payload lists no unconstrained mode (`unconstrained_modes: []`). The unconstrained-mode check fails,
  the convergence check passes, `derive-r2` is `held`, `reco-final` is not run and nothing is published. Failed `{L1, L2, L3, L4, L5,
  L6, L7}`.

**Open findings of the loop fixture (fix round 1, I4; also in calibration-alignment-interfaces.md, "Open, not gaps").**
- The control layer's gating does not read R32 records: an intermediate product recording the wrong round (P1) stays usable, and both
  deliverables are published. The harness catches it with `check_used` (L2); the record check runs only on `reco-final`.
- `validate_contract` accepts a step outside the loop wired to a round-1 step (P3). The control layer catches it only when it labels the
  product (`invalidated`, not deliverable), not at contract time, although the calibration reference says steps outside the loop consume
  only the final step. The harness catches it (L4).

**Contract refusals (C1-C4).** C1 a family without round 1 ("rounds must be exactly 1..final_round"), C2 two checked final-round steps
("exactly one checked step"), C3 a round-1 deliverable, refused by the checked-step rule ("only the family's final step is checked") before
the deliverable rule is reached, which it implies, C4 a not-applicable convergence check ("cannot be not-applicable"); each refused by
`validate_contract` with that message (G06: the fixed final-round rule).

**Exit codes (core/status.py, fix round 1, I3).** `t12_outer_loop.py run --variant converging|non-converging [--plant P] --out FILE`: status
`ok` exit 0, every expectation of the variant holds; `failed` exit 1, one does not (a planted defect is detected); `rejected` exit 2, bad
input (unknown variant or plant, an output file that exists: a record is never overwritten, a missing folder); `incomplete` exit 3, the
harness could not run or the record could not be written. Exit codes come from `core.status.exit_code`.

## Stage 2: conditions, invalidation and identity (fixed before the tests were written)

**Split, and why.** Stage 2 takes T12-05 to T12-09 and T12-24 to T12-27 only. T12-10 to T12-12 (partition and accounts) become stage 3 and
T12-13 (comparators) stage 4. Reasons: stage 2 changes a shared runner (`skills/hep-computing/scripts/run_workflow.py`, G05), which every
workflow uses and which deserves a review of its own; stage 3 needs multi-range recorded products and the E6 range layout; stage 4 needs
each recipe's reproducibility level and tolerances read from Freeze B. One reviewed stage cannot hold all three. T10 is still in progress,
so nothing here touches T10's recipe. A13 is recorded `blocked-by-resource` (Q1 answered), with no GPU job.

**Inputs.** Synthetic DAGs, conditions-payload/1 sidecars built here, and frozen recorded files read only, by SHA-256: the T08
configuration `adapters/calo-cluster/assets/t08-grid-1.configuration.json` and the T09 budget
`adapters/photon-likelihood/assets/t09-multistart-1.budget.json` (Freeze B items; never edited: a changed configuration is a copy in a
scratch folder). No recipe, frozen file or file of `jobs/evaluation/SOURCES.sha256` changes. No quality claim.

**Files.** Production: `skills/hep-computing/scripts/run_workflow.py` (G05), with its documentation in its docstring. Tests:
`tests/skills/hep_computing/test_workflow_native.py` (the runner) and `tests/contracts/test_t12_reprocessing.py` with its harness
`tests/contracts/t12_reprocessing.py` (reprocessing scenarios, the scope check, the configuration classifier, the chunk binder).

**The runner change (T12-07, T12-06).** All comparisons exact.
- N1. A step may declare `"native_inputs": [PATH, ...]`: native binaries, libraries, configurations. Each PATH takes the placeholders
  (`{plugin}`, `{workflow}`) or is absolute or relative to the work folder. Each is hashed when the step's record is formed, in every run,
  before the skip decision (a fresh identity, never a stored one), and recorded as `extension.native_sha256` {PATH as written: SHA-256};
  the receipt lists them as `native_inputs` [{path, sha256}]. A declared native input that is missing or not a regular file: `rejected`,
  exit 2, nothing run.
- N2. `--incremental` skips a step only if its `native_sha256` equals the previous record's. One changed byte in a declared native input
  reruns the step ("a native input changed"); an unchanged one keeps the skip.
- N3. An executable file named in argv (after placeholder filling; not the running interpreter, not a `.py` script, not a declared native
  input) is undeclared: recorded as `extension.undeclared_native` [token as written], and the step is never skipped ("an undeclared native
  file is in argv: its identity is not closed (G05)"). That is the broadened rerun of §9.4; a reuse is never granted.
- N4. Old recipes are unchanged: a step without `native_inputs` and without an undeclared executable writes a run record and a receipt
  with no new key, byte-identical to the runner at `4c08da43` (the shipped workflow's records compared), and keeps its skip behaviour.
- N6 (T12-27, seed policy). The skip rule also compares the step's `seeds` (recorded in the run record but, at `4c08da43`, not compared:
  a seed change that left argv unchanged kept the old record with the old seeds). A changed `seeds` reruns the step; unchanged seeds keep
  the skip.
- N5. Limits stated in the docstring: libraries loaded but not named are not observed (§9.8: within the binding's observable scope);
  `native_inputs` is what the caller declares.

**Reprocessing scenarios (harness; DAG `calibrate` -> `cluster` -> `response` -> `report`, plus `pedestal-monitor`; run by
`run_workflow.py --incremental`).** `calibrate` reads the gain payload sidecar, `pedestal-monitor` the pedestal sidecar, `cluster` the
T08 configuration (a byte copy), `report` a presentation file (title). Every step script is written by the harness; the native case uses a
small executable written by the harness as a stand-in for a native binary.
- R1 (T12-05, A04). The gain payload's content changes under the same tag (re-sealed: new `payload_id`, same tag). The rerun set is exactly
  {calibrate, cluster, response, report}; `pedestal-monitor` is skipped with its outputs unchanged. `reuse_decision` refuses the old
  `calibrate` product under the new payload and allows it under the old one.
- R2 (T12-05, broadening). A step that declares unknown closure (an undeclared executable in argv, N3) reruns on every incremental run
  even with nothing changed; `reuse_decision(..., unknown_dependencies=True)` refuses.
- R3 (T12-06, A40). The stand-in native binary of `cluster` changes one byte; the Python wrapper and the workflow file are unchanged.
  `cluster` reruns; downstream reruns exactly when `cluster`'s output changed (here the rebuilt stand-in writes another `tool` field, so
  `response` and `report` rerun; a byte change that leaves the output equal reruns `cluster` only); nothing upstream does. A manifest of native hashes left from the last run (a declared input
  file, unchanged) does not make the step skip: the binary itself is hashed afresh (§9.8: rehashing an old manifest is insufficient).
- R4 (T12-25, A32). The T08 configuration copy changes one constant (`seed_threshold_mev` 10.0 -> 12.0). Its identity
  (`configuration.from_bytes(...).sha256`, the recipe's own) changes; `cluster` writes to `products/<configuration sha256>/`, so the old and new
  products are both kept; `response` and `report` rerun with the new pairing; `calibrate` and `pedestal-monitor` are skipped.
- R5 (T12-26). Only the report title changes: only `report` reruns; every scientific output and run record is byte-identical. Recorded
  finding, not a defect: the T08 configuration identity is the SHA-256 of the file's bytes, so its `source` text (non-scientific) is in
  it, and a `source`-only edit reruns `cluster` (a conservative broadening, allowed by §9.4).
- R6 (T12-27). `configuration_change(old, new)` classifies changed keys: T08 constants (thresholds, quantum, noise, width, sharing
  iterations, grid) as `physics: response revalidation required`; T09 multistart budget keys (`starts`, `tie_tolerance`) as
  `candidate or resource limit: response revalidation to be judged`; `format`, `recipe` as `identity`; `source` as `metadata`. A T08
  configuration with a key removed (a value left to a default) is refused by the recipe's reader, so effective defaults are always written
  out; a changed iteration limit or budget changes the identity. The T08 recipe is deterministic (no seed); the seed policy row is shown on
  the runner's `seeds` field (N6).
- R7 (T12-09, A14, U12). Control layer (as stage 1): an artifact with a pass under criterion A; a stricter contract adds criterion B.
  The artifact is `unchecked` (no pass) until B's check runs; a `reuse` of it gives no result; its old fail under another criterion stays
  in `historical_failures`. Runner: a skipped step writes no receipt (no new evidence), and an earlier receipt is never replaced.
- R8 (T12-24, §9.3). `bind_chunk(keys, payloads)` binds each key to the one payload whose IOV holds it (`iov_holds`); a chunk crossing an
  IOV boundary is subdivided (keys 40-59 over IOVs [0, 50) and [50, 100) give 40-49 and 50-59); a key with no payload or two is refused;
  `check_chunk_binding` refuses a binding that applies the first key's payload to the whole chunk.
- R9 (T12-08, A42). `scope_check(snapshot, live, outputs)` runs in the job's process: every `sys.path` entry, every loaded module's file,
  the working folder and each output path must lie outside every live root (resolved, symlinks followed). A module imported from a live
  root, an output under one, or a working folder inside one is refused (`rejected`, exit 2); a Git worktree path alone proves nothing (a
  run whose working folder is a clean worktree but which imports from the main checkout is refused). The job of record runs it on itself
  from the snapshot copy.

**Exit codes.** `t12_reprocessing.py scope-check --snapshot DIR --live DIR [--live DIR ...] [--evidence-path PATH ...]`: `ok` 0, `rejected` 2
with the offending paths, `incomplete` 3; from `core.status.exit_code`.

### Stage 2, fix round 1 (review `jobs/t12-stage2/REVIEW.md`; written before the changed tests)

**What changed after green-1 (M9).** Between green-1 and green-2 three renames only, for the naming check, and the reference inventory
regenerated: the harness's `configuration_change(old, new)` parameter `new` became `changed`; the scope check's `--output` became
`--evidence-path` (harness, its test and the plan's exit-code line). No expectation, rule or value changed.

**Which scenarios test new behaviour (M4).** New behaviour: N1-N3, N6 and R2, R3 (the runner change), R8 and R9 (harness functions). R1,
R4, R5 and R7 characterise behaviour that existed at `4c08da43` (input hashes, the output contract, the control layer); they pass on the base
runner, and their red-2 failures came from the stub harness. R6 is a specification table (the harness's categories), not a demonstrated
classifier: what it shows beyond the table is that the frozen T08 and T09 files have no uncategorised key, that the recipe's reader refuses
a missing default, and that the identity changes with a limit.

**Changed expectations.**
- N3' (I1, I2: replaces N3). Only the program and an interpreter-run script are examined, so existing workflows keep their skip:
  - the program is `argv[0]` after placeholder filling, a bare name resolved through `PATH` (`shutil.which`); if it is not the running
    interpreter and not declared (an input or a native input), it is undeclared;
  - if the program is an interpreter of scripts (`sh`, `bash`, `dash`, `zsh`, `ksh`, `root`, `root.exe`, `Rscript`, `perl`, `ruby`, `node`),
    the first later token that names an existing regular file (for `root`, with a trailing `(...)` argument list removed) is its script; if it
    is not a `.py` file and not declared, it is undeclared. The interpreter itself is not hashed (a system program; a limit);
  - an executable named in any other argv token (an option value such as `--exe /path/prog`) is not examined: it is closed only when
    declared. This is the limit that keeps the generated Geant4 scan (`geant4_run.py scan`, `--exe` as an option value) skipping as at
    `4c08da43` when nothing changed;
  - an undeclared program or script is recorded in `extension.undeclared_native` and its step is never skipped.
  Workflows in this plugin whose program is not `{python}` (searched: `"argv": [` in the plugin): `ENV_ROOT/bin/python3` and
  `ENV_ROOT/allpix/bin/allpix` (detector-simulation backends, not run through `--incremental`), `scancel` (a Slurm shim), and the test-only
  `bin/legacy-tool`, `bin/cluster-tool`, `./native-tool`, `ENV_ROOT/bin/synthetic-sim`. None of them is an incremental workflow that skipped
  before; if one is run with `--incremental`, its program must be declared or it reruns.
- N7 (I1). `geant4_run.py scan` writes each step's `native_inputs` as `[<exe>, <build record>]`, in the same `~/` or absolute form as
  its `--exe` and `--build-record` options. The runner expands a leading `~/` in a native input. A generated scan workflow skips when nothing
  changed and reruns every step when one byte of the executable changes, with the executable outside home and under home.
- N1' (I3). Every native input that is absolute, starts with `~`, or uses a placeholder is checked before the first step runs: a missing
  one is `rejected` (exit 2) and no step has run. A work-relative native input (which an earlier step may write) is checked when its step
  is reached; that refusal also writes nothing of that step. A relative native input with `..` is refused when the workflow is loaded, as
  `inputs` are (M2); a native input that cannot be read is `rejected`, never a traceback (M2).
- N4' (M1). Old records keep exactly the key sets of the runner at `4c08da43` (the record and receipt key sets are pinned in the test);
  the diff adds keys only when declared, so values of existing keys are unchanged. "Byte-identical" is not claimed.
- N5' (M3). The docstring and analysis-workflows.md recommend placeholders (`{plugin}`, `{workflow}`) or work-relative paths in
  `native_inputs`, because an absolute path is written into the record as given.
- R8' (M6). `check_chunk_binding(binding, payloads, keys)` reports keys whose payload's IOV does not hold them, keys of the chunk no part
  covers, and keys two parts cover; `[{"keys": [40, 49], low}]` for the chunk 40-59 reports 50-59 uncovered. Each payload's own coordinate
  is used.
- R9' (M7, I5). The scope check also reports a namespace package whose search locations lie under a live root, and the running
  interpreter (`sys.executable`, resolved) under a live root. In the job it imports the modules under test (`--import`) and takes the live
  roots from `git worktree list --porcelain` of the checkout.

## Stage 3: partitioning, recovery and boundaries (fixed before the tests were written)

**Scope.** T12-10 (A11; §10.2 items 4-6), T12-11 (A12; §10.2 item 7, §10.5) and T12-12 (§10.2 item 3), and stage 2's concern (1): a
recorded T07 refit product. Nothing here is a quality claim: Freeze B's gates judge the recipes' quality, and this stage asks only whether
ranges, attempts and accounts lose, duplicate or invent observations. A13 stays `blocked-by-resource` (Q1).

**Files.** `tests/contracts/t12_partition.py` (the harness) and `tests/contracts/test_t12_partition.py`. No production file changes:
the runner cases (K5-K8) characterise `skills/hep-computing/scripts/run_workflow.py` as it is at `28763f50`, and the range and attempt
rules come from the E6 evaluation layout `tests/adapters/t04_evaluation_layout.py` (fix round 1, m4: SHA-256 `0cf7e2c1a8e4e645...` at
`28763f50`; Freeze B recorded its earlier state `185574f8...` beside the freeze, and the file changed after it), imported, never edited:
`EventRange`, `check_ranges`, `RangeRecord`, `classify_attempt`, `select_attempt`, `classify_t07_by_index` (which calls
`compare_t07_by_index`).
The harness adds what the layout does not have: object keys for the T07 refit product and for the JSON Lines products, a merge by key
with a header rule, a range collection that also reads the T07 refit product, per-event accounts and exposure.

**Inputs, read only, by SHA-256.**
- Recorded single-pass products, tracked (two events each): `examples/reconstruction-tracking/recorded/refit.product` (T07,
  `reco.track.acts-kf-refit/1`, 12 tracks; `a02d04b0b9d522eec9d6923fe79b406ab95477906eb3e3af23eac3231875495b`),
  `examples/reconstruction-calorimetry/recorded/events.product` (T08; `1107dcec6509d236f13954439d650384f389bab0a32096df6bb82f76fd729cc8`),
  `examples/reconstruction-photon-likelihood/recorded/main.multistart.product` (T09 /3;
  `9d44ae712dc4b758cc9cbd4311c17fd1e31568cccd6377250c65aeaa60eee6b1`) and `main.topology.product` (T09 /4;
  `b42cb36ace58a8a31c24fb8b8af0d0502d188dd8fad91e8598ee5b2ef1133150`). The unit tests cut each into ranges by the harness and merge
  them back: this exercises the keys, the merge and the collection on the recipes' real formats; it does not show that a recipe run on a
  range equals the full run (a cut of one run cannot).
- Block-1 range runs, private evidence, for the job of record only (`t12_partition.py recorded`): the E6a job 7591439 (folder
  `d4-e6a-7591439`), where each recipe ran on the full sample and on separate ranges: T07 clean and noise (`acts-ckf-planar`, block 1
  stratum 2, 150 events, ranges 0:50, 50:70, 120:30; two full runs), T08 main (600 events: 0:200, 200:250, 450:150) and dead (300 events:
  0:100, 100:200), T09 main stratum 9 multistart and topology (40 events: 0:13, 13:18, 31:9); and the E6b job 7591993 (folder
  `d4-e6b-7591993`), T07 clean block 1 stratum 4: three refit range products (`acts-kf-refit`, events 0-999, 1000-1999, 2000-2999) and
  the collection file naming them. Each file's SHA-256 is pinned in the harness (`RECORDED`); a different or missing file is `rejected`.
  The E6b job is round 0 (its round 1, 7592299, deleted its refit products); no single-pass refit of those 3,000 events was kept, so the
  refit ranges are checked for completeness and disjointness by key, not against a single pass.

**Object keys (M1).**
- T07 refit (`acts-tracking-product/2`): an object line is one of the seven sections `track`, `state`, `parameters`, `track_output`,
  `residual`, `measurement_output`, `residual_covariance`; its key is (section, its second token, e.g. `event-1000-track-3`, and its
  occurrence among the lines of that section and token, in file order); its event is the integer after `event-`; its value is the line.
  The end line `end c1 ... c7` must give each section's line count in that order (the recorded refit products follow it); otherwise the
  product is truncated and refused. Refit range products key events globally (E6b), so no renumbering.
- JSON Lines (T08 `calo-cluster-product/1`, T09 `light-likelihood-product/3` and `/4`): header, event lines numbered 0, 1, ... in order,
  end line whose `events` is their count (else refused, as `layout.product_events`). Event line i of the range from f has key
  (`event`, f + i) and value the parsed object with `event` set to f + i (parsed values compared, so number formatting cannot hide or
  invent a difference; JSON floats round-trip exactly).
- T07 finding products (`acts-ckf-planar`): the generator writes each file in an order of its own, so the key is the truth file's event
  index; the harness uses `layout.classify_t07_by_index` (job only; fix round 1, n2).
- Headers: the range identity may differ between a range and the single pass (T07 refit: `product_id`, `data_product`, `data_sha256`,
  `hit_sets_sha256`; JSON Lines: `product_id`, `input`, `events`, `h1_product`, the keys found to differ in the E6a products); every other
  header field must be equal (it carries the recipe, configuration, budget and conventions), else a header defect.

**Merge (T12-10, M2).** `merge_by_key(single, parts)` returns five lists, all empty when the merged ranges equal the single pass: `omitted`
(a key of the single pass in no range), `duplicated` (a key in two ranges or twice in one), `differing` (same key, other value), `extra`
(a key the single pass does not have) and `header`. Tolerance: none, exact equality. The products are declared deterministic and the E6a
job read them equal line for line (`PASS EQUAL` for T08 and T09, `CLASS ... equal` for T07, job 7591439); §14.1's numerical and
statistical comparators, with their tolerances, are stage 4's (T12-13).

**Range collection (T12-10, T12-11).** `collect_ranges(identity, kind, total, planned, attempts)`: the planned ranges must cover events 0 to
total - 1 once (`layout.check_ranges`; otherwise `rejected`: a plan, not a result). For each range, in order:
1. no attempt: failure, "missing range";
2. any attempt's (fix round 1, m2: not only the last one's) Slurm state is not final (`RUNNING`, `PENDING`, `REQUEUED`, `RESIZING`, `SUSPENDED`, `COMPLETING`, `UNKNOWN`) or its
   termination is `unconfirmed`: **unconfirmed**, "check before resubmitting" (§10.2 item 7, §14.2 "Stopping"), never failure or success;
3. the attempts' verdicts (`layout.classify_attempt`) and the counted one (`layout.select_attempt` for the block): a refusal is a failure
   with the layout's reason (on blocks 11 and 12 no repeat after a draw; on a Freeze-B block a `REPEATABLE` attempt may precede);
4. the counted attempt must have left a `RangeRecord` of this range and bin that names that attempt's own id (fix round 1, I1: `Attempt`
   carries its Slurm id; a record an earlier attempt left is a failure even when the product matches it), and the product file's SHA-256
   must be the record's: a file a killed attempt left, or an earlier attempt's file under the same name, is not the one its record names and
   is a failure;
5. the product must read as complete for its kind (M1) and hold no object outside its range: otherwise a failure.
A range that passes 1-5 is a success. The bin is `complete` when every range succeeds; otherwise `missing`, and every failed or
unconfirmed range is listed as "required output missing" with its reason (Freeze A section 10's words, as `layout.missing_bin_records`;
top-up never). An empty collection (an event with no objects inside a successful range) is never a failure. For JSON Lines products it is
a success: every event read writes an event line, so an event line with no objects is an empty collection and a missing line is refused.

**Format gap, T07 refit (fix round 1, I2).** The T07 refit product declares no events read: its end line counts lines per section, and
neither the E6b range files (the hit-sets input, the run log `{"status", "tracks", "failed", ...}`) nor the `RangeRecord` says how many
events the program read. A range stopped early but closed properly cannot be told from one whose last events are empty collections. So,
for that kind only, an event of a successful range that holds no object is **unconfirmed** ("T07 refit format gap"), and the bin is not
complete; T12-12's "an empty collection is not a failure" is shown for JSON Lines only and stays open for the T07 refit product until the
format (or its record) declares the events read. The hit-sets input declares the objects to refit, so "every hit set has a track line" is
a possible object-level remedy; it is not implemented here.

**Accounts and exposure (T12-12, A11).** Each source event has one stable scope, `<workflow>/<fixture>/b<block>/s<stratum>/e<event>`, and
exactly one category: `success` (its range succeeded and it is not excluded), `excluded` (its range succeeded and the caller excludes it,
with a non-empty reason: a selection or a boundary flag such as insufficient neighbourhood, §10.2 item 5), `failure` or `unconfirmed`
(its range's outcome). `check_accounts` reports an event in two categories, an event of the bin in none, an event outside it, and an
exclusion without a reason. Original data gaps (events never recorded) are not source events: `exposure` lists them apart, with their
observable scope, and never counts them as failures (§10.2 item 4). `exposure(accounts, total, gaps)` gives the counts per category and
`exposure = success / total`: excluded, failed and unconfirmed events lower it and nothing is invented (§10.2 item 6). Fix round 1, m1: it
refuses accounts that fail `check_accounts`, a gap without a reason or a span (`first`, `count` in the stream's own numbering), and two
overlapping gaps; it returns the use of each category in the denominator (success: numerator and denominator; excluded, failure,
unconfirmed: denominator only; original gaps: neither). These are the
fixture's accounting categories (§10.5: mapped to the existing vocabulary, not new public statuses).

**Expectations (unit tests, on the four recorded examples unless named).**
- P1. The recorded files have their pinned SHA-256; each reads with the expected keys (T07 refit: 12 `track` keys, end counts `12 96 288
  12 384 96 12`; JSON Lines: events 0 and 1).
- P2. Each product cut into the ranges [0, 1) and [1, 2) merges back equal (five empty lists), in either order of the parts.
- P3. Dropping the range [1, 2): `omitted` is exactly event 1's keys; the collection is `missing` with "missing range" for [1, 2); event 1
  is `failure`, event 0 `success`; exposure 1/2.
- P4. The range [0, 1) given twice: `duplicated` is exactly event 0's keys. A range product with one value changed (T07: the last field of
  `event-1`'s first `track` line; JSON Lines: in event 1, the first number met in a depth-first walk of its keys in sorted order, `event`
  left out, increased by 1): `differing` names exactly that key.
- P5. A changed configuration header field (T07 `start_prior`; T08 `configuration`; T09 `budget`) is a header defect; a changed range
  identity field is not.
- P6. A range product truncated (its end line removed, or a T07 end count off by one) is refused by the reader and is a failure at the
  collection; an object of event 1 inside the range [0, 1) is refused (outside its range).
- P7. Empty collection (fix round 1, I2: for T07, event 1 is unconfirmed and the bin missing, the merge still equal): T07, the single pass
  and the range both without event 1's objects (end line recounted); T08, event 1's `objects`
  emptied in both: the merge is equal and event 1 is `success`.
- P8. Accounts: every event in exactly one category in P2-P7 and K1-K4; `check_accounts` reports a hand-made event in two categories, an
  event in none, and an exclusion with an empty reason; an excluded event lowers the exposure; an original gap is listed apart and the
  total of the categories is still the bin's source events.

**Recovery (T12-11).**
- K1. A range whose last attempt is `TIMEOUT`, `OUT_OF_MEMORY` or `CANCELLED` after draws (milestone `draws-started`) and which left a
  partial product and no record: failure; the bin is `missing`; no event of that range is a success.
- K2. A later attempt `COMPLETED` exit 0 whose record names a fresh product, but the file found is the earlier attempt's partial file:
  failure ("not the one its record names"). On a Freeze-B block (2) a `TIMEOUT` attempt before a completed one with its own product is
  accepted (`REPEATABLE-WITH-NEW-REQUEST`); on block 11 the same history is a failure ("A failure stands").
- K3. Last attempt `RUNNING`, or `COMPLETED` with termination `unconfirmed`: `unconfirmed`, not failure; the bin is `missing`.
- K4. A product that reads complete but has no record (a killed attempt that had written everything): failure, never counted.
- K5 (runner). A step that writes part of its output and then outlives `timeout_s` (1 s): exit 1, step `end_status` `timeout`, later steps
  not run.
- K6 (runner). A step that writes part of its output and then kills itself with SIGKILL (an OOM stand-in): exit 1, `end_status`
  `failure`, `exit_status` -9.
- K7 (runner, resubmission). After K5, `--incremental` does not skip the step (`exit_status` changed); a resubmitted program that keeps the
  partial file and exits 0 fails ("existed before and were not written by this run"); one that rewrites the output succeeds.
- K8 (runner, retries). A failing step runs exactly once per runner invocation (an invocation counter file); with `"retries": 3` in the
  step it still runs once (the runner has no retry; an unknown key is ignored, see "Findings").

**Job of record (`recorded`).** `t12_partition.py recorded --evidence DIR` (DIR holds `d4-e6a-7591439` and `d4-e6b-7591993`): every
`RECORDED` file's SHA-256, then R1 T07 clean and noise: the two full runs equal and the ranges equal the full run by event index
(`classify_t07_by_index` gives `equal`); R2 T08 main and dead, T09 multistart and topology: `merge_by_key` of the range products against the
full product, five empty lists, header rule included; R3 the T07 refit ranges: each reads complete, events 0-2999 each in exactly one
range by key, no key in two ranges, headers equal except the range identity, each product's `data_sha256` its record's `stratum_sha256`
and its `hit_sets_sha256` its record's `input_sha256` (fix round 1, m3), and `collect_ranges` gives `complete` with all 3,000 events
`success`; with range 0's file found under the middle range's name, `missing` with 1000-1999 `failure` (fix round 1, n3: a real refusal
by SHA-256, replacing a dropped range, which was true by construction). The attempt history of R3 is synthetic: one completed attempt per
range, its id the E6b record's own `attempt` (I1); the PASS line says so. Status and exit (core/status.py): `ok` 0, every comparison as
expected; `failed` 1, one differs; `rejected` 2, a file missing or not its pinned SHA-256; `incomplete` 3, a crash, including a refusal
of a pinned file after its hash matched (fix round 1, m6).

**What the recorded runs show (fix round 1, concern 4).** The merge by object key on real, separately run ranges against a full run is shown
only for T08 and T09 (R2). T07 finding products are compared by the layout's event-index comparison (R1), not by `merge_by_key`. The T07
refit ranges (R3) have no kept single pass: they show completeness, disjointness and the tie to their records, not equality with a full
run. The unit tests cut one recorded run into ranges, which cannot show range independence.

**Open item against `skills/hep-computing/scripts/run_workflow.py` (fix round 1, concern 2; the runner is not changed in this stage).**
The runner ignores step keys it does not know, so `"retries"` is silently ignored and the step is never retried: safe under §10.5
("without retry configuration, do not retry automatically"), but a declared retry count is neither honoured nor refused, and §10.2 item 7's
"bounded retry" does not exist in the runner. Owner: the coordinator (a shared-runner change needs its own review, as stage 2's did).

**Finding (not a defect of this stage).** On a timeout or kill with confirmed termination, the
failed run record and the receipt list the partial output's SHA-256 (with `end_status` `timeout` or `failure`): a consumer must read
`end_status`; the layout's collection never admits it (K1, K4).

**Test order (M4 of stage 2's review, kept).** The 29 tests of P1-P8 and K1-K8 were written before the harness (red-1: a stub harness
with the names only, 28 errors; the one pass, `test_recorded_lists_every_file_once`, passes vacuously on the stub's empty `RECORDED`).
Added after green-1, not test-first: two tests of the job's R2 and R3 functions on files cut from the examples (`RecordedDriver`), and,
after mutation-1 (mutant M7 survived), one test of a JSON Lines product that lost an event line but kept its end line (P6). New
behaviour: M1, M2, the collection's steps 4-5 on the T07 refit product, accounts and exposure (P1-P8, K1-K4). Characterising: K5-K8
(the runner at `28763f50`) and, inside the collection, the layout's attempt rules (steps 1-3).

**Fix round 1 (review `jobs/t12-stage3/REVIEW.md`, 0/2/7/4; written with the fixes).** The tests for I1, I2, m1, m2 and m5 (class
`FixRound1`) were written before the harness change and run red twice: red-2 (5 errors: `Attempt` had no `attempt` field) and red-3 with the
field only, no rule (5 failures, each on its behaviour). The changed expectations: P7's T07 case (I2), the gap form in P8 (m1), every test
`Attempt` with its id (I1). Tests added with the fixes, not red first: n1 (RECORDED pins exactly the files `recorded` reads; replaces the
vacuous uniqueness test), m3 (`refit_ranges` with records), m6 (a refusal after the hashes is exit 3).

**Plan changes after the first green (fix round 1, m7).** The tests of the first round were written against this plan at SHA-256
`14100006c654165ece6dc1d16889c67443da600da06a0570b7577ba3261f1044` (reconstructed byte for byte by removing the "Test order"
paragraph; `jobs/t12-stage3/plan-at-green-14100006.md`). Change 1, after green-3 and before static-2: the "Test order" paragraph added
(`2f3c15a2...`; diff `jobs/t12-stage3/plan-diff-14100006-2f3c15a2.diff`, 8 lines, no rule or expectation changed). Change 2, fix round 1:
the edits marked "fix round 1" in this section (m4, n2, m2, I1, I2, m1, P7, m3, n3, m6, concern 4, concern 2, this record), made after
red-3 and before green; the hash at the fix round's green run is in `jobs/t12-stage3/green/green-*-fix-round-1.log`.

## Stage 4: comparators and quality before speed (fixed before the tests were written)

**Split.** Part A takes T12-13 (§14.1) and T12-15 (A15, A50, §16.1 "quality before speed"), on branch `t12/stage4` from `28763f50`
(Freeze B given, T10 done). Part B, T12-14 (§14.2, the CPU engineering benchmark), needs stage 3's partitioned products and stays out of
this lane: it is only planned below. Before this section was written, one feasibility probe ran on login (the destriper solved on the
fixture and on a reordered copy; the planted pull samples gated once); its numbers are the readings quoted in N2 and Q1-Q2 below, and no
test existed then.

**Files.** `tests/contracts/t12_comparators.py` (the harness: the per-recipe declarations, the three comparators, the fixed gate and the
quality-before-speed report, and a command line) and `tests/contracts/test_t12_comparators.py`. It lives in `tests/` because it imports
an adapter's recipe modules and the E6 statistics core (`tests/adapters/t04_evaluation_core.py`, E2's `t07_fake_rate.py`), which an adapter
or `core/` may not (`tools/check_layering.py`). No production file, recipe, frozen file or file of `jobs/evaluation/SOURCES.sha256` changes.
Frozen files are read by SHA-256 only. No quality claim: every fixture is synthetic, and a pass of a comparator says the two products
agree within the stated tolerance, nothing about either product's quality.

**Where the tolerances come from (the only sources).** Freeze B (`freeze-b.md`) fixes recipe identities, configurations, budgets and
`r_dev` "for test F2"; its "Not in this freeze" names tolerances as Freeze A's (`t04-values-v4.md`, `92f71f56…` in freeze-b.md "Freeze A,
unchanged"). The K09 rulings of freeze-b.md "Readings and rules" set levels, not reproducibility tolerances. T10's frozen tolerance is the
replay comparator's (decisions.md, "The user's freeze of T10's replay comparator tolerance", 2026-11-12; t10-closeout.md, replay row).
Searched: no recipe document of T07-T10 declares `reproducibility` (`grep -rn reproducibility` over `adapters/acts-tracking`,
`calo-cluster`, `photon-likelihood`, `timing-pid`, `destriper`: no match). So:

| Recipe | Byte | Numerical | Statistical |
| --- | --- | --- | --- |
| T07 CKF `reco.track.acts-ckf-planar/1` | B | open (OI-1) | fake rate per noise bin: F2 (S1); every other quantity open (OI-2) |
| T07 AMVF `reco.vertex.acts-amvf/1` | B | open (OI-3) | open (OI-3) |
| T07 refit `reco.track.acts-kf-refit/1` | B | open (OI-4) | open (OI-4) |
| T08 `reco.calo.cell-cluster/1` | open (OI-11, fix round 1) | open (OI-5) | open (OI-5) |
| T09 `reco.light.channel-likelihood/1` | B | open (OI-6) | open (OI-6) |
| T10 `reco.timing.time-chain/1` | B | open (OI-7) | open (OI-7) |
| T10 `reco.scan.destriper/1` | B | the frozen replay tolerance (N1), under the OI-8 ruling (fix round 1) | not applicable: one-to-one comparison is possible (§14.1) |

- **B (every recipe).** Byte equality of the whole file, nothing excluded as non-scientific metadata (§14.1: "define in advance whether
  bitwise identity is assessed after excluding nonscientific metadata": declared here, nothing is excluded). No tolerance exists to
  choose. Same node class only (U-W7, AMD EPYC 9645, freeze-b.md "Node class"); byte equality across classes is not claimed (as Freeze A
  says of the generators). Readings that support it, not proofs: T07 outputs byte-equal across jobs 7502411, 7503215 and 7512409
  (decisions.md, 2026-11-08); t09-closeout.md "Reproducibility"; t10-closeout.md "Reproducibility". t08-closeout.md records no byte rerun
  of the recipe's products.
- **N1 (destriper, numerical).** The frozen records, read by SHA-256: `adapters/destriper/assets/t10-replay.tolerance.json`
  (`217a38bc…`; stopping 1e-10: baselines `||a_c - a_r||_2 <= 2.5e-8 ||a_r||_2`, map `||m_c - m_r||_2 <= 2.2e-8 ||a_r||_2`) and
  `t10-replay-noiseless.tolerance.json` (`12738ebc…`; stopping 1e-13: 2.5e-11 and 2.2e-11); zero sum `|sum a_c| <= 1e-13 sum |a_c|` in
  both. The record is chosen by the products' stopping value; a product whose stopping value is in neither record, or two products with
  different stopping values, is rejected (the tolerance was derived for that stopping value). The reading T12 makes: the records were
  frozen for the solver against the exact rational reference; here the reference role is taken by a reference product of the same recipe
  (an open question for the coordinator, OI-8, not a choice of a new value).
- **S1 (T07 CKF fake rate per noise bin, statistical).** F2's rule and tolerance, unchanged: `(r_c - r_r) + sqrt((U_c - r_c)^2 + (r_r - L_r)^2)
  <= tau`, `tau` = 0.0025 (t04-values-v4.md §8.3, fixed at Freeze A), `U_c` and `L_r` section 5.2's 95 % bounds (E2's `rate_rule`, the
  attempt-1 level; the 99 % of K09's attempt 2 is an evaluation-attempt rule, and a T12 comparison is no evaluation attempt). `r_r`, `L_r`
  come from the reference sample (in evaluation, the Freeze-B record `ebf2aa0e…`). As frozen, F2 is one-sided: a lower candidate rate
  passes.
- **OI-1 to OI-7 (open, not chosen).** Freeze B fixes no numerical or statistical reproducibility tolerance for these recipes and
  quantities; each comparator answers `incomplete` (exit 3) with the open item's identifier and never a pass. Candidate recorded beside
  OI-6, not used: T09's close-out replay tolerance (decisions.md, T09 close-out, "Replay across platforms (review I1)": ln L 1e-6, the
  statistic 4e-6, parameters 1e-3 σ, discrete values exact), fixed by that stage's review, not by Freeze B or K09: whether it becomes T09's
  comparator tolerance is the user's word.
- **OI-9 (recipe declarations).** The table above is T12's harness declaration, from the records; the recipes themselves still declare no
  `reproducibility` (G03, `reconstruction_recipe.json`). Writing it into a recipe changes a Freeze B item (a return to Freeze B, v4 3.4), so
  it is left open.

**Matching rules (§14.1: quantities, matching rules, tolerances per quantity; permissible ordering apart from identity and association).**
For the destriper product (`destriper-product/1`, read and refused by the recipe's own `product.read`): pixels are identities (key:
pixel index); a baseline's key is the sorted tuple of its samples' observation values (the input values, copied exactly into the
embedded scan model; `destriper-timestream/1` gives samples no other identity), and its association is the sorted tuple of its samples'
(value, pixel) pairs, read from the embedded scan model's `design` and `observation`. A key held by two baselines of one product makes the
matching rule ambiguous: rejected (exit 2). Values are compared exactly (each float as its exact binary value, `fractions.Fraction`, as
T10's comparator does).

**Expectations, byte (B1-B3).**
- B1. Two products of the destriper solved twice on the same timestream (noisy fixture, seed 20260, stopping 1e-10, same `product_id`)
  are byte-equal: `passed`.
- B2. The same JSON written with another key order (a pure reordering) fails the byte comparator: `failed`, with the first differing
  offset. A reordering passes only where the form allows it (numerical, statistical); byte form allows none.
- B3. One changed byte fails; the result names both SHA-256 values. A hash is integrity evidence, never the scientific comparison
  (§14.1): the numerical comparator does not read hashes.

**Expectations, numerical (N1-N9; destriper on the fixture `t10-destripe/1`, noisy, seed 20260, stopping 1e-10).**
- N2. Reordering, baselines: the timestream's baseline segments permuted (a fixed permutation from `default_rng(7)`), solved again: every
  key matches, associations equal, `passed`. Reading of the probe: 15 iterations both; baseline difference 2.1e-15 and map 1.5e-15 of
  `||a_r||_2`.
- N3. Reordering, samples within each baseline (each segment's (pixel, value) pairs reversed), solved again: `passed`.
- N4. Changed association, numbers moved: two samples of baseline 0 exchange pixels (values stay), solved again: `failed` with
  `association` in the failed set (and the numbers, since they move: probe 5.4e-2 of `||a_r||_2`).
- N5. Changed association, numbers unchanged: the reference product with one design row naming another pixel (map, baselines and reported
  values untouched): `failed`, failed set exactly `{association}`. A topology change never passes because the numbers agree.
- N6. A value change beyond the tolerance (baselines 0 and 1 moved by +δ and −δ, δ = 1e-6 `||a_r||_2`, map and reported values kept
  consistent): `failed`, failed set exactly `{baselines}`; within it (δ = 1e-9 `||a_r||_2`): `passed`.
- N7. A dropped baseline (one segment removed from the timestream, solved again): `failed` with `objects` in the failed set (an
  unmatched reference key is a required object missing).
- N8. A product with a stopping value in no record (1e-8), or two products with different stopping values: `rejected`. A frozen record
  whose bytes differ from its SHA-256: rejected.
- N9. Any open recipe (OI-1, OI-3 to OI-7): `incomplete`, with the open item, never `passed`.

**Expectations, statistical (S2-S6; synthetic per-event counts, 12,000 events, `m_e` tracks and `y_e` fakes per event).**
- S2. Reordering: the candidate is the reference with its events permuted: the statistic is equal to the reference-against-itself
  value, and `passed`.
- S3. A candidate with fakes added beyond `tau` (the statistic above 0.0025): `failed`. A changed association in T07's sense (a track
  re-associated so it becomes a fake) shows only through the rate: a statistical comparator cannot see associations that leave the rate
  unchanged, which is why §14.1 allows it only when one-to-one comparison is impossible (stated in the result).
- S4. Data loss is not excused (§14.1): a candidate with a different event count from the reference's is `failed` (`events` in the failed
  set), even when its rate passes.
- S5. The statistic equals E6's F2 (`t07_evaluation_scoring.stability_test` at attempt 1) on the same counts to 1e-15 absolute
  (agreement of the formula only; no evaluation bin is scored).
- S6. Every other quantity of T07 CKF and every other recipe: `incomplete` (OI-2 to OI-7).

**Expectations, quality before speed (Q1-Q8; T12-15, A15, A50).** The fixed gate is Freeze A's common gates (t04-values-v4.md §6):
location and width by the pull test (§5.2 steps 1-4, tolerance 0.10, cap 0.0108) and the tail by the rate test `P(|pull| > 3)`, `L` = 1 %,
at the attempt-1 level (95 %), computed by the E6 core's own functions, with B = 1,000 bootstrap rows from a T12 tag (`SeedSequence([1215])`,
never the evaluation's 520). Samples: 12,000 events of one pull each. Baseline: `default_rng(20261115).normal(0, 1, 12000)`. Faster
variant: `default_rng(20261116)`: unit normal, then a fraction drawn `< 0.02` replaced by `normal(0, 5)` (a fatter tail, the same core).
Timings are synthetic numbers (baseline 10.0, variant 6.0, seconds per 1,000 events), labelled so; nothing is measured here.
- Q1. Baseline: centre, width and tail pass (probe: centre 0.0336, width 0.0090, tail 0.0020 with U 0.0028).
- Q2. Variant: centre and width pass, the tail fails at step 1 (probe: 225 replaced, tail 0.0121, lower bound 0.0105 > 0.01).
- Q3. Report: the variant is `rejected under the fixed gates`, with no speed number anywhere in its entry; the baseline is `qualified`,
  with its speed after its quality record; the selected candidate is the baseline, though the variant is faster (A50: a cost advantage
  cannot compensate).
- Q4. Declared as another working point, the variant is `listed as another working point`: its quality record (the tail fail) first, then
  its speed, labelled "not qualified under the fixed gates; not a replacement"; it is never selected.
- Q5. Order: no timing is read before that candidate's gate record is complete (a sealed timing refuses a release without a complete
  gate record; a spy records the order); in every entry `quality` precedes `speed`.
- Q6. Every candidate failing or inconclusive: nothing is selected ("no qualified candidate"), and no speed number is released except for
  declared working points (A50).
- Q7. An inconclusive gate (too few events: 2,000) is not qualified, and its speed is withheld.
- Q8. The gates are the fixed ones: the gate constants are read from the E6 core (tolerance 0.10, cap 0.0108, `L` 1 %), and the harness
  has no parameter that changes them.

**Command line and exit codes (core/status.py).** `t12_comparators.py compare --recipe R --form byte|numerical|statistical --reference
FILE --candidate FILE --out FILE [--quantity Q]`: `passed` 0, `failed` 1, `rejected` 2 (unknown recipe or form, a form declared not
applicable, unreadable input, an output file that exists: never overwritten, a missing folder), `incomplete` 3 (an open tolerance, or the
comparator could not run). `t12_comparators.py declarations` prints the table above as JSON, exit 0.

**Mutation check (after green).** Planted in a copy of the harness, one at a time, each must turn at least one test red: the association
check removed; keys matched by position instead of key; the tolerance multiplied by 100; the zero-sum check removed; the event-count check
removed; F2's development-uncertainty term dropped; the tail gate dropped from the fixed gate; speed released before the gate; a failing
candidate selected when faster; an open item answered `passed`.

### Stage 4, fix round 1 (review `jobs/t12-stage4/REVIEW.md`, NOT READY 0/4/6/4; every finding adopted)

Order of work, disclosed: the changed and new tests were written first and run red against the round-0 harness
(`jobs/t12-stage4/red-r1/red-3-round0-harness.log`: 53 run, 9 failures, 9 errors; the tests that passed there characterise round-0
behaviour, among them `test_constants_are_the_frozen_codings` (M1 is a refactor) and the 1e-13 record test); then the harness; this
subsection records the changed expectations after green. The round-0 job 7636498 (PASS, 34 min 41 s) is kept as a reading only.

**Changed declarations.**
- OI-6: the user answered "Leave open" (2026-11-13) to the T09 close-out replay tolerance: T09 stays open.
- OI-8 is a ruling, no longer an open item (the coordinator, fix round 1): T10's frozen replay tolerance holds for a product against a product
  of the same recipe only on the record's pointing (t10-destripe/1, seed 20260): each is within `kappa eps` of the exact solution, so they
  differ by at most `2 kappa eps` < `tau = safety kappa eps`. The 1e-13 record depends on the pointing only, so it applies to noisy products
  stopped at 1e-13 too. Every destriper result and its command-line summary name the ruling (`"ruling": "OI-8"`).
- OI-10 (new): F2 is one-sided as frozen. As a reproducibility rule, a lower candidate rate beyond `tau` (F2 with the roles of reference
  and candidate exchanged, above `tau`) or a changed object (track) count has no frozen rule: the answer is `incomplete` with OI-10 and the
  blocking reason, never `passed`. A different event count stays `failed` (S4).
- OI-11 (new, M4): T08 has no recorded byte rerun of its products, so T08's byte form is open (`incomplete`). Each other recipe's byte
  declaration names its record (T07 finder and vertexer: decisions.md 2026-11-08; refit: t07-closeout.md, job 7551619; T09 and T10 timing:
  their close-outs; destriper: B1 here and t10-closeout.md).

**Changed expectations.**
- I1. Before the destriper tolerance is applied, T10's own record checks run on the reference product's pointing (read from its design):
  `t10_comparator.fixture_numbers` gives kappa and G, which must be within 0.01 and 1e-4 of the record's; safety at least 10; `kappa eps`
  at least 1e3 rounding units; `tau_baselines >= safety kappa eps`, `tau_map >= safety G kappa eps`; the record must have exactly T10's
  keys and format. Otherwise `rejected` (exit 2). Seed 1's pointing (kappa 24.24 against 24.47) is rejected. A candidate on another pointing
  than the reference shows as an association or object difference (N4, N5, N7 unchanged). The result carries `derivation` (kappa, G).
- I2. As OI-10 above: a reference at rate 0.01 against a candidate with no fakes (F2 itself passes) answers `incomplete`, blocking
  `lower_rate`; one added track answers `incomplete`, blocking `objects`, with both object counts as readings. S2, S5 and the command line
  use a candidate with the reference's events and tracks per event (fakes drawn afresh), which `passed`.
- I3, M5. The command-line summary carries `open_item`, `ruling`, `blocking` and `reason` when the result has them.
- I4. An object without a result is NaN in the candidate's per-object array; the gate's location and width use the objects with a result,
  and the tail counts every object, an object without a result as a failure (v4 5.1, as E6's `t07_evaluation_scoring._pull_records`). The
  planted variant with its `|pull| > 3` objects turned into "no result" fails the tail. Candidates with different object counts are
  rejected (the same scientific work, Section 14.2).
- M1, N2. The tail constants and `tau` are E6's (`t07_evaluation_scoring.TAIL_LIMIT`, `TAIL_PULL`, `STABILITY_TOLERANCE`), the confidence
  E2's `CONFIDENCE`; tests assert the equality.
- M2. The statistical comparator and the gate refuse unless `t04_evaluation_core.py` is 265eb124… (freeze-b.md, evaluation manifest) and
  `t07_fake_rate.py` 4b4aa1ad… (evaluation manifest); `t07_evaluation_scoring.py` is pinned at this base (32d0adc6…), which differs from
  the evaluation manifest's 6102c2ef… (changed after attempt 1, commit 7a98aeff); only its constants are read.
- M3. A timing is bound to one candidate when the candidate is made and released only against `gate_record(name, gate)` of that
  candidate, which exists only when all three gate results carry v4's words; the value is not a public attribute.
- M6. The mutation list grows by eleven: the derivation check removed; the record chosen without the stopping value; the tail limit
  doubled; the statistical open item answered `passed`; the lower-rate block removed; the object-count block removed; objects without a
  result not counted; the timing owner check removed; the frozen-module check removed; the ruling dropped from the summary; the open answer
  given after parsing.
- N1. The `1e-12` bound in the N2 test is a test bound on the readings (the probe read about 2e-15), not a tolerance.
- N3. An open form answers `incomplete` (exit 3) before any input is parsed, so non-JSON input to an open recipe is exit 3, not 2.
- N4. `Candidate` is frozen: the working-point declaration is fixed before any gate runs and recorded first in its entry.

**Job.** `jobs/t12-stage4/t12-stage4-r1.sh` with `SOURCES-r1.sha256`, `--time 03:00:00`: a frozen test
(`test_t04_evaluation_layout` TaskDeadline) fails inside any job with less than 1 h left; it is not edited, and the allowed failures
stay the LCG ID only.

### Stage 4, fix round 2 (re-review `jobs/t12-stage4/REREVIEW.md`: everything closed but M3; N-A and N-B accepted as they are)

The three new tests were written first and run red against the round-1 harness (`jobs/t12-stage4/red-r2/red-4-round1-harness.log`:
56 run, 2 failures, 3 errors); then the harness; this subsection after green. Job 7647973 (round 1's files) is a reading only.

- M3, case 1 (forgery). A timing is released only against a record that `gate_record` made: a private class whose every instance
  `gate_record` registers, checked by identity. A dict such as `{"candidate": "a", "complete": True}`, or a copy of a genuine record,
  releases nothing (`rejected`).
- M3, case 2 (failed candidate). `release` itself refuses unless the gate passed or the candidate declared a working point, so a direct
  call cannot read a failed, undeclared candidate's timing; a declared working point still gets its speed after its gate.
- M3, case 3 (names). A timing is bound to the candidate object, not its name: a record of another candidate with the same name releases
  nothing. `quality_before_speed` rejects duplicate candidate names.
- Mutation: four more mutants (the issued-record check removed; the owner matched by name; a failed gate released without a working point;
  duplicate names accepted); the round-1 owner mutant follows the new code.

**Job.** `jobs/t12-stage4/t12-stage4-r2.sh` with `SOURCES-r2.sha256`, `--time 03:00:00`; the r1 files are kept.

**Part B, T12-14 (planned here; taken by stage 5, see "Stage 5" C1-C8).** The same scientific work on the same input domain and native output level, each
recipe at its Freeze B hash: reading and probes, initialization, I/O, conditions, conversion, native compute and output/checks timed
apart; with overlap, the total wall time and how each part was measured, never a sum of overlapping times (§14.2). Workload units per
task (events for T07-T09, samples and baselines for the destriper); success and failure denominators, memory, latency quantiles,
throughput. Cold and warm apart (K12, t04-values-v4.md §12: no targets; numbers are records, not gates). No speed number is reported
for a recipe before its quality gate (T12-15); these CPU numbers are what T12-17 records beside A13. It needs stage 3's partition and
accounts (T12-10 to T12-12) and its own job approval.

## Stage 5: A13 on the GPU, and T12-14 (fixed before the tests were written)

**Authority and scope.** The user, 2026-11-13: "A13: GPU part: allow use GPU". A13 is reopened; Q1's answer ("Record
blocked-by-resource") is superseded by it. The subchain is the T10 destriper's baseline solve (`reco.scan.destriper/1`), the only recipe
with a frozen reproducibility tolerance; the partition is `b6000-al9_devel` (`--gres=gpu:1`, never `--qos`), PyTorch from the existing
venv `torch-gpu/venv-cu130` (torch 2.14.1+cu130, Python 3.12, `PYTHONNOUSERSITE=1`; nothing installed). R30's tiny hardware job is done:
`jobs/a13-gpu/hw-check.sh`, job 7648670 PASS (NVIDIA RTX PRO 6000 Blackwell Server Edition, driver 590.48.01, capability 12.0, 188 SMs;
a 2048 x 2048 float64 solve on the GPU agreed with the CPU to 1.9e-15 relative; float64 GPU 0.0144 s against float32 0.0050 s warm, first
call 1.30 s: readings). This stage also takes part B of stage 4 (T12-14, the CPU engineering benchmark), whose destriper timings are A13's
CPU side and what T12-17 records beside A13, and T12-22 (execution fields). On branch `t12/stage5-a13` from `d1f6fc30`. Before this
section one feasibility probe ran on login (a PyTorch transcription of the solver on the CPU, float64, beside the recipe; a 1,048,576-sample
synthetic scan timed with NumPy and PyTorch); its numbers are the readings quoted below, and no test existed then.

**Files.** `tests/contracts/t12_a13_gpu.py` (the GPU subchain, the A13 comparison, the sealed timings, the execution fields, a command
line) and `tests/contracts/test_t12_a13_gpu.py` (skipped as a whole without PyTorch, and listed in the required torch-backend CI job,
`.github/workflows/tests.yml`, where no PyTorch skip is allowed; the CUDA cases skipped without a CUDA device);
`tests/contracts/t12_benchmark.py` (T12-14: component timers, recipe identity, the release rule) and
`tests/contracts/test_t12_benchmark.py`; `tools/optional_modules.json` lists the new torch module under `torch-cpu` (the required units
skip it). No recipe, frozen file, adapter asset or `jobs/evaluation/SOURCES.sha256` entry changes: the GPU subchain is a harness-side
transcription that reads the recipe's own timestream reader and writes the product with the recipe's own writer. No quality claim: every
input is synthetic or a block-1 development input.

**The GPU subchain (G1-G8).** The same algorithm as `destripe_recipe/solver.py`, line by line in PyTorch: conjugate gradient on the reduced
system `D a = F^T Z y` from `a = 0`, every residual and direction projected onto the zero-sum subspace (mean removed), the stopping test on
the recomputed residual `||Pi (F^T Z y - D a)|| / ||Pi F^T Z y|| <= eps`, the restart when the recurrence collapses, the budget 10 per
baseline (`BUDGET_PER_BASELINE`) and the recipe's `NotConverged`; the map by binning. `M^-1 P^T v` is `index_add_` divided by the hit
count, `F^T v` a reshape and row sum. The input is read by `destripe_recipe.timestream.read` (so a scan the recipe refuses is refused
here), the product built by `destripe_recipe.product.build` with a `destripe_recipe.solver.Solution`, and read back by `product.read` and
`contracts.reconstruction.read_sidecar`. Precision float64 (the frozen tolerance is a float64 derivation); float32 is a reading only.
- G1. On the frozen pointing (t10-destripe/1, noisy, seed 20260, stopping 1e-10), on `cpu` in tests: the product is read by the recipe's
  reader, the contract accepts its embedded product, and the stage 4 numerical comparator (`t12_comparators.compare_numerical`, the record
  `217a38bc…`, the OI-8 ruling) answers `passed` against the recipe's product. Probe: 15 iterations both; baselines 2.4e-16 and map
  1.7e-16 of `||a_r||_2`; zero sum 3.5e-17 of `sum |a|` (fix round 1: the iteration counts are equal exactly; tests bound the readings by
  1e-12: test bounds on readings, not tolerances).
- G2. The noiseless variant at stopping 1e-13 against the recipe's product at 1e-13 (record `12738ebc…`): `passed` (probe: 15 iterations
  both, 7.2e-16 and 2.8e-16).
- G3. The stopping rule is the recipe's: the product's `relative_residual` is at most its `stopping` (else `product.read` refuses it); a
  budget of 3 raises the recipe's `NotConverged` with 3 iterations and writes nothing, on both paths alike.
- G4. A scan the recipe refuses (the disconnected variant; an unobserved pixel) is refused by the same reader before any device work.
- G5. `device="cuda"` without a CUDA device is `DeviceUnavailable`: `incomplete` (exit 3), never a silent run on the CPU.
- G6. float32: the solve runs as a reading; at the recipe's stopping it ends in `NotConverged` or a residual above it, and a product is
  never built from a non-float64 solution (`rejected`). No float32 result is ever passed to the comparator.
- G7. Both products of a comparison must name the same input (`input.sha256`); otherwise `rejected`.
- G8. On CUDA (job only): G1 and G2 hold on the device (`passed`). Prediction: the iteration counts equal the recipe's (15, 15), the
  differences 1e-16 to 1e-14 of `||a_r||_2`, far below `tau` (2.5e-8 and 2.5e-11). GPU-to-GPU byte equality across repetitions is a
  reading (`index_add_` uses atomic adds on CUDA, so the order of the additions is not fixed), never a gate.

**The A13 comparison (T12-16; plan A13, R30, U8; Section 14.2).** Per size, the GPU subchain against the CPU recipe on the same timestream:
- Sizes. `frozen-noisy` (t10-destripe/1, seed 20260, 256 samples, 32 baselines, 16 pixels, stopping 1e-10) and `frozen-noiseless` (the
  same pointing, stopping 1e-13); larger synthetic scans by the harness's generator (the fixture's model at scale: baseline b sweeps a
  contiguous arc of L/2 or L pixels from a seeded start; map integers 1..19 with a sign; baselines in pairs (v, -v); white noise sigma 1;
  streams seed, seed + 1, seed + 2): `scan-1m` (4,096 pixels, 8,192 baselines of 128, 1,048,576 samples, seed 20261) and `scan-16m`
  (16,384 pixels, 65,536 baselines of 256, 16,777,216 samples, seed 20262), both at stopping 1e-10. Probe on login, `scan-1m`: NumPy
  recipe 2.32 s, 78 iterations; PyTorch on one CPU thread 2.04 s, 78 iterations, 2.0e-15 of `||a_r||_2`; JSON 27 MB.
- Quality at the specified reproducibility level. Frozen sizes: the stage 4 numerical comparator with T10's frozen tolerance under the OI-8
  ruling (same pointing only): `passed`, `failed` or `rejected` as it answers. Larger sizes: T10's record does not hold off its pointing
  (OI-8; the comparator's derivation check rejects the pointing), and no tolerance is frozen for them, so the answer is `incomplete` with
  **OI-12** (new) and the differences as readings, never a pass. **OI-13** (new): `destriper-product/1` embeds a dense design matrix
  (samples x (pixels + baselines)), so no product of a larger scan can be written (scan-1m: 1,048,576 x 12,288 entries); the larger sizes
  are compared in memory, the CPU side by the recipe's solver in the same process.
- Times, each apart, per repetition (a repetition is one process): queue wait (from `sacct`: Submit to Start, once per job); process
  start to the end of `import torch` (the shell's launch time passed in); CUDA initialization (context and first kernel, synchronized);
  reading (file read and `timestream.read`); host to device (pixel and value tensors, synchronized); compute, first solve and then warm
  solves (synchronized); device to host (map and baselines); checks (product build, `product.read`, `read_sidecar`, the comparator). Per
  iteration the stopping test and the CG scalars cross to the host (4 scalars, counted), which is the algorithm's own synchronization.
  Denominators: attempted, succeeded (converged, product read, contract accepted, comparator passed; for larger sizes: converged and
  compared, answer incomplete) and failed by category (not-converged, refused, comparator failed, rejected, crashed, device unavailable).
- Quality before speed (stage 4, M3; A15, A50). Every timing is sealed to its run when the run starts; it is released only against a
  quality record that the harness itself made from that run's products (by identity, never a dict or a copy), and only if that record says
  `passed`. Frozen sizes release after their comparator passes; larger sizes stay withheld (OI-12), written to a sealed file that no report
  reads. The CPU recipe's own timings (T12-14) are released on the recipe's quality record (below); the GPU's never on the CPU's record.
- Release-time CPU side. In `a13-measure.sh` the CPU side runs in the same job on the node's allocated CPUs (8 CPUs requested, the
  recipe single-threaded by `OMP_NUM_THREADS=1`, stated): the recipe's own command line under the project's Python 3.13 environment for
  the frozen sizes (the reference products), and the recipe's solver in the venv process for the larger sizes.

**T12-14, the CPU benchmark (C1-C8; Section 14.2; stage 4 part B).** Same scientific work, input domain and native output level, each
recipe at its Freeze B bytes; numbers are records, not gates (K12: no targets).
- C1. Destriper, in process: I/O (file read), reading (JSON parse and `timestream.read`, with its connectivity probe), initialization
  (a separate fresh-process probe: interpreter start and the recipe's imports), conditions (not applicable: the recipe consumes no
  conditions, `conditions_ref` "none"), compute (`solver.solve`), output (`product.build`, `dumps`, write), checks (`product.read`,
  `read_sidecar`). The whole command line `destriper.py solve` timed separately as the total wall. The in-process components are
  sequential in one thread (no overlap), and the total is measured, never their sum. Workload: samples, baselines, iterations.
- C2. The in-process product is byte-equal to the command line's product of the same input and `product_id` (the same work); else the
  benchmark is `failed` for that recipe.
- C3. T08 (`reco.calo.cell-cluster/1`), in process, the command line's `reconstruct` path step by step: configuration (its own component,
  beside the import probe), readout (reading and I/O), pedestal and gain payloads (conditions), the cell chain per event (conversion),
  clustering per event (compute), event documents and the writer (output); `check-product` as checks (command line). C2's byte equality
  against the command line's product. Per-event compute latency quantiles (50, 90, 99 %) and events per second.
- C4. T09 (`reco.light.channel-likelihood/1`): the command lines `fit --likelihood charge-time --starts multistart`, `topology` and
  `check-product`, as the evaluation runs them; initialization by the import probe. Reading, conversion, compute and output happen inside
  one call per event and are not separated: separating them means instrumenting a frozen file (recorded, not measured).
- C5. Recipe identity: every file of the recipe is pinned by SHA-256 at `d1f6fc30` (Freeze B's bytes; `calo_cluster.py` and
  `photon_likelihood.py` with exactly the recorded post-D4 bytecode line, decisions.md "The held bytecode line"); a different byte is
  `rejected` and nothing is timed.
- C6. Release (quality before speed): the destriper on the record's quality (T10 replay PASS, job 7596623, at its frozen hash) and, on
  the frozen pointing, this run's product passing the numerical comparator against the command line's; T08 and T09 on their evaluation
  attempt-1 pass at Freeze B bytes (summaries 7620411 and 7613459) with C5. T07 failed at attempt 1 (STATE.md): no speed number may be
  released for it (A50), so it is not measured.
- C7. Inputs. Destriper: the four A13 sizes. T08: main, block 1, stratum 4, 600 events, by the frozen generator `gen_t08_grid.py`
  (`d901362c…`) through `t08_fixture_files.py`, as E6a ran it. T09: main, block 1, stratum 9, 40 events, by `gen_t09_sphere.py`
  (`2657f56b…`). Tests use the tracked block-1 examples (`examples/reconstruction-calorimetry/recorded/events.*`, 2 events;
  `examples/reconstruction-photon-likelihood/recorded/main.readout`). Repetitions: 3 per recipe and size (the first process is "first",
  the rest "warm"; the file-system cache is not controlled, stated).
- C8. Reported per recipe: each component's seconds per repetition with the median, success and failure denominators, peak memory per
  process (`wait4`), throughput, and the not-measured list with reasons: T07 (failed gate; native build), `reco.timing.time-chain/1` (not
  named by part B; no A13 role), the destriper's conditions (none consumed), T09's inner components (C4), queue wait on the CPU partition
  (the job's own, from `sacct`, not per recipe).

**T12-22, execution fields (plan Section 10.4).** Written for the GPU subchain only, as a record in the run output: layout (contiguous
1-D tensors: pixel int64, value float64, structure of arrays), residence (host for reading and product, device for the solve), ownership
(PyTorch's caching allocator, released at process end), asynchronous completion (one CUDA stream, synchronized at each stopping test and
at every timing boundary), transfer edges (host to device once per solve, 16 bytes per sample; device to host once, 8 bytes per pixel and
baseline; 4 scalars per iteration), zero-copy not claimed (copies measured), precision (float64; float32 a reading), batch (one timestream
per solve, no batching), memory limits (the measured device peak, `max_memory_allocated`, against the device's 97,887 MiB; host peak RSS),
streaming queues (not applicable: an offline solve, no queue or in-flight limit). The CPU recipe's command line gets no GPU field: asked
for the CPU backend, the function returns none.

**Mutation check (after green).** Planted one at a time in a copy of the harness, each must turn at least one test red: the stopping test
loosened tenfold; the budget ignored; a silent CPU fallback for `cuda`; a float32 product built; the zero-sum projection of the right side
removed; the map binned without subtracting the baselines; the input-identity check removed; a larger size answered `passed`; a timing
released without the gate's record; released on a failed gate; GPU fields written for the CPU backend; the recipe identity check removed
(benchmark); the byte equality of C2 dropped; T07's timing released. (As run: see the disclosed changes below.)

**Changes after the tests were written (disclosed; red logs `jobs/t12-stage5/red/`).** (1) The mutation list: "the zero-sum projection of
the right side removed" is an equivalent mutant (`F^T Z y` sums to zero exactly, since `Z` removes each pixel's mean and the pixel means
cover every sample), so it is replaced by "binning sums instead of averaging"; added: "a frozen size compared in memory", "the owner check
removed", "a comparator failure ignored by the recipe gate"; 17 in all (`jobs/t12-stage5/mutate.py`). (2) The command line takes `--size
custom` for any pointing but the record's (always OI-12), so the tests need no larger file; the named sizes check their shape (and the
frozen ones their bytes). (3) The float32 reading's budget is capped at twice the float64 iteration count plus 10 (a reading's budget,
stated): at 1e-10 float32 never converges, and the recipe's budget (10 per baseline) would spend 655,360 iterations on scan-16m. (4) The
test module is listed in the required torch-backend CI job (`tests/tools/test_pyproject.py` requires every module with a PyTorch skip
there).

**Jobs (drafted; the coordinator submits).** `jobs/t12-stage5/t12-stage5.sh` (CPU, `edr2-al9_short_serial`, `--time 03:00:00`): units,
neighbours, the CPU benchmark, the full suite and static; LCG the only allowed failure. `jobs/a13-gpu/a13-pilot.sh` (B6000, 1 GPU, the
frozen sizes only, 2 repetitions; fix round 1: limit 30 min, wall 10 to 15 min with the setup). `jobs/a13-gpu/a13-measure.sh` (B6000, 1
GPU): every size, sized from the pilot, re-pinned by the coordinator after it. Each follows the snapshot rule
(`jobs/t12-stage4/t12-stage4-r2.sh`).

### Stage 5, fix round 1 (review `jobs/t12-stage5/REVIEW.md`, NOT READY 1/2/6/3; every finding adopted)

Order of work, disclosed: the changed and new tests were written first and run red against the round-0 harnesses
(`jobs/t12-stage5/red-r1/red-1-round0-harness.log`: a13 36 run, 3 failures, 2 errors; benchmark 19 run, 3 failures); the trajectory test and
the exact iteration counts passed there (they characterise round-0 behaviour, which the review found faithful by reading). One new bound
was set before any run and changed after the first green attempt: the injected-offset drift bound, 1e-12, read 5.2e-11 at c = 37.5 on the
unmutated harness (rounding of c against a late, small vector), so it is 1e-8 (a removed projection leaves 1e-1 to 1). The rounds-0 jobs
7648900 and 7648934 ran on the round-0 files and are readings for this round.

- **C1** (the coordinator's fix, kept): the GPU jobs' sandbox binds the real `/dev` (`--dev-bind /dev /dev`) and checks inside it that
  PyTorch sees the device before any step (else exit 3).
- **I1** (the tests did not pin the transcription). Exact iteration equality with the recipe (G1, G2). New tests: the trajectory, for
  every budget k = 1 .. n-1 on the frozen noisy and noiseless pointings and a 2,048-sample scan, both paths raise the recipe's
  `NotConverged` after k iterations with recomputed residuals within 1e-6 relative; the reported residual equals the one recomputed with
  the recipe's NumPy operators from the returned baselines (1e-6 relative, absolute floor 1e-13 at the rounding floor); the restart branch
  (stopping 1e-17 on the frozen pointing, budget 150: both paths restart, the same number of times, the recipe's counted from its
  `_zero_sum` calls, and end `NotConverged` at 150); fault injection (`probe["offset"]` puts c times the null vector into the start of a,
  the start of the direction and every application of D: the solution is unchanged within 1e-12 and every kept vector's mean stays below
  1e-8 of its largest entry). The reviewer's survivors are in the mutation list: stopping on the recurrence residual, the zero-sum
  projection removed from a, from the direction, from the image, and a stricter stopping value. In exact arithmetic the three projections
  are redundant (D maps into 1-perp and the Krylov space stays there); the fault injection is what makes them observable.
- **I2** (GPU limits ignored the setup; job 7648901 spent 7.6 min before its first step): the pilot's limit is 00:30:00, its wall
  prediction 10 to 15 min; the measurement's sizing rule adds the measured setup (snapshot and checks, from the pilot's receipt times).
- **M1**: a zero right side gives 0 iterations and residual 0.0, as the recipe (it gave 1.0); test added.
- **M2**: on another pointing the GPU run's `checks` exclude the CPU recipe's solve (timed apart in `cpu_side`); test added.
- **M3**: `process_to_import` ends after every import of the harness module (the plugin's and the recipe's included), not after `torch`.
- **M4**: the overlap statement is per recipe: the destriper's `total_wall` is the command line's own run and overlaps every in-process
  part; T08's `checks` is a command line's wall (its own interpreter start and reading); each T09 part is a whole command line's wall.
- **M5**: Q2 is a coordinator ruling for the user to confirm (below), not the user's word.
- **M6**: the jobs' queue-wait line no longer depends on `tee`'s status: the computed line is kept in a variable and its own exit decides.
- Nits: the destriper's pinned bytes cite the T10 replay of record (job 7596623; `destriper.py` 2a8a0a04, `solver.py` 85ca7de7), not the
  evaluation manifest, which does not hold the destriper; the jobs' `steps.tsv` seconds are whole-step walls (process starts included),
  never component timings.

**Proposal, not adopted (OI-12's way out; the user's call).** An intermediate pointing of about 4,096 to 65,536 samples with a T10-style
derived tolerance would let A13 release a GPU speed number at a size where the GPU could matter. It would need: a fixed generator and seed
for that pointing; kappa and G recomputed for it (`t10_comparator.fixture_numbers` builds dense matrices: at 65,536 samples an iterative
eigen-solver or a smaller size); the exact rational reference of the T10 replay or a stated substitute at that size; a record in the
`t10-replay-tolerance/1` format with tau = safety x kappa x eps; a review; and the user's freeze, as for T10's record. Not built here.

**Jobs (fix round 1; drafted).** `jobs/t12-stage5/t12-stage5-r1.sh` with `SOURCES-r1.sha256` and `mutate-r1.py` (24 mutations);
`jobs/a13-gpu/a13-pilot-r1.sh` (00:30:00) and `a13-measure-r1.sh` with `jobs/a13-gpu/SOURCES-r1.sha256`. The round-0 scripts and
manifests are kept.

## Stage 6: A37 and §9.6 in T12 (fixed before the tests were written)

**Scope.** T12-18 (the g×E degeneracy) and T12-19 (the weak-mode witness), A37 and §9.6 as R31 keeps them in T12. Both are
identifiability tests on synthetic fixtures: no constant is derived, no alignment or calibration quality is claimed (R31), and nothing
here waits for a K09 threshold (R37). Q3 is answered (T12 runs its own reprocessing of 7003 and 7004) and Q5 is moot (T10 done).

**Files.** `tests/contracts/t12_degeneracy.py` (the harness: the g×E fit and its report, the reprocessing of 7003 and 7004, the T12
method card, the checks, the assessments, the command line) and `tests/contracts/test_t12_degeneracy.py`. They live in `tests/` for the
reason stage 1 gives (they import the contracts, the control layer, T10's fixture tool and T07's test arithmetic). No production file,
recipe, adapter asset, frozen file or file of `jobs/evaluation/SOURCES.sha256` changes; T10's `t10_a37.py` and T07's
`test_acts_cai_refit.py` are imported, never edited.

**Fixture form shared with T10 (T12-18).** T10's `fixture_tools/t10_a37.py`: the design `gxe_design(C, E)` (one row per channel and
event, `ln A = ln g_c + ln E_e`), `exact_rank` (rational elimination), and its tolerances `GAUGE_TOLERANCE = 1e-12` (relative, for
amplitudes, identifiable combinations and recovered values) and `CONVERGED = 1e-20` (sum of squared log residuals), set in
`t10-timing-stage-plan.md` section 6.1 (row A37-T10) and used by job 7627284. All values below are exact inputs, without noise, so
every check is deterministic (R37: numerical tolerances), and there is no `n σ` in T12-18.

- Two-parameter case (the brief's "two-parameter synthetic fit of `y = gE`"): one channel, one source, `N = 6` observations of the same
  type, `g = 1.25`, `E = 2.0`, so `gE = 2.5`; `gxe_design(1, 1)` repeated `N` times. Gauge `a = 3`.
- T10's form: `C = 8` channels, `g_c = 1 + 0.05 c`; `E = 5` events, `E_e = (1, 2, 3, 5, 8)`; reference event 2; gauge `a = 3`.
- The named external scale: `constraint.external-energy-reference`, the energy of the reference source or event is known.

**T12-18 expectations (`gxe`).**
- G1 (rank). Exact rank of the design: 1 of 2 parameters (two-parameter case), `C + E - 1 = 12` of 13 (T10's form); with the named
  constraint row, 2 and 13.
- G2 (report). Without a constraint the fit reports exactly the identifiable combinations and no absolute value: the two-parameter case
  `reported == {"gE"}` with `gE = 2.5` (1e-12 relative); T10's form the gain ratios `g_c / g_0` and the products `g_c E_e` (1e-12
  relative to the truth's); `g` and `E` are listed as `unidentified` with the gauge `g -> a g, E -> E / a`.
- G3 (gauges, convergence). The two gauges `(g, E)` and `(a g, E / a)` give the same `y` (1e-12 relative); fits with `ln g_0 = 0` and
  `ln g_0 = ln a` both converge (residual at most 1e-20) and their scales differ by `ln a` (1e-12); the reported combinations agree in
  both gauges (1e-12). Convergence does not identify the scale.
- G4 (holdout). A same-type holdout (two-parameter case: the last observation; T10's form: the last event, its energy refitted from its
  own amplitudes with the gains held) closes in both gauges (residual at most 1e-20). Claims judged: "absolute scale validated by a
  same-type holdout" and "absolute scale identified by convergence" are refused (listed in `claims_refused`); the record says
  `same-type holdout: not validation (A37)`.
- G5 (named external scale). With `constraint.external-energy-reference` the rank is full and the fit reports `g` and `E` (1e-12 relative
  to the truth), naming the constraint as the identifying information; a constraint whose identifier does not start with `constraint.`
  is not a named constraint and identifies nothing.
- G6 (R32 record). The fit's payload sidecar (`conditions-payload/1`, built as stage 1's): without a constraint
  `unconstrained_modes == ["mode.global-gain-scale"]`, `constraints_used == []`; with it `constraints_used ==
  ["constraint.external-energy-reference"]`, `unconstrained_modes == []`; in both `independent_validation` names neither the constraint
  nor a same-type holdout, and `check_validation_claim(payload, constraint)` refuses the constraint as validation
  (`conditions.constraint_as_validation`, CAI-T06-3's rule).

**Planted defects (`gxe`, each detected, exit 1, failed set exact).** `report-absolute` (the fit reports `g` and `E` without a constraint):
`{G2}`. `holdout-as-validation` (the harness accepts the same-type holdout claim): `{G4}`. `constraint-as-validation` (the constrained
sidecar lists the constraint in `independent_validation`): `{G6}`. `unnamed-constraint` (the constraint is recorded as the text "the
energy is known", not a `constraint.` identifier): `{G5, G6}`.

**The reprocessing of 7003 and 7004 (T12-19).** Through the stage-1 loop machinery: a fixture contract validated by the control layer's
`validate_contract`, every step admitted by `dv.admit` with its computational identity, a receipt per step, the checks by digest as
`check_result` facts, the control-layer labels and `publish`; the identity-keyed cache lookup with `reuse_decision` acted on only through
`dv.admit(..., reuse_source=...)`; R32 records checked with `check_used`. It has no outer-round family: nothing is derived (R31), so a
round family would need a fake derivation; the loop's round rules are stage 1's (T12-01 to T12-04). Contract (session mode M1, steps in
order):
`nominal-alignment` (the zero payload `encode_payload({}, geometry, "nominal")` and its R32 sidecar, `t07_alignment_payload.py`),
`generate-7003` and `generate-7004` (the frozen CAI generator `t07_cai_fixture_generator generate --fixture cai-clean|cai-sagitta
--block 1 --stratum s --first-event 0 --count 3000`, s = 0..3, exactly as `CaiFiles` in `test_acts_cai_refit.py`), `refit-7003` and
`refit-7004` (the frozen driver `acts_tracking_driver refit` at nominal geometry, field 1 T, hit sets from truth with the truth `q/p`
assumed, no payload argument, no vertex or beam constraint: CAI-T07-4's fits), `witness` (checked; required: the weak-mode check and the
method-card check). Deliverable `weak-mode-witness` (`witness`), tier T2. The executed order is nominal-alignment, generate-7003,
refit-7003, generate-7004, refit-7004, witness. The command line runs the native programs inside the steps; the unit tests also run the
same contract with a toy executor (Gaussian toys from `weak_mode_toys` of `test_acts_cai_refit.py`), which tests the plumbing only.

**Native identity (G05 form).** Pinned SHA-256: driver `7556beb828f3a9029a79a34f41c938e7f9ff328281855800d21d655649ece958` (Freeze B
item "T07 built binary acts_tracking_driver"); CAI generator `f1c7309a804ba71a8e54a1ff55f16685a4255703142e130624fe290e77888931` (the
build of job 7546791, which wrote T07's record, and of the Freeze-B run 7585954, byte for byte). Each is hashed afresh when the run
starts and recorded in each step's document. The T07 record: job 7546791 `cai-refit.log`, SHA-256 `0f60e9ac…` as pinned in `t10_a37.py`
(`T07_LOG_SHA256`), read only.

**Tolerances (T12-19).** `k = 4.5` and `n = 4.5` are CAI-T07-4's (`K_WEAK`, `WEAK_N_SIGMA` in `test_acts_cai_refit.py`;
`calibration-alignment-interfaces.md`, T07; R37: `k` a fixed threshold, `n` times the se from the fixture's statistics); the cells,
units and se are `weak_mode_self_check`'s, imported. The agreement with T07's record is at the record's printed precision: track counts
exact, per-track and stated ratios within 1e-4 (printed to 4 decimals), the change in mean χ²/ndf and its se within 1e-5 (printed to 5
decimals). The generator and the driver are the same bytes and deterministic, so the two runs should agree to that precision; a larger
difference is a finding, not a tolerance to widen.

**T12-19 expectations (`witness`).**
- W1 (native identity). The driver and the generator hash to the pinned values (otherwise the command refuses: `rejected`, exit 2, before
  any step); `acts_tracking_driver geometry-id` equals the nominal payload's `derived_against.geometry_id`
  (`nominal_geometry_id()`), and each native step's document records both hashes.
- W2 (records). Every step ran once, in the order above; the fixture headers say 7003 and 7004, block 1, strata 0-3, 3000 events each;
  every track is fitted (none failed); each refit product records the nominal alignment payload (slot `alignment`, origin nominal, round
  null) and `check_used` passes; both refits consumed the same payload identity, and their data inputs differ.
- W3 (cache). Before each refit the harness asks of every cached product of the same recipe (`t12.cai-refit/1`) whether its data input is
  the same and what `reuse_decision` says with the payload resolved afresh. For `refit-7004` against `refit-7003` the payload is the
  same (`reuse_decision`: reuse true) but the data differ, so it is not a hit, nothing is acted on and the step is computed. Positive
  control: `refit-7004` requested again (same data, same payload) is a hit, acted on through admission, and the control layer records a
  `reuse` of `refit-7004`'s own artifact. A control-layer reuse of `refit-7003`'s product as `refit-7004` is refused at admission.
- W4 (the weak mode). In all 8 cells (charge ±1 × bending bins 0-3), the change in `q/p` is at least `k` per-track σ and at least `k`
  stated σ (0.00412 per GeV), and the change in mean χ²/ndf is within `n` se, in every cell and over all tracks.
- W5 (reuse of T07's fixture). The 8 cells reproduce CAI-T07-4's record (job 7546791) within the tolerances above.
- W6 (χ² is blind to it). A χ²-only judge (the change in mean χ²/ndf over all tracks within `n` se, the form of a "residuals converged"
  check) passes on 7004 against 7003 while W4's bias holds: the record states that χ²/ndf is essentially unchanged while `q/p` is biased.
- W7 (method card). The T12 reprocessing's method card (`t12-method-card/1`, the rules of `timing_recipe/method_card.py`: every mode has
  a witness, named constraining information and independent observables, the two identifier sets disjoint, `constraints_used` only this
  mode's constraints and never an observable) lists the mode `mode.sagitta-like-deformation` (description "sagitta-like deformation"),
  with `constraint.vertex-or-beam` among its constraining information (R37 names it), `constraints_used == []` (nothing derived), and
  `not_satisfying_a37` naming the T12 loop placeholders, convergence of a fit and closure on a same-type holdout. The card check passes.
- W8 (labels, release, claims). Every step is labelled `ok`; the deliverable is published at T2 naming the witness artifact; the record's
  claims are `{label: synthetic, quality: none, a37: "weak-mode witness reproduced in a T12 reprocessing (identifiability); no
  alignment quality", control_rules: "not qualified (G07, mode M1)"}`.

With the toy executor W1 and W5 cannot hold (no binaries, no T07 numbers): an honest toy run fails exactly `{W1, W5}`, and each plant
below fails `{W1, W5}` plus its own set.

**Planted defects (`witness`, each detected, exit 1, failed set exact).** `no-deformation` (the witness step compares `refit-7003`
with itself): the weak-mode check fails, `witness` is `held`, nothing is published: `{W4, W5, W6, W8}`. `visible-chi2` (every 7004
χ²/ndf raised by 0.1, a visible deformation, about 18 se over all tracks): the same `{W4, W5, W6, W8}`. `card-without-constraint` (the
mode's constraining information emptied): the card check fails, `held`, nothing published: `{W7, W8}`. `constraint-as-validation`
(`constraint.vertex-or-beam` also offered as an independent observable): `{W7, W8}`. `reuse-across-data` (the lookup ignores the data
input, so `refit-7004` gets a hit on `refit-7003`'s product, acts on it, is refused at admission and computes): `{W3}`.

**Exit codes (core/status.py).** `t12_degeneracy.py gxe [--plant P] --out FILE` and `t12_degeneracy.py witness --build DIR --t07-record
FILE --work DIR [--plant P] --out FILE`: `ok` 0, every expectation holds; `failed` 1, one does not; `rejected` 2, bad input (unknown plant,
an output that exists, a missing folder, a work folder that is not empty, a binary or the T07 record not the pinned bytes); `incomplete`
3, a crash, a native program that fails, or a record that cannot be written. Exit codes from `core.status.exit_code`.

**Found while implementing (after the red run; no expectation changed).** `t07_alignment_payload.payload_sidecar` lists only the
degrees of freedom a payload moves, so the zero payload's sidecar has no `alignment` section and the R32 reader refuses it
(`conditions.alignment_incomplete`, seen as W2's `check_used` error). The harness completes the nominal sidecar (every plane's parameters
of the parametrization, all at nominal) and seals its identity again; T07's tool is not changed (a frozen adapter asset). The check
digests of the witness step are recorded in each record (`check_digests`), not pinned in the test.

### Stage 6, fix round 1 (review `jobs/t12-stage6/REVIEW.md`, 0/1/5/3; written before the changed tests)

Job 7636529 failed only on `tests.adapters.test_t04_evaluation_layout.TaskDeadline` (a latent frozen test that reads the job's real
`SLURM_JOB_END_TIME` and fails with under an hour left); it is not edited, and the redrafted job `t12-stage6-r1.sh` asks for 3 h.

- **I1 (open finding against T07, no stage-6 code change).** `t07_alignment_payload.payload_sidecar` (a frozen adapter asset) writes no
  `alignment` section for a payload that moves nothing, and the R32 reader refuses such a sidecar (`conditions.alignment_incomplete`,
  `contracts/conditions.py`). The harness's completion of the nominal sidecar stays a workaround, not a fix: the defect is recorded as a
  post-freeze change request in `calibration-alignment-interfaces.md` ("Open, not gaps"), for the coordinator to put to the user.
- **m1 (claims).** Four claims are judged: "absolute scale validated" by the same-type holdout, "absolute scale identified" by
  convergence, "absolute scale identified" by the constraint used, and "absolute scale validated" by the constraint used. Only the third
  is accepted: a constraint the fit used identifies the scale but is never its validation (§9.6, CAI-T06-3). G4 requires the holdout and
  convergence claims refused; G5 requires exactly the "identified" claim by the constraint accepted and the "validated" one refused.
- **m2 (holdout gauges).** Each holdout fit records its `ln g_0`; G4 requires the two to differ by `ln a` (1e-12), so the closures are
  shown in two different gauges, not twice in one.
- **m3 (what the driver applied).** The driver is run as CAI-T07-4 ran it, with no payload argument (unchanged). Each refit product now
  records the native product header's `alignment_payload` per stratum (none expected: nothing applied, `applied: "driver nominal
  geometry, no payload argument"`) and cites T07's evidence that the zero payload through the placement route gives the plain geometry's
  records: the line "CAI-T07-3 zero payload through the placement route: /1 records equal" of job 7546791's `cai-refit.log`, which W5 now
  also requires. W2 requires the header value to be none in every stratum. So the nominal payload in `conditions_used` stands for the
  driver's built-in nominal geometry, and the record says so.
- **m4 (native identity per step).** The executor rehashes the driver and the generator at every native step (never a stored value), and
  the cache keys on it: a hit needs the same data input, `reuse_decision`'s reuse and the same native identity as the cached product's
  step. Each cache entry records `same_native`; W3's expected entry gains `same_native: true`. A test changes the identity after the run:
  the lookup for `refit-7004` then finds no hit (`same_native: false`).
- **m5 (job).** The job runs stage 2's scope check (`t12_reprocessing.py scope-check`) with `--import tests.contracts.test_t12_degeneracy`
  against every live root (exit 0) and its control, an evidence path in the live tree (exit 2); the receipt holds `ldd` of both binaries
  and the SHA-256 of every library they resolve to.
- **n2.** The nominal sidecar's planes come from the nominal geometry text (`planes N` of `nominal_geometry_text()`), not a literal 8.
- n1 (W6 restates part of W4) and n3 (`visible-chi2` run natively) are not taken: W6 keeps its own statement (the χ²-only judge), and the
  χ² side's power is shown on toys.
## A13: reopened by the user (stage 5)

The user answered Q1 on 2026-11-13 "Record blocked-by-resource (Recommended)"; later the same day the user reopened A13: "A13: GPU part:
allow use GPU", with the subchain (T10 destriper: its baseline solve on the GPU against the CPU recipe on the same pointing, the one recipe
with a frozen reproducibility tolerance) and the partition (B6000 devel, `b6000-al9_devel`, `--gres=gpu:1`, no `--qos`). Q1's answer is
superseded; R14's `blocked-by-resource` no longer applies to A13. R30's tiny hardware job ran first (job 7648670, PASS). U8 ("Use the site
GPU partition") stands. The T07-T09 recipes still have no GPU subchain (CPU code); A13 covers the destriper only, and the CPU engineering
benchmark (T12-14) is recorded beside it. See "Stage 5".

## Questions and rulings

- **Q1 (A13 subchain): superseded** by the user's word, 2026-11-13: "A13: GPU part: allow use GPU" (subchain T10 destriper, partition
  B6000 devel). The earlier answer, "Record blocked-by-resource (Recommended)", stands only as history.
- **Q2 (A13 reproducibility): a coordinator ruling for the user to confirm** (stage 5 brief and fix round 1, M5, 2026-11-13): the stage
  4 numerical comparator with T10's frozen tolerance under the OI-8 ruling, on the frozen pointing only; larger sizes `incomplete`
  (OI-12). Its ground is the user's choice of the subchain: the T10 destriper, "the only recipe with a frozen reproducibility tolerance"
  (as the stage 5 brief records the user's choice, 2026-11-13). The user has not ruled on Q2 itself.
- **Q3 (A37 in T12): answered** by the coordinator, 2026-11-13: T12's part needs its own reprocessing run of fixtures 7003 and 7004
  through the T12 loop machinery, because T12-19's acceptance says "inside a T12 reprocessing" and R31 says "reused", not cited. Stage 6
  (T12-19) runs it; T10's reading of the recorded log (`t10_a37.py` `witness_check`) is not T12's evidence.
- **Q4 (the previous-round link): closed** (coordinator, fix round 1, reversing the stage-0 reading). The schema has the fields:
  `derived_against.upstream_payloads` and `derived_from` hold the previous round's payload, and `producer.step_id` the producing step's
  identity (Stage 1, "Synthetic fixture"). No contracts change is needed.
- **Q5 (T10): moot** (coordinator, 2026-11-13): T10 is done (`t10-closeout.md`), so no T12 row waits for T10's part. Stage 6 shares
  T10's A37 fixture form (`t10_a37.py`) without changing it.

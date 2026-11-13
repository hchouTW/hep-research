# T12 stage plan: reprocessing and performance (finish-plan F2)

State: stage 0 and stage 1 drafted on branch `t12/stage1` (from `a8388685`), in fix round 1 after a fresh review; not committed. This plan
was written before stage 1's tests; the fix-round expectations below were added before the changed tests (red logs with file hashes in
`jobs/t12-stage1/red/`). Paths are relative to
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
| 2 | Conditions invalidation and identity on the T07-T09 recipes' products: A04, A40, A42, A14, G05, §9.8-9.9 | T07-T09 merged (E6); Freeze B for any quality reuse |
| 3 | Partitioning, recovery and boundaries: A11, A12, §10.2 items 3-7 | Stage 2; Freeze B for the T07-T09 recipes' quality |
| 4 | Comparators and CPU benchmarks: §14.1, §14.2, A15, quality before speed | Freeze B (K09 gates); T10 for T10's recipe |
| 5 | A13 GPU subchain against CPU (R30, U8) | Stage 4; a GPU-capable subchain (question Q1); the tiny confirmation job |
| 6 | A37 and §9.6 in T12: the g×E degeneracy and the weak-mode witness | T10 for T10's part; question Q3 |
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
| T12-14 | §14.2 | CPU engineering benchmark: the same scientific work, each component timed apart, overlap stated | Report reading, initialization, I/O, conditions, conversion, compute and checks separately, with success and failure denominators | Stage 3 | 4 | FB; T10 for T10's recipe |
| T12-15 | A15, A50, §16.1 "quality before speed" | A faster variant with worse tails or coverage is rejected under fixed gates or listed as another working point | A planted faster variant with a fatter tail fails the gate; no speed number is reported before the quality gate | K09 frozen | 4 | FB |
| T12-16 | A13, R30, U8 | GPU subchain against CPU: include transfer, initialization and queues; compare quality at a fixed reproducibility level | Section "A13 on the site GPU partitions" | Stages 4; Q1 | 5 | GPU, FB |
| T12-17 | R14 | Without a usable GPU subchain, A13 stays `blocked-by-resource` with CPU measurements recorded; T12 stays blocked for A13 and P5 is incomplete | CPU timings from T12-14 are recorded beside the A13 row; T12's state and every P5 report say blocked for A13 | Stage 4 | 5 | FB |
| T12-18 | A37, §9.6 | g×E degeneracy: convergence and same-type holdouts are no proof of absolute scale; identifiable combinations and named constraints retained | A two-parameter synthetic fit of `y = gE` reports only `gE` (or a named external scale); a same-type holdout is not accepted as validation | Q3 | 6 | T10 (shared fixture) |
| T12-19 | A37, §9.6, R31 (weak-mode witness) | The T07 weak-mode fixture reused in T12: χ²/ndf essentially unchanged while `q/p` is biased; the method card lists the mode and its named constraint | Reuse `CAI-T07-4`'s fixture 7004 against 7003 inside a T12 reprocessing; the card lists `sagitta-like deformation` with its constraint | T07 merged | 6 | T10 |
| T12-20 | R20, A26-A36 | A26-A36 runtime: injection before filtering, scan settings, per-channel exposure, angle bases, CRES first segment, averaged spectra, IRF reuse, veto-only scintillation, null modes, frame definitions, injected data labels | One executed case per scenario on a backend that covers it; otherwise a recorded gap keeping P4 execution incomplete | T11 design (F1) | 7 | none (backend absent: gap) |
| T12-21 | §16.1 T12 row, A10 | Waveform omitted: higher-level parameters usable; trace-requiring recomputation judged infeasible | A product with `raw` retention removed refuses a trace rerun (`can_recompute` false) inside a T12 reprocessing | T08 merged | 7 | none |
| T12-22 | §10.4, contract-map Section 10.4 row | Execution fields beyond concurrency, layout, residence and ownership: transfer edges, precision, batch and memory limits, streaming queues | Written only where a backend supports them; a CPU-only CLI gets no GPU field | Stage 5 findings | 5 | GPU |
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

## A13 on the site GPU partitions (stage 5, planned only; nothing submitted)

U8: "Use the site GPU partition". R30: a tiny approved job confirms the hardware and what the job receives before any GPU pilot.
- **Partitions.** `b6000-al9_devel` (RTX PRO 6000 Blackwell, sm_120, 1-2 GPUs per job, QoS `b6000_res` caps the partition at 2 GPUs) or
  `v100-al9_short` (V100, driver CUDA <= 12.9). `--gres=gpu:N`, never `--qos`; each CPU on a GPU node is billed 2.
- **Tiny confirmation job.** 1 GPU, 1 CPU, 2,000 MB, 10 minutes: `nvidia-smi`, `CUDA_VISIBLE_DEVICES`, the device the subchain's runtime
  sees, and the driver's CUDA version. Bound: 0.17 GPU-hours, 0.33 billed core-hours.
- **Pilot (after Q1 and the confirmation job).** The chosen subchain on a fixed block-1 sample, CPU and GPU from the same snapshot, timing
  reading, initialization, transfer, queue and compute apart (§14.2), quality compared at the reproducibility level Q2 fixes. Proposed caps
  for the coordinator to approve: 1 GPU-hour, 2 billed core-hours, at most 6 jobs.
- **Stops.** A failed quality comparison blocks the GPU result before any speed number (T12-15). No GPU-capable subchain: A13 stays
  `blocked-by-resource` (T12-17), now for want of a subchain, not of hardware.

## Questions and rulings

- **Q1 (A13 subchain): for the user** (coordinator, fix round 1). No T07-T09 recipe has a GPU path at this baseline (the ACTS build,
  calo-cluster and photon-likelihood are CPU code). Which subchain should A13 measure: a GPU build of one recipe's kernel (new work, which
  task owns it), a learned model's inference (hep-ml), or is A13 recorded `blocked-by-resource` for want of a subchain even though the
  hardware is approved? Owner: the user.
- **Q2 (A13 reproducibility).** §14.1 lets the recipe declare byte, numerical or statistical reproducibility for the GPU-CPU comparison; it
  needs K09-level tolerances. Fixed with Freeze B, or by T12 before the pilot? Owner: the coordinator.
- **Q3 (A37 in T12).** R31 says the weak-mode witness is the T07 fixture "reused in T10 and T12". Does T12's part need its own reprocessing
  run of fixtures 7003 and 7004 through the T12 loop machinery, or is citing `CAI-T07-4` with a T12 g×E fixture enough? Owner: the coordinator.
- **Q4 (the previous-round link): closed** (coordinator, fix round 1, reversing the stage-0 reading). The schema has the fields:
  `derived_against.upstream_payloads` and `derived_from` hold the previous round's payload, and `producer.step_id` the producing step's
  identity (Stage 1, "Synthetic fixture"). No contracts change is needed.
- **Q5 (T10).** T12 depends on T07-T10. Which T12 rows may close before T10 is done, with T10's part listed open? Owner: the coordinator.

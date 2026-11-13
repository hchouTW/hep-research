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
| 3 | Partitioning, recovery and boundaries: A11, A12, §10.2 items 3-7 | Stage 2; Freeze B for the T07-T09 recipes' quality |
| 4 | Comparators and CPU benchmarks: §14.1, §14.2, A15, quality before speed | Freeze B (given), T10 (done); part A (T12-13, T12-15) on branch `t12/stage4` (from `28763f50`): reviewed NOT READY, fix round 1 re-reviewed (all closed but M3), fix round 2 drafted, not committed, see "Stage 4"; part B (T12-14) planned, waits for stage 3 |
| 5 | A13: recorded `blocked-by-resource` (R14; Q1 answered 2026-11-13); no GPU job. The CPU measurements of stage 4 (T12-14) are recorded beside it | Stage 4 |
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
| T12-16 | A13, R30, U8 | GPU subchain against CPU: include transfer, initialization and queues; compare quality at a fixed reproducibility level | Not run: `blocked-by-resource` (R14). The user answered Q1 on 2026-11-13, "Record blocked-by-resource (Recommended)": no T07-T09 recipe has a GPU subchain, so there is no GPU job. Reopened only if a GPU subchain is built and the user asks | none | 5 | blocked-by-resource |
| T12-17 | R14, Q1 | A13 is recorded `blocked-by-resource` (the user, 2026-11-13) with CPU measurements recorded; T12 stays blocked for A13 and P5 is incomplete | CPU timings from T12-14 (still in scope, stage 4) are recorded beside the A13 row; T12's state and every P5 report say blocked for A13, for want of a GPU subchain | Stage 4 (T12-14) | 5 | FB |
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

**Part B, T12-14 (planned only; waits for stage 3).** The same scientific work on the same input domain and native output level, each
recipe at its Freeze B hash: reading and probes, initialization, I/O, conditions, conversion, native compute and output/checks timed
apart; with overlap, the total wall time and how each part was measured, never a sum of overlapping times (§14.2). Workload units per
task (events for T07-T09, samples and baselines for the destriper); success and failure denominators, memory, latency quantiles,
throughput. Cold and warm apart (K12, t04-values-v4.md §12: no targets; numbers are records, not gates). No speed number is reported
for a recipe before its quality gate (T12-15); these CPU numbers are what T12-17 records beside A13. It needs stage 3's partition and
accounts (T12-10 to T12-12) and its own job approval.

## A13: recorded blocked-by-resource (stage 5; no GPU job)

The user answered Q1 on 2026-11-13: "Record blocked-by-resource (Recommended)". No T07-T09 recipe has a GPU subchain (the ACTS build,
calo-cluster and photon-likelihood are CPU code), so A13 stays `blocked-by-resource` under R14, with the CPU measurements recorded instead.
There are no GPU jobs: neither the tiny confirmation job of R30 nor a pilot. U8 ("Use the site GPU partition") stands for any later GPU
subchain, which would reopen A13 only on the user's word. The CPU engineering benchmark (T12-14) stays in scope, in stage 4, and its timings
are the CPU measurements recorded beside A13.

## Questions and rulings

- **Q1 (A13 subchain): answered** by the user, 2026-11-13: "Record blocked-by-resource (Recommended)". A13 is `blocked-by-resource`
  (R14), no GPU job; CPU measurements recorded (T12-14, T12-17).
- **Q2 (A13 reproducibility): moot** while A13 is `blocked-by-resource` (Q1); it returns with a GPU subchain.
- **Q3 (A37 in T12).** R31 says the weak-mode witness is the T07 fixture "reused in T10 and T12". Does T12's part need its own reprocessing
  run of fixtures 7003 and 7004 through the T12 loop machinery, or is citing `CAI-T07-4` with a T12 g×E fixture enough? Owner: the coordinator.
- **Q4 (the previous-round link): closed** (coordinator, fix round 1, reversing the stage-0 reading). The schema has the fields:
  `derived_against.upstream_payloads` and `derived_from` hold the previous round's payload, and `producer.step_id` the producing step's
  identity (Stage 1, "Synthetic fixture"). No contracts change is needed.
- **Q5 (T10).** T12 depends on T07-T10. Which T12 rows may close before T10 is done, with T10's part listed open? Owner: the coordinator.

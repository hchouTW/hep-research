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
| 4 | Comparators and CPU benchmarks: §14.1, §14.2, A15, quality before speed | Freeze B (K09 gates); T10 for T10's recipe |
| 5 | A13: recorded `blocked-by-resource` (R14; Q1 answered 2026-11-13); no GPU job. The CPU measurements of stage 4 (T12-14) are recorded beside it | Stage 4 |
| 6 | A37 and §9.6 in T12: the g×E degeneracy and the weak-mode witness | T10 for T10's part; question Q3 |
| 7 | A10, A26-A36 runtime (R20: T11 design, T12 runtime) | T11 design (F1, done); drafted on `t12/stage7` from `28763f50`, see "Stage 7" and its fix round 1: 3 executed (A32 with a harness-side pairing check), 8 recorded gaps (P4 execution incomplete) |

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

## Stage 7: A26-A36 at run time and A10 (fixed before the tests were written)

**Scope.** T12-20 (R20: A26-A36 were designed in T11; T12 owes the run time: one executed case per scenario on a backend that covers it,
otherwise a recorded gap that keeps P4 execution incomplete) and T12-21 (A10, §16.1 row T12). Branch `t12/stage7` from `28763f50` (Gate D:
Freeze B given, T10 done). No new backend is built (the brief; R14): where none covers a scenario, the gap is recorded with its reason and
the scenario is never narrowed to what a backend happens to do. Synthetic fixtures and read-only frozen files only; no quality claim.
Sources read: plan v9.2 §13 (A10, A26-A36), §8.3, §10.2, §10.5, §14.1-14.2, §16.1 row T12, R14, R20; `t11-cells.md` (bindings of F10,
F11, F28, F30, F34-F38); `t10-closeout.md` (W6 and W7 rows, A20-A24 recorded as gaps in the same way); `t08-scenarios.md` (A32, T08's part);
`freeze-b.md`; `contract-map.md`; STATE.md.

**Files.** `tests/contracts/t12_runtime.py` (the harness: the scenario table, the executed cases, the A10 reprocessing, the record) and
`tests/contracts/test_t12_runtime.py`. They import the backends' own modules and run their command lines; no backend file, recipe, frozen
file or entry of `jobs/evaluation/SOURCES.sha256` changes.

**Which backend covers which scenario.** The backends in this repository are the T07-T10 development bindings (`adapters/acts-tracking`,
`calo-cluster`, `photon-likelihood`, `timing-pid`, `destriper`); the T11 cells give every family below binding `none` except where named.
The scenario text is plan §13's, pinned literally in the harness.

| Scenario | Run time | Backend, or the reason for the gap |
| --- | --- | --- |
| A26 injection before filtering | gap | No backend filters a signal: the destriper solves baselines, its method card says "no filtering or transfer function", and T11 F38 records "signal injection before filtering remain gaps"; F35 (HAYSTAC: SG filter attenuation, synthetic injections) has binding `none` |
| A27 per-setting scan conditions, dwell and merge weights | gap | No scan-setting backend: F35 (RF/IF map per setting) and F36 (retarding potential) have binding `none`; RF and retarding are T06 contract checks, not run time (`t10-closeout.md`, W7 row) |
| A28 per-channel exposure, readout generating signals | executed | `adapters/timing-pid` counts (`timing_recipe/counts.py`, T10 W6): per-channel valid exposure from the read intervals and dead time |
| A29 angle bases, periods, axial-vs-vector conventions | gap | No polarimetry or angle-basis backend: F37 has binding `none`; the destriper timestream has pixel and value only, no polarization angle |
| A30 first CRES segment undetected | gap | No CRES backend: F34 binding `none` |
| A31 averaged or filtered spectra are not raw counts | gap | No backend reads averaged or filtered spectra: F35 (HAYSTAC averaged spectra) binding `none` |
| A32 cuts, cleaning, model or multiplicity changed: no unchecked IRF reuse | executed (fix round 1: E32R) | `adapters/calo-cluster` (T08) and `skills/hep-detector/scripts/build_response.py`: a response built from frozen-configuration products is refused against the variant configuration's product by identity (a harness-side check; see fix round 1, I1). Round 0 wrote "executed, with a remainder" here |
| A33 scintillation insufficient for energy: veto or partial quantities only | gap | No backend measures scintillation against an energy domain: F10 binding `none`; F11 is bound to simreco (`adapters/geant4/assets/simreco/simreco.cc`: TOF station times and β on simulated element_sim events), adjacent, not a cover (no light-yield, quenching or energy model, no energy-domain or veto-only statement; corrected in fix round 1, I2); the photon likelihood (T09) fits one light model and has no veto-only mode; the timing counts (`per_event_energy` false, A19) are counting, not a scintillation veto: adjacent, not a cover |
| A34 null modes in global maps or fits | executed | `adapters/destriper` (T10 replay binding, U7 B2): the common offset named, or fixed by the stated zero-sum constraint |
| A35 same frame name, other projection or focal length: off-axis controls | gap | No imaging backend: F30 and F28 bindings `none` |
| A36 injection into real data: injection location, synthetic components, derived labels | gap | No backend injects into recorded data and none holds real data; the T08 product /3 carries an input label and provenance (`simulated-unvalidated`), a simulation label, not an injection record: adjacent, not a cover |

So P4 execution stays incomplete for A26, A27, A29, A30, A31, A33, A35, A36 (round 0 also listed A32's IRF part; fix round 1, I1, executes it). The record states this, and the harness's
exit 0 means only that every expectation below held, gaps included; it never means P4 is complete.

**Executed cases (all comparisons exact unless a tolerance is named).**
- E28 (A28, timing counts). Channel `ch-a`: threshold 3 mV; intervals [0, 10) s and [10, 20) s, each read, dead 1 s; pulses (1 s, 5 mV),
  (2 s, 1 mV), (12 s, 7 mV). Channel `ch-b`: threshold 3 mV; [0, 10) s read, dead 0.5 s; [10, 20) s not read; pulse (3 s, 4 mV).
  Expectations: the T06 reader accepts the product (no error code); valid exposures 18 s and 9.5 s, run time 20 s; counts `ch-a` 1 and 1,
  `ch-b` 1 and the interval [10, 20) absent with no count; each rate's denominator is its channel's valid exposure. Negatives, each with
  exactly its codes: N28a every rate on the run time (`reconstruction.counts.run_time_denominator`); N28b every rate on 20 s labelled as a
  valid exposure (`reconstruction.counts.exposure_mismatch`); N28c a consistent single run-level exposure (every channel's valid exposure
  and rate set to 20 s): the reader cannot see it, so the harness recomputes each channel's exposure from the native intervals and reports
  both channels. All values are sums of binary-exact numbers, so exact equality is the tolerance.
- E32 (A32, calo-cluster). Two hand-made events on the 40 x 40 grid (closed-form shower images, as `tests/adapters/test_calo_scenarios.py`:
  one shower 2000 MeV at (12.3, 20.1); two showers 2000 MeV at (18.4, 20.2) and 1500 MeV at (21.9, 20.6)), pedestal 0, gain 1. Products made
  by `calo_cluster.py reconstruct` with the frozen configuration (read by SHA-256 `5fbbea3b…`) and with a whole variant file
  (`cell_threshold_mev` 1.2, as T08's A32 test). Expectations: each header names its own configuration SHA-256 and the two differ; the
  frozen-configuration consumer (`t08_scenarios.py accounting`, default configuration) refuses the variant's product with exit 2 and a reason
  naming the configuration, accepts it (exit 0) with the variant file, and accepts the frozen product (exit 0).
- E34 (A34, destriper). Fixture `t10_fixture.py` seed 20260, variants noiseless and disconnected. `destriper.py solve` with
  `--constraint zero-sum --stopping 1e-13`: written; `check-product` exit 0; the constraint statement is named; the map and baselines equal
  the fixture's truth within the frozen noiseless tolerance (`t10-replay-noiseless.tolerance.json`, SHA-256 `12738ebc…`: τ_baselines
  2.5e-11 and τ_map 2.2e-11 of ‖a_truth‖₂, the user's freeze, decisions.md 2026-11-12). With `--constraint none`: written, `check-product`
  exit 0, every one of the 48 parameters listed unidentifiable, no reported item a single parameter, constraint null, no uniqueness claim.
  The disconnected scan is refused (exit 1, two components; one constraint cannot fix two null modes). Negative variants on the zero-sum
  product (`t10_fixture.negative_variant`): `jitter`, `chunk-average`, `unique-without-constraint` each refused with exactly its code.

**A10 inside a T12 reprocessing (T12-21; plan §8.3, A10, R34).** The reprocessing is a recalibration: a new gain payload G1 (1.1,
measured, derived against the pedestal payload) for E32's frozen-configuration product P0, made with G0 (1.0). Its step `trace-rerun`
needs the readout's raw values (`raw`): the cell chain and clustering rerun from the readout. The harness describes P0 by a
reconstruction-product/1 sidecar (`t08_sidecar`) that the T06 reader must accept: `conditions_used` from P0's chain (payload identities
as the chain records them; the T08 payloads carry no tag, so the tag is the harness's label `t08-chain-<step>`, and invalidation compares
identities, R32); retention mapped from P0's header and the files retained beside it:
- `raw`: `reproducible` when the readout whose SHA-256 the header names is retained, otherwise `removed`. The raw values P0 keeps for the
  cells of kept components never make `raw` kept: a trace rerun needs every cell, and removed information is not inferred from summaries
  (§8.3);
- `waveform`: `removed` (calo-cells/1 holds one value per cell, no samples), so a waveform-requiring step is refused in every case;
- `conditions_snapshot`: `reproducible` when both payload files are retained and their identities equal the chain's, otherwise `removed`;
- `truth`: `not-applicable` (a data-side product); `candidates`: `kept` (components, candidates and kept peaks are in P0);
- `lost_recalibrations`: P0's own statement plus "pulse-shape or timing recalibration (no samples in calo-cells/1)".
The planner admits a step only when `contracts.reconstruction.can_recompute(sidecar, level)` is true. Expectations:
- K1 (input retained): `can_recompute` raw true; `trace-rerun` runs and writes a new product P1 whose gain step names G1's identity; P0's
  bytes are unchanged; a rerun under P0's own payloads reproduces P0's bytes exactly (byte reproducibility, §14.1: deterministic fixture).
- K2 (input not retained: raw retention removed): `can_recompute` raw false; `trace-rerun` is refused (`can_recompute: false`, outcome
  "refused: the readout is not retained, so a trace rerun is infeasible"), nothing is written at its target; the higher-level parameters stay
  usable: every object of P0 is read back (energy, position and their uncertainties) with the gain payload it was made with (G0), labelled
  not recalibrated.
- K3 (another readout given, SHA-256 not the header's): raw `removed`, refused as K2.
- K4: a step needing `waveform` is refused even with the input retained.
- K5: the sidecar is accepted by `read_sidecar`; without `lost_recalibrations` it is refused with `reconstruction.retention.loss_unstated`.

**Record and exit codes (core/status.py).** `t12_runtime.py run --out FILE` runs E28, E32, E34 and K1-K5 in a scratch folder and writes
one JSON record: each scenario with its run-time state (`executed` with its items and readings, or `gap` with its reason and the T11
families), the A10 items, `p4_execution: incomplete` with the gap list, synthetic, no quality claim. Status `ok` exit 0: every expectation
above holds; `failed` 1: one does not; `rejected` 2: the output file exists (a record is never overwritten) or its folder is missing;
`incomplete` 3: a backend could not run or the record could not be written.

**Amendment 1 (after green-1, before the job; disclosed, not hidden).** E34's negatives were written as "each refused with exactly its
code". Green-1 refuted that wording, not the behaviour: on the zero-sum product, `jitter` and `unique-without-constraint` remove the
constraint while single parameters stay reported and `uniqueness_claim` stays true, so the reader also raises
`reconstruction.scan.unidentifiable_reported`, `.unidentifiable_unnamed` and `.unique_claim`, which follow from the change itself. T10's
job of record judged these same variants by "the variant's code is among the refusal codes" (`t10_replay.py`, `negatives`). Stage 7 now
uses that rule: each variant's code is among the codes, the unmodified product passes, and the full code lists are kept as readings in
the record. No other expectation changed.

### Stage 7, fix round 1 (review `jobs/t12-stage7/REVIEW.md`, NOT READY 0/2/5/3; written before the changed tests)

Job 7636499 failed only on a frozen test that reads the real `SLURM_JOB_END_TIME` (`test_t04_evaluation_layout`, task deadline under one
hour); that test is not edited, and the redrafted job (`t12-stage7-r1.sh`) asks for 3 h. All findings are adopted.

- **I1 (A32's IRF reuse).** `skills/hep-detector/scripts/build_response.py` can build a response from T08 products: it takes a matched
  truth/reco sample and writes a contract artifact that `contracts/validate.py` accepts. It has no structured field for the product or
  configuration it was made from; its `--provenance` text is carried into `extension.provenance`. So the case is executed, with the pairing
  check on the harness side (like E28's recomputation), and the absence of a structured identity in `build_response.py` is an open item.
  E32R: four hand-made single showers on the 40 x 40 grid, (600, 20.3, 19.8), (1400, 19.6, 20.4), (2200, 20.5, 20.5), (3000, 19.4, 19.6)
  [MeV, cell, cell], pedestal 0, gain 1; products with the frozen configuration and with the variant (`cell_threshold_mev` 1.2). The matched
  sample per event: truth the shower energy, reco the sum of the event's object energies, selected when the event has an object. Response:
  truth and reco edges 0, 1000, 2000, 3000, 4000 MeV, unweighted, `conditional_on_generated`, `inside_matrix`, residual `ratio`,
  `forward_folding`, provenance "T12 stage 7 matched sample from calo-cluster product sha256 P configuration sha256 C". Expectations:
  R1 the frozen response is written (exit 0) and its validation is `contracts_validate: ok`; R2 the pairing check accepts the frozen response
  with the frozen product; R3 it refuses it with the variant's product, naming both configuration identities; R4 a response whose provenance
  names no configuration identity is refused as unbound; readings: the variant's response, and whether its matrix differs from the frozen
  one. Stage 2's R4 (T12-25) showed the response step rerunning when the T08 configuration digest changes, on a synthetic DAG; E32R adds a
  real response artifact and the refusal to reuse it. A32 is `executed`; "A32 IRF reuse" leaves the gap list.
- **I2 (A33).** The reason is corrected as in the table above: F11's energy axis is bound to simreco (β), which is adjacent, not a cover.
- **M1 (A28, readout generating signals).** Two more negatives: N28d a pulse in a channel's unread interval is refused by the recipe
  (`counts.py`: "lies in an interval that was not read"), so no signal is counted where no readout was; N28e an unread interval given a count
  of 0 is refused by the reader (`reconstruction.counts.absent_filled`).
- **M2.** A10's reprocessing is the harness's planner (`plan_step`), not the shared runner: `run_workflow.py` has no retention gate. Open
  item, recorded in the record: "no runner-level retention gate".
- **M3.** `trace-rerun` needs `raw` and `conditions_snapshot`; it is admitted only when `can_recompute` allows both. K6: readout retained,
  pedestal payload not retained: refused ("the conditions snapshot is not retained"), nothing written. K2's decision lists both levels.
- **M4.** The job's scope step keeps stage 2's negative control (an evidence path under the live tree: exit 2) and imports the modules the
  harness loads lazily (`tests.contracts.t12_runtime`, `calo_recipe.product`, `calo_recipe.cell_input`, `timing_recipe.counts`,
  `t10_fixture`, `contracts.reconstruction`) as well as the test module.
- **M5.** The red-1 and green-1 test files were rebuilt exactly (SHA-256 equal to their logs' headers) and kept with their diffs in
  `jobs/t12-stage7/red/`.
- **N1.** N28c: the T06 reader's codes for a consistent single run-level exposure are a reading, not an assertion; the recomputation finding
  both channels is the expectation.
- **N2.** The A32 refusal must name the variant's and the frozen configuration identities in the accounting tool's words ("made with
  configuration V, not the one given (F)"); the zero-sum statement must equal the destriper's text exactly.
- **N3.** E34's item count (11) is listed by name in the test.

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

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
| 4 | Comparators and CPU benchmarks: §14.1, §14.2, A15, quality before speed | Freeze B (K09 gates); T10 for T10's recipe |
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

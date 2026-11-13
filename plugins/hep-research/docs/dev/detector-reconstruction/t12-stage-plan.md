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
- **Q3 (A37 in T12): answered** by the coordinator, 2026-11-13: T12's part needs its own reprocessing run of fixtures 7003 and 7004
  through the T12 loop machinery, because T12-19's acceptance says "inside a T12 reprocessing" and R31 says "reused", not cited. Stage 6
  (T12-19) runs it; T10's reading of the recorded log (`t10_a37.py` `witness_check`) is not T12's evidence.
- **Q4 (the previous-round link): closed** (coordinator, fix round 1, reversing the stage-0 reading). The schema has the fields:
  `derived_against.upstream_payloads` and `derived_from` hold the previous round's payload, and `producer.step_id` the producing step's
  identity (Stage 1, "Synthetic fixture"). No contracts change is needed.
- **Q5 (T10): moot** (coordinator, 2026-11-13): T10 is done (`t10-closeout.md`), so no T12 row waits for T10's part. Stage 6 shares
  T10's A37 fixture form (`t10_a37.py`) without changing it.

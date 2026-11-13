# Detector reconstruction plan v9.2: contract map (K04, draft)

Status: provisional. Built on contracts 3.19.0, compared row by row with the 3.20.0 release on 2026-11-06 (last section; decisions.md, D1). T02 completes it field by field against W1-W7. Names below are proposals, not existing APIs.

Each semantic need takes the first option that works (Section 8.1): existing field, typed native reference, versioned sidecar, schema migration.

## Existing schemas (R09)

| Existing item | What it is at this baseline | Reconstruction need | Decision | Reason |
| --- | --- | --- | --- | --- |
| `recipe.json` | Closed correction chain: `input`, `estimand_kind`, `steps` of operators and effects, `semantics` bound by digest | Method, binding, configuration, converter and checks | **Distinct name** (proposed `reconstruction_recipe`) | Same word, different thing. Its steps are effect-tracking operators, with no port, binding or conditions fields, and it is closed |
| `operator_semantics.json` | Table of quantities (`kind`, `unit`, `meaning`), effects, operators, estimands, scoped to a bounded recipe family | Quantity kinds for typed ports | **Reuse** where a reconstruction output enters a correction chain; **distinct** sidecar for port semantics | `kind`, `unit`, `meaning` cannot hold axis, basis, surface, hypothesis, role or presence (Section 8.2) |
| `qualification_record.json` | Host and plugin qualification with a validity window, issued by a custodian | "Qualification pilot" of a binding (Section 5.10) | **Distinct name** (proposed `binding_evidence`) | It qualifies a deployment, not a method. Sharing the word would suggest a deployment guarantee |
| `decision_record.json` | Analysis decision: actor, time, what was seen, artifacts, supersession | Selection record (Sections 5.13, 8.7) | **Distinct name** (proposed `selection_record`); may point to a `decision_record` for a human decision | Selection needs candidates, conditions, costs and invalidation, and the schema is closed |
| `tool_contract.json` 1.0.0, 1.1.0 | Closed; `entry` must be a `.py` file under the plugin root | Native executables | **Keep unchanged.** A thin Python wrapper where a contract is wanted; otherwise a registered native description in a sidecar | G04. The `entry` pattern refuses a native binary; a wrapper only forwards and reports (Section 8.1) |

## Other existing items

| Existing item | Reconstruction need | Decision | Reason |
| --- | --- | --- | --- |
| `ext_response.json` | Typed instrument response | **Reuse** for matrix and parametrized forms; typed native reference for effective areas, PSFs and transfer operators until T02 shows an extension is needed | Section 11.2: not every response is a migration matrix |
| `run_workflow.py` | Native execution identity | **Reuse** its argv, step and receipt handling; native binaries, libraries and configurations enter as declared inputs | G05: `script_sha256` covers `.py` entries only. T12 stage 2 (drafted, not yet merged): a step's `native_inputs` are hashed afresh before every skip decision (`extension.native_sha256`, receipt `native_inputs`); an undeclared executable in argv disables the skip |
| `ext_computational_run.json` | Run records | **Reuse.** g4sim S2 extended this schema; re-checked at 3.20.0, last section | Overlap found in the parallel-run review |
| `geometry_ir.json`, `detector_spec.json`, `core/geometry` | Nominal geometry identity in payloads (R32) | **Reuse** `geometry_id`; do not define a second identity | D2 |
| Calibration reference, N11 naming | Conditions payload naming | **Reuse** | R01, R32 |

## New sidecars proposed

| Proposed | Holds | Why not an existing field |
| --- | --- | --- |
| Typed port description | Section 8.2 fields | No existing schema holds them |
| Conditions payload | R32 fields | No conditions payload schema exists; no conditions database is built (Section 3.1) |
| `reconstruction_recipe`, `selection_record`, `binding_evidence` | See above | Closed schemas with a different meaning |
| Input signature | Section 5.5 facts with scope and source | New; K15 |

## Rules for readers

- A reader that meets an unknown required extension stops; an unknown optional one may be ignored and is reported (K13).
- Every reader path reads a sidecar one way, `read_document` in `contracts/sidecar_reader.py`: format, extensions, schema and semantic rules. Public functions take whole documents, and a test drives each one with an unknown format and an unknown required extension. A converter and an old tool contract are read by their own schemas, and two digest functions read no meaning.
- `contracts/input_inspector.py` reads files. A JSON document reaches a fact only through `read_document`, or, for an envelope artifact, through `validate_artifact`, and its two public functions have rows in the same test.
- Old recipes, tool contracts and response files keep their meaning and their validators.
- Exception: `ext_response.json` is open, so an old reader does not stop at a new key. `validate.py` warns from contracts 2.8.0 on and exits 0, and `response_adapter.py` drops the key with no message. So no reconstruction semantics go into a response, and a task that writes one calls `check_response_free_of_semantics`.
- New schemas are additive, a minor contracts bump, and the number is assigned at merge time because g4sim also bumps contracts.

## Open for T02

- Whether a sidecar is one schema or several.
- Whether `ext_response.json` needs a new `form` for transfer operators.
- Exact locations under `contracts/`; the plan leaves these to this decision.

## T02: witnesses W1-W7

Definitions only. Fixtures are written and run in T06 (P1), because P0 changes nothing outside this folder (R07). Passing a witness proves the stated contract behaviour, never instrument quality or a backend's correctness (Section 12.1). The stated algebra of W2, W5 and W7 was checked numerically on 2026-11-06.

Field status: **E** expressible now, **X** needs the proposed sidecar, **N** kept as a typed native reference, **I** still inexpressible.

| Witness | Fixture | Must pass | Must be caught | Status of needed fields |
| --- | --- | --- | --- | --- |
| W1 collections, source links, state | Two products with distinct identities, both holding key `0`, plus a reordered subset | Native mapping still reaches the original measurement; surface and state type distinguishable | Dereferencing by row index across products; absent treated as empty; truth role wired to a data-side port | Product identity, object key, revision: **X**. Presence (empty, absent, invalid, not-applicable), role: **X**. Native object: **N** |
| W2 linear pulse | `M=[[1,1],[0,1],[0,1]]`, `d=[5,2,2]`, `R=I`. Solution `[3,2]`, covariance `[[1.5,-0.5],[-0.5,0.5]]` | Analytic solution and covariance reproduced | First sample removed: rank 1, amplitude unidentifiable, no finite precision from jitter. Amplitude-dependent shape: out of domain, GLS not claimed optimal | Sampling, time origin, retention: **X**. Covariance scope (fixed model only): **X**. Identifiability result: **X** |
| W3 frames, halos, IOV | Keys `0..9`, cores `[0,5)` and `[5,10)`, halo 1, conditions change at key 5, one missing sample | One output per key by core ownership; each key uses its own conditions; missing sample stays marked | Halo keys counted twice; first payload used for the whole chunk; complete window claimed at stream end | Ownership and accounts: **X**. Per-key payload binding: **X** (R32). Partition: existing `core/partition` to be checked in T06 |
| W4 shared candidates | H1, H2 share a measurement; H1 goes revision 1 to 2 after reclustering | Sharing allowed; consumers read revision 2 after commit; counting follows the selected hypothesis | Hypothesis deleted early by a unique-use flag; old and new revision both counted; dangling association | Revision scope, selection policy: **X**. Memory ownership: **N** |
| W5 non-unique inversion | `A=[[1,0,1],[0,1,1]]`, `x1=[1,1,0]`, `x2=[0,0,1]`, both give `[1,1]`; null direction `[1,1,-1]` | Both solutions and the null direction retained; any prior stated | Column-normalizing `A` by default; one solution reported as the unique truth | Operator quantity, unit, normalization: **X**; `ext_response.json` does not fit a non-probability operator, so **N** unless T06 shows an extension is needed |
| W6 counts, exposure | `count=0` valid; one absent interval; two channels with different exposure | Zero stays an observation; rates use each channel's valid exposure and response | Absent filled with zero; run time as both denominators; energy assigned with no energy observable; Poisson inferred from integer type | Presence: **X**. Exposure: `exposure_record.json` to be reviewed in T06. Count model: **X** |
| W7 scan, coherent, global | RF: two settings share raw data. Retarding: one setting revisited with different dwell. Global: `y_i=s+b` | Coordinates and overlap kept; setting-time-count kept; only `s+b` reported | Chunk averages; independent Poisson assumed; frequency-time track treated as spatial; unique solution after jitter | Coordinates, overlap, dwell: **X**. Identifiable combinations: **X**. No **I** found, but the three subcases stay separate and replace no native backend |

W1-W7 need no field marked **I** on this reading. T06 must re-check that against 3.20.0 or later: the release comparison below covers the existing schemas, not the witness fields.

### Old-recipe comparison (for T06)

| Old item | Check |
| --- | --- |
| Recipes under `contracts/semantics/recipes/` (for example `flux_from_counts.json`) | Validate unchanged, before and after, with the same result |
| Tool contracts in `contracts/tool_contracts/` (16 files) | Same; a new semantic key sent to an old reader is refused clearly (A41) |
| `ext_response` examples | `response_adapter.py --validate` unchanged |

### Converter responsibilities

A converter is a declared step with its own input and output semantics, version, uncertainty and association handling, and cost (Section 8.4). Any information loss or selection change goes into retention or response, never counted as a harmless format change. None is written in P0.

## Preview of contracts 3.20.0 (superseded by the release comparison below)

Read 2026-11-06 from the g4sim S2 branch at `6903e4ef`, unreleased, so it can still change. Against this baseline, among the files this map depends on, only two changed: `contracts/__init__.py` and `ext_computational_run.json`, which gains an optional `extension.geometry` block. `geometry_id` there is a 64-character hexadecimal string, usable as R32's nominal geometry identity (D2). `recipe`, `operator_semantics`, `qualification_record`, `decision_record`, `tool_contract`, `ext_response`, `run_workflow.py` and the three G01-G03 files are unchanged, so no decision above changes on this reading. The re-baseline (D1) still re-checks this against the release.

## Release comparison, contracts 3.20.0

Task B2 step 1, 2026-11-06, `580dc79e` against `d51566a9`. Every name in the tables above was resolved to its files and diffed.

| Row | Change | Decision |
| --- | --- | --- |
| `ext_computational_run.json` | Adds optional `extension.geometry`, as previewed. Required: `geometry_id`, `request_id`, `run_id`, `build_hash`, `installed_features`; optional `provenance_id`; closed. Identities are 64-character hexadecimal strings | **Reuse** stands |
| `core/geometry` | Not in the preview. `identity.py` gains `in_decimals` and `request_id`; `geometry_id` and `provenance_id` are unchanged. The finish plan reopens K04 for a row like this; it was re-examined | **Reuse** of `geometry_id` stands. The same specification gives the same `geometry_id` on both trees. `request_id` identifies a simulation request and is not a second geometry identity (R32, D2) |
| `contracts/__init__.py` | Version and a comment | None needed |

The other 15 file names are unchanged: `recipe.json`, `operator_semantics.json`, `qualification_record.json`, `decision_record.json`, `tool_contract.json`, `ext_response.json`, `exposure_record.json`, `geometry_ir.json`, `detector_spec.json`, `run_workflow.py`, `response_adapter.py`, `flux_from_counts.json`, `contracts/semantics/recipes/`, `contracts/tool_contracts/` and `core/partition`. The release also adds `contracts/rules/geant4_datasets.json`, which no row uses.

No decision in this map changes. K04 stays provisional as before.

## T06 re-check, contracts 3.20.0

Done with the fixtures. W1-W7 need no field marked **I**. Field statuses above stand, with these answers to the open items.

| Open item | Answer |
| --- | --- |
| One schema or several | Several: `reconstruction_common.json` (shared definitions), `reconstruction_port.json`, `reconstruction_product.json`, `reconstruction_recipe.json`, `conditions_payload.json`, `binding_evidence.json`, `selection_record.json`, `input_signature.json`. Witness semantics are optional blocks of the product schema; each block declares its required extension |
| Locations | `contracts/schemas/` and three library modules, `contracts/sidecar_reader.py`, `contracts/reconstruction.py` and `contracts/conditions.py`. They work on parsed documents, with no command line |
| New `form` in `ext_response.json` | Not needed. The W5 operator stays a typed native reference, described by the `inversion` block; the adapter refuses it as a response |
| `exposure_record.json` (W6) | Not reused: it records who saw which released data. Live exposure is in the `counts` block |
| `core/partition` (W3) | Expresses the cores and refuses gaps and overlaps, with no halo. The `frames` block carries halos, ownership and accounts |
| `contracts/validate.py` | Unchanged. An unreferenced sidecar in an artifacts directory stays an error (`artifacts_dir.not_artifact`) |

Fields added at T06 that the tables above do not name, all **X**:

| Field | Traces to |
| --- | --- |
| `selections`, `selection_ref` (`counts`) | W6: zero/absent, exposure and selection are distinguishable |
| `sideband_sign`, `interval_unit` (`rf-scan` settings) | W7: coordinates must be mapped correctly |
| `constraint.value` (`global`, optional: an exact constraint only, since a prior has no single value) | W7: state the added constraint or prior explicitly |
| `reproducibility` (recipe; null for a proposal) | Section 14.1, sheet G03 |
| `scope.tested_domain`, `checks[].constructible` (`binding_evidence.json`) | Section 8.4, check 6 |
| `inversion.comparator` | Section 14.1, as for W2 |
| `frames.fixed_coordinates` | Section 9.3: predicates on several coordinates |

Owners of what the contract does not hold yet (recorded in decisions.md):

| Item | Proposed owner |
| --- | --- |
| Section 8.5 forms beyond a covariance (mixtures, intervals, samples), learned-estimator ports | T11, when a method needs them |
| Section 10.4 execution fields beyond concurrency, layout, residence and ownership | T12 |
| Section 8.7 hashes of a formal selection record | T15a |
| Section 16.1 method index | T15a |

## T14: the inspector (K15, K17)

| Item | Decision | Reason |
| --- | --- | --- |
| `contracts/input_inspector.py` | Fourth library module: `inspect_inputs`, `judge_candidates` | Section 5.6. It reads files, which `reconstruction.py` does not |
| `input_inspection.json` (`input-inspection/1`) | New sidecar, read through `read_document`, not an artifact type | Section 5.6 item 2 and SEL03 need costs, reading scope and stop reasons; `input_signature.json` is closed and describes one product |
| Probes | `probe.json-document`, `probe.csv-head`; each fixed in `PROBES`, and a record naming anything else is refused. Sizes, chosen here and not physics: JSON 16 MiB whole-document ceiling and 1024 documents per file, CSV 64 KiB window | Section 5.6: fixed parameter combinations; the plan gives no values |
| Budget | Probes, bytes, seconds, memory and tools, all declared by the caller, with no default. Seconds and memory cover the whole inspection and are watched during a probe. A tool is a registered reader | Section 5.6 item 5; plan K17 row. "No default" is a reading, stricter than K10's |
| Limits of that budget | The readers are imported before the budget starts, so that cost is not charged, and a stop waits for the end of any import under the watch. A watch runs between Python calls, so one C call (a blocking read, a JSON parse of plain numbers, one NumPy routine, one regular expression of a validator) runs to its end; the overrun is caught when it returns, the probe's facts are dropped and the record says stopped. Memory is the rise of the process's peak resident size, so an earlier higher peak hides a rise below it. A hard stop would need a separate process | Section 5.6: lightweight read-only probes. A59 is met by the stop reason |
| `family_candidates` | BP IDs from Section 5.15 and the witnesses' Correspondence lines, row by row in `CANDIDATES_BY_CLUE`, each row citing its source | Candidates to check, and no F-ID is formed here. A reading from Sections 5.15, W1-W5 and W7, not an owner's sign-off, to be rechecked before anything depends on it (decisions.md, "T14 rulings") |
| `judge_candidates` | AND/OR over one signature, states as in SEL05; ranks and selects nothing. A conflict on any branch of an OR gives `conflicting`, even if another branch would pass (decisions.md, "T14 rulings") | Section 5.8; A47-A49. T15a builds its index and record on it |
| Conflicts | `state: complete` is refused while a conflict is open. A declaration on a list file reaches each product read from it. A declared waveform on removed traces is a conflict. The caller's label is compared with `product_id` | A46, A48; Section 5.5 |
| Envelope artifacts, such as a `response` | Read through `validate_artifact`, the existing validator. They report `container`, `product_schema` (`artifact-envelope`) and `artifact_type`, with no physics inferred. A refusal keeps no fact. An unknown required capability stops as K13 does | K15, "the plugin's own JSON"; decisions.md, "T14 rulings" |
| A file that parsed with no known schema | Keeps `container: json` and nothing else, with its stop reason. A K13 stop or a known schema refused on its rules keeps nothing | decisions.md, "T14 rulings"; K13 |
| Project of the working directory | `validate_artifact` looks upward from the working directory for a project (`guard_report`). Under a project with `agent_policy` the same artifact can stop on a reason that describes the project, not the input, and those reads are not charged to `bytes`. It fails closed | Existing protected-use behaviour, kept |
| `required_extensions` on an artifact | Refused, at top level or in `extension`. The envelope is open, so its validator would pass the key | K13 |
| Profile terms in an artifact | The validator takes a profile's vocabulary from a project, which the inspector is not given, so such an artifact stays unknown with `vocab.unknown_term` | Fail closed; passing a project in is later work |

## T15a: offline selection (K16, K18)

| Item | Decision | Reason |
| --- | --- | --- |
| `contracts/candidate_selection.py` | Fifth library module: `select_candidate`, `check_selection_replay`. It imports `contracts.reconstruction`, and no reader imports it, so T14's budget list did not grow | Section 5.7; "offline rules before integration with existing runners" (Section 16.1) |
| `candidate_index.json` (`candidate-index/1`) | New sidecar: the finite candidate set, each row bound to one recipe by `recipe_identity`, with `requires`, cost, generation rationale and any composition. Its `methods` rows are the Section 16.1 method index | SEL04. `reconstruction_recipe.json` describes one recipe and is closed |
| `selection_policy.json` (`selection-policy/1`) | New sidecar: target, deliverable, quality contract (an id and the checks evidence must cover), objective, shared overhead, baseline (the declared fallback), sample roles and groups | Sections 5.9, 5.13; fixed before selection, so it has an identity of its own |
| `role` of both | A constant, `artificial-witness`. An index or policy not labelled so is refused. It is a label, so it does not test content | K16's gates are the user's. T15b widens this after K16 and must then gate the witness exception in `_quality` on the role |
| `formal` block of `selection_record.json` | Optional, additive: hashes, signature facts, judgments, restriction, claims. A record without it reads as before and cannot be replayed | Sections 5.13, 8.7. An existing record keeps its meaning (K13) |
| Section 8.7 hashes | Input: the whole inspection, feature costs included. Reader and rule: the source files, so a changed rule cannot keep an old digest, and a changed comment invalidates. Conditions: bound and used payloads. Evidence, policy, candidate set: canonical digests, order-free. Whole recipes, as `recipe_identity` omits runtime evidence | Section 8.7; A60; Section 9.4, conservative side |
| Post-selection evidence, confirmation, global best | `post_selection_evidence` is only null; `policy_confirmed` and `global_best` only false | K18 default; DS3; SEL08. T16 widens the first |
| Costs | Compared at `RELATIVE_TOLERANCE_CEILING`, a constant, so a policy cannot widen its own limit. That value is a stand-in on artificial fixtures, open for K16 (Section 5.9 item 3). Candidate cost plus shared overhead against the cap; feature costs are recorded in `trials`, apart | Sections 5.9 item 5, 5.10, 5.14 |
| Family candidates | Not used. The whole index is the candidate set, and `requires` decides | `CANDIDATES_BY_CLUE` is to be rechecked before anything depends on it (decisions.md, "T14 rulings") |
| Quality | A routine recipe with no required check is `insufficient-evidence`. Each check of the contract needs its own passed, constructible row in the evidence, and a check has one row. A failure is evidence stating `failed` or a `fail` row on a check the recipe or the contract requires; `inconclusive`, `unvalidated`, skipped, not applicable or absent is missing evidence | Section 5.14; Section 8.4 check 6; T06 reading on evidence |
| Baseline | Any routine-eligible baseline is used when no single candidate is supported, in a tie or not | Section 5.9 item 4 as written; coordinator's ruling |
| `needs-evidence`, `abstained` | `abstained` only when every candidate holds a block no information lifts: a failed check, an unsatisfied condition, a limit. A missing backend is open | SEL08; Section 8.7's worked record; coordinator's ruling |
| `judge_candidates`, changed | Conflict outranks unsatisfied at every level. A fact outside the signature's product counts for nothing. Two values of a `constraint.` key in scopes of one product conflict. `product_schema` stays multi-label across a label's files: its conflicts are what `_conflicts` names, two values in one scope or a statement that nothing read matches | decisions.md, "T14 rulings"; Sections 5.5, 5.14 (DS2); K15 |
| Target | `target` and `deliverable` reach the record only: a candidate of another quantity is told apart only by its `requires`. Accepted limit | SEL05 rests on the index author until T15b |

## Release comparison, contracts 3.21.0

2026-11-07, `d51566a9` against `662f58d4`. Rows this release reopens, as the finish plan requires:

| Row | Change | Decision |
| --- | --- | --- |
| `detector_spec.json` | Additions only, 301 lines: S3 shapes, placements, modifiers, segmentation | **Reuse** stands |
| `geometry_ir.json` | Widens: `trd`, `tube`, `polygon_prism`, a `solid` object, rotation entries as decimal strings. The IR's field set does not change | **Reuse** stands |
| `core/geometry`, `contracts/geometry.py` | New expansion, overlap and segmentation code; explicit positions from a hashed CSV. `identity.py` unchanged. `check_spec` gains optional `folder` and `protected` | **Reuse** of `geometry_id` stands: the same value on both trees |
| `contracts/__init__.py` | Version and comments | None needed |

No decision in this map changes. New: `source_density.json`, unused here. K04 stays provisional as before.


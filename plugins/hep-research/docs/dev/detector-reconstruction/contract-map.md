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
| `run_workflow.py` | Native execution identity | **Reuse** its argv, step and receipt handling; native binaries, libraries and configurations enter as declared inputs | G05: `script_sha256` covers `.py` entries only |
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

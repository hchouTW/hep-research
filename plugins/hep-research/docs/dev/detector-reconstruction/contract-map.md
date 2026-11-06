# Detector reconstruction plan v9.2: contract map (K04, draft)

Status: provisional. Built on contracts 3.19.0; must be redone on 3.20.0 or later before T06 (decisions.md, D1). T02 completes it field by field against W1-W7. Names below are proposals, not existing APIs.

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
| `ext_computational_run.json` | Run records | **Reuse.** g4sim S2 extends this schema, so re-check it after re-baselining | Overlap found in the parallel-run review |
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
- Old recipes, tool contracts and response files keep their meaning and their validators.
- New schemas are additive, a minor contracts bump, and the number is assigned at merge time because g4sim also bumps contracts.

## Open for T02

- Whether a sidecar is one schema or several.
- Whether `ext_response.json` needs a new `form` for transfer operators.
- Exact locations under `contracts/`; the plan leaves these to this decision.

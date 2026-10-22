# M2c: design of `run-lineage/v1` (v6.3 analysis-check programme)

Status: design, 2026-10-16. It follows the approved `m2c-proposal.md` and the brief's C9 and D05d. Interfaces were read
from `core/partition/` (campaign, bundle), `adapters/batch-schedulers/batch_campaign.py` (`build_artifact`) and
`contracts/verify_run.py`, without changing them. Labels: **Confirmed**, **Inferred**, **Unresolved**.

## Subject: pre-execution intent, post-execution evidence

- **Selection.** A chain context selects `run-lineage/1.0.0` as a further suite. Its generator reads only the roots,
  so its obligations are frozen in the inventory **before** execution: five per chain root (below).
  - In a pre-execution report each of them is `unverified`, `check.not_executed`.
  - The report says run lineage was not checked.
- **Result binding** (`contracts/schemas/result_binding.json`, a new v6.3 sidecar), written after execution:
  - It is never inside the bundle and names no digest of itself.
  - It binds the analysis bundle digest and the semantic-lock item digest used.
  - It lists the computational-runs (by ref and bytes digest), each with explicit input sources, and the campaigns
    (directory, the adapter's computational-run, the execution bundle digest).
  - Per root it gives the result file (bytes digest), the producer (one named run, or a campaign merge), unit,
    binning, scope and status labels.
- **Running it:** `analysis_check.py check BUNDLE --root DIR --results BINDING [--project DIR]` evaluates the same
  frozen inventory with that evidence. The bundle stays unchanged (V20).
- **Attribution is a declaration (C12).** The binding is agent-written, so `r-run.binding` is declaration-based when
  the binding's `asserted_by` is an agent. It is then unverified in the formal-use view until an accepted review
  lists the report.

## Rules (subject: each chain root)

| Rule | Question | Key outcomes |
| --- | --- | --- |
| `r-run.binding` | Is the result bound to this subject and this root? | **violated:** another analysis bundle (`check.binding_wrong_subject`); a lock digest that is not this bundle's lock (`check.semantic_drift`, V32); a file whose bytes differ (`check.result_digest`); unit, scope or binning not the root's (`check.result_identity`, V20). **unverified:** no binding (`check.not_executed`) or no result for the root (`check.result_unbound`). |
| `r-run.status` | Is the producer a named, successful terminal run or a complete campaign merge, with no failure upstream? | **violated:** a failed run or incomplete merge promoted (`check.failed_promoted`, V54); a failed upstream run (`check.failed_upstream`); a run ID listed twice (`check.producer_ambiguous`, V55); a cycle of product references (`check.run_cycle`, V55). |
| `r-run.closure` | Does every input of every run on the root's lineage map to a frozen item, a frozen external-data manifest entry, or a bound product of an upstream run? | **violated:** a mapped input whose digest differs (`check.closure_mismatch`), or an unmapped input whose bytes match nothing (`check.closure_open`, V33). **unverified:** an unmapped input whose bytes match some source, so an explicit binding is required (`check.closure_unbound`, V55); a JSON input whose bytes differ from the frozen item but whose canonical digest equals it, i.e. a re-serialized derived input (`check.closure_reserialized`, V38). **satisfied:** at the declared level (V53, V56). |
| `r-run.campaign` | For a campaign producer: is it campaign-recorded? | See below (V61, V62, V63). **not_applicable** for a single-run producer. |
| `r-run.blinding` | For a blinded spec: is the cited result a permitted derivative? | **satisfied:** status `asimov` or `synthetic`, or a `path:` or `artifact:` entry of `blinding.allowed_outputs` matches. A match is declaration-based. **violated:** neither (`check.blinded_result_cited`, V70). **unverified:** only an unprefixed entry names it (`check.allowed_output_ambiguous`), or no project was given (`check.blinding_policy_unknown`). **not_applicable:** the spec is not blinded. Reports carry digests and statuses only. |

## Single runs (declared level)

- A run is a computational-run with `extension.input_manifest` and `output_hashes`.
- Its paths resolve against the binding's `base` for that run, relative to the project root.
- Output consistency reuses `contracts.verify_run.verify_run`: a mismatch is `check.closure_mismatch`.
- Retries are told apart by run ID. The binding names the adopted run, never "latest".

## Campaigns (campaign-recorded or declared)

**Inputs (Confirmed by reading the code):**
- the adapter's computational-run: `extension.output_hashes` (`chunks/<cid>.json` bytes digests, and `merged` =
  sha256 of `json.dumps(merged, sort_keys=True)`, a separate digest kind used only as a cross-check),
  `environment.execution.campaign_uid` and `bundles`;
- `state.json`: `collected[cid] = {attempt_id, file, sha256}`, `attempt_records` (attempt → submission),
  `submissions[].status` and `bundle_digest`, `duplicates`;
- `bundles/<digest>.json`, checked with `core.partition.bundle.digest_of` and `check_campaign`.

**Outcomes of `r-run.campaign`:**
- **violated:**
  - the binding's campaign uid is not the campaign's (`check.campaign_mismatch`): a campaign with the same name
    does not pass (V63);
  - a chunk digest in the adapter artifact differs from the `collected` record, or the adopted chunk file differs
    from it (`check.chunk_digest_conflict`, V62, V61);
  - the binding's execution bundle digest differs from the common recorded one (`check.execution_bundle_mismatch`,
    V63);
  - the result file's digest of the adapter's kind differs from the merged hash (`check.merge_mismatch`).
- **unverified, declared level only:**
  - no `collected` record for a merged chunk (`check.campaign_uncollected`);
  - an orphan output, where the submission owning a collected attempt is not `submitted` (`check.campaign_orphan`);
  - a submission owning a collected attempt without a bundle digest, or digests that differ
    (`check.campaign_bundle_unrecorded`);
  - a bundle document whose `digest_of` or `check_campaign` fails (`check.campaign_bundle_invalid`).

  These are V62 and V63.
- **satisfied** (`check.campaign_recorded`): the level is campaign-recorded. Every report that shows this level says
  it is still agent-writable: it guards against mistakes and forged chunk files, not a forged `state.json`.

The checker never re-decides which attempt is valid: the adopted output is the one `collected` names (V61).

## Evidence level and report

- A post-execution report has `phase` `post-execution`, the binding's digest, and `execution_evidence_level` per
  root: `declared` or `campaign-recorded`. `trusted-submitter` is reserved and never shown.
- `result_binding` lists the result digests and the execution bundle digests, for the D10 check:
  - `permit.py check-report` refuses a post-execution report whose cited result digest is not in the permit's
    `artifacts` (`permit.report_result_unlisted`);
  - it also refuses one whose execution bundle differs from the permit's `execution_bundle_sha256`
    (`permit.report_execution_bundle_mismatch`).

  This is the post-execution part of V60. The permit schema does not change.

## Cases (D08 run, all synthetic, temporary folders)

| Case | Content |
| --- | --- |
| RUN-CHAIN | The reduced positive case with `run-lineage` selected. Run A reads the frozen spec and recipe and writes an intermediate product; run B reads it (an explicit product binding) and writes the root's result (V53, V56, V20). |
| RUN-STATUS | A failed run that left output; retries r1 (failed) and r2 (succeeded), with r2 adopted (V54). |
| RUN-LINEAGE | A product cycle, a duplicated run ID, and an input with a frozen item's bytes but no mapping (V55); an unknown input (V33); a re-serialized copy of a frozen JSON item (V38). |
| RUN-CAMPAIGN | `core.partition.campaign` with `LocalExecutor` and an execution bundle frozen in the test (`core.partition.bundle.freeze`). The adapter's `build_artifact` gives the interface record. Variants edit the synthetic records: a missing `collected`, an orphan, a swapped chunk file, null or disagreeing bundle digests, another campaign uid (V61, V62, V63). |
| Blinded | The positive case with a blinded spec: an observed result, a `synthetic` one, and `path:`, `artifact:` and unprefixed `allowed_outputs` entries (V70). Every report and summary is searched for the fixture's numbers. |

The fake-scheduler example has no freeze step, so its submissions carry no bundle digest (**Confirmed**). It is not
changed: the campaign-recorded cases use `LocalExecutor` with a test-side freeze, and the example stays a
declared-level comparison.

## Phase 2, release R2: DR-1 and DR-7 changes (2026-10-23)

The run-lineage fixes in the suites `1.1.0-dev.4` (DR-1 split, DR-7 and DR-9, adopted in `decision-architecture.md`):

- **G8, `r-run.binding` 1.1.0.** The result binding is agent-writable. Its `asserted_by.kind: "person"` no longer
  removes the declaration flag: the attribution is always declaration-based (`result-binding`). Whether a person
  really asserted it is a custody question for the assurance plane (B).
- **A3, check-context 1.1.0.** A satisfied or not-applicable outcome that read a coverage contract the bundle supplied
  (the view's `source: bundle`, agent-writable, not the plugin's) carries the declaration
  `coverage-contract:<table_id>` and is declaration-based; state and reason are unchanged. It is a trust annotation of
  1.1.0 contexts (like the 1.1.0 input checks), applied by the evaluator from the tables a rule read, so no rule's
  code or digest changes. 1.0.0 contexts keep their outcomes (P3).
- **G13, `r-run.blinding` 1.1.0.** Blinding applies when the spec's own flag says so, **or** when the project's
  blinding block lists the spec's `artifact_id` in `blinded` (DR-9). A path or another ID does not match.
- **G7, `r-run.blinding` 1.1.0.** A blinded spec's result is judged by the lineage of the run that produced it
  (DR-7), never by its own status label:

  | Lineage (all runs reached through product sources) | Outcome |
  | --- | --- |
  | every data leaf is a frozen `dataset-record` whose dataset status (`extension.status`, vocabulary `dataset_statuses`, kept apart from envelope labels) is `synthetic` or `simulated` | satisfied, `check.blinding_permitted` |
  | an `allowed_outputs` `path:` or `artifact:` entry names the result | satisfied (a policy declaration), as before |
  | a data leaf with another dataset status (published, preliminary, user-supplied), not allowed | violated, `check.blinded_result_cited`; without a project blinding block, unverified `check.blinding_policy_unknown` |
  | no data leaf | unverified, `check.lineage_no_data`: run records are agent-writable, so leaving the data input out must not pass (P4) |
  | an external-data manifest entry (no dataset status), an unreadable run, an input without a source, a cycle | unverified, `check.lineage_status_unknown` |
  | no run produced the result (a campaign result, or no producer): a label only | unverified, `check.blinding_label_only` |

  A campaign result is judged through the campaign's listed inputs (below); without them it is label-only.
- **G6, `r-run.campaign` 1.1.0 and result binding 1.1.0.** A campaign entry lists `inputs`, which take the same
  `{path, source}` form as a run's. To be campaign-recorded, every listed input must match its source (a frozen
  item, an external manifest entry, or an upstream run's product), and at least one must be an analysis item. A
  digest mismatch is violated (`check.closure_mismatch`). No inputs, an input without a matching source, or no
  analysis item is unverified (`check.campaign_inputs_unbound`, `check.campaign_closure_no_analysis`). These checks
  come after the existing ones (merge, collection, execution bundle), so violations found there still decide first.
  A 1.0.0 binding has no `inputs`, so the 1.1.0 rule gives it `check.campaign_inputs_unbound`. An installed 0.25.1
  refuses a 1.1.0 binding as invalid input (`result_binding.schema.const`, `.additional`, exit 1;
  `refusal-matrix.md`).

Measured on the Phase 0 comparison set:
- **On dev.4:** `g8-person` keeps its flag, and `g13-project-list` is now blinded, permitted by its synthetic lineage.
- **`run-campaign`:** its blinded result is judged through the campaign's inputs. The fixture campaign reads the
  spec, the recipe and a synthetic dataset record, so it stays satisfied, now by lineage.
- **On 1.0.0:** `r-run.binding` and `r-run.blinding` give `check.rule_not_run`.

The run fixtures (`tests/contracts/analysis_check_runs.py`) now freeze a dataset record that run A reads, write
result binding 1.1.0 with the campaign's inputs, and use 1.1.0 contexts.


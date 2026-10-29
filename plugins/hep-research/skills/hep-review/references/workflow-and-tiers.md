# Workflow, tiers and the review CLI

The entry reference of hep-review. Specification: hep-review spec v9 sections 4, 5 and 7 (development copy and run
records in `docs/dev/hep-review/`). Kernel: `contracts/hep_review.py` (pure); I/O: `scripts/hep_review_support/`.

## 1. Lifecycle

| Step | Action | Kept | If a condition is missing |
|---|---|---|---|
| 1 Intent | purpose, minimum requirements, target tier, scope | requirement ids, authority | no trustworthy scope → input-error |
| 2 Scope | materials, dependencies, known gaps; candidate obligations | requirement → obligation map | missing material stays a gap |
| 3 Freeze | snapshot materials; adopt a plan revision | manifest, plan, commit | unmet requirement → not met |
| 4 Assign | packets by owner and shared material | assignment refs, host observations | missing fresh context → that obligation's tier drops |
| 5 Review | reviewer works, writes one drop file | raw bytes, fidelity, attempts, evidence | timeout or tool failure kept, never "no defect" |
| 6 Admit | validator checks structure, bindings, dependencies | committed record | invalid original kept, quarantined |
| 7 Resolve | verification, responses, adjudication | judgment records | never majority or author denial |
| 8 Revise | new material or obligations → new plan revision | obligation_map, closure comparison | no silent downgrade |
| 9 Report | layer 1 projection + layer 2 attestation | as-of report | never fake completeness |
| 10 Close | stop per limits; **hand over the checkpoint** | cost, stop reason, open list | closed is not passed |

A broad review records a scope scan (`not-performed`, `performed-with-gaps`, `performed-no-known-gaps`); only the last
counts as no planning gap. Having read every file is a reading record, not scientific coverage.

## 2. Tiers per obligation

`obligation_tier` is the highest tier whose conditions all hold for that obligation; the report tier is the minimum
over required obligations (optional ones are listed, never lower it). A plan with no required obligation is refused.
Independence affects only the tier, never `plan_requirements_met`.

Reasons a tier drops, as the projection reports them: the plan's independence conditions miss a floor condition; an
assignment's basis is not accepted (self-reported fresh context, unknown non-author); the reviewer is an author of the
obligation's material; the reviewer saw other evaluations (contamination recorded on the assignment); fidelity below
file-transfer; an extra plan condition unmet. R3 additionally needs required restrictions observed as enforced and a
committed claim binding (not reachable on this host).

## 3. Outcomes, flags and the no-defect summary

Outcomes per obligation: `supported`, `violated` (linked to a current supported finding), `undetermined` (work exists,
no conclusion: missing input, pending adoption, substantive conflict), `not-examined`, `not-applicable` (valid
discharge only: `condition-absent`, `out-of-scope-by-intent`, `superseded-by-other-obligation`; never missing data,
difficulty or budget). Method observations: completed / failed / not-run.

Flags: `has_supported_defects` (current supported findings, optional obligations included), `has_disputed_findings`,
`has_open_questions` (candidate or disputed findings, stale negative follow-ups, a required obligation not-examined or
undetermined, a planning gap, a version inconsistency, an unjudged or unresolved conflict, a dependency gap from
quarantine), `plan_requirements_met`. `uncovered_optional` lists optional obligations not covered.

The no-defect sentence needs layer 1 (tier ≥ R1, record integrity valid, requirements met, no defect, no dispute, no
open question) and layer 2 (current mode, latest approved validator, verified head continuity, and for R3 an unchanged
claim). It always reads "<tier qualifier>: no still-valid defect was observed within the scope of this check", followed
by uncovered optional obligations. R0 never gives it.

## 4. The CLI (`scripts/review.py`)

Every command prints JSON with a `status` key; exit 0 ok, 1 negative verdict, 2 bad input, 3 incomplete or missing
dependency. The store defaults to `~/.local/state/hep-research/hep-review` (`--store DIR`); the coordinator's
out-of-store state file (`--state FILE`) keeps the anchor and the digests this session wrote.

| Command | Does |
|---|---|
| `r0 --bundle FILE` | an R0 consultation report from {intent, plan, answers}; no store is created |
| `start --context ID --state FILE [--checkpoint LINE]` | begin a session: anchor on the checkpoint, or record an unanchored start |
| `append --context ID --state FILE --objects FILE --operation-id ID` | commit control objects (intent, manifest, plan) after the admission checks; records come only from `ingest` |
| `snapshot --root DIR --paths P [P ...]` | controlled reading of materials into store blobs; prints manifest entries and coverage gaps |
| `assign --context ID --state FILE --actor NAME --spec-id ID --plan-revision N --via agent-tool --invocation-id ID [--authors-declared]` | build and commit an assignment whose condition bases come from the host profile and the dispatch record |
| `packets --context ID --assignment ID --drop-root DIR --out FILE` | write the packet for an assignment (its obligations, snapshot paths, drop path) |
| `supply --context ID --state FILE --assignment ID --source S --reason R [--contains-evaluation]` | commit material supplied to a reviewer after dispatch (another evaluation makes "no other evaluations seen" unmet) |
| `ingest --context ID --state FILE --assignment ID --drop-root DIR [--digest HEX]` | read the drop file by bytes, derive the record and commit it in one call (the store re-derives it) |
| `report --context ID --state FILE` | layer 1 + layer 2 report, ending with the checkpoint line |
| `checkpoint --context ID` | the checkpoint line to hand to the user |
| `export --context ID --out FILE` / `verify-export FILE [--checkpoint LINE]` / `import FILE --state FILE --into DIR [--checkpoint LINE]` | move a record between sessions or hosts |

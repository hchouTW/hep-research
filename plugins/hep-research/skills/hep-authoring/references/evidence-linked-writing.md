# Evidence-linked writing

Use when a result must be traced into prose, captions and talks, when a claim's support must be checked against the
evidence actually inspected, or when a changed result must be propagated. The record is a `communication` artifact in
the traceability format (`required_capabilities: ["communication:traceability-v1"]`, `traceability_version: "1.0.0"`;
schema `<plugin root>/contracts/schemas/ext_communication_traceability.json`, valid example
`<plugin root>/contracts/fixtures/artifacts/valid/communication_traceability.json`). For the writing itself use
`academic-papers-guide.md`; for literature checks `../../hep-citations/references/citation-verification.md`; for a changed result
`revision-impact-tracking.md`.

## Four statements that stay separate

| Statement | Established by | Never implies |
|---|---|---|
| Schema validity | `<plugin root>/contracts/validate.py` | that a referenced file exists |
| Dependency and source consistency | `check_communication.py --checks traceability` | that anything was read or supports a claim |
| Scientific support | a reader who inspects the evidence and records a verdict with locators | truth: it is the assessor's recorded judgment |
| Output readiness | `check_communication.py --checks manuscript`, rendering, review | that the science is right |

## Build the record

1. Gather the result artifacts (`inputs[]` with `sha256`, `artifact_id`, `version`, `status`) and the literature
   ledgers (`evidence_ledgers[]`, explicit project-relative files with hashes, or `bound: true` for a bound profile).
2. One claim per statement the document makes: stable `id`, exact `text`, `claim_type`, `scope` (regime, assumptions),
   `status` (the sticky caveats of every input it uses; `observed` only with an observed or source edge; never
   `observed` beside `synthetic` or `asimov` on one claim).
3. Evidence edges: `artifact` targets name an `inputs[].ref` and a field locator (`extension.results.ratio`); `source`
   targets name a ledger source id and the passage (`abstract, sentence 2`, `Table 3`). `role` (supports, qualifies,
   contradicts, background) is epistemic; `usage` (`used-in-claim`, default for supports and qualifies; `context-only`
   with a reason) decides whether provenance propagates. Contradictory evidence used to infer a negative claim is used.
4. Read events (`sources_read`): source id, level, locators read, date. A value quoted from an abstract carries the
   abstract locator; a table not read cannot be cited as read.
5. Occurrences: where each claim appears (`document_id`, `locator`, exact `passage`, display `value` with `unit` and
   `rounding` such as `decimals:2`, half up unless `:half-even` is appended), so the manuscript can be checked against the record, not the record against itself.
6. Assessment, after inspecting the evidence: verdict, rationale, the edge ids relied on, assessor, date,
   `claim_digest` (`contracts.communication.claim_digest`) and `evidence_fingerprints` (`evidence_fingerprint`). A
   wording or scope change, or a changed input hash, makes it stale; re-inspect, then re-pin.
7. `reporting_context`: result type, method metadata and field states (`provided`, `missing`, `not-applicable` with a
   reason, `unresolved`) against `<plugin root>/skills/hep-authoring/assets/reporting-policies.json`. A missing field is requested from the producing
   skill, never defaulted. A flux measurement that declares in its method `forward_folding`, `time_dependent`,
   `points_in_bins`, `variable_converted` or `multi_era` must also give the refold kit, the collection-time
   definition, the bin position, the variable conversion or the eras.

## Check it

```
python3 <plugin root>/skills/hep-authoring/scripts/check_communication.py RECORD.json --project-root ROOT --checks manuscript
python3 <plugin root>/skills/hep-authoring/scripts/audit_claims.py RECORD.json --project-root ROOT [--policy POLICY.json]
```

Exit 0 means the requested mechanical checks found nothing wrong; 1 a confirmed inconsistency (a dangling or changed
input, a manuscript sentence that no longer matches its occurrence, a display value outside its declared rounding, a
stale assessment marked current, an unsupported verdict); 3 incomplete (an unresolved source, an unassessed claim, a
cited passage not read, a missing reporting field, a legacy record); 2 bad input. JSON is the stable output; markdown
renders the same report (`--format markdown`, `--out`). Coverage is the declared occurrences only: paraphrases and
conceptual dependencies elsewhere in the manuscript need a targeted read, which the report says it did not do.

The manuscript check compares the recorded passage verbatim with the document source (whitespace normalized, `±` read as
`+/-`): record the passage as it is written in the source, LaTeX markup included. It reads one file per document and
does not follow `\input`/`\include`: a region that includes other files is reported as unresolved, so declare an
included section file as its own document when its passages are checked.

## Write from the record

`audit_claims.py` emits a claim matrix and draft-ready facts (value, unit, uncertainties, status, source locator,
limitations, unresolved inputs). Draft from those facts; keep every status label in the sentence; put a missing number
in a `[VALUE NEEDED: ...]` slot and its request in the claim's `unresolved_inputs`. Wording findings are advisory:
quoted language, negations and another paper's claims are not the author's own assertion.

**Done when:** `check_communication.py --checks manuscript` and `audit_claims.py` exit 0, or their open items are listed for the user.

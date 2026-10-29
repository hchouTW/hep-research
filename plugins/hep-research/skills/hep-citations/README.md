# hep-citations

Source-backed answers, citations and literature records, each from the bound profile's evidence ledger or a primary source with its read level and dates, never from memory.

## Core capabilities

- Answers to what a named experiment published, whether a paper exists, which result is the latest, what a paper states, and whether a result supports a claim.
- Finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv).
- Source and claim ledgers in a project; planned claims to recheck.
- Literature records and literature matrices; literature reviews and systematic screening.
- Owns: answers from cited sources, literature discovery and verification, read levels and verification dates, source and claim ledgers in a project, literature records and matrices; stewardship of `core/evidence` and the `adapters/literature-lookup` adapter.
- Typical artifacts: `literature-record`, literature matrices, inline source-backed answers.

## Triggering conditions

Use when:

- A request asks what a named experiment published, whether a paper exists, which result is the latest, what a paper states, whether a result supports a claim, or for a citation.
- Literature or citations are to be found or verified (INSPIRE-HEP, ADS, arXiv).
- Source and claim ledgers, planned claims to recheck, literature matrices or reviews are needed.

Not for: writing (hep-authoring); results, even from published data (hep-theory, hep-statistics).

| Need | Hand to |
|---|---|
| Related work, a review section or any text built from the sources | hep-authoring |
| Published data for a comparison (HEPData, CRDB import) | hep-theory |
| Compatibility of two published results | hep-statistics |
| Detector facts behind a cited number | hep-detector |
| Measurement design a paper describes | hep-measurement |

## Workspace directory architecture

```text
hep-citations/
├── SKILL.md
├── README.md
├── references/
├── scripts/
│   └── literature_lib/
├── assets/
└── examples/
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | eleven references: the literature guide (routing, rules, latest-result procedure, evidence ledgers, reading workflow, index) routes to the rest (lookup recipes, citation verification, citation databases, primary sources, discovery, reading papers and figures, claim-evidence mapping, review, systematic screening) |
| `scripts/` | three command-line tools (one is `extract_names.py`, the naming extractor for literature record ids) and the skill-local package `literature_lib/` behind `manage_literature.py` |
| `assets/` | reading-notes template and its JSON record, search-log template |
| `examples/` | worked cases: the latest result with its date and query, a draft's citations checked against a record, a ledger that disagrees with a lookup (index in [examples/README.md](examples/README.md)) |

## Input and output specifications

Inputs:

- Request: a question about a source, a result's status, a citation, or a literature task.
- Profiles and context: read only through the context-resolution steps in `SKILL.md`; the bound profile's evidence ledger is read before any lookup. No experiment facts are embedded in the skill.
- Files and artifacts read: profile evidence ledgers, search logs, notices, reading notes.

Outputs:

- Inline answers that name source, query, access date and read level.
- Artifacts written: `literature-record` and literature matrices; durable results go as JSON artifacts into the project's `artifacts_dir`, never inside the plugin.

### Scripts

- `manage_literature.py`: offline import of ledgers, search logs and notices into a `literature-record` artifact written to `--out`, never one of its inputs; flags arXiv version changes, notices, incomplete searches, old verification dates and planned claims past their `recheck_by` date; never a lookup; one JSON report; exit codes input-error 2, fail 1, incomplete 3, pass 0.
- `build_lit_matrix.py`: a literature matrix from reading notes; `--require-provenance` requires an identifier and a read level per paper; prints or writes a Markdown table; exit 0, 1 with `--require-provenance` when a row lacks either, 2 on bad input.
- `extract_names.py`: naming extractor for literature record ids.
- Every script takes `--help`.

Optional lookup adapter (outside this folder, required by nothing here):

- `adapters/literature-lookup` (owned by this skill) runs the INSPIRE-HEP, arXiv and ADS identifier lookups of `references/literature-lookup-recipes.md` and prints a metadata record per source with source URL, UTC retrieval time, read level and an arXiv version check.
- INSPIRE-HEP and arXiv are `tested-in-declared-environment` (E2, live smoke 2026-10-15); ADS is `demonstrated-on-synthetic-data` (no token was available).
- Without the adapter or network a citation stays `not-verified`.

## Setup requirements

- Python 3.13 or newer; the scripts are standard library only.
- Network access only for the optional lookup adapter.
- Environment variables: `ADS_API_TOKEN` (or `ADS_TOKEN`) for ADS lookups by the adapter (without a token no ADS request is made and the ADS result is `not-verified`); `HEP_LIVE_LOOKUP_TEST=1` enables the adapter's live smoke test.

## Operational constraints

- Never supplies a citation, identifier, number or "latest result" from memory.
- Never treats a metadata hit as having read a paper.
- Never presents collaboration-internal information as public.
- Every source records the level at which it was actually read; an answer about the latest result states the verification date and the query used.
- Prose built from the sources is handed to hep-authoring.
- A successful script run is a software check, not scientific validity.
- `SKILL.md` is the authoritative statement of ownership, invariants and workflow; it is the entry point the host loads (its front matter carries the description that routes a request here). This README is for people browsing the folder.

Entry references: `references/literature-guide.md` (its routing table names the minimum inputs, references and completion condition per task), `references/citation-verification.md` for sources, `references/literature-lookup-recipes.md` for lookups, `references/reading-papers.md` for reading.

## Validation

- `tests/skills/hep_citations/` (five test modules: literature lifecycle, planned claims, the literature matrix, the literature-record artifact).
- The contracts tests for the `literature-record` type under `tests/contracts/`.
- The cross-skill link test `tests/skills/test_reference_links.py`.
- The lookup adapter's offline tests `tests/adapters/test_literature_lookup.py` (recorded responses; a live smoke only with `HEP_LIVE_LOOKUP_TEST=1`).
- The behavioral evaluation outside the plugin under `evals/research_communication/` at the repository root (fixture-driven cases with the skill each should load).
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

Request types from `SKILL.md` and the worked examples:

- "Which is the latest FIX result on the ratio?" (`examples/01-latest-result.md`; FIX is an invented collaboration)
- "Does this paper exist, and what is its arXiv id or DOI?"
- "What does this paper state about the measurement?"
- "Does this source support the claim in my draft?"
- "Cite this paper."
- "Check this draft's citations against the literature record before submission." (`examples/02-draft-citations.md`)

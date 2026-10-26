# hep-citations

Use when a request asks what a named experiment published, whether a paper exists, which result is the latest, what a paper states, whether a result supports a claim, or for a citation; also for finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), source and claim ledgers, planned claims to recheck, literature matrices and reviews. It answers from cited sources and the bound profile's evidence ledger, never from memory, and hands the writing to hep-authoring.

**Owns:** answers from cited sources, literature discovery and verification, read levels and verification dates, source and claim ledgers in a project, literature records and matrices; stewardship of `core/evidence` and the `adapters/literature-lookup` adapter. Typical artifacts: `literature-record`, literature matrices, inline source-backed answers.

**Never:** supply a citation, identifier, number or "latest result" from memory; treat a metadata hit as having read a paper; present collaboration-internal information as public.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | eleven references: the literature guide (routing, rules, latest-result procedure, evidence ledgers, reading workflow, index) routes to the rest (lookup recipes, citation verification, citation databases, primary sources, discovery, reading papers and figures, claim-evidence mapping, review, systematic screening) |
| `scripts/` | three command-line tools (one is `extract_names.py`, the naming extractor for literature record ids) and the skill-local package `literature_lib/` behind `manage_literature.py` |
| `assets/` | reading-notes template and its JSON record, search-log template |
| `examples/` | worked cases: the latest result with its date and query, a draft's citations checked against a record, a ledger that disagrees with a lookup |

## Scripts

`manage_literature.py` (offline import of ledgers, search logs and notices into a `literature-record` artifact written to `--out`, never one of its inputs; flags arXiv version changes, notices, incomplete searches, old verification dates and planned claims past their `recheck_by` date; never a lookup; one JSON report, exit codes input-error 2, fail 1, incomplete 3, pass 0); `build_lit_matrix.py` (a literature matrix from reading notes; `--require-provenance` requires an identifier and a read level per paper; prints or writes a Markdown table and exits 0, 1 with `--require-provenance` when a row lacks either, or 2 on bad input).

Optional, outside this folder and required by nothing here: the adapter `adapters/literature-lookup` (owned by this skill) runs the INSPIRE-HEP, arXiv and ADS identifier lookups of `references/literature-lookup-recipes.md` and prints a metadata record per source with source URL, UTC retrieval time, read level and an arXiv version check. INSPIRE-HEP and arXiv are `tested-in-declared-environment` (E2, live smoke 2026-10-15); ADS is `demonstrated-on-synthetic-data` (no token was available); without the adapter or network a citation stays `not-verified`.

## References

`references/literature-guide.md` (its routing table names the minimum inputs, references and completion condition per task), `references/citation-verification.md` for sources, `references/literature-lookup-recipes.md` for lookups, `references/reading-papers.md` for reading.

## Handoffs

| Need | Hand to |
|---|---|
| Related work, a review section or any text built from the sources | hep-authoring |
| Published data for a comparison (HEPData, CRDB import) | hep-theory |
| Compatibility of two published results | hep-statistics |
| Detector facts behind a cited number | hep-detector |
| Measurement design a paper describes | hep-measurement |

## Tests and validation

`tests/skills/hep_citations/` (literature lifecycle, planned claims, the literature matrix, the literature-record artifact), the contracts tests for the `literature-record` type under `tests/contracts/`, the cross-skill link test `tests/skills/test_reference_links.py`, the lookup adapter's offline tests `tests/adapters/test_literature_lookup.py` (recorded responses; a live smoke only with `HEP_LIVE_LOOKUP_TEST=1`), and the behavioral evaluation outside the plugin under `evals/research_communication/` at the repository root (fixture-driven cases with the skill each should load). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here). This README is for people browsing the folder. The skill reads the project's profiles only through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard library only; a successful run is a software check, not scientific validity.

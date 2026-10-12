# research-communication

Use when the deliverable is scientific communication or literature work in physics: finding and verifying literature and citations, literature matrices and reviews, checking whether a source supports a claim, drafting or revising paper sections, abstracts and captions, figures and tables, diagrams as editable sources, talks and posters, referee reports, theses, proposals, handover notes, and packaging results with claim-to-result links and honest status. It answers questions about what a named experiment published from the evidence ledger, not memory.

**Owns:** literature discovery and verification workflow, writing, diagrams and their rendering, talks, referee replies, handover, packaging; stewardship of `core/evidence`. Typical artifacts: `communication` (claims linked to results and sources, read levels, figure inputs, limitations; the traceability format adds evidence edges, occurrences and assessments), literature matrices, manuscripts, figures with captions.

**Never:** invent a result, a number or a citation; upgrade a derivation or result status; describe synthetic or Asimov results as measurements.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | fifty-three references: the papers guide and the diagrams guide route to the rest (reading, writing, citations, claims and evidence, revisions, reviews, venues, figures, diagrams per field, outreach, theses, proposals) |
| `scripts/` | nine command-line tools and the skill-local package `communication_lib/` behind six of them |
| `assets/` | `paper/` (LaTeX skeleton, BibTeX, reading notes, methodology manual, adaptation manifest, audience templates, glossary and search-log templates), `diagrams/` (editable skeletons), `reporting-policies.json` |
| `examples/` | worked diagram examples by field and the evidence-linked writing example (`evidence-linked/`, with byte-stable committed reports) |

## Scripts

`build_lit_matrix.py` (a literature matrix from reading notes); `check_manuscript.py` (citations, labels, references and markers of a LaTeX manuscript; `--main` scans one document through its literal includes); `check_diagram_sources.py` (per-block render outcomes of the shipped diagram sources); and, for evidence-linked writing on a traceability record, `check_communication.py` (record, inputs, sources, manuscript occurrences), `audit_claims.py` (recorded assessments, read coverage, wording, numbers, reporting completeness; claim matrix and draft facts), `track_revision_impact.py` (baseline against revised record), `manage_literature.py` (offline import of ledgers, search logs and notices; never a lookup), `check_adaptation.py` (derived drafts against their manifest; referee replies from the action state) and `check_terminology.py` (glossary-scoped terminology and notation, English and Traditional Chinese). All are read-only, print one JSON report (markdown is a view) and use the exit precedence input-error 2, fail 1, incomplete 3, pass 0.

## References

`references/academic-papers-guide.md` (its routing table names the minimum inputs, references and completion condition per task), `references/academic-diagrams-guide.md`, `references/evidence-linked-writing.md` for the traceability record and the three checks that go with it, `references/citation-verification.md` for sources, `references/revision-impact-tracking.md` for a changed result.

## Handoffs

| Need | Hand to |
|---|---|
| A missing or unclear result | the producing skill |
| Physics correctness of a diagram or equation | hep-theory |
| Statistical wording of a claim | hep-statistics |
| Measurement design or selection behind a claim | hep-analysis |
| Detector performance numbers | detector-response |
| Code or scripts behind a figure or table | hep-computing |

## Tests and validation

`tests/skills/research_communication/` (fourteen modules, including the golden evidence-linked scenario), the contracts tests for the communication format under `tests/contracts/`, and the behavioral evaluation outside the plugin under `evals/research_communication/` (fixture-driven cases, a replay scorer with self-tests, and one recorded live run). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.

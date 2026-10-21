# hep-authoring

Use when the deliverable is physics writing or its presentation: drafting or revising paper sections, abstracts and captions, papers from results (short summaries, terminology, numbers and units; English or Chinese), figures and tables, diagrams as editable sources, talks and posters, referee reports, theses, proposals, handover notes, and packaging results with claim-to-result links and honest status. Every citation comes from a hep-citations record or a profile evidence ledger, never from memory; what a paper states, the latest result and citations themselves are hep-citations's.

**Owns:** writing, diagrams and their rendering, talks, referee replies, handover, packaging; the `communication` extension and the shared audit report shape (`contracts/audit_report.py`, also used by hep-citations). Typical artifacts: `communication` (claims linked to results and sources, read levels, figure inputs, limitations; the traceability format adds evidence edges, occurrences and assessments), manuscripts, figures with captions.

**Never:** invent a result, a number or a citation; cite from memory; upgrade a derivation or result status; describe synthetic or Asimov results as measurements.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | forty-nine references: the papers guide and the diagrams guide route to the rest (writing, bibliography and citation style, evidence-linked writing, revisions, reviews, venues, figures, diagrams per field, outreach, theses, proposals); reading and sources are hep-citations's |
| `scripts/` | eleven command-line tools, the skill-local package `communication_lib/` behind six of them, and `review_lib/` behind `review.py` |
| `assets/` | `paper/` (LaTeX skeleton, a Chinese thesis skeleton for XeLaTeX, BibTeX, methodology manual, adaptation manifest, audience templates, glossary template), `diagrams/` (editable skeletons), `reporting-policies.json`, `paper-blueprints.json`, `review-lenses.json` and `review-hosts.json` (independent review) |
| `examples/` | worked diagram examples by field and the evidence-linked writing example (`evidence-linked/`, with byte-stable committed reports) |

## Scripts

`check_citations.py` (each citation of a LaTeX, BibTeX or Markdown draft against hep-citations records and profile evidence ledgers: found with its read level, or `not-verified` when no record or ledger has it; one JSON report; exit 0 all found, 3 a citation not verified, 2 bad input; never a lookup); `render_results.py` (LaTeX macros and result tables from statistical-results and dataset-records with the artifact id and sha256, PDG rounding, watermark macros a final build refuses, one-bin dataset-records for HEPData); `check_manuscript.py` (citations, labels, references and markers of a LaTeX manuscript; `--numbers` fails when one quantity differs between abstract, body, tables and conclusions; `--blueprint search|precision-measurement|instrumentation|letter` lists the content a paper type usually needs from `assets/paper-blueprints.json`, advisory, exit code unchanged; `--main` scans one document through its literal includes); `spectrum_plot.py` (a spectrum from dataset-records only: a stated bin position such as Lafferty-Wyatt, E^gamma weighting, conversion through `spectrum_transform.py`, status labels in legend and caption, overlays never presented as a combination; a JSON sidecar traces every point to its record; exit 3 without matplotlib); `check_diagram_sources.py` (per-block render outcomes of the shipped diagram sources, or of a user's `.dot`, `.mmd`, `.puml`, `.svg` or `.tex` file read by its extension); and, for evidence-linked writing on a traceability record, `check_communication.py` (record, inputs, sources, manuscript occurrences), `audit_claims.py` (recorded assessments, read coverage, wording, numbers, reporting completeness; refuses a planned claim as support for a measured result; claim matrix and draft facts), `track_revision_impact.py` (baseline against revised record), `check_adaptation.py` (derived drafts against their manifest; referee replies from the action state) and `check_terminology.py` (glossary-scoped terminology and notation, English and Traditional Chinese; the glossary template separates collection time, exposure and data exposure, and rigidity and momentum). The evidence-linked tools (`check_communication.py`, `audit_claims.py`, `track_revision_impact.py`, `check_adaptation.py`, `check_terminology.py`) are read-only, print one JSON report (markdown is a view) and use the exit precedence input-error 2, fail 1, incomplete 3, pass 0. `check_citations.py` uses the same report shape and codes. `check_manuscript.py` and `check_diagram_sources.py` print text by default and one JSON report with `--format json`, with the same exit codes.

`review.py` drives an independent review of one Markdown draft by agents that did not write it (`references/independent-review.md`; design in `docs/dev/independent-review-spec.md`): `start`, then `next` until `stop`; it builds review packets with controls, validates review records on receipt, handles findings, arbitration, re-review and escalation, and writes `report.md`; `contracts/review.py check` verifies the review directory. It dispatches no agent. A closed review is not a non-author review record in the sense of the v6.3 open conditions.

Literature records (`manage_literature.py`), the literature matrix (`build_lit_matrix.py`) and the optional lookup adapter `adapters/literature-lookup` are hep-citations's.

## References

`references/academic-papers-guide.md` (its routing table names the minimum inputs, references and completion condition per task), `references/academic-diagrams-guide.md`, `references/evidence-linked-writing.md` for the traceability record and the three checks that go with it, hep-citations's `references/literature-guide.md` for sources, `references/revision-impact-tracking.md` for a changed result, `references/independent-review.md` for an independent review of a draft.

## Handoffs

| Need | Hand to |
|---|---|
| Citations, claim checks against sources, related-work sources | hep-citations |
| A missing or unclear result | the producing skill |
| Physics correctness of a diagram or equation | hep-theory |
| Statistical wording of a claim | hep-statistics |
| Measurement design or selection behind a claim | hep-measurement |
| Detector performance numbers | hep-detector |
| Code or scripts behind a figure or table | hep-computing |

## Tests and validation

`tests/skills/hep_authoring/` (the communication audits, manuscripts, diagrams, the citation check, the golden evidence-linked scenario), the cross-skill link test `tests/skills/test_reference_links.py`, the contracts tests for the communication format under `tests/contracts/`, and the behavioral evaluation outside the plugin under `evals/research_communication/` at the repository root (the folder keeps the former skill name and records which of hep-citations and hep-authoring each case should load; fixture-driven cases, a replay scorer with self-tests, and two recorded live runs, 2026-10-13 and 2026-10-15). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.

# hep-authoring

Physics writing and its presentation (papers, figures, diagrams, talks, referee replies, handover notes and packaged results), with every quantitative claim linked to a result artifact or a recorded source.

## Core capabilities

- Drafting and revising paper sections, abstracts and captions; papers from results (short summaries, terminology, numbers and units; English or Chinese); theses, proposals and handover notes.
- Figures and tables; spectra from dataset-records; diagrams as editable sources (`.dot`, `.mmd`, `.puml`, `.svg`, `.tex`) and their rendering.
- Talks and posters; referee reports and replies.
- Packaging results with claim-to-result links and honest status.
- Evidence-linked writing on a traceability record: claims, inputs, sources, manuscript occurrences, assessments, revision impact, audience adaptation and terminology.
- Independent review of one Markdown draft by agents that did not write it (`review.py`).
- Owns: writing, diagrams and their rendering, talks, referee replies, handover, packaging; the `communication` extension and the shared audit report shape (`contracts/audit_report.py`, also used by hep-citations).
- Typical artifacts: `communication` (claims linked to results and sources, read levels, figure inputs, limitations; the traceability format adds evidence edges, occurrences and assessments), manuscripts, figures with captions.

## Triggering conditions

Use when:

- The deliverable is physics writing or its presentation, even one sentence for an abstract or summary.
- A draft, caption, figure, table, diagram, talk, poster, referee report, thesis, proposal or handover note is to be written, revised or checked.
- Results are to be packaged with claim-to-result links and their status.
- A draft needs an independent review by agents that did not write it.

Not for: what a paper states, the latest result, or citations themselves (hep-citations); producing results (hep-measurement, hep-detector, hep-theory, hep-statistics, hep-computing, hep-ml).

| Need | Hand to |
|---|---|
| Citations, claim checks against sources, related-work sources | hep-citations |
| A missing or unclear result | the producing skill |
| Physics correctness of a diagram or equation | hep-theory |
| Statistical wording of a claim | hep-statistics |
| Measurement design or selection behind a claim | hep-measurement |
| Detector performance numbers | hep-detector |
| Code or scripts behind a figure or table | hep-computing |

## Workspace directory architecture

```text
hep-authoring/
├── SKILL.md
├── README.md
├── references/
├── scripts/
│   ├── communication_lib/
│   └── review_lib/
├── assets/
│   ├── paper/
│   ├── diagrams/
│   ├── paper-blueprints.json
│   ├── reporting-policies.json
│   ├── review-hosts.json
│   └── review-lenses.json
└── examples/
    ├── general/
    ├── hep/
    ├── statistics/
    ├── computer-science/
    ├── evidence-linked/
    └── prose/
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | forty-nine references: the papers guide and the diagrams guide route to the rest (writing, bibliography and citation style, evidence-linked writing, revisions, reviews, venues, figures, diagrams per field, outreach, theses, proposals); reading and sources are hep-citations's |
| `scripts/` | twelve command-line tools (among them `extract_names.py`, the naming extractor for LaTeX names and BibTeX keys), the skill-local package `communication_lib/` behind six of them, and `review_lib/` behind `review.py` |
| `assets/` | `paper/` (LaTeX skeleton, a Chinese thesis skeleton for XeLaTeX, BibTeX, methodology manual, adaptation manifest, audience templates, glossary template), `diagrams/` (editable skeletons), `reporting-policies.json`, `paper-blueprints.json`, `review-lenses.json` and `review-hosts.json` (independent review) |
| `examples/` | worked diagram examples by field (`general/`, `hep/`, `statistics/`, `computer-science/`), the evidence-linked writing example (`evidence-linked/`, with byte-stable committed reports) and three weak-versus-better prose examples in `prose/` (a results paragraph, a review synthesis, a review talk; index in [examples/prose/README.md](examples/prose/README.md)) |

## Input and output specifications

Inputs:

- Request: the text, figure, diagram, talk or review to produce or check.
- Profiles and context: read only through the context-resolution steps in `SKILL.md`; no experiment facts are embedded in the skill.
- Files and artifacts read: result artifacts (`statistical-result`, dataset-records), hep-citations `literature-record` artifacts and profile evidence ledgers, LaTeX, BibTeX or Markdown drafts, diagram sources, traceability records, adaptation manifests and glossaries.

Outputs:

- Artifacts written: `communication` records, manuscripts, figures with captions, LaTeX macros and result tables, diagram sources, review reports; durable results go as JSON artifacts into the project's `artifacts_dir`, never inside the plugin.
- Literature records (`manage_literature.py`), the literature matrix (`build_lit_matrix.py`) and the optional lookup adapter `adapters/literature-lookup` are hep-citations's.

### Scripts

- `check_citations.py`: each citation of a LaTeX, BibTeX or Markdown draft against hep-citations records and profile evidence ledgers: found with its read level, or `not-verified` when no record or ledger has it; one JSON report; exit 0 all found, 3 a citation not verified, 2 bad input; never a lookup.
- `render_results.py`: LaTeX macros and result tables from statistical-results and dataset-records with the artifact id and sha256, PDG rounding, watermark macros a final build refuses, one-bin dataset-records for HEPData.
- `check_manuscript.py`: citations, labels, references and markers of a LaTeX manuscript; `--numbers` fails when one quantity differs between abstract, body, tables and conclusions; `--blueprint search|precision-measurement|instrumentation|letter` lists the content a paper type usually needs from `assets/paper-blueprints.json` (advisory, exit code unchanged); `--main` scans one document through its literal includes.
- `spectrum_plot.py`: a spectrum from dataset-records only: a stated bin position such as Lafferty-Wyatt, E^gamma weighting, conversion through `spectrum_transform.py`, status labels in legend and caption, overlays never presented as a combination; a JSON sidecar traces every point to its record; exit 3 without matplotlib.
- `check_diagram_sources.py`: per-block render outcomes of the shipped diagram sources, or of a user's `.dot`, `.mmd`, `.puml`, `.svg` or `.tex` file read by its extension.
- Evidence-linked writing on a traceability record:
  - `check_communication.py`: record, inputs, sources, manuscript occurrences.
  - `audit_claims.py`: recorded assessments, read coverage, wording, numbers, reporting completeness; refuses a planned claim as support for a measured result; claim matrix and draft facts.
  - `track_revision_impact.py`: baseline against revised record.
  - `check_adaptation.py`: derived drafts against their manifest; referee replies from the action state.
  - `check_terminology.py`: glossary-scoped terminology and notation, English and Traditional Chinese; the glossary template separates collection time, exposure and data exposure, and rigidity and momentum.
- `extract_names.py`: naming extractor for LaTeX names and BibTeX keys.
- `review.py`: drives an independent review of one Markdown draft (`references/independent-review.md`; design in `docs/dev/independent-review-spec.md`): `start`, then `next` until `stop`; builds review packets with controls, validates review records on receipt, handles findings, arbitration, re-review and escalation, and writes the review report (report.md); `contracts/review.py check` verifies the review directory. It dispatches no agent. Optional settings (contracts 3.4.0, 3.6.0):
  - `start --lens-model LENS=MODEL` fixes a lens slot's model.
  - `start --filter-model M` adds one filtering pass over the round-1 findings, whose drops the report lists apart (with the reviewers' identities removed from the findings' text).
  - `start --expert-model M` adds an expert slot to round 1 that reads the whole document for substantive errors (being evaluated).
  - `start --own-config` gives a review its own configuration file so concurrent reviews can differ.

CLI contract:

- The evidence-linked tools (`check_communication.py`, `audit_claims.py`, `track_revision_impact.py`, `check_adaptation.py`, `check_terminology.py`) are read-only and print one JSON report (markdown is a view).
- Exit precedence: input-error 2, fail 1, incomplete 3, pass 0. `check_citations.py` uses the same report shape and codes.
- `check_manuscript.py` and `check_diagram_sources.py` print text by default and one JSON report with `--format json`, with the same exit codes.
- Every script takes `--help`.

## Setup requirements

- Python 3.13 or newer; scripts are standard library first.
- matplotlib for `spectrum_plot.py` (exit 3 without it).
- `check_diagram_sources.py` renders with the tools it finds: `dot` (Graphviz), `mmdc` (Mermaid CLI), `plantuml`, and LuaLaTeX or pdfLaTeX for TikZ; without a renderer a block is reported as lint-only or skipped, never as rendered. `--no-mermaid` never starts `mmdc`, which launches a headless browser.
- Environment variable `HEP_RENDER_TIMEOUT`: seconds per diagram and renderer before an environment error (default 60).

## Operational constraints

- Never invents a result, a number or a citation; never cites from memory; never upgrades a derivation or result status; never describes synthetic or Asimov results as measurements.
- Every citation comes from a hep-citations record or a profile evidence ledger; without one it is handed to hep-citations or marked unverified. What a paper states, the latest result and citations themselves are hep-citations's.
- Status survives writing: preliminary, synthetic, Asimov, failed, unvalidated and user-supplied results say so in text and captions.
- Physics correctness of a diagram is hep-theory's; rendering and captions are this skill's.
- A closed review from `review.py` is not a non-author review record in the sense of the v6.3 open conditions (maintainer decision); it is advisory input a human reviewer may cite.
- A successful script run is a software check, not scientific validity.
- `SKILL.md` is the authoritative statement of ownership, invariants and workflow; it is the entry point the host loads (its front matter carries the description that routes a request here; it stays under 8 KiB). This README is for people browsing the folder.

Entry references: `references/academic-papers-guide.md` (its routing table names the minimum inputs, references and completion condition per task), `references/academic-diagrams-guide.md`, `references/evidence-linked-writing.md` for the traceability record and the three checks that go with it, hep-citations's `references/literature-guide.md` for sources, `references/revision-impact-tracking.md` for a changed result, `references/independent-review.md` for an independent review of a draft.

## Validation

- `tests/skills/hep_authoring/` (thirty-two test modules: the communication audits, manuscripts, diagrams, the citation check, the golden evidence-linked scenario).
- The cross-skill link test `tests/skills/test_reference_links.py`.
- The contracts tests for the communication format under `tests/contracts/`.
- The behavioral evaluation outside the plugin under `evals/research_communication/` at the repository root (the folder keeps the former skill name and records which of hep-citations and hep-authoring each case should load; fixture-driven cases, a replay scorer with self-tests, and two recorded live runs, 2026-10-13 and 2026-10-15).
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

Request types from `SKILL.md` and the worked examples:

- "Write the results paragraph for this preliminary spectral break from its result record." (`examples/prose/`)
- "Check that every citation in this draft comes from a literature record."
- "Make the LaTeX macros and the result table from these statistical-result artifacts."
- "Draw the analysis workflow as an editable diagram source and check that it renders."
- "Draft the referee reply: completed changes with their locator, pending ones in planned voice."
- "Condense this paper into a Chinese summary with the same numbers, claim strength and status."
- "Run an independent review of this draft by agents that did not write it."

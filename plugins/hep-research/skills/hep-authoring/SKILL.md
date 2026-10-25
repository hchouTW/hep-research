---
name: hep-authoring
description: "Use when the deliverable is physics writing or its presentation, even one sentence for an abstract or summary; load it first: drafting or revising paper sections, abstracts and captions, papers from results (short summaries, terminology, numbers and units; English or Chinese), figures and tables, diagrams as editable sources, talks and posters, referee reports, theses, proposals, handover notes, packaging results with claim-to-result links, and independent review of a draft by agents that did not write it. Never cites from memory. Not for: what a paper states, the latest result, citations (hep-citations); producing results (hep-measurement, hep-detector, hep-theory, hep-statistics, hep-computing, hep-ml)."
---

# hep-authoring: papers, figures, diagrams, talks

**Owns:** writing and revising papers, theses, proposals and handover notes; related-work and review sections; figures, tables, diagrams and their rendering; talks and posters; referee reports and replies; packaging results with claim-to-result links; the `communication` extension and the shared audit report shape (`contracts/audit_report.py`); independent review of a draft by agents that did not write it (review packets, review records and the review log; `contracts/review.py`).
**Typical artifacts:** `communication` (claims linked to results, sources with their read levels, figure inputs, limitations), manuscripts, figures with captions, diagram sources.
**Never:** invent a result, a number or a citation; cite from memory; answer whether citations are verified yourself (load hep-citations, even mid-draft); upgrade a derivation or result status; describe synthetic or Asimov results as measurements.

## Invariants

- Every quantitative claim links to a result artifact or a source; each source carries the read level its literature record or ledger gives.
- Every citation comes from a hep-citations `literature-record` or a profile evidence ledger, never from memory. Without a record, hand the citation to hep-citations first, or mark it in the text as unverified (`[CITATION NEEDED: ...]`); `check_citations.py` lists each citation it cannot find as `not-verified`.
- Status survives writing: preliminary, synthetic, Asimov, failed, unvalidated and user-supplied results say so in text and captions; a perturbative or numerical result is not called a proof.
- Physics correctness of a diagram (for example a Feynman diagram) is hep-theory's; rendering and captions are this skill's.
- Collaboration-internal information is never presented as public, and nothing implies endorsement by any collaboration or institution.

## Workflow

1. Resolve context (stanza below); read evidence records only for the claims being written.
2. Gather the result artifacts the text will cite; list each claim with its artifact or source.
3. List every citation the text needs; hand those without a literature record or ledger entry to hep-citations before drafting, or mark them unverified.
4. Draft; mark limitations and statuses where they apply; run `check_citations.py` on the draft.
5. Write the `communication` artifact for durable deliverables and validate it.
6. Depth follows the request: **standard** (a durable deliverable with its `communication` record) or **audit** (the traceability record checked with the scripts below). A question about what a paper states, the latest result, a citation alone, or whether a draft's citations are verified is hep-citations's: load it.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; if present, run `python3 "<plugin root>/contracts/project.py" <project-dir> --preflight` and read the indexes it prints. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; `--preflight` checks them. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default ./hep-research-artifacts/), never the plugin, and pass `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`; no scratch. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it, except a Geant4 study record that passes the 3.1.0 upgrade rule.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English. Name what you add or change for what it holds, in the project's terms, per `<plugin root>/skills/hep-computing/references/semantic-naming.md`; never rename an external (C4) name.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Writing, revising, reviewing papers | [papers guide](references/academic-papers-guide.md) |
| Paper structure and genres (search, measurement, instrumentation, letter content lists) | [paper structure](references/paper-structure.md), [genre variants](references/paper-genre-variants.md); `check_manuscript.py --blueprint` |
| Citations in a draft: each from a record or ledger | `check_citations.py` lists those without one; whether they are verified, sources and lookups: load hep-citations |
| Bibliography hygiene and citation style | [bibliography](references/citations-and-bibliography.md) |
| Claims linked to results; numbers from artifacts (macros, tables, PDG rounding, version compare) | [linked writing](references/evidence-linked-writing.md); `audit_claims.py`, `render_results.py` |
| Figures, tables, physics plots; spectra from dataset-records (E^gamma, bin position, overlays) | [figures](references/figures-and-tables.md), [physics plots](references/physics-plots.md); `spectrum_plot.py` |
| Diagrams as editable sources (.dot, .mmd, .puml, .tex) | [diagrams guide](references/academic-diagrams-guide.md); `check_diagram_sources.py` |
| LaTeX checks and venues; Chinese typesetting, a thesis | [LaTeX venues](references/latex-venue-setup.md); `check_manuscript.py`; `assets/paper/thesis-skeleton-zh.tex` |
| Talks and posters | [talks](references/poster-and-talk-design.md) |
| Referee reports and replies | [reviewing](references/reviewer-style-assessment.md), [comment exchange](references/comment-and-reply-exchange.md) |
| Audience adaptation, terminology (exposure vs collection time, rigidity vs momentum) | [outreach](references/outreach-and-public-facing-summaries.md); `check_adaptation.py`, `check_terminology.py` with `assets/paper/glossary-template.json` |
| Revisions after a changed result | `track_revision_impact.py`; [revision tracking](references/revision-impact-tracking.md) |
| Independent review of a draft by agents that did not write it: review packets, records, the review log and its check | [independent review](references/independent-review.md); `review.py` |
| Statistics and astroparticle papers | [statistics and ML papers](references/statistics-and-ml-papers.md), [astroparticle papers](references/astroparticle-and-cosmic-ray-papers.md) |

Scripts in `<plugin root>/skills/hep-authoring/scripts/` (read `--help` first; what each checks: [README.md](README.md#scripts)). Field-specific patterns, venues and reviews have their own files under `references/`; diagram skeletons in `assets/diagrams/`, paper templates in `assets/paper/`, worked diagrams in `examples/`. Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Citations, claim checks against sources, related-work sources | hep-citations | citation list in `unresolved_inputs` |
| A missing or unclear result | the producing skill | request in `unresolved_inputs` |
| Physics correctness of a diagram or equation | hep-theory | `theory-spec` |
| Statistical wording of a claim | hep-statistics | `statistical-result` |
| Measurement design or selection behind a claim | hep-measurement | request in `unresolved_inputs` |
| Detector performance numbers | hep-detector | `response` |
| Code or scripts behind a figure or table | hep-computing | `computational-run` |

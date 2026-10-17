---
name: hep-communication
description: "Use when a request asks what a named experiment published, whether a paper exists, which result is the latest, what a paper states, whether a result supports a claim or interpretation, or for a citation: load it first even for a quick question, since it answers from cited sources, not memory; if a comparison names no observable or experiments, ask first. Also for physics writing and literature work: papers from results (short summaries, terminology, numbers and units; English or Chinese), finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), literature matrices and reviews, drafting or revising paper sections, abstracts and captions, figures and tables, diagrams as editable sources, talks and posters, referee reports, theses, proposals, handover notes, and packaging results with claim-to-result links. Not for producing results, even with published data: hep-measurement, hep-detector, hep-theory (derivations, CRDB), hep-statistics (fits, limits, compatibility), hep-computing, hep-ml."
---

# hep-communication: literature, writing, figures

**Owns:** literature discovery and verification workflow, writing, diagrams and their rendering, talks, referee replies, handover, packaging.
**Typical artifacts:** `communication` (claims linked to results, sources actually read and at what level, figure inputs, limitations), literature matrices, manuscripts, figures with captions.
**Never:** invent a result, a number or a citation; upgrade a derivation or result status; describe synthetic or Asimov results as measurements.

## Invariants

- Every quantitative claim links to a result artifact or a source; every source records the level at which it was actually read, in the contract's terms: `not-verified`, `not-opened`, `metadata-only`, `abstract+metadata`, `page`, `full-text`. A cached file is not evidence that it was read.
- The current date, the publication or data-taking date, and the verification date are distinct. A paper newer than a ledger's verification date is unverified, not nonexistent; prefer a primary-source check.
- An identifier the ledger lacks (arXiv number, DOI, INSPIRE record) is looked up at a primary source the session may reach (INSPIRE-HEP, arXiv, doi.org) when fetching is available, and reported as looked up there (source, date), not as a ledger claim; never supplied from memory. If no source can be reached, say so.
- Status survives writing: preliminary, synthetic, Asimov, failed, unvalidated and user-supplied results say so in text and captions; a perturbative or numerical result is not called a proof.
- Physics correctness of a diagram (for example a Feynman diagram) is hep-theory's; rendering and captions are this skill's.
- Collaboration-internal information is never presented as public, and nothing implies endorsement by any collaboration or institution.

## Workflow

1. Resolve context (stanza below); read evidence records only for the claims being written.
2. Gather the result artifacts the text will cite; list each claim with its artifact or source.
3. Draft; mark limitations and statuses where they apply.
4. Write the `communication` artifact for durable deliverables and validate it.
5. Depth follows the request: **quick** (a source-backed answer, inline, from the ledger or a stated lookup), **standard** (a durable deliverable with its `communication` record), **audit** (the traceability record checked with the scripts below). Never require a full dossier for a quick answer.

## Quick questions

Answer inline, never from memory: the bound profile's ledger first, else a primary source via [the lookup recipes](references/literature-lookup-recipes.md); state source, query, access date and read level.

| Request | Action |
|---|---|
| Does paper X exist; its arXiv id or DOI | ledger, else INSPIRE `arxiv:`/`texkey` query |
| What experiment X published; the latest result | ledger (note its verification date), else INSPIRE `collaboration:X` sorted newest |
| What paper P states | read it (abstract or page); a metadata hit only shows it exists |
| Does source S support claim C | read the cited passage, then [claim-evidence mapping](references/claim-evidence-mapping.md) |
| Cite this | INSPIRE `format=bibtex`; dedupe by identifier, not key |

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Reading, reviewing, writing papers | [papers guide](references/academic-papers-guide.md) |
| Paper structure and genres (search, measurement, instrumentation, letter content lists) | [paper structure](references/paper-structure.md), [genre variants](references/paper-genre-variants.md); `check_manuscript.py --blueprint` |
| Verify a citation, latest result, what a paper states | [citation verification](references/citation-verification.md), [literature recipes](references/literature-lookup-recipes.md) |
| Bibliography and citation style; primary sources for statistics and detector methods | [citations and bibliography](references/citations-and-bibliography.md), [primary sources](references/primary-sources-and-version-checks.md) |
| Literature search, matrix, review | [literature discovery](references/literature-discovery-and-search.md); `build_lit_matrix.py` |
| Claims linked to results | [claim-evidence mapping](references/claim-evidence-mapping.md), [evidence-linked writing](references/evidence-linked-writing.md); `audit_claims.py`, `check_communication.py` |
| Figures, tables, physics plots | [figures and tables](references/figures-and-tables.md), [physics plots](references/physics-plots.md) |
| Diagrams as editable sources | [diagrams guide](references/academic-diagrams-guide.md); `check_diagram_sources.py` |
| LaTeX checks and venues | [LaTeX venues](references/latex-venue-setup.md); `check_manuscript.py` |
| Talks and posters | [posters and talks](references/poster-and-talk-design.md) |
| Referee reports and replies | [reviewer assessment](references/reviewer-style-assessment.md), [comment exchange](references/comment-and-reply-exchange.md) |
| Audience adaptation, terminology (exposure vs collection time, rigidity vs momentum) | [outreach summaries](references/outreach-and-public-facing-summaries.md); `check_adaptation.py`, `check_terminology.py` with `assets/paper/glossary-template.json` |
| Revisions and literature records; planned claims to recheck | `track_revision_impact.py`, `manage_literature.py`; [citation-verification.md](references/citation-verification.md) |
| Statistics and astroparticle papers | [statistics and ML papers](references/statistics-and-ml-papers.md), [astroparticle papers](references/astroparticle-and-cosmic-ray-papers.md) |

Scripts in `<plugin root>/skills/hep-communication/scripts/` (read `--help` first; what each checks: [README.md](README.md#scripts)). Field-specific patterns, venues and reviews have their own files under `references/`; diagram skeletons in `assets/diagrams/`, paper templates in `assets/paper/`, worked diagrams in `examples/`. Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| A missing or unclear result | the producing skill | request in `unresolved_inputs` |
| Physics correctness of a diagram or equation | hep-theory | `theory-spec` |
| Statistical wording of a claim | hep-statistics | `statistical-result` |
| Measurement design or selection behind a claim | hep-measurement | request in `unresolved_inputs` |
| Detector performance numbers | hep-detector | `response` |
| Code or scripts behind a figure or table | hep-computing | `computational-run` |

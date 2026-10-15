---
name: hep-communication
description: "Use when a request asks what a named experiment published, whether a paper exists, which result is the latest, what a paper states, whether a result supports a claim or interpretation, or for a citation: load it first even for a quick question, since it answers from the evidence ledger or a primary-source lookup, not memory. Also when the deliverable is scientific communication or literature work in physics: finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), literature matrices and reviews, drafting or revising paper sections, abstracts and captions, figures and tables, diagrams (workflows, analysis pipelines, Feynman diagrams, plate notation) as editable sources, talks and posters, referee reports, theses, proposals, handover notes, and packaging results with claim-to-result links and honest status. Not for producing results: hep-measurement, hep-detector, hep-theory (derivations), hep-statistics (fits, limits), hep-computing, hep-ml."
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
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

Folder guide for people: [README.md](README.md).

Start with [the papers guide](references/academic-papers-guide.md) for reading, reviewing and writing, or [the diagrams guide](references/academic-diagrams-guide.md) for diagrams. Citation work: [citation verification](references/citation-verification.md), [citations and bibliography](references/citations-and-bibliography.md), [primary sources for statistics and detector methods](references/primary-sources-and-version-checks.md). Claims: [claim-evidence mapping](references/claim-evidence-mapping.md), [evidence-linked writing](references/evidence-linked-writing.md). Field-specific patterns, figures, talks, reviews and venues have their own files under `references/`; diagram skeletons in `assets/diagrams/`, paper templates in `assets/paper/`, worked diagrams in `examples/`.

Scripts in `<plugin root>/skills/hep-communication/scripts/` (read `--help` first; what each checks: [README.md](README.md#scripts)): `check_manuscript.py`, `check_diagram_sources.py`, `build_lit_matrix.py`, and for evidence-linked writing ([guide](references/evidence-linked-writing.md)) `check_communication.py`, `audit_claims.py`, `track_revision_impact.py`, `manage_literature.py`, `check_adaptation.py`, `check_terminology.py`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| A missing or unclear result | the producing skill | request in `unresolved_inputs` |
| Physics correctness of a diagram or equation | hep-theory | `theory-spec` |
| Statistical wording of a claim | hep-statistics | `statistical-result` |
| Measurement design or selection behind a claim | hep-measurement | request in `unresolved_inputs` |
| Detector performance numbers | hep-detector | `response` |
| Code or scripts behind a figure or table | hep-computing | `computational-run` |

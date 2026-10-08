---
name: research-communication
description: "Use when the deliverable is scientific communication or literature work in physics: finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), literature matrices and reviews, checking whether a source supports a claim, drafting or revising paper sections, abstracts and captions, figures and tables, diagrams (workflows, analysis pipelines, Feynman diagrams, plate notation) as editable sources, talks and posters, referee reports, theses, proposals, handover notes, and packaging results with claim-to-result links and honest status. Load it first even for a quick question on what a named experiment published, which result is the latest, whether a paper exists, what a paper states, or whether a result supports a claim or interpretation: it answers from the evidence ledger, not memory. Not for producing results: hep-analysis, detector-response, hep-theory (derivations), hep-statistics (fits, limits), hep-computing, physics-ml."
---

# research-communication: literature, writing, figures

**Owns:** literature discovery and verification workflow, writing, diagrams and their rendering, talks, referee replies, handover, packaging.
**Typical artifacts:** `communication` (claims linked to results, sources actually read and at what level, figure inputs, limitations), literature matrices, manuscripts, figures with captions.
**Never:** invent a result, a number or a citation; upgrade a derivation or result status; describe synthetic or Asimov results as measurements.

## Invariants

- Every quantitative claim links to a result artifact or a source; every source records the level at which it was actually read (metadata, abstract, page, full text). A cached file is not evidence that it was read.
- The current date, the publication or data-taking date, and the verification date are distinct. A paper newer than a ledger's verification date is unverified, not nonexistent; prefer a primary-source check.
- Status survives writing: preliminary, synthetic, Asimov, failed and unvalidated results say so in text and captions; a perturbative or numerical result is not called a proof.
- Physics correctness of a diagram (for example a Feynman diagram) is hep-theory's; rendering and captions are this skill's.
- Collaboration-internal information is never presented as public, and nothing implies endorsement by any collaboration or institution.

## Workflow

1. Resolve context (stanza below); read evidence records only for the claims being written.
2. Gather the result artifacts the text will cite; list each claim with its artifact or source.
3. Draft; mark limitations and statuses where they apply.
4. Write the `communication` artifact for durable deliverables and validate it.

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

Start with [the papers guide](references/academic-papers-guide.md) for reading, reviewing and writing, or [the diagrams guide](references/academic-diagrams-guide.md) for diagrams. Citation work: [citation verification](references/citation-verification.md), [citations and bibliography](references/citations-and-bibliography.md), [source list](references/primary-sources-and-version-checks.md). Claims: [claim-evidence mapping](references/claim-evidence-mapping.md). Field-specific paper patterns, figures, talks, reviews and venue formatting have their own files under `references/`; diagram skeletons are in `assets/diagrams/`, paper templates (LaTeX skeleton, BibTeX, reading notes, methodology manual) in `assets/paper/`, worked diagram examples in `examples/`.

Scripts in `<plugin root>/skills/research-communication/scripts/` (read `--help` first): `build_lit_matrix.py`, `check_manuscript.py`, `check_diagram_sources.py`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| A missing or unclear result | the producing skill | request in `unresolved_inputs` |
| Physics correctness of a diagram or equation | hep-theory | `theory-spec` |
| Statistical wording of a claim | hep-statistics | `statistical-result` |
| Measurement design or selection behind a claim | hep-analysis | request in `unresolved_inputs` |
| Detector performance numbers | detector-response | `response` |
| Code or scripts behind a figure or table | hep-computing | `computational-run` |

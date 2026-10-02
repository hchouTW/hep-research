---
name: research-communication
description: "Use when the deliverable is scientific communication or literature work in physics: finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), literature matrices and reviews, checking whether a source supports a claim, drafting or revising paper sections, abstracts and captions, figures and tables, diagrams (workflows, analysis pipelines, Feynman diagrams, plate notation) as editable sources, talks and posters, referee reports and replies, theses, proposals, handover notes, and packaging results with claim-to-result links and honest status. Not for producing the results themselves: measurements (hep-analysis), detector studies (detector-response), derivations (hep-theory), fits and limits (hep-statistics), code (hep-computing), or ML (physics-ml)."
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

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
<!-- END context-resolution -->

## Resources

Writing, citation-verification, venue-formatting and diagram references and templates arrive in M2 under `references/` and `templates/`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| A missing or unclear result | the producing skill | request in `unresolved_inputs` |
| Physics correctness of a diagram or equation | hep-theory | `theory-spec` |
| Statistical wording of a claim | hep-statistics | `statistical-result` |

---
name: hep-literature
description: "Use when a request asks what a named experiment published, whether a paper exists, which result is the latest, what a paper states, whether a result supports a claim or interpretation, a source's status, whether citations are verified, or for a citation: load it first even for a quick question; if a comparison names no observable or experiments, ask first. Also finding and verifying literature and citations (INSPIRE-HEP, ADS, arXiv), source and claim ledgers, planned claims to recheck, literature matrices and reviews. Not for writing (hep-writing) or results, even from published data: hep-theory (CRDB, HEPData import, models, constants), hep-statistics (compatibility, p-values)."
---

# hep-literature: sources, citations, literature records

**Owns:** answers from cited sources, literature discovery and verification, read levels and verification dates, source and claim ledgers in a project, literature records, literature matrices, the evidence a review rests on; stewardship of `core/evidence` and the `adapters/literature-lookup` adapter.
**Typical artifacts:** `literature-record` (sources with identifiers, read events and versions; claims; searches; notices; flags), literature matrices, inline answers that name source, query, date and read level.
**Never:** supply a citation, identifier, number or "latest result" from memory; treat a metadata hit as having read a paper; present collaboration-internal information as public.

## Invariants

- Every source records the level at which it was actually read, in the contract's terms: `not-verified`, `not-opened`, `metadata-only`, `abstract+metadata`, `page`, `full-text`. A cached file is not evidence that it was read.
- The current date, the publication or data-taking date, and the verification date are distinct. A paper newer than a ledger's verification date is unverified, not nonexistent; prefer a primary-source check.
- An identifier the ledger lacks (arXiv number, DOI, INSPIRE record) is looked up at a primary source the session may reach (INSPIRE-HEP, arXiv, doi.org) when fetching is available, and reported as looked up there (source, date), not as a ledger claim; never supplied from memory. If no source can be reached, say so.
- An answer about "the latest result" always states the verification date and the query used (ledger date, or the database query and the date it ran).
- Collaboration-internal information is never presented as public, and nothing implies endorsement by any collaboration or institution.

## Workflow

1. Resolve context (stanza below); read the bound profile's evidence ledger before any lookup.
2. Answer from the ledger, else from a primary source; record source, query, access date and read level.
3. For a durable deliverable, import ledgers, searches and notices with `manage_literature.py` into a `literature-record` in `artifacts_dir` and validate it.
4. Depth follows the request: **quick** (a source-backed answer inline) or **audit** (the literature record with its flags and planned claims rechecked). Prose built from the record (related work, a review section) goes to hep-writing.

## Quick questions

Answer inline, never from memory: the bound profile's ledger first, else a primary source via [the lookup recipes](references/literature-lookup-recipes.md) or the optional lookup adapter (`python3 "<plugin root>/adapters/literature-lookup/assets/literature_lookup.py" IDENTIFIER`: source URL, UTC time, read level `metadata-only`); state source, query, access date and read level.

| Request | Action |
|---|---|
| Does paper X exist; its arXiv id or DOI | ledger, else the lookup adapter or INSPIRE `arxiv:`/`texkey` query |
| What experiment X published; the latest result | ledger (note its verification date), else INSPIRE `collaboration:X` sorted newest ([latest-result procedure](references/literature-guide.md#latest-result-procedure)) |
| What paper P states | read it (abstract or page); a metadata hit only shows it exists |
| Does source S support claim C | read the cited passage, then [claim-evidence mapping](references/claim-evidence-mapping.md) |
| Cite this | INSPIRE `format=bibtex`; dedupe by identifier, not key |

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; if present, run `python3 "<plugin root>/contracts/project.py" <project-dir> --preflight` and read the indexes it prints. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; `--preflight` checks them. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default ./hep-research-artifacts/), never the plugin, and pass `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`; no scratch. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Any literature task: routing, rules, latest result, ledgers | [literature guide](references/literature-guide.md) |
| Identifier lookups (INSPIRE-HEP, arXiv, ADS) and what to record | [lookup recipes](references/literature-lookup-recipes.md); `<plugin root>/adapters/literature-lookup/` |
| Verify a citation: identity, version, status, support | [citation verification](references/citation-verification.md) |
| Export a BibTeX entry from INSPIRE-HEP, ADS, arXiv, DBLP | [citation databases](references/citation-databases.md) |
| Primary sources for statistics and detector methods | [primary sources](references/primary-sources-and-version-checks.md) |
| Literature search, snowballing, coverage | [discovery](references/literature-discovery-and-search.md) |
| Read a paper; read its figures | [reading papers](references/reading-papers.md), [graphics](references/interpreting-scientific-graphics.md) |
| Claims linked to sources; planned claims to recheck | [claim mapping](references/claim-evidence-mapping.md); `manage_literature.py` |
| Literature record: ledgers, searches, notices, versions | `manage_literature.py` (writes a `literature-record`) |
| Literature matrix with read levels; review basis | `build_lit_matrix.py --require-provenance`; [review](references/literature-review.md) |
| Systematic or scoping review | [screening](references/systematic-review-screening.md) |
| Profile evidence ledgers; a ledger that disagrees with a lookup | [ledgers](references/literature-guide.md#evidence-ledgers) |
| Worked cases: latest result, citation check, ledger conflict | `examples/README.md` |

Scripts in `<plugin root>/skills/hep-literature/scripts/` (read `--help` first; what each does: [README.md](README.md#scripts)); reading-notes and search-log templates in `assets/`; worked examples in `examples/`. Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Related work, a review section or any text built from the sources | hep-writing | `literature-record` |
| Published data for a comparison (HEPData, CRDB import) | hep-theory | source identifiers, dataset record request |
| Compatibility of two published results | hep-statistics | source identifiers |
| Detector facts behind a cited number | hep-detector | source identifiers |
| Measurement design a paper describes | hep-measurement | request in `unresolved_inputs` |

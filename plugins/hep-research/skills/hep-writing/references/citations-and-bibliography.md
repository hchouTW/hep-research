# Citations and Bibliography

How to keep a `.bib` file clean as a paper evolves, and venue-specific citation-style
expectations. Where entries come from is hep-literature's
[citation databases](../../hep-literature/references/citation-databases.md).

> Network use: query only services the session's egress policy allows; queries never contain unpublished numbers,
> internal names or other unpublished content; do not put API tokens into the agent environment of a protected session.

## Table of contents
- [Finding and exporting entries](#finding-and-exporting-entries)
- [BibTeX hygiene](#bibtex-hygiene)
- [Managing a personal reference library](#managing-a-personal-reference-library)
- [Citation style by venue](#citation-style-by-venue)
- [What to cite, and how much](#what-to-cite-and-how-much)
- [Linking supplemental material and data](#linking-supplemental-material-and-data)
- [Citing an accompanying Viewpoint or Synopsis](#citing-an-accompanying-viewpoint-or-synopsis)
- [Availability statements](#availability-statements)
- [Avoiding common bibliography mistakes](#avoiding-common-bibliography-mistakes)

## Finding and exporting entries

Which database supplies an entry (INSPIRE-HEP for HEP, ADS for astronomy-facing venues, arXiv, DBLP, the ACL Anthology,
Semantic Scholar or doi.org for statistics and ML) and how to export it with its native key is hep-literature's
[citation databases](../../hep-literature/references/citation-databases.md); verify a citation there before it enters
the `.bib` (never from memory).

## BibTeX hygiene

- One `.bib` file per paper (or per collaboration-shared library), not one
  per section — makes deduplication and `check_manuscript.py`-style
  validation possible.
- Deduplicate by DOI, then arXiv identifier (version stripped), then INSPIRE
  record id — never by INSPIRE key, since one record can carry two keys
  (rule 9 of `academic-papers-guide.md`). Two entries with slightly different
  formatting for the same paper is the most common bibliography bug. `<plugin root>/skills/hep-writing/scripts/check_manuscript.py` flags a key defined twice
  (BibTeX silently keeps the first); the same paper under two different keys
  still needs a title/DOI/eprint comparison.
- Every entry in the `.bib` file should be cited at least once in the final
  text, and every `\cite{}` in the text should resolve to an entry — see
  `<plugin root>/skills/hep-writing/scripts/check_manuscript.py` in this skill for an automated check.
- For preprints that were later published, prefer the published version's
  entry (with `doi`) once available, keeping the `eprint` field for the
  arXiv number as backup.

## Managing a personal reference library

The rest of this file assumes one `.bib` file per paper. That breaks down once
someone is tracking hundreds of references across many papers and projects —
at that scale, use a reference manager (Zotero or JabRef) as the source of
truth and export per-paper `.bib` subsets from it, rather than maintaining
each paper's `.bib` by hand.

1. **Pick based on workflow, not features.** Zotero is a GUI-first library
   with a browser connector (one-click import from INSPIRE/ADS/arXiv pages),
   collections/groups for organizing by project, and cloud sync across
   machines — but it needs the **Better BibTeX** plugin to generate stable,
   predictable citation keys (INSPIRE- or ADS-style keys) instead of its own
   `AuthorYearTitleWord` default. JabRef is BibTeX-native: it stores the
   library as a plain `.bib` file (or a set of them), which diffs cleanly in
   git and needs no plugin to keep INSPIRE/ADS keys intact, at the cost of a
   less polished one-click web import than Zotero's connector.
2. **Sync INSPIRE-HEP (or ADS) exports without creating duplicates.** Before
   importing a new BibTeX entry, check whether the library already has that
   paper under its DOI, arXiv ID or INSPIRE record id — not by key or by
   title/author string match,
   which misses formatting differences (see "Duplicate physical papers under
   different keys" below). Zotero: search by arXiv ID or DOI before adding: its
   built-in duplicate detector catches some but not all near-duplicates from
   repeated imports. JabRef: use its "Find Duplicates" function, which compares
   normalized fields rather than exact key strings.
3. **Keep the INSPIRE/ADS key format through the reference manager.** The same
   reasons given in the INSPIRE-HEP workflow of
   [citation databases](../../hep-literature/references/citation-databases.md) for keeping INSPIRE's native
   key apply here — Zotero's Better BibTeX plugin should be configured to
   preserve the imported key (`pinning` the citation key) rather than
   regenerating one from its own template, since collaborators and referees
   expect the INSPIRE/ADS form.
4. **Export a project-specific `.bib` subset**, not the whole library, into
   each paper's repository. Zotero: export a collection (not the full
   library) via "Export Collection... → BibTeX"; JabRef: select the entries
   for this paper and "Export Selected Entries...". Re-export (rather than
   hand-edit the paper's `.bib`) whenever an entry's metadata changes in the
   library, so corrections don't have to be made twice.
5. **Verify the exported subset against the manuscript** the same way any
   other `.bib` file is checked — run `<plugin root>/skills/hep-writing/scripts/check_manuscript.py` against
   the paper's directory after exporting, since an export scoped to the wrong
   collection produces exactly the orphaned-entry/missing-entry problems that
   script is meant to catch.

## Citation style by venue

| Venue | Style | Notes |
|---|---|---|
| PRL/PRD/PRX (APS) | Numbered, `\bibliographystyle{apsrev4-2}` | Author list style depends on entry count; APS's style handles this automatically |
| JHEP | Numbered, `\bibliographystyle{JHEP}` | Expects INSPIRE-formatted entries with `eprint`/`archivePrefix` |
| EPJC (Springer) | Numbered, Springer physics style | Similar expectations to JHEP |
| Nature family | Numbered, superscript, Nature `.bst` | Very compressed reference format; check current author guidelines for the exact fields required |
| JCAP (astroparticle) | Numbered, `\bibliographystyle{JHEP}` | Same expectations as JHEP; INSPIRE-formatted entries |
| ApJ/ApJL, A&A, MNRAS | `natbib` author-year (`\citep{}`/`\citet{}`) | ADS-sourced entries are the norm; check the venue's current `.bst` |
| NeurIPS/ICML/ICLR/AAAI/CVPR | Numbered, conference-specific `.bst` | DBLP-sourced entries are common; many entries are arXiv-only |
| ACL/EMNLP/NAACL | `natbib` author-year via shared ACL style file | ACL Anthology-sourced entries expected |
| JMLR/TMLR, statistics journals | Varies by venue; often `natbib` author-year | Check the specific journal/venue's current style |

Do not hand-adjust citation numbering or format — let the `.bst` style file
handle it; manual tweaks break on any bibliography addition/removal.

## What to cite, and how much

- Cite the original measurement/derivation, not just a review article that
  mentions it, when precision about *who* did *what* matters (e.g. "as first
  measured in [X]").
- Cite the specific detector/reconstruction paper being relied on (tracking
  algorithm, calibration paper) rather than only the general detector paper,
  when the analysis depends on that specific tool's performance.
- Cite Monte Carlo generators and tunes by version (e.g. Pythia 8.3 with a
  specific tune) — cite both the generator paper and the tune paper if they
  differ.
- Avoid citation stuffing (a string of four or more references for an uncontroversial
  general statement) — pick the 1-2 most relevant/foundational.

## Linking supplemental material and data

Beyond the reference list itself, point readers to where the underlying numbers
live:

- **HEPData** (`hepdata.net`) is the standard repository for collider-physics
  digitized tables, cutflows, and machine-readable versions of a paper's plots —
  link it explicitly in the paper (footnote or a dedicated "Data availability"
  statement) rather than assuming a reader will find it by searching.
<!-- example: experiment-specific illustration -->
- **Some collaborations host supplemental data on their own site instead of, or in
  addition to, HEPData.** AMS-02 is a concrete example: its publications page
  (`ams02.space/publications`) links "supplemental material and data" per paper
  directly alongside the journal DOI, separate from any HEPData record. Check the
  specific collaboration's convention before assuming HEPData is the only place a
  result's tables will be published.
<!-- /example -->
- State clearly in the paper *which* venue holds the data (HEPData record number,
  a collaboration data-release URL, or a Zenodo/institutional DOI) rather than a
  vague "data available upon request," which most venues now discourage or forbid.

### Preparing a HEPData record

Sources: [hepdata_lib](https://github.com/HEPData/hepdata_lib) and the
[submission format](https://hepdata-submission.readthedocs.io/en/latest/submission_yaml.html) (opened 2026-10-14).

- `hepdata_lib` (Python, MIT licence; installed only with the user's approval) builds the submission from
  arrays or ROOT objects; the code that runs it is hep-computing's.
- `submission.yaml` lists one entry per table: a `name` (64 characters or less), a `description` close to the
  figure or table caption, `keywords`, the `data_file`, and optionally its `location` in the paper ("Figure 8A"),
  a `data_license` and `additional_resources` (code, ROOT files, likelihoods in HistFactory format).
- One table per figure panel or paper table, with the same binning and units as the paper; give the covariance
  (or correlation) matrix of the bins as its own table when the paper's uncertainties are correlated.
- The record is linked to the paper's INSPIRE record; cite the HEPData record (its DOI) in the paper's data
  availability statement.
- Analysis preservation and reinterpretation (Rivet routines, REANA workflows, CERN Analysis Preservation) are
  hep-measurement's (the analysis logic) and hep-computing's (the workflow); this skill only cites and describes them.

## Citing an accompanying Viewpoint or Synopsis

A result covered by an APS *Physics Magazine* Viewpoint/Synopsis, a Nature "News &
Views," or similar outlet commentary is not itself the primary literature — it is
secondary commentary *about* the primary paper, written either by an outside
invited expert (Viewpoint) or a science journalist/editor (Synopsis), not by the
paper's own authors.

- Cite the primary paper (the PRL/PRD/journal article) as the actual reference for
  any physics claim — never substitute the commentary piece's citation for the
  paper it discusses.
- If citing the commentary itself (e.g. the manuscript discusses how a result was
  received, or quotes the commentary's own framing), cite it separately with its
  own byline and venue — an APS Viewpoint has its own citable identity, e.g.
  `Physics 18, 19 (2025)`, distinct from the paper it comments on.
<!-- example: experiment-specific illustration -->
- Don't assume a page hosted on a collaboration's own domain is collaboration-
  authored — check the byline before citing or characterizing its authorship. See
  `outreach-and-public-facing-summaries.md` for a worked AMS-02 example
  where three same-looking pages turn out to be three different bylines (a
  journalist's recap, an APS Synopsis, and an APS Viewpoint).
<!-- /example -->

## Availability statements

Use to draft or revise data and code availability statements from actual release
information. Inventory separately the raw data, processed data, figure/table source
data, analysis code, configurations, and model weights that support the results.
For each relevant artifact record its owner/source, version or commit, persistent
identifier or URL, access status, and any verified restrictions or license.

Distinguish publicly released, controlled-access, embargoed/planned, and unavailable
artifacts. Verify links and versions when possible; an existing repository does not
prove that it contains the specific artifacts needed for this paper. Do not claim
open licensing because code is visible, or claim data are public because a request
form is available. State unverified access explicitly.

Draft concrete statements covering what is available, where, which version, and
how access works. For restricted materials, use the author-provided reason and
actual access procedure; do not invent privacy, contractual, or legal grounds,
promise future release, or imply requests will be granted. Distinguish third-party
materials from those the authors can distribute. Cite repository records alongside
the paper when they are separate scholarly objects.

Check current official venue requirements if compliance is requested. Use missing-
input markers for absent identifiers, licenses, or release dates rather than
publishing placeholders as facts. An availability statement describes access;
it does not certify reproducibility (see `reproducibility-auditing.md`).

Deliver publication-ready wording where facts are established and a short list of
unresolved inputs elsewhere. Depositing files, changing repository visibility, or
releasing restricted artifacts is outside the statement-writing task.

## Avoiding common bibliography mistakes

- **Orphaned entries**: `.bib` entries never cited in the final text — these
  accumulate as drafts evolve; `check_manuscript.py` flags them.
- **Missing entries**: a `\cite{key}` with no matching `.bib` entry, often
  from a typo in the key or an entry deleted during cleanup.
- **Duplicate physical papers under different keys**: happens when co-authors
  independently pull the same INSPIRE entry with slightly different export
  settings — dedupe by DOI, arXiv number or INSPIRE record id, not by key.
- **Self-citation imbalance**: a healthy reference list cites the field
  broadly, not disproportionately the authors' own prior work — referees
  notice and sometimes flag this explicitly.

**Done when:** `check_manuscript.py --main` reports no missing or duplicate keys, and no two `.bib` entries share a DOI, arXiv id or INSPIRE record.

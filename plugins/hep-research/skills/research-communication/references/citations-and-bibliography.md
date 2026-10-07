# Citations and Bibliography

Where to source BibTeX entries, how to keep a `.bib` file clean as a paper evolves,
and venue-specific citation-style expectations.

## Table of contents
- [INSPIRE-HEP workflow](#inspire-hep-workflow)
- [ADS for astroparticle/astronomy-facing venues](#ads-for-astroparticleastronomy-facing-venues)
- [arXiv, DBLP, and ACL Anthology for statistics/ML venues](#arxiv-dblp-and-acl-anthology-for-statisticsml-venues)
- [BibTeX hygiene](#bibtex-hygiene)
- [Managing a personal reference library](#managing-a-personal-reference-library)
- [Citation style by venue](#citation-style-by-venue)
- [What to cite, and how much](#what-to-cite-and-how-much)
- [Linking supplemental material and data](#linking-supplemental-material-and-data)
- [Citing an accompanying Viewpoint or Synopsis](#citing-an-accompanying-viewpoint-or-synopsis)
- [Availability statements](#availability-statements)
- [Avoiding common bibliography mistakes](#avoiding-common-bibliography-mistakes)

## INSPIRE-HEP workflow

For HEP papers, INSPIRE-HEP (inspirehep.net) is the standard source of BibTeX
entries — it is maintained, includes arXiv/journal cross-references, and its
keys are recognized by collaborators and referees. Workflow:

1. Search the paper on INSPIRE-HEP by title, author, or arXiv number.
<!-- example: experiment-specific illustration -->
2. Use INSPIRE's "Cite" / export feature to get a BibTeX entry with its
   standard key format: first-author surname, year, three random letters
   (`Cowan:2010js`); for a collaboration paper, the collaboration name instead
   of a surname (the ATLAS Higgs discovery is `ATLAS:2012yve`). The same export
   is available from the REST API, e.g.
   `https://inspirehep.net/api/literature?q=arxiv:1207.7214&format=bibtex`.
   Older exports used first-author keys for collaboration papers
   (`Aad:2012tfa`); INSPIRE still resolves them as aliases, but a `.bib` that
   mixes old and new keys holds the same paper twice — deduplicate on
   `eprint`/`doi` when merging an older `.bib` (checked 2026-09-26).
<!-- /example -->
3. Paste the entry as-is into the `.bib` file rather than retyping it by
   hand — this preserves the `eprint`, `archivePrefix`, `doi`, and `journal`
   fields that different `.bst` styles rely on.
4. Keep INSPIRE's key format even if it looks unfamiliar — collaboration
   co-authors and referees often expect it, and it avoids key collisions
   across a large `.bib` file.

<!-- example: experiment-specific illustration -->
Never fabricate a citation or a plausible-looking INSPIRE key — if the exact
reference can't be located, mark it (`[CITATION NEEDED: original ATLAS
combined mass paper]`) rather than inventing one.
<!-- /example -->

## ADS for astroparticle/astronomy-facing venues

For astroparticle-physics and cosmic-ray papers targeting ApJ/ApJL, A&A, or MNRAS
(rather than PRD/JHEP/JCAP), the NASA Astrophysics Data System (ADS,
`ui.adsabs.harvard.edu`) is the dominant citation database, not INSPIRE-HEP:

1. Search ADS by title, author, or arXiv number; export the BibTeX entry using its
   `bibcode` key format (e.g. `2017ApJ...848L..12A`, the GW170817 multi-messenger
   ApJL paper; INSPIRE lists the same bibcode as its ADS identifier), analogous to
   INSPIRE's `Surname:2012abc`-style keys. ADS's API needs a personal token;
   scripted access to the web UI is blocked, so export from the browser or use
   the token (checked 2026-09-26).
2. Keep the bibcode key as-is for the same reason INSPIRE keys are kept as-is —
   referees and co-authors on astronomy-side venues expect it.
3. When a paper needs both HEP-side and astronomy-side citations (common for
   multi-messenger or dark-matter-search papers), pull from whichever database
   covers that specific reference better and combine into one `.bib` file;
   deduplicate by DOI if the same paper is pulled from both databases under
   different keys.

See `astroparticle-and-cosmic-ray-papers.md` for when to prefer ADS vs. INSPIRE-HEP
by venue, and for the `natbib` author-year citation style common to these journals.

## arXiv, DBLP, and ACL Anthology for statistics/ML venues

Statistics and ML papers have no single dominant citation database the way
physics has INSPIRE-HEP — which source to use depends on where the specific paper
was actually published:

1. **arXiv's own BibTeX export** for a preprint that was never separately
   published, or when the point being made depends on a specific arXiv version
   (`v1`, `v2`, ...) — cite the version number explicitly if content changed
   between versions, since an arXiv preprint is mutable in a way a published
   paper is not. arXiv's export (`https://arxiv.org/bibtex/<id>`) is a `@misc`
   whose key and `year` come from the *latest* version: for 1706.03762 (v1 June
   2017) it gives `vaswani2023attentionneed` with `year={2023}` (checked
   2026-09-26). Set the year to the version actually cited, or use the published
   version's entry.
2. **DBLP** (`dblp.org`) for a conference-proceedings paper — strong, clean
   per-paper BibTeX export with a stable key, especially good for ML/AI
   conferences (NeurIPS, ICML, ICLR, AAAI, CVPR/ICCV/ECCV). Not verified here:
   on 2026-09-26 DBLP answered scripted requests with a bot-check page, so use
   it from a browser.
3. **ACL Anthology** (`aclanthology.org`) for any ACL/EMNLP/NAACL paper — the
   canonical source for NLP-venue papers, with its own BibTeX export matching
   the venue's own citation key conventions (`https://aclanthology.org/<id>.bib`,
   e.g. `N19-1423` gives `devlin-etal-2019-bert`; checked 2026-09-26).
4. **Semantic Scholar** (web export or API) as a fallback that covers most of the
   above plus general citation-graph lookups, useful when quickly locating a
   paper's canonical published venue is the actual blocker. Its API rate-limits
   unauthenticated use (HTTP 429 on 2026-09-26); request an API key for more than
   occasional lookups.
5. **Any DOI** (all fields): `curl -LH "Accept: application/x-bibtex"
   https://doi.org/<doi>` returns the publisher's Crossref metadata as BibTeX
   (checked 2026-09-26). Its key (`Meystre_2016`) and capitalization are
   generic, so rename the key to the project's convention and protect acronyms
   with braces.

A large fraction of the field's own citations are to arXiv preprints that were
never formally published elsewhere, or where the arXiv version and the
camera-ready conference version differ non-trivially — this is normal here in a
way it isn't in physics, so don't treat an arXiv-only citation as necessarily
incomplete. See `statistics-and-ml-papers.md` for the venue-specific citation
*style* (numbered vs. `natbib` author-year) that goes with these sources.

## BibTeX hygiene

- One `.bib` file per paper (or per collaboration-shared library), not one
  per section — makes deduplication and `check_manuscript.py`-style
  validation possible.
- Deduplicate by INSPIRE key before dedup by title/author — two entries with
  slightly different formatting for the same paper is the most common
  bibliography bug. `<plugin root>/skills/research-communication/scripts/check_manuscript.py` flags a key defined twice
  (BibTeX silently keeps the first); the same paper under two different keys
  still needs a title/DOI/eprint comparison.
- Every entry in the `.bib` file should be cited at least once in the final
  text, and every `\cite{}` in the text should resolve to an entry — see
  `<plugin root>/skills/research-communication/scripts/check_manuscript.py` in this skill for an automated check.
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
   paper under its INSPIRE key or arXiv ID — not by title/author string match,
   which misses formatting differences (see "Duplicate physical papers under
   different keys" below). Zotero: search by arXiv ID or DOI before adding: its
   built-in duplicate detector catches some but not all near-duplicates from
   repeated imports. JabRef: use its "Find Duplicates" function, which compares
   normalized fields rather than exact key strings.
3. **Keep the INSPIRE/ADS key format through the reference manager.** The same
   reasons given in "INSPIRE-HEP workflow" above for keeping INSPIRE's native
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
   other `.bib` file is checked — run `<plugin root>/skills/research-communication/scripts/check_manuscript.py` against
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
- Avoid citation stuffing (a string of 5+ references for an uncontroversial
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
  settings — dedupe by INSPIRE key or arXiv number, not by BibTeX key string.
- **Self-citation imbalance**: a healthy reference list cites the field
  broadly, not disproportionately the authors' own prior work — referees
  notice and sometimes flag this explicitly.

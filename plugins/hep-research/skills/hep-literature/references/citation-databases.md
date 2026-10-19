# Citation databases

Where a citation comes from: finding a paper and exporting its record from INSPIRE-HEP, ADS, arXiv, DBLP, the ACL
Anthology, Semantic Scholar or doi.org, and which database a venue expects. Moved from hep-writing's
[citations and bibliography](../../hep-writing/references/citations-and-bibliography.md), which keeps BibTeX hygiene,
the reference library and citation style. Scripted identifier lookups and what to record for each (source, query,
date, read level) are in [literature lookup recipes](literature-lookup-recipes.md); whether the cited text supports
the claim is [citation verification](citation-verification.md).

> Network use: query only services the session's egress policy allows; queries never contain unpublished numbers,
> internal names or other unpublished content; do not put API tokens into the agent environment of a protected session.

## Table of contents
- [INSPIRE-HEP workflow](#inspire-hep-workflow)
- [ADS for astroparticle/astronomy-facing venues](#ads-for-astroparticleastronomy-facing-venues)
- [arXiv, DBLP, and ACL Anthology for statistics/ML venues](#arxiv-dblp-and-acl-anthology-for-statisticsml-venues)

## INSPIRE-HEP workflow

For HEP papers, INSPIRE-HEP (inspirehep.net) is the standard source of BibTeX
entries — it is maintained, includes arXiv/journal cross-references, and its
keys are recognized by collaborators and referees. Workflow:

1. Search the paper on INSPIRE-HEP by title, author, or arXiv number.
<!-- example: experiment-specific illustration -->
2. Use INSPIRE's "Cite" / export feature to get a BibTeX entry with its
   standard key format: first-author surname, year and a random suffix, three
   letters in current keys (`Geller:2026xhh`) and two in older ones
   (`Cowan:2010js`); for a collaboration paper, the collaboration name instead
   of a surname (the ATLAS Higgs discovery is `ATLAS:2012yve`; INSPIRE REST
   `texkeys`, checked 2026-10-14). The same export
   is available from the REST API, e.g.
   `https://inspirehep.net/api/literature?q=arxiv:1207.7214&format=bibtex`.
   Older exports used first-author keys for collaboration papers
   (`Aad:2012tfa`); INSPIRE still resolves them as aliases, but a `.bib` that
   mixes old and new keys holds the same paper twice (record 1124337 carries
   both, checked 2026-10-14) — deduplicate by identifier, never by key; the
   order and the renaming rule are rule 9 of hep-writing's
   [papers guide](../../hep-writing/references/academic-papers-guide.md).
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

See hep-writing's
[astroparticle papers](../../hep-writing/references/astroparticle-and-cosmic-ray-papers.md) for when to prefer ADS vs. INSPIRE-HEP
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
incomplete. See hep-writing's
[statistics and ML papers](../../hep-writing/references/statistics-and-ml-papers.md) for the venue-specific citation
*style* (numbered vs. `natbib` author-year) that goes with these sources.

**Done when:** the entry was exported from the database that holds the paper (not retyped), its key is the
database's own, and the identifier it carries has been checked as `citation-verification.md` describes.

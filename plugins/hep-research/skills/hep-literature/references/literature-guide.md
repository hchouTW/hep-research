# Literature (guide)

Routing and rules for every hep-literature task: answers from cited sources, citation verification, literature search,
reading, literature records and matrices. The reading half of the former papers guide and its reference index moved
here when the communication skill was split; writing, refereeing and venues stay in hep-writing's
[papers guide](../../hep-writing/references/academic-papers-guide.md).

## When to read this file

| Task | Minimum inputs | Load | Output | Done when |
|---|---|---|---|---|
| Quick source-backed answer | the question; ledger or a reachable primary source | `literature-lookup-recipes.md`, `citation-verification.md` | an inline answer naming the source, its version and read level | the source and date are stated; nothing from memory |
| The latest result of a collaboration or on an observable | collaboration or observable; ledger if bound | [latest-result procedure](#latest-result-procedure) | the answer with verification date and query | date and query are stated; a newer paper is not ruled out without a lookup |
| What a paper states; does a source support a claim | the source and the claim | `reading-papers.md`, `claim-evidence-mapping.md` | the passage read, its locator and the read level | the read level is `page` or `full-text` for a support verdict |
| Literature search and lifecycle | search log, ledgers, notices | `literature-discovery-and-search.md` | `manage_literature.py` `literature-record` with provenance | merges only on identifiers; flags listed; the record validates |
| Literature matrix or review basis | reading notes (CSV) | `literature-review.md` | `build_lit_matrix.py --require-provenance` table | every row has an identifier and a read level |
| Systematic or scoping review | protocol, databases | `systematic-review-screening.md` | screening log and counts | each exclusion has a reason |
| A BibTeX entry for a known paper | the identifier | `citation-databases.md` | the exported entry with its source | exported, not retyped |

Writing the related-work text, a review section or a referee report from the record is hep-writing's: hand over the
`literature-record`.

## Rules for every task

1. **Nothing from memory.** No citation key, DOI, arXiv id, page range, number or "latest" claim that was not read or
   looked up in this session; give the lookup route or mark it `[CITATION NEEDED: ...]`.
2. **Ledger first, then a primary source.** The bound profile's evidence ledger is read before any lookup; an
   identifier it lacks is looked up at INSPIRE-HEP, arXiv, ADS or doi.org (the optional adapter
   `<plugin root>/adapters/literature-lookup/assets/literature_lookup.py` runs these lookups and records source URL and
   UTC time) and reported as looked up there, never as a ledger claim.
3. **Read levels are honest.** A metadata hit (`metadata-only`) shows a paper exists, not what it says; a claim is
   supported only by a passage read at `page` or `full-text` level, with its locator.
4. **Dates are distinct.** The current date, the publication or data-taking date and the verification date are three
   values; a paper newer than the ledger's verification date is unverified, not nonexistent.
5. **Compare like with like.** Before comparing values across papers, check quantity and unit (energy vs rigidity,
   per-nucleon vs total, local vs global significance, 68% vs 95% CL); a compatibility statement is hep-statistics'.
6. **One paper, one entry.** Identifiers decide (DOI, else arXiv id without version, else INSPIRE record id), never
   keys or titles; similarity proposes a merge, a reader decides.

## Latest-result procedure

1. Ledger: find the newest source for the collaboration and observable; note its verification date.
2. Lookup: query INSPIRE-HEP sorted by date, newest first (`collaboration:X and t <observable>`, `sort=mostrecent`);
   for an astronomy-facing venue also ADS. Record the query string, the date it ran and the number of hits.
3. Compare: a hit newer than the ledger's verification date is reported as "newer, not in the ledger, read level
   `metadata-only`" until it is read; a superseded result is named with what supersedes it.
4. Answer: the result, its source and status (preliminary, published), the verification date and the query. With no
   reachable source, give the ledger's answer with its date and say that nothing newer was checked.

## Evidence ledgers

A bound profile may ship an evidence ledger (`sources.json`, `claims.json`, an index) and a source policy. Read the
index the preflight prints, then only the claims the question needs; never load a whole large ledger.

- A ledger claim carries a source, a read level and a verification date; quote them with the claim.
- A planned claim (an announced run, an intended upgrade) has a `recheck_by` date; after it, the claim is rechecked
  before use (`manage_literature.py` flags it).
- **Ledger and lookup disagree** (a different identifier, version, status or value): report both with their dates and
  sources, prefer the primary source read at the higher level, and record the disagreement (a notice or a new read
  event in the literature record); never silently overwrite the ledger, which belongs to the profile's maintainers.
- A profile's source policy (which sources count, which tiers) overrides general preferences for that profile.

## Core workflow: reading

0. **Find the literature before triaging it**, when there isn't already a paper or stack in hand: pick the right
   database(s) for the field, formulate and vary search terms, and snowball citations forward and backward from
   strong seed papers rather than relying on one keyword search. See `literature-discovery-and-search.md`.
1. **Triage before deep-reading.** For any paper (or stack of papers), do a fast first pass (title, abstract, section
   headings, figures, conclusion) before deciding it's worth reading in full. Most papers only need this pass. See
   `reading-papers.md` for the full three-pass method.
2. **Read for claims and evidence separately.** What does the paper claim, and what evidence actually supports each
   claim (dataset, method, statistical test, comparison baseline)? Keep these visibly distinct in notes: conflating
   "the paper says X" with "X is well-supported" is the most common reading error. When the evidence is a figure, see
   `interpreting-scientific-graphics.md`.
3. **Take structured notes as you read**, not after: `../assets/reading-notes-template.md` (claim / method /
   evidence / limitations / relevance) and its JSON record `../assets/reading-notes-record-template.json`.
4. **When reading multiple papers toward a review**, build a comparison matrix (method, dataset, key result, year)
   as you go: `<plugin root>/skills/hep-literature/scripts/build_lit_matrix.py` turns the notes into a Markdown
   table. See `literature-review.md`.
5. **Synthesize, don't list.** A review groups papers by what they share or how they differ and states the gap; the
   prose is drafted in hep-writing from the matrix and the record.

## Reference files

Read these as needed; don't load them all up front.

**Sources and verification**
- `literature-lookup-recipes.md`: INSPIRE-HEP, ADS and arXiv queries, rate limits, and what to record (source, query,
  date, read level)
- `citation-verification.md`: reference identity, version and status, and whether cited text supports the claim (a
  resolving DOI or a valid BibTeX entry alone doesn't verify it)
- `citation-databases.md`: exporting entries from INSPIRE-HEP, ADS, arXiv, DBLP, the ACL Anthology, Semantic Scholar
  and doi.org, with their key conventions
- `primary-sources-and-version-checks.md`: PDG reviews, Cowan et al., pyhf, RooStats, exact-interval and
  shower-profile sources the plugin's tools rely on (also cited by hep-detector)
- `claim-evidence-mapping.md`: connect claims to results, derivations and citations; flag unsupported
  generalizations (hep-writing uses it for its own drafts)

**Reading and discovery**
- `literature-discovery-and-search.md`: database and tool choice by field, query formulation, snowballing, alerts,
  and knowing when search coverage is enough
- `reading-papers.md`: the three-pass method, claims vs evidence, a critical-reading checklist, and HEP,
  astroparticle and statistics/ML specific checks
- `interpreting-scientific-graphics.md`: reading plots correctly (exclusion contours, corner plots, ROC curves,
  skymaps), approximate values when no table exists, misleading techniques
- `literature-review.md`: organizing a review (chronological, thematic, methodological), comparison matrices,
  synthesis vs citation-stuffing, research gaps and novelty assessment
- `systematic-review-screening.md`: eligibility, reproducible search logs, deduplication, screening decisions

## Literature record

`manage_literature.py import INPUT.json --project-root ROOT --out <artifacts_dir>/<name>.json` writes a
`literature-record` artifact (contracts 2.13.0): the envelope with `producer_skill` hep-literature and the record in
`extension` (sources with identifiers, read events and versions; claims; searches; notices; relations; proposed
merges; flags). It never looks anything up: online verification is recorded as not performed. Validate it with
`python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`, then hand it to hep-writing, whose
`check_citations.py` checks a draft's citations against it.

**Done when:** the answer or record names every source with its identifier, read level and verification date, and
anything not verified is marked as such.

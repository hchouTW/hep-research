# Citation verification

Use for a reference audit, questionable attribution, or checking the evidence
behind manuscript claims. For export, use
`citation-databases.md` (formatting and `.bib` hygiene: `../../hep-authoring/references/citations-and-bibliography.md`); for the lookup queries themselves (INSPIRE-HEP,
ADS, arXiv), `literature-lookup-recipes.md`.

## Table of contents
- [Verification steps](#verification-steps)
- [Deliverable](#deliverable)
- [Tooling note](#tooling-note)

## Verification steps

1. Establish scope: all references, a specified section, or selected consequential
   claims. If sampling, report the selection and do not certify the whole paper.
2. Resolve each reference against the publisher, original repository, or relevant
   scholarly index. Compare title, authors, year, DOI/arXiv identifier, and version;
   do not accept a plausible title or a search snippet as verification. This
   includes an AI-generated summary of a fetched page: a summarization pass can
   misreport a count, date, or list length even when the page was fetched
   correctly — treat it the same as a search snippet, not as having checked the
   source. For anything numeric or enumerable (a publication count, a list of
   entries), get the itemized content or the raw page/record directly, or
   cross-check two passes that reach the source by different routes (two summaries of the same page by the same
   model are not independent), rather than trusting one summarized answer.
3. Read the relevant passage, equation, table, or figure in the primary source.
   Check the population/dataset, conditions, uncertainty, and qualifiers against
   the citing sentence. Separate direct support from inference and secondary
   attribution; locate the original source for priority claims when possible.
4. Check current publisher/repository records for corrections, retractions, and
   version changes. Record the lookup date and sources consulted. If access or
   network limits prevent a check, mark it unverified rather than inferring that
   no notice exists. A notice requires assessing its effect on the specific claim,
   not silently deleting the citation. Where to look (checked 2026-10-14):
   - INSPIRE-HEP: the record's `withdrawn` field (query `withdrawn:true` works) and
     linked erratum records;
   - arXiv: the abstract page and version history (a withdrawal is a new version
     with a withdrawal comment; see arXiv, "Withdraw / Retract a Submission",
     https://info.arxiv.org/help/withdraw.html);
   - Crossref: `https://api.crossref.org/works?filter=updates:<DOI>` lists notices
     (erratum, correction, retraction) that update a DOI; each carries `update-to`
     with its `type`, and retractions may come from the Retraction Watch data
     (`source: retraction-watch`). An empty result means no notice is registered
     there, not that none exists. Documentation: Crossref REST API filters
     (https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/, `updates`: "is an
     update to the given DOI") and Retraction Watch in the REST API
     (https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/), both opened 2026-10-14.
5. Propose the smallest correction: narrow the claim, fix metadata, cite the
   relevant version, or supply a verified replacement. Keys: rename only to
   merge one paper held under two keys, by rule 9 of `../../hep-authoring/references/academic-papers-guide.md`
   (keep the current key, update every `\cite`, delete the other).

## Licence and open access

Before reusing a figure or text, read the article's licence on its journal page. HEP articles in journals covered
by SCOAP3 are immediately open access with authors keeping copyright (the article states its licence): for 2025-2027 SCOAP3 lists EPJC, JHEP, NPB and PLB at 100% coverage, while for
PRL, PRD and PRC only articles submitted to a high-energy-physics arXiv category are covered (13%, 56% and 9% of HEP
articles in its 2022-2023 coverage figures) ([SCOAP3 journals 2025-2027](https://scoap3.org/journals-2025-2027/),
opened 2026-10-14). Coverage of one article is checked on the article, not inferred from the journal.

## Reusing previously verified records

A ledger entry or a `sources_read` record from an earlier session is reused as it
is: keep its verification date, version (arXiv version, DOI version), read level
and locators. It stays a statement about what was read on that date. Never
relabel an old read event as a new one, and never raise its read level without
reading again. Recheck before quoting when the claim is time-sensitive ("the
latest result", "still the best limit", "no correction has appeared"), when the
record's version differs from the version cited, or when the manuscript now cites
a passage the old locators do not cover; otherwise the old record supports the
same claim it supported before. A recheck is a new read event with its own date
beside the old one, not a replacement of it.

## Planned claims

A schedule, an intended upgrade, an announced run or a promised release is a plan, not a result. Record it in the
ledger as a claim with `"kind": "planned"` and a `"recheck_by": "YYYY-MM-DD"` date, and write it in the future tense
with the date it was read: "as of 2026-10-12, the installation is planned for 2027 [source]", never "the detector has
the new layer". `manage_literature.py` flags a planned claim once its `recheck_by` date has passed (exit 3) and reports
one without a date; recheck at a primary source, then record the outcome as a new claim or move the date. A planned
claim never supports a measured result: `audit_claims.py` refuses a supporting edge of a measurement, search or limit
claim to a source whose only ledger claims are planned, and a measured claim marked planned (exit 1).

## Deliverable

Deliver a ledger with: manuscript location and claim; citation key and stable
identifier/version; evidence locator and source link; metadata/status findings;
support verdict (supported, partial, unsupported, or unverified); proposed fix.
Keep metadata correctness separate from evidentiary support. Report unresolved
items explicitly, including sources available only as abstracts.

## Tooling note

`check_manuscript.py` checks local reference consistency; it does not establish
that a source exists, remains current, or supports a scientific claim.

**Done when:** every audited citation has a recorded lookup (source, date, read level) and a verdict, and every mismatch has a proposed correction or is marked unverified.

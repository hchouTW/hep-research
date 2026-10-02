# Source Policy and Evidence Rules

## When to read this file

Read when quoting any AMS result or performance value, when a question contains "latest", "current", "has AMS published", "is this paper real", or when interpreting a result. Canonical home for source tiers, the evidence-ledger schema, currency checks, conflict resolution, citation placement, and unsupported-claim behavior. The populated ledger is [source-index](../../evidence/index.md).

## Contents

1. [Source tiers](#source-tiers)
2. [Evidence ledger schema](#evidence-ledger-schema)
3. [Source-review procedure](#source-review-procedure)
4. [Currency checks ("latest")](#currency-checks-latest)
5. [Conflicts between sources](#conflicts-between-sources)
6. [Citation placement](#citation-placement)
7. [Result interpretation](#result-interpretation)
8. [Unsupported-claim behavior](#unsupported-claim-behavior)
9. [Failure modes / Required source classes / Questions to ask](#failure-modes)

## Source tiers

| Tier | Class | Use |
|---|---|---|
| 1 | Peer-reviewed AMS Collaboration papers and supplements | AMS results, methods, performance in that analysis |
| 2 | Official AMS detector papers, website, technical documents, formal data releases | Detector description, geometry, mechanism |
| 3 | Public conference material or theses by AMS authors | Labeled "less formal or potentially outdated"; **preliminary** unless a paper says otherwise |
| 4 | PDG, authoritative textbooks, peer-reviewed methodology papers | General principles (kinematics, statistics, unfolding) |
| 5 | Other experiments | Methodological comparison only; never AMS practice |
| 6 | Reviews, press, slides, secondary articles, encyclopedias | Navigation only; secondary-only evidence must be labeled |

## Evidence ledger schema

Every quantitative claim entering an answer or this skill needs a ledger row:

```yaml
claim_id: null
claim: null
claim_type: detector_fact | performance_number | analysis_method | published_result | general_method
source_title: null
collaboration_or_author: null
publication_date: null
doi_or_url: null
source_tier: 1
location_in_source: section/page/figure/table
supported_scope: null      # species, energy/rigidity range, selection, period, CL, detector configuration
known_limitations: null
last_verified: YYYY-MM-DD
```

The populated ledger is machine-readable in `${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/evidence/sources.json` and `${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/evidence/claims.json` (checked by `${CLAUDE_PLUGIN_ROOT}/core/evidence/ledger.py`; the tables in [source-index](../../evidence/index.md) are generated from it). A claim's `verification_strength` may not exceed its best supporting source, numeric quotation needs at least an abstract read, and an AMS-practice claim needs a Tier 1-2 source. A number without its context (species, range, selection, period, CL, configuration) must not be quoted. `source-index` records the verification level actually achieved: `full-text`, `abstract+metadata`, `metadata-only`, or `not-opened`; a claim's strength never exceeds it.

**Reading a paper from the local cache (maintainers).** `${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/evidence/papers_manifest.json` lists every AMS Collaboration article in INSPIRE-HEP (AMS-01 and AMS-02, tagged by a heuristic) with its DOI, the ledger source IDs that cite it and ordered candidate PDF URLs; `${CLAUDE_PLUGIN_ROOT}/profiles/experiments/ams-02/scripts/fetch_papers.py fetch` downloads into a cache outside the repository (`$AMS_PAPERS_CACHE`) and records a SHA-256 and a version label per file. The label matters: a `publisher` PDF is the published paper, while an `arxiv` or `repository` copy is a preprint or accepted manuscript, and the ledger's `verification_note` must say which was read. A transient error (HTTP 5xx, 406, a network failure) is retried once; a paper that blocks scripted access (HTTP 401/403/429, a bot-verification page) is never retried, is recorded as blocked and must be downloaded by a person and registered with `adopt`; do not work around it. The optional `--supplements` flag also fetches APS Supplemental Material files (off by default; the table supplements of S43-S47 alone are about 16,000 pages); their numbers still need scoped claims, so transcribing them is a separate decision. A cached file creates no claim: add or promote claims only after reading it, at the level read, and re-run the ledger validator. Check that a downloaded file is the paper its name says before relying on it.

## Source-review procedure

1. Open the primary document; do not rely on search snippets or citation aggregators.
2. Separate **publication date** from the **data-taking interval**. In any "latest" or superseded-paper answer, write both explicitly for each cited result (e.g. "published year Y, data taken years A-B") and say when the newer publication merely extends the data period versus changes the analysis. Example: the positron-flux paper S04 (published 2019) used data from 2011-05-19 to 2017-11-12 (C24); the 2013 and 2014 positron-fraction papers (S02, S03) used data from 2011-05-19 to 2012-12-10 and to 2013-11-26 (C03, C113), so the later one extends the range and statistics rather than changing the data period start. Do this even when the user's premise only mentions a publication year.
3. Check errata, supplementary material, and later superseding publications. When offering verified alternatives, give each one's verification level, publication date and data-taking period from its ledger row. Do this for every alternative, including the review (S01) and the Supplemental Material records (S41-S47, e.g. S46): a short per-alternative line such as `S0x: <verification level>; published <date>; data <period>`, with "not recorded in the index" where the row has none.
4. Record whether a conference claim is preliminary.
5. When several AMS results coexist (e.g. different rigidity ranges, periods, track configurations), explain which question each answers rather than retaining only the newest number.
6. Paraphrase; do not copy long copyrighted passages.
7. A bracket citing several claim IDs asserts every clause of the sentence for every ID: cite per clause, and check each ID's own species, range, period and paper (a daily-proton claim does not support a Bartels-rotation or lepton statement).
8. Phrase absence statements taken from the ledger as "the index records no ...", not as a first-person search ("I found no ...").

## Currency checks ("latest")

Triggers: "latest", "most recent", "current", "has AMS published", "as of", any result or hardware-status claim that may have changed since the verification date of the ledger rows it rests on (each source row carries its own `verification_date`; most rows were verified **2026-09-20**, some later).

Keep three dates distinct: the **current date** (from the environment or the user; this profile does not know it), each result's **publication date and data-taking period** (from its ledger row), and each row's **verification date** (when the row was last checked). Never present a verification date as today's date, and never use one as a publication or data-taking date. For a ledger statement say "as of its verification on <that row's verification_date>"; when the current date is known and later, say the check may be out of date. Procedure: (1) search INSPIRE-HEP with the collaboration filter and date sort (metadata, not a snippet); (2) open the AMS results page and the journal record; (3) report publication date, data period, formal status (peer-reviewed / preprint / conference); (4) check for supplements and superseding papers; (5) state the verification date of each row used. If browsing is unavailable: state the verification limitation and the verification dates of the rows used; do not claim currency; give the last known result with its publication date and data-taking period as "as of the last check".

## Conflicts between sources

Prefer the newer primary analysis, and explain the difference in definition, period, selection, or calibration (e.g. rigidity vs energy binning, track configuration, data-taking period, reconstruction version). A conflict between Tier 1 and Tier 3/6 resolves to Tier 1; a Tier 1 conflict with another Tier 1 is explained, not averaged.

## Citation placement

Put the citation next to the claim (S-number from [source-index](../../evidence/index.md), plus paper and year), not at the end of the answer. General methods carry Tier 4 references; proposals are labeled as proposals and not cited as AMS practice. Formatting alone earns nothing: the cited source must support the specific claim.

## Result interpretation

Separate: **direct measurement** (flux, ratio, fraction and their uncertainties) from **model interpretation** (dark matter, pulsar, propagation, source-term fits). State what the measurement excludes and what it does not. Reject unsupported extrapolation beyond the measured rigidity/energy range, period, and species. A fit of a functional form in a paper is a description, not a proof of mechanism. Agreement between measurements is consistency, not proof.

## Unsupported-claim behavior

- **Fabricated or unverifiable citation:** say it could not be verified; report what a search found (or that nothing matched); do not confirm it and do not "fill in" its content; offer the closest verified papers.
- **Citation dated after the verification date, or one that cannot be accessed:** classify it as **unverified**, not as nonexistent: the ledger only records what was checked up to each row's verification date, and a newer or paywalled paper may well exist. Check primary sources when browsing is available (INSPIRE-HEP with the collaboration filter, the journal record, the Collaboration publications page). Until the paper is located and read, do not summarize, confirm or quote it; say what was checked and when. If it is found, record the level actually read (`metadata-only`, `abstract+metadata`, `full-text`) and use it only at that level. An implausible volume, page or date is worth stating as a reason for caution, but it still yields "unverified", not "nonexistent".
- **Ambiguous "the 2015 paper":** ask whether the publication year or the data-taking year is meant, and offer the candidate record from [source-index](../../evidence/index.md).
- **Unpublished claim:** classify as conference/preliminary/rumor; never state as an established result; never supply counts.
- **Missing performance number:** say which source class would contain it and what context is needed; do not estimate.
- **Internal AMS detail requested** (pass, trigger bit, good-run rule, calibration constants, internal notes): state that it is not public; offer a generic recommendation and list the missing evidence.
- **Old result vs new:** distinguish; do not mix definitions.

## Failure modes

- Citing search snippets; citing a paper not opened without stating so.
- Quoting a headline number without species/range/selection/period.
- Presenting a Tier 3 or 6 statement as a result; "latest" answered from memory.
- Attributing a general method to AMS because the paper is about AMS.
- Averaging or merging results with different definitions.

## Required source classes

This file itself: no AMS numbers. Evidence for the procedure: INSPIRE-HEP and journal records (Tier 1/2 for AMS); PDG (Tier 4).

## Questions to ask the user

Is browsing available for a current check? Which specific result, species, range, and period? Do you have a DOI or arXiv number for the paper in question? Is this for a public paper or an internal note?

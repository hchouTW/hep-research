# Literature discovery and search

Use when the task is finding relevant papers on a topic — before there is
anything to triage or read yet. This precedes `reading-papers.md` (which
assumes you already have papers in hand) and is narrower than the searching
done inside `systematic-review-screening.md` (a formal, logged protocol for
a specific review) or the one-off "has this been done before" check inside
the novelty-assessment section of `literature-review.md`. Use
`citations-and-bibliography.md` instead when the paper is already identified
and the task is only pulling a clean BibTeX entry for it.

1. **Pick the database(s) for the field**, not just whichever is habitual:
   - HEP/collider: INSPIRE-HEP first (citation graph, author disambiguation,
     collaboration-paper handling), arXiv hep-ex/hep-ph/hep-th listings.
   - Astroparticle/astro: ADS (bibcode-based, tracks errata/retractions),
     arXiv astro-ph.
   - Statistics/ML: arXiv cs.LG/stat.ML listings, Semantic Scholar (citation
     graph and API), DBLP (conference/venue metadata), ACL Anthology for
     NLP venues.
   - Cross-field or unsure: Google Scholar and Semantic Scholar cover the
     widest range but have weaker field-specific metadata (venue tiering,
     collaboration author lists) — cross-check a key result against the
     field-specific database before relying on it.
2. **Formulate queries deliberately.** Start from the terminology in a seed
   paper's own keywords/abstract, not just the user's phrasing — a technique
   often has multiple names across subfields (e.g. "unfolding" vs.
   "deconvolution", "in-context learning" vs. "few-shot prompting"). Run
   the same search with at least two term variants before concluding
   coverage is complete; record which terms were tried.
3. **Snowball in both directions from strong seed papers**, not just
   forward from an initial keyword search:
   - Backward: read the seed paper's own related-work/references for the
     line of work it builds on.
   - Forward: use "cited by" (INSPIRE-HEP, ADS, Semantic Scholar, Google
     Scholar all support this) to find who has since built on or challenged
     the seed paper — this is often how the *most current* related work is
     found, since a brand-new paper won't yet appear in keyword search
     rankings.
   - Stop snowballing a branch when new results stop being relevant, not
     after a fixed number of hops.
4. **Set up alerts for fast-moving areas** (arXiv daily listings by
   category, INSPIRE-HEP/ADS/Semantic Scholar saved-search alerts) when the
   literature search will need to stay current across a writing project
   rather than being a one-time pull.
5. **Track what was searched and when.** Even outside a formal systematic
   review, record the databases, query terms, and date searched — this
   lets a later claim of "no prior work found" be checked rather than taken
   on faith, and avoids re-running the same search from scratch later.
6. **Know when to stop.** Coverage is adequate when new searches and
   citation-snowball branches stop surfacing papers not already found, not
   when a fixed count is reached. "Not found in the sources searched" is
   not proof of absence — state it as a bounded claim, not a universal one.

Deliver a source list with, per entry: how it was found (query/snowball
direction/alert), and enough bibliographic detail to hand off to
`citations-and-bibliography.md` for formatting. Deliver the query/database
log alongside it so the search is reproducible later. Do not silently drop
papers that seemed off-topic — note why they were excluded if a systematic
record is being kept.

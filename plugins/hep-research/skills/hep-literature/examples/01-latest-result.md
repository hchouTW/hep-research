# The latest result, with its date and query

**Request.** "Which is the latest FIX result on the secondary-to-primary ratio? I want to cite it."

**Read first.** The bound profile's evidence ledger (its index from the preflight): the newest FIX source on the ratio
is `fix:S12`, a journal paper, `verification_level: full-text`, `verification_date: 2026-03-02`.

**Lookup (rules 2 and 4 of the literature guide).** The ledger is seven months old, so a newer paper is possible:

```text
INSPIRE-HEP  q = collaboration:FIX and t ratio   sort = mostrecent   run 2026-10-19 09:40 UTC   hits: 14
newest hit:  "FIX ratio with the full data set" (arXiv:2609.01234v1, 2026-09-28, no journal reference yet)
```

The adapter form of the same check records source URL and UTC time:
`python3 "<plugin root>/adapters/literature-lookup/assets/literature_lookup.py" arxiv:2609.01234` (read level
`metadata-only`).

**Answer.**

> The newest FIX ratio paper in the profile ledger is `fix:S12` (journal paper, read in full, ledger verified
> 2026-03-02). An INSPIRE-HEP query run on 2026-10-19 (`collaboration:FIX and t ratio`, newest first) finds a newer
> preprint, arXiv:2609.01234v1 (2026-09-28), seen at `metadata-only`: it exists, but its content has not been read
> and it is not yet published. Cite `fix:S12` for a published value; cite the preprint only after reading the passage
> you rely on, and state its preprint status.

**Hand on.** Nothing to hep-writing yet; if the user drafts with it, the read preprint goes into a `literature-record`
first (`manage_literature.py import`).

**Done when:** the answer states the ledger date, the query and the date it ran, and the read level of each source.

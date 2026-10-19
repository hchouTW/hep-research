# Literature lookup recipes

How to answer "does this paper exist", "what did X publish", "which is the latest" or "give me the BibTeX" from a
primary source instead of memory, and what to record afterwards. Use only when the session may reach the network
(egress policy); otherwise say the lookup could not be made and mark the answer `not-verified`. Queries never carry
protected or collaboration-internal content. Endpoints and limits below were opened on 2026-10-14; recheck them if a
request fails.

## Which source for which question

| Question | First source | Then |
|---|---|---|
| HEP paper exists; its arXiv id, DOI, journal reference | INSPIRE-HEP literature API | arXiv API for the preprint itself |
| What a collaboration published, newest first | INSPIRE-HEP, `collaboration:` query sorted `mostrecent` | the collaboration's own publication list |
| Astronomy or astroparticle paper outside INSPIRE | ADS search API (needs a token) | arXiv |
| BibTeX for a paper | INSPIRE `format=bibtex` (keeps the INSPIRE texkey) | ADS export |
| Who cites a paper | INSPIRE `refersto:recid:N` | ADS (see below) |
| Withdrawn, retracted or corrected | see `citation-verification.md` (retraction and licence checks) | |

## INSPIRE-HEP

Source: [INSPIRE REST API documentation](https://github.com/inspirehep/rest-api-doc) (opened 2026-10-14).

```bash
curl -s 'https://inspirehep.net/api/literature?q=arxiv:1007.1727&fields=titles,dois,arxiv_eprints,texkeys,control_number'
curl -s 'https://inspirehep.net/api/literature?q=texkey%20Cowan:2010js&fields=titles,control_number'
curl -s 'https://inspirehep.net/api/literature?q=collaboration:NAME&sort=mostrecent&size=5&fields=titles,dois,arxiv_eprints'
curl -s 'https://inspirehep.net/api/literature?q=refersto:recid:860907&size=1&fields=control_number'   # citing papers
curl -s 'https://inspirehep.net/api/literature/860907?format=bibtex'
```

- `fields=` limits the JSON to what you need; `format=bibtex` returns the BibTeX entry.
- Rate limit: 15 requests per 5 s window per IP; above it the server answers HTTP 429, and blocked requests count
  towards the quota, so wait at least 5 s after a 429.
- An absent `arxiv_eprints` field means the record has no arXiv version; it says nothing about why.
- One record can carry two texkeys (an older and a current one); deduplicate by identifier (rule 9 of
  `../../hep-authoring/references/academic-papers-guide.md`).

## ADS

Source: [ADS API documentation](https://github.com/adsabs/adsabs-dev-api) (opened 2026-10-14).

```bash
curl -H "Authorization: Bearer $ADS_TOKEN" 'https://api.adsabs.harvard.edu/v1/search/query?q=doi:"10.1103/PhysRevLett.126.041104"&fl=bibcode,title,doi'
```

- Every request needs a personal token in an `Authorization: Bearer` header; without one, the lookup is not made:
  say so, never guess. Limits are per endpoint and reported in the `X-RateLimit-*` response headers (a daily quota).
- Second-order operators: `citations(query)` returns the records citing the results of `query`, and
  `references(query)` the records cited by them, for example `citations(author:"huchra, john")` or
  `references(bibcode:2003AJ....125..525J)`; they combine with other terms, as in
  `citations(bibcode:2006SSRv..123..485G) OR abstract:(Webb OR JWST)`. Source: [ADS search help, citations and
  references](https://ui.adsabs.harvard.edu/help/search/citations-and-references), read through its
  [source file](https://raw.githubusercontent.com/adsabs/adsabs.github.io/master/_includes/_help/search/_posts/citations-and-references.md)
  (accessed 2026-10-15, read level `page`; the help page itself returned an empty HTTP 202 response to a plain
  request).

## arXiv

Source: [arXiv API terms of use](https://info.arxiv.org/help/api/tou.html) (opened 2026-10-14).

```bash
curl -s 'https://export.arxiv.org/api/query?id_list=1007.1727'
curl -s 'https://export.arxiv.org/api/query?search_query=ti:%22asymptotic%20formulae%22&max_results=5'
```

- The response is Atom XML; the version is part of the id (`1007.1727v3`).
- At most one request every three seconds, one connection at a time.
- On 2026-10-15 the API answered HTTP 429 ("Rate exceeded.") four times to `id_list` with a nonexistent id, while
  an existing id resolved minutes apart: a 429 says neither that the id exists nor that it does not.

## Optional lookup client

`<plugin root>/adapters/literature-lookup/assets/literature_lookup.py` runs the identifier lookups above (INSPIRE,
arXiv, ADS) and prints one record per source with the source URL, the UTC retrieval time, the read level and an arXiv
version check (cited `v1` against the latest), for example `literature_lookup.py arxiv:1007.1727v1`. It is optional:
nothing here requires it, and the `curl` recipes give the same answer. The ADS token comes from `ADS_API_TOKEN` (or
`ADS_TOKEN`) and is never printed; without it the ADS result is `not-verified`. Exit 0 found, 1 not found, 2 bad
input, 3 incomplete (rate limit, network error, no token, version mismatch).

## What to record after a lookup

Each lookup that supports an answer is recorded, inline for a quick answer or as a read event in the `communication`
record (`../../hep-authoring/references/evidence-linked-writing.md`):

- source and the exact query or URL;
- access date (the current date, distinct from the paper's date and the ledger's verification date);
- read level, in the contract's terms: `not-verified`, `not-opened`, `metadata-only` (an API record),
  `abstract+metadata`, `page`, `full-text`;
- the identifiers found (DOI, arXiv id with version, INSPIRE record id, texkey).

A metadata lookup is `metadata-only`: it shows that a paper exists and where, not what it says. Read the abstract or
the page before attributing a statement to it.

**Done when:** the answer names its source, query, access date and read level, and every identifier in it was
returned by that lookup (none supplied from memory), or the answer says the lookup could not be made.

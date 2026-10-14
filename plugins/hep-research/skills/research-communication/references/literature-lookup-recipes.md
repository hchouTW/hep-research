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
curl -s 'https://inspirehep.net/api/literature?q=collaboration:ATLAS&sort=mostrecent&size=5&fields=titles,dois,arxiv_eprints'
curl -s 'https://inspirehep.net/api/literature?q=refersto:recid:860907&size=1&fields=control_number'   # citing papers
curl -s 'https://inspirehep.net/api/literature/860907?format=bibtex'
```

- `fields=` limits the JSON to what you need; `format=bibtex` returns the BibTeX entry.
- Rate limit: 15 requests per 5 s window per IP; above it the server answers HTTP 429, and blocked requests count
  towards the quota, so wait at least 5 s after a 429.
- An absent `arxiv_eprints` field means the record has no arXiv version; it says nothing about why.
- One record can carry two texkeys (an older and a current one); deduplicate by identifier (rule 9 of
  `academic-papers-guide.md`).

## ADS

Source: [ADS API documentation](https://github.com/adsabs/adsabs-dev-api) (opened 2026-10-14).

```bash
curl -H "Authorization: Bearer $ADS_TOKEN" 'https://api.adsabs.harvard.edu/v1/search/query?q=doi:"10.1103/PhysRevLett.126.041104"&fl=bibcode,title,doi'
```

- Every request needs a personal token in an `Authorization: Bearer` header; without one, the lookup is not made:
  say so, never guess. Limits are per endpoint and reported in the `X-RateLimit-*` response headers (a daily quota).
- Second-order operators `citations()` and `references()` exist in the ADS search syntax; their exact behaviour was
  not re-opened here (unverified): check the ADS search help before relying on them.

## arXiv

Source: [arXiv API terms of use](https://info.arxiv.org/help/api/tou.html) (opened 2026-10-14).

```bash
curl -s 'http://export.arxiv.org/api/query?id_list=1007.1727'
curl -s 'http://export.arxiv.org/api/query?search_query=ti:%22asymptotic%20formulae%22&max_results=5'
```

- The response is Atom XML; the version is part of the id (`1007.1727v3`).
- At most one request every three seconds, one connection at a time.

## What to record after a lookup

Each lookup that supports an answer is recorded, inline for a quick answer or as a read event in the `communication`
record (`evidence-linked-writing.md`):

- source and the exact query or URL;
- access date (the current date, distinct from the paper's date and the ledger's verification date);
- read level, in the contract's terms: `not-verified`, `not-opened`, `metadata-only` (an API record),
  `abstract+metadata`, `page`, `full-text`;
- the identifiers found (DOI, arXiv id with version, INSPIRE record id, texkey).

A metadata lookup is `metadata-only`: it shows that a paper exists and where, not what it says. Read the abstract or
the page before attributing a statement to it.

**Done when:** the answer names its source, query, access date and read level, and every identifier in it was
returned by that lookup (none supplied from memory), or the answer says the lookup could not be made.

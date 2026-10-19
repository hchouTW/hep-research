# A draft's citations against a literature record

**Request (to hep-authoring).** "The introduction is drafted; check that every citation is real before we submit."

**Step 1, hep-citations: the record.** The reading notes and the ledger rows the introduction rests on are imported
into the project's artifacts folder:

```bash
python3 "<plugin root>/skills/hep-citations/scripts/manage_literature.py" import notes/lit_input.json \
  --project-root . --out hep-research-artifacts/literature-intro.json --today 2026-10-19
python3 "<plugin root>/contracts/validate.py" hep-research-artifacts/
```

The record is a `literature-record` artifact (`producer_skill` hep-citations, status `user-supplied`), so the
directory validates and the record can be handed over.

**Step 2, hep-authoring: the check.**

```bash
python3 "<plugin root>/skills/hep-authoring/scripts/check_citations.py" paper/intro.tex paper/refs.bib \
  --record hep-research-artifacts/literature-intro.json
```

Synthetic outcome (exit 3, `incomplete`):

| Citation | Status | Matched by | Read level |
|---|---|---|---|
| `Fix:2026a` | found (`lit:S01`) | identifier (DOI) | page |
| `Fix:2024b` | found (`lit:S03`) | identifier (arXiv) | metadata-only: warning `citation.read_level_low` |
| `Smith:2025q` | not-verified | none | none |

**Step 3, back to hep-citations.** `Smith:2025q` came from a co-author's memory. It is looked up (INSPIRE `texkey`
query, date recorded); if it exists, its cited passage is read and a new import adds it to the record; if not, the
sentence is rewritten or carries `[CITATION NEEDED: ...]`. `Fix:2024b` is read at page level before it supports the
claim in the second paragraph.

**Done when:** a rerun of `check_citations.py` exits 0, or every remaining citation is marked unverified in the text.

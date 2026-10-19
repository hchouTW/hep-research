# Worked examples

Illustrative and synthetic: the collaboration "FIX", its papers, identifiers and dates are invented, and no lookup in
these files was run against a live service. Each file shows the request, what is read first, the commands or queries,
the answer with its source, read level and dates, and what is handed on. Run the real tools (`manage_literature.py`,
the lookup adapter, hep-writing's `check_citations.py`) on real inputs before relying on an answer.

| File | Case | Takeaway |
|---|---|---|
| [01-latest-result.md](01-latest-result.md) | "Which is the latest FIX result on the ratio?" with a ledger checked months ago | the answer names the verification date and the query; a newer hit is reported at `metadata-only`, not dismissed |
| [02-draft-citations.md](02-draft-citations.md) | a draft's citations checked against a literature record before submission | `check_citations.py` lists each citation without a record as `not-verified`; the fix is a lookup and a read, not memory |
| [03-ledger-conflict.md](03-ledger-conflict.md) | the profile ledger and an INSPIRE lookup disagree on a paper's arXiv version | report both with dates, prefer the source read at the higher level, record the disagreement; never rewrite the ledger |

# The ledger and a lookup disagree

**Request.** "The profile ledger cites arXiv:2501.04321v1 for the FIX efficiency paper. Is that the version to cite?"

**Read first.** Ledger row `fix:S20`: `arxiv_ids: ["2501.04321v1"]`, `verification_level: full-text`,
`verification_date: 2025-02-11`.

**Lookup.** The adapter, run 2026-10-19 (`literature_lookup.py arxiv:2501.04321v1`), reports from the arXiv API:
latest version `v3` (2025-11-30), a version check `requested v1, latest v3`, exit 3 (incomplete: a version mismatch);
INSPIRE now lists a journal reference.

**Answer.**

> Two records disagree. The profile ledger (verified 2025-02-11) holds v1, read in full. arXiv now has v3
> (2025-11-30) and INSPIRE a journal version; both were seen on 2026-10-19 at `metadata-only`. The ledger is not
> wrong, it is older: v1 is what was read. To cite the published version, read the passage you rely on in it (or in
> v3) and compare it with v1; until then, cite v1 explicitly and say a later version exists.

**Record, do not overwrite.** The ledger belongs to the profile's maintainers; the session records its own reading in
the project: an import with a `journal-version` notice for `fix:S20` flags the claims that cite it for reassessment
(`manage_literature.py`, exit 3 until they are reread), and the old read event stays.

**Done when:** both versions are named with their dates and read levels, and the reassessment is recorded, not
silently resolved.

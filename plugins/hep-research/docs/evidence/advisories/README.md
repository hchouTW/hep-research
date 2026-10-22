# Sci-fix advisories

`SFA-YYYY-NNN.json`, format `hep-research-scifix-advisory/2` (see `tools/scifix_advisories.py` and the
*Scientific corrections* section of `docs/maintenance.md`). Numbers are never reused.

**Numbers never published.** SFA-2026-012, SFA-2026-013 and SFA-2026-026 to SFA-2026-029 have no file. No commit of
the repository ever held such a file or mentioned these numbers (`git log --all`, checked 2026-10-22); the 26
advisories of commit `6e7274c3` were numbered within SFA-2026-004 to -035, and the six unused numbers were left out
then. The reason was not recorded. They are not withdrawn advisories, so they carry no OSV `withdrawn` tombstone.

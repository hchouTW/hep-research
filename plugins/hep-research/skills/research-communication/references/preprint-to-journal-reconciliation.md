# Preprint-to-journal reconciliation

Use when tracking what changed between an arXiv (or other preprint-server)
version and the peer-reviewed journal version of the same work — deciding
what to update on the preprint, writing an erratum, or explaining a
discrepancy a reader has flagged. Use `revision-impact-tracking.md` for
tracing changes *during* an active revision; this file is for reconciling two
already-existing, publicly citable versions afterward.

1. Establish which versions are being compared: preprint version number
   (e.g. arXiv vN) and the published version (with DOI, volume/issue/page or
   article number). Pull both texts directly rather than relying on memory of
   what changed during review.
2. Diff systematically, not just by skimming the abstract:
   - Numerical results: any changed value, uncertainty, or significance
     between versions, and whether the change came from a correction, a
     referee-requested reanalysis, or a copy-edit.
   - Title, author list, and affiliations (order or membership changes are
     common and easy to miss).
   - Structural changes: renamed/reordered sections, material moved to
     supplementary information, added/removed figures or tables.
   - Added citations or comparisons requested by referees.
3. Classify each difference: substantive (affects a claim, number, or
   conclusion), presentational (journal house style, length-limit trims), or
   correction of an actual preprint error. Flag any substantive difference
   that a reader citing only the preprint version would miss.
4. Check what the venue and preprint server expect after publication: most
   journals expect the arXiv listing updated with the published DOI and a
   journal-reference field. The journal DOI is the version of record; the arXiv
   listing is the open copy (in HEP often the one readers use, and it should
   carry the journal reference and DOI). Check the target venue's own norm for
   what the preprint may contain after acceptance. Note if
   collaboration policy skips arXiv entirely, per an existing publication
   pattern the user has already told you about — do not add one that wasn't
   posted.
5. If a substantive difference resulted from a post-publication error
   (rather than the normal review process), route it as an erratum/corrigendum
   decision to the user rather than silently reconciling — this is an editorial
   action, not a text edit.

Deliver a version-diff table (location, preprint text/value, published
text/value, classification) and the specific preprint-metadata updates
needed (DOI, journal reference, version note). Do not claim a discrepancy is
"just a copy-edit" without checking whether it changes a number or claim.

**Done when:** every difference between the preprint and the journal version is listed with its effect on the results, and the arXiv record carries the journal reference and DOI.

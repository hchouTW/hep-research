# Multi-venue reformatting

Use when adapting one manuscript's content across two venues with different
class files or length limits — a conference paper extended into a journal
submission, a journal letter expanded into a full-length companion paper, or
the same result reformatted for a second venue (e.g. a NeurIPS paper into a
JMLR submission, or a PRL letter into an accompanying PRD). Use
`latex-and-formatting.md` for the mechanics of any single class file, and
`paper-structure.md` for what belongs in each section; this file is about
reconciling *two* versions of the same content.

1. Establish the relationship between the versions: is the new venue a strict
   superset (conference → journal extension, typically requiring genuinely
   new material — extended proofs, more experiments, related-work depth — not
   just reformatting, per most venues' policies against duplicate
   publication), a length-reduced version (journal → conference/letter), or a
   parallel version for a different audience (e.g. a technical PRD alongside
   a PRL letter)? This determines whether content is added, cut, or ported.
2. Check the target venue's duplicate/prior-publication policy before
   starting — many venues require the new submission to cite the earlier
   version explicitly and describe what is new; some require a percentage-new
   threshold. Do not treat this as a purely mechanical reformat if the venue
   treats it as a submission-ethics question.
3. When cutting for a shorter venue: preserve the result and its uncertainty/
   significance, the minimum method description needed to trust the result,
   and the single most important comparison; move derivations, additional
   systematics, and secondary results to supplementary material or the longer
   companion version, with an explicit pointer between the two.
4. When extending for a longer venue: identify what's genuinely new
   (additional derivations, ablations, systematics, datasets) versus what is
   only being restated at greater length — reviewers and editors will ask the
   same question. Do not pad a short result to fill a longer venue's implicit
   expectations.
5. Reconcile shared artifacts across both versions: figure/table numbering
   will differ, but the underlying data, captions' factual content, and
   citation keys should stay consistent unless the underlying result changed
   between submissions (in which case, use `revision-impact-tracking.md`).
   Check that neither version claims priority or credit inconsistent with the
   other's stated submission/acceptance dates.

Deliver a mapping table (source-version location → target-version location:
kept as-is, cut, moved to supplement, or newly written) plus the venue's
duplicate-publication disclosure text if required. Flag any content cut for
length that changes the target version's own claims or conclusions rather
than dropping it silently.

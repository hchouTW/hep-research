# Plagiarism and text-reuse checking

Use when checking a manuscript for improper text reuse: copied passages from
other authors, undisclosed reuse of the user's own prior publications
(self-plagiarism), or paraphrase close enough to need attribution. This is
about textual originality, not reference identity or claim support — use
`citation-verification.md` for whether a cited source exists and supports a
claim.

1. Establish scope: full manuscript, a specific section, or passages flagged
   by the user or a similarity report. If working from a similarity-checker
   report (iThenticate, Turnitin, or similar), treat its percentage as a
   starting point, not a verdict — it flags string overlap, including
   boilerplate (methods-section phrasing, standard model names, dataset
   descriptions) that is not plagiarism.
2. For each flagged or suspected passage, locate the earlier source and
   compare directly. Distinguish:
   - Verbatim or near-verbatim copying without quotation or citation.
   - Close paraphrase that follows the source's sentence structure and
     ordering while swapping words — still requires attribution.
   - Legitimate reuse: direct quotation with citation, standard field
     terminology, boilerplate method/equipment descriptions, or the user's
     own previously published text reused with proper self-citation and
     without violating the earlier venue's copyright transfer.
3. For self-plagiarism specifically, check whether the earlier work is cited
   at the point of reuse and whether the reused material is substantive
   (methods, results, argument) rather than incidental (a standard dataset
   description repeated across a paper series). Flag reused figures/tables
   that need copyright permission from the original publisher, not just a
   citation.
4. Do not accept a low similarity-report score as proof of originality
   (it misses idea-level plagiarism and paraphrase of non-English sources)
   or a high score as proof of misconduct (it flags legitimate quotation and
   common phrasing). Read the underlying text in both cases.
5. Propose the smallest fix: add a citation and quotation marks, rewrite in
   the author's own words with citation retained, or flag for removal if the
   passage cannot be legitimately attributed. Route a suspected misconduct
   finding (undisclosed large-scale reuse, duplicate submission) to the user
   as a decision, not an automatic edit — do not silently rewrite around a
   finding that may need disclosure to an editor.

Deliver a ledger with: manuscript location, source location, overlap type
(verbatim / close paraphrase / legitimate reuse), similarity-report score if
available, verdict, and proposed fix. Keep the originality check separate
from citation-identity verification — a passage can be correctly cited and
still be an unattributed copy of its wording.

# Thesis-by-publication assembly

Use when assembling a thesis or dissertation from the user's own
already-published (or submitted) papers, rather than writing one
continuous document from scratch. Use the thesis-chapter guidance in
`paper-genre-variants.md` for how a single chapter is structured,
`plagiarism-and-text-reuse-checking.md` for the self-plagiarism/reuse
questions this specifically raises, and `latex-mechanics-and-tooling.md`'s
multi-file-document-structuring section for the actual `\include{}`/
`\includeonly{}` mechanics of combining chapter files; this file is about
the decisions involved in assembling multiple papers into one coherent
document, not the LaTeX syntax itself.

1. Confirm the institution's specific requirements before drafting — most
   graduate schools that permit thesis-by-publication require: a stated
   minimum/maximum number of included papers, connective material (an
   overarching introduction and conclusion, sometimes linking preambles
   before each paper), an explicit statement of the candidate's contribution
   to each multi-author paper, and permission language for reusing
   copyrighted published material. These requirements vary by institution
   and department — get the current graduate-school guidelines rather than
   assuming a generic format.
2. **Check copyright/reuse rights before reusing published text or figures
   verbatim.** A published paper's copyright is often held by the publisher,
   not the author; most publishers grant authors a right to reuse their own
   work in a thesis, but this needs confirming per-publisher (check the
   copyright transfer agreement or the publisher's self-archiving policy)
   rather than assumed. Where reuse isn't automatically permitted, get
   explicit permission or reproduce as a citation/summary instead of
   verbatim text.
3. **Write connective material that argues for the thesis as a whole**, not
   just a list of papers: an overarching Introduction that states the
   thesis's unifying question and how each paper contributes to answering
   it, and a Conclusion that synthesizes across papers — restating each
   paper's individual conclusion is not synthesis. Use
   `literature-review.md`'s synthesis-vs-listing guidance for this framing
   even though the "literature" here is the candidate's own prior work.
4. **State each paper's individual contribution and co-author breakdown**
   explicitly where the papers are multi-author — this is usually a required
   statement (often per-chapter) distinguishing the candidate's own
   contribution from co-authors', not an authorship-order judgment to make
   unilaterally. Get this from the user/co-authors rather than inferring it
   from author-list position, per `submission-and-peer-review.md`'s
   authorship-and-contributions guidance.
5. **Reconcile inconsistencies across papers written at different times**:
   notation, terminology, dataset versions, or a result later revised
   (`revision-impact-tracking.md`/`preprint-to-journal-reconciliation.md`)
   may differ between an early-thesis paper and a late one. Flag these
   explicitly in connective material rather than silently harmonizing
   notation in a way that misrepresents what was actually published.
6. Check the specific status of each included paper (published, accepted,
   under review, submitted, or a thesis-only unpublished chapter) and label
   it accordingly — a thesis committee and examiners need to know which
   chapters have been peer-reviewed.

Deliver the assembled thesis with connective material clearly distinguished
from the reproduced papers, a per-chapter contribution/copyright-permission
status table, and any cross-paper inconsistencies flagged rather than
silently smoothed over.

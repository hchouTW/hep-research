# Erratum and corrigendum drafting

Use once the decision to correct the published record has already been
made (by the user, following `preprint-to-journal-reconciliation.md`'s
routing of a post-publication error, or a `comment-and-reply-exchange.md`
Reply that concedes a material point) and the task is drafting the
correction notice itself. This file is about the mechanics of the notice,
not deciding whether one is warranted — that decision belongs to the user
and, often, the journal's editor.

1. Classify the correction before drafting, since venues distinguish these
   and expect the right label:
   - **Erratum**: an error introduced during production (typesetting,
     figure/table transposition, a value corrupted after acceptance) not
     present in the accepted manuscript.
   - **Corrigendum**: an error made by the authors in the published science
     itself (a calculation mistake, a mislabeled dataset, an incorrect
     statistical test) that the accepted manuscript also contained.
   - **Addendum**: new information supplementing (not correcting) the
     published result — check whether the venue treats this the same as a
     corrigendum or as a distinct type.
   Ask the user or check the journal's guidelines when the classification is
   ambiguous; do not default to the less serious-sounding label.

   The classification (whose error, what changed) is always stated in the
   notice; the **label is the venue's**, and venues differ. The split above is
   Elsevier's and IOP's; others title every correction "Erratum":

   | Venue | Label used | Source (opened 2026-10-14) |
   |---|---|---|
   | Elsevier (PLB, NPB, ...) | Erratum = publisher's error; Corrigendum = author's change approved by the editor | [Elsevier errata policy](https://www.elsevier.com/editor/perk/policy-and-best-practice-errata-and-corrigenda) |
   | IOP (JCAP, JINST, ...) | Corrigendum = author's error; Erratum = IOP's error | [IOP publishing support](https://publishingsupport.iopscience.iop.org/?p=393) |
   | APS (PRL, PRD, PRC) | Erratum for errors or omissions in published papers, whatever the cause; a "Publisher's Note" exists but its definition is unverified | [PRL information for authors](https://journals.aps.org/prl/authors) |
   | JHEP (Springer/SISSA) | "Erratum to: <title>" (usage seen, not a policy page) | Crossref record of doi:10.1007/JHEP04(2024)064 |
   | EPJC (Springer) | "Publisher Erratum: <title>" for a publisher error (usage seen) | Crossref record of doi:10.1140/epjc/s10052-023-12244-w |

   Recheck the venue's live page before submitting; these change.
2. State precisely what was wrong and what it should have been — quote the
   original text/value/figure and give the corrected version side by side.
   Do not restate the whole paper; a correction notice is scoped to the
   specific error and its consequences, not a general revision.
3. Trace and disclose the error's actual impact using
   `revision-impact-tracking.md`'s dependency-tracing approach: does the
   error change the headline result, its uncertainty, or the conclusion, or
   is it confined to a presentational detail? State this explicitly in the
   notice — a correction that doesn't affect the paper's conclusions should
   say so; one that does must say what the corrected conclusion is, not just
   that an error occurred.
4. Follow the venue's specific mechanics: most journals require the
   correction submitted through the same production system as the original
   paper, linked bidirectionally by DOI (the correction cites the original;
   the original's online record is updated to point to the correction), and
   some require co-author sign-off on the correction text itself, separate
   from the original paper's sign-off.
5. If the underlying result was cited by other papers before the correction
   was issued, that is a fact to disclose to the user, not something to fix
   retroactively in this notice — a correction notice fixes the original
   paper's record, it does not chase down citing papers.

Deliver the correction notice in the venue's required form (often a strict,
short template), with the error, its correction, and its impact on
conclusions stated explicitly and separately. Use the venue's label, but never
soften the classification: an author error is described as the authors'
error even when the venue calls the notice an Erratum.

**Done when:** the notice uses the venue's label, states whose error it was, quotes the old and corrected values, and says whether the conclusions change.

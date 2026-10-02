# Literature Review

How to turn a set of individually-read papers (see `reading-papers.md`) into a
coherent literature review or a paper's own related-work/Introduction section.

## Table of contents
- [Organizing structure](#organizing-structure)
- [Building a comparison matrix](#building-a-comparison-matrix)
- [Synthesis, not a list](#synthesis-not-a-list)
- [Spotting the gap](#spotting-the-gap)
- [Novelty assessment](#novelty-assessment)
- [Common pitfalls](#common-pitfalls)

## Organizing structure

Pick one primary organizing principle and use it consistently; mixing several
mid-section is a common source of a confusing review:

- **Chronological** — good when a field's understanding evolved in a clear sequence
  (each result built on or corrected the last). Risk: can read as a list of "and then
  X happened" without synthesis unless each transition explains *why* the field
  moved on.
- **Thematic** — group by sub-question or physical effect addressed, regardless of
  publication date. Good for a broad field where several independent lines of work
  converge on the same overall question. Most literature reviews and most papers'
  related-work sections use this by default.
- **Methodological** — group by technique/approach (e.g. "cut-based analyses" vs.
  "multivariate analyses" vs. "unfolding-based approaches" for the same measurement).
  Good when the user's own contribution is specifically a new method being compared
  against prior methods.

For a paper's own Introduction (as opposed to a standalone review article), keep this
section short and purposeful — it exists to set up what's new in *this* paper, not to
be exhaustive; see `paper-structure.md`.

## Building a comparison matrix

Once several papers address the same question, a table communicates faster and more
precisely than prose. Typical columns: paper (citation key), year, dataset/energy,
method, key result (with uncertainty), and any notable limitation. Build this
incrementally while reading (per `reading-papers.md`), not as a final step.

`${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py` automates the formatting step: give it a CSV with one
row per paper and it produces a ready-to-paste markdown table.

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py notes.csv --sort-by year -o lit_matrix.md
```

Expected CSV columns are flexible — the script uses whatever header row is given —
but a typical one looks like:

```csv
key,year,method,dataset,result,notes
ATLAS:2012yve,2012,cut-based search,7-8 TeV ATLAS,"126.0 +/- 0.4 +/- 0.4 GeV",discovery paper
Chatrchyan:2012xdj,2012,cut-based search,7-8 TeV CMS,"125.3 +/- 0.4 +/- 0.5 GeV",independent discovery
```

The result is a compact table the user can paste straight into a draft and adjust the
prose around, rather than reformatting a spreadsheet by hand each time a paper is
added.

## Synthesis, not a list

A synthesized paragraph groups papers by what they share or where they disagree, and
states the takeaway explicitly — it does not narrate a bibliography in citation
order. Compare:

> **List (avoid):** Smith et al. measured X using method A [1]. Jones et al. later
> measured X using method B [2]. Lee et al. extended this to a wider energy range [3].

> **Synthesis (prefer):** Two independent measurements of X, using different methods
> [1, 2], agree within uncertainties, and a subsequent extension to a wider energy
> range [3] found no significant energy dependence — together these establish X as
> largely constant over the range relevant to this analysis.

The synthesized version tells the reader *why* the citations are grouped together and
what conclusion to draw, which is the actual job of a literature review paragraph.

## Spotting the gap

Every literature review section (whether standalone or inside a paper's Introduction)
should end by stating, explicitly, what is not yet addressed by the work just
surveyed — this is what motivates the current paper or highlights an open question
for a review article. Useful gap patterns to look for while building the comparison
matrix:

- **Coverage gap** — no prior work addresses this specific regime/channel/energy.
- **Precision gap** — prior work addresses it, but with larger uncertainty than a new
  dataset or method could achieve.
- **Consistency gap** — prior results disagree with each other, and this work aims to
  resolve the tension.
- **Method gap** — prior work relies on an assumption or approximation that a new
  method avoids.

State the gap in one or two sentences, directly connected to what the current paper
(or the review's own conclusion) does about it — a gap identified but never
addressed in the rest of the paper reads as an unfulfilled promise to the reader.

## Novelty assessment

Use when evaluating a proposed contribution or substantiating an Introduction's
novelty claim. State the contribution precisely: new question, method, proof,
measurement, dataset, regime, precision, or validation. Separate novelty from
usefulness and evidentiary strength; an incremental contribution can be valuable.

Search current primary literature using both the proposed terminology and nearby
methods or older names for the same idea. Follow references and subsequent work
from the closest papers. Record sources searched, queries, date, and coverage
limits; use `citation-verification.md` to verify what the nearest sources actually
establish. Search-result snippets and titles alone cannot establish equivalence.

Build a focused comparison: prior work/version, question, assumptions, method,
data/regime, result, overlap with the proposal, and substantive difference. Account
for preprint/published versions of the same work. Distinguish a conceptual change
from a new application, larger sample, implementation change, or stronger test.
Do not infer priority solely from publication year when version dates matter.

Deliver a defensible gap statement, the closest competing contributions with
evidence locators, and what must be demonstrated to substantiate the difference.
Qualify coverage: "not found in the sources searched" is not proof of absence.
Avoid "first" or "unprecedented" unless the evidence supports the stated scope.
If the novelty depends on unresolved equivalence or inaccessible prior work,
mark it unresolved rather than declaring the proposal novel or unoriginal.

## Common pitfalls

- **Recency bias**: over-weighting the newest papers just because they're freshest in
  mind, at the expense of foundational earlier work that a referee will expect cited.
- **Self-citation imbalance**: leaning heavily on the authors' own prior work rather
  than surveying the field broadly — referees notice and sometimes flag this
  explicitly (see also `citations-and-bibliography.md`).
- **Citation stuffing**: a string of 4-5+ references for an uncontroversial general
  statement, with no differentiation between them — pick the 1-2 most relevant/
  foundational instead, or briefly note how the grouped papers differ if they must
  all be cited together.
- **Outdated comparison**: citing a method's original paper for "the state of the
  art" when later work has since improved on it — check the comparison matrix's
  `year` column before writing "the best current approach is..."
- **Treating a review as a to-do list**: a review's job is to synthesize what's known
  and identify gaps, not to exhaustively summarize every paper's abstract in
  sequence — if a paragraph could be replaced by "see refs. [1-8]" without losing
  information, it isn't yet doing a review's actual job.

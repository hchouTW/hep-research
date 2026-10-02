# Paper Genre Variants

How the standard section-by-section backbone in `paper-structure.md` (Title →
Abstract → Introduction → Methods → Analysis → Systematics → Results → Summary)
shifts for document types that aren't a standard experimental HEP paper: theory
papers, review articles, thesis chapters, and proceedings. Read the relevant
subsection rather than the whole file.

## Table of contents
- [Theory papers](#theory-papers)
- [Review articles](#review-articles)
- [Thesis chapters](#thesis-chapters)
- [Proceedings](#proceedings)
- [Astroparticle and cosmic-ray papers](#astroparticle-and-cosmic-ray-papers)
- [Statistics and ML papers](#statistics-and-ml-papers)

## Theory papers

The template shifts: Introduction → Model/Formalism → Calculation → Results/
Phenomenology → Discussion. Expect (and budget space for):
- A longer, self-contained derivation section — theory referees expect to be
  able to follow the calculation, not just cite the result.
- Explicit statement of assumptions and their validity range early, since the
  entire paper's conclusions are conditional on them.
- A phenomenology section translating the formal result into observable
  predictions, ideally compared against existing or near-future experimental
  sensitivity.

## Review articles

Structured more like a textbook chapter: broad Introduction, then organized by
sub-topic rather than by "what we did" — since there is no single "we did X."
Expect a much larger reference list, an explicit statement of scope (what is
and isn't covered, and why), and a closing "open questions" section rather than
a conclusion restating a single result.

## Thesis chapters

Similar backbone to a paper but expanded: include material a paper would cut
for space (fuller derivations, more validation plots, negative results/things
tried that didn't work, more detail on personal contribution vs.
collaboration-wide work). A thesis chapter based on a published paper should
still be written in the author's own words, not pasted from the paper, both
for originality and because the fuller thesis context changes what needs
explaining.

## Proceedings

Short (often 4-10 pages), summarizing a talk rather than presenting a full new
result: Introduction (brief) → the one or two key plots/results shown at the
conference → brief conclusion. Assume the reader has seen, or could look up,
the full paper this proceeding is based on — proceedings should not duplicate
a full paper's derivations.

## Astroparticle and cosmic-ray papers

The same backbone applies, with "Detector" becoming "Instrument"/"Observatory"/
"Array," "luminosity" becoming "exposure," and — for point-source or anisotropy
searches — an arrival-direction section with its own pre-trial/post-trial
significance treatment, separate from the energy-spectrum section. Atmospheric and
hadronic-interaction-model systematics (QGSJET, EPOS, Sibyll, ...) typically dominate
the systematics section for air-shower analyses, in place of detector-alignment
systematics. See `astroparticle-and-cosmic-ray-papers.md` for the full treatment,
including venue-specific conventions (JCAP, ApJ/ApJL, Astroparticle Physics),
collaboration author-list handling for ground arrays/IACTs/space detectors, and
skymap/energy-spectrum figure conventions.

## Statistics and ML papers

The backbone shifts more here than for any other variant in this file: Related
Work is usually its own section rather than woven into the Introduction, and
Limitations and (at several venues) a Broader Impact/Ethics Statement are
required, separately-labeled sections rather than closing remarks. A
reproducibility checklist is often a required submission component, not optional
prose, and the appendix routinely carries full hyperparameter tables and
additional experiments that reviewers are expected to actually read - unlike a
physics paper's supplemental material, which a referee may or may not open. See
`statistics-and-ml-papers.md` for the full treatment, including venue-specific
conventions (NeurIPS/ICML/ICLR/ACL vs. JMLR/TMLR vs. statistics journals),
author-contribution statements, arXiv-first citation practice, and the
single-shot rebuttal process that replaces a journal's multi-round revision.

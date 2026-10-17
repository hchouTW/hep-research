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
- [Combination papers](#combination-papers)
- [Statistics and ML papers](#statistics-and-ml-papers)
- [Search papers](#search-papers), [Precision measurements](#precision-measurements), [Instrumentation and performance papers](#instrumentation-and-performance-papers), [Letters](#letters)

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
searches — an arrival-direction section, separate from the energy-spectrum section,
whose significances are quoted pre- and post-trial (`scientific-style.md`). Atmospheric and
hadronic-interaction-model systematics (QGSJET, EPOS, Sibyll, ...) typically dominate
the systematics section for air-shower analyses, in place of detector-alignment
systematics. See `astroparticle-and-cosmic-ray-papers.md` for the full treatment,
including venue-specific conventions (JCAP, ApJ/ApJL, Astroparticle Physics),
collaboration author-list handling for ground arrays/IACTs/space detectors, and
skymap/energy-spectrum figure conventions.

## Combination papers

A combination merges published or approved results of several analyses or experiments; the statistics are
hep-statistics', the wording this skill's.

- List every input result with its reference, dataset and status; a preliminary input keeps its label in the
  combination.
- State the correlation assumptions per uncertainty source (fully correlated, uncorrelated, partially with the
  value used) and show how the result moves when they change; this is the part referees read first.
- Say who owns the numbers: the combined value comes from the combination's own fit (a `statistical-result`),
  not from averaging quoted values by hand.
- Give each input's weight or pull and the compatibility of the inputs (χ²/ndf or p-value), with the method named.

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

The four experimental types below have machine-readable content lists in `assets/paper-blueprints.json`;
`check_manuscript.py --blueprint TYPE` lists what a draft seems to lack (advisory, keyword-based; the exit code is
unchanged). An item cites the author guideline it was read from (APS PRL and PRD Information for Authors, the JHEP
author guidelines; read 2026-10-17) or says to-verify when it is field practice no guideline states. Length limits
are in `latex-venue-setup.md`, not repeated here.

## Search papers

The signal model or hypothesis; the selection; how each background is estimated (control regions, simulation,
data-driven) with its validation; a table of systematic uncertainties; observed and expected results side by side;
the statistical method and confidence level of limits or significances, with the look-elsewhere treatment when a
significance is quoted; where the numbers are available (HEPData or a repository, as JHEP asks for data files).

## Precision measurements

The definition of the measured quantity (fiducial region, phase space, units); the corrections (efficiency,
acceptance, unfolding) and their validation; a systematics table; the result with statistical and systematic
uncertainties quoted separately and their correlations when several values are given; the comparison with
predictions and with earlier measurements (PRD: state how the result corrects, supplements or supersedes earlier
ones).

## Instrumentation and performance papers

The detector, prototype or test setup; the performance figures with the conditions under which they hold (beam,
rate, temperature, configuration); the calibration and its stability; the uncertainties of the quoted performance;
what was measured as opposed to designed or simulated.

## Letters

PRL's structure: a title that conveys the main result, an abstract that summarizes it, an introduction that gives
the general reader the context, a central set of sections that establish the result, a concluding section; End
Matter (up to two pages) for specialists; a justification of the importance submitted with the paper. A PRD Letter
may be followed by a longer Regular Article. Run-in heads replace `\section` in PRL (`latex-venue-setup.md`).

**Done when:** the draft follows the genre's backbone and its genre-specific sections are present.

# Paper Structure

Detailed section-by-section guidance for the standard experimental-physics paper
backbone: Title, Abstract, Introduction, Methods, Analysis, Systematics, Results,
Summary. For how this backbone shifts for theory papers, review articles, thesis
chapters, proceedings, astroparticle/cosmic-ray papers, and statistics/ML papers,
see `paper-genre-variants.md`; for a plain-language public/outreach summary, see
`outreach-and-public-facing-summaries.md`. Read the relevant subsection rather
than the whole file when time-pressed.

## Table of contents
- [Title](#title)
- [Abstract](#abstract)
- [Abstract and title variants](#abstract-and-title-variants)
- [Argument restructuring](#argument-restructuring)
- [Introduction](#introduction)
- [Detector / Dataset / Methods](#detector--dataset--methods)
- [Analysis](#analysis)
- [Systematic uncertainties](#systematic-uncertainties)
- [Results](#results)
- [Summary / Conclusion](#summary--conclusion)

## Title

- States the *result*, not the method: "Measurement of the top-quark mass in
  ttbar events" beats "A study of ttbar events using kinematic reconstruction."
- Avoid acronyms unless they are field-standard (LHC, ATLAS is fine; a
  collaboration-internal acronym is not).
- No punctuation-heavy titles ("Results, revisited: a new look at...") for
  experimental papers; theory papers have more latitude.
- Keep it under ~15 words where the venue doesn't dictate otherwise.

## Abstract

The abstract is a self-contained paper in miniature. A referee, and most readers,
decide whether to keep reading based on this paragraph alone. Structure (roughly
one to two sentences each):

1. **Context** — what physics question, in one sentence, assuming an educated
   physicist reader but not a specialist in this exact sub-topic.
2. **What was done** — data source, method, in the fewest words that are still
   accurate ("Using 139 fb⁻¹ of pp collisions at √s = 13 TeV recorded by ATLAS...").
3. **The result** — the number, with uncertainty, and its statistical
   significance if relevant. This is the sentence people will quote.
4. **Significance / comparison** — how it compares to previous measurements or
   theory predictions, and why it matters.

Do not cite references in the abstract (most venues disallow it). Do not
introduce new terminology in the abstract that isn't defined in the main text.
Write the abstract *last*, after the results are final — it should never be
the place where a number is decided.

## Abstract and title variants

Use when asked to optimize a title/abstract or adapt it to a venue, audience, or
length limit. Establish the intended reader and constraints from the request;
verify current official venue rules when needed. Treat the generic conventions
above as defaults, not universal requirements. A methods paper can appropriately
foreground its method rather than a measurement.

Extract the factual core from the manuscript: question, approach, dataset/regime,
main result and uncertainty, and bounded implication. Preserve this core across
variants. If a result is missing, mark the missing input; do not invent a number or
convert a planned experiment into a completed one.

Produce meaningfully different variants only as useful or requested, such as one
for specialists and one for a broader scientific readership. Label the purpose
and give measured word/character counts when a limit applies, stating the counting
convention if ambiguous. Improve specificity and searchability with accurate field
terms, without keyword stuffing or claims of guaranteed discoverability.

Check each version against the Results and limitations: preserve qualifiers,
uncertainty conventions, tested scope, and the distinction between association
and causation or evidence and discovery. A shorter version may omit secondary
detail but must not broaden the conclusion. Recommend the version that fits the
stated constraints and explain any substantive wording tradeoff briefly.

## Argument restructuring

Use when a draft's logic or organization needs improvement. Build a reverse
outline: each paragraph/section's purpose, claim, evidence, and prerequisites.
Trace the central chain from question to method to result to interpretation using
`claim-evidence-mapping.md` when support is disputed, or
`logical-consistency-and-argument-uniformity.md` for a full diagnostic pass over
contradictions, fallacies, and dropped assumptions before restructuring.

Identify missing premises, circular reasoning, definitions introduced too late,
duplicated arguments, abrupt shifts, and conclusions broader than the evidence.
Distinguish a presentation gap from a missing analysis: rearranging text cannot
repair an unsupported scientific inference.

Propose a revised outline with each section's role and an old-to-new location map
for substantial moves. Put prerequisites before dependent claims while following
the target genre; a review, theory paper, and experimental report need different
structures. Preserve caveats beside the claims they qualify and avoid moving
essential evidence to supplements merely to simplify the narrative.

If editing is requested, make the structural changes, repair transitions and
cross-references, and preserve supported technical content and author voice.
Flag required evidence or author decisions rather than supplying invented bridges.
Deliver the revised draft/outline with a brief explanation of the consequential
moves and remaining logical gaps.

## Introduction

- Open with the physics motivation in 2-4 sentences: why does this measurement or
  calculation matter, aimed at a broad-but-expert reader.
- Summarize the state of the art: what has been measured/calculated before, with
  citations, and what its limitations were (precision, assumptions, energy regime).
- State explicitly what this paper adds that is new — do not make the reader infer
  it from the rest of the paper.
- End with a one-sentence roadmap only if the paper is long or has an unusual
  structure; for a 4-page PRL this is often unnecessary.
- Avoid a literature-review tone that reads as padding — every citation here should
  be doing work (establishing precedent, motivating the measurement, or setting up
  a comparison used later in Results).

## Detector / Dataset / Methods

- State the experiment/detector, the dataset (collision energy, integrated
  luminosity, run period), and any triggers or preselection, in enough detail that
  an expert in the field could judge whether the dataset is adequate — not enough
  to re-derive the detector design.
- For theory/phenomenology papers, this section becomes "Methods" or
  "Theoretical Framework": the model, approximations, and tools (generators,
  codes) used, with version numbers and citations.
- Cite the detector paper and any relevant Monte Carlo generator papers here, not
  scattered through the analysis section.

## Analysis

- Describe the event selection / calculation pipeline as a narrative, not a list
  of every cut ever tried — the reader needs the selection that produced the final
  result, plus enough of the *why* to trust it (e.g. "electrons are required to
  have pT > 25 GeV to suppress QCD background, as validated in Sec. X").
- State background estimation methods explicitly, including whether they are
  data-driven or simulation-based, and validate with a control region if one
  exists.
- Use a cutflow table when it clarifies rather than clutters — see
  `figures-and-tables.md`.
- Keep derivations that are standard (well-known formulas, standard fit
  functions) brief with a citation; reserve full derivation space for anything
  novel to this paper.

## Systematic uncertainties

- Organize by source (detector calibration, theoretical modeling, background
  estimation, luminosity, statistical) not by which cut they affect.
- State how each systematic was evaluated (envelope of variations, alternate
  generator comparison, data/MC scale factor uncertainty propagated) — "assigned
  as X%" without justification invites referee pushback.
- Summarize in a table (source → size → whether correlated across bins/channels)
  even if the accompanying text is short.
- Distinguish clearly, in both text and any result quoted, statistical vs.
  systematic uncertainty (e.g. `125.3 ± 0.4 (stat) ± 0.6 (syst) GeV`).

## Results

- Lead with the headline number, stated plainly, before any supporting plot
  discussion.
- Compare explicitly to the Standard Model prediction or the previous best
  measurement — state the pull/tension in standard deviations if that's the
  relevant metric, and avoid over- or under-stating significance (see
  `scientific-style.md` for phrasing conventions around "evidence" vs.
  "observation" vs. "excess").
- If there are multiple channels/bins, a summary figure (often the paper's
  Figure 1 candidate) usually communicates more than a results table alone —
  but include both if space allows.

## Summary / Conclusion

- Restate the result in one or two sentences, without new numbers not already
  given in Results.
- One sentence on implications (what this constrains or rules out) and,
  optionally, one on outlook (what would improve it — more data, next-gen
  detector). Do not oversell; referees notice.
- No new citations here except perhaps a forward pointer to planned/ongoing work.

For theory papers, review articles, thesis chapters, proceedings, and the
astroparticle/statistics-ML variants of this backbone, see
`paper-genre-variants.md`. For a plain-language public/outreach summary, see
`outreach-and-public-facing-summaries.md`.

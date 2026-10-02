# Scientific Style

Sentence- and paragraph-level guidance for physics prose. Most of this applies
to scientific writing generally; a few items are physics-specific conventions.

## Table of contents
- [Tense and voice](#tense-and-voice)
- [Hedging and precision](#hedging-and-precision)
- [Significance language](#significance-language)
- [Astroparticle-specific phrasing](#astroparticle-specific-phrasing)
- [Statistical and ML reporting language](#statistical-and-ml-reporting-language)
- [Sentence and paragraph shape](#sentence-and-paragraph-shape)
- [Common non-native-English pitfalls](#common-non-native-english-pitfalls)
- [Words and phrases to cut](#words-and-phrases-to-cut)

## Tense and voice

- **Past tense** for what was done in this analysis ("Events were selected
  requiring...", or active: "We selected events requiring...").
- **Present tense** for statements that remain true independent of when the
  paper was written: physical laws, the current state of the theory, and the
  paper's own stated conclusions ("The measured mass is consistent with...").
- Active voice ("We fit the distribution...") is now standard and preferred
  in most physics venues over passive ("The distribution was fit..."),
  though PRL/APS style has historically tolerated more passive
  construction. Follow the venue's existing papers if unsure, but default to
  active voice — it is shorter and clearer.
- Be internally consistent: don't alternate active/passive for the same kind
  of action within one section without reason.

## Hedging and precision

- Physics readers read hedges literally. "May suggest" and "could indicate"
  are appropriate for genuinely tentative results; do not use them as a
  reflexive softener for a result that is actually solid.
- Conversely, do not overstate: a 2σ excess is "an excess" or "a mild
  tension," not "evidence for" (conventionally ≥3σ) or "observation of"
  (conventionally ≥5σ) new physics. See the significance table below.
- Quantify wherever possible instead of hedging in words: "significantly
  larger" should become "34% larger" if the number is available.

## Significance language

Standard HEP convention (not universal, but widely expected by referees):

| Significance | Conventional language |
|---|---|
| < 2σ | "consistent with the background-only hypothesis"; do not call it an excess |
| 2–3σ | "an excess," "a mild/moderate tension" |
| 3–5σ | "evidence for" |
| ≥ 5σ | "observation of" |

State the exact significance number alongside the word, not instead of it
("a 3.4σ excess, corresponding to evidence for...").

The σ values are one-sided Gaussian tail probabilities: 3σ is p = 1.35 × 10⁻³ and
5σ is p = 2.87 × 10⁻⁷ (computed 2026-09-26). The 3σ/5σ thresholds are a field
convention, not a statistical law; L. Lyons, "Discovering the significance of 5
sigma", arXiv:1310.1284 (`Lyons:2013yja`), discusses why and when a different
threshold is argued for. Whenever a look-elsewhere effect applies (a scan over
mass, sky position, energy or time), the thresholds apply to the global
(post-trial) significance; always state which one is quoted. Collider searches
usually quote local and global side by side. Astroparticle point-source searches
say "pre-trial" and "post-trial" (see below).

## Astroparticle-specific phrasing

Extends the table above for astroparticle-physics and cosmic-ray writing (see
`astroparticle-and-cosmic-ray-papers.md` for the full treatment):

- Always state whether a quoted significance is **pre-trial or post-trial** when a
  search scanned more than one direction, energy bin, or source candidate — a bare
  "5σ" for a point-source search is ambiguous and referees will ask which.
- **"Exposure"** (area × solid angle × time, folding in geometric acceptance and duty
  cycle) is not interchangeable with **"livetime"** (raw observing time) — use the
  term that matches what the quoted uncertainty was actually derived from.
- Composition claims ("proton-dominated," "mixed composition") should name the
  hadronic-interaction model(s) used to infer them in the same sentence or the
  immediately following one — these inferences are model-dependent, and omitting the
  model reads as more certain than the result supports.

## Statistical and ML reporting language

The physics significance-language table above (σ-based, "evidence"/"observation")
doesn't transfer directly to statistics or ML writing, which has its own reporting
conventions (see `statistics-and-ml-papers.md` for the venue/process context this
phrasing sits inside):

- **"Statistically significant" is not the same claim as "practically
  meaningful."** A large sample size can make a tiny, unimportant effect reach
  `p < 0.05`; state the effect size (not just the p-value) alongside any
  significance claim, and say explicitly if a statistically significant effect is
  too small to matter for the paper's actual conclusion.
- **State the multiple-comparison correction applied**, if more than one
  hypothesis/metric was tested (Bonferroni, Holm, false-discovery-rate/Benjamini-
  Hochberg) — an uncorrected p-value reported alongside several other tests
  overstates significance the same way an uncorrected local significance does in
  physics (see the astroparticle pre-trial/post-trial convention above for the
  direct analogue).
- **Distinguish a confidence interval from a credible interval** explicitly when
  reporting either — "95% CI" defaults to the frequentist reading unless the paper
  is explicitly Bayesian, and conflating the two misstates what the interval
  actually means (mirrors the frequentist/Bayesian distinction
  `astroparticle-and-cosmic-ray-papers.md` and the physics literature draw for
  intervals generally).
- **Report variance across seeds/runs, not a single number**, for any ML result
  claiming an improvement — "we observe a 1.2% improvement" with no variance
  reported invites the same skepticism as an unstated systematic uncertainty in a
  physics measurement. State how many runs/seeds and what the spread was.
- **"Outperforms" is a comparison claim, not just a bigger number** — state
  whether the comparison used a matched compute/tuning budget (see
  `deep-learning`'s `../../physics-ml/references/ablation-and-design-review.md`); a claim of outperforming an
  under-tuned baseline should be phrased accordingly, not as an unconditional win.

## Sentence and paragraph shape

- One idea per sentence; if a sentence needs more than one comma-separated
  clause to state a single result, consider splitting it.
- Topic-sentence-first paragraphs: state the paragraph's point in the first
  sentence, then support it — physics referees skim, and a paragraph that
  buries its conclusion in the last sentence is easy to misread.
- Vary sentence length deliberately: a short sentence after several long ones
  gives a result room to land ("The excess is not observed in data.").
- Keep paragraphs to roughly 4-8 sentences in the main text; longer
  paragraphs in a length-limited Letter format are a sign the paragraph is
  doing two jobs and should split.

## Common non-native-English pitfalls

(Useful to check regardless of the author's first language — these show up
across many drafts.)

- **Article usage** ("a"/"the"/none): physics nouns for general categories
  usually take no article ("Background is estimated from..." not "The
  background is estimated..." when discussing backgrounds generally, but
  "The background *in this analysis*..." when specific). When unsure, prefer
  the more specific/definite reading if a specific instance is meant.
- **"Respectively" misuse**: only use when there is a clear one-to-one
  ordered correspondence already established in the same sentence.
- **Confusing "which" and "that"**: "that" for restrictive clauses (no
  comma), "which" for non-restrictive (with comma) — this changes meaning,
  not just style, in technical writing.
- **False friends in derived nouns**: "actual" (English: current/real) vs.
  cognates in other languages that mean "current news"; "eventually"
  (English: at some later point) vs. cognates meaning "possibly."
- **Overuse of "in order to"**: "to" alone is almost always sufficient and
  shorter.

## Words and phrases to cut

Common first-draft filler that rarely survives a careful edit — cutting these
typically saves 10-20% of word count with no loss of meaning:

- "It should be noted that...", "It is worth mentioning that..." → just state
  the fact.
- "In this paper, we...", repeated more than once → state it clearly once,
  usually at the end of the introduction.
- "Very," "quite," "fairly," "somewhat" as intensifiers on quantitative
  claims → replace with the actual number, or cut.
- "In order to" → "to".
- "Due to the fact that" → "because".
- Redundant pairs: "past history," "future plans," "completely eliminate,"
  "each and every" → drop the redundant word.

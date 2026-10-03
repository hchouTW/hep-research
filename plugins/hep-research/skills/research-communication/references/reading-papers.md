# Reading Papers

How to read a scientific paper efficiently and critically — whether skimming a daily
arXiv listing or working through a paper the user needs to reuse a method from.

## Table of contents
- [The three-pass method](#the-three-pass-method)
- [Separating claims from evidence](#separating-claims-from-evidence)
- [A critical-reading checklist](#a-critical-reading-checklist)
- [HEP-specific things to check](#hep-specific-things-to-check)
- [Astroparticle/cosmic-ray-specific things to check](#astroparticlecosmic-ray-specific-things-to-check)
- [Statistics/ML-specific things to check](#statisticsml-specific-things-to-check)
- [Reading at scale](#reading-at-scale)
- [Taking notes](#taking-notes)

## The three-pass method

Based on the widely-used approach for reading research papers efficiently (Keshav,
"How to Read a Paper"). Most papers only need pass one; go further only as relevance
justifies the time.

**Pass 1 (~5–10 minutes) — decide if it's worth reading further.**
Read the title, abstract, section headings, and conclusion. Glance at the figures.
Skim the reference list for familiar names/venues. After this pass you should be able
to answer: what category of paper is this (measurement, theory calculation, method
paper, review)? Is it relevant to the current task? Is it worth a deeper read now, or
worth bookmarking for later? Do not attempt to understand the method in detail yet.

**Pass 2 (~30–60 minutes) — grasp the content, not every detail.**
Read the paper more carefully, but skip proofs/derivations on a first pass through
them — note the assumptions and the result, not necessarily every algebraic step.
Look closely at figures and tables: identify axes, units, and what a "good" result
looks like on that plot — see `interpreting-scientific-graphics.md` for reading
specific plot types correctly (exclusion contours, corner plots, ROC curves, and
others) and spotting a misleading axis choice or an unstated significance
convention. Note unfamiliar references worth chasing later. After this
pass you should be able to summarize the paper's contribution, method, and result to
someone else in a few sentences, and should know whether a full pass-3 read is needed.

**Pass 3 (multiple hours) — reimplementation-level understanding.**
Needed only when the user will build directly on this paper's method (reproducing it,
extending it, or critiquing it in detail). Work through derivations, re-derive results
where feasible, identify every assumption and where it could break down, and note
what's unclear or seems questionable. This pass often surfaces the paper's actual
weaknesses — vague experimental setup, an assumption stated but never justified, a
comparison baseline that isn't quite fair.

## Separating claims from evidence

The single most common reading error is treating "the paper says X" as equivalent to
"X is well-supported." Keep these visibly distinct, in notes and in any summary given
to the user:

- **Claim** — what the paper asserts, in its own words or a close paraphrase.
- **Evidence** — the specific data, calculation, or experiment that's supposed to
  support the claim, and how directly it does so.
- **Gap** — anywhere the evidence is weaker than the claim's phrasing suggests (a
  single benchmark generalized to "state of the art"; a 2σ excess described in
  language that implies more certainty than that).

This separation matters most when the user will cite the paper's claim in their own
work — cite what the evidence actually supports, not the paper's most confident
phrasing of it.

## A critical-reading checklist

- **Comparison baselines**: are they current and fairly tuned, or an outdated/
  under-tuned strawman that makes the paper's method look better than it is?
- **Statistical rigor**: are uncertainties reported (not just point estimates)? Is
  significance/effect size distinguished from a raw p-value? For a small
  sample/dataset, is that acknowledged as a limitation?
- **Reproducibility**: is code and/or data available? Are hyperparameters,
  preprocessing steps, and random seeds specified well enough to reproduce the
  central result?
- **Generalization**: is the result validated on more than one dataset/regime, or
  does it risk being an artifact of one specific setup?
- **Stated vs. actual scope**: does the introduction/abstract's framing match what
  the experiments/derivation section actually shows, or does the paper's title/
  abstract overreach beyond its own results?
- **Funding/conflicts of interest**: relevant mainly when a result has direct
  commercial implications; usually a non-issue in HEP but worth a glance for
  detector-vendor or industry-adjacent work.

## HEP-specific things to check

- **Dataset and luminosity**: which run period, what collision energy, how much
  integrated luminosity — a result on 36 fb⁻¹ and one on 139 fb⁻¹ of the same
  channel are not directly comparable without accounting for that.
- **Blinding**: was the analysis blinded (signal region hidden until the method was
  frozen)? Papers that skip this for a search are more vulnerable to
  look-elsewhere-effect-style bias, even unintentionally.
- **Look-elsewhere effect**: for any reported local significance, check whether a
  global significance (accounting for the number of places an excess could have
  appeared) is also quoted — a "3σ local" excess is often much less significant
  globally. See `../../hep-statistics/references/statistical-inference-for-physics.md`'s frequentist-inference
  section for the actual trials-correction/global-significance check.
- **Systematics treatment**: are systematic uncertainties itemized by source (not
  just a single lumped number), and is it clear how they were evaluated (data-driven
  vs. simulation-based)? See `../../hep-statistics/references/statistical-inference-for-physics.md`'s systematic-
  uncertainty section for what "accounted for" should actually mean (nuisance
  modeling, correlation, propagation) before accepting the itemized list at
  face value.
- **Cross-checking numbers**: for headline measurements, check whether the quoted
  value and its context are consistent with the corresponding PDG (Particle Data
  Group) average or HEPData record, when relevant — a large unexplained tension with
  the existing world average is worth flagging, not silently accepting.

## Astroparticle/cosmic-ray-specific things to check

- **Exposure and livetime**: stated explicitly, and consistent with the
  instrument's/array's known operating history for the quoted period?
- **Trials factor**: for a point-source or anisotropy search, is a post-trial
  (global) significance given alongside the pre-trial number — the same
  look-elsewhere-effect concern as collider searches, but easy to miss since the
  "trials" here are sky positions or energy bins rather than mass bins. See
  `../../hep-statistics/references/statistical-inference-for-physics.md`'s frequentist-inference section for the
  actual trials-correction/global-significance check.
- **Hadronic-interaction-model dependence**: for shower-based composition results, is
  the model-dependence of the conclusion itself discussed (not just shown as a
  systematic-uncertainty band with no comment on whether the qualitative conclusion
  survives a different model choice)?
- **Solar-cycle/epoch context**: for a direct-detection flux result below ~30
  GeV/nucleon, is the solar activity period stated, and relevant to any comparison
  drawn against another experiment's data from a different epoch?

See `astroparticle-and-cosmic-ray-papers.md` for how these interact with the paper's
structure and figures, not just what to check while reading.

## Statistics/ML-specific things to check

- **Baseline fairness**: are baselines tuned to a comparable degree as the
  proposed method, or is the comparison against an under-tuned baseline from an
  older paper?
- **Statistical significance across seeds/splits**: is a reported improvement
  backed by multiple seeds/runs with a variance estimate, or a single run that
  could be seed noise?
- **Train/test contamination**: for a public benchmark or a pretrained model, is
  there a check that the test set didn't leak into pretraining or fine-tuning
  data? See `../../hep-computing/references/numerical-and-computational-methods.md`'s computational-experiment-
  design section for the general circular-validation pattern this is one
  instance of.
- **Code/data availability**: is the result actually reproducible from what's
  released, or does the paper claim reproducibility while withholding a
  load-bearing detail?
- **Effect size vs. statistical significance**: is a statistically significant
  effect also practically meaningful, or just detectable because of a very large
  sample size?

See `statistics-and-ml-papers.md` for how these interact with the paper's
structure, venue, and review process, not just what to check while reading.

## Reading at scale

For staying current rather than deep-reading one paper:
- Triage an arXiv daily listing or INSPIRE-HEP alert with pass 1 only, for every
  entry; most will be filtered out at this stage.
- Keep a lightweight backlog (a list of titles/arXiv numbers with a one-line reason
  they were flagged) rather than trying to fully process everything in real time.
- When several flagged papers turn out to be relevant to the same question, that's
  the trigger to move into `literature-review.md`'s comparison-matrix workflow rather
  than reading each in isolation.

## Taking notes

Use `../assets/paper/reading-notes-template.md` as a starting shape for structured
notes on a single paper: claim, method, evidence, limitations, and relevance to the
user's own work. Notes taken in this shape during pass 2/3 are directly reusable
later — as the raw material for a literature-review comparison matrix
(`${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py`), or as accurately-sourced material for a related-work
paragraph — in a way that a vague memory of "a paper that did something like this" is
not.

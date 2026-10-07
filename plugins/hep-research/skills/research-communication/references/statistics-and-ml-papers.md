# Statistics and Machine-Learning Papers

How writing and reading conventions shift for statistics and machine-learning
papers — from applied/theoretical statistics journals (JASA, Annals of Statistics,
Biometrika, JRSS-B) to ML/AI conferences (NeurIPS, ICML, ICLR, AAAI, CVPR/ICCV/ECCV)
and NLP venues (ACL, EMNLP, NAACL) and their journal counterparts (JMLR, TMLR). This
file covers the *writing/venue/citation/review-process* differences; the actual
statistical or ML rigor behind a claim (matched compute budgets, seed variance,
ablations that isolate a mechanism, proving an improvement is real rather than
noise) is `physics-ml`'s domain — see its `../../physics-ml/references/ablation-and-design-review.md` and
`../../physics-ml/references/evaluation-strategy.md` for that content. Everything below assumes the analysis is
already done and correct, and focuses on how to write it up and get it through
review.

## Table of contents
- [How the structure differs from a physics paper](#how-the-structure-differs-from-a-physics-paper)
- [Venue landscape](#venue-landscape)
- [Author contribution statements](#author-contribution-statements)
- [Citations: arXiv-first culture](#citations-arxiv-first-culture)
- [Reproducibility checklists and artifacts](#reproducibility-checklists-and-artifacts)
- [Peer review mechanics](#peer-review-mechanics)
- [Reading checklist additions](#reading-checklist-additions)

## How the structure differs from a physics paper

The section-by-section backbone in `paper-structure.md` (Introduction → Methods →
Results → Discussion) still applies loosely, but several sections are specific to
this field, and some are outright required by the venue rather than optional:

- **Related Work** is usually its own section, placed either right after the
  Introduction or just before the Conclusion — unlike a physics paper, which
  typically weaves prior measurements into the Introduction itself. Check the
  venue's own recent accepted papers rather than assuming a fixed position.
- **Limitations** is a required, explicitly-labeled section at several venues
  (NeurIPS, ACL) rather than a closing paragraph folded into the conclusion — state
  concretely what the method doesn't handle, not a generic "future work" hand-wave;
  reviewers are instructed to check for this section and penalize a missing or
  vacuous one.
- **Broader Impact / Ethics Statement** is a required section at NeurIPS and
  several other venues, distinct from Limitations: it addresses societal
  consequences (misuse potential, fairness, environmental cost of compute) rather
  than technical shortcomings. Do not merge the two - reviewers and area chairs
  check for both separately.
- **Reproducibility** is usually a required checklist (see below), often submitted
  as a separate form rather than prose in the paper itself, plus a "Reproducibility
  Statement" section at some venues (ICLR) that summarizes what's included to
  support reproduction (code, data, hyperparameters, compute).
- **Supplementary material / Appendix** carries far more real content than a
  physics paper's supplemental material: full hyperparameter tables, additional
  experiments/ablations that didn't fit the page limit, proofs for a theory paper,
  and licensing/compute statements for datasets and models used. Reviewers are
  expected to read the appendix during review at most of these venues (unlike a
  journal, where supplementary material is often optional for the referee).
- **Statistics-journal papers** (JASA, Annals of Statistics, Biometrika, JRSS-B)
  follow a more classical theorem/proof structure closer to a math paper: an
  applied-statistics paper still has Introduction/Method/Simulation study/Real-data
  application/Discussion, but a theoretical-statistics paper is often Introduction
  → Assumptions → Theorem statements → Proof sketches (full proofs in an appendix)
  → Simulation study validating finite-sample behavior → Discussion.

## Venue landscape

Unlike physics, where PRL/PRD/JHEP are all journals with a broadly similar
multi-round referee process, ML/AI publishing is dominated by conferences with a
fundamentally different review cycle (see "Peer review mechanics" below):

| Venue type | Examples | Review process | Notes |
|---|---|---|---|
| ML/AI conferences | NeurIPS, ICML, ICLR, AAAI | OpenReview (ICLR, and NeurIPS since recent years), single-shot with one author-rebuttal window, area chairs and meta-reviews, hard camera-ready deadline | Acceptance is final at notification; no further revision rounds like a journal |
| Computer vision conferences | CVPR, ICCV, ECCV | Similar single-shot cycle, often double-blind with a separate rebuttal PDF | Page limits strictly enforced; supplementary material often unlimited length |
| NLP venues | ACL, EMNLP, NAACL | ACL Rolling Review (ARR): review happens on a rolling basis, decoupled from a specific conference deadline, and a paper can be resubmitted with reviews carried over | Different cadence from the single annual-cycle conferences above |
| ML journals | JMLR, TMLR | Journal-style: no strict page limit, open review (TMLR), can take multiple revision rounds like a physics journal | Closer to the physics-journal model than the conferences above |
| Statistics journals | JASA, Annals of Statistics, Biometrika, JRSS-B | Traditional multi-round peer review, often slow (many months to over a year) | Closest in process to PRD/JHEP; class files are typically plain LaTeX (`article`) or a light journal style, not a heavily branded class like REVTeX |

Class files/templates: NeurIPS, ICML, ICLR, and AAAI each publish a `.sty` file for
the specific year's conference (these change yearly — always pull the current
year's official template rather than reusing last year's, since margins/fonts/
section-numbering rules are enforced by an automated formatting checker at several
of these venues). ACL/EMNLP/NAACL share a common ACL Anthology style file. JMLR/TMLR
have their own LaTeX templates. Statistics journals rarely mandate a specific class
file — check the specific journal's author guidelines.

## Author contribution statements

Explicit author-contribution statements are far more common here than in a physics
paper (where the collaboration author-list convention dominates instead — see
`astroparticle-and-cosmic-ray-papers.md`):

- **CRediT taxonomy** (Conceptualization, Methodology, Software, Validation, ...)
  is increasingly requested by journals (including statistics journals) as a
  structured contribution statement, distinct from free-text acknowledgments.
- **Equal-contribution footnotes** (`*`/`†` marking two or more authors who
  contributed equally, usually the first two or three) are the norm in ML papers
  with multiple co-first-authors — get this from the user rather than guessing who
  should be marked, since it has real credit implications.
- A **corresponding author** is usually named explicitly (email in the affiliation
  footnote), same as most journals, but less uniformly enforced at conference
  venues than at journals.

## Citations: arXiv-first culture

ML/AI research moves fast enough that arXiv preprints, not the eventual conference
proceedings version, are frequently the version actually cited and read:

- **A large fraction of the field's own citations are to arXiv preprints that were
  never separately published**, or where the arXiv version and the camera-ready
  conference version differ non-trivially (the arXiv version often gets updated
  after the conference with additional experiments). State which version is being
  cited if it matters to the point being made.
- **Bibliography sources**: arXiv's own BibTeX export, **DBLP** (`dblp.org`,
  strong for conference proceedings, has a clean per-paper BibTeX export with a
  stable key), **ACL Anthology** (`aclanthology.org`, the canonical source for
  NLP-venue papers, with its own BibTeX export), and **Semantic Scholar** (API and
  web export, good for citation graphs and quickly finding a paper's canonical
  venue). None of these plays the singular canonical role INSPIRE-HEP or ADS play
  in physics — which source to use depends on where the paper was actually
  published (DBLP/venue-specific for a published proceedings paper, arXiv for a
  preprint with no other record).
- **Citation style**: numbered citations are standard at ML/AI conferences
  (`natbib` numbered or a conference-specific `.bst`); ACL-family venues use
  `\citep`/`\citet` author-year via a shared ACL style file. Statistics journals
  vary by title, similar to physics journals - check the specific venue.
- **Versioned preprints**: cite a specific arXiv version number (`v1`, `v2`, ...)
  if the point being made depends on content that changed between versions - arXiv
  preprints are mutable in a way a published paper is not.

## Reproducibility checklists and artifacts

- **The NeurIPS paper checklist** (a required submission component, not optional
  prose) asks, per-claim, whether experimental results are reproducible from what's
  provided: code availability, data availability and licensing, compute resources
  used, hyperparameters, number of seeds/runs and how variance was reported, and
  whether the paper's claims match what the experiments actually show. Treat it as
  a real accountability document, not a formality - reviewers cross-check specific
  boxes against the paper's actual content.
- **ACM/IEEE artifact evaluation badges** (Available / Functional / Reusable, or
  similar) apply mainly to systems-adjacent ML venues; they're a separate,
  independently-reviewed submission (the code/data repository itself), not just a
  statement in the paper.
- **Model cards and dataset datasheets** are the field's standard structured
  documentation for a released model or dataset respectively (intended use,
  training data provenance, known limitations/biases, evaluation results by
  subgroup where relevant) - increasingly expected as supplementary material
  alongside a paper that releases either.
- **Code and data release** is the norm, not the exception, at these venues -
  state clearly in the paper (a footnote or a dedicated "Code availability"
  sentence) where the repository lives, mirroring the supplemental-data-linking
  practice already described in `citations-and-bibliography.md`.

## Peer review mechanics

This differs enough from a physics journal's referee process
(`submission-and-peer-review.md`) to call out explicitly:

- **Single-shot rebuttal, not a multi-round revision.** A journal referee report
  gets a full revision and a new round of review; an ML conference gives one
  author-response window (often just a few days, with a strict word/character
  limit) to respond to the initial reviews, after which reviewers may update their
  scores but there is no further back-and-forth before the accept/reject decision.
  Write the rebuttal accordingly: address every reviewer's concerns concretely and
  concisely in the space given, prioritize points that could flip a borderline
  score, and don't promise a revision that can't actually be delivered before the
  camera-ready deadline.
- **Public reviews on OpenReview** (ICLR, and increasingly others) mean the review
  text, rebuttal, and often reviewer identities-to-the-public-after-decision are
  visible - write the rebuttal knowing it's a public record, not a private letter
  to an editor.
- **Area chairs and meta-reviews** sit between the reviewers and the final
  decision, and weigh reviewer confidence/reviews holistically rather than
  averaging scores mechanically - a rebuttal that changes one reviewer's mind can
  matter even if the numeric scores don't move much.
- **Camera-ready deadlines are hard and typically non-negotiable** - unlike a
  journal's more flexible production schedule, a missed camera-ready deadline can
  mean the paper doesn't appear in the proceedings at all.
- **ACL Rolling Review (ARR)** decouples review timing from any specific
  conference: a paper can be reviewed, revised, and resubmitted to a later
  conference cycle with the same reviews carried forward - closer to a journal's
  revision model than the single-shot conferences above.

## Reading checklist additions

When reading someone else's statistics or ML paper, extend `reading-papers.md`'s
critical-reading checklist with:

- **Baseline fairness**: are baselines tuned to a comparable degree as the
  proposed method (same compute/search budget), or is the comparison against an
  under-tuned baseline from an older paper? See `physics-ml`'s
  `../../physics-ml/references/ablation-and-design-review.md` for the full treatment of matched-budget
  comparisons.
- **Statistical significance across seeds/splits**: is a reported improvement
  backed by multiple seeds/runs with a variance estimate, or is it a single run
  that could be seed noise? A single strong number with no variance reported is a
  red flag, not a formality being skipped.
- **Train/test contamination**: for anything using a public benchmark or a
  pretrained model, is there a check that the test set (or something derived from
  it) didn't leak into pretraining or fine-tuning data? See
  `../../hep-computing/references/numerical-and-computational-methods.md`'s computational-experiment-design
  section for the general circular-validation pattern this is one instance of.
- **Code/data availability**: is the result actually reproducible from what's
  released, or does the paper claim reproducibility while withholding a
  load-bearing detail (a specific hyperparameter, a data preprocessing step, a
  proprietary dataset)?
- **Effect size vs. statistical significance**: for a paper reporting p-values or
  confidence intervals, is the effect itself practically meaningful, or is a tiny
  effect being reported as significant only because of a very large sample size?
  See `scientific-style.md`'s statistical-reporting-language section for the
  phrasing conventions this implies.

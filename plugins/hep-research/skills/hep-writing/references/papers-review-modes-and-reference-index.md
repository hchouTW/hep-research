# Academic papers: review modes and reference index

Moved verbatim from [the papers guide](academic-papers-guide.md) (upgrade plan B-03), which keeps the method: read
it first, then the section here that the task needs.

## Focused verification and review modes

Use these when requested or needed to substantiate claims — not for an ordinary summary. Literature lookups, citation
verification, primary sources and systematic-review screening are hep-literature's modes: its
[literature guide](../../hep-literature/references/literature-guide.md#reference-files).

**Verification and auditing**
- **Collaboration results lifecycle** — internal note, approved preliminary (CONF note/PAS), paper, proceedings; what is citable at each stage, approved plots, review rounds and the frozen-number sign-off record: `collaboration-results-lifecycle.md`
- **Physics plots** — status labels on figures, ratio panels and bands, fonts and vector output, colour and raster resolution, cosmic-ray flux and neutrino figure conventions: `physics-plots.md`
- **Reproducibility auditing** — trace results to methods/data/code/config/execution evidence; distinguish documentation inspection from an actual rerun (hand execution to `hep-computing`; what a rerun's number means to `hep-statistics`, `hep-measurement` or `hep-ml` as the question demands): `reproducibility-auditing.md`
- **Code review report** — paper-to-code alignment, documentation, packaging, severity-ranked findings; distinct from reproducibility auditing, delegates by the question: implementation to `hep-computing`, statistical treatment to `hep-statistics`, measurement design to `hep-measurement`, ML rigor to `hep-ml`: `code-review-report.md`
- **Equation and notation auditing** — definitions, dimensions, index/shape consistency, assumptions, derivation steps: `equation-and-notation-auditing.md`
- **Mathematical reasoning and proof status** — soundness of assumptions vs. claimed proof status (formal/analytic/perturbative/asymptotic/heuristic/numerical/empirical/conjecture): `../../hep-theory/references/mathematical-reasoning-and-proof.md`
- **Statistical inference for physics** — correctness of a likelihood/test/interval/limit vs. the stated conclusion: `../../hep-statistics/references/statistical-inference-for-physics.md`
- **Numerical and computational methods** — whether a numerical/computational result is validated (convergence, stability, independent cross-check), not just run: `../../hep-computing/references/numerical-and-computational-methods.md`
- **Claim–evidence mapping** — connect claims to results/derivations/citations, flag unsupported generalizations: `../../hep-literature/references/claim-evidence-mapping.md`
- **Logical consistency and argument uniformity** — cross-section contradictions, dropped assumptions, fallacious inference, definitional drift: `logical-consistency-and-argument-uniformity.md`
- **Manuscript consistency auditing** — reconcile repeated results, uncertainty conventions, dataset descriptions, conclusions: `manuscript-consistency-auditing.md`
- **Plagiarism and text-reuse checking** — copied/paraphrased text vs. legitimate quotation, self-citation, boilerplate: `plagiarism-and-text-reuse-checking.md`

**Assessment and restructuring**
- **Reviewer-style assessment** — contribution, validity, comparisons, actionable concerns: `reviewer-style-assessment.md`
- **Research-gap and novelty assessment** — compare the contribution to verified close prior work: novelty-assessment section of `../../hep-literature/references/literature-review.md`
- **Scientific argument restructuring** — missing logical steps, reordering around evidence: argument-restructuring section of `paper-structure.md`
- **Abstract and title optimization** — accurate variants for an audience/venue/length limit: abstract-and-title-variants section of `paper-structure.md`
- **Supplementary-material planning** — allocate derivations/checks/artifacts between main paper and supplements: `supplementary-material-planning.md`

**Tracking and cross-version reconciliation**
- **Revision-impact tracking** — trace changed results/reviewer requests through manuscript artifacts and response letters: `revision-impact-tracking.md`
- **Preprint-to-journal reconciliation** — diff preprint vs. published version, identify substantive differences: `preprint-to-journal-reconciliation.md`
- **Multi-venue reformatting** — adapt one manuscript across two venues (conference/journal extension, letter/full-paper companion): `multi-venue-reformatting.md`
- **Comment/Reply exchange** — draft a formal post-publication Comment or Reply: `comment-and-reply-exchange.md`
- **Erratum and corrigendum drafting** — classify and draft a correction notice: `erratum-and-corrigendum-drafting.md`

**Disclosure and compliance statements**
- **Data and code availability statements** — verified repos, versions, restrictions, missing artifacts: availability-statements section of `citations-and-bibliography.md`
- **Authorship and contribution statements** — organize supplied contributions/acknowledgments/disclosures, don't infer credit or author order: authorship-and-contributions section of `submission-and-peer-review.md`
- **Conflict-of-interest and ethics statements** — COI, funding, IRB/ethics-approval, consent statements: `conflict-of-interest-and-ethics-statements.md`
- **Accessible scientific communication** — figure descriptions and visual-encoding checks: accessible-descriptions section of `figures-and-tables.md`

## Reference files

Read these as needed — don't load them all up front unless doing a full draft or
review. Grouped by function; within a group, order roughly follows the workflow.

**Reading and discovery**
- hep-literature's [literature guide](../../hep-literature/references/literature-guide.md#reference-files): finding,
  reading and reviewing papers, reading others' figures, literature matrices

**Structure, venue, and formatting**
- `paper-structure.md` — section-by-section guidance for the standard
  experimental-physics backbone (Title through Summary/Conclusion), what a
  referee expects in each section
- `paper-genre-variants.md` — how that backbone shifts for theory
  papers, review articles, thesis chapters, and proceedings, plus pointers to
  the dedicated astroparticle and statistics/ML variant files
- `outreach-and-public-facing-summaries.md` — writing a
  plain-language public/outreach summary, and telling apart collaboration-voice
  outreach from syndicated third-party commentary (a journalist's recap, an
  APS Synopsis, an APS Viewpoint)
<!-- example: experiment-specific illustration -->
- `astroparticle-and-cosmic-ray-papers.md` — how structure, venues,
  author lists, citations, figures, and phrasing shift for astroparticle-physics
  and cosmic-ray papers (ground arrays, IACTs, neutrino observatories, space-based
  direct detection): exposure vs. luminosity, arrival-direction/anisotropy sections,
  JCAP/ApJ/Astroparticle Physics venues, ADS/bibcode citations, skymap conventions,
  and how to check a collaboration's publication pattern (venue mix, arXiv practice,
  author lists, off-journal data tables, web-only notes, highlight-page bylines)
<!-- /example -->
- `statistics-and-ml-papers.md` — how structure, venues, author-
  contribution statements, citations, and review process shift for statistics and
  machine-learning papers: required Limitations/Broader-Impact sections,
  reproducibility checklists and artifacts (model cards, datasheets), NeurIPS/
  ICML/ICLR/AAAI/ACL-family/JMLR/TMLR/statistics-journal venue landscape,
  arXiv-first citation culture (DBLP, ACL Anthology, Semantic Scholar), and
  single-shot OpenReview rebuttals vs. a journal's multi-round revision
- `latex-venue-setup.md` — REVTeX/JHEP/Springer/JCAP/AASTeX/
  Elsevier/NeurIPS/ICML/ICLR/ACL/JMLR venue-specific setup and skeletons,
  arXiv-specific rules, units/equation conventions, common compile errors,
  length-limit tricks
- `latex-mechanics-and-tooling.md` — cross-cutting LaTeX
  mechanics that apply regardless of venue: cross-referencing (`cleveref`)
  and `\newcommand` notation macros, `siunitx`/`multirow`/`longtable` table
  syntax, tagged-PDF accessibility, `latexdiff` tracked-changes diffing,
  `latexmk` build automation, bibtex-vs-biber/biblatex engine choice,
  `\include`/`\includeonly` multi-file document structuring, and non-ASCII
  author-name encoding

**Prose, figures, and citations**
- `figures-and-tables.md` — plot design for publication (following on from
  ROOT/matplotlib output made under `hep-measurement`), caption writing, table
  conventions, skymap/cosmic-ray-spectrum figures, and learning-curve/ablation/
  leaderboard tables
- `citations-and-bibliography.md` — BibTeX hygiene, managing a personal reference library
  (Zotero/JabRef) across papers/projects, citation style by venue, linking
  supplemental material/data, citing an accompanying Viewpoint or Synopsis
  separately from the primary paper, avoiding orphaned/duplicate entries
- `scientific-style.md` — sentence-level prose guidance: tense, voice,
  hedging, common non-native-English pitfalls, physics-specific,
  astroparticle-specific, and statistical/ML-specific (p-values, effect sizes,
  multiple-comparison correction) phrasing conventions

**Submission and peer review**
- `submission-and-peer-review.md` — pre-submission checklist, cover
  letters, referee response structure, revision tracking, collaboration internal
  review, arXiv submission mechanics (licence, ancillary files, replacements;
  collaborations that skip arXiv entirely), desk rejections, editor queries and
  transfer offers, and single-shot conference rebuttals

**Verification, assessment, tracking, and disclosure**
- Covered above under `## Focused verification and review modes`, which lists
  each mode's trigger and reference file (citation verification and systematic-review
  screening are hep-literature's): reproducibility auditing, code review, equation/notation auditing,
  mathematical reasoning, statistical inference, numerical methods, claim-evidence
  mapping, logical consistency, manuscript consistency, plagiarism checking,
  reviewer-style assessment, research-gap/novelty, argument restructuring,
  abstract/title optimization, supplementary-material planning, revision
  tracking, preprint-journal reconciliation, multi-venue reformatting,
  Comment/Reply, erratum drafting, and availability/authorship/COI/accessibility
  statements.

**Adjacent document types**
- `poster-and-talk-design.md` — re-laying-out a paper's results
  for a conference poster (viewing-distance figures, walkable panel order)
  or a slide deck (one-idea-per-slide, matching depth to slot length)
- `preregistration-and-registered-reports.md` — writing a
  preregistration or a registered report's Stage 1/Stage 2, keeping
  confirmatory and exploratory analyses distinguishable
- `artifact-packaging-for-release.md` — preparing the user's own
  code/data repository for public release (README, pinned environment,
  license, verified end-to-end reproduction), as the writing-side
  counterpart to `reproducibility-auditing.md`
- `grant-and-fellowship-proposal-writing.md` — Specific Aims/
  research-statement structure, preliminary-results vs. proposed-work
  separation, broader-impacts sections, and budget-justification handling
  for a grant or fellowship proposal (a distinct genre from a paper)
- `thesis-by-publication-assembly.md` — assembling a thesis from
  the user's own already-published papers: institutional requirements,
  copyright/reuse permissions, connective-material synthesis, per-chapter
  contribution statements, and cross-paper inconsistency reconciliation
- `code-to-methodology-synthesis.md` — reverse-engineering
  research/algorithmic source code with no existing paper (not generic
  software with no mathematical content) into a Methodology + Technical
  Manual document: codebase dissection, math/algorithm reconstruction,
  two-part synthesis; delegates correctness verification by the question
  (`hep-computing`, `hep-statistics`, `hep-measurement`, `hep-ml`); template skeleton in
  `../assets/paper/code-to-methodology-manual-template.md`

**Done when:** the review mode or topic file the task needs has been chosen from this index and read; the method stays in the papers guide.

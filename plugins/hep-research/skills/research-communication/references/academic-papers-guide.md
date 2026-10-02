# Academic Papers (guide)

## When to read this file

This file is the migrated routing and rules of the legacy `academic-papers` skill (agentic-ai-skills@3e995a4). Read it when a research-communication task falls in its scope; the reference files it routes to are linked relative to this file.

A skill for the full lifecycle around scientific papers: reading and critically
understanding one or many papers, synthesizing them into a literature review or a
paper's own related-work section, and then drafting, formatting, and submitting a
manuscript of your own. It is written with physics conventions front and center —
collider/high-energy-physics (HEP) and astroparticle physics/cosmic-ray science
(ground-based air-shower arrays, imaging Cherenkov telescopes, neutrino
observatories, space-based direct detection), plus statistics and machine-learning
publishing conventions (NeurIPS/ICML/ICLR/ACL-family conferences, JMLR/TMLR,
statistics journals) — but the reading strategies, prose guidance, and structural
conventions apply to scientific writing generally.

Pairs well with `hep-analysis` (the physics content: cutflows, fits, systematics,
limits, and — for the astroparticle side — spectrum/composition/anisotropy analysis
and astroparticle statistics) and `physics-ml` (the ML/statistical rigor itself:
ablations, seed variance, matched-budget comparisons, evaluation-harness design —
not just a methods section to read through). This skill owns the *reading and
writing*, not the analysis itself — if the user still needs to run a fit, produce a
limit, prove an improvement is real, or debug a plot, hand that off to
`hep-statistics` or `physics-ml` first.

## Rules for every task

These override anything later in this file. Weaker models skip references, so they
are stated here in full.

1. **No invented facts or citations.** Never output a citation key, DOI, arXiv ID,
   page range or BibTeX entry you have not verified in this session; give a lookup
   route (INSPIRE-HEP/ADS/arXiv query) or mark it `[CITATION NEEDED: ...]`. Do not add
   trial counts, "standard" systematic breakdowns, validation studies or uncertainties
   the source or user did not give; say they are missing.
2. **No computed statistical results.** A limit, significance, fit value or interval
   the user did not supply is analysis output: hand it to `hep-statistics`
   (pyhf/Combine/RooStats) or `physics-ml`, and write `[VALUE NEEDED: 95% CL CLs
   limit]`. Reading a plotted value is fine if labeled approximate (see
   `interpreting-scientific-graphics.md`). A back-of-envelope result, if
   given at all, is labeled approximate with its method and what it ignores. The
   reporting sentence still names the method: confidence level and construction
   (CLs, Feldman-Cousins), asymptotic or toys, and how each uncertainty enters
   (e.g. "the background uncertainty is included as a constrained nuisance
   parameter"); use a placeholder for any choice not yet made. **Never estimate a
   σ, limit or fit value from a plot or a ratio panel, not even roughly.**
3. **Calibrate claims to the evidence.** "Evidence" needs ≥ 3σ and "observation"
   ≥ 5σ; whenever a look-elsewhere effect applies (a scan over mass, sky position,
   energy or time), use the global (post-trial) significance, and always say which
   one is quoted. If a claim is stronger than its source, say so and propose the
   weaker wording explicitly, rather than silently softening it.
4. **Check the citation actually says it.** A number attributed to a paper must be
   the number that paper reports (a later combination or a PDG average is a different
   source). If what you know suggests a mismatch (a precision too good for the cited
   paper's dataset, or a value you recognize from a later combination), say so
   plainly and name the likely source, marked "to verify". Rule 1 forbids inventing
   references, not flagging a probable error. Never call an unchecked number "looks
   right" or "safe to use".
5. **Compare like with like.** Before comparing values across papers, check quantity
   and unit (energy in GeV vs. rigidity in GV, per-nucleon vs. total, local vs. global
   significance, 68% vs. 95% CL) and flag needed conversions.
6. **Referee replies are drafted text.** Thank the referee, concede what is valid,
   answer with the user's own numbers, state exactly what changed in the manuscript,
   stay courteous even to a hostile comment, and never call a criticized choice
   "validated" unless the user said so. Commit to one concrete response (a specific
   revision, or an explicit reasoned decline) rather than a menu of options, and do not compare the effect to other uncertainties the user
   has not given ("well below the statistical precision"). If the user supplied the
   result, draft the reply now instead of asking which stance to take; put any
   missing fact in a `[VALUE NEEDED: ...]` slot. Minimal shape: "We thank the referee.
   We agree that <point>. We have now <change>, which changes <result> by <the
   user's number>. Section <N> now reads: '<new text>'." Fill it only with facts the
   user gave.
7. **Methodology from code describes only the code.** Say what it computes (binned vs.
   unbinned, what is fitted, what is fixed) and list what it does not (intervals,
   nuisance parameters, background estimation).
8. **Venue rules from the table below, not memory.** PRL abstracts are ≤ 600
   characters; JHEP/JCAP are `article` + `jheppub`/`jcappub` with `\flushbottom`
   after `\maketitle`. Before converting between classes, read
   `latex-and-formatting.md`.
9. **One INSPIRE record under two keys.** When two `.bib` entries share an `eprint`, they are one paper: keep the current key, update every `\cite` to it, and delete the other. For a collaboration paper the collaboration key (`ATLAS:2012yve`) is the current one and the first-author key (`Aad:2012tfa`) is the older export; say so, and tell the user to confirm on INSPIRE. A `.bib` year taken from arXiv may be the latest-version year, not the publication year.
10. **A single run is not a variance estimate.** In any ML audit or results review, state that one split or one seed gives no variance estimate. Besides fixing the seed, recommend several seeds or cross-validation and report the mean and the spread.

## When to use this skill

Use it for any of:

**Reading side**
- Summarizing a single paper, or extracting its method/dataset/result for reuse
- Critically evaluating a paper's claims, evidence, statistics, and comparisons
- Comparing several papers against each other (methods, datasets, results)
- Building a literature review, a "related work" section, or a paper's Introduction
- Triaging a reading backlog / arXiv listing to decide what's worth reading deeply
- Taking structured reading notes for later reuse in the user's own writing

**Writing side**
- Drafting a paper from scratch, given results/notes/plots the user already has
- Structuring or restructuring a section (abstract, intro, results, discussion, conclusion)
- Converting an internal analysis note into a paper draft, or a paper into a talk/proceedings
- Writing a plain-language public/outreach summary of a published result for a
  collaboration or institution website
- LaTeX formatting: REVTeX (PRL/PRD/PRX), JHEP (`jheppub`), EPJC/Springer Nature, JCAP, AASTeX
  (ApJ/ApJL), Elsevier `elsarticle` (Astroparticle Physics journal), NeurIPS/ICML/
  ICLR/AAAI/ACL-family style files, JMLR/TMLR, general `article`
- Building, cleaning, or deduplicating a BibTeX file; fixing INSPIRE-HEP citation
  keys, pulling ADS/bibcode entries for astronomy-facing venues, or sourcing
  arXiv/DBLP/ACL-Anthology entries for statistics/ML venues
- Designing or captioning figures and tables for publication (including learning
  curves, ablation tables, and leaderboard tables)
- Tightening prose: cutting hedging, fixing tense/voice consistency, trimming
  length, or getting statistical/ML reporting language right (p-values, effect
  sizes, multiple-comparison correction)
- Drafting responses to referee reports, a cover letter to an editor, or a
  single-shot conference rebuttal
- A pre-submission pass: checking length limits, undefined references, missing
  labels, or a reproducibility checklist

**Adjacent document types** (related genres, not paper sections themselves)
- Converting a paper's results into a conference poster or a talk's slide deck
- Drafting a preregistration document or a registered report's Stage 1/Stage 2
- Packaging the user's own code and data for public release alongside a paper
- Drafting a grant or fellowship proposal (Specific Aims, budget justification,
  broader-impacts sections) — a related but distinct genre from a paper
- Assembling a thesis or dissertation from the user's own already-published papers
- Reverse-engineering research/algorithmic source code with no existing
  paper — code that implements a mathematical, statistical, or algorithmic
  method — into a Methodology + Technical Manual document; not for generic
  software with no such content (a CRUD API, a UI library) — see
  `code-to-methodology-synthesis.md`; distinct from reviewing
  code against an already-written paper (`code-review-report.md`, below)

Do **not** reach for this skill for pure numerical/statistical work (fitting, limit
setting, unfolding — `hep-statistics`; ablations, seed variance, proving an ML result
is real — `physics-ml`), experiment-specific data analysis (the bound experiment profile (see the context-resolution steps in the skill's SKILL.md; profiles are listed in `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json`)), or drawing a
schematic or diagram ([academic-diagrams-guide.md](academic-diagrams-guide.md)). Do reach for it the moment that work needs to be
understood from someone else's paper, or turned into English prose,
a figure caption, or a formatted document of your own.

## Core workflow: reading

0. **Find the literature before triaging it**, when there isn't already a
   paper or stack in hand — pick the right database(s) for the field,
   formulate and vary search terms, and snowball citations forward and
   backward from strong seed papers rather than relying on one keyword
   search. See `literature-discovery-and-search.md`.
1. **Triage before deep-reading.** For any paper (or stack of papers), do a fast first
   pass — title, abstract, section headings, figures, conclusion — before deciding it's
   worth reading in full. Most papers only need this pass. See
   `reading-papers.md` for the full three-pass method.
2. **Read for claims and evidence separately.** What does the paper claim, and what
   evidence actually supports each claim (dataset, method, statistical test,
   comparison baseline)? Keep these visibly distinct in notes — conflating "the paper
   says X" with "X is well-supported" is the most common reading error. When the
   evidence is a figure, see `interpreting-scientific-graphics.md` for
   reading it correctly rather than taking its visual impression at face value.
3. **Take structured notes as you read**, not after — use
   `../assets/templates/reading_notes_template.md` as a starting shape (claim / method /
   evidence / limitations / relevance-to-my-work). Notes taken during reading are far
   more reusable later than a memory of "a paper that showed something like this."
4. **When reading multiple papers toward a literature review**, build a comparison
   matrix (method, dataset, key result, year) as you go rather than after —
   `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py` turns a simple CSV of these notes into a formatted
   markdown table ready to drop into a draft. See `literature-review.md`.
5. **Synthesize, don't list.** A literature review or related-work section groups
   papers by what they share or how they differ and states the gap this work fills —
   it is not "Paper A did X [1]. Paper B did Y [2]. Paper C did Z [3]." See
   `literature-review.md` for synthesis patterns.

## Focused verification and review modes

Use these when requested or needed to substantiate claims — not for an ordinary summary.

**Verification and auditing**
- **Citation verification** — reference identity/version/status and whether cited text supports the claim (a resolving DOI/valid BibTeX entry alone doesn't verify it): `citation-verification.md`
- **Systematic-review screening** — eligibility, reproducible search logs, deduplication, screening decisions; keep narrative reviews lightweight unless this is requested: `systematic-review-screening.md`
- **Reproducibility auditing** — trace results to methods/data/code/config/execution evidence; distinguish documentation inspection from an actual rerun (hand execution to `hep-analysis`/`physics-ml`): `reproducibility-auditing.md`
- **Code review report** — paper-to-code alignment, documentation, packaging, severity-ranked findings; distinct from reproducibility auditing, delegates framework correctness to `physics-ml`/`hep-analysis`: `code-review-report.md`
- **Equation and notation auditing** — definitions, dimensions, index/shape consistency, assumptions, derivation steps: `equation-and-notation-auditing.md`
- **Mathematical reasoning and proof status** — soundness of assumptions vs. claimed proof status (formal/analytic/perturbative/asymptotic/heuristic/numerical/empirical/conjecture): `../../hep-theory/references/mathematical-reasoning-and-proof.md`
- **Statistical inference for physics** — correctness of a likelihood/test/interval/limit vs. the stated conclusion: `../../hep-statistics/references/statistical-inference-for-physics.md`
- **Numerical and computational methods** — whether a numerical/computational result is validated (convergence, stability, independent cross-check), not just run: `../../hep-computing/references/numerical-and-computational-methods.md`
- **Claim–evidence mapping** — connect claims to results/derivations/citations, flag unsupported generalizations: `claim-evidence-mapping.md`
- **Logical consistency and argument uniformity** — cross-section contradictions, dropped assumptions, fallacious inference, definitional drift: `logical-consistency-and-argument-uniformity.md`
- **Manuscript consistency auditing** — reconcile repeated results, uncertainty conventions, dataset descriptions, conclusions: `manuscript-consistency-auditing.md`
- **Plagiarism and text-reuse checking** — copied/paraphrased text vs. legitimate quotation, self-citation, boilerplate: `plagiarism-and-text-reuse-checking.md`

**Assessment and restructuring**
- **Reviewer-style assessment** — contribution, validity, comparisons, actionable concerns: `reviewer-style-assessment.md`
- **Research-gap and novelty assessment** — compare the contribution to verified close prior work: novelty-assessment section of `literature-review.md`
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

## Core workflow: writing

1. **Scope the paper.** Before writing a word, pin down: target venue (PRL / PRD /
   JHEP / EPJC / JCAP / ApJ / NeurIPS / ICML / ACL / JMLR / thesis chapter /
   proceedings / internal note), length limit, single result or full analysis, and
   whether this is a from-scratch draft or an edit of existing text. Ambiguity here
   wastes the most time downstream — ask if it's genuinely unclear, but if the user
   has already given enough (e.g. "PRL letter on the Higgs mass measurement" or
   "NeurIPS submission on this method"), proceed without a clarifying round-trip.
2. **Build the skeleton first.** Write section headers and one-sentence placeholders for
   each ("This section will show the fit is consistent with SM at 1.2σ.") before
   writing full prose. This catches structural problems — missing systematics
   discussion, no comparison to prior measurements — while they're cheap to fix.
   See `paper-structure.md`.
3. **Draft section by section, result-first.** For physics papers, write the abstract
   *last* even though it's read first — it's a compressed version of everything else.
   Draft in this order: Results → Analysis/Methods → Introduction → Discussion/
   Conclusion → Abstract → Title. See `paper-structure.md` for what belongs
   in each section and `scientific-style.md` for sentence-level guidance.
4. **Build figures and tables alongside the text**, not after. A figure that needs a
   paragraph of caption to be understood usually needs redesigning, not more caption.
   See `figures-and-tables.md`.
5. **Manage citations as you write**, not in a final sweep — pull keys from the
   right source for the venue (INSPIRE-HEP, ADS, arXiv, DBLP, or ACL Anthology) as
   each claim is made, reusing any reading notes already gathered above, so nothing
   gets forgotten. See `citations-and-bibliography.md`.
6. **Typeset in the target class file** from early on if the venue is known (REVTeX,
   JHEP, etc.) — page/length limits interact with formatting in ways that are painful
   to discover after the fact. See `latex-and-formatting.md`.
7. **Run a pre-submission pass.** Use `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_manuscript.py` to catch undefined
   references, duplicate labels and `.bib` keys, leftover TODOs, cited keys missing from the `.bib`, and unused `.bib` entries
   before the user sends the draft anywhere. Then do a human read-aloud pass for prose
   using `scientific-style.md`.
8. **If reviews come back**, use `submission-and-peer-review.md` for how to
   structure a referee response and cover letter, or a single-shot conference
   rebuttal if the venue uses that process instead.

## Physics/HEP paper structure (quick reference)

A typical experimental HEP paper (PRL/PRD/JHEP style) runs, roughly:

| Section | Purpose | Typical length |
|---|---|---|
| Title | States the result, not the method | ≤ 15 words |
| Abstract | Self-contained summary: context, method, result, significance | 150–250 words (PRL: ≤ 600 characters incl. spaces, about 90 words) |
| Introduction | Physics motivation, prior measurements, what's new here | 0.5–1.5 pages |
| Detector & Dataset | What data, what detector, what luminosity/energy | 0.25–0.75 pages |
| Analysis / Event Selection | Cuts, reconstruction, background estimation | 1–3 pages |
| Systematic Uncertainties | Sources, sizes, correlations, how propagated | 0.5–1.5 pages |
| Results | The number(s), with statistical + systematic uncertainty, comparison to theory/prior results | 0.5–1.5 pages |
| Summary / Conclusion | Restate result, implications, outlook — no new claims | 3–8 sentences |
| Acknowledgments | Funding agencies, collaboration boilerplate | fixed by collaboration |

Full guidance for this backbone is in `paper-structure.md`. How it
differs for theory papers, review articles, thesis chapters, astroparticle/
cosmic-ray papers (exposure instead of luminosity, arrival-direction/anisotropy
sections, multi-messenger context), and statistics/ML papers (required
Limitations/Broader-Impact sections, reproducibility checklists, single-shot
rebuttals) is in `paper-genre-variants.md`,
`astroparticle-and-cosmic-ray-papers.md`, and
`statistics-and-ml-papers.md`.

## Journal / venue conventions (quick reference)

| Venue | Class file | Length (verified 2026-09) | Notes |
|---|---|---|---|
| PRL | `revtex4-2` (`\documentclass[aps,prl,reprint]{revtex4-2}`) | 3,750 words (about 4 pages); abstract ≤ 600 characters | Run-in italic heads, not `\section`; no PACS (PhySH since 2016) |
| PRD / PRX | `revtex4-2` (`\documentclass[aps,prd,reprint]{revtex4-2}`) | PRD regular articles: no fixed limit; PRD Letters 4,500 words | Numbered sections, full methods |
| JHEP | `article` + SISSA's `jheppub.sty` (not a `.cls`) | No fixed limit | `\abstract{}` before `\begin{document}`; labeled `\author[a]`/`\affiliation[a]`, `\emailAdd`; `\flushbottom`; `\bibliographystyle{JHEP}`. REVTeX front matter does not carry over: read the reference before converting |
| EPJC | Springer Nature template `sn-jnl.cls`, `[iicol]` option | No fixed limit | Old `svjour3` superseded; decimal headings, ≤ 3 levels |
| Nature Physics | Nature LaTeX template or Word | Article: 3,000 words main text, ~200-word summary paragraph, ≤ 6 display items | Letters retired in 2022; check Nature itself separately |
| JCAP (astroparticle) | `article` + SISSA's `jcappub.sty` | No fixed limit | Same front matter as JHEP; common for cosmic-ray/dark-matter theory and phenomenology |
| ApJ / ApJL (astroparticle) | AASTeX v7 (`\documentclass{aastex7}`) | Abstract ≤ 250 words; ApJL 3,500 words and ≤ 5 figures+tables (soft) | natbib author-year citations |
| Astroparticle Physics (Elsevier) | `elsarticle.cls` (v3.5) | Not verified (publisher pages blocked); read the journal's Guide for Authors | Elsevier house style |
| NeurIPS / ICML / ICLR (2026) | Conference's current-year `.sty` | 9 / 8 / 9 pages main text including figures and tables; references, appendices (and NeurIPS's checklist) do not count; +1 page at camera-ready (ICLR: 10 pages at rebuttal and camera-ready) | Double-blind; NeurIPS checklist, ICML impact statement required; re-check every year |
| ACL / EMNLP / NAACL (ARR) | Official ACL template, unmodified | Long 8 pages, short 4 | Required "Limitations" section, not counted; `natbib` author-year |
| TMLR | Venue's own LaTeX template | No page limit (long papers review more slowly) | Journal-style open review, closer to a physics journal's process |
| JMLR | `jmlr2e.sty` | No hard limit; > 35 pages (with appendices) risks rejection, > 50 pages needs a cover-letter justification; abstract ≤ 200 words | Journal review; non-JMLR style is rejected without review |
| Statistics journals (JASA, Annals of Statistics, ...) | Usually plain `article`-based | Not verified | Journal-specific reference style; theorem/proof structure for theory papers |
| arXiv preprint | Whatever the target journal uses, or `article` | Match target venue | arXiv runs BibTeX/biber itself; upload any `.sty`/`.cls` not in TeX Live; don't mix PS and PDF figures |

Sources and per-row dates are in `latex-and-formatting.md` ("Venue rules:
sources and last-verified dates"). A row older than a year, or for a different
conference year, must be re-checked before it is quoted as a hard limit.

Details, obtaining the right class file, and common compile errors are in
`latex-and-formatting.md`; astroparticle-specific venues and author-list
conventions are in `astroparticle-and-cosmic-ray-papers.md`;
statistics/ML-specific venues, reproducibility checklists, and rebuttal mechanics
are in `statistics-and-ml-papers.md`. A generic starting skeleton (not
tied to any journal's copyrighted class file) is in
`../assets/templates/paper_skeleton.tex`, paired with an example INSPIRE-HEP-formatted
entry in `../assets/templates/references.bib` — copy the actual class file from the
journal/APS/SISSA/Springer/AAS/Elsevier/conference site once the venue is fixed.

## Reference files

Read these as needed — don't load them all up front unless doing a full draft or
review. Grouped by function; within a group, order roughly follows the workflow.

**Reading and discovery**
- `literature-discovery-and-search.md` — finding relevant papers
  before there's anything to triage: database/tool choice by field, query
  formulation, forward/backward citation snowballing, alerts, and knowing
  when search coverage is enough
- `reading-papers.md` — the three-pass reading method, separating claims
  from evidence, a critical-reading checklist (fair baselines, statistical rigor,
  reproducibility), HEP-specific things to check (dataset/luminosity, systematics
  treatment, look-elsewhere effect), astroparticle-specific things to check
  (exposure/livetime, trials factor, hadronic-model dependence), and
  statistics/ML-specific things to check (baseline fairness, cross-seed
  significance, train/test contamination)
- `interpreting-scientific-graphics.md` — the reading-side counterpart
  to figure design: reading common plot types correctly (exclusion contours,
  corner plots, ROC curves, skymaps, learning curves), extracting approximate
  values when no data table is given, spotting misleading visualization
  techniques, and separating visual impression from statistical significance
- `literature-review.md` — organizing a review or related-work section
  (chronological vs. thematic vs. methodological), building a comparison matrix,
  synthesis patterns vs. citation-stuffing, spotting research gaps

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
- `astroparticle-and-cosmic-ray-papers.md` — how structure, venues,
  author lists, citations, figures, and phrasing shift for astroparticle-physics
  and cosmic-ray papers (ground arrays, IACTs, neutrino observatories, space-based
  direct detection): exposure vs. luminosity, arrival-direction/anisotropy sections,
  JCAP/ApJ/Astroparticle Physics venues, ADS/bibcode citations, skymap conventions,
  pre-trial vs. post-trial significance, and a worked AMS-02 publication-pattern
  case study (letter-only/no-arXiv publishing, a Phys. Rept. review alongside PRL
  letters, 44-institution author-list scale, a web-only non-citable
  "advances-in-data-analysis" technical-progress genre, and syndicated vs.
  collaboration-authored outreach pages)
- `statistics-and-ml-papers.md` — how structure, venues, author-
  contribution statements, citations, and review process shift for statistics and
  machine-learning papers: required Limitations/Broader-Impact sections,
  reproducibility checklists and artifacts (model cards, datasheets), NeurIPS/
  ICML/ICLR/AAAI/ACL-family/JMLR/TMLR/statistics-journal venue landscape,
  arXiv-first citation culture (DBLP, ACL Anthology, Semantic Scholar), and
  single-shot OpenReview rebuttals vs. a journal's multi-round revision
- `latex-and-formatting.md` — REVTeX/JHEP/Springer/JCAP/AASTeX/
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
  ROOT/matplotlib output made under `hep-analysis`), caption writing, table
  conventions, skymap/cosmic-ray-spectrum figures, and learning-curve/ablation/
  leaderboard tables
- `citations-and-bibliography.md` — INSPIRE-HEP, ADS, and arXiv/DBLP/
  ACL-Anthology workflows, BibTeX hygiene, managing a personal reference library
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
  each mode's trigger and reference file: citation verification, systematic-review
  screening, reproducibility auditing, code review, equation/notation auditing,
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
  two-part synthesis; delegates correctness verification to
  `hep-analysis`/`physics-ml` where applicable; template skeleton in
  `../assets/templates/code_to_methodology_manual_template.md`

## Bundled scripts

- `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py` — turns a CSV of reading notes (one row per paper:
  key, year, method, dataset, result, notes — columns are flexible) into a formatted
  markdown comparison table, ready to drop into a literature review or related-work
  draft. Standard library only.

  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/build_lit_matrix.py <notes.csv> [--sort-by year] [-o out.md]
  ```

- `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_manuscript.py` — scans a directory of `.tex`/`.bib` files and reports:
  undefined `\ref`/`\cref`/`\pageref` targets, duplicate `\label`s, citation keys
  (natbib, biblatex and `\nocite`) missing from any `.bib` file, duplicate `.bib` keys,
  unused `.bib` entries, and leftover TODO/FIXME/placeholder markers. Comments are
  ignored. With no `.bib` (only a `.bbl` or inline `\bibitem`s) the citation checks are
  skipped. `--style` adds two advisory typography checks (label word + plain space
  before `\ref`; number and unit joined by a plain space) that never change the exit
  code. Read-only; standard library only. Run it near the end of a drafting session, not
  after every sentence.

  ```
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_manuscript.py <path-to-manuscript-dir>
  ```

- legacy academic-papers/scripts/validate_skill_bundle.py at agentic-ai-skills@3e995a4 (not shipped) — integrity checker for this skill bundle itself
  (not for the user's paper or reading notes). Run after editing this skill.

## Working style within this skill

- **Rules 1-4 above apply throughout.** In particular, keep separate what a paper
  claims, what it demonstrates, and any interpretation being added.
- **Match existing voice** when editing a draft rather than a blank page — improve
  clarity and correctness without rewriting a passage that already works, and flag
  the specific sentences changed rather than silently rewriting whole sections.
- **Default to the venue's convention**, not personal preference, once a venue is
  named (e.g. PRL wants short, punchy paragraphs; JHEP tolerates more derivation).
- **Ask, don't assume, about author list and acknowledgments** for collaboration
  papers — get these from the user or an existing template rather than guessing
  collaboration boilerplate.

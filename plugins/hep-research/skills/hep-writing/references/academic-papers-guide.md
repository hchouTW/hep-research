# Academic Papers (guide)

## When to read this file

| Task | Minimum inputs | Load | Output | Done when |
|---|---|---|---|---|
| Citations a draft needs | the citation list; literature records or ledgers | hep-literature's [literature guide](../../hep-literature/references/literature-guide.md) | `check_citations.py` report; unverified ones marked | every citation is found in a record or ledger, or marked `not-verified` |
| Draft or revise a section | result artifacts or supplied numbers; target venue | this guide, `scientific-style.md` | the text with status labels and `[VALUE NEEDED]` slots | every number links to an artifact or a source |
| Evidence-linked manuscript (audit depth) | a traceability `communication` record and the documents | `evidence-linked-writing.md` | `check_communication.py` and `audit_claims.py` reports, draft facts | both reports pass or their open items are listed |
| Changed result during revision | baseline and revised records | `revision-impact-tracking.md` | `track_revision_impact.py` report, reopened assessments | stale occurrences fixed and re-checked |
| Referee reply or derived draft | reviewer and revision items; a manifest for the draft | `submission-and-peer-review.md`, `../assets/paper/audience-adaptation-templates.md` | `check_adaptation.py` report and generated wording | no assertion of uncompleted work; caveats kept |
| Terminology pass | glossary, documents | `equation-and-notation-auditing.md` | `check_terminology.py` report | findings reviewed by a reader |


This file holds the routing and rules for work on scientific papers. Read it when a hep-writing task falls in its scope; the reference files it routes to are linked relative to this file.
Finding, reading and verifying sources (quick source-backed answers, the latest result, literature records) are
hep-literature's: its [literature guide](../../hep-literature/references/literature-guide.md).

Scope: reviewing and writing physics papers (collider, astroparticle and
cosmic-ray, statistics and ML venues). This skill owns the *writing*, not the sources
(hep-literature) or the analysis: a fit or a limit goes to `hep-statistics`; proving an improvement is real
to `hep-ml`; the code behind a plot or table to `hep-computing`; a selection or a
correction to `hep-measurement`; a diagram to [academic-diagrams-guide.md](academic-diagrams-guide.md).

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
   (pyhf/Combine/RooStats) or `hep-ml`, and write `[VALUE NEEDED: 95% CL CLs
   limit]`. **Plots: read, never compute.** Reading a value the plot shows
   (a point, a published limit curve at a given mass) is allowed with the label
   *approximate* and the reading method stated (digitiser, or interpolation
   between gridlines; `../../hep-literature/references/interpreting-scientific-graphics.md`); prefer the
   HEPData table when one exists. Computing a new σ, limit, interval or fit
   value from plotted values (a ratio panel, a residual, two curves) is not
   allowed, not even roughly: hand it to `hep-statistics` with the published
   numbers or HEPData tables. The reporting sentence still names the method:
   confidence level and construction (CLs, Feldman-Cousins), asymptotic or toys,
   and how each uncertainty enters (e.g. "the background uncertainty is included
   as a constrained nuisance parameter"); use a placeholder for any choice not
   yet made.
3. **Calibrate claims to the evidence.** Significance words ("evidence for",
   "observation of") are a field convention with thresholds, and the everyday
   "evidence" (a source that supports a claim) carries none; they, local vs.
   global (pre- vs. post-trial) wording and limit wording follow `scientific-style.md` (Significance language;
   Reporting limits and nulls), their single home. If a claim is stronger than its
   source, say so and propose the weaker wording explicitly, rather than silently
   softening it.
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
8. **Venue rules from `latex-venue-setup.md` (quick reference), not memory.**
   Read it before quoting a limit or converting between classes.
<!-- example: experiment-specific illustration -->
9. **One paper, one entry: identifiers decide, keys follow.** Two `.bib` entries are one paper when they share a DOI, else an arXiv identifier (version stripped), else an INSPIRE record id; never compare keys, because one INSPIRE record can carry two. Keep the current key, update every `\cite` to it, and delete the other; this is the only reason to rename a key. For a collaboration paper the collaboration key (`ATLAS:2012yve`) is the current one and the first-author key (`Aad:2012tfa`) is the older export; say so, and tell the user to confirm on INSPIRE. A `.bib` year taken from arXiv may be the latest-version year, not the publication year.
<!-- /example -->
10. **A single run is not a variance estimate.** In any ML audit or results review, state that one split or one seed gives no variance estimate. Besides fixing the seed, recommend several seeds or cross-validation and report the mean and the spread.

## Core workflow: reading

Finding, triaging and reading papers, structured reading notes and the literature matrix moved to hep-literature's
[literature guide](../../hep-literature/references/literature-guide.md#core-workflow-reading); hand it the reading and
take back a `literature-record` to write from.

## Focused verification and review modes

Use these when requested or needed to substantiate claims: the list of verification, assessment, tracking
and disclosure modes, each with its file, is in [review modes](papers-review-modes-and-reference-index.md#focused-verification-and-review-modes).

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
5. **Manage citations as you write**, not in a final sweep: every citation comes from a
   hep-literature `literature-record` or a profile evidence ledger (exported from the venue's database as
   [citation databases](../../hep-literature/references/citation-databases.md) describes), never from memory; a
   citation without a record goes to hep-literature first or is marked `[CITATION NEEDED: ...]`. Run
   `<plugin root>/skills/hep-writing/scripts/check_citations.py` on the draft; it lists every citation it cannot find
   as `not-verified`. See `citations-and-bibliography.md` for `.bib` hygiene.
6. **Typeset in the target class file** from early on if the venue is known (REVTeX,
   JHEP, etc.) — page/length limits interact with formatting in ways that are painful
   to discover after the fact. See `latex-venue-setup.md`.
7. **Run a pre-submission pass.** Use `<plugin root>/skills/hep-writing/scripts/check_manuscript.py` to catch undefined
   references, duplicate labels and `.bib` keys, leftover TODOs, cited keys missing from the `.bib`, and unused `.bib` entries
   before the user sends the draft anywhere. Then do a human read-aloud pass for prose
   using `scientific-style.md`.
8. **If reviews come back**, use `submission-and-peer-review.md` for how to
   structure a referee response and cover letter, or a single-shot conference
   rebuttal if the venue uses that process instead.

## Paper structure

The section backbone of an experimental HEP paper (title, abstract, introduction,
detector and dataset, analysis, systematics, results, summary, acknowledgments) with
purposes and typical lengths is in `paper-structure.md`; how it differs for theory
papers, reviews, theses, astroparticle and statistics/ML papers is in
`paper-genre-variants.md`, `astroparticle-and-cosmic-ray-papers.md` and
`statistics-and-ml-papers.md`.

## Journal / venue conventions

Venue facts (class files, length and abstract limits, front matter) have one home:
the quick-reference table in `latex-venue-setup.md`, with its sources and
last-verified dates; never quote a limit from memory.

A generic starting skeleton (no copyrighted class file) is
`../assets/paper/paper-skeleton.tex` with `../assets/paper/references.bib`.

## Reference files

Which file to read for each topic: [reference index](papers-review-modes-and-reference-index.md#reference-files).

## Bundled scripts

`check_manuscript.py` (`--main MAIN.tex` for a submission check: references, labels, citation keys, `.bib`
entries, markers, include coverage) and `check_citations.py` (each citation against literature records and ledgers)
are described in the skill's README ("Scripts"); read `--help` first. The literature matrix (`build_lit_matrix.py`) is
hep-literature's.

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

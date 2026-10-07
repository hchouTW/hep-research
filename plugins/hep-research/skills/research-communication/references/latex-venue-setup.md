# LaTeX and Formatting

How to set a manuscript up correctly for the major physics venues, and how to
avoid the compile errors and length-limit surprises that eat time late in
drafting. See `latex-mechanics-and-tooling.md` for cross-cutting LaTeX
mechanics that apply regardless of venue (notation macros, table syntax,
PDF accessibility, diffing, build automation, bibliography engines,
multi-file structuring, encoding) — this file is venue-specific setup only.

## Table of contents
- [Getting the right class file](#getting-the-right-class-file)
- [REVTeX (PRL / PRD / PRX)](#revtex-prl--prd--prx)
- [JHEP](#jhep)
- [EPJC / Springer](#epjc--springer)
- [Astroparticle venues (JCAP / AASTeX / Elsevier)](#astroparticle-venues-jcap--aastex--elsevier)
- [Statistics and ML venues](#statistics-and-ml-venues)
- [arXiv-specific rules](#arxiv-specific-rules)
- [Units, numbers, and equations](#units-numbers-and-equations)
- [Common compile errors](#common-compile-errors)
- [Length-limit tactics](#length-limit-tactics)
- [Venue rules: sources and last-verified dates](#venue-rules-sources-and-last-verified-dates)

## Getting the right class file

Never hand-copy a journal's `.cls`/`.bst` file from memory or reconstruct it —
these are maintained and versioned by the publisher/society. Get the current
version from the authoritative source:
- REVTeX 4.2 (APS: PRL, PRD, PRX, PRA, PRB, ...): APS's REVTeX page.
- JHEP: SISSA's JHEP author guidelines page (`jheppub.sty`, loaded on top of
  `article`, plus `JHEP.bst`). The old `JHEP3.cls` class is no longer what SISSA ships.
- EPJC: the Springer Nature LaTeX template (`sn-jnl.cls`) with the `[iicol]` option.
- Nature family: Nature's LaTeX template page (or submit in Word, per journal).
- JCAP / ApJ / Astroparticle Physics (Elsevier): see "Astroparticle venues" below.
- NeurIPS / ICML / ICLR / AAAI / ACL family / JMLR / TMLR: see "Statistics and ML
  venues" below.

If offline or unsure of the exact current filename/version, tell the user to
pull it fresh from the journal's site rather than guessing — a stale or
hand-reconstructed class file is a common source of subtle formatting bugs
that only show up after submission.

## REVTeX (PRL / PRD / PRX)

Minimal PRL skeleton:

```latex
\documentclass[aps,prl,reprint,superscriptaddress]{revtex4-2}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{hyperref}

\begin{document}

\title{Measurement of ...}

\author{A.\ Researcher}
\affiliation{Department of Physics, University X}
% A collaboration-only byline uses \collaboration{The XYZ Collaboration}
% (never \author); with individual authors, REVTeX warns
% "Assuming \noaffiliation for collaboration", which is harmless.

\date{\today}

\begin{abstract}
...
\end{abstract}

\maketitle

\textit{Introduction}---Body text starts here (PRL uses run-in italic heads,
not \verb|\section|).

\end{document}
```

Notes (checked 2026-09 against the APS REVTeX 4.2 author guide and the APS Journals Style
Guide, November 2024; the skeleton above compiles with Tectonic):
- PRL does not generally use freestanding headings. Use run-in heads: paragraph indent,
  italic, em dash (`\textit{Introduction}---Text ...`). PRD/PRX use numbered sections.
- Do not add `showpacs`/`\pacs{}`: APS stopped asking for PACS codes in 2016 (the scheme
  has not been maintained since 2010) and uses PhySH subject headings, chosen at submission.
- PRL length: the body may not exceed 3,750 words (about 4 journal pages), excluding the
  abstract, author list and affiliations, and references; footnote text in the
  reference list does count. Figures, displayed equations and tables are converted to
  word equivalents (APS length guide: two-column figure = 300/(0.5 x aspect ratio) + 40
  words; single-column figure = 150/aspect ratio + 20; displayed equation = 16 words
  per row single-column, 32 two-column; table = 13 + 6.5 words per line single-column,
  26 + 13 two-column). The abstract is limited to 600 characters including spaces.
  PRD and PRC Letters: 4,500 words. PRD regular articles have no fixed limit.
- `\collaboration{}` and `\affiliation{}` handle large collaboration author
  lists — for genuinely large collaborations (hundreds of authors), APS
  provides a separate author-list macro package; ask the collaboration's
  publications committee for the current boilerplate rather than typing
  hundreds of `\author{}` lines by hand.
- APS accepts submissions typeset with either the `reprint` or the `twocolumn` option
  (`reprint` approximates the journal look); `preprint` gives single-column 12pt for
  drafts. None of these is required for a given journal, and APS re-typesets from the
  source anyway. Format for US letter paper.

## JHEP

```latex
\documentclass[a4paper,11pt]{article}
\usepackage{jheppub}   % from SISSA's JHEP author page; not in TeX Live
\usepackage{amsmath,amssymb,graphicx}

\title{...}
\author[a]{First Author,}
\author[b]{and Second Author}
\affiliation[a]{Institution A}
\affiliation[b]{Institution B}
\emailAdd{author@inst.edu}

\abstract{...}

\begin{document}
\maketitle
\flushbottom

\section{Introduction}
...

\bibliographystyle{JHEP}
\bibliography{references}
\end{document}
```

Checked 2026-09: this skeleton compiles with Tectonic against `jheppub.sty`
v.1.1227 (2018/12/04) and `JHEP.bst` downloaded from SISSA. `jheppub` is a package
for the standard `article` class, not a document class; the author manual asks for
the `11pt,a4paper` options. Authors are separated by commas and the last one starts
with "and", as in SISSA's own example. `\keywords{}` and `\arxivnumber{}` are optional.
JHEP has no fixed page limit.

Converting from REVTeX (checked against `jheppub.sty`; the same applies to JCAP):
- `\begin{abstract}...\end{abstract}` after `\begin{document}` becomes
  `\abstract{...}` *before* `\begin{document}` (jheppub redefines `\abstract` as a
  command, so the environment no longer works).
- REVTeX attaches each `\affiliation` to the authors above it; jheppub links them by
  label: `\author[a,b]{Name,}`, `\affiliation[a]{...}`. A plain `\author{}` +
  `\affiliation{}` pair only works for the single-affiliation case.
- Emails go in `\emailAdd{}` (one per author, in author order), not in `\email{}`.
  `\collaboration{}` exists in jheppub too.
- Drop `\pacs{}`, `showpacs`, `superscriptaddress` and PRL run-in heads; use
  numbered `\section{}`s. Switch `\bibliographystyle{apsrev4-2}` to `{JHEP}`.

JHEP numbers all sections, expects `\flushbottom`, and its `JHEP.bst` style
formats INSPIRE-style BibTeX entries (with `eprint`/`archivePrefix` fields)
correctly — pull `.bib` entries from INSPIRE-HEP directly rather than
retyping them (see `citations-and-bibliography.md`).

## EPJC / Springer

EPJC's submission guidelines recommend the Springer Nature LaTeX template
(`sn-jnl.cls`) with the `[iicol]` option, since the journal is typeset double column;
manuscripts in other LaTeX templates are converted. The older `svjour3` class with
`svepjc3.clo` (still on Overleaf, last updated about 2019) is superseded. Headings
use the decimal system, at most three levels. Word files are also accepted. Checked
2026-09 from a search-engine copy of Springer's EPJC guidelines page, because the page
itself redirects to a login step when fetched.

## Astroparticle venues (JCAP / AASTeX / Elsevier)

- **JCAP** uses SISSA's `jcappub.sty`, the JCAP twin of `jheppub.sty`: load it with
  `\usepackage{jcappub}` on `\documentclass[a4paper,11pt]{article}`, with the same
  front-matter commands and `JHEP.bst` (checked 2026-09: the JHEP skeleton above
  compiles unchanged with `jcappub.sty` v.1.1227). Pull it from JCAP's author page.
- **ApJ / ApJL** use AASTeX. The current version is v7 (`\documentclass{aastex7}`,
  guide covers v7.0.1; `[modern]` is still an optional style), checked 2026-09; the
  older `aastex631` is what TeX distributions such as Tectonic's bundle still carry,
  so download v7 from the AAS journals page. AASTeX version bumps have changed
  author-list and table syntax before. AAS abstracts: at most 250 words. ApJ Letters:
  at most 3,500 words of main text (excluding acknowledgments and appendices) and at
  most 5 figures plus tables combined (each figure at most 9 panels); AAS says these
  limits are no longer strictly compulsory, but exceeding them needs the editor's
  agreement.
  `natbib`-style author-year citations (`\citep{}`/`\citet{}`) are the default, not
  the numbered style used by REVTeX/JHEP.
- **Astroparticle Physics (Elsevier)** uses `elsarticle.cls`; get it from Elsevier's
  author-support page along with the current citation-style option the journal
  specifies (Elsevier journals vary in numbered vs. author-year style by title).

See `astroparticle-and-cosmic-ray-papers.md` for the structural and citation-database
(ADS vs. INSPIRE-HEP) differences that go along with these venues, not just the class
files.

## Statistics and ML venues

- **NeurIPS / ICML / ICLR / AAAI** each publish a `.sty`/class file for that
  specific year's conference — pull the *current year's* template, not a cached
  one from a prior year: margins, font, and section-numbering rules change
  year to year and several of these venues run an automated formatting checker
  at submission that rejects a paper built on a stale template. 2026 limits
  (checked 2026-09 on each venue's own page; re-check every year):
  - NeurIPS 2026: 9 content pages including figures and tables; references, the
    mandatory paper checklist and optional technical appendices do not count;
    +1 content page for camera-ready. Over-length papers are not reviewed.
  - ICML 2026: 8 pages main paper; references, the required impact statement and
    appendices are unlimited and do not count; +1 page (9) for camera-ready.
  - ICLR 2026: 9 pages main text at submission, 10 during rebuttal and for
    camera-ready; references and appendices do not count.
  - All three are double-blind.
  - Style files, options and bibliography setup (compiled with Tectonic 2026-10-01; each
    official example builds with no errors and no undefined references or citations):
    - NeurIPS: `\usepackage{neurips_2026}` (from `Formatting_Instructions_For_NeurIPS_2026.zip`,
      linked on the call-for-papers page). Track options `main`, `position`, `eandd`,
      `creativeai`, `education` and two workshop options; `final` for camera-ready,
      `preprint` for arXiv, `nonanonymous` to drop anonymization, `nonatbib` if you load
      natbib yourself. The template ships `checklist.tex`.
    - ICML: `\usepackage{icml2026}` plus `\icmltitlerunning{...}`; options `accepted`
      (camera-ready), `preprint`, `nohyperref`. Ships `icml2026.bst`, so use
      `\bibliographystyle{icml2026}`.
    - ICLR: `\usepackage{iclr2026_conference,times}`; `\iclrfinalcopy` for camera-ready;
      `\bibliographystyle{iclr2026_conference}`. Ships its own `natbib.sty`.
    - Tectonic is XeTeX-based, so ICML and ICLR give "Font shape `TU/ptm/...' undefined"
      warnings and embed some CID fonts; the output has no Type 3 fonts. A venue's
      format checker may still prefer pdfTeX output: do the final build with the engine
      the venue documents.
- **ACL / EMNLP / NAACL** (reviewed through ACL Rolling Review) require the official
  ACL style template from the ACL GitHub repository, unmodified, with
  `\citep`/`\citet` author-year citations. Compiled 2026-10-01 from the ACL GitHub
  `acl-style-files` master (`acl_latex.tex`, 4 pages, no errors): `\usepackage[review]{acl}`
  for submission (anonymous, line numbers), `final` for camera-ready, `preprint` for
  arXiv; bibliography style `acl_natbib`. ARR limits (checked 2026-09): long papers 8
  pages of content, short papers 4, plus unlimited references; a "Limitations"
  section is required (desk rejection without it), goes after the conclusion and
  before the references, and does not count toward the limit, like the optional
  ethical-considerations section.
- **JMLR / TMLR** each have their own dedicated LaTeX template (JMLR's is a
  long-running stable style, closer to a journal's `article`-based class than a
  yearly-changing conference one). TMLR requires its own style file and sets no
  page limit ("submissions may be any length"), but unusually long papers are
  likely to be reviewed more slowly. JMLR has no hard limit, but its author
  page (fetched 2026-10) warns that papers over 35 pages, appendices included, may be
  rejected if no editor or reviewers are found, and papers over 50 pages need a
  justification in the cover letter and may be desk-rejected. JMLR rejects papers not
  in its `jmlr2e.sty` style without review.
- **Statistics journals** (JASA, Annals of Statistics, Biometrika, JRSS-B) rarely
  mandate a specific heavily-branded class file the way REVTeX/AASTeX do — most
  accept a plain `article`-based submission with the journal's own reference
  style; check the specific journal's current author guidelines rather than
  assuming a house class exists.

See `statistics-and-ml-papers.md` for the structural differences (Limitations and
Broader Impact/Ethics as required sections, reproducibility checklists, appendix
conventions) and the review-process differences (single-shot rebuttal vs. a
journal's multi-round revision) that go with these venues, not just the class
files.

## arXiv-specific rules

- arXiv recompiles from source with TeX Live (2025 by default, 2023 selectable;
  checked 2026-09). It detects the bibliography and runs BibTeX or biber itself, so
  either the `.bib` or a pre-built `.bbl` works. A supplied `.bbl` must have the
  same base name as the main `.tex`, and with biblatex it must match arXiv's biber
  version, so letting arXiv build it is usually safer.
- Upload every file the build reads: figures, and any custom `.cls`/`.sty`/`.bst`
  not in TeX Live (for example `jheppub.sty`, `jcappub.sty`, conference `.sty` files).
- Use one figure format family: arXiv will not convert between PostScript and
  PDF/PNG/JPG during processing, so do not mix them.
- In `hyperref` URLs that contain `#`, write `\string#` so the link survives
  processing.
- Category selection (e.g. `hep-ex`, `hep-ph`, `hep-th`, `astro-ph.HE`)
  determines the primary audience and moderation queue — pick the primary
  category that matches the paper's main claim, with cross-lists for
  secondary relevance.

## Units, numbers, and equations

- Use natural units (`\hbar = c = 1`) consistently in HEP papers unless the
  venue/subfield convention is SI; state the convention once, early.
- Number format: prefer `125.09 \pm 0.24$ GeV` style with explicit
  uncertainty, not `~125 GeV` in a Results section (approximations are fine
  in prose elsewhere).
- Use `siunitx` (`\SI{125.09}{\GeV}`) for consistent unit typesetting if the
  venue allows extra packages; otherwise typeset units in roman, values in
  math mode, with a non-breaking space (`~`) between them: `125~GeV`.
- Number all equations that are referenced later; do not number equations
  that are never cross-referenced (clutters the margin, and some venues
  penalize it in length-limited formats).

## Common compile errors

| Symptom | Likely cause |
|---|---|
| `Undefined control sequence` right after `\documentclass` | Wrong/missing class file, or a package loaded before its dependency |
| References show as `[?]` | Need to run `bibtex`/`biber` then `pdflatex` twice more (four-pass compile) |
| `\cite` shows `[??]` after full 4-pass compile | Citation key not in the `.bib` file, or the `.bib` file isn't listed in `\bibliography{}` |
| Figure "not found" | Path relative to `.tex` file, not to where the compiler is invoked; check `\graphicspath{}` |
| `Too many unprocessed floats` | Too many `\begin{figure}` without enough text between them; add `\clearpage` or reduce simultaneous floats |
| Overfull `\hbox` warnings | Usually cosmetic (line slightly too wide) but check for un-hyphenatable long words/URLs — wrap with `\url{}` or `\seqsplit{}` |

## Length-limit tactics

When a venue enforces a hard page/word limit (PRL's 3,750 words, about 4 pages, is
the classic case):
- Move derivation detail and extra validation plots to Supplemental
  Material, if the venue supports it, rather than cutting the physics.
- Combine multi-panel figures rather than using several single-panel
  figures — this often saves more space than trimming prose.
- Cut hedging and redundant transition phrases before cutting content (see
  `scientific-style.md`) — most first drafts have 10-20% removable words
  with no loss of information.
- Do not shrink font size or margins to cheat a page limit; venues check
  for this and it reads poorly to referees.

See `latex-mechanics-and-tooling.md` for notation macros, table syntax,
tagged-PDF accessibility, `latexdiff` tracked-changes diffing, `latexmk`
build automation, bibliography-engine choice, multi-file document
structuring, and non-ASCII name encoding.

## Venue rules: sources and last-verified dates

Venue rules change, conference rules every year. Each rule above is dated. Re-check
a row when it is more than a year old, or when the user's venue or year differs.
"Search copy" means the publisher page could not be fetched (login redirect), so the
value comes from a search engine's copy of that official page.

| Venue | Rule(s) checked | Source | Last verified |
|---|---|---|---|
| PRL / PRD / PRC | length limits, word equivalents | https://journals.aps.org/authors/length-guide | 2026-09 |
| PRL | 600-character abstract, 3,750 words | https://journals.aps.org/prl/info/infoL.html | 2026-09 |
| APS | PACS dropped, PhySH | PRL editorial 10.1103/PhysRevLett.116.080001 (2016) | 2026-09 |
| APS | run-in heads in PRL | APS Journals Style Guide for Authors (November 2024) | 2026-09 |
| APS | `reprint`/`twocolumn`, `superscriptaddress`, `\collaboration` | APS Author Guide for REVTeX 4.2 (CTAN `apsguide4-2.pdf`) | 2026-09 |
| JHEP | `jheppub.sty` on `article`, front matter | https://jhep.sissa.it/jhep/help/JHEP_TeXclass.jsp and its author manual (2021) | 2026-09 |
| JCAP | `jcappub.sty` | https://jcap.sissa.it/jcap/help/JCAP_TeXclass.jsp | 2026-09 |
| EPJC | Springer Nature template, `[iicol]` | https://link.springer.com/journal/10052/submission-guidelines (search copy) | 2026-09 |
| ApJ / ApJL | AASTeX v7, 250-word abstract, ApJL 3,500 words and 5 display items | https://journals.aas.org/aastexguide/ , https://journals.aas.org/manuscript-preparation/ , https://journals.aas.org/the-astrophysical-journal-letters/ | 2026-09 |
| Nature Physics | Article: 3,000 words main text, 200-word summary, 6 display items | https://www.nature.com/nphys/content (search copy) | 2026-09 |
| Nature Physics | Letters retired (2022) | editorial "A farewell to Letters", https://www.nature.com/articles/s41567-022-01621-z (search copy) | 2026-09 |
| NeurIPS 2026 | 9 content pages, checklist | https://neurips.cc/Conferences/2026/MainTrackHandbook | 2026-09 |
| ICML 2026 | 8 pages (+1 camera-ready), impact statement | https://icml.cc/Conferences/2026/CallForPapers | 2026-09 |
| ICLR 2026 | 9 pages (10 at rebuttal/camera-ready) | https://iclr.cc/Conferences/2026/AuthorGuide | 2026-09 |
| ACL Rolling Review | 8/4 pages, required Limitations | https://aclrollingreview.org/cfp | 2026-09 |
| TMLR | no page limit, own style file | https://jmlr.org/tmlr/author-guide.html | 2026-09 |
| arXiv | TeX Live, BibTeX/biber, `.bbl` naming, figure formats | https://info.arxiv.org/help/submit_tex.html | 2026-09 |
| JMLR | `jmlr2e.sty` on `article`; > 35 pages (with appendices) may be rejected if no editor or reviewers are found, > 50 pages need a cover-letter justification and may be desk-rejected; abstract <= 200 words, 5 keywords, running title <= 50 characters; non-JMLR-style papers rejected without review | https://www.jmlr.org/author-info.html , https://www.jmlr.org/format/format.html , https://github.com/JmlrOrg/jmlr-style-file | 2026-10 |
| AAAI-27 | 7 content pages, 9 total (pages 8-9 references only); double-blind; reproducibility checklist at submission. The style-file name `aaai27.sty` is from a search snippet only: not verified, take it from the Author Kit | https://aaai.org/conference/aaai/aaai-27/submission-instructions/ , https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/ | 2026-10 |
| Elsevier `elsarticle` (class) | v3.5 (2026-01-09); options `preprint`/`review`/`1p`/`3p`/`5p`/`authoryear`/`number`/`sort&compress`; `.bst` files `elsarticle-num`, `elsarticle-num-names`, `elsarticle-harv`; `keyword` and `highlights` environments | https://mirrors.ctan.org/macros/latex/contrib/elsarticle/doc/elsdoc.pdf | 2026-10 |
| Astroparticle Physics (journal) | page/word limits, reference style, abstract length, highlights requirement: not verified (publisher pages returned HTTP 403). Take them from the journal's Guide for Authors | https://www.sciencedirect.com/journal/astroparticle-physics/publish/guide-for-authors (not fetchable) | 2026-10 |
| A&A | `aa.cls`; Letters 3,000 words (search copy only, not verified); structured abstract optional (search copy). aanda.org returned HTTP 403; a "100-word Letter abstract" snippet conflicts and is unsourced | https://www.aanda.org/doc_journal/instructions/aadoc.pdf (not fetchable) | 2026-10 |
| Statistics journals (JASA, Annals of Statistics) | not verified: the Annals page defers to a "Preparation of Manuscripts" page that was not followed, and tandfonline returned HTTP 403 | https://imstat.org/journals-and-publications/annals-of-statistics/annals-of-statistics-manuscript-submission/ | 2026-10 |

# LaTeX Mechanics and Tooling

Cross-cutting LaTeX mechanics that apply regardless of which venue's class
file is in use — notation, tables, accessibility, diffing, build tooling,
and document structuring. See `latex-and-formatting.md` for venue-specific
class files, skeletons, arXiv rules, and length-limit tactics; this file is
everything that applies once the venue-specific setup is already done.

## Table of contents
- [Cross-referencing and notation macros](#cross-referencing-and-notation-macros)
- [Table syntax specifics](#table-syntax-specifics)
- [PDF accessibility (tagged PDF)](#pdf-accessibility-tagged-pdf)
- [Tracked changes and diffing](#tracked-changes-and-diffing)
- [Build automation (latexmk)](#build-automation-latexmk)
- [Bibliography backend: bibtex vs. biber/biblatex](#bibliography-backend-bibtex-vs-biberbiblatex)
- [Multi-file document structuring](#multi-file-document-structuring)
- [Non-ASCII names and encoding](#non-ascii-names-and-encoding)

## Cross-referencing and notation macros

- Always `\label{}` immediately after `\section`, `\begin{equation}`,
  `\begin{figure}`, or `\begin{table}` — a label placed elsewhere (e.g.
  inside a table's caption but outside a figure's) can silently pick up the
  wrong number.
- Use `\eqref{}` for equations (adds parentheses automatically) and `\ref{}`
  for everything else; the `cleveref` package's `\cref{}`/`\Cref{}` picks the
  right word ("Eq.", "Fig.", "Table") automatically from the label prefix.
  Adopt a consistent prefix convention (`eq:`, `fig:`, `tab:`, `sec:`) from
  the first label onward so `cleveref` — or a human skimming the source —
  can tell what's referenced at a glance.
- `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_manuscript.py` catches undefined `\ref`/`\cite` targets and
  duplicate `\label`s mechanically, but not a label that resolves without
  error yet points at the wrong equation/figure after reordering — check
  numbering visually after any significant section reordering.
- Define a symbol once with `\newcommand{\mysymbol}{...}` in the preamble
  (or a separate `notation.tex` pulled in with `\input{}`) rather than
  retyping a multi-part symbol (a fit parameter, a cross-section variable)
  throughout the manuscript. This is what keeps a symbol's definition from
  silently drifting across a long derivation — exactly the failure
  `equation-and-notation-auditing.md` audits for — and lets a notation
  change be made once instead of via a manuscript-wide find-and-replace
  that a hyphenated or spaced variant would slip past.
- A `\newcommand` collision with an existing LaTeX/package command fails
  loudly at compile time — don't silence it with `\renewcommand` unless the
  override is intentional.

## Table syntax specifics

Beyond `booktabs`'s `\toprule`/`\midrule`/`\bottomrule` (see
`figures-and-tables.md` for table *design* conventions — this section is the
LaTeX syntax to build one):

- **Aligning numbers with uncertainties**: `siunitx`'s `S` column type
  (`\begin{tabular}{l S[separate-uncertainty]}`) aligns a column of
  `125.09(24)`- or `125.09 \pm 0.24`-style values on the decimal point
  automatically — don't hand-pad with `\phantom{}`, which breaks the moment
  a value's digit count changes during revision.
- **Spanning cells**: `\multicolumn{2}{c}{...}` for a header spanning
  several columns, `\multirow{2}{*}{...}` (from the `multirow` package) for
  a label spanning several rows. Don't fake either with merged-looking but
  structurally separate cells — this breaks screen readers and any
  `\label`-based reference into the table.
- **Long tables spanning pages**: use the `longtable` package rather than
  manually splitting one table into several `table` environments — a
  manually split table loses its single caption/label, and referencing a
  specific row becomes ambiguous.
- **Footnotes inside tables**: use `threeparttable` (keeps footnote markers
  scoped to the table and printed directly below it) rather than a regular
  `\footnote{}` inside a `tabular`, which can float to the bottom of the
  page detached from the table it annotates.

## PDF accessibility (tagged PDF)

Several venues (ACM already requires it; more are moving this direction)
now require a tagged, accessible PDF — a structural layer a screen reader
uses to navigate headings, read tables cell-by-cell, and announce a
figure's alt text — not just a visually correct PDF.

- `pdflatex`/`lualatex` alone do not produce a tagged PDF; use the `tagpdf`
  package (LaTeX3-based, actively maintained) or a document class with
  built-in tagging support if the venue's template provides one — check the
  venue's current author guidelines, since support and required packages
  change as tagging tooling matures.
- Attach the alt text written using `figures-and-tables.md`'s
  accessible-descriptions guidance to the actual figure via the tagging
  package's alt-text hooks — alt text that exists only in a separate
  document handed to the user is not embedded accessibility; it must be in
  the PDF's structure tree to be usable by a screen reader.
- Tag reading order explicitly for multi-column layouts (PRL's
  `twocolumn`; JHEP's single-column is simpler) — a naive tagging pass can
  read across columns left-to-right instead of down one column then the
  next. Verify reading order with a PDF accessibility checker (e.g. Adobe
  Acrobat's or PAC's checker) before submission, not just visually.
- This is a young, fast-moving area of LaTeX tooling — verify current
  package support against the specific venue's requirement rather than
  assuming a fixed recipe, and ask the user whether the target venue
  currently mandates this before investing time in it.

## Tracked changes and diffing

For a referee response or a co-author review round that needs a visible
diff against a prior revision (see `submission-and-peer-review.md`'s
referee-response guidance, and `revision-impact-tracking.md` for tracking
*what* changed and why):

```
latexdiff old_version.tex new_version.tex > diff.tex
pdflatex diff.tex   # compile diff.tex like any other .tex file
```

- `latexdiff` marks deletions with strikethrough and additions
  underlined/colored directly in the compiled PDF — this is what most
  physics/stats venues mean by a "marked-up" or "tracked-changes" version
  accompanying a resubmission, not a Word-style comment thread.
- Run it on the two `.tex` source files, not on rendered PDFs. It operates
  on LaTeX source and can misfire on heavily restructured text (a moved
  paragraph can show as a spurious delete-and-add pair) — check the diff
  output visually rather than trusting it blindly after a large
  reorganization.
- For multi-file documents (`\input{}`/`\include{}`), use `latexdiff-vc` or
  run `latexdiff` per included file and reassemble, rather than diffing
  only the top-level `.tex` file, which will miss changes inside included
  files entirely.
- Strip the diff markup before final submission — the diff version is for
  referees/co-authors during review, not the camera-ready submission;
  `submission-and-peer-review.md` covers when a marked-up version is
  expected versus a clean one.

## Build automation (latexmk)

The "run bibtex/biber, then pdflatex twice more" four-pass compile
(`latex-and-formatting.md`'s common-compile-errors table) is exactly what
`latexmk` automates — use it instead of remembering the pass order by hand:

```
latexmk -pdf paper.tex        # compiles, reruns bibtex/biber and pdflatex
                               # as many times as references actually need
latexmk -pdf -pvc paper.tex   # continuous-preview mode: recompiles on save
latexmk -c paper.tex          # clean auxiliary files (.aux, .log, .bbl, ...)
```

- `latexmk` inspects the `.log`/`.aux` files to decide how many passes are
  actually needed, rather than a fixed four-pass ritual — it also reruns
  automatically when a cross-reference is still unresolved after a pass.
- Configure the bibliography engine (`bibtex` vs. `biber`) and default
  compiler (`pdflatex`/`xelatex`/`lualatex`) in a project's `.latexmkrc`
  file rather than passing flags every invocation — see the next two
  sections for which engine a given venue actually needs.
- Most CI setups that compile LaTeX on every push (a GitHub Action, for
  instance) call `latexmk` under the hood rather than reimplementing the
  pass logic — reach for it there too, not just locally.

## Bibliography backend: bibtex vs. biber/biblatex

These are two different, non-interchangeable systems — the venue's class
file and style determine which one is required:

- **Classic `bibtex` + a `.bst` style file**: what REVTeX, JHEP, AASTeX, and
  most physics/astroparticle venues ship. `natbib` (`\usepackage{natbib}`)
  layers author-year citation commands (`\citep{}`/`\citet{}`) on top of
  this system for ApJ/A&A/MNRAS-style venues; numbered-citation venues use
  the `.bst` file directly without `natbib`. INSPIRE-HEP/ADS BibTeX exports
  are plain `.bib` entries compatible with this system.
- **`biblatex` + `biber`**: a newer, more flexible system (native Unicode,
  more configurable citation/bibliography styles) driven by a `.bbx`/`.cbx`
  style pair instead of a `.bst` file. Some statistics/ML and ACL-family
  venues support or expect this; most REVTeX/JHEP/AASTeX-based physics
  venues do not — check the venue's template before assuming either is a
  drop-in swap for the other.
- **Do not mix them**: a `.bst` file needs `bibtex`; a `.bbx`/`.cbx` pair
  needs `biber`. Running the wrong engine against the wrong style produces
  confusing errors that look unrelated to the actual mismatch (missing
  citation commands, or a `.bst`-not-found error when `biber` was invoked).
  Check which style file the venue's template ships before configuring
  `latexmk` or invoking the engine directly.
- `biblatex`'s citation commands (`\autocite{}`, `\parencite{}`) look
  similar to `natbib`'s but are not interchangeable syntax — switching
  bibliography systems mid-project means updating every in-text citation
  command, not just the preamble configuration.

## Multi-file document structuring

For a document assembled from several files — a long thesis, or a
thesis-by-publication (`thesis-by-publication-assembly.md`) combining
several already-written papers as chapters:

- `\include{chapter1}` forces a page break and supports `\includeonly{}`
  to compile only a chosen subset of chapters — use this while drafting
  one chapter of a large document for faster iteration, then remove the
  restriction before a final full compile so cross-references between
  chapters are actually checked.
- `\input{}` does not force a page break and doesn't support
  `\includeonly{}` — appropriate for a smaller shared piece (a notation
  file, one section) rather than a full chapter.
- Typical structure: `main.tex` holds the preamble and
  `\include{introduction}`, `\include{paper1}`, `\include{paper2}`, ...,
  `\include{conclusion}`; each chapter file starts directly with
  `\chapter{}`/`\section{}` and has no preamble of its own.
- Put shared notation macros (see the cross-referencing-and-notation-macros
  section above) in one file pulled into `main.tex` once — not duplicated
  into each chapter file, which reintroduces the drift problem macros
  exist to prevent.
- If the institution requires each embedded paper to keep its own
  reference list rather than one merged bibliography, use `bibunits` or
  `chapterbib` rather than manually partitioning a single `.bib` file by
  hand — check the graduate school's formatting requirements for which is
  expected before choosing.

## Non-ASCII names and encoding

For author names with accents or non-Latin characters (common in large
international collaborations):

- With `pdflatex`, load `\usepackage[utf8]{inputenc}` (input encoding) and
  `\usepackage[T1]{fontenc}` (output font encoding) so accented characters
  in the `.tex` source (e.g. "Müller", "Núñez", "Söderström") typeset
  correctly in Computer Modern/Latin Modern — without both, some
  characters silently fail to render or need clunky escape sequences
  (`\"u` for ü) instead of being typed directly.
- XeLaTeX or LuaLaTeX support UTF-8 and system fonts natively, without
  `inputenc`/`fontenc` — if the venue's class file supports one of these
  engines (check its documentation; most APS/JHEP-family classes are
  `pdflatex`-first but often compatible), switching engines can sidestep
  encoding issues entirely for a large author list rather than patching
  each name.
- `unicode-math` (with XeLaTeX/LuaLaTeX) covers math symbols beyond the
  standard AMS set if a paper's notation needs them.
- For names in a non-Latin script, check the venue's specific policy —
  some indexes (INSPIRE-HEP records, for instance) support a native-script
  name field alongside the Latin-transliterated byline; don't assume
  transliteration alone satisfies a collaboration member's naming
  preference.
- Test-compile with the actual full author list early for a large
  collaboration paper — an encoding problem discovered at submission time,
  across dozens of institutions' worth of author names, is expensive to
  track down and fix under a deadline.

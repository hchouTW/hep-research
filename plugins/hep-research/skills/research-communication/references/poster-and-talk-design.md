# Poster and talk design

> Talk outlines and poster content derived from a communication record use the skeletons in
> `../assets/paper/audience-adaptation-templates.md` with a companion manifest checked by `check_adaptation.py`.

Use when converting a paper's content into a conference poster or an oral
presentation's slide deck. This is downstream of the paper, not a
replacement for it — use `figures-and-tables.md` for the publication-quality
figures themselves and `outreach-and-public-facing-summaries.md`
for a plain-language write-up; this file is about re-laying-out
already-established results for a room or a poster board, not re-deriving
prose structure.

## Posters

1. Identify the single result the poster must land from a few metres away
   or a thirty-second glance — a poster is read by people walking past, not
   read start-to-finish like a paper. State that result in the title or a
   large top-line statement, not buried in an abstract block.
2. Cut, don't shrink. A poster is not a paper reformatted into columns —
   drop derivation detail, secondary results, and extended related-work
   discussion; point to the paper/arXiv link (as a QR code or printed URL)
   for anyone who wants that. Keep only the figures and numbers needed to
   support the headline result.
3. Design figures for poster viewing distance: larger fonts and line weights
   than a paper figure, fewer overlapping series per panel, and captions
   that stand alone without requiring the body text alongside them. Reuse
   a paper figure's data, not its exact publication-sized rendering.
4. Order panels for a walking reader: motivation → method (brief) → key
   result → takeaway, left-to-right/top-to-bottom, so someone can follow the
   logic without the presenter narrating it.

### Formats and sizes

| Item | Starting point | Check |
|---|---|---|
| A0 poster, 841 x 1189 mm | `\documentclass[final]{beamer}` + `\usepackage[orientation=portrait,size=a0,scale=1.4]{beamerposter}`, or `\documentclass[25pt,a0paper,portrait]{tikzposter}` (both on CTAN, both compiled to A0 pages here, 2026-10-14) | `pdfinfo poster.pdf` shows the page size |
| US 48 x 36 in poster | set the paper size in the class options to the venue's stated size | the venue's poster instructions |
| Text sizes (heuristic, not a venue rule) | title about 80-100 pt, headings 40-60 pt, body at least 24 pt, figure labels at least 24 pt on A0; scale with the paper size | measure on the PDF at 100% |

Read the conference's poster instructions for the size and orientation; they override this table.

## Slide decks

0. **Format and approval.** Use 16:9 unless the venue says 4:3: Beamer
   `\documentclass[aspectratio=169]{beamer}` gives 160 x 90 mm pages (compiled 2026-10-14). Plan about one content
   slide per minute of the slot (a heuristic; dense result slides take longer). A collaboration talk usually needs
   the speaker's slides approved by the collaboration before it is given: ask which approval applies and record it.

1. One idea per slide. If a slide needs the presenter to say "there are
   three things going on here," split it. A slide's job is to support what
   is being said, not to contain everything that could be said.
2. Match depth to the audience and slot length: a 10-minute contributed talk
   supports one method slide and one or two result slides; a 45-minute
   seminar can carry the full derivation and multiple result sections that a
   short talk must cut. Do not port a paper's full structure into a short
   slot.
3. Put the punchline result on a slide early (after brief motivation), not
   only at the end — physics/stats talk audiences frequently need to know
   what to listen for during the method section.
4. Figures on slides need larger fonts and simpler legends than paper
   figures, and should build incrementally (reveal one series/panel at a
   time) when the comparison is the point, rather than presenting a dense
   multi-panel paper figure unchanged.
5. Prepare for the Q&A: back-up slides for likely systematic/statistical
   objections (e.g. the specific concern a referee raised) belong after the
   main deck's end, not inline.

## Diagrams on posters, in theses and in talks

### Format adjustments

| Target | Adjust |
|---|---|
| Poster | fewer nodes (<= ~8), text sizes from the table under Posters, one figure per poster section, no legends longer than 3 entries |
| Thesis | one figure per concept, numbered by chapter, full detail allowed (technical level), a symbol table in the list of symbols, vector PDF at text width |
| Slides | see below |

### Beamer overlays and talk simplification

Simplify by **abstraction level** (see `general-diagram-principles.md` section 6), not by shrinking: keep node identity
so the audience can follow the paper figure. For a talk, reduce to <= ~7 boxes, labels <= 3 words, drop legends by using
one edge style, and reveal the pipeline one stage at a time.

Beamer with TikZ, reveal stage by stage using `visible on` (compiled with Tectonic: 3 overlay pages, boxes stay in place):

```latex
% diagram-check: skip Beamer overlay fragment: needs a beamer frame, overlay-beamer-styles and the proc/flow styles of tikz-patterns.md
\begin{tikzpicture}[node distance=8mm]
  \node[proc] (a) {Trigger};
  \node[proc, right=of a, visible on=<2->] (b) {Reconstruction};
  \node[proc, right=of b, visible on=<3->] (c) {Selection};
  \draw[flow, visible on=<2->] (a) -- (b);
  \draw[flow, visible on=<3->] (b) -- (c);
\end{tikzpicture}
```
`visible on=<n->` needs `\usetikzlibrary{overlay-beamer-styles}`. Alternatives that avoid it: export one PDF per stage, or
`\only<n>{\includegraphics{...}}`. Keep positions fixed across overlays so nothing jumps.

Deliver poster/slide content mapped explicitly back to its source
figure/section in the paper, so a factual or numerical correction to the
paper can be propagated to the derived materials — do not let poster/slide
numbers drift from a since-revised paper value.

**Done when:** every number on the poster or slides maps to its paper figure or section, the page size and text sizes are checked on the PDF (`pdfinfo`, the size table), and the speaker or poster approval the collaboration requires is recorded.

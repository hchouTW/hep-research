# Figures and Tables

Publication figures are a different design problem than analysis plots made for
yourself or a collaboration meeting. This assumes plots already exist (e.g. from
ROOT/matplotlib work under `hep-analysis`) and focuses on turning them into
publication-quality figures with correct, complete captions. This is the design
side; use `interpreting-scientific-graphics.md` for the reading side — critically
interpreting a figure already in someone else's paper.

## Table of contents
- [What makes a figure publication-ready](#what-makes-a-figure-publication-ready)
- [Figure types and when to use them](#figure-types-and-when-to-use-them)
- [Caption writing](#caption-writing)
- [Tables](#tables)
- [Color and accessibility](#color-and-accessibility)
- [Accessible descriptions](#accessible-descriptions)
- [File formats and resolution](#file-formats-and-resolution)

## What makes a figure publication-ready

- **One clear message per figure.** If a figure needs a full paragraph to
  explain what to look at, either split it or redesign it (remove clutter,
  add an annotation/arrow, reorder panels).
- **Self-contained with the caption.** A reader flipping straight to the
  figures should understand the axes, what's plotted, and the headline
  takeaway without reading the main text.
- **Axis labels include units**, and are large enough to read at the
  journal's printed column width (test at ~8.6 cm wide for a single-column
  figure) — not just legible on a laptop screen.
- **Legends inside the plot area** (or a compact key in the caption) rather
  than a separate wide legend that wastes horizontal space in a two-column
  layout.
- **Uncertainty bands/error bars are present** on any data points or curves
  where they matter to the claim, and their meaning (stat only vs. stat+syst)
  is stated in the caption.

## Figure types and when to use them

| Goal | Good choice |
|---|---|
| Distribution comparison (data vs. MC/background) | Stacked histogram with data points + ratio panel below |
| Result vs. previous measurements | Horizontal "measurement comparison" plot (points with error bars, one row per measurement) |
| Exclusion/discovery reach | 2D exclusion contour, or Brazil-band limit plot |
| Correlation between two quantities | 2D scatter or profile histogram, or a correlation-coefficient table for many variables |
| Cutflow / selection efficiency | Table, not a figure, unless efficiency vs. a continuous variable is the point |
| Systematic breakdown | Stacked or grouped bar chart, or a table if there are more than ~6 sources |
| Cosmic-ray energy spectrum | Flux scaled by `E^n` (`n` ~2.6-3) vs. energy, log-log — see `astroparticle-and-cosmic-ray-papers.md` |
| Arrival-direction / significance skymap | All-sky equal-area projection (Mollweide/Hammer-Aitoff), coordinate system stated explicitly — see `astroparticle-and-cosmic-ray-papers.md` |
| Workflow, pipeline, architecture, graphical model, causal DAG, detector schematic, decay tree | A structural diagram as editable text (Mermaid, Graphviz, TikZ), not a data plot - use [academic-diagrams-guide.md](academic-diagrams-guide.md) |
| Training progress | Learning curve: loss/metric vs. epoch or step, train and validation on the same axes so overfitting is visible |
| Classifier performance | ROC or precision-recall curve (report AUC alongside the curve, not instead of it); confusion matrix for a fixed operating point |
| Comparing many methods on many datasets/tasks | Leaderboard-style table, not a figure, with the best result per column in **bold**, or underlined if bold is taken by the paper's own method |
| Isolating which component caused an improvement | Ablation table: one row per component removed/added, same metric column(s) as the main results table — see `physics-ml`'s `../../physics-ml/references/ablation-and-design-review.md` for how to design the ablation itself |

Avoid 3D plots for print publications — they rarely survive being flattened to
a static page and are hard to read precisely; a 2D projection or a pair of 2D
slices usually communicates more.

## Caption writing

A caption typically has three parts, in order:
1. **What is shown** — plot type, what's on each axis, what the data source is.
2. **How it was made**, briefly, if not obvious (selection applied, binning
   choice, what error bars represent).
3. **What to take away** — the one-sentence interpretation, especially for the
   paper's headline figure.

Example:
> Figure 2: Reconstructed dijet invariant mass distribution after the full
> event selection (points, with statistical uncertainties), compared to the
> background-only fit (solid line) and the signal-plus-background fit (dashed
> line). The lower panel shows the fit residuals in units of the statistical
> uncertainty. The excess near 750 GeV corresponds to a local significance of
> 2.1σ.

Keep captions self-contained but not redundant with the main text — the main
text can discuss implications at length; the caption states facts about the
figure itself.

## Tables

- Use tables (not prose) for anything with more than ~4 numeric values a
  reader might want to look up individually — systematic uncertainty
  breakdowns, cutflows, results across multiple channels/bins.
- One consistent number of significant figures/decimal places per column.
- State units in the column header, not repeated in every cell
  (`p_T [GeV]`, not `p_T = 42 GeV`, `p_T = 51 GeV`, ...).
- For cutflow tables, include both absolute yield and relative/cumulative
  efficiency — either alone forces the reader to do arithmetic.
- `booktabs` (`\toprule`/`\midrule`/`\bottomrule`) rather than full grid
  lines is the near-universal house style for physics journals; avoid
  vertical rules.

## Color and accessibility

- Use colorblind-safe palettes (e.g. Okabe-Ito, or ROOT's `kViridis`/
  `kCividis`) rather than default red/green distinctions.
- Ensure figures remain interpretable in grayscale — many readers print or
  view PDFs without color; use distinct line styles (solid/dashed/dotted) in
  addition to color for curves.
- Do not rely on color alone to distinguish more than ~4-5 categories; add
  markers or hatching.

For every scientifically meaningful distinction, provide a non-color cue when
needed, even with only two categories. Inspect at the intended display/print size:
text, markers, error bars, and line patterns must remain distinguishable. A palette
name alone does not establish accessibility; check actual contrast and encodings.

## Accessible descriptions

Use for figure alt text, longer descriptions, and accessible presentation of
scientific findings. Inspect the actual figure and caption before describing it;
if unavailable, label any draft based on supplied text as provisional. Preserve
the scientific claim and uncertainty when simplifying language. This section is
about writing the description; see `latex-mechanics-and-tooling.md`'s PDF-accessibility
section for actually embedding it in a tagged PDF's structure tree, which is what
a screen reader needs to reach it.

Write concise alt text identifying the figure's purpose, plot type, variables,
and main observed relationship. Include units, scale, or uncertainty when needed
to interpret that relationship. Describe series by scientific identity rather
than color alone. Do not transcribe every tick or repeat a nearby caption verbatim;
use the caption for methodological detail and the description for access to visual
information that would otherwise be lost.

For a dense or multi-panel figure, supply a longer description with panel order,
axes/scales, series, key patterns, and exceptions. Distinguish visible trends from
statistical conclusions requiring analysis: overlapping error bars alone do not
establish a significance test. Use source data for exact values; do not invent
precision from pixels. Link a machine-readable table when detailed lookup matters.

For tables, retain text-based cells, explicit headers and units, clear missing-value
definitions, and a sensible reading order. Avoid conveying a winner, significance,
or grouping solely through color, boldface, or spatial placement. Explain those
meanings in text without overstating what the analysis establishes.

Deliver descriptions mapped to stable figure/table labels and concrete visual fixes.
If editing the artifact, use the format's supported alt-text, tagging, and reading-
order features and inspect the exported result with available document tools.
Writing an alt-text draft does not prove it is embedded in the final PDF or that
the document is accessible. State what was actually checked; consult current
official requirements before claiming compliance with a named standard or venue.

## File formats and resolution

- Vector formats (PDF, EPS) for anything that's lines/text/histograms — they
  stay sharp at any zoom and keep file size small.
- Raster (PNG at ≥300 dpi) only for genuinely raster content (detector event
  displays, photographs, heatmaps with very many points where vector output
  would bloat file size).
- Avoid re-exporting a raster screenshot of a vector plot — regenerate from
  source (ROOT macro / matplotlib script) at the target format instead.

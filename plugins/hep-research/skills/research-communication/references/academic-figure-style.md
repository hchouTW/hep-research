# Academic Figure Style

## Typography

- Sans-serif for labels (Helvetica/Arial-like, or the paper's font); math via LaTeX syntax
  (`$p_T$`, `$\theta$`) so it typesets in the paper's font.
- Final printed size >= 6-7 pt (aim 8 pt); test by scaling to the column width.
- Hierarchy: one size for node text, one slightly smaller for edge labels/annotations,
  one bolder for group titles. No more than three sizes.
- Preserve notation exactly as defined in the paper (`\hat{\theta}` vs `\theta`, `\mathcal{L}`).
  Do not re-letter symbols for layout reasons.

## Color

- Grayscale-safe by default: verify by mentally (or actually) desaturating. Distinguish by
  fill lightness + border/line style + shape + label.
- Color for semantic grouping only: data vs simulation, signal vs background, training vs
  inference, deterministic vs stochastic, detector subsystems, software layers.
- Colorblind-safe palette, e.g. Okabe-Ito: `#000000 #E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7`
  (avoid red/green as the only contrast). Use <= 4 hues per figure.
- Keep the same color for the same concept across every figure in a paper.

## Line and shape vocabulary (suggested, declare in a legend when used)

| Meaning | Encoding |
|---|---|
| process / computation | rectangle, light fill |
| data / artifact | rounded rectangle or parallelogram |
| storage | cylinder |
| decision | diamond |
| observed variable | shaded circle |
| latent variable | unshaded circle |
| parameter / hyperparameter | small square or bare symbol |
| learned component | double border or bold outline |
| training-only | dashed border |
| inference-only | dotted border or separate group |
| simulation | dashed outline; data solid |
| control flow | dashed arrow; data flow solid |

## Column and page geometry

| Target | Width (typical, verify against the venue template) |
|---|---|
| Single column (REVTeX/APS) | 8.6 cm (3 3/8 in), stated on the APS journal "Information for Contributors" pages (e.g. PRB); "1.5 or 2 columns may be used" when detail requires it |
| Double column span (REVTeX/APS) | neither APS nor the REVTeX 4.2 guide states a width; the class sets `\textwidth` = 510 pt = 17.92 cm in two-column mode (measured with `revtex4-2` under Tectonic, `reprint`, `aps,prl,twocolumn`, `aps,prd,reprint`). Page-spanning figures use `figure*`; draw at 17.8 cm (7 in) or `\textwidth` |
| JHEP (`jheppub`, `11pt,a4paper`) | text width `.72\paperwidth` = 430 pt = 15.1 cm (measured by compiling `jheppub.sty` v1.1227); 11 pt body, captions `\small` and centered when they fit on one line |
| NeurIPS 2026 | text width 5.5 in (13.97 cm), single column, 10 pt Times body (`neurips_2026.sty`) |
| ICML 2026 | two columns; overall text width 6.75 in (17.1 cm), 0.25 in between columns, so each column is 3.25 in (8.26 cm); left margin 0.75 in |
| ICLR 2026 | single column, text width 5.5 in (13.97 cm), 10 pt Times body (`iclr2026_conference.sty`; ICLR 2027's file sets the same) |
| Beamer 16:9 | ~ full slide; text >= 14-18 pt |
| Poster | text >= 24 pt for labels |

None of JHEP, NeurIPS, or ICLR sets a minimum font size for text inside figures: apply the 6-7 pt floor above and
aim to match the caption size (JHEP `\small` = 10 pt; NeurIPS/ICLR captions are 10 pt with a 10 pt body). Their figure
rules (checked 2026-09-25 against the NeurIPS 2026 and ICLR 2026 templates and the JHEP author manual shipped with
`jheppub`): **NeurIPS / ICLR** - artwork "neat, clean, and legible", lines dark enough to reproduce, caption *after*
the figure in lower case (except the first word and proper nouns), color allowed but caption and text should make
sense printed in black and white; NeurIPS also requires Type 1 or embedded TrueType fonts only (check with `pdffonts`).
**JHEP** - caption below the figure; refer to "figure 2" in the text, never "fig. 2"; raster images at 150-250 dpi;
vector images with fonts embedded; remove transparency layers; float figures to the top of a page.

Venue figure-quality rules found in the same sources: APS - lettering at least 2 mm high after reproduction, lines at least 0.18 mm (0.5 pt), 600 dpi or more for raster art; ICML - lines at least 0.5 pt, no text on a gray background, Type-1 fonts only. (A 2 mm cap height is roughly an 8 pt font; the 6-7 pt minimum above is a floor, not a target.) Checked 2026-09-21 against: the ICML 2026 example paper (widths above, plus figure lines at least 0.5 pt thick, no text on a gray background, and Type-1 fonts only - avoid Type-3 fonts from exported figures), the NeurIPS 2026 formatting instructions, the JHEP `jheppub` documentation, and the APS RMP style guide
(JHEP/NeurIPS/ICLR re-checked 2026-09-25 from the style files themselves). Re-check each year and for every journal. These are common defaults, not guarantees: read the venue's author kit. Design at final size;
avoid scaling a large figure down until the text is unreadable. Prefer vector (PDF/SVG) output.

## Panels and multi-figure consistency

- Panels `(a) (b) (c)` labeled consistently top-left; each panel one message; shared node names.
- One `figure_style` block for the whole paper:

```yaml
figure_style:
  orientation: left-to-right     # or top-to-bottom
  typography: academic           # sans labels, LaTeX math
  color_policy: grayscale-safe
  edge_style: semantic           # style encodes meaning; legend when >1
  math_format: latex
  abstraction: paper             # overview | paper | presentation | technical | educational
  output: svg                    # or pdf / tikz
```

- Keep a symbol table (figure label <-> paper symbol) to guarantee the figure matches the text.

## Equations inside diagrams

Put short equations on nodes/edges only when they are the point (`$p(\theta \mid x)$`). Long
equations belong in the text; reference them ("Eq. 3") only if the paper's numbering is known -
do not invent numbers.

## Talks, posters, theses

- Talk: 3-7 nodes, one idea per slide, build progressively (reveal stages), large labels.
- Poster: one dominant flow, minimal prose, high contrast.
- Thesis: may use paper level in the body and the detailed technical version in an appendix.
- Beamer: TikZ overlays (`\onslide<2->`) or Mermaid/SVG exported per step.

## Export

Prefer vector: SVG -> PDF (Inkscape/`rsvg-convert`), Graphviz `dot -Tsvg|pdf`, Mermaid
`mmdc -o fig.svg`, TikZ compile natively (or `standalone` class for a cropped PDF). State any
external tool needed; do not assume it is installed.

## Final readability check

Grayscale test; column-width test; can a reader in the field name every arrow's meaning without
the caption? Is anything in the figure absent from the text (or vice versa)?

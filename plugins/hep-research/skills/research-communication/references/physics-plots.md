# Physics plots

How a quantitative physics plot should look and what it must say: status labels, ratio panels, uncertainty bands,
vector output and fonts, colour, raster resolution, and the conventions of cosmic-ray, astroparticle and neutrino
figures. The plotting code is hep-computing's (matplotlib with `mplhep`, ROOT `TStyle`); the numbers come from the
result artifacts; the physics of a model curve is hep-theory's. This file is the single home for colour and raster
rules of plots; `figures-and-tables.md` covers figure types, captions and tables, `diagram-figure-style.md` diagrams.

## Starting points (code lives in hep-computing)

- matplotlib with [`mplhep`](https://github.com/scikit-hep/mplhep) (Scikit-HEP; experiment styles and HEP histogram
  plotting; installed only with the user's approval) or ROOT with a `TStyle` set once per figure set.
- Set fonts and sizes once for the whole set; draw at the printed width (the venue's column width in
  `diagram-figure-style.md`, "Column and page geometry"), not scaled afterwards.

## Status label on every figure

The figure carries the status of the result it shows, as the text does (SKILL.md invariant):

| Result status | Label on the figure | Who decides |
|---|---|---|
| `preliminary` | "Preliminary" | the collaboration's approval process (`collaboration-results-lifecycle.md`) |
| simulation only, `synthetic`, `asimov` | "Simulation", "Synthetic data", "Asimov" | the author; never omitted |
| internal, not approved | "Internal" or "Work in progress"; never shown outside the collaboration | the collaboration |
| `observed`, published | no label, or the collaboration's published-figure mark | the collaboration |

A figure that drops the label of a non-published result misstates its status, whatever the caption says.

## Ratio panels and uncertainty bands

- Data/MC (or data/fit) ratio below the main panel, sharing the x axis (no x tick labels on the upper panel).
  Choose a ratio range that shows the points (e.g. 0.5-1.5) and mark points outside it with arrows.
- Say in the legend or caption which uncertainty each band shows: statistical only, or statistical ⊕ systematic,
  and whether it belongs to the data or to the prediction. Do not draw the same uncertainty twice (on the points and
  in the band).
- Log axes for steeply falling distributions, with minor ticks; never a log axis on a ratio.
- Axis labels with units in brackets (`$p_\mathrm{T}$ [GeV]`, `R [GV]`); a per-bin quantity says per what
  (`Events / 10 GeV`).

## Vector output and fonts

- Save PDF (or SVG); raster only for genuinely raster content (event displays, sky maps from images).
- matplotlib's default `pdf.fonttype = 3` embeds Type 3 fonts, which some journals refuse; set
  `matplotlib.rcParams["pdf.fonttype"] = 42` (TrueType; checked 2026-10-14 with matplotlib 3.11: `pdffonts` shows
  `Type 3` by default and `CID TrueType` with 42). Check every figure with `pdffonts f.pdf`: no `Type 3`, all fonts
  embedded (`emb` = yes).

## Colour and raster resolution

- Palettes safe for colour-vision deficiencies (Okabe-Ito; viridis/cividis for maps); never red/green alone; a
  non-colour cue (marker, line style, hatching) for every meaningful distinction.
- Check on renders, not by eye: a greyscale copy (`pdftoppm -gray -r 150 -png f.pdf f_gray`) and a colour-vision
  simulation (`diagram-figure-style.md`, "Color"); without a simulator the check is reported as not done.
- Raster at 300 dpi or more at the printed size by default; **the venue's rule wins**: APS asks 600 dpi or more for
  raster art, JHEP 150-250 dpi (sources and dates in `diagram-figure-style.md`, "Column and page geometry").

## Cosmic-ray and astroparticle figures

- **Flux spectra.** Against rigidity R, the flux in m⁻² sr⁻¹ s⁻¹ GV⁻¹ is usually multiplied by R^2.7 so that the
  spectrum is nearly flat (axis unit then m⁻² sr⁻¹ s⁻¹ GV^1.7); against kinetic energy per nucleon, Φ × E_K^2.7.
  State the power in the axis label.
<!-- example: experiment-specific illustration -->
  (Convention seen in AMS PRL 126, 041104 (2021), INSPIRE 1844651, full text opened 2026-10-14.)
<!-- /example -->
  Converting between rigidity and kinetic energy per nucleon needs a mass-to-charge (isotope)
  assumption: hand the conversion to hep-theory and state the assumption in the caption.
- **Bin positions.** In wide bins of a steeply falling spectrum, place each point at the abscissa where the spectrum
  takes its bin-average value (Lafferty and Wyatt, Nucl. Instrum. Meth. A 355 (1995) 541,
  doi:10.1016/0168-9002(94)01112-5, INSPIRE `Lafferty:1994cj`), for an assumed spectral shape that the caption names
  (for example a flux ∝ R^-2.7). The calculation belongs with the analysis, not the plot.
- **Ratios** (p̄/p, B/C, isotope ratios): plotted unmultiplied, on a linear or log axis chosen for the range, with the
  numerator and denominator binning stated when they differ.
- **Time-resolved fluxes**: time axis in the unit the data use (Bartels rotations of 27 days, months), with the
  solar-modulation period and, for charge-sign effects, the heliospheric polarity epoch stated.
- **Systematic breakdown**: a table of the components per bin (`figures-and-tables.md`, "Tables") plus, where useful, a
  stacked or line plot of the relative contributions against R or E; the total equals the quadrature sum shown.
- **Neutrino oscillation figures**: Δm²-sin²θ contours name the interval construction (Feldman-Cousins, Wilks, a
  Bayesian credible region) and the confidence levels drawn; L/E plots state the baseline and energy definition.
  The construction itself is hep-statistics'.

## Pre-submission checklist

- [ ] `pdffonts` on every figure: no Type 3, all embedded.
- [ ] Status label on the figure matches the result's status in the `communication` record.
- [ ] Every axis has a label with units; every band is named; the ratio panel shares the x axis.
- [ ] Greyscale render readable; colour-vision simulation run (or reported not done).
- [ ] Drawn at the venue's printed width; smallest text at least the size floor in `diagram-figure-style.md`.

**Done when:** the checklist above passes for every figure, and each figure's numbers trace to a result artifact.

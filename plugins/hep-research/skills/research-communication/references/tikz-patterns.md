# TikZ / LaTeX Patterns

Use when the figure should be native LaTeX: exact fonts, math labels, Beamer overlays, precise
placement, plates, Feynman diagrams. Always state the dependencies and the engine.

## Preamble (state it in the answer)

```latex
\usepackage{tikz}
\usetikzlibrary{positioning, arrows.meta, shapes.geometric, fit, backgrounds, calc}
% optional: \usepackage{pgfplots}   \usepackage{tikz-cd}   \usepackage{tikz-feynman}
```
For standalone cropped output: `\documentclass[tikz,border=2pt]{standalone}`.

## Styles once, reuse everywhere

```latex
\tikzset{
  proc/.style   = {draw, rounded corners=2pt, minimum height=8mm, minimum width=22mm, align=center, font=\small},
  data/.style   = {proc, fill=gray!12},
  sim/.style    = {proc, dashed},
  learned/.style= {proc, line width=1.2pt},
  flow/.style   = {-{Stealth[length=2mm]}},                 % data flow
  ctrl/.style   = {-{Stealth[length=2mm]}, dashed},          % control flow
}
```

## Pipeline

```latex
\begin{tikzpicture}[node distance=8mm and 10mm]
  \node[data]  (raw)  {Detector\\data};
  \node[proc, right=of raw]  (rec) {Event\\reconstruction};
  \node[proc, right=of rec]  (sel) {Event\\selection};
  \node[proc, right=of sel]  (fit) {Likelihood\\fit};
  \draw[flow] (raw) -- (rec); \draw[flow] (rec) -- (sel); \draw[flow] (sel) -- (fit);
\end{tikzpicture}
```
Use `positioning` (`right=of`) rather than absolute coordinates so edits do not break layout.
Scale with `\resizebox{\columnwidth}{!}{...}` only as a last resort (it scales fonts): prefer
setting `node distance`/widths to fit the column.

## Graphical model with plate

```latex
\begin{tikzpicture}[latent/.style={circle,draw,minimum size=8mm},
                    obs/.style={latent,fill=gray!25}]
  \node[latent] (theta) {$\theta$};
  \node[latent, below=of theta] (z) {$z_i$};
  \node[obs, right=of z] (x) {$x_i$};
  \draw[-{Stealth}] (theta) -- (z); \draw[-{Stealth}] (z) -- (x); \draw[-{Stealth}] (theta) -- (x);
  \begin{scope}[on background layer]
    \node[draw, rounded corners, fit=(z)(x), inner sep=4mm, label={[anchor=south east]south east:$N$}] {};
  \end{scope}
\end{tikzpicture}
```
`fit` builds the plate around exactly the nodes it names; the index label goes in its corner.

## Feynman diagrams (tikz-feynman)

Needs `\usepackage[compat=1.1.0]{tikz-feynman}` (without `compat` the package warns on every run).
`\feynmandiagram` with automatic layout needs LuaLaTeX. Under pdfLaTeX/XeLaTeX it still compiles (exit 0,
only a "LuaTeX is required" warning) but ignores the layout keys and draws overlapping, garbled lines -
always inspect the output. For a portable result place vertices by hand:

```latex
\begin{tikzpicture}
  \begin{feynman}
    \vertex (a);
    \vertex [above left=of a]  (i1) {\(e^{-}\)};
    \vertex [below left=of a]  (i2) {\(e^{+}\)};
    \vertex [right=of a]       (b);
    \vertex [above right=of b] (f1) {\(\mu^{+}\)};
    \vertex [below right=of b] (f2) {\(\mu^{-}\)};
    \diagram* {
      (i1) -- [fermion] (a) -- [fermion] (i2),
      (a)  -- [photon, edge label=\(\gamma^{*}\)] (b),
      (f1) -- [fermion] (b) -- [fermion] (f2),
    };
  \end{feynman}
\end{tikzpicture}
```
(compiled with Tectonic, LuaLaTeX, and pdfLaTeX and inspected; incoming/outgoing arrow orientation checked).
LuaLaTeX automatic layout (compiled with LuaHBTeX 1.24 / TeX Live 2026 and inspected: clean layout, correct
arrows; the algorithm puts `e^+` on top and `e^-` below, the reverse of the manual version, so check label
positions against the text):

```latex
% e+ e- -> gamma* -> mu+ mu- (QED, illustrative); LuaLaTeX, automatic layout
\feynmandiagram [horizontal=a to b] {
  i1 [particle=\(e^-\)] -- [fermion] a -- [fermion] i2 [particle=\(e^+\)],   % e+ in: arrow points away from vertex
  a -- [photon, edge label=\(\gamma^*\)] b,
  f1 [particle=\(\mu^+\)] -- [fermion] b -- [fermion] f2 [particle=\(\mu^-\)],
};
```
Adjust arrow orientation for antiparticles (`anti fermion`), use `boson` for W/Z (with `edge label`),
`gluon`, `scalar` for Higgs, `photon`. Only draw the process the user specified; verify charge and
fermion-flow conservation at every vertex; label the result "schematic" when it has not been
checked against a theory model. Compile and inspect: layout bugs (crossed lines, wrong incoming
orientation) are common.

## Commutative / mapping diagrams

`tikz-cd`: `\begin{tikzcd} X \arrow[r,"f"] \arrow[d,"g"'] & Y \arrow[d,"h"] \\ Z \arrow[r,"k"'] & W \end{tikzcd}`.
State whether the diagram is claimed to commute.

## Detector schematic (conceptual)

Concentric `circle`/`rectangle` layers around an IP marker, labeled outward (tracker, ECAL, HCAL, muon),
a beam-axis arrow, and the note "not to scale". No numeric radii unless provided.

## Beamer

Use `\only<2->{...}`, `\onslide<2->` or `\visible` on nodes/edges for progressive reveal;
`[overlay]` remember-picture for annotating.

## Pitfalls

- Missing library -> obscure errors; list required `\usetikzlibrary` items.
- `\resizebox` shrinks text below legibility; check final point size.
- Colors: define with `xcolor` names; verify grayscale.
- Text in nodes: use `align=center` with `\\`, set `text width` for wrapping.
- Externalize (`\usetikzlibrary{external}`) for large figures to speed compile.
- The snippets here are unverified by compilation; compile and inspect before publishing.

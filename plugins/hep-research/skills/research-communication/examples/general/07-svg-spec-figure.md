# General 7: SVG-spec figure (train / validation / test workflow)

**Request:** "Give me an editable SVG of the train/validation/test workflow that I can polish in Inkscape."
**Diagram type:** workflow, paper level, left-to-right, as a hand-placed SVG (custom coordinates because the branch layout is small and fixed). Solid arrow = data flow; dashed arrow = hyperparameter tuning; thick outline = the selected model; gray fill = data not used for fitting.

**Spec (from `../../templates/svg-spec.md`):**

| item | value |
|---|---|
| canvas | 640 x 224 px viewBox, no background rect; Helvetica/Arial 12 px (10 px for notes) |
| grid | columns at x = 20, 170, 330, 500; rows at y = 20, 78, 136 (raw/split centered at y = 70); nodes 44 px high, 100-120 px wide |
| nodes | raw (20,70), split (170,70), train (330,20), val (330,78), test (330,136), model (500,20), eval (500,136) |
| edges | orthogonal paths; shared bus at x = 300 leaving split; arrowhead marker `arrow` |
| groups | `nodes`, `labels`, `edges`, `edge-labels` (one style per group, so a restyle is a one-line edit) |
| accessibility | `<title>`; meaning also carried by dash pattern and outline weight, not by color alone |

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 224" width="640" height="224" font-family="Helvetica, Arial, sans-serif" font-size="12">
  <title>Train, validate, test workflow</title>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#000"/>
    </marker>
  </defs>
  <g id="nodes" stroke="#000" stroke-width="1.2" fill="#fff">
    <rect id="raw"   x="20"  y="70" width="100" height="44" rx="6" fill="#e6e6e6"/>
    <rect id="split" x="170" y="70" width="100" height="44" rx="6"/>
    <rect id="train" x="330" y="20" width="110" height="44" rx="6"/>
    <rect id="val"   x="330" y="78" width="110" height="44" rx="6"/>
    <rect id="test"  x="330" y="136" width="110" height="44" rx="6" fill="#e6e6e6"/>
    <rect id="model" x="500" y="20" width="120" height="44" rx="6" stroke-width="2.4"/>
    <rect id="eval"  x="500" y="136" width="120" height="44" rx="6"/>
  </g>
  <g id="labels" text-anchor="middle" dominant-baseline="middle" fill="#000">
    <text x="70"  y="92">Raw data</text>
    <text x="220" y="92">Split</text>
    <text x="385" y="42">Train set</text>
    <text x="385" y="100">Validation set</text>
    <text x="385" y="158">Test set</text>
    <text x="560" y="42">Model</text>
    <text x="560" y="158">Final evaluation</text>
  </g>
  <g id="edges" stroke="#000" stroke-width="1.2" fill="none" marker-end="url(#arrow)">
    <path d="M120,92 H170"/>
    <path d="M270,92 H300 V42 H330"/>
    <path d="M270,92 H330"/>
    <path d="M270,92 H300 V158 H330"/>
    <path d="M440,42 H500"/>
    <path d="M440,100 H470 V52 H500" stroke-dasharray="5 3"/>
    <path d="M560,64 V136"/>
    <path d="M440,158 H500"/>
  </g>
  <g id="edge-labels" font-size="10" fill="#000">
    <text x="474" y="84">tune</text>
    <text x="445" y="34">fit</text>
  </g>
  <text x="20" y="200" font-size="10" fill="#000">Solid = data flow; dashed = hyperparameter tuning (validation only).</text>
  <text x="20" y="214" font-size="10" fill="#000">No arrow runs from the test set into training.</text>
</svg>
```

**Checks:** the file is well-formed XML and was rasterized with `rsvg-convert` and inspected. The first render exposed a test set with no outgoing edge (the "Final evaluation" node was added) and a clipped footnote (moved to two lines). Every edge endpoint lies on a node border; the test set only feeds the final evaluation; validation feeds tuning only; text is real `<text>` (editable), not paths.
**Caption:** Data-partitioning workflow. Raw data are split into training, validation, and test sets. The model is fit on the training set; the validation set is used only to tune hyperparameters (dashed). The test set is used once, for the final evaluation of the selected model (thick outline).

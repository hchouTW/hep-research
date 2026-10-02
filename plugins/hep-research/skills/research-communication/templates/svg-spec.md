# Template: SVG Spec

**Use for:** a custom figure whose layout must be exact or hand-polished (Inkscape/Illustrator), a small fixed
diagram where an automatic layout engine would move things, or an output that must be text but not Mermaid/DOT/TikZ.
Not for large graphs (use Graphviz) or Feynman diagrams (use TikZ).
**Assumption line:** state the canvas, units, and which shapes carry which meaning.

## Spec table (fill before writing any markup)

| item | decide |
|---|---|
| canvas | viewBox width x height, units (px); background (none / white) |
| type | font family, sizes (body, notes), minimum size at final column width |
| grid | column x-positions, row y-positions, node width/height, gap; snap everything to it |
| nodes | id, label (short), shape, fill, outline weight, meaning of that style |
| edges | from id, to id, route (straight / orthogonal / curve), style, label, meaning |
| groups | `nodes`, `labels`, `edges`, `edge-labels`, optional panels; style set once per group |
| legend | one entry per distinct fill, dash pattern, and arrow style |
| accessibility | `<title>`/`<desc>`; meaning never by color alone (dash, weight, shape, or label as well) |

## Skeleton

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200" width="640" height="200"
     font-family="Helvetica, Arial, sans-serif" font-size="12">
  <title>Figure title</title>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#000"/>
    </marker>
  </defs>
  <g id="nodes" stroke="#000" stroke-width="1.2" fill="#fff">
    <rect id="a" x="20"  y="70" width="100" height="44" rx="6"/>
    <rect id="b" x="170" y="70" width="100" height="44" rx="6"/>
  </g>
  <g id="labels" text-anchor="middle" dominant-baseline="middle" fill="#000">
    <text x="70"  y="92">Input</text>
    <text x="220" y="92">Process</text>
  </g>
  <g id="edges" stroke="#000" stroke-width="1.2" fill="none" marker-end="url(#arrow)">
    <path d="M120,92 H170"/>
  </g>
</svg>
```

## Rules

- Label centers = node center (`x + width/2`, `y + height/2`); compute, do not eyeball.
- Edges end on node borders; when several edges leave one node, share a bus segment and branch.
- Give every node an `id`; refer to the same ids in the caption and in the logical-graph table.
- Prefer `<text>` over outlined text so the figure stays editable; embed no raster images.
- Keep a dashed arrow, thick outline, or gray fill only if the legend or caption says what it means.

## Checks

Well-formed XML (`python3 -c "import xml.dom.minidom as m; m.parse('f.svg')"`); render it
(`rsvg-convert f.svg -o f.png` or a browser) and look at it - overlaps, clipped text, and edges with
no target are only visible in the render. `${CLAUDE_PLUGIN_ROOT}/skills/research-communication/scripts/check_diagram_sources.py` checks XML well-formedness
of fenced `svg` blocks. Worked example: `../examples/general/07-svg-spec-figure.md`.

# Academic Diagrams (guide)

## When to read this file

This file is the migrated routing and rules of the legacy `academic-diagrams` skill (agentic-ai-skills@3e995a4). Read it when a research-communication task falls in its scope; the reference files it routes to are linked relative to this file.

A scientifically literate figure-design assistant. **Build the correct scientific
model of the figure first, then render it.** Never start from boxes and arrows.

```text
Scientific meaning -> Logical graph -> Visual grammar -> Layout -> Rendering format
```

## When to Use / Not Use

Use for structural diagrams (things, stages, relations). Not for quantitative data
plots (histograms, spectra, fit results) - those belong to `hep-analysis` /
[figures-and-tables.md](figures-and-tables.md). Division of labor with
[academic-papers-guide.md](academic-papers-guide.md): it owns the scientific narrative and method interpretation; this
guide owns diagram selection, abstraction, specification, validation, and captions.

## Workflow

1. **Context** - what is being communicated, to whom (paper / thesis / talk / poster / docs)?
2. **Purpose** - one message per figure. If more than one, decompose (see below).
3. **Extract** - entities, processes, inputs, outputs, decisions, loops, uncertainty,
   interactions. Tag each **Known** (stated), **Inferred** (reasonable), or
   **Assumed** (needs a scientific assumption).
4. **Edge semantics** - decide what every arrow means (data flow, control flow, causal
   influence, dependency, time, mapping, physical interaction, message). One meaning
   per style; legend if mixed.
5. **Diagram family** - use the selection table.
6. **Abstraction level** - overview / paper / presentation / technical / educational.
7. **Logical graph** - nodes, typed edges, groups, in a neutral list before any syntax.
8. **Validate** - run the domain checklists in the references (below).
9. **Layout** - direction, grouping, crossings; then **render** in the chosen format.
10. **Caption** and, if useful, in-text reference sentence.
11. **Readability check** - grayscale, column width, minimum font, arrow clarity.

For simple requests collapse steps 1-9 mentally and return only what Output Style asks.

## Diagram Selection

| Source describes | Use |
|---|---|
| Sequential actions, branching, loops | Flowchart |
| Scientific processing stages | Pipeline (LR) |
| Interacting components, deployment | Architecture / component diagram |
| Message order and timing | Sequence diagram |
| Probabilistic dependence among variables | Graphical model (DAG / factor graph / plates) |
| Causal assumptions stated explicitly | Causal DAG |
| Particle process, decay chain | Decay tree; Feynman-style only if the process is given |
| Hierarchy | Tree |
| Database entities | ER diagram |
| Mathematical (non-temporal) dependence | Dependency graph |
| Layered detector / apparatus | Schematic layer diagram |
| Network topology | Network diagram |
| Neural / ML model | Model-architecture diagram |

State the chosen type when non-obvious. Requests that fit two families: pick the one
matching the message, mention the other as an alternative.

## Output Formats

| Format | Prefer for |
|---|---|
| Mermaid | flowcharts, pipelines, sequence, state, docs/README (editable, renders on GitHub) |
| Graphviz DOT | dense DAGs, dependency and probabilistic graphs, complex workflows |
| PlantUML | UML, component, sequence in software docs |
| TikZ / LaTeX | publication-native figures; `tikz-feynman` for Feynman diagrams; declare packages |
| SVG spec | custom figures: canvas, nodes, coordinates, edges, labels, groups, alignment |
| ASCII | quick sketch, terminal, early prototype |

Default: one format matched to the use. Offer more only when they serve different
purposes (ASCII preview -> Mermaid docs -> TikZ paper). Do not emit all formats.
Text sources beat raster images. Never claim a source was rendered/compiled unless it
was actually run.

## Output Style

Normally return: **Diagram type** - short rationale - **source** - optional **caption**
- optional **scientific notes / assumptions**. Simple request: type + source + caption.
Even for a simple request, always state in one line what the arrows mean, and say when the figure
was drawn from a description or listing only (so edges and counts beyond it are unknown). Draw
control flow (who triggers whom) and data flow with different line styles when both appear. They
both appear whenever the request says a component splits, dispatches or calls others: draw those
edges in a second style with a legend entry, never omit them, and list unstated triggers as open
questions. Add no node the request did not name; list extra steps as open questions instead.

## Publication Standards (summary; detail in `diagram-figure-style.md`)

- Clarity over decoration; short labels (<= ~4 words), math in LaTeX syntax. In Mermaid, single-`$` math does not render;
  use `$$...$$` (renderer-dependent) or plain Unicode (θ, α) in labels.
- LR for computational pipelines, TB for research processes, hierarchical for dependencies.
- Arrows always carry one declared meaning; legend when several coexist.
- Must survive grayscale and common color-vision deficiencies; never encode meaning by
  color alone (add line style, shape, or label). Color = semantic grouping only.
- Avoid edge crossings, dense text in boxes, ambiguous direction.

## Scientific Validation (run before finalizing)

Generic: arrows meaningful? causality implied wrongly? input/output direction consistent?
loops explicit? hidden vs observed distinct? training vs inference separate? measurement
vs prediction? control flow vs data flow? uncertainty shown appropriately?
Domain checklists: [HEP](diagrams-hep.md),
[statistics](diagrams-statistics.md),
[computer science](diagrams-computer-science.md).

## Specializations - load only the one needed

- HEP -> [diagrams-hep.md](diagrams-hep.md)
- Probability/statistics -> [diagrams-statistics.md](diagrams-statistics.md)
- Computer science / ML / agents -> [diagrams-computer-science.md](diagrams-computer-science.md)

## Reference Routing

- Layout, abstraction levels, decomposition, refactoring, type transformations ->
  [general-diagram-principles.md](general-diagram-principles.md)
- Typography, color, column widths, style spec, multi-figure consistency ->
  [diagram-figure-style.md](diagram-figure-style.md)
- Mermaid / Graphviz / PlantUML / TikZ syntax patterns and pitfalls ->
  [mermaid-patterns.md](mermaid-patterns.md),
  [graphviz-patterns.md](graphviz-patterns.md),
  [plantuml-patterns.md](plantuml-patterns.md),
  [tikz-patterns.md](tikz-patterns.md); SVG spec -> `../assets/diagrams/svg-spec.md`
- Captions and in-text references -> [diagram-captions.md](diagram-captions.md)
- Legends, multi-panel figures, posters/theses, Beamer overlays, equation placement, symbol table, export
  (SVG/PDF/PNG) -> [legends-panels-and-export.md](legends-panels-and-export.md)
- Starting skeletons -> `../assets/diagrams/` (research-workflow, algorithm-flowchart,
  system-architecture, hep-analysis-pipeline, probabilistic-graphical-model,
  agentic-ai-architecture, ml-pipeline, bayesian-model, svg-spec)
- Rough sketch or photo -> spec: [general-diagram-principles.md](general-diagram-principles.md) section 11
- Worked examples -> `../examples/general/`, `../examples/hep/`, `../examples/statistics/`, `../examples/computer-science/`
  (see `../examples/README.md`); the examples are illustrative, not verified against any
  named experiment or codebase.

## Ask vs. Assume; Do Not Invent

- **Ask** when the diagram's correctness depends on a fact not given: the process or
  Lagrangian for a Feynman diagram, causal assumptions for a DAG, which quantities are
  observed vs latent, the actual detector geometry, which components exist in a codebase.
- **Assume, state it, and proceed** for layout and abstraction choices, and for generic
  pipelines (label as conceptual).
- Never invent interactions, detector components, causal edges, services, or layers.
  Label what is inferred. Examples of stated assumptions:
  - "Arrows are data dependencies, not causal relationships."
  - "Conceptual event-processing diagram, not a specific experiment's reconstruction software."
  - "Simplified decay tree, not a formally verified Feynman diagram."
- If source files (code, configs, LaTeX, schemas, Docker, manifests) are available,
  read them before drawing an architecture; do not infer from filenames alone.
- Numbers in labels (file counts, section counts, layer sizes, thresholds) are facts: measure or copy
  them from the source (`ls | wc -l`, the code, the text) or leave them out. Count the things
  themselves, not mentions of them: counting the links in a `SKILL.md` over-counts a `references/` folder
  when some links point into other folders.
- Do not add generator, detector, or method details the source does not give (e.g. "parton shower +
  hadronization" for a plain "simulation"); leave the box generic and ask.

## Review, Refactor, Transform

- **Review**: evaluate correctness, readability, scientific meaning, complexity,
  missing pieces, ambiguous arrows, hierarchy, publication fitness; list concrete fixes.
- **Refactor** between abstraction levels (overview / paper / talk / technical /
  educational) keeping node identity traceable across versions.
- **Transform** across types (algorithm -> flowchart, Methods -> workflow, model
  description -> graphical model, code -> architecture, API -> sequence, schema -> ER).
  See the general principles reference.
- **Decompose** when one figure carries more than ~12-15 nodes or several messages:
  propose panels (a)/(b)/(c), each single-purpose.

## Shared Figure Style

For multi-figure papers, fix one `figure_style` block up front and reuse it; the block and its fields are in
[diagram-figure-style.md](diagram-figure-style.md#panels-and-multi-figure-consistency).

## Quick Checklist

- [ ] One message per figure; family chosen with reason
- [ ] Every node and arrow has a stated meaning; legend if mixed
- [ ] Known / Inferred / Assumed separated; assumptions written down
- [ ] Domain validation checklist run
- [ ] Grayscale-safe, readable at column width
- [ ] Source is editable text; syntax checked when a renderer was available
- [ ] Caption explains meaning and flow, not just box labels; no invented figure numbers

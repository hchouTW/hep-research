# Figure Captions and References

## Caption anatomy

1. **What it shows** (first sentence, standalone, complete - journals often use it as the short caption).
2. **How to read it**: direction of flow, edge meanings, shading/line conventions.
3. **What the key components mean** (only the non-obvious).
4. **Notation and abbreviations** defined at first use if not defined in the text.
5. **Scope/assumption** when relevant: "conceptual", "simplified", "not to scale", "arrows denote data dependence, not causation".

A caption must add information the boxes do not: purpose, relations, conventions. Never just restate labels.

## Pattern

`Figure X. <Overview of / Schematic of ...>. <Main flow sentence.> <Convention sentence.> <Scope/abbreviation sentence.>`

Do not invent figure numbers: use "Figure X" / `\ref{fig:...}` placeholders unless the user gives numbers.

## Examples

Analysis pipeline:
> Overview of the analysis workflow. Collision and simulated events are processed by the same event reconstruction and object selection before entering the statistical inference stage. Systematic uncertainties are modeled as nuisance parameters in the likelihood fit. Solid arrows denote data flow; dashed boxes denote simulation.

Graphical model:
> Graphical model of the hierarchical analysis. Shaded nodes are observed, open nodes are latent; the plate indexes the $N$ groups. Arrows denote conditional dependence in the generative model, $p(\theta)\prod_i p(z_i\mid\theta)\,p(x_i\mid z_i,\theta)$, and are not interpreted causally.

Causal DAG:
> Assumed causal structure. Arrows denote direct causal effects assumed by the authors; the dashed node $U$ is an unmeasured confounder of $T$ and $Y$. The absence of an arrow from $Z$ to $Y$ encodes the assumption that $Z$ affects $Y$ only through $T$.

Architecture:
> System architecture. The orchestrator delegates sub-tasks (solid arrows, control) to specialist agents, which read from and write to tools (dashed arrows, data). Code execution occurs only in the sandbox.

Model figure:
> Model architecture. Bold boxes are learned modules; the dashed branch is used only during training. Tensor shapes are $(B,T,d)$ unless noted.

Multi-panel:
> (a) Event generation and detector simulation. (b) Event reconstruction. (c) Statistical analysis. Boxes in (c) correspond to the likelihood terms of Eq.~(\ref{eq:likelihood}).

## In-text references

- "As illustrated in Fig.~\ref{fig:pipeline}, the analysis consists of four stages: reconstruction, selection, background estimation, and statistical inference."
- Refer to *what the figure establishes*, not merely "see Fig. X". Use `\autoref`/`\cref` per venue style; "Fig." vs "Figure" per the journal.
- Sub-panels: `Fig.~\ref{fig:overview}(b)` or `\subref`.

## Alt text / accessibility (when requested)

One or two sentences naming the structure ("Left-to-right pipeline of five stages ... with a feedback arrow from validation to selection") - not a re-listing of labels.

## Checks

- Every symbol in the figure is defined in caption or text.
- Caption claims match the source (no extra stages); direction words match arrow directions.
- No unverified numbers; no "we show" for a figure that is a schematic of prior work without citation.
- Length: 1-4 sentences for a workflow; more only for multi-panel or convention-heavy figures.

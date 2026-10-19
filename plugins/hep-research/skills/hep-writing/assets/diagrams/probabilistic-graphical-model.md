# Template: Probabilistic Graphical Model

**Use for:** Bayesian networks, hierarchical models, latent-variable models, HMMs, plate notation.
**Assumption line:** edges denote conditional dependence in the generative model, not causation.

## Variable table (fill before drawing)

| symbol | role (observed / latent / parameter / hyperparameter / deterministic) | distribution / definition | indexed by (plate) |
|---|---|---|---|

## Factorization (write it; the graph must match)

`p(\text{everything}) = \prod ...`

## Graphviz skeleton (observed = filled, latent = open, plate = cluster)

```dot
digraph model {
    rankdir=TB; node [fontname="Helvetica", shape=circle];
    alpha [shape=plaintext, label=<&alpha;>];
    theta [label=<&theta;>];
    subgraph cluster_N {
        label="i = 1..N"; labeljust=r; labelloc=b;
        z [label=<z<sub>i</sub>>];
        x [label=<x<sub>i</sub>>, style=filled, fillcolor="#dddddd"];
    }
    alpha -> theta; theta -> z; z -> x; theta -> x;
}
```
For nested plates and exact plate boundaries prefer TikZ (`fit` node; see `../references/tikz-patterns.md`).

## Checks

Shaded = observed only; plate contains exactly the indexed variables; global parameters outside;
priors on parameters; hyperparameters distinguished; d-separation statements you make are true in the
graph; if the user asks for causal reading, require stated assumptions.

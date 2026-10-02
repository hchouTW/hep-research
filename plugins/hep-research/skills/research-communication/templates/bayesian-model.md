# Template: Bayesian Model

**Use for:** a Bayesian analysis whose figure must show *both* the generative model (variables, plates) *and* the inference procedure.
Use `probabilistic-graphical-model.md` when only the model graph is needed, and `../examples/statistics/04-mcmc-workflow.md` for the sampler.
**Assumption line:** edges in the model graph denote conditional dependence in the generative model, not causation; arrows in the workflow denote data flow.

## 1. Model specification (fill first)

| symbol | role | distribution / definition | plate | observed? |
|---|---|---|---|---|
| `\mu` | hyperparameter with a prior (latent) | `\mu \sim \mathcal N(0,10)` | - | no |
| `\tau` | hyperparameter with a prior (latent) | `\tau \sim \mathrm{HalfCauchy}(5)` | - | no |
| `\sigma` | fixed known constant | `\sigma = \mathrm{const}` | - | fixed |
| `\theta_j` | latent parameter | `\theta_j \sim \mathcal N(\mu,\tau)` | j = 1..J | no |
| `y_{ij}` | data | `y_{ij} \sim \mathcal N(\theta_j,\sigma)` | i = 1..N_j | yes |

**Factorization** (the graph must match it exactly):
`p(y,\theta,\mu,\tau \mid \sigma) = p(\mu)\,p(\tau)\prod_j p(\theta_j \mid \mu,\tau) \prod_i p(y_{ij} \mid \theta_j,\sigma)`

## 2. Model graph (Graphviz; observed = filled, plates = clusters)

```dot
digraph model {
    rankdir=TB; graph [fontname="Helvetica"]; node [fontname="Helvetica", shape=circle];
    mu  [label=<&mu;>];
    tau [label=<&tau;>];
    sig [shape=plaintext, label=<&sigma;>];
    subgraph cluster_j {
        label="j = 1..J"; labeljust=r; labelloc=b;
        th [label=<&theta;<sub>j</sub>>];
        subgraph cluster_i {
            label=<i = 1..N<sub>j</sub>>; labeljust=r; labelloc=b;
            y [label=<y<sub>ij</sub>>, style=filled, fillcolor="#dddddd"];
        }
    }
    mu -> th; tau -> th; th -> y; sig -> y;
}
```
A bare (plaintext) symbol is a fixed constant only (here `\sigma`); a hyperparameter with a prior (here `\mu`, `\tau`) is a random variable and is drawn as a circle, with its prior in the specification table. Drawing a variable that has a prior as a bare symbol is a common mistake. For exact plate boundaries or nested-plate typography use TikZ (`../references/tikz-patterns.md`).

## 3. Inference workflow (Mermaid)

```mermaid
flowchart LR
    PR["Prior and model<br/>p(θ), p(y | θ)"] --> INF
    D[(Data y)] --> INF["Inference<br/>MCMC / VI / analytic"]
    INF --> DIA{"Diagnostics<br/>R-hat, ESS, divergences"}
    DIA -- fail --> REV["Revise model<br/>or sampler"] --> INF
    DIA -- pass --> POST["Posterior p(θ | y)"]
    POST --> PPC["Posterior predictive checks"]
    PPC -- misfit --> REV
    PPC -- adequate --> RES([Summaries, intervals, decisions])
    PR -.-> PRC["Prior predictive checks"] -.-> INF
```

## Checks

Shaded = observed only; each plate contains exactly the variables indexed by it; global parameters and hyperparameters
sit outside; priors are stated on every unobserved root; the posterior is computed, never an input; credible (not
confidence) intervals; prior sensitivity mentioned if the conclusion depends on the prior; any causal reading needs stated
assumptions (see `../examples/statistics/03-causal-dag.md`). Load `../references/probability-statistics.md`.

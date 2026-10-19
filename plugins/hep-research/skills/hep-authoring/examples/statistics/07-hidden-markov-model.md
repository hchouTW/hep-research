# Statistics 7: Hidden Markov model

**Request:** "Draw an HMM."
**Type:** dynamic Bayesian network (unrolled), T steps. Assumptions: first-order Markov states, emissions depend only on the current state. Edges = conditional dependence.

```dot
digraph hmm {
    rankdir=LR; node [shape=circle, fontname="Helvetica"];
    pi [shape=plaintext, label=<&pi;>]; A [shape=plaintext, label="A"]; B [shape=plaintext, label="B"];
    z1 [label=<z<sub>1</sub>>]; z2 [label=<z<sub>2</sub>>]; zT [label=<z<sub>T</sub>>];
    x1 [label=<x<sub>1</sub>>, style=filled, fillcolor="#dddddd"];
    x2 [label=<x<sub>2</sub>>, style=filled, fillcolor="#dddddd"];
    xT [label=<x<sub>T</sub>>, style=filled, fillcolor="#dddddd"];
    dots [shape=plaintext, label="…"];
    pi -> z1; z1 -> z2 [label="A"]; z2 -> dots -> zT;
    z1 -> x1 [label="B"]; z2 -> x2 [label="B"]; zT -> xT [label="B"];
    { rank=same; z1; x1 }   { rank=same; z2; x2 }   { rank=same; zT; xT }
}
```
Model: $p(z_{1:T},x_{1:T})=p(z_1)\prod_{t=2}^{T}p(z_t\mid z_{t-1})\prod_{t=1}^{T}p(x_t\mid z_t)$, with initial distribution $\pi$, transition matrix $A$, emission model $B$.
**Checks:** shaded = observed, open = latent; parameters π, A, B are shared across t (noted; a plate over t is the compact alternative); no edge from x to z.
**Caption:** Hidden Markov model unrolled over $T$ time steps. Latent states $z_t$ (open) form a first-order Markov chain with transition matrix $A$; each observation $x_t$ (shaded) depends only on the current state through the emission model $B$.

# Statistics 2: Hierarchical Bayesian model in plate notation

**Request:** "Turn this hierarchical model into plate notation."
**Given model (input):** μ₀, τ hyperparameters; θⱼ ~ N(μ₀, τ²) for groups j=1..J; y_ij ~ N(θⱼ, σ²) for i=1..N_j, σ known.
**Type:** graphical model, nested plates. Assumption: edges are conditional dependence, not causation.

Variable table: μ₀, τ, σ = hyperparameters/fixed (bare symbols); θⱼ latent (open circle, group plate); y_ij observed (shaded, inner plate).
Factorization: $p(\theta,y\mid\mu_0,\tau)=\prod_{j=1}^{J}p(\theta_j\mid\mu_0,\tau)\prod_{i=1}^{N_j}p(y_{ij}\mid\theta_j,\sigma)$.

```latex
% Requires tikz + libraries positioning, fit, backgrounds, calc (calc is needed for the $(mu)!0.5!(tau)$ coordinate). Compiled with Tectonic and inspected.
\begin{tikzpicture}[latent/.style={circle,draw,minimum size=9mm},
                    obs/.style={latent,fill=gray!25}, hyp/.style={inner sep=1pt}]
  \node[hyp] (mu) {$\mu_0$};  \node[hyp, right=8mm of mu] (tau) {$\tau$};
  \node[latent, below=10mm of $(mu)!0.5!(tau)$] (th) {$\theta_j$};
  \node[obs, below=10mm of th] (y) {$y_{ij}$};
  \node[hyp, right=12mm of y] (sig) {$\sigma$};
  \draw[-{Stealth}] (mu)--(th); \draw[-{Stealth}] (tau)--(th);
  \draw[-{Stealth}] (th)--(y);  \draw[-{Stealth}] (sig)--(y);
  \begin{scope}[on background layer]
    \node[draw,rounded corners,fit=(y),inner sep=4mm,label={[anchor=south east]south east:$N_j$}] (inner) {};
    \node[draw,rounded corners,fit=(th)(inner),inner sep=3mm,label={[anchor=south east]south east:$J$}] {};
  \end{scope}
\end{tikzpicture}
```
(Uses `calc` for the coordinate expression; add `\usetikzlibrary{calc}`.)
Graphviz alternative (single plate only) is in `../../references/graphviz-patterns.md`; use TikZ for nested plates.
**Caption:** Plate diagram of the hierarchical normal model. Group means $\theta_j$ (open circles) are drawn from a population distribution with hyperparameters $\mu_0,\tau$; observations $y_{ij}$ (shaded) are conditionally independent given $\theta_j$ with known variance $\sigma^2$. Plates repeat over $J$ groups and $N_j$ observations per group.

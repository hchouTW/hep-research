# Probability and Statistics Diagrams

## 1. Graphical models

| Element | Convention |
|---|---|
| observed random variable | shaded circle |
| latent random variable | unshaded circle |
| parameter (fixed unknown, or point estimate) | bare symbol / small square |
| hyperparameter **with a prior** (full Bayes) | a random variable: unshaded circle, outside the data plates, with its own prior stated |
| hyperparameter **set to a fixed value**, or a known constant | bare symbol, with the value or "fixed" marked |
| deterministic node | double circle or diamond |
| stochastic node | single circle |
| plate | rectangle around repeated variables, with index range (`N`) in the corner |
| directed edge | conditional dependence in a Bayesian network (factorization), *not* automatically causation |
| undirected edge | Markov random field |
| factor node | small filled square, connecting variables in a factor graph |

Factorization must be readable from the graph: `p(x_{1:N}, z_{1:N}, \theta) = p(\theta) \prod_i p(z_i\mid\theta)\,p(x_i\mid z_i,\theta)`.
Write it in the caption or a side annotation when the model is non-trivial.

Plate example (mixture-like):
```text
   α → θ
        ↓
   [ z_i → x_i ]  i = 1..N      (x_i shaded = observed; z_i, θ latent)
```
Plate rules: everything indexed by `i` is inside the plate; global parameters are outside;
nested plates for nested indices (`J` groups x `N_j` observations); edges may cross plate
boundaries only from outside-in (a global node feeding an indexed one).

Hierarchical model: hyperparameters -> group-level parameters (plate over groups) -> data (plate
inside). State the distribution on each edge or in a table.

HMM: chain of latent states `z_t`, transitions `p(z_t|z_{t-1})`, emissions `p(x_t|z_t)`, initial
`p(z_1)`; unrolled (t=1..T) or a plate over t for a stationary model; note that `x_t` shaded.
Dynamic Bayesian network: repeat a slice with inter-slice edges; state the Markov order.
Markov random field: undirected, cliques -> potentials; factor graphs when factors matter.

## 2. Inference workflows

Bayesian: `Prior p(θ) + Likelihood p(x|θ) + Observed data x -> Posterior p(θ|x) -> Posterior predictive p(x_new|x)`.
Data enters at the likelihood; the posterior is *computed*, not an input. Show computation
(analytic / MCMC / VI) as a labeled step when relevant. Prior predictive checks feed model
criticism, not the posterior.

Frequentist: `Sample -> Estimator/statistic -> Sampling (or null) distribution -> Test statistic -> p-value / CI`.
The sampling distribution is over *hypothetical repetitions*, not over the parameter. Never
place "probability of the hypothesis" downstream of a p-value.

Bootstrap: `Sample -> resample with replacement (B times) -> statistic each -> bootstrap distribution -> SE / CI`.
Permutation: `Sample -> permute labels (B times) -> statistic each -> null distribution -> p-value`.

## 3. MCMC / sampling flowcharts

Metropolis-Hastings loop: `state x_t -> propose x' ~ q(.|x_t) -> compute α = min(1, [p(x')q(x_t|x')]/[p(x_t)q(x'|x_t)]) -> u ~ U(0,1) -> u < α? accept x_{t+1}=x' : reject x_{t+1}=x_t -> t < T? loop : diagnostics`.
Distinguish burn-in / warm-up and thinning; convergence diagnostics (R-hat, ESS) run after (or
across) chains, not inside a single accept/reject step. Gibbs: sweep of conditionals, always
accepted. HMC: momentum resample -> leapfrog -> MH accept. Importance sampling: draw from proposal ->
weights `w=p/q` -> normalize. Rejection sampling: propose -> accept w.p. `p/(Mq)`. SMC: propagate ->
reweight -> resample loop over time.

## 4. Statistical models

Regression / GLM: `linear predictor η = Xβ -> link g^{-1} -> mean μ -> distribution -> y`. Mixed models:
fixed + random effects with grouping structure. Survival: hazard, censoring mechanism noted. State
space: latent state, observation equation, filtering flow. Gaussian process: prior over functions,
kernel with hyperparameters, posterior at test points. Draw the *data-generating* process, not just the
fitting algorithm.

## 5. Causal diagrams

DAG nodes = variables, edges = *assumed* direct causal effects. Role labels: treatment (T),
outcome (Y), confounder (common cause of T and Y), mediator (on the path T -> M -> Y),
collider (T -> C <- Y, conditioning opens a path), instrument (affects T, only through T affects Y),
selection node (S, conditioned on).

**Rules**
- Never add a causal edge because two variables are correlated.
- If the user has not stated causal assumptions, produce an *associational/conceptual* diagram, label
  it so, and ask for the assumptions.
- Unobserved confounding: dashed bidirected edge or explicit latent node `U`.
- Missing edge = strong claim of no direct effect - say so.
- Do not condition on colliders or mediators in an adjustment set without saying it.

Probability trees: branches labeled with conditional probabilities summing to 1 at every node; leaves
carry joint probabilities (product along the path); Bayesian updating = reversing the tree.

## 6. Validation checklist

- conditional dependence / independence claims match the graph (d-separation)
- parameter vs random variable; estimator vs estimand
- prior vs likelihood vs posterior placed correctly
- observed vs latent; deterministic vs stochastic
- sampling process vs inference process
- confidence interval vs credible interval (frequentist coverage vs posterior probability)
- correlation vs causation
- plates enclose exactly the indexed quantities

For statistical *analysis*/code (fits, limits, unfolding) see `hep-analysis` and `deep-learning`
(calibration); this reference only covers the diagram semantics.

## Identification claims on causal DAGs

Do not add adjustment or identification statements (backdoor, front-door, "control for X") unless the user asks. If you do,
derive them from the graph: list the paths, mark which are open, say which nodes are colliders or mediators, and note that an
unmeasured confounder cannot be adjusted for. Do not write sentences that conflate the effect being identified ("the effect of S
on T->C"). When unsure, state only what the graph encodes (edges present and absent) and leave the estimation strategy out.

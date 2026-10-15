# Statistics 4: MCMC (Metropolis-Hastings) workflow

**Request:** "Convert this MCMC algorithm into a flowchart." (Algorithm: Metropolis-Hastings, T iterations, burn-in B.)
**Type:** algorithm flowchart with a loop; convergence diagnostics after the loop.

```mermaid
flowchart TD
    S([Start]) --> I[/"Target p(x), proposal q, x_0, T, B"/]
    I --> K["t ← 0"]
    K --> PR["Propose x' ~ q(· | x_t)"]
    PR --> A["α ← min(1, p(x') q(x_t | x') / p(x_t) q(x' | x_t))"]
    A --> U["Draw u ~ Uniform(0,1)"]
    U --> D{"u < α ?"}
    D -- accept --> AC["x_{t+1} ← x'"]
    D -- reject --> RJ["x_{t+1} ← x_t"]
    AC --> N["t ← t + 1"]
    RJ --> N
    N --> L{"t < T ?"}
    L -- yes --> PR
    L -- no --> BI["Discard first B samples (burn-in)"]
    BI --> DG["Convergence diagnostics<br/>(R-hat, ESS, trace plots)"]
    DG --> O[/"Posterior samples"/]
    O --> E([End])
```
**Checks:** rejection *keeps* the current state (repeated sample), it does not resample; diagnostics use the collected chain(s), not a single step; Gibbs would have no accept/reject; HMC adds momentum + leapfrog before the accept step.
**Caption:** Metropolis-Hastings sampler. At each iteration a candidate is proposed and accepted with probability α; on rejection the chain repeats its current state. After T iterations the burn-in samples are discarded and convergence is assessed before the samples are used for inference.

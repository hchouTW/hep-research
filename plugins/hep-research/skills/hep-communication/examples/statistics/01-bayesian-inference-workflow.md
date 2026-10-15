# Statistics 1: Bayesian inference workflow

**Request:** "Diagram the Bayesian workflow from prior to posterior predictive."
**Type:** inference workflow. Arrows = "is combined into / computed from". Data enters at the likelihood; the posterior is computed, not an input.

```mermaid
flowchart TB
    PR["Prior p(θ)"] --> POST
    LK["Likelihood p(x | θ)"] --> POST
    X[(Observed data x)] --> POST
    POST["Posterior p(θ | x)<br/>∝ p(x | θ) p(θ)"] --> PP["Posterior predictive<br/>p(x_new | x) = ∫ p(x_new | θ) p(θ | x) dθ"]
    COMP["Computation: analytic / MCMC / VI"] -.-> POST
```
**Checks:** prior vs likelihood vs posterior placement; posterior is not called a "likelihood"; credible (not confidence) intervals come from the posterior.
**Caption:** Bayesian inference workflow. The prior and the likelihood of the observed data are combined by Bayes' theorem into the posterior, which is propagated to the posterior predictive distribution for new observations. The dashed box indicates that the posterior is evaluated numerically when no closed form exists.

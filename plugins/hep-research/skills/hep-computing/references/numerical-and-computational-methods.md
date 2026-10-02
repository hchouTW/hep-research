# Numerical and computational methods

Use when evaluating or designing a numerical/computational scientific
result — whether a paper's integral, fit, simulation, or scan is actually
trustworthy, or checking one's own computation before reporting it. This is
about *scientific validity of the computation*, not general software
engineering — code architecture, deployment, and service boundaries belong to
[agile-development-guide.md](agile-development-guide.md); running the actual physics fit or ML training belongs to
`hep-statistics`/`physics-ml`. **A numerical result is not validated merely
because the code runs.**

## Table of contents
- [Numerical reliability](#numerical-reliability)
- [Numerical validation workflow](#numerical-validation-workflow)
- [Optimization](#optimization)
- [Monte Carlo and sampling](#monte-carlo-and-sampling)
- [Scientific computing](#scientific-computing)
- [Computational experiment design](#computational-experiment-design)
- [Algorithmic reasoning](#algorithmic-reasoning)

## Numerical reliability

Check the subset relevant to the computation at hand:

- **Floating-point precision and conditioning**: does the computation involve
  subtracting nearly-equal large numbers, inverting a near-singular matrix, or
  otherwise amplifying rounding error?
- **Convergence**: for an iterative method (fit, ODE solver, series sum), was
  convergence actually verified (residual/step-size below a stated tolerance),
  or just assumed because the loop terminated?
- **Discretization, truncation, integration, and interpolation error**: for a
  numerical integral, grid, or lookup table, is the reported precision
  consistent with the resolution actually used?
- **Extrapolation risk**: is the result being evaluated inside the range the
  numerical method/table/fit was validated over, or extrapolated beyond it?
- **Optimizer/solver tolerance, binning sensitivity, parameter-scan
  resolution**: would a tighter tolerance, finer binning, or denser scan
  change the reported conclusion, not just its last significant digit?
- **Stochastic uncertainty**: for any result with a Monte Carlo component,
  does the reported uncertainty include the simulation's own statistical
  noise, separate from the physical/statistical uncertainty being measured?

## Numerical validation workflow

Use the subset appropriate to the computation:

```text
Known analytic/special case
        ↓
Convergence test (does the result stabilize as resolution/iterations increase?)
        ↓
Tolerance/resolution sensitivity (does the conclusion survive a stricter setting?)
        ↓
Independent implementation or cross-check (different method, tool, or code path)
        ↓
Physics/scientific sanity check (right sign, right order of magnitude, right limit)
```

A single run at one tolerance that "looks stable" has not been shown to be
converged — request or perform at least one point of comparison (a finer
setting, a known limit, or a second implementation) before treating the value
as validated.

## Optimization

Do not equate optimizer termination with proof that the intended (often
global) solution was found. Check:

- The objective and constraints actually being optimized match the stated
  scientific problem.
- Initialization: was more than one starting point tried, for a
  non-convex problem?
- Local vs. global minima: is there a reason to believe the found minimum is
  global (convexity, a scan showing no better basin) or is it merely the one
  the optimizer happened to reach?
- Convergence criteria: what tolerance/gradient-norm/iteration cap defined
  "done," and is it tight enough for the claimed precision?
- Parameter degeneracy and flat directions: does the likelihood/objective have
  a direction along which it barely changes — if so, a "well-determined"
  parameter estimate along that direction is not actually well constrained.

## Monte Carlo and sampling

- **Reproducibility**: is the random seed (or seed-handling scheme) recorded
  well enough that the result could be regenerated?
- **Statistical uncertainty and convergence**: does the reported precision
  reflect the actual number of samples/toys drawn, and was convergence with
  sample size checked rather than assumed?
- **Sampling efficiency, importance weights, variance reduction**: for
  importance sampling or a reweighting scheme, are effective sample size and
  weight variance reported — a few dominant weights can silently invalidate an
  otherwise large nominal sample.
- **Rare-event sampling**: for a small-probability tail estimate, was a
  variance-reduction technique used, or is the estimate resting on a handful of
  rare draws with a large relative uncertainty?

For MCMC specifically, where applicable: burn-in/warmup, mixing, autocorrelation
time, use of multiple independent chains, and a convergence diagnostic
appropriate to the sampler. Do not demand a specific diagnostic (e.g. one named
statistic) unless the sampling method and claim actually call for it.

## Scientific computing

Scope this section to what materially affects scientific correctness or
reproducibility — not general software engineering, which belongs to
[agile-development-guide.md](agile-development-guide.md):

| Concern | Home |
|---|---|
| Code architecture, service boundaries, deployment | [agile-development-guide.md](agile-development-guide.md) |
| Numerical convergence, precision, reproducible seeds | this file |
| Provenance of a specific reported number (code version, config, inputs) | this file / `../../research-communication/references/reproducibility-auditing.md` |
| General CI/testing practice for a codebase | [agile-development-guide.md](agile-development-guide.md) |
| Monte Carlo/statistical validation of a scientific result | this file / `../../hep-statistics/references/statistical-inference-for-physics.md` |

Within that scope, check: is the random-state/seed management explicit enough
to reproduce a stochastic result; is there provenance for which code
version/configuration produced a quoted number; and, where numerical
regression matters (a long-lived pipeline whose output feeds later papers), is
there a reference dataset or known-value check that would catch a silent
regression?

## Computational experiment design

Relevant to simulations, phenomenology scans, ML-based scientific analyses, and
detector studies. The core question is whether the same information was used
to both build/tune the method and evaluate it — guard against circular
validation:

1. Design or tune the method.
2. Choose the model/selection based on that tuning.
3. Evaluate the final result.

If steps 1-2 and step 3 draw on overlapping information (the same events used
to optimize a selection and then quote its significance; hyperparameters tuned
against the final test metric) without a stated correction, the reported
performance is optimistically biased — identify this as a data-leakage/implicit-
tuning gap rather than accepting the final number at face value.

Where relevant, check for: a held-out validation sample distinct from the one
used to tune the method; a blinded signal region; closure tests (does the
method recover a known/injected answer on a control sample); injection tests
(does an artificially inserted signal come back at the injected size); null
tests (does the method report nothing when nothing is there); and whether
sensitivity/robustness was checked against the choices that were somewhat
arbitrary (binning, a selection threshold). For the depth of an ML ablation or
matched-budget comparison itself, hand off to `physics-ml`; for a physics
control/validation-region design, hand off to `hep-analysis` — this section is
for recognizing the gap while reading or reviewing, not for running the study.

## Algorithmic reasoning

Consider computational complexity, memory complexity, and scaling with dataset
size only when they affect feasibility, correctness, precision, or
reproducibility — not as abstract complexity-theory commentary. Relevant
questions: does an algorithm's scaling make a claimed dataset size actually
tractable; does an approximation used purely for speed change the numerical
answer beyond the stated tolerance; is a parallel/distributed implementation's
result confirmed to match its serial equivalent?

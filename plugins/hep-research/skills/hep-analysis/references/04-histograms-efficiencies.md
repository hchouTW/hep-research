# Histograms, Efficiencies, and Covariance

## Definitions and storage

Record bin edges, units, observable, selection, weight, and flow policy. Store sumw and sumw2 separately: a weighted-histogram uncertainty is not sqrt(sumw). If underflow/overflow is dropped, stored separately, or folded into edge bins, apply the same policy to variances. Compare edges, not only bin counts.

One value per independent event in mutually exclusive bins often permits a diagonal MC variance approximation. Multiple contributions from the same event require event-level treatment: combine same-bin contributions before estimating that event's variance contribution, and retain relevant cross-bin covariance. Unit-normalized histograms, subtraction, and unfolding generally introduce correlations.

Dividing by bin width divides variance by width squared. Further normalization by a total estimated from the same sample requires propagation of denominator covariance. Rebinning with a linear map A gives `y'=Ay` and `V'=AVA^T`.

## Efficiencies

Use a binomial model for unweighted independent Bernoulli trials where passing events are a subset of the total. Specify the interval method and level: for example Wilson, Clopper–Pearson, or Bayesian with a stated prior. Do not report only a zero Wald error at efficiencies zero or one.

For a weighted ratio `e=A/B`, first-order propagation gives

`Var(e) ≈ Var(A)/B^2 + A^2 Var(B)/B^4 - 2A Cov(A,B)/B^3`.

Passing and total samples share events. With the same event weights, their covariance can be obtained from the passing sumw2 under the corresponding independent-event approximation. Signed-weight ratios may fall outside [0,1]; do not clip them into probabilities. Near-zero denominators invalidate simple delta-method reasoning; consider event-level resampling or an explicit model with documented assumptions.

For a data/MC efficiency scale factor, propagate shared systematic sources and fitted-efficiency covariance. Tag-and-probe requires background modeling, pass/fail correlation, selection-bias checks, signal-shape uncertainty, and closure.

## Plotting

Use appropriate count intervals for data. Label MC bands as statistical-only, total prefit, or postfit. Postfit predictions need the full nuisance covariance; summing impacts in quadrature is generally insufficient. A zero denominator in a data/MC ratio is undefined, not zero. Empty data bins can have a nonzero upper uncertainty.

Define pull denominators. Data and a fitted prediction are not necessarily independent, so a simple residual divided by the square root of combined variances is a diagnostic under specific assumptions, not a universally standard-normal pull. Do not hide negative bins on a log scale; provide a signed-value view or explicit diagnostics.

Label observable units, bin-width conventions, luminosity, collision energy, region, channel, and data/simulation status. Do not attach collaboration approval labels without actual approval. Mask blinded bins in the main panel, ratio, and pull alike.

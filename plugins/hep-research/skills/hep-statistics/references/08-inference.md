# Statistical Inference, Significance, and Limits

## Define the question

State the POI, null and alternative hypotheses, one- or two-sided convention, confidence level, nuisance treatment, and data type. A p-value is a probability of results at least as incompatible under a hypothesis, not the probability that the hypothesis is true. For a one-sided Gaussian equivalent, use `Z=Phi_inverse(1-p)` without mixing two-sided conventions.

## Profile likelihood

Define `lambda(mu)=L(mu,theta_hat_hat_mu)/L(mu_hat,theta_hat)`. The usual two-sided statistic is `-2 log lambda`. For discovery q0, treatment of negative fitted strength must match the fitting convention. Upper-limit q_mu is commonly zero when the fitted strength exceeds the tested value. Physical lower bounds require the corresponding bounded statistic; do not mix q_mu and q-tilde formulas or reference distributions.

Wilks/Wald/Asimov approximations have regularity requirements. Sparse bins, weak identifiability, boundaries, discrete models, and strongly nonlinear nuisances may require toy calibration or other checks. A fixed rule such as five entries per bin does not guarantee validity. See the [original Cowan et al. paper](https://arxiv.org/abs/1007.1727).

## CLs and upper limits

Fix a convention in which larger q_mu is less compatible with the tested strength. Define `p_mu=P(q_mu>=q_obs | mu)` and `p_b_tail=P(q_mu>=q_obs | 0)`. A common convention is then `CLs=p_mu/p_b_tail`. Sources defining p_b through the opposite tail write the denominator as `1-p_b`. Verify a backend's definition instead of inferring it from the symbol alone.

For example, exclusion may use CLs<0.05. CLs is a modified exclusion criterion, not a posterior probability or a generic exact Neyman interval. Expected median and one-/two-standard-deviation bands describe background-only expected results or a specified asymptotic construction, not the standard error of an observed limit.

The scan must bracket the threshold crossing. If it does not, report that the limit lies outside the scanned range rather than returning an endpoint. Investigate failed fits and model behavior for nonmonotonic curves; report multiple intervals when appropriate.

## Toys, coverage, and trials

Record seeds, toy counts, generating parameters, auxiliary-observation fluctuations, nuisance generation strategy, and refitting rules. Fixed truth values, plug-in nuisances, and nuisance draws define different procedures and are not interchangeable.

For a tail estimate k/N, report Monte Carlo uncertainty. Zero exceedances do not establish p=0; use a binomial bound. Small toy ensembles cannot directly calibrate five-sigma tails. Coverage studies repeat the full procedure at multiple POI/nuisance truth points and report coverage, failure rates, and failure handling. Dropping failed fits can bias results.

Searching across masses, channels, or cuts creates a look-elsewhere effect. Obtain a global p-value from the full search procedure or a validated approximation; a single-point local p-value is not global.

## Bayesian inference

Specify priors and parameterization, and check posterior propriety. A flat prior in signal strength is not flat in its logarithm. For MCMC inspect multiple chains, R-hat, effective sample size, divergences, mixing, and tail sampling. State whether intervals are central or highest-posterior-density and assess prior sensitivity.

## Minimal cross-check

`counting_reference.py` assumes nonnegative signal, exactly known background, and a flat prior in signal yield. Its credible bound is not expected to match CLs with background uncertainty. With zero observations and zero background, its 95% upper bound is `-log(0.05)≈2.995732`; this is a reference for that specific model.

# Unfolding: algorithms, regularization and coverage

Part of hep-statistics: load that skill first if it is not loaded (its step 1 validates the response).

The unfolded spectrum is a `statistical-result`: write it from the `dagostini-unfold` output with
`<plugin root>/skills/hep-statistics/scripts/result_artifact.py --cli-output <unfold.json> --paradigm likelihood-only
--construction other --test-statistic none --poi unfolded_spectrum --label <label> --artifact-id <id> --out
<artifacts_dir>/<name>.json` (it keeps estimate, sigma_total and the covariances), and keep scan, closure and coverage
outputs outside `artifacts_dir`.

This is the one place for unfolding methods in the plugin (ownership table in `docs/routing-contract.md`). The response
object, forward folding of a prediction and the double-counting checks belong to hep-detector
([response and forward folding](../../hep-detector/references/response-and-forward-folding.md)); whether a
measurement should be unfolded at all, and at which level it is published, is a design question for hep-measurement
([measurement definitions](../../hep-measurement/references/measurements-and-unfolding.md)).

Executable validation: `<plugin root>/core/stats/unfolding_diagnostics.py outer-coverage` repeats data, MC response and
efficiency draws and the regularization choice inside every outer toy and reports bias, marginal and simultaneous
coverage; a pull width measured on the ensemble that tuned the regularization is not independent evidence.
An external package (pyunfold, or RooUnfold through ROOT) runs through `<plugin root>/adapters/unfolding/assets/unfold.py`,
which applies the same validation to a regularization declared before the run: nominal and reweighted closure, stress
tests and toy coverage (exit 1 when one fails); `compare-core` checks pyunfold against the core estimator up to 60 bins.

## Choosing a method

Choose forward-folded likelihoods, matrix methods, regularized inversion, or iterative Bayesian unfolding according to
the target and project. When the result is a fit of a few model parameters, a forward-folded likelihood in reco space
avoids unfolding; unfolding is needed when the deliverable is a truth-level spectrum other people will compare with.
Regularization and stopping rules trade variance against bias. Use predefined criteria and independent truth
variations, not visual smoothness alone.

### Methods and what each assumes

- **Regularized inversion, SVD** (Hoecker and Kartvelishvili, NIM A372 (1996) 469, hep-ph/9509307): the response is
  decomposed into singular values and the small ones, which amplify noise, are damped or cut; the regularization is the
  number of kept components or the damping strength. `unfolding_diagnostics.py --method tsvd` is the truncated form.
- **Tikhonov least squares with an area constraint, TUnfold** (Schmitt, JINST 7 (2012) T10003, arXiv:1205.6201):
  least-squares fit of the truth with a curvature (or other) penalty, background subtraction and an optional constraint
  on the total; the strength is chosen by the L-curve or a minimum global correlation. `--method tikhonov` is the
  curvature-penalty form without the area constraint.
- **Iterative Bayesian (D'Agostini)** (NIM A362 (1995) 487; improved treatment of uncertainties: arXiv:1010.0632):
  Bayes' theorem applied iteratively from a prior; the iteration count is the regularization, and the result depends
  on the prior for few iterations. Scan the iterations with `statistical_toys.py unfold-scan`, check `closure`, then
  unfold the data with its covariance with `unfolding_diagnostics.py dagostini-unfold`.
- **Fully Bayesian unfolding** (Choudalakis, arXiv:1201.4612): the posterior over truth spectra, regularized through
  a non-constant prior; report the prior and a prior-sensitivity study (as for any Bayesian result).
- **OmniFold** (Andreassen et al., PRL 124 (2020) 182001, arXiv:1911.09107): iterative reweighting of simulated events
  by classifiers, unbinned and in many observables at once; its uncertainty and coverage need the same toy validation
  as the binned methods, and the trained models are hep-ml artifacts.

### Binning: purity and stability

Choose truth and reco bins so that most events stay in their bin: purity (the fraction of reco-bin events generated in
the same truth bin) and stability (the fraction of truth-bin events reconstructed in the same bin) are commonly kept above
about one half; bins narrower than the resolution make the inversion unstable and the correlations large. Use at least
as many reco as truth bins (an underdetermined system is refused by `validate_response.py` for unfolding).

## Validation

Validate nominal closure, alternative truth shapes, stress tests, injections, pulls/coverage, response MC statistics,
backgrounds, detector/theory effects, and regularization bias. Building the response and testing closure on the same
events may be optimistic; split samples or use valid resampling.

Coverage is a property of the full procedure (method, regularization choice, response uncertainty) at a stated truth.
Report bias and pull width per bin for at least one truth other than the one used to build the response, and state
the truths tested; a procedure validated only at the nominal truth has unknown coverage elsewhere.

**Regularized intervals undercover.** The regularized estimate is biased toward the prior or the smooth solution, so
intervals built around it (Bayesian credible intervals or a standard bootstrap) can cover well below nominal; Kuusela
and Panaretos (Ann. Appl. Stat. 9 (2015) 1671, arXiv:1505.04768) show this and restore nearly nominal coverage with an
iteratively bias-corrected bootstrap at a modest cost in length. State the coverage measured by
`unfolding_diagnostics.py outer-coverage` at the truths tested, or say it is not established.

## Uncertainties

Bootstrap at event level, preserving truth/reconstruction pairing and signed weights. Independently resampling matrix
cells destroys event correlations. Propagate each systematic consistently through response, background, and
efficiency; use the same nuisance variation when one source affects several components. Quote the unfolded result
with its full covariance (data and response parts); regularized bins are correlated, and a fit to the unfolded
spectrum that ignores those correlations is wrong.

**Strong negative correlations.** Weak regularization leaves adjacent unfolded bins strongly anticorrelated; the
covariance is then nearly singular and its inverse amplifies rounding and Monte Carlo noise. Validate it first
(`validate_covariance.py`: PSD and conditioning on the correlation matrix), fit with the full matrix, and if it is
ill-conditioned refit in reco space (forward folding) rather than inverting it; never drop the off-diagonal terms.

## Publishing

Publish the unfolded spectrum with its full covariance (statistical and systematic parts separately when possible),
the response matrix and the truth and reco binning, the regularization choice and its criterion, and the truths used
for the coverage study, so that others can refold a prediction or redo the comparison in reco space.

## Executable checks

`<plugin root>/core/stats/unfolding_diagnostics.py` runs regularization scans, closure and pulls, forward-fold versus
unfold-then-fit comparisons, response-statistics propagation and regularization-choice criteria on small matrices
(see the [core/stats guide](core-stats-commands.md#unfolding_diagnosticspy-regularization-closure-folding)). Validate the
response first with `<plugin root>/core/stats/validate_response.py`, declaring `"intended_use": "unfolding"` so that
rank deficiency and empty truth bins stay errors. These are diagnostics with independent Poisson data
and no systematics, not an unfolding framework; label results `[General method]` and keep the input status
(`synthetic`, `asimov`, `observed`) on every output.

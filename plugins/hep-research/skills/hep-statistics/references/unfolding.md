# Unfolding: algorithms, regularization and coverage

This is the one place for unfolding methods in the plugin (ownership table in `docs/routing-contract.md`). The response
object, forward folding of a prediction and the double-counting checks belong to detector-response
([response and forward folding](../../detector-response/references/response-and-forward-folding.md)); whether a
measurement should be unfolded at all, and at which level it is published, is a design question for hep-analysis
([measurement definitions](../../hep-analysis/references/measurements-and-unfolding.md)).

## Choosing a method

Choose forward-folded likelihoods, matrix methods, regularized inversion, or iterative Bayesian unfolding according to
the target and project. When the result is a fit of a few model parameters, a forward-folded likelihood in reco space
avoids unfolding; unfolding is needed when the deliverable is a truth-level spectrum other people will compare with.
Regularization and stopping rules trade variance against bias. Use predefined criteria and independent truth
variations, not visual smoothness alone.

## Validation

Validate nominal closure, alternative truth shapes, stress tests, injections, pulls/coverage, response MC statistics,
backgrounds, detector/theory effects, and regularization bias. Building the response and testing closure on the same
events may be optimistic; split samples or use valid resampling.

Coverage is a property of the full procedure (method, regularization choice, response uncertainty) at a stated truth.
Report bias and pull width per bin for at least one truth other than the one used to build the response, and state
the truths tested; a procedure validated only at the nominal truth has unknown coverage elsewhere.

## Uncertainties

Bootstrap at event level, preserving truth/reconstruction pairing and signed weights. Independently resampling matrix
cells destroys event correlations. Propagate each systematic consistently through response, background, and
efficiency; use the same nuisance variation when one source affects several components. Quote the unfolded result
with its full covariance (data and response parts); regularized bins are correlated, and a fit to the unfolded
spectrum that ignores those correlations is wrong.

## Executable checks

`<plugin root>/core/stats/unfolding_diagnostics.py` runs regularization scans, closure and pulls, forward-fold versus
unfold-then-fit comparisons, response-statistics propagation and regularization-choice criteria on small matrices
(see the [core/stats guide](core-stats-guide.md#unfolding_diagnosticspy-regularization-closure-folding)). Validate the
response first with `<plugin root>/core/stats/validate_response.py`. These are diagnostics with independent Poisson data
and no systematics, not an unfolding framework; label results `[General method]` and keep the input status
(`synthetic`, `asimov`, `observed`) on every output.

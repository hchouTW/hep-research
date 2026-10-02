# Systematic Uncertainties and Nuisance Correlations

## Source inventory

Use `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/systematics.csv` to record source, type, affected processes/eras/regions, correlation key, rate/shape behavior, payload, and validation. Nuisance names have statistical meaning: sharing a name often shares a parameter. Do not reuse names solely for convenience.

Correlations follow shared physical sources, measurement procedures, and documented prescriptions. Neither "all uncertainties in one year are correlated" nor "different years are independent" is a valid blanket rule. Decompose luminosity, JES, or object scale factors into justified components when prescribed. Represent partial Gaussian correlations with a covariance matrix or latent standard-normal variables; verify positive semidefiniteness and compatibility of pairwise correlations.

## Types and propagation

- **Rate-only:** change normalization with a parameterization valid over the relevant parameter domain. Log-normal factors are common for positive multiplicative effects, not mandatory for every source.
- **Shape:** preserve nominal/up/down templates, including bin and region migration. Renormalize only for a defined shape-only source and specified domain. Avoid adding the same rate effect again if templates already contain it.
- **Detector:** propagate affected four-momenta, sorting, selection, missing transverse momentum, categories, and related weights. Pairing variations on the same events helps control comparison noise.
- **Theory:** document scale combinations/envelopes, exclusions, PDF replica/Hessian confidence conventions, alpha-s, shower/hadronization, and generator alternatives according to the production prescription.
- **MC statistics:** model finite simulation precision independently of observed-data counting fluctuations. Check the applicability of Barlow–Beeston-type approximations to weighted or signed samples.

## Variation registry and implementation pattern

Keep a central registry (`${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/systematics.csv` or equivalent) recording, per
source: variation name and downstream suffix; type (weight, shape,
normalization-only, one-sided, envelope, theory set); samples affected; the data
exclusion rule; the correlation model across eras/channels/bins/processes; the
nominal branch or weight the variation replaces; and the validation tolerance with
known exceptions.

When implementing variations in code: build nominal histograms first; iterate over a
configured variation list rather than hand-writing each one; for weight systematics
replace only the weight expression; for shape systematics replace only the affected
kinematic columns and recompute any dependent selections (recomputing selections for a
weight-only variation, or failing to recompute them for a shape variation that moves
objects across thresholds, are both common bugs); write output objects using the exact
naming the downstream datacard or plotting tool expects; and record skipped variations
with a reason instead of silently dropping them.

## Template validation

Check edges, flow handling, finite values, variance bookkeeping, required sources, and units. Identical variations are an investigation flag, not proof of a bug. Migration may lower a bin for an Up variation; integral ordering cannot establish whether labels are reversed. Inspect payloads and generation code to establish direction.

A zero nominal with a nonzero variation needs explicit treatment; do not define ratios with arbitrary epsilons. Negative sample templates require a backend-compatible model. Investigate additional MC, justified rebinning, or a model supporting signed contributions. If smoothing or regularization is used, preserve raw templates and quantify closure, bias, and result changes.

## Model validation

Evaluate nuisance values at -1, 0, +1 and relevant extrapolation points. Check finite, valid expected rates and continuity within the designed parameter domain. Unbounded scanning of every nuisance is not required.

Quantify sensitivity, shape, correlation, and POI consequences before pruning sources. A small postfit impact alone does not justify removal. Freezing groups is a diagnostic; uncertainty decompositions can depend on method and order. Correlated impacts are not independent errors to add in quadrature.
